# Arvis Server

**Status**: MVP Phase 🚀 (LDS Load Distribution System in active development)

This repository contains two major components:

## 1. 🆕 LDS (Load Distribution System) - IN DEVELOPMENT

**What**: Peer-to-peer distributed LLM marketplace allowing consumers to submit tasks and providers to contribute computing resources.

**Status**: MVP implementation complete ✅
- ✅ 10 API endpoints live (auth + consumer + provider)
- ✅ Database schema designed (8 tables, PostgreSQL ready)
- ✅ Virtual credits system (1000 signup + 100/day)
- ✅ Security implementation (JWT + bcrypt + validation)
- ✅ Docker containers (API + executor + compose stack)
- 🔄 Infrastructure provisioning (Week 1)
- 📋 Security hardening (Week 2-3)
- 📋 Beta launch (Week 4)

**Quick Start**:
```bash
cd Arvis-Server

# Local development
docker-compose up
python test_lds_api.py  # Verify all endpoints

# Read full guide
cat lds/README.md
```

**Documentation**:
- [`lds/README.md`](./lds/README.md) - Complete developer guide (400+ lines)
- [`LDS_DOCUMENTATION_INDEX.md`](./LDS_DOCUMENTATION_INDEX.md) - All docs index
- [`LDS_IMPLEMENTATION_STATUS.md`](./LDS_IMPLEMENTATION_STATUS.md) - Progress tracking
- [`LDS_SESSION_LOG.md`](./LDS_SESSION_LOG.md) - Development log
- [`LDS_LAUNCH_CHECKLIST.md`](./LDS_LAUNCH_CHECKLIST.md) - Launch steps

**Architecture**:
```
FastAPI (async Python)
├── PostgreSQL (user, tasks, credits)
├── Redis (caching, rate limiting)
└── Docker Executor (isolated task execution)

Virtual Credits: 1000 signup + 100/day (free MVP)
Supported Models: mistral:7b, gemma:2b, code-llama:34b
Security: JWT + bcrypt + input validation + container sandboxing
```

**API Endpoints** (10 total):
- `POST /auth/register` - User signup
- `GET /health` - System health
- `POST /tasks/submit` - Consumer: submit task
- `GET /tasks/{task_id}` - Consumer: check result
- `GET /account/balance` - Consumer: view credits
- `GET /account/transactions` - Consumer: history
- `POST /providers/register-resources` - Provider: declare capacity
- `POST /providers/heartbeat` - Provider: send alive signal
- `GET /providers/tasks/next` - Provider: get next task
- `POST /providers/tasks/{task_id}/result` - Provider: submit result

**For Infrastructure Setup**:
→ See [`LDS_LAUNCH_CHECKLIST.md`](./LDS_LAUNCH_CHECKLIST.md) (4-week timeline)

---

## 2. 📡 Legacy Authentication Server

**Status**: Existing infrastructure (being superseded by LDS)

Original features:
- JWT-based authentication
- User management (CRUD)
- 2FA support (TOTP)
- RBAC (Role-Based Access Control)

---

## Quick Navigation

| Need | File |
|------|------|
| 📖 Complete API guide | [`lds/README.md`](./lds/README.md) |
| 🚀 Launch checklist | [`LDS_LAUNCH_CHECKLIST.md`](./LDS_LAUNCH_CHECKLIST.md) |
| 📊 Progress tracking | [`LDS_IMPLEMENTATION_STATUS.md`](./LDS_IMPLEMENTATION_STATUS.md) |
| 📚 All documentation | [`LDS_DOCUMENTATION_INDEX.md`](./LDS_DOCUMENTATION_INDEX.md) |
| 🛠️ Development log | [`LDS_SESSION_LOG.md`](./LDS_SESSION_LOG.md) |
| 🧪 Test the API | `python test_lds_api.py` |
| ⚙️ Configuration | `.env.development` or `.env.production` |

---

## Technology Stack

**Backend**: FastAPI 0.104.1 (async Python)  
**Database**: PostgreSQL 15 + SQLAlchemy ORM  
**Cache**: Redis 7 (rate limiting, task queue)  
**Auth**: JWT (python-jose) + bcrypt (passlib)  
**Validation**: Pydantic 2.5.0  
**Containers**: Docker + docker-compose  
**Migrations**: Alembic

---

## Development Workflow

### 1️⃣ Local Setup (15 min)
```bash
# Install dependencies
pip install -r lds/requirements.txt

# Start all services (PostgreSQL + Redis + API)
docker-compose up

# Test endpoints
python test_lds_api.py
```

### 2️⃣ Make Changes
```bash
# Edit files in lds/ - auto-reload enabled in dev mode
# curl http://localhost:8000/docs to test

# View logs
docker-compose logs -f api
```

### 3️⃣ Database Changes
```bash
# Create migration
docker-compose exec api alembic revision --autogenerate -m "your message"

# Apply migration
docker-compose exec api alembic upgrade head
```

### 4️⃣ Deploy
```bash
# See LDS_LAUNCH_CHECKLIST.md for production steps
# Infrastructure provisioning needed first
```

---

## Directory Structure

