import math
from datetime import time

from django.db import models
from django.utils import timezone
from modelcluster.fields import ParentalKey
from wagtail.admin.panels import FieldPanel, FieldRowPanel, InlinePanel, MultiFieldPanel
from wagtail.fields import RichTextField
from wagtail.models import Orderable, Page
from wagtail.search import index


def is_open_at(opening: time, closing: time, at: time) -> bool:
    if opening == closing:  # 24/7
        return True
    if opening < closing:
        return opening <= at < closing
    return at >= opening or at < closing  # closes after midnight


class StoreIndexPage(Page):
    intro = models.TextField("Вступление", blank=True)

    content_panels = Page.content_panels + [FieldPanel("intro")]
    subpage_types = ["stores.StorePage"]
    parent_page_types = ["pages.HomePage"]
    max_count_per_parent = 1
    template = "stores/store_index_page.html"

    class Meta:
        verbose_name = "Магазины (карта и список)"

    def seo_auto_title(self) -> str:
        from core.ui import t
        return t("seo_stores_title")

    def stores(self):
        return StorePage.objects.child_of(self).live().order_by("title")

    def get_context(self, request, *args, **kwargs):
        ctx = super().get_context(request, *args, **kwargs)
        stores = list(self.stores())
        ctx["stores"] = stores
        ctx["stores_data"] = [s.public_dict() for s in stores]
        ctx["districts"] = sorted({s.district for s in stores if s.district})
        ctx["cities"] = sorted({s.city for s in stores if s.city})
        ctx["query"] = request.GET.get("q", "")[:100]
        return ctx


