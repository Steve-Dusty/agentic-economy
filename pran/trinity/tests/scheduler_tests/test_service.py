"""
Tests for the scheduler service.
"""

# Path setup must happen before scheduler imports
import sys
from pathlib import Path
_this_file = Path(__file__).resolve()
_src_path = str(_this_file.parent.parent.parent / 'src')
if _src_path not in sys.path:
    sys.path.insert(0, _src_path)
import os

import asyncio
from datetime import datetime
from unittest.mock import MagicMock, AsyncMock, patch
import pytest

from scheduler.service import SchedulerService
from scheduler.database import SchedulerDatabase
from scheduler.locking import LockManager
from scheduler.models import Schedule, AgentTaskResponse, AgentTaskMetrics


class TestSchedulerService:
    """Tests for SchedulerService."""

    @pytest.mark.asyncio
    async def test_initialization(self, db_with_data: SchedulerDatabase, mock_lock_manager: LockManager):
        """Test scheduler initialization."""
        service = SchedulerService(
            database=db_with_data,
            lock_manager=mock_lock_manager
        )

        service.initialize()

        assert service._initialized is True
        assert service.scheduler is not None
        assert service.scheduler.running is True

        service.shutdown()

    @pytest.mark.asyncio
    async def test_double_initialization_warning(self, db_with_data: SchedulerDatabase, mock_lock_manager: LockManager):
        """Test that double initialization logs a warning."""
        service = SchedulerService(
            database=db_with_data,
            lock_manager=mock_lock_manager
        )

        service.initialize()
        service.initialize()  # Should log warning but not fail

        service.shutdown()

    @pytest.mark.asyncio
    async def test_shutdown(self, db_with_data: SchedulerDatabase, mock_lock_manager: LockManager):
        """Test graceful shutdown."""
        service = SchedulerService(
            database=db_with_data,
            lock_manager=mock_lock_manager
        )

        service.initialize()
        service.shutdown()

        # The key invariant is that _initialized is False after shutdown
        assert service._initialized is False
        # Note: AsyncIOScheduler.running may not immediately be False with wait=False
        # The service properly tracks shutdown via _initialized

    def test_get_status_not_initialized(self, db: SchedulerDatabase, mock_lock_manager: LockManager):
        """Test status when scheduler not initialized."""
        service = SchedulerService(
            database=db,
            lock_manager=mock_lock_manager
        )

        status = service.get_status()

        assert status.running is False
        assert status.jobs_count == 0

    @pytest.mark.asyncio
    async def test_get_status_running(self, db_with_data: SchedulerDatabase, mock_lock_manager: LockManager):
        """Test status when scheduler is running."""
        service = SchedulerService(
            database=db_with_data,
            lock_manager=mock_lock_manager
        )

        service.initialize()
        status = service.get_status()

        assert status.running is True
        assert status.jobs_count == 2  # Two enabled schedules
        assert status.uptime_seconds >= 0

        service.shutdown()

    @pytest.mark.asyncio
    async def test_is_healthy(self, db_with_data: SchedulerDatabase, mock_lock_manager: LockManager):
        """Test health check."""
        service = SchedulerService(
            database=db_with_data,
            lock_manager=mock_lock_manager
        )

        assert service.is_healthy() is False

        service.initialize()
        assert service.is_healthy() is True

        service.shutdown()
        assert service.is_healthy() is False


