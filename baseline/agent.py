import os
from openai import OpenAI
from pydantic import BaseModel
from src.models import Action, Priority, Department

class AgentResponse(BaseModel):
    thoughts: str
    action: Action

class SupportAgent:
    def __init__(self, model_name="gpt-4o-mini"):
        self.model_name = model_name
        self.client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY", "dummy_key"))

    def get_action(self, observation) -> Action:
        system_prompt = (
            "You are a customer support triage agent. Review the ticket details and decide the "
            "Priority (P0, P1, P2, P3), the appropriate Department, a concise empathetic Response draft, "
            "and whether it requires immediate escalation (escalate: true/false)."
        )
        
        user_prompt = f"Ticket Details:\n{observation.model_dump_json(indent=2)}"

        try:
            response = self.client.beta.chat.completions.parse(
                model=self.model_name,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                response_format=AgentResponse,
                temperature=0.0
            )
            return response.choices[0].message.parsed.action
        except Exception as e:
            print(f"Agent error processing ticket {observation.ticket_id}: {e}")
            # Fallback action
            return Action(
                priority=Priority.P2,
                department=Department.product_support,
                response="We have received your ticket and are looking into it.",
                escalate=False
            )
