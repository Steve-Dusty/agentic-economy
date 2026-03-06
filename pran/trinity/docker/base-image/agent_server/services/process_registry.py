"""
Process Registry for tracking running subprocess handles.

Enables termination of executions by execution_id.
Used by both Claude Code and Gemini runtimes.

Also provides log streaming infrastructure for live execution monitoring.
"""

import signal
import subprocess
import asyncio
import logging
from datetime import datetime
from typing import Dict, Optional, List, AsyncIterator
from threading import Lock

logger = logging.getLogger(__name__)


class ProcessRegistry:
    """
    Registry for tracking running subprocess handles.
    Enables termination of executions by execution_id.

    Thread-safe via mutex lock for all operations.

    Also provides log streaming infrastructure:
    - Each execution can have multiple log subscribers (asyncio.Queue)
    - Log entries are published to all subscribers as they arrive
    - Subscribers receive entries until execution completes
    """

    def __init__(self):
        self._processes: Dict[str, dict] = {}
        self._lock = Lock()
        # Log streaming: execution_id -> list of subscriber queues
        self._log_subscribers: Dict[str, List[asyncio.Queue]] = {}
        # Buffered logs: execution_id -> list of log entries (for late joiners)
        self._log_buffers: Dict[str, List[dict]] = {}
        # Maximum buffer size per execution (prevents memory bloat)
        self._max_buffer_size = 1000

    def register(self, execution_id: str, process: subprocess.Popen, metadata: dict = None):
        """
        Register a running process.

        Args:
            execution_id: Unique identifier for this execution
            process: The subprocess.Popen handle
            metadata: Optional metadata (type, message preview, etc.)
        """
        with self._lock:
            self._processes[execution_id] = {
                "process": process,
                "started_at": datetime.utcnow(),
                "metadata": metadata or {}
            }
            # Initialize log streaming structures
            self._log_subscribers[execution_id] = []
            self._log_buffers[execution_id] = []
            logger.info(f"[ProcessRegistry] Registered execution {execution_id}")

    def unregister(self, execution_id: str):
        """Unregister a completed process and signal stream end to subscribers."""
        with self._lock:
            if execution_id in self._processes:
                del self._processes[execution_id]
                logger.info(f"[ProcessRegistry] Unregistered execution {execution_id}")

            # Signal end of stream to all subscribers
            if execution_id in self._log_subscribers:
                for queue in self._log_subscribers[execution_id]:
                    try:
                        queue.put_nowait({"type": "stream_end"})
                    except asyncio.QueueFull:
                        pass
                del self._log_subscribers[execution_id]

            # Clean up buffer (keep for a bit for late requests, but this is fine)
            if execution_id in self._log_buffers:
                del self._log_buffers[execution_id]

    def terminate(self, execution_id: str, graceful_timeout: int = 5) -> dict:
        """
        Terminate a running process.

        Uses graceful termination (SIGINT) first, then force kills (SIGKILL)
        if the process doesn't respond within the timeout.

        Args:
            execution_id: The execution to terminate
            graceful_timeout: Seconds to wait after SIGINT before SIGKILL

        Returns:
            dict with termination status:
            - {"success": True, "returncode": int} on success
            - {"success": False, "reason": "not_found"} if not registered
            - {"success": False, "reason": "already_finished", "returncode": int}
            - {"success": False, "reason": "error", "error": str}
        """
        with self._lock:
            entry = self._processes.get(execution_id)
            if not entry:
                return {"success": False, "reason": "not_found"}

            process = entry["process"]
            if process.poll() is not None:
                # Already finished
                returncode = process.returncode
                del self._processes[execution_id]
                return {"success": False, "reason": "already_finished", "returncode": returncode}

        # Terminate outside lock to avoid blocking other operations
        try:
            # Graceful termination first (SIGINT = Ctrl+C)
            # Claude Code handles SIGINT gracefully, finishing current tool
            logger.info(f"[ProcessRegistry] Sending SIGINT to execution {execution_id}")
            process.send_signal(signal.SIGINT)

            try:
                process.wait(timeout=graceful_timeout)
                logger.info(f"[ProcessRegistry] Execution {execution_id} terminated gracefully")
            except subprocess.TimeoutExpired:
                # Force kill if graceful didn't work
                logger.warning(f"[ProcessRegistry] Force killing execution {execution_id}")
                process.kill()
                process.wait(timeout=2)

            returncode = process.returncode

            with self._lock:
                if execution_id in self._processes:
                    del self._processes[execution_id]

            return {"success": True, "returncode": returncode}

        except Exception as e:
            logger.error(f"[ProcessRegistry] Error terminating {execution_id}: {e}")
            return {"success": False, "reason": "error", "error": str(e)}

    def get_status(self, execution_id: str) -> Optional[dict]:
        """
        Get status of a registered process.

        Returns None if execution not found.
        """
        with self._lock:
            entry = self._processes.get(execution_id)
            if not entry:
                return None

            process = entry["process"]
            poll_result = process.poll()

            return {
                "execution_id": execution_id,
                "running": poll_result is None,
                "returncode": poll_result,
                "started_at": entry["started_at"].isoformat(),
                "metadata": entry["metadata"]
            }

    def list_running(self) -> list:
        """List all currently running executions."""
        with self._lock:
            result = []
            for exec_id, entry in self._processes.items():
                process = entry["process"]
                if process.poll() is None:
                    result.append({
                        "execution_id": exec_id,
                        "started_at": entry["started_at"].isoformat(),
                        "metadata": entry["metadata"]
                    })
            return result

    def cleanup_finished(self) -> int:
        """
        Remove entries for finished processes.

        Returns the count of cleaned up entries.
        """
        with self._lock:
            finished = [
                exec_id for exec_id, entry in self._processes.items()
                if entry["process"].poll() is not None
            ]
            for exec_id in finished:
                del self._processes[exec_id]
            if finished:
                logger.info(f"[ProcessRegistry] Cleaned up {len(finished)} finished processes")
            return len(finished)

    # ========================================================================
    # Log Streaming Methods
    # ========================================================================

    def publish_log_entry(self, execution_id: str, entry: dict):
        """
        Publish a log entry to all subscribers for an execution.

        Called from claude_code.py as each line is processed.
        Non-blocking: if a subscriber's queue is full, the entry is dropped for that subscriber.

        Args:
            execution_id: The execution ID
            entry: The raw JSON log entry from Claude Code
        """
        with self._lock:
            # Add to buffer for late joiners
            if execution_id in self._log_buffers:
                buffer = self._log_buffers[execution_id]
                buffer.append(entry)
                # Trim buffer if too large
                if len(buffer) > self._max_buffer_size:
                    self._log_buffers[execution_id] = buffer[-self._max_buffer_size:]

            # Publish to all subscribers
            if execution_id in self._log_subscribers:
                for queue in self._log_subscribers[execution_id]:
                    try:
                        queue.put_nowait(entry)
                    except asyncio.QueueFull:
                        # Drop entry for this slow subscriber
                        logger.warning(f"[ProcessRegistry] Log queue full for execution {execution_id}, dropping entry")

    def subscribe_logs(self, execution_id: str) -> asyncio.Queue:
        """
        Subscribe to log entries for an execution.

        Returns a queue that will receive log entries as they arrive.
        First sends all buffered entries, then streams new ones.
        Returns None if execution not found.

        Args:
            execution_id: The execution ID to subscribe to

        Returns:
            asyncio.Queue to receive log entries, or None if not found
        """
        queue = asyncio.Queue(maxsize=500)

        with self._lock:
            # Check if execution exists (or recently existed with buffer)
            if execution_id not in self._log_subscribers and execution_id not in self._log_buffers:
                return None

            # Send buffered entries first
            if execution_id in self._log_buffers:
                for entry in self._log_buffers[execution_id]:
                    try:
                        queue.put_nowait(entry)
                    except asyncio.QueueFull:
                        break

            # Register as subscriber if execution is still running
            if execution_id in self._log_subscribers:
                self._log_subscribers[execution_id].append(queue)
            else:
                # Execution finished, just send stream_end
                try:
                    queue.put_nowait({"type": "stream_end"})
                except asyncio.QueueFull:
                    pass

        return queue

    def unsubscribe_logs(self, execution_id: str, queue: asyncio.Queue):
        """
        Unsubscribe from log entries.

        Args:
            execution_id: The execution ID
            queue: The queue to unsubscribe
        """
        with self._lock:
            if execution_id in self._log_subscribers:
                try:
                    self._log_subscribers[execution_id].remove(queue)
                except ValueError:
                    pass

    def get_buffered_logs(self, execution_id: str) -> Optional[List[dict]]:
        """
        Get all buffered log entries for an execution.

        Used for non-streaming requests (e.g., page refresh on completed execution).

        Args:
            execution_id: The execution ID

        Returns:
            List of log entries, or None if execution not found
        """
        with self._lock:
            if execution_id in self._log_buffers:
                return list(self._log_buffers[execution_id])
            return None

    def is_execution_running(self, execution_id: str) -> bool:
        """Check if an execution is currently running."""
        with self._lock:
            return execution_id in self._processes


# Global instance
_process_registry: Optional[ProcessRegistry] = None


def get_process_registry() -> ProcessRegistry:
    """Get the global process registry instance."""
    global _process_registry
    if _process_registry is None:
        _process_registry = ProcessRegistry()
    return _process_registry
