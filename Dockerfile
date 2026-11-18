FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 \
    STATIC_ROOT=/app/staticfiles MEDIA_ROOT=/app/media PRIVATE_MEDIA_ROOT=/app/private \
    SQLITE_PATH=/app/data/db.sqlite3 BACKUP_DIR=/app/data/backups
WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends libjpeg62-turbo zlib1g libwebp7 \
    && rm -rf /var/lib/apt/lists/*
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
# collectstatic at build time must not touch the real database
RUN SECRET_KEY=build DEBUG=False SQLITE_PATH=/tmp/build.sqlite3 python manage.py collectstatic --noinput \
    && rm -f /tmp/build.sqlite3*

# data, media and private are mounted from the host (see docker-compose.yml)
VOLUME ["/app/data", "/app/media", "/app/private"]
EXPOSE 8000
# small footprint: 2 workers × 2 threads (~270 MB RSS) is plenty for an info site;
# workers restart after 1000 requests so memory never creeps up
ENV WEB_CONCURRENCY=2 WEB_THREADS=2
CMD ["sh", "-c", "python manage.py migrate --noinput && python manage.py sync_site && exec gunicorn config.wsgi:application --bind 0.0.0.0:8000 --workers ${WEB_CONCURRENCY} --threads ${WEB_THREADS} --preload --max-requests 1000 --max-requests-jitter 100 --timeout 60"]
