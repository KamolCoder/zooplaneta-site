from django.core.paginator import Paginator
from django.db import models
from django.utils import timezone
from wagtail.admin.panels import FieldPanel, FieldRowPanel, MultiFieldPanel
from wagtail.fields import RichTextField, StreamField
from wagtail.images.blocks import ImageChooserBlock
from wagtail.models import Page
from wagtail.search import index

from core.blocks import AdvantageBlock, AggregatorBlock, HeroSlideBlock, StatItem, StepBlock, body_blocks
from leads.forms import FeedbackForm, JobApplicationForm, PartnerRequestForm
from leads.handling import handle_lead_form


class ImageMixin(models.Model):
    """A cover image used on cards, at the top of the page and as og:image."""

    image = models.ForeignKey("wagtailimages.Image", null=True, blank=True, on_delete=models.SET_NULL,
                              related_name="+", verbose_name="Обложка")

    class Meta:
        abstract = True


class FormPageMixin:
    """Pages with a lead form: GET shows it, POST validates, saves and redirects with ?sent=1."""

    form_class = None

    def build_form(self, request, data=None, files=None):
        return self.form_class(data, files)

    def lead_title(self, obj) -> str:
        return obj._meta.verbose_name

    def lead_summary(self, obj) -> list[str]:
        return [f"{f.verbose_name}: {getattr(obj, f.name)}" for f in obj._meta.fields
                if f.name not in ("id", "status", "manager_note", "created_at") and getattr(obj, f.name)]

    def before_lead_save(self, obj):
        pass

    def serve(self, request, *args, **kwargs):
        if request.method == "POST":
            form = self.build_form(request, request.POST, request.FILES)
            result = handle_lead_form(request, self, form, title=self.lead_title(form.instance),
                                      summary=self.lead_summary, before_save=self.before_lead_save)
            if not isinstance(result, type(form)):
                return result
            kwargs["form"] = result
        return super().serve(request, *args, **kwargs)

    def get_context(self, request, *args, **kwargs):
        ctx = super().get_context(request, *args, **kwargs)
        ctx["form"] = kwargs.get("form") or self.build_form(request)
        ctx["sent"] = request.GET.get("sent") == "1"
        return ctx


# ── home ─────────────────────────────────────────────────────────────────────

