from django.templatetags.static import static
from django.utils.html import format_html
from wagtail import hooks

from core.dashboard import LeadsPanel, PromosPanel, QuickActionsPanel


@hooks.register("insert_global_admin_css")
def admin_css():
    return format_html('<link rel="stylesheet" href="{}">', static("css/cms.css"))


@hooks.register("construct_homepage_panels")
def dashboard_panels(request, panels):
    # keep Wagtail's own panels (pages to moderate, locked pages, recent edits) below ours
    panels[:0] = [QuickActionsPanel(), LeadsPanel(), PromosPanel()]
