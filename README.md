# Zoo Planeta — сайт компании

Ознакомительный сайт сети зоомагазинов Zoo Planeta (Ташкент): RU / UZ / EN, без интернет-магазина.
Django 5.2 + Wagtail 7.4 (CMS), SQLite, собственный CSS без сборки. Шрифт Onest и Leaflet лежат в репозитории (внешних CDN нет).

## Разделы

| Раздел | Тип страницы | Языки в демо |
|---|---|---|
| Главная: баннеры, акции, поиск магазина, блоки, новости | `HomePage` | RU UZ EN |
| О компании, политика конфиденциальности | `StandardPage` (блоки) | RU UZ EN |
| Магазины: список + карта, фильтры, «рядом со мной»; страница каждого магазина | `StoreIndexPage` / `StorePage` | RU UZ EN |
| Акции: активные, будущие, архив | `PromoIndexPage` / `PromoPage` | RU UZ |
| Новости | `NewsIndexPage` / `NewsPage` | RU UZ |
| Карьера: вакансии + отклик с резюме | `CareersPage` / `VacancyPage` | RU UZ |
| Партнёрам: направления + форма заявки | `PartnersPage` | RU UZ EN |
| Контакты + обратная связь | `ContactPage` | RU UZ EN |

Страницы без перевода просто отсутствуют в языке: их нет в меню, а переключатель языка ведёт на главную этого языка.

## Локальный запуск

```bash
pip install -r requirements.txt
DEBUG=True python manage.py migrate
DEBUG=True python manage.py createsuperuser
DEBUG=True python manage.py seed_demo
DEBUG=True python manage.py runserver
```

Сайт: http://localhost:8000/ru/ · CMS: http://localhost:8000/cms/

База — SQLite (`db.sqlite3` рядом с `manage.py`, путь меняется через `SQLITE_PATH`).

## Работа в CMS

- **Страницы**: дерево по языкам. Перевод — меню страницы → «Перевести» (копия появится в другом языке, правите текст и публикуете).
- **Настройки → Контакты и реквизиты**: телефон, e-mail, соцсети, юр. название, адрес офиса — одни на все языки.
- **Заявки**: отклики на вакансии, заявки партнёров, обращения покупателей. Статусы, заметки, выгрузка в CSV/Excel. Резюме скачиваются только из CMS.
- **Изображения**: размеры подбираются автоматически (WebP). Пока фото нет, на сайте показывается фирменная заглушка.
- Акция показывается сама в даты «Начало–Окончание», потом уходит в архив.
- **Главная**: блоки идут в фиксированном порядке (баннеры → о бренде и цифры → категории → акции → о компании и
  преимущества → карта магазинов → новости → Give a Paw → бренды). Тексты и цифры правятся на странице «Главная»;
  `{stores}` в поле «Число» заменяется на количество магазинов. Автоматические блоки отключаются галочками.
- **Каталог**: страницы-категории (иконка, фото, подкатегории, бренды). Товаров и цен нет — только информация.
  Поле «Код в 1С» у категорий и брендов — задел под будущую синхронизацию номенклатуры через OData.
- **Бренды** (пункт меню CMS): логотипы для главной и страниц категорий.
- **Give a Paw**: раздел благотворительности; материалы трёх типов — проект, мероприятие, история животного
  (со статусом «Ищет дом / Нашёл дом / На лечении»). Кнопка помощи ведёт на внешнюю платформу, если задана.
- **Новости**: рубрика (открытие, событие, уход, совет ветеринара, обзор) — на сайте фильтр по рубрикам.
- **Магазины**: город, район, галерея фото. Фильтр по городу появляется, когда городов больше одного.
- Блоки страниц: кроме текста/карточек/цифр есть «Фотогалерея», «Команда», «Карта магазинов (автоматически)».

### Примерные фото

```bash
python manage.py seed_photos            # скачать примерные фото (Unsplash) и расставить по страницам без фото
python manage.py seed_photos --remove   # удалить все примерные фото
```

