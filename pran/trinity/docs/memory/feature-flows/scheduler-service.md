# Feature: Dedicated Scheduler Service

> **Status**: Implemented
> **Created**: 2026-01-13
> **Priority**: HIGH
> **Requirement**: Fixes duplicate execution bug in multi-worker deployments

---

## Overview

The Dedicated Scheduler Service is a standalone Python service that executes scheduled agent tasks. It replaces the previous embedded scheduler in the backend to fix the duplicate execution bug that occurred when running multiple uvicorn workers.

**Key Features**:
- **Single-instance design** - Only one scheduler runs, preventing duplicates
- **Distributed locking** - Redis locks ensure exactly-once execution
- **Independent deployment** - Can be scaled/monitored separately from API workers
- **Event publishing** - Redis pub/sub for WebSocket compatibility
- **Health endpoints** - Kubernetes-ready health checks

---

## User Story

As a **platform administrator**, I want **scheduled tasks to execute exactly once** so that **agents do not receive duplicate commands and billing is accurate**.

---

## Architecture

```
+------------------------------------------------------------------+
|                        Trinity Platform                            |
+------------------------------------------------------------------+
|                                                                    |
|  +------------------+    +------------------+    +--------------+  |
|  |     Backend      |    |    Scheduler     |    |    Agent     |  |
|  |   (API only)     |    |   (singleton)    |    |  Containers  |  |
|  |   N workers      |    |   1 replica      |    |              |  |
|  +--------+---------+    +--------+---------+    +------+-------+  |
|           |                       |                     ^          |
|           |   CRUD operations     |                     |          |
|           v                       v                     |          |
|  +------------------+    +------------------+           |          |
|  |     SQLite       |    |      Redis       |           |          |
|  |  - Schedules     |<---|  - Locks         |           |          |
|  |  - Executions    |    |  - Events        |           |          |
|  +------------------+    |  - Heartbeats    |-----------+          |
|                          +------------------+    HTTP POST         |
|                                                  /api/task         |
+------------------------------------------------------------------+
```

**Data Flow**:
1. Backend writes schedule CRUD to SQLite (`agent_schedules` table)
2. Scheduler reads schedules from SQLite on startup
3. APScheduler triggers jobs at cron times
4. Scheduler acquires Redis lock before execution
5. Scheduler sends task to agent via HTTP
6. Scheduler publishes events to Redis for WebSocket relay

---

## Entry Points

- **Service Startup**: `python -m scheduler.main`
- **Health Check**: `GET http://localhost:8001/health`
- **Status Endpoint**: `GET http://localhost:8001/status`
- **Docker**: `docker-compose up scheduler`

---

## Source Files

| Category | File | Purpose |
|----------|------|---------|
| Entry | `src/scheduler/main.py` | SchedulerApp, signal handlers, health server |
| Core | `src/scheduler/service.py` | SchedulerService with APScheduler integration |
| Config | `src/scheduler/config.py` | Environment-based configuration |
| Models | `src/scheduler/models.py` | Schedule, ScheduleExecution, AgentTaskResponse |
| Database | `src/scheduler/database.py` | SQLite read/write operations |
| HTTP | `src/scheduler/agent_client.py` | Agent container communication |
| Locking | `src/scheduler/locking.py` | Redis distributed locks |
| Docker | `docker/scheduler/Dockerfile` | Container definition |
| Docker | `docker/scheduler/requirements.txt` | Python dependencies |
| Docker | `docker/scheduler/docker-compose.test.yml` | Standalone testing |
| Tests | `tests/scheduler_tests/*.py` | Unit and integration tests |

---

## Configuration

**Location**: `src/scheduler/config.py:13-68`

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_PATH` | `/data/trinity.db` | SQLite database path |
| `REDIS_URL` | `redis://redis:6379` | Redis connection URL |
| `LOCK_TIMEOUT` | `600` | Lock expiration in seconds (10 min) |
| `LOCK_AUTO_RENEWAL` | `true` | Auto-renew locks during execution |
| `HEALTH_PORT` | `8001` | Health check server port |
| `HEALTH_HOST` | `0.0.0.0` | Health check server bind address |
| `DEFAULT_TIMEZONE` | `UTC` | Default timezone for schedules |
| `AGENT_TIMEOUT` | `900` | Default agent request timeout (15 min) - can be overridden per-schedule |
| `LOG_LEVEL` | `INFO` | Logging verbosity |
| `PUBLISH_EVENTS` | `true` | Enable Redis event publishing |

---

## Flow 1: Service Startup

**Trigger**: Container starts or `python -m scheduler.main`

```
main.py:170                     main.py:51                      service.py:71
asyncio.run(main())   -->       SchedulerApp.start()   -->      SchedulerService.initialize()
                                |                               |
                                v                               v
                                Start health server             Load enabled schedules from DB
                                (aiohttp on :8001)              |
                                |                               v
                                v                               Create APScheduler
                                Setup signal handlers           (AsyncIOScheduler + MemoryJobStore)
                                |                               |
                                v                               v
                                Run heartbeat loop              Add CronTrigger jobs
                                (30s interval)                  |
                                                                v
                                                                scheduler.start()
```

