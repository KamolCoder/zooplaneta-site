from django.core.paginator import Paginator
from django.db import models
from django.utils import timezone
from wagtail.admin.panels import FieldPanel, FieldRowPanel, MultiFieldPanel
from wagtail.fields import RichTextField, StreamField
from wagtail.models import Page
from wagtail.search import index

from core.blocks import HeroSlideBlock, body_blocks
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
    slides = StreamField([("slide", HeroSlideBlock())], blank=True, verbose_name="Баннеры на главной",
                         use_json_field=True)
    show_promos = models.BooleanField("Показывать акции", default=True)
    show_store_finder = models.BooleanField("Показывать поиск магазина", default=True)
    body = StreamField(body_blocks(), blank=True, verbose_name="Блоки страницы", use_json_field=True)
    show_news = models.BooleanField("Показывать новости", default=True)

    content_panels = Page.content_panels + [
        FieldPanel("slides"),
        MultiFieldPanel([FieldPanel("show_promos"), FieldPanel("show_store_finder"), FieldPanel("show_news")],
                        "Автоматические блоки"),
        FieldPanel("body"),
    ]
    parent_page_types = ["wagtailcore.Page"]
    max_count_per_parent = 1
    template = "pages/home_page.html"

    class Meta:
        verbose_name = "Главная"

    def get_context(self, request, *args, **kwargs):
        from stores.models import StoreIndexPage, StorePage
        ctx = super().get_context(request, *args, **kwargs)
        today = timezone.localdate()
        ctx["promos"] = (PromoPage.objects.live().filter(locale=self.locale, date_from__lte=today,
                                                         date_to__gte=today).order_by("date_to")[:4])
        ctx["promo_index"] = PromoIndexPage.objects.live().filter(locale=self.locale).first()
        ctx["news"] = NewsPage.objects.live().filter(locale=self.locale).order_by("-date")[:3]
        ctx["news_index"] = NewsIndexPage.objects.live().filter(locale=self.locale).first()
        ctx["store_index"] = StoreIndexPage.objects.live().filter(locale=self.locale).first()
        ctx["store_count"] = StorePage.objects.live().filter(locale=self.locale).count()
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
        paginator = Paginator(NewsPage.objects.child_of(self).live().order_by("-date"), 9)
        ctx["news_page"] = paginator.get_page(request.GET.get("page"))
        return ctx


class NewsPage(ImageMixin, Page):
    date = models.DateField("Дата", default=timezone.localdate)
    summary = models.CharField("Кратко", max_length=255, blank=True)
    body = StreamField(body_blocks(), blank=True, verbose_name="Текст", use_json_field=True)

    search_fields = Page.search_fields + [index.SearchField("summary"), index.SearchField("body")]
    content_panels = Page.content_panels + [FieldPanel("date"), FieldPanel("summary"), FieldPanel("image"),
                                            FieldPanel("body")]
    parent_page_types = ["pages.NewsIndexPage"]
    subpage_types = []
    template = "pages/news_page.html"

    class Meta:
        verbose_name = "Новость"
        verbose_name_plural = "Новости"


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
