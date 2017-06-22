from django.conf.urls import include, url
from . import views

urlpatterns = [
    url(r'^api/actionkit/hostloginreminder/(?P<event_id>[-.\w]+)/$',
        views.send_actionkit_host_login_reminder,
        name='event_review_actionkit_hostloginreminder'),
]