**Key Code** (`service.py:71-98`):
```python
def initialize(self):
    """Initialize the scheduler and load all enabled schedules."""
    if self._initialized:
        logger.warning("Scheduler already initialized")
        return

    # Create scheduler with memory job store
    jobstores = {
        'default': MemoryJobStore()
    }

    self.scheduler = AsyncIOScheduler(
        jobstores=jobstores,
        timezone=pytz.UTC
    )

    # Load all enabled schedules from database
    schedules = self.db.list_all_enabled_schedules()
    for schedule in schedules:
        self._add_job(schedule)

    # Start the scheduler
    self.scheduler.start()
    self._initialized = True
    self._start_time = datetime.utcnow()

    logger.info(f"Scheduler initialized with {len(schedules)} enabled schedules")
```

---

## Flow 2: Schedule Execution (Cron Trigger)

**Trigger**: APScheduler CronTrigger fires at scheduled time

```
APScheduler                     service.py:219                  locking.py:221
CronTrigger fires   -->         _execute_schedule()   -->       try_acquire_schedule_lock()
                                |                               |
                                v                               v (if acquired)
                                Check lock                      DistributedLock.acquire()
                                |                               Redis SET NX EX
                                |                               |
                                v (if locked)                   v
                                Skip execution                  _execute_schedule_with_lock()
                                Log "already running"           |
                                                                v
                                                                database.py:167
                                                                create_execution()
                                                                INSERT schedule_executions
                                                                |
                                                                v
                                                                Publish "started" event
                                                                |
                                                                v
                                                                agent_client.py:101
                                                                client.task(message)
                                                                POST /api/task
                                                                |
                                                                v
                                                                database.py:205
                                                                update_execution_status()
                                                                |
                                                                v
                                                                Publish "completed" event
                                                                |
                                                                v
                                                                lock.release()
```

**Lock Acquisition** (`service.py:219-235`):
```python
async def _execute_schedule(self, schedule_id: str):
    """
    Execute a scheduled task.

    This is called by APScheduler when a schedule is due.
    Uses distributed locking to prevent duplicate executions.
    """
    # Try to acquire lock - if failed, another instance is executing
    lock = self.lock_manager.try_acquire_schedule_lock(schedule_id)
    if not lock:
        logger.info(f"Schedule {schedule_id} already being executed by another instance")
        return

    try:
        await self._execute_schedule_with_lock(schedule_id)
    finally:
        lock.release()
```

**Execution Logic** (`service.py:237-345`):
```python
async def _execute_schedule_with_lock(self, schedule_id: str):
    """Execute schedule after acquiring lock."""
    schedule = self.db.get_schedule(schedule_id)
    if not schedule:
        logger.error(f"Schedule {schedule_id} not found")
        return

    if not schedule.enabled:
        logger.info(f"Schedule {schedule_id} is disabled, skipping")
        return

    # Check if agent has autonomy enabled
    if not self.db.get_autonomy_enabled(schedule.agent_name):
        logger.info(f"Schedule {schedule_id} skipped: agent {schedule.agent_name} autonomy is disabled")
        return

    logger.info(f"Executing schedule: {schedule.name} for agent {schedule.agent_name}")

    # Create execution record (MODEL-001: record model_used)
    execution = self.db.create_execution(
        schedule_id=schedule.id,
        agent_name=schedule.agent_name,
        message=schedule.message,
        triggered_by="schedule",
        model_used=schedule.model
    )

    # Broadcast execution started
    await self._publish_event({
        "type": "schedule_execution_started",
        "agent": schedule.agent_name,
        "schedule_id": schedule.id,
        "execution_id": execution.id,
        "schedule_name": schedule.name
    })

    try:
        # Send task to agent (MODEL-001: pass model to agent)
        client = get_agent_client(schedule.agent_name)
        task_response = await client.task(
            schedule.message,
            execution_id=execution.id,
            model=schedule.model
        )

        # Update execution status with parsed response
        self.db.update_execution_status(
            execution_id=execution.id,
            status="success",
            response=task_response.response_text,
            context_used=task_response.metrics.context_used,
            context_max=task_response.metrics.context_max,
            cost=task_response.metrics.cost_usd,
            tool_calls=task_response.metrics.tool_calls_json,
            execution_log=task_response.metrics.execution_log_json
        )

        # Update schedule last run time
        now = datetime.utcnow()
        next_run = self._get_next_run_time(schedule.cron_expression, schedule.timezone)
        self.db.update_schedule_run_times(schedule.id, last_run_at=now, next_run_at=next_run)

        logger.info(f"Schedule {schedule.name} executed successfully")

        # Broadcast execution completed
        await self._publish_event({
            "type": "schedule_execution_completed",
            "agent": schedule.agent_name,
            "schedule_id": schedule.id,
            "execution_id": execution.id,
            "status": "success"
        })

    except AgentNotReachableError as e:
        error_msg = f"Agent not reachable: {str(e)}"
        logger.error(f"Schedule {schedule.name} execution failed: {error_msg}")

        self.db.update_execution_status(
            execution_id=execution.id,
            status="failed",
            error=error_msg
        )

        await self._publish_event({
            "type": "schedule_execution_completed",
            "agent": schedule.agent_name,
            "schedule_id": schedule.id,
            "execution_id": execution.id,
            "status": "failed",
            "error": error_msg
        })
```

