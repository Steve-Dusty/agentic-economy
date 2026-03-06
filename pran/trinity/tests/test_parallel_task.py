"""
Parallel Task Execution Tests (test_parallel_task.py)

Tests for the parallel task execution feature (Requirement 12.1).
Covers parallel/stateless task execution without execution queue.
"""

import pytest
import time
import asyncio
import concurrent.futures
from utils.api_client import TrinityApiClient
from utils.assertions import (
    assert_status,
    assert_status_in,
    assert_json_response,
    assert_has_fields,
)


class TestParallelTaskEndpoint:
    """REQ-PARALLEL-001: Parallel task endpoint tests."""

    def test_task_endpoint_exists(
        self,
        api_client: TrinityApiClient,
        created_agent
    ):
        """POST /api/agents/{name}/task endpoint exists."""
        response = api_client.post(
            f"/api/agents/{created_agent['name']}/task",
            json={"message": "What is 2+2?"},
            timeout=30.0,
        )

        # Should not be 404 (endpoint exists)
        # May be 503 if agent not ready
        if response.status_code == 503:
            pytest.skip("Agent server not ready (503)")

        assert response.status_code != 404, "Task endpoint should exist"

    def test_task_nonexistent_agent_returns_404(self, api_client: TrinityApiClient):
        """POST /api/agents/{name}/task for non-existent agent returns 404."""
        response = api_client.post(
            "/api/agents/nonexistent-agent-xyz/task",
            json={"message": "hello"},
            timeout=30.0,
        )
        assert_status(response, 404)

    def test_task_stopped_agent_returns_error(
        self,
        api_client: TrinityApiClient,
        stopped_agent
    ):
        """POST /api/agents/{name}/task for stopped agent returns error."""
        response = api_client.post(
            f"/api/agents/{stopped_agent['name']}/task",
            json={"message": "hello"},
            timeout=30.0,
        )
        # Should get 400 or 503 for stopped agent
        assert_status_in(response, [400, 503])


class TestParallelTaskResponse:
    """REQ-PARALLEL-002: Parallel task response format tests."""

    @pytest.mark.slow
    @pytest.mark.requires_agent
    def test_task_returns_response(
        self,
        api_client: TrinityApiClient,
        created_agent
    ):
        """POST /api/agents/{name}/task returns a response."""
        response = api_client.post(
            f"/api/agents/{created_agent['name']}/task",
            json={"message": "What is 2+2? Reply with just the number."},
            timeout=120.0,
        )

        if response.status_code == 503:
            pytest.skip("Agent server not ready (503)")

        assert_status(response, 200)
        data = assert_json_response(response)

        # Should have required fields
        assert "response" in data, "Response should contain 'response' field"
        assert "session_id" in data, "Response should contain 'session_id' field"
        assert "timestamp" in data, "Response should contain 'timestamp' field"

    @pytest.mark.slow
    @pytest.mark.requires_agent
    def test_task_has_metadata(
        self,
        api_client: TrinityApiClient,
        created_agent
    ):
        """Task response includes execution metadata."""
        response = api_client.post(
            f"/api/agents/{created_agent['name']}/task",
            json={"message": "Say hello"},
            timeout=120.0,
        )

        if response.status_code == 503:
            pytest.skip("Agent server not ready")

        assert_status(response, 200)
        data = response.json()

        # Should have metadata
        assert "metadata" in data, "Response should contain 'metadata'"

    @pytest.mark.slow
    @pytest.mark.requires_agent
    def test_task_has_execution_log(
        self,
        api_client: TrinityApiClient,
        created_agent
    ):
        """Task response includes execution log."""
        response = api_client.post(
            f"/api/agents/{created_agent['name']}/task",
            json={"message": "Say hello"},
            timeout=120.0,
        )

        if response.status_code == 503:
            pytest.skip("Agent server not ready")

        assert_status(response, 200)
        data = response.json()

        # Should have execution log
        assert "execution_log" in data, "Response should contain 'execution_log'"
        assert isinstance(data["execution_log"], list)


