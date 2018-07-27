from django.contrib import admin

from event_store.models import Organization
from event_exim.models import EventDupeGuesses
from event_review.admin import EventDisplayAdminMixin


admin.site.register(Organization)

@admin.register(EventDupeGuesses)
class EventDupeGuessesAdmin(admin.ModelAdmin, EventDisplayAdminMixin):
    list_display = ('source_event_list_display', 'dupe_event_list_display', 'decision')
    list_display_links = None
    list_editable = ('decision',)

    def source_event_list_display(self, eventdupeguess):
        return self.event_list_display(eventdupeguess.source_event, onecol=True)
    source_event_list_display.short_description = "Original Event"

    def dupe_event_list_display(self, eventdupeguess):
        return self.event_list_display(eventdupeguess.dupe_event, onecol=True)
    dupe_event_list_display.short_description = 'Duplicate Event'
    
