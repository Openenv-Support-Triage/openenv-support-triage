from typing import Dict, Any

from src.models import Action
from src.rewards import calculate_reward

def grade_easy(action: Action, ground_truth: Dict[str, Any]) -> float:
    """Grader for easy tasks. No extra penalties."""
    return calculate_reward(action, ground_truth, unnecessary_steps=0)

def grade_medium(action: Action, ground_truth: Dict[str, Any]) -> float:
    """Grader for medium tasks. Penalize significantly wrong priorities."""
    base_score = calculate_reward(action, ground_truth, unnecessary_steps=0)
    
    priorities = ["P0", "P1", "P2", "P3"]
    try:
        if abs(priorities.index(action.priority.value) - priorities.index(ground_truth["priority"])) > 1:
            base_score -= 0.2
    except ValueError:
        pass
        
    return max(0.0, base_score)

def grade_hard(action: Action, ground_truth: Dict[str, Any]) -> float:
    """Grader for hard tasks. Escalation misses are heavily penalized."""
    base_score = calculate_reward(action, ground_truth, unnecessary_steps=0)
    
    if action.escalate != ground_truth["escalate"]:
        base_score -= 0.3
        
    return max(0.0, base_score)

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
