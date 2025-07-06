"""
Game Analytics SDK

A simple Python SDK for sending game events to the analytics API.
"""

from .events import InstallEvent, PurchaseEvent
from .client import GameAnalyticsClient

__version__ = "1.0.0"

__all__ = [
    "InstallEvent",
    "PurchaseEvent", 
    "GameAnalyticsClient"
]