class HomePage(Page):
    """Sections in a fixed order (see the template); each automatic section can be switched off."""

    slides = StreamField([("slide", HeroSlideBlock())], blank=True, verbose_name="Баннеры на главной",
                         use_json_field=True)
    intro_title = models.CharField("Заголовок", max_length=160, blank=True,
                                   help_text="Коротко о бренде, напр. «Крупнейшая сеть зоомагазинов Ташкента»")
    intro_text = models.TextField("Текст", blank=True)
    stats = StreamField([("stat", StatItem())], blank=True, verbose_name="Цифры", use_json_field=True,
                        help_text="Число магазинов подставляется само, если написать в поле «Число» {stores}")
    show_categories = models.BooleanField("Показывать категории", default=True)
    show_promos = models.BooleanField("Показывать акции", default=True)
    about_title = models.CharField("Заголовок", max_length=160, blank=True)
    about_text = RichTextField("Текст", blank=True, features=["bold", "italic", "link"])
    about_image = models.ForeignKey("wagtailimages.Image", null=True, blank=True, on_delete=models.SET_NULL,
                                    related_name="+", verbose_name="Фото")
    about_page = models.ForeignKey("wagtailcore.Page", null=True, blank=True, on_delete=models.SET_NULL,
                                   related_name="+", verbose_name="Ссылка «Подробнее»")
    advantages = StreamField([("item", AdvantageBlock())], blank=True, verbose_name="Преимущества",
                             use_json_field=True)
    show_store_finder = models.BooleanField("Показывать карту магазинов", default=True)
    show_services = models.BooleanField("Показывать «Доставка и бонусы»", default=True)
    show_news = models.BooleanField("Показывать новости", default=True)
    show_charity = models.BooleanField("Показывать Give a Paw", default=True)
    show_brands = models.BooleanField("Показывать бренды", default=True)
    body = StreamField(body_blocks(), blank=True, verbose_name="Дополнительные блоки (внизу)", use_json_field=True)

    content_panels = Page.content_panels + [
        FieldPanel("slides"),
        MultiFieldPanel([FieldPanel("intro_title"), FieldPanel("intro_text"), FieldPanel("stats")],
                        "О бренде коротко"),
        MultiFieldPanel([FieldPanel("about_title"), FieldPanel("about_text"), FieldPanel("about_image"),
                         FieldPanel("about_page"), FieldPanel("advantages")], "О компании и преимущества"),
        MultiFieldPanel([FieldPanel("show_categories"), FieldPanel("show_promos"), FieldPanel("show_store_finder"),
                         FieldPanel("show_services"), FieldPanel("show_news"), FieldPanel("show_charity"), FieldPanel("show_brands")],
                        "Автоматические блоки"),
        FieldPanel("body"),
    ]
    parent_page_types = ["wagtailcore.Page"]
    max_count_per_parent = 1
    template = "pages/home_page.html"

    class Meta:
        verbose_name = "Главная"

    def get_context(self, request, *args, **kwargs):
        from catalog.models import Brand, CategoryIndexPage
        from stores.models import StoreIndexPage
        ctx = super().get_context(request, *args, **kwargs)
        today = timezone.localdate()
        ctx["promos"] = (PromoPage.objects.live().filter(locale=self.locale, date_from__lte=today,
                                                         date_to__gte=today).order_by("date_to")[:4])
        ctx["promo_index"] = PromoIndexPage.objects.live().filter(locale=self.locale).first()
        ctx["news"] = NewsPage.objects.live().filter(locale=self.locale).order_by("-date")[:3]
        ctx["news_index"] = NewsIndexPage.objects.live().filter(locale=self.locale).first()
        store_index = StoreIndexPage.objects.live().filter(locale=self.locale).first()
        stores = list(store_index.stores()) if store_index else []
        ctx["store_index"] = store_index
        ctx["stores"] = stores
        ctx["store_count"] = len(stores)
        ctx["stores_data"] = [s.public_dict() for s in stores]
        ctx["districts"] = sorted({s.district for s in stores if s.district})
        ctx["stats_list"] = [{"value": b.value["value"].replace("{stores}", str(len(stores))),
                              "label": b.value["label"]} for b in self.stats]
        category_index = CategoryIndexPage.objects.live().filter(locale=self.locale).first()
        ctx["category_index"] = category_index
        ctx["categories"] = category_index.categories() if category_index else []
        charity = CharityIndexPage.objects.live().filter(locale=self.locale).first()
        ctx["charity_index"] = charity
        ctx["charity_items"] = charity.items()[:3] if charity else []
        ctx["brands"] = Brand.objects.filter(is_featured=True).select_related("logo")[:18]
        ctx["delivery_page"] = DeliveryPage.objects.live().filter(locale=self.locale).first()
        ctx["loyalty_page"] = LoyaltyPage.objects.live().filter(locale=self.locale).first()
        return ctx


# ── generic pages ────────────────────────────────────────────────────────────

class StandardPage(ImageMixin, Page):
    """About, history, privacy policy — any page built from blocks."""

    intro = models.TextField("Вступление", blank=True)
    body = StreamField(body_blocks(), blank=True, verbose_name="Содержание", use_json_field=True)

    search_fields = Page.search_fields + [index.SearchField("intro"), index.SearchField("body")]
    content_panels = Page.content_panels + [FieldPanel("intro"), FieldPanel("image"), FieldPanel("body")]
    template = "pages/standard_page.html"

    class Meta:
        verbose_name = "Обычная страница"


class ContactPage(FormPageMixin, Page):
    intro = models.TextField("Вступление", blank=True)
    body = StreamField(body_blocks(), blank=True, verbose_name="Дополнительно", use_json_field=True)
    form_class = FeedbackForm

    content_panels = Page.content_panels + [FieldPanel("intro"), FieldPanel("body")]
    max_count_per_parent = 1
    template = "pages/contact_page.html"

    class Meta:
        verbose_name = "Контакты"

    def build_form(self, request, data=None, files=None):
        from stores.models import StorePage
        stores = StorePage.objects.live().filter(locale=self.locale).order_by("title").values_list("title", flat=True)
        return FeedbackForm(data, files, stores=list(stores))

    def lead_title(self, obj):
        return "Обращение покупателя"