class StorePage(Page):
    city = models.CharField("Город", max_length=60, default="Ташкент")
    district = models.CharField("Район", max_length=100, blank=True)
    address = models.CharField("Адрес", max_length=255)
    landmark = models.CharField("Ориентир", max_length=255, blank=True)
    metro = models.CharField("Ближайшее метро", max_length=100, blank=True)
    phone = models.CharField("Телефон", max_length=32, blank=True)
    latitude = models.DecimalField("Широта", max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField("Долгота", max_digits=9, decimal_places=6, null=True, blank=True)
    opens = models.TimeField("Открытие", default=time(9, 0))
    closes = models.TimeField("Закрытие", default=time(22, 0),
                              help_text="Если равно открытию — круглосуточно")
    image = models.ForeignKey("wagtailimages.Image", null=True, blank=True, on_delete=models.SET_NULL,
                              related_name="+", verbose_name="Фото магазина")
    features = models.CharField("Что есть в магазине", max_length=255, blank=True,
                                help_text="Через запятую: Ветаптека, Аквариумы, Парковка")
    description = RichTextField("Описание", blank=True, features=["bold", "italic", "link", "ul"])

    search_fields = Page.search_fields + [index.SearchField("address"), index.SearchField("district"),
                                          index.SearchField("landmark")]
    content_panels = Page.content_panels + [
        MultiFieldPanel([FieldRowPanel([FieldPanel("city"), FieldPanel("district")]), FieldPanel("address"), FieldPanel("landmark"),
                         FieldPanel("metro"), FieldPanel("phone")], "Адрес и связь"),
        MultiFieldPanel([FieldRowPanel([FieldPanel("opens"), FieldPanel("closes")])], "Часы работы"),
        MultiFieldPanel([FieldRowPanel([FieldPanel("latitude"), FieldPanel("longitude")])], "Координаты",
                        help_text="В Яндекс/Google Картах: правый клик по точке → скопировать координаты"),
        FieldPanel("image"),
        InlinePanel("photos", label="Фото", heading="Галерея магазина"),
        FieldPanel("features"), FieldPanel("description"),
    ]
    parent_page_types = ["stores.StoreIndexPage"]
    subpage_types = []
    template = "stores/store_page.html"

    class Meta:
        verbose_name = "Магазин"
        verbose_name_plural = "Магазины"

    @property
    def is_24h(self) -> bool:
        return self.opens == self.closes

    @property
    def is_open(self) -> bool:
        return is_open_at(self.opens, self.closes, timezone.localtime().time())

    @property
    def feature_list(self) -> list[str]:
        return [f.strip() for f in self.features.split(",") if f.strip()]

    @property
    def has_coords(self) -> bool:
        return self.latitude is not None and self.longitude is not None

    @property
    def route_url(self) -> str:
        if self.has_coords:
            return f"https://yandex.uz/maps/?rtext=~{self.latitude},{self.longitude}&rtt=auto"
        from urllib.parse import quote
        return f"https://yandex.uz/maps/?text={quote(self.address)}"

    def distance_km(self, other: "StorePage") -> float:
        lat1, lng1, lat2, lng2 = map(math.radians, map(float, (self.latitude, self.longitude,
                                                                other.latitude, other.longitude)))
        h = math.sin((lat2 - lat1) / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin((lng2 - lng1) / 2) ** 2
        return 6371 * 2 * math.asin(math.sqrt(h))

    def nearby(self, limit: int = 3) -> list["StorePage"]:
        siblings = [s for s in StorePage.objects.sibling_of(self, inclusive=False).live() if s.has_coords]
        if not self.has_coords:
            return siblings[:limit]
        return sorted(siblings, key=self.distance_km)[:limit]

    def hours_text(self) -> str:
        from core.ui import t
        return t("open_24") if self.is_24h else f"{t('hours')}: {self.opens:%H:%M}–{self.closes:%H:%M}"

    def seo_auto_title(self) -> str:
        from core.ui import t
        return t("seo_store_title").format(name=self.title)

    def seo_auto_description(self) -> str:
        from core.models import SiteSettings
        from core.ui import t
        return t("seo_store_desc").format(address=self.address, hours=self.hours_text(),
                                          phone=self.phone or SiteSettings.load().phone)

    def structured_data(self) -> dict:
        from core.models import SiteSettings
        from core.seo import absolute
        site = SiteSettings.load()
        data = {
            "@type": "PetStore",
            "@id": self.full_url + "#store",
            "name": f"Zoo Planeta — {self.title}",
            "url": self.full_url,
            "telephone": self.phone or site.phone,
            "address": {"@type": "PostalAddress", "streetAddress": self.address,
                        "addressLocality": self.city or "Tashkent", "addressCountry": "UZ"},
            "openingHoursSpecification": [{
                "@type": "OpeningHoursSpecification",
                "dayOfWeek": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"],
                "opens": "00:00" if self.is_24h else f"{self.opens:%H:%M}",
                "closes": "23:59" if self.is_24h else f"{self.closes:%H:%M}",
            }],
            "parentOrganization": {"@id": absolute("/#organization")},
        }
        images = [img for img in [self.image, *(p.image for p in self.photos.all())] if img]
        if images:
            data["image"] = [absolute(img.get_rendition("fill-1200x800|format-jpeg").url) for img in images[:5]]
        if self.has_coords:
            data["geo"] = {"@type": "GeoCoordinates", "latitude": float(self.latitude),
                           "longitude": float(self.longitude)}
        return data

    def get_context(self, request, *args, **kwargs):
        ctx = super().get_context(request, *args, **kwargs)
        ctx["nearby"] = self.nearby()
        return ctx

    def public_dict(self) -> dict:
        return {
            "id": self.pk,
            "name": self.title,
            "city": self.city,
            "district": self.district,
            "address": self.address,
            "landmark": self.landmark,
            "metro": self.metro,
            "phone": self.phone,
            "lat": float(self.latitude) if self.latitude is not None else None,
            "lng": float(self.longitude) if self.longitude is not None else None,
            "opens": self.opens.strftime("%H:%M"),
            "closes": self.closes.strftime("%H:%M"),
            "url": self.url,
            "route": self.route_url,
        }


class StorePhoto(Orderable):
    page = ParentalKey(StorePage, on_delete=models.CASCADE, related_name="photos")
    image = models.ForeignKey("wagtailimages.Image", on_delete=models.CASCADE, related_name="+",
                              verbose_name="Фото")
    caption = models.CharField("Подпись", max_length=120, blank=True)

    panels = [FieldPanel("image"), FieldPanel("caption")]
