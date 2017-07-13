from django.utils.html import linebreaks
from django.utils import timezone, dateformat

from drf_hal_json.serializers import HalModelSerializer
from rest_framework import serializers

from event_store.models import Event


class OsdiLocationGeoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Event
        fields = ['longitude','latitude']

    def get_attribute(self, obj):
        return obj

class OsdiLocationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Event
        fields = ['venue', 'country', 'postal_code', 'locality', 'region', 'location']

    postal_code = serializers.CharField(source="zip", required=False)
    locality = serializers.CharField(source="city", required=False)
    region = serializers.CharField(source="state", required=False)
    location = OsdiLocationGeoSerializer(required=False)

    def get_attribute(self, obj):
        return obj

# HalModelSerializer is failing with location (non)'nested' field
class OsdiEventSerializer(serializers.ModelSerializer):
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
            'end_date', #does anyone use this?
            'capacity',
            'visibility',
            'location',
            #non-OSDI
            'human_time', #friendly display
            'human_date', #friendly display
        ]

    origin_system = serializers.CharField(source="osdi_origin_system", required=False)
    name = serializers.CharField(source="slug", required=False)
    #title
    description = serializers.CharField(source="public_description", required=False)
    browser_url = serializers.CharField(source="url", required=False)
    type = serializers.SerializerMethodField(required=False)
    def get_type(self, obj):
        return obj.get_ticket_type_display()
    total_accepted = serializers.IntegerField(source="attendee_count", required=False)
    status = serializers.SerializerMethodField(required=False)
    def get_status(self, obj):
        if obj.host_is_confirmed and obj.status == 'active':
            return 'confirmed'
        elif obj.status == 'cancelled':
            return 'cancelled'
        else:
            return 'tentative'

    # e.g. 2017-07-04T19:00:00
    start_date = serializers.DateTimeField(source='starts_at', format='iso-8601', required=False)
    end_date = serializers.DateTimeField(source='ends_at', allow_null=True, format='iso-8601', required=False)

    capacity = serializers.IntegerField(source="max_attendees", required=False)
    visibility = serializers.SerializerMethodField(required=False)
    def get_visibility(self, obj):
        """we are using this strictly as private/public, but is_searchable is different"""
        return obj.get_is_private_display()
    location = OsdiLocationSerializer(required=False)

    human_date = serializers.SerializerMethodField(read_only=True)
    def get_human_date(self, obj):
        """e.g. 'Saturday, November 5' """
        return dateformat.format(obj.starts_at, 'l, F j')
    human_time = serializers.SerializerMethodField(read_only=True)
    def get_human_time(self, obj):
        """e.g. '6:30pm' or '5am' """
        return dateformat.format(obj.starts_at, 'fa').replace('.', '')

    def to_internal_value(self, data):
        internal = super(OsdiEventSerializer,self).to_internal_value(data)
        # Flatten the location fields into the same internal value
        if 'location' in internal:
            loc = internal.pop('location')
            if loc:
                if 'location' in loc:
                    locloc = loc.pop('location')
                    loc.update(locloc)
                internal.update(loc)
        return internal

    @classmethod
    def odata_field_mapper(cls, fieldtuple):
        """
        Maps a field tuple like ("location", "region")
        to the django filter value (like 'region' for the above)
        """
        target = cls()
        for f in fieldtuple:
            target = target[f]
        if target:
            return target.source
