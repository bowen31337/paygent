# Docker Compose Setup Guide

This guide explains how to use Docker Compose to run the Paygent application with all dependencies.

## Prerequisites

- Docker 20.10+
- Docker Compose 2.0+

## Quick Start

### 1. Start All Services

```bash
docker-compose up -d
```

This will start:
- **PostgreSQL** on port 5432
- **Redis** on port 6379
- **FastAPI** application on port 8000

### 2. Check Service Status

```bash
docker-compose ps
```

All services should show as "healthy" after startup.

### 3. View Logs

```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f api
docker-compose logs -f postgres
docker-compose logs -f redis
```

### 4. Stop Services

```bash
docker-compose down
```

To remove volumes as well:
```bash
docker-compose down -v
```

## Services

### PostgreSQL

- **Port**: 5432
- **Database**: paygent
- **User**: paygent
- **Password**: paygent_dev_password
- **Health Check**: Runs every 10s

Connection string:
```
postgresql://paygent:paygent_dev_password@localhost:5432/paygent
```

### Redis

- **Port**: 6379
- **Persistence**: AOF enabled
- **Health Check**: Runs every 10s

Connection string:
```
redis://localhost:6379
```

### FastAPI Application

- **Port**: 8000
- **Health Check**: HTTP GET /health every 30s
- **Auto-restart**: Enabled

Endpoints:
- Health: http://localhost:8000/health
- API Docs: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Optional Tools

To start admin tools (database UI, Redis commander):

```bash
docker-compose --profile tools up -d
```

### Adminer (Database UI)

- **URL**: http://localhost:8080
- **Server**: postgres
- **Username**: paygent
- **Password**: paygent_dev_password
- **Database**: paygent

### Redis Commander

- **URL**: http://localhost:8081
- **Host**: redis
- **Port**: 6379

## Development Workflow

### Rebuild Application

After making code changes:

```bash
docker-compose up -d --build api
```

### Run Commands in Container

```bash
# Python shell
docker-compose exec api python

# Run tests
docker-compose exec api pytest

# Database migrations
docker-compose exec api alembic upgrade head
```

### View Database

```bash
docker-compose exec postgres psql -U paygent -d paygent
```

## Environment Variables

The API service uses these environment variables (see docker-compose.yml):

- `DATABASE_URL`: PostgreSQL connection string
- `REDIS_URL`: Redis connection string
- `CRONOS_RPC_URL`: Cronos RPC endpoint
- `X402_FACILITATOR_URL`: x402 facilitator URL
- `APP_ENV`: Environment (development)
- `LOG_LEVEL`: Logging level (INFO)

Add your API keys in `.env` or uncomment in docker-compose.yml:
- `ANTHROPIC_API_KEY`
- `OPENAI_API_KEY`

## Volumes

Data persists in named Docker volumes:
- `postgres_data`: PostgreSQL data
- `redis_data`: Redis AOF file

## Troubleshooting

### Services Not Starting

Check logs:
```bash
docker-compose logs
```

### Database Connection Errors

Ensure postgres is healthy:
```bash
docker-compose ps postgres
```

Wait for health check: `Status: healthy (health: starting)`

### Port Already in Use

Change ports in docker-compose.yml:
```yaml
services:
  postgres:
    ports:
      - "5433:5432"  # Use 5433 instead
```

### Reset Everything

⚠️ **This deletes all data**:

```bash
docker-compose down -v
docker-compose up -d
```

## Production Considerations

For production deployment:

1. Change default passwords in docker-compose.yml
2. Use Docker secrets for sensitive data
3. Enable SSL/TLS for database connections
4. Set resource limits on services
5. Use external managed database (e.g., Vercel Postgres)
6. Configure proper logging drivers
7. Set up monitoring and alerting

## Multi-Stage Build

The Dockerfile uses multi-stage builds:

1. **Builder stage**: Compiles dependencies
2. **Runtime stage**: Minimal image with only runtime dependencies

This results in a smaller production image.

## Health Checks

All services have health checks:

- PostgreSQL: `pg_isready`
- Redis: `redis-cli ping`
- API: HTTP GET /health

The API service waits for database and Redis to be healthy before starting.

## Next Steps

- See [README.md](../README.md) for general setup
- See [ARCHITECTURE.md](ARCHITECTURE.md) for system design
- See [API.md](API.md) for API documentation
