from django.urls import path
from wagtail import hooks
from wagtail.admin.viewsets.base import ViewSetGroup
from wagtail.admin.viewsets.model import ModelViewSet

from leads.models import Feedback, JobApplication, PartnerRequest
from leads.views import resume_download

COMMON_FILTERS = ["status", "created_at", "language"]


class JobApplicationViewSet(ModelViewSet):
    model = JobApplication
    icon = "user"
    menu_label = "Отклики на вакансии"
    list_display = ["name", "vacancy_title", "phone", "status", "created_at"]
    list_filter = COMMON_FILTERS
    list_export = ["created_at", "name", "phone", "email", "vacancy_title", "message", "status", "language"]
    search_fields = ["name", "phone", "email", "vacancy_title"]
    form_fields = ["status", "manager_note", "name", "phone", "email", "vacancy_title", "message", "resume"]
    inspect_view_enabled = True


class PartnerRequestViewSet(ModelViewSet):
    model = PartnerRequest
    icon = "group"
    menu_label = "Заявки партнёров"
    list_display = ["company", "kind", "country", "contact_name", "status", "created_at"]
    list_filter = ["kind"] + COMMON_FILTERS
    list_export = ["created_at", "kind", "company", "country", "website", "contact_name", "email", "phone",
                   "category", "message", "status", "language"]
    search_fields = ["company", "contact_name", "email", "country"]
    form_fields = ["status", "manager_note", "kind", "company", "country", "website", "contact_name", "email",
                   "phone", "category", "message"]
    inspect_view_enabled = True


class FeedbackViewSet(ModelViewSet):
    model = Feedback
    icon = "mail"
    menu_label = "Обращения покупателей"
    list_display = ["name", "topic", "store", "phone", "status", "created_at"]
    list_filter = ["topic"] + COMMON_FILTERS
    list_export = ["created_at", "topic", "name", "phone", "email", "store", "message", "status", "language"]
    search_fields = ["name", "phone", "email", "store", "message"]
    form_fields = ["status", "manager_note", "topic", "name", "phone", "email", "store", "message"]
    inspect_view_enabled = True


class LeadsGroup(ViewSetGroup):
    menu_label = "Заявки"
    menu_icon = "tasks"
    menu_order = 150
    items = (JobApplicationViewSet, PartnerRequestViewSet, FeedbackViewSet)


@hooks.register("register_admin_viewset")
def register_leads():
    return LeadsGroup()


@hooks.register("register_admin_urls")
def leads_admin_urls():
    return [path("leads/resume/<path:name>", resume_download, name="leads_resume")]
