# OWASP Agentic Security - Implementation Plan

> **Created**: 2025-12-23
> **Based On**: OWASP Top 10 for Agentic Applications 2026
> **Scope**: On-premises deployment priorities
> **Source**: `docs/security/OWASP_AGENTIC_COMPLIANCE_REPORT.md`

---

## Executive Summary

This plan addresses **8 security improvements** from the OWASP Agentic Compliance Report, prioritized for on-premises deployment. Items are organized by implementation effort and operational value.

### What We're Implementing

| Phase | Items | Effort | Timeline |
|-------|-------|--------|----------|
| **Phase 1** | Permission enforcement, System prompt restriction | Low | 1 day |
| **Phase 2** | Circuit breaker, Audit reliability | Medium | 2-3 days |
| **Phase 3** | Automatic emergency triggers | Medium-High | 3-4 days |
| **Phase 4** | Tool allowlist, Credential scoping, Vector provenance | Medium | Optional |

### What We're NOT Implementing (On-Prem Deprioritized)

- mTLS between agents (trusted network)
- Message signing/HMAC (trusted network)
- Network isolation between agents (single org)
- Prompt injection detection (insider threat only)
- Template signing (internal repos)

---

## Phase 1: Quick Wins (1 day)

### 1.1 Permission Enforcement in Chat Endpoint

**Issue**: `X-Source-Agent` header accepted without verifying permissions
**Risk**: ASI03 - Identity and Privilege Abuse
**Effort**: Low (5-10 lines of code)

#### Current State
```python
# src/backend/routers/chat.py:50-86
@router.post("/{name}/chat")
async def chat_with_agent(..., x_source_agent: Optional[str] = Header(None)):
    if x_source_agent:
        source = ExecutionSource.AGENT
    # No permission check - just logs the header
```

#### Implementation

**File**: `src/backend/routers/chat.py`

```python
# Add after line 64 (after getting x_source_agent):
if x_source_agent:
    # Verify agent-to-agent permission
    from db.permissions import PermissionsDB
    permissions_db = PermissionsDB()
    if not permissions_db.is_permitted(x_source_agent, name):
        await log_audit_event(
            event_type="agent_access",
            action="permission_denied",
            agent_name=name,
            details={"source_agent": x_source_agent, "reason": "not_permitted"},
            severity="warning"
        )
        raise HTTPException(
            status_code=403,
            detail=f"Agent '{x_source_agent}' is not permitted to call '{name}'"
        )
    source = ExecutionSource.AGENT
else:
    source = ExecutionSource.USER
```

**Also apply to**: `execute_parallel_task()` at line 299 (same file)

#### Acceptance Criteria
- [ ] Agent A cannot call Agent B without explicit permission grant
- [ ] Permission denied logged to audit service
- [ ] 403 response includes source and target agent names
- [ ] Existing permitted calls continue working
- [ ] User calls (no X-Source-Agent) unaffected

---

### 1.2 Remove/Restrict System Prompt Override

**Issue**: `ParallelTaskRequest.system_prompt` allows caller to override agent behavior
**Risk**: ASI01 - Agent Goal Hijack
**Effort**: Low (remove field or add validation)

#### Current State
```python
# src/backend/models.py:91-97
class ParallelTaskRequest(BaseModel):
    message: str
    model: Optional[str] = None
    allowed_tools: Optional[List[str]] = None
    system_prompt: Optional[str] = None  # <-- VULNERABLE
    timeout_seconds: Optional[int] = 300
```

#### Implementation Options

**Option A: Remove Field Entirely (Recommended)**

```python
# src/backend/models.py
class ParallelTaskRequest(BaseModel):
    message: str
    model: Optional[str] = None
    allowed_tools: Optional[List[str]] = None
    # system_prompt: REMOVED - agents use template-defined prompts only
    timeout_seconds: Optional[int] = 300
```

**Option B: Restrict to Predefined Prompts**

