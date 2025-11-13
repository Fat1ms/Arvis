# 🔄 Система "Распределения нагрузки" (Load Distribution System, LDS)

## Концептуальное описание

**Цель:** Создать экосистему, где пользователи могут монетизировать свои вычислительные ресурсы (CPU, GPU, RAM) путем их предоставления для обработки запросов других пользователей. Система формирует общую вычислительную мощность, которая затем используется для запуска высокопроизводительных LLM-моделей.

**Модель:** Peer-to-Peer распределение задач с централизованной координацией на сервере.

---

## 1. АРХИТЕКТУРА СИСТЕМЫ

### 1.1 Компоненты

```
┌─────────────────────────────────────────────────────────────┐
│                    ARVIS SERVER (Coordinator)                │
├─────────────────────────────────────────────────────────────┤
│ • Task Queue & Scheduling                                    │
│ • Resource Registry & Discovery                              │
│ • Reputation & Credit System                                 │
│ • Billing & Accounting                                       │
│ • Monitoring & Analytics                                     │
└────────┬──────────────────────────────────────────────┬──────┘
         │                                              │
    ┌────▼──────┐                            ┌──────────▼──────┐
    │ PROVIDER   │◄───Resource Heartbeat──►│ CONSUMER         │
    │ (Lender)   │   (Active Connection)    │ (Requestor)      │
    ├────────────┤                          ├──────────────────┤
    │• Allocate  │                          │• Submit Tasks    │
    │  resources │                          │• Get Results     │
    │• Accept    │                          │• Pay Credits     │
    │  tasks     │                          │                  │
    │• Execute   │                          │                  │
    │• Report    │                          │                  │
    │  metrics   │                          │                  │
    └────────────┘                          └──────────────────┘
         ▲                                         ▲
         │                                         │
    ┌────┴─────────────────┬───────────────────────┴───────┐
    │ Task Execution       │ Resource Monitoring             │
    │ Result Streaming     │ Health Checks                   │
    └──────────────────────┴─────────────────────────────────┘
```

### 1.2 Основные участники

#### **Provider (Провайдер ресурсов)**
- Пользователь, предоставляющий свои CPU/GPU/RAM
- Запускает Arvis-Client в режиме "Resource Provider"
- Выделяет определенный объем ресурсов
- Получает вознаграждение за каждую выполненную задачу
- Может включать/отключать режим в любой момент

#### **Consumer (Потребитель)**
- Пользователь, отправляющий запросы на обработку
- Использует обычный режим Arvis-Client
- Платит кредитами за использование ресурсов
- Получает результаты асинхронно или в режиме реального времени

#### **Coordinator (Сервер)**
- Centralized orchestration
- Маршрутизирует задачи к доступным провайдерам
- Управляет кредитной системой
- Хранит репутационные данные
- Обеспечивает безопасность и аудит

---

## 2. ЭКОНОМИЧЕСКАЯ МОДЕЛЬ

### 2.1 Кредитная система

```
┌──────────────────────────────────────────────────┐
│           CREDIT ECONOMY MODEL                   │
├──────────────────────────────────────────────────┤
│                                                  │
│ 1 Credit = фиксированное выражение стоимости     │
│            (e.g., $0.001 USD equivalent)        │
│                                                  │
│ Формула: Credit Cost =                          │
│  Model_Complexity × Execution_Time ×            │
│  Resource_Allocation × Urgency_Factor           │
│                                                  │
└──────────────────────────────────────────────────┘
```

#### **Примеры расчетов**

| Сценарий | Сложность | Время (сек) | Ресурсы | Кредитов |
|----------|-----------|-------------|---------|----------|
| GPT-like (7B) быстро | 1.0x | 10 | 4GB RAM, 1xCPU | 10 |
| GPT-like (7B) нормально | 1.0x | 30 | 4GB RAM, 1xCPU | 30 |
| Mistral (13B) | 1.5x | 20 | 8GB RAM, 2xCPU | 60 |
| Code Analysis (32B) | 2.0x | 45 | 16GB RAM, 4xCPU | 180 |
| Image Generation (Flux) | 3.0x | 60 | 8GB VRAM | 540 |

### 2.2 Реверс-распределение (Provider Rewards)

