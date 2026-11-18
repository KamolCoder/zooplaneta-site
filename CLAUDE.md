# zooplaneta-site — notes for Claude

Owner: Kamol. Answer in Russian, code and code comments in English. Short, essentials first.
Do not write code until Kamol says «делай».

Company website of the Zoo Planeta pet store chain (Tashkent, 23 stores). Info only — no online shop.
Separate product: nothing here depends on ZooCorpApp (stores can be imported from its export).

## Stack
Django 5.2 + Wagtail 7.4, SQLite (WAL, IMMEDIATE transactions; file in `/app/data` mounted from the host
`/srv/zooplaneta`, nightly `backup_db --with-files`), whitenoise, gunicorn, Docker.
Low-traffic site: keep it small — container 384 MB / 0.5 CPU, gunicorn 2 workers × 2 threads.
No frontend build: hand-written `static/css/site.css`, vanilla JS (`static/js/site.js`, `stores.js`),
self-hosted Onest font and Leaflet (no CDNs).

## Structure
- `config/` settings/urls. Languages ru/uz/en via `i18n_patterns` (`/ru/…`), `WAGTAIL_I18N_ENABLED`,
  translations with `wagtail.contrib.simple_translation`. CMS at `ADMIN_URL` (default `cms/`).
- `core/` — `SiteSettings` (contacts, one set for all languages), StreamField blocks (`blocks.py`),
  UI strings `ui.py` (`{% t "key" %}`; no gettext), template tags `site_tags.py`, `seed_demo`, `import_stores`.
- `pages/` — Home, Standard, Contact, Promo index/page, News index/page, Careers/Vacancy, Partners.
  `FormPageMixin`: POST → `leads.handling.handle_lead_form` (honeypot, 10/hour per IP, notify) → `?sent=1`.
- `stores/` — StoreIndexPage (list + map, JSON in page) and StorePage (JSON-LD PetStore, nearby stores);
  `GET /api/stores/<lang>/`.
- CMS: Wagtail default colours (no recolouring), Zoo Planeta logo via `templates/wagtailadmin/*`, light theme forced
  for everyone (`core/signals.py` + migration, theme choice hidden in `static/css/cms.css`), start page panels in
  `core/dashboard.py` (quick actions, new leads, running promos).
- `leads/` — JobApplication / PartnerRequest / Feedback, Wagtail ModelViewSets («Заявки», CSV export).
  CVs in `PRIVATE_MEDIA_ROOT`, downloaded only via `/cms/leads/resume/<name>` (needs view perm).

## Design
Brand from the logo: yellow `#FDCC27`, black `#111`, white / `#F6F5F1`. Onest. Yellow is a surface colour
(banners, badges, CTA) — never yellow text on white. No gradients/blobs/emoji/eyebrow labels; restrained grid,
14/22 px radii, line icons from `templates/includes/icons.html`, paw placeholder `includes/ph.html` until photos.
Name is «Zoo Planeta» (Latin) in every language.

## Content rules
EN is for foreign partners: home, about, stores, partners, contacts. Promos/news/vacancies are RU+UZ;
untranslated pages are hidden from that language's menu automatically.
Uzbek uses ʻ (U+02BB) and ʼ (U+02BC): oʻ, gʻ, maʼlumot.

## Run / test
```bash
DEBUG=True python manage.py migrate && DEBUG=True python manage.py seed_demo
DEBUG=True python manage.py test core
```
Previews: Playwright screenshots (OSM tiles are blocked in the sandbox — route them to a stub SVG).

## Git
Work branch `claude/keen-ramanujan-3w56l9`; Kamol merges PRs himself. No force push.
