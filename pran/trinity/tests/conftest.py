"""
Shared pytest fixtures for Trinity API tests.

OPTIMIZATION NOTES (2025-12-09):
- Module-scoped agent fixture: Creates ONE agent per test FILE (not per test)
- Session-scoped shared agent: Single agent for tests that can share
- Tiered test execution: smoke < core < full

Configuration:
- TRINITY_API_URL: Backend URL (default: http://localhost:8000)
- TRINITY_TEST_USERNAME: Test user username (default: admin)
- TRINITY_TEST_PASSWORD: Test user password (default: trinity)
- TRINITY_MCP_API_KEY: MCP API key for authenticated tests
- TEST_AGENT_NAME: Pre-existing agent for agent-server tests
"""

# Skip test files that require backend context (can't be run from test suite)
collect_ignore = ["test_archive_security.py"]

import os
import pytest
import uuid
import time
from typing import Generator

from utils.api_client import TrinityApiClient, ApiConfig
from utils.cleanup import ResourceTracker, cleanup_test_agent


def pytest_configure(config):
    """Configure custom markers."""
    config.addinivalue_line("markers", "smoke: mark test as smoke test (fast, no agent)")
    config.addinivalue_line("markers", "slow: mark test as slow running (chat execution)")
    config.addinivalue_line("markers", "requires_agent: test requires a running agent")
    config.addinivalue_line("markers", "unit: unit tests that don't need backend")


def pytest_addoption(parser):
    """Add custom command line options."""
    parser.addoption(
        "--cleanup-only",
        action="store_true",
        default=False,
        help="Only run cleanup of test resources, no tests",
    )
    parser.addoption(
        "--skip-cleanup",
        action="store_true",
        default=False,
        help="Skip cleanup of test resources after tests",
    )
    parser.addoption(
        "--fast",
        action="store_true",
        default=False,
        help="Run only fast tests (no agent creation)",
    )


@pytest.fixture(scope="session")
def api_config() -> ApiConfig:
    """Load API configuration from environment."""
    return ApiConfig.from_env()


@pytest.fixture(scope="session")
def api_client(api_config: ApiConfig) -> Generator[TrinityApiClient, None, None]:
    """Create authenticated API client for the test session."""
    client = TrinityApiClient(api_config)
    try:
        client.authenticate()
        yield client
    finally:
        client.close()


@pytest.fixture(scope="session")
def unauthenticated_client(api_config: ApiConfig) -> Generator[TrinityApiClient, None, None]:
    """Create unauthenticated API client."""
    client = TrinityApiClient(api_config)
    try:
        yield client
    finally:
        client.close()


@pytest.fixture(scope="function")
def resource_tracker() -> ResourceTracker:
    """Track created resources for cleanup."""
    return ResourceTracker()


@pytest.fixture(scope="function")
def test_agent_name() -> str:
    """Generate unique test agent name."""
    return f"test-api-agent-{uuid.uuid4().hex[:8]}"


@pytest.fixture(scope="function")
def test_credential_name() -> str:
    """Generate unique test credential name."""
    return f"TEST_API_CRED_{uuid.uuid4().hex[:8].upper()}"


@pytest.fixture(scope="function")
def test_mcp_key_name() -> str:
    """Generate unique test MCP key name."""
    return f"test-api-key-{uuid.uuid4().hex[:8]}"


@pytest.fixture(scope="function")
def test_schedule_name() -> str:
    """Generate unique test schedule name."""
    return f"test-api-schedule-{uuid.uuid4().hex[:8]}"


# =============================================================================
# MODULE-SCOPED AGENT FIXTURE (OPTIMIZED)
# Creates ONE agent per test module instead of per test function
# =============================================================================

@pytest.fixture(scope="module")
def module_agent_name(request) -> str:
    """Generate unique agent name for the module."""
    # Use module name to create predictable but unique name
    module_name = request.module.__name__.replace("test_", "").replace("_", "-")[:20]
    return f"test-{module_name}-{uuid.uuid4().hex[:6]}"


@pytest.fixture(scope="module")
def created_agent(
    api_client: TrinityApiClient,
    module_agent_name: str,
    request
) -> Generator[dict, None, None]:
    """Create a test agent for the entire module.

    OPTIMIZED: scope="module" means ONE agent per test file.
    All tests in the same file share this agent.
    """
    agent_name = module_agent_name

    # Create the agent
    response = api_client.post(
        "/api/agents",
        json={"name": agent_name},
    )

    if response.status_code not in [200, 201]:
        pytest.skip(f"Failed to create test agent: {response.text}")

    agent = response.json()

    # Wait for agent to be ready (optimized wait - check status instead of fixed sleep)
    max_wait = 45
    start = time.time()
    agent_data = None
    while time.time() - start < max_wait:
        check = api_client.get(f"/api/agents/{agent_name}")
        if check.status_code == 200:
            agent_data = check.json()
            if agent_data.get("status") == "running":
                # Brief wait for agent server to fully initialize
                time.sleep(2)
                break
        time.sleep(1)

    if not agent_data or agent_data.get("status") != "running":
        cleanup_test_agent(api_client, agent_name)
        pytest.skip(f"Agent {agent_name} did not start within {max_wait}s")

    yield agent_data

    # Cleanup after ALL tests in module complete
    if not request.config.getoption("--skip-cleanup"):
        cleanup_test_agent(api_client, agent_name)


