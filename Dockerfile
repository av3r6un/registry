FROM node:22-bookworm-slim AS frontend-builder
WORKDIR /app/registry
COPY registry/package.json registry/package-lock.json ./
RUN npm ci
COPY registry/ ./
RUN npm run build

FROM python:3.14-slim
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends nginx libnginx-mod-stream certbot \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir uv
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

COPY backend/ /app/backend/
COPY main.py /app/
COPY alembic /app/alembic
COPY alembic.ini /app/
COPY entrypoint.sh /app/

COPY --from=frontend-builder /app/registry/dist /app/frontend/dist
COPY docker/nginx.conf /etc/nginx/nginx.conf
COPY docker/nginx-admin-available.conf /etc/nginx/conf.d/nginx-admin-available.conf
RUN mkdir -p /app/backend/data /etc/nginx/sites-available /etc/nginx/sites-enabled /etc/nginx/streams-available /etc/nginx/streams-enabled /app/backend/runtime/backups /var/www/certbot /etc/letsencrypt /var/lib/letsencrypt /var/log/letsencrypt /var/log/registry

EXPOSE 8081

RUN chmod +x /app/entrypoint.sh

ENTRYPOINT ["/app/entrypoint.sh"]
