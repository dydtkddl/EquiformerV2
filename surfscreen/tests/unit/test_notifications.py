"""
Unit Tests for Notifications Module

Tests NotificationService, WebhookClient, and event handling.
"""

import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from datetime import datetime
from pathlib import Path
import tempfile
import json
import hashlib
import hmac


class TestEventType:
    """Tests for EventType enum."""
    
    def test_event_type_values(self):
        """Test event type values."""
        from surfscreen.notifications.notification_service import EventType
        
        assert EventType.JOB_SUBMITTED.value == "job.submitted"
        assert EventType.JOB_COMPLETED.value == "job.completed"
        assert EventType.JOB_FAILED.value == "job.failed"
        assert EventType.BATCH_COMPLETED.value == "batch.completed"
        assert EventType.QUOTA_WARNING.value == "quota.warning"


class TestWebhookStatus:
    """Tests for WebhookStatus enum."""
    
    def test_webhook_status_values(self):
        """Test webhook status values."""
        from surfscreen.notifications.webhook_client import WebhookStatus
        
        assert WebhookStatus.ACTIVE.value == "active"
        assert WebhookStatus.PAUSED.value == "paused"
        assert WebhookStatus.FAILED.value == "failed"


class TestWebhookConfig:
    """Tests for WebhookConfig dataclass."""
    
    def test_config_creation(self):
        """Test webhook configuration creation."""
        from surfscreen.notifications.webhook_client import WebhookConfig
        
        config = WebhookConfig(
            webhook_id="wh-123",
            url="https://example.com/webhook",
            name="Test Webhook",
            events=["job.completed", "job.failed"],
            secret="mysecret",
        )
        
        assert config.webhook_id == "wh-123"
        assert config.url == "https://example.com/webhook"
        assert len(config.events) == 2
    
    def test_config_to_dict(self):
        """Test webhook config serialization."""
        from surfscreen.notifications.webhook_client import WebhookConfig, WebhookStatus
        
        config = WebhookConfig(
            webhook_id="wh-123",
            url="https://example.com/webhook",
            name="Test Webhook",
            events=["job.completed"],
            secret="mysecret",
            status=WebhookStatus.ACTIVE,
        )
        
        data = config.to_dict()
        
        assert data["webhook_id"] == "wh-123"
        assert data["status"] == "active"
        assert "secret" not in data  # Should not include secret in serialization


class TestWebhookDelivery:
    """Tests for WebhookDelivery dataclass."""
    
    def test_delivery_creation(self):
        """Test webhook delivery record creation."""
        from surfscreen.notifications.webhook_client import WebhookDelivery
        
        delivery = WebhookDelivery(
            delivery_id="del-123",
            webhook_id="wh-123",
            event_type="job.completed",
        )
        
        assert delivery.delivery_id == "del-123"
        assert delivery.status == "pending"
        assert delivery.attempts == 0
    
    def test_delivery_success(self):
        """Test successful delivery."""
        from surfscreen.notifications.webhook_client import WebhookDelivery
        
        delivery = WebhookDelivery(
            delivery_id="del-123",
            webhook_id="wh-123",
            event_type="job.completed",
            status="success",
            response_status=200,
            delivered_at="2026-01-01T12:00:00",
            attempts=1,
        )
        
        assert delivery.status == "success"
        assert delivery.response_status == 200
    
    def test_delivery_failure(self):
        """Test failed delivery."""
        from surfscreen.notifications.webhook_client import WebhookDelivery
        
        delivery = WebhookDelivery(
            delivery_id="del-123",
            webhook_id="wh-123",
            event_type="job.completed",
            status="failed",
            error="Connection refused",
            attempts=3,
        )
        
        assert delivery.status == "failed"
        assert delivery.error == "Connection refused"


