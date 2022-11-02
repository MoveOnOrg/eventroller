import datetime
import importlib
import time

from django.conf import settings
from django.contrib.auth.models import User, Group, Permission
from django.db import models
from django.utils.functional import cached_property
from django.db.models import Count
from django.dispatch import Signal
# from django.db.models.signals import post_save
# from django.dispatch import receiver

from event_store.models import Activist, Event, Organization
from event_exim import connectors

CRM_TYPES = {
    #'actionkit_db': lambda: connectors.ActionKitDBWrapper,
    'actionkit_api': 1,
    'facebook': 1,
    #'actionnetwork',
    #'bsd',
    #'csv_uploads',
    #'osdi_endpoint'
}


event_source_updated = Signal(providing_args=["event_data", "last_update"])


class EventSource(models.Model):

    """
    This represents a source of data to fill event_store.models.Event

    One question is how best to connect an eventsource to the Event

    """
    name = models.CharField(max_length=128, help_text="e.g. campaign or just describe the system")
    origin_organization = models.ForeignKey(Organization, related_name='source')
    osdi_name = models.CharField(max_length=765)

    crm_type = models.CharField(max_length=16, choices=[(k, k) for k in CRM_TYPES])

    crm_data = models.TextField(null=True, blank=True)

    #(provided: ping url for update (put this on your thanks page for event creation)
    update_style = models.IntegerField(choices=(
        (0, 'manual or ping only'),
        (3, 'daily pull'),
        (4, 'hourly pull'),))

    allows_updates = models.IntegerField(default=0, choices=((0, 'no'), (1, 'yes')), help_text='as sink')

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

    def update_event(self, source_pk):
        event_dict = self.api.get_event(source_pk)
        if event_dict:
            self.update_events_from_dicts([event_dict])
        return event_dict

    def update_events(self, last_update=None):
        """
        Sync events from source to local database
        """
        # load events from our connector
        if last_update is None:
            last_update = self.last_update
        event_data = self.api.load_events(last_updated=last_update)
        self.update_events_from_dicts(event_data['events'])
        # now that we've updated things, save this EventSource record with last_updated
        self.last_update = event_data['last_updated']
        self.save()
        event_source_updated.send(self, event_data=event_data, last_update=self.last_update)

    def update_events_from_dicts(self, event_dicts):
        all_events = {str(e['organization_source_pk']): e for e in event_dicts}
        new_host_ids = set([e['organization_host'].member_system_pk
                            for e in all_events.values()
                            if e['organization_host']])
        existing = list(Event.objects.filter(organization_source_pk__in=all_events.keys(),
                                             organization_source=self))
        # 2. save hosts, new and existing Activist records
        host_update_fields = ('hashed_email', 'email', 'name', 'phone')
        existing_hosts = {a.member_system_pk: a
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
                            break  # inner loop
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
            self.update_event_from_dict(e, all_events[e.organization_source_pk])

    def update_event_from_dict(self, event, new_event_dict):
        changed = False
        for k, v in new_event_dict.items():
            if k == 'organization_host' and event.organization_host:
                if not event.organization_host.likely_same(v):
                    event.organization_host = v
                    changed = True
            else:
                if getattr(event, k) != v:
                    setattr(event, k, v)
                    changed = True
        if changed:
            event.save()
        return changed

    @classmethod
    def autocreate_from_settings(cls, source=None, possible_sources=None):
        from reviewer.models import ReviewGroup
        if possible_sources is None:
            possible_sources = getattr(settings, 'EVENT_SOURCES', {})
        results = {}
        if source:
            possible_sources = {k: v for k, v in possible_sources.items() if k == source}
        for source_name, source_data in possible_sources.items():
            data = source_data.get('autocreate')
            #validate
            if not data:
                results[source_name] = ['No autocreate key, skipping.']
            else:
                eventsource_spec = data.get('event_source')
                organization_spec = data.get('organization')
                if not eventsource_spec\
                   or not organization_spec\
                   or not set(eventsource_spec).issuperset(['osdi_name', 'crm_type'])\
                   or not set(organization_spec).issuperset(['title', 'slug', 'osdi_source_id', 'group']):
                    results[source_name] = [("Not all fields are available for autocreation."
                                             " See documentation at: "
                                             "TKTKTK")]
                    continue
                else:
                    # Ok, we have all the data we need.
                    # Now let's check what objects exist already
                    db_source = EventSource.objects.filter(name=source_name).first()
                    db_org = Organization.objects.filter(slug=organization_spec['slug']).first()
                    if db_source:
                        results[source_name] = ['Source already exists.']
                        continue
                    else:
                        results[source_name] = ['Creating EventSource %s.' % source_name]
                        db_source = EventSource(name=source_name)
                        for field, val in eventsource_spec.items():
                            if hasattr(db_source, field):
                                setattr(db_source, field, val)
                        if not db_org:
                            db_org = Organization()
                            for field, val in organization_spec.items():
                                if field == 'group':
                                    db_org.group, created = Group.objects.get_or_create(
                                        name=val)
                                    if created:
                                        p = list(Permission.objects.filter(
                                            content_type__app_label__in=['event_exim', 'event_store'],
                                            codename__in=['change_eventsource',
                                                          'change_event',
                                                          'change_organization']))
                                        if p:
                                            db_org.group.permissions.add(*p)
                                        results[source_name].append('Created organization group %s.' % val)
                                    else:
                                        results[source_name].append('Organization group %s already existed.' % val)
                                elif hasattr(db_org, field):
                                    setattr(db_org, field, val)
                            db_org.save()
                        db_source.origin_organization = db_org
                        db_source.save()

                        review_group = organization_spec.get('review_group')
                        if review_group:
                            db_review_group, created = Group.objects.get_or_create(
                                name=review_group)
                            if created:
                                p = list(Permission.objects.filter(
                                    content_type__app_label='event_store',
                                    codename='change_event'))
                                if p:
                                    db_review_group.permissions.add(*p)
                                results[source_name].append('Created review group %s.' % review_group)
                            ReviewGroup.objects.get_or_create(
                                organization=db_org,
                                group=db_review_group)
                            results[source_name].append('Allowed review group review access.')
        return results


class EventDupeManager(models.Manager):
    def create_event_dupe(self, source_event, dupe_event):
        event_dupe = self.create(source_event=source_event, dupe_event=dupe_event, decision=0)
        event_dupe.save()
        return event_dupe.id


class EventDupeGuesses(models.Model):
    source_event = models.ForeignKey(Event, related_name='dupe_guesses')
    dupe_event = models.ForeignKey(Event, related_name='dupe_guess_sources')

    decision = models.IntegerField(choices=((0, 'undecided'),
                                            (1, 'not a duplicate'),
                                            (2, 'yes, duplicates')),
                                   verbose_name='Status',
                                   null=True,
                                   blank=True
                                   )

    class Meta:
        unique_together = (('source_event', 'dupe_event'),)

    @staticmethod
    def get_potential_dupes(last_update=None):
        """
            Things that will muddle screening for duplicates:
            * Bad data, e.g. zip code typos, errors converting local time to starts_at_utc.
            * Missing data, e.g. virtual events with no zip code/location data
            Returns a QuerySet of zip + starts_at_utc pairs which match more than one event.
        """
        if last_update is None:
            return (
                Event.objects.values('zip', 'starts_at_utc')
                .annotate(count=Count('id'))
                .order_by()
                .filter(
                    count__gt=1,
                    zip__isnull=False,
                    starts_at_utc__isnull=False,
                    status='active'
                )
                .exclude(zip='')
            )
        # For ONLY new events, compare to all events to check for duplicates
        new_events = Event.objects.values('zip', 'starts_at_utc').order_by().filter(
                dupe_id__isnull=True,
                zip__isnull=False,
                starts_at_utc__isnull=False,
                updated_at__gt=last_update,
                status='active'
            ).exclude(zip='')
        dupe_events = Event.objects.values('zip', 'starts_at_utc').annotate(count=Count('id')).none()
        for new_event in new_events:
            dupes = Event.objects.values('zip', 'starts_at_utc').annotate(count=Count('id')).filter(
                zip=new_event['zip'], starts_at_utc=new_event['starts_at_utc'],
                count__gt=1,
                dupe_id__isnull=True,
                status='active'
            )
            dupe_events = dupe_events | dupes
        return dupe_events

    @ staticmethod
    def record_potential_dupes(potential_dupes):
        message = 'Recording new potential duplicate events: \n'
        for dupe in potential_dupes:
            events = (
                Event.objects
                .filter(zip=dupe['zip'], starts_at_utc=dupe['starts_at_utc'])
                .order_by('id')
            )
            for x in range(dupe['count']):
                for y in range(x+1, dupe['count']):
                    source_event = events[x]
                    dupe_event = events[y]
                    answer = EventDupeGuesses.objects.get_or_create(
                        source_event=source_event,
                        dupe_event=dupe_event,
                        decision=0
                    )
                    if not answer[1]:
                        message += (
                            "Duplicate event guess for {} and {} already recorded \n"
                            .format(source_event.id, dupe_event.id)
                        )
                    else:
                        message += (
                            "Recorded duplicate guess: Events {} and {} \n"
                            .format(source_event.id, dupe_event.id)
                        )
        return message

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

  status = models.IntegerField(choices=((-1, 'disabled'),
                                        (0, 'offered'),
                                        (1, 'enabled')))

  filters = models.TextField(null=True, blank=True)

  created_at = models.DateTimeField(auto_now_add=True)
  modified_at = models.DateTimeField(auto_now=True)

  creator = models.ForeignKey(User)