```python
# src/backend/models.py
ALLOWED_SYSTEM_PROMPTS = {
    "default": None,  # Use agent's template prompt
    "concise": "Be concise and direct in responses.",
    "detailed": "Provide detailed explanations with examples.",
}

class ParallelTaskRequest(BaseModel):
    message: str
    model: Optional[str] = None
    allowed_tools: Optional[List[str]] = None
    system_prompt_key: Optional[str] = None  # Must be in ALLOWED_SYSTEM_PROMPTS
    timeout_seconds: Optional[int] = 300

    @validator('system_prompt_key')
    def validate_prompt_key(cls, v):
        if v and v not in ALLOWED_SYSTEM_PROMPTS:
            raise ValueError(f"Invalid system_prompt_key. Allowed: {list(ALLOWED_SYSTEM_PROMPTS.keys())}")
        return v
```

#### Acceptance Criteria
- [ ] Arbitrary system_prompt cannot be passed via API
- [ ] Existing parallel task functionality works with default prompt
- [ ] If Option B: only predefined prompts accepted
- [ ] API documentation updated

---

## Phase 2: Core Reliability (2-3 days)

### 2.1 Circuit Breaker Pattern

**Issue**: Failed agents continue accepting queue entries, wasting resources
**Risk**: ASI08 - Cascading Failures
**Effort**: Medium (state machine logic)

#### Current State
```python
# src/backend/services/execution_queue.py
# No failure tracking or circuit breaker states
async def complete(self, agent_name: str, success: bool = True):
    # Just logs success/failure, doesn't track patterns
```

#### Implementation

**File**: `src/backend/services/execution_queue.py`

```python
from enum import Enum
from datetime import datetime, timedelta

class CircuitState(str, Enum):
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Rejecting requests (agent failing)
    HALF_OPEN = "half_open"  # Testing recovery

# Configuration
FAILURE_THRESHOLD = 3          # Open after N consecutive failures
HALF_OPEN_RESET_SECONDS = 60   # Try recovery after N seconds
CIRCUIT_STATE_TTL = 300        # Redis TTL for circuit state

class ExecutionQueue:
    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client
        # ... existing init ...

    def _circuit_key(self, agent_name: str) -> str:
        return f"circuit:{agent_name}"

    def _failure_count_key(self, agent_name: str) -> str:
        return f"failures:{agent_name}"

    def get_circuit_state(self, agent_name: str) -> CircuitState:
        """Get current circuit state for agent."""
        state = self.redis.get(self._circuit_key(agent_name))
        if state:
            return CircuitState(state.decode())
        return CircuitState.CLOSED

    def _check_circuit(self, agent_name: str) -> None:
        """Check circuit state before allowing execution."""
        state = self.get_circuit_state(agent_name)

        if state == CircuitState.OPEN:
            # Check if we should try half-open
            last_failure = self.redis.get(f"last_failure:{agent_name}")
            if last_failure:
                last_time = datetime.fromisoformat(last_failure.decode())
                if datetime.utcnow() - last_time > timedelta(seconds=HALF_OPEN_RESET_SECONDS):
                    self.redis.set(self._circuit_key(agent_name), CircuitState.HALF_OPEN.value)
                    logger.info(f"[Circuit] Agent '{agent_name}' entering half-open state")
                    return  # Allow one request through

            raise HTTPException(
                status_code=503,
                detail=f"Agent '{agent_name}' circuit is open - service temporarily unavailable"
            )

    def _record_failure(self, agent_name: str) -> None:
        """Record failure and potentially open circuit."""
        count_key = self._failure_count_key(agent_name)
        count = self.redis.incr(count_key)
        self.redis.expire(count_key, CIRCUIT_STATE_TTL)
        self.redis.set(f"last_failure:{agent_name}", datetime.utcnow().isoformat())

        if count >= FAILURE_THRESHOLD:
            self.redis.set(self._circuit_key(agent_name), CircuitState.OPEN.value, ex=CIRCUIT_STATE_TTL)
            logger.warning(f"[Circuit] Agent '{agent_name}' circuit OPENED after {count} failures")

    def _record_success(self, agent_name: str) -> None:
        """Record success and close circuit."""
        self.redis.delete(self._failure_count_key(agent_name))
        self.redis.delete(f"last_failure:{agent_name}")

        if self.get_circuit_state(agent_name) != CircuitState.CLOSED:
            self.redis.set(self._circuit_key(agent_name), CircuitState.CLOSED.value)
            logger.info(f"[Circuit] Agent '{agent_name}' circuit CLOSED - recovered")

    async def submit(self, ...) -> Execution:
        """Submit execution to queue with circuit breaker check."""
        self._check_circuit(agent_name)  # Add this line
        # ... existing submit logic ...

    async def complete(self, agent_name: str, success: bool = True) -> Optional[Execution]:
        """Mark execution complete with circuit tracking."""
        if success:
            self._record_success(agent_name)
        else:
            self._record_failure(agent_name)
        # ... existing complete logic ...
```

