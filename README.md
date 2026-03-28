# OpenEnv: Customer Support Ticket Triage

An **OpenEnv**-compliant environment that simulates a customer support ticket queue. AI agents must classify priority, route to the correct department, draft an empathetic response, and decide whether to escalate — scored against human-verified ground truth.

## Why This Matters

| Metric | Impact |
|--------|--------|
| **Cost** | A mis-routed ticket costs 2.5x more to resolve than a correctly routed one |
| **Speed** | A 1-hour delay in P0 response drops CSAT by 15 points |
| **Churn** | 62% of customers who experience poor support handling will not return |
| **Scale** | Mid-size D2C brands process 200-500 tickets/day — manual triage is the biggest L1 time sink |

## Environment Architecture

The environment follows the **OpenEnv** specification with three core API methods:

```
reset(task_id)  → Observation          # Start a new episode
step(action)    → (Obs, Reward, Done, Info)  # Submit triage decision
state()         → State                # Check progress
```

### Observation Space (What the Agent Sees)

| Field | Type | Description |
|-------|------|-------------|
| `ticket_id` | str | Unique identifier |
| `ticket_text` | str | Full body text |
| `subject` | str | Email subject / chat title |
| `customer_name` | str | Customer name |
| `customer_email` | str (email) | Customer contact email |
| `customer_tier` | enum | `standard` \| `premium` \| `enterprise` |
| `channel` | enum | `email` \| `chat` \| `phone` \| `social_media` |
| `timestamp` | datetime | When the ticket was submitted |
| `conversation_history` | list[str] | Previous messages in thread |
| `attachments` | list[str] | Attached filenames |

### Action Space (What the Agent Decides)

| Field | Type | Values |
|-------|------|--------|
| `priority` | enum | `P0` (critical) \| `P1` (high) \| `P2` (medium) \| `P3` (low) |
| `department` | enum | `billing` \| `engineering` \| `product_support` \| `customer_success` \| `legal` \| `security` |
| `response` | str | Draft reply text (50-500 chars recommended) |
| `escalate` | bool | `true` = escalate to manager/specialist |

## Reward Function

Continuous signal from 0.0 to 1.0 with partial credit:

```
reward = 0.40 * priority_score       # 1.0 exact, 0.5 off-by-one, 0.0 otherwise
       + 0.30 * department_score     # 1.0 exact, 0.5 secondary dept match
       + 0.20 * response_score       # F1 keyword overlap with reference
       + 0.10 * escalation_score     # 1.0 exact, 0.0 wrong
       - 0.05 * unnecessary_steps    # penalty for stalling
```

Result clamped to [0.0, 1.0]. Additional penalties apply for missed legal/security escalations.

## Tasks

| Task | Tickets | Expected Score (GPT-4o-mini) | Challenges |
|------|---------|------------------------------|------------|
| **Easy** | 10 | 0.85+ | Clear single-intent, obvious keywords |
| **Medium** | 15 | 0.55-0.70 | Multi-intent, VIP overrides, emotional language |
| **Hard** | 20 | 0.35-0.50 | Sarcasm, legal threats, multi-turn, broken English, adversarial inputs |

## Project Structure

```
openenv-support-triage/
├── openenv.yaml          # Environment metadata & schemas
├── app.py                # FastAPI wrapper (REST API)
├── Dockerfile            # Container for HF Spaces deployment
├── requirements.txt      # Python dependencies
├── src/
│   ├── environment.py    # reset() / step() / state()
│   ├── models.py         # Pydantic: Observation, Action, Reward, State
│   ├── graders.py        # Task-specific grading functions
│   ├── simulator.py      # Ticket queue manager
│   └── rewards.py        # Composite reward computation
├── tasks/
│   ├── task_easy.json    # 10 tickets with ground truth
│   ├── task_medium.json  # 15 tickets with ground truth
│   └── task_hard.json    # 20 tickets with ground truth
├── baseline/
│   └── inference.py      # OpenAI API baseline agent
└── tests/
    ├── test_environment.py
    └── test_validate.py
```

## Setup

### Local Development

```bash
# Clone and install
git clone <repo-url>
cd openenv-support-triage
pip install -r requirements.txt

# Run tests
python -m pytest tests/ -v

# Verify environment
python verify.py

# Run the baseline agent (requires OpenAI API key)
export OPENAI_API_KEY='sk-...'
python -m baseline.inference
```

### Docker

```bash
docker build -t openenv-support-triage .
docker run -p 7860:7860 openenv-support-triage
```

### REST API Endpoints

Once running (locally or in Docker), the API is available at `http://localhost:7860`:

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/reset` | Start new episode. Body: `{"task_id": "easy"}` |
| POST | `/step` | Submit action. Body: `{"priority": "P1", "department": "billing", "response": "...", "escalate": false}` |
| GET | `/state` | Get current progress |
| GET | `/health` | Health check |
| GET | `/docs` | Interactive API documentation (Swagger UI) |

### Deploy to Hugging Face Spaces

1. Create a new Space at huggingface.co/new-space (select **Docker** SDK)
2. Push your code:
   ```bash
   git clone https://huggingface.co/spaces/YOUR_USERNAME/openenv-support-triage
   cd openenv-support-triage
   # copy project files
   git add . && git commit -m "Initial deployment" && git push
   ```
3. Add the `openenv` tag in Space settings
4. Wait for build, then test `/health` endpoint

## Baseline Agent

The baseline agent (`baseline/inference.py`) uses OpenAI's GPT-4o-mini with structured output parsing. Set `OPENAI_MODEL` env var to use a different model.

```bash
export OPENAI_API_KEY='sk-...'
export OPENAI_MODEL='gpt-4o-mini'   # or gpt-4o
python -m baseline.inference
```

### Expected Baseline Scores

| Model | Easy | Medium | Hard |
|-------|------|--------|------|
| GPT-4o-mini | 0.85-0.90 | 0.55-0.70 | 0.35-0.50 |
| GPT-4o | 0.90-0.95 | 0.70-0.80 | 0.50-0.65 |

## Python API Usage

```python
from src.environment import SupportTriageEnv
from src.models import Action

env = SupportTriageEnv()
obs = env.reset("easy")

action = Action(
    priority="P1",
    department="billing",
    response="We will process your refund immediately.",
    escalate=False,
)

next_obs, reward, done, info = env.step(action)
print(f"Score: {reward.score:.2f}")
print(f"State: {env.state()}")
```
