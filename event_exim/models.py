import datetime
import importlib
import time

from django.conf import settings
from django.contrib.auth.models import User, Group
from django.contrib.postgres.fields import JSONField
from django.db import models
from django.utils.functional import cached_property

from event_store.models import Event, Organization
from event_exim import connectors


CRM_TYPES = {
    'actionkit_db': lambda: connectors.ActionKitDBWrapper,
    'actionkit_api': lambda: connectors.ActionKitAPIWrapper,
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

   crm_type = models.CharField(max_length=16, choices=[(k,k) for k in CRM_TYPES])

   crm_data = JSONField(null=True, blank=True)

   #(provided: ping url for update (put this on your thanks page for event creation)
   update_style = models.IntegerField(choices=(
       (0, 'manual only'),
       (1, 'ping'),
       (2, 'ping with event reference'),
       (3, 'daily pull'),
       (4, 'hourly'),))

   allows_updates = models.IntegerField(default=0, choices=((0,'no'), (1,'yes')), help_text='as sink')

   #(test connection button)
   last_update = models.CharField(max_length=128, null=True, blank=True)

   @property
   def data(self):
      """
      Canonical data for this record -- sometimes this can be loaded from settings
      so that the database doesn't need to store a password in plaintext
      """
      settings_data = getattr(settings, 'EVENT_SOURCES', {})
      return settings_data.get(self.name, self.crm_data)

   @cached_property
   def api(self):
      connector_module = importlib.import_module('event_exim.connectors.%s' % self.crm_type)
      return connector_module.Connector(self)


class EventDupeGuesses(models.Model):
  source_event = models.ForeignKey(Event, related_name='dupe_guesses')
  dupe_event = models.ForeignKey(Event, related_name='dupe_guess_sources')

  decision = models.IntegerField(choices=( (0, 'undecided'),
                                           (1, 'not a duplicate'),
                                           (2, 'yes, duplicates')))


class Org2OrgShare(models.Model):
  event_source = models.ForeignKey(EventSource, related_name='share_sources')
  event_sink = models.ForeignKey(EventSource, related_name='share_sinks')

  status = models.IntegerField(choices=( (-1, 'disabled'),
                                         (0, 'offered'),
                                         (1, 'enabled')))

  filters = JSONField(null=True, blank=True)

  created_at = models.DateTimeField(auto_now_add=True)
  modified_at = models.DateTimeField(auto_now=True)

  creator = models.ForeignKey(User)
