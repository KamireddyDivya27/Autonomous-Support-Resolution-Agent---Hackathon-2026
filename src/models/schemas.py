"""Pydantic models for type safety and schema validation."""
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

class TicketStatus(str, Enum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    RESOLVED = "RESOLVED"
    ESCALATED = "ESCALATED"
    FAILED = "FAILED"

class TicketCategory(str, Enum):
    REFUND_REQUEST = "REFUND_REQUEST"
    ORDER_STATUS = "ORDER_STATUS"
    PRODUCT_QUESTION = "PRODUCT_QUESTION"
    ACCOUNT_ISSUE = "ACCOUNT_ISSUE"
    SHIPPING_ISSUE = "SHIPPING_ISSUE"
    GENERAL_INQUIRY = "GENERAL_INQUIRY"
    COMPLEX = "COMPLEX"
    UNKNOWN = "UNKNOWN"

class UrgencyLevel(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"

class Ticket(BaseModel):
    ticket_id: str
    customer_email: str
    subject: str
    message: str
    created_at: datetime = Field(default_factory=datetime.now)
    metadata: Dict[str, Any] = Field(default_factory=dict)
