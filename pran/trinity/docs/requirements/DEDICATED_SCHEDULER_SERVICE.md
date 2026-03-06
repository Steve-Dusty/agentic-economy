# Dedicated Scheduler Service Requirements

> **Status**: Planning
> **Priority**: HIGH
> **Target**: Phase 10
> **Created**: 2026-01-13
> **Last Updated**: 2026-01-13

---

## Problem Statement

The current scheduler implementation has a critical flaw: when running multiple uvicorn workers in production (`--workers 2`), each worker initializes its own APScheduler instance with an in-memory job store. This causes scheduled tasks to execute **multiple times** (once per worker).

**Current Architecture (Broken)**:
```
┌─────────────────────────────────────────┐
│           Backend Container              │
│  ┌─────────────┐  ┌──────────────────┐  │
│  │  Worker 1   │  │  APScheduler 1   │──┼──→ Executes job
│  └─────────────┘  └──────────────────┘  │
│  ┌─────────────┐  ┌──────────────────┐  │
│  │  Worker 2   │  │  APScheduler 2   │──┼──→ Executes SAME job (duplicate!)
│  └─────────────┘  └──────────────────┘  │
└─────────────────────────────────────────┘
```

**Evidence**: `docker-compose.prod.yml:72` runs `--workers 2`

---

## Solution: Dedicated Scheduler Service

Separate the scheduler into an independent service that:
1. Runs as a **single process** (no worker duplication)
2. Uses **Redis for job storage** (survives restarts)
3. Uses **distributed locks** for exactly-once execution
4. Can be monitored and scaled independently

**Target Architecture**:
```
┌──────────────────────────────────────────────────────────────────┐
│                        Trinity Platform                           │
├──────────────────────────────────────────────────────────────────┤
│                                                                    │
│  ┌─────────────────┐    ┌─────────────────┐    ┌──────────────┐  │
│  │    Backend      │    │   Scheduler     │    │   Workers    │  │
│  │   (API only)    │    │   (singleton)   │    │  (optional)  │  │
│  │   N workers     │    │   1 replica     │    │   N replicas │  │
│  └────────┬────────┘    └────────┬────────┘    └──────┬───────┘  │
│           │                      │                     │          │
│           └──────────────────────┼─────────────────────┘          │
│                                  │                                 │
│                          ┌───────▼───────┐                        │
│                          │     Redis     │                        │
│                          │  - Job Store  │                        │
│                          │  - Locks      │                        │
│                          │  - Events     │                        │
│                          └───────────────┘                        │
└──────────────────────────────────────────────────────────────────┘
```

---

## Research Summary

### APScheduler Version Analysis

| Version | Distributed Support | Status | Recommendation |
|---------|---------------------|--------|----------------|
| **3.11.2** (current) | ❌ No coordination between schedulers | Stable | Keep for now |
| **4.0.0a6** | ✅ Built-in via Redis event broker + data store | Alpha | **Migrate when stable** |

**Key APScheduler 4.0 Features**:
- `RedisEventBroker` for multi-instance coordination
- `SchedulerRole.scheduler` vs `SchedulerRole.worker` separation
- Lease-based job acquisition (prevents duplicates)
- Native async support with AnyIO

