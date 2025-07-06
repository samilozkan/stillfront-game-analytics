"""
Tests for the Game Analytics API.
"""

import pytest
from datetime import datetime
from fastapi.testclient import TestClient
from api.main import app


class TestAPI:
    """Test the Game Analytics API."""
    
    def setup_method(self):
        """Setup test fixtures."""
        self.client = TestClient(app)
        self.headers = {"Authorization": "Bearer your-api-key-here"}
    
    def test_root_endpoint(self):
        """Test root endpoint."""
        response = self.client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Game Analytics API"
    
    def test_health_check(self):
        """Test health check endpoint."""
        response = self.client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "timestamp" in data
    
    def test_install_event_success(self):
        """Test successful install event submission."""
        event_data = {
            "event_id": "evt_123",
            "user_id": "user_123",
            "game_id": "test_game",
            "timestamp": datetime.utcnow().isoformat(),
            "platform": "ios",
            "app_version": "1.0.0",
            "session_id": "session_123",
            "source": "organic",
            "country": "US"
        }
        
        response = self.client.post(
            "/events/install",
            json=event_data,
            headers=self.headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["event_id"] == "evt_123"
    
    def test_purchase_event_success(self):
        """Test successful purchase event submission."""
        event_data = {
            "event_id": "evt_456", 
            "user_id": "user_123",
            "game_id": "test_game",
            "timestamp": datetime.utcnow().isoformat(),
            "platform": "ios",
            "app_version": "1.0.0",
            "session_id": "session_123",
            "product_id": "coins100",
            "product_name": "100 Coins",
            "price": 0.99,
            "currency": "USD"
        }
        
        response = self.client.post(
            "/events/purchase",
            json=event_data,
            headers=self.headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["event_id"] == "evt_456"
    
    def test_unauthorized_access(self):
        """Test unauthorized access."""
        event_data = {
            "event_id": "evt_123",
            "user_id": "user_123", 
            "game_id": "test_game",
            "timestamp": datetime.utcnow().isoformat(),
            "platform": "ios",
            "app_version": "1.0.0",
            "session_id": "session_123"
        }
        
        # No authorization header
        response = self.client.post("/events/install", json=event_data)
        assert response.status_code == 403
        
        # Wrong API key
        wrong_headers = {"Authorization": "Bearer wrong-key"}
        response = self.client.post("/events/install", json=event_data, headers=wrong_headers)
        assert response.status_code == 401
    
    def test_validation_error(self):
        """Test validation error."""
        # Missing required field
        event_data = {
            "event_id": "evt_123",
            # Missing user_id
            "game_id": "test_game",
            "timestamp": datetime.utcnow().isoformat(),
            "platform": "ios",
            "app_version": "1.0.0",
            "session_id": "session_123"
        }
        
        response = self.client.post(
            "/events/install",
            json=event_data,
            headers=self.headers
        )
        
        assert response.status_code == 422  # Validation error
    
    def test_purchase_validation_error(self):
        """Test purchase event validation."""
        # Negative price
        event_data = {
            "event_id": "evt_123",
            "user_id": "user_123",
            "game_id": "test_game", 
            "timestamp": datetime.utcnow().isoformat(),
            "platform": "ios",
            "app_version": "1.0.0",
            "session_id": "session_123",
            "product_id": "coins100",
            "product_name": "100 Coins",
            "price": -1.0,  # Invalid negative price
            "currency": "USD"
        }
        
        response = self.client.post(
            "/events/purchase",
            json=event_data,
            headers=self.headers
        )
        
        assert response.status_code == 422  # Validation error


class TestFirehoseIntegration:
    """Test Firehose integration."""
    
    def test_mock_firehose_client(self):
        """Test mock Firehose client."""
        from api.firehose_client import MockFirehoseClient
        
        client = MockFirehoseClient()
        
        # Test sending event
        event_data = {"event_id": "test_123", "user_id": "user_123"}
        result = client.send_event(event_data)
        assert result is True
        
        # Test health check
        assert client.health_check() is True
        
        # Check sent events
        sent_events = client.get_sent_events()
        assert len(sent_events) == 1
        assert sent_events[0]["event_id"] == "test_123"