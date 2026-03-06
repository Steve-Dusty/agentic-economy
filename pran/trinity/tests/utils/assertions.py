"""
Custom test assertions for Trinity API tests.
"""

from typing import Any, Dict, List, Optional
import httpx


def assert_status(response: httpx.Response, expected: int, message: str = ""):
    """Assert response has expected status code."""
    actual = response.status_code
    if actual != expected:
        body = response.text[:500] if response.text else ""
        raise AssertionError(
            f"Expected status {expected}, got {actual}. {message}\n"
            f"Response body: {body}"
        )


def assert_status_in(response: httpx.Response, expected: List[int], message: str = ""):
    """Assert response status is one of expected codes."""
    actual = response.status_code
    if actual not in expected:
        body = response.text[:500] if response.text else ""
        raise AssertionError(
            f"Expected status in {expected}, got {actual}. {message}\n"
            f"Response body: {body}"
        )


def assert_json_response(response: httpx.Response) -> Dict[str, Any]:
    """Assert response is valid JSON and return parsed data."""
    assert "application/json" in response.headers.get("content-type", ""), \
        f"Expected JSON response, got {response.headers.get('content-type')}"
    try:
        return response.json()
    except Exception as e:
        raise AssertionError(f"Failed to parse JSON response: {e}")


def assert_has_fields(data: Dict[str, Any], fields: List[str], context: str = ""):
    """Assert dict has all required fields."""
    missing = [f for f in fields if f not in data]
    if missing:
        raise AssertionError(
            f"Missing required fields: {missing}. {context}\n"
            f"Available fields: {list(data.keys())}"
        )


def assert_agent_fields(agent: Dict[str, Any]):
    """Assert agent has all required fields."""
    required = ["name", "status"]
    assert_has_fields(agent, required, "Agent response")


def assert_agent_status(agent: Dict[str, Any], expected: str):
    """Assert agent has expected status."""
    actual = agent.get("status")
    if actual != expected:
        raise AssertionError(
            f"Expected agent status '{expected}', got '{actual}'"
        )


def assert_list_response(data: Any, item_type: str = "items") -> List[Any]:
    """Assert response is a list."""
    if not isinstance(data, list):
        raise AssertionError(
            f"Expected list of {item_type}, got {type(data).__name__}"
        )
    return data


def assert_not_empty(data: Any, context: str = ""):
    """Assert data is not empty."""
    if not data:
        raise AssertionError(f"Expected non-empty data. {context}")


def assert_contains_agent(agents: List[Dict], name: str) -> Dict[str, Any]:
    """Assert list contains agent with given name and return it."""
    for agent in agents:
        if agent.get("name") == name:
            return agent
    agent_names = [a.get("name") for a in agents]
    raise AssertionError(
        f"Agent '{name}' not found in list. Available: {agent_names}"
    )


def assert_not_contains_agent(agents: List[Dict], name: str):
    """Assert list does not contain agent with given name."""
    for agent in agents:
        if agent.get("name") == name:
            raise AssertionError(f"Agent '{name}' should not be in list")


def assert_error_response(response: httpx.Response, expected_status: int):
    """Assert response is an error with expected status."""
    assert_status(response, expected_status)
    data = assert_json_response(response)
    assert "detail" in data, f"Error response should have 'detail' field: {data}"
    return data


def assert_tree_structure(data: Dict[str, Any]):
    """Assert data is a valid file tree structure."""
    assert_has_fields(data, ["name", "type"])
    assert data["type"] in ["file", "directory"], \
        f"Invalid type: {data['type']}"
    if data["type"] == "file":
        assert_has_fields(data, ["size", "modified"])
    elif data["type"] == "directory":
        assert "children" in data, "Directory should have children field"


def assert_plan_fields(plan: Dict[str, Any]):
    """Assert plan has required fields."""
    required = ["id", "name", "status"]
    assert_has_fields(plan, required, "Plan response")


def assert_task_fields(task: Dict[str, Any]):
    """Assert task has required fields."""
    required = ["id", "name", "status"]
    assert_has_fields(task, required, "Task response")


def assert_credential_fields(cred: Dict[str, Any]):
    """
    DEPRECATED: Legacy credential assertion for old Redis-based system.
    CRED-002 uses file-based credentials. Kept for backward compatibility.
    """
    pass
