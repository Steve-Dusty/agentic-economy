"""
Tests for the scheduler's agent client.
"""

# Path setup must happen before scheduler imports
import sys
from pathlib import Path
_this_file = Path(__file__).resolve()
_src_path = str(_this_file.parent.parent.parent / 'src')
if _src_path not in sys.path:
    sys.path.insert(0, _src_path)
import os

from unittest.mock import AsyncMock, MagicMock, patch
import pytest
import httpx

from scheduler.agent_client import (
    AgentClient,
    AgentNotReachableError,
    AgentRequestError,
    get_agent_client
)
from scheduler.models import AgentTaskResponse


class TestAgentClient:
    """Tests for AgentClient."""

    def test_initialization(self):
        """Test client initialization."""
        client = AgentClient("test-agent")

        assert client.agent_name == "test-agent"
        assert client.base_url == "http://agent-test-agent:8000"

    def test_factory_function(self):
        """Test the factory function."""
        client = get_agent_client("my-agent")

        assert isinstance(client, AgentClient)
        assert client.agent_name == "my-agent"

    @pytest.mark.asyncio
    async def test_task_success(self):
        """Test successful task execution."""
        client = AgentClient("test-agent")

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "response": "Task completed successfully",
            "metadata": {
                "input_tokens": 1500,
                "context_window": 200000,
                "cost_usd": 0.05
            },
            "execution_log": [{"type": "text", "content": "Hello"}]
        }

        with patch.object(client, '_request', return_value=mock_response):
            response = await client.task("Run the test")

        assert isinstance(response, AgentTaskResponse)
        assert response.response_text == "Task completed successfully"
        assert response.metrics.context_used == 1500
        assert response.metrics.cost_usd == 0.05

    @pytest.mark.asyncio
    async def test_task_with_execution_id(self):
        """Test task execution with execution ID."""
        client = AgentClient("test-agent")

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "response": "Done",
            "metadata": {},
            "execution_log": []
        }

        with patch.object(client, '_request', return_value=mock_response) as mock_request:
            await client.task("Run test", execution_id="exec-123")

        # Verify execution_id was passed in payload
        call_kwargs = mock_request.call_args[1]
        assert call_kwargs["json"]["execution_id"] == "exec-123"

    @pytest.mark.asyncio
    async def test_task_error_response(self):
        """Test task with error response."""
        client = AgentClient("test-agent")

        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.json.return_value = {"detail": "Internal server error"}

        with patch.object(client, '_request', return_value=mock_response):
            with pytest.raises(AgentRequestError) as exc_info:
                await client.task("Run test")

        assert exc_info.value.status_code == 500
        assert "Internal server error" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_task_connection_error(self):
        """Test task when agent is not reachable."""
        client = AgentClient("test-agent")

        with patch.object(client, '_request', side_effect=AgentNotReachableError("Connection refused")):
            with pytest.raises(AgentNotReachableError):
                await client.task("Run test")

    @pytest.mark.asyncio
    async def test_health_check_success(self):
        """Test successful health check."""
        client = AgentClient("test-agent")

        mock_response = MagicMock()
        mock_response.status_code = 200

        with patch.object(client, '_request', return_value=mock_response):
            result = await client.health_check()

        assert result is True

    @pytest.mark.asyncio
    async def test_health_check_failure(self):
        """Test failed health check."""
        client = AgentClient("test-agent")

        with patch.object(client, '_request', side_effect=AgentNotReachableError("Timeout")):
            result = await client.health_check()

        assert result is False

    def test_parse_task_response_truncation(self):
        """Test that long responses are truncated."""
        client = AgentClient("test-agent")

        long_response = "x" * 15000
        result = {
            "response": long_response,
            "metadata": {},
            "execution_log": []
        }

        parsed = client._parse_task_response(result)

        assert len(parsed.response_text) < len(long_response)
        assert "truncated" in parsed.response_text

    def test_parse_task_response_with_execution_log(self):
        """Test parsing response with execution log."""
        client = AgentClient("test-agent")

        result = {
            "response": "Done",
            "metadata": {
                "input_tokens": 1000,
                "context_window": 200000,
                "cost_usd": 0.03
            },
            "execution_log": [
                {"type": "tool_use", "name": "Read"},
                {"type": "text", "content": "Found"}
            ]
        }

        parsed = client._parse_task_response(result)

        assert parsed.metrics.execution_log_json is not None
        assert parsed.metrics.tool_calls_json is not None

    def test_extract_error_detail_json(self):
        """Test extracting error detail from JSON response."""
        client = AgentClient("test-agent")

        mock_response = MagicMock()
        mock_response.json.return_value = {"detail": "Specific error message"}

        error = client._extract_error_detail(mock_response)
        assert error == "Specific error message"

    def test_extract_error_detail_text(self):
        """Test extracting error detail from text response."""
        client = AgentClient("test-agent")

        mock_response = MagicMock()
        mock_response.json.side_effect = Exception("Not JSON")
        mock_response.text = "Plain text error"

        error = client._extract_error_detail(mock_response)
        assert error == "Plain text error"

    def test_extract_error_detail_fallback(self):
        """Test error detail fallback to status code."""
        client = AgentClient("test-agent")

        mock_response = MagicMock()
        mock_response.json.side_effect = Exception("Not JSON")
        mock_response.text = ""
        mock_response.status_code = 503

        error = client._extract_error_detail(mock_response)
        assert "503" in error