**Sources**:
- [APScheduler 4.0 API Reference](https://apscheduler.readthedocs.io/en/master/api.html)
- [APScheduler Migration Guide](https://apscheduler.readthedocs.io/en/master/migration.html)
- [APScheduler PyPI](https://pypi.org/project/APScheduler/)
- [APScheduler 4.0 Progress Tracking](https://github.com/agronholm/apscheduler/issues/465)

### APScheduler 4.0 Breaking Changes

When migrating to v4.0, these changes must be addressed:

1. **API Changes**:
   - `add_job()` → `add_schedule()`
   - `BlockingScheduler` → `Scheduler`
   - `start()` → `run_until_stopped()` or `start_in_background()`

2. **Timezone**:
   - `pytz` → `zoneinfo` (stdlib)

3. **Cron Weekday**:
   - v3.x: Monday=0, Sunday=6
   - v4.0: Sunday=0, Saturday=6 (ISO standard)

4. **Configuration**:
   - `configure()` method removed
   - All config via constructor kwargs

**Example Migration**:
```python
# APScheduler 3.x (current)
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.jobstores.memory import MemoryJobStore

scheduler = AsyncIOScheduler(jobstores={'default': MemoryJobStore()})
scheduler.add_job(execute_schedule, CronTrigger(...), id=job_id)
scheduler.start()

# APScheduler 4.0 (target)
from apscheduler import AsyncScheduler, SchedulerRole
from apscheduler.datastores.sqlalchemy import SQLAlchemyDataStore
from apscheduler.eventbrokers.redis import RedisEventBroker

async with AsyncScheduler(
    data_store=SQLAlchemyDataStore("postgresql+asyncpg://..."),
    event_broker=RedisEventBroker("redis://redis:6379"),
    role=SchedulerRole.both
) as scheduler:
    await scheduler.add_schedule(execute_schedule, CronTrigger(...), id=job_id)
    await scheduler.run_until_stopped()
```

### Distributed Lock Options

For Phase 1 (immediate fix with APScheduler 3.x), use Redis locks:

| Library | Status | Auto-Renewal | Reentrant | Recommendation |
|---------|--------|--------------|-----------|----------------|
| **python-redis-lock** | Inactive maintenance | ✅ Yes | ❌ No | **Use for simplicity** |
| **redis-py Lock** | Active (built-in) | ❌ No | ❌ No | Alternative |
| **redlock-py** | Inactive | ❌ No | ❌ No | For multi-master Redis |
| **pottery** | Active | ✅ Yes | ✅ Yes | Consider for complex needs |

**Sources**:
- [Redis Distributed Locks Documentation](https://redis.io/docs/latest/develop/clients/patterns/distributed-locks/)
- [python-redis-lock Documentation](https://python-redis-lock.readthedocs.io/en/latest/readme.html)
- [python-redis-lock GitHub](https://github.com/ionelmc/python-redis-lock)

**Recommended Pattern** (python-redis-lock):
```python
import redis_lock
from redis import Redis

conn = Redis.from_url("redis://redis:6379")

async def _execute_schedule(self, schedule_id: str):
    lock_name = f"schedule:{schedule_id}"

    # Auto-renewal prevents lock expiry during long executions
    with redis_lock.Lock(conn, lock_name, expire=300, auto_renewal=True):
        # Only one worker executes this
        schedule = db.get_schedule(schedule_id)
        # ... execution logic ...
```

**Alternative** (redis-py built-in):
```python
from redis import Redis

redis_client = Redis.from_url("redis://redis:6379")

async def _execute_schedule(self, schedule_id: str):
    lock = redis_client.lock(f"schedule:{schedule_id}", timeout=300)

    if not lock.acquire(blocking=False):
        logger.info(f"Schedule {schedule_id} already running on another worker")
        return

    try:
        # ... execution logic ...
    finally:
        lock.release()
```

---

## Implementation Phases

### Phase 1: Immediate Fix (Stopgap)

**Goal**: Stop duplicate executions in production NOW.

**Changes**:
1. Add distributed lock to `_execute_schedule()` in `scheduler_service.py`
2. Change production to single worker OR add lock

**Option A - Single Worker** (simplest):
```yaml
# docker-compose.prod.yml
command: uvicorn main:app --host 0.0.0.0 --port 8000  # Remove --workers 2
```

**Option B - Distributed Lock** (better):
```python
# scheduler_service.py
import redis_lock

def _execute_schedule(self, schedule_id: str):
    lock = redis_lock.Lock(
        self.redis_client,
        f"schedule_exec:{schedule_id}",
        expire=600,  # 10 min max
        auto_renewal=True
    )

    if not lock.acquire(blocking=False):
        logger.info(f"Schedule {schedule_id} already being executed")
        return

    try:
        # existing execution logic
    finally:
        lock.release()
```

**Files to modify**:
- `src/backend/services/scheduler_service.py`
- `docker-compose.prod.yml` (if using Option A)
- `docker/backend/requirements.txt` (add python-redis-lock)

**Estimated effort**: 2-4 hours

---

### Phase 2: Dedicated Scheduler Service

**Goal**: Clean separation of concerns, independent scaling.

**New Service Structure**:
```
src/
├── backend/           # API-only (no scheduler)
│   └── main.py        # Remove scheduler_service.initialize()
├── scheduler/         # NEW - dedicated scheduler
│   ├── __init__.py
│   ├── main.py        # Entry point
│   ├── service.py     # SchedulerService (moved from backend)
│   └── config.py      # Scheduler-specific config
```

**Docker Compose Changes**:
```yaml
services:
  backend:
    # Remove scheduler initialization
    command: uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4
    environment:
      - SCHEDULER_ENABLED=false  # Disable embedded scheduler

  scheduler:
    build:
      context: .
      dockerfile: docker/scheduler/Dockerfile
    container_name: trinity-scheduler
    restart: unless-stopped
    deploy:
      replicas: 1  # ALWAYS single instance
    environment:
      - REDIS_URL=redis://redis:6379
      - DATABASE_URL=sqlite:///data/trinity.db
    volumes:
      - trinity-data:/data
    depends_on:
      - redis
    networks:
      - trinity-network
    healthcheck:
      test: ["CMD", "python", "-c", "import requests; requests.get('http://localhost:8001/health')"]
      interval: 30s
      timeout: 10s
      retries: 3
```

**Scheduler Service Entry Point**:
```python
# src/scheduler/main.py
import asyncio
from scheduler.service import SchedulerService
from config import REDIS_URL, DATABASE_PATH

async def main():
    service = SchedulerService(
        redis_url=REDIS_URL,
        database_path=DATABASE_PATH
    )

    # Optional: minimal health check server
    # await start_health_server(port=8001)

    await service.run_forever()

if __name__ == "__main__":
    asyncio.run(main())
```

**Communication Pattern**:
```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Backend   │────▶│    Redis    │◀────│  Scheduler  │
│  (API)      │     │  - Pub/Sub  │     │  (cron)     │
└─────────────┘     │  - Queues   │     └─────────────┘
                    └─────────────┘
```

- Backend writes schedule CRUD to SQLite
- Backend publishes "schedule_updated" events to Redis
- Scheduler subscribes to events, reloads affected schedules
- Scheduler executes tasks via agent HTTP API

**Files to create**:
- `src/scheduler/main.py`
- `src/scheduler/service.py`
- `src/scheduler/config.py`
- `docker/scheduler/Dockerfile`

**Files to modify**:
- `src/backend/main.py` - Remove scheduler initialization
- `docker-compose.yml` - Add scheduler service
- `docker-compose.prod.yml` - Add scheduler service

**Estimated effort**: 1-2 days

---

### Phase 3: APScheduler 4.0 Migration (Future)

**Goal**: Native distributed scheduling with official support.

**Prerequisites**:
- APScheduler 4.0 reaches stable release
- PostgreSQL migration (for shared data store)

**Benefits**:
- Built-in distributed coordination
- No custom locking needed
- Lease-based job acquisition
- Better async support

**Migration Steps**:
1. Wait for APScheduler 4.0 stable
2. Add PostgreSQL to infrastructure
3. Migrate scheduler to 4.0 API
4. Test in staging environment
5. Deploy with feature flag

**Estimated effort**: 3-5 days (when 4.0 is stable)

---

## Technical Specifications

### Redis Keys (Phase 1-2)

| Key Pattern | Type | Purpose | TTL |
|-------------|------|---------|-----|
| `schedule_exec:{schedule_id}` | String | Execution lock | 600s |
| `schedule_events` | Pub/Sub | CRUD notifications | N/A |
| `scheduler:heartbeat` | String | Health indicator | 60s |

### Database Schema (No Changes)

Current schema in `database.py` remains unchanged:
- `agent_schedules` - Schedule definitions
- `schedule_executions` - Execution history

### API Endpoints (Phase 2)

Scheduler service exposes minimal health API:

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Health check |
| GET | `/status` | Scheduler status, job count |

### Monitoring & Alerting

**Metrics to track**:
- `scheduler_jobs_total` - Total scheduled jobs
- `scheduler_executions_total` - Executions by status
- `scheduler_execution_duration_seconds` - Execution time histogram
- `scheduler_lock_acquisitions_total` - Lock acquisition attempts
- `scheduler_lock_failures_total` - Lock acquisition failures

**Alerts to configure**:
- Scheduler heartbeat missing > 2 minutes
- Execution failure rate > 10%
- Lock acquisition failures > 5/minute

---

## Dependencies

### New Dependencies (Phase 1)

```
# docker/backend/requirements.txt
python-redis-lock>=4.0.0
```

### New Dependencies (Phase 2)

```
# docker/scheduler/requirements.txt
apscheduler>=3.11.0
croniter>=2.0.1
pytz>=2024.1
redis>=5.0.0
python-redis-lock>=4.0.0
httpx>=0.27.0
```

### Future Dependencies (Phase 3)

```
# When APScheduler 4.0 is stable
apscheduler>=4.0.0
asyncpg>=0.29.0  # PostgreSQL async driver
```

---

## Testing Strategy

### Phase 1 Testing

```python
# tests/test_scheduler_locking.py
import pytest
import asyncio
from unittest.mock import patch, MagicMock

async def test_duplicate_execution_prevented():
    """Verify only one worker executes a schedule."""
    execution_count = 0

    async def mock_execute():
        nonlocal execution_count
        execution_count += 1
        await asyncio.sleep(0.5)

    # Simulate two workers trying to execute same schedule
    await asyncio.gather(
        scheduler_service._execute_schedule("schedule-123"),
        scheduler_service._execute_schedule("schedule-123"),
    )

    assert execution_count == 1, "Schedule should only execute once"
```

### Phase 2 Testing

```python
# tests/test_scheduler_service.py
async def test_scheduler_receives_events():
    """Verify scheduler reloads on backend events."""
    # Create schedule via API
    # Verify scheduler picks it up via Redis pub/sub

async def test_scheduler_survives_restart():
    """Verify schedules persist across restarts."""
    # Create schedule
    # Restart scheduler container
    # Verify schedule still fires
```

---

## Rollback Plan

### Phase 1 Rollback
- Remove distributed lock code
- Revert to single-worker production config

### Phase 2 Rollback
- Stop scheduler service container
- Re-enable scheduler in backend (`SCHEDULER_ENABLED=true`)
- Backend handles scheduling again (single worker mode)

---

## Success Criteria

- [ ] **Phase 1**: No duplicate executions in production logs for 7 days
- [ ] **Phase 2**: Scheduler runs independently with 99.9% uptime
- [ ] **Phase 2**: Backend can scale to 4+ workers without scheduling issues
- [ ] **Phase 3**: Successful migration to APScheduler 4.0 with zero missed schedules

---

## References

### Documentation
- [APScheduler 3.x User Guide](https://apscheduler.readthedocs.io/en/3.x/userguide.html)
- [APScheduler 4.0 API Reference](https://apscheduler.readthedocs.io/en/master/api.html)
- [APScheduler Migration Guide](https://apscheduler.readthedocs.io/en/master/migration.html)
- [Redis Distributed Locks](https://redis.io/docs/latest/develop/clients/patterns/distributed-locks/)
- [python-redis-lock Documentation](https://python-redis-lock.readthedocs.io/en/latest/readme.html)

### GitHub Issues & Discussions
- [APScheduler: Distributed Scheduling Discussion](https://github.com/agronholm/apscheduler/discussions/612)
- [APScheduler: Distributed Lock Issue](https://github.com/agronholm/apscheduler/issues/169)
- [APScheduler 4.0 Progress](https://github.com/agronholm/apscheduler/issues/465)
- [Flask-APScheduler Multiple Workers Issue](https://github.com/viniciuschiele/flask-apscheduler/issues/230)

### Articles
- [12 Redis Locking Patterns](https://medium.com/@navidbarsalari/the-twelve-redis-locking-patterns-every-distributed-systems-engineer-should-know-06f16dfe7375)
- [Martin Kleppmann's Redlock Analysis](http://martin.kleppmann.com/2016/02/08/how-to-do-distributed-locking.html)

---

## Appendix: APScheduler 4.0 Example

Full example of APScheduler 4.0 with Redis event broker (for Phase 3):

```python
# src/scheduler/service_v4.py
from apscheduler import AsyncScheduler, SchedulerRole
from apscheduler.datastores.sqlalchemy import SQLAlchemyDataStore
from apscheduler.eventbrokers.redis import RedisEventBroker
from apscheduler.triggers.cron import CronTrigger
from zoneinfo import ZoneInfo

async def create_scheduler():
    """Create APScheduler 4.0 instance with distributed support."""

    # PostgreSQL for shared state (required for multi-instance)
    data_store = SQLAlchemyDataStore(
        "postgresql+asyncpg://user:pass@localhost/trinity",
        schema="scheduler"
    )

    # Redis for event coordination
    event_broker = RedisEventBroker("redis://redis:6379")

    return AsyncScheduler(
        data_store=data_store,
        event_broker=event_broker,
        identity="scheduler-1",  # Unique per instance
        role=SchedulerRole.both,  # Can also separate scheduler/worker
    )

async def run_scheduler():
    async with create_scheduler() as scheduler:
        # Add a schedule
        await scheduler.add_schedule(
            execute_agent_task,
            CronTrigger(hour=9, minute=0, timezone=ZoneInfo("UTC")),
            id="daily-report",
            args=["agent-name", "Generate daily report"]
        )

        # Run until stopped
        await scheduler.run_until_stopped()

# Entry point
if __name__ == "__main__":
    import asyncio
    asyncio.run(run_scheduler())
```

---

**Document Version**: 1.0
**Author**: Claude Code
**Review Status**: Pending
