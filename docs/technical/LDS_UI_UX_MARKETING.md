# 🎨 Система "Распределения нагрузки": UI/UX и маркетинг

---

## ЧАСТЬ 1: USER INTERFACE DESIGN

### 1.1 Provider Dashboard

```
┌─────────────────────────────────────────────────────────────┐
│  ARVIS LDS • Provider Dashboard                        [☰]   │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────────────┐  ┌──────────────────┐               │
│  │ Your Allocation  │  │ Reputation Score │               │
│  │                  │  │                  │               │
│  │ RAM: 4.2 / 8 GB  │  │      ⭐⭐⭐⭐☆     │               │
│  │ CPU: 1.8 / 2     │  │      4.2 / 5.0   │               │
│  │ GPU: 0 / 1       │  │   +0.1 this week │               │
│  └──────────────────┘  └──────────────────┘               │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │ Earnings This Week                                   │   │
│  │                                                        │   │
│  │  ██████░░░░  250 CREDITS  ($0.25)                   │   │
│  │  Progress to next tier: Verified Provider           │   │
│  │  15 more completed tasks needed (currently 85/100)  │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │ Active Tasks (3)                                     │   │
│  ├──────────────────────────────────────────────────────┤   │
│  │                                                        │   │
│  │ [🟢] Task #12345  Mistral 7B     35 credits         │   │
│  │     ▓▓▓▓▓░░░░ 50% (2.5 / 5.0 sec)                   │   │
│  │     Prompt: "Write Python script for..."             │   │
│  │                                                        │   │
│  │ [🟡] Task #12346  Code-Llama 34B  85 credits        │   │
│  │     ▓▓▓▓░░░░░░ 40% (8.3 / 20.0 sec)                 │   │
│  │     Prompt: "Debug this function..."                 │   │
│  │                                                        │   │
│  │ [🟡] Task #12347  Gemma 2B        15 credits        │   │
│  │     ▓░░░░░░░░░ 10% (0.5 / 5.0 sec)                  │   │
│  │     Prompt: "Summarize: [article]..."               │   │
│  │                                                        │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                              │
│  [ Settings ]  [ View Earnings ]  [ Help ]                  │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### 1.2 Consumer - Task Submission UI

```
┌─────────────────────────────────────────────────────────────┐
│  ARVIS LDS • Submit Task                              [☰]   │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  Your Balance: 💎 1,250 credits  [ Buy More ]              │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │ SELECT MODEL                                         │   │
│  ├──────────────────────────────────────────────────────┤   │
│  │                                                        │   │
│  │  ◉ Mistral 7B (Fast, Balanced)                       │   │
│  │     Cost: ~30 credits per prompt                     │   │
│  │     Speed: ~10 sec / 256 tokens                      │   │
│  │     Best for: General tasks, code review             │   │
│  │                                                        │   │
│  │  ○ Code-Llama 34B (Code Specialist)                 │   │
│  │     Cost: ~80 credits per prompt                     │   │
│  │     Speed: ~30 sec / 256 tokens                      │   │
│  │     Best for: Programming tasks                      │   │
│  │                                                        │   │
│  │  ○ Gemma 2B (Ultra-fast, Lightweight)               │   │
│  │     Cost: ~15 credits per prompt                     │   │
│  │     Speed: ~3 sec / 256 tokens                       │   │
│  │     Best for: Quick answers, summaries               │   │
│  │                                                        │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │ YOUR PROMPT                                          │   │
│  ├──────────────────────────────────────────────────────┤   │
│  │                                                        │   │
│  │  ┌─────────────────────────────────────────────────┐ │   │
│  │  │ Write a Python function to parse JSON and      │ │   │
│  │  │ return keys that have numeric values. Include  │ │   │
│  │  │ error handling.                                │ │   │
│  │  │                                                 │ │   │
│  │  │ [word count: 32]                               │ │   │
│  │  └─────────────────────────────────────────────────┘ │   │
│  │                                                        │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │ ADVANCED SETTINGS                                    │   │
│  ├──────────────────────────────────────────────────────┤   │
│  │                                                        │   │
│  │  Max Tokens:       256  [—————•——]                  │   │
│  │  Temperature:      0.7  [——•————]                  │   │
│  │  Priority:         Normal  ▼  (affects queue)       │   │
│  │  Timeout:          5 min                             │   │
│  │                                                        │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                              │
│  Estimated Cost: 30 credits (~$0.03)                       │
│  Estimated Wait: < 10 seconds                             │
│                                                              │
│  [ Cancel ]  [ ⚡ Submit (30 credits) ]                     │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### 1.3 Task Results Streaming UI