---

## Flow 3: Distributed Locking

**Purpose**: Prevent duplicate executions across multiple scheduler instances or restarts

**Redis Key Pattern**: `scheduler:lock:schedule:{schedule_id}`

```
locking.py:21                   Redis                           locking.py:129
DistributedLock()   -->         SET key token NX EX 600   -->   _renewal_loop()
|                               |                               |
v                               v (if NX succeeds)              v (every 300s)
acquire() returns True          Lock acquired                   EXPIRE key 600
|                                                               (auto-renewal)
v
_start_renewal()
(background thread)

...execution happens...

locking.py:92
release()           -->         Lua script:
                                if GET key == token
                                  DEL key
                                else
                                  0 (not our lock)
```

**Lock Implementation** (`locking.py:55-90`):
```python
def acquire(self, blocking: bool = False, blocking_timeout: float = None) -> bool:
    """
    Attempt to acquire the lock.

    Args:
        blocking: If True, wait for lock to become available
        blocking_timeout: Max time to wait if blocking

    Returns:
        True if lock was acquired, False otherwise
    """
    import secrets
    self._lock_token = secrets.token_hex(16)

    if blocking:
        end_time = time.time() + (blocking_timeout or self.timeout)
        while time.time() < end_time:
            if self._try_acquire():
                self._start_renewal()
                return True
            time.sleep(0.1)
        return False
    else:
        if self._try_acquire():
            self._start_renewal()
            return True
        return False

def _try_acquire(self) -> bool:
    """Try to acquire the lock once."""
    return self.redis.set(
        self.name,
        self._lock_token,
        nx=True,  # Only if not exists
        ex=self.timeout  # Expiration in seconds
    )
```

**Auto-Renewal** (`locking.py:129-154`):
```python
def _renewal_loop(self):
    """Background thread that renews the lock."""
    # Renew at 50% of timeout to be safe
    renewal_interval = self.timeout / 2

    while not self._stop_renewal.wait(renewal_interval):
        try:
            # Only extend if we still own the lock
            script = """
            if redis.call("get", KEYS[1]) == ARGV[1] then
                return redis.call("expire", KEYS[1], ARGV[2])
            else
                return 0
            end
            """
            result = self.redis.eval(
                script, 1, self.name, self._lock_token, self.timeout
            )
            if not result:
                logger.warning(f"Lock {self.name} renewal failed - lock lost")
                break
            else:
                logger.debug(f"Lock {self.name} renewed for {self.timeout}s")
        except Exception as e:
            logger.error(f"Error renewing lock {self.name}: {e}")
            break
```

---

## Flow 4: Agent Communication

**Purpose**: Send scheduled task to agent container via HTTP

```
agent_client.py:101             agent-{name}:8000               Agent Server
AgentClient.task()   -->        POST /api/task          -->     Execute Claude Code
|                               {message, timeout,              |
|                                execution_id,                  v
|                                allowed_tools?}                Return response
v                                                               with metrics
_parse_task_response()  <-------  200 OK  <-----------------
|                               {response, metadata,
v                                execution_log}
AgentTaskResponse
(response_text, metrics)
```

**Agent Client** (`agent_client.py:44-100`):
```python
class AgentClient:
    """
    HTTP client for agent container communication.

    Designed for scheduler use - focuses on task execution.
    """

    def __init__(self, agent_name: str, timeout: float = None):
        self.agent_name = agent_name
        self.base_url = f"http://agent-{agent_name}:8000"
        self.timeout = timeout or config.agent_timeout

    async def task(
        self,
        message: str,
        timeout: float = None,
        execution_id: Optional[str] = None,
        allowed_tools: Optional[List[str]] = None,
        model: Optional[str] = None          # MODEL-001
    ) -> AgentTaskResponse:
        """
        Execute a stateless task on the agent.

        This endpoint:
        - Does NOT maintain conversation history
        - Each call is independent
        - Returns raw Claude Code execution log
        - Supports per-schedule timeout, tool restrictions (2026-02-20), and model override (2026-03-02)
        """
        timeout = timeout or self.timeout

        payload = {"message": message, "timeout_seconds": int(timeout)}
        if execution_id:
            payload["execution_id"] = execution_id
        if allowed_tools:
            payload["allowed_tools"] = allowed_tools
        if model:
            payload["model"] = model           # MODEL-001

        response = await self._request(
            "POST",
            "/api/task",
            json=payload,
            timeout=timeout + 10  # Add buffer to agent timeout
        )

        if response.status_code >= 400:
            error_msg = self._extract_error_detail(response)
            raise AgentRequestError(error_msg, status_code=response.status_code)

        result = response.json()
        return self._parse_task_response(result)
```

