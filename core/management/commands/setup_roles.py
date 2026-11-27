"""Create CMS roles (user groups) with access limited to their sections. Safe to rerun.

    python manage.py setup_roles

Run after the page tree exists (seed_demo or real content); rerun after adding a new language
so the role also covers that language's pages. Assign people to roles in CMS → Settings → Users.

Roles:
  Контент-менеджер — every page, images, documents, brands; no settings, no leads
  Маркетинг        — promos, news, Give a Paw, catalogue, brands, images
  Магазины         — store pages (addresses, hours, photos), images
  HR               — careers and vacancies, job applications
  Заявки           — customer feedback and partner requests (view / change status)
"""
from django.contrib.auth.models import Group, Permission
from django.core.management.base import BaseCommand
from django.db import transaction
from wagtail.models import Collection, GroupCollectionPermission, GroupPagePermission, Page

PAGE_PERMS = ("add_page", "change_page", "publish_page", "lock_page", "unlock_page")
IMAGE_PERMS = ("add_image", "change_image", "choose_image")
DOC_PERMS = ("add_document", "change_document", "choose_document")

# role → (page models whose pages (with subpages) are editable, extra "app.codename" permissions, collections)
ROLES = {
    "Контент-менеджер": (["pages.HomePage"],
                         ["catalog.add_brand", "catalog.change_brand", "catalog.delete_brand",
                          "simple_translation.submit_translation"], IMAGE_PERMS + DOC_PERMS),
    "Маркетинг": (["pages.PromoIndexPage", "pages.NewsIndexPage", "pages.CharityIndexPage", "catalog.CategoryIndexPage"],
                  ["catalog.add_brand", "catalog.change_brand", "simple_translation.submit_translation"],
                  IMAGE_PERMS),
    "Магазины": (["stores.StoreIndexPage"], [], IMAGE_PERMS),
    "HR": (["pages.CareersPage"], ["leads.view_jobapplication", "leads.change_jobapplication"], IMAGE_PERMS),
    "Заявки": ([], ["leads.view_feedback", "leads.change_feedback", "leads.view_partnerrequest",
                    "leads.change_partnerrequest"], ()),
}


def perm(code: str) -> Permission:
    app, codename = code.split(".")
    return Permission.objects.get(content_type__app_label=app, codename=codename)


class Command(BaseCommand):
    help = "Create CMS roles with section-limited permissions"

    @transaction.atomic
    def handle(self, *args, **opts):
        from django.apps import apps
        access_admin = perm("wagtailadmin.access_admin")
        page_perms = [perm(f"wagtailcore.{c}") for c in PAGE_PERMS]
        root_collection = Collection.get_first_root_node()
        for name, (models, extra, collection_perms) in ROLES.items():
            group, created = Group.objects.get_or_create(name=name)
            group.permissions.add(access_admin, *[perm(c) for c in extra])
            sections = 0
            for label in models:
                model = apps.get_model(label)
                for page in model.objects.all():  # one per language
                    for p in page_perms:
                        GroupPagePermission.objects.get_or_create(group=group, page=Page.objects.get(pk=page.pk),
                                                                  permission=p)
                    sections += 1
            for code in collection_perms:
                app = "wagtaildocs" if code.endswith("document") else "wagtailimages"
                GroupCollectionPermission.objects.get_or_create(group=group, collection=root_collection,
                                                                permission=perm(f"{app}.{code}"))
            self.stdout.write(f"{'+' if created else '='} {name}: {sections} page sections, "
                              f"{len(extra)} extra permissions")
        self.stdout.write(self.style.SUCCESS("Roles ready. Add users to them in CMS → Settings → Users."))
