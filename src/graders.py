from typing import Dict, Any

from src.models import Action
from src.rewards import calculate_reward

def grade_easy(action: Action, ground_truth: Dict[str, Any]) -> float:
    """Grader for easy tasks. No extra penalties."""
    return calculate_reward(action, ground_truth, unnecessary_steps=0)

def grade_medium(action: Action, ground_truth: Dict[str, Any]) -> float:
    """Grader for medium tasks."""
    return calculate_reward(action, ground_truth, unnecessary_steps=0)

def grade_hard(action: Action, ground_truth: Dict[str, Any]) -> float:
    """Grader for hard tasks."""
    return calculate_reward(action, ground_truth, unnecessary_steps=0)

def grade_action(task_id: str, action: Action, ground_truth: Dict[str, Any]) -> float:
    """Dispatcher for grading."""
    task_id = task_id.lower()
    if task_id == "easy" or task_id.endswith("task_easy"):
        return grade_easy(action, ground_truth)
    elif task_id == "medium" or task_id.endswith("task_medium"):
        return grade_medium(action, ground_truth)
    elif task_id == "hard" or task_id.endswith("task_hard"):
        return grade_hard(action, ground_truth)
    else:
        # Default fallback
        return calculate_reward(action, ground_truth)