```
Provider Reward = Task_Cost × (1 - Commission) × Reputation_Multiplier

Где:
- Task_Cost: полная стоимость задачи в кредитах
- Commission: комиссия платформы (10-20%)
- Reputation_Multiplier: от 0.5 (новый) до 1.5 (проверенный)

Примеры:
- Новый провайдер выполняет задачу на 100 кредитов:
  100 × 0.85 × 0.5 = 42.5 кредита заработка

- Проверенный провайдер (репутация 1.2x):
  100 × 0.85 × 1.2 = 102 кредита заработка
```

### 2.3 Уровни подписки и доступ

```
TIER        | Monthly Fee | Features                    | LDS Access
─────────────────────────────────────────────────────────────────────
Free        | $0          | Local LLM only              | ❌
Standard    | $4.99       | Local + Cloud LLM           | ❌
Professional| $14.99      | All + LDS Consumer Access   | ✅ (Consumer)
Enterprise  | $49.99      | All + LDS Provider + Premium| ✅ (Both)
```

### 2.4 Примеры доходов (Incentive Model)

**Scenario 1: Casual Provider**
```
Провайдер: Домашний компьютер, 8GB RAM, Ryzen 5
Выделяемые ресурсы: 4GB RAM, 2 CPU cores
Типичная нагрузка: 5-10 задач/день × 50 кредитов
Заработок: 250-500 кредитов/день × $0.001 = $0.25-$0.50/день
Месячный доход: $7.50-$15 (попутная монетизация)
```

**Scenario 2: Active Provider**
```
Провайдер: Мощная рабочая станция, 64GB RAM, RTX 4080
Выделяемые ресурсы: 32GB RAM, GPU, 8 CPU cores
Типичная нагрузка: 50-100 задач/день × 80 кредитов avg
Заработок: 4000-8000 кредитов/день × $0.001 = $4-$8/день
Месячный доход: $120-$240/месяц
```

**Scenario 3: Enterprise Provider**
```
Провайдер: Выделенный сервер, 256GB RAM, 2xA100 GPU
Выделяемые ресурсы: 200GB RAM, 2 GPU, 32 CPU cores
Типичная нагрузка: 500+ задач/день × 120 кредитов avg
Заработок: 60,000+ кредитов/день × $0.001 = $60+/день
Месячный доход: $1,800+/месяц (окупает серверные расходы)
```

---

## 3. БЕЗОПАСНОСТЬ И ПРОТИВОДЕЙСТВИЕ ЗЛОУПОТРЕБЛЕНИЯМ

### 3.1 Угрозы и контрмеры

#### **Угроза 1: Malicious Code Execution**
```
Злоумышленник отправляет вредоносный код через LLM

Контрмеры:
1. Sandboxing (Docker/WASM)
   - Каждый Provider запускает выполнение в контейнере
   - Изолирован от основной системы
   
2. Resource Limits (cgroups)
   - Максимум CPU: выделенное + 10%
   - Максимум RAM: выделенное + 10%
   - Максимум disk I/O
   - Максимум network bandwidth
   
3. Syscall Whitelist (eBPF/seccomp)
   - Разрешить только безопасные syscalls
   - Запретить file write, network I/O, device access
   
4. Code Analysis Pre-execution
   - Сканирование полученного контейнера на сигнатуры вирусов
   - ML-based anomaly detection на bytecode
```

#### **Угроза 2: Cryptomining (Hidden Resource Theft)**
```
Провайдер выделяет 4GB RAM, но на самом деле использует 8GB

Контрмеры:
1. Real-time Resource Monitoring
   - cgroups metrics каждые 100ms
   - Отключение провайдера если превышение >5%
   - Штраф на репутацию
   
2. Heartbeat & Health Checks
   - Server пингует провайдера каждые 30s
   - Таймаут = автоматическое отключение
   
3. Billing Audit
   - Провайдер не может выставить счет за неиспользуемые ресурсы
   - Тройная проверка: запрос, выполнение, результат
```

#### **Угроза 3: Denial of Service (DoS)**
```
Массовая отправка пустых/поддельных задач

Контрмеры:
1. Rate Limiting
   - Per-user: 100 requests/minute (standard tier)
   - Per-IP: 10,000 requests/minute
   - Exponential backoff на блокировку
   
2. Task Validation
   - Проверка синтаксиса до маршрутизации
   - Проверка на спам-паттерны (ML)
   
3. Credit Pre-allocation
   - Consumer должен иметь кредиты ДО отправки задачи
   - Блокировка на счете, освобождение после результата
```

