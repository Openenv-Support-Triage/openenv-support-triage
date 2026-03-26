import json
import random
from datetime import datetime, timedelta

def dt_str(days_ago):
    return (datetime.now() - timedelta(days=days_ago)).isoformat()

def generate_easy(num_tickets=10):
    tickets = []
    intents = [
        ("duplicate charge", "P1", "billing", "I placed an order but my bank shows two charges.", False),
        ("password reset", "P2", "product_support", "I cannot log in, password reset link not working.", False),
        ("order tracking", "P3", "customer_success", "Where is my order #1234?", False),
        ("cancellation request", "P2", "billing", "Please cancel my subscription before the next cycle.", False),
        ("delivery complaint", "P2", "customer_success", "My item arrived damaged.", False),
        ("product defect", "P1", "engineering", "The app crashes every time I open the reports tab.", False),
        ("account upgrade", "P3", "billing", "I want to upgrade to premium.", False),
        ("refund status", "P2", "billing", "When will I get my refund?", False),
        ("general feedback", "P3", "product_support", "I love the new UI, but the fonts are too small.", False),
        ("how to use", "P3", "product_support", "How do I export data to CSV?", False)
    ]
    
    for i in range(num_tickets):
        intent, priority, dept, body, escalate = intents[i % len(intents)]
        ticket = {
            "observation": {
                "ticket_id": f"EASY-{1000+i}",
                "ticket_text": body,
                "subject": intent.capitalize(),
                "customer_name": f"User {i}",
                "customer_email": f"user{i}@example.com",
                "customer_tier": "standard",
                "channel": "email",
                "timestamp": dt_str(days_ago=random.randint(1, 5)),
                "conversation_history": [],
                "attachments": []
            },
            "ground_truth": {
                "priority": priority,
                "department": dept,
                "response": "Thank you for reaching out. We are processing your request regarding " + intent + ".",
                "escalate": escalate,
                "secondary_department": None
            }
        }
        tickets.append(ticket)
    return tickets

def generate_medium(num_tickets=15):
    tickets = []
    # Medium requires weighing multiple signals.
    # E.g., VIP overrides priority; 2-3 intents that need strict primary routing with partial secondary.
    # Example 2: Arlington Mehta VIP enterprise -> down since Monday, evaluating alternatives -> Churn risk
    for i in range(num_tickets):
        is_vip = (i % 3 == 0)
        multi_intent = (i % 2 == 0)
        
        tier = "enterprise" if is_vip else "premium"
        
        if is_vip:
            body = "Your last update broke our bulk import feature. We use this daily. Plus, our dedicated AM is missing. We are evaluating alternatives."
            priority = "P0" # VIP + down + churn
            dept = "engineering"
            sec_dept = "customer_success"
            escalate = True
        elif multi_intent:
            body = "I want to upgrade my plan, but I also have a technical question about the API rate limits. Who do I speak to?"
            priority = "P2"
            dept = "engineering"
            sec_dept = "billing"
            escalate = False
        else:
            body = "Is your system SOC2 compliant? Our procurement requires documentation."
            priority = "P2"
            dept = "security"
            sec_dept = "legal"
            escalate = False
            
        ticket = {
            "observation": {
                "ticket_id": f"MED-{2000+i}",
                "ticket_text": body,
                "subject": "Multiple queries" if multi_intent else "Important request",
                "customer_name": f"Corporate User {i}",
                "customer_email": f"corp{i}@enterprise.co",
                "customer_tier": tier,
                "channel": "chat",
                "timestamp": dt_str(days_ago=random.randint(0, 2)),
                "conversation_history": [],
                "attachments": []
            },
            "ground_truth": {
                "priority": priority,
                "department": dept,
                "response": "We have received your request. We will escalate this to the appropriate team.",
                "escalate": escalate,
                "secondary_department": sec_dept
            }
        }
        tickets.append(ticket)
    return tickets

def generate_hard(num_tickets=20):
    tickets = []
    # Hard: Multi-turn, sarcastic, legal threats, passive aggressive
    for i in range(num_tickets):
        is_legal = (i % 4 == 0)
        is_sarcastic = (i % 3 == 0)
        
        if is_legal:
            body = "Wow, ticket #882 is now 12 days old. TWELVE. I have explained data loss 4 times. Documenting for my lawyer. But sure, take your time :)"
            priority = "P0"
            dept = "engineering"
            sec_dept = "legal"
            escalate = True
            history = ["We are looking into it.", "Still looking into it."]
        elif is_sarcastic:
            body = "Great job on the new release! It only deleted 3 of my user accounts. Fantastic feature. Please restore them immediately."
            priority = "P1" # Data loss
            dept = "engineering"
            sec_dept = None
            escalate = True # Repeated / Data loss
            history = []
        else:
            body = "re: re: re: re: previous issue. You said you'd refund me last week. The CEO promised on twitter that refunds are processed in 2 days. What gives? I will report to BBB."
            priority = "P1"
            dept = "billing"
            sec_dept = "legal" # BBB threat
            escalate = True
            history = ["Refund processed", "Where is it?"]
            
        ticket = {
            "observation": {
                "ticket_id": f"HARD-{3000+i}",
                "ticket_text": body,
                "subject": "Re: Re: Re: Still waiting...",
                "customer_name": f"Angry User {i}",
                "customer_email": f"angry{i}@startup.io",
                "customer_tier": "premium",
                "channel": "email",
                "timestamp": dt_str(days_ago=random.randint(1, 10)),
                "conversation_history": history,
                "attachments": []
            },
            "ground_truth": {
                "priority": priority,
                "department": dept,
                "response": "We apologize for the severe delay and the issues you've faced. This has been escalated immediately.",
                "escalate": escalate,
                "secondary_department": sec_dept
            }
        }
        tickets.append(ticket)
    return tickets

if __name__ == "__main__":
    import os
    os.makedirs("tasks", exist_ok=True)
    with open("tasks/task_easy.json", "w") as f:
        json.dump(generate_easy(10), f, indent=2)
    with open("tasks/task_medium.json", "w") as f:
        json.dump(generate_medium(15), f, indent=2)
    with open("tasks/task_hard.json", "w") as f:
        json.dump(generate_hard(20), f, indent=2)
    print("Generated 45 tickets across 3 JSON files.")
