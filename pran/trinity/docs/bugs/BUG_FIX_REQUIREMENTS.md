# Bug Fix Implementation Requirements

**Date**: 2026-01-14
**Status**: Ready for Implementation
**Source**: Roadmap priority queue + Best Practices Audit 2026-01-13

---

## Overview

This document details the implementation requirements for fixing 6 bugs identified in the Trinity platform. Bugs are organized by priority (HIGH → LOW).

---

## Bug 1: Execution Queue Race Conditions

**Priority**: HIGH
**ID**: EQ-H1, EQ-H2
**Files**: `src/backend/services/execution_queue.py`

### Problem Description

The execution queue uses non-atomic Redis operations that can cause race conditions:

1. **submit() race condition (lines 128-136)**: Two concurrent requests can both see `current is None` and both acquire the slot, leading to duplicate executions.

```python
# Current problematic code:
current = self.redis.get(running_key)  # Check
if current is None:
    # RACE WINDOW: Another request can pass the check here
    self.redis.set(running_key, ...)   # Set
```

2. **complete() race condition (lines 176-184)**: Non-atomic pop from queue and set running key can cause lost queue entries or duplicate starts.

```python
# Current problematic code:
next_item = self.redis.rpop(queue_key)  # Pop
if next_item:
    self.redis.set(running_key, ...)    # Set - not atomic!
```

### Root Cause

Redis GET-then-SET and RPOP-then-SET are separate commands with a race window between them.

### Impact

- Two users could trigger the same agent simultaneously
- Queue entries could be lost or processed twice
- Platform-level concurrency guarantee is violated

### Implementation Requirements

#### 1.1 Fix submit() with SET NX EX

Replace the check-and-set pattern with atomic `SET key value NX EX ttl`:

```python
async def submit(self, execution: Execution, wait_if_busy: bool = True) -> tuple[str, Execution]:
    running_key = self._running_key(execution.agent_name)
    queue_key = self._queue_key(execution.agent_name)

    # Prepare execution for running state
    execution.status = ExecutionStatus.RUNNING
    execution.started_at = datetime.utcnow()
    serialized = self._serialize_execution(execution)

    # Atomic acquire: SET key value NX EX ttl
    # Returns True if key was set (we acquired), False if key exists (busy)
    acquired = self.redis.set(
        running_key,
        serialized,
        nx=True,  # Only set if Not eXists
        ex=EXECUTION_TTL
    )

    if acquired:
        logger.info(f"[Queue] Agent '{execution.agent_name}' execution started: {execution.id}")
        return ("running", execution)

    # Agent is busy - either queue or reject
    if not wait_if_busy:
        current = self.redis.get(running_key)
        current_exec = self._deserialize_execution(current) if current else None
        raise AgentBusyError(execution.agent_name, current_exec)

    # Reset execution state for queuing
    execution.status = ExecutionStatus.QUEUED
    execution.started_at = None

    # Check queue length and add (queue operations are separate concern)
    queue_len = self.redis.llen(queue_key)
    if queue_len >= MAX_QUEUE_SIZE:
        raise QueueFullError(execution.agent_name, queue_len)

    self.redis.lpush(queue_key, self._serialize_execution(execution))
    return (f"queued:{queue_len + 1}", execution)
```

#### 1.2 Fix complete() with Lua Script

Use a Lua script for atomic pop-and-set:

```python
# Add Lua script at class level
COMPLETE_SCRIPT = """
local running_key = KEYS[1]
local queue_key = KEYS[2]
local ttl = ARGV[1]

-- Pop next from queue
local next_item = redis.call('RPOP', queue_key)

if next_item then
    -- Atomically set as running
    redis.call('SET', running_key, next_item, 'EX', ttl)
    return next_item
else
    -- No more items, clear running state
    redis.call('DEL', running_key)
    return nil
end
"""

class ExecutionQueue:
    def __init__(self, redis_url: str = "redis://redis:6379"):
        self.redis = redis.from_url(redis_url, decode_responses=True)
        # Register Lua script
        self._complete_script = self.redis.register_script(COMPLETE_SCRIPT)
        # ... rest of init

    async def complete(self, agent_name: str, success: bool = True) -> Optional[Execution]:
        running_key = self._running_key(agent_name)
        queue_key = self._queue_key(agent_name)

        # Log completed execution
        completed = self.redis.get(running_key)
        if completed:
            completed_exec = self._deserialize_execution(completed)
            status = "completed" if success else "failed"
            logger.info(f"[Queue] Agent '{agent_name}' execution {status}: {completed_exec.id}")

        # Atomic: pop next and set as running (or clear if empty)
        next_item = self._complete_script(
            keys=[running_key, queue_key],
            args=[EXECUTION_TTL]
        )

        if next_item:
            next_exec = self._deserialize_execution(next_item)
            # Update status (already set in Redis by Lua)
            next_exec.status = ExecutionStatus.RUNNING
            next_exec.started_at = datetime.utcnow()
            logger.info(f"[Queue] Agent '{agent_name}' starting next: {next_exec.id}")
            return next_exec

        logger.info(f"[Queue] Agent '{agent_name}' queue empty, now idle")
        return None
```

