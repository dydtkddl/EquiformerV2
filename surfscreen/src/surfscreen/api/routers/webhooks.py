"""
Webhooks API Router

REST API endpoints for webhook management and notifications.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field, HttpUrl
from typing import Optional, List, Dict, Any
import logging

from ...notifications import NotificationService, get_notification_service
from ...notifications.webhook_client import WebhookStatus

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


# ============================================
# Pydantic Models
# ============================================

class WebhookCreate(BaseModel):
    """Request model for creating a webhook."""
    
    url: str = Field(..., description="Webhook URL")
    name: str = Field(..., min_length=1, max_length=256)
    events: List[str] = Field(
        ...,
        min_items=1,
        description="Event types to subscribe (e.g., 'job.completed', 'batch.failed')"
    )
    
    class Config:
        schema_extra = {
            "example": {
                "url": "https://example.com/webhooks/surfscreen",
                "name": "My Webhook",
                "events": ["job.completed", "job.failed", "batch.completed"],
            }
        }


class WebhookUpdate(BaseModel):
    """Request model for updating a webhook."""
    
    name: Optional[str] = Field(None, max_length=256)
    url: Optional[str] = None
    events: Optional[List[str]] = None
    status: Optional[WebhookStatus] = None


class WebhookResponse(BaseModel):
    """Response model for webhook."""
    
    webhook_id: str
    url: str
    name: str
    events: List[str]
    status: WebhookStatus
    created_at: str
    last_triggered: Optional[str]
    success_count: int
    failure_count: int


class WebhookCreateResponse(BaseModel):
    """Response model for webhook creation (includes secret)."""
    
    webhook_id: str
    url: str
    name: str
    events: List[str]
    secret: str  # Only returned on creation
    status: WebhookStatus
    created_at: str


class WebhookListResponse(BaseModel):
    """Response model for webhook list."""
    
    webhooks: List[WebhookResponse]
    total: int


class DeliveryResponse(BaseModel):
    """Response model for webhook delivery."""
    
    delivery_id: str
    webhook_id: str
    event_type: str
    status: str
    created_at: str
    delivered_at: Optional[str]
    response_status: Optional[int]
    error: Optional[str]
    attempts: int


class TestWebhookResponse(BaseModel):
    """Response model for webhook test."""
    
    success: bool
    delivery_id: str
    status: str
    response_status: Optional[int]
    error: Optional[str]


# ============================================
# Dependencies
# ============================================

def get_notifications() -> NotificationService:
    """Dependency to get notification service."""
    return get_notification_service()


# ============================================
# Endpoints
# ============================================

@router.post("", response_model=WebhookCreateResponse)
async def create_webhook(
    request: WebhookCreate,
    notifications: NotificationService = Depends(get_notifications),
):
    """
    Register a new webhook.
    
    Returns the webhook configuration including the secret.
    Store the secret securely - it won't be shown again.
    """
    webhook, secret = notifications.register_webhook(
        url=request.url,
        name=request.name,
        events=request.events,
    )
    
    return WebhookCreateResponse(
        webhook_id=webhook.webhook_id,
        url=webhook.url,
        name=webhook.name,
        events=webhook.events,
        secret=secret,  # Only returned once
        status=webhook.status,
        created_at=webhook.created_at,
    )


@router.get("", response_model=WebhookListResponse)
async def list_webhooks(
    status: Optional[WebhookStatus] = Query(None),
    event: Optional[str] = Query(None, description="Filter by event type"),
    notifications: NotificationService = Depends(get_notifications),
):
    """
    List all registered webhooks.
    """
    webhooks = notifications.list_webhooks(status=status, event=event)
    
    return WebhookListResponse(
        webhooks=[
            WebhookResponse(
                webhook_id=w.webhook_id,
                url=w.url,
                name=w.name,
                events=w.events,
                status=w.status,
                created_at=w.created_at,
                last_triggered=w.last_triggered,
                success_count=w.success_count,
                failure_count=w.failure_count,
            )
            for w in webhooks
        ],
        total=len(webhooks),
    )


@router.get("/{webhook_id}", response_model=WebhookResponse)
async def get_webhook(
    webhook_id: str,
    notifications: NotificationService = Depends(get_notifications),
):
    """
    Get webhook by ID.
    """
    webhook = notifications.get_webhook(webhook_id)
    
    if not webhook:
        raise HTTPException(status_code=404, detail="Webhook not found")
    
    return WebhookResponse(
        webhook_id=webhook.webhook_id,
        url=webhook.url,
        name=webhook.name,
        events=webhook.events,
        status=webhook.status,
        created_at=webhook.created_at,
        last_triggered=webhook.last_triggered,
        success_count=webhook.success_count,
        failure_count=webhook.failure_count,
    )


@router.put("/{webhook_id}", response_model=WebhookResponse)
async def update_webhook(
    webhook_id: str,
    request: WebhookUpdate,
    notifications: NotificationService = Depends(get_notifications),
):
    """
    Update webhook configuration.
    """
    webhook = notifications.update_webhook(
        webhook_id=webhook_id,
        name=request.name,
        url=request.url,
        events=request.events,
        status=request.status,
    )
    
    if not webhook:
        raise HTTPException(status_code=404, detail="Webhook not found")
    
    return WebhookResponse(
        webhook_id=webhook.webhook_id,
        url=webhook.url,
        name=webhook.name,
        events=webhook.events,
        status=webhook.status,
        created_at=webhook.created_at,
        last_triggered=webhook.last_triggered,
        success_count=webhook.success_count,
        failure_count=webhook.failure_count,
    )


@router.delete("/{webhook_id}")
async def delete_webhook(
    webhook_id: str,
    notifications: NotificationService = Depends(get_notifications),
):
    """
    Delete a webhook.
    """
    success = notifications.delete_webhook(webhook_id)
    
    if not success:
        raise HTTPException(status_code=404, detail="Webhook not found")
    
    return {"deleted": True, "webhook_id": webhook_id}


@router.post("/{webhook_id}/test", response_model=TestWebhookResponse)
async def test_webhook(
    webhook_id: str,
    notifications: NotificationService = Depends(get_notifications),
):
    """
    Send a test event to a webhook.
    
    Useful for verifying webhook configuration.
    """
    try:
        delivery = await notifications.test_webhook(webhook_id)
        
        return TestWebhookResponse(
            success=delivery.status == "success",
            delivery_id=delivery.delivery_id,
            status=delivery.status,
            response_status=delivery.response_status,
            error=delivery.error,
        )
        
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/{webhook_id}/rotate-secret")
async def rotate_webhook_secret(
    webhook_id: str,
    notifications: NotificationService = Depends(get_notifications),
):
    """
    Regenerate webhook secret.
    
    Returns the new secret. The old secret becomes invalid immediately.
    """
    new_secret = notifications.regenerate_secret(webhook_id)
    
    if not new_secret:
        raise HTTPException(status_code=404, detail="Webhook not found")
    
    return {
        "webhook_id": webhook_id,
        "secret": new_secret,
        "message": "Secret rotated. Update your endpoint to use the new secret.",
    }


@router.get("/{webhook_id}/deliveries", response_model=List[DeliveryResponse])
async def get_webhook_deliveries(
    webhook_id: str,
    limit: int = Query(50, ge=1, le=500),
    notifications: NotificationService = Depends(get_notifications),
):
    """
    Get delivery history for a webhook.
    """
    webhook = notifications.get_webhook(webhook_id)
    
    if not webhook:
        raise HTTPException(status_code=404, detail="Webhook not found")
    
    deliveries = notifications.get_delivery_history(webhook_id=webhook_id, limit=limit)
    
    return [
        DeliveryResponse(
            delivery_id=d.delivery_id,
            webhook_id=d.webhook_id,
            event_type=d.event_type,
            status=d.status,
            created_at=d.created_at,
            delivered_at=d.delivered_at,
            response_status=d.response_status,
            error=d.error,
            attempts=d.attempts,
        )
        for d in deliveries
    ]


# ============================================
# Event Types Endpoint
# ============================================

@router.get("/events/types")
async def list_event_types():
    """
    List all available event types.
    """
    from ...notifications.notification_service import EventType
    
    return {
        "event_types": [
            {
                "type": e.value,
                "description": _get_event_description(e),
            }
            for e in EventType
        ]
    }


def _get_event_description(event_type) -> str:
    """Get human-readable description for event type."""
    descriptions = {
        "job.submitted": "A job was submitted",
        "job.started": "A job started processing",
        "job.completed": "A job completed successfully",
        "job.failed": "A job failed",
        "batch.submitted": "A batch job was submitted",
        "batch.completed": "A batch job completed successfully",
        "batch.partial": "A batch job completed with some failures",
        "batch.failed": "A batch job failed completely",
        "schedule.triggered": "A scheduled job was triggered",
        "schedule.completed": "A scheduled job completed",
        "schedule.failed": "A scheduled job failed",
        "quota.warning": "Usage approaching quota limit",
        "quota.exceeded": "Quota limit exceeded",
    }
    return descriptions.get(event_type.value, "")
