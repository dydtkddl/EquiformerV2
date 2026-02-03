"""
Notification Service

Central notification system with webhook, email, and WebSocket support.
"""

import asyncio
import json
import logging
import secrets
import uuid
from datetime import datetime
from pathlib import Path
from threading import Lock
from typing import Any, Callable, Dict, List, Optional, Tuple
from enum import Enum
from dataclasses import dataclass, field

from .webhook_client import WebhookClient, Webhook, WebhookStatus, WebhookDelivery

logger = logging.getLogger(__name__)


class EventType(str, Enum):
    """Notification event types."""
    
    JOB_SUBMITTED = "job.submitted"
    JOB_STARTED = "job.started"
    JOB_COMPLETED = "job.completed"
    JOB_FAILED = "job.failed"
    
    BATCH_SUBMITTED = "batch.submitted"
    BATCH_COMPLETED = "batch.completed"
    BATCH_PARTIAL = "batch.partial"
    BATCH_FAILED = "batch.failed"
    
    SCHEDULE_TRIGGERED = "schedule.triggered"
    SCHEDULE_COMPLETED = "schedule.completed"
    SCHEDULE_FAILED = "schedule.failed"
    
    QUOTA_WARNING = "quota.warning"
    QUOTA_EXCEEDED = "quota.exceeded"


@dataclass
class Notification:
    """Notification record."""
    
    notification_id: str
    event_type: EventType
    user_id: Optional[str]
    title: str
    message: str
    data: Dict[str, Any] = field(default_factory=dict)
    
    # Status
    created_at: str = ""
    read: bool = False
    read_at: Optional[str] = None
    
    # Channels
    sent_webhook: bool = False
    sent_email: bool = False
    sent_websocket: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "notification_id": self.notification_id,
            "event_type": self.event_type.value,
            "user_id": self.user_id,
            "title": self.title,
            "message": self.message,
            "data": self.data,
            "created_at": self.created_at,
            "read": self.read,
        }


