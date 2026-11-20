from django.conf import settings
from django.http import HttpResponse


def health(request):
    return HttpResponse(status=204)


def robots_txt(request):
    lines = [
        "User-agent: *",
        f"Disallow: /{settings.ADMIN_URL}",
        "Disallow: /api/",
        "Disallow: /*?sent=",
        "",
        f"Sitemap: {settings.SITE_URL}/sitemap.xml",
    ]
    return HttpResponse("\n".join(lines) + "\n", content_type="text/plain")


def _icon_response(name, content_type):
    from django.contrib.staticfiles import finders
    from django.http import FileResponse, Http404
    path = finders.find(f"icons/{name}")
    if not path:
        from django.contrib.staticfiles.storage import staticfiles_storage
        try:
            path = staticfiles_storage.path(f"icons/{name}")
        except Exception:
            raise Http404
    resp = FileResponse(open(path, "rb"), content_type=content_type)
    resp["Cache-Control"] = "public, max-age=604800"
    return resp


def favicon(request):
    """/favicon.ico — browsers and Google ask the site root for it."""
    return _icon_response("favicon.ico", "image/x-icon")


def apple_touch_icon(request):
    """/apple-touch-icon.png — iOS asks the site root when no <link> is found."""
    return _icon_response("apple-touch-icon.png", "image/png")


def webmanifest(request):
    import json
    from django.templatetags.static import static
    data = {
        "name": "Zoo Planeta",
        "short_name": "Zoo Planeta",
        "start_url": "/",
        "display": "browser",
        "background_color": "#FFFFFF",
        "theme_color": "#FDCC27",
        "icons": [{"src": static(f"icons/favicon-{px}.png"), "sizes": f"{px}x{px}", "type": "image/png"}
                  for px in (48, 96, 192)],
    }
    resp = HttpResponse(json.dumps(data), content_type="application/manifest+json")
    resp["Cache-Control"] = "public, max-age=86400"
    return resp
