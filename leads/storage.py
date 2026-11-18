"""CVs are personal data: stored outside MEDIA_ROOT and served only through the CMS."""
from django.conf import settings
from django.core.files.storage import FileSystemStorage
from django.urls import reverse


class PrivateStorage(FileSystemStorage):
    def __init__(self, **kwargs):
        super().__init__(location=settings.PRIVATE_MEDIA_ROOT, **kwargs)

    def url(self, name):
        return reverse("leads_resume", args=[name])


def private_storage():
    return PrivateStorage()
