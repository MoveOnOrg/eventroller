from __future__ import unicode_literals

from django.db import models
from event_store.models import Event, Organization
from event_exim import connectors

from django.contrib.auth.models import User, Group

from connectors.actionkit_db import ActionKitDBWrapper
from connectors.actionkit_api import ActionKitAPIWrapper

CRM_TYPES = {
    'actionkit_db': ActionKitDBWrapper,
    'actionkit_api': ActionKitAPIWrapper,
    #'facebook',
    #'actionnetwork',
    #'bsd',
    #'csv_uploads',
    #'osdi_endpoint'
}

class EventSource(models.Model):
   """
   This represents a source of data to fill event_store.models.Event

   One question is how best to connect an eventsource to the Event
   
   """
   name = models.CharField(max_length=128, help_text="e.g. campaign or just describe the system")
   origin_organization = models.ForeignKey(Organization)
   osdi_name = models.CharField(max_length=765)

   crm_type = models.CharField(max_length=16, choices=[(k,k) for k in CRM_TYPES.keys()])

   #Fields conditionally prompted based on crm_type, and meaning different things
   url = models.CharField(max_length=765)
   username = models.CharField(max_length=765)
   password = models.CharField(max_length=765)
   # (could be, e.g. actionkit campaign slug or id)
   token_pw1 = models.CharField(max_length=765)
   token_pw2 = models.CharField(max_length=765)
   token_pw3 = models.CharField(max_length=765)

   #(provided: ping url for update (put this on your thanks page for event creation)
   update_style = models.IntegerField(choices=(
       (0, 'manual only'),
       (1, 'ping'),
       (2, 'ping with event reference'),
       (3, 'daily pull'),
       (4, 'hourly'),))

   allows_updates = models.IntegerField(default=0, choices=((0,'no'), (1,'yes')), help_text='as sink')

   #(test connection button)
   last_update = models.CharField(max_length=128)


class EventDupeGuesses(models.Model):
  source_event = models.ForeignKey(Event, related_name='dupe_guesses')
  dupe_event = models.ForeignKey(Event, related_name='dupe_guess_sources')

  decision = models.IntegerField(choices=(
       (0, 'undecided'),
       (1, 'not a duplicate'),
       (2, 'yes, duplicates')))


class Org2OrgShare(models.Model):
  event_source = models.ForeignKey(EventSource, related_name='share_sources')
  event_sink = models.ForeignKey(EventSource, related_name='share_sinks')

  created_at = models.DateTimeField(auto_now_add=True)
  modified_at = models.DateTimeField(auto_now=True)

  creator = models.ForeignKey(User)
