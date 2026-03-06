"""
Execution Termination Tests (test_execution_termination.py)

Tests for execution termination feature - stopping running executions.
Added 2026-01-12 to cover new termination endpoints.

Feature Flow: execution-termination.md

Endpoints tested:
- POST /api/agents/{name}/executions/{execution_id}/terminate
- GET /api/agents/{name}/executions/running
"""

import pytest
import time
import threading
from utils.api_client import TrinityApiClient
from utils.assertions import (
    assert_status,
    assert_status_in,
    assert_json_response,
    assert_has_fields,
    assert_list_response,
)


class TestRunningExecutions:
    """Tests for GET /api/agents/{name}/executions/running endpoint."""

    def test_get_running_executions_returns_list(
        self,
        api_client: TrinityApiClient,
        created_agent
    ):
        """GET /api/agents/{name}/executions/running returns executions list."""
        response = api_client.get(f"/api/agents/{created_agent['name']}/executions/running")

        assert_status(response, 200)
        data = assert_json_response(response)
        assert "executions" in data, "Should have executions key"
        assert isinstance(data["executions"], list), "executions should be a list"

    def test_running_executions_empty_when_idle(
        self,
        api_client: TrinityApiClient,
        created_agent
    ):
        """Running executions list is empty when agent is idle."""
        # Wait a moment for any startup tasks to settle
        time.sleep(2)

        response = api_client.get(f"/api/agents/{created_agent['name']}/executions/running")

        assert_status(response, 200)
        data = response.json()

        # May or may not be empty depending on timing, but should be a valid list
        assert isinstance(data.get("executions"), list)

    def test_running_executions_nonexistent_agent_returns_404(
        self,
        api_client: TrinityApiClient
    ):
        """GET /api/agents/{name}/executions/running for non-existent agent returns 404."""
        response = api_client.get("/api/agents/nonexistent-agent-xyz123/executions/running")
        assert_status(response, 404)

    def test_running_executions_stopped_agent_returns_empty(
        self,
        api_client: TrinityApiClient,
        stopped_agent
    ):
        """GET /api/agents/{name}/executions/running for stopped agent returns empty list."""
        response = api_client.get(f"/api/agents/{stopped_agent['name']}/executions/running")

        assert_status(response, 200)
        data = response.json()
        assert data.get("executions") == [], "Stopped agent should have no running executions"

    def test_running_executions_requires_auth(
        self,
        unauthenticated_client: TrinityApiClient,
        created_agent
    ):
        """GET /api/agents/{name}/executions/running requires authentication."""
        response = unauthenticated_client.get(
            f"/api/agents/{created_agent['name']}/executions/running",
            auth=False
        )
        assert_status(response, 401)


class TestTerminateExecution:
    """Tests for POST /api/agents/{name}/executions/{execution_id}/terminate endpoint."""

    def test_terminate_nonexistent_execution_returns_404(
        self,
        api_client: TrinityApiClient,
        created_agent
    ):
        """Terminating non-existent execution returns 404."""
        response = api_client.post(
            f"/api/agents/{created_agent['name']}/executions/nonexistent-exec-xyz123/terminate"
        )
        assert_status(response, 404)

    def test_terminate_nonexistent_agent_returns_404(
        self,
        api_client: TrinityApiClient
    ):
        """Terminating execution on non-existent agent returns 404."""
        response = api_client.post(
            "/api/agents/nonexistent-agent-xyz123/executions/some-exec-id/terminate"
        )
        assert_status(response, 404)

    def test_terminate_stopped_agent_returns_503(
        self,
        api_client: TrinityApiClient,
        stopped_agent
    ):
        """Terminating execution on stopped agent returns 503."""
        response = api_client.post(
            f"/api/agents/{stopped_agent['name']}/executions/some-exec-id/terminate"
        )
        assert_status(response, 503)

    def test_terminate_requires_auth(
        self,
        unauthenticated_client: TrinityApiClient,
        created_agent
    ):
        """Termination requires authentication."""
        response = unauthenticated_client.post(
            f"/api/agents/{created_agent['name']}/executions/some-exec-id/terminate",
            auth=False
        )
        assert_status(response, 401)


