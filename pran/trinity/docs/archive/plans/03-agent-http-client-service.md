# Implementation Plan: Agent HTTP Client Service

**Priority**: HIGH
**Report Section**: 1.2 - Agent HTTP Communication Pattern + 1.3 - Agent Response Parsing
**Estimated Effort**: Medium
**Impact**: High - Consolidates ~200 lines of HTTP client code, standardizes error handling

---

## Problem Statement

HTTP client code for communicating with agent containers is duplicated across multiple files with slight variations:

### Duplicate 1: Chat Execution (scheduler_service.py - 2 places)

```python
# Lines 265-271 and 478-484 (nearly identical)
async with httpx.AsyncClient() as client:
    response = await client.post(
        f"http://agent-{schedule.agent_name}:8000/api/chat",
        json={"message": schedule.message, "stream": False},
        timeout=300.0
    )
```

### Duplicate 2: Context Stats (ops.py - lines 66-70)

```python
agent_url = f"http://agent-{agent_name}:8000/api/chat/session"
async with httpx.AsyncClient(timeout=5.0) as client:
    response = await client.get(agent_url)
```

### Duplicate 3: Trinity Injection (lifecycle.py - lines 52-58)

```python
async with httpx.AsyncClient(timeout=10.0) as client:
    response = await client.post(
        f"{agent_url}/api/trinity/inject",
        json=payload
    )
```

### Duplicate 4: Response Parsing (scheduler_service.py - 2 places)

```python
# Lines 279-311 and 491-522 (nearly identical)
session_data = result.get("session", {})
metadata = result.get("metadata", {})
execution_log = result.get("execution_log", [])

context_used = session_data.get("context_tokens") or metadata.get("input_tokens", 0)
context_max = session_data.get("context_window") or metadata.get("context_window", 200000)
cost = metadata.get("cost_usd") or session_data.get("total_cost_usd")
```

**Why this is a problem:**
1. Violates DRY - HTTP client setup repeated everywhere
2. Inconsistent timeout handling
3. Error handling varies by location
4. Response parsing logic duplicated
5. URL construction scattered across codebase

---

## Solution

Create a dedicated `AgentClient` service that encapsulates all agent HTTP communication.

---

## Implementation Steps

### Step 1: Create Agent Client Service

**File**: `src/backend/services/agent_client.py`

