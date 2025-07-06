"""
Pydantic models for the analytics API.
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, validator
from decimal import Decimal
from enum import Enum


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
    price: Decimal = Field(ge=0, decimal_places=4)  # Decimal precision for currency and Must be >= 0
    currency: str
    quantity: int = Field(default=1, gt=0)  # Must be > 0
    store: Optional[str] = None
    transaction_id: Optional[str] = None
    
    @validator('price')
    def validate_price_precision(cls, v):
        """Ensure price has proper decimal precision."""
        if isinstance(v, (int, float)):
            v = Decimal(str(v))
        return v.quantize(Decimal('0.0001'))  # 4 decimal places

    @validator('currency')  
    def validate_currency_code(cls, v):
        """Validate currency code format."""
        if not v or len(v) != 3:
            raise ValueError('Currency must be 3-letter ISO code (e.g., USD, EUR)')
        return v.upper()


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