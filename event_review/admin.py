import re

from django.conf import settings
from django.contrib import admin
from django import forms
from django.template.loader import render_to_string
from django.urls import reverse, NoReverseMatch
from django.utils.html import format_html, mark_safe

from event_store.models import Event
from reviewer.filters import ReviewerOrganizationFilter, review_widget
from reviewer.message_sending import MessageSendingAdminMixin
from event_review.filters import (filter_with_emptyvalue,
                                  CampaignFilter,
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
        if getattr(host, 'email', None) and getattr(settings, 'FROM_EMAIL', None):
            host_items.append(message_to_host(event))

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


def message_to_host(event):
    ### TODO: DELETE THIS METHOD
    ### We need to be able to pass the widget through the meta host_format, event_list_display
    try:
        api_link = reverse('event_review_host_message', args=[event.organization.slug, event.id, ''])
        return render_to_string(
            'reviewer/message_send_widget.html',
            {'obj_id':event.id,
             'placeholder': 'Optional message to host. Email will include a link to manage the event.',
             'link': api_link})
    except NoReverseMatch:
        return None


def long_field(longtext, heading=''):
    if not longtext:
        return ''
    return format_html(heading
                       + '<div style="max-height: 7.9em; max-width: 600px; overflow-y: auto" class="well well-sm">{}</div>',
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
class EventAdmin(MessageSendingAdminMixin, admin.ModelAdmin):
    def changelist_view(self, request, extra_context=None):
        extra_context = {'title': 'Event admin tool'}
        return super(EventAdmin, self).changelist_view(request, extra_context=extra_context)

    change_list_template = "admin/change_list_filters_top.html" #part of huerta
    filters_collapsable = True
    filters_require_submit = True
    disable_list_headers = True
    list_striped = True
    list_display = (event_list_display, 'send_message_widget')
    list_filter = (ReviewerOrganizationFilter,
                   ('organization_campaign', CampaignFilter),
                   ('organization_status_review', filter_with_emptyvalue('new')),
                   ('organization_status_prep', filter_with_emptyvalue('unclaimed')),
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
                   textinputfilter_factory('title',
                                           'title'),
                   textinputfilter_factory('host email',
                                           'organization_host__email'),
                   textinputfilter_factory('host name',
                                           'organization_host__name'),
                   textinputfilter_factory('city',
                                           'city'),
                   textinputfilter_factory('zip',
                                           'zip'),
                   textinputfilter_factory('event ID number (comma-separated)',
                                           'organization_source_pk',
                                           accept_multiple=True),
               )

    list_display_links = None

    def get_actions(self, request):
        actions = super(EventAdmin, self).get_actions(request)
        if 'delete_selected' in actions:
            del actions['delete_selected']
        ## TODO: bulk_message_send permissions conditional
        actions.update({'bulk_message_send': (
            self.bulk_message_send,
            'bulk_message_send',
            'Send a message to many people')})
        return actions

    def has_delete_permission(self, request, obj=None):
        return False

    def has_add_permission(self, request, obj=None):
        return False

    def get_queryset(self, *args, **kw):
        qs = super(EventAdmin, self).get_queryset(*args, **kw)
        qs = qs.select_related('organization_host', 'organization_source', 'organization')
        return qs

    ## BEGIN EventAdmin Message Sending
    send_a_message_placeholder = 'Optional message to host. Email will include a link to manage the event.'
    def message_template(self, message, event):
        """
        NOTE: This takes a while to render, almost entirely because
          get_host_event_link needs to get a login token by AK API, which takes some time.
          This will SLOW mass message delivery
        """
        src = event.organization_source
        host_link = src.api.get_host_event_link(event, edit_access=True,
                                                host_id=event.organization_host.member_system_pk,
                                                confirm=True)
        email_subject = 'Regarding your event'#'Regarding your event with %s' % event.organization.title
        message = render_to_string(
            'event_review/message_to_host_email.html',
            {'host_name': event.organization_host.name,
             'event': event,
             'source': src.name,
             'link': host_link,
             'message': message,
             'footer': getattr(settings, 'EVENT_REVIEW_MESSAGE_FOOTER',
                               "\nThanks for all you do.")})
        return {
            'to': event.organization_host.email,
            'subject': email_subject,
            'message_text': message,
            'from_line': settings.FROM_EMAIL,
        }

    def message_obj_lookup(self, event_id, organization, request):
        event = Event.objects.filter(id=event_id).select_related('organization_host', 'organization').first()
        if event and event.organization_host_id and event.organization_host.email:
            src = event.organization_source
            if src and hasattr(src.api, 'get_host_event_link'):
                return event

    ## END EventAdmin Message Sending
