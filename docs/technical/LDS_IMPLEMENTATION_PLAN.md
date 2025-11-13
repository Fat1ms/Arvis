# 📋 Система "Распределения нагрузки": Детальный план реализации

## ЧАСТЬ 1: ЮРИДИЧЕСКИЕ И РЕГУЛЯТОРНЫЕ АСПЕКТЫ

---

## 1. АНАЛИЗ ЮРИСДИКЦИЙ

### 1.1 Украина (Primary Market)

**Статус:** Полностью открыт

**Применимое законодательство:**
- Закон України "Про захист прав споживачів" (Consumer Protection)
- НК України (Tax Code)
- Закон "Про електронну комерцію" (E-commerce)
- GDPR (if processing EU residents' data)

**Ключевые требования:**
```
1. Consumer Protection
   - Четкие Т&С на украинском
   - Гарантия возврата средств за дефектное исполнение
   - 14-дневный period for disputes
   
2. Tax Obligations
   - Платформа: налог на прибыль 18% (базовая ставка)
   - Провайдеры: самозанятые, налог на самозанятых 5-20%
   - VAT может не применяться (digital service exemption)
   
3. Anti-Money Laundering (AML)
   - KYC для провайдеров при выводе > 1000 EUR/месяц
   - Reporting to State Financial Monitoring Service
```

**Рекомендуемая структура:**
```
Вариант А (Рекомендуется):
  • Регистрация: ООО in Київ
  • Структура: Платформа (Украина) + Server (EU для GDPR)
  • Преимущества: Local presence, easy compliance
  • Сложность: Medium

Вариант Б:
  • Регистрация: EU company + Ukraine branch
  • Преимущества: GDPR compliance built-in
  • Недостатки: More paperwork
```

---

### 1.2 Европейский Союз

**Статус:** Открыт с условиями (GDPR compliance required)

**Применимое законодательство:**
- GDPR (General Data Protection Regulation)
- Digital Services Act (DSA)
- eIDAS (electronic identification)
- PSD2 (Payment Services Directive 2)

**Ключевые требования:**
```
1. GDPR Compliance
   ✅ Data minimization: collect only needed data
   ✅ Privacy by design: encryption, access controls
   ✅ Data retention limits: delete old data after 6 months
   ✅ DPA (Data Processing Agreement) with providers
   ✅ Right to erasure: user can delete all data
   ✅ DPIA (Data Impact Assessment) for risky processing
   
   COST: €5,000-€20,000 for compliance audit + legal

2. Digital Services Act (DSA)
   ✅ Transparency report (quarterly)
   ✅ Content moderation policies
   ✅ Terms & Conditions in user language
   ✅ Dispute resolution mechanism
   
   COST: €3,000-€10,000 for DSA implementation

3. Payment Services
   ✅ PSD2 strong customer authentication (3DS)
   ✅ Refund processing within 5 working days
   ✅ Chargebacks handling
```

**Рекомендуемая структура:**
```
Вариант 1: Remote Company
  • Серверы: DE/NL/IE (good GDPR infrastructure)
  • DPO (Data Protection Officer): hire external
  • Compliance: €20,000-€30,000 setup
  
Вариант 2: Local Branch
  • Регистрация: Germany (Best compliance infrastructure)
  • Local team: compliance manager + DPO
  • Benefits: Local authority contact, easier audits
  • Cost: Higher but safer
```

---

### 1.3 США

**Статус:** Сложно (no single comprehensive law, fragmented)

**Применимое законодательство:**
- State laws (California CCPA/CPRA most restrictive)
- FTC Act Section 5 (unfair/deceptive practices)
- CAN-SPAM Act (if sending marketing emails)
- SOC 2 Type II (for enterprise customers)

**Ключевые требования:**
```
1. State-by-state Compliance
   ✅ California CCPA/CPRA: most restrictive
   ✅ Texas: HB 4
   ✅ Colorado: CPA
   ✅ Connecticut: CTDPA
   ✅ Utah: UCPA
   
   Strategy: Code to California standard, applies everywhere

2. 1099 Tax Reporting
   ✅ Issue 1099-NEC to providers earning > $600/year
   ✅ File with IRS
   ✅ Requires SSN/EIN collection
   
   COST: Accounting + tax filing: $3,000-$5,000/year

3. Chargebacks & Disputes
   ✅ Full refund if task fails
   ✅ Chargeback rate < 1% (require better fraud detection)
```

**Рекомендация для MVP:**
```
❌ Skip US market initially
  - Too fragmented, too expensive
  - Focus EU + Ukraine
  - Add US in Phase 2 when revenue justifies cost
```

---

### 1.4 России

**Статус:** ❌ ЗАПРЕЩЕНО

```
Причины:
  1. Санкции (OFAC sanctions)
  2. Политические отношения
  3. Нет платежных систем
  4. Валютный контроль

Действие: Блокировать IPs из России
          Запретить в Т&С для РФ пользователей
```

---

## 2. ПРАВОВЫЕ ДОКУМЕНТЫ И ШАБЛОНЫ

### 2.1 Terms of Service (главные пункты)

```markdown
# ARVIS LDS - TERMS OF SERVICE

## 1. SERVICE DESCRIPTION
- Define what LDS is
- Disclaimer: best effort, no guarantees
- Modification rights: we can change terms with notice

## 2. USER CLASSIFICATIONS
- Consumer: submits tasks, pays credits
- Provider: allocates resources, earns credits
- Admin: platform management (us)

## 3. PROVIDER OBLIGATIONS
- Allocate resources accurately
- Maintain security of system
- Comply with AUP (Acceptable Use Policy)
- Report security issues
- No mining, botnet, adult content

## 4. CONSUMER OBLIGATIONS
- Provide accurate account info
- Responsible for API key security
- Payment for services rendered
- No illegal content submission

## 5. LIABILITY & INDEMNIFICATION
- We're not liable for:
  • Lost profits
  • Data loss from provider failure
  • Third-party claims
  • Interruptions (force majeure)
  
- Each party indemnifies other for breach

## 6. DISPUTE RESOLUTION
- Good faith negotiation (30 days)
- Mediation (30 days)
- Arbitration (binding)
- Venue: (Your legal jurisdiction)

## 7. TERMINATION
- Either party: 30 days notice
- Immediate for breach/violation
- Effect: settle credits, return data

## 8. INTELLECTUAL PROPERTY
- We own platform
- You own submitted code/data
- License to us to execute/process
- We don't claim IP of outputs
```

### 2.2 Provider Agreement (дополнительно к ToS)

```markdown
# PROVIDER SERVICE AGREEMENT

## 1. RESOURCE COMMITMENT
- Provider: Allocate at least X GB RAM, Y CPU cores
- Duration: Minimum 1 month commitment
- Downtime: Allowed < 5 hours/week
- Performance: Minimum 95% uptime required

## 2. COMPENSATION
- Rates: [specified in pricing table]
- Currency: Credits (convert to USD at posted rate)
- Payment: Weekly settlement, minimum $10
- Tax: Provider responsible for own tax reporting

## 3. SECURITY OBLIGATIONS
- Maintain system security
- Report vulnerabilities immediately
- Comply with Docker/container security practices
- Allow security audits (30 days notice)

## 4. LIABILITY CAP
- Provider liability: Capped at 1x monthly earnings
- Exception: Intentional misconduct, breach of confidentiality

## 5. INTELLECTUAL PROPERTY
- We own platform code
- Provider owns modifications to own code (if any)
- Provider grants us license to execute/process
- Work product (results) ownership depends on task

## 6. CONFIDENTIALITY
- Provider must keep tasks confidential
- No copying, distribution, or use for own benefit
- Exceptions: legal process, safety
- Breach: Immediate termination + damages
```

### 2.3 Data Processing Agreement (GDPR DPA)

```markdown
# DATA PROCESSING AGREEMENT

## 1. SUBJECT & SCOPE
Processor (Arvis) processes personal data of:
- Consumers
- Providers
- End-users of tasks (if applicable)

## 2. DATA CATEGORIES & PROCESSING PURPOSE
Category: Contact, Auth, Payment, Activity Logs
Purpose: Service delivery, fraud prevention, analytics
Legal basis: Legitimate interest, contract performance

## 3. PROCESSOR OBLIGATIONS
- Process only on documented instructions
- Staff confidentiality agreements
- Data subject rights support (SAR, deletion, etc.)
- Regular audits of processing
- Incident reporting within 24 hours

## 4. SUB-PROCESSORS
- Server hosting: AWS/Azure/own datacenter
- Payment processor: Stripe
- Analytics: Mixpanel (anonymized)
- Email service: SendGrid

## 5. DATA RETENTION
- Personal data: 3 years post-termination
- Logs: 6 months (security)
- Audit trail: 7 years (legal requirement)

## 6. DELETION / PORTABILITY
- User can export data (GDPR Article 20)
- User can request deletion (with 30-day grace period for disputes)
```

---

## 3. COMPLIANCE CHECKLIST FOR LAUNCH

### Pre-Launch (8 weeks before)

```
WEEK 1-2: Legal Setup
☐ Consult with lawyer (criminal, tax, contract)
☐ Draft ToS, DPA, Provider Agreement
☐ Review insurance requirements
☐ Determine tax structure

WEEK 3-4: Privacy & Security
☐ Conduct privacy impact assessment (DPIA)
☐ Implement data minimization
☐ Set up encryption (in-transit + at-rest)
☐ Create incident response plan

WEEK 5-6: Payment & Compliance
☐ Select payment processor + compliance review
☐ Implement refund mechanism
☐ Set up chargebacks handling
☐ Decide on KYC threshold

WEEK 7-8: Launch Prep
☐ Final legal review with counsel
☐ Create privacy notice + FAQ
☐ Train support team on compliance
☐ Set up audit logging
```

### Post-Launch (ongoing)

```
MONTHLY:
☐ Review payment chargebacks (< 1% target)
☐ Audit provider activity logs
☐ Check for ToS violations
☐ Security incident review

QUARTERLY:
☐ Compliance report to legal counsel
☐ Data retention audit
☐ Access control review
☐ Vendor assessment

ANNUALLY:
☐ Full security audit
☐ Privacy assessment update
☐ DPA/legal document refresh
☐ Tax filing + compliance report
```

---

## ЧАСТЬ 2: ТЕХНИЧЕСКИЙ ПЛАН РЕАЛИЗАЦИИ

---

## 4. DETAILED SYSTEM DESIGN

### 4.1 Database Schema

```sql
-- PROVIDERS (Resource Suppliers)
CREATE TABLE providers (
    id UUID PRIMARY KEY,
    user_id UUID REFERENCES users(id),
    status ENUM('active', 'inactive', 'banned', 'suspended'),
    ram_allocated_gb INT,
    cpu_cores_allocated INT,
    gpu_allocated INT DEFAULT 0,
    
    reputation_score FLOAT DEFAULT 3.0,  -- 0-5.0
    total_tasks_completed INT DEFAULT 0,
    total_uptime_hours BIGINT DEFAULT 0,
    
    registration_date TIMESTAMP,
    last_heartbeat TIMESTAMP,
    
    UNIQUE(user_id)
);

-- RESOURCES (Current Resource Snapshot)
CREATE TABLE provider_resources (
    id UUID PRIMARY KEY,
    provider_id UUID REFERENCES providers(id),
    
    ram_used_mb INT,
    ram_limit_mb INT,
    cpu_percent FLOAT,
    gpu_percent FLOAT,
    
    timestamp TIMESTAMP DEFAULT NOW(),
    reported_by_provider BOOLEAN  -- Did provider report, or did we measure?
    
    CREATE INDEX idx_provider_resources ON provider_resources(provider_id, timestamp);
);

-- TASKS (Job Queue)
CREATE TABLE tasks (
    id UUID PRIMARY KEY,
    consumer_id UUID REFERENCES users(id),
    provider_id UUID REFERENCES providers(id) NULLABLE,
    
    status ENUM('pending', 'assigned', 'running', 'completed', 'failed', 'timeout', 'cancelled'),
    priority ENUM('low', 'normal', 'high', 'urgent'),  -- Affects routing
    
    llm_model VARCHAR(100),  -- 'mistral:7b', 'code-llama:34b'
    prompt TEXT,
    max_tokens INT,
    temperature FLOAT,
    
    estimated_credits INT,
    actual_credits_charged INT NULLABLE,
    
    submission_time TIMESTAMP,
    assignment_time TIMESTAMP NULLABLE,
    start_time TIMESTAMP NULLABLE,
    completion_time TIMESTAMP NULLABLE,
    timeout_seconds INT DEFAULT 300,
    
    result TEXT NULLABLE,
    error_message TEXT NULLABLE,
    
    CREATE INDEX idx_tasks_consumer ON tasks(consumer_id);
    CREATE INDEX idx_tasks_status ON tasks(status);
    CREATE INDEX idx_tasks_provider ON tasks(provider_id);
);

-- TASK_METRICS (Performance Tracking)
CREATE TABLE task_metrics (
    id UUID PRIMARY KEY,
    task_id UUID REFERENCES tasks(id),
    
    chunks_received INT,  -- For streaming
    tokens_generated INT,
    execution_seconds FLOAT,
    provider_ram_used_mb INT,
    provider_cpu_percent FLOAT,
    
    provider_reported_time TIMESTAMP,
);

-- CREDITS & ACCOUNTING
CREATE TABLE credit_ledger (
    id UUID PRIMARY KEY,
    transaction_id UUID,  -- Links related transactions
    
    user_id UUID REFERENCES users(id),
    amount INT,  -- Positive = credit, Negative = debit
    balance_after INT,
    
    transaction_type ENUM(
        'purchase', 'task_cost', 'provider_earn', 
        'refund', 'adjustment', 'bonus'
    ),
    reference_id UUID NULLABLE,  -- task_id or purchase_id
    
    timestamp TIMESTAMP DEFAULT NOW(),
    
    CREATE INDEX idx_ledger_user ON credit_ledger(user_id);
    CREATE INDEX idx_ledger_time ON credit_ledger(timestamp);
);

-- REPUTATION EVENTS
CREATE TABLE reputation_events (
    id UUID PRIMARY KEY,
    provider_id UUID REFERENCES providers(id),
    
    event_type ENUM(
        'task_completed', 'task_failed', 'resource_overuse', 
        'malware_detected', 'data_breach', 'fraud_attempt',
        'audit_passed', 'manual_adjustment'
    ),
    
    impact FLOAT,  -- -2.0 to +1.0 (deltas to score)
    description TEXT,
    
    timestamp TIMESTAMP DEFAULT NOW(),
    
    CREATE INDEX idx_reputation_provider ON reputation_events(provider_id);
);

-- DISPUTES
CREATE TABLE disputes (
    id UUID PRIMARY KEY,
    task_id UUID REFERENCES tasks(id),
    
    initiator_id UUID REFERENCES users(id),
    respondent_id UUID REFERENCES users(id),
    
    reason TEXT,  -- 'result_incorrect', 'timeout', 'fraud_suspected', etc.
    status ENUM('open', 'resolving', 'resolved', 'escalated'),
    
    created_at TIMESTAMP,
    resolved_at TIMESTAMP NULLABLE,
    
    resolution TEXT NULLABLE,
    winner_id UUID NULLABLE,  -- Who won dispute
    
    CREATE INDEX idx_disputes_task ON disputes(task_id);
);
```

### 4.2 API Design (OpenAPI 3.0)

```yaml
openapi: 3.0.0
info:
  title: Arvis LDS API
  version: 1.0.0

servers:
  - url: https://api.arvis.cloud/v1

paths:
  /auth/register:
    post:
      tags: [Authentication]
      summary: Register new user (consumer or provider)
      requestBody:
        required: true
        content:
          application/json:
            schema:
              type: object
              properties:
                email: { type: string, format: email }
                password: { type: string, minLength: 12 }
                role: { enum: [consumer, provider] }
              required: [email, password, role]
      responses:
        201:
          description: User created
          content:
            application/json:
              schema:
                type: object
                properties:
                  user_id: { type: string, format: uuid }
                  api_key: { type: string }
                  
  /providers/register-resources:
    post:
      tags: [Provider Operations]
      summary: Register allocated resources
      security:
        - ApiKeyAuth: []
      requestBody:
        required: true
        content:
          application/json:
            schema:
              type: object
              properties:
                ram_gb: { type: integer, minimum: 2, maximum: 1024 }
                cpu_cores: { type: integer, minimum: 1, maximum: 256 }
                gpu_count: { type: integer, default: 0 }
              required: [ram_gb, cpu_cores]
      responses:
        200:
          description: Resources registered
          content:
            application/json:
              schema:
                type: object
                properties:
                  provider_id: { type: string, format: uuid }
                  status: { enum: [active, pending_verification] }
                  
  /providers/heartbeat:
    post:
      tags: [Provider Operations]
      summary: Keep-alive signal with current metrics
      security:
        - ApiKeyAuth: []
      requestBody:
        required: true
        content:
          application/json:
            schema:
              type: object
              properties:
                ram_used_mb: { type: integer }
                cpu_percent: { type: number }
                gpu_percent: { type: number, nullable: true }
                tasks_processing: { type: integer }
              required: [ram_used_mb, cpu_percent]
      responses:
        200:
          description: Heartbeat received
          content:
            application/json:
              schema:
                type: object
                properties:
                  next_task_id: { type: string, format: uuid, nullable: true }
                  server_time: { type: string, format: date-time }
                  
  /tasks/submit:
    post:
      tags: [Consumer Operations]
      summary: Submit new task
      security:
        - ApiKeyAuth: []
      requestBody:
        required: true
        content:
          application/json:
            schema:
              type: object
              properties:
                model: { enum: [mistral:7b, code-llama:34b, gemma:2b] }
                prompt: { type: string, minLength: 1, maxLength: 10000 }
                max_tokens: { type: integer, default: 256 }
                priority: { enum: [low, normal, high, urgent], default: normal }
              required: [model, prompt]
      responses:
        202:
          description: Task accepted
          content:
            application/json:
              schema:
                type: object
                properties:
                  task_id: { type: string, format: uuid }
                  estimated_credits: { type: integer }
                  estimated_wait_seconds: { type: integer }
                  
  /tasks/{taskId}:
    get:
      tags: [Consumer Operations]
      summary: Get task status
      security:
        - ApiKeyAuth: []
      parameters:
        - name: taskId
          in: path
          required: true
          schema:
            type: string
            format: uuid
      responses:
        200:
          description: Task status
          content:
            application/json:
              schema:
                type: object
                properties:
                  task_id: { type: string, format: uuid }
                  status: { enum: [pending, assigned, running, completed, failed] }
                  result: { type: string, nullable: true }
                  
  /providers/tasks/{taskId}/result:
    post:
      tags: [Provider Operations]
      summary: Submit task result
      security:
        - ApiKeyAuth: []
      parameters:
        - name: taskId
          in: path
          required: true
          schema:
            type: string
            format: uuid
      requestBody:
        required: true
        content:
          application/json:
            schema:
              type: object
              properties:
                result: { type: string }
                metrics:
                  type: object
                  properties:
                    execution_seconds: { type: number }
                    tokens_generated: { type: integer }
              required: [result]
      responses:
        200:
          description: Result accepted
          
  /account/balance:
    get:
      tags: [Account]
      summary: Get current credit balance
      security:
        - ApiKeyAuth: []
      responses:
        200:
          description: Balance info
          content:
            application/json:
              schema:
                type: object
                properties:
                  balance_credits: { type: integer }
                  reserved_credits: { type: integer }
                  available_credits: { type: integer }
                  
  /account/ledger:
    get:
      tags: [Account]
      summary: Get transaction history
      security:
        - ApiKeyAuth: []
      parameters:
        - name: limit
          in: query
          schema: { type: integer, default: 100 }
        - name: offset
          in: query
          schema: { type: integer, default: 0 }
      responses:
        200:
          description: Transaction list
          
components:
  securitySchemes:
    ApiKeyAuth:
      type: apiKey
      in: header
      name: X-API-Key
```

### 4.3 Routing Algorithm

```python
def select_provider(task: Task, available_providers: List[Provider]) -> Provider:
    """
    Select best provider for task using weighted scoring
    """
    
    scores = {}
    
    for provider in available_providers:
        score = 0.0
        reasons = []
        
        # Factor 1: Reputation (40%)
        reputation_score = provider.reputation_score / 5.0
        score += reputation_score * 0.40
        reasons.append(f"Reputation: {reputation_score:.2f}")
        
        # Factor 2: Resource availability (30%)
        if has_sufficient_resources(provider, task):
            available = (provider.ram_available / provider.ram_allocated)
            resource_score = min(1.0, available)
            score += resource_score * 0.30
            reasons.append(f"Resources: {resource_score:.2f}")
        else:
            score += 0.0  # No go
            reasons.append("Resources: insufficient")
            
        # Factor 3: Latency/Connection quality (15%)
        latency_ms = measure_latency(provider)
        latency_score = 1.0 - min(1.0, latency_ms / 500.0)  # Normalize to 500ms
        score += latency_score * 0.15
        reasons.append(f"Latency: {latency_score:.2f} ({latency_ms}ms)")
        
        # Factor 4: Task completion rate (15%)
        completion_rate = provider.total_tasks_completed / 
                         (provider.total_tasks_completed + provider.failed_tasks)
        score += completion_rate * 0.15
        reasons.append(f"Completion: {completion_rate:.2f}")
        
        # Special handling for priority
        if task.priority == 'urgent':
            # Slightly favor providers with lowest current load
            load = current_load(provider)
            score *= (1.0 - load * 0.1)
            
        scores[provider.id] = (score, reasons)
    
    # Select top scorer
    if not scores:
        raise NoAvailableProvidersError("No providers meet requirements")
        
    best_provider_id = max(scores.keys(), key=lambda k: scores[k][0])
    best_score, reasons = scores[best_provider_id]
    
    logger.info(f"Selected provider {best_provider_id}: score={best_score:.3f}")
    for reason in reasons:
        logger.debug(f"  - {reason}")
        
    return get_provider(best_provider_id)
```

---

## 5. SECURITY HARDENING

### 5.1 Container Sandbox Configuration

```dockerfile
# Provider-side: Dockerfile for task execution
FROM python:3.11-slim

# Minimal base image
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Run as non-root
RUN useradd -m -u 1000 executor
USER executor

WORKDIR /app

# Copy only necessary files (no package manager, compiler, etc.)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY task.py .

# Security settings
ENTRYPOINT ["python", "-u", "task.py"]
```

```yaml
# docker-compose.yml - Provider resource limits
version: '3.8'
services:
  task_executor:
    image: arvis/task-executor:latest
    environment:
      TASK_ID: ${TASK_ID}
      TASK_TIMEOUT: ${TASK_TIMEOUT}
    
    # Resource limits (hard caps)
    mem_limit: 4g  # Cannot exceed
    memswap_limit: 4g  # No swap
    cpus: 2.0  # Max 2 CPU cores
    cpu_quota: 200000
    cpu_period: 100000
    
    # Network isolation
    networks:
      - task_network
    cap_drop:
      - ALL
    cap_add:
      - NET_BIND_SERVICE
      - SYS_PTRACE  # For debugging
    
    # Seccomp profile
    security_opt:
      - seccomp=unconfined  # Can be restricted further
    
    # Read-only filesystem
    read_only: true
    tmpfs:
      - /tmp
      - /run
    
    # Logging (monitor for abuse)
    logging:
      driver: json-file
      options:
        max-size: "10m"
        max-file: "3"
    
    # Exit on complete
    restart_policy:
      condition: none
```

### 5.2 Syscall Whitelist (Seccomp Profile)

```json
{
  "defaultAction": "SCMP_ACT_ERRNO",
  "defaultErrnoRet": 1,
  "archMap": [
    {
      "architecture": "SCMP_ARCH_X86_64",
      "subArchitectures": [
        "SCMP_ARCH_X86",
        "SCMP_ARCH_X32"
      ]
    }
  ],
  "syscalls": [
    {
      "names": [
        "read", "write", "open", "close", "stat",
        "fstat", "lstat", "poll", "lseek",
        "mmap", "mprotect", "munmap", "brk",
        "rt_sigaction", "rt_sigprocmask",
        "rt_sigpending", "rt_sigtimedwait",
        "rt_sigaction", "rt_sigpending",
        "sigaltstack", "pause", "nanosleep",
        "getitimer", "alarm", "setitimer",
        "getpid", "sendfile", "socket",
        "connect", "accept", "sendto",
        "recvfrom", "sendmsg", "recvmsg",
        "shutdown", "bind", "listen", "getsockname",
        "getpeername", "socketpair", "setsockopt",
        "getsockopt", "clone", "fork", "vfork",
        "execve", "exit", "wait4", "kill",
        "uname", "fcntl", "flock", "fsync",
        "fdatasync", "truncate", "ftruncate",
        "getdents", "getcwd", "chdir", "fchdir",
        "rename", "mkdir", "rmdir", "creat",
        "link", "unlink", "symlink", "readlink",
        "chmod", "fchmod", "chown", "fchown",
        "lchown", "umask", "gettimeofday",
        "getrlimit", "getrusage", "sysinfo",
        "times", "ptrace", "getuid", "syslog",
        "getgid", "setuid", "setgid", "geteuid",
        "getegid", "setpgid", "getppid",
        "getpgrp", "setsid", "setreuid",
        "setregid", "getgroups", "setgroups",
        "setresuid", "getresuid", "setresgid",
        "getresgid", "getpgid", "setfsuid",
        "setfsgid", "getsid", "capget", "capset",
        "rt_pending", "rt_sigtimedwait",
        "rt_sigqueueinfo", "rt_sigsuspend",
        "sigaltstack", "utime", "mknod",
        "uselib", "personality", "ustat",
        "statfs", "fstatfs", "sysfs",
        "getpriority", "setpriority", "sched_setparam",
        "sched_getparam", "sched_setscheduler",
        "sched_getscheduler", "sched_get_priority_max",
        "sched_get_priority_min", "sched_rr_get_interval",
        "mlock", "munlock", "mlockall", "munlockall",
        "vhangup", "modify_ldt", "pivot_root",
        "_sysctl", "prctl", "arch_prctl",
        "adjtimex", "setrlimit", "chroot",
        "sync", "acct", "settimeofday",
        "mount", "umount2", "syslog",
        "pread64", "pwrite64", "chown",
        "setfattr", "getfattr", "removexattr",
        "listxattr", "llistxattr", "flistxattr",
        "removexattr", "lremovexattr",
        "fremovexattr", "tkill", "time",
        "futex", "sched_setaffinity",
        "sched_getaffinity", "set_thread_area",
        "io_setup", "io_destroy", "io_getevents",
        "io_submit", "io_cancel", "get_thread_area",
        "lookup_dcookie", "epoll_create",
        "epoll_ctl_old", "epoll_wait_old",
        "remap_file_pages", "getdents64",
        "set_tid_address", "restart_syscall",
        "semtimedop", "fadvise64",
        "timer_create", "timer_settime",
        "timer_gettime", "timer_getoverrun",
        "timer_delete", "clock_settime",
        "clock_gettime", "clock_getres",
        "clock_nanosleep", "exit_group",
        "epoll_wait", "epoll_ctl",
        "tgkill", "utimes", "vserver",
        "mbind", "set_mempolicy",
        "get_mempolicy", "mq_open",
        "mq_unlink", "mq_timedsend",
        "mq_timedreceive", "mq_notify",
        "mq_getsetattr", "kexec_load",
        "waitid", "add_key", "request_key",
        "keyctl", "ioprio_set", "ioprio_get",
        "inotify_init", "inotify_add_watch",
        "inotify_rm_watch", "migrate_pages",
        "openat", "mkdirat", "mknodat",
        "fchownat", "futimesat", "newfstatat",
        "unlinkat", "renameat", "linkat",
        "symlinkat", "readlinkat", "fchmodat",
        "faccessat", "pselect6", "ppoll",
        "unshare", "set_robust_list",
        "get_robust_list", "splice",
        "tee", "sync_file_range",
        "vmsplice", "move_pages",
        "utimensat", "epoll_pwait",
        "signalfd", "timerfd_create",
        "eventfd", "fallocate",
        "timerfd_settime", "timerfd_gettime",
        "accept4", "signalfd4",
        "eventfd2", "epoll_create1",
        "dup3", "pipe2", "inotify_init1",
        "preadv", "pwritev", "rt_tgsigqueueinfo",
        "perf_event_open", "recvmmsg",
        "fanotify_init", "fanotify_mark",
        "prlimit64", "name_to_handle_at",
        "open_by_handle_at", "clock_adjtime",
        "syncfs", "sendmmsg", "setns",
        "getcpu", "process_vm_readv",
        "process_vm_writev"
      ],
      "action": "SCMP_ACT_ALLOW",
      "args": []
    }
  ]
}
```

---

## ЗАКЛЮЧЕНИЕ

Этот документ описывает:

1. ✅ **Юридическую основу** (Украина, ЕС, США)
2. ✅ **Регуляторные требования** (GDPR, tax, compliance)
3. ✅ **Шаблоны документов** (ToS, DPA, Provider Agreement)
4. ✅ **Технический дизайн** (Database, API, Routing)
5. ✅ **Безопасность** (Sandboxing, Seccomp, Resource limits)

### Рекомендуемый порядок действий:

1. **Недели 1-2:** Юридическая консультация + выбор структуры
2. **Недели 3-4:** Адаптация документов под юрисдикцию
3. **Недели 5-6:** Начать разработку инфраструктуры (API, Database)
4. **Недели 7-8:** Реализация контейнера-санда + security hardening
5. **Недели 9+:** Интеграция с Arvis-Client (Provider + Consumer modes)
