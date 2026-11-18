"""sitemap.xml with every language: one <url> per page + xhtml:link alternates (hreflang)."""
from django.conf import settings
from django.http import HttpResponse
from django.utils.html import escape
from django.views.decorators.cache import cache_page
from wagtail.models import Page

from pages.models import HomePage


def sitemap_pages():
    homes = HomePage.objects.live()
    pages = Page.objects.none()
    for home in homes:
        pages |= Page.objects.descendant_of(home, inclusive=True)
    return (pages.live().public().filter(depth__gte=2).select_related("locale")
            .order_by("translation_key", "locale__language_code").specific())


def _priority(page) -> str:
    if page.depth == 2:
        return "1.0"
    return "0.8" if page.depth == 3 else "0.6"


@cache_page(60 * 30)
def sitemap(request):
    pages = list(sitemap_pages())
    # ended promos are noindex — keep them out
    pages = [p for p in pages if not getattr(p, "is_over", False)]
    groups: dict = {}
    for p in pages:
        groups.setdefault(p.translation_key, []).append(p)
    lines = ['<?xml version="1.0" encoding="UTF-8"?>',
             '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" xmlns:xhtml="http://www.w3.org/1999/xhtml">']
    for p in pages:
        siblings = groups[p.translation_key]
        lines.append("<url>")
        lines.append(f"<loc>{escape(p.full_url)}</loc>")
        if p.last_published_at:
            lines.append(f"<lastmod>{p.last_published_at.date().isoformat()}</lastmod>")
        lines.append(f"<priority>{_priority(p)}</priority>")
        if len(siblings) > 1:
            for s in siblings:
                lines.append(f'<xhtml:link rel="alternate" hreflang="{s.locale.language_code}" href="{escape(s.full_url)}"/>')
            default = next((s for s in siblings if s.locale.language_code == settings.LANGUAGE_CODE), None)
            if default:
                lines.append(f'<xhtml:link rel="alternate" hreflang="x-default" href="{escape(default.full_url)}"/>')
        lines.append("</url>")
    lines.append("</urlset>")
    return HttpResponse("\n".join(lines), content_type="application/xml; charset=utf-8")