@pytest.fixture(scope="module")
def stopped_agent(
    api_client: TrinityApiClient,
    request
) -> Generator[dict, None, None]:
    """Create a stopped test agent for the module.

    Creates agent, waits for it to start, then stops it.
    OPTIMIZED: scope="module" - one stopped agent per test file.
    """
    agent_name = f"test-stopped-{uuid.uuid4().hex[:6]}"

    # Create the agent
    response = api_client.post(
        "/api/agents",
        json={"name": agent_name},
    )

    if response.status_code not in [200, 201]:
        pytest.skip(f"Failed to create test agent: {response.text}")

    # Wait for agent to start
    time.sleep(8)

    # Stop the agent
    api_client.post(f"/api/agents/{agent_name}/stop")
    time.sleep(2)

    # Get final state
    check = api_client.get(f"/api/agents/{agent_name}")
    if check.status_code == 200:
        yield check.json()
    else:
        pytest.skip("Failed to get agent state")

    # Cleanup
    if not request.config.getoption("--skip-cleanup"):
        cleanup_test_agent(api_client, agent_name)


# =============================================================================
# SESSION-SCOPED SHARED AGENT (MAXIMUM OPTIMIZATION)
# Single agent shared across ALL tests that don't modify agent state
# =============================================================================

@pytest.fixture(scope="session")
def shared_agent(api_client: TrinityApiClient, request) -> Generator[dict, None, None]:
    """Session-scoped shared agent for read-only tests.

    Use this for tests that:
    - Only READ data (logs, info, files)
    - Don't modify agent state
    - Don't need isolation

    DO NOT use for tests that:
    - Modify agent settings
    - Test agent creation/deletion
    - Need a clean agent state
    """
    agent_name = f"test-shared-session-{uuid.uuid4().hex[:6]}"

    # Create agent
    response = api_client.post(
        "/api/agents",
        json={"name": agent_name},
    )

    if response.status_code not in [200, 201]:
        pytest.skip(f"Failed to create shared test agent: {response.text}")

    # Wait for agent to be ready
    max_wait = 45
    start = time.time()
    agent_data = None
    while time.time() - start < max_wait:
        check = api_client.get(f"/api/agents/{agent_name}")
        if check.status_code == 200:
            agent_data = check.json()
            if agent_data.get("status") == "running":
                time.sleep(3)
                break
        time.sleep(1)

    if not agent_data or agent_data.get("status") != "running":
        cleanup_test_agent(api_client, agent_name)
        pytest.skip(f"Shared agent did not start within {max_wait}s")

    yield agent_data

    # Cleanup after entire test session
    if not request.config.getoption("--skip-cleanup"):
        cleanup_test_agent(api_client, agent_name)


# =============================================================================
# LEGACY FUNCTION-SCOPED FIXTURE (for tests that need isolation)
# =============================================================================

@pytest.fixture(scope="function")
def isolated_agent(
    api_client: TrinityApiClient,
    test_agent_name: str,
    resource_tracker,
    request
) -> Generator[dict, None, None]:
    """Create an ISOLATED test agent (cleaned up after each test).

    Use this ONLY for tests that:
    - Modify agent state destructively
    - Test agent deletion
    - Need guaranteed clean state

    For most tests, use `created_agent` (module-scoped) instead.
    """
    # Create the agent
    response = api_client.post(
        "/api/agents",
        json={"name": test_agent_name},
    )

    if response.status_code not in [200, 201]:
        pytest.skip(f"Failed to create test agent: {response.text}")

    agent = response.json()
    resource_tracker.track_agent(test_agent_name)

    # Wait for agent to be ready
    max_wait = 30
    start = time.time()
    while time.time() - start < max_wait:
        check = api_client.get(f"/api/agents/{test_agent_name}")
        if check.status_code == 200:
            agent_data = check.json()
            if agent_data.get("status") == "running":
                time.sleep(2)
                yield agent_data
                break
        time.sleep(1)
    else:
        cleanup_test_agent(api_client, test_agent_name)
        pytest.skip(f"Agent {test_agent_name} did not start within {max_wait}s")

    # Cleanup
    if not request.config.getoption("--skip-cleanup"):
        cleanup_test_agent(api_client, test_agent_name)


@pytest.fixture(scope="session")
def pre_existing_agent(api_config: ApiConfig) -> str:
    """Get pre-existing agent name from environment.

    Used for agent-server direct tests that need a running agent.
    """
    agent_name = api_config.test_agent_name
    if not agent_name:
        pytest.skip("TEST_AGENT_NAME environment variable not set")
    return agent_name


def pytest_collection_modifyitems(config, items):
    """Modify test collection based on markers and options."""
    # If cleanup-only mode, skip all tests
    if config.getoption("--cleanup-only"):
        skip_all = pytest.mark.skip(reason="cleanup-only mode")
        for item in items:
            item.add_marker(skip_all)

    # If fast mode, skip tests that require agents
    if config.getoption("--fast"):
        skip_agent = pytest.mark.skip(reason="--fast mode: skipping agent tests")
        for item in items:
            if "requires_agent" in [m.name for m in item.iter_markers()]:
                item.add_marker(skip_agent)
            # Also skip tests that use created_agent fixture
            if "created_agent" in item.fixturenames or "stopped_agent" in item.fixturenames:
                item.add_marker(skip_agent)


@pytest.fixture(autouse=True)
def cleanup_after_test(api_client: TrinityApiClient, resource_tracker: ResourceTracker, request):
    """Automatically clean up tracked resources after each test."""
    yield
    if not request.config.getoption("--skip-cleanup"):
        resource_tracker.cleanup(api_client)