class TestWebhookClient:
    """Tests for WebhookClient class."""
    
    def test_signature_generation(self):
        """Test HMAC signature generation."""
        from surfscreen.notifications.webhook_client import WebhookClient
        
        client = WebhookClient.__new__(WebhookClient)
        
        payload = {"event": "test", "data": {"id": 123}}
        secret = "mysecret"
        
        signature = client._generate_signature(payload, secret)
        
        assert signature is not None
        assert len(signature) == 64  # SHA256 hex digest
    
    def test_signature_verification(self):
        """Test signature verification."""
        from surfscreen.notifications.webhook_client import WebhookClient
        
        client = WebhookClient.__new__(WebhookClient)
        
        payload = {"event": "test", "data": {"id": 123}}
        secret = "mysecret"
        
        # Generate signature
        signature = client._generate_signature(payload, secret)
        
        # Verify signature
        is_valid = client._verify_signature(payload, secret, signature)
        assert is_valid is True
        
        # Wrong signature should fail
        is_valid = client._verify_signature(payload, secret, "wrongsignature")
        assert is_valid is False
    
    @pytest.mark.asyncio
    async def test_send_webhook_success(self):
        """Test successful webhook sending."""
        from surfscreen.notifications.webhook_client import WebhookClient, WebhookConfig
        
        mock_response = AsyncMock()
        mock_response.status = 200
        
        with patch("aiohttp.ClientSession") as mock_session:
            mock_session_instance = AsyncMock()
            mock_session_instance.post.return_value.__aenter__.return_value = mock_response
            mock_session.return_value.__aenter__.return_value = mock_session_instance
            
            client = WebhookClient()
            
            config = WebhookConfig(
                webhook_id="wh-123",
                url="https://example.com/webhook",
                name="Test",
                events=["test"],
                secret="secret",
            )
            
            payload = {"event": "test", "data": {}}
            
            delivery = await client.send_webhook(config, payload)
            
            assert delivery.status == "success"
            assert delivery.response_status == 200
    
    @pytest.mark.asyncio
    async def test_send_webhook_failure(self):
        """Test webhook sending with failure."""
        from surfscreen.notifications.webhook_client import WebhookClient, WebhookConfig
        
        with patch("aiohttp.ClientSession") as mock_session:
            mock_session_instance = AsyncMock()
            mock_session_instance.post.side_effect = Exception("Connection refused")
            mock_session.return_value.__aenter__.return_value = mock_session_instance
            
            client = WebhookClient(max_retries=1)  # Reduce retries for test
            
            config = WebhookConfig(
                webhook_id="wh-123",
                url="https://unreachable.example.com/webhook",
                name="Test",
                events=["test"],
                secret="secret",
            )
            
            delivery = await client.send_webhook(config, {"event": "test"})
            
            assert delivery.status == "failed"
            assert "Connection refused" in delivery.error


