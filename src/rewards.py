import string
from src.models import Action, Priority

def calculate_reward(action: Action, ground_truth: dict, unnecessary_steps: int = 0) -> float:
    """
    Computes a continuous reward signal [0.0, 1.0]
    
    Arguments:
    - action: Agent's Action object (Pydantic)
    - ground_truth: Dict containing specific ground truth fields
    - unnecessary_steps: Speed penalty modifier
    """
    # 1. Priority Match (0.40)
    priority_score = 0.0
    if action.priority.value == ground_truth["priority"]:
        priority_score = 1.0
    else:
        priorities = [Priority.P0, Priority.P1, Priority.P2, Priority.P3]
        idx_action = priorities.index(action.priority)
        idx_truth = priorities.index(Priority(ground_truth["priority"]))
        if abs(idx_action - idx_truth) == 1:
            priority_score = 0.5
            
    # 2. Department Match (0.30)
    department_score = 0.0
    if action.department.value == ground_truth["department"]:
        department_score = 1.0
    elif action.department.value == ground_truth.get("secondary_department"):
        department_score = 0.5

    # 3. Response Quality (0.20)
    # Using simple heuristic: word overlap between response draft and ground truth response
    agent_resp_words = set(action.response.lower().translate(str.maketrans('', '', string.punctuation)).split())
    truth_resp_words = set(ground_truth["response"].lower().translate(str.maketrans('', '', string.punctuation)).split())
    
    if len(truth_resp_words) == 0:
        response_score = 1.0
    else:
        intersection_len = len(agent_resp_words.intersection(truth_resp_words))
        precision = intersection_len / max(1, len(agent_resp_words))
        recall = intersection_len / max(1, len(truth_resp_words))
        
        if precision + recall == 0:
            response_score = 0.0
        else:
            response_score = 2 * (precision * recall) / (precision + recall)
        
    # 4. Escalation Match (0.10)
    escalation_score = 1.0 if action.escalate == ground_truth["escalate"] else 0.0
    
    # 5. Critical Penalty Check
    critical_penalty = 0.0
    # Legal and security routing misses MUST be penalized immediately if not escalated
    if ground_truth.get("department") in ["legal", "security"] and not action.escalate:
        critical_penalty = -1.0
    
    # Calculate final score
    raw_score = (0.40 * priority_score + 
                 0.30 * department_score + 
                 0.20 * response_score + 
                 0.10 * escalation_score +
                 critical_penalty - 
                 0.05 * unnecessary_steps)
                 
    return max(0.0, min(1.0, raw_score))