**Response Parsing** (`agent_client.py:176-228`):
```python
def _parse_task_response(self, result: Dict[str, Any]) -> AgentTaskResponse:
    """
    Parse agent task response into structured data.

    Extracts:
    - Response text
    - Context usage
    - Cost
    - Execution log
    - Session ID (for --resume support, EXEC-023)
    """
    # Extract response text
    response_text = result.get("response", str(result))
    if len(response_text) > 10000:
        response_text = response_text[:10000] + "... (truncated)"

    # Extract observability data
    metadata = result.get("metadata", {})
    execution_log = result.get("execution_log")

    # Context usage
    context_used = metadata.get("input_tokens", 0)
    context_max = metadata.get("context_window", 200000)
    context_percent = round(context_used / max(context_max, 1) * 100, 1)

    # Cost
    cost = metadata.get("cost_usd")

    # Claude Code session ID for --resume support (EXEC-023)
    session_id = result.get("session_id") or metadata.get("session_id")

    # Execution log - raw Claude Code transcript
    tool_calls_json = None
    execution_log_json = None
    if execution_log is not None:
        execution_log_json = json.dumps(execution_log)
        tool_calls_json = execution_log_json

    metrics = AgentTaskMetrics(
        context_used=context_used,
        context_max=context_max,
        context_percent=context_percent,
        cost_usd=cost,
        tool_calls_json=tool_calls_json,
        execution_log_json=execution_log_json,
        session_id=session_id  # EXEC-023
    )

    return AgentTaskResponse(
        response_text=response_text,
        metrics=metrics,
        raw_response=result
    )
```

---

## Flow 5: Event Publishing

**Purpose**: Broadcast execution events to Redis for backend WebSocket relay

```
service.py:387                  Redis                           Backend
_publish_event()    -->         PUBLISH scheduler:events  -->   (subscriber)
|                               {type, agent, ...}              |
v                                                               v
JSON serialize                                                  Relay to WebSocket
redis.publish()                                                 clients
```

**Event Types**:

| Event | Fields | Description |
|-------|--------|-------------|
| `schedule_execution_started` | agent, schedule_id, execution_id, schedule_name | Execution begins |
| `schedule_execution_completed` | agent, schedule_id, execution_id, status, error? | Execution ends |

**Publishing Code** (`service.py:387-401`):
```python
async def _publish_event(self, event: dict):
    """
    Publish an event to Redis for WebSocket compatibility.

    Events are published to a channel that the backend can subscribe to.
    """
    if not config.publish_events:
        return

    try:
        event_json = json.dumps(event)
        self.redis.publish("scheduler:events", event_json)
        logger.debug(f"Published event: {event['type']}")
    except Exception as e:
        logger.error(f"Failed to publish event: {e}")
```

---

## Database Operations

**Location**: `src/scheduler/database.py`

### Read Operations (Schedules)

| Method | Line | SQL | Purpose |
|--------|------|-----|---------|
| `get_schedule(id)` | 95-101 | `SELECT * FROM agent_schedules WHERE id = ?` | Get single schedule |
| `list_all_enabled_schedules()` | 103-111 | `SELECT * FROM agent_schedules WHERE enabled = 1` | Load on startup |
| `list_agent_schedules(name)` | 113-121 | `SELECT * FROM agent_schedules WHERE agent_name = ?` | Per-agent list |
| `get_autonomy_enabled(name)` | 123-131 | `SELECT autonomy_enabled FROM agent_ownership` | Check autonomy |

### Write Operations (Schedules)

| Method | Line | SQL | Purpose |
|--------|------|-----|---------|
| `update_schedule_run_times()` | 137-161 | `UPDATE agent_schedules SET last_run_at, next_run_at` | Track execution times |

### Execution Operations

| Method | Line | SQL | Purpose |
|--------|------|-----|---------|
| `create_execution()` | 167-203 | `INSERT INTO schedule_executions` | Create execution record (MODEL-001: includes `model_used`) |
| `update_execution_status()` | 233-284 | `UPDATE schedule_executions SET status, response, ..., claude_session_id` | Complete execution (EXEC-023: added `claude_session_id` param) |
| `get_execution(id)` | 252-258 | `SELECT * FROM schedule_executions WHERE id = ?` | Get execution |
| `get_recent_executions()` | 260-269 | `SELECT * FROM schedule_executions ORDER BY started_at DESC` | List recent |

**Session ID Storage (EXEC-023)**: `update_execution_status()` now accepts optional `claude_session_id` parameter (line 244) which stores the Claude Code session ID for `--resume` support. This enables the "Continue Execution as Chat" feature for scheduled executions.

---

## Health & Status Endpoints

**Location**: `src/scheduler/main.py:73-128`

### GET /health

Returns 200 if scheduler is healthy, 503 otherwise.

```json
{"status": "healthy"}
```

### GET /status

Returns detailed scheduler status.

```json
{
  "running": true,
  "jobs_count": 5,
  "uptime_seconds": 3600.5,
  "last_check": "2026-01-13T10:30:00.000Z",
  "jobs": [
    {
      "id": "schedule_abc123",
      "name": "my-agent:Daily Report",
      "next_run": "2026-01-14T09:00:00+00:00"
    }
  ]
}
```

### GET /

Service information.

```json
{
  "service": "Trinity Scheduler",
  "version": "1.0.0",
  "endpoints": {
    "/health": "Health check",
    "/status": "Detailed status"
  }
}
```

