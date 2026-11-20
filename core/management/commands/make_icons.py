"""Build the favicon set from the logo (re-run when a bigger / vector-exported PNG arrives).

    python manage.py make_icons [--source static/img/logo.png]

Writes static/icons/: favicon.ico (16/32/48), favicon-48/96/192.png, apple-touch-icon.png (180, yellow
background — iOS does not support transparency). Google wants a square favicon whose side is a
multiple of 48 px.
"""
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand
from PIL import Image

BRAND_YELLOW = (253, 204, 39, 255)


class Command(BaseCommand):
    help = "Generate favicons from the logo"

    def add_arguments(self, parser):
        parser.add_argument("--source", default=str(settings.BASE_DIR / "static" / "img" / "logo.png"))

    def handle(self, *args, source, **opts):
        out = settings.BASE_DIR / "static" / "icons"
        out.mkdir(parents=True, exist_ok=True)
        logo = Image.open(source).convert("RGBA")
        side = max(logo.size)
        square = Image.new("RGBA", (side, side), (0, 0, 0, 0))
        square.paste(logo, ((side - logo.width) // 2, (side - logo.height) // 2), logo)

        def sized(px):
            return square.resize((px, px), Image.LANCZOS)

        for px in (48, 96, 192):
            sized(px).save(out / f"favicon-{px}.png", optimize=True)
        sized(48).save(out / "favicon.ico", sizes=[(16, 16), (32, 32), (48, 48)])
        touch = Image.new("RGBA", (180, 180), BRAND_YELLOW)
        inner = sized(164)
        touch.paste(inner, (8, 8), inner)
        touch.convert("RGB").save(out / "apple-touch-icon.png", optimize=True)
        for f in sorted(Path(out).iterdir()):
            self.stdout.write(f"{f.relative_to(settings.BASE_DIR)}  {f.stat().st_size // 1024 or 1} KB")
