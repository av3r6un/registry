# Registry

Registry is an internal control panel for managing nginx reverse proxy and stream proxy snippets. It stores domain definitions in a database, renders nginx config files from templates, validates the generated nginx configuration, and can optionally request HTTP-01 certificates through certbot.

This project is intended for trusted operators. Protect the panel with Basic Auth and do not expose it directly to the public internet.

## Stack

- Backend: `aiohttp`, SQLAlchemy async ORM, Alembic
- Database: any SQLAlchemy async URL supported by the installed drivers, commonly SQLite or MySQL
- Frontend: Vue 3 in `registry/`
- Config rendering: Mako templates for nginx HTTP and stream snippets
- Certificate issuance: certbot webroot flow

## Repo Layout

- `main.py`: backend entrypoint
- `backend/config/`: static YAML defaults loaded by `Settings`
- `backend/functions/`: payload normalization and validation helpers
- `backend/models/`: SQLAlchemy models for domains, routes, server names, deployments, and certificates
- `backend/routes/`: aiohttp route handlers
- `backend/services/`: service layer for database changes, nginx file operations, and certbot calls
- `backend/templates/`: generated nginx config templates
- `alembic/`: database migrations
- `docker/`: nginx config used by the container image
- `registry/`: Vue frontend

## Core Logic

The frontend talks to the backend through `/api`. The backend route handlers keep request handling thin and delegate domain behavior to `DomainService`.

Domain creation and update follow this flow:

1. The API receives a payload from the Vue form.
2. `normalize_payload()` validates the domain type, hostname, upstream host, ports, scheme, stream protocol, and server names.
3. `DomainService` stores the normalized `Domain`, `DomainRoute`, and `DomainServerName` rows.
4. A draft `DomainDeployment` is created with the rendered nginx config text.
5. The draft deployment is returned to the UI and can be previewed before applying.

Applying a domain follows this flow:

1. The latest deployment is selected, or a deployment is rendered from the current domain state.
2. The nginx config is written atomically to the configured `sites-available` or `streams-available` path.
3. The config is copied into the configured enabled path.
4. `NGINX_TEST_COMMAND` is executed, usually `/usr/sbin/nginx -t`.
5. If validation fails, the previous config files are restored from backups.
6. If validation succeeds, `NGINX_RELOAD_COMMAND` is executed when configured.
7. The deployment and domain status are updated in the database.

Disabling or deleting a domain removes the enabled config file and optionally reloads nginx. Deleting also removes the database row and cascades related route, server name, deployment, and certificate records.

Certificate issuance is only supported for hostname domains:

1. A temporary HTTP deployment is applied with `/.well-known/acme-challenge/` served from `CERTBOT_WEBROOT`.
2. certbot runs `certonly --webroot` for the domain and aliases.
3. If certbot succeeds, an SSL-enabled nginx deployment is rendered and applied.
4. Certificate paths and status are stored in the database.

## Configuration

Runtime configuration comes from environment variables and `backend/config/settings.yaml`. On Windows, `.env` is loaded for local development. On Linux/container deployments, pass environment variables through the service manager or Compose.

Required:

- `DB_URL`: SQLAlchemy async database URL, for example `sqlite+aiosqlite:///app/backend/data/app.db`

Common optional variables:

- `APP_PORT`: aiohttp port, default `8090`
- `DEBUG`: enables console logging when set
- `BASIC_AUTH_ENABLED`: defaults to enabled
- `BASIC_AUTH_USER`, `BASIC_AUTH_PASS`: when user is set, requests require HTTP Basic Auth
- `NGINX_TEST_COMMAND`: command used to validate nginx config
- `NGINX_RELOAD_COMMAND`: optional command used after a successful apply
- `NGINX_SITES_AVAILABLE`, `NGINX_SITES_ENABLED`: HTTP snippet paths
- `NGINX_STREAMS_AVAILABLE`, `NGINX_STREAMS_ENABLED`: stream snippet paths
- `NGINX_BACKUP_DIR`: backup directory for overwritten generated configs
- `CERTBOT_BIN`: certbot executable, default `/usr/bin/certbot`
- `CERTBOT_EMAIL`: optional ACME registration email
- `CERTBOT_WEBROOT`: HTTP-01 challenge webroot
- `LETSENCRYPT_DIR`, `CERTBOT_WORK_DIR`, `CERTBOT_LOGS_DIR`: certbot state paths
- `CERTBOT_STAGING`: use Let's Encrypt staging when truthy in settings

