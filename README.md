# ZhuchkaKeyboards auth

Microservice based on [Reei-dp/fastapi-template](https://github.com/Reei-dp/fastapi-template) (systemd unit and GitHub Actions workflow removed).


A production-ready FastAPI boilerplate designed for rapid project setup — featuring clean architecture, Docker support, logging and INI-based configuration.

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
make test           # Run tests
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

#### Health Check
- Database connectivity check
- Redis connectivity check
- Returns 200 (healthy) or 503 (unhealthy)
- Accessible at `/api/root/health`


## Testing

```bash
# Run all tests
make test

# Run with coverage
pytest --cov=src --cov-report=html

# Run specific test
pytest tests/test_api.py -v
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
