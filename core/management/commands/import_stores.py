"""Create / update store pages from a JSON export (e.g. ZooCorpApp branches).

    python manage.py import_stores stores.json [--dry-run]

File: [{"id": "...", "name": "...", "address": "...", "lat": "41.3", "lng": "69.2",
        "opens": "09:00", "closes": "22:00", "phone": "", "city": "", "district": "", "landmark": ""}, ...]

Stores are matched by `id` (kept in the slug as store-<first 8 chars>). New stores
are created in RU and copied to UZ/EN with the same text — translate them in the CMS.
Existing pages get address / coordinates / hours / phone updated in every language;
titles and texts already edited in the CMS are left alone.
"""
import json
import re
from datetime import time
from decimal import Decimal

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils.text import slugify
from wagtail.models import Locale

from stores.models import StoreIndexPage, StorePage

PREFIX = re.compile(r"^\s*(zoo\s*planeta|zooplaneta|зоопланета)\s*[—–\-:,.]?\s*", re.I)
SYNCED = ("address", "latitude", "longitude", "opens", "closes", "phone")


def parse_time(value, default):
    if not value:
        return default
    h, m = str(value).split(":")[:2]
    return time(int(h) % 24, int(m))


def dec(value):
    return Decimal(str(value)).quantize(Decimal("0.000001")) if value not in (None, "") else None


class Command(BaseCommand):
    help = "Import stores from a JSON file"

    def add_arguments(self, parser):
        parser.add_argument("path")
        parser.add_argument("--dry-run", action="store_true")

    @transaction.atomic
    def handle(self, path, dry_run=False, **opts):
        with open(path, encoding="utf-8") as fh:
            rows = json.load(fh)
        ru = Locale.objects.get(language_code="ru")
        index = StoreIndexPage.objects.filter(locale=ru).first()
        if index is None:
            raise CommandError("Create the «Магазины» page in Russian first (or run seed_demo).")
        others = list(Locale.objects.exclude(pk=ru.pk))
        created = updated = 0
        for row in rows:
            name = PREFIX.sub("", row["name"]).strip() or row["name"]
            key = str(row.get("id") or slugify(name, allow_unicode=False) or name)
            slug = "store-" + re.sub(r"[^a-z0-9]", "", key.lower())[:8]
            values = {
                "address": row.get("address", "").strip(),
                "latitude": dec(row.get("lat")),
                "longitude": dec(row.get("lng")),
                "opens": parse_time(row.get("opens"), time(9)),
                "closes": parse_time(row.get("closes"), time(22)),
                "phone": row.get("phone", "") or "",
            }
            page = StorePage.objects.child_of(index).filter(slug=slug).first()
            if page is None:
                page = StorePage(title=name, slug=slug, locale=ru, district=row.get("district", ""),
                                 city=row.get("city") or "Ташкент",
                                 landmark=row.get("landmark", ""), **values)
                if not dry_run:
                    index.add_child(instance=page)
                    page.save_revision().publish()
                    for loc in others:
                        tr = page.copy_for_translation(loc).specific
                        tr.save_revision().publish()
                created += 1
                self.stdout.write(f"+ {name}")
                continue
            pages = [page] + [p.specific for p in page.get_translations()]
            for p in pages:
                changed = [f for f in SYNCED if getattr(p, f) != values[f]]
                if changed and not dry_run:
                    for f in changed:
                        setattr(p, f, values[f])
                    p.save_revision().publish()
            updated += 1
        if dry_run:
            transaction.set_rollback(True)
        self.stdout.write(self.style.SUCCESS(f"created {created}, checked {updated}" + (" (dry run)" if dry_run else "")))
