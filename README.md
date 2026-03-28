# OpenEnv: Customer Support Ticket Triage

An **OpenEnv**-compliant environment that simulates a customer support ticket queue. AI agents must classify priority, route to the correct department, draft an empathetic response, and decide whether to escalate — scored against human-verified ground truth.

> **Hackathon submission by Ashish** | Stack: Python + FastAPI + OpenAI API | Deployment: Hugging Face Spaces

---

## Why This Matters

Every company receives support tickets — from password resets to security breaches. A human agent must make four decisions per ticket: **priority**, **department routing**, **response drafting**, and **escalation**. Getting this wrong has real consequences:

| Metric | Impact |
|--------|--------|
| **Cost** | A mis-routed ticket costs 2.5x more to resolve (Zendesk 2024) |
| **Speed** | A 1-hour delay in P0 response drops CSAT by 15 points |
| **Churn** | 62% of customers who experience poor support handling will not return |
| **Scale** | Mid-size D2C brands process 200–500 tickets/day — manual triage is the biggest L1 time sink |

Most AI tools today are one-shot classifiers. This environment trains and evaluates agents that perform the **full triage workflow** — classify, route, respond, and escalate — with measurable, reproducible scoring.

---

## Environment Architecture

Follows the **OpenEnv** specification with three core API methods:

```
reset(task_id)  -> Observation               # Start a new episode
step(action)    -> (Obs, Reward, Done, Info)  # Submit triage decision
state()         -> State                     # Check current progress
```

### Observation Space (What the Agent Sees)

| Field | Type | Description |
|-------|------|-------------|
| `ticket_id` | str | Unique identifier |
| `ticket_text` | str | Full body text of the support ticket |
| `subject` | str | Email subject line or chat title |
| `customer_name` | str | Customer name |
| `customer_email` | str (email) | Customer contact email |
| `customer_tier` | enum | `standard` \| `premium` \| `enterprise` |
| `channel` | enum | `email` \| `chat` \| `phone` \| `social_media` |
| `timestamp` | datetime | When the ticket was submitted |
| `conversation_history` | list[str] | Previous messages in the thread |
| `attachments` | list[str] | Attached filenames |

### Action Space (What the Agent Decides)

| Field | Type | Values |
|-------|------|--------|
| `priority` | enum | `P0` (critical) \| `P1` (high) \| `P2` (medium) \| `P3` (low) |
| `department` | enum | `billing` \| `engineering` \| `product_support` \| `customer_success` \| `legal` \| `security` |
| `response` | str | Draft reply text (50–500 chars recommended) |
| `escalate` | bool | `true` = escalate to manager/specialist |

---

## Reward Function

Continuous signal **0.0 → 1.0** with partial credit at every component:

```
reward = 0.40 * priority_score      # 1.0 exact match, 0.5 off-by-one, 0.0 otherwise
       + 0.30 * department_score    # 1.0 exact match, 0.5 secondary dept match
       + 0.20 * response_score      # F1 keyword overlap with reference response
       + 0.10 * escalation_score    # 1.0 exact match, 0.0 wrong
       - 0.05 * unnecessary_steps   # penalty for stalling
```

- Result clamped to **[0.0, 1.0]**
- **Critical penalty**: `-1.0` if a `legal` or `security` ticket is not escalated
- **Medium extra penalty**: `-0.20` if priority is off by more than 1 level
- **Hard extra penalty**: `-0.30` if escalation decision is wrong

### Example (Easy ticket — duplicate charge)

| Component | Calculation | Score |
|-----------|------------|-------|
| Priority P1 == P1 | exact match | 0.40 × 1.0 = **0.40** |
| Dept billing == billing | exact match | 0.30 × 1.0 = **0.30** |
| Response F1 overlap | precision=0.69, recall=0.26, F1=0.375 | 0.20 × 0.375 = **0.075** |
| Escalate False == False | exact match | 0.10 × 1.0 = **0.10** |
| **Total** | | **0.875** |

