"""
Integration Tests for Webhooks API

Tests webhook management API endpoints.
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import MagicMock, patch, AsyncMock


@pytest.fixture
def mock_notification_service():
    """Create a mock NotificationService."""
    mock = MagicMock()
    
    # Mock webhook
    mock_webhook = MagicMock()
    mock_webhook.webhook_id = "wh-123"
    mock_webhook.url = "https://example.com/webhook"
    mock_webhook.name = "Test Webhook"
    mock_webhook.events = ["job.completed", "job.failed"]
    mock_webhook.status.value = "active"
    mock_webhook.created_at = "2026-01-01T00:00:00"
    mock_webhook.last_triggered = None
    mock_webhook.success_count = 10
    mock_webhook.failure_count = 2
    
    # Mock delivery
    mock_delivery = MagicMock()
    mock_delivery.delivery_id = "del-123"
    mock_delivery.webhook_id = "wh-123"
    mock_delivery.event_type = "job.completed"
    mock_delivery.status = "success"
    mock_delivery.created_at = "2026-01-01T12:00:00"
    mock_delivery.delivered_at = "2026-01-01T12:00:01"
    mock_delivery.response_status = 200
    mock_delivery.error = None
    mock_delivery.attempts = 1
    
    mock.register_webhook.return_value = (mock_webhook, "whsec_secret_key_123")
    mock.get_webhook.return_value = mock_webhook
    mock.list_webhooks.return_value = [mock_webhook]
    mock.update_webhook.return_value = mock_webhook
    mock.delete_webhook.return_value = True
    mock.regenerate_secret.return_value = "whsec_new_secret_456"
    mock.test_webhook = AsyncMock(return_value=mock_delivery)
    mock.get_delivery_history.return_value = [mock_delivery]
    
    return mock


@pytest.fixture
def client(mock_notification_service):
    """Create test client with mocked notification service."""
    with patch("surfscreen.api.routers.webhooks.get_notification_service", return_value=mock_notification_service):
        from surfscreen.api.main import app
        
        with TestClient(app) as client:
            yield client


class TestWebhookCreate:
    """Tests for webhook creation endpoint."""
    
    def test_create_webhook(self, client, mock_notification_service):
        """Test creating a webhook."""
        request_data = {
            "url": "https://example.com/webhooks/surfscreen",
            "name": "My Webhook",
            "events": ["job.completed", "job.failed", "batch.completed"],
        }
        
        response = client.post("/api/v1/webhooks", json=request_data)
        
        assert response.status_code == 200
        data = response.json()
        
        assert "webhook_id" in data
        assert "secret" in data  # Secret returned on creation
        mock_notification_service.register_webhook.assert_called_once()
    
    def test_create_webhook_invalid_url(self, client):
        """Test creating webhook with invalid URL."""
        request_data = {
            "url": "not-a-valid-url",
            "name": "Bad Webhook",
            "events": ["job.completed"],
        }
        
        response = client.post("/api/v1/webhooks", json=request_data)
        
        # Should return validation error
        assert response.status_code in [400, 422]
    
    def test_create_webhook_empty_events(self, client):
        """Test creating webhook with no events."""
        request_data = {
            "url": "https://example.com/webhook",
            "name": "Empty Events",
            "events": [],
        }
        
        response = client.post("/api/v1/webhooks", json=request_data)
        
        assert response.status_code == 422


class TestWebhookList:
    """Tests for webhook list endpoint."""
    
    def test_list_webhooks(self, client, mock_notification_service):
        """Test listing webhooks."""
        response = client.get("/api/v1/webhooks")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "webhooks" in data
        assert "total" in data
    
    def test_list_webhooks_with_status_filter(self, client, mock_notification_service):
        """Test listing with status filter."""
        response = client.get("/api/v1/webhooks?status=active")
        
        assert response.status_code == 200
    
    def test_list_webhooks_with_event_filter(self, client, mock_notification_service):
        """Test listing with event filter."""
        response = client.get("/api/v1/webhooks?event=job.completed")
        
        assert response.status_code == 200


class TestWebhookGet:
    """Tests for webhook get endpoint."""
    
    def test_get_webhook(self, client, mock_notification_service):
        """Test getting a webhook."""
        response = client.get("/api/v1/webhooks/wh-123")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["webhook_id"] == "wh-123"
        assert "secret" not in data  # Secret should not be returned after creation
    
    def test_get_webhook_not_found(self, client, mock_notification_service):
        """Test getting non-existent webhook."""
        mock_notification_service.get_webhook.return_value = None
        
        response = client.get("/api/v1/webhooks/nonexistent")
        
        assert response.status_code == 404


class TestWebhookUpdate:
    """Tests for webhook update endpoint."""
    
    def test_update_webhook(self, client, mock_notification_service):
        """Test updating a webhook."""
        request_data = {
            "name": "Updated Name",
            "events": ["job.completed", "batch.completed"],
        }
        
        response = client.put("/api/v1/webhooks/wh-123", json=request_data)
        
        assert response.status_code == 200
    
    def test_update_webhook_status(self, client, mock_notification_service):
        """Test pausing a webhook via update."""
        request_data = {
            "status": "paused",
        }
        
        response = client.put("/api/v1/webhooks/wh-123", json=request_data)
        
        assert response.status_code == 200


class TestWebhookDelete:
    """Tests for webhook delete endpoint."""
    
    def test_delete_webhook(self, client, mock_notification_service):
        """Test deleting a webhook."""
        response = client.delete("/api/v1/webhooks/wh-123")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["deleted"] is True
        mock_notification_service.delete_webhook.assert_called_with("wh-123")
    
    def test_delete_webhook_not_found(self, client, mock_notification_service):
        """Test deleting non-existent webhook."""
        mock_notification_service.delete_webhook.return_value = False
        
        response = client.delete("/api/v1/webhooks/nonexistent")
        
        assert response.status_code == 404


class TestWebhookTest:
    """Tests for webhook test endpoint."""
    
    def test_test_webhook(self, client, mock_notification_service):
        """Test sending test event to webhook."""
        response = client.post("/api/v1/webhooks/wh-123/test")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "success" in data
        assert "delivery_id" in data
    
    def test_test_webhook_not_found(self, client, mock_notification_service):
        """Test testing non-existent webhook."""
        mock_notification_service.test_webhook.side_effect = ValueError("Webhook not found")
        
        response = client.post("/api/v1/webhooks/nonexistent/test")
        
        assert response.status_code == 404


class TestWebhookSecretRotation:
    """Tests for webhook secret rotation endpoint."""
    
    def test_rotate_secret(self, client, mock_notification_service):
        """Test rotating webhook secret."""
        response = client.post("/api/v1/webhooks/wh-123/rotate-secret")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "secret" in data
        assert data["secret"] == "whsec_new_secret_456"
    
    def test_rotate_secret_not_found(self, client, mock_notification_service):
        """Test rotating secret for non-existent webhook."""
        mock_notification_service.regenerate_secret.return_value = None
        
        response = client.post("/api/v1/webhooks/nonexistent/rotate-secret")
        
        assert response.status_code == 404


class TestWebhookDeliveries:
    """Tests for webhook deliveries endpoint."""
    
    def test_get_deliveries(self, client, mock_notification_service):
        """Test getting delivery history."""
        response = client.get("/api/v1/webhooks/wh-123/deliveries")
        
        assert response.status_code == 200
        data = response.json()
        
        assert isinstance(data, list)
        assert len(data) >= 0
    
    def test_get_deliveries_with_limit(self, client, mock_notification_service):
        """Test getting deliveries with limit."""
        response = client.get("/api/v1/webhooks/wh-123/deliveries?limit=10")
        
        assert response.status_code == 200


class TestEventTypes:
    """Tests for event types endpoint."""
    
    def test_list_event_types(self, client):
        """Test listing available event types."""
        response = client.get("/api/v1/webhooks/events/types")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "event_types" in data
        assert len(data["event_types"]) > 0
        
        # Check structure of event types
        event = data["event_types"][0]
        assert "type" in event
        assert "description" in event


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
