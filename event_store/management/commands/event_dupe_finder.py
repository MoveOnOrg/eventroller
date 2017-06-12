from datetime import datetime, timedelta
from django.conf import settings
from django.core.management.base import BaseCommand
from django.db.models import Count

from event_exim.models import EventDupeGuesses
from event_store.models import Event

class Command(BaseCommand):

    help = 'Checks events across all sources for events in the same zip code at the same time'

    def handle(self, *args, **options):
        # find events in the same zip code at the same time that have not already been marked dupes
        potential_dupes = Event.objects.values('zip','starts_at_utc').annotate(count = Count('id')).order_by().filter(count__gt = 1, dupe_id__isnull = True)
        if potential_dupes:
            for dupe in potential_dupes:
                events = Event.objects.filter(zip = dupe['zip'], starts_at_utc = dupe['starts_at_utc']).order_by('id')
                source_event = events[0]
                for x in range(1, dupe['count'], 1):
                    dupe_event = events[x]
                    EventDupeGuesses.objects.create_event_dupe(source_event,dupe_event)

    # def add_arguments(self, parser):
    #     parser.add_argument('--source',
    #                         help='event source name',
    #                         type=str)
    #     parser.add_argument('--update_style',
    #                         help="\n".join(['which event sources should be updated?',
    #                                         ' 0=all manual only sources',
    #                                         ' 3=daily',
    #                                         ' 4=hourly',
    #                                     ]),
    #                         type=int)
    #     parser.add_argument('--last_update',
    #                         help=('Use this to override what to consider the last update.'
    #                               ' Note that this may be a different kind of value per-connector'),
    #                         type=str)

    # def handle(self, *args, **options):
    #     sources = []
    #     source = options.get('source')
    #     if source:
    #         sources.append(EventSource.objects.get(name=source))
    #     else:
    #         style = options.get('update_style')
    #         if style:
    #             sources = EventSource.objects.filter(update_style=style)
    #     for s in sources:
    #         kwargs = {}
    #         if options['last_update'] is not None:
    #             kwargs['last_update'] = options['last_update']
    #         print('updating', s, options['last_update'] or '')
    #         s.update_events(**kwargs)
