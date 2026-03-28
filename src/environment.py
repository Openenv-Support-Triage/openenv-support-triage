from typing import Tuple, Dict, Any, Optional

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

from src.models import Action, Observation, Reward, State
from src.simulator import CustomerSupportSimulator
from src.graders import grade_action
from src.logger import get_logger

log = get_logger("environment")


class SupportTriageEnv(BaseEnvironment):
    def __init__(self):
        super().__init__()
        self._simulator = CustomerSupportSimulator(tasks_dir="tasks")
        self._cumulative_score = 0.0
        self._current_task_id: str = ""
        self._current_ticket: Optional[Observation] = None
        self._current_ground_truth: Optional[Dict[str, Any]] = None
        self._is_reset = False
        self._step_count = 0
        log.info("SupportTriageEnv initialised")

    def reset(self, task_id: str) -> Observation:
        """Starts a new episode, loads the task, and returns the first ticket as an Observation."""
        log.info(f"{'='*60}")
        log.info(f"RESET -> task_id='{task_id}'")

        self._current_task_id = task_id
        self._simulator.load_task(task_id)
        self._cumulative_score = 0.0
        self._step_count = 0
        self._is_reset = True

        next_data = self._simulator.get_next_ticket()
        if not next_data:
            log.error(f"Task '{task_id}' has no tickets!")
            raise ValueError(f"Task '{task_id}' has no tickets.")

        self._current_ticket, self._current_ground_truth = next_data
        log.info(f"Episode started -- first ticket: {self._current_ticket.ticket_id}")
        return self._current_ticket

    def step(self, action: Action) -> Tuple[Optional[Observation], Reward, bool, Dict[str, Any]]:
        """Accepts an Action, scores it against ground truth, and returns the next state."""
        if not self._is_reset:
            raise RuntimeError("Environment has not been reset. Call reset(task_id) before step().")

        if self._current_ticket is None or self._current_ground_truth is None:
            raise RuntimeError("No active tickets. The episode is already done. Call reset() to start a new episode.")

        if not isinstance(action, Action):
            raise TypeError(f"Expected Action object, got {type(action).__name__}.")

        self._step_count += 1
        tickets_done, total = self._simulator.get_progress()
        log.info(f"STEP {self._step_count} | ticket={self._current_ticket.ticket_id} | progress={tickets_done}/{total}")
        log.info(f"  Agent decided -> priority={action.priority.value}, dept={action.department.value}, escalate={action.escalate}")
        log.debug(f"  Agent response: \"{action.response[:100]}{'...' if len(action.response) > 100 else ''}\"")

        # Score the action
        score = grade_action(self._current_task_id, action, self._current_ground_truth)
        self._cumulative_score += score
        avg_so_far = self._cumulative_score / self._step_count

        log.info(f"  Step score      = {score:.4f}")
        log.info(f"  Cumulative score= {self._cumulative_score:.4f}  (avg so far = {avg_so_far:.4f})")

        reward_obj = Reward(score=score, metrics={"cumulative_score": self._cumulative_score})
        info = {
            "task_id": self._current_task_id,
            "score_this_step": score,
            "ground_truth": self._current_ground_truth
        }

        # Advance the queue
        next_data = self._simulator.get_next_ticket()

        if next_data is None:
            self._current_ticket = None
            self._current_ground_truth = None
            done = True
            next_obs = None
            log.info(f"EPISODE DONE [OK] | {self._step_count} tickets | cumulative={self._cumulative_score:.4f} | avg={avg_so_far:.4f}")
            log.info(f"{'='*60}")
        else:
            self._current_ticket, self._current_ground_truth = next_data
            done = False
            next_obs = self._current_ticket

        return next_obs, reward_obj, done, info

    def state(self) -> State:
        """Returns current progress, including tickets processed and cumulative score."""
        tickets_processed, total_tickets = self._simulator.get_progress()

        if not self._is_reset:
            status = "Not Started"
        elif tickets_processed >= total_tickets and total_tickets > 0:
            status = "Completed"
        else:
            status = "In Progress"

        avg = self._cumulative_score / max(1, tickets_processed) if tickets_processed > 0 else 0.0
        log.debug(
            f"STATE -> status={status} | processed={tickets_processed}/{total_tickets} "
            f"| cumulative={self._cumulative_score:.4f} | avg={avg:.4f}"
        )

        return State(
            status=status,
            tickets_processed=tickets_processed,
            total_tickets=total_tickets,
            cumulative_score=self._cumulative_score
        )
