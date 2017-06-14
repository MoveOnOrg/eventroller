import re

from django.contrib import admin
from django import forms
from django.utils.html import format_html, mark_safe

from event_store.models import Event
from reviewer.filters import ReviewerOrganizationFilter, review_widget
from huerta.filters import CollapsedListFilter

def phone_format(phone):
    return format_html('<span style="white-space: nowrap">{}</span>',
                       re.sub(r'^(\d{3})(\d{3})(\d{4})', '(\\1) \\2-\\3',
                              phone))

def host_format(event):
    host_items = []
    host = event.organization_host
    if not host.email:
        host_items.append(str(host))
    else:
        host_items.append(format_html('<a data-system-pk="{}" href="mailto:{}">{}</a>',
                                      host.member_system_pk or '',
                                      host.email,
                                      host))

    if event.host_is_confirmed:
        host_items.append(mark_safe(' (<span style="color:green">confirmed</span>) '))
    else:
        host_items.append(mark_safe(' (<span style="color:red">unconfirmed</span>) '))

    host_link = event.host_edit_url(edit_access=True)
    if host_link:
        host_items.append(format_html('<a href="{}">Act as host</a>', host_link))
    return mark_safe(''.join(host_items))

def event_list_display(obj):
    scope = obj.political_scope_display()
    if scope:
        scope = ' ({})'.format(scope)
    return format_html("""
        <div class="row">
            <div class="col-md-6">
                <h5>{title} ({pk})</h5>
                {private}
                <div><b>Host:</b> {host}</div>
                <div><b>Where:</b>{political_scope}
                    <div>{venue}</div>
                    <div>{address}</div>
                    <div>{city}, {state}</div>
                </div>
                <div><b>When:</b> {when}</div>
                <div><b>Attendees:</b> {attendee_count}{max_attendees}</div>
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
        political_scope=scope,
        private_phone=phone_format(obj.private_phone),
        when=obj.starts_at.strftime('%c'),
        attendee_count=obj.attendee_count,
        max_attendees='/%s' % obj.max_attendees
                      if obj.max_attendees else '',
        private=mark_safe('<div class="label label-danger">Private</div>')
                if obj.is_private else '',
        host=host_format(obj),
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
        if 'delete_selected' in actions:
            del actions['delete_selected']
        return actions

    def has_delete_permission(self, request, obj=None):
        return False

    def has_add_permission(self, request, obj=None):
        return False

    def get_queryset(self, *args, **kw):
        qs = super(EventAdmin, self).get_queryset(*args, **kw)
        qs = qs.select_related('organization_host')
        return qs
