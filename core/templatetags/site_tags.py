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