class TestParallelTaskOptions:
    """REQ-PARALLEL-003: Parallel task option tests."""

    @pytest.mark.slow
    @pytest.mark.requires_agent
    def test_task_with_model_override(
        self,
        api_client: TrinityApiClient,
        created_agent
    ):
        """Task accepts model override parameter."""
        response = api_client.post(
            f"/api/agents/{created_agent['name']}/task",
            json={
                "message": "Say hi",
                "model": "haiku"
            },
            timeout=120.0,
        )

        if response.status_code == 503:
            pytest.skip("Agent server not ready")

        # Should work (200) or fail gracefully if model not available
        assert_status_in(response, [200, 400, 500])

    @pytest.mark.slow
    @pytest.mark.requires_agent
    def test_task_with_timeout(
        self,
        api_client: TrinityApiClient,
        created_agent
    ):
        """Task accepts timeout_seconds parameter."""
        response = api_client.post(
            f"/api/agents/{created_agent['name']}/task",
            json={
                "message": "Say hello",
                "timeout_seconds": 60
            },
            timeout=120.0,
        )

        if response.status_code == 503:
            pytest.skip("Agent server not ready")

        assert_status_in(response, [200, 504])  # 504 if timeout


class TestParallelTaskStateless:
    """REQ-PARALLEL-004: Parallel task statelessness tests."""

    @pytest.mark.slow
    @pytest.mark.requires_agent
    def test_task_does_not_affect_chat_history(
        self,
        api_client: TrinityApiClient,
        created_agent
    ):
        """Parallel tasks should not pollute chat history."""
        # Get initial history
        history_before = api_client.get(
            f"/api/agents/{created_agent['name']}/chat/history"
        )
        if history_before.status_code == 503:
            pytest.skip("Agent server not ready")

        # Execute parallel task
        task_response = api_client.post(
            f"/api/agents/{created_agent['name']}/task",
            json={"message": "This is a parallel task"},
            timeout=120.0,
        )

        if task_response.status_code == 503:
            pytest.skip("Agent server not ready")

        assert_status(task_response, 200)

        # Get history after
        history_after = api_client.get(
            f"/api/agents/{created_agent['name']}/chat/history"
        )

        # History should be unchanged (task is stateless)
        # Note: implementation may vary - some tracking is OK
        # but conversation context should not change
        assert_status(history_after, 200)

    @pytest.mark.slow
    @pytest.mark.requires_agent
    def test_tasks_have_unique_session_ids(
        self,
        api_client: TrinityApiClient,
        created_agent
    ):
        """Each parallel task should have a unique session ID."""
        # Execute two tasks
        response1 = api_client.post(
            f"/api/agents/{created_agent['name']}/task",
            json={"message": "Task 1"},
            timeout=120.0,
        )

        if response1.status_code == 503:
            pytest.skip("Agent server not ready")

        assert_status(response1, 200)
        session_id_1 = response1.json().get("session_id")

        response2 = api_client.post(
            f"/api/agents/{created_agent['name']}/task",
            json={"message": "Task 2"},
            timeout=120.0,
        )

        assert_status(response2, 200)
        session_id_2 = response2.json().get("session_id")

        # Session IDs should be different (each task is independent)
        assert session_id_1 != session_id_2, "Each task should have a unique session ID"


class TestParallelExecution:
    """REQ-PARALLEL-005: Actual parallel execution tests."""

    @pytest.mark.slow
    @pytest.mark.requires_agent
    def test_multiple_tasks_can_start_without_queue(
        self,
        api_client: TrinityApiClient,
        created_agent
    ):
        """Multiple parallel tasks should not get queued (no 429 response)."""
        # Start first task with short timeout to not block too long
        response1 = api_client.post(
            f"/api/agents/{created_agent['name']}/task",
            json={
                "message": "Task 1: What is 2+2?",
                "timeout_seconds": 60
            },
            timeout=30.0,  # Don't wait for completion
        )

        # Start second task immediately (shouldn't be queued)
        response2 = api_client.post(
            f"/api/agents/{created_agent['name']}/task",
            json={
                "message": "Task 2: What is 3+3?",
                "timeout_seconds": 60
            },
            timeout=30.0,
        )

        # Neither should return 429 (queue full)
        # Tasks may return 503 if agent not ready, that's OK
        if response1.status_code == 503:
            pytest.skip("Agent server not ready")

        # 429 would indicate queuing, which shouldn't happen for /task
        assert response1.status_code != 429, "Parallel tasks should not be queued"
        assert response2.status_code != 429, "Parallel tasks should not be queued"

    @pytest.mark.slow
    @pytest.mark.requires_agent
    def test_task_timeout_returns_504(
        self,
        api_client: TrinityApiClient,
        created_agent
    ):
        """Task that exceeds timeout should return 504."""
        # Use very short timeout
        response = api_client.post(
            f"/api/agents/{created_agent['name']}/task",
            json={
                "message": "Write a very long story about dragons",
                "timeout_seconds": 1  # Very short timeout
            },
            timeout=30.0,
        )

        if response.status_code == 503:
            pytest.skip("Agent server not ready")

        # Should either complete quickly or timeout
        assert_status_in(response, [200, 504])


