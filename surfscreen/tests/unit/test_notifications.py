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
        assert WebhookStatus.INACTIVE.value == "inactive"
        assert WebhookStatus.FAILED.value == "failed"


class TestWebhookConfig:
    """Tests for Webhook dataclass."""
    
    def test_config_creation(self):
        """Test webhook configuration creation."""
        from surfscreen.notifications.webhook_client import Webhook
        
        webhook = Webhook(
            webhook_id="wh-123",
            url="https://example.com/webhook",
            name="Test Webhook",
            events=["job.completed", "job.failed"],
            secret="mysecret",
        )
        
        assert webhook.webhook_id == "wh-123"
        assert webhook.url == "https://example.com/webhook"
        assert len(webhook.events) == 2
    
    def test_config_to_dict(self):
        """Test webhook config serialization."""
        from surfscreen.notifications.webhook_client import Webhook, WebhookStatus
        
        webhook = Webhook(
            webhook_id="wh-123",
            url="https://example.com/webhook",
            name="Test Webhook",
            events=["job.completed"],
            secret="mysecret",
            status=WebhookStatus.ACTIVE,
        )
        
        data = webhook.to_dict()
        
        assert data["webhook_id"] == "wh-123"
        assert data["status"] == "active"
        # Note: secret is not included in to_dict()


