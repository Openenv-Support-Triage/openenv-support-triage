import string
from src.models import Action, Priority
from src.logger import get_logger

log = get_logger("rewards")


def calculate_reward(action: Action, ground_truth: dict, unnecessary_steps: int = 0) -> float:
    """
    Computes a continuous reward signal [0.0, 1.0].

    Weights:
      priority    = 0.40
      department  = 0.30
      response    = 0.20
      escalation  = 0.10
      speed penalty = -0.05 per unnecessary step
    """
    log.debug("-" * 60)
    log.debug("REWARD CALCULATION START")
    log.debug(f"  Agent Action   -> priority={action.priority.value}, dept={action.department.value}, escalate={action.escalate}")
    log.debug(f"  Ground Truth   -> priority={ground_truth['priority']}, dept={ground_truth['department']}, escalate={ground_truth['escalate']}")
    log.debug(f"  Secondary dept -> {ground_truth.get('secondary_department')}")

    # -- 1. Priority Match (weight 0.40) ----------------------------------
    priority_score = 0.0
    priorities = [Priority.P0, Priority.P1, Priority.P2, Priority.P3]
    idx_action = priorities.index(action.priority)
    idx_truth  = priorities.index(Priority(ground_truth["priority"]))
    diff = abs(idx_action - idx_truth)

    if diff == 0:
        priority_score = 1.0
        log.debug(f"  [PRIORITY]  agent={action.priority.value} == truth={ground_truth['priority']} -> EXACT MATCH -> score=1.0")
    elif diff == 1:
        priority_score = 0.5
        log.debug(f"  [PRIORITY]  agent={action.priority.value} vs truth={ground_truth['priority']} -> OFF BY 1 -> score=0.5")
    else:
        priority_score = 0.0
        log.debug(f"  [PRIORITY]  agent={action.priority.value} vs truth={ground_truth['priority']} -> OFF BY {diff} -> score=0.0")

    weighted_priority = 0.40 * priority_score
    log.debug(f"  [PRIORITY]  0.40 × {priority_score:.2f} = {weighted_priority:.4f}")

    # -- 2. Department Match (weight 0.30) ---------------------------------

    department_score = 0.0
    if action.department.value == ground_truth["department"]:
        department_score = 1.0
        log.debug(f"  [DEPT]      agent={action.department.value} == truth={ground_truth['department']} -> EXACT MATCH -> score=1.0")
    elif action.department.value == ground_truth.get("secondary_department"):
        department_score = 0.5
        log.debug(f"  [DEPT]      agent={action.department.value} == secondary={ground_truth.get('secondary_department')} -> SECONDARY MATCH -> score=0.5")
    else:
        department_score = 0.0
        log.debug(f"  [DEPT]      agent={action.department.value} vs truth={ground_truth['department']} (secondary={ground_truth.get('secondary_department')}) -> NO MATCH -> score=0.0")

    weighted_dept = 0.30 * department_score
    log.debug(f"  [DEPT]      0.30 × {department_score:.2f} = {weighted_dept:.4f}")

    # -- 3. Response Quality (weight 0.20) ---------------------------------
    agent_words = set(action.response.lower().translate(str.maketrans('', '', string.punctuation)).split())
    truth_words = set(ground_truth["response"].lower().translate(str.maketrans('', '', string.punctuation)).split())

    log.debug(f"  [RESPONSE]  agent words ({len(agent_words)}): {sorted(agent_words)[:8]}{'...' if len(agent_words) > 8 else ''}")
    log.debug(f"  [RESPONSE]  truth words ({len(truth_words)}): {sorted(truth_words)[:8]}{'...' if len(truth_words) > 8 else ''}")

    if len(truth_words) == 0:
        response_score = 1.0
        log.debug("  [RESPONSE]  truth has no words -> score=1.0 (trivially correct)")
    else:
        intersection = agent_words.intersection(truth_words)
        intersection_len = len(intersection)
        precision = intersection_len / max(1, len(agent_words))
        recall    = intersection_len / max(1, len(truth_words))

        log.debug(f"  [RESPONSE]  matching words ({intersection_len}): {sorted(intersection)[:8]}{'...' if intersection_len > 8 else ''}")
        log.debug(f"  [RESPONSE]  precision = {intersection_len}/{max(1, len(agent_words))} = {precision:.4f}")
        log.debug(f"  [RESPONSE]  recall    = {intersection_len}/{max(1, len(truth_words))} = {recall:.4f}")

        if precision + recall == 0:
            response_score = 0.0
            log.debug("  [RESPONSE]  precision+recall=0 -> F1=0.0")
        else:
            response_score = 2 * (precision * recall) / (precision + recall)
            log.debug(f"  [RESPONSE]  F1 = 2×({precision:.4f}×{recall:.4f}) / ({precision:.4f}+{recall:.4f}) = {response_score:.4f}")

    weighted_response = 0.20 * response_score
    log.debug(f"  [RESPONSE]  0.20 × {response_score:.4f} = {weighted_response:.4f}")

    # -- 4. Escalation Match (weight 0.10) ---------------------------------
    escalation_score = 1.0 if action.escalate == ground_truth["escalate"] else 0.0
    match_label = "MATCH" if escalation_score == 1.0 else "MISMATCH"
    log.debug(f"  [ESCALATION] agent={action.escalate} vs truth={ground_truth['escalate']} -> {match_label} -> score={escalation_score:.1f}")

    weighted_escalation = 0.10 * escalation_score
    log.debug(f"  [ESCALATION] 0.10 × {escalation_score:.2f} = {weighted_escalation:.4f}")

    # -- 5. Critical Penalty -----------------------------------------------
    critical_penalty = 0.0
    if ground_truth.get("department") in ["legal", "security"] and not action.escalate:
        critical_penalty = -1.0
        log.warning(f"  [CRITICAL]  dept='{ground_truth['department']}' requires escalation but agent did NOT escalate -> PENALTY = -1.0")
    else:
        log.debug(f"  [CRITICAL]  no critical penalty")

    # -- 6. Speed Penalty -------------------------------------------------
    speed_penalty = 0.05 * unnecessary_steps
    if unnecessary_steps > 0:
        log.debug(f"  [SPEED]     {unnecessary_steps} unnecessary step(s) -> penalty = -{speed_penalty:.4f}")
    else:
        log.debug(f"  [SPEED]     no unnecessary steps -> penalty = 0.0")

    # -- 7. Final Score ----------------------------------------------------
    raw_score = (weighted_priority + weighted_dept + weighted_response
                 + weighted_escalation + critical_penalty - speed_penalty)
    final_score = max(0.0, min(1.0, raw_score))

    log.debug(f"  [TOTAL]     {weighted_priority:.4f} + {weighted_dept:.4f} + {weighted_response:.4f} + {weighted_escalation:.4f} + ({critical_penalty:.4f}) - ({speed_penalty:.4f}) = {raw_score:.4f}")
    log.debug(f"  [TOTAL]     clamped to [0,1] -> FINAL SCORE = {final_score:.4f}")
    log.debug("-" * 60)

    return final_score