---

## Tasks

| Task | Tickets | Key Challenges |
|------|---------|----------------|
| **Easy** | 10 | Clear single-intent, obvious keywords, standard customers |
| **Medium** | 15 | Multi-intent, VIP overrides, emotional language, industry jargon |
| **Hard** | 20 | Sarcasm, legal threats, multi-turn threads, broken English, prompt injection, adversarial inputs |

### Example Tickets

**Easy** — Clear signal, all indicators point the same way:
> *"I placed an order yesterday for a yoga mat (Order #45821, Rs 1,299) but my bank shows two charges. Can you refund the duplicate?"*
> → P1, billing, no escalation

**Medium** — VIP churn signal, three issues in one ticket:
> *"Your latest update broke our bulk import. Also export format changed without notice. We were promised an account manager 3 months ago. We are evaluating alternatives."*
> → P0, engineering + customer_success, escalate

**Hard** — Sarcasm masking a critical data loss + legal threat:
> *"Wow, ticket #882 is now 12 days old. TWELVE. At this point I am documenting everything for my lawyer. But sure, take your time 😊"*
> → P0, engineering + legal, escalate immediately

---

## Actual Baseline Scores (GPT-4o-mini)

Scores recorded on March 28, 2026:

| Model | Easy | Medium | Hard | Notes |
|-------|------|--------|------|-------|
| **GPT-4o-mini** | **0.7324** | **0.5681** | **0.6444** | Measured scores |
| GPT-4o (projected) | 0.90–0.95 | 0.70–0.80 | 0.50–0.65 | Projected |

> Hard (0.6444) exceeded the expected range (0.35–0.50), showing the agent handles sarcasm and adversarial inputs well. Medium (0.5681) is within the expected 0.55–0.70 range.

---

## Project Structure

```
openenv-support-triage/
├── openenv.yaml          # Environment metadata & action/observation schemas
├── app.py                # FastAPI REST wrapper (/reset, /step, /state, /health)
├── Dockerfile            # Container for Hugging Face Spaces (port 7860)
├── requirements.txt      # Python dependencies
├── .env.example          # Environment variable template
├── verify.py             # Manual end-to-end verification script
├── generate_data.py      # Ticket data generation script
├── src/
│   ├── environment.py    # reset() / step() / state() — main OpenEnv interface
│   ├── models.py         # Pydantic: Observation, Action, Reward, State
│   ├── graders.py        # Task-specific grading (easy/medium/hard)
│   ├── simulator.py      # Ticket queue loader and manager
│   ├── rewards.py        # Composite reward computation with full logging
│   └── logger.py         # Centralised logging configuration
├── tasks/
│   ├── task_easy.json    # 10 tickets with ground truth labels
│   ├── task_medium.json  # 15 tickets with ground truth labels
│   └── task_hard.json    # 20 tickets with ground truth labels
├── baseline/
│   └── inference.py      # OpenAI API baseline agent (GPT-4o-mini)
└── tests/
    ├── test_environment.py   # 24 env API tests (reset/step/state/edge cases)
    └── test_validate.py      # 27 schema and data validation tests
```

---

## Setup

### 1. Install dependencies

```bash
git clone <repo-url>
cd openenv-support-triage
pip install -r requirements.txt
```

### 2. Configure environment variables

Copy `.env.example` to `.env` and fill in your OpenAI key:

```bash
cp .env.example .env
```

```env
OPENAI_API_KEY=sk-your-key-here
OPENAI_MODEL=gpt-4o-mini
```

### 3. Run tests

```bash
python -m pytest tests/ -v
# 51 passed
```

### 4. Start the REST API server

```bash
uvicorn app:app --host 0.0.0.0 --port 7860 --reload
```

Open **http://localhost:7860/docs** for the interactive Swagger UI.

### 5. Run the baseline agent

```bash
python -m baseline.inference
```

You will see detailed logs for every reward calculation:

