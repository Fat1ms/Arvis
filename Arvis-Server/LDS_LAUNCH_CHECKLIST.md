# 🚀 LDS MVP Launch Checklist

## Phase 1: Local Development (TODAY - 30 min)

### Prerequisites Check
- [ ] Python 3.11+ installed (`python --version`)
- [ ] Docker Desktop installed and running
- [ ] Docker Compose installed (`docker-compose --version`)
- [ ] Git installed (`git --version`)
- [ ] 8GB free disk space
- [ ] Port 5432 available (PostgreSQL)
- [ ] Port 6379 available (Redis)
- [ ] Port 8000 available (API)

### Local Setup
```bash
# 1. Install Python dependencies
pip install -r lds/requirements.txt

# 2. Start services (one-liner)
docker-compose up

# 3. Test API (in another terminal)
curl http://localhost:8000/health

# 4. Run integration tests
python test_lds_api.py

# Expected Result: ✅ All 10 endpoints working
```

### Validation
- [ ] Health check returns 200 OK
- [ ] PostgreSQL container is running
- [ ] Redis container is running
- [ ] API container is running
- [ ] All 10 endpoints respond correctly
- [ ] Test users created successfully
- [ ] Virtual credits deducted correctly
- [ ] Database contains transaction logs

**Estimated Time**: 15 minutes  
**Success Rate**: 95% (usually just pip install)

---

## Phase 2: Infrastructure Provisioning (WEEK 1)

### Choose Provider
- [ ] Evaluate OVH vs DigitalOcean vs AWS
  - **Recommendation**: OVH (€46/month, EU-based, transparent pricing)
  
### Create Accounts & Add Billing
- [ ] Create infrastructure provider account
- [ ] Add payment method
- [ ] Verify account

### Provision Resources

#### 1. Virtual Private Server (VPS)
```
OS: Ubuntu 22.04 LTS
CPU: 2 vCPU (Intel/AMD)
RAM: 4 GB
Storage: 40 GB SSD
Network: 100 Mbps
Price: €10/month

Expected Cost: €10/month
```

#### 2. PostgreSQL Managed Database
```
Version: PostgreSQL 15
Storage: 20 GB
Backups: Daily (7-day retention)
High Availability: No (MVP)
Replicas: 0
Price: €20/month

Expected Cost: €20/month
```

#### 3. Redis Managed Cache
```
Version: Redis 7
Memory: 1 GB
Persistence: RDB + AOF
Backups: Daily
Price: €10/month

Expected Cost: €10/month
```

#### 4. Domain & DNS
```
Domain: lds-api.arvis.cloud (via AWS Route53 or OVH)
DNS TTL: 300 seconds
A Record: points to VPS IP
Expected Cost: €6/month or €1/year

Total Infrastructure: €46/month
```

### Checklist
- [ ] VPS created and SSH accessible
- [ ] PostgreSQL connection string noted
- [ ] Redis connection string noted
- [ ] Domain registered
- [ ] DNS A record created (points to VPS IP)
- [ ] SSH key copied to VPS

**Estimated Time**: 1-2 hours  
**Cost**: €46/month

---

## Phase 3: TLS Certificate Setup (WEEK 1)

### Install Let's Encrypt Certificate
```bash
# SSH into VPS
ssh root@lds-api.arvis.cloud

# Install Certbot
sudo apt-get update
sudo apt-get install certbot

# Get certificate
sudo certbot certonly --standalone \
  -d lds-api.arvis.cloud \
  -m admin@arvis.cloud \
  --agree-tos

# Copy cert paths (for .env.production)
ls /etc/letsencrypt/live/lds-api.arvis.cloud/
# Should show: cert.pem, chain.pem, fullchain.pem, privkey.pem

# Setup auto-renewal (cron job)
sudo certbot renew --dry-run
```

### Verify Certificate
```bash
# Check certificate expiration
openssl s_client -connect lds-api.arvis.cloud:443 </dev/null | grep notAfter

# Expected: NOT_AFTER=2025-XX-XX
```

