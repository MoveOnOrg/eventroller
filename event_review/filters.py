from django.contrib.admin.filters import AllValuesFieldListFilter, RelatedFieldListFilter
from django.db.models import Q
from huerta.filters import CollapsedListFilter
from event_store.models import EVENT_REVIEW_CHOICES


class ReviewFilter(CollapsedListFilter):

    def __init__(self, *args, **kw):
        CollapsedListFilter.__init__(self, *args, **kw)
        self.empty_value_display = "New"

