# Process-Driven Thinking - Iteration 5

> **Status**: Scale, Reliability & Enterprise Architecture
> **Date**: 2026-01-15
> **Previous**: `PROCESS_DRIVEN_THINKING_IT4.md`
> **Purpose**: Address operational scale, reliability patterns, multi-team usage, and enterprise requirements

---

## Executive Summary

Previous iterations established **what** to build (IT1-2), **how** to structure it (IT3), and **how users interact** with it (IT4). This iteration addresses **how it operates at scale** — when dozens of processes run concurrently across multiple teams with varying reliability requirements.

**Key Concerns Addressed**:
1. **Concurrent Execution at Scale** — Dozens of processes, resource contention
2. **Reliability & Recovery** — Crashes, retries, state consistency
3. **User Onboarding** — Empty vs running processes, progressive capability
4. **Multi-Department Processes** — Cross-team workflows, ownership boundaries
5. **Access Management** — Who can do what, audit trails
6. **Compliance** — Data retention, audit requirements, regulatory needs

**Priority Recommendation**: Focus first on **Reliability** (P0), then **Access Management** (P1), then **Scale Optimizations** (P2). Multi-department and compliance features are P3 unless specific customer requirements demand otherwise.

---

## 1. Concurrent Execution at Scale

### 1.1 The Problem

With dozens of processes running simultaneously:
- Agent resources become contested (same agent in multiple processes)
- System resources (CPU, memory, Redis connections) need management
- Execution ordering and fairness becomes important
- Observability becomes overwhelming without aggregation

### 1.2 Resource Contention Model

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  Resource Hierarchy                                                          │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │  Platform Resources (Shared)                                         │    │
│  │  • Redis connections (pool limit: ~50)                               │    │
│  │  • SQLite write locks (one at a time)                                │    │
│  │  • WebSocket connections per client                                   │    │
│  │  • Backend memory/CPU                                                 │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │  Agent Resources (Per-Agent)                                         │    │
│  │  • Each agent: 1 concurrent task (queue for more)                    │    │
│  │  • Agent context window (200K tokens typical)                         │    │
│  │  • Agent memory/filesystem                                           │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │  Process Resources (Per-Execution)                                   │    │
│  │  • Execution state in Redis (~10KB typical)                          │    │
│  │  • Event history in SQLite (~1KB per event)                          │    │
│  │  • Step outputs in filesystem (variable)                              │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 1.3 Agent Contention Strategy

**Problem**: Agent X is requested by Process A and Process B simultaneously.

**Solution**: Agent-level queuing with fairness

```python
class AgentTaskQueue:
    """
    Manages task submissions to agents with fairness across processes.
    """

    async def submit_task(
        self,
        agent_name: str,
        execution_id: ExecutionId,
        step_id: StepId,
        message: str,
        priority: TaskPriority = TaskPriority.NORMAL,
    ) -> TaskHandle:
        """
        Submit task to agent queue.

        Fairness: Round-robin across executions prevents one process
        from starving others when using shared agents.
        """
        task = AgentTask(
            agent=agent_name,
            execution_id=execution_id,
            step_id=step_id,
            message=message,
            priority=priority,
            submitted_at=datetime.now(),
        )

        # Priority queue with fairness weighting
        # High priority: immediate
        # Normal: round-robin by execution_id
        await self._enqueue(task)

        return TaskHandle(task_id=task.id, queue_position=self._position(task))


class TaskPriority(Enum):
    HIGH = "high"      # Human-approval follow-ups, retries
    NORMAL = "normal"  # Regular step execution
    LOW = "low"        # Background/batch processes
```

### 1.4 Execution Concurrency Limits

**Recommendation**: Configurable limits at multiple levels

```yaml
# config/process-engine.yaml
execution:
  # Global limits
  max_concurrent_executions: 50          # Total running processes
  max_concurrent_steps_per_execution: 5  # Parallel branches limit

  # Per-process limits (can override in process definition)
  default_max_instances: 3               # Same process running simultaneously

  # Queue behavior when limits reached
  queue_overflow: "queue"                # queue | reject | delay
  queue_timeout: "30m"                   # How long to wait in queue
```