```python
"""
Agent HTTP Client Service.

Provides a clean interface for communicating with agent containers.
Centralizes URL construction, timeout handling, and error handling.
"""
import httpx
import json
import logging
from dataclasses import dataclass
from typing import Optional, Any, List, Dict
from pydantic import BaseModel

logger = logging.getLogger(__name__)


# ============================================================================
# Response Models
# ============================================================================

@dataclass
class AgentChatMetrics:
    """Observability data extracted from agent chat response."""
    context_used: int
    context_max: int
    context_percent: float
    cost_usd: Optional[float]
    tool_calls_json: Optional[str]
    execution_log_json: Optional[str]


@dataclass
class AgentChatResponse:
    """Parsed response from agent chat endpoint."""
    response_text: str
    metrics: AgentChatMetrics
    raw_response: Dict[str, Any]


@dataclass
class AgentSessionInfo:
    """Agent context/session information."""
    context_tokens: int
    context_window: int
    context_percent: float
    total_cost_usd: Optional[float] = None


class AgentClientError(Exception):
    """Base exception for agent client errors."""
    pass


class AgentNotReachableError(AgentClientError):
    """Agent container is not responding."""
    pass


class AgentRequestError(AgentClientError):
    """Agent returned an error response."""
    def __init__(self, message: str, status_code: int = None):
        super().__init__(message)
        self.status_code = status_code


# ============================================================================
# Agent Client
# ============================================================================

class AgentClient:
    """
    HTTP client for agent container communication.

    Centralizes:
    - URL construction
    - Timeout handling
    - Error handling
    - Response parsing
    """

    # Default timeouts
    CHAT_TIMEOUT = 300.0      # 5 minutes for chat
    SESSION_TIMEOUT = 5.0     # 5 seconds for session info
    INJECT_TIMEOUT = 10.0     # 10 seconds for Trinity injection
    DEFAULT_TIMEOUT = 30.0    # 30 seconds default

    def __init__(self, agent_name: str):
        """
        Initialize client for a specific agent.

        Args:
            agent_name: Name of the agent (without 'agent-' prefix)
        """
        self.agent_name = agent_name
        self.base_url = f"http://agent-{agent_name}:8000"

    # ========================================================================
    # Core HTTP Methods
    # ========================================================================

    async def _request(
        self,
        method: str,
        path: str,
        timeout: float = None,
        **kwargs
    ) -> httpx.Response:
        """
        Make an HTTP request to the agent.

        Args:
            method: HTTP method (GET, POST, etc.)
            path: URL path (e.g., "/api/chat")
            timeout: Request timeout in seconds
            **kwargs: Additional arguments for httpx request

        Returns:
            httpx.Response

        Raises:
            AgentNotReachableError: If connection fails
            AgentRequestError: If request fails with error status
        """
        url = f"{self.base_url}{path}"
        timeout = timeout or self.DEFAULT_TIMEOUT

        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.request(method, url, **kwargs)
                return response
        except httpx.ConnectError as e:
            raise AgentNotReachableError(
                f"Cannot connect to agent {self.agent_name}: {e}"
            )
        except httpx.TimeoutException as e:
            raise AgentNotReachableError(
                f"Request to agent {self.agent_name} timed out after {timeout}s"
            )

    async def get(self, path: str, timeout: float = None, **kwargs) -> httpx.Response:
        """Make a GET request to the agent."""
        return await self._request("GET", path, timeout, **kwargs)

    async def post(self, path: str, timeout: float = None, **kwargs) -> httpx.Response:
        """Make a POST request to the agent."""
        return await self._request("POST", path, timeout, **kwargs)

    # ========================================================================
    # Chat Operations
    # ========================================================================

    async def chat(
        self,
        message: str,
        stream: bool = False,
        timeout: float = None
    ) -> AgentChatResponse:
        """
        Send a chat message to the agent.

        Args:
            message: Message to send
            stream: Whether to stream the response
            timeout: Request timeout (default: 5 minutes)

        Returns:
            AgentChatResponse with parsed metrics
        """
        timeout = timeout or self.CHAT_TIMEOUT

        response = await self.post(
            "/api/chat",
            json={"message": message, "stream": stream},
            timeout=timeout
        )
        response.raise_for_status()

        result = response.json()
        return self._parse_chat_response(result)

    def _parse_chat_response(self, result: Dict[str, Any]) -> AgentChatResponse:
        """
        Parse agent chat response into structured data.

        Extracts:
        - Response text (truncated if > 10000 chars)
        - Context usage (tokens, window, percentage)
        - Cost
        - Tool calls / execution log
        """
        # Extract response text
        response_text = result.get("response", str(result))
        if len(response_text) > 10000:
            response_text = response_text[:10000] + "... (truncated)"

        # Extract observability data
        session_data = result.get("session", {})
        metadata = result.get("metadata", {})
        execution_log = result.get("execution_log")

        # Context usage
        # NOTE: cache_creation_tokens and cache_read_tokens are SUBSETS of input_tokens
        # for billing purposes, NOT additional tokens. Do NOT sum them.
        context_used = session_data.get("context_tokens") or metadata.get("input_tokens", 0)
        context_max = session_data.get("context_window") or metadata.get("context_window", 200000)
        context_percent = round(context_used / max(context_max, 1) * 100, 1)

        # Cost
        cost = metadata.get("cost_usd") or session_data.get("total_cost_usd")

        # Tool calls / execution log
        tool_calls_json = None
        execution_log_json = None
        if execution_log is not None:
            execution_log_json = json.dumps(execution_log)
            tool_calls_json = execution_log_json  # Backwards compatibility

        metrics = AgentChatMetrics(
            context_used=context_used,
            context_max=context_max,
            context_percent=context_percent,
            cost_usd=cost,
            tool_calls_json=tool_calls_json,
            execution_log_json=execution_log_json
        )

        return AgentChatResponse(
            response_text=response_text,
            metrics=metrics,
            raw_response=result
        )

    # ========================================================================
    # Session / Context Operations
    # ========================================================================

    async def get_session(self, timeout: float = None) -> Optional[AgentSessionInfo]:
        """
        Get current session/context information.

        Returns:
            AgentSessionInfo or None if request fails
        """
        timeout = timeout or self.SESSION_TIMEOUT

        try:
            response = await self.get("/api/chat/session", timeout=timeout)
            if response.status_code == 200:
                session = response.json()
                context_tokens = session.get("context_tokens", 0)
                context_window = session.get("context_window", 200000)
                return AgentSessionInfo(
                    context_tokens=context_tokens,
                    context_window=context_window,
                    context_percent=round(
                        context_tokens / max(context_window, 1) * 100, 1
                    ),
                    total_cost_usd=session.get("total_cost_usd")
                )
        except AgentClientError:
            pass
        return None

    # ========================================================================
    # Trinity Injection
    # ========================================================================

    async def inject_trinity_prompt(
        self,
        custom_prompt: Optional[str] = None,
        force: bool = False,
        timeout: float = None,
        max_retries: int = 3,
        retry_delay: float = 2.0
    ) -> Dict[str, Any]:
        """
        Inject Trinity meta-prompt into the agent.

        Args:
            custom_prompt: Optional custom prompt to inject
            force: Force re-injection even if already done
            timeout: Request timeout
            max_retries: Number of retry attempts
            retry_delay: Delay between retries in seconds

        Returns:
            Injection result dict
        """
        import asyncio

        timeout = timeout or self.INJECT_TIMEOUT
        payload = {"force": force}
        if custom_prompt:
            payload["custom_prompt"] = custom_prompt

        for attempt in range(max_retries):
            try:
                response = await self.post(
                    "/api/trinity/inject",
                    json=payload,
                    timeout=timeout
                )

                if response.status_code == 200:
                    result = response.json()
                    logger.info(
                        f"Trinity injection successful for {self.agent_name}: "
                        f"{result.get('status')}"
                    )
                    return result
                else:
                    logger.warning(
                        f"Trinity injection returned {response.status_code}: "
                        f"{response.text}"
                    )
                    return {"status": "error", "error": f"HTTP {response.status_code}"}

            except AgentNotReachableError:
                if attempt < max_retries - 1:
                    logger.info(
                        f"Agent {self.agent_name} not ready yet "
                        f"(attempt {attempt + 1}/{max_retries}), retrying..."
                    )
                    await asyncio.sleep(retry_delay)
                else:
                    logger.warning(
                        f"Could not connect to agent {self.agent_name} "
                        f"after {max_retries} attempts"
                    )
                    return {"status": "error", "error": "Agent not reachable after retries"}

            except Exception as e:
                logger.error(f"Trinity injection error for {self.agent_name}: {e}")
                return {"status": "error", "error": str(e)}

        return {"status": "error", "error": "Max retries exceeded"}

    # ========================================================================
    # Health Check
    # ========================================================================

    async def health_check(self, timeout: float = 5.0) -> bool:
        """
        Check if agent is healthy and responding.

        Returns:
            True if agent responds to health check
        """
        try:
            response = await self.get("/api/health", timeout=timeout)
            return response.status_code == 200
        except AgentClientError:
            return False


# ============================================================================
# Factory Function
# ============================================================================

def get_agent_client(agent_name: str) -> AgentClient:
    """
    Factory function to create an AgentClient.

    Args:
        agent_name: Name of the agent

    Returns:
        AgentClient instance
    """
    return AgentClient(agent_name)
```

