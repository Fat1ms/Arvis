# 🔐 LDS MVP: Приоритет - Безопасность и Запуск

---

## ЧАСТЬ 1: SECURITY FIRST - КРИТИЧЕСКИЕ ТРЕБОВАНИЯ

### 1.1 Угрозы MVP и как их нейтрализовать

```
🔴 КРИТИЧЕСКИЙ РИСК #1: Malicious Code Execution
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Сценарий:
  Злоумышленник-провайдер выполняет вредоносный код
  через LLM модель (например, rm -rf / вместо результата)

МВП ЗАЩИТА (достаточно для запуска):

✅ СЛОЙ 1: Container Sandboxing (Docker)
   └─ Каждая задача в НОВОМ контейнере (не переиспользуемом)
   └─ Контейнер уничтожается после выполнения
   └─ User namespace: контейнер не видит хост
   └─ Network namespace: нет доступа в интернет (сеть изолирована)
   └─ Mount namespace: read-only /usr, /lib, /bin
   
✅ СЛОЙ 2: Resource Limits (cgroups)
   └─ Максимум CPU: 1 core (можно увеличить до выделенного)
   └─ Максимум RAM: 2GB (жёсткий лимит, no swap)
   └─ Timeout: 5 минут максимум (SIGKILL потом)
   └─ Disk: Нет доступа кроме /tmp (10MB max)
   
✅ СЛОЙ 3: Syscall Filtering (seccomp - базовый)
   └─ Запретить: fork(), execve(), system(), ptrace()
   └─ Запретить: socket(), bind(), connect() (network)
   └─ Запретить: open() с write на / (root fs)
   └─ Разрешить: read(), write(), mmap(), brk(), exit() и еще ~50
   
✅ СЛОЙ 4: Input Validation
   └─ Проверить prompt на длину (макс 10KB)
   └─ Проверить prompt на опасные паттерны (regex blacklist)
   └─ Проверить модель на whitelist (только одобренные модели)
   
✅ СЛОЙ 5: Monitoring & Audit
   └─ Логировать ВСЕ запросы
   └─ Логировать результаты
   └─ Логировать resource usage во время выполнения
   └─ Alert на anomalies (>1000 CPU %, timeout, error)

IMPLEMENTATION PRIORITY:
  [НЕДЕЛЯ 1] Слой 1 + Слой 2 (Docker + cgroups)
  [НЕДЕЛЯ 2] Слой 3 (seccomp базовый)
  [НЕДЕЛЯ 3] Слой 4 + 5 (validation + monitoring)
```

```
🔴 КРИТИЧЕСКИЙ РИСК #2: Provider Resource Theft
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Сценарий:
  Провайдер выделяет 4GB RAM, но на самом деле
  использует 8GB (скрытое криптомайнинг или майнинг)

МВП ЗАЩИТА:

✅ СЛОЙ 1: Heartbeat с Resource Reporting
   └─ Provider отправляет метрики каждые 30 сек
   └─ Metrics: CPU %, RAM used MB, disk I/O
   └─ Server проверяет: используемые < выделенные + 5%
   └─ Если превышение: отключить провайдера сразу
   
✅ СЛОЙ 2: Server-side Monitoring (без доверия провайдеру)
   └─ Server пингует провайдера каждые 30 сек
   └─ Если нет ответа > 2 минуты: отключить
   └─ Server отслеживает КОГДА провайдер активен
   └─ Если активен ≥99% времени: подозрение на bot
   
✅ СЛОЙ 3: Billing Audit
   └─ Провайдер не может просто выставить счет
   └─ Для каждой задачи: request → execution → result
   └─ Задача должна быть "подтверждена" потребителем
   └─ Если потребитель говорит "результат неправильный":
      → Отменить платеж провайдеру
      → Штраф на репутацию -0.5
   
✅ СЛОЙ 4: Reputation Slashing
   └─ Первое подозрение на overuse: -0.3 репутации
   └─ Второе подозрение: -0.5 репутации
   └─ Третье подозрение: Автобан на 30 дней
   
IMPLEMENTATION:
  [НЕДЕЛЯ 1] Heartbeat protocol (client отправляет метрики)
  [НЕДЕЛЯ 2] Server validation logic (проверяем метрики)
  [НЕДЕЛЯ 3] Audit trail (логируем все task → result)
  [НЕДЕЛЯ 4] Reputation penalties (автоматические штрафы)
```

