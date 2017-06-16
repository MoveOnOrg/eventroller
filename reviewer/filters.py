import json
import datetime

from django.conf import settings
from django.contrib.admin.filters import SimpleListFilter
from django.contrib.contenttypes.models import ContentType
from django.urls import reverse
from django.utils.html import format_html, conditional_escape

from event_store.models import Organization, EVENT_REVIEW_CHOICES, EVENT_PREP_CHOICES
from reviewer.models import ReviewGroup

def review_widget(obj, subject_id=None):
    return format_html('<div class="review" data-pk="{}" {}></div>',
                       obj.id,
                       format_html('data-subject="{}"', subject_id)
                       if subject_id is not None else '')


class ReviewerOrganizationFilter(SimpleListFilter):
    template = "reviewer/admin/reviewerorganizationfilter.html"
    parameter_name = "org"
    title = "Organization"

    fieldname = 'organization'

    @property
    def poll_rate(self):
        """number of seconds that poll rate should update"""
        return getattr(settings, 'REVIEW_POLL_RATE', 15)

    def value(self):
        """
        If only one choice, then auto-choose it for the easy/default case
        """
        val = super(ReviewerOrganizationFilter, self).value()
        if not val and len(self.lookup_choices) == 1:
            val = self.lookup_choices[0][0]
        return val

    def get_slug(self):
        val = self.value()
        if val:
            return Organization.objects.filter(id=val).first().slug

    def get_path(self):
        return reverse('reviewer_base')[:-1] #lop off trailing /

    def review_schema_json(self):
        return json.dumps([
            {'name': 'review_status',
             'choices': EVENT_REVIEW_CHOICES,
             'label': 'Review Status'},
            {'name': 'prep_status',
             'choices': EVENT_PREP_CHOICES,
             'label': 'Prep Status'},
        ])

    def lookups(self, request, model_admin):
        # we need this to save the right content type with the review api
        self.content_type = ContentType.objects.get_for_model(model_admin.model)
        user = request.user
        return ReviewGroup.user_review_groups(request.user).values_list('organization_id', 'organization__title')

    def queryset(self, request, queryset):
        org = self.value()
        if org:
            filterargs = {self.fieldname: org}
            return queryset.filter(**filterargs)
        return queryset

class EventMinDateFilter(SimpleListFilter):
    title = "Event start date"
    parameter_name = "mindate"
    query_arg = 'starts_at__gte'

    def lookups(self, request, model_admin):
        today = datetime.datetime.now().date()
        firstdate = today - datetime.timedelta(days=4)
        dates = [firstdate + datetime.timedelta(days=i) for i in range(30)]
        return [ (d.strftime('%Y-%m-%d'),
                  ('%s (today)' % d.strftime('%m/%d') if d==today else d.strftime('%m/%d')))
                 for d in dates]

    def queryset(self, request, queryset):
        val = self.value()
        if val:
            kwargs = {self.query_arg: val}
            queryset = queryset.filter(**kwargs)
        return queryset