#### **Угроза 4: Blockchain/Fraud Avoidance**
```
Провайдер отрицает выполнение задачи

Контрмеры:
1. Cryptographic Proof of Work
   - Task ID = hash(request_params + timestamp + nonce)
   - Provider подписывает результат приватным ключом
   - Server верифицирует подпись
   
2. Immutable Ledger (optional blockchain)
   - Записать в блокчейн: Task ID, Provider, Result Hash
   - Тройная подпись: Consumer, Provider, Server
   - Разрешение споров через smart contract
   
3. Reputation Slashing
   - Провайдер с репутацией < 0.5 = автобан
```

#### **Угроза 5: Data Privacy/Leakage**
```
Провайдер сохраняет копию приватных запросов

Контрмеры:
1. Data Encryption in Transit
   - TLS 1.3+ для всех соединений
   - Perfect Forward Secrecy
   
2. Memory Encryption at Rest (optional)
   - AMD SEV / Intel SGX для критических операций
   - Hardware-backed key storage
   
3. Audit Logging
   - Log all resource access
   - Compliance with GDPR/CCPA
   - User can export/delete logs
   
4. NDA & Legal Terms
   - Провайдер подписывает соглашение о конфиденциальности
   - Штраф за утечку данных
   - Страховка (escrow account)
```

### 3.2 Система репутации и наказания

```
Provider Reputation Score (0.0 - 5.0):

POSITIVE FACTORS:
  +0.1  Task completed successfully
  +0.2  Task completed early (time_saved > 20%)
  +0.3  100+ consecutive tasks without issues
  +0.5  Average rating from consumers > 4.5/5
  +1.0  Security audit passed

NEGATIVE FACTORS (AUTO-ACTIONS):
  -0.1  Task failed / timeout
  -0.3  Resource overuse detected (>10% overage)
  -0.5  Task timeout (20+ min)
  -1.0  Malware/security violation detected
  -2.0  Data breach confirmed
  -5.0  Multiple fraud attempts

SCORE RANGES & ACTIONS:
  >= 4.0: Verified Provider badge, +1.5x earnings multiplier
  2.0-4.0: Standard Provider, 1.0x earnings multiplier
  0.5-2.0: New Provider, 0.5x earnings multiplier, restrictions
  < 0.5: AUTO-BAN, funds locked for 30 days
```

---

## 4. ТЕХНИЧЕСКИЙ СТЕК

### 4.1 Architecture Pattern

```
PROVIDER SIDE:
  ┌─────────────────────────────────────┐
  │     Arvis-Client (Provider Mode)    │
  ├─────────────────────────────────────┤
  │                                     │
  │  ┌──────────────────────────────┐  │
  │  │ LDS Provider Agent           │  │
  │  │ • Monitor resources          │  │
  │  │ • Register with coordinator  │  │
  │  ├──────────────────────────────┤  │
  │  │ Docker Container Runtime     │  │
  │  │ • cgroups + seccomp          │  │
  │  │ • Sandbox execution          │  │
  │  ├──────────────────────────────┤  │
  │  │ Task Executor                │  │
  │  │ • Ollama integration         │  │
  │  │ • Result streaming           │  │
  │  └──────────────────────────────┘  │
  │                                     │
  └──────────────┬──────────────────────┘
                 │ WebSocket / HTTP2
                 │ Task + Results
                 ▼
  ┌──────────────────────────────────────┐
  │       ARVIS SERVER (Coordinator)     │
  ├──────────────────────────────────────┤
  │                                      │
  │  ┌────────────────────────────────┐ │
  │  │ Task Queue & Scheduler          │ │
  │  │ • Redis queue (high throughput) │ │
  │  │ • Task routing algorithm        │ │
  │  ├────────────────────────────────┤ │
  │  │ Resource Registry               │ │
  │  │ • Available providers DB        │ │
  │  │ • Resource allocation tracking  │ │
  │  ├────────────────────────────────┤ │
  │  │ Credit Accounting               │ │
  │  │ • PostgreSQL ledger             │ │
  │  │ • Transaction journal           │ │
  │  ├────────────────────────────────┤ │
  │  │ Monitoring & Analytics          │ │
  │  │ • Prometheus metrics            │ │
  │  │ • Performance dashboards        │ │
  │  └────────────────────────────────┘ │
  │                                      │
  └──────────────┬───────────────────────┘
                 │
                 ▼
  ┌──────────────────────────────────────┐
  │   CONSUMER (Arvis-Client User Mode)  │
  │   • Submit tasks                     │
  │   • Get results                      │
  │   • Track spend                      │
  └──────────────────────────────────────┘
```

