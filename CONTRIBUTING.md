# Contributing Guide

Thank you for your interest in contributing to this FastAPI template! This guide will help you get started.

## Development Setup

### Prerequisites

- Python 3.13+
- Docker and Docker Compose
- Git
- Make (optional but recommended)

### Local Setup

1. **Fork and clone the repository:**
```bash
git clone https://github.com/your-username/fastapi-template.git
cd fastapi-template
```

2. **Create configuration files:**
```bash
cp config.ini.example config.ini
cp alembic.ini.example alembic.ini
```

3. **Start development environment:**
```bash
make dev
# or
docker compose -f docker/docker-compose.dev.yml up --build
```

### Without Docker

1. **Create virtual environment:**
```bash
python3.13 -m venv venv
source venv/bin/activate
```

2. **Install dependencies:**
```bash
pip install -r requirements.txt
```

3. **Start PostgreSQL and Redis** (using Docker or locally)

4. **Configure application:**
```bash
cp config.ini.example config.ini
cp alembic.ini.example alembic.ini
# Edit config files with your settings
```

5. **Run application:**
```bash
python src/main.py
# or
uvicorn src.main:app --reload
```

## Code Style

We use the following tools to maintain code quality:

### Ruff

For linting and formatting:

```bash
# Check for issues
make lint
# or
ruff check .

# Auto-fix issues
make format
# or
ruff check --fix .
ruff format .
```

### Type Hints

- Use type hints for all function parameters and return values
- Use modern Python type syntax (Python 3.10+)
```python
# Good
def get_user(user_id: int) -> User | None:
    ...

# Avoid
def get_user(user_id):
    ...
```

## Testing

### Running Tests

```bash
# Run all tests
make test

# Run with coverage
pytest --cov=app --cov-report=html

# Run specific test file
pytest tests/test_api.py

# Run specific test
pytest tests/test_api.py::test_create_user
```

### Writing Tests

- Write tests for all new features
- Maintain at least 80% code coverage
- Use descriptive test names
- Follow AAA pattern (Arrange, Act, Assert)

```python
def test_create_user_success():
    # Arrange
    user_data = {"email": "test@example.com", "password": "secure123"}
    
    # Act
    response = client.post("/users", json=user_data)
    
    # Assert
    assert response.status_code == 201
    assert response.json()["email"] == user_data["email"]
```

## Database Migrations

### Creating Migrations

```bash
# Auto-generate migration
make migrate-create
# or
alembic revision --autogenerate -m "description"
```

### Applying Migrations

```bash
make migrate
# or
alembic upgrade head
```

### Migration Best Practices

- Always review auto-generated migrations
- Test migrations both up and down
- Include data migrations when schema changes
- Never modify existing migrations that are in production

## Commit Guidelines

### Commit Messages

Follow conventional commits format:

```
<type>(<scope>): <subject>

<body>

<footer>
```

**Types:**
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes (formatting, etc.)
- `refactor`: Code refactoring
- `test`: Adding or updating tests
- `chore`: Maintenance tasks

**Examples:**
```bash
feat(auth): add JWT token refresh endpoint
fix(users): resolve email validation bug
docs(readme): update installation instructions
test(api): add tests for user registration
```

### Branch Naming

- `feature/description` - New features
- `fix/description` - Bug fixes
- `docs/description` - Documentation
- `refactor/description` - Refactoring

**Examples:**
```
feature/user-authentication
fix/database-connection-pool
docs/api-documentation
refactor/error-handling
```

## Pull Request Process

1. **Create a feature branch:**
```bash
git checkout -b feature/your-feature-name
```

2. **Make your changes and commit:**
```bash
git add .
git commit -m "feat: your feature description"
```

3. **Run tests and linting:**
```bash
make test
make lint
```

4. **Push to your fork:**
```bash
git push origin feature/your-feature-name
```

5. **Create Pull Request:**
   - Provide clear description of changes
   - Reference related issues
   - Ensure tests and lint pass locally
   - Request review from maintainers

### PR Description Template