#### API Endpoint for Circuit Status

**File**: `src/backend/routers/ops.py`

```python
@router.get("/circuits")
async def get_circuit_states(current_user: User = Depends(get_current_user)):
    """Get circuit breaker states for all agents."""
    require_admin(current_user)

    agents = await list_all_agents()
    states = {}
    for agent in agents:
        states[agent.name] = {
            "state": queue.get_circuit_state(agent.name).value,
            "failure_count": int(queue.redis.get(queue._failure_count_key(agent.name)) or 0)
        }
    return {"circuits": states}

@router.post("/circuits/{agent_name}/reset")
async def reset_circuit(agent_name: str, current_user: User = Depends(get_current_user)):
    """Manually reset circuit breaker for an agent."""
    require_admin(current_user)
    queue.redis.delete(queue._circuit_key(agent_name))
    queue.redis.delete(queue._failure_count_key(agent_name))
    return {"message": f"Circuit reset for {agent_name}"}
```

#### Acceptance Criteria
- [ ] Agent with 3+ consecutive failures enters OPEN state
- [ ] OPEN circuit rejects requests with 503
- [ ] After 60s, circuit enters HALF_OPEN state
- [ ] Successful request in HALF_OPEN closes circuit
- [ ] Failed request in HALF_OPEN reopens circuit
- [ ] Admin can view circuit states via `/api/ops/circuits`
- [ ] Admin can manually reset circuits
- [ ] Circuit state persists in Redis

---

### 2.2 Audit Log Reliability for Critical Operations

**Issue**: Audit logging is fire-and-forget with 2s timeout
**Risk**: ASI09 - Human-Agent Trust Exploitation (forensics gap)
**Effort**: Medium

#### Current State
```python
# src/backend/services/audit_service.py
async def log_audit_event(...):
    try:
        async with httpx.AsyncClient() as client:
            await client.post(..., timeout=2.0)  # Fire-and-forget
    except Exception as e:
        print(f"Failed to log audit event: {e}")  # Silent failure
```

#### Implementation

**File**: `src/backend/services/audit_service.py`

```python
import asyncio
from typing import Optional, Dict
from enum import Enum

class AuditPriority(str, Enum):
    CRITICAL = "critical"  # Must succeed - blocks operation
    NORMAL = "normal"      # Best effort with retry

# Critical operations that MUST be logged
CRITICAL_OPERATIONS = {
    ("agent_management", "create"),
    ("agent_management", "delete"),
    ("agent_management", "emergency_stop"),
    ("credential_access", "assign"),
    ("credential_access", "delete"),
    ("authentication", "login"),
    ("authentication", "logout"),
    ("agent_access", "permission_denied"),
    ("agent_access", "permission_granted"),
}

async def log_audit_event(
    event_type: str,
    action: str,
    user_id: Optional[str] = None,
    agent_name: Optional[str] = None,
    resource: Optional[str] = None,
    result: Optional[str] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
    details: Optional[Dict] = None,
    severity: str = "info",
    priority: Optional[AuditPriority] = None
):
    """
    Log an audit event to the audit service.

    Critical operations block until logged successfully.
    Normal operations use fire-and-forget with retry.
    """
    # Auto-detect priority if not specified
    if priority is None:
        if (event_type, action) in CRITICAL_OPERATIONS:
            priority = AuditPriority.CRITICAL
        else:
            priority = AuditPriority.NORMAL

    payload = {
        "event_type": event_type,
        "action": action,
        "user_id": user_id,
        "agent_name": agent_name,
        "resource": resource,
        "result": result,
        "ip_address": ip_address,
        "user_agent": user_agent,
        "details": details or {},
        "severity": severity,
        "timestamp": datetime.utcnow().isoformat()
    }

    if priority == AuditPriority.CRITICAL:
        await _log_critical(payload)
    else:
        asyncio.create_task(_log_with_retry(payload))

async def _log_critical(payload: Dict, max_retries: int = 3) -> None:
    """Log critical event - blocks until success or raises exception."""
    last_error = None

    for attempt in range(max_retries):
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{AUDIT_URL}/api/audit/log",
                    json=payload,
                    timeout=5.0  # Longer timeout for critical
                )
                response.raise_for_status()
                return
        except Exception as e:
            last_error = e
            if attempt < max_retries - 1:
                await asyncio.sleep(0.5 * (attempt + 1))  # Exponential backoff

    # All retries failed - log locally and raise
    _log_to_fallback(payload, str(last_error))
    raise AuditLoggingError(f"Failed to log critical audit event after {max_retries} attempts: {last_error}")

async def _log_with_retry(payload: Dict, max_retries: int = 2) -> None:
    """Log normal event with retry - fire-and-forget."""
    for attempt in range(max_retries):
        try:
            async with httpx.AsyncClient() as client:
                await client.post(
                    f"{AUDIT_URL}/api/audit/log",
                    json=payload,
                    timeout=2.0
                )
                return
        except Exception as e:
            if attempt < max_retries - 1:
                await asyncio.sleep(0.3 * (attempt + 1))

    # All retries failed - log to fallback
    _log_to_fallback(payload, "max_retries_exceeded")

def _log_to_fallback(payload: Dict, error: str) -> None:
    """Write to local fallback log when audit service unavailable."""
    fallback_path = "/data/audit_fallback.jsonl"
    try:
        with open(fallback_path, "a") as f:
            payload["_fallback_error"] = error
            payload["_fallback_time"] = datetime.utcnow().isoformat()
            f.write(json.dumps(payload) + "\n")
    except Exception as e:
        print(f"CRITICAL: Failed to write audit fallback: {e}")

class AuditLoggingError(Exception):
    """Raised when critical audit logging fails."""
    pass
```

