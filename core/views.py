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