Фото лежат в CMS → Изображения, коллекция «Демо-фото (Unsplash)», названия начинаются с «Демо:». Свои фото можно
просто выбрать вместо демо на нужной странице; когда всё заменено — `seed_photos --remove`. Лицензия Unsplash
разрешает коммерческое использование без указания автора. Нужен доступ сервера к images.unsplash.com.

### Роли

```bash
python manage.py setup_roles   # после наполнения; повторный запуск безопасен
```

Создаёт группы: «Контент-менеджер» (все страницы), «Маркетинг» (акции, новости, Give a Paw, каталог, бренды),
«Магазины» (страницы магазинов), «HR» (карьера + отклики), «Заявки» (обращения и заявки партнёров).
Пользователей добавляют в группы в CMS → Настройки → Пользователи.

Уведомления о новых заявках: `LEADS_NOTIFY_EMAILS` (почта) и/или `TELEGRAM_BOT_TOKEN` + `TELEGRAM_CHAT_ID`.

## Реальные магазины из ZooCorpApp

В Django shell ZooCorpApp:

```python
import json
from structure.models import Branch
qs = Branch.objects.filter(organization__slug="zooplaneta", branch_type="store", is_active=True)
json.dump([{"id": str(b.id), "name": b.name, "address": b.address,
            "lat": str(b.latitude) if b.latitude is not None else None,
            "lng": str(b.longitude) if b.longitude is not None else None,
            "opens": b.opening_time.strftime("%H:%M"), "closes": b.closing_time.strftime("%H:%M")}
           for b in qs], open("stores.json", "w"), ensure_ascii=False, indent=1)
```

Здесь:

```bash
python manage.py import_stores stores.json --dry-run
python manage.py import_stores stores.json
```

Новые магазины создаются на трёх языках (UZ/EN — копия, переведите названия в CMS); у существующих обновляются адрес, координаты, часы и телефон. Демо-магазины (`store-01…23`) после импорта удалите в CMS.

## Продакшен (сервер timkon.uz, nginx на хосте)

Один контейнер, без отдельной базы. Всё, что должно пережить пересборку, лежит на хосте в `/srv/zooplaneta`
(другой путь — переменная `ZP_DATA_DIR`):

| Папка на хосте | В контейнере | Что там |
|---|---|---|
| `/srv/zooplaneta/data` | `/app/data` | база `db.sqlite3` и `backups/` |
| `/srv/zooplaneta/media` | `/app/media` | загруженные фото и документы (отдаёт nginx) |
| `/srv/zooplaneta/private` | `/app/private` | резюме (только через CMS) |

### 1. DNS
A-записи `zooplaneta.uz` и `www.zooplaneta.uz` → IP сервера. Проверка: `dig +short zooplaneta.uz`.

### 2. Приложение
```bash
cd /srv && git clone https://github.com/KamolCoder/zooplaneta-site.git && cd zooplaneta-site
sudo mkdir -p /srv/zooplaneta/{data,media,private}
cp .env.example .env    # SECRET_KEY, ALLOWED_HOSTS, SITE_URL=https://zooplaneta.uz, ADMIN_URL (неочевидный путь)
docker compose up -d --build
docker compose exec web python manage.py createsuperuser
curl -sI -H "Host: zooplaneta.uz" http://127.0.0.1:8030/health/    # 204
```
Контейнер при каждом старте выполняет `migrate` и `sync_site` (адрес сайта для canonical и sitemap берётся из `SITE_URL`).

### 3. nginx
```bash
sudo cp deploy/nginx/zooplaneta.conf /etc/nginx/conf.d/zooplaneta.conf
# в /etc/nginx/nginx.conf внутри http { } добавить одну строку:
#     include /etc/nginx/conf.d/zooplaneta.conf;
sudo nginx -t && sudo systemctl reload nginx     # reload не прерывает остальные сайты
```

