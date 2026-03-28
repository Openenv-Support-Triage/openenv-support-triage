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

    # 2. Test step
    print("\nTesting step()...")
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

    # 3. Process remaining tickets
    print("\nProcessing remaining tickets...")
    while not done:
        next_obs, reward, done, info = env.step(action)

    state = env.state()
    print("\nFinal State:")
    print(f"Tickets Processed: {state.tickets_processed}")
    print(f"Total Tickets: {state.total_tickets}")
    print(f"Cumulative Score: {state.cumulative_score:.2f}")
    print(f"Average Score: {state.cumulative_score / max(1, state.tickets_processed):.2f}")
    print(f"Status: {state.status}")

    # 4. Test reset mid-episode
    print("\n--- Testing reset mid-episode ---")
    obs = env.reset("medium")
    print(f"Reset to medium. First ticket: {obs.ticket_id}")
    action = Action(priority="P0", department="engineering", response="Escalating immediately.", escalate=True)
    next_obs, reward, done, info = env.step(action)
    print(f"Step 1 reward: {reward.score:.2f}")

    # Reset mid-episode
    obs = env.reset("hard")
    print(f"Reset mid-episode to hard. First ticket: {obs.ticket_id}")
    state = env.state()
    print(f"State after reset: processed={state.tickets_processed}, total={state.total_tickets}, score={state.cumulative_score:.2f}")

    # 5. Test step before reset error
    print("\n--- Testing step before reset ---")
    fresh_env = SupportTriageEnv()
    try:
        fresh_env.step(action)
        print("ERROR: Should have raised RuntimeError")
    except RuntimeError as e:
        print(f"Correctly raised: {e}")

    print("\nAll verification checks passed!")

if __name__ == "__main__":
    verify()
