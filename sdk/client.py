"""
HTTP client for sending events to the analytics API.
"""

import requests
import logging
from typing import Union
from .events import InstallEvent, PurchaseEvent

logger = logging.getLogger(__name__)


class GameAnalyticsClient:
    """Client for sending game events to the analytics API."""
    
    def __init__(self, base_url: str, api_key: str, timeout: int = 30):
        """
        Initialize the client.
        
        Args:
            base_url: API base URL
            api_key: API key for authentication
            timeout: Request timeout in seconds
        """
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        self.timeout = timeout
        
        # Setup session with headers
        self.session = requests.Session()
        self.session.headers.update({
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {self.api_key}'
        })
    
    def send_install_event(self, event: InstallEvent) -> bool:
        """
        Send an install event.
        
        Args:
            event: InstallEvent to send
            
        Returns:
            True if successful, False otherwise
        """
        return self._send_event('/events/install', event)
    
    def send_purchase_event(self, event: PurchaseEvent) -> bool:
        """
        Send a purchase event.
        
        Args:
            event: PurchaseEvent to send
            
        Returns:
            True if successful, False otherwise
        """
        return self._send_event('/events/purchase', event)
    
    def _send_event(self, endpoint: str, event: Union[InstallEvent, PurchaseEvent]) -> bool:
        """Send event to API endpoint."""
        url = f"{self.base_url}{endpoint}"
        
        try:
            response = self.session.post(
                url,
                json=event.to_dict(),
                timeout=self.timeout
            )
            
            if response.status_code == 200:
                logger.info(f"Event sent successfully: {event.event_id}")
                return True
            else:
                logger.error(f"Failed to send event: {response.status_code}")
                return False
                
        except requests.RequestException as e:
            logger.error(f"Request failed: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            return False
    
    def health_check(self) -> bool:
        """Check if API is healthy."""
        try:
            response = self.session.get(f"{self.base_url}/health", timeout=self.timeout)
            return response.status_code == 200
        except Exception:
            return False