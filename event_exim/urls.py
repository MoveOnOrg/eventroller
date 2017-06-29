from django.conf import settings
from django.conf.urls import include, url

from event_exim import views

public_patterns = [
    url(r'^events/?$', views.PublicEventViewSet.as_view({'get': 'list'}),
        name='osdi_public_events'),
]
refresh_patterns = [
    url(r'^events/refresh/(?P<eventsource_name>[-.\w]+)/(?P<organization_source_pk>[-.\w]+)/?$',
        views.refresh_event,
        name='refresh_event'),
]

urlpatterns = []
if getattr(settings, 'EVENT_PUBLIC_API', False):
    urlpatterns = urlpatterns + public_patterns
if getattr(settings, 'EVENT_PUBLIC_API_REFRESH', False):
    urlpatterns = urlpatterns + refresh_patterns
