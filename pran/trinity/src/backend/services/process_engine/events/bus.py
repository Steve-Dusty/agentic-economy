"""
Event Bus Implementation

Provides publish/subscribe infrastructure for domain events.
MVP uses in-memory implementation; can be extended for Redis/Kafka later.

Reference: IT3 Section 5 (Domain Events)
"""

from __future__ import annotations

import asyncio
import logging
from abc import ABC, abstractmethod
from collections import defaultdict
from typing import Callable, Coroutine, Type, TypeVar, Any

from ..domain.events import DomainEvent


logger = logging.getLogger(__name__)


# Type definitions
T = TypeVar("T", bound=DomainEvent)
EventHandler = Callable[[DomainEvent], Coroutine[Any, Any, None]]
SyncEventHandler = Callable[[DomainEvent], None]


class EventBus(ABC):
    """
    Abstract event bus interface.
    
    Supports:
    - Publishing events (async, non-blocking)
    - Subscribing handlers to specific event types
    - Subscribing handlers to all events
    """

    @abstractmethod
    async def publish(self, event: DomainEvent) -> None:
        """
        Publish an event to all subscribed handlers.
        
        Handlers are invoked asynchronously (non-blocking).
        Errors in handlers are logged but don't stop other handlers.
        """
        ...

    @abstractmethod
    def subscribe(
        self,
        event_type: Type[T],
        handler: EventHandler,
    ) -> None:
        """
        Subscribe a handler to a specific event type.
        
        The handler will be called for all events of this type.
        """
        ...

    @abstractmethod
    def subscribe_all(self, handler: EventHandler) -> None:
        """
        Subscribe a handler to all events.
        
        The handler will be called for every event published.
        """
        ...

    @abstractmethod
    def unsubscribe(
        self,
        event_type: Type[T],
        handler: EventHandler,
    ) -> None:
        """
        Unsubscribe a handler from a specific event type.
        """
        ...

    @abstractmethod
    def unsubscribe_all(self, handler: EventHandler) -> None:
        """
        Unsubscribe a handler from all events.
        """
        ...

    @abstractmethod
    def clear(self) -> None:
        """
        Clear all subscriptions.
        """
        ...


class InMemoryEventBus(EventBus):
    """
    In-memory event bus implementation.
    
    Suitable for:
    - MVP/development
    - Testing
    - Single-instance deployments
    
    Events are dispatched asynchronously using asyncio.create_task().
    Handlers run concurrently for a single event.
    
    Thread Safety: This implementation is NOT thread-safe.
    Use in a single-threaded async context or add locking if needed.
    """

    def __init__(self):
        # Handlers by event type
        self._handlers: dict[Type[DomainEvent], list[EventHandler]] = defaultdict(list)
        # Handlers for all events
        self._global_handlers: list[EventHandler] = []
        # Track in-flight tasks for testing/shutdown
        self._pending_tasks: set[asyncio.Task] = set()

    async def publish(self, event: DomainEvent) -> None:
        """
        Publish event to all relevant handlers.
        
        Handlers are invoked asynchronously via asyncio.create_task().
        Errors in handlers are logged but don't propagate.
        """
        event_type = type(event)
        
        # Collect all handlers for this event
        handlers: list[EventHandler] = []
        
        # Type-specific handlers
        handlers.extend(self._handlers.get(event_type, []))
        
        # Global handlers
        handlers.extend(self._global_handlers)
        
        if not handlers:
            logger.debug(f"No handlers for event {event_type.__name__}")
            return
        
        logger.debug(
            f"Publishing {event_type.__name__} to {len(handlers)} handler(s)"
        )
        
        # Dispatch to all handlers concurrently
        for handler in handlers:
            task = asyncio.create_task(self._safe_dispatch(handler, event))
            self._pending_tasks.add(task)
            task.add_done_callback(self._pending_tasks.discard)

    async def _safe_dispatch(
        self,
        handler: EventHandler,
        event: DomainEvent,
    ) -> None:
        """
        Dispatch event to handler with error handling.
        
        Errors are logged but don't propagate.
        """
        try:
            await handler(event)
        except Exception as e:
            logger.error(
                f"Error in event handler {handler.__name__} "
                f"for {type(event).__name__}: {e}",
                exc_info=True,
            )

    def subscribe(
        self,
        event_type: Type[T],
        handler: EventHandler,
    ) -> None:
        """Subscribe handler to specific event type."""
        if handler not in self._handlers[event_type]:
            self._handlers[event_type].append(handler)
            logger.debug(
                f"Subscribed {handler.__name__} to {event_type.__name__}"
            )

    def subscribe_all(self, handler: EventHandler) -> None:
        """Subscribe handler to all events."""
        if handler not in self._global_handlers:
            self._global_handlers.append(handler)
            logger.debug(f"Subscribed {handler.__name__} to all events")

    def unsubscribe(
        self,
        event_type: Type[T],
        handler: EventHandler,
    ) -> None:
        """Unsubscribe handler from specific event type."""
        if handler in self._handlers[event_type]:
            self._handlers[event_type].remove(handler)
            logger.debug(
                f"Unsubscribed {handler.__name__} from {event_type.__name__}"
            )

    def unsubscribe_all(self, handler: EventHandler) -> None:
        """Unsubscribe handler from all events."""
        if handler in self._global_handlers:
            self._global_handlers.remove(handler)
            logger.debug(f"Unsubscribed {handler.__name__} from all events")

    def clear(self) -> None:
        """Clear all subscriptions."""
        self._handlers.clear()
        self._global_handlers.clear()
        logger.debug("Cleared all event subscriptions")

    async def wait_for_pending(self, timeout: float = 5.0) -> None:
        """
        Wait for pending event handlers to complete.
        
        Useful for testing and graceful shutdown.
        """
        if self._pending_tasks:
            try:
                await asyncio.wait_for(
                    asyncio.gather(*self._pending_tasks, return_exceptions=True),
                    timeout=timeout,
                )
            except asyncio.TimeoutError:
                logger.warning(
                    f"Timeout waiting for {len(self._pending_tasks)} pending handlers"
                )

    @property
    def handler_count(self) -> int:
        """Total number of registered handlers."""
        type_handlers = sum(len(h) for h in self._handlers.values())
        return type_handlers + len(self._global_handlers)

    def get_handlers_for(self, event_type: Type[DomainEvent]) -> list[EventHandler]:
        """Get handlers for a specific event type (for testing)."""
        handlers = list(self._handlers.get(event_type, []))
        handlers.extend(self._global_handlers)
        return handlers
