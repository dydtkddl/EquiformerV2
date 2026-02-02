"""
SurfScreen Notifications Module

Notification system with webhooks, email, and WebSocket support.
"""

from .notification_service import NotificationService, get_notification_service
from .webhook_client import WebhookClient

__all__ = [
    "NotificationService",
    "get_notification_service",
    "WebhookClient",
]