```
23:01:37 | INFO  | environment | STEP 1 | ticket=EASY-1001 | progress=1/10
23:01:37 | INFO  | environment |   Agent decided -> priority=P1, dept=billing, escalate=False
23:01:37 | DEBUG | rewards     |   [PRIORITY]  agent=P1 == truth=P1 -> EXACT MATCH -> score=1.0
23:01:37 | DEBUG | rewards     |   [PRIORITY]  0.40 x 1.00 = 0.4000
23:01:37 | DEBUG | rewards     |   [DEPT]      agent=billing == truth=billing -> EXACT MATCH -> score=1.0
23:01:37 | DEBUG | rewards     |   [RESPONSE]  F1 = 0.3750
23:01:37 | DEBUG | rewards     |   [TOTAL]     0.4000 + 0.3000 + 0.0750 + 0.1000 = 0.8750
23:01:37 | INFO  | graders     | [EASY] final score = 0.8750
```

---

## REST API Endpoints

| Method | Endpoint | Body | Description |
|--------|----------|------|-------------|
| POST | `/reset` | `{"task_id": "easy"}` | Start new episode, returns first Observation |
| POST | `/step` | `{"priority":"P1","department":"billing","response":"...","escalate":false}` | Submit action, returns reward + next ticket |
| GET | `/state` | — | Current progress (tickets processed, score) |
| GET | `/health` | — | Returns `{"status": "ok"}` |
| GET | `/docs` | — | Interactive Swagger UI |

### Quick test via curl

```bash
# 1. Start episode
curl -X POST http://localhost:7860/reset \
  -H "Content-Type: application/json" \
  -d '{"task_id": "easy"}'

# 2. Submit triage decision
curl -X POST http://localhost:7860/step \
  -H "Content-Type: application/json" \
  -d '{"priority":"P1","department":"billing","response":"We will process your refund.","escalate":false}'

# 3. Check progress
curl http://localhost:7860/state
```

---

## Docker

```bash
docker build -t openenv-support-triage .
docker run -p 7860:7860 openenv-support-triage
# Visit http://localhost:7860/health
```

---

## Deploy to Hugging Face Spaces

1. Create a new Space at huggingface.co/new-space — select **Docker** SDK
2. Push your code:
   ```bash
   git clone https://huggingface.co/spaces/YOUR_USERNAME/openenv-support-triage
   cd openenv-support-triage
   git add . && git commit -m "Initial deployment" && git push
   ```
3. Add the `openenv` tag in Space Settings
4. Wait 2–5 minutes for the build, then test:
   ```
   https://YOUR_USERNAME-openenv-support-triage.hf.space/health
   ```

---

## Python API Usage

```python
from src.environment import SupportTriageEnv
from src.models import Action

env = SupportTriageEnv()
obs = env.reset("easy")   # loads 10 easy tickets

action = Action(
    priority="P1",
    department="billing",
    response="We can see the duplicate charge and have initiated a refund.",
    escalate=False,
)

next_obs, reward, done, info = env.step(action)
print(f"Score: {reward.score:.4f}")   # e.g. 0.8750
print(f"State: {env.state()}")
```

---

## Definition of Done

- [x] `reset()` returns valid Observation for all 3 task IDs
- [x] `step()` accepts Action and returns `(Observation, Reward, done, info)`
- [x] `state()` returns progress at any point during an episode
- [x] All 45 tickets have verified ground-truth labels
- [x] Reward function produces values in [0.0, 1.0] for all valid inputs
- [x] Partial credit works (off-by-one priority gives 0.5)
- [x] Baseline `inference.py` runs against all 3 tasks
- [x] Baseline scores recorded (easy=0.7324, medium=0.5681, hard=0.6444)
- [x] Dockerfile builds and serves on port 7860
- [x] 51 tests passing (`pytest tests/ -v`)
- [x] Full DEBUG logging for every reward calculation
- [ ] Deployed to Hugging Face Spaces with `openenv` tag