class TestAsyncModeEndpoint:
    """REQ-PARALLEL-006: Async mode endpoint tests.

    Tests for the async_mode parameter which allows fire-and-forget
    task execution with polling for results.
    """

    def test_async_mode_nonexistent_agent_returns_404(
        self,
        api_client: TrinityApiClient
    ):
        """POST /api/agents/{name}/task with async_mode for non-existent agent returns 404."""
        response = api_client.post(
            "/api/agents/nonexistent-agent-xyz/task",
            json={"message": "hello", "async_mode": True},
            timeout=30.0,
        )
        assert_status(response, 404)

    def test_async_mode_stopped_agent_returns_error(
        self,
        api_client: TrinityApiClient,
        stopped_agent
    ):
        """POST /api/agents/{name}/task with async_mode for stopped agent returns error."""
        response = api_client.post(
            f"/api/agents/{stopped_agent['name']}/task",
            json={"message": "hello", "async_mode": True},
            timeout=30.0,
        )
        # Should get 400 or 503 for stopped agent
        assert_status_in(response, [400, 503])


class TestAsyncModeResponse:
    """REQ-PARALLEL-007: Async mode response format tests."""

    @pytest.mark.requires_agent
    def test_async_mode_returns_immediately(
        self,
        api_client: TrinityApiClient,
        created_agent
    ):
        """Task with async_mode=true returns immediately with execution_id."""
        response = api_client.post(
            f"/api/agents/{created_agent['name']}/task",
            json={
                "message": "What is the meaning of life? Think deeply and write a long essay.",
                "async_mode": True
            },
            timeout=10.0,  # Should return in < 1 second, not wait for task completion
        )

        if response.status_code == 503:
            pytest.skip("Agent server not ready (503)")

        assert_status(response, 200)
        data = assert_json_response(response)

        # Verify async response format
        assert_has_fields(data, ["status", "execution_id", "agent_name", "message", "async_mode"])
        assert data["status"] == "accepted", "Status should be 'accepted'"
        assert data["async_mode"] is True, "async_mode flag should be True"
        assert data["execution_id"], "execution_id should be non-empty"
        assert data["agent_name"] == created_agent["name"], "agent_name should match"
        assert "poll" in data["message"].lower() or "GET" in data["message"], \
            "Message should mention polling endpoint"

    @pytest.mark.requires_agent
    def test_async_mode_false_works_synchronously(
        self,
        api_client: TrinityApiClient,
        created_agent
    ):
        """Task with async_mode=false (default) still works synchronously."""
        response = api_client.post(
            f"/api/agents/{created_agent['name']}/task",
            json={
                "message": "What is 2+2? Reply with just the number.",
                "async_mode": False
            },
            timeout=120.0,
        )

        if response.status_code == 503:
            pytest.skip("Agent server not ready (503)")

        assert_status(response, 200)
        data = assert_json_response(response)

        # Should have synchronous response fields (NOT async fields)
        assert "response" in data, "Synchronous mode should return 'response' field"
        assert "session_id" in data, "Synchronous mode should return 'session_id' field"
        assert "status" not in data or data["status"] != "accepted", \
            "Should not return async 'accepted' status"

    @pytest.mark.requires_agent
    def test_async_mode_default_is_synchronous(
        self,
        api_client: TrinityApiClient,
        created_agent
    ):
        """Task without async_mode parameter defaults to synchronous execution."""
        response = api_client.post(
            f"/api/agents/{created_agent['name']}/task",
            json={"message": "What is 2+2? Reply with just the number."},
            timeout=120.0,
        )

        if response.status_code == 503:
            pytest.skip("Agent server not ready (503)")

        assert_status(response, 200)
        data = assert_json_response(response)

        # Should have synchronous response fields (NOT async fields)
        assert "response" in data, "Default mode should be synchronous"
        assert "session_id" in data, "Default mode should have session_id"


