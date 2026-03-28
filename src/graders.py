from typing import Dict, Any

from src.models import Action
from src.rewards import calculate_reward
from src.logger import get_logger

log = get_logger("graders")


def grade_easy(action: Action, ground_truth: Dict[str, Any]) -> float:
    """Easy grader -- no extra penalties beyond base reward."""
    log.debug("Using EASY grader (no extra penalties)")
    score = calculate_reward(action, ground_truth, unnecessary_steps=0)
    log.info(f"[EASY]   final score = {score:.4f}")
    return score


def grade_medium(action: Action, ground_truth: Dict[str, Any]) -> float:
    """Medium grader -- extra -0.20 penalty if priority is off by more than 1 level."""
    log.debug("Using MEDIUM grader (priority gap > 1 -> -0.20 penalty)")
    base_score = calculate_reward(action, ground_truth, unnecessary_steps=0)

    priorities = ["P0", "P1", "P2", "P3"]
    try:
        gap = abs(priorities.index(action.priority.value) - priorities.index(ground_truth["priority"]))
        if gap > 1:
            penalised = max(0.0, base_score - 0.20)
            log.warning(f"[MEDIUM] priority gap={gap} > 1 -> extra penalty -0.20: {base_score:.4f} -> {penalised:.4f}")
            return penalised
        else:
            log.debug(f"[MEDIUM] priority gap={gap} <= 1 -> no extra penalty")
    except ValueError:
        log.warning("[MEDIUM] could not compute priority gap (ValueError)")

    log.info(f"[MEDIUM] final score = {base_score:.4f}")
    return max(0.0, base_score)


def grade_hard(action: Action, ground_truth: Dict[str, Any]) -> float:
    """Hard grader -- extra -0.30 penalty if escalation decision is wrong."""
    log.debug("Using HARD grader (wrong escalation -> -0.30 penalty)")
    base_score = calculate_reward(action, ground_truth, unnecessary_steps=0)

    if action.escalate != ground_truth["escalate"]:
        penalised = max(0.0, base_score - 0.30)
        log.warning(
            f"[HARD]   escalation WRONG (agent={action.escalate}, truth={ground_truth['escalate']}) "
            f"-> extra penalty -0.30: {base_score:.4f} -> {penalised:.4f}"
        )
        return penalised

    log.debug(f"[HARD]   escalation correct -> no extra penalty")
    log.info(f"[HARD]   final score = {base_score:.4f}")
    return max(0.0, base_score)


def grade_action(task_id: str, action: Action, ground_truth: Dict[str, Any]) -> float:
    """Dispatcher -- routes to the correct grader based on task_id."""
    task_id = task_id.lower()
    log.debug(f"Dispatching grade_action for task_id='{task_id}'")

    if task_id == "easy" or task_id.endswith("task_easy"):
        return grade_easy(action, ground_truth)
    elif task_id == "medium" or task_id.endswith("task_medium"):
        return grade_medium(action, ground_truth)
    elif task_id == "hard" or task_id.endswith("task_hard"):
        return grade_hard(action, ground_truth)
    else:
        log.warning(f"Unknown task_id='{task_id}' -- falling back to base calculate_reward")
        return calculate_reward(action, ground_truth)