class NotificationService:
    """
    Central notification service.
    
    Supports multiple channels:
    - Webhooks (HTTP callbacks)
    - Email (placeholder)
    - WebSocket (real-time)
    """
    
    def __init__(self, storage_dir: Optional[Path] = None):
        """
        Initialize notification service.
        
        Args:
            storage_dir: Directory for persistent storage
        """
        self.storage_dir = storage_dir or Path.cwd() / "notifications"
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        
        self.webhooks: Dict[str, Webhook] = {}
        self.notifications: Dict[str, Notification] = {}
        self.deliveries: List[WebhookDelivery] = []
        
        self.webhook_client = WebhookClient()
        self._lock = Lock()
        
        # Event handlers for extensibility
        self._event_handlers: Dict[EventType, List[Callable]] = {}
        
        # WebSocket connections (placeholder)
        self._websocket_connections: Dict[str, Any] = {}
        
        # Load persisted data
        self._load_data()
    
    # ========================================
    # Webhook Management
    # ========================================
    
    def register_webhook(
        self,
        url: str,
        name: str,
        events: List[str],
        user_id: Optional[str] = None,
    ) -> Tuple[Webhook, str]:
        """
        Register a new webhook.
        
        Args:
            url: Webhook URL
            name: Webhook name
            events: List of event types to subscribe
            user_id: Optional user ID
            
        Returns:
            Tuple of (Webhook, secret)
        """
        webhook_id = str(uuid.uuid4())
        secret = secrets.token_urlsafe(32)
        now = datetime.utcnow().isoformat()
        
        webhook = Webhook(
            webhook_id=webhook_id,
            url=url,
            secret=secret,
            name=name,
            events=events,
            created_at=now,
        )
        
        with self._lock:
            self.webhooks[webhook_id] = webhook
        
        self._save_data()
        logger.info(f"Registered webhook: {webhook_id} ({name})")
        
        return webhook, secret
    
    def get_webhook(self, webhook_id: str) -> Optional[Webhook]:
        """Get webhook by ID."""
        with self._lock:
            return self.webhooks.get(webhook_id)
    
    def list_webhooks(
        self,
        status: Optional[WebhookStatus] = None,
        event: Optional[str] = None,
    ) -> List[Webhook]:
        """List webhooks with optional filtering."""
        with self._lock:
            webhooks = list(self.webhooks.values())
        
        if status:
            webhooks = [w for w in webhooks if w.status == status]
        
        if event:
            webhooks = [w for w in webhooks if event in w.events]
        
        return webhooks
    
    def update_webhook(
        self,
        webhook_id: str,
        name: Optional[str] = None,
        url: Optional[str] = None,
        events: Optional[List[str]] = None,
        status: Optional[WebhookStatus] = None,
    ) -> Optional[Webhook]:
        """Update webhook configuration."""
        with self._lock:
            webhook = self.webhooks.get(webhook_id)
            
            if not webhook:
                return None
            
            if name:
                webhook.name = name
            if url:
                webhook.url = url
            if events:
                webhook.events = events
            if status:
                webhook.status = status
        
        self._save_data()
        
        return webhook
    
    def delete_webhook(self, webhook_id: str) -> bool:
        """Delete a webhook."""
        with self._lock:
            if webhook_id not in self.webhooks:
                return False
            
            del self.webhooks[webhook_id]
        
        self._save_data()
        logger.info(f"Deleted webhook: {webhook_id}")
        
        return True
    
    def regenerate_secret(self, webhook_id: str) -> Optional[str]:
        """Regenerate webhook secret."""
        with self._lock:
            webhook = self.webhooks.get(webhook_id)
            
            if not webhook:
                return None
            
            new_secret = secrets.token_urlsafe(32)
            webhook.secret = new_secret
        
        self._save_data()
        
        return new_secret
    
    # ========================================
    # Notification Sending
    # ========================================
    
    async def send_notification(
        self,
        event_type: EventType,
        title: str,
        message: str,
        data: Optional[Dict[str, Any]] = None,
        user_id: Optional[str] = None,
    ) -> Notification:
        """
        Send a notification through all applicable channels.
        
        Args:
            event_type: Type of event
            title: Notification title
            message: Notification message
            data: Additional data
            user_id: Target user ID
            
        Returns:
            Created Notification
        """
        notification_id = str(uuid.uuid4())[:12]
        now = datetime.utcnow().isoformat()
        
        notification = Notification(
            notification_id=notification_id,
            event_type=event_type,
            user_id=user_id,
            title=title,
            message=message,
            data=data or {},
            created_at=now,
        )
        
        with self._lock:
            self.notifications[notification_id] = notification
        
        # Send to webhooks
        await self._send_to_webhooks(notification)
        
        # Send to WebSocket (if connected)
        await self._send_to_websocket(notification)
        
        # Call event handlers
        await self._call_event_handlers(event_type, notification)
        
        self._save_data()
        
        logger.info(f"Notification sent: {event_type.value} - {title}")
        
        return notification
    
    def send_notification_sync(
        self,
        event_type: EventType,
        title: str,
        message: str,
        data: Optional[Dict[str, Any]] = None,
        user_id: Optional[str] = None,
    ) -> Notification:
        """Synchronous version of send_notification."""
        return asyncio.run(
            self.send_notification(event_type, title, message, data, user_id)
        )
    
    async def _send_to_webhooks(self, notification: Notification):
        """Send notification to matching webhooks."""
        event_str = notification.event_type.value
        
        webhooks_to_notify = [
            w for w in self.webhooks.values()
            if w.status == WebhookStatus.ACTIVE and event_str in w.events
        ]
        
        if not webhooks_to_notify:
            return
        
        payload = notification.to_dict()
        
        tasks = [
            self.webhook_client.send(webhook, event_str, payload)
            for webhook in webhooks_to_notify
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        notification.sent_webhook = any(
            isinstance(r, WebhookDelivery) and r.status == "success"
            for r in results
        )
        
        # Store deliveries
        for result in results:
            if isinstance(result, WebhookDelivery):
                self.deliveries.append(result)
    
    async def _send_to_websocket(self, notification: Notification):
        """Send notification to WebSocket connections."""
        # Placeholder for WebSocket implementation
        # In a real implementation, this would push to connected clients
        notification.sent_websocket = False
    
    async def _call_event_handlers(
        self,
        event_type: EventType,
        notification: Notification,
    ):
        """Call registered event handlers."""
        handlers = self._event_handlers.get(event_type, [])
        
        for handler in handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(notification)
                else:
                    handler(notification)
            except Exception as e:
                logger.warning(f"Event handler error: {e}")
    
    # ========================================
    # Event Handlers
    # ========================================
    
    def on_event(self, event_type: EventType):
        """
        Decorator to register an event handler.
        
        Example:
            @notifications.on_event(EventType.JOB_COMPLETED)
            async def handle_job_completed(notification):
                print(f"Job completed: {notification.data}")
        """
        def decorator(func: Callable):
            if event_type not in self._event_handlers:
                self._event_handlers[event_type] = []
            self._event_handlers[event_type].append(func)
            return func
        
        return decorator
    
    # ========================================
    # Notification History
    # ========================================
    
    def get_notifications(
        self,
        user_id: Optional[str] = None,
        event_type: Optional[EventType] = None,
        unread_only: bool = False,
        limit: int = 100,
    ) -> List[Notification]:
        """Get notifications with optional filtering."""
        with self._lock:
            notifications = list(self.notifications.values())
        
        if user_id:
            notifications = [n for n in notifications if n.user_id == user_id]
        
        if event_type:
            notifications = [n for n in notifications if n.event_type == event_type]
        
        if unread_only:
            notifications = [n for n in notifications if not n.read]
        
        # Sort by created_at descending
        notifications.sort(key=lambda n: n.created_at, reverse=True)
        
        return notifications[:limit]
    
    def mark_as_read(self, notification_id: str) -> bool:
        """Mark a notification as read."""
        with self._lock:
            notification = self.notifications.get(notification_id)
            
            if not notification:
                return False
            
            notification.read = True
            notification.read_at = datetime.utcnow().isoformat()
        
        self._save_data()
        
        return True
    
    def get_delivery_history(
        self,
        webhook_id: Optional[str] = None,
        limit: int = 100,
    ) -> List[WebhookDelivery]:
        """Get webhook delivery history."""
        deliveries = self.deliveries
        
        if webhook_id:
            deliveries = [d for d in deliveries if d.webhook_id == webhook_id]
        
        return deliveries[-limit:]
    
    # ========================================
    # Convenience Methods
    # ========================================
    
    async def notify_job_completed(
        self,
        job_id: str,
        job_type: str,
        result: Optional[Dict[str, Any]] = None,
        user_id: Optional[str] = None,
    ) -> Notification:
        """Send job completion notification."""
        return await self.send_notification(
            event_type=EventType.JOB_COMPLETED,
            title=f"{job_type.capitalize()} Job Completed",
            message=f"Job {job_id} has completed successfully.",
            data={"job_id": job_id, "job_type": job_type, "result": result},
            user_id=user_id,
        )
    
    async def notify_job_failed(
        self,
        job_id: str,
        job_type: str,
        error: str,
        user_id: Optional[str] = None,
    ) -> Notification:
        """Send job failure notification."""
        return await self.send_notification(
            event_type=EventType.JOB_FAILED,
            title=f"{job_type.capitalize()} Job Failed",
            message=f"Job {job_id} failed: {error}",
            data={"job_id": job_id, "job_type": job_type, "error": error},
            user_id=user_id,
        )
    
    async def notify_batch_completed(
        self,
        batch_id: str,
        total: int,
        completed: int,
        failed: int,
        user_id: Optional[str] = None,
    ) -> Notification:
        """Send batch completion notification."""
        event_type = EventType.BATCH_COMPLETED if failed == 0 else EventType.BATCH_PARTIAL
        
        return await self.send_notification(
            event_type=event_type,
            title="Batch Processing Complete",
            message=f"Batch {batch_id}: {completed}/{total} succeeded, {failed} failed.",
            data={
                "batch_id": batch_id,
                "total": total,
                "completed": completed,
                "failed": failed,
            },
            user_id=user_id,
        )
    
    # ========================================
    # Test Webhook
    # ========================================
    
    async def test_webhook(self, webhook_id: str) -> WebhookDelivery:
        """Send a test event to a webhook."""
        webhook = self.get_webhook(webhook_id)
        
        if not webhook:
            raise ValueError(f"Webhook not found: {webhook_id}")
        
        test_payload = {
            "test": True,
            "message": "This is a test webhook delivery from SurfScreen.",
            "timestamp": datetime.utcnow().isoformat(),
        }
        
        delivery = await self.webhook_client.send(
            webhook,
            "test.ping",
            test_payload,
        )
        
        self.deliveries.append(delivery)
        self._save_data()
        
        return delivery
    
    # ========================================
    # Persistence
    # ========================================
    
    def _save_data(self):
        """Persist data to disk."""
        try:
            data = {
                "webhooks": {
                    wid: {
                        **w.to_dict(),
                        "secret": w.secret,  # Include secret for persistence
                    }
                    for wid, w in self.webhooks.items()
                },
                "notifications": {
                    nid: n.to_dict()
                    for nid, n in list(self.notifications.items())[-1000:]  # Keep last 1000
                },
            }
            
            path = self.storage_dir / "notifications.json"
            with open(path, "w") as f:
                json.dump(data, f, indent=2)
                
        except Exception as e:
            logger.warning(f"Failed to save notifications data: {e}")
    
    def _load_data(self):
        """Load data from disk."""
        path = self.storage_dir / "notifications.json"
        
        if not path.exists():
            return
        
        try:
            with open(path) as f:
                data = json.load(f)
            
            for wid, wdata in data.get("webhooks", {}).items():
                self.webhooks[wid] = Webhook(
                    webhook_id=wid,
                    url=wdata["url"],
                    secret=wdata.get("secret", ""),
                    name=wdata["name"],
                    events=wdata["events"],
                    status=WebhookStatus(wdata.get("status", "active")),
                    created_at=wdata.get("created_at", ""),
                    last_triggered=wdata.get("last_triggered"),
                    success_count=wdata.get("success_count", 0),
                    failure_count=wdata.get("failure_count", 0),
                )
            
            logger.info(f"Loaded {len(self.webhooks)} webhooks")
            
        except Exception as e:
            logger.warning(f"Failed to load notifications data: {e}")


# Global notification service instance
_notification_service: Optional[NotificationService] = None


def get_notification_service() -> NotificationService:
    """Get or create global notification service instance."""
    global _notification_service
    
    if _notification_service is None:
        _notification_service = NotificationService()
    
    return _notification_service
