from datetime import datetime, timedelta
from django.conf import settings
from django.contrib.auth.models import Group
from django.core.management.base import BaseCommand

from optparse import make_option

from event_exim.models import EventSource, CRM_TYPES
from event_store.models import Organization

class Command(BaseCommand):

    def add_arguments(self, parser):
        parser.add_argument('--source',
                            help='event source name',
                            type=str)

    def handle(self, *args, **options):
        results = EventSource.autocreate_from_settings(source=options.get('source'))
        for source_name, source_results in list(results.items()):
            print(('{}:\n   {}'.format(source_name, "\n   ".join(source_results))))
