from django.conf import settings
from django.conf.urls import include, url

from event_exim.views import PublicEventViewSet

public_patterns = [
    url(r'^events/$', PublicEventViewSet.as_view({'get': 'list'}),
        name='osdi_public_events'),
]

urlpatterns = []
if getattr(settings, 'EVENT_PUBLIC_API', False):
    urlpatterns = urlpatterns + public_patterns
