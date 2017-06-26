import json

from rest_framework.viewsets import ModelViewSet
from osdi.pagination import OsdiPagination
from event_exim.serializers import OsdiEventSerializer
from event_store.models import Event



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