### Checklist
- [ ] Certificate obtained from Let's Encrypt
- [ ] Certificate paths noted:
  - CERT_PATH: `/etc/letsencrypt/live/lds-api.arvis.cloud/fullchain.pem`
  - KEY_PATH: `/etc/letsencrypt/live/lds-api.arvis.cloud/privkey.pem`
- [ ] Auto-renewal configured
- [ ] Certificate valid for 90 days
- [ ] Next renewal: Set calendar reminder (Day 80)

**Estimated Time**: 30 minutes  
**Cost**: Free (Let's Encrypt)

---

## Phase 4: Production Deployment (WEEK 1)

### Prepare Production Environment

#### 1. Clone Repository to VPS
```bash
ssh root@lds-api.arvis.cloud

# Clone repo
git clone https://github.com/your-org/Arvis.git /opt/arvis

# Navigate
cd /opt/arvis/Arvis-Server

# Install Docker & Docker Compose
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
```

#### 2. Create Production .env
```bash
# Copy production template
cp .env.production .env

# Edit with actual secrets
nano .env

# MUST update these:
# - DATABASE_URL (OVH PostgreSQL managed connection string)
# - REDIS_URL (OVH Redis managed connection string)
# - SECRET_KEY (generate: python -c "import secrets; print(secrets.token_urlsafe(32))")
# - CERT_PATH & KEY_PATH (Let's Encrypt paths)
# - CORS_ORIGINS (add your domain)
```

#### 3. Deploy Using Docker Compose
```bash
# Build and start
docker-compose -f docker-compose.prod.yml up -d

# (Note: Create docker-compose.prod.yml for production settings)

# Verify containers
docker-compose ps

# Expected output:
# lds-api: Running on port 8000
```

#### 4. Setup Reverse Proxy (Nginx)
```bash
# Install Nginx
sudo apt-get install nginx

# Create config
sudo nano /etc/nginx/sites-available/lds

# Paste:
server {
    listen 443 ssl http2;
    server_name lds-api.arvis.cloud;

    ssl_certificate /etc/letsencrypt/live/lds-api.arvis.cloud/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/lds-api.arvis.cloud/privkey.pem;

    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}

server {
    listen 80;
    server_name lds-api.arvis.cloud;
    return 301 https://$server_name$request_uri;
}

# Enable site
sudo ln -s /etc/nginx/sites-available/lds /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

#### 5. Initialize Database
```bash
# Run migrations
docker-compose exec api alembic upgrade head

# Verify schema created
docker-compose exec postgres psql -U arvis_lds -d arvis_lds \
  -c "SELECT table_name FROM information_schema.tables WHERE table_schema='public';"

# Expected: 8 tables (user, user_credits, credit_ledger, provider, provider_resources, task, audit_log)
```

### Checklist
- [ ] Repository cloned to /opt/arvis
- [ ] Docker installed on VPS
- [ ] .env.production created with real secrets
- [ ] Certificates in correct paths
- [ ] API container running (`docker-compose ps`)
- [ ] Nginx reverse proxy configured
- [ ] Database migrations applied
- [ ] 8 tables created in PostgreSQL

**Estimated Time**: 1-2 hours  
**Cost**: €0 (labor only)

---

## Phase 5: Production Validation (WEEK 1)

### Smoke Tests
```bash
# 1. Health check
curl https://lds-api.arvis.cloud/health

# Expected response:
# {
#   "status": "healthy",
#   "version": "0.1.0",
#   "database": "healthy",
#   "redis": "healthy"
# }

# 2. User registration
curl -X POST https://lds-api.arvis.cloud/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "TestPassword123!",
    "role": "consumer"
  }'

# 3. Task submission (use API key from registration)
curl -X POST https://lds-api.arvis.cloud/tasks/submit \
  -H "Authorization: Bearer sk_xxxxx..." \
  -H "Content-Type: application/json" \
  -d '{
    "llm_model": "mistral:7b",
    "prompt": "Hello world",
    "timeout_seconds": 300
  }'