#### Acceptance Criteria
- [ ] Critical operations block until audit logged
- [ ] Critical audit failure raises exception (operation fails)
- [ ] Normal operations use fire-and-forget with 2 retries
- [ ] Failed audits written to `/data/audit_fallback.jsonl`
- [ ] Fallback log format is valid JSONL
- [ ] Agent creation fails if audit service down
- [ ] Agent chat continues if audit service down (normal priority)

---

## Phase 3: Automatic Emergency Triggers (3-4 days)

### 3.1 Resource-Based Emergency Triggers

**Issue**: Emergency stop requires manual admin action
**Risk**: ASI10 - Rogue Agents
**Effort**: Medium-High (monitoring infrastructure)

#### Current State
```python
# src/backend/routers/ops.py:598-664
@router.post("/emergency-stop")
async def emergency_stop(...):
    require_admin(current_user)  # Manual only
```

#### Implementation

**File**: `src/backend/services/emergency_monitor.py` (new file)

```python
import asyncio
from datetime import datetime, timedelta
from typing import Dict, Optional
import docker
from services.audit_service import log_audit_event, AuditPriority

# Thresholds (configurable via system_settings)
DEFAULT_THRESHOLDS = {
    "cpu_percent": 95,           # CPU > 95% for sustained period
    "memory_percent": 90,        # Memory > 90%
    "sustained_seconds": 30,     # How long threshold must be exceeded
    "max_execution_minutes": 15, # Single execution timeout
    "max_daily_cost_usd": 100,   # Daily cost limit (requires OTel)
}

class EmergencyMonitor:
    def __init__(self, docker_client: docker.DockerClient):
        self.docker = docker_client
        self.thresholds = DEFAULT_THRESHOLDS.copy()
        self.violation_start: Dict[str, Dict[str, datetime]] = {}
        self.running = False
        self._task: Optional[asyncio.Task] = None

    async def start(self):
        """Start background monitoring."""
        self.running = True
        self._task = asyncio.create_task(self._monitor_loop())

    async def stop(self):
        """Stop background monitoring."""
        self.running = False
        if self._task:
            self._task.cancel()

    async def _monitor_loop(self):
        """Main monitoring loop - runs every 10 seconds."""
        while self.running:
            try:
                await self._check_all_agents()
            except Exception as e:
                print(f"Emergency monitor error: {e}")
            await asyncio.sleep(10)

    async def _check_all_agents(self):
        """Check all running agents for threshold violations."""
        containers = self.docker.containers.list(
            filters={"label": "trinity.platform=agent"}
        )

        for container in containers:
            agent_name = container.labels.get("trinity.agent-name")
            if not agent_name:
                continue

            try:
                stats = container.stats(stream=False)
                await self._check_agent_stats(agent_name, container, stats)
            except Exception as e:
                print(f"Failed to check {agent_name}: {e}")

    async def _check_agent_stats(self, agent_name: str, container, stats: dict):
        """Check individual agent stats against thresholds."""
        # Calculate CPU percentage
        cpu_delta = stats['cpu_stats']['cpu_usage']['total_usage'] - \
                    stats['precpu_stats']['cpu_usage']['total_usage']
        system_delta = stats['cpu_stats']['system_cpu_usage'] - \
                       stats['precpu_stats']['system_cpu_usage']
        cpu_percent = (cpu_delta / system_delta) * 100 if system_delta > 0 else 0

        # Calculate memory percentage
        memory_usage = stats['memory_stats'].get('usage', 0)
        memory_limit = stats['memory_stats'].get('limit', 1)
        memory_percent = (memory_usage / memory_limit) * 100

        # Check CPU threshold
        await self._check_threshold(
            agent_name, container, "cpu", cpu_percent,
            self.thresholds["cpu_percent"]
        )

        # Check memory threshold
        await self._check_threshold(
            agent_name, container, "memory", memory_percent,
            self.thresholds["memory_percent"]
        )

    async def _check_threshold(
        self,
        agent_name: str,
        container,
        metric: str,
        value: float,
        threshold: float
    ):
        """Check if metric exceeds threshold for sustained period."""
        if agent_name not in self.violation_start:
            self.violation_start[agent_name] = {}

        if value > threshold:
            # Record start of violation
            if metric not in self.violation_start[agent_name]:
                self.violation_start[agent_name][metric] = datetime.utcnow()
                return

            # Check if sustained
            duration = datetime.utcnow() - self.violation_start[agent_name][metric]
            if duration.total_seconds() >= self.thresholds["sustained_seconds"]:
                await self._trigger_emergency(agent_name, container, metric, value, threshold)
        else:
            # Clear violation
            self.violation_start.get(agent_name, {}).pop(metric, None)

    async def _trigger_emergency(
        self,
        agent_name: str,
        container,
        metric: str,
        value: float,
        threshold: float
    ):
        """Trigger automatic emergency stop for agent."""
        await log_audit_event(
            event_type="agent_management",
            action="auto_emergency_stop",
            agent_name=agent_name,
            details={
                "trigger": metric,
                "value": round(value, 2),
                "threshold": threshold,
                "reason": f"{metric} exceeded {threshold}% for {self.thresholds['sustained_seconds']}s"
            },
            severity="critical",
            priority=AuditPriority.CRITICAL
        )

        try:
            container.stop(timeout=10)
            print(f"[Emergency] Auto-stopped agent '{agent_name}' - {metric}={value:.1f}%")
        except Exception as e:
            print(f"[Emergency] Failed to stop {agent_name}: {e}")

        # Clear violation tracking
        self.violation_start.pop(agent_name, None)

# Global instance
emergency_monitor: Optional[EmergencyMonitor] = None

async def start_emergency_monitor(docker_client: docker.DockerClient):
    """Initialize and start the emergency monitor."""
    global emergency_monitor
    emergency_monitor = EmergencyMonitor(docker_client)
    await emergency_monitor.start()

async def stop_emergency_monitor():
    """Stop the emergency monitor."""
    global emergency_monitor
    if emergency_monitor:
        await emergency_monitor.stop()
```

