import datetime
import json
import time

from django.contrib.contenttypes.models import ContentType
from django.http import HttpResponse, HttpResponseForbidden
from django.shortcuts import render

from django_redis import get_redis_connection

from reviewer.models import Review, ReviewLog

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

#TODO auth
def save_review(request, organization, content_type):
    # save a review
    redis = get_redis_connection("default")
    itemskey = '{}_items'.format(organization)
    reviewskey = '{}_reviews'.format(organization)

    if request.method == 'POST':
        content_type = request.POST.get('content_type')
        pk = request.POST.get('pk')
        decisions_str = request.POST.get('decisions','')
        log_message = request.POST.get('log')
        if content_type and pk and len(decisions_str) >= 3 and ':' in decisions_str:
            ct = ContentType.objects.get_for_id(int(content_type))
            # make sure the object exists
            obj = ct.get_object_for_this_type(pk=pk)
            decisions = [d[:257].split(':') for d in decisions_str.split(';')]
            # 1. save to database
            reviews = [Review.objects.create(content_type=ct, object_id=obj.id,
                                             reviewer=request.user,
                                             key=k, decision=decision)
                       for k,decision in decisions]

            if log_message:
                ReviewLog.objects.create(content_type=ct,
                                         object_id=obj.id,
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

#TODO auth
def get_review_history(request, organization):
    redis = get_redis_connection("default")
    reviewskey = '{}_reviews'.format(organization)

    content_type_id = int(request.GET.get('type'))
    pks = request.GET.get('pks').split(',')
    getlogs = request.GET.get('logs')

    pk_keys = ['{}_{}'.format(content_type_id, pk) for pk in pks]
    reviews = redis.hmget(reviewskey, **pk_keys)
    logs = []
    if getlogs:
        for pk in pks:
            logs.append({"pk": pk, 'type': content_type_id,
                         "m": [{
                             'r': r['reviewer__first_name'],
                             'm': r['message'],
                             'ts': int(time.mktime(r['created_at'].timetuple()))
                         } for r in ReviewLog.objects.filter(
                             content_type_id=content_type_id,
                             object_id=int(pk)
                         ).order_by('-id').values_list('reviewer__first_name',
                                                       'message',
                                                       'created_at')
                           ]})
    return HttpResponse("""{"reviews":[{reviews}],"logs":[{logs}]}""".format(
        reviews=','.join([o.encode('utf-8') for o in reviews]),
        logs=json.dumps(logs)
    ), content_type='application/json')

#TODO auth
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
    too_old = int(time.time()) - 60*60*2 #2 hours
    redis = get_redis_connection("default")
    rkey = '{}_marks'.format(organization)
    marks = sorted([json.loads(v.decode('utf-8'))
             for v in redis.hgetall(rkey).values()],
                   key=lambda m:m[3], reverse=True)
    to_delete = [m[2] for i,m in enumerate(marks)
                 if i > max or m[3] < too_old]
    if to_delete:
        redis.hdel(rkey, *to_delete)


#TODO auth
def current_review_state(request, organization):
    """
    for polling fast updates
    {
      objects: [
        {"type":"<event content type id>",
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
        pass
    else:
        if items[-1] == b'':
            #edge case of no items
            # redis.rpop'ing here could race with other client hits
            # so we will do that somewhere else
            items.pop()

    return HttpResponse("""{"objects":[{objects}],"marks":[{marks}]}""".format(
        objects=','.join([o.decode('utf-8') for o in items]),
        marks=','.join([m.decode('utf-8') for m in marks])
    ), content_type='application/json')
