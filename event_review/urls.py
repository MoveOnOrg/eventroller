from django.conf.urls import include, url
from . import views

urlpatterns = [
    url(r'^api/messagehost/(?P<organization>[-.\w]+)/(?P<event_id>[-.\w]+)/(?P<host_id>[-.\w]+)?/?$',
        views.send_host_message,
        name='event_review_host_message'),
]
