import mimetypes

from django.core.exceptions import PermissionDenied, SuspiciousFileOperation
from django.http import FileResponse, Http404

from leads.storage import PrivateStorage


def resume_download(request, name):
    """CMS-only download of a CV (the admin URL wrapper already requires a logged-in editor)."""
    if not request.user.has_perm("leads.view_jobapplication"):
        raise PermissionDenied
    storage = PrivateStorage()
    try:
        if not storage.exists(name):
            raise Http404
        fh = storage.open(name, "rb")
    except SuspiciousFileOperation:
        raise Http404
    content_type = mimetypes.guess_type(name)[0] or "application/octet-stream"
    return FileResponse(fh, as_attachment=True, filename=name.rsplit("/", 1)[-1], content_type=content_type)
