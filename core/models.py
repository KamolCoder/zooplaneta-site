from django.db import models
from wagtail.admin.panels import FieldPanel, MultiFieldPanel
from wagtail.contrib.settings.models import BaseGenericSetting, register_setting

from core.ui import current_lang


@register_setting(icon="site")
class SiteSettings(BaseGenericSetting):
    """Contacts shown in the header, footer and contact page (one set for all languages)."""

    phone = models.CharField("Справочная (телефон)", max_length=32, default="+998 71 200-00-00")
    phone_hours = models.CharField("Часы справочной", max_length=32, default="09:00–21:00", blank=True)
    email = models.EmailField("E-mail для покупателей", default="info@zooplaneta.uz")
    partners_email = models.EmailField("E-mail для партнёров", default="partners@zooplaneta.uz")
    hr_phone = models.CharField("Телефон отдела кадров", max_length=32, blank=True, default="+998 71 200-00-01")
    telegram = models.CharField("Telegram (без @)", max_length=64, blank=True, default="zooplaneta_uz")
    instagram = models.CharField("Instagram (без @)", max_length=64, blank=True, default="zooplaneta.uz")
    facebook = models.URLField("Facebook (ссылка)", blank=True)
    youtube = models.URLField("YouTube (ссылка)", blank=True)

    legal_name = models.CharField("Юридическое название", max_length=200, default="ООО «ZOO PLANETA»")
    tax_id = models.CharField("ИНН", max_length=20, blank=True)
    address_ru = models.CharField("Адрес офиса (RU)", max_length=255, blank=True, default="г. Ташкент")
    address_uz = models.CharField("Адрес офиса (UZ)", max_length=255, blank=True, default="Toshkent sh.")
    address_en = models.CharField("Адрес офиса (EN)", max_length=255, blank=True, default="Tashkent, Uzbekistan")
    office_lat = models.DecimalField("Офис: широта", max_digits=9, decimal_places=6, null=True, blank=True)
    office_lng = models.DecimalField("Офис: долгота", max_digits=9, decimal_places=6, null=True, blank=True)

    panels = [
        MultiFieldPanel([FieldPanel("phone"), FieldPanel("phone_hours"), FieldPanel("email"),
                         FieldPanel("partners_email"), FieldPanel("hr_phone")], "Контакты"),
        MultiFieldPanel([FieldPanel("telegram"), FieldPanel("instagram"), FieldPanel("facebook"),
                         FieldPanel("youtube")], "Соцсети"),
        MultiFieldPanel([FieldPanel("legal_name"), FieldPanel("tax_id"), FieldPanel("address_ru"),
                         FieldPanel("address_uz"), FieldPanel("address_en"), FieldPanel("office_lat"),
                         FieldPanel("office_lng")], "Компания"),
    ]

    class Meta:
        verbose_name = "Контакты и реквизиты"

    @property
    def phone_href(self) -> str:
        return "".join(c for c in self.phone if c.isdigit() or c == "+")

    @property
    def hr_phone_href(self) -> str:
        return "".join(c for c in self.hr_phone if c.isdigit() or c == "+")

    @property
    def address(self) -> str:
        return getattr(self, f"address_{current_lang()}") or self.address_ru