### 4.2 API Endpoints (Server side)

```
AUTH & REGISTRATION:
  POST   /api/v1/lds/register-provider     (Register resource provider)
  POST   /api/v1/lds/register-consumer     (Register consumer)
  GET    /api/v1/lds/resources/status      (Provider resource status)
  PUT    /api/v1/lds/resources/allocate    (Allocate resources)

TASK SUBMISSION & EXECUTION:
  POST   /api/v1/lds/tasks/submit          (Consumer submits task)
  GET    /api/v1/lds/tasks/{task_id}       (Get task status)
  WS     /api/v1/lds/tasks/{task_id}/stream (Stream results)
  POST   /api/v1/lds/tasks/{task_id}/cancel (Cancel task)

PROVIDER SIDE:
  GET    /api/v1/lds/provider/tasks        (Get next task to execute)
  POST   /api/v1/lds/provider/tasks/{task_id}/result (Submit result)
  POST   /api/v1/lds/provider/heartbeat    (Keep-alive)
  GET    /api/v1/lds/provider/earnings     (Earnings report)

ACCOUNTING & CREDITS:
  GET    /api/v1/lds/account/balance       (Get credit balance)
  POST   /api/v1/lds/account/purchase      (Buy credits)
  GET    /api/v1/lds/account/transactions  (Transaction history)
  GET    /api/v1/lds/account/reputation    (Reputation score)

ADMIN & MONITORING:
  GET    /api/v1/lds/admin/providers       (List providers)
  GET    /api/v1/lds/admin/tasks           (List all tasks)
  GET    /api/v1/lds/admin/metrics         (System metrics)
  POST   /api/v1/lds/admin/sanctions       (Ban provider)
```

### 4.3 Client-side Implementation (Arvis-Client)

#### **Provider Mode Module** (`src/core/lds_provider.py`)
```python
class LDSProvider:
    """Resource provider agent for LDS"""
    
    def __init__(self, arvis_core):
        self.core = arvis_core
        self.resources_allocated = {}
        self.task_queue = asyncio.Queue()
        self.monitoring_active = False
        
    async def register_provider(self, ram_gb, cpu_cores, gpu=None):
        """Register this machine as resource provider"""
        # 1. Validate hardware
        # 2. Send registration to server
        # 3. Get provider_id + API key
        # 4. Start heartbeat loop
        
    async def execute_task(self, task_payload):
        """Execute received task in sandboxed container"""
        # 1. Parse task
        # 2. Validate security
        # 3. Run in Docker container
        # 4. Stream results back
        # 5. Report metrics
        
    async def monitor_resources(self):
        """Monitor actual vs allocated resources"""
        # 1. Read cgroups metrics
        # 2. Check for overuse
        # 3. Report to server
        # 4. Stop execution if violation
```

#### **Consumer Mode Module** (`src/core/lds_consumer.py`)
```python
class LDSConsumer:
    """LDS task submission and tracking"""
    
    def __init__(self, arvis_core):
        self.core = arvis_core
        self.pending_tasks = {}
        
    async def submit_task(self, llm_request, priority='normal'):
        """Submit task to distributed network"""
        # 1. Calculate cost
        # 2. Check balance
        # 3. Pre-allocate credits
        # 4. Submit to server
        # 5. Return task_id
        
    async def wait_for_result(self, task_id, timeout=300):
        """Wait for task completion with streaming"""
        # 1. Connect to WebSocket stream
        # 2. Stream partial results to UI
        # 3. Return final result
        # 4. Handle timeout/error
        
    async def track_spending(self):
        """Track credit spending over time"""
        # Analytics for user
```

---

## 5. ФАЗЫ РАЗВЕРТЫВАНИЯ

### Фаза 1: MVP (2-3 месяца)
```
✅ Задачи:
  • Basic provider registration
  • Simple task queue (no optimization)
  • Fixed credit pricing
  • Docker sandboxing (basic)
  • Manual dispute resolution
  
❌ Не включать:
  • Blockchain
  • GPU support
  • Auto-scaling
  • ML reputation
  • Redundancy
```

### Фаза 2: Stability (3-4 месяца)
```
✅ Добавить:
  • Intelligent task routing
  • Dynamic pricing (based on supply/demand)
  • GPU support
  • Advanced monitoring
  • Automated reputation scoring
  
❌ Пока не:
  • Blockchain
  • Multi-region deployment
  • Zero-knowledge proofs
```

