# Quick Start Guide

Get your FastAPI application up and running in 5 minutes!

## Prerequisites

- Docker and Docker Compose installed
- OR Python 3.13+ (for local development)

## Option 1: Docker (Recommended)

### 1. Configure

```bash
# Copy configuration files
cp config.ini.example config.ini
cp alembic.ini.example alembic.ini

# Edit config.ini with your settings (or use defaults for development)
nano config.ini
```

### 2. Start Development Environment

```bash
# Using Makefile (if available)
make dev

# OR using docker compose directly
docker compose -f docker/docker-compose.dev.yml up --build
```

### 3. Access Your Application

- **API**: http://localhost:8000
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **PostgreSQL**: localhost:5432
- **Redis**: localhost:6379

### 4. Run Database Migrations

```bash
# In another terminal
docker compose -f docker/docker-compose.dev.yml exec fastapi-app alembic upgrade head
```

### 5. Stop Everything

```bash
make down
# OR
docker compose -f docker/docker-compose.dev.yml down
```

## Option 2: Local Development (Without Docker)

### 1. Setup PostgreSQL and Redis

You'll need to have PostgreSQL and Redis running locally or via Docker:

```bash
# PostgreSQL
docker run -d --name postgres -e POSTGRES_PASSWORD=postgres -p 5432:5432 postgres:15-alpine

# Redis
docker run -d --name redis -p 6379:6379 redis:7-alpine
```

### 2. Configure

```bash
# Copy configuration files
cp config.ini.example config.ini
cp alembic.ini.example alembic.ini

# Edit config.ini to point to localhost services
nano config.ini
```

### 3. Create Virtual Environment

```bash
python3.13 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 4. Install Dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### 5. Run Migrations

```bash
alembic upgrade head
```

### 6. Start Application

```bash
# With auto-reload
uvicorn src.main:app --reload --host 0.0.0.0 --port 8000

# OR using Python directly
python src/main.py

# OR using the start script
chmod +x start.sh
./start.sh
```

### 7. Access Your Application

- **API**: http://localhost:8000
- **Swagger UI**: http://localhost:8000/api/docs (protected with HTTP Basic Auth)
- **OpenAPI**: http://localhost:8000/api/openapi.json
- **Health Check**: http://localhost:8000/api/root/health

## Production Deployment

### Quick Deploy with Docker

```bash
# 1. Configure production settings
cp config.ini.example config.ini
nano config.ini  # Set environment=production, update secrets

# 2. Start production services
make up
# OR
docker compose -f docker/docker-compose.yml up -d --build

# 3. Run migrations
docker compose -f docker/docker-compose.yml exec fastapi-app alembic upgrade head

# 4. Check status
docker compose -f docker/docker-compose.yml ps
docker compose -f docker/docker-compose.yml logs -f fastapi-app
```


## Common Commands

```bash
# Development
make dev            # Start development environment
make logs           # View logs
make down           # Stop all services
make test           # Run tests
make lint           # Check code quality
make format         # Format code

# Database
make migrate        # Apply migrations
make migrate-create # Create new migration
make db-shell       # Open PostgreSQL shell
make redis-cli      # Open Redis CLI

# Production
make build          # Build production image
make up             # Start production
make clean          # Remove everything
```

## Project Structure

The template uses the following structure:

```
src/
├── main.py                    # Application entry point
├── config.py                  # Configuration loader (INI)
├── configuration/
│   └── app.py                 # FastAPI app initialization
├── middlewares/               # HTTP middlewares
│   └── database.py            # Database session per request
├── routers/                   # API routes
│   ├── __init__.py            # Router registration
│   └── root/                  # Example router
│       ├── router.py          # Route definitions
│       ├── actions.py         # Business logic
│       ├── dal.py             # Data access layer
│       ├── models.py          # SQLAlchemy models
│       └── schemas.py         # Pydantic schemas
├── database/                  # Database config
│   ├── core.py                # Engine and sessions
│   ├── dependencies.py        # DB dependencies
│   └── alembic/               # Migrations
├── redis_client/              # Redis operations
│   └── redis.py               # Cache controller
└── services/                  # External services
```

### Example: Create New Router

1. **Create new router directory:**

```bash
mkdir -p src/routers/users
touch src/routers/users/__init__.py
touch src/routers/users/router.py
touch src/routers/users/actions.py
touch src/routers/users/dal.py
touch src/routers/users/models.py
touch src/routers/users/schemas.py
```

2. **Define routes** (`src/routers/users/router.py`):

```python
from fastapi import APIRouter
from src.database.dependencies import DbSession
from src.routers.users.actions import _get_users

router = APIRouter()

@router.get("/")
async def get_users(session: DbSession):
    return await _get_users(session)
```

3. **Register router** in `src/routers/__init__.py`:

```python
from src.routers.root.router import router as root_router
from src.routers.users.router import router as users_router

@dataclass(frozen=True)
class Router:
    routers = [
        (root_router, "/api/root", ["root"]),
        (users_router, "/api/users", ["users"]),
    ]
```

4. **Restart application** and visit http://localhost:8000/api/docs

## Next Steps

1. **Add Database Models** - Create SQLAlchemy models in `app/models/`
2. **Create Schemas** - Define Pydantic schemas in `app/schemas/`
3. **Write Business Logic** - Implement services in `app/services/`
4. **Add API Endpoints** - Create routes in `app/api/endpoints/`
5. **Write Tests** - Add tests in `tests/` directory
6. **Deploy** — см. [DEPLOYMENT.md](DEPLOYMENT.md) (Docker)

## Troubleshooting

### Port already in use
```bash
# Check what's using the port
lsof -i :8000

# Change port in config.ini or docker-compose file
```

### Database connection error
```bash
# Check database is running
docker ps | grep postgres

# Verify connection string in config.ini
```

### Permission denied on start.sh
```bash
chmod +x start.sh
```

### Docker image build fails
```bash
# Clean up and rebuild
make clean
make build
```

## Getting Help

- **Documentation**: Read [README.md](README.md) for full documentation
- **Deployment**: See [DEPLOYMENT.md](DEPLOYMENT.md) for deployment guides
- **Contributing**: Check [CONTRIBUTING.md](CONTRIBUTING.md) for development guidelines
- **Template Info**: See [TEMPLATE_INFO.md](TEMPLATE_INFO.md) for complete overview

## Useful Resources

- [FastAPI Docs](https://fastapi.tiangolo.com/)
- [SQLAlchemy Docs](https://docs.sqlalchemy.org/)
- [Alembic Tutorial](https://alembic.sqlalchemy.org/en/latest/tutorial.html)
- [Docker Compose Docs](https://docs.docker.com/compose/)

Happy coding! 🚀

