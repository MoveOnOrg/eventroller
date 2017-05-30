from django.contrib import admin

from event_store.models import Event

@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = ('slug',
                    'organization_status_review',
                    'organization_status_prep',
                    'status',
                    'organization_host',
                    'notes')
    list_filter = ('organization_status_review',
                   'organization_status_prep',
                   'organization_campaign',
                   # US district
                   'state',
                   'is_private',
                   'starts_at',
                   'ends_at',
                   'attendee_count',
                   # event fields
                   'status',
                   'host_is_confirmed'
                   # sorting
                   )