```
┌─────────────────────────────────────────────────────────────┐
│  ARVIS LDS • Task Results                             [☰]   │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  Task #12349  [🟢 COMPLETED]  15 sec   Cost: 28 credits   │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │ PROMPT                                               │   │
│  ├──────────────────────────────────────────────────────┤   │
│  │ Write a Python function to parse JSON and return    │   │
│  │ keys that have numeric values. Include error        │   │
│  │ handling.                                            │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │ RESULT (Streaming: 115/256 tokens)                 │   │
│  ├──────────────────────────────────────────────────────┤   │
│  │                                                        │   │
│  │ def extract_numeric_keys(json_data):                 │   │
│  │     """Extract keys with numeric values from JSON""" │   │
│  │     try:                                              │   │
│  │         if isinstance(json_data, str):               │   │
│  │             json_data = json.loads(json_data)        │   │
│  │                                                        │   │
│  │         numeric_keys = []                             │   │
│  │         for key, value in json_data.items():         │   │
│  │             if isinstance(value,                      │   │
│  │                            (int, float)):             │   │
│  │                 numeric_keys.append(key)              │   │
│  │         return numeric_keys                           │   │
│  │     except (json.JSONDecodeError,                     │   │
│  │             AttributeError) as e:                     │   │
│  │         print(f"Error: {e}")                          │   │
│  │         return []                                      │   │
│  │                                                        │   │
│  │ ▌ [TYPING...]                                        │   │
│  │                                                        │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │ Task Details                                         │   │
│  │ Provider: Verified (⭐⭐⭐⭐☆ 4.2/5.0)                │   │
│  │ Execution Time: 14.8 sec                             │   │
│  │ Tokens Generated: 115 / 256 max                      │   │
│  │ Energy Cost: ~2.5 kWh equivalent                     │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                              │
│  [ Copy ]  [ Export ]  [ Share ]  [ Download ]              │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### 1.4 Settings & Allocation UI (Provider)

```
┌─────────────────────────────────────────────────────────────┐
│  ARVIS LDS • Provider Settings                         [☰]   │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │ RESOURCE ALLOCATION                                 │   │
│  ├──────────────────────────────────────────────────────┤   │
│  │                                                        │   │
│  │  Total Available:          32 GB RAM / 16 CPU cores  │   │
│  │                                                        │   │
│  │  🟨 Allocate to LDS:                                 │   │
│  │                                                        │   │
│  │  RAM:  [█████•░░░░░░░░░░░░░░░░░░░░░░░░]             │   │
│  │        8 GB / 32 GB allocated (⚠️ 25% - conservative) │   │
│  │                                                        │   │
│  │  CPU:  [██•░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░]     │   │
│  │        2 cores / 16 allocated                        │   │
│  │                                                        │   │
│  │  GPU:  ○ None available                              │   │
│  │        ◉ No GPU allocated                            │   │
│  │        ○ Allocate GPU [Not available]                │   │
│  │                                                        │   │
│  │  ⓘ Allocated resources are reserved exclusively for  │   │
│  │    LDS tasks. Your own usage remains unaffected.     │   │
│  │                                                        │   │
│  │  ⚠️ High allocation increases earnings but may       │   │
│  │    impact system responsiveness                      │   │
│  │                                                        │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │ PERFORMANCE                                          │   │
│  ├──────────────────────────────────────────────────────┤   │
│  │                                                        │   │
│  │  Uptime Target:        95% minimum                   │   │
│  │  Current Uptime:       99.2% ✅                       │   │
│  │                                                        │   │
│  │  Average Task Time:    18.4 seconds                  │   │
│  │  Success Rate:         98.7% ✅                       │   │
│  │                                                        │   │
│  │  Last Heartbeat:       2 seconds ago ✅               │   │
│  │  Connection Status:    🟢 Stable                     │   │
│  │                                                        │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │ SECURITY & PRIVACY                                  │   │
│  ├──────────────────────────────────────────────────────┤   │
│  │                                                        │   │
│  │  ✓ Data Encryption (TLS 1.3)                         │   │
│  │  ✓ Task Isolation (Docker Sandbox)                   │   │
│  │  ✓ Resource Limits (cgroups)                         │   │
│  │  ✓ Syscall Whitelist (seccomp)                       │   │
│  │                                                        │   │
│  │  [ View Privacy Policy ]                             │   │
│  │  [ Download Security Audit ]                         │   │
│  │                                                        │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                              │
│  [ Save Changes ]  [ Reset ]  [ Disable LDS ]              │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

