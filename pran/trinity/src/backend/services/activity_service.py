"""
Activity tracking service for unified activity stream.

This service provides centralized activity tracking with:
- Database persistence via DatabaseManager
- WebSocket broadcasting for real-time updates
- Subscriber pattern for extensibility
- Activity lifecycle management (start, complete, fail)
"""

import asyncio
import json
from typing import Dict, List, Optional, Callable, Any
from datetime import datetime
from models import ActivityType, ActivityState, ActivityCreate
from database import db


class ActivityService:
    """
    Centralized service for tracking agent activities.

    Handles:
    - Activity creation and completion
    - WebSocket broadcasting
    - Subscriber notifications
    - Current activity queries
    """

    def __init__(self):
        self.websocket_manager = None
        self.filtered_websocket_manager = None  # For /ws/events (Trinity Connect)
        self.subscribers: List[Callable] = []

    def set_websocket_manager(self, manager):
        """Set the WebSocket manager for broadcasting."""
        self.websocket_manager = manager

    def set_filtered_websocket_manager(self, manager):
        """Set the filtered WebSocket manager for /ws/events (Trinity Connect)."""
        self.filtered_websocket_manager = manager

    def subscribe(self, callback: Callable):
        """Register a callback to be notified of all activity events."""
        self.subscribers.append(callback)

    def unsubscribe(self, callback: Callable):
        """Unregister a callback."""
        if callback in self.subscribers:
            self.subscribers.remove(callback)

    async def track_activity(
        self,
        agent_name: str,
        activity_type: ActivityType,
        user_id: Optional[int] = None,
        triggered_by: str = "user",
        parent_activity_id: Optional[str] = None,
        related_chat_message_id: Optional[str] = None,
        related_execution_id: Optional[str] = None,
        details: Optional[Dict] = None
    ) -> str:
        """
        Track the start of a new activity.

        Args:
            agent_name: Name of the agent
            activity_type: Type of activity (from ActivityType enum)
            user_id: User who triggered the activity
            triggered_by: Source of trigger (user, schedule, agent, system)
            parent_activity_id: ID of parent activity (for tool_call → chat_start linkage)
            related_chat_message_id: Link to chat_messages table
            related_execution_id: Link to schedule_executions table
            details: Activity-specific details as dict

        Returns:
            activity_id: UUID of created activity
        """
        # Create activity in database
        activity = ActivityCreate(
            agent_name=agent_name,
            activity_type=activity_type,
            activity_state=ActivityState.STARTED,
            parent_activity_id=parent_activity_id,
            user_id=user_id,
            triggered_by=triggered_by,
            related_chat_message_id=related_chat_message_id,
            related_execution_id=related_execution_id,
            details=details
        )

        activity_id = db.create_activity(activity)

        # Broadcast via WebSocket
        await self._broadcast_activity_event(
            agent_name=agent_name,
            activity_id=activity_id,
            activity_type=activity_type.value,
            activity_state="started",
            action=self._get_action_description(activity_type, details),
            details=details
        )

        # Notify subscribers
        await self._notify_subscribers({
            "event": "activity_started",
            "activity_id": activity_id,
            "agent_name": agent_name,
            "activity_type": activity_type.value,
            "details": details
        })

        return activity_id

    async def complete_activity(
        self,
        activity_id: str,
        status: str = "completed",
        details: Optional[Dict] = None,
        error: Optional[str] = None
    ) -> bool:
        """
        Mark an activity as completed or failed.

        Args:
            activity_id: UUID of the activity
            status: "completed" or "failed"
            details: Additional details to merge with existing details
            error: Error message if failed

        Returns:
            bool: True if activity was found and updated
        """
        # Get activity to broadcast details
        activity = db.get_activity(activity_id)
        if not activity:
            return False

        # Update in database
        success = db.complete_activity(activity_id, status, details, error)

        if success:
            # Broadcast via WebSocket
            await self._broadcast_activity_event(
                agent_name=activity["agent_name"],
                activity_id=activity_id,
                activity_type=activity["activity_type"],
                activity_state=status,
                action=f"Completed: {activity['activity_type']}",
                details=details,
                error=error
            )

            # Notify subscribers
            await self._notify_subscribers({
                "event": "activity_completed",
                "activity_id": activity_id,
                "agent_name": activity["agent_name"],
                "activity_type": activity["activity_type"],
                "status": status,
                "error": error,
                "details": details
            })

        return success

    async def get_current_activities(self, agent_name: str) -> List[Dict]:
        """Get all in-progress activities for an agent."""
        return db.get_current_activities(agent_name)

    async def _broadcast_activity_event(
        self,
        agent_name: str,
        activity_id: str,
        activity_type: str,
        activity_state: str,
        action: str,
        details: Optional[Dict] = None,
        error: Optional[str] = None
    ):
        """Broadcast activity event via WebSocket."""
        if not self.websocket_manager:
            return

        event = {
            "type": "agent_activity",
            "agent_name": agent_name,
            "activity_id": activity_id,
            "activity_type": activity_type,
            "activity_state": activity_state,
            "action": action,
            "timestamp": datetime.utcnow().isoformat(),
            "details": details or {},
            "error": error
        }

        # Add context info if present in details
        if details:
            if "context_used" in details and "context_max" in details:
                event["details"]["context"] = {
                    "used": details["context_used"],
                    "max": details["context_max"],
                    "percentage": round((details["context_used"] / details["context_max"]) * 100, 2)
                }

        # Broadcast to main WebSocket manager (UI)
        # Note: ConnectionManager.broadcast expects a string, so serialize to JSON
        await self.websocket_manager.broadcast(json.dumps(event))

        # Also broadcast to filtered manager (Trinity Connect /ws/events)
        if self.filtered_websocket_manager:
            await self.filtered_websocket_manager.broadcast_filtered(event)

    async def _notify_subscribers(self, event: Dict):
        """Notify all subscribers of an activity event."""
        for callback in self.subscribers:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(event)
                else:
                    callback(event)
            except Exception as e:
                # Log error but don't fail the activity tracking
                print(f"Subscriber callback error: {e}")

    def _get_action_description(self, activity_type: ActivityType, details: Optional[Dict] = None) -> str:
        """Generate human-readable action description."""
        if activity_type == ActivityType.CHAT_START:
            if details and "message_preview" in details:
                preview = details["message_preview"][:50]
                return f"Processing: {preview}..."
            return "Processing chat"

        elif activity_type == ActivityType.TOOL_CALL:
            if details and "tool_name" in details:
                return f"Using tool: {details['tool_name']}"
            return "Executing tool"

        elif activity_type == ActivityType.SCHEDULE_START:
            if details and "schedule_name" in details:
                return f"Running: {details['schedule_name']}"
            return "Running scheduled task"

        elif activity_type == ActivityType.AGENT_COLLABORATION:
            if details and "target_agent" in details:
                return f"Collaborating with: {details['target_agent']}"
            return "Agent collaboration"

        elif activity_type == ActivityType.CHAT_END:
            return "Chat completed"

        elif activity_type == ActivityType.SCHEDULE_END:
            return "Schedule completed"

        else:
            return f"Activity: {activity_type.value}"


# Global activity service instance
activity_service = ActivityService()
