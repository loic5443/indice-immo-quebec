FROM caddy:2.10.2-alpine AS proxy
FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 \
    IMMORADAR_DATABASE_PATH=/app/var/immoradar.db
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt \
    && useradd --uid 10001 --create-home app \
    && mkdir -p /app/var && chown app:app /app/var
COPY --from=proxy /usr/bin/caddy /usr/bin/caddy
COPY --chown=app:app . .
# The launcher owns the mounted directory, then drops root before migrations
# or any server starts. No database is initialized in the build image.
EXPOSE 10000
CMD ["python", "-m", "scripts.render_server"]