**Process-level override**:

```yaml
# In process definition
name: high-priority-alerts
config:
  max_concurrent_instances: 10  # Allow more of this process
  priority: high                # Jump the queue
```

### 1.5 Observability at Scale

**Problem**: With 50 concurrent processes, individual execution views don't scale.

**Solution**: Aggregate dashboard with drill-down

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  Process Engine Health                                        Last 1 hour   │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌─ Summary ────────────────────────────────────────────────────────────┐   │
│  │  Running: 23 │ Queued: 7 │ Completed: 145 │ Failed: 3 │ Success: 97% │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
│  ┌─ Resource Utilization ───────────────────────────────────────────────┐   │
│  │  Agents:  ████████████████████░░░░░░░░░░  18/24 busy                  │   │
│  │  Redis:   ████████░░░░░░░░░░░░░░░░░░░░░░  35/100 connections          │   │
│  │  Queue:   ███░░░░░░░░░░░░░░░░░░░░░░░░░░░  7 tasks waiting             │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
│  ┌─ Hot Spots (Bottlenecks) ────────────────────────────────────────────┐   │
│  │  ⚠️ Agent "researcher" - 5 tasks queued (avg wait: 3m 20s)            │   │
│  │  ⚠️ Human Approval - 12 pending > 1 hour                              │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
│  ┌─ By Process Type ────────────────────────────────────────────────────┐   │
│  │  Process              Running  Queued  Completed  Failed   Avg Time  │   │
│  │  ───────────────────────────────────────────────────────────────────│   │
│  │  Weekly Report            2       0        12       0       45m      │   │
│  │  Customer Onboarding      8       3        45       1       12m      │   │
│  │  Content Pipeline         5       2        34       2       2h       │   │
│  │  Alert Processing        8       2        54       0       30s      │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Reliability & Recovery

### 2.1 Failure Categories

| Category | Example | Impact | Recovery Strategy |
|----------|---------|--------|-------------------|
| **Transient** | Network timeout, rate limit | Step fails | Automatic retry with backoff |
| **Agent** | Agent crashed, OOM | Step fails | Restart agent, retry step |
| **Platform** | Backend restart, Redis flush | All running | State recovery, resume |
| **Permanent** | Invalid config, missing agent | Execution stuck | Manual intervention |
| **Logical** | Infinite loop, budget exceeded | Execution stuck | Circuit breaker, alerts |

### 2.2 State Persistence Strategy

**Principle**: Every state change is persisted before proceeding.

```python
class ExecutionCoordinator:
    """
    Reliability-first execution coordination.
    """

    async def execute_step(
        self,
        execution: ProcessExecution,
        step: StepDefinition,
    ) -> None:
        # 1. Mark step as started (persist)
        execution.start_step(step.id)
        await self.execution_repo.save(execution)
        await self.publish_event(StepStarted(...))

        try:
            # 2. Execute (may take minutes/hours)
            result = await self.handler.execute(step)

            # 3. Mark step as completed (persist)
            execution.complete_step(step.id, result)
            await self.execution_repo.save(execution)
            await self.publish_event(StepCompleted(...))

        except Exception as e:
            # 4. Mark step as failed (persist)
            execution.fail_step(step.id, error=str(e))
            await self.execution_repo.save(execution)
            await self.publish_event(StepFailed(...))
            raise
```

### 2.3 Recovery on Backend Restart

**Scenario**: Backend crashes or restarts while executions are running.

**Solution**: Recovery scan on startup

