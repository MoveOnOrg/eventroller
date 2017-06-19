import datetime

from django.contrib.admin.filters import AllValuesFieldListFilter, RelatedFieldListFilter, SimpleListFilter
from django.db.models import Q
from huerta.filters import CollapsedListFilter, CollapsedSimpleListFilter
from event_store.models import EVENT_REVIEW_CHOICES


class ReviewFilter(CollapsedListFilter):

    def __init__(self, *args, **kw):
        CollapsedListFilter.__init__(self, *args, **kw)
        self.empty_value_display = "New"

class EventMinDateFilter(CollapsedSimpleListFilter):
    title = "events starting on or after"
    parameter_name = "mindate"
    query_arg = 'starts_at__gte'
    multiselect_enabled = False

    def lookups(self, request, model_admin):
        today = datetime.datetime.now().date()
        firstdate = today - datetime.timedelta(days=4)
        dates = [firstdate + datetime.timedelta(days=i) for i in range(30)]
        return [ (d.strftime('%Y-%m-%d'),
                  ('%s (today)' % d.strftime('%m/%d') if d==today else d.strftime('%m/%d')))
                 for d in dates]

class EventMaxDateFilter(EventMinDateFilter):
    title = "events starting on or before"
    parameter_name = "maxdate"
    query_arg = 'starts_at__lte'