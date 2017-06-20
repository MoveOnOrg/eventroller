from datetime import datetime, timedelta
from django.conf import settings
from django.core.management.base import BaseCommand

from event_exim.models import EventDupeGuesses

class Command(BaseCommand):

    help = ('Checks events across all sources for events in the same zip code '
            'at the same UTC start time and marks them as potential dupes for review.')

    def handle(self, *args, **options):
        dupes = EventDupeGuesses.get_potential_dupes()
        if dupes:
            EventDupeGuesses.record_potential_dupes(dupes)