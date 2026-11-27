"""Everything search engines read in <head>: titles, descriptions, hreflang, Open Graph, JSON-LD.

Editors can always override title / description in the page's «Продвижение» tab; when they leave them
empty the values below are generated from the page content.
"""
import json
import re

from django.conf import settings
from django.templatetags.static import static
from django.utils.html import strip_tags
from django.utils.text import Truncator

from core.ui import current_lang, t

BRAND = "Zoo Planeta"
OG_LOCALES = {"ru": "ru_RU", "uz": "uz_UZ", "en": "en_US"}


def site_url() -> str:
    return settings.SITE_URL.rstrip("/")


def absolute(url: str) -> str:
    return url if url.startswith("http") else site_url() + url


def clean(text: str, limit: int = 160) -> str:
    text = re.sub(r"\s+", " ", strip_tags(text or "")).strip()
    return Truncator(text).chars(limit)


def meta_title(page) -> str:
    if page is None:
        return BRAND
    if page.seo_title:
        return page.seo_title
    auto = getattr(page, "seo_auto_title", None)
    if callable(auto) and (value := auto()):
        return value
    return BRAND if page.depth == 2 else f"{page.title} — {BRAND}"


def meta_description(page) -> str:
    if page is None:
        return ""
    if page.search_description:
        return clean(page.search_description)
    auto = getattr(page, "seo_auto_description", None)
    if callable(auto) and (value := auto()):
        return clean(value)
    for field in ("intro", "summary"):
        if getattr(page, field, ""):
            return clean(getattr(page, field))
    return ""


def og_image(page) -> str:
    image = getattr(page, "image", None)
    if image:
        return absolute(image.get_rendition("fill-1200x630|format-jpeg").url)
    return absolute(static("img/logo.png"))


def alternates(page) -> list[dict]:
    """hreflang links: every live translation + x-default (the Russian version)."""
    pages = list(page.get_translations(inclusive=True).live().select_related("locale"))
    links = [{"lang": p.locale.language_code, "url": p.full_url} for p in pages]
    default = next((p for p in pages if p.locale.language_code == settings.LANGUAGE_CODE), None)
    if default:
        links.append({"lang": "x-default", "url": default.full_url})
    return links


# ── JSON-LD ──────────────────────────────────────────────────────────────────

def _organization(full: bool = False) -> dict:
    from core.models import SiteSettings
    s = SiteSettings.load()
    org = {"@type": "Organization", "@id": site_url() + "/#organization", "name": BRAND,
           "url": site_url() + "/", "logo": absolute(static("img/logo.png"))}
    if full:
        org.update({"legalName": s.legal_name, "telephone": s.phone, "email": s.email,
                    "address": {"@type": "PostalAddress", "streetAddress": s.address_en or s.address_ru,
                                "addressLocality": "Tashkent", "addressCountry": "UZ"}})
        same_as = [u for u in (f"https://t.me/{s.telegram}" if s.telegram else "",
                               f"https://instagram.com/{s.instagram}" if s.instagram else "",
                               s.facebook, s.youtube) if u]
        if same_as:
            org["sameAs"] = same_as
    return org


def _breadcrumbs(page) -> dict | None:
    chain = [p.specific for p in page.get_ancestors(inclusive=True) if p.depth >= 2]
    if len(chain) < 2:
        return None
    return {"@type": "BreadcrumbList", "itemListElement": [
        {"@type": "ListItem", "position": i, "name": BRAND if p.depth == 2 else p.title, "item": p.full_url}
        for i, p in enumerate(chain, start=1)]}


def _salary(text: str) -> dict | None:
    digits = re.findall(r"\d[\d\s]*", text or "")
    if not digits:
        return None
    value = int(re.sub(r"\s", "", digits[0]))
    if value < 1000:
        return None
    return {"@type": "MonetaryAmount", "currency": "UZS",
            "value": {"@type": "QuantitativeValue", "minValue": value, "unitText": "MONTH"}}


def _job_posting(page) -> dict:
    employment = {"full": "FULL_TIME", "shift": "FULL_TIME", "part": "PART_TIME"}
    description = " ".join(filter(None, [page.summary, str(page.duties), str(page.requirements),
                                         str(page.conditions)]))
    data = {
        "@type": "JobPosting",
        "title": page.title,
        "description": description or page.title,
        "datePosted": (page.first_published_at or page.latest_revision_created_at).date().isoformat()
        if (page.first_published_at or page.latest_revision_created_at) else None,
        "employmentType": employment.get(page.employment, "FULL_TIME"),
        "hiringOrganization": {"@type": "Organization", "name": BRAND, "sameAs": site_url() + "/",
                               "logo": absolute(static("img/logo.png"))},
        "jobLocation": {"@type": "Place", "address": {"@type": "PostalAddress", "addressLocality": "Tashkent",
                                                      "addressRegion": "Tashkent", "addressCountry": "UZ"}},
        "directApply": True,
    }
    if salary := _salary(page.salary):
        data["baseSalary"] = salary
    return {k: v for k, v in data.items() if v}


def _article(page) -> dict:
    data = {
        "@type": "NewsArticle" if page.kind in ("news", "opening", "event") else "Article",
        "headline": page.title[:110],
        "description": page.summary or None,
        "datePublished": page.date.isoformat(),
        "dateModified": (page.last_published_at.date().isoformat() if page.last_published_at else None),
        "inLanguage": current_lang(),
        "mainEntityOfPage": page.full_url,
        "image": og_image(page),
        "author": {"@id": site_url() + "/#organization"},
        "publisher": {"@id": site_url() + "/#organization"},
    }
    return {k: v for k, v in data.items() if v}


def structured_data(page) -> str:
    """One <script type="application/ld+json"> payload (@graph) for the page, or ''."""
    from pages.models import CharityPage, HomePage, NewsPage, VacancyPage
    from stores.models import StorePage
    if page is None:
        return ""
    graph = []
    if isinstance(page, HomePage):
        graph.append(_organization(full=True))
        graph.append({"@type": "WebSite", "@id": site_url() + "/#website", "url": page.full_url, "name": BRAND,
                      "inLanguage": current_lang(), "publisher": {"@id": site_url() + "/#organization"}})
    elif isinstance(page, StorePage):
        graph.append(page.structured_data())
    elif isinstance(page, VacancyPage) and page.is_open:
        graph.append(_job_posting(page))
    elif isinstance(page, (NewsPage, CharityPage)):
        graph.append(_article(page))
        graph.append(_organization())
    if crumbs := _breadcrumbs(page):
        graph.append(crumbs)
    if not graph:
        return ""
    raw = json.dumps({"@context": "https://schema.org", "@graph": graph}, ensure_ascii=False)
    # never let content close the <script> tag
    return raw.replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")