```python
class ExecutionRecoveryService:
    """
    Recovers in-progress executions after platform restart.
    """

    async def recover_on_startup(self) -> RecoveryReport:
        """
        Called during backend initialization.
        """
        report = RecoveryReport()

        # Find all executions that were running
        running = await self.execution_repo.get_by_status(
            status=[ExecutionStatus.RUNNING, ExecutionStatus.PENDING]
        )

        for execution in running:
            try:
                recovery_action = self._determine_recovery(execution)

                if recovery_action == RecoveryAction.RESUME:
                    # Continue from last completed step
                    await self.coordinator.resume(execution)
                    report.resumed.append(execution.id)

                elif recovery_action == RecoveryAction.RETRY_STEP:
                    # Re-execute the interrupted step
                    await self.coordinator.retry_current_step(execution)
                    report.retried.append(execution.id)

                elif recovery_action == RecoveryAction.MARK_FAILED:
                    # Too old or unrecoverable
                    execution.fail("Recovery timeout exceeded")
                    await self.execution_repo.save(execution)
                    report.failed.append(execution.id)

            except Exception as e:
                logger.error(f"Recovery failed for {execution.id}: {e}")
                report.errors.append((execution.id, str(e)))

        return report

    def _determine_recovery(self, execution: ProcessExecution) -> RecoveryAction:
        """
        Decide how to recover based on state and age.
        """
        age = datetime.now() - execution.updated_at

        # Too old - probably should fail
        if age > timedelta(hours=24):
            return RecoveryAction.MARK_FAILED

        # Check current step status
        current_step = execution.get_current_step()

        if current_step.status == StepStatus.RUNNING:
            # Step was interrupted - retry it
            return RecoveryAction.RETRY_STEP
        else:
            # Between steps - just resume
            return RecoveryAction.RESUME
```

### 2.4 Retry Policies

**Per-step retry configuration**:

```yaml
steps:
  - id: call-external-api
    type: agent_task
    agent: api-caller
    message: "Fetch data from external service"

    retry:
      max_attempts: 3
      backoff: exponential      # linear | exponential | fixed
      initial_delay: 10s
      max_delay: 5m
      retryable_errors:
        - TIMEOUT
        - RATE_LIMIT
        - AGENT_UNAVAILABLE
      non_retryable_errors:
        - INVALID_CONFIG
        - BUDGET_EXCEEDED
```

### 2.5 Circuit Breaker Pattern

**Problem**: A failing agent causes cascading failures across processes.

**Solution**: Agent-level circuit breaker

```python
class AgentCircuitBreaker:
    """
    Prevents cascading failures when an agent is unhealthy.
    """

    def __init__(
        self,
        failure_threshold: int = 5,      # Failures before opening
        recovery_timeout: Duration = Duration.from_minutes(5),
        half_open_requests: int = 3,     # Test requests when recovering
    ):
        self.states: Dict[str, CircuitState] = {}

    async def call(
        self,
        agent_name: str,
        task: Callable,
    ) -> Any:
        state = self._get_state(agent_name)

        if state.status == CircuitStatus.OPEN:
            # Check if recovery timeout passed
            if state.can_attempt_recovery():
                state.status = CircuitStatus.HALF_OPEN
            else:
                raise CircuitOpenError(
                    f"Agent {agent_name} circuit is open. "
                    f"Recovery in {state.time_until_recovery()}"
                )

        try:
            result = await task()
            self._record_success(agent_name)
            return result

        except Exception as e:
            self._record_failure(agent_name, e)
            raise
```

### 2.6 Execution Checkpointing

**For long-running processes**: Save intermediate state that can survive even total data loss.

```python
class CheckpointService:
    """
    Saves execution checkpoints to durable storage for disaster recovery.
    """

    async def save_checkpoint(
        self,
        execution: ProcessExecution,
        trigger: CheckpointTrigger,  # step_completed | periodic | manual
    ) -> CheckpointId:
        """
        Save full execution state to filesystem/S3/etc.
        """
        checkpoint = Checkpoint(
            id=CheckpointId.generate(),
            execution_id=execution.id,
            timestamp=datetime.now(),
            trigger=trigger,
            state=execution.to_dict(),
            completed_outputs=self._gather_outputs(execution),
        )

        # Write to durable storage (filesystem, S3, etc.)
        path = self._checkpoint_path(checkpoint)
        await self.storage.write_json(path, checkpoint.to_dict())

        return checkpoint.id

    async def restore_from_checkpoint(
        self,
        checkpoint_id: CheckpointId,
    ) -> ProcessExecution:
        """
        Restore execution from checkpoint (disaster recovery).
        """
        checkpoint = await self.storage.read_json(self._checkpoint_path_by_id(checkpoint_id))
        execution = ProcessExecution.from_dict(checkpoint["state"])

        # Restore outputs to expected locations
        for step_id, output in checkpoint["completed_outputs"].items():
            await self.output_storage.restore(execution.id, step_id, output)

        return execution
```

