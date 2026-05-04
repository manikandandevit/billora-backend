from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path, re_path
from django.views.static import serve

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/v1/", include("accounts.urls")),
    path("api/v1/orgs/", include("orgs.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
else:
    # django.conf.urls.static.static() returns [] when DEBUG=False — uploads would 404 on Render.
    # Ephemeral disk: files are lost on redeploy unless you attach a disk or use object storage (S3).
    _media_prefix = settings.MEDIA_URL.lstrip("/")
    if _media_prefix:
        urlpatterns += [
            re_path(
                rf"^{_media_prefix}(?P<path>.*)$",
                serve,
                {"document_root": settings.MEDIA_ROOT},
            ),
        ]
