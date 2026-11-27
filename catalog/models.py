"""Informational catalogue: product categories and brands (no prices, no cart).

Integration point for 1C: `code_1c` on Brand and CategoryPage holds the 1C group/brand code, so a
future sync command (OData) can attach products, prices and stock to these records without
reworking the pages.
"""
from django import forms
from django.db import models
from modelcluster.fields import ParentalManyToManyField
from wagtail.admin.panels import FieldPanel, MultiFieldPanel
from wagtail.fields import StreamField
from wagtail.models import Page
from wagtail.search import index

from core.blocks import body_blocks


class Brand(index.Indexed, models.Model):
    name = models.CharField("Название", max_length=100, unique=True)
    logo = models.ForeignKey("wagtailimages.Image", null=True, blank=True, on_delete=models.SET_NULL,
                             related_name="+", verbose_name="Логотип")
    website = models.URLField("Сайт бренда", blank=True)
    country = models.CharField("Страна", max_length=60, blank=True)
    is_featured = models.BooleanField("Показывать на главной", default=True)
    sort_order = models.PositiveIntegerField("Порядок", default=100, help_text="Меньше — выше")
    code_1c = models.CharField("Код в 1С", max_length=64, blank=True, db_index=True)

    panels = [FieldPanel("name"), FieldPanel("logo"), FieldPanel("website"), FieldPanel("country"),
              FieldPanel("is_featured"), FieldPanel("sort_order"), FieldPanel("code_1c")]
    search_fields = [index.SearchField("name"), index.AutocompleteField("name")]

    class Meta:
        verbose_name = "Бренд"
        verbose_name_plural = "Бренды"
        ordering = ["sort_order", "name"]

    def __str__(self):
        return self.name


ICONS = [("dog", "Собака"), ("cat", "Кошка"), ("bird", "Птица"), ("rodent", "Грызун"), ("fish", "Рыбка"),
         ("vet", "Ветаптека"), ("toy", "Игрушка"), ("bowl", "Миска / аксессуары"), ("paw", "Лапка")]


class CategoryIndexPage(Page):
    intro = models.TextField("Вступление", blank=True)
    note = models.CharField("Примечание под списком", max_length=255, blank=True,
                            help_text="Напр. «Наличие товара уточняйте в магазине»")

    content_panels = Page.content_panels + [FieldPanel("intro"), FieldPanel("note")]
    parent_page_types = ["pages.HomePage"]
    subpage_types = ["catalog.CategoryPage"]
    max_count_per_parent = 1
    template = "catalog/category_index_page.html"

    class Meta:
        verbose_name = "Каталог (категории)"

    def categories(self):
        return CategoryPage.objects.child_of(self).live().specific()

    def get_context(self, request, *args, **kwargs):
        ctx = super().get_context(request, *args, **kwargs)
        ctx["categories"] = self.categories()
        return ctx


class CategoryPage(Page):
    icon = models.CharField("Иконка", max_length=20, choices=ICONS, default="paw")
    image = models.ForeignKey("wagtailimages.Image", null=True, blank=True, on_delete=models.SET_NULL,
                              related_name="+", verbose_name="Фото")
    summary = models.CharField("Кратко", max_length=255, blank=True, help_text="Что входит: корма, лакомства…")
    subcategories = models.CharField("Подкатегории", max_length=500, blank=True,
                                     help_text="Через запятую: Сухие корма, Влажные корма, Лакомства")
    body = StreamField(body_blocks(), blank=True, verbose_name="Содержание", use_json_field=True)
    brands = ParentalManyToManyField(Brand, blank=True, verbose_name="Бренды", related_name="categories")
    code_1c = models.CharField("Код группы в 1С", max_length=64, blank=True, db_index=True)

    search_fields = Page.search_fields + [index.SearchField("summary"), index.SearchField("subcategories")]
    content_panels = Page.content_panels + [
        FieldPanel("icon"), FieldPanel("image"), FieldPanel("summary"), FieldPanel("subcategories"),
        FieldPanel("brands", widget=forms.CheckboxSelectMultiple), FieldPanel("body"),
        MultiFieldPanel([FieldPanel("code_1c")], "Интеграция", classname="collapsed"),
    ]
    parent_page_types = ["catalog.CategoryIndexPage"]
    subpage_types = []
    template = "catalog/category_page.html"

    class Meta:
        verbose_name = "Категория"
        verbose_name_plural = "Категории"

    @property
    def subcategory_list(self) -> list[str]:
        return [s.strip() for s in self.subcategories.split(",") if s.strip()]

    def seo_auto_title(self) -> str:
        from core.ui import t
        return t("seo_category_title").format(name=self.title)

    def seo_auto_description(self) -> str:
        from core.ui import t
        return t("seo_category_desc").format(name=self.title, items=self.summary or ", ".join(self.subcategory_list))

    def get_context(self, request, *args, **kwargs):
        ctx = super().get_context(request, *args, **kwargs)
        ctx["siblings"] = CategoryPage.objects.sibling_of(self, inclusive=False).live()
        return ctx
