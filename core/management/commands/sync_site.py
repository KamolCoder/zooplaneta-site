"""Point Wagtail's default Site at SITE_URL (e.g. https://zooplaneta.uz) — canonical URLs and the sitemap use it.

Runs on every container start (see Dockerfile), so changing SITE_URL in .env is enough.
"""
from urllib.parse import urlsplit

from django.conf import settings
from django.core.management.base import BaseCommand
from wagtail.models import Site


class Command(BaseCommand):
    help = "Set the default Wagtail site's hostname/port from SITE_URL"

    def handle(self, *args, **opts):
        url = urlsplit(settings.SITE_URL)
        port = url.port or (443 if url.scheme == "https" else 80)
        site = Site.objects.filter(is_default_site=True).first()
        if site is None:
            self.stdout.write("no default site yet — skipped")
            return
        if (site.hostname, site.port) != (url.hostname, port):
            site.hostname, site.port, site.site_name = url.hostname, port, "Zoo Planeta"
            site.save()
            Site.clear_site_root_paths_cache()
        self.stdout.write(f"site: {site.root_url}")