class TestScheduleJobManagement:
    """Tests for job management in the scheduler."""

    @pytest.mark.asyncio
    async def test_add_schedule(self, db_with_data: SchedulerDatabase, mock_lock_manager: LockManager, sample_schedule: Schedule):
        """Test adding a schedule to the scheduler."""
        service = SchedulerService(
            database=db_with_data,
            lock_manager=mock_lock_manager
        )
        service.initialize()

        initial_count = len(service.scheduler.get_jobs())
        service.add_schedule(sample_schedule)

        assert len(service.scheduler.get_jobs()) == initial_count + 1

        service.shutdown()

    @pytest.mark.asyncio
    async def test_add_disabled_schedule(self, db_with_data: SchedulerDatabase, mock_lock_manager: LockManager, sample_schedule: Schedule):
        """Test that disabled schedules are not added."""
        service = SchedulerService(
            database=db_with_data,
            lock_manager=mock_lock_manager
        )
        service.initialize()

        sample_schedule.enabled = False
        initial_count = len(service.scheduler.get_jobs())
        service.add_schedule(sample_schedule)

        assert len(service.scheduler.get_jobs()) == initial_count

        service.shutdown()

    @pytest.mark.asyncio
    async def test_remove_schedule(self, db_with_data: SchedulerDatabase, mock_lock_manager: LockManager):
        """Test removing a schedule from the scheduler."""
        service = SchedulerService(
            database=db_with_data,
            lock_manager=mock_lock_manager
        )
        service.initialize()

        initial_count = len(service.scheduler.get_jobs())
        service.remove_schedule("schedule-1")

        assert len(service.scheduler.get_jobs()) == initial_count - 1

        service.shutdown()

    @pytest.mark.asyncio
    async def test_update_schedule(self, db_with_data: SchedulerDatabase, mock_lock_manager: LockManager, sample_schedule: Schedule):
        """Test updating a schedule."""
        service = SchedulerService(
            database=db_with_data,
            lock_manager=mock_lock_manager
        )
        service.initialize()

        # Add then update
        service.add_schedule(sample_schedule)
        sample_schedule.cron_expression = "0 10 * * *"
        service.update_schedule(sample_schedule)

        # Job should still exist with new schedule
        job = service.scheduler.get_job(f"schedule_{sample_schedule.id}")
        assert job is not None

        service.shutdown()

    @pytest.mark.asyncio
    async def test_reload_schedules(self, db_with_data: SchedulerDatabase, mock_lock_manager: LockManager):
        """Test reloading all schedules."""
        service = SchedulerService(
            database=db_with_data,
            lock_manager=mock_lock_manager
        )
        service.initialize()

        # Reload
        service.reload_schedules()

        # Should have same number of jobs (2 enabled)
        assert len(service.scheduler.get_jobs()) == 2

        service.shutdown()


