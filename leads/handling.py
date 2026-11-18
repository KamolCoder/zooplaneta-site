"""POST handling shared by the pages that carry a form."""
from django.contrib import messages
from django.core.cache import cache
from django.http import HttpResponseRedirect

from core.ui import current_lang, t
from leads.notify import notify

MAX_PER_HOUR = 10


def _client_ip(request) -> str:
    return (request.META.get("HTTP_X_REAL_IP")
            or request.META.get("HTTP_X_FORWARDED_FOR", "").split(",")[0].strip()
            or request.META.get("REMOTE_ADDR", ""))


def handle_lead_form(request, page, form, *, title: str, summary, before_save=None):
    """Validate + save + notify. Returns a redirect on success, or the bound form with errors."""
    if not form.is_valid():
        return form
    if form.is_spam():  # pretend success for bots
        return HttpResponseRedirect(f"{page.url}?sent=1#form")
    key = f"leads:{_client_ip(request)}"
    count = cache.get(key, 0)
    if count >= MAX_PER_HOUR:
        form.add_error(None, t("f_too_many"))
        return form
    cache.set(key, count + 1, 3600)

    obj = form.save(commit=False)
    obj.language = current_lang()
    obj.page_url = request.build_absolute_uri(page.url)[:500]
    if before_save:
        before_save(obj)
    obj.save()
    notify(title, summary(obj))
    return HttpResponseRedirect(f"{page.url}?sent=1#form")