### Step 2: Update scheduler_service.py

**Before** (duplicated in 2 places):

```python
async with httpx.AsyncClient() as client:
    response = await client.post(
        f"http://agent-{schedule.agent_name}:8000/api/chat",
        json={"message": schedule.message, "stream": False},
        timeout=300.0
    )
    response.raise_for_status()
    result = response.json()

# ... 30+ lines of response parsing
```

**After**:

```python
from services.agent_client import get_agent_client, AgentClientError, AgentNotReachableError

try:
    client = get_agent_client(schedule.agent_name)
    chat_response = await client.chat(schedule.message, stream=False)

    # All parsing done - use structured data
    db.update_execution_status(
        execution_id=execution.id,
        status="success",
        response=chat_response.response_text,
        context_used=chat_response.metrics.context_used,
        context_max=chat_response.metrics.context_max,
        cost=chat_response.metrics.cost_usd,
        tool_calls=chat_response.metrics.tool_calls_json,
        execution_log=chat_response.metrics.execution_log_json
    )
except AgentNotReachableError as e:
    error_msg = f"Agent not reachable: {e}"
except AgentClientError as e:
    error_msg = f"Agent error: {e}"
```

### Step 3: Update ops.py

**Before**:

```python
agent_url = f"http://agent-{agent_name}:8000/api/chat/session"
async with httpx.AsyncClient(timeout=5.0) as client:
    response = await client.get(agent_url)
    if response.status_code == 200:
        session = response.json()
        context_stats[agent_name] = {
            "context_tokens": session.get("context_tokens", 0),
            "context_window": session.get("context_window", 200000),
            "context_percent": round(...)
        }
```

