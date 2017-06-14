from django.contrib import admin

from event_store.models import Organization
from event_exim.models import EventDupeGuesses

admin.site.register(Organization)

@admin.register(EventDupeGuesses)
class EventDupeGuessesAdmin(admin.ModelAdmin):
    list_display = ('source_event_summary', 'dupe_event_summary', 'decision')
    list_display_links = None
    list_editable = ('decision',)