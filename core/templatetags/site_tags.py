from django import template
from django.utils import timezone
from wagtail.models import Locale, Page

from core.ui import LANGS, current_lang, t as translate

register = template.Library()

LANG_LABELS = {"ru": "RU", "uz": "UZ", "en": "EN"}
LANG_NAMES = {"ru": "Русский", "uz": "Oʻzbekcha", "en": "English"}
MONTHS = {
    "ru": ["января", "февраля", "марта", "апреля", "мая", "июня", "июля", "августа", "сентября",
           "октября", "ноября", "декабря"],
    "uz": ["yanvar", "fevral", "mart", "aprel", "may", "iyun", "iyul", "avgust", "sentabr", "oktabr",
           "noyabr", "dekabr"],
    "en": ["January", "February", "March", "April", "May", "June", "July", "August", "September",
           "October", "November", "December"],
}


@register.simple_tag
def t(key):
    return translate(key)


@register.simple_tag
def lang():
    return current_lang()


@register.filter
def human_date(value, with_year=True):
    """18 ноября 2026 / 18-noyabr 2026 / 18 November 2026."""
    if not value:
        return ""
    lang = current_lang()
    month = MONTHS[lang][value.month - 1]
    year = f" {value.year}" if with_year else ""
    if lang == "uz":
        return f"{value.day}-{month}{year}"
    return f"{value.day} {month}{year}"


@register.filter
def short_date(value):
    return human_date(value, with_year=value and value.year != timezone.localdate().year)


@register.filter
def link_url(link):
    """URL of a LinkBlock value (page wins over a raw url)."""
    if not link:
        return ""
    page = link.get("page")
    if page:
        return page.localized.url
    return link.get("url") or ""


@register.filter
def tel(value):
    return "".join(c for c in str(value or "") if c.isdigit() or c == "+")


def _active_locale():
    try:
        return Locale.get_active()
    except Locale.DoesNotExist:
        return Locale.get_default()


@register.simple_tag
def home_page():
    from pages.models import HomePage
    return HomePage.objects.live().filter(locale=_active_locale()).first()


@register.simple_tag
def find_page(model_name):
    """First live page of a type in the current language, e.g. {% find_page 'stores.StoreIndexPage' %}."""
    from django.apps import apps
    model = apps.get_model(model_name)
    return model.objects.live().filter(locale=_active_locale()).first()


@register.simple_tag
def menu_items():
    home = home_page()
    if not home:
        return []
    return list(home.get_children().live().in_menu().specific())


@register.simple_tag(takes_context=True)
def language_links(context):
    """[{code, label, name, url, active}] — the same page in other languages, or that language's home."""
    page = context.get("page")
    current = current_lang()
    translations = {}
    if isinstance(page, Page):
        for p in page.get_translations(inclusive=True).live().select_related("locale"):
            translations[p.locale.language_code] = p.url
    from pages.models import HomePage
    homes = {h.locale.language_code: h.url for h in HomePage.objects.live().select_related("locale")}
    links = []
    for code in LANGS:
        url = translations.get(code) or homes.get(code) or f"/{code}/"
        links.append({"code": code, "label": LANG_LABELS[code], "name": LANG_NAMES[code], "url": url,
                      "active": code == current, "exact": code in translations})
    return links


@register.filter
def in_section(page, item):
    """True when page is item or below it (for the active menu link)."""
    return isinstance(page, Page) and page.path.startswith(item.path)


@register.filter
def page_type(page):
    return type(page).__name__


@register.inclusion_tag("includes/seo_head.html", takes_context=True)
def seo_head(context):
    from django.utils.safestring import mark_safe
    from core import seo
    from core.models import SiteSettings
    page = context.get("page")
    page = page if isinstance(page, Page) else None
    lang = current_lang()
    return {
        "page": page,
        "title": seo.meta_title(page),
        "description": seo.meta_description(page),
        "canonical": page.full_url if page else "",
        "alternates": seo.alternates(page) if page else [],
        "og_image": seo.og_image(page) if page else seo.absolute("/static/img/logo.png"),
        "og_locale": seo.OG_LOCALES.get(lang, "ru_RU"),
        "jsonld": mark_safe(seo.structured_data(page)),
        "s": SiteSettings.load(),
        "noindex": bool(page and getattr(page, "is_over", False)),
    }


@register.inclusion_tag("includes/analytics.html")
def analytics():
    from django.conf import settings as dj_settings
    from core.models import SiteSettings
    return {"s": SiteSettings.load(), "enabled": not dj_settings.DEBUG}


@register.simple_tag
def qr(url, scale=4):
    """Inline SVG QR code for a URL (for desktop visitors who need to open a link on their phone)."""
    from django.utils.safestring import mark_safe
    return mark_safe(_qr_svg(str(url), int(scale))) if url else ""


@__import__("functools").lru_cache(maxsize=64)
def _qr_svg(url: str, scale: int) -> str:
    import segno
    return segno.make(url, error="m").svg_inline(scale=scale, dark="#111", border=2, omitsize=False)


THEME_COLORS = {"yellow": "#FDCC27", "dark": "#111111", "light": "#F6F5F1"}


def _luminance(hex_color: str) -> float:
    r, g, b = (int(hex_color[i:i + 2], 16) / 255 for i in (1, 3, 5))
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def edge_color(image) -> str | None:
    """Median colour of the photo's left edge, so the slide background continues the photo. Cached."""
    import re
    from statistics import median
    from django.core.cache import cache
    key = f"edge-color:{image.pk}:{image.file_hash or image.file.name}"
    found = cache.get(key)
    if found:
        return found
    try:
        from PIL import Image as PILImage
        rendition = image.get_rendition("max-200x200")
        with rendition.file.open("rb") as fh:
            img = PILImage.open(fh).convert("RGB")
        w, h = img.size
        px = [img.getpixel((x, y)) for x in range(min(4, w)) for y in range(h)]
        color = "#%02X%02X%02X" % tuple(int(median(c[i] for c in px)) for i in range(3))
    except Exception:  # missing file, odd format: fall back to the theme colour
        return None
    if re.fullmatch(r"#[0-9A-F]{6}", color):
        cache.set(key, color, 60 * 60 * 24 * 30)
    return color


@register.simple_tag
def slide_look(value):
    """{bg, tone} for a hero slide: own colour > photo edge colour > theme colour; tone = text colour."""
    import re
    bg = (value.get("bg_color") or "").strip().upper()
    if not re.fullmatch(r"#[0-9A-F]{6}", bg):
        bg = ""
    if not bg and value.get("kind") == "banner" and value.get("banner"):
        bg = edge_color(value["banner"]) or ""
    if not bg and value.get("auto_bg") and value.get("image") and value.get("image_style") != "object":
        bg = edge_color(value["image"]) or ""
    bg = bg or THEME_COLORS.get(value.get("theme"), THEME_COLORS["yellow"])
    return {"bg": bg, "tone": "dark" if _luminance(bg) < 0.55 else "light"}
