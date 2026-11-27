"""Fill the site with sample photos (free Unsplash License) until the company's own photos arrive.

    python manage.py seed_photos            # download + attach to pages that have no photo yet
    python manage.py seed_photos --force    # also replace photos that are already set
    python manage.py seed_photos --remove   # delete every sample photo (pages fall back to the paw placeholder)

Photos go into the image collection «Демо-фото (Unsplash)», titled «Демо: …», so they are easy to find and
replace in the CMS. Pages are matched by slug (the structure created by seed_demo); missing pages are skipped.
Unsplash License: free for commercial use, attribution not required (https://unsplash.com/license).
"""
import urllib.request
from io import BytesIO

from django.core.files.images import ImageFile
from django.core.management.base import BaseCommand
from django.db import transaction
from wagtail.images import get_image_model
from wagtail.models import Collection, Page

COLLECTION = "Демо-фото (Unsplash)"
URL = "https://images.unsplash.com/photo-{id}?w=2400&q=78&fm=jpg&fit=max"

# key -> (Unsplash photo id, title)
PHOTOS = {
    "hero": ("1583512603805-3cc6b41f3edb", "щенок на жёлтом фоне"),
    "hero_delivery": ("1583337130417-3346a1be7dee", "бульдог на голубом фоне"),
    "hero_uds": ("1537151625747-768eb6cf92b2", "корги на оранжевом фоне"),
    "hero_promo": ("1574158622682-e40e69881006", "кот на синем фоне"),
    "delivery": ("1605568427561-40dd23c2acea", "хаски"),
    "loyalty": ("1548681528-6a5c45b66b42", "кот"),
    "hero_cat": ("1514888286974-6c03e2ca1dba", "кошка"),
    "hero_team": ("1516734212186-a967f81ad0d7", "уход за собакой"),
    "hero_partners": ("1548199973-03cce0bbc87b", "две собаки"),
    "about": ("1601758003122-53c40e686a19", "люди с питомцами дома"),
    "about_head": ("1450778869180-41d0601e046e", "кошка и собака"),
    "cat_dogs": ("1543466835-00a7907e9de1", "бигль"),
    "cat_cats": ("1596854407944-bf87f6fdd49e", "рыжий кот"),
    "cat_birds": ("1552728089-57bdde30beb3", "попугай"),
    "cat_rodents": ("1425082661705-1834bfd09dca", "хомяк"),
    "cat_aquatics": ("1522069169874-c58ec4b76be5", "золотая рыбка"),
    "cat_vet": ("1628009368231-7bb7cfcb0def", "осмотр кошки"),
    "cat_accessories": ("1581888227599-779811939961", "собака на лежанке"),
    "cat_toys": ("1591946614720-90a587da4a36", "собака с игрушкой"),
    "promo_1": ("1574158622682-e40e69881006", "кот"),
    "promo_2": ("1592194996308-7b43878e84a6", "котёнок"),
    "promo_3": ("1589924691995-400dc9ecc119", "миска с кормом"),
    "promo_4": ("1535591273668-578e31182c4f", "рыба-клоун"),
    "promo_5": ("1518717758536-85ae29035b6d", "собака"),
    "promo_6": ("1608096299210-db7e38487075", "собака в свитере"),
    "news_1": ("1544568100-847a948585b9", "собака на прогулке"),
    "news_2": ("1560114928-40f1f1eb26a0", "котёнок в траве"),
    "news_3": ("1534361960057-19889db9621e", "собака бежит"),
    "news_4": ("1606425271394-c3ca9aa1fc06", "лапа"),
    "charity": ("1604848698030-c434ba08ece1", "человек обнимает собаку"),
    "gap_1": ("1576201836106-db1758fd1c97", "щенок"),
    "gap_2": ("1529429617124-95b109e86bb8", "белая собака"),
    "gap_3": ("1604675223954-b1aabd668078", "рыжий кот"),
    "gap_4": ("1601758124510-52d02ddb7cbd", "пара с собакой"),
    "careers": ("1516734212186-a967f81ad0d7", "уход за собакой"),
    "partners": ("1580894908361-967195033215", "офис"),
    "gallery_1": ("1548767797-d8c844163c4c", "морские свинки"),
    "gallery_2": ("1559190394-df5a28aab5c5", "спаниель"),
    "gallery_3": ("1495360010541-f48722b34f7d", "кошка на лестнице"),
    "gallery_4": ("1537151625747-768eb6cf92b2", "корги"),
    "gallery_5": ("1452857297128-d9c29adba80b", "кролик"),
    "store_1": ("1581888227599-779811939961", "собака на лежанке"),
    "store_2": ("1477884213360-7e9d7dcc1e48", "собака"),
    "store_3": ("1520087619250-584c0cbd35e8", "такса в переноске"),
    "store_4": ("1526336024174-e58f5cdd8e13", "кошка с бабочкой"),
    "store_5": ("1561037404-61cd46aa615b", "собака"),
    "store_6": ("1583337130417-3346a1be7dee", "бульдог в худи"),
    "store_7": ("1573865526739-10659fec78a5", "рыжий кот"),
    "store_8": ("1517849845537-4d257902454a", "мопс"),
}
STORE_KEYS = [f"store_{i}" for i in range(1, 9)]


def download(photo_id: str) -> bytes:
    req = urllib.request.Request(URL.format(id=photo_id), headers={"User-Agent": "zooplaneta-site seed_photos"})
    with urllib.request.urlopen(req, timeout=60) as resp:
        return resp.read()