---

## Docker Deployment

**Dockerfile** (`docker/scheduler/Dockerfile`):
```dockerfile
FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY docker/scheduler/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY src/scheduler /app/scheduler

ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8001/health || exit 1

ENV DATABASE_PATH=/data/trinity.db
ENV REDIS_URL=redis://redis:6379
ENV HEALTH_PORT=8001
ENV LOG_LEVEL=INFO

CMD ["python", "-m", "scheduler.main"]
```

**Dependencies** (`docker/scheduler/requirements.txt`):
```
APScheduler>=3.10.0,<4.0.0
croniter>=2.0.1
httpx>=0.27.0
aiohttp>=3.9.0
redis>=5.0.0
pytz>=2024.1
pytest>=8.0.0
pytest-asyncio>=0.23.0
pytest-cov>=4.1.0
pytest-mock>=3.12.0
typing-extensions>=4.9.0
```

---

## Testing

**Location**: `tests/scheduler_tests/`

### Test Files

| File | Tests | Purpose |
|------|-------|---------|
| `test_config.py` | Configuration loading | Environment variables |
| `test_cron.py` | Cron expression parsing | 5-field format validation |
| `test_database.py` | Database operations | CRUD for schedules/executions |
| `test_locking.py` | Distributed locks | Redis lock acquire/release |
| `test_agent_client.py` | HTTP client | Agent communication |
| `test_service.py` | Scheduler service | Full integration tests |
| `conftest.py` | Fixtures | Mock database, Redis, models |

### Running Tests

```bash
# Run all scheduler tests
pytest tests/scheduler_tests/ -v

# Run with coverage
pytest tests/scheduler_tests/ --cov=src/scheduler --cov-report=html

# Run standalone test environment
docker compose -f docker/scheduler/docker-compose.test.yml up
```

### Key Test Cases (`test_service.py`)

```python
async def test_initialization(self, db_with_data, mock_lock_manager):
    """Test scheduler initialization."""
    service = SchedulerService(database=db_with_data, lock_manager=mock_lock_manager)
    service.initialize()
    assert service._initialized is True
    assert service.scheduler.running is True
    service.shutdown()

async def test_execute_schedule_skips_if_locked(self, db_with_data, mock_lock_manager):
    """Test that execution is skipped if lock cannot be acquired."""
    service = SchedulerService(database=db_with_data, lock_manager=mock_lock_manager)
    mock_lock_manager.try_acquire_schedule_lock = MagicMock(return_value=None)

    with patch('scheduler.service.get_agent_client') as mock_get_client:
        await service._execute_schedule("schedule-1")

    mock_get_client.assert_not_called()  # Should not attempt execution
```

---

## Error Handling

