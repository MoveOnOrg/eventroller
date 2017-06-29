import importlib
import json
import re

from django.conf import settings
from django.contrib.gis.geos import Point
from django.contrib.gis.measure import Distance
from django.http import HttpResponse
from django.shortcuts import render, get_object_or_404

import odata
from osdi.pagination import OsdiPagination
from rest_framework.viewsets import ModelViewSet

from event_exim.models import EventSource
from event_exim.serializers import OsdiEventSerializer
from event_store.models import Event


def refresh_event(request, eventsource_name, organization_source_pk):
    eventsource = get_object_or_404(EventSource, name=eventsource_name)
    eventsource.update_event(organization_source_pk)
    #http://probablyprogramming.com/2009/03/15/the-tiniest-gif-ever
    return HttpResponse(
        bytes([71,73,70,56,57,97,1,0,1,0,0,255,0,44,0,0,0,0,1,0,1,0,0,2,0,59]),
        content_type='image/gif')


class PublicEventViewSet(ModelViewSet):
    serializer_class = OsdiEventSerializer
    pagination_class = OsdiPagination
    pagination_class.osdi_schema = 'osdi:events'

    def get_queryset(self):
        #self.request.query_params
        # TODO: exclude based on review
        queryset = Event.objects.filter(
            is_searchable=True, is_private=False).exclude(
                organization_status_review__in=('questionable', 'limbo'))
        rGET = self.request.GET
        # supporting geo query described here:
        # https://github.com/ResistanceCalendar/resistance-calendar-api#location
        distance_max = rGET.get('distance_max') # unit is in meters
        if distance_max:
            coords = None
            # e.g. distance_coords=[-98.435508,29.516496]&distance_max=10000
            if rGET.get('distance_coords'):
                coord_re = re.match(r'\[([-\d.]+),([-\d.]+)\]', rGET['distance_coords'])
                if coord_re:
                    coords = Point(coord_re.group(1), coord_re.group(2))
            # e.g. distance_postal_code=94110&distance_max=10000
            elif rGET.get('distance_postal_code') and getattr(settings, 'POSTAL_CODE_GEO_LIBRARY', None):
                # This is mostly assuming POSTAL_CODE_GEO_LIBRARY = 'pyzipcode.ZipCodeDatabase'
                # Anything else implementing it must have the same API
                if not hasattr(self, 'postaldb'):
                    module, obj = settings.POSTAL_CODE_GEO_LIBRARY.rsplit('.', 1)
                    postal_module = importlib.import_module(module)
                    self.postaldb = getattr(postal_module, obj)()
                zipcode = self.postaldb[int(rGET.get('distance_postal_code'))]
                if zipcode:
                    coords = Point(zipcode.longitude, zipcode.latitude)
            if coords:
                queryset = queryset.filter(point__distance_lt=(coords, Distance(m=int(distance_max))))
        _filter = rGET.get('$filter')
        if _filter:
            odata_query = odata.django_filter(_filter, OsdiEventSerializer.odata_field_mapper)
            if odata_query:
                queryset = queryset.filter(odata_query)
        return queryset
