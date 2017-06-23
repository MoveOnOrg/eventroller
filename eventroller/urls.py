from django.conf import settings
from django.conf.urls import include, static, url
from django.contrib import admin

urlpatterns = [
    # Examples:
    # url(r'^$', 'eventroller.views.home', name='home'),
    # url(r'^blog/', include('blog.urls')),

    url(r'^admin/', include(admin.site.urls)),
    url(r'^review/', include('reviewer.urls')),
    url(r'^api/v1/', include('event_exim.urls')),
    url('^event_review/', include('event_review.urls')),
    url('^', include('django.contrib.auth.urls')),
]

if settings.DEBUG:
    urlpatterns = urlpatterns + static.static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
