# Arvis Load Distribution System (LDS) - MVP Implementation

## Overview

LDS is a peer-to-peer distributed LLM marketplace that allows:
- **Consumers**: Submit LLM tasks (prompts) and get results back
- **Providers**: Contribute computing resources and earn virtual credits
- **All users**: Get FREE resources during MVP phase (no real money yet)

## Quick Start (Development)

### Prerequisites

- Docker & Docker Compose
- Python 3.11+ (for local development without Docker)
- Git

### 1. Clone and Setup

```bash
cd Arvis-Server

# Create environment file
cp .env.development .env

# Install dependencies (optional, Docker does this)
pip install -r lds/requirements.txt
```

### 2. Start Services with Docker Compose

```bash
# Start PostgreSQL, Redis, and FastAPI
docker-compose up --build

# In another terminal, initialize database
docker-compose exec api alembic upgrade head

# Verify health check
curl http://localhost:8000/health
```

### 3. Test API Endpoints

#### Register as Consumer
```bash
curl -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "consumer@example.com",
    "password": "secure_password",
    "role": "consumer"
  }'
```

Response (save the `api_key`):
```json
{
  "user_id": "uuid-here",
  "email": "consumer@example.com",
  "api_key": "sk_xxx...",
  "virtual_credits": 1000,
  "message": "Welcome! You got 1000 virtual credits..."
}
```

#### Submit Task (Consumer)
```bash
export CONSUMER_API_KEY="sk_xxx..."

curl -X POST http://localhost:8000/tasks/submit \
  -H "Authorization: Bearer $CONSUMER_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "llm_model": "mistral:7b",
    "prompt": "What is machine learning?",
    "timeout_seconds": 300,
    "priority": "normal"
  }'
```

#### Register as Provider
```bash
curl -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "provider@example.com",
    "password": "secure_password",
    "role": "provider"
  }'
```

#### Provider: Register Resources
```bash
export PROVIDER_API_KEY="sk_xxx..."

curl -X POST http://localhost:8000/providers/register-resources \
  -H "Authorization: Bearer $PROVIDER_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "ram_gb": 8,
    "cpu_cores": 4,
    "gpu_available": true
  }'
```

#### Provider: Send Heartbeat
```bash
curl -X POST http://localhost:8000/providers/heartbeat \
  -H "Authorization: Bearer $PROVIDER_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "ram_used_mb": 2048,
    "cpu_percent": 45.5,
    "gpu_percent": 60.0,
    "available": true
  }'
```

## Architecture

```
┌─────────────────────────────────────────────────┐
│           Load Distribution System (LDS)        │
├─────────────────────────────────────────────────┤
│                  FastAPI Server                 │
│  ┌──────────────────────────────────────────┐  │
│  │  /health       (monitoring)              │  │
│  │  /auth/register (user signup)            │  │
│  │  /tasks/* (consumer - submit/query tasks)│  │
│  │  /providers/* (provider - work + earn)   │  │
│  └──────────────────────────────────────────┘  │
├─────────────────────────────────────────────────┤
│              Data Layer                         │
│  ┌─────────────────┐  ┌─────────────────────┐ │
│  │  PostgreSQL     │  │  Redis (caching,   │ │
│  │  - Users        │  │  rate limiting)     │ │
│  │  - Tasks        │  └─────────────────────┘ │
│  │  - Credits      │                          │
│  │  - Audit Logs   │                          │
│  └─────────────────┘                          │
├─────────────────────────────────────────────────┤
│           Docker Executor (Sandboxed)          │
│  - Runs LLM tasks in isolated containers       │
│  - cgroups: 2GB RAM, 1 CPU core limit          │
│  - seccomp: whitelist safe syscalls only       │
└─────────────────────────────────────────────────┘
```

## Project Structure

```
lds/
├── config/
│   ├── settings.py       # Configuration (environment vars)
│   └── database.py       # SQLAlchemy setup
├── models/
│   ├── schemas.py        # Pydantic request/response models
│   └── database.py       # SQLAlchemy ORM models
├── services/
│   ├── security.py       # JWT, bcrypt, crypto
│   └── validators.py     # Input validation, rate limiting
├── api/
│   └── routes/
│       ├── providers.py   # Provider endpoints
│       └── consumers.py   # Consumer endpoints
├── executor/
│   ├── Dockerfile        # Task execution container
│   └── executor.py       # Task execution logic
├── migrations/           # Alembic database migrations
├── main.py               # FastAPI application entry point
└── requirements.txt      # Python dependencies
```

## Database Schema

**Tables:**
- `user` - Users (consumers/providers)
- `user_credits` - Virtual credit balance per user
- `credit_ledger` - Transaction history (audit trail)
- `provider` - Provider metadata + reputation
- `provider_resources` - Real-time resource metrics
- `task` - Task queue (pending → completed)
- `audit_log` - Security audit trail

## Security Layers

