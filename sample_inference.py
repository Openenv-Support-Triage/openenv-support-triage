"""
Sample Inference Script — OpenEnv Support Triage
===================================
MANDATORY
- Before submitting, ensure the following variables are defined in your environment:
    API_BASE_URL      The API endpoint for the LLM (OpenAI-compatible).
    MODEL_NAME        The model identifier to use for inference.
    HF_TOKEN          Your Hugging Face / API key.
    PING_URL          Your HF Space base URL (e.g. https://your-space.hf.space)

- Defaults:
    API_BASE_URL = os.getenv("API_BASE_URL", "https://router.huggingface.co/v1")
    MODEL_NAME   = os.getenv("MODEL_NAME", "Qwen/Qwen2.5-72B-Instruct")

- The actual submission file must be named `inference.py` and placed in the repo root.
- All LLM calls must use the OpenAI client with the above variables.

STDOUT FORMAT
- The script must emit exactly three line types to stdout, in this order:

    [START] task=<task_name> env=<benchmark> model=<model_name>
    [STEP]  step=<n> action=<action_str> reward=<0.00> done=<true|false> error=<msg|null>
    [END]   success=<true|false> steps=<n> score=<score> rewards=<r1,r2,...,rn>

  Rules:
    - One [START] line at episode begin.
    - One [STEP] line per step, immediately after env.step() returns.
    - One [END] line after env.close(), always emitted (even on exception).
    - reward and rewards are formatted to 2 decimal places.
    - done and success are lowercase booleans: true or false.
    - error is the raw error string, or null if none.
    - All fields on a single line with no newlines within a line.
    - Each task returns score in [0, 1].

  Example:
    [START] task=easy env=support-triage model=Qwen2.5-72B-Instruct
    [STEP] step=1 action=priority=P2,dept=billing,escalate=false reward=0.75 done=false error=null
    [STEP] step=2 action=priority=P0,dept=engineering,escalate=true reward=0.90 done=true error=null
    [END] success=true steps=2 score=0.83 rewards=0.75,0.90
"""

import os
import textwrap
from typing import List, Optional

import requests
from openai import OpenAI

API_KEY = os.getenv("HF_TOKEN") or os.getenv("API_KEY", "dummy_key")
API_BASE_URL = os.getenv("API_BASE_URL", "https://router.huggingface.co/v1")
MODEL_NAME = os.getenv("MODEL_NAME", "Qwen/Qwen2.5-72B-Instruct")
PING_URL = os.getenv("PING_URL", "http://localhost:8000").rstrip("/")

TASK_NAME = os.getenv("SUPPORT_TRIAGE_TASK", "easy")   # easy | medium | hard
BENCHMARK = "support-triage"
SUCCESS_SCORE_THRESHOLD = 0.5

SYSTEM_PROMPT = textwrap.dedent("""
    You are a customer support triage agent. For each ticket, decide:

    1. priority: P0 (critical — security breach, data loss, production down),
                 P1 (high — financial impact, service degradation),
                 P2 (medium — standard issues),
                 P3 (low — questions, feedback)
    2. department: billing | engineering | product_support | customer_success | legal | security
    3. response: concise, empathetic draft reply (50-500 characters)
    4. escalate: true if manager/specialist needed, false otherwise

    Key rules:
    - Enterprise customers with production down = P0
    - Legal threats or lawyer mentions → escalate immediately
    - Sarcasm often masks serious anger — read between the lines
    - "Evaluating alternatives" from enterprise = churn risk = escalate

    Reply in this exact JSON format (no extra text):
    {
      "priority": "<P0|P1|P2|P3>",
      "department": "<billing|engineering|product_support|customer_success|legal|security>",
      "response": "<your draft reply>",
      "escalate": <true|false>
    }
""").strip()


# ── stdout helpers ────────────────────────────────────────────────────────────

def log_start(task: str, env: str, model: str) -> None:
    print(f"[START] task={task} env={env} model={model}", flush=True)


