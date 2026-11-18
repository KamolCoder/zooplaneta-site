"""Daily backup: a consistent copy of the SQLite file (+ optionally uploaded files).

    python manage.py backup_db               # db only
    python manage.py backup_db --with-files  # db + media/ + private/ (CVs) as .tar.gz

Uses SQLite's online backup API, so it is safe while the site is writing.
Keeps the newest BACKUP_KEEP copies of each kind in BACKUP_DIR. Copy BACKUP_DIR off the
server as well — a backup on the same disk does not survive a dead disk.
"""
import sqlite3
import tarfile
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import connection
from django.utils import timezone


def rotate(folder: Path, pattern: str, keep: int) -> list[Path]:
    files = sorted(folder.glob(pattern))
    old = files[:-keep] if keep > 0 else []
    for f in old:
        f.unlink()
    return old


class Command(BaseCommand):
    help = "Back up the SQLite database (and optionally media/private files)"

    def add_arguments(self, parser):
        parser.add_argument("--with-files", action="store_true", help="Also archive media/ and private/")

    def handle(self, *args, with_files=False, **opts):
        out = Path(settings.BACKUP_DIR)
        out.mkdir(parents=True, exist_ok=True)
        stamp = timezone.localtime().strftime("%Y%m%d-%H%M%S")

        db_file = out / f"db-{stamp}.sqlite3"
        connection.ensure_connection()
        dst = sqlite3.connect(db_file)
        try:
            connection.connection.backup(dst)  # Django's own sqlite3 connection
        finally:
            dst.close()
        check = sqlite3.connect(db_file)
        try:
            ok = check.execute("PRAGMA integrity_check").fetchone()[0]
        finally:
            check.close()
        if ok != "ok":
            db_file.unlink(missing_ok=True)
            raise RuntimeError(f"backup integrity check failed: {ok}")
        self.stdout.write(f"db → {db_file} ({db_file.stat().st_size // 1024} KB)")

        if with_files:
            archive = out / f"files-{stamp}.tar.gz"
            with tarfile.open(archive, "w:gz") as tar:
                for name, path in (("media", settings.MEDIA_ROOT), ("private", settings.PRIVATE_MEDIA_ROOT)):
                    if Path(path).exists():
                        tar.add(path, arcname=name)
            self.stdout.write(f"files → {archive} ({archive.stat().st_size // 1024} KB)")

        removed = rotate(out, "db-*.sqlite3", settings.BACKUP_KEEP) + rotate(out, "files-*.tar.gz", settings.BACKUP_KEEP)
        if removed:
            self.stdout.write(f"removed {len(removed)} old backup(s)")
