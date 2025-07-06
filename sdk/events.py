"""
Event data models for the game analytics SDK.
"""

import uuid
from datetime import datetime
from typing import Optional, Dict, Any


class BaseEvent:
    """Base class for all events."""
    
    def __init__(self, user_id: str, game_id: str, platform: str, 
                 app_version: str, session_id: str):
        self.event_id = str(uuid.uuid4())
        self.user_id = user_id
        self.game_id = game_id
        self.platform = platform
        self.app_version = app_version
        self.session_id = session_id
        self.timestamp = datetime.utcnow().isoformat()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary."""
        return {
            'event_id': self.event_id,
            'user_id': self.user_id,
            'game_id': self.game_id,
            'platform': self.platform,
            'app_version': self.app_version,
            'session_id': self.session_id,
            'timestamp': self.timestamp
        }


class InstallEvent(BaseEvent):
    """Install event sent when user installs the game."""
    
    def __init__(self, user_id: str, game_id: str, platform: str, 
                 app_version: str, session_id: str,
                 source: Optional[str] = None, country: Optional[str] = None):
        super().__init__(user_id, game_id, platform, app_version, session_id)
        self.event_type = "install"
        self.source = source
        self.country = country
    
    def to_dict(self) -> Dict[str, Any]:
        data = super().to_dict()
        data.update({
            'event_type': self.event_type,
            'source': self.source,
            'country': self.country
        })
        return data


class PurchaseEvent(BaseEvent):
    """Purchase event sent when user makes a purchase."""
    
    def __init__(self, user_id: str, game_id: str, platform: str,
                 app_version: str, session_id: str,
                 product_id: str, product_name: str, price: float, currency: str,
                 quantity: int = 1, store: Optional[str] = None):
        super().__init__(user_id, game_id, platform, app_version, session_id)
        self.event_type = "purchase"
        self.product_id = product_id
        self.product_name = product_name
        self.price = price
        self.currency = currency
        self.quantity = quantity
        self.store = store
        self.transaction_id = f"txn_{self.event_id}"
        
        # Basic validation
        if not product_id:
            raise ValueError("product_id is required")
        if price < 0:
            raise ValueError("price cannot be negative")
        if quantity <= 0:
            raise ValueError("quantity must be positive")
    
    def to_dict(self) -> Dict[str, Any]:
        data = super().to_dict()
        data.update({
            'event_type': self.event_type,
            'product_id': self.product_id,
            'product_name': self.product_name,
            'price': self.price,
            'currency': self.currency,
            'quantity': self.quantity,
            'store': self.store,
            'transaction_id': self.transaction_id
        })
        return data