import json

from django.contrib.admin.filters import SimpleListFilter
from django.contrib.contenttypes.models import ContentType
from django.utils.html import format_html, conditional_escape

from event_store.models import Organization, EVENT_REVIEW_CHOICES, EVENT_PREP_CHOICES
from reviewer.models import ReviewGroup

def review_widget(obj):
    return format_html('<div class="review" data-pk="{}"></div>', obj.id)

class ReviewerOrganizationFilter(SimpleListFilter):
    template = "reviewer/admin/reviewerorganizationfilter.html"
    parameter_name = "org"
    title = "Organization"

    fieldname = 'organization'

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