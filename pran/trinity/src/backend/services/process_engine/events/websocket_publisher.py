"""
WebSocket Event Publisher

Subscribes to domain events and broadcasts them to WebSocket clients.
Part of the Process-Driven Platform feature.
"""

import json
import logging
from dataclasses import asdict
from datetime import datetime
from typing import Any, Callable, Optional, Set

from ..domain.events import (
    DomainEvent,
    ProcessStarted,
    ProcessCompleted,
    ProcessFailed,
    StepStarted,
    StepCompleted,
    StepFailed,
    ApprovalRequested,
    CompensationStarted,
    CompensationCompleted,
    CompensationFailed,
)
from ..events.bus import EventBus

logger = logging.getLogger(__name__)


class WebSocketEventPublisher:
    """
    Publishes domain events to WebSocket clients.

    Clients can subscribe to specific execution IDs to receive
    only relevant updates.
    """

    # Event types that should be broadcast
    BROADCAST_EVENTS = {
        ProcessStarted,
        ProcessCompleted,
        ProcessFailed,
        StepStarted,
        StepCompleted,
        StepFailed,
        ApprovalRequested,
        CompensationStarted,
        CompensationCompleted,
        CompensationFailed,
    }

    def __init__(self, broadcast_fn: Optional[Callable[[str], Any]] = None):
        """
        Initialize the WebSocket publisher.

        Args:
            broadcast_fn: Async function to broadcast messages to all clients.
                         Typically ConnectionManager.broadcast from main.py.
        """
        self._broadcast_fn = broadcast_fn
        self._subscriptions: dict[str, Set[str]] = {}  # client_id -> set of execution_ids

    def set_broadcast_function(self, fn: Callable[[str], Any]) -> None:
        """Set the broadcast function (for late binding)."""
        self._broadcast_fn = fn

    def subscribe_to_execution(self, client_id: str, execution_id: str) -> None:
        """Subscribe a client to updates for a specific execution."""
        if client_id not in self._subscriptions:
            self._subscriptions[client_id] = set()
        self._subscriptions[client_id].add(execution_id)
        logger.debug(f"Client {client_id} subscribed to execution {execution_id}")

    def unsubscribe_from_execution(self, client_id: str, execution_id: str) -> None:
        """Unsubscribe a client from execution updates."""
        if client_id in self._subscriptions:
            self._subscriptions[client_id].discard(execution_id)
            if not self._subscriptions[client_id]:
                del self._subscriptions[client_id]
        logger.debug(f"Client {client_id} unsubscribed from execution {execution_id}")

    def unsubscribe_client(self, client_id: str) -> None:
        """Remove all subscriptions for a client."""
        if client_id in self._subscriptions:
            del self._subscriptions[client_id]
        logger.debug(f"Client {client_id} removed all subscriptions")

    def register_with_event_bus(self, event_bus: EventBus) -> None:
        """Register this publisher as a handler on the event bus."""
        for event_type in self.BROADCAST_EVENTS:
            event_bus.subscribe(event_type, self.handle_event)
        logger.info(f"WebSocket publisher registered for {len(self.BROADCAST_EVENTS)} event types")

    async def handle_event(self, event: DomainEvent) -> None:
        """Handle a domain event by broadcasting it to WebSocket clients."""
        if not self._broadcast_fn:
            logger.warning("No broadcast function set, skipping WebSocket publish")
            return

        # Convert event to WebSocket message
        message = self._event_to_message(event)
        if message:
            await self._broadcast_fn(json.dumps(message))
            logger.debug(f"Broadcast {event.__class__.__name__} for execution {getattr(event, 'execution_id', 'N/A')}")

    def _event_to_message(self, event: DomainEvent) -> Optional[dict[str, Any]]:
        """Convert a domain event to a WebSocket message."""
        event_type = self._get_event_type(event)
        if not event_type:
            return None

        # Build base message
        message = {
            "type": "process_event",
            "event_type": event_type,
            "timestamp": datetime.utcnow().isoformat(),
        }

        # Add event-specific data
        if isinstance(event, ProcessStarted):
            message.update({
                "execution_id": str(event.execution_id),
                "process_id": str(event.process_id),
                "process_name": event.process_name,
                "triggered_by": event.triggered_by,
            })
        elif isinstance(event, ProcessCompleted):
            message.update({
                "execution_id": str(event.execution_id),
                "process_id": str(event.process_id),
                "process_name": event.process_name,
                "duration_seconds": event.total_duration.seconds if event.total_duration else None,
            })
        elif isinstance(event, ProcessFailed):
            message.update({
                "execution_id": str(event.execution_id),
                "process_id": str(event.process_id),
                "process_name": event.process_name,
                "error": event.error_message,
                "failed_step_id": str(event.failed_step_id),
            })
        elif isinstance(event, StepStarted):
            message.update({
                "execution_id": str(event.execution_id),
                "step_id": str(event.step_id),
            })
        elif isinstance(event, StepCompleted):
            message.update({
                "execution_id": str(event.execution_id),
                "step_id": str(event.step_id),
                "duration_seconds": event.duration.seconds if event.duration else None,
            })
        elif isinstance(event, StepFailed):
            message.update({
                "execution_id": str(event.execution_id),
                "step_id": str(event.step_id),
                "error": event.error_message,
            })
        elif isinstance(event, ApprovalRequested):
            message.update({
                "execution_id": str(event.execution_id),
                "step_id": str(event.step_id),
                "approvers": event.approvers,
            })
        elif isinstance(event, CompensationStarted):
            message.update({
                "execution_id": str(event.execution_id),
                "process_id": str(event.process_id),
                "process_name": event.process_name,
                "compensation_count": event.compensation_count,
            })
        elif isinstance(event, CompensationCompleted):
            message.update({
                "execution_id": str(event.execution_id),
                "step_id": str(event.step_id),
                "step_name": event.step_name,
                "compensation_type": event.compensation_type,
            })
        elif isinstance(event, CompensationFailed):
            message.update({
                "execution_id": str(event.execution_id),
                "step_id": str(event.step_id),
                "step_name": event.step_name,
                "compensation_type": event.compensation_type,
                "error": event.error_message,
            })

        return message

    def _get_event_type(self, event: DomainEvent) -> Optional[str]:
        """Get the WebSocket event type string for a domain event."""
        event_types = {
            ProcessStarted: "process_started",
            ProcessCompleted: "process_completed",
            ProcessFailed: "process_failed",
            StepStarted: "step_started",
            StepCompleted: "step_completed",
            StepFailed: "step_failed",
            ApprovalRequested: "approval_requested",
            CompensationStarted: "compensation_started",
            CompensationCompleted: "compensation_completed",
            CompensationFailed: "compensation_failed",
        }
        return event_types.get(type(event))


# Global instance for injection
_websocket_publisher: Optional[WebSocketEventPublisher] = None


def get_websocket_publisher() -> WebSocketEventPublisher:
    """Get the global WebSocket publisher instance."""
    global _websocket_publisher
    if _websocket_publisher is None:
        _websocket_publisher = WebSocketEventPublisher()
    return _websocket_publisher


def set_websocket_publisher_broadcast(broadcast_fn: Callable[[str], Any]) -> None:
    """Set the broadcast function on the global publisher."""
    publisher = get_websocket_publisher()
    publisher.set_broadcast_function(broadcast_fn)