```
🟡 СРЕДНИЙ РИСК #3: Data Privacy Leakage
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Сценарий:
  Провайдер сохраняет копию приватного запроса
  потребителя после выполнения задачи

МВП ЗАЩИТА:

✅ СЛОЙ 1: Task Isolation
   └─ Контейнер уничтожается после выполнения
   └─ Никаких файлов не сохраняется на диск провайдера
   └─ Результат отправляется напрямую серверу (не в файл)
   
✅ СЛОЙ 2: TLS Encryption in Transit
   └─ Все соединения: TLS 1.3+
   └─ Certificate pinning (провайдер проверяет сертификат сервера)
   └─ No MITM attacks возможны
   
✅ СЛОЙ 3: Legal & NDA
   └─ Provider подписывает NDA (Non-Disclosure Agreement)
   └─ При подозрении на утечку: судебное разбирательство
   └─ Штраф в контракте (escrow account может применить)
   
✅ СЛОЙ 4: Audit Logging
   └─ Логировать: кто получил доступ к каким данным
   └─ User может скачать logs и проверить
   └─ Соответствие GDPR (Article 32 - data security)

IMPLEMENTATION:
  [НЕДЕЛЯ 1] TLS for all connections
  [НЕДЕЛЯ 2] Container cleanup (delete after task)
  [НЕДЕЛЯ 3] NDA in legal docs
  [WEEK 4] Audit logging
```

```
🟡 СРЕДНИЙ РИСК #4: Task Fraud / Denial of Service
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Сценарий:
  Консьюмер отправляет 1000 пустых задач за 1 сек
  Система перегружена, провайдеры стоят в простое

МВП ЗАЩИТА:

✅ СЛОЙ 1: Pre-Credit Allocation
   └─ Consumer должен ИМЕТЬ кредиты ДО отправки задачи
   └─ Кредиты зарезервированы (blocked) в момент submit
   └─ Если не хватает → Error 402 Payment Required
   └─ При отмене задачи: кредиты возвращаются
   
✅ СЛОЙ 2: Rate Limiting per User
   └─ Free tier: 10 tasks/minute max
   └─ Pro tier: 100 tasks/minute max
   └─ IP-based backup limit: 1000 req/minute per IP
   └─ Превышение: 429 Too Many Requests на 1 час
   
✅ СЛОЙ 3: Task Validation
   └─ Проверить синтаксис prompt перед queue
   └─ Проверить на spam patterns (повторяющиеся символы, etc)
   └─ Checksum/hash: детект дубликатов
   └─ Отклонить явно пустые/невалидные задачи
   
✅ СЛОЙ 4: Adaptive Queue
   └─ Если queue > 10,000 tasks: начать отклонять новые
   └─ Если средняя очередь ждет > 1 часа: отклонять new
   └─ Очистить старые tasks (>6 часов в очереди)

IMPLEMENTATION:
  [НЕДЕЛЯ 1] Pre-credit validation + Rate limiting
  [НЕДЕЛЯ 2] Task validation (syntax check)
  [НЕДЕЛЯ 3] Queue management + backpressure
```

```
🟢 НИЗКИЙ РИСК #5: Provider Fraud / Dispute
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Сценарий:
  Провайдер претендует что выполнил задачу,
  но результат некачественный или полностью фальшивый

МВП ЗАЩИТА (базовая):

✅ СЛОЙ 1: Cryptographic Proof (простой вариант)
   └─ Каждая задача: SHA256(request + timestamp)
   └─ Provider подписывает результат: signature
   └─ Server проверяет подпись
   └─ Результат не может быть изменен потом
   
✅ СЛОЙ 2: Consumer Rating
   └─ After task completion: потребитель может оценить
   └─ Rating 1-5 звезд
   └─ Если < 3 звезды: автоматически создать dispute
   
✅ СЛОЙ 3: Manual Dispute Resolution (MVP)
   └─ Консьюмер открывает dispute: "результат неправильный"
   └─ Admin вручную проверяет (сначала это вы)
   └─ Решение: refund потребителю или pay провайдеру
   └─ Логировать все решения
   
✅ СЛОЙ 4: Reputation Impact
   └─ Низкие rating → отключение от высокооплачиваемых задач
   └─ Повторные disputes → бан на 7 дней
   └─ Много бана → permanent removal

IMPLEMENTATION:
  [НЕДЕЛЯ 2] Rating system
  [НЕДЕЛЯ 3] Manual dispute process
  [НЕДЕЛЯ 4] Reputation penalties
```

