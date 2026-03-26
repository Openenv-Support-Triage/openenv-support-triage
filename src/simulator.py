import json
import os
from typing import List, Dict, Any, Optional

from src.models import Observation, Action

class CustomerSupportSimulator:
    def __init__(self, tasks_dir: str = "tasks"):
        self.tasks_dir = tasks_dir
        self.tickets: List[Dict[str, Any]] = []
        self.current_idx = 0
        self.total_tickets = 0

    def load_task(self, task_id: str) -> bool:
        """Loads a given task JSON file (e.g., 'easy', 'medium', 'hard')."""
        file_path = os.path.join(self.tasks_dir, f"task_{task_id}.json")
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Task file {file_path} not found.")

        with open(file_path, 'r', encoding='utf-8') as f:
            self.tickets = json.load(f)

        self.total_tickets = len(self.tickets)
        self.current_idx = 0
        return True

    def get_next_ticket(self) -> Optional[tuple[Observation, dict]]:
        """Returns the next parsed Observation and the raw ground_truth dictionary."""
        if not self.has_more_tickets():
            return None

        ticket_data = self.tickets[self.current_idx]
        self.current_idx += 1

        obs_data = ticket_data["observation"]
        ground_truth = ticket_data["ground_truth"]

        obs = Observation(**obs_data)

        return obs, ground_truth

    def has_more_tickets(self) -> bool:
        return self.current_idx < self.total_tickets

    def get_progress(self) -> tuple[int, int]:
        """Returns (tickets_processed, total_tickets)"""
        return self.current_idx, self.total_tickets
