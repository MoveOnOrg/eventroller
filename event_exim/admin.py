from django.contrib import admin

from event_exim.models import EventSource

@admin.register(EventSource)
class EventSourceAdmin(admin.ModelAdmin):

    list_display = ('name', 'origin_organization', 'crm_type',
                    'update_style', 'allows_updates', 'last_update')
