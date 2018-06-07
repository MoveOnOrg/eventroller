from django.conf import settings
from django.conf.urls import include, url

from event_exim import views

# public API endpoint for developers to fetch data from
public_patterns = [
    url(r'^events/?$', views.PublicEventViewSet.as_view({'get': 'list'}),
        name='osdi_public_events'),
]

# 'pixel' for CRMs to include in webpages; returns no actual data
refresh_patterns = [
    url(r'^events/refresh/(?P<eventsource_name>[-.\w]+)/(?P<organization_source_pk>[-.\w]+)/?$',
        views.refresh_event,
        name='refresh_event'),
]

# sometimes we want a public API, other times we want a pixel
# this lets us conditionally register URLs
urlpatterns = []
if getattr(settings, 'EVENT_PUBLIC_API', False):
    urlpatterns = urlpatterns + public_patterns
if getattr(settings, 'EVENT_PUBLIC_API_REFRESH', False):
    urlpatterns = urlpatterns + refresh_patterns