---

## ЧАСТЬ 2: USER EXPERIENCE FLOWS

### 2.1 Provider Onboarding Flow

```
START
  │
  ├─→ [1] Welcome Screen
  │       - Explain what LDS is
  │       - Show earnings potential
  │       - Security promise
  │
  ├─→ [2] Hardware Detection
  │       - Scan CPU cores, RAM, GPU
  │       - Display detection results
  │       - Allow manual override
  │
  ├─→ [3] Resource Allocation
  │       - Show system load
  │       - Recommend allocation (25% safe default)
  │       - User selects: RAM + CPU cores
  │
  ├─→ [4] Security & Privacy Acknowledgement
  │       ✓ Read ToS
  │       ✓ Read DPA (GDPR)
  │       ✓ Confirm no mining/malware
  │
  ├─→ [5] Account Linking
  │       - Connect to user account
  │       - Generate API key
  │       - Set withdrawal payment method
  │
  ├─→ [6] Testing Phase
  │       - Run health check
  │       - Measure latency to server
  │       - First test task (auto-paid)
  │       - Show results
  │
  ├─→ [7] Activation
  │       - Start heartbeat/monitoring
  │       - Show earnings dashboard
  │       - Display waiting tasks
  │
  └─→ SUCCESS (Provider Active)
```

### 2.2 Consumer Task Submission Flow

```
START
  │
  ├─→ [1] Check Balance
  │       if balance < estimated_cost:
  │           └─→ Show "Buy Credits" dialog
  │               └─→ Payment processor (Stripe/PayPal)
  │               └─→ Back to [1]
  │
  ├─→ [2] Select Model
  │       - Display options with cost/speed tradeoff
  │       - Show recommendations based on prompt
  │
  ├─→ [3] Enter Prompt
  │       - Text input with live word count
  │       - Auto-detect prompt category (code/text/data)
  │       - Show relevant model suggestions
  │
  ├─→ [4] Advanced Settings (Optional)
  │       - Temperature
  │       - Max tokens
  │       - Priority (affects wait time + cost)
  │       - Timeout
  │
  ├─→ [5] Review & Confirm
  │       - Show total cost
  │       - Show estimated wait time
  │       - Explain: credits will be reserved
  │
  ├─→ [6] Submit
  │       - Reserve credits
  │       - Send to server
  │       - Get task_id
  │       - Transition to results view
  │
  ├─→ [7] Results Streaming
  │       - Show live status (pending/assigned/running)
  │       - Stream partial results as they arrive
  │       - Show provider info (reputation)
  │       - Auto-complete when done
  │
  ├─→ [8] Post-Processing
  │       - Finalize credits charge
  │       - Rate provider (optional)
  │       - Export/Share options
  │       - Suggest related features
  │
  └─→ SUCCESS (Results Saved)
```

---

## ЧАСТЬ 3: MARKETING & MONETIZATION

### 3.1 Launch Marketing Strategy

