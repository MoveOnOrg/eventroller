import json

from rest_framework.viewsets import ModelViewSet

from event_exim.serializers import OsdiEventSerializer
from event_store.models import Event

class PublicEventViewSet(ModelViewSet):
    serializer_class = OsdiEventSerializer
    queryset = Event.objects.filter(is_searchable=True, is_private=False, state='AK')