---

## ЧАСТЬ 2: MVP SECURITY CHECKLIST

### Week 1: Docker + TLS Hardening

```
BACKEND SETUP:
☐ Select infrastructure provider (AWS/GCP/OVH)
  Рекомендация: OVH (EU, GDPR-friendly, cheaper than AWS)
  
☐ Setup PostgreSQL + Redis (managed service)
  PostgreSQL with SSL/TLS
  Redis with requirepass (authentication)
  
☐ Install Docker Runtime on server
  Docker version: 24.0+
  Verify: docker --version
  
☐ Create base executor image
  FROM python:3.11-slim
  Install only: pip, Python libs
  Remove: apt-get, compiler, shell utils
  
☐ Setup TLS certificates
  Get from Let's Encrypt (certbot)
  Auto-renewal (certbot timer)
  Nginx reverse proxy with TLS 1.3+

CLIENT SETUP:
☐ Update Arvis-Client to use HTTPS only
  No HTTP fallback for task submission
  Certificate pinning (optional for MVP)
  
☐ API Key authentication
  Generate random API keys (32 chars, base64)
  Send in header: X-API-Key: sk_xxxxxx
  Hash keys in database (bcrypt)

TESTING:
☐ Test: curl -X GET https://api.arvis.local/health
  Response: 200 OK, {"status": "ok"}
  
☐ Test: Task submission fails without API key
  Response: 401 Unauthorized
  
☐ Test: Invalid certificate in browser
  Show security warning (as expected)
```

### Week 2: Container Isolation + cgroups

```
DOCKER CONFIGURATION:
☐ Create executor-container with restrictions

  Dockerfile:
  ────────────────────────────────
  FROM python:3.11-slim
  
  # No shell, no package manager
  RUN rm -rf /bin/sh /bin/bash /usr/bin/apt-get
  
  # Non-root user
  RUN useradd -m -u 1000 executor
  USER executor
  
  WORKDIR /app
  
  # Copy only necessary files
  COPY requirements.txt .
  RUN pip install --no-cache-dir -r requirements.txt
  
  COPY executor.py .
  
  # No shell, just Python
  ENTRYPOINT ["python", "-u", "executor.py"]
  ────────────────────────────────

☐ Docker run command with resource limits

  docker run \
    --rm \                              # Auto-remove after exit
    --memory=2g \                       # Max 2GB RAM
    --memswap=2g \                      # No swap
    --cpus=1 \                          # Max 1 CPU core
    --cpu-quota=100000 \                # Strict limit
    --pids-limit=10 \                   # Max 10 processes
    --read-only \                       # Read-only root
    --tmpfs /tmp:size=100m \            # Temp space 100MB
    --network=none \                    # No network
    -e TASK_ID=12345 \
    -e TASK_TIMEOUT=300 \
    arvis/executor:latest
  
☐ Test: Container exceeds memory limit
  Task should be killed with OOMKilled
  Verify: docker inspect <container> → OOMKilled: true
  
☐ Test: Container tries network access
  Should fail (network=none)
  Verify: ping google.com → error
  
☐ Test: Container tries to write to /
  Should fail (read-only)
  Verify: echo "test" > /root/test.txt → Permission denied

MONITORING:
☐ Add resource monitoring during task execution
  Every 100ms: check cgroup memory/cpu usage
  If exceeds limit by >5%: kill container
  Log: "Container exceeded resource limit"
```

### Week 3: Seccomp + Input Validation