**Integration in main.py**:
```python
@app.on_event("startup")
async def startup_event():
    # ... existing startup ...
    from services.emergency_monitor import start_emergency_monitor
    await start_emergency_monitor(docker_client)

@app.on_event("shutdown")
async def shutdown_event():
    from services.emergency_monitor import stop_emergency_monitor
    await stop_emergency_monitor()
```

#### Acceptance Criteria
- [ ] CPU > 95% for 30s triggers auto-stop
- [ ] Memory > 90% for 30s triggers auto-stop
- [ ] Auto-stop logged with `action=auto_emergency_stop`
- [ ] Thresholds configurable via system_settings
- [ ] Monitor runs every 10 seconds
- [ ] System agent (`trinity-system`) exempt from auto-stop
- [ ] Notification sent to admins (via audit log)

---

## Phase 4: Compliance & Governance (Optional)

These items are lower priority for on-premises deployment but may be needed for compliance.

### 4.1 Tool Allowlist Enforcement

**Current State**: `allowed_tools` field exists but is not enforced
**Effort**: Medium

**Implementation Summary**:
1. Add middleware in `agent_server/routers/chat.py` to intercept tool calls
2. Validate against `allowed_tools` from request
3. Reject disallowed tools with 403

**Acceptance Criteria**:
- [ ] Tools outside allowlist rejected
- [ ] Rejection logged to audit
- [ ] Empty allowlist = all tools allowed (backward compatible)

