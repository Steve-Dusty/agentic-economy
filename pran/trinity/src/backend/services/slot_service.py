"""
Slot Service for Trinity platform.

Implements per-agent parallel execution capacity tracking (CAPACITY-001).
Uses Redis ZSET for slot tracking with automatic TTL-based cleanup.

Key Pattern:
- agent:slots:{name} (ZSET) - Active execution IDs with start timestamps
- agent:slot:{name}:{execution_id} (HASH) - Slot metadata (auto-expires)

Slot Rules:
- Each agent has configurable max_parallel_tasks (1-10, default 3)
- Parallel /task endpoint respects capacity limits
- Return 429 when at capacity
- Slots auto-expire after 30 minutes (safety net)
"""

import json
import logging
from datetime import datetime
from typing import Optional, Dict, List, Any
import redis
import time

from dataclasses import dataclass

logger = logging.getLogger(__name__)

# Configuration
SLOT_TTL_SECONDS = 1800  # 30 minutes - safety net for orphaned slots
SLOT_METADATA_TTL = 1800  # 30 minutes


@dataclass
class SlotInfo:
    """Information about a single execution slot."""
    execution_id: str
    slot_number: int
    started_at: str
    message_preview: str
    duration_seconds: int


@dataclass
class SlotState:
    """Current slot state for an agent."""
    agent_name: str
    max_parallel_tasks: int
    active_slots: int
    available_slots: int
    slots: List[SlotInfo]


