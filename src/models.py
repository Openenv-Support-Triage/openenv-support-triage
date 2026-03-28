from datetime import datetime
from enum import Enum
from typing import List

from pydantic import BaseModel, EmailStr

class CustomerTier(str, Enum):
    standard = "standard"
    premium = "premium"
    enterprise = "enterprise"

class Channel(str, Enum):
    email = "email"
    chat = "chat"
    phone = "phone"
    social_media = "social_media"

class Observation(BaseModel):
    ticket_id: str
    ticket_text: str
    subject: str
    customer_name: str
    customer_email: EmailStr
    customer_tier: CustomerTier
    channel: Channel
    timestamp: datetime
    conversation_history: List[str]
    attachments: List[str]

class Priority(str, Enum):
    P0 = "P0"
    P1 = "P1"
    P2 = "P2"
    P3 = "P3"

class Department(str, Enum):
    billing = "billing"
    engineering = "engineering"
    product_support = "product_support"
    customer_success = "customer_success"
    legal = "legal"
    security = "security"

class Action(BaseModel):
    priority: Priority
    department: Department
    response: str
    escalate: bool

class Reward(BaseModel):
    score: float
    metrics: dict

class State(BaseModel):
    status: str
    tickets_processed: int
    total_tickets: int
    cumulative_score: float