### Фаза 3: Scale (6+ месяцев)
```
✅ Production features:
  • Blockchain audit log
  • Multi-region deployment
  • Advanced analytics
  • API for 3rd-party integrations
  • Mobile app for providers
  
✅ Optimizations:
  • Task prediction & pre-warming
  • Load balancing algorithms
  • Cost optimization
```

---

## 6. COMPLIANCE & LEGAL

### 6.1 Jurisdictional Considerations

```
REGION          | Framework            | Key Requirements
─────────────────────────────────────────────────────────────
EU              | GDPR                 | Data residency, right to erasure
USA             | Various (state laws) | Tax reporting, 1099s
Ukraine         | Local laws           | Consumer protection, licensing
Russia          | Blocked (sanctions)  | Cannot operate
```

### 6.2 Required Agreements

```
1. Service Terms of Use
   - Liability limitations
   - Acceptable Use Policy
   - IP ownership

2. Provider Agreement
   - Resource lease terms
   - Payment terms
   - Liability caps
   - Security obligations
   - Dispute resolution

3. Consumer Agreement
   - Service level expectations
   - Credit expiration
   - Refund policy
   - Data processing agreement (GDPR)

4. Privacy Policy
   - What data is collected
   - How it's used
   - Retention periods
```

### 6.3 Insurance & Risk Management

```
NEED INSURANCE FOR:
  • Provider equipment damage claims
  • Data breach liability
  • E&O (Errors & Omissions)
  • Professional liability
  • Cyber liability

RISK MITIGATION:
  • Escrow account for disputes (5-10% of monthly volume)
  • Fraud reserve (2-5% of earnings)
  • Security audit budget
  • Legal budget for disputes
```

---

## 7. КОНКУРЕНТНЫЙ АНАЛИЗ

### 7.1 Существующие решения

| Проект | Модель | Экосистема | Статус | 
|--------|--------|-----------|--------|
| Render | GPU marketplace | Python/ML | Live ✅ |
| Lambda Labs | Spot GPUs | ML Training | Live ✅ |
| Vast.ai | GPU rental | Flexible workloads | Live ✅ |
| Akash | Kubernetes marketplace | Containers | Live ✅ |
| Filecoin | Storage sharing | Content delivery | Live ✅ |
| Livepeer | Video processing | Media | Live ✅ |

### 7.2 Преимущества Arvis LDS

```
1. Integrated Ecosystem
   - Не отдельный маркетплейс, а встроенная функция
   - Natural incentive for user base growth
   
2. LLM-Focused
   - Оптимизирована именно для LLM tasks
   - Другие проекты универсальные
   
3. Privacy First
   - На-premises execution в контейнерах
   - Vs. Render/Lambda (cloud-only)
   
4. Regional
   - Фокус на Европе + Украину
   - Избегаем конкуренции с US-фокусированными проектами
```

---

## 8. МЕТРИКИ УСПЕХА

### Фаза 1 (MVP, 3 месяца)

```
Целевые KPI:
  • 500 registered providers
  • 5,000 submitted tasks
  • $10,000 platform GMV (gross merchandise value)
  • 99.0% task success rate
  • < 5% fraud rate
  • < 1h average task completion time
  
Отточить в MVP:
  • Container security
  • Credit accounting accuracy
  • Task routing efficiency
```

### Фаза 2 (Stability, 6 месяцев)

```
Целевые KPI:
  • 5,000 active providers
  • 100,000 monthly tasks
  • $100,000+ monthly GMV
  • 99.5% success rate
  • < 2% fraud rate
  • < 30min average completion
  
Новые метрики:
  • Provider lifetime value (LTV)
  • Consumer churn rate
  • Average provider earnings
  • Cost per task (platform efficiency)
```

### Фаза 3 (Scale, 12 месяцев)

```
Целевые KPI:
  • 50,000+ active providers
  • 1M+ monthly tasks
  • $1M+ monthly GMV
  • 99.9% uptime
  • Multi-region deployment
  
Enterprise metrics:
  • SLA compliance rate
  • Cost savings vs. cloud (AWS/Azure)
  • Provider profitability baseline
```

---

## 9. РИСКАМИ И СМЯГЧЕНИЕ

### Таблица рисков

