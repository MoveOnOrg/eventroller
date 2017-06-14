from datetime import datetime, timedelta
from django.conf import settings
from django.core.management.base import BaseCommand
from django.db.models import Count

from event_exim.models import EventDupeGuesses
from event_store.models import Event

class Command(BaseCommand):

    help = ('Checks events across all sources for events in the same zip code '
            'at the same UTC start time and marks them as potential dupes for review.')

    """
        Things that will muddle screening for duplicates:
        * Bad data, e.g. zip code typos, errors converting local time to starts_at_utc.
        * Missing data, e.g. virtual events with no zip code/location data
    """

    def handle(self, *args, **options):
        potential_dupes = (
                Event.objects.values('zip','starts_at_utc')
                .annotate(count = Count('id'))
                .order_by()
                .filter(
                    count__gt = 1,
                    dupe_id__isnull = True,
                    zip__isnull = False,
                    starts_at_utc__isnull = False,
                    status = 'active'
                )
            )
        if potential_dupes:
            for dupe in potential_dupes:
                events = (
                    Event.objects
                    .filter(zip = dupe['zip'], starts_at_utc = dupe['starts_at_utc'])
                    .order_by('id')
                )
                for x in range(dupe['count']):
                    for y in range(x-1):
                        source_event = events[x]
                        dupe_event = events[y]
                        try:
                            (
                                EventDupeGuesses.objects
                                .create_event_dupe(source_event, dupe_event)
                            )
                            print (
                                "Documented duplicate guess: Events {} and {}"
                                .format(source_event.id, dupe_event.id)
                            )
                        except:
                            print (
                                "Duplicate event guess for {} and {} already documented"
                                .format(source_event.id, dupe_event.id)
                            )