1. **Authentication**: JWT tokens + bcrypt password hashing
2. **Input Validation**: Prompt length limits, model whitelist, blacklist patterns
3. **Rate Limiting**: Redis-based, 10 tasks/minute per user
4. **Container Isolation**:
   - cgroups: RAM/CPU limits
   - seccomp: Restrict dangerous syscalls
   - Non-root user execution
5. **Audit Logging**: All actions recorded with actor_id + timestamp

## Development Workflow

### 1. Making Code Changes

```bash
# Code is auto-reloaded in development (hot reload enabled)
# Edit files in lds/ and changes apply immediately
```

### 2. Running Tests

```bash
# Run all tests
docker-compose exec api pytest

# Run specific test file
docker-compose exec api pytest tests/test_auth.py

# With coverage
docker-compose exec api pytest --cov=lds tests/
```

### 3. Database Migrations

```bash
# Create new migration (after changing models)
docker-compose exec api alembic revision --autogenerate -m "Add new field"

# Apply migrations
docker-compose exec api alembic upgrade head

# Revert last migration
docker-compose exec api alembic downgrade -1
```

### 4. Accessing Database

```bash
# Connect to PostgreSQL
docker-compose exec postgres psql -U arvis_lds -d arvis_lds

# Common queries
SELECT * FROM "user";
SELECT * FROM task WHERE status = 'pending';
SELECT * FROM credit_ledger ORDER BY created_at DESC LIMIT 10;
```

## Virtual Credits System (MVP Phase)

**All resources are FREE:**

- **Signup Bonus**: 1000 credits (enough for ~20 mistral:7b queries)
- **Daily Bonus**: 100 credits/day (automatic, resets daily)
- **Provider Earnings**: Credits for each task completed
- **No Real Money**: MVP only uses virtual credits, no payments

**Cost Structure:**
- mistral:7b: 50 credits/task
- gemma:2b: 20 credits/task
- code-llama:34b: 100 credits/task
- Length factor: +10% per 1000 chars above base
- Urgency factor: 1.5x for <60s timeout, 0.8x for >300s

## Monitoring

### Health Check
```bash
curl http://localhost:8000/health
# Returns: status, database health, Redis health, version
```

### Logs
```bash
docker-compose logs -f api      # API logs
docker-compose logs -f postgres # Database logs
docker-compose logs -f redis    # Cache logs
```

## Week 1-4 Roadmap

**Week 1: Infrastructure** (done in docker-compose, skip for MVP local dev)
- Provision VPS, PostgreSQL, Redis
- Setup TLS certificates
- Configure DNS

**Week 2: Endpoints + Docker**
- Finish remaining endpoints ✅
- Build executor Docker image ✅
- Test resource limits

**Week 3: Security Hardening**
- Implement seccomp profile
- Test attack scenarios
- Add input validation integration

**Week 4: Monitoring + Go Live**
- Setup Prometheus + Grafana
- Create dashboards
- Beta invite

## API Endpoints Summary

### Authentication
- `POST /auth/register` - Create user account

### Consumer
- `POST /tasks/submit` - Submit task for processing
- `GET /tasks/{task_id}` - Get task status
- `GET /account/balance` - Get credit balance
- `GET /account/transactions` - View transaction history

### Provider
- `POST /providers/register-resources` - Declare available resources
- `POST /providers/heartbeat` - Send alive signal + metrics
- `GET /providers/tasks/next` - Get next task to execute
- `POST /providers/tasks/{task_id}/result` - Submit task result
- `GET /providers/earnings` - View earnings summary

### Monitoring
- `GET /health` - System health check

## Troubleshooting

**Port 8000 already in use:**
```bash
# Change port in docker-compose.yml or .env
docker-compose up -p 8001
```

**PostgreSQL connection refused:**
```bash
# Wait for database to start
docker-compose up postgres

# In another terminal, create database
docker-compose exec postgres createdb -U arvis_lds arvis_lds
```

**Redis auth error:**
```bash
# Ensure REDIS_URL in .env matches docker-compose
# Should be: redis://:password@redis:6379/0
```

## Next Steps

1. **For Local Testing**: Run `docker-compose up` and test endpoints above
2. **For Production**: 
   - Update .env with real infrastructure URLs
   - Generate TLS certificates via Let's Encrypt
   - Run alembic migrations
   - Deploy with Docker/Kubernetes
3. **For Integration**: Add to Arvis-Client as Provider Mode or Consumer Mode

## Resources

- [FastAPI Docs](https://fastapi.tiangolo.com/)
- [SQLAlchemy Docs](https://docs.sqlalchemy.org/)
- [Pydantic Docs](https://docs.pydantic.dev/)
- [Alembic Docs](https://alembic.sqlalchemy.org/)
- [Redis Docs](https://redis.io/commands/)

---

**Status**: MVP Phase 1 🚀
**Last Updated**: 2024
**Contact**: Arvis Team