#### **Phase 1: Awareness (Months 1-2)**

```
TARGET AUDIENCE:
  1. Existing Arvis users (best conversion)
  2. Developers (Python, ML, crypto communities)
  3. Distributed computing enthusiasts
  4. Gamers with idle GPU capacity
  5. Data scientists / ML researchers

CHANNELS:

1. Product Launch
   • Blog post: "Monetize Your Computer, Support AI Research"
   • HN submission: "Show HN: Distributed LLM Marketplace"
   • Reddit: r/MachineLearning, r/SideHustle, r/learnprogramming
   • GitHub: Star, discussions
   
2. Community Engagement
   • Discord: Arvis community + ML communities
   • Twitter: Threads about LDS economics
   • LinkedIn: B2B angle (enterprise providers)
   
3. Content Creation
   • Tutorial: "How to Set Up Your First Task (5 min)"
   • Blog: "Why LDS is Fairer Than Cloud GPU Rental"
   • YouTube: Demo video (2-3 minutes)
   • Twitter: Daily tips, earnings screenshots
   
4. Partnerships
   • Contact ML framework communities (PyTorch, TensorFlow)
   • Reach out to hardware companies (NVIDIA, AMD)
   • Partner with productivity apps (VSCode extensions?)
   
BUDGET: ~$3,000-5,000 (mostly content creation, no paid ads yet)

GOALS (End of Phase 1):
  • 500+ registered providers
  • 50+ daily active tasks
  • 1,000+ social media followers
  • $5,000-10,000 monthly GMV
```

#### **Phase 2: Growth (Months 3-6)**

```
STRATEGY: Convert awareness to adoption, build reputation

1. Early Adopter Program
   • 10% bonus credits for first 1,000 signups
   • Referral program: 5% commission
   • Provider cashback: 20% bonus for first week
   
2. Enterprise Partnerships
   • Offer volume discounts to companies using Ollama/LLM
   • B2B SaaS angle: "Reduce AI infrastructure costs"
   • API integration examples
   
3. Events & Sponsorships
   • Sponsor local AI/Dev meetups
   • Conference booths (PyCon, AI summits)
   • Hackathons (provide free task credits)
   
4. Content Marketing
   • Case studies: "From $100/month cloud bill to $0"
   • Earnings reports: Transparent data on provider income
   • Security blog: "How We Protect Your Data" (build trust)
   
5. Press & PR
   • Tech press outreach (TechCrunch, VentureBeat)
   • Podcast interviews (AI, crypto, startup podcasts)
   • Newsletter sponsorships (Python Weekly, Indie Hackers)
   
BUDGET: ~$15,000-25,000 (sponsorships, PR agency, paid ads)

GOALS (End of Phase 2):
  • 5,000+ registered providers
  • 100+ daily active tasks
  • $50,000-100,000 monthly GMV
  • 0.5% platform market penetration (vs. AWS/Azure)
```

### 3.2 Pricing Model & Tiering

#### **Option A: Freemium (Recommended for MVP)**

```
TIER           COST    FEATURES
──────────────────────────────────────────────────────
Free           $0      • Consumer: 10 free tasks/month
                       • Provider: Not available

Professional   $4.99/mo • Consumer: Unlimited tasks
                         • 1,000 credits/month
                         • Join waiting list for provider
                         
LDS Provider   $14.99/mo • All Professional features
                         • Allocate resources
                         • Earn credits from tasks
                         • Priority task queue access
                         • Reputation tracking
                         
Enterprise     $99/mo   • Custom allocations (up to 256GB RAM)
                        • Dedicated support
                        • SLA (99.5% uptime)
                        • Volume discounts (coming later)
```

#### **Option B: Pure Freemium (For market penetration)**

```
Consumer: Always Free
  - Basic tier: 100 credits/month free
  - Premium: Unlimited for $9.99/month

Provider: Free to Join
  - No subscription fee
  - 100% earn from tasks (minus 15% platform fee)
  - Incentive: Reputation milestones unlock higher earnings multiplier
```

