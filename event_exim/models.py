import datetime
import importlib
import time

from django.conf import settings
from django.contrib.auth.models import User, Group
from django.db import models
from django.utils.functional import cached_property
# from django.db.models.signals import post_save
# from django.dispatch import receiver

from event_store.models import Activist, Event, Organization
from event_exim import connectors


CRM_TYPES = {
    #'actionkit_db': lambda: connectors.ActionKitDBWrapper,
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
    origin_organization = models.ForeignKey(Organization, related_name='source')
    osdi_name = models.CharField(max_length=765)

    crm_type = models.CharField(max_length=16, choices=[(k,k) for k in CRM_TYPES])

    crm_data = models.TextField(null=True, blank=True)

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

    def __str__(self):
        return self.name

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
        if self.crm_type:
            connector_module = importlib.import_module('event_exim.connectors.%s' % self.crm_type)
            return connector_module.Connector(self)

    def update_events(self, last_update=None):
        """
        Sync events from source to local database
        """
        # 1. load events from our connector
        if last_update is None:
            last_update = self.last_update
        event_data = self.api.load_events(last_updated=last_update)

        all_events = {str(e['organization_source_pk']):e for e in event_data['events']}
        new_host_ids = set([e['organization_host'].member_system_pk for e in all_events.values()])
        existing = list(Event.objects.filter(organization_source_pk__in=all_events.keys(),
                                             organization_source=self))
        # 2. save hosts, new and existing Activist records
        host_update_fields = ('hashed_email', 'email', 'name', 'phone')
        existing_hosts = {a.member_system_pk:a
                          for a in Activist.objects.filter(member_system=self,
                                                           member_system_pk__in=new_host_ids)}
        for e in all_events.values():
            ehost = e.get('organization_host')
            if ehost:
                host_by_pk = existing_hosts.get(ehost.member_system_pk)
                if host_by_pk:
                    ehost.id = host_by_pk.id
                    for hf in host_update_fields:
                        if getattr(host_by_pk, hf) != getattr(ehost, hf):
                            ehost.save()
                            existing_hosts[ehost.member_system_pk] = ehost
                            break #inner loop
                else:
                    ehost.save()
                    existing_hosts[ehost.member_system_pk] = ehost

        # 3. bulk-create all new events not in the system yet
        existing_ids = set([e.organization_source_pk for e in existing])
        new_events = [Event(**e) for e in all_events.values()
                      if e['organization_source_pk'] not in existing_ids]
        Event.objects.bulk_create(new_events)

        # 4. save any changes to existing events
        for e in existing:
            self.update_event(e, all_events[e.organization_source_pk])
        # 5. now that we've updated things, save this EventSource record with last_updated
        self.last_update = event_data['last_updated']
        self.save()

    def update_event(self, event, new_event_dict):
        changed = False
        for k,v in new_event_dict.items():
            if k == 'organization_host' and event.organization_host:
                if not event.organization_host.likely_same(v):
                    event.organization_host = v
                    changed = True
            else:
                if getattr(event,k) != v:
                    setattr(event,k,v)
                    changed = True
        if changed:
            event.save()
        return changed


class EventDupeManager(models.Manager):
    def create_event_dupe(self, source_event, dupe_event):
        event_dupe = self.create(source_event = source_event, dupe_event = dupe_event, decision = 0)
        event_dupe.save()
        return event_dupe.id


class EventDupeGuesses(models.Model):
    source_event = models.ForeignKey(Event, related_name='dupe_guesses')
    dupe_event = models.ForeignKey(Event, related_name='dupe_guess_sources')

    decision = models.IntegerField(choices=( (0, 'undecided'),
                                             (1, 'not a duplicate'),
                                             (2, 'yes, duplicates')), 
                                             verbose_name = 'Status',
                                             null = True,
                                             blank = True
                                            )

    objects = EventDupeManager()
    class Meta:
        unique_together = (('source_event','dupe_event'),)
  
    def source_event_summary(self):
        source_event = '{} (source ID: {}): {}. {}, {}, {}, {}. "{}". RSVP: {}'.format(
            self.source_event.id,
            self.source_event.organization_source_pk,
            self.source_event.title,
            self.source_event.venue,
            self.source_event.address1,
            self.source_event.city,
            self.source_event.state,
            self.source_event.public_description,
            str(self.source_event.rsvp_url)
        )
        return source_event
    source_event_summary.short_description = 'Original Event'

    def dupe_event_summary(self):
        dupe_event = '{} (source ID: {}): {}. {}, {}, {}, {}. "{}". RSVP at {}'.format(
            self.dupe_event.id,
            self.dupe_event.organization_source_pk,
            self.dupe_event.title,
            self.dupe_event.venue,
            self.dupe_event.address1,
            self.dupe_event.city,
            self.dupe_event.state,
            self.dupe_event.public_description,
            str(self.dupe_event.rsvp_url)
        )
        return dupe_event
    dupe_event_summary.short_description = 'Duplicate Event'

# Currently doesn't handle the case where an event has more than one duplicate. 
# Implementing this should wait until we have a clear use case for dupe_id on events
# @receiver(post_save, sender = EventDupeGuesses, dispatch_uid = 'update_event_dupe')
# def update_event_dupe_id(sender, instance, **kwargs):
#     print("now in post save!")
#     # yes, a duplicate
#     if instance.decision == 2:
#         instance.dupe_event.dupe_id = instance.source_event_id
#         instance.dupe_event.save()
#         print("recording dupe id %s on event %s" %(instance.source_event_id, instance.dupe_event.id))
#     # undecided or not a duplicate
#     elif instance.decision == 1 or instance.decision == 0 or instance.decision == None:
#         instance.dupe_event.dupe_id = None
#         instance.dupe_event.save()
#         print("event %s dupe_id set to None" % instance.dupe_event.id)


class Org2OrgShare(models.Model):
  event_source = models.ForeignKey(EventSource, related_name='share_sources')
  event_sink = models.ForeignKey(EventSource, related_name='share_sinks')

  status = models.IntegerField(choices=( (-1, 'disabled'),
                                         (0, 'offered'),
                                         (1, 'enabled')))

  filters = models.TextField(null=True, blank=True)

  created_at = models.DateTimeField(auto_now_add=True)
  modified_at = models.DateTimeField(auto_now=True)

  creator = models.ForeignKey(User)