---

## 3. User Onboarding Patterns

### 3.1 Onboarding Scenarios

| Scenario | User State | Goal | UX Approach |
|----------|------------|------|-------------|
| **First Process** | No processes exist | Create first workflow | Guided wizard with templates |
| **Empty Process** | Definition exists, never run | Trigger first execution | "Test Run" with input assistance |
| **Running Process** | Execution in progress | Understand what's happening | Live view with explanations |
| **Mature Process** | History exists | Monitor, optimize, debug | Analytics and comparison |

### 3.2 First-Time User Experience

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  Welcome to Trinity Processes                                                │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  Processes automate multi-step workflows using your AI agents.               │
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                                                                     │    │
│  │  Start with a Template                           Create from Scratch│    │
│  │  ─────────────────────                           ─────────────────── │    │
│  │                                                                     │    │
│  │  ┌─────────────────┐  ┌─────────────────┐       ┌─────────────────┐│    │
│  │  │ 📊 Data Report  │  │ 📝 Content      │       │ ✏️ Blank Canvas ││    │
│  │  │                 │  │    Pipeline     │       │                 ││    │
│  │  │ Gather → Analyze│  │ Write → Review  │       │ Start with an   ││    │
│  │  │ → Report        │  │ → Publish       │       │ empty process   ││    │
│  │  │                 │  │                 │       │                 ││    │
│  │  │ [Use Template]  │  │ [Use Template]  │       │ [Create Empty]  ││    │
│  │  └─────────────────┘  └─────────────────┘       └─────────────────┘│    │
│  │                                                                     │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                                                              │
│  📖 Need help? Check the [Getting Started Guide] or [Watch Tutorial]        │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 3.3 Template System

**Bundled templates** (already implemented in E12-01):
- `content-review` — AI analysis + human approval
- `data-analysis` — Multi-agent data pipeline
- `customer-support` — Escalation with notifications

**Template customization wizard**:

```
Step 1: Choose Template           Step 2: Configure Agents
────────────────────────          ─────────────────────────
[x] Data Analysis Report          Which agents should be used?

                                  Data Collector: [researcher ▾]
                                  Analyst:        [analyst ▾]
                                  Report Writer:  [writer ▾]

Step 3: Set Trigger               Step 4: Review & Create
─────────────────────             ────────────────────────
How should this process start?
                                  Name: weekly-sales-report
( ) Manual only                   Trigger: Every Monday 9am
(x) On schedule                   Agents: researcher, analyst, writer
    [Every Monday at 9:00 AM]     Steps: 3
( ) Via webhook
                                  [Create Process]
```

### 3.4 First Execution Guidance

When a user triggers their first execution:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  🎉 First Run: Weekly Sales Report                                           │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  This is your first execution of this process. Here's what will happen:     │
│                                                                              │
│  ┌─ Step 1 ─────────────────────────────────────────────────────────────┐   │
│  │ 📥 Gather Data                                                        │   │
│  │ Agent "researcher" will collect sales data from your configured      │   │
│  │ sources. This usually takes 2-5 minutes.                              │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                      ↓                                                       │
│  ┌─ Step 2 ─────────────────────────────────────────────────────────────┐   │
│  │ 📊 Analyze Trends                                                     │   │
│  │ Agent "analyst" will identify patterns and insights.                  │   │
│  │ This usually takes 5-10 minutes.                                      │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                      ↓                                                       │
│  ┌─ Step 3 ─────────────────────────────────────────────────────────────┐   │
│  │ 📝 Generate Report                                                    │   │
│  │ Agent "writer" will create the final report.                          │   │
│  │ This usually takes 3-5 minutes.                                       │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
│  Total estimated time: 10-20 minutes                                        │
│  Estimated cost: $2-4                                                        │
│                                                                              │
│  [Start Execution]  [Cancel]                                                 │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 4. Multi-Department Processes

