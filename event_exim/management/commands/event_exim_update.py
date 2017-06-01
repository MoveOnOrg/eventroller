from datetime import datetime, timedelta
from django.conf import settings
from django.core.management.base import BaseCommand

from optparse import make_option

from event_exim.models import EventSource
from event_store.models import Event

class Command(BaseCommand):

    def add_arguments(self, parser):
        parser.add_argument('--source',
                            help='event source name',
                            type=str)
        parser.add_argument('--update_style',
                            help="\n".join(['which event sources should be updated?',
                                            ' 0=all manual only sources',
                                            ' 3=daily',
                                            ' 4=hourly',
                                        ]),
                            type=int)
        parser.add_argument('--last_update',
                            help=('Use this to override what to consider the last update.'
                                  ' Note that this may be a different kind of value per-connector'),
                            type=str)

    def handle(self, *args, **options):
        sources = []
        source = options.get('source')
        if source:
            sources.append(EventSource.objects.get(name=source))
        else:
            style = options.get('update_style')
            if style:
                sources = EventSource.objects.filter(update_style=style)
        for s in sources:
            kwargs = {}
            if options['last_update'] is not None:
                kwargs['last_update'] = options['last_update']
            print('updating', s, options['last_update'] or '')
            s.update_events(**kwargs)
