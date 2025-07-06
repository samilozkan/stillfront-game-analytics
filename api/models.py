"""
Pydantic models for the analytics API.
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class BaseEventModel(BaseModel):
    """Base model for all events."""
    event_id: str
    user_id: str
    game_id: str
    timestamp: datetime
    platform: str
    app_version: str
    session_id: str


class InstallEventModel(BaseEventModel):
    """Model for install events."""
    event_type: str = Field(default="install")
    source: Optional[str] = None
    country: Optional[str] = None


class PurchaseEventModel(BaseEventModel):
    """Model for purchase events."""
    event_type: str = Field(default="purchase")
    product_id: str
    product_name: str
    price: float = Field(ge=0)  # Must be >= 0
    currency: str
    quantity: int = Field(default=1, gt=0)  # Must be > 0
    store: Optional[str] = None
    transaction_id: Optional[str] = None


class EventResponse(BaseModel):
    """Response for successful event processing."""
    success: bool
    event_id: str
    message: str
    timestamp: datetime


class ErrorResponse(BaseModel):
    """Response for errors."""
    success: bool = False
    error: str
    message: str
    timestamp: datetime


class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    timestamp: datetime
    version: str = "1.0.0"