class TestScheduleExecution:
    """Tests for schedule execution."""

    @pytest.mark.asyncio
    async def test_execute_schedule_acquires_lock(self, db_with_data: SchedulerDatabase, mock_lock_manager: LockManager):
        """Test that execution acquires a lock."""
        service = SchedulerService(
            database=db_with_data,
            lock_manager=mock_lock_manager
        )

        # Mock lock acquisition
        mock_lock = MagicMock()
        mock_lock.acquire.return_value = True
        mock_lock_manager.try_acquire_schedule_lock = MagicMock(return_value=mock_lock)

        # Mock agent client
        with patch('scheduler.service.get_agent_client') as mock_get_client:
            mock_client = AsyncMock()
            mock_client.task.return_value = AgentTaskResponse(
                response_text="Success",
                metrics=AgentTaskMetrics(context_used=1000, context_max=200000)
            )
            mock_get_client.return_value = mock_client

            await service._execute_schedule("schedule-1")

        mock_lock_manager.try_acquire_schedule_lock.assert_called_once_with("schedule-1")
        mock_lock.release.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_schedule_skips_if_locked(self, db_with_data: SchedulerDatabase, mock_lock_manager: LockManager):
        """Test that execution is skipped if lock cannot be acquired."""
        service = SchedulerService(
            database=db_with_data,
            lock_manager=mock_lock_manager
        )

        # Mock lock acquisition failure
        mock_lock_manager.try_acquire_schedule_lock = MagicMock(return_value=None)

        # Mock agent client (should not be called)
        with patch('scheduler.service.get_agent_client') as mock_get_client:
            await service._execute_schedule("schedule-1")

        mock_get_client.assert_not_called()

    @pytest.mark.asyncio
    async def test_execute_schedule_checks_enabled(self, db_with_data: SchedulerDatabase, mock_lock_manager: LockManager):
        """Test that disabled schedules are skipped."""
        service = SchedulerService(
            database=db_with_data,
            lock_manager=mock_lock_manager
        )

        # Mock lock acquisition
        mock_lock = MagicMock()
        mock_lock.acquire.return_value = True
        mock_lock_manager.try_acquire_schedule_lock = MagicMock(return_value=mock_lock)

        # Try to execute disabled schedule
        with patch('scheduler.service.get_agent_client') as mock_get_client:
            await service._execute_schedule("schedule-3")  # Disabled

        mock_get_client.assert_not_called()

    @pytest.mark.asyncio
    async def test_execute_schedule_checks_autonomy(self, initialized_db: str, mock_lock_manager: LockManager):
        """Test that schedules are skipped if autonomy is disabled."""
        # Create DB with autonomy disabled
        import sqlite3
        conn = sqlite3.connect(initialized_db)
        cursor = conn.cursor()
        now = datetime.utcnow().isoformat()

        # Add agent with autonomy disabled
        cursor.execute("""
            INSERT INTO agent_ownership (agent_name, owner_id, autonomy_enabled, created_at)
            VALUES ('no-autonomy-agent', 1, 0, ?)
        """, (now,))

        # Add schedule for that agent
        cursor.execute("""
            INSERT INTO agent_schedules (
                id, agent_name, name, cron_expression, message, enabled,
                timezone, description, owner_id, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            "schedule-no-auto", "no-autonomy-agent", "Task",
            "0 9 * * *", "Run task", 1, "UTC", "Test", 1, now, now
        ))
        conn.commit()
        conn.close()

        db = SchedulerDatabase(database_path=initialized_db)
        service = SchedulerService(database=db, lock_manager=mock_lock_manager)

        # Mock lock
        mock_lock = MagicMock()
        mock_lock.acquire.return_value = True
        mock_lock_manager.try_acquire_schedule_lock = MagicMock(return_value=mock_lock)

        with patch('scheduler.service.get_agent_client') as mock_get_client:
            await service._execute_schedule("schedule-no-auto")

        mock_get_client.assert_not_called()


class TestEventPublishing:
    """Tests for event publishing."""

    @pytest.mark.asyncio
    async def test_publish_event(self, db_with_data: SchedulerDatabase, mock_lock_manager: LockManager, mock_redis: MagicMock):
        """Test event publishing to Redis."""
        service = SchedulerService(
            database=db_with_data,
            lock_manager=mock_lock_manager
        )
        service._redis = mock_redis

        await service._publish_event({
            "type": "test_event",
            "data": "test"
        })

        mock_redis.publish.assert_called_once()
        call_args = mock_redis.publish.call_args
        assert call_args[0][0] == "scheduler:events"


class TestActivityTracking:
    """Tests for activity tracking via backend internal API (added 2026-02-11)."""

    @pytest.mark.asyncio
    async def test_track_activity_start_calls_backend_api(self, db_with_data: SchedulerDatabase, mock_lock_manager: LockManager):
        """Test that _track_activity_start calls the backend internal API."""
        service = SchedulerService(
            database=db_with_data,
            lock_manager=mock_lock_manager
        )

        schedule = db_with_data.get_schedule("schedule-1")

        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"activity_id": "test-activity-123"}
            mock_client.post.return_value = mock_response
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client_class.return_value = mock_client

            activity_id = await service._track_activity_start(
                agent_name="test-agent",
                schedule=schedule,
                execution_id="exec-123",
                triggered_by="schedule"
            )

            assert activity_id == "test-activity-123"
            mock_client.post.assert_called_once()
            call_args = mock_client.post.call_args
            assert "/api/internal/activities/track" in call_args[0][0]
            assert call_args[1]["json"]["agent_name"] == "test-agent"
            assert call_args[1]["json"]["activity_type"] == "schedule_start"
            assert call_args[1]["json"]["triggered_by"] == "schedule"

    @pytest.mark.asyncio
    async def test_track_activity_start_returns_none_on_failure(self, db_with_data: SchedulerDatabase, mock_lock_manager: LockManager):
        """Test that _track_activity_start returns None on API failure."""
        service = SchedulerService(
            database=db_with_data,
            lock_manager=mock_lock_manager
        )

        schedule = db_with_data.get_schedule("schedule-1")

        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_response = MagicMock()
            mock_response.status_code = 500
            mock_response.text = "Internal error"
            mock_client.post.return_value = mock_response
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client_class.return_value = mock_client

            activity_id = await service._track_activity_start(
                agent_name="test-agent",
                schedule=schedule,
                execution_id="exec-123",
                triggered_by="schedule"
            )

            assert activity_id is None

    @pytest.mark.asyncio
    async def test_complete_activity_calls_backend_api(self, db_with_data: SchedulerDatabase, mock_lock_manager: LockManager):
        """Test that _complete_activity calls the backend internal API."""
        service = SchedulerService(
            database=db_with_data,
            lock_manager=mock_lock_manager
        )

        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_client.post.return_value = mock_response
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client_class.return_value = mock_client

            await service._complete_activity(
                activity_id="test-activity-123",
                status="completed",
                details={"execution_id": "exec-123"}
            )

            mock_client.post.assert_called_once()
            call_args = mock_client.post.call_args
            assert "/api/internal/activities/test-activity-123/complete" in call_args[0][0]
            assert call_args[1]["json"]["status"] == "completed"

    @pytest.mark.asyncio
    async def test_complete_activity_skips_if_no_activity_id(self, db_with_data: SchedulerDatabase, mock_lock_manager: LockManager):
        """Test that _complete_activity does nothing if activity_id is None."""
        service = SchedulerService(
            database=db_with_data,
            lock_manager=mock_lock_manager
        )

        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value = mock_client

            await service._complete_activity(
                activity_id=None,
                status="completed"
            )

            # Should not have created a client at all
            mock_client.post.assert_not_called()

    @pytest.mark.asyncio
    async def test_execute_schedule_with_lock_tracks_activity(self, db_with_data: SchedulerDatabase, mock_lock_manager: LockManager):
        """Test that execution tracks activity via internal API."""
        service = SchedulerService(
            database=db_with_data,
            lock_manager=mock_lock_manager
        )

        # Mock agent client
        with patch('scheduler.service.get_agent_client') as mock_get_client, \
             patch.object(service, '_track_activity_start', new_callable=AsyncMock) as mock_track, \
             patch.object(service, '_complete_activity', new_callable=AsyncMock) as mock_complete, \
             patch.object(service, '_publish_event', new_callable=AsyncMock):

            mock_client = AsyncMock()
            mock_client.task.return_value = AgentTaskResponse(
                response_text="Success",
                metrics=AgentTaskMetrics(context_used=1000, context_max=200000),
                raw_response={"execution_log": []}
            )
            mock_get_client.return_value = mock_client
            mock_track.return_value = "activity-123"

            await service._execute_schedule_with_lock("schedule-1", triggered_by="schedule")

            # Should have tracked activity start
            mock_track.assert_called_once()
            call_args = mock_track.call_args
            assert call_args[1]["triggered_by"] == "schedule"

            # Should have completed activity
            mock_complete.assert_called_once()
            complete_args = mock_complete.call_args
            assert complete_args[1]["activity_id"] == "activity-123"
            assert complete_args[1]["status"] == "completed"

    @pytest.mark.asyncio
    async def test_execute_schedule_with_manual_trigger(self, db_with_data: SchedulerDatabase, mock_lock_manager: LockManager):
        """Test that manual triggers use triggered_by='manual'."""
        service = SchedulerService(
            database=db_with_data,
            lock_manager=mock_lock_manager
        )

        # Mock agent client
        with patch('scheduler.service.get_agent_client') as mock_get_client, \
             patch.object(service, '_track_activity_start', new_callable=AsyncMock) as mock_track, \
             patch.object(service, '_complete_activity', new_callable=AsyncMock), \
             patch.object(service, '_publish_event', new_callable=AsyncMock):

            mock_client = AsyncMock()
            mock_client.task.return_value = AgentTaskResponse(
                response_text="Success",
                metrics=AgentTaskMetrics(context_used=1000, context_max=200000),
                raw_response={"execution_log": []}
            )
            mock_get_client.return_value = mock_client
            mock_track.return_value = "activity-456"

            await service._execute_schedule_with_lock("schedule-1", triggered_by="manual")

            # Should have tracked activity with manual trigger
            mock_track.assert_called_once()
            call_args = mock_track.call_args
            assert call_args[1]["triggered_by"] == "manual"
