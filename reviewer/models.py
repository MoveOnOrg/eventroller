from __future__ import unicode_literals

from django.db import models

from django.contrib.auth.models import User, Group

from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey


class Review(models.Model):
  content_type = models.ForeignKey(ContentType,
                                   editable=False,
                                   blank=True)
  object_id = models.IntegerField()
  content_object = GenericForeignKey('content_type', 'object_id')

  created_at = models.DateTimeField(auto_now_add=True)
  modified_at = models.DateTimeField(auto_now=True)

  reviewer = models.ForeignKey(User)

  decision = models.CharField(max_length=128)


class ReviewLog(models.Model):
  content_type = models.ForeignKey(ContentType,
                                   editable=False,
                                   blank=True)
  object_id = models.IntegerField()
  content_object = GenericForeignKey('content_type', 'object_id')

  reviewer = models.ForeignKey(User)
  created_at = models.DateTimeField(auto_now_add=True)
  message = models.TextField()


#keep these just in redis
#Claims
#  release    
