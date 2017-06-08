import datetime
import json
import time

from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.http import HttpResponse, HttpResponseForbidden, Http404
from django.shortcuts import render, get_object_or_404
from django.views.decorators.csrf import csrf_exempt

from django_redis import get_redis_connection

from reviewer.models import Review, ReviewLog, ReviewGroup

"""
  This api tries to keep things super-fast using redis datastructures
  per-organization.  Here's the list:

  Hashes:
   <organization>_focus key=username val=<json array of 4 items>
   <organization>_reviews key=<content_type>_<pk> val=<json obj>
  Lists:
   #slightly redundant to reviews, but focused on recent updates
   <organization>_items val=<json obj>
      Will be LTRIM'd to avoid going over 50 objects
  Log queries will search by PK one at a time,
   and will leverage django-cachalot
"""

REDIS_CACHE_KEY = getattr(settings, 'REVIEWER_CACHE_KEY', 'default')

# should be the upperish size of simultaneous reviewers (per organization)
FOCUS_MAX = getattr(settings, 'REVIEWER_FOCUS_MAX', 30)

# the upperish size of how many review-changes will occur inside the poll rate
# queue_size should probably be less than focus_max
QUEUE_SIZE = getattr(settings, 'REVIEWER_QUEUE_SIZE', 12)

def reviewgroup_auth(view_func):
    """
    Confirms that user is in a ReviewGroup of the appropriate organization.
    Note: Assumes that `organization` is the first view parameter (after request)
    """
    def wrapped(request, organization, *args, **kw):
        allowed = ReviewGroup.org_groups(organization)
        allowed_groups = set([x.group_id for x in allowed])
        group_ids = set(request.user.groups.values_list('id', flat=True))
        if not group_ids.intersection(allowed_groups) \
           and not request.user.is_superuser:
            return HttpResponseForbidden('nope')
        return view_func(request, organization, *args, **kw)
    return wrapped

@reviewgroup_auth
def save_review(request, organization, content_type, pk):
    # save a review
    redis = get_redis_connection(REDIS_CACHE_KEY)
    itemskey = '{}_items'.format(organization)
    reviewskey = '{}_reviews'.format(organization)

    if request.method == 'POST':
        content_type = request.POST.get('content_type')
        decisions_str = request.POST.get('decisions', '')
        log_message = request.POST.get('log')
        if content_type and pk and len(decisions_str) >= 3\
           and ':' in decisions_str:
            org = ReviewGroup.org_groups(organization)
            ct = ContentType.objects.get_for_id(int(content_type))
            # make sure the object exists
            obj = ct.get_object_for_this_type(pk=pk)
            decisions = [d[:257].split(':') for d in decisions_str.split(';')]
            # 1. save to database
            reviews = [Review.objects.create(content_type=ct, object_id=obj.id,
                                             organization_id=org[0].organization_id,
                                             reviewer=request.user,
                                             key=k, decision=decision)
                       for k, decision in decisions]

            if log_message:
                ReviewLog.objects.create(content_type=ct,
                                         object_id=obj.id,
                                         organization_id=org[0].organization_id,
                                         reviewer=request.user,
                                         message=log_message)
            # 2. signal to obj
            if callable(getattr(obj, 'on_save_review', None)):
                obj.on_save_review(reviews, log_message)
            # 3. save to redis
            json_obj = {"type": ct.id,
                        "pk": obj.id,
                        'ts': int(time.mktime(datetime.datetime.utcnow().timetuple()))}
            json_obj.update(decisions)
            json_str = json.dumps(json_obj)

            obj_key = '{}_{}'.format(ct.id, obj.id)
            redis.hset(reviewskey, obj_key, json_str)
            redis.lpush(itemskey, json_str)
            redis.ltrim(itemskey, 0, QUEUE_SIZE)
            return HttpResponse("ok")
    return HttpResponse("nope!")


