"""
Event Logger Service

Subscribes to all domain events and persists them to the EventRepository.
This provides a complete audit log of system activities.

Reference: BACKLOG_MVP.md - E15-04
"""

import logging
from typing import Optional

from ..domain.events import DomainEvent
from ..repositories.interfaces import EventRepository
from ..events.bus import EventBus

logger = logging.getLogger(__name__)


class EventLogger:
    """
    Service that listens to all domain events and saves them to storage.
    """
    
    def __init__(self, repository: EventRepository, event_bus: EventBus):
        """
        Initialize the event logger.
        
        Args:
            repository: Repository to save events to
            event_bus: Event bus to subscribe to
        """
        self.repository = repository
        self.event_bus = event_bus
        self._subscribed = False
        
    def start(self) -> None:
        """Start listening to events."""
        if not self._subscribed:
            self.event_bus.subscribe_all(self.handle_event)
            self._subscribed = True
            logger.info("EventLogger subscribed to all events")
            
    def stop(self) -> None:
        """Stop listening to events."""
        if self._subscribed:
            self.event_bus.unsubscribe_all(self.handle_event)
            self._subscribed = False
            logger.info("EventLogger unsubscribed from all events")
            
    async def handle_event(self, event: DomainEvent) -> None:
        """
        Handle a domain event by saving it to the repository.
        
        This handler is async because the EventBus calls handlers asynchronously,
        but the repository save operation is currently synchronous (SQLite).
        """
        try:
            # We wrap the synchronous save in a way that works with the async handler
            # In a real async DB, we would await self.repository.save(event)
            self.repository.save(event)
        except Exception as e:
            logger.error(f"Failed to log event {type(event).__name__}: {e}", exc_info=True)
