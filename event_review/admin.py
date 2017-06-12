from django.contrib import admin
from django import forms
from django.utils.html import format_html, mark_safe

from event_store.models import Event
from reviewer.filters import ReviewerOrganizationFilter, review_widget
from huerta.filters import CollapsedListFilter

def event_list_display(obj):
    return format_html("""
        <div class="row">
            <div class="col-md-6">
                <h5>{title} ({pk})</h5>
                {private}
                <div><b>Host:</b> {host} ({host_is_confirmed})</div>
                <div><b>Where:</b>
                    <div>{venue}</div>
                    <div>{address}</div>
                    <div>{city}, {state}</div>
                </div>
                <div><b>When:</b> {when}</div>
                <div><b>Attendees:</b> {attendee_count}{max_attendees}</div>
                <div><b>Political Scope:</b> {political_scope}</div>
                <div><b>Description</b> {description}</div>
            </div>
            <div class="col-md-6">
                <div><b>Private Phone:</b> {private_phone}</div>
                <div><b>Event Status:</b> {active_status}</div>
                {review_widget}
            </div>
        </div>
        """,
        title=obj.title,
        pk=obj.organization_source_pk,
        venue=obj.venue,
        address='%s %s' % (obj.address1, obj.address2),
        city=obj.city,
        state=obj.state,
        political_scope=obj.political_scope,
        private_phone=obj.private_phone,
        when=obj.starts_at_utc,
        attendee_count=obj.attendee_count,
        max_attendees='/%s' % obj.max_attendees
                      if obj.max_attendees else '',
        host_is_confirmed='confirmed'
                          if obj.host_is_confirmed else 'unconfirmed',
        private=mark_safe('<div class="alert alert-danger">Private</div>')
                if obj.is_private else '',
        host=obj.organization_host,
        #review_status=obj.organization_status_review,
        #prep_status=obj.organization_status_prep,
        active_status=obj.status,
        review_widget=review_widget(obj),
        #notes=mark_safe('<textarea rows="5" class="form-control" readonly>%s</textarea>' % obj.notes)
        #    if obj.notes else None,
        description = mark_safe('<textarea rows="5" class="form-control" readonly>%s</textarea>' % obj.public_description)
            if obj.public_description else None)

@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    change_list_template = "admin/change_list_filters_top.html"
    filters_collapsable = True
    filters_require_submit = True
    disable_list_headers = True
    list_striped = True
    list_display = (event_list_display,)
    list_filter = (ReviewerOrganizationFilter,
                   ('organization_campaign', CollapsedListFilter),
                   ('organization_status_review', CollapsedListFilter),
                   ('organization_status_prep', CollapsedListFilter),
                   ('state', CollapsedListFilter),
                   ('is_private', CollapsedListFilter),
                   ('starts_at', CollapsedListFilter),
                   ('ends_at', CollapsedListFilter),
                   ('attendee_count', CollapsedListFilter),
                   ('status', CollapsedListFilter),
                   ('host_is_confirmed', CollapsedListFilter))
    list_display_links = None

    def get_actions(self, request):
        actions = super(EventAdmin, self).get_actions(request)
        del actions['delete_selected']
        return actions

    def has_delete_permission(self, request, obj=None):
        return False

    def has_add_permission(self, request, obj=None):
        return False