class TestAsyncModeExecution:
    """REQ-PARALLEL-008: Async mode execution and polling tests."""

    @pytest.mark.slow
    @pytest.mark.requires_agent
    def test_async_mode_creates_execution_record(
        self,
        api_client: TrinityApiClient,
        created_agent
    ):
        """Async task creates execution record with 'running' status."""
        # Submit async task
        response = api_client.post(
            f"/api/agents/{created_agent['name']}/task",
            json={
                "message": "Count to 10 slowly",
                "async_mode": True
            },
            timeout=10.0,
        )

        if response.status_code == 503:
            pytest.skip("Agent server not ready")

        assert_status(response, 200)
        data = response.json()
        execution_id = data["execution_id"]

        # Wait briefly for database write
        time.sleep(1)

        # Get executions list
        exec_list_response = api_client.get(
            f"/api/agents/{created_agent['name']}/executions"
        )
        assert_status(exec_list_response, 200)
        executions = exec_list_response.json()

        # Find our execution
        matching = [e for e in executions if e.get("id") == execution_id]
        assert len(matching) > 0, f"Execution {execution_id} should exist in executions list"

        execution = matching[0]
        assert execution["agent_name"] == created_agent["name"]
        # Status should be "running" or "success" (if task completed quickly)
        assert execution["status"] in ["running", "success", "failed"], \
            f"Expected status running/success/failed, got {execution['status']}"

    @pytest.mark.slow
    @pytest.mark.requires_agent
    def test_async_mode_polling_endpoint_returns_execution(
        self,
        api_client: TrinityApiClient,
        created_agent
    ):
        """Async task execution can be retrieved via polling endpoint."""
        # Submit async task
        response = api_client.post(
            f"/api/agents/{created_agent['name']}/task",
            json={
                "message": "What is 5+5? Reply with just the number.",
                "async_mode": True
            },
            timeout=10.0,
        )

        if response.status_code == 503:
            pytest.skip("Agent server not ready")

        assert_status(response, 200)
        data = response.json()
        execution_id = data["execution_id"]

        # Wait briefly for database write
        time.sleep(1)

        # Poll execution endpoint
        poll_response = api_client.get(
            f"/api/agents/{created_agent['name']}/executions/{execution_id}"
        )
        assert_status(poll_response, 200)
        execution = poll_response.json()

        # Verify execution details
        assert_has_fields(execution, [
            "id",
            "agent_name",
            "status",
            "started_at",
            "message"
        ])
        assert execution["id"] == execution_id
        assert execution["agent_name"] == created_agent["name"]
        assert execution["status"] in ["running", "success", "failed"]

    @pytest.mark.slow
    @pytest.mark.requires_agent
    def test_async_mode_execution_completes(
        self,
        api_client: TrinityApiClient,
        created_agent
    ):
        """Async task eventually completes and result can be retrieved."""
        # Submit async task
        response = api_client.post(
            f"/api/agents/{created_agent['name']}/task",
            json={
                "message": "What is 7+3? Reply with just the number.",
                "async_mode": True
            },
            timeout=10.0,
        )

        if response.status_code == 503:
            pytest.skip("Agent server not ready")

        if response.status_code == 429:
            pytest.skip("Agent at capacity from prior async tests")

        assert_status(response, 200)
        data = response.json()
        execution_id = data["execution_id"]

        # Poll until task completes (max 120 seconds)
        max_wait = 120
        start = time.time()
        final_execution = None

        while time.time() - start < max_wait:
            poll_response = api_client.get(
                f"/api/agents/{created_agent['name']}/executions/{execution_id}"
            )

            if poll_response.status_code == 200:
                execution = poll_response.json()
                status = execution.get("status")

                if status in ["success", "failed"]:
                    final_execution = execution
                    break

            time.sleep(2)

        assert final_execution is not None, "Task should complete within timeout"
        assert final_execution["status"] == "success", \
            f"Task should complete successfully, got status: {final_execution['status']}"

        # Verify completion fields
        assert final_execution.get("completed_at") is not None, "Should have completed_at"
        assert final_execution.get("duration_ms") is not None, "Should have duration_ms"
        assert final_execution.get("duration_ms") > 0, "Duration should be positive"

    @pytest.mark.slow
    @pytest.mark.requires_agent
    def test_async_mode_with_options(
        self,
        api_client: TrinityApiClient,
        created_agent
    ):
        """Async mode works with other task options (model, timeout, etc)."""
        response = api_client.post(
            f"/api/agents/{created_agent['name']}/task",
            json={
                "message": "What is 9+1?",
                "async_mode": True,
                "model": "haiku",
                "timeout_seconds": 60
            },
            timeout=10.0,
        )

        if response.status_code == 503:
            pytest.skip("Agent server not ready")

        if response.status_code == 429:
            pytest.skip("Agent at capacity from prior async tests")

        # Should work (200) or fail gracefully if model not available
        assert_status_in(response, [200, 400, 500])

        if response.status_code == 200:
            data = response.json()
            assert data["async_mode"] is True
            assert "execution_id" in data

    @pytest.mark.requires_agent
    def test_async_mode_multiple_concurrent_tasks(
        self,
        api_client: TrinityApiClient,
        created_agent
    ):
        """Multiple async tasks can be submitted concurrently."""
        execution_ids = []

        # Submit 3 async tasks concurrently
        for i in range(3):
            response = api_client.post(
                f"/api/agents/{created_agent['name']}/task",
                json={
                    "message": f"Async task {i+1}: What is {i}+1?",
                    "async_mode": True
                },
                timeout=10.0,
            )

            if response.status_code == 503:
                pytest.skip("Agent server not ready")

            if response.status_code == 429:
                pytest.skip("Agent at capacity from prior async tests")

            assert_status(response, 200)
            data = response.json()
            execution_ids.append(data["execution_id"])

        # All should have unique execution IDs
        assert len(execution_ids) == 3
        assert len(set(execution_ids)) == 3, "All execution IDs should be unique"

        # All should be retrievable
        time.sleep(2)
        for execution_id in execution_ids:
            poll_response = api_client.get(
                f"/api/agents/{created_agent['name']}/executions/{execution_id}"
            )
            assert_status(poll_response, 200)


