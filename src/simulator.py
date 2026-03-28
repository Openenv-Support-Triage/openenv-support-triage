import json
import os
from typing import List, Dict, Any, Optional

from src.models import Observation
from src.logger import get_logger

log = get_logger("simulator")


class CustomerSupportSimulator:
    def __init__(self, tasks_dir: str = "tasks"):
        self.tasks_dir = tasks_dir
        self.tickets: List[Dict[str, Any]] = []
        self.current_idx = 0
        self.total_tickets = 0
        log.debug(f"Simulator initialised (tasks_dir='{tasks_dir}')")

    def load_task(self, task_id: str) -> bool:
        """Loads a given task JSON file (e.g., 'easy', 'medium', 'hard')."""
        file_path = os.path.join(self.tasks_dir, f"task_{task_id}.json")
        log.info(f"Loading task '{task_id}' from {file_path}")

        if not os.path.exists(file_path):
            log.error(f"Task file not found: {file_path}")
            raise FileNotFoundError(f"Task file {file_path} not found.")

        with open(file_path, 'r', encoding='utf-8') as f:
            self.tickets = json.load(f)

        self.total_tickets = len(self.tickets)
        self.current_idx = 0
        log.info(f"Loaded {self.total_tickets} tickets for task '{task_id}'")
        return True

    def get_next_ticket(self) -> Optional[tuple[Observation, dict]]:
        """Returns the next parsed Observation and the raw ground_truth dictionary."""
        if not self.has_more_tickets():
            log.debug("No more tickets in queue -> returning None")
            return None

        ticket_data = self.tickets[self.current_idx]
        ticket_num = self.current_idx + 1
        self.current_idx += 1

        obs_data = ticket_data["observation"]
        ground_truth = ticket_data["ground_truth"]
        obs = Observation(**obs_data)

        log.info(
            f"Serving ticket {ticket_num}/{self.total_tickets} -> "
            f"id={obs.ticket_id} | tier={obs.customer_tier.value} | channel={obs.channel.value}"
        )
        log.debug(f"  subject   : {obs.subject}")
        log.debug(f"  body      : {obs.ticket_text[:80]}{'...' if len(obs.ticket_text) > 80 else ''}")
        log.debug(f"  history   : {len(obs.conversation_history)} prior message(s)")
        log.debug(f"  attachments: {obs.attachments if obs.attachments else 'none'}")
        log.debug(f"  GT answer : priority={ground_truth['priority']}, dept={ground_truth['department']}, escalate={ground_truth['escalate']}")

        return obs, ground_truth

    def has_more_tickets(self) -> bool:
        return self.current_idx < self.total_tickets

    def get_progress(self) -> tuple[int, int]:
        """Returns (tickets_processed, total_tickets)."""
        return self.current_idx, self.total_tickets
