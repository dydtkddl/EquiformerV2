"""
Webhook Client

HTTP client for sending webhook notifications with retries and signature verification.
"""

import asyncio
import hashlib
import hmac
import json
import logging
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
from enum import Enum

logger = logging.getLogger(__name__)


class WebhookStatus(str, Enum):
    """Webhook status."""
    
    ACTIVE = "active"
    INACTIVE = "inactive"
    FAILED = "failed"  # Too many failures


@dataclass
class Webhook:
    """Webhook configuration."""
    
    webhook_id: str
    url: str
    secret: str  # For signature verification
    name: str
    events: List[str]  # Event types to receive
    status: WebhookStatus = WebhookStatus.ACTIVE
    
    # Stats
    created_at: str = ""
    last_triggered: Optional[str] = None
    success_count: int = 0
    failure_count: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "webhook_id": self.webhook_id,
            "url": self.url,
            "name": self.name,
            "events": self.events,
            "status": self.status.value,
            "created_at": self.created_at,
            "last_triggered": self.last_triggered,
            "success_count": self.success_count,
            "failure_count": self.failure_count,
        }


@dataclass
class WebhookDelivery:
    """Webhook delivery record."""
    
    delivery_id: str
    webhook_id: str
    event_type: str
    payload: Dict[str, Any]
    status: str  # "pending", "success", "failed"
    
    # Timing
    created_at: str = ""
    delivered_at: Optional[str] = None
    
    # Response
    response_status: Optional[int] = None
    response_body: Optional[str] = None
    error: Optional[str] = None
    
    # Retries
    attempts: int = 0
    max_attempts: int = 3


class WebhookClient:
    """
    HTTP client for webhook deliveries.
    
    Features:
    - HMAC signature for payload verification
    - Exponential backoff retries
    - Delivery tracking
    """
    
    def __init__(
        self,
        timeout: float = 30.0,
        max_retries: int = 3,
        retry_delay: float = 1.0,
    ):
        """
        Initialize webhook client.
        
        Args:
            timeout: Request timeout in seconds
            max_retries: Maximum retry attempts
            retry_delay: Initial delay between retries (exponential backoff)
        """
        self.timeout = timeout
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self._session = None
    
    def generate_signature(self, payload: str, secret: str) -> str:
        """
        Generate HMAC-SHA256 signature for payload.
        
        Args:
            payload: JSON payload string
            secret: Webhook secret
            
        Returns:
            Hex-encoded signature
        """
        return hmac.new(
            secret.encode(),
            payload.encode(),
            hashlib.sha256
        ).hexdigest()
    
    def verify_signature(
        self,
        payload: str,
        signature: str,
        secret: str,
    ) -> bool:
        """
        Verify webhook signature.
        
        Args:
            payload: JSON payload string
            signature: Received signature
            secret: Webhook secret
            
        Returns:
            True if signature matches
        """
        expected = self.generate_signature(payload, secret)
        return hmac.compare_digest(signature, expected)
    
    async def send(
        self,
        webhook: Webhook,
        event_type: str,
        payload: Dict[str, Any],
    ) -> WebhookDelivery:
        """
        Send webhook notification.
        
        Args:
            webhook: Webhook configuration
            event_type: Event type
            payload: Event payload
            
        Returns:
            WebhookDelivery with result
        """
        delivery_id = str(uuid.uuid4())[:8]
        now = datetime.utcnow().isoformat()
        
        delivery = WebhookDelivery(
            delivery_id=delivery_id,
            webhook_id=webhook.webhook_id,
            event_type=event_type,
            payload=payload,
            status="pending",
            created_at=now,
            max_attempts=self.max_retries,
        )
        
        # Prepare payload with metadata
        full_payload = {
            "event": event_type,
            "timestamp": now,
            "delivery_id": delivery_id,
            "data": payload,
        }
        
        payload_json = json.dumps(full_payload, default=str)
        signature = self.generate_signature(payload_json, webhook.secret)
        
        headers = {
            "Content-Type": "application/json",
            "X-SurfScreen-Signature": f"sha256={signature}",
            "X-SurfScreen-Event": event_type,
            "X-SurfScreen-Delivery": delivery_id,
        }
        
        # Try to send with retries
        last_error = None
        
        for attempt in range(self.max_retries):
            delivery.attempts = attempt + 1
            
            try:
                response_status, response_body = await self._make_request(
                    webhook.url,
                    payload_json,
                    headers,
                )
                
                delivery.response_status = response_status
                delivery.response_body = response_body[:1000] if response_body else None
                
                if 200 <= response_status < 300:
                    delivery.status = "success"
                    delivery.delivered_at = datetime.utcnow().isoformat()
                    webhook.success_count += 1
                    webhook.last_triggered = now
                    
                    logger.debug(
                        f"Webhook delivered: {webhook.webhook_id} -> {event_type}"
                    )
                    return delivery
                
                else:
                    last_error = f"HTTP {response_status}"
                    
            except Exception as e:
                last_error = str(e)
                logger.warning(
                    f"Webhook delivery failed (attempt {attempt + 1}): {e}"
                )
            
            # Wait before retry (exponential backoff)
            if attempt < self.max_retries - 1:
                delay = self.retry_delay * (2 ** attempt)
                await asyncio.sleep(delay)
        
        # All retries failed
        delivery.status = "failed"
        delivery.error = last_error
        webhook.failure_count += 1
        
        # Deactivate webhook after too many failures
        if webhook.failure_count >= 10:
            webhook.status = WebhookStatus.FAILED
            logger.warning(f"Webhook deactivated due to failures: {webhook.webhook_id}")
        
        return delivery
    
    async def _make_request(
        self,
        url: str,
        payload: str,
        headers: Dict[str, str],
    ) -> Tuple[int, Optional[str]]:
        """
        Make HTTP POST request.
        
        Returns:
            Tuple of (status_code, response_body)
        """
        try:
            import aiohttp
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    url,
                    data=payload,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=self.timeout),
                ) as response:
                    body = await response.text()
                    return response.status, body
                    
        except ImportError:
            # Fallback to sync requests
            import urllib.request
            import urllib.error
            
            req = urllib.request.Request(
                url,
                data=payload.encode(),
                headers=headers,
                method="POST",
            )
            
            try:
                with urllib.request.urlopen(req, timeout=self.timeout) as response:
                    return response.status, response.read().decode()
            except urllib.error.HTTPError as e:
                return e.code, e.read().decode() if e.fp else None
    
    def send_sync(
        self,
        webhook: Webhook,
        event_type: str,
        payload: Dict[str, Any],
    ) -> WebhookDelivery:
        """
        Synchronous version of send.
        """
        return asyncio.run(self.send(webhook, event_type, payload))