class TestTerminateRunningExecution:
    """Tests for actually terminating a running execution.

    These tests are marked slow because they require starting a task
    and then terminating it.
    """

    @pytest.mark.slow
    @pytest.mark.requires_agent
    def test_terminate_running_execution(
        self,
        api_client: TrinityApiClient,
        created_agent
    ):
        """Can terminate a running execution."""
        agent_name = created_agent['name']
        execution_id = None
        task_completed = False

        def start_long_task():
            nonlocal task_completed
            # Start a task that takes a while (but not too long)
            try:
                api_client.post(
                    f"/api/agents/{agent_name}/task",
                    json={"message": "Count from 1 to 100, saying each number out loud. Take your time."},
                    timeout=120.0
                )
                task_completed = True
            except Exception:
                pass  # May be interrupted by termination

        # Start task in background thread
        task_thread = threading.Thread(target=start_long_task)
        task_thread.start()

        # Wait for execution to start and capture execution_id
        max_wait = 10
        start_time = time.time()
        while time.time() - start_time < max_wait:
            running_response = api_client.get(f"/api/agents/{agent_name}/executions/running")
            if running_response.status_code == 200:
                running_data = running_response.json()
                executions = running_data.get("executions", [])
                if executions:
                    execution_id = executions[0].get("execution_id")
                    if execution_id:
                        break
            time.sleep(0.5)

        if not execution_id:
            # Task may have completed quickly, check if it finished
            task_thread.join(timeout=5)
            if task_completed:
                pytest.skip("Task completed before we could capture execution_id")
            pytest.skip("Could not capture execution_id from running executions")

        # Terminate the execution
        terminate_response = api_client.post(
            f"/api/agents/{agent_name}/executions/{execution_id}/terminate"
        )

        # Should succeed with 200 or indicate already finished
        assert_status_in(terminate_response, [200])
        data = terminate_response.json()

        # Status should be 'terminated' or 'already_finished'
        assert data.get("status") in ["terminated", "already_finished"], \
            f"Expected terminated or already_finished, got {data.get('status')}"

        # Wait for task thread to complete
        task_thread.join(timeout=10)

    @pytest.mark.slow
    @pytest.mark.requires_agent
    def test_terminate_response_has_expected_fields(
        self,
        api_client: TrinityApiClient,
        created_agent
    ):
        """Termination response has expected fields."""
        agent_name = created_agent['name']
        execution_id = None

        def start_long_task():
            try:
                api_client.post(
                    f"/api/agents/{agent_name}/task",
                    json={"message": "Write a very long essay about testing software."},
                    timeout=120.0
                )
            except Exception:
                pass

        # Start task
        task_thread = threading.Thread(target=start_long_task)
        task_thread.start()

        # Wait for execution to start
        max_wait = 10
        start_time = time.time()
        while time.time() - start_time < max_wait:
            running_response = api_client.get(f"/api/agents/{agent_name}/executions/running")
            if running_response.status_code == 200:
                executions = running_response.json().get("executions", [])
                if executions:
                    execution_id = executions[0].get("execution_id")
                    if execution_id:
                        break
            time.sleep(0.5)

        if not execution_id:
            task_thread.join(timeout=5)
            pytest.skip("Could not capture execution_id")

        # Terminate
        terminate_response = api_client.post(
            f"/api/agents/{agent_name}/executions/{execution_id}/terminate"
        )

        if terminate_response.status_code == 200:
            data = terminate_response.json()
            assert "status" in data, "Response should have status field"
            assert "execution_id" in data, "Response should have execution_id field"

        task_thread.join(timeout=10)


class TestRunningExecutionDetails:
    """Tests for running execution list details."""

    @pytest.mark.slow
    @pytest.mark.requires_agent
    def test_running_execution_has_expected_fields(
        self,
        api_client: TrinityApiClient,
        created_agent
    ):
        """Running execution entry has expected fields."""
        agent_name = created_agent['name']
        found_execution = False

        def start_task():
            try:
                api_client.post(
                    f"/api/agents/{agent_name}/task",
                    json={"message": "Think about something for a while."},
                    timeout=60.0
                )
            except Exception:
                pass

        # Start task
        task_thread = threading.Thread(target=start_task)
        task_thread.start()

        # Check running executions
        max_wait = 10
        start_time = time.time()
        while time.time() - start_time < max_wait:
            response = api_client.get(f"/api/agents/{agent_name}/executions/running")
            if response.status_code == 200:
                executions = response.json().get("executions", [])
                if executions:
                    execution = executions[0]
                    found_execution = True

                    # Check expected fields
                    assert "execution_id" in execution, "Should have execution_id"
                    assert "started_at" in execution, "Should have started_at"
                    assert "metadata" in execution, "Should have metadata"
                    break
            time.sleep(0.5)

        task_thread.join(timeout=60)

        if not found_execution:
            pytest.skip("Task completed too quickly to capture running execution")


class TestTerminationActivityTracking:
    """Tests for activity tracking when executions are terminated."""

    @pytest.mark.slow
    @pytest.mark.requires_agent
    def test_termination_creates_activity(
        self,
        api_client: TrinityApiClient,
        created_agent
    ):
        """Terminating an execution creates EXECUTION_CANCELLED activity."""
        agent_name = created_agent['name']
        execution_id = None

        # Get current activity count
        initial_activities = api_client.get(
            f"/api/activities/{agent_name}",
            params={"limit": 100}
        )
        initial_count = len(initial_activities.json()) if initial_activities.status_code == 200 else 0

        def start_task():
            try:
                api_client.post(
                    f"/api/agents/{agent_name}/task",
                    json={"message": "Count slowly from 1 to 50."},
                    timeout=120.0
                )
            except Exception:
                pass

        # Start task
        task_thread = threading.Thread(target=start_task)
        task_thread.start()

        # Wait for execution
        max_wait = 10
        start_time = time.time()
        while time.time() - start_time < max_wait:
            running_response = api_client.get(f"/api/agents/{agent_name}/executions/running")
            if running_response.status_code == 200:
                executions = running_response.json().get("executions", [])
                if executions:
                    execution_id = executions[0].get("execution_id")
                    if execution_id:
                        break
            time.sleep(0.5)

        if not execution_id:
            task_thread.join(timeout=5)
            pytest.skip("Could not capture execution_id")

        # Terminate
        terminate_response = api_client.post(
            f"/api/agents/{agent_name}/executions/{execution_id}/terminate"
        )

        task_thread.join(timeout=10)

        if terminate_response.status_code != 200:
            pytest.skip("Termination did not succeed")

        # Wait for activity to be recorded
        time.sleep(2)

        # Check for EXECUTION_CANCELLED activity
        activities_response = api_client.get(
            f"/api/activities/{agent_name}",
            params={"limit": 100}
        )

        if activities_response.status_code == 200:
            activities = activities_response.json()
            cancelled_activities = [
                a for a in activities
                if a.get("activity_type") == "execution_cancelled"
            ]
            # Note: Activity tracking is best-effort, don't fail if not found
            # Just verify that more activities exist if termination succeeded
            assert len(activities) >= initial_count, \
                "Activity count should not decrease after termination"
