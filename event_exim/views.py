import json

from django.conf import settings
from django.http import HttpResponse
from django.shortcuts import render, get_object_or_404
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
        return Event.objects.filter(
            is_searchable=True, is_private=False).exclude(
                organization_status_review__in=('questionable', 'limbo'))