### 3.3 Revenue Projections (Year 1)

```
MONTH 1-2 (MVP Launch)
  Platform GMV:        $5,000
  Platform Revenue:    $500 (10% fee)
  Infrastructure Cost: $1,500
  NET:                 -$1,000/month

MONTH 3-4 (Growth)
  Platform GMV:        $40,000
  Platform Revenue:    $4,000 (10% fee)
  Infrastructure Cost: $2,000
  NET:                 +$2,000/month

MONTH 5-6 (Scale)
  Platform GMV:        $100,000
  Platform Revenue:    $10,000
  Infrastructure Cost: $3,000
  NET:                 +$7,000/month

MONTH 7-12 (Maturity)
  Platform GMV:        $300,000-500,000
  Platform Revenue:    $30,000-50,000
  Infrastructure Cost: $5,000
  NET:                 +$25,000-45,000/month

YEAR 1 TOTAL:
  Annual Revenue:      ~$50,000-75,000
  Annual Costs:        ~$25,000-35,000 (infrastructure + ops)
  Year 1 Profit:       ~$25,000-40,000
  
  Break-even:         Month 5
```

### 3.4 Competitive Positioning

```
vs. Vast.ai / Render / Lambda Labs:

ARVIS LDS ADVANTAGES:
✅ Integrated into AI assistant (network effects)
✅ Privacy-first (on-prem execution)
✅ Lower overhead for home users
✅ Regional focus (EU/Ukraine advantage)
✅ Transparent economics
✅ Community-driven

ARVIS LDS DISADVANTAGES:
❌ Smaller initial user base
❌ No GPU support yet (Phase 2)
❌ Newer platform (reputation building)
❌ Smaller ecosystem

POSITIONING: "Distributed LLM for Everyone"
  vs. "Professional GPU Marketplace"
```

---

## ЧАСТЬ 4: CUSTOMER RETENTION

### 4.1 Provider Retention Tactics

```
GOAL: Reduce provider churn, increase earnings loyalty

1. Reputation Gamification
   ✓ Milestone badges (10 tasks, 100 tasks, 1000 tasks)
   ✓ Public leaderboards (top providers by earnings/uptime)
   ✓ Achievement notifications ("You reached 4.5 stars!")
   ✓ Reputation tiers with increasing earnings multipliers
   
2. Loyalty Program
   ✓ Referral bonuses (5% commission for life)
   ✓ Long-term provider bonuses (1 year = +10% earnings)
   ✓ Consistency rewards (99%+ uptime = +20% for month)
   ✓ Seasonal bonuses (holiday boosts)
   
3. Communication
   ✓ Monthly earnings reports (email + dashboard)
   ✓ Tips for optimization ("Increase earnings by allocating GPU")
   ✓ Community spotlights ("Provider of the Month")
   ✓ Early access to new features
   
4. Support & Education
   ✓ Dedicated support channel (Slack/Discord)
   ✓ Knowledge base (troubleshooting, optimization)
   ✓ Weekly webinars (earnings strategies, security)
   ✓ 1-on-1 onboarding for high-earners
   
5. Payment & Conversion
   ✓ Weekly withdrawal (not monthly)
   ✓ Low withdrawal minimum ($5 not $100)
   ✓ Multiple payment options (PayPal, Crypto, Bank)
   ✓ Withdrawal bonuses (2x multiplier on first withdrawal)
```

### 4.2 Consumer Retention Tactics

```
GOAL: Increase task submission frequency, credit purchases

1. Task Credit Bundles
   ✓ Buy 100 credits = get 10 free (10% bonus)
   ✓ Subscribe to 500/month = get 50 free (10% bonus)
   ✓ Loyalty tiers (spend $100 → get permanent 5% discount)
   
2. Personalization
   ✓ Model recommendations based on task history
   ✓ Quick shortcuts for frequent tasks
   ✓ Saved prompts & settings
   ✓ Task templates ("code review", "summarization", etc.)
   
3. Results Enhancement
   ✓ Export to multiple formats (Markdown, PDF, JSON)
   ✓ Integration with tools (VSCode, Jupyter, Notion)
   ✓ History & search of past results
   ✓ Share results with team members
   
4. Community Features
   ✓ Share prompts & results with others
   ✓ Rate tasks for quality/speed
   ✓ Leaderboards (top prompt engineers)
   ✓ Community showcase ("Best Results")
   
5. Education
   ✓ Prompt engineering tips
   ✓ Model comparison guide
   ✓ Cost optimization strategies
   ✓ Integration tutorials
```

