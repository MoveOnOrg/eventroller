from django.utils.html import linebreaks
from django.utils import timezone, dateformat

from drf_hal_json.serializers import HalModelSerializer
from rest_framework import serializers

from event_store.models import Event

class OsdiEventSerializer(HalModelSerializer):
    class Meta:
        model = Event
        fields = [
            'origin_system',
            'name',
            'title',
            'description',
            'browser_url',
            'type',
            'total_accepted',
            'status',
            'start_date',
            #'end_date', #does anyone use this?
            'capacity',
            'visibility',
            'location',
            #non-OSDI
            'human_time', #friendly display
            'human_date', #friendly display
        ]

    origin_system = serializers.CharField(source="osdi_origin_system", read_only=True)
    name = serializers.CharField(source="slug", read_only=True)
    #title
    description = serializers.CharField(source="public_description", read_only=True)
    browser_url = serializers.CharField(source="url", read_only=True)
    type = serializers.SerializerMethodField()
    def get_type(self, obj):
        return obj.get_ticket_type_display()
    total_accepted = serializers.IntegerField(source="attendee_count", read_only=True)
    status = serializers.SerializerMethodField()
    def get_status(self, obj):
        return 'confirmed' if (obj.host_is_confirmed and obj.status == 'active') else obj.status
    # e.g. 2017-07-04T19:00:00
    start_date = serializers.DateTimeField(source='starts_at', format='iso-8601')
    #end_date = serializers.DateTimeField(source='ends_at', allow_null=True, format='iso-8601')

    capacity = serializers.IntegerField(source="max_attendees", read_only=True)
    visibility = serializers.SerializerMethodField()
    def get_visibility(self, obj):
        """we are using this strictly as private/public, but is_searchable is different"""
        return obj.get_is_private_display()
    location = serializers.SerializerMethodField()
    def get_location(self, obj):
        return {
            'venue': obj.venue,
            'location': {
                'longitude': obj.longitude,
                'latitude': obj.latitude,
            },
            'postal_code': obj.zip,
            'locality': obj.city,
            'region': obj.state
        }

    human_date = serializers.SerializerMethodField()
    def get_human_date(self, obj):
        """e.g. 'Saturday, November 5' """
        return dateformat.format(obj.starts_at, 'l, F j')
    human_time = serializers.SerializerMethodField()
    def get_human_time(self, obj):
        """e.g. '6:30pm' or '5am' """
        return dateformat.format(obj.starts_at, 'fa').replace('.', '')