@reviewgroup_auth
def get_review_history(request, organization):
    redis = get_redis_connection(REDIS_CACHE_KEY)
    reviewskey = '{}_reviews'.format(organization)

    content_type_id = int(request.GET.get('type'))
    ct = ContentType.objects.get_for_id(content_type_id) # confirm existance
    pks = [pk for pk in request.GET.get('pks').split(',') if pk]
    getlogs = request.GET.get('logs')
    pk_keys = ['{}_{}'.format(content_type_id, pk) for pk in pks]
    cached_reviews = []
    if pk_keys:
        cached_reviews = redis.hmget(reviewskey, *pk_keys)
    logs = []
    if getlogs:
        for pk in pks:
            if not pk:
                continue
            review_logs = ReviewLog.objects.filter(
                             organization__slug=organization,
                             content_type_id=content_type_id,
                             object_id=int(pk)
                         ).order_by('-id').values('reviewer__first_name',
                                                  'reviewer__last_name',
                                                  'message',
                                                  'created_at')
            logs.append({"pk": pk, 'type': content_type_id,
                         "m": [{
                             'r': '{} {}'.format(r['reviewer__first_name'],r['reviewer__last_name'][:1]),
                             'm': r['message'],
                             'ts': int(time.mktime(r['created_at'].timetuple()))
                         } for r in review_logs]})
    reviews = []
    for i,r in enumerate(cached_reviews):
        if r is not None:
            reviews.append(r.decode('utf-8'))
        else: # no cached version yet
            pk = pks[i]
            objrev = {'pk': pk, 'type': content_type_id}
            org = ReviewGroup.org_groups(organization)
            dbreview = Review.reviews_by_object(
                content_type_id=content_type_id,
                object_id=pk,
                organization_id=org[0].organization_id
            )
            if dbreview:
                objrev.update(dbreview((content_type_id, pk)))
            else:
                obj = ct.get_object_for_this_type(pk=pk)
                objrev.update(getattr(obj, 'review_data', lambda: {})())

            obj_key = '{}_{}'.format(content_type_id, pk)
            json_str = json.dumps(objrev)
            redis.hset(reviewskey, obj_key, json_str)
            reviews.append(json_str)
    return HttpResponse(
        """{"reviews":[%s],"logs":%s}""" % (','.join(reviews), json.dumps(logs)),
        content_type='application/json')

@csrf_exempt
@reviewgroup_auth
def mark_focus(request, organization, content_type, pk):
    # POST/DELETE mark whether someone is looking at this
    # takes the reviewer name from login username
    # saved object: [<type>, <pk>, <name>, <timestamp>]
    # HSET <organization>_focus <name> <object>
    redis = get_redis_connection(REDIS_CACHE_KEY)
    rkey = '{}_focus'.format(organization)
    if request.method == "POST":
        name = request.user.get_full_name()
        redis.hset(rkey, name[:128], json.dumps([
            content_type[:32], int(pk), name[:128],
            int(time.time())
        ]))
        if redis.hlen(rkey) > FOCUS_MAX:
            _clear_old_focus(organization)
    elif request.method == "DELETE":
        redis.hdel(rkey, name[:128])
    return HttpResponse("ok")


def _clear_old_focus(organization, max=FOCUS_MAX):
    too_old = int(time.time()) - 60*60*2  # 2 hours
    redis = get_redis_connection(REDIS_CACHE_KEY)
    rkey = '{}_focus'.format(organization)
    focus = sorted(
        [json.loads(v.decode('utf-8'))
         for v in redis.hgetall(rkey).values()],
        key=lambda m: m[3], reverse=True)
    to_delete = [m[2] for i, m in enumerate(focus)
                 if i > max or m[3] < too_old]
    if to_delete:
        redis.hdel(rkey, *to_delete)


@reviewgroup_auth
def current_review_state(request, organization):
    """
    for polling fast updates
    {
      "reviews": [
        {"type":<event content type id>,
         "pk": 123456,
         "ts": <timestamp in epoch seconds>,
         "<review key>":"<decision>",...
        }, ...
      ],
      "focus": [
        [<event type id>, <pk>, "<name>", <timestamp in epoch seconds>],
        ...
      ]
    }
    """
    redis = get_redis_connection(REDIS_CACHE_KEY)
    itemskey = '{}_items'.format(organization)
    num_items = int(request.GET.get('num', QUEUE_SIZE / 2))
    items = redis.lrange(itemskey, 0, num_items)
    focus = redis.hgetall('{}_focus'.format(organization)).values()
    if not items:
        org = ReviewGroup.org_groups(organization)
        if not org:
            return HttpResponseForbidden('nope')
        #maybe just get most recent review for each object
        reviews = Review.reviews_by_object(max=QUEUE_SIZE,
                                           organization_id=org[0].organization_id)
        if not reviews:
            # no keys, so to stop db hits every time, we push an empty
            redis.lpush(itemskey, '')
        else:
            json_revs = [json.dumps(r) for r in reviews.values()]
            redis.lpush(itemskey, *json_revs)
    else:
        if items[-1] == b'':
            # edge case of no items (or had no items earlier)
            # redis.rpop'ing here could race with other client hits so
            # we will just ignore until the queue fills up and it gets bumped
            items.pop()

    return HttpResponse("""{"reviews":[%s],"focus":[%s]}""" % (
        ','.join([o.decode('utf-8') for o in items]),
        ','.join([m.decode('utf-8') for m in focus])
    ), content_type='application/json')