class Command(BaseCommand):
    help = "Attach sample photos (Unsplash) to the demo pages, or remove them"

    def add_arguments(self, parser):
        parser.add_argument("--force", action="store_true", help="Replace photos that are already set")
        parser.add_argument("--remove", action="store_true", help="Delete all sample photos")

    def handle(self, *args, force=False, remove=False, **opts):
        Image = get_image_model()
        if remove:
            coll = Collection.objects.filter(name=COLLECTION).first()
            if not coll:
                self.stdout.write("No sample photos.")
                return
            n = Image.objects.filter(collection=coll).count()
            for img in Image.objects.filter(collection=coll):
                img.delete()
            coll.delete()
            self.stdout.write(self.style.SUCCESS(f"Removed {n} sample photos."))
            return
        self.force = force
        self.images = self.load_images(Image)
        with transaction.atomic():
            changed = self.attach()
        self.stdout.write(self.style.SUCCESS(f"{len(self.images)} photos in «{COLLECTION}», {changed} pages updated."))

    # ── images ───────────────────────────────────────────────────────────────
    def load_images(self, Image) -> dict:
        root = Collection.get_first_root_node()
        coll = Collection.objects.filter(name=COLLECTION).first() or root.add_child(name=COLLECTION)
        by_id = {}
        images = {}
        for key, (photo_id, title) in PHOTOS.items():
            if photo_id not in by_id:
                img = Image.objects.filter(collection=coll, title__endswith=f"[{photo_id}]").first()
                if img is None:
                    data = download(photo_id)
                    img = Image(title=f"Демо: {title} [{photo_id}]", collection=coll,
                                file=ImageFile(BytesIO(data), name=f"demo-{photo_id}.jpg"))
                    img.save()
                    self.stdout.write(f"↓ {title}")
                by_id[photo_id] = img
            images[key] = by_id[photo_id]
        return images

    # ── pages ────────────────────────────────────────────────────────────────
    def pages(self, model_label: str, **filters):
        from django.apps import apps
        return apps.get_model(model_label).objects.filter(**filters)

    def set_field(self, page, field: str, key: str) -> bool:
        if getattr(page, f"{field}_id") and not self.force:
            return False
        setattr(page, field, self.images[key])
        return True

    def publish(self, page):
        page.save_revision().publish()

    def attach(self) -> int:
        changed = 0
        img = self.images

        simple = [
            ("pages.StandardPage", {"slug": "about"}, "image", "about_head"),
            ("pages.CharityIndexPage", {}, "image", "charity"),
            ("pages.DeliveryPage", {}, "image", "delivery"),
            ("pages.LoyaltyPage", {}, "image", "loyalty"),
            ("pages.CareersPage", {}, "image", "careers"),
            ("pages.PartnersPage", {}, "image", "partners"),
        ]
        simple += [("catalog.CategoryPage", {"slug": s}, "image", f"cat_{s}")
                   for s in ("dogs", "cats", "birds", "rodents", "aquatics", "vet", "accessories", "toys")]
        simple += [("pages.PromoPage", {"slug": f"promo-{k}"}, "image", f"promo_{k}") for k in range(1, 7)]
        simple += [("pages.NewsPage", {"slug": f"news-{k}"}, "image", f"news_{k}") for k in range(1, 5)]
        simple += [("pages.CharityPage", {"slug": f"gap-{k}"}, "image", f"gap_{k}") for k in range(1, 5)]
        for label, filters, field, key in simple:
            for page in self.pages(label, **filters):
                if self.set_field(page, field, key):
                    self.publish(page)
                    changed += 1

        # stores: main photo + two gallery photos, rotating through the pool
        from stores.models import StorePage, StorePhoto
        for page in StorePage.objects.all():
            try:
                n = int(page.slug.rsplit("-", 1)[-1]) - 1
            except ValueError:
                n = page.pk
            touched = self.set_field(page, "image", STORE_KEYS[n % len(STORE_KEYS)])
            if not page.photos.exists() or self.force:
                page.photos.all().delete()
                for j in (1, 2):
                    page.photos.add(StorePhoto(image=img[STORE_KEYS[(n + j * 3) % len(STORE_KEYS)]]))
                touched = True
            if touched:
                self.publish(page)
                changed += 1

        # home: slides, about photo
        from pages.models import HomePage
        slide_keys = {"ru": ["hero", "hero_delivery", "hero_uds", "hero_promo"],
                      "uz": ["hero", "hero_delivery", "hero_uds", "hero_promo"],
                      "en": ["hero", "hero_uds"]}
        for home in HomePage.objects.all():
            keys = slide_keys.get(home.locale.language_code, slide_keys["ru"])
            raw = list(home.slides.raw_data)
            touched = False
            for i, block in enumerate(raw):
                if i < len(keys) and (not block["value"].get("image") or self.force):
                    block["value"]["image"] = img[keys[i]].pk
                    touched = True
            if touched:
                home.slides = raw
            touched |= self.set_field(home, "about_image", "about")
            if touched:
                self.publish(home)
                changed += 1

        # about page: photo in the text+image block, gallery after the stats
        for page in self.pages("pages.StandardPage", slug="about"):
            raw = list(page.body.raw_data)
            touched = False
            for block in raw:
                if block["type"] == "text_image" and (not block["value"].get("image") or self.force):
                    block["value"]["image"] = img["about"].pk
                    touched = True
            if not any(b["type"] == "gallery" for b in raw):
                pos = next((i + 1 for i, b in enumerate(raw) if b["type"] == "stats"), len(raw))
                title = {"ru": "Наши магазины и питомцы", "uz": "Doʻkonlarimiz va uy hayvonlari",
                         "en": "Our stores and pets"}.get(page.locale.language_code, "")
                raw.insert(pos, {"type": "gallery", "value": {
                    "title": title, "images": [img[f"gallery_{k}"].pk for k in range(1, 6)]}})
                touched = True
            if touched:
                page.body = raw
                self.publish(page)
                changed += 1
        return changed