### 4. HTTPS
```bash
sudo certbot --nginx -d zooplaneta.uz -d www.zooplaneta.uz --redirect
sudo nginx -t && sudo systemctl reload nginx
```
certbot сам допишет 443, сертификат и редирект http → https; продление — его же таймер.

### 5. Проверка
```bash
curl -sI http://zooplaneta.uz/ | head -3            # 301 → https
curl -sI https://www.zooplaneta.uz/ru/ | head -3    # 301 → https://zooplaneta.uz/ru/
curl -sI https://zooplaneta.uz/ru/ | head -1        # 200
curl -s https://zooplaneta.uz/robots.txt
curl -s https://zooplaneta.uz/sitemap.xml | head -5 # адреса https://zooplaneta.uz/…
```

### 6. Поисковики
1. Яндекс.Вебмастер и Google Search Console: добавить `https://zooplaneta.uz`, способ подтверждения — meta-тег.
   Код вставить в CMS: «Настройки → Контакты и реквизиты → Поисковики и аналитика».
2. В обоих отправить `https://zooplaneta.uz/sitemap.xml`.
3. Там же — номер счётчика Яндекс.Метрики и ID GA4 (счётчики подключаются только при `DEBUG=False`).

Обновление: `git pull && docker compose up -d --build` — база и файлы остаются.
**Не запускайте** `docker compose down -v` и не удаляйте `/srv/zooplaneta`.

Ресурсы: лимит контейнера 384 МБ и 0.5 CPU, gunicorn 2 процесса × 2 потока (~270 МБ). Для большей нагрузки —
`WEB_CONCURRENCY` / `WEB_THREADS` в `.env` и `mem_limit` в `docker-compose.yml`.

## SEO (что делает сайт сам)

- `sitemap.xml` со всеми языками и `hreflang`-альтернативами, `robots.txt` (CMS, API и `?sent=` закрыты).
- `canonical`, `hreflang` + `x-default` (русская версия), Open Graph на каждой странице.
- Автоматические `title` / `description`, если редактор не заполнил вкладку «Продвижение»:
  магазины — «Зоомагазин Zoo Planeta — {название}, Ташкент» + адрес, часы, телефон; акции — скидка и даты;
  вакансии — зарплата и график.
- JSON-LD: `Organization` + `WebSite` (главная), `PetStore` (магазины), `JobPosting` (открытые вакансии),
  `BreadcrumbList` (все внутренние страницы).
- Завершённые акции — `noindex` и вне sitemap.

Вне сайта, но важнее всего для «зоомагазин рядом»: карточки всех магазинов в Google Business Profile,
Яндекс Бизнесе и 2ГИС со ссылкой на страницу магазина; название, адрес и телефон — как на сайте.

### Бэкап

`deploy/crontab` — каждую ночь `backup_db --with-files`: копия базы (онлайн-бэкап SQLite с проверкой целостности)
и архив `media` + `private` в `/srv/zooplaneta/data/backups`, хранятся последние 14. Папку `backups` копируйте
и за пределы сервера (диск может умереть вместе с бэкапами).

Восстановление:

```bash
docker compose stop web
cp /srv/zooplaneta/data/backups/db-YYYYMMDD-HHMMSS.sqlite3 /srv/zooplaneta/data/db.sqlite3
rm -f /srv/zooplaneta/data/db.sqlite3-wal /srv/zooplaneta/data/db.sqlite3-shm
tar -xzf /srv/zooplaneta/data/backups/files-YYYYMMDD-HHMMSS.tar.gz -C /srv/zooplaneta   # если нужны и файлы
docker compose start web
```

## Тесты

```bash
DEBUG=True python manage.py test core
```

## Что заменить перед запуском

- Логотип: `static/img/logo.png` (сейчас 150 px из присланного файла) → нужен SVG.
- Все демо-тексты, адреса (`демо-адрес`), телефоны, акции, вакансии, бренды.
- Политика конфиденциальности — текст от юриста.
- Фото: баннеры, категории, магазины, акции.