# ── promos ───────────────────────────────────────────────────────────────────

class PromoIndexPage(Page):
    intro = models.TextField("Вступление", blank=True)

    content_panels = Page.content_panels + [FieldPanel("intro")]
    subpage_types = ["pages.PromoPage"]
    max_count_per_parent = 1
    template = "pages/promo_index_page.html"

    class Meta:
        verbose_name = "Акции (список)"

    def get_context(self, request, *args, **kwargs):
        ctx = super().get_context(request, *args, **kwargs)
        today = timezone.localdate()
        promos = PromoPage.objects.child_of(self).live()
        ctx["active"] = promos.filter(date_from__lte=today, date_to__gte=today).order_by("date_to")
        ctx["upcoming"] = promos.filter(date_from__gt=today).order_by("date_from")
        ctx["archive"] = promos.filter(date_to__lt=today).order_by("-date_to")[:8]
        return ctx


class PromoPage(ImageMixin, Page):
    date_from = models.DateField("Начало")
    date_to = models.DateField("Окончание")
    badge = models.CharField("Плашка", max_length=30, blank=True, help_text="Напр. −20% или 1+1")
    summary = models.CharField("Кратко", max_length=255, blank=True)
    old_price = models.CharField("Старая цена", max_length=30, blank=True, help_text="Напр. 145 000 сум")
    new_price = models.CharField("Новая цена", max_length=30, blank=True)
    body = RichTextField("Условия", blank=True, features=["bold", "italic", "link", "ul", "ol"])

    search_fields = Page.search_fields + [index.SearchField("summary"), index.SearchField("body")]
    content_panels = Page.content_panels + [
        FieldRowPanel([FieldPanel("date_from"), FieldPanel("date_to")], heading="Сроки"),
        FieldPanel("image"), FieldPanel("badge"), FieldPanel("summary"),
        FieldRowPanel([FieldPanel("old_price"), FieldPanel("new_price")], heading="Цены (необязательно)"),
        FieldPanel("body"),
    ]
    parent_page_types = ["pages.PromoIndexPage"]
    subpage_types = []
    template = "pages/promo_page.html"

    class Meta:
        verbose_name = "Акция"
        verbose_name_plural = "Акции"

    @property
    def is_active(self) -> bool:
        return self.date_from <= timezone.localdate() <= self.date_to

    def seo_auto_title(self) -> str:
        from core.ui import t
        return t("seo_promo_title").format(name=self.title)

    def seo_auto_description(self) -> str:
        from core.templatetags.site_tags import human_date
        from core.ui import t
        dates = f"{t('valid')} {human_date(self.date_from, False)} — {human_date(self.date_to)}."
        lead = f"{self.badge}: {self.summary}" if self.badge and self.summary else (self.summary or self.badge)
        return " ".join(filter(None, [lead.rstrip(".") + "." if lead else "", dates]))

    @property
    def is_upcoming(self) -> bool:
        return self.date_from > timezone.localdate()

    @property
    def is_over(self) -> bool:
        return self.date_to < timezone.localdate()


# ── news ─────────────────────────────────────────────────────────────────────

class NewsIndexPage(Page):
    intro = models.TextField("Вступление", blank=True)

    content_panels = Page.content_panels + [FieldPanel("intro")]
    subpage_types = ["pages.NewsPage"]
    max_count_per_parent = 1
    template = "pages/news_index_page.html"

    class Meta:
        verbose_name = "Новости (список)"

    def get_context(self, request, *args, **kwargs):
        ctx = super().get_context(request, *args, **kwargs)
        news = NewsPage.objects.child_of(self).live().order_by("-date")
        used = set(news.values_list("kind", flat=True))
        kind = request.GET.get("kind", "")
        if kind in used:
            news = news.filter(kind=kind)
        else:
            kind = ""
        paginator = Paginator(news, 9)
        ctx["news_page"] = paginator.get_page(request.GET.get("page"))
        ctx["kinds"] = [(k, NewsPage(kind=k).kind_label) for k, _ in NewsPage.Kind.choices if k in used]
        ctx["kind"] = kind
        return ctx