class TestNotificationService:
    """Tests for NotificationService class."""
    
    @pytest.fixture
    def notification_service(self):
        """Create a NotificationService instance."""
        with tempfile.TemporaryDirectory() as tmpdir:
            from surfscreen.notifications.notification_service import NotificationService
            
            service = NotificationService(storage_dir=Path(tmpdir))
            yield service
    
    def test_service_creation(self):
        """Test notification service initialization."""
        from surfscreen.notifications.notification_service import NotificationService
        
        with tempfile.TemporaryDirectory() as tmpdir:
            service = NotificationService(storage_dir=Path(tmpdir))
            
            assert service.storage_dir == Path(tmpdir)
    
    def test_register_webhook(self, notification_service):
        """Test webhook registration."""
        webhook, secret = notification_service.register_webhook(
            url="https://example.com/webhook",
            name="Test Webhook",
            events=["job.completed", "job.failed"],
        )
        
        assert webhook.url == "https://example.com/webhook"
        assert webhook.name == "Test Webhook"
        assert len(webhook.events) == 2
        assert secret is not None
    
    def test_get_webhook(self, notification_service):
        """Test getting a webhook."""
        webhook, _ = notification_service.register_webhook(
            url="https://example.com/webhook",
            name="Test",
            events=["job.completed"],
        )
        
        retrieved = notification_service.get_webhook(webhook.webhook_id)
        
        assert retrieved.webhook_id == webhook.webhook_id
        assert notification_service.get_webhook("nonexistent") is None
    
    def test_update_webhook(self, notification_service):
        """Test updating a webhook."""
        webhook, _ = notification_service.register_webhook(
            url="https://example.com/webhook",
            name="Original",
            events=["job.completed"],
        )
        
        updated = notification_service.update_webhook(
            webhook_id=webhook.webhook_id,
            name="Updated Name",
            events=["job.completed", "job.failed", "batch.completed"],
        )
        
        assert updated.name == "Updated Name"
        assert len(updated.events) == 3
    
    def test_delete_webhook(self, notification_service):
        """Test deleting a webhook."""
        webhook, _ = notification_service.register_webhook(
            url="https://example.com/webhook",
            name="Delete Me",
            events=["job.completed"],
        )
        
        success = notification_service.delete_webhook(webhook.webhook_id)
        
        assert success is True
        assert notification_service.get_webhook(webhook.webhook_id) is None
    
    def test_list_webhooks(self, notification_service):
        """Test listing webhooks."""
        from surfscreen.notifications.webhook_client import WebhookStatus
        
        notification_service.register_webhook("https://ex1.com", "WH1", ["job.completed"])
        notification_service.register_webhook("https://ex2.com", "WH2", ["job.failed"])
        notification_service.register_webhook("https://ex3.com", "WH3", ["batch.completed"])
        
        # List all
        all_webhooks = notification_service.list_webhooks()
        assert len(all_webhooks) == 3
        
        # Filter by event
        job_webhooks = notification_service.list_webhooks(event="job.completed")
        assert len(job_webhooks) == 1
    
    def test_regenerate_secret(self, notification_service):
        """Test regenerating webhook secret."""
        webhook, original_secret = notification_service.register_webhook(
            url="https://example.com/webhook",
            name="Test",
            events=["job.completed"],
        )
        
        new_secret = notification_service.regenerate_secret(webhook.webhook_id)
        
        assert new_secret is not None
        assert new_secret != original_secret
    
    @pytest.mark.asyncio
    async def test_send_notification(self, notification_service):
        """Test sending notification to webhooks."""
        from surfscreen.notifications.notification_service import EventType
        
        notification_service.register_webhook(
            url="https://example.com/webhook",
            name="Test",
            events=["job.completed"],
        )
        
        # Mock the webhook client
        notification_service._webhook_client = MagicMock()
        notification_service._webhook_client.send_webhook = AsyncMock(
            return_value=MagicMock(status="success")
        )
        
        await notification_service.send_notification(
            event_type=EventType.JOB_COMPLETED,
            data={"job_id": "job-123", "status": "completed"},
        )
        
        notification_service._webhook_client.send_webhook.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_send_notification_filters_events(self, notification_service):
        """Test that notifications are only sent to relevant webhooks."""
        from surfscreen.notifications.notification_service import EventType
        
        # Register webhooks with different events
        notification_service.register_webhook("https://ex1.com", "WH1", ["job.completed"])
        notification_service.register_webhook("https://ex2.com", "WH2", ["job.failed"])
        notification_service.register_webhook("https://ex3.com", "WH3", ["batch.completed"])
        
        notification_service._webhook_client = MagicMock()
        notification_service._webhook_client.send_webhook = AsyncMock(
            return_value=MagicMock(status="success")
        )
        
        # Send job.failed event
        await notification_service.send_notification(
            event_type=EventType.JOB_FAILED,
            data={"job_id": "job-123"},
        )
        
        # Should only be called for WH2
        assert notification_service._webhook_client.send_webhook.call_count == 1
    
    @pytest.mark.asyncio
    async def test_test_webhook(self, notification_service):
        """Test sending test event to webhook."""
        webhook, _ = notification_service.register_webhook(
            url="https://example.com/webhook",
            name="Test",
            events=["job.completed"],
        )
        
        notification_service._webhook_client = MagicMock()
        notification_service._webhook_client.send_webhook = AsyncMock(
            return_value=MagicMock(status="success", response_status=200)
        )
        
        delivery = await notification_service.test_webhook(webhook.webhook_id)
        
        assert delivery.status == "success"