**After**:

```python
from services.agent_client import get_agent_client

client = get_agent_client(agent_name)
session_info = await client.get_session()
if session_info:
    context_stats[agent_name] = {
        "context_tokens": session_info.context_tokens,
        "context_window": session_info.context_window,
        "context_percent": session_info.context_percent
    }
```

### Step 4: Update lifecycle.py

**Before**:

```python
async with httpx.AsyncClient(timeout=10.0) as client:
    response = await client.post(
        f"{agent_url}/api/trinity/inject",
        json=payload
    )
    # ... retry logic, error handling
```

**After**:

```python
from services.agent_client import get_agent_client

client = get_agent_client(agent_name)
result = await client.inject_trinity_prompt(
    custom_prompt=custom_prompt,
    max_retries=max_retries,
    retry_delay=retry_delay
)
```

---

## Files Changed

| File | Change |
|------|--------|
| `services/agent_client.py` | **NEW** - Centralized HTTP client |
| `services/scheduler_service.py` | Replace 2 chat blocks + parsing |
| `services/agent_service/lifecycle.py` | Replace inject_trinity_meta_prompt body |
| `routers/ops.py` | Replace session fetching |
| `routers/chat.py` | Consider using for agent chat forwarding |

---

## Testing

1. **Unit Tests**: `tests/test_agent_client.py`
   ```python
   @pytest.mark.asyncio
   async def test_parse_chat_response():
       client = AgentClient("test-agent")
       result = {
           "response": "Hello",
           "session": {"context_tokens": 1000, "context_window": 200000},
           "metadata": {"cost_usd": 0.05},
           "execution_log": [{"tool": "Read"}]
       }
       parsed = client._parse_chat_response(result)
       assert parsed.response_text == "Hello"
       assert parsed.metrics.context_used == 1000
       assert parsed.metrics.cost_usd == 0.05

   @pytest.mark.asyncio
   async def test_context_percent_calculation():
       client = AgentClient("test-agent")
       result = {"session": {"context_tokens": 50000, "context_window": 200000}}
       parsed = client._parse_chat_response(result)
       assert parsed.metrics.context_percent == 25.0
   ```

2. **Integration Tests**: Existing schedule tests should still pass

3. **Manual Testing**:
   - Scheduled execution works
   - Manual trigger works
   - Fleet status shows context stats
   - Trinity injection on agent start

---

## Benefits

1. **DRY**: Single implementation of agent communication
2. **Standardized Timeouts**: Consistent timeout values
3. **Structured Responses**: Type-safe response parsing
4. **Error Handling**: Centralized exception types
5. **Testability**: Easy to mock `AgentClient`
6. **~200 lines removed**: Less code to maintain
7. **Bug Prevention**: Response parsing logic in one place prevents context% bugs
