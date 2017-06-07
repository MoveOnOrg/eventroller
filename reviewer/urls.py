from django.conf.urls import include, url
from reviewer import views

urlpatterns = [
    url(r'^current/(?P<organization>[-.\w]+)/?$', views.current_review_state,
        name='reviewer_current'),
    url(r'^history/(?P<organization>[-.\w]+)/?$', views.get_review_history,
        name='reviewer_history'),
    url(r'^focus/(?P<organization>[-.\w]+)/(?P<content_type>\w+)/(?P<pk>\w+)/?$', views.mark_focus,
        name='reviewer_visit'),
    url(r'^(?P<organization>[-.\w]+)/(?P<content_type>\w+)/(?P<pk>\w+)/?$', views.save_review,
        name='reviewer_save'),
]
