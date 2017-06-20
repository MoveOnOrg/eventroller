from django.contrib import admin

from event_store.models import Organization
from event_exim.models import EventDupeGuesses

def event_display(obj):
    return event_list_display(obj, onecol=True)

admin.site.register(Organization)

@admin.register(EventDupeGuesses)
class EventDupeGuessesAdmin(admin.ModelAdmin):
    list_display = ('source_event_list_display', 'dupe_event_list_display', 'decision')
    list_display_links = None
    list_editable = ('decision',)