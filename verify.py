import sys
import os
sys.path.insert(0, os.path.abspath('.'))

from src.environment import SupportTriageEnv
from src.models import Action

def verify():
    env = SupportTriageEnv()
    
    # 1. Test reset
    print("Testing reset('easy')...")
    obs = env.reset("easy")
    print(f"Observation ID: {obs.ticket_id}")
    print(f"Subject: {obs.subject}")
    
    # 2. Test Step
    print("\nTesting step()...")
    # Provide a simple action
    action = Action(
        priority="P1",
        department="billing",
        response="Thank you for reaching out. We are processing your request regarding duplicate charge.",
        escalate=False
    )
    
    next_obs, reward, done, info = env.step(action)
    print(f"Reward: {reward.score}")
    print(f"Done: {done}")
    if next_obs:
        print(f"Next Ticket ID: {next_obs.ticket_id}")
        
    # 3. Test loop till end
    print("\nProcessing remaining tickets...")
    while not done:
        action.response = "generic response" # change just to step fast
        next_obs, reward, done, info = env.step(action)
    
    state = env.state()
    print("\nFinal State:")
    print(f"Tickets Processed: {state.tickets_processed}")
    print(f"Cumulative Score: {state.cumulative_score}")
    print(f"Status: {state.status}")

if __name__ == "__main__":
    verify()