class NewsPage(ImageMixin, Page):
    class Kind(models.TextChoices):
        NEWS = "news", "Новость компании"
        OPENING = "opening", "Открытие магазина"
        EVENT = "event", "Мероприятие"
        CARE = "care", "Уход за питомцем"
        VET = "vet", "Совет ветеринара"
        REVIEW = "review", "Обзор товаров"

    date = models.DateField("Дата", default=timezone.localdate)
    kind = models.CharField("Рубрика", max_length=10, choices=Kind.choices, default=Kind.NEWS)
    summary = models.CharField("Кратко", max_length=255, blank=True)
    body = StreamField(body_blocks(), blank=True, verbose_name="Текст", use_json_field=True)

    search_fields = Page.search_fields + [index.SearchField("summary"), index.SearchField("body")]
    content_panels = Page.content_panels + [FieldRowPanel([FieldPanel("date"), FieldPanel("kind")]),
                                            FieldPanel("summary"), FieldPanel("image"), FieldPanel("body")]
    parent_page_types = ["pages.NewsIndexPage"]
    subpage_types = []
    template = "pages/news_page.html"

    class Meta:
        verbose_name = "Новость"
        verbose_name_plural = "Новости"

    @property
    def kind_label(self) -> str:
        from core.ui import t
        return t(f"kind_{self.kind}")


# ── careers ──────────────────────────────────────────────────────────────────

class CareersPage(FormPageMixin, ImageMixin, Page):
    intro = models.TextField("Вступление", blank=True)
    body = StreamField(body_blocks(), blank=True, verbose_name="О работе у нас", use_json_field=True)
    form_class = JobApplicationForm

    content_panels = Page.content_panels + [FieldPanel("intro"), FieldPanel("image"), FieldPanel("body")]
    subpage_types = ["pages.VacancyPage"]
    max_count_per_parent = 1
    template = "pages/careers_page.html"

    class Meta:
        verbose_name = "Карьера"

    def get_context(self, request, *args, **kwargs):
        ctx = super().get_context(request, *args, **kwargs)
        ctx["vacancies"] = VacancyPage.objects.child_of(self).live().filter(is_open=True).order_by("title")
        return ctx

    def lead_title(self, obj):
        return "Резюме без вакансии"


class VacancyPage(FormPageMixin, Page):
    class Employment(models.TextChoices):
        FULL = "full", "Полная занятость"
        SHIFT = "shift", "Сменный график"
        PART = "part", "Частичная занятость"

    is_open = models.BooleanField("Вакансия открыта", default=True)
    employment = models.CharField("Занятость", max_length=10, choices=Employment.choices, default=Employment.FULL)
    schedule = models.CharField("График", max_length=100, blank=True, help_text="Напр. 2/2 по 12 часов")
    location = models.CharField("Где", max_length=150, blank=True, help_text="Напр. Магазины по всему Ташкенту")
    salary = models.CharField("Зарплата", max_length=100, blank=True, help_text="Напр. от 4 000 000 сум")
    summary = models.CharField("Кратко", max_length=255, blank=True)
    duties = RichTextField("Обязанности", blank=True, features=["bold", "ul", "ol", "link"])
    requirements = RichTextField("Требования", blank=True, features=["bold", "ul", "ol", "link"])
    conditions = RichTextField("Условия", blank=True, features=["bold", "ul", "ol", "link"])
    form_class = JobApplicationForm

    content_panels = Page.content_panels + [
        FieldPanel("is_open"),
        MultiFieldPanel([FieldPanel("employment"), FieldPanel("schedule"), FieldPanel("location"),
                         FieldPanel("salary"), FieldPanel("summary")], "Коротко"),
        FieldPanel("duties"), FieldPanel("requirements"), FieldPanel("conditions"),
    ]
    parent_page_types = ["pages.CareersPage"]
    subpage_types = []
    template = "pages/vacancy_page.html"

    class Meta:
        verbose_name = "Вакансия"
        verbose_name_plural = "Вакансии"

    def seo_auto_title(self) -> str:
        from core.ui import t
        return t("seo_vacancy_title").format(name=self.title)

    def seo_auto_description(self) -> str:
        from core.ui import t
        parts = [self.summary or self.location, f"{t('salary')}: {self.salary}" if self.salary else "",
                 f"{t('schedule')}: {self.schedule}" if self.schedule else ""]
        return ". ".join(p for p in parts if p) + "."

    def before_lead_save(self, obj):
        obj.vacancy = self
        obj.vacancy_title = self.title

    def lead_title(self, obj):
        return f"Отклик: {self.title}"


