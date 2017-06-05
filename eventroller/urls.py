from django.conf import settings
from django.conf.urls import include, static, url
from django.contrib import admin

urlpatterns = [
    # Examples:
    # url(r'^$', 'eventroller.views.home', name='home'),
    # url(r'^blog/', include('blog.urls')),

    url(r'^admin/', include(admin.site.urls)),
    url(r'^review/', include('reviewer.urls')),
]

if settings.DEBUG:
    urlpatterns = urlpatterns + static.static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
