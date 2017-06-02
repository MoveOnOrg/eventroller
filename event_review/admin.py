from django.contrib import admin
from django import forms

from event_store.models import Event
from huerta.filters import CollapsedListFilter

@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = ('title',
                    'organization_status_review',
                    'organization_status_prep',
                    'status',
                    'organization_host',
                    'notes')
    list_filter = (('organization_status_review', CollapsedListFilter),
                   ('organization_status_prep', CollapsedListFilter),
                   ('organization_campaign', CollapsedListFilter),
                   ('state', CollapsedListFilter),
                   ('is_private', CollapsedListFilter),
                   ('starts_at', CollapsedListFilter),
                   ('ends_at', CollapsedListFilter),
                   ('attendee_count', CollapsedListFilter),
                   ('status', CollapsedListFilter),
                   ('host_is_confirmed', CollapsedListFilter))
    list_display_links = None
