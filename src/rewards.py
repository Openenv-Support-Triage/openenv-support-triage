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
        intersection = agent_resp_words.intersection(truth_resp_words)
        overlap_ratio = len(intersection) / len(truth_resp_words)
        response_score = min(1.0, overlap_ratio * 1.5) # simple boost multiplier
        
    # 4. Escalation Match (0.10)
    escalation_score = 1.0 if action.escalate == ground_truth["escalate"] else 0.0
    
    # Calculate final score
    raw_score = (0.40 * priority_score + 
                 0.30 * department_score + 
                 0.20 * response_score + 
                 0.10 * escalation_score - 
                 0.05 * unnecessary_steps)
                 
    return max(0.0, min(1.0, raw_score))
