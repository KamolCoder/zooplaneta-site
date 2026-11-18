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

## Продакшен

Один контейнер, без отдельной базы. Всё, что должно пережить пересборку, лежит на хосте в `/srv/zooplaneta`
(другой путь — переменная `ZP_DATA_DIR`):

| Папка на хосте | В контейнере | Что там |
|---|---|---|
| `/srv/zooplaneta/data` | `/app/data` | база `db.sqlite3` и `backups/` |
| `/srv/zooplaneta/media` | `/app/media` | загруженные фото и документы (отдаёт nginx) |
| `/srv/zooplaneta/private` | `/app/private` | резюме (только через CMS) |

```bash
sudo mkdir -p /srv/zooplaneta/{data,media,private}
cp .env.example .env        # заполнить
docker compose up -d --build
docker compose exec web python manage.py createsuperuser
```

Обновление: `git pull && docker compose up -d --build` — база и файлы остаются (миграции выполняются при старте).
**Не запускайте** `docker compose down -v` и не удаляйте `/srv/zooplaneta`.

Ресурсы: лимит контейнера 384 МБ и 0.5 CPU, gunicorn 2 процесса × 2 потока (~270 МБ). Для большей нагрузки —
`WEB_CONCURRENCY` / `WEB_THREADS` в `.env` и `mem_limit` в `docker-compose.yml`.

nginx — `deploy/nginx.conf` (порт 8030, `/media/` из `/srv/zooplaneta/media`).

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
