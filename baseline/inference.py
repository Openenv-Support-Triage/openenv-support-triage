"""
Baseline agent for the OpenEnv Support Triage environment.
Uses OpenAI API (GPT-4o-mini by default) to make triage decisions.

Usage:
    Set OPENAI_API_KEY in .env or environment, then run:
    python -m baseline.inference
"""
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from dotenv import load_dotenv
load_dotenv()

from openai import OpenAI
from pydantic import BaseModel

from src.environment import SupportTriageEnv
from src.models import Action, Priority, Department
from src.logger import get_logger

log = get_logger("agent")


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
- Sarcasm often masks serious anger -- read between the lines
- Multi-intent tickets: route to primary department, note secondary
- "Evaluating alternatives" from enterprise = churn signal = escalate
- Empty ticket body with legal attachments = P0 + legal + escalate"""


class SupportAgent:
    def __init__(self, model_name: str = "gpt-4o-mini"):
        self.model_name = model_name
        self.client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY", "dummy_key"))
        log.info(f"SupportAgent initialised with model='{model_name}'")

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
            ticket_info += "Conversation History:\n" + "\n".join(f"  - {msg}" for msg in observation.conversation_history) + "\n"
        if observation.attachments:
            ticket_info += f"Attachments: {', '.join(observation.attachments)}\n"

        log.debug(f"Sending ticket {observation.ticket_id} to {self.model_name}")

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
            parsed = response.choices[0].message.parsed
            action = parsed.action

            log.info(f"[{observation.ticket_id}] Agent thoughts: {parsed.thoughts[:120]}{'...' if len(parsed.thoughts) > 120 else ''}")
            log.info(f"[{observation.ticket_id}] Agent decision -> priority={action.priority.value}, dept={action.department.value}, escalate={action.escalate}")
            log.debug(f"[{observation.ticket_id}] Agent response draft: \"{action.response[:120]}{'...' if len(action.response) > 120 else ''}\"")

            return action

        except Exception as e:
            log.error(f"[{observation.ticket_id}] OpenAI API error: {e}")
            log.warning(f"[{observation.ticket_id}] Falling back to default action: P2 / product_support / escalate=False")
            return Action(
                priority=Priority.P2,
                department=Department.product_support,
                response="We have received your ticket and are looking into it.",
                escalate=False,
            )


def run_evaluation(task_id: str, agent: SupportAgent):
    log.info(f"{'#'*60}")
    log.info(f"  STARTING EVALUATION -- task='{task_id.upper()}'")
    log.info(f"{'#'*60}")

    env = SupportTriageEnv()
    try:
        obs = env.reset(task_id)
    except Exception as e:
        log.error(f"Could not start task '{task_id}': {e}")
        return None

    scores = []
    done = False

    while not done:
        action = agent.get_action(obs)
        next_obs, reward, done, info = env.step(action)

        gt = info["ground_truth"]
        correct_p   = "[OK]" if action.priority.value == gt["priority"] else f"[X](gt={gt['priority']})"
        correct_d   = "[OK]" if action.department.value == gt["department"] else f"[X](gt={gt['department']})"
        correct_esc = "[OK]" if action.escalate == gt["escalate"] else f"[X](gt={gt['escalate']})"

        log.info(
            f"  RESULT {obs.ticket_id:12s} | score={reward.score:.3f} "
            f"| priority {correct_p:15s} | dept {correct_d:25s} | escalate {correct_esc}"
        )
        scores.append(reward.score)
        obs = next_obs

    state = env.state()
    avg = state.cumulative_score / max(1, state.tickets_processed)

    log.info(f"{'-'*60}")
    log.info(f"  TASK '{task_id.upper()}' COMPLETE")
    log.info(f"  Tickets processed : {state.tickets_processed}/{state.total_tickets}")
    log.info(f"  Cumulative score  : {state.cumulative_score:.4f}")
    log.info(f"  Average score     : {avg:.4f}")
    log.info(f"  Min / Max         : {min(scores):.4f} / {max(scores):.4f}")
    log.info(f"{'-'*60}")

    return avg


if __name__ == "__main__":
    if not os.environ.get("OPENAI_API_KEY"):
        log.warning("OPENAI_API_KEY not set -- agent will use fallback actions on API failure")

    model = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")
    agent = SupportAgent(model_name=model)

    results = {}
    for task_id in ["easy", "medium", "hard"]:
        results[task_id] = run_evaluation(task_id, agent)

    log.info(f"{'#'*60}")
    log.info("  FINAL SUMMARY")
    log.info(f"{'#'*60}")
    for task_id, avg in results.items():
        if avg is not None:
            log.info(f"  {task_id:8s} -> avg score = {avg:.4f}")
    log.info(f"{'#'*60}")