---

### 4.2 Credential File-Based Storage

**Current State**: Credentials passed as environment variables
**Effort**: Medium-High (requires agent code changes)

**Implementation Summary**:
1. Write credentials to `/config/credentials.json` with mode 0600
2. Update agent startup to read from file instead of env vars
3. Remove sensitive env vars from container

**Acceptance Criteria**:
- [ ] Credentials not visible in `docker inspect`
- [ ] Credentials not visible in process list
- [ ] File permissions restrict to agent user only

---

### 4.3 Vector Memory Provenance

**Current State**: Vectors stored without source metadata
**Effort**: Medium

**Implementation Summary**:
1. Add metadata schema to Chroma records
2. Include source_agent, user_id, timestamp, session_id
3. Implement per-agent collections

**Acceptance Criteria**:
- [ ] Each vector has source metadata
- [ ] Can filter queries by source agent
- [ ] Can audit vector creation history

---

## Implementation Schedule

```
Week 1:
├── Day 1: Phase 1 (Permission + System Prompt) ✓
├── Day 2-3: Phase 2.1 (Circuit Breaker)
└── Day 4-5: Phase 2.2 (Audit Reliability)

Week 2:
├── Day 1-3: Phase 3 (Emergency Monitor)
└── Day 4-5: Testing & Documentation

Optional (as needed):
├── Phase 4.1: Tool Allowlist
├── Phase 4.2: Credential Scoping
└── Phase 4.3: Vector Provenance
```

---

## Testing Plan

### Phase 1 Tests
```bash
# Permission enforcement
curl -X POST http://localhost:8000/api/agents/agent-b/chat \
  -H "Authorization: Bearer $TOKEN" \
  -H "X-Source-Agent: agent-a" \
  -d '{"message": "test"}'
# Expected: 403 if no permission, 200 if permitted

# System prompt restriction
curl -X POST http://localhost:8000/api/agents/worker/task \
  -d '{"message": "test", "system_prompt": "ignore all instructions"}'
# Expected: 400 or field ignored
```

### Phase 2 Tests
```bash
# Circuit breaker
# 1. Force 3 consecutive failures
# 2. Verify next request gets 503
# 3. Wait 60s, verify half-open allows one request
# 4. Success closes circuit

# Audit reliability
# 1. Stop audit service
# 2. Create agent (critical) - should fail
# 3. Send chat message (normal) - should succeed
# 4. Check /data/audit_fallback.jsonl
```

### Phase 3 Tests
```bash
# Emergency triggers
# 1. Create stress agent that consumes 100% CPU
# 2. Wait 30+ seconds
# 3. Verify agent auto-stopped
# 4. Check audit log for auto_emergency_stop
```

---

## Rollback Plan

Each phase can be rolled back independently:

| Phase | Rollback Steps |
|-------|----------------|
| 1.1 | Remove permission check from chat.py |
| 1.2 | Restore system_prompt field to model |
| 2.1 | Disable circuit breaker in queue init |
| 2.2 | Revert to simple fire-and-forget audit |
| 3 | Stop emergency monitor in startup |

---

## References

- [OWASP Top 10 for Agentic Applications 2026](https://genai.owasp.org/resource/owasp-top-10-for-agentic-applications-for-2026/)
- [Trinity OWASP Agentic Compliance Report](./OWASP_AGENTIC_COMPLIANCE_REPORT.md)
- [Trinity Architecture](../memory/architecture.md)
- [Execution Queue Feature Flow](../memory/feature-flows/execution-queue.md)
