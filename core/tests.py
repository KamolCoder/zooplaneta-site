from django.core import mail
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.test import TestCase, TransactionTestCase, override_settings

from leads.models import Feedback, JobApplication, PartnerRequest
from pages.models import HomePage, PromoPage, VacancyPage
from stores.models import StorePage, is_open_at


@override_settings(SECURE_SSL_REDIRECT=False, LEADS_NOTIFY_EMAILS=["team@example.com"],
                   EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
class SiteTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_demo", verbosity=0)

    def setUp(self):
        cache.clear()

    def test_three_languages_have_a_home(self):
        self.assertEqual(set(HomePage.objects.values_list("locale__language_code", flat=True)), {"ru", "uz", "en"})
        for lang in ("ru", "uz", "en"):
            self.assertEqual(self.client.get(f"/{lang}/").status_code, 200)

    def test_root_redirects_to_a_language(self):
        resp = self.client.get("/")
        self.assertEqual(resp.status_code, 302)
        self.assertTrue(resp["Location"].startswith("/ru/"))

    def test_every_page_renders(self):
        from wagtail.models import Page
        for page in Page.objects.live().filter(depth__gte=2).specific():
            with self.subTest(url=page.url):
                self.assertEqual(self.client.get(page.url).status_code, 200)

    def test_english_has_no_promos_and_no_menu_link(self):
        self.assertEqual(self.client.get("/en/promos/").status_code, 404)
        html = self.client.get("/en/").content.decode()
        self.assertNotIn("/en/promos/", html)
        self.assertIn("/en/partners/", html)

    def test_language_switch_points_to_same_page(self):
        html = self.client.get("/ru/stores/store-01/").content.decode()
        self.assertIn('href="/uz/stores/store-01/"', html)
        self.assertIn('href="/en/stores/store-01/"', html)
        # a promo has no EN translation -> EN link goes to the EN home
        html = self.client.get("/ru/promos/promo-1/").content.decode()
        self.assertIn('href="/en/"', html)

    def test_store_page_has_jsonld_and_nearby(self):
        resp = self.client.get("/ru/stores/store-01/")
        self.assertContains(resp, '"@type": "PetStore"')
        self.assertEqual(len(resp.context["nearby"]), 3)

    def test_stores_api(self):
        data = self.client.get("/api/stores/uz/").json()
        self.assertEqual(data["count"], StorePage.objects.filter(locale__language_code="uz").count())
        self.assertIn("lat", data["results"][0])

    def test_promo_split_active_archive(self):
        resp = self.client.get("/ru/promos/")
        active = list(resp.context["active"])
        self.assertTrue(active and all(p.is_active for p in active))
        self.assertTrue(all(p.is_over for p in resp.context["archive"]))
        self.assertTrue(PromoPage.objects.filter(locale__language_code="en").count() == 0)

    def test_open_hours(self):
        from datetime import time
        self.assertTrue(is_open_at(time(9), time(22), time(21, 59)))
        self.assertFalse(is_open_at(time(9), time(22), time(22)))
        self.assertTrue(is_open_at(time(9), time(2), time(1)))
        self.assertTrue(is_open_at(time(0), time(0), time(4)))


@override_settings(SECURE_SSL_REDIRECT=False, LEADS_NOTIFY_EMAILS=["team@example.com"],
                   EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
class LeadFormTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_demo", verbosity=0)

    def setUp(self):
        cache.clear()

    def test_partner_request_saved_and_notified(self):
        resp = self.client.post("/en/partners/", {
            "kind": "brand", "company": "Acme Pet GmbH", "country": "Germany", "contact_name": "Anna",
            "email": "anna@acme.example", "message": "Hello", "consent": "on"})
        self.assertEqual(resp.status_code, 302)
        self.assertIn("sent=1", resp["Location"])
        req = PartnerRequest.objects.get()
        self.assertEqual((req.company, req.language), ("Acme Pet GmbH", "en"))
        self.assertEqual(len(mail.outbox), 1)

    def test_vacancy_application_with_resume(self):
        vacancy = VacancyPage.objects.filter(locale__language_code="ru").first()
        cv = SimpleUploadedFile("cv.pdf", b"%PDF-1.4 test", content_type="application/pdf")
        resp = self.client.post(vacancy.url, {"name": "Алишер", "phone": "+998901234567", "consent": "on",
                                              "resume": cv})
        self.assertEqual(resp.status_code, 302)
        app = JobApplication.objects.get()
        self.assertEqual(app.vacancy_id, vacancy.pk)
        self.assertEqual(app.vacancy_title, vacancy.title)
        self.assertTrue(app.resume.name.endswith(".pdf"))
        self.assertIn("/cms/leads/resume/", app.resume.url)
        self.assertEqual(self.client.get(app.resume.url).status_code, 302)  # anonymous -> CMS login
        app.resume.delete()

    def test_bad_resume_rejected(self):
        vacancy = VacancyPage.objects.filter(locale__language_code="ru").first()
        exe = SimpleUploadedFile("cv.exe", b"MZ", content_type="application/octet-stream")
        resp = self.client.post(vacancy.url, {"name": "X", "phone": "1", "consent": "on", "resume": exe})
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(JobApplication.objects.exists())

    def test_feedback_needs_phone_or_email_and_consent(self):
        resp = self.client.post("/ru/contacts/", {"topic": "feedback", "name": "A", "message": "hi", "consent": "on"})
        self.assertEqual(resp.status_code, 200)
        resp = self.client.post("/ru/contacts/", {"topic": "feedback", "name": "A", "message": "hi",
                                                  "phone": "+998901112233"})
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(Feedback.objects.exists())

    def test_honeypot_pretends_success(self):
        resp = self.client.post("/ru/contacts/", {"topic": "feedback", "name": "Bot", "message": "spam",
                                                  "phone": "1", "consent": "on", "company_url": "http://spam"})
        self.assertEqual(resp.status_code, 302)
        self.assertFalse(Feedback.objects.exists())

    def test_rate_limit(self):
        data = {"topic": "feedback", "name": "A", "message": "hi", "phone": "+998901112233", "consent": "on"}
        for _ in range(10):
            self.assertEqual(self.client.post("/ru/contacts/", data).status_code, 302)
        self.assertEqual(self.client.post("/ru/contacts/", data).status_code, 200)
        self.assertEqual(Feedback.objects.count(), 10)


@override_settings(SECURE_SSL_REDIRECT=False)
class CmsTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_demo", verbosity=0)

    def test_light_theme_forced_and_dashboard_panels(self):
        from django.contrib.auth import get_user_model
        from wagtail.users.models import UserProfile
        user = get_user_model().objects.create_superuser("ed", "ed@example.com", "pass12345")
        profile = UserProfile.get_for_user(user)
        profile.theme = "dark"
        profile.save()
        self.assertEqual(UserProfile.get_for_user(user).theme, "light")
        Feedback.objects.create(name="Мадина", phone="1", message="hi")
        self.client.force_login(user)
        html = self.client.get("/cms/").content.decode()
        self.assertIn("w-theme-light", html)
        for text in ("Быстрые действия", "Новые заявки", "Действующие акции", "Мадина", "Zoo Planeta CMS"):
            self.assertIn(text, html)


class BackupTests(TransactionTestCase):
    def test_backup_and_rotation(self):
        import sqlite3
        import tempfile
        from pathlib import Path
        with tempfile.TemporaryDirectory() as tmp, override_settings(BACKUP_DIR=tmp, BACKUP_KEEP=2,
                                                                     MEDIA_ROOT=Path(tmp) / "m",
                                                                     PRIVATE_MEDIA_ROOT=Path(tmp) / "p"):
            (Path(tmp) / "db-20000101-000000.sqlite3").write_bytes(b"old")
            (Path(tmp) / "db-20000102-000000.sqlite3").write_bytes(b"old")
            Feedback.objects.create(name="X", phone="1", message="m")
            call_command("backup_db", "--with-files", stdout=open("/dev/null", "w"))
            dbs = sorted(Path(tmp).glob("db-*.sqlite3"))
            self.assertEqual(len(dbs), 2)  # oldest removed
            self.assertFalse((Path(tmp) / "db-20000101-000000.sqlite3").exists())
            con = sqlite3.connect(dbs[-1])
            self.assertEqual(con.execute("select count(*) from leads_feedback").fetchone()[0], 1)
            con.close()
            self.assertEqual(len(list(Path(tmp).glob("files-*.tar.gz"))), 1)


@override_settings(SECURE_SSL_REDIRECT=False, SITE_URL="https://zooplaneta.uz", ALLOWED_HOSTS=["zooplaneta.uz", "testserver"])
class SeoTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_demo", verbosity=0)
        call_command("sync_site", stdout=open("/dev/null", "w"))

    def head(self, url):
        import re
        html = self.client.get(url, HTTP_HOST="zooplaneta.uz", secure=True).content.decode()
        return html, re.search(r"<head>(.*?)</head>", html, re.S).group(1)

    def test_canonical_uses_site_url(self):
        _, head = self.head("/ru/stores/store-01/")
        self.assertIn('<link rel="canonical" href="https://zooplaneta.uz/ru/stores/store-01/">', head)
        self.assertIn('hreflang="x-default" href="https://zooplaneta.uz/ru/stores/store-01/"', head)

    def test_sitemap_has_every_language_and_alternates(self):
        xml = self.client.get("/sitemap.xml").content.decode()
        for lang in ("ru", "uz", "en"):
            self.assertIn(f"<loc>https://zooplaneta.uz/{lang}/</loc>", xml)
        self.assertIn('hreflang="x-default"', xml)
        self.assertNotIn("localhost", xml)
        self.assertNotIn("/promo-6/", xml)  # ended promo

    def test_robots_points_to_sitemap(self):
        txt = self.client.get("/robots.txt").content.decode()
        self.assertIn("Sitemap: https://zooplaneta.uz/sitemap.xml", txt)
        self.assertIn("Disallow: /cms/", txt)

    def test_auto_titles_descriptions_and_structured_data(self):
        _, head = self.head("/ru/stores/store-01/")
        self.assertIn("<title>Зоомагазин Zoo Planeta — Чиланзар, 1-й квартал, Ташкент</title>", head)
        self.assertIn('<meta name="description" content="Зоомагазин Zoo Planeta:', head)
        self.assertIn('"@type": "PetStore"', head)
        self.assertIn('"@type": "BreadcrumbList"', head)
        _, head = self.head("/ru/careers/vacancy-1/")
        self.assertIn('"@type": "JobPosting"', head)
        self.assertIn('"minValue": 4000000', head)
        _, head = self.head("/ru/")
        self.assertIn('"@type": "Organization"', head)

    def test_ended_promo_is_noindex(self):
        _, head = self.head("/ru/promos/promo-6/")
        self.assertIn('<meta name="robots" content="noindex, follow">', head)
        _, head = self.head("/ru/promos/promo-1/")
        self.assertNotIn("noindex", head)

    def test_verification_and_analytics(self):
        from core.models import SiteSettings
        s = SiteSettings.load()
        s.yandex_verification, s.google_verification, s.yandex_metrika_id = "abc123", "g-XyZ_1", "12345678"
        s.save()
        html, head = self.head("/ru/")
        self.assertIn('<meta name="yandex-verification" content="abc123">', head)
        self.assertIn('<meta name="google-site-verification" content="g-XyZ_1">', head)
        self.assertTrue('ym(12345678,"init"' in html)  # tests run with DEBUG=False
        with override_settings(DEBUG=True):
            html, _ = self.head("/ru/")
        self.assertFalse("mc.yandex.ru" in html)  # no counters on a dev machine

    def test_bad_metrika_id_rejected(self):
        from django.core.exceptions import ValidationError
        from core.models import SiteSettings
        s = SiteSettings.load()
        s.yandex_metrika_id = "<script>"
        with self.assertRaises(ValidationError):
            s.full_clean()


class IconTests(TestCase):
    def test_root_icons_and_manifest(self):
        resp = self.client.get("/favicon.ico")
        self.assertEqual((resp.status_code, resp["Content-Type"]), (200, "image/x-icon"))
        self.assertEqual(self.client.get("/apple-touch-icon.png").status_code, 200)
        data = self.client.get("/site.webmanifest").json()
        self.assertEqual([i["sizes"] for i in data["icons"]], ["48x48", "96x96", "192x192"])

    def test_icons_in_head(self):
        call_command("seed_demo", verbosity=0)
        html = self.client.get("/ru/").content.decode()
        self.assertIn('<link rel="icon" href="/favicon.ico"', html)
        self.assertIn('rel="apple-touch-icon"', html)


@override_settings(SECURE_SSL_REDIRECT=False, MEDIA_ROOT=__import__("tempfile").mkdtemp(prefix="zp-media-"))
class SectionTests(TestCase):
    """Catalogue, Give a Paw, home sections, news rubrics, store gallery/city, CMS roles."""

    @classmethod
    def setUpTestData(cls):
        call_command("seed_demo", verbosity=0)

    def test_home_shows_every_section_in_order(self):
        html = self.client.get("/ru/").content.decode()
        markers = ["/ru/promos/promo-", "Крупная сеть зоомагазинов", "/ru/catalog/dogs/", "Проверенный ассортимент",
                   "data-overview-map", "/ru/news/news-", "charity-teaser", "Royal Canin"]
        positions = [html.index(m) for m in markers]
        self.assertEqual(positions, sorted(positions))
        self.assertIn(">23<", html)  # {stores} placeholder in stats replaced by the store count

    def test_home_sections_can_be_switched_off(self):
        home = HomePage.objects.get(locale__language_code="ru")
        home.show_categories = home.show_charity = home.show_brands = False
        home.save_revision().publish()
        html = self.client.get("/ru/").content.decode()
        self.assertNotIn("/ru/catalog/dogs/", html)
        self.assertNotIn("charity-teaser", html)

    def test_catalogue(self):
        resp = self.client.get("/ru/catalog/")
        self.assertEqual(len(resp.context["categories"]), 8)
        resp = self.client.get("/ru/catalog/dogs/")
        self.assertContains(resp, "Сухие корма")
        self.assertContains(resp, "Royal Canin")
        self.assertEqual(self.client.get("/uz/catalog/cats/").status_code, 200)

    def test_give_a_paw_groups_and_story_status(self):
        resp = self.client.get("/ru/give-a-paw/")
        self.assertEqual(len(resp.context["stories"]), 2)
        self.assertContains(resp, "Ищет дом")
        self.assertEqual(self.client.get("/en/give-a-paw/").status_code, 404)  # RU + UZ only

    def test_news_kind_filter_and_article_jsonld(self):
        resp = self.client.get("/ru/news/?kind=vet")
        self.assertEqual([p.kind for p in resp.context["news_page"]], ["vet"])
        resp = self.client.get("/ru/news/?kind=bogus")
        self.assertEqual(resp.context["kind"], "")
        self.assertContains(self.client.get("/ru/news/news-1/"), '"@type": "NewsArticle"')

    def test_store_city_and_gallery(self):
        from wagtail.images.tests.utils import get_test_image_file
        from wagtail.images.models import Image
        from stores.models import StorePhoto
        store = StorePage.objects.get(locale__language_code="ru", slug="store-01")
        img = Image.objects.create(title="shop", file=get_test_image_file())
        StorePhoto.objects.create(page=store, image=img, caption="Торговый зал")
        resp = self.client.get(store.url)
        self.assertContains(resp, "Торговый зал")
        self.assertContains(resp, '"addressLocality": "Ташкент"')
        self.assertEqual(self.client.get("/api/stores/ru/").json()["results"][0]["city"], "Ташкент")

    def test_privacy_link_in_footer(self):
        self.assertContains(self.client.get("/uz/"), 'href="/uz/privacy/"')

    def test_setup_roles_limits_sections(self):
        from django.contrib.auth.models import Group
        from wagtail.models import GroupPagePermission
        call_command("setup_roles", stdout=open("/dev/null", "w"))
        call_command("setup_roles", stdout=open("/dev/null", "w"))  # idempotent
        hr = Group.objects.get(name="HR")
        pages = set(GroupPagePermission.objects.filter(group=hr).values_list("page__slug", flat=True))
        self.assertEqual(pages, {"careers"})
        self.assertTrue(hr.permissions.filter(codename="view_jobapplication").exists())
        self.assertEqual(GroupPagePermission.objects.filter(group=hr, permission__codename="publish_page").count(), 2)


@override_settings(SECURE_SSL_REDIRECT=False, MEDIA_ROOT=__import__("tempfile").mkdtemp(prefix="zp-media-"))
class SamplePhotoTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_demo", verbosity=0)

    def test_seed_and_remove_sample_photos(self):
        from io import BytesIO
        from unittest import mock
        from PIL import Image as PILImage
        from catalog.models import CategoryPage

        def fake_download(photo_id):
            buf = BytesIO()
            PILImage.new("RGB", (64, 48), "orange").save(buf, "JPEG")
            return buf.getvalue()

        with mock.patch("core.management.commands.seed_photos.download", side_effect=fake_download):
            call_command("seed_photos", stdout=open("/dev/null", "w"))
        self.assertTrue(all(c.image_id for c in CategoryPage.objects.all()))
        store = StorePage.objects.get(locale__language_code="ru", slug="store-01")
        self.assertTrue(store.image_id)
        self.assertEqual(store.photos.count(), 2)
        home = HomePage.objects.get(locale__language_code="ru")
        self.assertTrue(all(b.value["image"] for b in home.slides))
        self.assertEqual(self.client.get("/ru/").status_code, 200)
        self.assertEqual(self.client.get("/ru/about/").status_code, 200)

        call_command("seed_photos", "--remove", stdout=open("/dev/null", "w"))
        self.assertFalse(CategoryPage.objects.filter(image__isnull=False).exists())
        self.assertEqual(self.client.get("/ru/").status_code, 200)
        self.assertEqual(self.client.get("/ru/about/").status_code, 200)


@override_settings(SECURE_SSL_REDIRECT=False)
class DeliveryLoyaltyTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_demo", verbosity=0)

    def set_links(self):
        from core.models import SiteSettings
        s = SiteSettings.load()
        s.app_store_url = "https://apps.apple.com/app/id1"
        s.google_play_url = "https://play.google.com/store/apps/details?id=uz.zp"
        s.uds_url = "https://zp.uds.app/c/join?ref=x"
        s.uds_code = "ZOOPLANETA"
        s.short_phone = "1234"
        s.save()

    def test_pages_without_links_hide_buttons(self):
        from core.models import SiteSettings
        s = SiteSettings.load()
        s.app_store_url = s.google_play_url = s.uds_url = s.uds_code = ""
        s.save()
        resp = self.client.get("/ru/delivery/")
        self.assertContains(resp, "Express24")
        self.assertNotContains(resp, "app-btn")
        self.assertNotContains(self.client.get("/ru/bonus/"), "data-copy")

    def test_links_buttons_qr_and_short_number(self):
        self.set_links()
        html = self.client.get("/ru/delivery/").content.decode()
        self.assertIn('data-android="https://play.google.com/store/apps/details?id=uz.zp"', html)
        self.assertIn('class="segno"', html)
        html = self.client.get("/ru/bonus/").content.decode()
        self.assertIn('data-copy="ZOOPLANETA"', html)
        self.assertIn("https://zp.uds.app/c/join?ref=x", html)
        home = self.client.get("/ru/").content.decode()
        self.assertIn("service-card-dark", home)
        self.assertIn('class="mobile-bar"', home)
        self.assertIn('href="tel:1234"', home)

    def test_english_has_no_delivery_section(self):
        html = self.client.get("/en/").content.decode()
        self.assertNotIn("service-card", html)
        self.assertEqual(self.client.get("/en/delivery/").status_code, 404)

    def test_organization_contact_point(self):
        self.assertContains(self.client.get("/ru/"), '"contactType": "customer service"')


@override_settings(SECURE_SSL_REDIRECT=False)
class TeamAndSeedTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_demo", verbosity=0)

    def test_leadership_manager_and_staff_stories(self):
        about = self.client.get("/ru/about/").content.decode()
        self.assertIn("Руководство", about)
        self.assertIn("Генеральный директор", about)
        self.assertIn('class="person-quote"', about)
        self.assertContains(self.client.get("/ru/stores/store-01/"), "Управляющий магазином")
        careers = self.client.get("/ru/careers/").content.decode()
        self.assertIn("Люди Zoo Planeta", careers)
        self.assertIn("Не нашли подходящую вакансию", careers)  # vacancies exist → no "no vacancies" text
        self.assertNotIn("Сейчас открытых вакансий нет", careers)

    def test_demo_settings_filled(self):
        from core.models import SiteSettings
        s = SiteSettings.load()
        self.assertTrue(s.has_app and s.uds_url and s.uds_code and s.short_phone and s.privacy_page_id)

    def test_missing_adds_only_absent_sections(self):
        from django.core.management.base import CommandError
        from pages.models import DeliveryPage, LoyaltyPage
        with self.assertRaises(CommandError):
            call_command("seed_demo", verbosity=0)
        for p in [*DeliveryPage.objects.all(), *LoyaltyPage.objects.all()]:
            p.delete()
        stores_before = StorePage.objects.count()
        call_command("seed_demo", "--missing", stdout=open("/dev/null", "w"))
        self.assertEqual(DeliveryPage.objects.count(), 2)  # RU + UZ
        self.assertEqual(LoyaltyPage.objects.count(), 2)
        self.assertEqual(StorePage.objects.count(), stores_before)
        call_command("seed_demo", "--missing", stdout=open("/dev/null", "w"))  # idempotent
        self.assertEqual(DeliveryPage.objects.count(), 2)



class HeroSlideTests(TestCase):
    def test_slide_look_colours_and_tone(self):
        from core.templatetags.site_tags import slide_look
        self.assertEqual(slide_look({"theme": "dark"}), {"bg": "#111111", "tone": "dark"})
        self.assertEqual(slide_look({"theme": "yellow"})["tone"], "light")
        self.assertEqual(slide_look({"bg_color": "#ffffff", "theme": "dark"}), {"bg": "#FFFFFF", "tone": "light"})
        self.assertEqual(slide_look({"bg_color": "red", "theme": "light"})["bg"], "#F6F5F1")  # bad hex ignored

    @override_settings(MEDIA_ROOT=__import__("tempfile").mkdtemp(prefix="zp-media-"))
    def test_edge_colour_from_photo(self):
        from io import BytesIO
        from django.core.files.images import ImageFile
        from PIL import Image as PILImage
        from wagtail.images.models import Image
        from core.templatetags.site_tags import slide_look
        buf = BytesIO()
        pic = PILImage.new("RGB", (200, 100), (20, 90, 200))
        pic.paste((255, 255, 255), (100, 0, 200, 100))  # right half white: only the left edge counts
        pic.save(buf, "PNG")
        img = Image.objects.create(title="blue", file=ImageFile(BytesIO(buf.getvalue()), name="blue.png"))
        look = slide_look({"image": img, "auto_bg": True, "image_style": "photo", "theme": "yellow"})
        self.assertEqual(look, {"bg": "#145AC8", "tone": "dark"})
        # a cut-out object keeps the theme colour
        self.assertEqual(slide_look({"image": img, "auto_bg": True, "image_style": "object", "theme": "yellow"})["bg"],
                         "#FDCC27")


@override_settings(SECURE_SSL_REDIRECT=False)
class HomeHeroRenderTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_demo", verbosity=0)

    def test_hero_perks_tone_and_deals(self):
        html = self.client.get("/ru/").content.decode()
        self.assertIn('class="home-hero"', html)
        self.assertIn('class="perks"', html)
        self.assertIn('data-tone="dark"', html)      # UDS slide on black
        self.assertIn('class="deal"', html)
        self.assertIn("148 000 сум", html)
        self.assertIn('class="slider-next"', html)


@override_settings(SECURE_SSL_REDIRECT=False)
class InteractiveTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_demo", verbosity=0)

    def _settings(self, **fields):
        from core.models import SiteSettings
        s = SiteSettings.load()
        for k, v in fields.items():
            setattr(s, k, v)
        s.save()
        return s

    def test_404_cat_in_every_language(self):
        for lang, title in (("ru", "Кот уронил эту страницу"), ("uz", "Mushuk bu sahifani"), ("en", "The cat knocked")):
            r = self.client.get(f"/{lang}/no-such-page/")
            self.assertEqual(r.status_code, 404)
            html = r.content.decode()
            self.assertIn(title, html)
            self.assertIn("data-nf-scene", html)
            self.assertIn('name="robots" content="noindex"', html)

    def test_404_plain_when_switched_off(self):
        self._settings(fun_404=False)
        html = self.client.get("/ru/no-such-page/").content.decode()
        self.assertNotIn("data-nf-scene", html)
        self.assertIn("Страница не найдена", html)

    def test_paw_button(self):
        from pages.models import CharityIndexPage
        charity = CharityIndexPage.objects.get(locale__language_code="ru")
        ru = self.client.get("/ru/").content.decode()
        self.assertIn("data-paw-fab", ru)
        self.assertIn("Дай лапу", ru)
        self.assertIn(f'href="{charity.url}">Помогите и приютам', ru)   # toast links to Give a Paw
        en = self.client.get("/en/").content.decode()
        self.assertIn("Give a paw", en)
        self.assertNotIn("Help shelters too", en)                        # no Give a Paw in English
        self._settings(easter_paws=False)
        ru = self.client.get("/ru/").content.decode()
        self.assertNotIn("data-paw-fab", ru)
        self.assertNotIn("data-paws", ru)

    def test_season_dates(self):
        import datetime
        from django.core.exceptions import ValidationError
        from django.utils import timezone
        today = timezone.localdate()
        day = datetime.timedelta(days=1)
        self.assertNotIn("season.js", self.client.get("/ru/").content.decode())   # off by default
        cases = [((None, None), True), ((today, today), True), ((today - day, None), True),
                 ((today + day, None), False), ((None, today - day), False)]
        for (start, end), shown in cases:
            s = self._settings(season_effect="snow", season_from=start, season_to=end)
            self.assertEqual(s.season_active, "snow" if shown else "")
            html = self.client.get("/uz/").content.decode()
            self.assertEqual('data-effect="snow"' in html, shown, (start, end))
        s = self._settings(season_from=today, season_to=today - day)
        with self.assertRaises(ValidationError):
            s.clean()