### 4.1 The Challenge

Organizations have:
- **Multiple teams** with different agents, processes, and permissions
- **Cross-team workflows** that span department boundaries
- **Data isolation** requirements (team A shouldn't see team B's data)
- **Shared resources** (some agents/processes used by everyone)

### 4.2 Ownership Model

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  Ownership Hierarchy                                                         │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  Organization                                                                │
│  └── Department/Team (ownership boundary)                                    │
│       ├── Agents (owned by team)                                             │
│       ├── Processes (owned by team)                                          │
│       │    └── Executions (inherit process ownership)                        │
│       └── Shared Resources (explicit sharing)                                │
│                                                                              │
│  Sharing Model:                                                              │
│  • Agents can be shared across teams (read-only or full access)              │
│  • Processes can reference agents from other teams (with permission)         │
│  • Executions are private to the team that triggered them                    │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 4.3 Cross-Team Process Pattern

**Scenario**: Marketing creates content, Legal reviews it, Brand approves it.

```yaml
name: cross-team-content-approval
owner: marketing-team

steps:
  - id: create-content
    type: agent_task
    agent: marketing/content-writer    # Marketing's agent
    message: "Create blog post about {{input.topic}}"

  - id: legal-review
    type: human_approval
    depends_on: [create-content]
    assignees:
      - team: legal-team              # Cross-team assignment
        role: compliance-reviewer
    title: "Legal Compliance Review"
    artifacts:
      - "{{steps.create-content.output.draft_path}}"

  - id: brand-review
    type: human_approval
    depends_on: [legal-review]
    assignees:
      - team: brand-team
        role: brand-manager
    title: "Brand Guidelines Review"

  - id: publish
    type: agent_task
    depends_on: [brand-review]
    agent: marketing/publisher
    condition: "{{steps.brand-review.decision}} == 'approved'"
```

### 4.4 Visibility Rules

| Viewer | Can See | Cannot See |
|--------|---------|------------|
| Process owner team | All executions, all steps | Nothing hidden |
| Shared agent owner | Steps using their agent | Other steps |
| Approval assignee | Step requiring their approval + context | Unrelated steps |
| Organization admin | All processes, all executions | Full visibility |

### 4.5 Handoff Events

When a process crosses team boundaries, emit explicit handoff events:

```python
@dataclass
class ProcessHandoff(DomainEvent):
    """Fired when process responsibility moves between teams."""
    execution_id: ExecutionId
    from_team: TeamId
    to_team: TeamId
    step_id: StepId
    handoff_type: HandoffType  # approval_request | agent_task | notification
    context: Dict[str, Any]    # What the receiving team needs to know
    timestamp: datetime
```

---

## 5. Access Management

### 5.1 Permission Model

**RBAC with resource-level overrides**:

```python
class ProcessPermission(Enum):
    # Definition permissions
    PROCESS_CREATE = "process:create"
    PROCESS_READ = "process:read"
    PROCESS_UPDATE = "process:update"
    PROCESS_DELETE = "process:delete"
    PROCESS_PUBLISH = "process:publish"

    # Execution permissions
    EXECUTION_TRIGGER = "execution:trigger"
    EXECUTION_VIEW = "execution:view"
    EXECUTION_CANCEL = "execution:cancel"
    EXECUTION_RETRY = "execution:retry"

    # Approval permissions
    APPROVAL_DECIDE = "approval:decide"
    APPROVAL_DELEGATE = "approval:delegate"

    # Admin permissions
    ADMIN_VIEW_ALL = "admin:view_all"
    ADMIN_MANAGE_LIMITS = "admin:manage_limits"
```

### 5.2 Role Definitions

