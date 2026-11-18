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