Do not commit `.env` or any file containing real credentials. The repository ignore rules exclude `.env`, `.env.*`, local databases, logs, caches, and generated build artifacts.

## Backend Setup

```bash
uv sync --frozen
uv run alembic upgrade head
uv run python main.py
```

For local SQLite development, set `DB_URL` before running migrations and the app:

```bash
DB_URL=sqlite+aiosqlite:///app.db
```

On PowerShell:

```powershell
$env:DB_URL = "sqlite+aiosqlite:///app.db"
uv run alembic upgrade head
uv run python main.py
```

## Frontend Setup

```bash
cd registry
npm install
npm run serve
```

Build for deployment:

```bash
cd registry
npm install
npm run build
```

The Vue dev server proxies `/api/` to `http://localhost:8081/`.

## Docker

The Dockerfile builds the Vue frontend, installs the backend, copies nginx support config, and starts the app through `entrypoint.sh`.

Build:

```bash
docker build -t your-dockerhub-user/nginx-admin:latest .
```

Run with Compose after setting the image name:

```bash
export NGINX_ADMIN_IMAGE=your-dockerhub-user/nginx-admin:latest
docker compose -f docker-compose.example.yml up -d
```

Ports:

- `8081`: admin UI and API
- Generated stream listen ports must also be published or routed on the host if stream proxying is used.

Container nginx paths:

- HTTP source configs: `/etc/nginx/sites-available`
- HTTP enabled configs: `/etc/nginx/sites-enabled`
- Stream source configs: `/etc/nginx/streams-available`
- Stream enabled configs: `/etc/nginx/streams-enabled`
- Backups: `/app/backend/runtime/backups`
- ACME webroot: `/var/www/certbot`
- Certificates: `/etc/letsencrypt`

The app validates configs with nginx inside the container. If the real traffic-serving nginx is outside the container, ensure the mounted enabled directories and certbot webroot are visible to that nginx instance too.

## API

- `GET /health`
- `GET /api/domains`
- `GET /api/domains/{id}`
- `POST /api/domains`
- `PUT /api/domains/{id}`
- `POST /api/domains/{id}/apply`
- `POST /api/domains/{id}/certificate`
- `POST /api/domains/{id}/disable`
- `DELETE /api/domains/{id}`

Success response:

```json
{ "status": "success", "body": {} }
```

Error response:

```json
{ "status": "error", "message": "invalid_upstream_port" }
```

## Example Payloads

HTTP reverse proxy:

```json
{
  "type": "hostname",
  "name": "example.com",
  "server_names": ["example.com", "www.example.com"],
  "upstream_host": "10.20.30.10",
  "upstream_port": 3000,
  "upstream_scheme": "http"
}
```

TCP stream proxy:

```json
{
  "type": "port_proxy",
  "name": "minecraft",
  "listen_port": 25565,
  "stream_protocol": "tcp",
  "upstream_host": "10.20.30.10",
  "upstream_port": 25565
}
```

The backend also accepts legacy `proxy_type` values: `http` maps to hostname mode and `stream` maps to port proxy mode.

## Generated Config Behavior

Hostname domains render an HTTP `server` block on port 80. When SSL is enabled, nginx also renders a port 443 block and redirects HTTP traffic to HTTPS. Server aliases become nginx `server_name` values.

Port proxy domains render a `stream` `server` block. TCP uses a plain `listen` directive, while UDP adds `udp` and `proxy_responses 1`.

Generated filenames are derived from the lowercased domain name and limited to alphanumeric characters, dots, and hyphens.

## Security Checklist

- Keep `.env`, local databases, logs, and certbot state out of git.
- Use `BASIC_AUTH_USER` and `BASIC_AUTH_PASS` in any shared environment.
- Prefer running the panel on a private network or behind an authenticated reverse proxy.
- Review generated nginx config in the preview page before applying.
- Use `CERTBOT_STAGING` while testing certificate flows to avoid rate limits.
- Mount only the nginx directories this app needs to write.
