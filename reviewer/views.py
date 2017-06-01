import json

from django.shortcuts import render

from django_redis import get_redis_connection
#get_redis_connection("default").flushall()

def save_review(self, organization, content_type):
    # save a review
    pass

def get_review_history(self, organization):
    # take a bunch of ids and a content_type and get status+logs
    pass

def mark_attention(self, organization, content_type, pk):
    # mark whether someone is looking at this
    pass

def current_review_state(self, organization):
    """
    for polling fast updates
    {
      objects: [
      ]
    }
    """
    pass
