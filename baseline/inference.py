"""
Baseline agent for the OpenEnv Support Triage environment.
Uses OpenAI API (GPT-4o-mini by default) to make triage decisions.

Usage:
    export OPENAI_API_KEY='sk-...'
    python -m baseline.inference
"""
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from openai import OpenAI
from pydantic import BaseModel

from src.environment import SupportTriageEnv
from src.models import Action, Priority, Department


class AgentResponse(BaseModel):
    thoughts: str
    action: Action


SYSTEM_PROMPT = """You are a customer support triage agent. For each ticket, you must decide:

1. **Priority**: P0 (critical - security breach, data loss, production down), P1 (high - financial impact, service degradation), P2 (medium - standard issues), P3 (low - questions, feedback)
2. **Department**: billing, engineering, product_support, customer_success, legal, security
3. **Response**: A concise, empathetic draft reply (50-500 characters)
4. **Escalate**: true if manager/specialist needed (legal threats, VIP churn risk, data breach, repeated failures)

Key rules:
- VIP/enterprise customers with production issues = P0
- Legal threats or mentions of lawyers = escalate immediately
- Sarcasm often masks serious anger — read between the lines
- Multi-intent tickets: route to primary department, note secondary
- "Evaluating alternatives" from enterprise = churn signal = escalate
- Empty ticket body with legal attachments = P0 + legal + escalate"""


class SupportAgent:
    def __init__(self, model_name: str = "gpt-4o-mini"):
        self.model_name = model_name
        self.client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY", "dummy_key"))

    def get_action(self, observation) -> Action:
        ticket_info = (
            f"Ticket ID: {observation.ticket_id}\n"
            f"Subject: {observation.subject}\n"
            f"From: {observation.customer_name} ({observation.customer_email})\n"
            f"Tier: {observation.customer_tier.value}\n"
            f"Channel: {observation.channel.value}\n"
            f"Body: {observation.ticket_text}\n"
        )
        if observation.conversation_history:
            ticket_info += f"Conversation History:\n" + "\n".join(f"  - {msg}" for msg in observation.conversation_history) + "\n"
        if observation.attachments:
            ticket_info += f"Attachments: {', '.join(observation.attachments)}\n"

        try:
            response = self.client.beta.chat.completions.parse(
                model=self.model_name,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": ticket_info},
                ],
                response_format=AgentResponse,
                temperature=0.0,
            )
            return response.choices[0].message.parsed.action
        except Exception as e:
            print(f"  Agent error on {observation.ticket_id}: {e}")
            return Action(
                priority=Priority.P2,
                department=Department.product_support,
                response="We have received your ticket and are looking into it.",
                escalate=False,
            )


def run_evaluation(task_id: str, agent: SupportAgent):
    env = SupportTriageEnv()
    try:
        obs = env.reset(task_id)
    except Exception as e:
        print(f"Task '{task_id}' could not be started: {e}")
        return

    print(f"\n{'='*60}")
    print(f"  Task: {task_id.upper()}")
    print(f"{'='*60}")

    done = False
    while not done:
        action = agent.get_action(obs)
        next_obs, reward, done, info = env.step(action)
        print(f"  {obs.ticket_id:12s} | Score: {reward.score:.2f} | {action.priority.value} | {action.department.value} | Esc: {action.escalate}")
        obs = next_obs

    state = env.state()
    avg = state.cumulative_score / max(1, state.tickets_processed)
    print(f"\n  Processed: {state.tickets_processed}/{state.total_tickets}")
    print(f"  Cumulative Score: {state.cumulative_score:.2f}")
    print(f"  Average Score: {avg:.3f}")
    return avg


if __name__ == "__main__":
    if "OPENAI_API_KEY" not in os.environ:
        print("WARNING: OPENAI_API_KEY not set. Agent will use fallback actions on API failure.\n")

    model = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")
    agent = SupportAgent(model_name=model)

    scores = {}
    for task_id in ["easy", "medium", "hard"]:
        scores[task_id] = run_evaluation(task_id, agent)

    print(f"\n{'='*60}")
    print("  SUMMARY")
    print(f"{'='*60}")
    for task_id, score in scores.items():
        if score is not None:
            print(f"  {task_id:8s}: {score:.3f}")
