import os
import sys

import boto3
import django
from django.conf import settings

"""
This makes it easy to call daily and hourly updates directly with a python path.
This is useful on frameworks like aws lambda+Zappa's events feature
https://github.com/Miserlou/Zappa#scheduling
"""

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "eventroller.settings")
django.setup()


def run_daily(event, context):
    from event_exim.models import EventSource
    last_update = None
    for source in EventSource.objects.filter(update_style=3):  # 3=daily
        if last_update is None:
            last_update = source.last_update
        else:
            last_update = min(source.last_update, last_update)
        source.update_events()

    from event_exim.models import EventDupeGuesses
    dupes = EventDupeGuesses.get_potential_dupes(last_update)
    if dupes:
        EventDupeGuesses.record_potential_dupes(dupes)
    else:
        print("no new suspected duplicated events")


def run_hourly(event, context):
    from event_exim.models import EventSource
    last_update = None
    for source in EventSource.objects.filter(update_style=4):  # 4=hourly
        if last_update is None:
            last_update = source.last_update
        else:
            last_update = min(source.last_update, last_update)
        source.update_events()
    from event_exim.models import EventDupeGuesses
    dupes = EventDupeGuesses.get_potential_dupes(last_update)
    if dupes:
        EventDupeGuesses.record_potential_dupes(dupes)
    else:
        print("no new suspected duplicated events")
