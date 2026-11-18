from django.http import Http404, JsonResponse
from django.views.decorators.cache import cache_page
from wagtail.models import Locale

from stores.models import StorePage


@cache_page(300)
def stores_json(request, lang):
    """GET /api/stores/<ru|uz|en>/ — public store list (e.g. for the mobile app)."""
    locale = Locale.objects.filter(language_code=lang).first()
    if locale is None:
        raise Http404
    stores = StorePage.objects.live().filter(locale=locale).order_by("title")
    resp = JsonResponse({"count": len(stores), "results": [s.public_dict() for s in stores]},
                        json_dumps_params={"ensure_ascii": False})
    resp["Access-Control-Allow-Origin"] = "*"
    return resp
