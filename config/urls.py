from django.conf import settings
from django.conf.urls.i18n import i18n_patterns
from django.conf.urls.static import static
from django.urls import include, path
from django.views.generic import TemplateView
from wagtail import urls as wagtail_urls
from wagtail.admin import urls as wagtailadmin_urls
from wagtail.documents import urls as wagtaildocs_urls

from core.sitemap import sitemap
from core.views import apple_touch_icon, favicon, health, robots_txt, webmanifest
from stores.views import stores_json

urlpatterns = [
    path(settings.ADMIN_URL, include(wagtailadmin_urls)),
    path("documents/", include(wagtaildocs_urls)),
    path("sitemap.xml", sitemap),
    path("robots.txt", robots_txt),
    path("favicon.ico", favicon),
    path("apple-touch-icon.png", apple_touch_icon),
    path("site.webmanifest", webmanifest),
    path("health/", health),
    path("api/stores/<str:lang>/", stores_json, name="stores-json"),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

urlpatterns += i18n_patterns(
    path("", include(wagtail_urls)),
    prefix_default_language=True,
)