```
SECCOMP PROFILE (restricted syscalls):

☐ Create seccomp.json with whitelist

  Basic allowed syscalls:
    read, write, open, close, stat, fstat
    mmap, mprotect, munmap, brk
    rt_sigaction, rt_sigprocmask, sigaltstack
    exit, exit_group, gettimeofday, time
    getpid, getuid, getgid, getppid
    futex, poll, epoll_wait, nanosleep
    + ~30 more safe syscalls
    
  Explicitly denied:
    fork, clone, vfork, execve, system
    socket, connect, bind, listen, send, recv
    ptrace, process_vm_readv, process_vm_writev
    all other system calls → SCMP_ACT_ERRNO

☐ Apply seccomp to Docker container
  --security-opt seccomp=/path/to/seccomp.json
  
☐ Test: Container tries fork()
  Should fail: Operation not permitted
  
☐ Test: Container tries execve()
  Should fail: Operation not permitted

INPUT VALIDATION:
☐ Prompt length check
  if len(prompt) > 10000:
    return 400 Bad Request "Prompt too long"
    
☐ Prompt content validation
  Blacklist patterns: [
    "rm -rf",
    "fork()",
    "exec(",
    "system(",
    "__import__",
    "eval(",
    "exec(",
    "pickle",
  ]
  if any pattern in prompt.lower():
    return 400 Bad Request "Suspicious content detected"
    
☐ Model whitelist
  Allowed models: ["mistral:7b", "gemma:2b"]
  if model not in whitelist:
    return 400 Bad Request "Model not allowed"
    
☐ Test: Submit prompt with "fork()"
  Response: 400 Bad Request
  
☐ Test: Submit prompt with 20KB text
  Response: 400 Bad Request

RATE LIMITING:
☐ Implement Redis-based rate limiter

  per_user_per_minute = redis.get(f"ratelimit:{user_id}:tasks")
  if per_user_per_minute >= 10:
    return 429 Too Many Requests
  
  redis.incr(f"ratelimit:{user_id}:tasks")
  redis.expire(f"ratelimit:{user_id}:tasks", 60)
  
☐ Test: Submit 15 tasks in 1 minute
  First 10: success
  Next 5: 429 error
```

### Week 4: Monitoring + Audit Logging

```
AUDIT LOGGING:

☐ Create audit table
  CREATE TABLE audit_log (
    id UUID PRIMARY KEY,
    timestamp TIMESTAMP,
    actor_type ENUM('provider', 'consumer', 'admin'),
    actor_id UUID,
    action VARCHAR(100),
    resource_id UUID,
    details JSONB,
    INDEX (timestamp, actor_id)
  );

☐ Log all critical actions
  - User registration
  - Task submission (prompt logged? no, only ID)
  - Task assignment to provider
  - Task completion
  - Provider resource allocation change
  - Reputation score change
  - Any errors/exceptions

☐ Sample audit queries
  -- Find all tasks from user_id=X
  SELECT * FROM audit_log 
  WHERE actor_id = X AND action = 'task_submitted';
  
  -- Find all reputation changes
  SELECT * FROM audit_log 
  WHERE action = 'reputation_change' 
  ORDER BY timestamp DESC;

MONITORING DASHBOARD:
☐ Setup Prometheus metrics
  - lds_tasks_total (counter)
  - lds_task_duration_seconds (histogram)
  - lds_provider_uptime_percent (gauge)
  - lds_resource_utilization_percent (gauge)
  - lds_errors_total (counter)
  
☐ Setup Grafana dashboard
  - Real-time task submission rate
  - Provider availability
  - Average task completion time
  - Error rate
  - Resource usage

ALERTING:
☐ Setup alerts
  if error_rate > 5% in last 5 min:
    → Alert: "High error rate detected"
    
  if provider_uptime < 90%:
    → Alert: "Provider X offline"
    
  if task_completion_time > 10 min:
    → Alert: "Slow task completion"
    
  if fraud_detected:
    → Alert: "Potential fraud on provider X"

TESTING:
☐ Inject fake errors, verify logging
☐ Verify audit trail completeness
☐ Test: Query all tasks from specific user
☐ Test: Export audit log to CSV
```

---

## ЧАСТЬ 3: DEPLOYMENT CHECKLIST

### Pre-Launch Security Review