#### 1.3 Additional Fix: Replace KEYS with SCAN (EQ-M1)

```python
async def get_all_busy_agents(self) -> List[str]:
    """Get list of all agents currently executing."""
    pattern = f"{self.running_prefix}*"
    agents = []
    cursor = 0
    while True:
        cursor, keys = self.redis.scan(cursor, match=pattern, count=100)
        agents.extend(key.replace(self.running_prefix, "") for key in keys)
        if cursor == 0:
            break
    return agents
```

### Testing Requirements

1. **Unit test**: Mock Redis and verify atomic operations are called
2. **Integration test**: Concurrent submit requests (use threading/asyncio)
3. **Load test**: 10 concurrent requests to same agent should result in 1 running + up to 3 queued

### Files to Modify

- `src/backend/services/execution_queue.py`

---

## Bug 2: Missing Auth on Lifecycle Endpoints

**Priority**: HIGH
**ID**: AL-H1, AL-H2
**Files**: `src/backend/routers/agents.py`

### Problem Description

Two endpoints accept `agent_name` as a string parameter but don't verify the user has access:

1. **start_agent_endpoint (lines 315-339)**: Any authenticated user can start any agent
2. **get_agent_logs_endpoint (lines 367-384)**: Any authenticated user can view any agent's logs

### Current Code

```python
@router.post("/{agent_name}/start")
async def start_agent_endpoint(agent_name: str, request: Request, current_user: User = Depends(get_current_user)):
    """Start an agent."""
    # NO ACCESS CHECK - proceeds directly to start
    result = await start_agent_internal(agent_name)
    ...

@router.get("/{agent_name}/logs")
async def get_agent_logs_endpoint(
    agent_name: str,
    request: Request,
    tail: int = 100,
    current_user: User = Depends(get_current_user)
):
    """Get agent container logs."""
    # NO ACCESS CHECK - proceeds directly to get logs
    container = get_agent_container(agent_name)
    ...
```

### Root Cause

These endpoints were added without following the `AuthorizedAgentByName` pattern used elsewhere.

### Impact

- Information disclosure: Users can view logs of agents they don't own
- Unauthorized actions: Users can start/stop agents they don't have access to

### Implementation Requirements

#### 2.1 Option A: Use AuthorizedAgentByName Dependency (Recommended)

Change parameter type from `str` to `AuthorizedAgentByName`:

```python
@router.post("/{agent_name}/start")
async def start_agent_endpoint(
    agent_name: AuthorizedAgentByName,  # Changed from str
    request: Request,
    current_user: CurrentUser  # Use CurrentUser for consistency
):
    """Start an agent."""
    try:
        result = await start_agent_internal(agent_name)
        ...

@router.get("/{agent_name}/logs")
async def get_agent_logs_endpoint(
    agent_name: AuthorizedAgentByName,  # Changed from str
    request: Request,
    tail: int = 100,
    current_user: CurrentUser  # Use CurrentUser for consistency
):
    """Get agent container logs."""
    container = get_agent_container(agent_name)
    ...
```

#### 2.2 Option B: Explicit Access Check