| Role | Permissions | Typical User |
|------|-------------|--------------|
| **Process Designer** | CREATE, READ, UPDATE, DELETE, PUBLISH | Developer, automation engineer |
| **Process Operator** | READ, TRIGGER, VIEW, CANCEL, RETRY | Ops team, power user |
| **Process Viewer** | READ, VIEW (own executions) | Business user |
| **Approver** | VIEW (relevant steps), DECIDE | Manager, reviewer |
| **Admin** | All permissions | Platform admin |

### 5.3 API Authorization

```python
class ProcessAuthorization:
    """
    Authorization layer for process operations.
    """

    def can_trigger_process(
        self,
        user: User,
        process: ProcessDefinition,
    ) -> AuthorizationResult:
        # Check basic permission
        if not user.has_permission(ProcessPermission.EXECUTION_TRIGGER):
            return AuthorizationResult.denied("Missing trigger permission")

        # Check process-specific ACL
        if process.allowed_users and user.id not in process.allowed_users:
            return AuthorizationResult.denied("Not in process allowed users")

        # Check team ownership
        if process.owner_team != user.team and not process.is_shared:
            return AuthorizationResult.denied("Process belongs to another team")

        # Check rate limits
        if self._exceeds_rate_limit(user, process):
            return AuthorizationResult.denied("Rate limit exceeded")

        return AuthorizationResult.allowed()

    def can_view_execution(
        self,
        user: User,
        execution: ProcessExecution,
    ) -> AuthorizationResult:
        # Owner team can always view
        if execution.owner_team == user.team:
            return AuthorizationResult.allowed()

        # Approvers can view steps assigned to them
        if self._is_approver_for_execution(user, execution):
            return AuthorizationResult.allowed(scope="approval_steps_only")

        # Admins can view all
        if user.has_permission(ProcessPermission.ADMIN_VIEW_ALL):
            return AuthorizationResult.allowed()

        return AuthorizationResult.denied("No access to this execution")
```

### 5.4 Audit Trail

Every action is logged for compliance:

```python
@dataclass
class AuditEntry:
    """Immutable audit log entry."""
    id: AuditId
    timestamp: datetime
    actor: str                      # user email or "system"
    action: str                     # "process.trigger", "approval.decide", etc.
    resource_type: str              # "process", "execution", "approval"
    resource_id: str
    details: Dict[str, Any]         # Action-specific context
    ip_address: Optional[str]
    user_agent: Optional[str]

    # Compliance fields
    data_classification: str        # "public", "internal", "confidential"
    retention_days: int             # How long to keep this entry


class AuditService:
    """
    Append-only audit log service.
    """

    async def log(
        self,
        actor: str,
        action: str,
        resource: Any,
        details: Dict[str, Any] = None,
        request: Optional[Request] = None,
    ) -> AuditId:
        entry = AuditEntry(
            id=AuditId.generate(),
            timestamp=datetime.now(timezone.utc),
            actor=actor,
            action=action,
            resource_type=type(resource).__name__.lower(),
            resource_id=str(resource.id),
            details=details or {},
            ip_address=request.client.host if request else None,
            user_agent=request.headers.get("user-agent") if request else None,
            data_classification=self._classify(resource),
            retention_days=self._retention_for(action),
        )

        # Append-only storage (never update or delete)
        await self.audit_repo.append(entry)

        return entry.id
```

---

## 6. Compliance Considerations

### 6.1 Data Retention

| Data Type | Default Retention | Configurable | Rationale |
|-----------|-------------------|--------------|-----------|
| Process definitions | Forever | No | Version history important |
| Execution state | 90 days | Yes | Balance storage vs debugging |
| Step outputs | 30 days | Yes | Can be large |
| Audit logs | 7 years | Per policy | Compliance requirement |
| Cost records | 7 years | Per policy | Financial records |

### 6.2 Data Classification in Processes

Process definitions can declare data sensitivity:

```yaml
name: customer-data-processing
data_classification: confidential

# Data handling rules applied automatically:
# - Outputs encrypted at rest
# - Audit logs include data access
# - Execution details redacted in cross-team views
# - Longer retention for compliance

steps:
  - id: process-customer-data
    type: agent_task
    agent: data-processor
    data_handling:
      input_classification: pii        # Personal Identifiable Information
      output_classification: internal
      encryption_required: true
```

