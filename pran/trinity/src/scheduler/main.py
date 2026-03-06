#!/usr/bin/env python3
"""
Trinity Scheduler Service - Main Entry Point.

A standalone scheduler service for executing scheduled agent tasks.
Runs as a single-instance service with distributed locking.

Usage:
    python -m scheduler.main
    # or
    python src/scheduler/main.py
"""

import asyncio
import logging
import signal
import sys
from datetime import datetime
from typing import Optional

from aiohttp import web

from .config import config
from .service import SchedulerService

# Configure logging
logging.basicConfig(
    level=getattr(logging, config.log_level),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger(__name__)


class SchedulerApp:
    """
    Main application for the scheduler service.

    Manages:
    - Scheduler service lifecycle
    - Health check HTTP server
    - Graceful shutdown
    """

    def __init__(self):
        self.scheduler_service: Optional[SchedulerService] = None
        self.health_app: Optional[web.Application] = None
        self.health_runner: Optional[web.AppRunner] = None
        self._shutdown_event = asyncio.Event()

    async def start(self):
        """Start the scheduler application."""
        logger.info("=" * 60)
        logger.info("Trinity Scheduler Service Starting")
        logger.info("=" * 60)
        logger.info(f"Database: {config.database_path}")
        logger.info(f"Redis: {config.redis_url}")
        logger.info(f"Health server: {config.health_host}:{config.health_port}")
        logger.info("=" * 60)

        # Initialize scheduler service
        self.scheduler_service = SchedulerService()

        # Start health server
        await self._start_health_server()

        # Initialize and run scheduler
        self.scheduler_service.initialize()

        # Run until shutdown
        await self._run_until_shutdown()

    async def _start_health_server(self):
        """Start the health check HTTP server."""
        self.health_app = web.Application()
        self.health_app.router.add_get("/health", self._health_handler)
        self.health_app.router.add_get("/status", self._status_handler)
        self.health_app.router.add_get("/", self._root_handler)
        # Manual trigger endpoint - called by backend for manual schedule triggers
        self.health_app.router.add_post("/api/schedules/{schedule_id}/trigger", self._trigger_handler)

        self.health_runner = web.AppRunner(self.health_app)
        await self.health_runner.setup()

        site = web.TCPSite(
            self.health_runner,
            config.health_host,
            config.health_port
        )
        await site.start()

        logger.info(f"Health server started on {config.health_host}:{config.health_port}")

    async def _health_handler(self, request: web.Request) -> web.Response:
        """Health check endpoint."""
        if self.scheduler_service and self.scheduler_service.is_healthy():
            return web.json_response({"status": "healthy"})
        else:
            return web.json_response(
                {"status": "unhealthy"},
                status=503
            )

    async def _status_handler(self, request: web.Request) -> web.Response:
        """Detailed status endpoint."""
        if not self.scheduler_service:
            return web.json_response(
                {"error": "Scheduler not initialized"},
                status=503
            )

        status = self.scheduler_service.get_status()
        return web.json_response({
            "running": status.running,
            "jobs_count": status.jobs_count,
            "uptime_seconds": status.uptime_seconds,
            "last_check": status.last_check.isoformat(),
            "jobs": status.jobs
        })

    async def _root_handler(self, request: web.Request) -> web.Response:
        """Root endpoint with service info."""
        return web.json_response({
            "service": "Trinity Scheduler",
            "version": "1.0.0",
            "endpoints": {
                "/health": "Health check",
                "/status": "Detailed status",
                "/api/schedules/{schedule_id}/trigger": "Manual trigger (POST)"
            }
        })

    async def _trigger_handler(self, request: web.Request) -> web.Response:
        """
        Manual trigger endpoint.

        POST /api/schedules/{schedule_id}/trigger

        Manually triggers a schedule execution with the same flow as cron triggers,
        including activity tracking and WebSocket broadcasts.

        Returns:
            {
                "status": "triggered",
                "schedule_id": "...",
                "execution_id": "..."
            }
        """
        schedule_id = request.match_info.get("schedule_id")
        if not schedule_id:
            return web.json_response(
                {"error": "schedule_id is required"},
                status=400
            )

        if not self.scheduler_service:
            return web.json_response(
                {"error": "Scheduler not initialized"},
                status=503
            )

        # Get schedule to validate it exists
        schedule = self.scheduler_service.db.get_schedule(schedule_id)
        if not schedule:
            return web.json_response(
                {"error": f"Schedule not found: {schedule_id}"},
                status=404
            )

        logger.info(f"Manual trigger received for schedule {schedule_id} ({schedule.name})")

        # Execute in background (fire-and-forget)
        # Pass triggered_by="manual" to distinguish from cron triggers
        asyncio.create_task(
            self._execute_manual_trigger(schedule_id)
        )

        # Return immediately with execution info
        # The actual execution will create its own execution record
        return web.json_response({
            "status": "triggered",
            "schedule_id": schedule_id,
            "schedule_name": schedule.name,
            "agent_name": schedule.agent_name,
            "message": "Execution started in background"
        })

    async def _execute_manual_trigger(self, schedule_id: str):
        """Execute a manually triggered schedule."""
        try:
            # Acquire lock (manual triggers still need locking to prevent concurrent execution)
            lock = self.scheduler_service.lock_manager.try_acquire_schedule_lock(schedule_id)
            if not lock:
                logger.warning(f"Manual trigger for {schedule_id}: schedule already executing")
                return

            try:
                await self.scheduler_service._execute_schedule_with_lock(
                    schedule_id,
                    triggered_by="manual"
                )
            finally:
                lock.release()

        except Exception as e:
            logger.error(f"Manual trigger execution failed for {schedule_id}: {e}")

    async def _run_until_shutdown(self):
        """Run the scheduler until shutdown signal."""
        from .config import config

        sync_interval = config.schedule_reload_interval
        heartbeat_interval = 30
        last_sync = datetime.utcnow()

        try:
            # Heartbeat and sync loop
            while not self._shutdown_event.is_set():
                if self.scheduler_service:
                    # Heartbeat
                    self.scheduler_service.lock_manager.set_heartbeat(
                        self.scheduler_service._instance_id
                    )

                    # Check if it's time to sync schedules
                    now = datetime.utcnow()
                    if (now - last_sync).total_seconds() >= sync_interval:
                        await self.scheduler_service._sync_schedules()
                        last_sync = now

                await asyncio.sleep(heartbeat_interval)
        except asyncio.CancelledError:
            pass

    async def shutdown(self):
        """Graceful shutdown."""
        logger.info("Initiating graceful shutdown...")
        self._shutdown_event.set()

        if self.scheduler_service:
            self.scheduler_service.shutdown()

        if self.health_runner:
            await self.health_runner.cleanup()

        logger.info("Scheduler service stopped")

    def setup_signal_handlers(self, loop: asyncio.AbstractEventLoop):
        """Setup signal handlers for graceful shutdown."""
        for sig in (signal.SIGTERM, signal.SIGINT):
            loop.add_signal_handler(
                sig,
                lambda s=sig: asyncio.create_task(self._signal_handler(s))
            )

    async def _signal_handler(self, sig):
        """Handle shutdown signals."""
        logger.info(f"Received signal {sig.name}, shutting down...")
        await self.shutdown()


async def main():
    """Main entry point."""
    app = SchedulerApp()

    loop = asyncio.get_running_loop()
    app.setup_signal_handlers(loop)

    try:
        await app.start()
    except Exception as e:
        logger.exception(f"Scheduler service error: {e}")
        await app.shutdown()
        sys.exit(1)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Scheduler interrupted")
        sys.exit(0)
