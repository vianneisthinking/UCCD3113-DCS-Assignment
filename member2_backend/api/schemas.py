"""Request and response shapes exposed to Member 1's frontend and Member 5's dashboard."""

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class RegisterRequest(BaseModel):
    email: EmailStr
    # bcrypt refuses passwords longer than 72 bytes, so cap it here rather than
    # letting the hash call raise a 500.
    password: str = Field(..., min_length=8, max_length=72)
    name: str = Field(..., min_length=1, max_length=100)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=1, max_length=72)


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    name: str
    role: str


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str
    name: str


class TicketCreate(BaseModel):
    complaint: str = Field(
        ...,
        min_length=3,
        max_length=2000,
        examples=["My credit card was charged twice for one order."],
    )


class TicketOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    complaint: str
    status: str
    department: str
    sla_due_at: datetime
    category: Optional[str] = None
    category_confidence: Optional[float] = None
    priority: str
    priority_confidence: Optional[float] = None
    model_version: Optional[str] = None
    classified_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime


class StatusUpdate(BaseModel):
    status: Literal[
        "pending_classification",
        "open",
        "in_progress",
        "resolved",
        "closed",
    ]