| Error Case | Handling | Result |
|------------|----------|--------|
| Schedule not found | Log error, return | Execution skipped |
| Schedule disabled | Log info, return | Execution skipped |
| Autonomy disabled | Log info, return | Execution skipped |
| Lock not acquired | Log info, return | Execution skipped (another running) |
| **Max instances reached** | Create skipped execution, publish event | **Recorded with status='skipped'** (Issue #46) |
| Agent not reachable | Update status=failed, publish event | Error recorded |
| Agent timeout | Update status=failed, publish event | Error recorded |
| Agent error response | Update status=failed, publish event | Error recorded |
| Redis publish fails | Log error, continue | Execution still succeeds |

---

## Flow 9: Skipped Execution Recording (Issue #46)

**Purpose**: Record executions that are dropped due to APScheduler's max_instances=1 constraint

**Trigger**: APScheduler fires `EVENT_JOB_MAX_INSTANCES` when a scheduled job is skipped because the previous execution is still running

```
APScheduler                     service.py:408                  database.py:233
EVENT_JOB_MAX_INSTANCES  -->    _on_job_max_instances()  -->    create_skipped_execution()
|                               |                               |
v                               v                               v
Job skipped because             Parse job_id to get             INSERT schedule_executions
max_instances=1 reached         schedule_id                     status='skipped'
                                |                               duration_ms=0
                                v                               error=skip_reason
                                _record_skipped_agent_schedule()
                                or _record_skipped_process_schedule()
                                |
                                v
                                Publish event
                                "schedule_execution_skipped"
```

**Event Listener Setup** (`service.py:initialize()`):
```python
# Add listener for skipped executions (max_instances reached)
self.scheduler.add_listener(
    self._on_job_max_instances,
    EVENT_JOB_MAX_INSTANCES
)
```

**Handler Implementation** (`service.py:408-471`):
```python
def _on_job_max_instances(self, event: JobExecutionEvent):
    """
    Handle EVENT_JOB_MAX_INSTANCES - triggered when a job is skipped because
    the previous execution is still running (max_instances=1 reached).
    """
    job_id = event.job_id
    logger.warning(f"Job {job_id} skipped: previous execution still running")

    # Extract schedule_id from job_id
    if job_id.startswith("schedule_"):
        schedule_id = job_id[len("schedule_"):]
        self._record_skipped_agent_schedule(schedule_id)
    elif job_id.startswith("process_schedule_"):
        schedule_id = job_id[len("process_schedule_"):]
        self._record_skipped_process_schedule(schedule_id)
```

**Database Record** (`database.py:233-290`):
```python
def create_skipped_execution(
    self,
    schedule_id: str,
    agent_name: str,
    message: str,
    triggered_by: str = "schedule",
    skip_reason: str = None
) -> Optional[ScheduleExecution]:
    """Create a skipped execution record for audit trail."""
    now = datetime.utcnow().isoformat()
    execution_id = self.generate_id()

    cursor.execute("""
        INSERT INTO schedule_executions (
            id, schedule_id, agent_name, status, started_at, completed_at,
            duration_ms, message, triggered_by, error
        ) VALUES (?, ?, ?, 'skipped', ?, ?, 0, ?, ?, ?)
    """, (execution_id, schedule_id, agent_name, now, now, message, triggered_by, skip_reason))
```

**WebSocket Event**:
```json
{
  "type": "schedule_execution_skipped",
  "agent": "my-agent",
  "schedule_id": "abc123",
  "execution_id": "exec-456",
  "schedule_name": "Daily Report",
  "reason": "Previous execution still running"
}
```

**UI Display**: Skipped executions appear in execution history with purple status badge and can be filtered in ExecutionList view.

---

## Security Considerations

1. **Database Access**: Read-only access to schedules; write access only to executions
2. **Lock Tokens**: Random 16-byte hex tokens prevent lock hijacking
3. **Agent Communication**: Internal Docker network, no external exposure
4. **No Authentication**: Health endpoints are unauthenticated (internal use only)
5. **Credential Isolation**: Scheduler has no access to agent credentials

---

## Graceful Shutdown

**Signal Handling** (`main.py:156-167`):
```python
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
```

**Shutdown Sequence** (`main.py:143-154`):
```python
async def shutdown(self):
    """Graceful shutdown."""
    logger.info("Initiating graceful shutdown...")
    self._shutdown_event.set()

    if self.scheduler_service:
        self.scheduler_service.shutdown()

    if self.health_runner:
        await self.health_runner.cleanup()

    logger.info("Scheduler service stopped")
```

---

## Trinity Connect Integration (Added 2026-02-05)

The dedicated scheduler service publishes events to Redis, which the backend relays to both the main WebSocket and the filtered Trinity Connect WebSocket.

### Event Publishing via Redis

**Location**: `src/scheduler/service.py:387-401`

The dedicated scheduler publishes events to the `scheduler:events` Redis channel:

```python
async def _publish_event(self, event: dict):
    """Publish an event to Redis for WebSocket compatibility."""
    event_json = json.dumps(event)
    self.redis.publish("scheduler:events", event_json)
```

The backend subscribes to this channel and relays events to both WebSocket managers:
- Main WebSocket Manager: All UI clients
- Filtered WebSocket Manager: Trinity Connect clients (server-side agent filtering)

### Events Broadcast to Trinity Connect

Schedule execution events are forwarded to external listeners:

| Event Type | Agent Name Field | Description |
|------------|------------------|-------------|
| `schedule_execution_started` | `agent` | Execution begins |
| `schedule_execution_completed` | `agent` | Execution ends (success or failure) |

### Use Case: External Coordination

Local Claude Code instances can wait for scheduled task completion:

```bash
# Wait for report-agent's scheduled task to complete
export TRINITY_API_KEY="trinity_mcp_xxx"
./trinity-listen.sh report-agent completed

# Event received: {"type": "schedule_execution_completed", "agent": "report-agent", "status": "success", ...}
# Claude Code can now fetch results and continue processing
```

### Related Documentation

- **Trinity Connect**: [trinity-connect.md](trinity-connect.md) - Full feature flow for `/ws/events` endpoint

---

## Related Flows

- **Upstream**:
  - [scheduling.md](scheduling.md) - Backend CRUD for schedules (API layer)
  - [autonomy-mode.md](autonomy-mode.md) - Autonomy toggle affects execution
- **Downstream**:
  - [parallel-headless-execution.md](parallel-headless-execution.md) - Agent `/api/task` endpoint
  - [execution-log-viewer.md](execution-log-viewer.md) - Viewing execution transcripts
- **Related**:
  - [execution-queue.md](execution-queue.md) - Queue system (not used by scheduler)
  - [activity-stream.md](activity-stream.md) - Activity tracking (not yet integrated)
  - [trinity-connect.md](trinity-connect.md) - Filtered event broadcast for external listeners (Added 2026-02-05)

---

## Migration Notes

**Embedded Scheduler Fully Removed (2026-02-11)**:

The embedded scheduler (`src/backend/services/scheduler_service.py`) has been completely removed. The dedicated scheduler is now the single source of truth for all schedule execution.

**Current Architecture**:
1. Backend only manages schedule CRUD in database
2. Dedicated scheduler syncs from database every 60 seconds
3. All triggers (cron and manual) are executed by dedicated scheduler
4. Activity tracking via internal API ensures Timeline visibility

**For Rollback** (if needed, restore from git):
1. Restore `src/backend/services/scheduler_service.py` from git history
2. Re-add imports in affected files
3. Stop dedicated scheduler container
4. Run backend with single worker (`--workers 1`)

**Note**: Rollback is not recommended as the consolidated architecture provides:
- Cleaner separation of concerns
- Consistent activity tracking
- Single source of truth for schedule state

---

## Flow 6: Periodic Schedule Sync

**Purpose**: Detect new/updated/deleted schedules without container restart

**Trigger**: Every 60 seconds (configurable via `SCHEDULE_RELOAD_INTERVAL`)

```
run_forever()                 _sync_schedules()             _sync_agent_schedules()
(main loop)      -->          (every 60s)      -->          Compare DB with snapshot
|                             |                              |
v                             v                              v
heartbeat (30s)               _sync_agent_schedules()        Build current_state map
|                             _sync_process_schedules()      from list_all_schedules()
v                                                            |
check sync_interval                                          v
(>= 60s since last?)                                         Detect changes:
|                                                            - new_ids (add jobs)
v                                                            - deleted_ids (remove jobs)
_sync_schedules()                                            - updated (cron/tz/enabled)
last_sync = now                                              |
                                                             v
                                                             Update _schedule_snapshot
```

**Key Implementation** (`service.py:224-316`):

```python
async def _sync_agent_schedules(self):
    """Sync agent schedules with database."""
    all_schedules = self.db.list_all_schedules()

    # Build current state map: schedule_id -> (enabled, updated_at_iso)
    current_state: Dict[str, tuple] = {}
    for schedule in all_schedules:
        current_state[schedule.id] = (schedule.enabled, schedule.updated_at.isoformat())

    # Detect changes
    snapshot_ids = set(self._schedule_snapshot.keys())
    current_ids = set(current_state.keys())

    # New schedules
    for schedule_id in (current_ids - snapshot_ids):
        schedule = schedule_map[schedule_id]
        if schedule.enabled:
            self._add_job(schedule)  # Add to APScheduler
        self._schedule_snapshot[schedule_id] = current_state[schedule_id]

    # Deleted schedules
    for schedule_id in (snapshot_ids - current_ids):
        self._remove_job(schedule_id)  # Remove from APScheduler
        del self._schedule_snapshot[schedule_id]

    # Updated schedules (enabled/disabled or cron changed)
    for schedule_id in (snapshot_ids & current_ids):
        if self._schedule_snapshot[schedule_id] != current_state[schedule_id]:
            # Re-add job with updated config
            self._remove_job(schedule_id)
            if schedule.enabled:
                self._add_job(schedule)
            self._schedule_snapshot[schedule_id] = current_state[schedule_id]
```

**Configuration** (`config.py:46-48`):
```python
schedule_reload_interval: int = field(default_factory=lambda: int(os.getenv(
    "SCHEDULE_RELOAD_INTERVAL", "60"
)))  # seconds
```

**Log Examples**:
```
INFO - Sync: Adding new schedule Daily Report for agent my-agent
INFO - Sync: Disabling schedule Weekly Digest
INFO - Sync: Updating schedule Hourly Check
INFO - Sync complete: 2 added, 1 removed
```

---

## Flow 7: Manual Trigger (via Dedicated Scheduler)

**Purpose**: Manual schedule triggers are now routed through the dedicated scheduler to ensure consistent activity tracking and locking.

**Trigger**: User clicks "Run Now" button in UI or API call

```
Backend API                      Scheduler Service              Backend Internal API
POST /api/agents/{name}/         POST /api/schedules/           POST /api/internal/
    schedules/{id}/trigger       {id}/trigger                   activities/track
|                                |                               |
v                                v                               v
schedules.py:trigger_schedule    main.py:_trigger_handler        internal.py:track_activity
  → httpx.post to scheduler        → validate schedule              → activity_service.track_activity
                                   → create_task(_execute_manual)   → WebSocket broadcast
                                   → return immediately             |
                                                                    v
                                   _execute_manual_trigger()     POST /api/internal/
                                     → acquire lock               activities/{id}/complete
                                     → _execute_schedule_with_lock
                                       → _track_activity_start
                                       → send task to agent
                                       → _complete_activity
```

**Endpoint**: `POST /api/schedules/{schedule_id}/trigger` (scheduler service port 8001)

**Response**:
```json
{
  "status": "triggered",
  "schedule_id": "abc123",
  "schedule_name": "Daily Report",
  "agent_name": "my-agent",
  "message": "Execution started in background"
}
```

---

## Flow 8: Activity Tracking via Internal API

**Purpose**: Create `agent_activities` records for Timeline dashboard visibility

**Trigger**: Both cron-triggered and manual schedule executions

```
Scheduler Service                     Backend Internal API
_execute_schedule_with_lock()   -->   POST /api/internal/activities/track
|                                     {agent_name, activity_type, ...}
v                                     |
Send task to agent                    v
|                                     Creates agent_activities record
v                                     Broadcasts via WebSocket
_complete_activity()            -->   POST /api/internal/activities/{id}/complete
                                      {status, details, error}
                                      |
                                      v
                                      Updates activity record
                                      Broadcasts completion via WebSocket
```

**Internal API Endpoints** (no authentication - internal Docker network only):

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/internal/activities/track` | POST | Start tracking an activity |
| `/api/internal/activities/{id}/complete` | POST | Mark activity as completed/failed |

**Request Model** (`ActivityTrackRequest`):
```python
{
    "agent_name": "my-agent",
    "activity_type": "schedule_start",
    "user_id": 1,  # optional
    "triggered_by": "schedule",  # or "manual"
    "related_execution_id": "exec-123",
    "details": {
        "schedule_id": "abc123",
        "schedule_name": "Daily Report"
    }
}
```

---

## Scheduler Consolidation (2026-02-11)

### What Changed

The scheduler architecture was consolidated to make the dedicated scheduler the **single source of truth** for all schedule execution:

1. **Embedded Scheduler Removed**: `src/backend/services/scheduler_service.py` was deleted
2. **Manual Triggers Delegated**: Backend API now routes manual triggers to dedicated scheduler
3. **Activity Tracking Added**: Dedicated scheduler creates `agent_activities` records via internal API
4. **CRUD Simplified**: Backend only updates database; scheduler syncs automatically

### Before vs After

| Operation | Before (Dual Schedulers) | After (Consolidated) |
|-----------|--------------------------|----------------------|
| Cron triggers | Dedicated scheduler | Dedicated scheduler |
| Manual triggers | Embedded scheduler | Dedicated scheduler (via API) |
| Activity tracking | Only manual triggers | Both cron and manual |
| Schedule CRUD | Backend updates APScheduler directly | Backend updates DB; scheduler syncs |
| APScheduler jobs | Managed by both | Managed by dedicated scheduler only |

### Timeline Dashboard Fix

The consolidation fixes the bug where cron-triggered executions didn't appear on the Timeline dashboard:

**Root Cause**: The dedicated scheduler created `schedule_executions` records but not `agent_activities` records.

**Fix**: Added internal API endpoints for activity tracking. The dedicated scheduler now calls:
- `POST /api/internal/activities/track` - on execution start
- `POST /api/internal/activities/{id}/complete` - on execution end

### Configuration

Backend connects to dedicated scheduler via:
```python
# src/backend/routers/schedules.py
SCHEDULER_URL = os.getenv("SCHEDULER_URL", "http://scheduler:8001")
```

### Database Sync

The dedicated scheduler automatically syncs with the database every 60 seconds:
- New schedules are detected and added to APScheduler
- Deleted schedules are removed from APScheduler
- Updated schedules (cron, timezone, enabled) are re-added

No immediate notification is needed from the backend.

---

## Future Enhancements

1. **APScheduler 4.0 Migration**: When stable, migrate to native distributed scheduling
2. ~~**Activity Stream Integration**: Track executions in unified activity stream~~ ✅ Completed 2026-02-11
3. **Redis Job Store**: Persist jobs across restarts
4. **PostgreSQL Support**: Shared data store for multi-instance coordination
5. **Metrics Export**: Prometheus metrics for monitoring
6. **Force-Sync Endpoint**: Trigger immediate schedule sync without waiting for interval

---

## Revision History

| Date | Change |
|------|--------|
| 2026-03-02 | **MODEL-001 Model Selection**: `Schedule` dataclass has `model` field. `AgentClient.task()` accepts `model` parameter. `create_execution()` records `model_used`. `service.py` passes `schedule.model` to both execution record and agent client. See [model-selection.md](model-selection.md). |
| 2026-03-01 | **Skipped Execution Recording (Issue #46)**: Added APScheduler event listener for `EVENT_JOB_MAX_INSTANCES`. Skipped executions are now recorded in database with `status='skipped'` instead of being silently dropped. Added `create_skipped_execution()` and `create_skipped_process_schedule_execution()` database methods. WebSocket event `schedule_execution_skipped` broadcast for real-time UI. Frontend displays skipped status with purple styling. |
| 2026-02-21 | **Session ID Capture (EXEC-023)**: Added `claude_session_id` capture for "Continue as Chat" support. `AgentTaskMetrics` now includes `session_id` field. `_parse_task_response()` extracts from agent response. `update_execution_status()` stores in database. Scheduled executions now support "Continue as Chat" like manual executions. |
| 2026-02-20 | **Per-Schedule Execution Configuration**: AgentClient.task() now accepts `allowed_tools` parameter. Schedules can specify custom timeout (5m-2h) and tool restrictions. See scheduling.md for full documentation. |
| 2026-02-11 | **Scheduler Consolidation**: Removed embedded scheduler, routed manual triggers through dedicated scheduler, added activity tracking via internal API. Fixes Timeline dashboard missing cron executions. |
| 2026-02-05 | **Trinity Connect Integration**: Added section documenting filtered broadcast callback for external event listeners. Schedule events forwarded to `/ws/events` endpoint. |
| 2026-01-29 | Added periodic schedule sync - new schedules work without restart |
| 2026-01-13 | Initial documentation - standalone scheduler service |

---

**Requirement Reference**: [DEDICATED_SCHEDULER_SERVICE.md](../../requirements/DEDICATED_SCHEDULER_SERVICE.md)
