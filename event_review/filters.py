from django.contrib.admin.filters import (AllValuesFieldListFilter,
                                          RelatedFieldListFilter,
                                          SimpleListFilter)
from django.db.models import Q
from huerta.filters import (CollapsedListFilter,
                            CollapsedListFilterMixin,
                            CollapsedSimpleListFilter)
from event_store.models import EVENT_REVIEW_CHOICES, Event


class ReviewFilter(CollapsedListFilter):

    def __init__(self, *args, **kw):
        CollapsedListFilter.__init__(self, *args, **kw)
        self.empty_value_display = "New"


class PoliticalScopeFilter(CollapsedListFilter):
    def get_display_value(self, val):
        return Event.political_scope_display(val)


class EventAttendeeMaxFilter(CollapsedSimpleListFilter):
    title = "Max attendees"
    parameter_name = "maxattendees"
    query_arg = 'max_attendees__range'

    def lookups(self, request, model_admin):
        # avoid commas which might be used by multi-choice marker
        return (('0-10', '0-10'),
                ('10-49', '10-49'),
                ('50-99', '50-99'),
                ('100-199', '100-199'),
                ('200-499', '200-499'),
                ('500-99999999', '500+'))

    def queryset(self, request, queryset):
        val = self.value()
        if val:
            arg = self.query_arg
            query = None
            for choice in val.split(','):
                qparam = Q(**{arg: choice.split('-')})
                if query is None:
                    query = qparam
                else:
                    query = query | qparam
            queryset = queryset.filter(query)
        return queryset


class EventAttendeeCountFilter(EventAttendeeMaxFilter):
    title = "Attendee count"
    parameter_name = "attending"
    query_arg = 'attendee_count__range'


class EventFullness(CollapsedSimpleListFilter):
    title = "How full is the event"
    parameter_name = "fullness"
    multiselect_enabled = False

    def lookups(self, request, model_admin):
        return ((0.9, '90% full'),
                (1.0, 'full'))

    def queryset(self, request, queryset):
        val = self.value()
        if val:
            queryset = queryset.extra(
                where=['max_attendees > 0 AND attendee_count/max_attendees >= %s'],
                params=[float(val)]
            )
        return queryset
