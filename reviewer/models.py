from __future__ import unicode_literals

from django.db import models

from django.contrib.auth.models import User, Group
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey

from event_store.models import Organization

class ReviewGroup(models.Model):
  """
  many-to-many link of what groups can review for what organizations
  (TODO) Eventually, we may want a workflow that allows someone
  from one organization to vet events from another for the purposes
  of copying them over.  In that case, the org would allow sharing (see event_exim app)
  and wouldn't be added to the other org here, but a user might also be a member
  of more than one org, and both orgs might be ok with 'sharing' the vetting
  for the same event (assuming they have the same criteria).
  """
  organization = models.ForeignKey(Organization, db_index=True)
  group = models.ForeignKey(Group, db_index=True)


class Review(models.Model):
  content_type = models.ForeignKey(ContentType,
                                   editable=False,
                                   blank=True)
  object_id = models.IntegerField()
  content_object = GenericForeignKey('content_type', 'object_id')

  created_at = models.DateTimeField(auto_now_add=True)
  modified_at = models.DateTimeField(auto_now=True)

  organization = models.ForeignKey(Organization)
  reviewer = models.ForeignKey(User)
  key = models.CharField(max_length=128,
                         help_text=("the data key for what is being reviewed"
                                    " -- this allows multiple keys per-object"),
                         default="review")
  decision = models.CharField(max_length=128)


class ReviewLog(models.Model):
  content_type = models.ForeignKey(ContentType,
                                   editable=False,
                                   blank=True)
  object_id = models.IntegerField()
  content_object = GenericForeignKey('content_type', 'object_id')

  organization = models.ForeignKey(Organization)
  reviewer = models.ForeignKey(User)
  created_at = models.DateTimeField(auto_now_add=True)
  message = models.TextField()


#keep these just in redis
#Claims
#  release    