Add explicit access check (if AuthorizedAgentByName can't be used):

```python
@router.post("/{agent_name}/start")
async def start_agent_endpoint(agent_name: str, request: Request, current_user: User = Depends(get_current_user)):
    """Start an agent."""
    # Add access check
    if not db.can_user_access_agent(current_user.username, agent_name):
        raise HTTPException(status_code=403, detail="Access denied")

    result = await start_agent_internal(agent_name)
    ...
```

#### 2.3 Also Check stop_agent_endpoint

The stop endpoint (lines 342-360) has the same issue:

```python
@router.post("/{agent_name}/stop")
async def stop_agent_endpoint(
    agent_name: AuthorizedAgentByName,  # Changed from str
    request: Request,
    current_user: CurrentUser
):
    ...
```

### Testing Requirements

1. **Auth test**: Verify 403 when user without access tries to start/stop/logs
2. **Owner test**: Verify owner can start/stop/logs
3. **Shared test**: Verify shared user can start/stop/logs
4. **Admin test**: Verify admin can start/stop/logs for any agent

### Files to Modify

- `src/backend/routers/agents.py`

---

## Bug 3: Container Security Inconsistency

**Priority**: HIGH
**ID**: AL-H3
**Files**: `src/backend/services/agent_service/lifecycle.py`

### Problem Description

When `full_capabilities=True`, the container recreation code drops ALL security settings, leaving containers with Docker's permissive defaults.

### Current Code (lines 308-324)

```python
new_container = docker_client.containers.run(
    image,
    detach=True,
    name=f"agent-{agent_name}",
    ports={'22/tcp': ssh_port},
    volumes=volumes,
    environment=env_vars,
    labels=labels,
    security_opt=['apparmor:docker-default'] if not full_capabilities else [],  # DROPS ALL
    cap_drop=[] if full_capabilities else ['ALL'],  # DROPS NOTHING
    cap_add=[] if full_capabilities else ['NET_BIND_SERVICE', 'SETGID', 'SETUID', 'CHOWN', 'SYS_CHROOT', 'AUDIT_WRITE'],
    read_only=False,
    tmpfs={'/tmp': 'size=100m'} if full_capabilities else {'/tmp': 'noexec,nosuid,size=100m'},  # LESS RESTRICTIVE
    network='trinity-agent-network',
    mem_limit=memory,
    cpu_count=int(cpu)
)
```

### Root Cause

The ternary logic completely removes security settings when full_capabilities is True, rather than applying a different (but still safe) set.

### Impact

- Containers with full_capabilities have Docker default caps (including dangerous ones like SYS_ADMIN)
- /tmp has no noexec protection
- No AppArmor profile applied

### Implementation Requirements

#### 3.1 Apply Baseline Security Even with Full Capabilities

```python
# Define capability sets
RESTRICTED_CAP_ADD = ['NET_BIND_SERVICE', 'SETGID', 'SETUID', 'CHOWN', 'SYS_CHROOT', 'AUDIT_WRITE']
FULL_CAP_ADD = RESTRICTED_CAP_ADD + ['DAC_OVERRIDE', 'FOWNER', 'FSETID', 'KILL', 'MKNOD', 'NET_RAW', 'SYS_PTRACE']

# Dangerous capabilities that should NEVER be added
DANGEROUS_CAPS = ['SYS_ADMIN', 'NET_ADMIN', 'SYS_RAWIO', 'SYS_MODULE', 'SYS_BOOT']

new_container = docker_client.containers.run(
    image,
    detach=True,
    name=f"agent-{agent_name}",
    ports={'22/tcp': ssh_port},
    volumes=volumes,
    environment=env_vars,
    labels=labels,
    # Always apply AppArmor
    security_opt=['apparmor:docker-default'],
    # Always drop ALL, then add back what's needed
    cap_drop=['ALL'],
    cap_add=FULL_CAP_ADD if full_capabilities else RESTRICTED_CAP_ADD,
    read_only=False,
    # Always apply noexec,nosuid to /tmp for security
    tmpfs={'/tmp': 'noexec,nosuid,size=100m'},
    network='trinity-agent-network',
    mem_limit=memory,
    cpu_count=int(cpu)
)
```

#### 3.2 Document the Capability Sets

Add constants at module level with documentation:

```python
# Restricted mode capabilities - minimum for agent operation
RESTRICTED_CAPABILITIES = [
    'NET_BIND_SERVICE',  # Bind to ports < 1024
    'SETGID', 'SETUID',  # Change user/group (for su/sudo)
    'CHOWN',             # Change file ownership
    'SYS_CHROOT',        # Use chroot
    'AUDIT_WRITE',       # Write to audit log
]

# Full capabilities mode - adds package installation support
FULL_CAPABILITIES = RESTRICTED_CAPABILITIES + [
    'DAC_OVERRIDE',      # Bypass file permission checks
    'FOWNER',            # Bypass permission checks on file owner
    'FSETID',            # Don't clear setuid/setgid bits
    'KILL',              # Send signals to processes
    'MKNOD',             # Create special files
    'NET_RAW',           # Use raw sockets (ping, etc.)
    'SYS_PTRACE',        # Trace processes (debugging)
]

# These capabilities are NEVER granted
PROHIBITED_CAPABILITIES = [
    'SYS_ADMIN',         # Mount filesystems, configure network
    'NET_ADMIN',         # Network administration
    'SYS_RAWIO',         # Raw I/O access
    'SYS_MODULE',        # Load kernel modules
    'SYS_BOOT',          # Reboot system
]
```

### Testing Requirements

1. **Verify restricted mode**: Container should have only RESTRICTED_CAPABILITIES
2. **Verify full mode**: Container should have FULL_CAPABILITIES but NOT PROHIBITED_CAPABILITIES
3. **Verify tmpfs**: /tmp should always have noexec,nosuid
4. **Verify AppArmor**: Profile should always be applied

### Files to Modify

- `src/backend/services/agent_service/lifecycle.py`

---

## Bug 4: Executions 404 for Non-Existent Agent

**Priority**: LOW
**ID**: From roadmap
**Files**: `src/backend/routers/schedules.py`

### Problem Description

The `GET /api/agents/{name}/executions` endpoint returns `200 []` instead of `404` when the agent doesn't exist.

### Current Code (lines 309-316)

```python
@router.get("/{name}/executions", response_model=List[ExecutionResponse])
async def get_agent_executions(
    name: AuthorizedAgent,  # This validates access but not existence properly
    limit: int = 50
):
    """Get all executions for an agent across all schedules."""
    executions = db.get_agent_executions(name, limit=limit)
    return [ExecutionResponse(**e.model_dump()) for e in executions]
```

### Root Cause

The `AuthorizedAgent` dependency checks access but may not explicitly check agent existence before querying executions. If the agent doesn't exist, `db.get_agent_executions()` returns an empty list.

### Impact

- API inconsistency: Other endpoints return 404 for non-existent agents
- Confusing for clients: Can't distinguish "no executions" from "agent doesn't exist"

### Implementation Requirements

#### 4.1 Add Explicit Agent Existence Check

```python
@router.get("/{name}/executions", response_model=List[ExecutionResponse])
async def get_agent_executions(
    name: AuthorizedAgent,
    limit: int = 50
):
    """Get all executions for an agent across all schedules."""
    # Verify agent exists (container check)
    from services.docker_service import get_agent_container
    container = get_agent_container(name)
    if not container:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent not found"
        )

    executions = db.get_agent_executions(name, limit=limit)
    return [ExecutionResponse(**e.model_dump()) for e in executions]
```

#### 4.2 Alternative: Update AuthorizedAgent Dependency

Modify the `AuthorizedAgent` dependency to always verify container existence:

```python
# In dependencies.py
async def get_authorized_agent(
    name: str = Path(...),
    current_user: User = Depends(get_current_user)
) -> str:
    """Dependency that validates agent access and existence."""
    # Check container exists
    container = get_agent_container(name)
    if not container:
        raise HTTPException(status_code=404, detail="Agent not found")

    # Check access
    if not db.can_user_access_agent(current_user.username, name):
        raise HTTPException(status_code=403, detail="Access denied")

    return name
```

### Testing Requirements

1. **404 test**: Verify 404 for non-existent agent
2. **Empty test**: Verify 200 [] for existing agent with no executions
3. **Data test**: Verify 200 with data for agent with executions

### Files to Modify

- `src/backend/routers/schedules.py` OR
- `src/backend/dependencies.py`

---

## Bug 5: Test Client Headers Bug

**Priority**: LOW
**ID**: From roadmap
**Files**: `tests/utils/api_client.py`

### Problem Description

The roadmap mentions that `TrinityApiClient.post()` passes `headers` param twice.

### Current Code Analysis

After reviewing the code, this bug appears to have been **already fixed**. The current implementation properly merges headers:

```python
def post(
    self,
    path: str,
    json: Optional[Dict[str, Any]] = None,
    data: Optional[Dict[str, Any]] = None,
    auth: bool = True,
    timeout: Optional[float] = None,
    **kwargs
) -> httpx.Response:
    """Make authenticated POST request."""
    if auth:
        self._ensure_fresh_token()
    request_timeout = timeout if timeout else self._client.timeout
    # Merge any custom headers with default headers
    custom_headers = kwargs.pop('headers', {})
    headers = {**self._get_headers(auth), **custom_headers}
    return self._client.post(
        path,
        json=json,
        data=data,
        headers=headers,  # Only passed once
        timeout=request_timeout,
        **kwargs
    )
```

### Status

**RESOLVED** - The code shows proper header handling. The roadmap entry may be outdated.

### Recommendation

Remove from roadmap or verify if there's a different manifestation of this bug.

---

## Bug 6: Emergency Stop Test Timeout

**Priority**: LOW
**ID**: From roadmap
**Files**: `tests/test_ops.py`

### Problem Description

The emergency stop test (`test_emergency_stop_returns_structure`) times out when there are multiple agents running, even with a 180-second timeout.

### Current Code (lines 374-389)

```python
@pytest.mark.slow
@pytest.mark.timeout(180)
def test_emergency_stop_returns_structure(self, api_client: TrinityApiClient):
    """POST /api/ops/emergency-stop returns expected structure."""
    response = api_client.post("/api/ops/emergency-stop")
    assert_status_in(response, [200, 403])
    ...
```

### Root Cause

1. **Sequential stops**: The emergency stop endpoint likely stops agents one at a time
2. **Container stop timeout**: Docker container.stop() has a default 10-second timeout per container
3. **Many agents**: With N agents, worst case is N * 10 seconds = 100+ seconds easily

### Impact

- Test flakiness in CI
- Unclear test failures

### Implementation Requirements

#### 6.1 Option A: Increase Test Timeout

Simple fix for test stability:

```python
@pytest.mark.slow
@pytest.mark.timeout(300)  # 5 minutes
def test_emergency_stop_returns_structure(self, api_client: TrinityApiClient):
    ...
```

#### 6.2 Option B: Parallel Agent Stopping (Backend Fix)

Modify the emergency stop endpoint to stop agents in parallel:

```python
# In routers/ops.py or wherever emergency_stop is implemented
import asyncio
import concurrent.futures

async def emergency_stop():
    """Emergency stop - parallel agent stopping."""
    agents = get_all_agents()

    # Stop agents in parallel using thread pool (Docker SDK is sync)
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        futures = {
            executor.submit(stop_agent, agent.name): agent.name
            for agent in agents
        }

        results = {}
        for future in concurrent.futures.as_completed(futures, timeout=60):
            agent_name = futures[future]
            try:
                results[agent_name] = future.result()
            except Exception as e:
                results[agent_name] = {"error": str(e)}

    return results
```

#### 6.3 Option C: Test with Fewer Agents

Create a dedicated test fixture that ensures minimal agents:

```python
@pytest.fixture
def clean_test_environment(api_client):
    """Ensure minimal agents for emergency stop test."""
    # Stop all agents except the test agent before the test
    response = api_client.get("/api/ops/fleet/status")
    agents = response.json()["agents"]

    for agent in agents:
        if agent["status"] == "running" and "test-" not in agent["name"]:
            api_client.post(f"/api/agents/{agent['name']}/stop")

    yield
    # Cleanup handled by other fixtures

@pytest.mark.slow
@pytest.mark.timeout(180)
def test_emergency_stop_returns_structure(self, api_client, clean_test_environment):
    ...
```

### Recommendation

Implement Option B (parallel stopping) as it improves the actual user experience, not just tests.

### Files to Modify

- `tests/test_ops.py` (for timeout increase)
- `src/backend/routers/ops.py` (for parallel stopping)

---

## Implementation Order

Recommended order based on priority and dependencies:

1. **Bug 2: Missing Auth** - Quick fix, high security impact
2. **Bug 1: Race Conditions** - High priority, requires careful testing
3. **Bug 3: Security Inconsistency** - High priority, straightforward change
4. **Bug 4: Executions 404** - Low priority, simple fix
5. **Bug 6: Emergency Stop** - Low priority, optional backend improvement
6. **Bug 5: Headers Bug** - Already fixed, verify and close

---

## Appendix: File References

| Bug | Primary File | Lines |
|-----|--------------|-------|
| 1 | `src/backend/services/execution_queue.py` | 128-136, 176-184, 246-251 |
| 2 | `src/backend/routers/agents.py` | 315-339, 342-360, 367-384 |
| 3 | `src/backend/services/agent_service/lifecycle.py` | 308-324 |
| 4 | `src/backend/routers/schedules.py` | 309-316 |
| 5 | `tests/utils/api_client.py` | N/A (already fixed) |
| 6 | `tests/test_ops.py` | 374-389 |

---

*Document generated by Claude Code analysis of Trinity codebase*
