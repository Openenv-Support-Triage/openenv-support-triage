import sys
import os
sys.path.insert(0, os.path.abspath('.'))

from src.environment import SupportTriageEnv
from baseline.agent import SupportAgent

def run_evaluation(task_id: str):
    env = SupportTriageEnv()
    try:
        obs = env.reset(task_id)
    except Exception as e:
        print(f"Task '{task_id}' could not be started: {e}")
        return
        
    agent = SupportAgent()
    print(f"--- Evaluating Task: {task_id.upper()} ---")
    
    done = False
    while not done:
        action = agent.get_action(obs)
        next_obs, reward, done, info = env.step(action)
        print(f"Ticket: {obs.ticket_id} | Score: {reward.score:.2f} | Priority: {action.priority.value} | Dept: {action.department.value}")
        obs = next_obs
        
    state = env.state()
    print(f"Finished {task_id.upper()}. Tickets processed: {state.tickets_processed}")
    print(f"Total Cumulative Score: {state.cumulative_score:.2f}")
    print(f"Average Score: {(state.cumulative_score / max(1, state.tickets_processed)):.2f}\n")

if __name__ == "__main__":
    if "OPENAI_API_KEY" not in os.environ:
        print("Disclaimer: OPENAI_API_KEY is not set. The agent will default to fallback actions in case of API failure.")
        
    run_evaluation("easy")
    run_evaluation("medium")
    run_evaluation("hard")