```
Arvis-Server/
├── lds/                          # Load Distribution System (MAIN)
│   ├── config/                   # Settings, database config
│   ├── models/                   # Pydantic schemas + SQLAlchemy ORM
│   ├── services/                 # Security, validation, business logic
│   ├── api/routes/               # API endpoints (providers, consumers)
│   ├── executor/                 # Sandboxed task execution
│   ├── migrations/               # Alembic database migrations
│   ├── main.py                   # FastAPI application
│   ├── requirements.txt          # Python dependencies
│   └── README.md                 # Full developer guide
│
├── docker-compose.yml            # PostgreSQL + Redis + API stack
├── Dockerfile.api                # API server container
├── .env.development              # Dev configuration
├── .env.production               # Prod secrets template
├── test_lds_api.py              # Integration tests
│
├── LDS_DOCUMENTATION_INDEX.md    # Documentation map
├── LDS_IMPLEMENTATION_STATUS.md  # Progress & checklist
├── LDS_SESSION_LOG.md            # Development log
├── LDS_LAUNCH_CHECKLIST.md       # 4-week launch plan
│
├── start-lds.sh                  # Linux quick start
├── start-lds.bat                 # Windows quick start
│
└── (legacy files...)             # Original auth server
```

---

## Security

**MVP Security Model** (4 layers):

1. **Input Validation** ✅
   - 10KB prompt limit
   - Model whitelist enforcement
   - Blacklist patterns (rm -rf, fork(), etc.)

2. **Authentication** ✅
   - JWT tokens (7-day expiration)
   - bcrypt password hashing (12 rounds)
   - API key generation (sk_xxxxx format)

3. **Rate Limiting** ✅
   - Redis-based: 10 tasks/minute per user
   - Daily bonus once per 24 hours

4. **Container Sandboxing** 🔄
   - cgroups: 2GB RAM, 1 CPU core limit
   - seccomp: Whitelist safe syscalls (Week 3)
   - Non-root user execution

**Plan**: Full security audit in Week 3 before beta launch.

---

## Infrastructure Costs

| Component | Provider | Cost |
|-----------|----------|------|
| VPS (2vCPU, 4GB RAM) | OVH | €10/month |
| PostgreSQL (20GB managed) | OVH | €20/month |
| Redis (1GB managed) | OVH | €10/month |
| Domain (1 year) | Route53/OVH | €6/year |
| **TOTAL** | | **€46/month** |

All resources free during MVP (virtual credits only, no real payments).

---

## Testing

### Unit Tests
```bash
docker-compose exec api pytest tests/ --cov=lds
```

### Integration Tests
```bash
# All 10 endpoints + full workflow
python test_lds_api.py
```

### Load Testing
```bash
# 100 concurrent requests
ab -n 1000 -c 100 http://localhost:8000/health
```

---

## Performance Targets

| Metric | Target | Current |
|--------|--------|---------|
| Latency (p95) | <200ms | TBD (local) |
| Throughput | >1000 req/min | TBD (local) |
| Uptime | 99.5% | TBD (prod) |
| Error Rate | <0.5% | TBD (prod) |

**Note**: Local development on Docker may not reflect production performance.

---

## Troubleshooting

**Port already in use?**
```bash
# Check what's using port 8000
netstat -tulpn | grep 8000

# Change port in docker-compose.yml
```

**Database connection error?**
```bash
# Wait for PostgreSQL to start
docker-compose up postgres
sleep 10
docker-compose up
```

**Redis auth error?**
```bash
# Verify REDIS_URL in .env matches docker-compose password
REDIS_URL=redis://:password@redis:6379/0
```

See [`lds/README.md`](./lds/README.md) for more troubleshooting.

---

## Next Steps

### Today
1. Run: `docker-compose up`
2. Test: `python test_lds_api.py`
3. Read: [`lds/README.md`](./lds/README.md)

### This Week
1. Choose infrastructure provider (recommend OVH)
2. Provision VPS + PostgreSQL + Redis
3. Setup TLS certificate
4. Deploy to production

### This Month
1. Implement cgroups + seccomp hardening
2. Setup Prometheus monitoring
3. Security audit
4. Invite beta testers

**Expected Launch**: 4 weeks from infrastructure provisioning start

---

## Documentation

- **API Docs**: Auto-generated at `http://localhost:8000/docs` (Swagger UI)
- **Getting Started**: [`lds/README.md`](./lds/README.md)
- **Full Index**: [`LDS_DOCUMENTATION_INDEX.md`](./LDS_DOCUMENTATION_INDEX.md)
- **Progress**: [`LDS_IMPLEMENTATION_STATUS.md`](./LDS_IMPLEMENTATION_STATUS.md)
- **Launch Guide**: [`LDS_LAUNCH_CHECKLIST.md`](./LDS_LAUNCH_CHECKLIST.md)

---

## Project Status

**Phase 1 - Core Infrastructure**: ✅ 100% Complete
- Backend API: ✅ 10 endpoints
- Database: ✅ 8 tables, schema
- Security: ✅ Layer 1-3 (4 in progress)
- Documentation: ✅ Comprehensive

**Phase 2 - Infrastructure & TLS**: 🔄 Starting Week 1
- VPS provisioning: ⏳ Pending
- Database setup: ⏳ Pending
- TLS certificates: ⏳ Pending

**Phase 3 - Security Hardening**: 📋 Planned Week 2-3
- cgroups implementation: ⏳ Pending
- seccomp filtering: ⏳ Pending
- Security audit: ⏳ Pending

**Phase 4 - Monitoring & Launch**: 📋 Planned Week 4
- Prometheus + Grafana: ⏳ Pending
- Beta testing: ⏳ Pending
- Production launch: ⏳ Pending

---

## Support

- **Documentation**: See files listed above
- **Issues**: https://github.com/your-org/arvis/issues
- **Discussions**: https://github.com/your-org/arvis/discussions
- **Email**: support@arvis.cloud

---

## License

MIT

---

**Status**: MVP Implementation Active 🚀  
**Last Updated**: January 2024  
**Next Milestone**: Infrastructure provisioning (Week 1)

---

👉 **[START HERE: Read `lds/README.md` →](./lds/README.md)**
