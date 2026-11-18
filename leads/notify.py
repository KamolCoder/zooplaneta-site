"""Tell the team about a new request: e-mail and/or Telegram, both optional."""
import json
import logging
import urllib.request

from django.conf import settings
from django.core.mail import send_mail

log = logging.getLogger(__name__)


def notify(title: str, lines: list[str]) -> None:
    text = title + "\n\n" + "\n".join(line for line in lines if line)
    if settings.LEADS_NOTIFY_EMAILS:
        try:
            send_mail(f"[zooplaneta.uz] {title}", text, settings.DEFAULT_FROM_EMAIL,
                      settings.LEADS_NOTIFY_EMAILS, fail_silently=False)
        except Exception:  # never lose the request because of mail
            log.exception("lead e-mail failed")
    if settings.TELEGRAM_BOT_TOKEN and settings.TELEGRAM_CHAT_ID:
        try:
            body = json.dumps({"chat_id": settings.TELEGRAM_CHAT_ID, "text": text[:4000]}).encode()
            req = urllib.request.Request(
                f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/sendMessage",
                data=body, headers={"Content-Type": "application/json"})
            urllib.request.urlopen(req, timeout=5).close()
        except Exception:
            log.exception("lead telegram failed")