# ── partners ─────────────────────────────────────────────────────────────────

class PartnersPage(FormPageMixin, ImageMixin, Page):
    intro = models.TextField("Вступление", blank=True)
    body = StreamField(body_blocks(), blank=True, verbose_name="Содержание", use_json_field=True)
    form_intro = models.TextField("Текст над формой", blank=True)
    form_class = PartnerRequestForm

    content_panels = Page.content_panels + [FieldPanel("intro"), FieldPanel("image"), FieldPanel("body"),
                                            FieldPanel("form_intro")]
    max_count_per_parent = 1
    template = "pages/partners_page.html"

    class Meta:
        verbose_name = "Партнёрам"

    def lead_title(self, obj):
        return "Заявка партнёра"


# ── Give a Paw (charity) ─────────────────────────────────────────────────────

class CharityIndexPage(ImageMixin, Page):
    """Give a Paw: the social responsibility programme. Children are projects, events and animal stories."""

    intro = models.TextField("Вступление", blank=True)
    body = StreamField(body_blocks(), blank=True, verbose_name="О проекте", use_json_field=True)
    donate_text = models.CharField("Текст кнопки помощи", max_length=60, blank=True,
                                   help_text="Напр. «Помочь приюту». Пусто — кнопки нет")
    donate_url = models.URLField("Ссылка кнопки помощи", blank=True,
                                 help_text="Внешняя платформа пожертвований или Telegram-канал")

    content_panels = Page.content_panels + [
        FieldPanel("intro"), FieldPanel("image"),
        FieldRowPanel([FieldPanel("donate_text"), FieldPanel("donate_url")], heading="Кнопка помощи"),
        FieldPanel("body"),
    ]
    parent_page_types = ["pages.HomePage"]
    subpage_types = ["pages.CharityPage"]
    max_count_per_parent = 1
    template = "pages/charity_index_page.html"

    class Meta:
        verbose_name = "Give a Paw (благотворительность)"

    def items(self):
        return CharityPage.objects.child_of(self).live().order_by("-date")

    def get_context(self, request, *args, **kwargs):
        ctx = super().get_context(request, *args, **kwargs)
        items = list(self.items())
        ctx["projects"] = [p for p in items if p.kind == CharityPage.Kind.PROJECT]
        ctx["stories"] = [p for p in items if p.kind == CharityPage.Kind.STORY]
        ctx["events"] = [p for p in items if p.kind == CharityPage.Kind.EVENT]
        return ctx


class CharityPage(ImageMixin, Page):
    class Kind(models.TextChoices):
        PROJECT = "project", "Проект / инициатива"
        EVENT = "event", "Мероприятие"
        STORY = "story", "История животного"

    class Status(models.TextChoices):
        NONE = "", "—"
        LOOKING = "looking", "Ищет дом"
        HOME = "home", "Нашёл дом"
        TREATMENT = "treatment", "На лечении"

    kind = models.CharField("Тип", max_length=10, choices=Kind.choices, default=Kind.PROJECT)
    date = models.DateField("Дата", default=timezone.localdate)
    summary = models.CharField("Кратко", max_length=255, blank=True)
    animal_status = models.CharField("Статус животного", max_length=10, choices=Status.choices, blank=True,
                                     default="", help_text="Только для историй животных")
    body = StreamField(body_blocks(), blank=True, verbose_name="Текст и фото", use_json_field=True)

    search_fields = Page.search_fields + [index.SearchField("summary"), index.SearchField("body")]
    content_panels = Page.content_panels + [
        FieldRowPanel([FieldPanel("kind"), FieldPanel("date"), FieldPanel("animal_status")]),
        FieldPanel("summary"), FieldPanel("image"), FieldPanel("body"),
    ]
    parent_page_types = ["pages.CharityIndexPage"]
    subpage_types = []
    template = "pages/charity_page.html"

    class Meta:
        verbose_name = "Give a Paw: материал"
        verbose_name_plural = "Give a Paw: материалы"

    @property
    def kind_label(self) -> str:
        from core.ui import t
        return t(f"charity_{self.kind}")

    @property
    def status_label(self) -> str:
        from core.ui import t
        return t(f"animal_{self.animal_status}") if self.animal_status else ""


