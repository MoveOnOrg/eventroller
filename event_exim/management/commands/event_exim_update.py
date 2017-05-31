from datetime import datetime, timedelta
from django.conf import settings
from django.core.management.base import BaseCommand

from optparse import make_option

from event_exim.models import EventSource
from event_store.models import Event

class Command(BaseCommand):

    def add_arguments(self, parser):
        parser.add_argument('source', help='event source name', type=str)

    def handle(self, *args, **options):
        source = options.get('source')
        evtsource = EventSource.objects.get(name=source)
        #TODO: maybe regulate updating based on argument and update_style
        all_events = evtsource.api.load_all_events()
        #evtsource.last_update
        event_ids = [e.organization_source_pk for e in all_events]
        existing = set(Event.objects.filter(
            organization_source_pk__in=event_ids,
            organization_source=evtsource).values_list('organization_source_pk', flat=True))
        new_events = [e for e in all_events
                      if e.organization_source_pk not in existing]
        print(Event.objects.bulk_create(new_events))