```

### Performance Tests
```bash
# Response time check (should be <200ms)
time curl https://lds-api.arvis.cloud/health

# Load test (100 requests)
ab -n 100 -c 10 https://lds-api.arvis.cloud/health

# Expected: >500 requests/sec on 2vCPU
```

### Security Validation
```bash
# Check TLS version (should be 1.2+)
openssl s_client -connect lds-api.arvis.cloud:443 </dev/null | grep Protocol

# Check certificate
curl -vI https://lds-api.arvis.cloud/health 2>&1 | grep -i certificate
```

### Checklist
- [ ] Health check returns 200 OK with healthy status
- [ ] User registration works
- [ ] Task submission accepted
- [ ] Response time <200ms
- [ ] Load test passes >500 req/sec
- [ ] TLS 1.2+ enabled
- [ ] HTTPS redirects from HTTP
- [ ] No error logs on startup

**Estimated Time**: 30 minutes  
**Expected Outcome**: Production API live ✅

---

## Phase 6: Monitoring Setup (WEEK 2)

### Setup Prometheus & Grafana
```bash
# Add to docker-compose.yml:
# - prometheus:9090 service
# - grafana:3000 service

# Scrape config for Prometheus
# - FastAPI /metrics endpoint
# - PostgreSQL exporter
# - Redis exporter

# Grafana dashboard
# - Task throughput (tasks/min)
# - Provider uptime (%)
# - Error rates (%)
# - Credit ledger balance
```

### Checklist
- [ ] Prometheus scraping metrics
- [ ] Grafana dashboards created
- [ ] Alerts configured
  - [ ] >5% error rate → page
  - [ ] <90% uptime → warning
  - [ ] Database lag >1s → critical
- [ ] Monitoring accessible at https://lds-api.arvis.cloud:3000

**Estimated Time**: 2 hours  
**Cost**: €0 (open source)

---

## Phase 7: Beta Launch (WEEK 3-4)

### Pre-Launch Checklist
- [ ] Security audit completed
  - [ ] SQL injection testing
  - [ ] XSS testing
  - [ ] CSRF protection
  - [ ] Rate limit bypass
  - [ ] Container escape attempts
  - [ ] Privilege escalation
  - [ ] Data exposure review
  - [ ] DOS resistance
  - [ ] Authentication bypass

- [ ] Performance baseline established
  - [ ] Latency: p50 <50ms, p95 <200ms, p99 <500ms
  - [ ] Throughput: >1000 req/min sustained
  - [ ] Error rate: <0.1%
  - [ ] Uptime target: >99.5%

- [ ] Documentation complete
  - [ ] API docs (auto-generated at /docs)
  - [ ] Getting started guide
  - [ ] API reference
  - [ ] Troubleshooting guide
  - [ ] Architecture overview

- [ ] Support infrastructure ready
  - [ ] Email support (support@arvis.cloud)
  - [ ] Bug bounty program (if applicable)
  - [ ] Issue tracking (GitHub/Jira)
  - [ ] Runbooks for common issues

### Beta Tester Recruitment
- [ ] Prepare 50 beta tester invites
- [ ] Create sign-up link
- [ ] Send welcome email with:
  - [ ] API documentation link
  - [ ] Quick start guide
  - [ ] Support email
  - [ ] Feature request form
  - [ ] Bug report form

### Launch Announcement
```
Subject: 🚀 Arvis LDS MVP is LIVE!

Dear Community,

We're excited to announce the beta launch of Arvis Load Distribution System (LDS)!

🎯 What is LDS?
- Peer-to-peer distributed LLM marketplace
- Consumers: Submit tasks, get results
- Providers: Contribute resources, earn credits
- All FREE during MVP phase!

📊 Quick Stats:
- 10 API endpoints live
- Virtual credits system (1000 signup + 100/day)
- Support for: mistral:7b, gemma:2b, code-llama:34b
- PostgreSQL + Redis backed
- 99.5% uptime SLA