class TestEventHandlers:
    """Tests for event handler registration and invocation."""
    
    @pytest.fixture
    def notification_service(self):
        """Create a NotificationService instance."""
        with tempfile.TemporaryDirectory() as tmpdir:
            from surfscreen.notifications.notification_service import NotificationService
            
            service = NotificationService(storage_dir=Path(tmpdir))
            yield service
    
    def test_register_handler(self, notification_service):
        """Test registering event handler."""
        from surfscreen.notifications.notification_service import EventType
        
        handler_called = False
        
        def my_handler(event_type, data):
            nonlocal handler_called
            handler_called = True
        
        notification_service.register_handler(EventType.JOB_COMPLETED, my_handler)
        
        assert EventType.JOB_COMPLETED in notification_service._handlers
        assert my_handler in notification_service._handlers[EventType.JOB_COMPLETED]
    
    @pytest.mark.asyncio
    async def test_handler_invocation(self, notification_service):
        """Test that handlers are invoked on events."""
        from surfscreen.notifications.notification_service import EventType
        
        received_data = []
        
        def capture_handler(event_type, data):
            received_data.append((event_type, data))
        
        notification_service.register_handler(EventType.JOB_COMPLETED, capture_handler)
        
        await notification_service.send_notification(
            event_type=EventType.JOB_COMPLETED,
            data={"job_id": "test-123"},
        )
        
        assert len(received_data) == 1
        assert received_data[0][1]["job_id"] == "test-123"
    
    @pytest.mark.asyncio
    async def test_multiple_handlers(self, notification_service):
        """Test multiple handlers for same event."""
        from surfscreen.notifications.notification_service import EventType
        
        call_count = 0
        
        def handler1(event_type, data):
            nonlocal call_count
            call_count += 1
        
        def handler2(event_type, data):
            nonlocal call_count
            call_count += 1
        
        notification_service.register_handler(EventType.BATCH_COMPLETED, handler1)
        notification_service.register_handler(EventType.BATCH_COMPLETED, handler2)
        
        await notification_service.send_notification(
            event_type=EventType.BATCH_COMPLETED,
            data={},
        )
        
        assert call_count == 2


class TestDeliveryHistory:
    """Tests for delivery history tracking."""
    
    @pytest.fixture
    def notification_service(self):
        """Create a NotificationService instance."""
        with tempfile.TemporaryDirectory() as tmpdir:
            from surfscreen.notifications.notification_service import NotificationService
            
            service = NotificationService(storage_dir=Path(tmpdir))
            yield service
    
    def test_record_delivery(self, notification_service):
        """Test recording delivery in history."""
        from surfscreen.notifications.webhook_client import WebhookDelivery
        
        delivery = WebhookDelivery(
            delivery_id="del-123",
            webhook_id="wh-123",
            event_type="job.completed",
            status="success",
        )
        
        notification_service._record_delivery(delivery)
        
        history = notification_service.get_delivery_history(webhook_id="wh-123")
        
        assert len(history) == 1
        assert history[0].delivery_id == "del-123"
    
    def test_get_delivery_history_limit(self, notification_service):
        """Test delivery history with limit."""
        from surfscreen.notifications.webhook_client import WebhookDelivery
        
        for i in range(10):
            delivery = WebhookDelivery(
                delivery_id=f"del-{i}",
                webhook_id="wh-123",
                event_type="job.completed",
                status="success",
            )
            notification_service._record_delivery(delivery)
        
        history = notification_service.get_delivery_history(webhook_id="wh-123", limit=5)
        
        assert len(history) == 5


class TestNotificationPayload:
    """Tests for notification payload construction."""
    
    def test_job_completed_payload(self):
        """Test payload for job completed event."""
        from surfscreen.notifications.notification_service import NotificationService, EventType
        
        service = NotificationService.__new__(NotificationService)
        
        payload = service._build_payload(
            event_type=EventType.JOB_COMPLETED,
            data={
                "job_id": "job-123",
                "job_type": "screening",
                "status": "completed",
                "result": {"energy": -1.5},
            },
        )
        
        assert payload["event"] == "job.completed"
        assert payload["data"]["job_id"] == "job-123"
        assert "timestamp" in payload
    
    def test_quota_warning_payload(self):
        """Test payload for quota warning event."""
        from surfscreen.notifications.notification_service import NotificationService, EventType
        
        service = NotificationService.__new__(NotificationService)
        
        payload = service._build_payload(
            event_type=EventType.QUOTA_WARNING,
            data={
                "user_id": "user-123",
                "quota_type": "jobs",
                "used": 90,
                "limit": 100,
            },
        )
        
        assert payload["event"] == "quota.warning"
        assert payload["data"]["used"] == 90


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
