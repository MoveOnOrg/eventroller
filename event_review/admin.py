import re

from django.conf import settings
from django.contrib import admin
from django import forms
from django.utils.html import format_html, mark_safe

from event_store.models import Event
from reviewer.filters import ReviewerOrganizationFilter, review_widget
from event_review.filters import (filter_with_emptyvalue,
                                  CollapsedListFilter,
                                  EventAttendeeMaxFilter,
                                  EventAttendeeCountFilter,
                                  EventFullness,
                                  EventMaxDateFilter,
                                  EventMinDateFilter,
                                  IsPrivateFilter,
                                  HostStatusFilter,
                                  PoliticalScopeFilter,
                                  SortingFilter)

from huerta.filters import CollapsedListFilter, textinputfilter_factory

def phone_format(phone):
    return format_html('<span style="white-space: nowrap">{}</span>',
                       re.sub(r'^(\d{3})(\d{3})(\d{4})', '(\\1) \\2-\\3',
                              phone))

def host_format(event):
    host = event.organization_host
    host_line = [format_html('{}', host)]
    host_items = []
    if event.host_is_confirmed:
        host_line.append(mark_safe(' (<span style="color:green">confirmed</span>) '))
    else:
        host_line.append(mark_safe(' (<span style="color:red">unconfirmed</span>) '))

    host_line.append(mark_safe('<br />'))

    if getattr(host, 'email', None):
        host_items.append(format_html('<a data-system-pk="{}" href="mailto:{}">email</a>',
                                      host.member_system_pk or '',
                                      host.email,
                                      host))


    host_link = event.host_edit_url(edit_access=True)
    if host_link:
        host_items.append(format_html('<a href="{}">Act as host</a>', host_link))

    # from the connector
    extra_html=event.extra_management_html()
    if extra_html:
        host_items.append(extra_html)

    # give settings a chance to tweak/alter/add items
    customize_host_link = getattr(settings, 'EVENT_REVIEW_CUSTOM_HOST_DISPLAY', None)
    if callable(customize_host_link):
        host_items = customize_host_link(event, host_items)
    host_items.insert(0, ' '.join(host_line))
    return mark_safe(' <span class="glyphicon glyphicon-star-empty"></span>'.join(host_items))

def long_field(longtext, heading=''):
    if not longtext:
        return ''
    return format_html(heading
                       + '<div style="max-height: 7.9em; overflow-y: auto" class="well well-sm">{}</div>',
                       longtext)

def event_list_display(obj, onecol=False):
    scope = obj.get_political_scope_display()
    if scope:
        scope = ' ({})'.format(scope)
    second_col = ''
    if not onecol:
        second_col = format_html("""
          <div class="col-md-6">
            <div><b>Private Phone:</b> {private_phone}</div>
            <div><b>Event Status:</b> {active_status}</div>
            {review_widget}
            {internal_notes}
          </div>
        """,
        private_phone=phone_format(obj.private_phone),
        active_status=obj.status,
        review_widget=review_widget(obj, obj.organization_host_id),
        internal_notes=(long_field(obj.internal_notes,'<b>Past Notes</b>') if obj.internal_notes else '')
        )
    return format_html("""
        <div class="row">
            <div class="col-md-6">
                <h5>{title} ({pk}) {private}</h5>
                <div><b>Host:</b> {host}</div>
                <div><b>Where:</b>{political_scope}
                    <div>{venue}</div>
                    <div>{address}</div>
                    <div>{city}, {state}</div>
                </div>
                <div><b>When:</b> {when}</div>
                <div><b>Attendees:</b> {attendee_count}{max_attendees}</div>
                <div><b>Description</b> {description}</div>
                <div><b>Directions</b> {directions}</div>
                <div><b>Note to Attendees</b> {note_to_attendees}</div>
            </div>
            {second_col}
        </div>
        """,
        title=obj.title,
        pk=obj.organization_source_pk,
        venue=obj.venue,
        address='%s %s' % (obj.address1, obj.address2),
        city=obj.city,
        state=obj.state,
        political_scope=scope,
        when=obj.starts_at.strftime('%c'),
        attendee_count=obj.attendee_count,
        max_attendees='/%s' % obj.max_attendees
                      if obj.max_attendees else '',
        private=mark_safe('<div class="label label-danger">Private</div>')
                if obj.is_private else '',
        host=host_format(obj),
        second_col=second_col,
        description=long_field(obj.public_description),
        directions=long_field(obj.directions),
        note_to_attendees=long_field(obj.note_to_attendees))

@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    change_list_template = "admin/change_list_filters_top.html" #part of huerta
    filters_collapsable = True
    filters_require_submit = True
    disable_list_headers = True
    list_striped = True
    list_display = (event_list_display,)
    list_filter = (ReviewerOrganizationFilter,
                   ('organization_campaign', CollapsedListFilter),
                   ('organization_status_review', filter_with_emptyvalue('New')),
                   ('organization_status_prep', filter_with_emptyvalue('Unclaimed')),
                   ('state', CollapsedListFilter),
                   ('political_scope', PoliticalScopeFilter),
                   IsPrivateFilter,
                   EventMinDateFilter,EventMaxDateFilter,
                   ('status', CollapsedListFilter),
                   HostStatusFilter,
                   EventAttendeeMaxFilter,
                   EventAttendeeCountFilter,
                   EventFullness,
                   SortingFilter,
                   textinputfilter_factory('Title',
                                           'title'),
                   textinputfilter_factory('Host Email',
                                           'organization_host__email'),
                   textinputfilter_factory('Host Name',
                                           'organization_host__name'),
                   textinputfilter_factory('City',
                                           'city'),
                   textinputfilter_factory('Zip',
                                           'zip'),
                   textinputfilter_factory('Event Id',
                                           'organization_source_pk'),
               )

    list_display_links = None

    def get_actions(self, request):
        actions = super(EventAdmin, self).get_actions(request)
        if 'delete_selected' in actions:
            del actions['delete_selected']
        return actions

    def has_delete_permission(self, request, obj=None):
        return False

    def has_add_permission(self, request, obj=None):
        return False

    def get_queryset(self, *args, **kw):
        qs = super(EventAdmin, self).get_queryset(*args, **kw)
        qs = qs.select_related('organization_host', 'organization_source')
        return qs
