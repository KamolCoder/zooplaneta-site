from django.db import models
from wagtail.admin.panels import FieldPanel, MultiFieldPanel
from wagtail.contrib.settings.models import BaseGenericSetting, register_setting

from core.ui import current_lang


@register_setting(icon="site")
class SiteSettings(BaseGenericSetting):
    """Contacts shown in the header, footer and contact page (one set for all languages)."""

    phone = models.CharField("Справочная (телефон)", max_length=32, default="+998 71 200-00-00")
    phone_hours = models.CharField("Часы справочной", max_length=32, default="09:00–21:00", blank=True)
    short_phone = models.CharField("Короткий номер колл-центра", max_length=10, blank=True,
                                   help_text="Напр. 1234 — показывается рядом с основным номером")
    email = models.EmailField("E-mail для покупателей", default="info@zooplaneta.uz")
    partners_email = models.EmailField("E-mail для партнёров", default="partners@zooplaneta.uz")
    hr_phone = models.CharField("Телефон отдела кадров", max_length=32, blank=True, default="+998 71 200-00-01")
    telegram = models.CharField("Telegram (без @)", max_length=64, blank=True, default="zooplaneta_uz")
    instagram = models.CharField("Instagram (без @)", max_length=64, blank=True, default="zooplaneta.uz")
    facebook = models.URLField("Facebook (ссылка)", blank=True)
    youtube = models.URLField("YouTube (ссылка)", blank=True)

    app_store_url = models.URLField("Приложение доставки: App Store", blank=True)
    google_play_url = models.URLField("Приложение доставки: Google Play", blank=True)
    uds_url = models.URLField("UDS: ссылка на компанию", blank=True,
                              help_text="Ссылка-приглашение из кабинета UDS (вступление в программу)")
    uds_code = models.CharField("UDS: промокод", max_length=32, blank=True)

    yandex_verification = models.CharField("Яндекс.Вебмастер: код подтверждения", max_length=64, blank=True,
                                           help_text="Только значение content из meta-тега yandex-verification")
    google_verification = models.CharField("Google Search Console: код подтверждения", max_length=128, blank=True,
                                           help_text="Только значение content из meta-тега google-site-verification")
    yandex_metrika_id = models.CharField("Яндекс.Метрика: номер счётчика", max_length=20, blank=True)
    ga4_id = models.CharField("Google Analytics 4: ID потока", max_length=20, blank=True, help_text="Вида G-XXXXXXXXXX")

    legal_name = models.CharField("Юридическое название", max_length=200, default="ООО «ZOO PLANETA»")
    tax_id = models.CharField("ИНН", max_length=20, blank=True)
    address_ru = models.CharField("Адрес офиса (RU)", max_length=255, blank=True, default="г. Ташкент")
    address_uz = models.CharField("Адрес офиса (UZ)", max_length=255, blank=True, default="Toshkent sh.")
    address_en = models.CharField("Адрес офиса (EN)", max_length=255, blank=True, default="Tashkent, Uzbekistan")
    privacy_page = models.ForeignKey("wagtailcore.Page", null=True, blank=True, on_delete=models.SET_NULL,
                                     related_name="+", verbose_name="Страница политики конфиденциальности",
                                     help_text="Ссылка в подвале и у форм")
    office_lat = models.DecimalField("Офис: широта", max_digits=9, decimal_places=6, null=True, blank=True)
    office_lng = models.DecimalField("Офис: долгота", max_digits=9, decimal_places=6, null=True, blank=True)

    easter_paws = models.BooleanField("Пасхалка «следы лап»", default=True,
                                      help_text="5 кликов по логотипу на главной (или код Konami) — по экрану пробегают следы")
    fun_404 = models.BooleanField("Интерактивная страница 404", default=True,
                                  help_text="Кот, которого можно погладить; выключено — обычная страница «не найдено»")
    SEASON_CHOICES = [("", "Нет"), ("snow", "Снег")]
    season_effect = models.CharField("Сезонное оформление", max_length=16, choices=SEASON_CHOICES, blank=True,
                                     help_text="Показывается вверху каждой страницы в заданные даты")
    season_from = models.DateField("Показывать с", null=True, blank=True, help_text="Пусто — сразу")
    season_to = models.DateField("Показывать по", null=True, blank=True,
                                 help_text="Включительно; пусто — пока не выключат вручную")

    panels = [
        MultiFieldPanel([FieldPanel("phone"), FieldPanel("phone_hours"), FieldPanel("short_phone"), FieldPanel("email"),
                         FieldPanel("partners_email"), FieldPanel("hr_phone")], "Контакты"),
        MultiFieldPanel([FieldPanel("app_store_url"), FieldPanel("google_play_url"), FieldPanel("uds_url"),
                         FieldPanel("uds_code")], "Приложение и бонусы"),
        MultiFieldPanel([FieldPanel("telegram"), FieldPanel("instagram"), FieldPanel("facebook"),
                         FieldPanel("youtube")], "Соцсети"),
        MultiFieldPanel([FieldPanel("yandex_verification"), FieldPanel("google_verification"),
                         FieldPanel("yandex_metrika_id"), FieldPanel("ga4_id")], "Поисковики и аналитика"),
        MultiFieldPanel([FieldPanel("legal_name"), FieldPanel("tax_id"), FieldPanel("address_ru"),
                         FieldPanel("address_uz"), FieldPanel("address_en"), FieldPanel("office_lat"),
                         FieldPanel("office_lng"), FieldPanel("privacy_page")], "Компания"),
        MultiFieldPanel([FieldPanel("easter_paws"), FieldPanel("fun_404"), FieldPanel("season_effect"),
                         FieldPanel("season_from"), FieldPanel("season_to")], "Интерактив и сезонное оформление"),
    ]

    class Meta:
        verbose_name = "Контакты и реквизиты"

    @property
    def phone_href(self) -> str:
        return "".join(c for c in self.phone if c.isdigit() or c == "+")

    @property
    def has_app(self) -> bool:
        return bool(self.app_store_url or self.google_play_url)

    @property
    def hr_phone_href(self) -> str:
        return "".join(c for c in self.hr_phone if c.isdigit() or c == "+")

    def clean(self):
        import re
        from django.core.exceptions import ValidationError
        errors = {}
        if self.yandex_metrika_id and not re.fullmatch(r"\d{5,12}", self.yandex_metrika_id):
            errors["yandex_metrika_id"] = "Только цифры номера счётчика"
        if self.ga4_id and not re.fullmatch(r"G-[A-Z0-9]{4,16}", self.ga4_id):
            errors["ga4_id"] = "Формат G-XXXXXXXXXX"
        for f in ("yandex_verification", "google_verification"):
            if getattr(self, f) and not re.fullmatch(r"[\w\-]+", getattr(self, f)):
                errors[f] = "Вставьте только код из content, без тега"
        if self.season_from and self.season_to and self.season_from > self.season_to:
            errors["season_to"] = "Дата окончания раньше даты начала"
        if errors:
            raise ValidationError(errors)

    @property
    def season_active(self) -> str:
        """The seasonal effect to show today ("" when none): the dates are inclusive, blank means open-ended."""
        if not self.season_effect:
            return ""
        from django.utils import timezone
        today = timezone.localdate()
        if (self.season_from and today < self.season_from) or (self.season_to and today > self.season_to):
            return ""
        return self.season_effect

    @property
    def address(self) -> str:
        return getattr(self, f"address_{current_lang()}") or self.address_ru
