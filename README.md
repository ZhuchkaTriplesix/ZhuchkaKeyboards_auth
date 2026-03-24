# ZhuchkaKeyboards auth

OAuth2/OIDC authorization server for ZhuchkaKeyboards: **JWT (RS256)**, **JWKS**, **token** (`client_credentials`, `password`, `refresh_token`), **userinfo**, admin API for users. See `docs/microservices/01-auth.md` in the parent monorepo.

Microservice based on [Reei-dp/fastapi-template](https://github.com/Reei-dp/fastapi-template) (upstream systemd unit removed; this repo has its own CI).

**CI:** on push/PR to `dev`, GitHub Actions runs **ruff** (lint + format check), **pytest** with coverage, **docker build** (`docker/Dockerfile`), and a separate job **integration-tests** (PostgreSQL service, migrations, `pytest -m integration`). Dev tools: `pip install -r requirements-dev.txt`.

**OpenAPI 3.x:** `GET /api/openapi.json` — machine-readable spec (tags, `BearerAuth` security scheme). `GET /api/docs` serves Swagger UI (Basic auth placeholder in `src/main.py`).

**Workflow:** one issue → one branch from `dev` → tests for that change → one PR into `dev`. Same policy for [`bots/auth_bot`](https://github.com/ZhuchkaTriplesix/ZhuchkaKeyboards_auth_bot). Details: [git-workflow.md](https://github.com/ZhuchkaTriplesix/ZhuchkaKeyboards/blob/main/docs/git-workflow.md) (section «`services/auth` и `bots/auth_bot`»).

### Auth API (summary)

| Endpoint | Purpose |
|----------|---------|
| `GET /.well-known/openid-configuration` | OIDC discovery |
| `GET /.well-known/jwks.json` | Public keys for JWT verification |
| `POST /oauth/token` | Token (form body: `grant_type`, client auth Basic or `client_id`/`client_secret`) |
| `POST /oauth/revoke` | Revoke refresh token |
| `POST /oauth/introspect` | RFC 7662 token introspection (confidential client only; form: `token`, optional `token_type_hint`) |
| `GET /oauth/userinfo` | OIDC userinfo (Bearer access token) |
| `GET /oauth/authorize` | Stub until PKCE UI (returns `unsupported_response_type`) |
| `POST /oauth/federated/google` | JSON: `client_id` (public), `id_token` (Google ID token). **Requires** `[AUTH] GOOGLE_CLIENT_IDS`. |
| `POST /oauth/federated/telegram` | JSON: Telegram Login widget fields + `client_id`. **Requires** `[AUTH] TELEGRAM_BOT_TOKEN`. |
| `GET /health/live`, `GET /health/ready` | Liveness / readiness |
| `GET /metrics` | Prometheus metrics (`auth_http_requests_total`, process stats) |
| `/api/v1/users`, `/api/v1/users/{id}` | Admin: list/create/get/patch/delete (soft) users |
| `/api/v1/users/{id}/roles`, `/api/v1/users/{id}/mfa` | Admin: replace/add roles; enable/disable MFA flags |
| `/api/v1/roles`, `/api/v1/clients` | Admin: list roles; OAuth clients CRUD (secret shown once on create) |

All `/api/v1/*` routes require **Bearer** JWT with **`admin` scope**.

**Bootstrap (dev):** set `[AUTH]` `BOOTSTRAP_ADMIN_EMAIL`, `BOOTSTRAP_ADMIN_PASSWORD`, and `BOOTSTRAP_CLIENT_SECRET` in `config.ini`. On startup the service creates roles, a confidential OAuth client (`BOOTSTRAP_CLIENT_ID`), and an admin user. RSA key for JWT is created under `var/jwt_private.pem` if `AUTH_JWT_PRIVATE_KEY_PEM` is not set.

**Federated login (storefront):** bootstrap also creates a **public** OAuth client (`PUBLIC_OAUTH_CLIENT_ID`, default `zhuchka-market-web`) with no secret — use this `client_id` from browser apps. Set `TELEGRAM_BOT_TOKEN` (from @BotFather) and comma-separated `GOOGLE_CLIENT_IDS` (Google OAuth Web client ID(s)) to enable `POST /oauth/federated/*`. Users with `identity_kind=staff` **cannot** complete Telegram/Google login (HTTP 403 `access_denied`); they must use the operational password/MFA flow.

**Migrations:** `alembic upgrade head` (from repo root with `alembic.ini` / `config.ini` configured). Chain: `20250323_0001` (users, roles, OAuth clients, refresh tokens, login audit) → `20250323_0002` (`users.identity_kind` `customer`/`staff`, `external_identity` for federated IdPs, `login_audit.login_method`). Requires PostgreSQL with `pgcrypto` or `gen_random_uuid()` (PostgreSQL 13+).

**Python:** use **3.11–3.13** for local venv; 3.14 may lack wheels for some dependencies.

## Features

- ⚡ **FastAPI** with Python 3.13
- 🐳 **Docker** & **Docker Compose** for development and production
- 🗄️ **PostgreSQL** database with SQLAlchemy
- 🔴 **Redis** for caching
- 🔒 **Nginx** reverse proxy with rate limiting
- 📝 **Alembic** for database migrations
- 🧪 **Pytest** for testing
- 📊 **Logging** configured and ready to use
- 🔧 **Makefile** for convenient development

## Quick Start

### Prerequisites

- Docker and Docker Compose
- Python 3.13+ (for local development)
- Make (optional)

### Installation

1. Clone the repository:
```bash
git clone <your-repo-url>
cd ZhuchkaKeyboards_auth
```

2. Create `config.ini` file from example:
```bash
cp config.ini.example config.ini
```

3. Edit `config.ini` file according to your needs

**Docker:** the app image runs **`alembic upgrade head`** on container start (before Granian/uvicorn), using the same DB URL as the app (`config.ini` `[POSTGRES]` or `DATABASE_URL` / `ALEMBIC_DATABASE_URL`). In Compose, point Postgres `IP` at the DB service name (e.g. `postgres`). To skip migrations, set **`SKIP_MIGRATIONS=1`**.

### Running (Development)

#### Using Docker Compose:
```bash
make dev
# or
docker compose -f docker/docker-compose.dev.yml up --build
```

#### Locally (without Docker):
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
python src/main.py
# or
uvicorn src.main:app --reload
```

Application will be available at: http://localhost:8000

API documentation:
- Swagger UI: http://localhost:8000/api/docs (protected)
- OpenAPI JSON: http://localhost:8000/api/openapi.json

### Running (Production)

```bash
make up
# or
docker compose -f docker/docker-compose.yml up -d
```

## Project Structure

```
ZhuchkaKeyboards_auth/
├── src/                          # Source code
│   ├── main.py                   # FastAPI application entry point
│   ├── config.py                 # Configuration loader (INI files)
│   ├── dependencies.py           # Global dependencies
│   ├── schemas.py                # Shared Pydantic schemas
│   ├── configuration/
│   │   └── app.py                # FastAPI app initialization
│   ├── middlewares/              # HTTP middlewares
│   │   ├── __init__.py
│   │   └── database.py           # Database session middleware
│   ├── routers/                  # API routers
│   │   ├── __init__.py           # Router registration
│   │   └── root/                 # Root endpoints
│   │       ├── router.py         # Route definitions
│   │       ├── actions.py        # Business logic
│   │       ├── dal.py            # Data access layer
│   │       ├── models.py         # Database models
│   │       └── schemas.py        # Request/response schemas
│   ├── database/                 # Database configuration
│   │   ├── core.py               # Database engine and sessions
│   │   ├── base.py               # Base model class
│   │   ├── dependencies.py       # Database dependencies
│   │   ├── logging.py            # Session tracking
│   │   └── alembic/              # Database migrations
│   ├── redis_client/             # Redis operations
│   │   └── redis.py              # Redis controller with caching methods
│   ├── services/                 # External service integrations
│   └── misc/                     # Utilities
│       ├── security.py           # Security utilities
│       └── timezone.py           # Timezone utilities
├── docker/
│   ├── Dockerfile                # Production Dockerfile
│   ├── Dockerfile.dev            # Development Dockerfile
│   ├── docker-entrypoint.sh      # alembic upgrade head, then app
│   ├── docker-compose.yml        # Production stack
│   ├── docker-compose.dev.yml    # Development stack
│   └── nginx/
│       └── nginx.conf            # Nginx configuration
├── config.ini.example            # Configuration template
├── alembic.ini.example           # Alembic configuration template
├── requirements.txt              # Python dependencies
├── Makefile                      # Build commands
├── start.sh                      # Startup script
└── README.md                     # This file
```

## Makefile Commands

```bash
make help           # Show all available commands
make install        # Install dependencies
make dev            # Start development environment
make build          # Build production Docker image
make up             # Start production environment
make down           # Stop all containers
make logs           # Show logs
make clean          # Remove containers and volumes
make test           # Run tests (integration skipped unless INTEGRATION_TEST=1)
make test-integration # DB integration tests (Unix; needs Postgres + alembic upgrade head)
make lint           # Run linter
make format         # Format code
make migrate        # Apply migrations
make migrate-create # Create new migration
```


## Configuration

Application uses INI files for configuration (see `config.ini.example`):

```ini
[POSTGRES]
# PostgreSQL database configuration
DATABASE = postgresql
DRIVER = asyncpg
DATABASE_NAME = your_database_name
USERNAME = postgres
PASSWORD = your_password
IP = localhost
PORT = 5432

# Connection pool settings
DATABASE_ENGINE_POOL_TIMEOUT = 30
DATABASE_ENGINE_POOL_RECYCLE = 3600
DATABASE_ENGINE_POOL_SIZE = 5
DATABASE_ENGINE_MAX_OVERFLOW = 10
DATABASE_ENGINE_POOL_PING = true

# Database echo (SQL logging) - set to false in production
DATABASE_ECHO = false

[UVICORN]
# Uvicorn server configuration
HOST = 0.0.0.0
PORT = 8000
WORKERS = 4
LOOP = uvloop          # Event loop: asyncio | uvloop (uvloop is faster)
HTTP = httptools       # HTTP protocol: h11 | httptools (httptools is faster)

[REDIS]
# Redis cache configuration
HOST = localhost
PORT = 6379
DB = 0
PASSWORD =
```

### Key Features

#### Database Middleware
- Automatic session management per request
- Auto-commit on success, rollback on error
- Session tracking for debugging
- Request ID generation for tracing

#### Redis Client
- Simple caching interface with `get()`, `set()`, `delete()`, `update()`
- JSON serialization support with `get_json()` and `set_json()`
- TTL (Time To Live) management
- Multiple key deletion support

#### Health checks
- **`GET /health/live`** — liveness (process up, no dependencies)
- **`GET /health/ready`** — readiness (database reachable)
- **`GET /api/root/health`** — full check: database + Redis; returns 200 or 503


## Testing

```bash
pip install -r requirements.txt -r requirements-dev.txt
# Run all tests (markers @pytest.mark.integration are skipped unless INTEGRATION_TEST=1)
make test
```

Coverage: `pytest tests/ -v --cov=src --cov-report=html`. Single file: `pytest tests/test_smoke_public.py -v`.

**Integration tests** hit a real PostgreSQL database (`/health/ready`, OAuth flows that need the DB). Prerequisites: `config.ini` from `config.ini.example` with a reachable `[POSTGRES]` block, then `alembic upgrade head`.

```bash
# Linux/macOS (GNU make sets INTEGRATION_TEST for this target)
make test-integration
```

On **Windows** (PowerShell), set the variable and run pytest:

```powershell
$env:INTEGRATION_TEST = "1"
pytest tests/ -v -m integration
```

## Development

### Creating new migration:
```bash
make migrate-create
# or
alembic revision --autogenerate -m "migration description"
```

### Applying migrations:
```bash
make migrate
# or
alembic upgrade head
```

### Code formatting:
```bash
make format
```

## License

MIT License - see [LICENSE](LICENSE) file