```
☐ INFRASTRUCTURE
  ☐ Firewall configured (allow only 443/TLS)
  ☐ SSH key-based auth only (no password)
  ☐ Fail2ban or similar for brute force protection
  ☐ Fail2ban config: 5 attempts → 1 hour ban
  ☐ DDoS protection (CloudFlare or similar)
  ☐ Backups enabled (daily, 7 days retention)
  ☐ Backup encryption enabled
  
☐ DATABASE
  ☐ PostgreSQL password: 32+ char random
  ☐ Redis password: 32+ char random
  ☐ Database backups encrypted
  ☐ No default credentials anywhere
  ☐ SQL injection testing passed
  ☐ Connection pooling configured
  
☐ APPLICATION
  ☐ No hardcoded credentials
  ☐ Secrets in environment variables only
  ☐ Logging doesn't log passwords/API keys
  ☐ CORS headers configured properly
  ☐ Content-Security-Policy headers set
  ☐ X-Frame-Options: DENY
  ☐ X-Content-Type-Options: nosniff
  
☐ CONTAINER SECURITY
  ☐ Docker image scanned for vulnerabilities
  ☐ (Use: docker scan arvis/executor:latest)
  ☐ seccomp profile validated
  ☐ cgroups limits tested
  ☐ TLS in Docker daemon enabled
  ☐ No privileged containers
  
☐ LEGAL/COMPLIANCE
  ☐ Privacy Policy published
  ☐ Terms of Service published
  ☐ GDPR DPA ready (EU)
  ☐ Provider NDA available
  ☐ Dispute resolution process documented
  ☐ Insurance (if required locally)
  
☐ MONITORING
  ☐ Error tracking (Sentry or similar)
  ☐ Uptime monitoring (Uptime.com)
  ☐ Log aggregation (ELK or similar)
  ☐ Alerts configured for critical issues
  ☐ Incident response process documented
  
☐ TESTING
  ☐ Load testing: 1000 concurrent connections
  ☐ Security testing: OWASP Top 10 scanned
  ☐ Penetration testing: by external firm (optional for MVP)
  ☐ Chaos engineering: kill random containers, verify recovery
  
☐ DOCUMENTATION
  ☐ API documentation (OpenAPI/Swagger)
  ☐ Deployment runbook
  ☐ Security runbook
  ☐ Incident response playbook
  ☐ Provider setup guide
  ☐ Consumer getting started guide
```

---

## ЧАСТЬ 4: QUICK START - ПЕРВЫЕ 4 НЕДЕЛИ

### Week 1: Setup + TLS

```
ДЕНЬ 1-2: Infrastructure
─────────────────────────────────
git clone <repo>
cd arvis-lds-server

# Install infrastructure
terraform init
terraform apply  # Provisions AWS/OVH resources
# Output: server IP, DB endpoint, Redis endpoint

ДЕНЬ 3-4: TLS Certificates
─────────────────────────────────
# Get domain (e.g., lds-api.arvis.cloud)
# Setup DNS A record pointing to server IP

ssh ubuntu@<server_ip>

# Install certbot
sudo apt-get update && sudo apt-get install -y certbot

# Get certificate
sudo certbot certonly --standalone -d lds-api.arvis.cloud
# Output: /etc/letsencrypt/live/lds-api.arvis.cloud/

# Auto-renewal
sudo systemctl enable certbot.timer

ДЕНЬ 5: API Server + TLS
─────────────────────────────────
# Install Docker
sudo apt-get install -y docker.io

# Build API server image
docker build -t arvis/lds-api:latest .

# Run with TLS
docker run -d \
  -p 443:8000 \
  -v /etc/letsencrypt:/etc/letsencrypt:ro \
  -e CERT_PATH=/etc/letsencrypt/live/lds-api.arvis.cloud/fullchain.pem \
  -e KEY_PATH=/etc/letsencrypt/live/lds-api.arvis.cloud/privkey.pem \
  arvis/lds-api:latest

# Test
curl https://lds-api.arvis.cloud/health
# {"status": "ok"}

DELIVERABLE: Secure API running on HTTPS ✅
```

### Week 2: Container Isolation

```
ДЕНЬ 8-10: Docker Hardening
─────────────────────────────────
# Create executor image
docker build -f Dockerfile.executor -t arvis/executor:latest .

# Test: Run with resource limits
docker run --rm \
  --memory=2g \
  --cpus=1 \
  --network=none \
  --read-only \
  -e TASK_ID=test-1 \
  arvis/executor:latest

# Test: Try to exceed memory
python -c "import numpy as np; x = np.zeros((1000000000,))"
# Should be killed by container

# Test: Try network access
ping 8.8.8.8
# Should fail: network=none

ДЕНЬ 11-12: Resource Monitoring
─────────────────────────────────
# Implement container monitor loop
# Pseudo-code:
while task_running:
  stats = docker.stats(container_id)
  if stats.memory_usage > 2GB * 1.05:  # 5% tolerance
    docker.kill(container_id)
    log_event("Container exceeded memory")
  sleep(0.1)  # Check every 100ms

# Test: Monitor task and verify limits enforced

ДЕНЬ 13-14: Seccomp Profile
─────────────────────────────────
# Create seccomp.json (from Part 1 docs)

# Apply to Docker:
docker run --rm \
  --security-opt seccomp=/path/to/seccomp.json \
  arvis/executor:latest

# Test: Try fork() → should fail
python -c "import os; os.fork()"
# Should fail: Operation not permitted

DELIVERABLE: Isolated containers with resource limits ✅
```