# ── delivery app + aggregators, UDS loyalty ──────────────────────────────────

class DeliveryPage(ImageMixin, Page):
    """Own delivery app (store links live in SiteSettings) and the aggregators where Zoo Planeta sells."""

    intro = models.TextField("Вступление", blank=True)
    app_title = models.CharField("Заголовок о приложении", max_length=120, blank=True)
    app_text = models.TextField("Текст о приложении", blank=True)
    app_features = StreamField([("item", AdvantageBlock())], blank=True, verbose_name="Возможности приложения",
                               use_json_field=True)
    screenshots = StreamField([("image", ImageChooserBlock(label="Скриншот"))], blank=True,
                              verbose_name="Скриншоты приложения", use_json_field=True)
    steps = StreamField([("step", StepBlock())], blank=True, verbose_name="Как заказать", use_json_field=True)
    conditions = RichTextField("Условия доставки", blank=True, features=["bold", "italic", "link", "ul", "ol"],
                               help_text="Зоны, сроки, минимальная сумма, оплата")
    aggregators = StreamField([("service", AggregatorBlock())], blank=True, verbose_name="Сервисы доставки",
                              use_json_field=True)
    body = StreamField(body_blocks(), blank=True, verbose_name="Дополнительно (напр. вопросы)", use_json_field=True)

    content_panels = Page.content_panels + [
        FieldPanel("intro"), FieldPanel("image"),
        MultiFieldPanel([FieldPanel("app_title"), FieldPanel("app_text"), FieldPanel("app_features"),
                         FieldPanel("screenshots")], "Приложение Zoo Planeta",
                        help_text="Ссылки на App Store и Google Play — в Настройках → Контакты и реквизиты"),
        FieldPanel("steps"), FieldPanel("conditions"), FieldPanel("aggregators"), FieldPanel("body"),
    ]
    parent_page_types = ["pages.HomePage"]
    subpage_types = []
    max_count_per_parent = 1
    template = "pages/delivery_page.html"

    class Meta:
        verbose_name = "Доставка (приложение и сервисы)"


class LoyaltyPage(ImageMixin, Page):
    """UDS loyalty programme. The join link and promo code live in SiteSettings."""

    intro = models.TextField("Вступление", blank=True)
    cashback = models.CharField("Кешбэк", max_length=30, blank=True, help_text="Крупная цифра, напр. «до 5%»")
    cashback_note = models.CharField("Подпись к кешбэку", max_length=120, blank=True,
                                     help_text="Напр. «баллами с каждой покупки»")
    steps = StreamField([("step", StepBlock())], blank=True, verbose_name="Как подключиться", use_json_field=True)
    rules = RichTextField("Правила программы", blank=True, features=["bold", "italic", "link", "ul", "ol"])
    body = StreamField(body_blocks(), blank=True, verbose_name="Дополнительно (напр. вопросы)", use_json_field=True)

    content_panels = Page.content_panels + [
        FieldPanel("intro"), FieldPanel("image"),
        FieldRowPanel([FieldPanel("cashback"), FieldPanel("cashback_note")], heading="Главная цифра"),
        FieldPanel("steps"), FieldPanel("rules"), FieldPanel("body"),
    ]
    parent_page_types = ["pages.HomePage"]
    subpage_types = []
    max_count_per_parent = 1
    template = "pages/loyalty_page.html"

    class Meta:
        verbose_name = "Бонусы UDS"