```markdown
## Description
Brief description of what this PR does.

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Breaking change
- [ ] Documentation update

## Changes Made
- Change 1
- Change 2
- Change 3

## Testing
Describe how you tested these changes.

## Checklist
- [ ] Code follows project style guidelines
- [ ] Tests added/updated
- [ ] Documentation updated
- [ ] All tests passing
- [ ] No linting errors
```

## Project Structure

The project follows a clean architecture pattern:

```
src/
├── main.py                    # Application entry point
├── config.py                  # Configuration loader (INI)
├── configuration/
│   └── app.py                 # FastAPI app initialization
├── middlewares/               # HTTP middlewares
│   └── database.py            # Database session per request
├── routers/                   # API routers
│   ├── __init__.py            # Router registration
│   └── root/                  # Example router
│       ├── router.py          # Route definitions
│       ├── actions.py         # Business logic
│       ├── dal.py             # Data access layer
│       ├── models.py          # SQLAlchemy models
│       └── schemas.py         # Pydantic schemas
├── database/                  # Database configuration
│   ├── core.py                # Database engine
│   ├── dependencies.py        # DB dependencies
│   └── alembic/               # Migrations
├── redis_client/              # Redis operations
│   └── redis.py               # Cache controller
├── services/                  # External services
└── misc/                      # Utilities
```

### Adding New Routes

1. Create router directory: `src/routers/your_feature/`
2. Add required files: `router.py`, `actions.py`, `dal.py`, `models.py`, `schemas.py`
3. Register in `src/routers/__init__.py`

## API Design Guidelines

### Endpoints

- Use plural nouns for resources: `/users`, `/items`
- Use HTTP methods appropriately:
  - GET: Retrieve resources
  - POST: Create resources
  - PUT: Update entire resource
  - PATCH: Partial update
  - DELETE: Remove resource

### Response Format

```python
# Success response
{
    "data": {...},
    "message": "Success message"
}

# Error response
{
    "detail": "Error description",
    "code": "ERROR_CODE"
}
```

### Status Codes

- 200: OK (GET, PUT, PATCH)
- 201: Created (POST)
- 204: No Content (DELETE)
- 400: Bad Request
- 401: Unauthorized
- 403: Forbidden
- 404: Not Found
- 422: Validation Error
- 500: Internal Server Error

## Configuration

### Adding New Settings

1. Add to `config.ini.example`:
```ini
[new_section]
setting = value
```

2. Update configuration model (if using Pydantic):
```python
class Settings(BaseSettings):
    new_setting: str
```

3. Document in README.md

## Documentation

### Code Documentation

- Add docstrings to all functions and classes
- Use Google-style docstrings:

```python
def get_user_by_id(user_id: int) -> User | None:
    """
    Retrieve a user by their ID.
    
    Args:
        user_id: The unique identifier of the user.
        
    Returns:
        User object if found, None otherwise.
        
    Raises:
        DatabaseError: If database connection fails.
    """
    ...
```

### API Documentation

- Use FastAPI's automatic documentation
- Add descriptions to endpoints:

```python
@router.get("/users/{user_id}", summary="Get user by ID")
async def get_user(
    user_id: int = Path(..., description="The user ID"),
) -> User:
    """
    Retrieve a user by their unique identifier.
    
    Returns user details including email, name, and creation date.
    """
    ...
```

## Security

### Reporting Vulnerabilities

- **DO NOT** open public issues for security vulnerabilities
- Email security concerns to: [your-email@example.com]
- Include detailed description and reproduction steps

### Security Best Practices

- Never commit sensitive data (credentials, keys)
- Use environment variables or config files for secrets
- Validate all user inputs
- Use parameterized queries (SQLAlchemy handles this)
- Keep dependencies updated

## Getting Help

- Check existing [Issues](https://github.com/your-repo/issues)
- Read [Documentation](README.md)
- Ask questions in [Discussions](https://github.com/your-repo/discussions)

## License

By contributing, you agree that your contributions will be licensed under the same license as the project (MIT License).

