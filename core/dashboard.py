"""Start page of the CMS: quick actions, new requests, running promos."""
from django.urls import reverse
from django.utils import timezone
from wagtail.admin.ui.components import Component
from wagtail.models import Locale

from leads.models import Feedback, JobApplication, PartnerRequest, Status


def _ru():
    return Locale.objects.filter(language_code="ru").first()


def _add_url(parent_model, app, model):
    parent = parent_model.objects.filter(locale=_ru()).first()
    return reverse("wagtailadmin_pages:add", args=[app, model, parent.pk]) if parent else None


class QuickActionsPanel(Component):
    name = "quick_actions"
    order = 10
    template_name = "cms/panel_quick_actions.html"

    def get_context_data(self, parent_context):
        from pages.models import CareersPage, NewsIndexPage, PromoIndexPage
        from stores.models import StoreIndexPage
        actions = [
            ("Добавить акцию", "tag", _add_url(PromoIndexPage, "pages", "promopage")),
            ("Добавить вакансию", "user", _add_url(CareersPage, "pages", "vacancypage")),
            ("Добавить новость", "doc-full", _add_url(NewsIndexPage, "pages", "newspage")),
            ("Добавить магазин", "home", _add_url(StoreIndexPage, "stores", "storepage")),
            ("Контакты и реквизиты", "cogs", reverse("wagtailsettings:edit", args=["core", "sitesettings"])),
            ("Загрузить фото", "image", reverse("wagtailimages:add_multiple")),
        ]
        return {"actions": [a for a in actions if a[2]]}


class LeadsPanel(Component):
    name = "leads"
    order = 20
    template_name = "cms/panel_leads.html"

    def get_context_data(self, parent_context):
        user = parent_context["request"].user
        groups, latest = [], []
        for model, label in ((JobApplication, "Отклики на вакансии"), (PartnerRequest, "Заявки партнёров"),
                             (Feedback, "Обращения покупателей")):
            ns = model._meta.model_name
            if not user.has_perm(f"leads.view_{ns}"):
                continue
            new = model.objects.filter(status=Status.NEW)
            groups.append({"label": label, "new": new.count(),
                           "url": reverse(f"{ns}:index") + "?status=new"})
            for obj in new[:5]:
                latest.append({"obj": obj, "kind": label, "url": reverse(f"{ns}:edit", args=[obj.pk])})
        latest.sort(key=lambda r: r["obj"].created_at, reverse=True)
        return {"groups": groups, "latest": latest[:6]}

    def render_html(self, parent_context=None):
        ctx = self.get_context_data(parent_context)
        return "" if not ctx["groups"] else super().render_html(parent_context)


class PromosPanel(Component):
    name = "promos"
    order = 30
    template_name = "cms/panel_promos.html"

    def get_context_data(self, parent_context):
        from pages.models import PromoIndexPage, PromoPage
        today = timezone.localdate()
        promos = PromoPage.objects.filter(locale=_ru())
        rows = []
        for p in promos.live().filter(date_from__lte=today, date_to__gte=today).order_by("date_to")[:8]:
            rows.append({"page": p, "days": (p.date_to - today).days,
                         "url": reverse("wagtailadmin_pages:edit", args=[p.pk])})
        upcoming = promos.live().filter(date_from__gt=today).order_by("date_from")[:4]
        drafts = promos.filter(live=False).count()
        return {"rows": rows, "upcoming": [{"page": p, "url": reverse("wagtailadmin_pages:edit", args=[p.pk])}
                                           for p in upcoming], "drafts": drafts,
                "add_url": _add_url(PromoIndexPage, "pages", "promopage")}
