# Deployment Guide

This guide covers different deployment methods for your FastAPI application.

## Table of Contents

- [Docker Deployment](#docker-deployment)
- [Auth service environment (`config.ini` `[AUTH]`)](#auth-service-environment-configini-auth)
- [Production Checklist](#production-checklist)

## Auth service environment (`config.ini` `[AUTH]`)

OAuth/JWT and federated login are configured under the **`[AUTH]`** section (see `config.ini.example` in the repo).

| Variable | Purpose |
|----------|---------|
| `ISSUER` | JWT `iss` claim; must match the public URL of this service (no trailing slash). |
| `AUDIENCE` | Default JWT `aud` for API tokens. |
| `ACCESS_TOKEN_MINUTES` / `REFRESH_TOKEN_DAYS` | Access and refresh lifetimes. |
| `JWT_PRIVATE_KEY_PATH` | PEM path for RS256 signing; generated on first run if missing. |
| `BOOTSTRAP_*` | Optional: create admin user + confidential OAuth client on startup (dev). |
| `PASSWORD_GRANT_ENABLED` | Allow `grant_type=password` (typically for staff; not for public clients). |
| `TELEGRAM_BOT_TOKEN` | @BotFather token; required for `POST /oauth/federated/telegram`. |
| `GOOGLE_CLIENT_IDS` | Comma-separated Google OAuth **Web** client IDs; required for `POST /oauth/federated/google` (ID token audience check). |
| `PUBLIC_OAUTH_CLIENT_ID` | Public browser client (no secret), e.g. `zhuchka-market-web`, used with federated and refresh flows. |

For production, load secrets via your orchestrator (Kubernetes secrets, Docker secrets) and mount or inject `config.ini`; do not commit real tokens.

## Docker Deployment

### Using Docker Compose (Recommended)

1. **Prepare configuration files:**
```bash
cp config.ini.example config.ini
cp alembic.ini.example alembic.ini
# Edit config.ini and alembic.ini with production values
```

2. **Build and start services:**
```bash
docker compose -f docker/docker-compose.yml up -d --build
```

3. **Check service status:**
```bash
docker compose -f docker/docker-compose.yml ps
docker compose -f docker/docker-compose.yml logs -f
```

4. **Run database migrations:**
```bash
docker compose -f docker/docker-compose.yml exec fastapi-app alembic upgrade head
```

### Using Docker only

1. **Build image:**
```bash
docker build -f docker/Dockerfile -t fastapi-app:latest .
```

2. **Run container:**
```bash
docker run -d \
  --name fastapi-app \
  -p 8000:8000 \
  -v $(pwd)/config.ini:/app/config.ini:ro \
  -v $(pwd)/logs:/app/logs \
  fastapi-app:latest
```



## Production Checklist

Before deploying to production, ensure:

### Security

- [ ] Changed `secret_key` in config.ini to a strong random value
- [ ] Set `debug = false` in config.ini
- [ ] Updated database credentials
- [ ] Configured CORS origins properly
- [ ] Set up SSL/TLS certificates for HTTPS
- [ ] Configure firewall rules (only allow 80, 443, 22)
- [ ] Disable PostgreSQL remote access if not needed
- [ ] Set strong Redis password if exposed

### Configuration

- [ ] Set `environment = production` in config.ini
- [ ] Configure proper database connection pooling
- [ ] Set appropriate log levels
- [ ] Configure Redis connection
- [ ] Update Nginx configuration if using custom domain
- [ ] Set proper CORS origins

### Infrastructure

- [ ] Database backups configured
- [ ] Log rotation configured
- [ ] Monitoring and alerting set up
- [ ] Health check endpoints working
- [ ] Nginx reverse proxy configured
- [ ] SSL certificates installed and renewed automatically
- [ ] Sufficient disk space allocated

### Performance

- [ ] Adjust uvicorn workers count based on CPU cores
- [ ] Configure database connection pool size
- [ ] Set up Redis for caching
- [ ] Enable gzip compression in Nginx
- [ ] Configure static file serving

### Testing

- [ ] All tests passing
- [ ] Load testing completed
- [ ] Health check endpoint responding
- [ ] Database migrations tested
- [ ] Rollback procedure tested

## Monitoring

### Health Check

The API exposes **liveness** and **readiness** probes (`src/configuration/app.py`), plus a detailed check under `/api/root`:

```bash
curl http://localhost:8000/health/live    # process up (200)
curl http://localhost:8000/health/ready   # DB reachable (200)
curl http://localhost:8000/api/root/health # DB + Redis (200 or 503)
```

Behind Nginx on port 80, `GET /health` proxies to liveness (`/health/live`).

### Prometheus metrics

`GET /metrics` exposes Prometheus text format (process metrics plus `auth_http_requests_total{method,status_code}`). Restrict scraping to internal networks or mTLS; do not expose publicly without auth.

**Request correlation:** Send optional `X-Request-Id` (1–128 characters); the same value is returned on the response. If omitted, the service generates an ID. Application code can read the current value via `get_request_id()` in `src.middlewares.database`.

### Logs

#### Docker:
```bash
docker compose -f docker/docker-compose.yml logs -f fastapi-app
```

#### Systemd:
```bash
sudo journalctl -u fastapi-app -f
# or
tail -f logs/app.log
```

### Service Status

#### Docker:
```bash
docker compose -f docker/docker-compose.yml ps
```

#### Systemd:
```bash
sudo systemctl status fastapi-app
```

## Rollback

### Docker Deployment

```bash
# Stop current version
docker compose -f docker/docker-compose.yml down

# Checkout previous version
git checkout <previous-commit>

# Rebuild and start
docker compose -f docker/docker-compose.yml up -d --build
```

### Systemd Deployment

```bash
# Stop service
sudo systemctl stop fastapi-app

# Checkout previous version
cd /opt/apps/fastapi-app
git checkout <previous-commit>

# Reinstall dependencies if needed
source venv/bin/activate
pip install -r requirements.txt

# Restart service
sudo systemctl start fastapi-app
```

## Scaling

### Horizontal Scaling

For load balancing multiple instances:

1. Run multiple containers on different ports
2. Configure Nginx upstream:

```nginx
upstream fastapi_cluster {
    server localhost:8000;
    server localhost:8001;
    server localhost:8002;
}
```

### Vertical Scaling

Adjust worker processes in production:

```ini
# In your start script or service file
uvicorn app.main:app --workers 8
```

Rule of thumb: `workers = (2 x CPU cores) + 1`

## Troubleshooting

### Application won't start

1. Check logs: `docker compose logs` or `journalctl -u fastapi-app`
2. Verify config.ini exists and is readable
3. Check database connectivity
4. Ensure port 8000 is not in use

### Database connection errors

1. Verify database is running
2. Check database credentials in config.ini
3. Ensure database accepts connections
4. Test connection manually: `psql -h localhost -U postgres -d fastapi_db`

### High memory usage

1. Reduce number of workers
2. Adjust database connection pool size
3. Check for memory leaks in application code
4. Monitor with `docker stats` or `htop`

## Support

For issues or questions:
- Check application logs
- Review configuration files
- Consult FastAPI documentation: https://fastapi.tiangolo.com/
- Check Docker documentation: https://docs.docker.com/