class TestWebhookDelivery:
    """Tests for WebhookDelivery dataclass."""
    
    def test_delivery_creation(self):
        """Test webhook delivery record creation."""
        from surfscreen.notifications.webhook_client import WebhookDelivery
        
        delivery = WebhookDelivery(
            delivery_id="del-123",
            webhook_id="wh-123",
            event_type="job.completed",
            payload={},
            status="pending",
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
        
        client = WebhookClient()
        
        payload = '{"event": "test", "data": {"id": 123}}'
        secret = "mysecret"
        
        signature = client.generate_signature(payload, secret)
        
        assert signature is not None
        assert len(signature) == 64  # SHA256 hex digest
    
    def test_signature_verification(self):
        """Test signature verification."""
        from surfscreen.notifications.webhook_client import WebhookClient
        
        client = WebhookClient()
        
        payload = '{"event": "test", "data": {"id": 123}}'
        secret = "mysecret"
        
        # Generate signature
        signature = client.generate_signature(payload, secret)
        
        # Verify signature
        is_valid = client.verify_signature(payload, signature, secret)
        assert is_valid is True
        
        # Wrong signature should fail
        is_valid = client.verify_signature(payload, "wrongsignature", secret)
        assert is_valid is False
    
    @pytest.mark.asyncio
    async def test_send_webhook_success(self):
        """Test successful webhook sending."""
        from surfscreen.notifications.webhook_client import WebhookClient, Webhook
        
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.text.return_value = "OK"
        
        with patch("aiohttp.ClientSession") as mock_session:
            mock_session_instance = AsyncMock()
            mock_session_instance.post.return_value.__aenter__.return_value = mock_response
            mock_session.return_value.__aenter__.return_value = mock_session_instance
            
            client = WebhookClient()
            
            webhook = Webhook(
                webhook_id="wh-123",
                url="https://example.com/webhook",
                name="Test",
                events=["test"],
                secret="secret",
            )
            
            payload = {"event": "test", "data": {}}
            
            delivery = await client.send(webhook, "test", payload)
            
            assert delivery.status == "success"
            assert delivery.response_status == 200
    
    @pytest.mark.asyncio
    async def test_send_webhook_failure(self):
        """Test webhook sending with failure."""
        from surfscreen.notifications.webhook_client import WebhookClient, Webhook
        
        with patch("aiohttp.ClientSession") as mock_session:
            mock_session_instance = AsyncMock()
            mock_session_instance.post.side_effect = Exception("Connection refused")
            mock_session.return_value.__aenter__.return_value = mock_session_instance
            
            client = WebhookClient(max_retries=1)  # Reduce retries for test
            
            webhook = Webhook(
                webhook_id="wh-123",
                url="https://unreachable.example.com/webhook",
                name="Test",
                events=["test"],
                secret="secret",
            )
            
            delivery = await client.send(webhook, "test", {"event": "test"})
            
            assert delivery.status == "failed"
            assert "Connection refused" in str(delivery.error)


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
        notification_service.webhook_client = MagicMock()
        notification_service.webhook_client.send = AsyncMock(
            return_value=MagicMock(status="success")
        )
        
        await notification_service.send_notification(
            event_type=EventType.JOB_COMPLETED,
            title="Test",
            message="Test message",
            data={"job_id": "job-123", "status": "completed"},
        )
        
        notification_service.webhook_client.send.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_send_notification_filters_events(self, notification_service):
        """Test that notifications are only sent to relevant webhooks."""
        from surfscreen.notifications.notification_service import EventType
        
        # Register webhooks with different events
        notification_service.register_webhook("https://ex1.com", "WH1", ["job.completed"])
        notification_service.register_webhook("https://ex2.com", "WH2", ["job.failed"])
        notification_service.register_webhook("https://ex3.com", "WH3", ["batch.completed"])
        
        notification_service.webhook_client = MagicMock()
        notification_service.webhook_client.send = AsyncMock(
            return_value=MagicMock(status="success")
        )
        
        # Send job.failed event
        await notification_service.send_notification(
            event_type=EventType.JOB_FAILED,
            title="Job Failed",
            message="Job has failed",
            data={"job_id": "job-123"},
        )
        
        # Should only be called for WH2
        assert notification_service.webhook_client.send.call_count == 1
    
    @pytest.mark.asyncio
    async def test_test_webhook(self, notification_service):
        """Test sending test event to webhook."""
        webhook, _ = notification_service.register_webhook(
            url="https://example.com/webhook",
            name="Test",
            events=["job.completed"],
        )
        
        notification_service.webhook_client = MagicMock()
        notification_service.webhook_client.send = AsyncMock(
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
    
    def test_register_handler_with_decorator(self, notification_service):
        """Test registering event handler with decorator."""
        from surfscreen.notifications.notification_service import EventType
        
        handler_called = False
        
        @notification_service.on_event(EventType.JOB_COMPLETED)
        def my_handler(notification):
            nonlocal handler_called
            handler_called = True
        
        assert EventType.JOB_COMPLETED in notification_service._event_handlers
        assert my_handler in notification_service._event_handlers[EventType.JOB_COMPLETED]
    
    @pytest.mark.asyncio
    async def test_handler_invocation(self, notification_service):
        """Test that handlers are invoked on events."""
        from surfscreen.notifications.notification_service import EventType
        
        received_notifications = []
        
        @notification_service.on_event(EventType.JOB_COMPLETED)
        def capture_handler(notification):
            received_notifications.append(notification)
        
        await notification_service.send_notification(
            event_type=EventType.JOB_COMPLETED,
            title="Test",
            message="Test message",
            data={"job_id": "test-123"},
        )
        
        assert len(received_notifications) == 1
        assert received_notifications[0].data["job_id"] == "test-123"
    
    @pytest.mark.asyncio
    async def test_multiple_handlers(self, notification_service):
        """Test multiple handlers for same event."""
        from surfscreen.notifications.notification_service import EventType
        
        call_count = 0
        
        @notification_service.on_event(EventType.BATCH_COMPLETED)
        def handler1(notification):
            nonlocal call_count
            call_count += 1
        
        @notification_service.on_event(EventType.BATCH_COMPLETED)
        def handler2(notification):
            nonlocal call_count
            call_count += 1
        
        await notification_service.send_notification(
            event_type=EventType.BATCH_COMPLETED,
            title="Test",
            message="Test message",
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
            payload={},
            status="success",
        )
        
        # Directly append to deliveries list (as the service does internally)
        notification_service.deliveries.append(delivery)
        
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
                payload={},
                status="success",
            )
            notification_service.deliveries.append(delivery)
        
        history = notification_service.get_delivery_history(webhook_id="wh-123", limit=5)
        
        assert len(history) == 5


class TestNotificationPayload:
    """Tests for Notification dataclass."""
    
    def test_notification_creation(self):
        """Test notification creation."""
        from surfscreen.notifications.notification_service import Notification, EventType
        
        notification = Notification(
            notification_id="notif-123",
            event_type=EventType.JOB_COMPLETED,
            user_id="user-123",
            title="Job Completed",
            message="Job job-123 completed successfully",
            data={"job_id": "job-123", "status": "completed"},
        )
        
        assert notification.notification_id == "notif-123"
        assert notification.event_type == EventType.JOB_COMPLETED
        assert notification.read is False
    
    def test_notification_to_dict(self):
        """Test notification serialization."""
        from surfscreen.notifications.notification_service import Notification, EventType
        
        notification = Notification(
            notification_id="notif-123",
            event_type=EventType.JOB_COMPLETED,
            user_id="user-123",
            title="Job Completed",
            message="Job completed",
            data={"job_id": "job-123"},
            created_at="2026-01-01T12:00:00",
        )
        
        data = notification.to_dict()
        
        assert data["notification_id"] == "notif-123"
        assert data["event_type"] == "job.completed"
        assert data["title"] == "Job Completed"
        assert data["read"] is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
