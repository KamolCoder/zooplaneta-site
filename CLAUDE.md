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
  UI strings `ui.py` (`{% t "key" %}`; no gettext), template tags `site_tags.py`, `seed_demo` (covers every page type,
  block and setting; `--missing` adds absent sections to a live site, `--photos` runs seed_photos), `import_stores`,
  `seed_photos` (sample Unsplash photos in the «Демо-фото (Unsplash)» collection; `--remove` deletes them).
- `pages/` — Home (fixed section order: hero → deals of the week (promo price tags) → quick links → intro+stats →
  categories → about+advantages → stores map → delivery/UDS → news → Give a Paw → brands → extra blocks). Hero slides
  (`HeroSlideBlock`): «Конструктор» = background colour (own HEX > photo edge colour via `{% slide_look %}` > theme),
  photo to the edge or cut-out PNG, headline, up to 3 perks; or «Готовый баннер» = desktop + mobile images. On the home
  page the header lies transparent over the hero (`body.home-hero`, `data-hero-tone`) until the page scrolls; Standard, Contact, Promo index/page, News index/page (rubric `kind`,
  `?kind=` filter, NewsArticle JSON-LD), Careers/Vacancy, Partners, CharityIndex/CharityPage (Give a Paw: project /
  event / animal story, RU+UZ), DeliveryPage (own app + aggregators StreamField) and LoyaltyPage (UDS), RU+UZ.
  App Store / Google Play / UDS link + code / short call-centre number live in SiteSettings; `{% qr url %}` (segno)
  renders inline SVG QR codes; phones get a fixed bottom bar (call · delivery · stores).
- `catalog/` — informational catalogue: CategoryIndexPage/CategoryPage (icon, subcategories, brands) and the `Brand`
  snippet. No products/prices; `code_1c` fields are the hook for a future 1C OData sync.
  `FormPageMixin`: POST → `leads.handling.handle_lead_form` (honeypot, 10/hour per IP, notify) → `?sent=1`.
- `stores/` — StoreIndexPage (list + map, city/district filters, JSON in page) and StorePage (city, manager name +
  photo, photo gallery `StorePhoto`, JSON-LD PetStore, nearby stores); overview maps (`data-overview-map`) are lazy-initialised in `stores.js`;
  `GET /api/stores/<lang>/`.
- CMS: Wagtail default colours (no recolouring), Zoo Planeta logo via `templates/wagtailadmin/*`, light theme forced
  for everyone (`core/signals.py` + migration, theme choice hidden in `static/css/cms.css`), start page panels in
  `core/dashboard.py` (quick actions, new leads, running promos).
- SEO: `core/seo.py` (meta title/description with per-page `seo_auto_title/description`, hreflang + x-default,
  OG, JSON-LD @graph: Organization/WebSite, PetStore, JobPosting, BreadcrumbList), `core/sitemap.py` (all locales
  + xhtml:link), robots in `core/views.py`. Absolute URLs come from `SITE_URL`; `sync_site` (run at container start)
  writes it into Wagtail's Site. Verification codes + Metrika/GA4 in SiteSettings (counters only when DEBUG=False).
- Icons: `static/icons/*` built by `manage.py make_icons` from `static/img/logo.png` (rerun when an SVG/bigger logo
  arrives); `/favicon.ico`, `/apple-touch-icon.png`, `/site.webmanifest` served from the site root (`core/views.py`).
- Deploy: host nginx on the timkon.uz server, `deploy/nginx/zooplaneta.conf` → `/etc/nginx/conf.d/`, included from
  nginx.conf; certbot --nginx adds HTTPS; app on 127.0.0.1:8030.
- `leads/` — JobApplication / PartnerRequest / Feedback, Wagtail ModelViewSets («Заявки», CSV export).
  CVs in `PRIVATE_MEDIA_ROOT`, downloaded only via `/cms/leads/resume/<name>` (needs view perm).

## Design
Brand from the logo: yellow `#FDCC27`, black `#111`, white / `#F6F5F1`. Onest. Yellow is a surface colour
(banners, badges, CTA) — never yellow text on white. No gradients/blobs/emoji/eyebrow labels; restrained grid,
container 1440 px (32/16 px side padding); photos bleed to the screen edge (full-width hero on the slide colour, page-head photo on the right 45%, about photo / stores map / gallery / delivery cards via `--edge`); 14/22 px radii, line icons from `templates/includes/icons.html`, paw placeholder `includes/ph.html` until photos.
Motion: `.reveal` / `.reveal-group` fade-in on scroll (only under `html.js`, off with reduced motion).
Name is «Zoo Planeta» (Latin) in every language.

## Content rules
EN is for foreign partners: home, about, stores, catalogue, partners, contacts. Promos/news/vacancies/Give a Paw/delivery/UDS are RU+UZ;
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