def log_step(step: int, action: str, reward: float, done: bool, error: Optional[str]) -> None:
    error_val = error if error else "null"
    print(
        f"[STEP] step={step} action={action} reward={reward:.2f} "
        f"done={str(done).lower()} error={error_val}",
        flush=True,
    )


def log_end(success: bool, steps: int, score: float, rewards: List[float]) -> None:
    rewards_str = ",".join(f"{r:.2f}" for r in rewards)
    print(
        f"[END] success={str(success).lower()} steps={steps} "
        f"score={score:.3f} rewards={rewards_str}",
        flush=True,
    )


# ── environment HTTP helpers ──────────────────────────────────────────────────

def env_reset(task_id: str) -> dict:
    resp = requests.post(f"{PING_URL}/reset", json={"task_id": task_id}, timeout=30)
    resp.raise_for_status()
    return resp.json()


def env_step(action: dict) -> dict:
    resp = requests.post(f"{PING_URL}/step", json=action, timeout=30)
    resp.raise_for_status()
    return resp.json()


# ── LLM action ───────────────────────────────────────────────────────────────

def get_action(client: OpenAI, obs: dict) -> dict:
    ticket_info = (
        f"Ticket ID: {obs.get('ticket_id', 'unknown')}\n"
        f"Subject: {obs.get('subject', '')}\n"
        f"From: {obs.get('customer_name', '')} ({obs.get('customer_email', '')})\n"
        f"Tier: {obs.get('customer_tier', 'standard')}\n"
        f"Channel: {obs.get('channel', 'email')}\n"
        f"Body:\n{obs.get('ticket_text', '')}\n"
    )
    history = obs.get("conversation_history", [])
    if history:
        ticket_info += "Conversation History:\n" + "\n".join(f"  - {m}" for m in history) + "\n"
    attachments = obs.get("attachments", [])
    if attachments:
        ticket_info += f"Attachments: {', '.join(attachments)}\n"

    try:
        import json
        completion = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": ticket_info},
            ],
            temperature=0.0,
            max_tokens=300,
        )
        text = (completion.choices[0].message.content or "").strip()
        return json.loads(text)
    except Exception as exc:
        print(f"[DEBUG] Model request failed: {exc}", flush=True)
        return {
            "priority": "P2",
            "department": "product_support",
            "response": "We have received your ticket and are looking into it.",
            "escalate": False,
        }


def action_summary(action: dict) -> str:
    return (
        f"priority={action.get('priority','?')},"
        f"dept={action.get('department','?')},"
        f"escalate={str(action.get('escalate', False)).lower()}"
    )


# ── main loop ─────────────────────────────────────────────────────────────────

def main() -> None:
    client = OpenAI(base_url=API_BASE_URL, api_key=API_KEY)

    rewards: List[float] = []
    steps_taken = 0
    score = 0.0
    success = False

    log_start(task=TASK_NAME, env=BENCHMARK, model=MODEL_NAME)

    try:
        obs = env_reset(TASK_NAME)
        done = False

        while not done:
            action = get_action(client, obs)
            result = env_step(action)

            reward_obj = result.get("reward", {})
            reward = float(reward_obj.get("score", 0.0))
            done = result.get("done", True)
            next_obs = result.get("observation")
            error = None

            rewards.append(reward)
            steps_taken += 1

            log_step(
                step=steps_taken,
                action=action_summary(action),
                reward=reward,
                done=done,
                error=error,
            )

            if next_obs:
                obs = next_obs

        score = sum(rewards) / max(len(rewards), 1)
        score = min(max(score, 0.0), 1.0)
        success = score >= SUCCESS_SCORE_THRESHOLD

    except Exception as exc:
        print(f"[DEBUG] Episode error: {exc}", flush=True)
    finally:
        log_end(success=success, steps=steps_taken, score=score, rewards=rewards)


if __name__ == "__main__":
    main()