🚀 Get Started:
1. Visit: https://lds-api.arvis.cloud/docs
2. Register: https://lds-api.arvis.cloud/auth/register
3. Submit task: POST /tasks/submit
4. Check results: GET /tasks/{task_id}

📞 Support:
- Documentation: https://arvis.cloud/lds-docs
- Email: support@arvis.cloud
- GitHub: https://github.com/your-org/arvis

🐛 Report Issues:
- Bug: https://github.com/your-org/arvis/issues
- Feature Request: https://github.com/your-org/arvis/discussions

Thank you for being part of the Arvis journey!

Best regards,
Arvis Team
```

### Checklist
- [ ] Security audit signed off
- [ ] Performance baselines met
- [ ] Support email functional
- [ ] Beta testers invited (50+)
- [ ] Launch announcement sent
- [ ] Monitoring alerts active
- [ ] Incident response team briefed
- [ ] Database backups automated
- [ ] Rollback plan documented

**Estimated Time**: 1 day  
**Success Criteria**: 
- ✅ 0 critical security issues
- ✅ >99% uptime on first week
- ✅ <100ms p95 latency
- ✅ 50+ beta testers engaged
- ✅ 0 user-blocking issues

---

## Rollback Plan (Emergency)

**If API fails, immediate actions:**

1. Check API logs
```bash
docker-compose logs api | tail -100
```

2. Restart API
```bash
docker-compose restart api
```

3. Check database connection
```bash
docker-compose exec postgres pg_isready
```

4. Restart everything
```bash
docker-compose down
docker-compose up -d
```

5. Check backups exist
```bash
# Recent backup should be <1 hour old
ls -lh /backups/postgresql/
ls -lh /backups/redis/
```

6. If all fails, rollback to previous version
```bash
git revert HEAD
docker-compose build --no-cache
docker-compose up -d
```

---

## Success Criteria for MVP Launch

✅ **Functionality**
- All 10 endpoints working
- User registration flow complete
- Task submission & tracking working
- Provider resource management working

✅ **Performance**
- p95 latency <200ms
- Throughput >1000 req/min
- Error rate <0.5%

✅ **Security**
- Zero CRITICAL vulnerabilities
- All user passwords bcrypt-hashed
- JWT tokens valid
- Rate limiting enforced

✅ **Reliability**
- 99%+ uptime
- Database backups working
- Logs aggregated
- Alerts configured

✅ **Documentation**
- API docs complete
- Getting started guide
- Troubleshooting guide
- Architecture docs

---

## Timeline Summary

| Phase | Tasks | Timeline | Status |
|-------|-------|----------|--------|
| 1. Local Dev | Setup, tests | TODAY | ✅ Complete |
| 2. Infrastructure | VPS, DB, Redis | Week 1 Day 1-2 | 🔄 Start today |
| 3. TLS Certs | Let's Encrypt | Week 1 Day 3 | 🔄 After infra |
| 4. Deployment | Docker, Nginx | Week 1 Day 4-5 | 🔄 After TLS |
| 5. Validation | Smoke tests | Week 1 Day 6 | 🔄 After deploy |
| 6. Monitoring | Prometheus, Grafana | Week 2 | 📋 Planned |
| 7. Security Audit | Pen testing | Week 3 | 📋 Planned |
| 8. Beta Launch | 50 testers | Week 4 | 📋 Planned |

**Total Time to Launch**: 4 weeks ⏰

---

## Resources & Contact

- **Documentation**: See `LDS_DOCUMENTATION_INDEX.md`
- **API Reference**: Auto-generated at `/docs` after deployment
- **GitHub**: (add your repository URL)
- **Support Email**: support@arvis.cloud
- **On-Call**: (add your team)

---

**Status**: Ready to launch 🚀  
**Last Updated**: January 2024  
**Next Review**: After infrastructure provisioning

---

✅ **All systems go! Execute this checklist in order. Expected launch: 4 weeks from start date.**