---

## ЧАСТЬ 5: SUCCESS METRICS

### 5.1 Provider Metrics (KPIs)

```
ACQUISITION:
  • New providers/month
  • Signup-to-allocation rate (% who set up resources)
  • Time to first task (hours)
  
ENGAGEMENT:
  • Daily active providers (DAP)
  • Avg tasks completed per provider/day
  • Avg uptime (%)
  • Repeat submission rate
  
MONETIZATION:
  • Average provider earnings/month
  • Provider lifetime value (LTV)
  • Payout requests volume
  • Referral conversion rate
  
QUALITY:
  • Task success rate (%)
  • Provider rating (1-5 stars)
  • Complaint rate
  • Reputation score distribution
  
RETENTION:
  • Provider churn rate (% who stop per month)
  • 30-day retention
  • 90-day retention
  • Average provider lifetime (days)
```

### 5.2 Consumer Metrics (KPIs)

```
ACQUISITION:
  • New consumers/month
  • Trial-to-paying conversion rate
  • Time to first credit purchase
  
ENGAGEMENT:
  • Daily active consumers (DAC)
  • Tasks submitted per consumer per month
  • Avg session duration
  • Feature adoption rate (advanced settings)
  
MONETIZATION:
  • Average revenue per consumer (ARPC)
  • Consumer lifetime value (LTV)
  • Credit purchase frequency
  • Avg order value (AOV)
  
SATISFACTION:
  • Result quality rating
  • Provider rating distribution
  • NPS (Net Promoter Score)
  • Support ticket volume
  
RETENTION:
  • Consumer churn rate
  • 30-day retention
  • 90-day retention
  • Repeat purchase rate
```

### 5.3 Platform Metrics

```
VOLUME:
  • Total tasks processed
  • Total credits transacted
  • Platform GMV
  • Total provider pool (active)
  • Total consumer pool (active)
  
QUALITY:
  • Overall success rate (%)
  • Average task completion time
  • Provider availability (% online)
  • Task timeout rate (%)
  
ECONOMICS:
  • Platform margin (%)
  • Customer acquisition cost (CAC)
  • Provider acquisition cost
  • Operating expenses
  • Platform profitability
  
STABILITY:
  • Uptime (99.x%)
  • P95 task completion time
  • Chargebacks/fraud rate
  • SLA compliance
```

---

## ЗАКЛЮЧЕНИЕ

Документ охватывает:

1. ✅ **UI/UX дизайн** (Provider dashboard, Consumer flows, Settings)
2. ✅ **User flows** (Onboarding, Task submission, Results)
3. ✅ **Marketing стратегия** (Phase 1-2, Positioning, Budget)
4. ✅ **Monetization** (Pricing tiers, Revenue projections)
5. ✅ **Retention** (Gamification, Loyalty programs)
6. ✅ **Success metrics** (KPIs for tracking)

### Критические вопросы:

```
Q1: Freemium или Pure subscription?
A:  Рекомендуется Pure freemium + optional tier upgrade
    (Consumers: free + premium)
    (Providers: free to join)

Q2: Какова минимальная выплата провайдерам?
A:  Рекомендуется: $5 (для удерживания провайдеров)

Q3: Какой процент комиссии 15% / 20%?
A:  15% конкурентна с Vast.ai, 20% безопаснее для margins

Q4: Когда добавить GPU поддержку?
A:  Phase 2 (месяцы 4-6 после MVP)

Q5: Блокчейн необходим для лонча?
A:  Нет, добавить в Phase 3 для зрелости экосистемы
```
