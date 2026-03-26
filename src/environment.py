from typing import Tuple, Dict, Any, Optional
from datetime import datetime

try:
    from openenv import BaseEnvironment
except ImportError:
    class BaseEnvironment:
        def __init__(self):
            pass
        def reset(self, task_id: str):
            pass
        def step(self, action):
            pass
        def state(self):
            pass

from src.models import Action, Observation, Reward, State, Priority, Department
from src.simulator import CustomerSupportSimulator
from src.graders import grade_action


class SupportTriageEnv(BaseEnvironment):
    def __init__(self):
        super().__init__()
        self._simulator = CustomerSupportSimulator(tasks_dir="tasks")
        self._cumulative_score = 0.0
        self._current_task_id: str = ""
        self._current_ticket: Optional[Observation] = None
        self._current_ground_truth: Optional[Dict[str, Any]] = None

    def reset(self, task_id: str) -> Observation:
        """Starts a new episode, loads the task, and returns the first ticket as an Observation."""
        self._current_task_id = task_id
        
        # This acts like a dataset load/reset.
        # OpenEnv expects task_id to direct to 'easy', 'medium', 'hard', etc.
        self._simulator.load_task(task_id)
        
        self._cumulative_score = 0.0
        
        # Get the first ticket
        next_data = self._simulator.get_next_ticket()
        if not next_data:
            raise ValueError(f"Task {task_id} has no tickets.")
            
        self._current_ticket, self._current_ground_truth = next_data
        
        return self._current_ticket

    def step(self, action: Action) -> Tuple[Optional[Observation], Reward, bool, Dict[str, Any]]:
        """Accepts an Action, scores it against ground truth using graders.py, and returns a tuple."""
        if not self._current_ticket or not self._current_ground_truth:
            raise RuntimeError("Environment has not been reset or there are no active tickets.")
            
        # 1. Score the action
        score = grade_action(self._current_task_id, action, self._current_ground_truth)
        self._cumulative_score += score
        
        reward_obj = Reward(score=score, metrics={"cumulative_score": self._cumulative_score})
        
        info = {
            "task_id": self._current_task_id, 
            "score_this_step": score,
            "ground_truth": self._current_ground_truth
        }
        
        # 2. Advance the queue
        next_data = self._simulator.get_next_ticket()
        
        if next_data is None:
            # Done
            self._current_ticket = None
            self._current_ground_truth = None
            done = True
            next_obs = None
        else:
            self._current_ticket, self._current_ground_truth = next_data
            done = False
            next_obs = self._current_ticket
            
        return next_obs, reward_obj, done, info

    def state(self) -> State:
        """Returns current progress, including tickets processed and cumulative score."""
        tickets_processed, total_tickets = self._simulator.get_progress()
        status = "Completed" if tickets_processed >= total_tickets and total_tickets > 0 else "In Progress"
        
        return State(
            status=status,
            tickets_processed=tickets_processed,
            cumulative_score=self._cumulative_score
        )
