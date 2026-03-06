"""
Webhook Event Publisher

Subscribes to domain events and sends them to configured webhooks.
Allows external systems to react to process execution events.

Reference: BACKLOG_MVP.md - E15-03
"""

import asyncio
import logging
from datetime import datetime
from typing import Any, Callable, Optional

import httpx

from ..domain.events import (
    DomainEvent,
    ProcessStarted,
    ProcessCompleted,
    ProcessFailed,
    ApprovalRequested,
)
from ..events.bus import EventBus

logger = logging.getLogger(__name__)


class WebhookEventPublisher:
    """
    Publishes domain events to configured webhooks.

    Webhooks can be configured globally or per-process.
    Events are sent asynchronously to avoid blocking execution.
    """

    # Event types to publish
    WEBHOOK_EVENTS = {
        ProcessCompleted,
        ProcessFailed,
        ApprovalRequested,
    }

    def __init__(self):
        """Initialize the webhook publisher."""
        self._global_webhooks: list[str] = []
        self._process_webhooks: dict[str, list[str]] = {}  # process_id -> webhook URLs
        self._get_process_webhooks_fn: Optional[Callable[[str], list[str]]] = None

    def add_global_webhook(self, url: str) -> None:
        """Add a global webhook URL that receives all events."""
        if url and url not in self._global_webhooks:
            self._global_webhooks.append(url)
            logger.info(f"Added global webhook: {url}")

    def set_process_webhooks_resolver(self, fn: Callable[[str], list[str]]) -> None:
        """
        Set a function to resolve webhook URLs for a process.

        The function receives a process_id and returns a list of webhook URLs.
        """
        self._get_process_webhooks_fn = fn

    def register_with_event_bus(self, event_bus: EventBus) -> None:
        """Register this publisher as a handler on the event bus."""
        for event_type in self.WEBHOOK_EVENTS:
            event_bus.subscribe(event_type, self.handle_event)
        logger.info(f"Webhook publisher registered for {len(self.WEBHOOK_EVENTS)} event types")

    async def handle_event(self, event: DomainEvent) -> None:
        """Handle a domain event by sending it to configured webhooks."""
        process_id = str(getattr(event, 'process_id', ''))

        # Collect webhook URLs
        webhooks = list(self._global_webhooks)

        # Add process-specific webhooks
        if self._get_process_webhooks_fn and process_id:
            try:
                process_webhooks = self._get_process_webhooks_fn(process_id)
                webhooks.extend(process_webhooks)
            except Exception as e:
                logger.error(f"Failed to get process webhooks: {e}")

        if not webhooks:
            return

        # Build payload
        payload = self._event_to_payload(event)
        if not payload:
            return

        # Send to all webhooks asynchronously
        logger.info(f"Sending {event.__class__.__name__} to {len(webhooks)} webhooks")
        await asyncio.gather(
            *[self._send_webhook(url, payload) for url in webhooks],
            return_exceptions=True,
        )

    async def _send_webhook(self, url: str, payload: dict) -> None:
        """Send a webhook request."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    url,
                    json=payload,
                    timeout=10.0,
                    headers={"Content-Type": "application/json"},
                )
                if response.status_code >= 400:
                    logger.warning(f"Webhook {url} returned {response.status_code}")
                else:
                    logger.debug(f"Webhook {url} delivered successfully")
        except httpx.TimeoutException:
            logger.warning(f"Webhook {url} timed out")
        except Exception as e:
            logger.error(f"Webhook {url} failed: {e}")

    def _event_to_payload(self, event: DomainEvent) -> Optional[dict[str, Any]]:
        """Convert a domain event to a webhook payload."""
        event_type = self._get_event_type(event)
        if not event_type:
            return None

        # Build base payload
        payload = {
            "event_type": event_type,
            "timestamp": datetime.utcnow().isoformat() + "Z",
        }

        # Add event-specific data
        if isinstance(event, ProcessCompleted):
            payload.update({
                "execution_id": str(event.execution_id),
                "process_id": str(event.process_id),
                "process_name": event.process_name,
                "status": "completed",
                "duration_seconds": event.total_duration.seconds if event.total_duration else None,
                "total_cost": str(event.total_cost) if event.total_cost else None,
            })
        elif isinstance(event, ProcessFailed):
            payload.update({
                "execution_id": str(event.execution_id),
                "process_id": str(event.process_id),
                "process_name": event.process_name,
                "status": "failed",
                "error": event.error_message,
                "failed_step_id": str(event.failed_step_id),
            })
        elif isinstance(event, ApprovalRequested):
            payload.update({
                "execution_id": str(event.execution_id),
                "step_id": str(event.step_id),
                "step_name": event.step_name,
                "title": event.title,
                "description": event.description,
                "approvers": event.approvers,
                "requires_action": True,
            })

        return payload

    def _get_event_type(self, event: DomainEvent) -> Optional[str]:
        """Get the event type string for a domain event."""
        event_types = {
            ProcessCompleted: "process_completed",
            ProcessFailed: "process_failed",
            ApprovalRequested: "approval_requested",
        }
        return event_types.get(type(event))


# Global instance
_webhook_publisher: Optional[WebhookEventPublisher] = None


def get_webhook_publisher() -> WebhookEventPublisher:
    """Get the global webhook publisher instance."""
    global _webhook_publisher
    if _webhook_publisher is None:
        _webhook_publisher = WebhookEventPublisher()
    return _webhook_publisher
