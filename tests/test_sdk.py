"""
Tests for the Game Analytics SDK.
"""

import pytest
from unittest.mock import Mock, patch
from sdk.events import InstallEvent, PurchaseEvent
from sdk.client import GameAnalyticsClient


class TestEvents:
    """Test event classes."""
    
    def test_install_event_creation(self):
        """Test creating an install event."""
        event = InstallEvent(
            user_id="user123",
            game_id="game1",
            platform="ios",
            app_version="1.0.0",
            session_id="session123",
            source="organic",
            country="US"
        )
        
        assert event.user_id == "user123"
        assert event.event_type == "install"
        assert event.source == "organic"
        assert event.event_id is not None
    
    def test_install_event_to_dict(self):
        """Test converting install event to dict."""
        event = InstallEvent(
            user_id="user123",
            game_id="game1", 
            platform="ios",
            app_version="1.0.0",
            session_id="session123"
        )
        
        data = event.to_dict()
        assert data['user_id'] == "user123"
        assert data['event_type'] == "install"
        assert 'timestamp' in data
    
    def test_purchase_event_creation(self):
        """Test creating a purchase event."""
        event = PurchaseEvent(
            user_id="user123",
            game_id="game1",
            platform="ios", 
            app_version="1.0.0",
            session_id="session123",
            product_id="coins100",
            product_name="100 Coins",
            price=0.99,
            currency="USD"
        )
        
        assert event.product_id == "coins100"
        assert event.price == 0.99
        assert event.event_type == "purchase"
    
    def test_purchase_event_validation(self):
        """Test purchase event validation."""
        # Test empty product_id
        with pytest.raises(ValueError, match="product_id is required"):
            PurchaseEvent(
                user_id="user123",
                game_id="game1",
                platform="ios",
                app_version="1.0.0", 
                session_id="session123",
                product_id="",
                product_name="100 Coins",
                price=0.99,
                currency="USD"
            )
        
        # Test negative price
        with pytest.raises(ValueError, match="price cannot be negative"):
            PurchaseEvent(
                user_id="user123",
                game_id="game1",
                platform="ios",
                app_version="1.0.0",
                session_id="session123", 
                product_id="coins100",
                product_name="100 Coins",
                price=-1.0,
                currency="USD"
            )


class TestClient:
    """Test GameAnalyticsClient."""
    
    def setup_method(self):
        """Setup test fixtures."""
        self.client = GameAnalyticsClient(
            base_url="https://test-api.com",
            api_key="test-key"
        )
    
    def test_client_initialization(self):
        """Test client initialization."""
        assert self.client.base_url == "https://test-api.com"
        assert self.client.api_key == "test-key"
    
    @patch('sdk.client.requests.Session.post')
    def test_send_install_event_success(self, mock_post):
        """Test successful install event sending."""
        # Mock successful response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_post.return_value = mock_response
        
        # Create and send event
        event = InstallEvent(
            user_id="user123",
            game_id="game1",
            platform="ios",
            app_version="1.0.0",
            session_id="session123"
        )
        
        result = self.client.send_install_event(event)
        assert result is True
        mock_post.assert_called_once()
    
    @patch('sdk.client.requests.Session.post')
    def test_send_purchase_event_success(self, mock_post):
        """Test successful purchase event sending."""
        # Mock successful response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_post.return_value = mock_response
        
        # Create and send event
        event = PurchaseEvent(
            user_id="user123",
            game_id="game1",
            platform="ios",
            app_version="1.0.0",
            session_id="session123",
            product_id="coins100",
            product_name="100 Coins", 
            price=0.99,
            currency="USD"
        )
        
        result = self.client.send_purchase_event(event)
        assert result is True
        mock_post.assert_called_once()
    
    @patch('sdk.client.requests.Session.post')
    def test_send_event_failure(self, mock_post):
        """Test failed event sending."""
        # Mock failed response
        mock_response = Mock()
        mock_response.status_code = 500
        mock_post.return_value = mock_response
        
        event = InstallEvent(
            user_id="user123",
            game_id="game1",
            platform="ios", 
            app_version="1.0.0",
            session_id="session123"
        )
        
        result = self.client.send_install_event(event)
        assert result is False
    
    @patch('sdk.client.requests.Session.get')
    def test_health_check(self, mock_get):
        """Test health check."""
        # Mock successful health check
        mock_response = Mock()
        mock_response.status_code = 200
        mock_get.return_value = mock_response
        
        result = self.client.health_check()
        assert result is True
        mock_get.assert_called_with("https://test-api.com/health", timeout=30)