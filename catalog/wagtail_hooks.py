from wagtail.snippets.models import register_snippet
from wagtail.snippets.views.snippets import SnippetViewSet

from catalog.models import Brand


class BrandViewSet(SnippetViewSet):
    model = Brand
    icon = "pick"
    menu_label = "Бренды"
    menu_order = 140
    add_to_admin_menu = True
    list_display = ["name", "country", "is_featured", "sort_order"]
    list_filter = ["is_featured"]
    search_fields = ["name"]


register_snippet(BrandViewSet)