### 6.3 Compliance Reporting

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  Compliance Dashboard                                            Export ↓   │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  Data Processing Summary (Last 30 Days)                                      │
│  ────────────────────────────────────                                        │
│  • 1,245 executions processed                                                │
│  • 23 contained PII data                                                     │
│  • 0 policy violations detected                                              │
│  • 100% audit coverage                                                       │
│                                                                              │
│  Access Audit                                                                │
│  ────────────                                                                │
│  • 45 users accessed process data                                            │
│  • 12 cross-team data shares                                                 │
│  • 3 elevated privilege uses (admin)                                         │
│                                                                              │
│  Data Retention Status                                                       │
│  ────────────────────                                                        │
│  • 892 executions pending cleanup (> 90 days)                                │
│  • 156 GB eligible for archival                                              │
│  • [Run Cleanup] [Export Before Delete]                                      │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 7. Priority Recommendations

### 7.1 Priority Matrix

| Feature | Complexity | Business Value | Priority |
|---------|------------|----------------|----------|
| **Reliability/Recovery** | Medium | Critical | **P0** |
| **Basic Access Control** | Low | High | **P1** |
| **Audit Logging** | Low | High (compliance) | **P1** |
| **Execution Limits** | Low | Medium | **P1** |
| **Agent Circuit Breaker** | Medium | Medium | **P2** |
| **Multi-Team Ownership** | High | Medium | **P2** |
| **Cross-Team Processes** | High | Medium | **P3** |
| **Advanced Compliance** | High | Context-dependent | **P3** |
| **Aggregate Dashboard** | Medium | Nice-to-have | **P3** |

### 7.2 Recommended Implementation Order

**Phase 1: Reliability Foundation** (P0)
1. Execution recovery on startup
2. Per-step retry configuration
3. State persistence before every transition
4. Basic health checks

**Phase 2: Access & Audit** (P1)
1. Role-based permissions
2. Audit logging for all operations
3. Execution concurrency limits
4. Basic rate limiting

**Phase 3: Scale Optimization** (P2)
1. Agent task queuing with fairness
2. Circuit breaker for failing agents
3. Checkpointing for long processes
4. Team-based ownership

**Phase 4: Enterprise Features** (P3)
1. Cross-team process handoffs
2. Compliance dashboards
3. Data classification enforcement
4. Advanced retention policies

---

## 8. Open Questions

1. **Multi-tenancy**: Should Trinity support fully isolated tenants (separate databases) or is team-level isolation sufficient?

2. **Process versioning during execution**: If a process definition is updated mid-execution, what happens? (Current: use version at start. Future: migration path?)

3. **Cost allocation**: When a cross-team process runs, who pays for the agents? (Options: triggering team, agent owner, split)

4. **Disaster recovery**: What's the RTO/RPO requirement? Current architecture supports minutes, not seconds.

5. **Geographic distribution**: Any requirements for running processes in specific regions for data residency?

---

## 9. Summary

| Area | Current State | This Iteration Adds |
|------|---------------|---------------------|
| **Scale** | Single-process focus | Concurrency limits, queuing, aggregate views |
| **Reliability** | Basic persistence | Recovery, retry policies, circuit breakers |
| **Onboarding** | YAML editor | Templates, wizards, first-run guidance |
| **Multi-team** | Single owner | Team boundaries, cross-team handoffs |
| **Access** | Basic auth | RBAC, resource-level permissions |
| **Compliance** | Minimal | Audit logs, retention, data classification |

---

## 10. Next Steps

1. [ ] Implement execution recovery on backend startup
2. [ ] Add configurable retry policies to step definitions
3. [ ] Design RBAC schema for permissions
4. [ ] Implement audit logging infrastructure
5. [ ] Create aggregate health dashboard mockup
6. [ ] Create IT6 with implementation specifications for P0/P1 items

---

## Document History

| Date | Change |
|------|--------|
| 2026-01-15 | Scale, reliability, and enterprise architecture (IT5) |
