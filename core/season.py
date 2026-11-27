"""Seasonal decoration calendar: which effect (if any) the site shows on a given day.

The periods are edited in the CMS (SiteSettings → «Сезонное оформление»): effect + start/end date, optionally
repeated every year (then the year in the dates is ignored and a period may cross New Year, e.g. 01.12–28.02).
When several periods cover a day, a holiday wins over a season of the year; among equals the first in the list wins.
"""
import datetime

SEASONS = ("winter", "spring", "summer", "autumn")
HOLIDAYS = ("newyear", "navruz", "hayit")
EFFECT_CHOICES = [
    ("winter", "Зима — снег"), ("spring", "Весна — лепестки урюка"), ("summer", "Лето — пух одуванчика"),
    ("autumn", "Осень — листья"), ("newyear", "Новый год — снег, гирлянда, колпак на логотипе"),
    ("navruz", "Навруз — лепестки, орнамент, тюльпаны"), ("hayit", "Хайит — звёзды и полумесяц"),
]

# Defaults for a new site. Yearly periods use the leap year 2000 (only day and month matter, 29.02 allowed).
# Hayit follows the lunar calendar: one-off periods, to be updated every year from the official announcement.
DEFAULT_PERIODS = [
    ("newyear", (2000, 12, 20), (2000, 1, 10), True),
    ("navruz", (2000, 3, 14), (2000, 3, 24), True),
    ("hayit", (2027, 3, 9), (2027, 3, 12), False),     # Ramazon hayit 2027 (expected ~10.03)
    ("hayit", (2027, 5, 16), (2027, 5, 19), False),    # Qurbon hayit 2027 (expected ~17.05)
    ("winter", (2000, 12, 1), (2000, 2, 29), True),
    ("spring", (2000, 3, 1), (2000, 5, 31), True),
    ("summer", (2000, 6, 1), (2000, 8, 31), True),
    ("autumn", (2000, 9, 1), (2000, 11, 30), True),
]


def add_default_periods(settings, period_model) -> None:
    """Fill an empty period list with DEFAULT_PERIODS (also used by the data migration with historical models)."""
    if period_model.objects.filter(setting=settings).exists():
        return
    for order, (effect, start, end, yearly) in enumerate(DEFAULT_PERIODS):
        period_model.objects.create(setting=settings, sort_order=order, effect=effect, yearly=yearly,
                                    date_from=datetime.date(*start), date_to=datetime.date(*end))


def covers(period, day: datetime.date) -> bool:
    """Whether a period is on that day; both dates inclusive."""
    if not period.yearly:
        return period.date_from <= day <= period.date_to
    md, start, end = (day.month, day.day), (period.date_from.month, period.date_from.day), \
        (period.date_to.month, period.date_to.day)
    return start <= md <= end if start <= end else md >= start or md <= end   # crosses New Year


def effect_on(periods, day: datetime.date) -> str:
    """The effect to show on this day ("" when no period covers it)."""
    on = [p.effect for p in periods if covers(p, day)]
    for effect in on:
        if effect in HOLIDAYS:
            return effect
    return on[0] if on else ""