| Риск | Вероятность | Влияние | Смягчение |
|------|-------------|--------|----------|
| Security breach | HIGH | CRITICAL | Bounty program, audit, insurance |
| Low provider adoption | MEDIUM | HIGH | Early incentives, referral program |
| Regulatory action | LOW | CRITICAL | Legal compliance, jurisdiction selection |
| Blockchain scalability | MEDIUM | MEDIUM | Start without blockchain, add later |
| Task completion failure | HIGH | MEDIUM | Redundancy, fallback providers, retry logic |
| Provider earn-out issue | MEDIUM | MEDIUM | Clear economics, transparent accounting |
| GPU support delays | LOW | MEDIUM | MVP without GPU, add in Phase 2 |

---

## 10. ДОРОЖНАЯ КАРТА ВНЕДРЕНИЯ

### Q4 2024 - Q1 2025: Design & Infrastructure
```
Week 1-4:   Requirements analysis, API design
Week 5-8:   Infrastructure setup (Redis, PostgreSQL, Docker)
Week 9-12:  Security architecture, compliance review
Week 13-16: Prototype & initial testing
```

### Q2 2025: MVP Development
```
✅ Server-side:
  • Task Queue (Redis)
  • Provider Registry
  • Credit Accounting
  • Basic monitoring
  
✅ Client-side:
  • Provider registration UI
  • Consumer task submission UI
  • Result streaming
  • Credit balance display

✅ Testing:
  • 500 provider integration test
  • Stress test (1000 concurrent tasks)
  • Security audit (limited)
```

### Q3 2025: Beta Launch
```
✅ Limited launch to:
  • 200 trusted providers
  • 500 consumers (early access)
  • Internal team + advisors
  
✅ Goals:
  • Validate economics
  • Find bugs
  • Refine task routing
  • Measure success metrics
```

### Q4 2025: Public Launch
```
✅ Full production deployment
✅ Marketing campaign
✅ Community onboarding
✅ Phase 2 planning (GPU, scaling, blockchain)
```

---

## 11. ФИНАНСОВЫЙ ПРОГНОЗ

### Unit Economics (Per Task)

```
Consumer pays:           100 credits
Provider earns:          80 credits (after 20% commission)
Platform cost (infra):   ~5-10 credits
Platform margin:         10-20 credits (10-20%)

Break-even scenario:
  Monthly volume: 10,000 tasks
  Platform GMV: $10,000
  Platform revenue: $1,000-$2,000
  Infrastructure cost: $1,500/month (initial)
  → PROFITABLE at 15,000+ tasks/month
```

### Year 1 Projection

```
Month 1-2:   1,000 tasks/month,    $100/month platform revenue
Month 3-4:   5,000 tasks/month,    $500-$1,000/month
Month 5-6:   20,000 tasks/month,   $2,000-$4,000/month  ← Break-even
Month 7-12:  50,000-100,000/month, $5,000-$20,000/month

Year 1 Total: ~$40,000-$80,000 platform revenue
Year 1 Cost:  ~$18,000 (infrastructure only)
Year 1 Profit: ~$22,000-$62,000
```

---

## 12. ЗАКЛЮЧЕНИЕ И СЛЕДУЮЩИЕ ШАГИ

### Критические вопросы для ответа:

```
1. ✅ Blockchain необходимый?
   → Предложение: MVP без blockchain, добавить в Phase 3

2. ✅ Какой диапазон кредитной стоимости?
   → Предложение: 1 credit = $0.001, регулируемо на основе спроса

3. ✅ Какой процент комиссии платформы?
   → Предложение: 15-20% (competitive с Render/Vast.ai)

4. ✅ Какие регионы/юрисдикции в MVP?
   → Предложение: EU + Ukraine, добавить US в Phase 2

5. ✅ Требуется ли insurance/escrow?
   → Предложение: Yes, 5-10% escrow для disputes, insurance для liability
```

### Рекомендуемые следующие шаги:

1. **Одобрение высокоуровневой архитектуры**
   - Review by core team
   - Feedback on economics
   - Legal review of terms

2. **Детальная спецификация API**
   - OpenAPI/Swagger definition
   - Endpoint examples
   - Error codes

3. **Детальный план безопасности**
   - Penetration testing scope
   - Compliance checklist
   - Audit requirements

4. **Финансовая модель (детальная)**
   - Приобретение юридических услуг
   - Tax implications research
   - Payment processor integration plan

5. **Начало разработки инфраструктуры**
   - Redis/PostgreSQL provisioning
   - Docker registry setup
   - Server framework (FastAPI) skeleton
