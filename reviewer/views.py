from collections import OrderedDict
import datetime
import json
import time

from django.contrib.contenttypes.models import ContentType
from django.http import HttpResponse, HttpResponseForbidden, Http404
from django.shortcuts import render, get_object_or_404

from django_redis import get_redis_connection

from reviewer.models import Review, ReviewLog, ReviewGroup

"""
  This api tries to keep things super-fast using redis datastructures
  per-organization.  Here's the list:

  Hashes:
   <organization>_marks key=username val=<json array of 4 items>
   <organization>_reviews key=<content_type>_<pk> val=<json obj>
  Lists:
   #slightly redundant to reviews, but focused on recent updates
   <organization>_items val=<json obj>
      Will be LTRIM'd to avoid going over 50 objects
  Log queries will search by PK one at a time,
   and will leverage django-cachalot
"""

_ORGANIZATIONS = {}  # by slug
def _get_org_groups(organization_slug):
    """
    memo-ize orgs--it'll be a long time before we're too big for memory
    """
    if organization_slug not in _ORGANIZATIONS:
        _ORGANIZATIONS[organization_slug] = list(ReviewGroup.objects.filter(
            organization__slug=organization_slug))
    grps = _ORGANIZATIONS[organization_slug]
    if not grps:
        raise Http404("nope") #if the org doesn't have any review groups its dead
    return grps

def reviewgroup_auth(view_func):
    """
    Confirms that user is in a ReviewGroup of the appropriate organization.
    Note: Assumes that `organization` is the first view parameter (after request)
    """
    def wrapped(request, organization, *args, **kw):
        allowed = _get_org_groups(organization)
        allowed_groups = set([x.group_id for x in allowed])
        group_ids = set(request.user.groups.values_list('id', flat=True))
        if not group_ids.intersection(allowed_groups) \
           and not request.user.is_superuser:
            return HttpResponseForbidden('nope')
        return view_func(request, organization, *args, **kw)
    return wrapped

@reviewgroup_auth
def save_review(request, organization, content_type):
    # save a review
    redis = get_redis_connection("default")
    itemskey = '{}_items'.format(organization)
    reviewskey = '{}_reviews'.format(organization)

    if request.method == 'POST':
        content_type = request.POST.get('content_type')
        pk = request.POST.get('pk')
        decisions_str = request.POST.get('decisions', '')
        log_message = request.POST.get('log')
        if content_type and pk and len(decisions_str) >= 3\
           and ':' in decisions_str:
            org = _get_org_groups(organization)
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
            # 2. save to redis
            json_obj = {"type": ct.id, "pk": obj.id}
            json_obj.update(decisions)
            json_str = json.dumps(json_obj)

            obj_key = '{}_{}'.format(ct.id, obj.id)
            redis.hset(reviewskey, obj_key, json_str)
            redis.lpush(itemskey, json_str)
            redis.ltrim(itemskey, 0, 50)
            return HttpResponse("ok")
    return HttpResponse("nope!")


@reviewgroup_auth
def get_review_history(request, organization):
    redis = get_redis_connection("default")
    reviewskey = '{}_reviews'.format(organization)

    content_type_id = int(request.GET.get('type'))
    pks = request.GET.get('pks').split(',')
    getlogs = request.GET.get('logs')

    pk_keys = ['{}_{}'.format(content_type_id, pk) for pk in pks]
    reviews = redis.hmget(reviewskey, *pk_keys)
    logs = []
    if getlogs:
        for pk in pks:
            logs.append({"pk": pk, 'type': content_type_id,
                         "m": [{
                             'r': r['reviewer__first_name'],
                             'm': r['message'],
                             'ts': int(time.mktime(r['created_at'].timetuple()))
                         } for r in ReviewLog.objects.filter(
                             organization__slug=organization,
                             content_type_id=content_type_id,
                             object_id=int(pk)
                         ).order_by('-id').values_list('reviewer__first_name',
                                                       'message',
                                                       'created_at')]})
    return HttpResponse("""{"reviews":[%s],"logs":[%s]}""" % (
        ','.join([o.encode('utf-8') for o in reviews]),
        json.dumps(logs)
    ), content_type='application/json')


@reviewgroup_auth
def mark_attention(request, organization, content_type, pk):
    # POST/DELETE mark whether someone is looking at this
    # takes the reviewer name from login username
    # saved object: [<type>, <pk>, <name>, <timestamp>]
    # HSET <organization>_marks <name> <object>
    redis = get_redis_connection("default")
    rkey = '{}_marks'.format(organization)
    if request.method == "POST":
        name = request.user.get_full_name()
        redis.hset(rkey, name[:128], json.dumps([
            content_type[:32], int(pk), name[:128],
            int(time.time())
        ]))
        if reds.hlen(rkey) > 50:
            _clear_old_marks(organization)
    elif request.method == "DELETE":
        redis.hdel(rkey, name[:128])
    return HttpResponse("ok")


def _clear_old_marks(organization, max=50):
    too_old = int(time.time()) - 60*60*2  # 2 hours
    redis = get_redis_connection("default")
    rkey = '{}_marks'.format(organization)
    marks = sorted(
        [json.loads(v.decode('utf-8'))
         for v in redis.hgetall(rkey).values()],
        key=lambda m: m[3], reverse=True)
    to_delete = [m[2] for i, m in enumerate(marks)
                 if i > max or m[3] < too_old]
    if to_delete:
        redis.hdel(rkey, *to_delete)


@reviewgroup_auth
def current_review_state(request, organization):
    """
    for polling fast updates
    {
      objects: [
        {"type":<event content type id>,
         "pk": 123456,
         "<review key>":"<decision>",...
        }, ...
      ],
      marks: [
        ["event", <pk>, "<name>", <timestamp in epoch seconds>],
        ...
      ]
    }
    """
    redis = get_redis_connection("default")
    itemskey = '{}_items'.format(organization)
    items = redis.lrange(itemskey, 0, 50)
    marks = redis.hgetall('{}_marks'.format(organization)).values()
    if not items:
        # TODO: get them from db and save them to redis
        # if no items in db, then lpush empty string to items
        org = _get_org_groups(organization)
        #maybe just get most recent review for each object
        query = Review.objects.filter(organization_id=org[0].organization_id).order_by('-id')
        try:
            db_res = list(query.distinct('content_type', 'object_id', 'key')[:50])
        except NotImplementedError:
            #sqlite doesn't support 'DISTINCT ON' so we'll fake it
            db_res = []
            db_pre = list(query[:100]) # double
            already = set()
            for r in db_pre:
                key = (r.content_type_id, r.object_id, r.key)
                if key not in already:
                    db_res.append(r)
                    already.add(key)
                    if len(db_res) > 50:
                        break
        if not db_res:
            # no keys, so to stop db hits every time, we push an empty
            redis.lpush(itemskey, '')
        else:
            revs = OrderedDict()
            for rev in db_res:
                revs.setdefault(
                    (rev.content_type_id, rev.object_id),
                    {'type': rev.content_type_id,
                     'pk': rev.object_id}).update({rev.key: rev.decision})
            json_revs = [json.dumps(r) for r in revs.values()]
            redis.lpush(itemskey, *json_revs)
    else:
        if items[-1] == b'':
            # edge case of no items (or had no items earlier)
            # redis.rpop'ing here could race with other client hits so
            # we will just ignore until the queue fills up and it gets bumped
            items.pop()

    return HttpResponse("""{"objects":[%s],"marks":[%s]}""" % (
        ','.join([o.decode('utf-8') for o in items]),
        ','.join([m.decode('utf-8') for m in marks])
    ), content_type='application/json')