### Week 3: Input Validation + Rate Limiting

```
ДЕНЬ 15-17: Input Validation
─────────────────────────────────
# Add to API layer:

def validate_task_submission(request):
    if len(request.prompt) > 10000:
        raise ValueError("Prompt too long")
    
    if any(pattern in request.prompt.lower() 
           for pattern in ["rm -rf", "fork()", "eval("]):
        raise ValueError("Suspicious content")
    
    if request.model not in ALLOWED_MODELS:
        raise ValueError("Model not allowed")

# Test prompts:
✓ Normal: "Write Python function for X"
✗ With code: "rm -rf /" → 400 Bad Request
✗ Too long: 20KB text → 400 Bad Request
✗ Invalid model: "gpt-999" → 400 Bad Request

ДЕНЬ 18: Rate Limiting
─────────────────────────────────
# Setup Redis rate limiter:

@app.post("/tasks/submit")
async def submit_task(request: TaskRequest, user_id: str):
    key = f"ratelimit:{user_id}:tasks"
    count = redis.incr(key)
    
    if count == 1:
        redis.expire(key, 60)  # Reset per minute
    
    if count > 10:  # Free tier limit
        raise HTTPException(status_code=429)
    
    # ... process task ...

# Test:
for i in range(15):
    response = client.post("/tasks/submit", json=task)
    print(response.status_code)  # First 10: 202, next 5: 429

DELIVERABLE: Input validation + rate limiting working ✅
```

### Week 4: Monitoring + Go-Live

```
ДЕНЬ 22-24: Monitoring Setup
─────────────────────────────────
# Install Prometheus
docker run -d \
  -p 9090:9090 \
  -v /etc/prometheus.yml:/etc/prometheus/prometheus.yml:ro \
  prom/prometheus:latest

# Install Grafana
docker run -d \
  -p 3000:3000 \
  grafana/grafana:latest

# Create dashboard:
- Task submission rate (req/sec)
- Error rate (%)
- Provider uptime (%)
- Average task duration (sec)

ДЕНЬ 25-26: Audit Logging
─────────────────────────────────
# Test audit log completeness:
curl -X POST https://lds-api/tasks/submit \
  -H "X-API-Key: sk_xxx" \
  -d '{"model": "mistral:7b", "prompt": "test"}'

# Verify in database:
SELECT * FROM audit_log 
WHERE action = 'task_submitted' 
ORDER BY timestamp DESC LIMIT 1;
# Should show: timestamp, user_id, task_id, status

ДЕНЬ 27: Security Checklist
─────────────────────────────────
Run through pre-launch checklist:
☐ Firewall configured
☐ TLS working
☐ Container isolation verified
☐ Input validation passing tests
☐ Rate limiting active
☐ Audit logging complete
☐ Monitoring dashboard up
☐ Backups configured
☐ Privacy Policy published
☐ ToS published

ДЕНЬ 28: GO LIVE 🚀
─────────────────────────────────
# Deploy to production
terraform apply -auto-approve

# Start with:
- 50 beta testers (internal + trusted community)
- 1 GB/sec API rate limit (can increase)
- 100 task queue limit (can increase)
- Monitor closely

# Send to beta testers:
"Arvis LDS MVP is live! Sign up at lds-api.arvis.cloud"
"Help us test and earn credits! Join our Discord for support"

DELIVERABLE: Production MVP launched ✅
```

---

## ЧАСТЬ 5: DEPLOYMENT INFRASTRUCTURE

### Recommended Stack (MVP)