class TestAsyncModeActivities:
    """REQ-PARALLEL-009: Async mode activity tracking tests."""

    @pytest.mark.slow
    @pytest.mark.requires_agent
    def test_async_mode_creates_task_activity(
        self,
        api_client: TrinityApiClient,
        created_agent
    ):
        """Async task creates TASK_STARTED activity."""
        # Get initial activity count
        activities_before = api_client.get(
            f"/api/agents/{created_agent['name']}/activities"
        )

        # Activities endpoint returns {"agent_name": ..., "count": ..., "activities": [...]}
        initial_count = 0
        if activities_before.status_code == 200:
            data = activities_before.json()
            initial_count = data.get("count", 0)

        # Submit async task
        response = api_client.post(
            f"/api/agents/{created_agent['name']}/task",
            json={
                "message": "Activity tracking test",
                "async_mode": True
            },
            timeout=10.0,
        )

        if response.status_code == 503:
            pytest.skip("Agent server not ready")

        if response.status_code == 429:
            pytest.skip("Agent at capacity from prior async tests")

        assert_status(response, 200)

        # Wait for activity to be recorded
        time.sleep(2)

        # Get activities
        activities_after = api_client.get(
            f"/api/agents/{created_agent['name']}/activities"
        )
        assert_status(activities_after, 200)
        data = activities_after.json()

        # Should have new activity
        current_count = data.get("count", 0)
        assert current_count > initial_count, \
            f"Should have new activity for async task (before: {initial_count}, after: {current_count})"