class SlotService:
    """
    Redis-backed slot tracking for parallel execution capacity.

    Uses ZSET with timestamps as scores for automatic cleanup:
    - ZADD agent:slots:{name} {timestamp} {execution_id}
    - ZCARD for counting active slots
    - ZREMRANGEBYSCORE for cleanup
    """

    def __init__(self, redis_url: str = "redis://redis:6379"):
        self.redis = redis.from_url(redis_url, decode_responses=True)
        self.slots_prefix = "agent:slots:"
        self.metadata_prefix = "agent:slot:"

    def _slots_key(self, agent_name: str) -> str:
        """Redis key for agent's slot set."""
        return f"{self.slots_prefix}{agent_name}"

    def _metadata_key(self, agent_name: str, execution_id: str) -> str:
        """Redis key for slot metadata."""
        return f"{self.metadata_prefix}{agent_name}:{execution_id}"

    async def acquire_slot(
        self,
        agent_name: str,
        execution_id: str,
        max_parallel_tasks: int,
        message_preview: str = ""
    ) -> bool:
        """
        Try to acquire a slot for an execution.

        Args:
            agent_name: Name of the agent
            execution_id: Unique execution ID
            max_parallel_tasks: Maximum allowed parallel tasks for this agent
            message_preview: First 100 chars of message for display

        Returns:
            True if slot acquired, False if at capacity
        """
        slots_key = self._slots_key(agent_name)
        now = time.time()

        # Clean up expired slots first
        await self._cleanup_stale_slots_for_agent(agent_name)

        # Check current count
        current_count = self.redis.zcard(slots_key)
        if current_count >= max_parallel_tasks:
            logger.info(
                f"[Slots] Agent '{agent_name}' at capacity ({current_count}/{max_parallel_tasks}), "
                f"rejecting execution {execution_id}"
            )
            return False

        # Add slot (ZADD with timestamp score)
        self.redis.zadd(slots_key, {execution_id: now})

        # Store metadata
        metadata_key = self._metadata_key(agent_name, execution_id)
        slot_number = current_count + 1  # Assign next available slot number
        self.redis.hset(metadata_key, mapping={
            "started_at": datetime.utcnow().isoformat(),
            "message_preview": message_preview[:100] if message_preview else "",
            "slot_number": str(slot_number)
        })
        self.redis.expire(metadata_key, SLOT_METADATA_TTL)

        logger.info(
            f"[Slots] Agent '{agent_name}' acquired slot {slot_number}/{max_parallel_tasks} "
            f"for execution {execution_id}"
        )
        return True

    async def release_slot(self, agent_name: str, execution_id: str) -> None:
        """
        Release a slot when execution completes.

        Args:
            agent_name: Name of the agent
            execution_id: Execution ID to release
        """
        slots_key = self._slots_key(agent_name)
        metadata_key = self._metadata_key(agent_name, execution_id)

        # Remove from ZSET
        removed = self.redis.zrem(slots_key, execution_id)

        # Delete metadata
        self.redis.delete(metadata_key)

        if removed:
            remaining = self.redis.zcard(slots_key)
            logger.info(
                f"[Slots] Agent '{agent_name}' released slot for execution {execution_id}, "
                f"{remaining} slots still active"
            )

    async def get_slot_state(self, agent_name: str, max_parallel_tasks: int) -> SlotState:
        """
        Get current slot usage for an agent.

        Args:
            agent_name: Name of the agent
            max_parallel_tasks: Maximum allowed parallel tasks

        Returns:
            SlotState with current usage information
        """
        slots_key = self._slots_key(agent_name)
        now = time.time()

        # Get all active execution IDs with scores (timestamps)
        slot_entries = self.redis.zrangebyscore(
            slots_key, "-inf", "+inf", withscores=True
        )

        slots = []
        for execution_id, start_timestamp in slot_entries:
            metadata_key = self._metadata_key(agent_name, execution_id)
            metadata = self.redis.hgetall(metadata_key)

            duration_seconds = int(now - start_timestamp)
            slot_number = int(metadata.get("slot_number", 0))

            slots.append(SlotInfo(
                execution_id=execution_id,
                slot_number=slot_number,
                started_at=metadata.get("started_at", ""),
                message_preview=metadata.get("message_preview", ""),
                duration_seconds=duration_seconds
            ))

        # Sort by slot number
        slots.sort(key=lambda s: s.slot_number)

        active_count = len(slots)
        return SlotState(
            agent_name=agent_name,
            max_parallel_tasks=max_parallel_tasks,
            active_slots=active_count,
            available_slots=max(0, max_parallel_tasks - active_count),
            slots=slots
        )

    async def get_all_slot_states(self, agent_capacities: Dict[str, int]) -> Dict[str, Dict[str, Any]]:
        """
        Get slot states for multiple agents efficiently.

        Args:
            agent_capacities: Dict mapping agent_name to max_parallel_tasks

        Returns:
            Dict mapping agent_name to {"max": N, "active": M}
        """
        result = {}

        for agent_name, max_tasks in agent_capacities.items():
            slots_key = self._slots_key(agent_name)
            active_count = self.redis.zcard(slots_key)
            result[agent_name] = {
                "max": max_tasks,
                "active": active_count
            }

        return result

    async def _cleanup_stale_slots_for_agent(self, agent_name: str) -> int:
        """Remove slots older than TTL for a single agent."""
        slots_key = self._slots_key(agent_name)
        cutoff = time.time() - SLOT_TTL_SECONDS

        # Get stale entries before removing
        stale = self.redis.zrangebyscore(slots_key, "-inf", cutoff)

        if stale:
            # Remove stale slots
            removed = self.redis.zremrangebyscore(slots_key, "-inf", cutoff)

            # Clean up metadata
            for execution_id in stale:
                metadata_key = self._metadata_key(agent_name, execution_id)
                self.redis.delete(metadata_key)

            logger.warning(
                f"[Slots] Cleaned up {removed} stale slots for agent '{agent_name}'"
            )
            return removed

        return 0

    async def cleanup_stale_slots(self) -> int:
        """
        Remove slots older than TTL for all agents.

        Returns:
            Total number of stale slots removed
        """
        total_removed = 0

        # Find all agent slot keys
        pattern = f"{self.slots_prefix}*"
        cursor = 0
        while True:
            cursor, keys = self.redis.scan(cursor, match=pattern, count=100)
            for key in keys:
                agent_name = key.replace(self.slots_prefix, "")
                removed = await self._cleanup_stale_slots_for_agent(agent_name)
                total_removed += removed
            if cursor == 0:
                break

        if total_removed > 0:
            logger.info(f"[Slots] Cleanup removed {total_removed} stale slots total")

        return total_removed

    async def get_active_count(self, agent_name: str) -> int:
        """Get count of active slots for an agent."""
        slots_key = self._slots_key(agent_name)
        return self.redis.zcard(slots_key)

    async def is_at_capacity(self, agent_name: str, max_parallel_tasks: int) -> bool:
        """Check if agent is at capacity."""
        active = await self.get_active_count(agent_name)
        return active >= max_parallel_tasks

    async def force_clear_slots(self, agent_name: str) -> int:
        """
        Force clear all slots for an agent (emergency use).

        Returns:
            Number of slots cleared
        """
        slots_key = self._slots_key(agent_name)

        # Get all execution IDs first
        entries = self.redis.zrange(slots_key, 0, -1)
        count = len(entries)

        if count > 0:
            # Delete slot set
            self.redis.delete(slots_key)

            # Delete all metadata
            for execution_id in entries:
                metadata_key = self._metadata_key(agent_name, execution_id)
                self.redis.delete(metadata_key)

            logger.warning(f"[Slots] Force cleared {count} slots for agent '{agent_name}'")

        return count


# Global instance
_slot_service: Optional[SlotService] = None


def get_slot_service() -> SlotService:
    """Get the global slot service instance."""
    global _slot_service
    if _slot_service is None:
        import os
        redis_url = os.getenv("REDIS_URL", "redis://redis:6379")
        _slot_service = SlotService(redis_url)
    return _slot_service