```
┌─────────────────────────────────────────────────────────┐
│                    MVP INFRASTRUCTURE                    │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  FRONTEND (Arvis-Client)                                │
│  └─ Python 3.11+ PyQt6                                  │
│     • Provider Mode UI                                  │
│     • Consumer Mode UI                                  │
│     • Heartbeat loop (30s interval)                     │
│                                                          │
│  ├─────── HTTPS TLS 1.3+ ──────────                    │
│                                                          │
│  BACKEND (api.lds.arvis.cloud)                          │
│  └─ FastAPI + Uvicorn                                   │
│     • 4 worker processes                                │
│     • Rate limiting                                     │
│     • Request validation                                │
│     • Payment API integration                           │
│                                                          │
│  ├──── Internal Network ────                            │
│                                                          │
│  DATABASE TIER                                           │
│  ├─ PostgreSQL 15                                       │
│  │  └─ audit_log, providers, tasks, ledger, etc        │
│  │                                                       │
│  ├─ Redis 7                                             │
│  │  └─ Task queue, rate limiting, cache               │
│  │                                                       │
│  └─ S3/Backblaze B2                                     │
│     └─ Daily encrypted backups                         │
│                                                          │
│  CONTAINER RUNTIME (on Provider machines)              │
│  └─ Docker 24+                                          │
│     • arvis/executor:latest                             │
│     • Resource limits: 2GB RAM, 1 CPU, no network      │
│     • Seccomp profile applied                          │
│                                                          │
│  MONITORING TIER (optional, outside MVP)               │
│  ├─ Prometheus (metrics collection)                     │
│  ├─ Grafana (dashboards)                               │
│  └─ Sentry (error tracking)                            │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

### Cost Estimate (MVP, 3 months)

```
SERVICE                 PROVIDER        COST/MONTH      TOTAL (3 MO)
────────────────────────────────────────────────────────────────
API Server              OVH VPS         €10             €30
  (2 vCPU, 4GB RAM)

PostgreSQL              OVH Managed     €20             €60
  (20GB storage)

Redis                   OVH Managed     €10             €30
  (1GB)

Backups (B2)            Backblaze       ~€5             €15
  (Daily, 100GB max)

Domain (lds-api.arvis)  Namecheap       €10/year        €2.50
  (3 months)

TLS Certificate         Let's Encrypt   FREE            FREE
  (Auto-renewing)

Monitoring              Prometheus      FREE (self)     FREE
  (self-hosted)

Error Tracking          Sentry          FREE tier       FREE
  (Free up to 5K/month)

────────────────────────────────────────────────────────────────
TOTAL MVP 3 MONTHS:                                     ~€137.50

Or ~€46/month ongoing (after 3-month MVP)
```

---

## ЧАСТЬ 6: QUICK REFERENCE - SECURITY COMMANDS

```bash
# Test TLS
curl -v https://lds-api.arvis.cloud/health

# Check container isolation
docker run --rm arvis/executor python -c "import os; os.fork()"
# Expected: Operation not permitted

# Verify rate limiting
for i in {1..15}; do curl -X POST https://lds-api/tasks/submit ...; done
# Expected: First 10 → 202 Accepted, Next 5 → 429 Too Many Requests

# Check audit log
psql postgresql://user@host/arvis_lds <<EOF
SELECT COUNT(*) as total_events FROM audit_log;
SELECT actor_id, action, COUNT(*) as count 
FROM audit_log 
GROUP BY actor_id, action 
ORDER BY count DESC;
EOF

# Monitor container resources
docker stats --no-stream

# Check seccomp profile
docker inspect <container> | grep -i seccomp

# Verify database backups
ls -lh /backups/postgresql/
# Should show daily backup files
```

---

## ЗАКЛЮЧЕНИЕ

### ✅ Ready to Start

Все 4 недели структурированы:
- **Неделя 1:** TLS + HTTPS security ✅
- **Неделя 2:** Container isolation + cgroups ✅
- **Неделя 3:** Input validation + rate limiting ✅
- **Неделя 4:** Monitoring + live launch ✅

### 🎯 MVP Success Criteria

```
🟢 SECURITY:
  ✅ No container escapes (verified by internal test)
  ✅ No resource theft possible (cgroups enforced)
  ✅ No input attacks (validation + seccomp)
  ✅ All data encrypted in transit (TLS 1.3)
  ✅ Full audit trail for all operations

🟢 FUNCTIONALITY:
  ✅ Task submission → execution → results (end-to-end)
  ✅ Provider allocation & heartbeat working
  ✅ Consumer credit system functional
  ✅ Rating/reputation system basic (manual disputes OK for MVP)

🟢 OPERATIONAL:
  ✅ Monitoring dashboard visible
  ✅ Alerts configured for critical issues
  ✅ Backups verified
  ✅ Team can respond to incidents
```

### 🚀 Go-Live Confidence: HIGH (8/10)

Фокус на **одну цель**: безопасный MVP, который не может быть взломан начинающими злоумышленниками.

Готовы начинать! 💪
