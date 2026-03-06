# Process-Driven Thinking - Iteration 3

> **Status**: Domain-Driven Design Integration
> **Date**: 2026-01-14
> **Previous**: `PROCESS_DRIVEN_THINKING_IT2.md`
> **Purpose**: Apply DDD principles to the Trinity Process Engine architecture

---

## Executive Summary

This iteration introduces **Domain-Driven Design (DDD)** as the architectural foundation for Trinity's Process Engine. DDD provides:

1. **Bounded Contexts** — Clear separation between Process Engine and other Trinity components
2. **Ubiquitous Language** — Shared vocabulary with business stakeholders
3. **Domain Events** — Natural fit for process execution and "Informed" agent pattern
4. **Aggregate Design** — Proper encapsulation of process state
5. **Anti-Corruption Layers** — Clean integration with existing Trinity infrastructure

**Key Insight**: Process orchestration IS a complex domain. DDD gives us battle-tested patterns to manage that complexity while keeping the codebase maintainable and testable.

---

## 1. Why DDD for Process Engine

### The Complexity Argument

Process orchestration involves:
- State machines with multiple states and transitions
- Parallel execution with fan-out/fan-in
- Conditional branching (gateways)
- Human-in-the-loop interactions
- Error handling and compensation
- Long-running executions (hours/days)
- Cost tracking and budget enforcement

This is **inherently complex**. DDD provides patterns specifically designed for complex domains.

### The Synergy with BPMN + Event-Driven

| Approach | Contribution |
|----------|--------------|
| **BPMN** | What to build (patterns, concepts) |
| **DDD** | How to structure it (aggregates, events, services) |
| **Event-Driven** | How it communicates (domain events) |

These three approaches reinforce each other naturally.

---

## 2. Bounded Contexts in Trinity

### Context Map

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                            Trinity Platform                                  │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                    PROCESS ENGINE CONTEXT (NEW)                      │   │
│  │                                                                      │   │
│  │  Core Domain:                                                        │   │
│  │  • ProcessDefinition      • Gateway                                  │   │
│  │  • ProcessExecution       • Approval                                 │   │
│  │  • Step                   • Trigger                                  │   │
│  │                                                                      │   │
│  │  Speaks: Process, Step, Execution, Gateway, Approval                 │   │
│  └───────────────────────────────┬──────────────────────────────────────┘   │
│                                  │                                           │
│                    Anti-Corruption Layer (ACL)                               │
│                                  │                                           │
│  ┌───────────────────┐  ┌───────┴───────┐  ┌───────────────────┐           │
│  │ AGENT MANAGEMENT  │  │ SCHEDULING    │  │ COLLABORATION     │           │
│  │ CONTEXT           │  │ CONTEXT       │  │ CONTEXT           │           │
│  │                   │  │               │  │                   │           │
│  │ • Agent           │  │ • Schedule    │  │ • Permission      │           │
│  │ • Container       │  │ • Execution   │  │ • SharedFolder    │           │
│  │ • Template        │  │ • Trigger     │  │ • ActivityStream  │           │
│  │                   │  │               │  │                   │           │
│  │ Speaks: Agent,    │  │ Speaks: Cron, │  │ Speaks: Permission│           │
│  │ Container, MCP    │  │ Job, Trigger  │  │ Share, Activity   │           │
│  └───────────────────┘  └───────────────┘  └───────────────────┘           │
│                                                                             │
│  ┌───────────────────┐  ┌───────────────┐  ┌───────────────────┐           │
│  │ CREDENTIAL        │  │ AUTHENTICATION│  │ OBSERVABILITY     │           │
│  │ CONTEXT           │  │ CONTEXT       │  │ CONTEXT           │           │
│  │                   │  │               │  │                   │           │
│  │ • Credential      │  │ • User        │  │ • Metrics         │           │
│  │ • Secret          │  │ • Session     │  │ • Logs            │           │
│  │ • OAuthFlow       │  │ • ApiKey      │  │ • Telemetry       │           │
│  └───────────────────┘  └───────────────┘  └───────────────────┘           │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Context Relationships

| Upstream Context | Downstream Context | Relationship |
|------------------|-------------------|--------------|
| Process Engine | Agent Management | Customer-Supplier (Process requests agent execution) |
| Process Engine | Scheduling | Conformist (Process uses existing scheduling) |
| Process Engine | Collaboration | Partnership (Shared events, permissions) |
| Agent Management | Process Engine | Published Language (Agent status, capabilities) |

### Why Bounded Contexts Matter

1. **Process Engine doesn't need to know**:
   - How agents are containerized
   - How Docker networking works
   - How credentials are stored
   - How MCP protocol works internally

2. **Process Engine only needs to know**:
   - "Execute task on agent X with message Y"
   - "Agent X is available/unavailable"
   - "Task completed with result Z"

This separation enables independent evolution and testing.

---

## 3. Ubiquitous Language

### Process Engine Vocabulary

| Term | Definition | Used By |
|------|------------|---------|
| **Process** | A repeatable workflow definition with steps, triggers, and outputs | Business, Tech |
| **Step** | A single unit of work within a process | Business, Tech |
| **Execution** | A running instance of a process | Business, Tech |
| **Gateway** | A decision point that routes flow based on conditions | Business, Tech |
| **Approval** | A step requiring human decision before continuing | Business, Tech |
| **Trigger** | What initiates a process (schedule, event, manual) | Business, Tech |
| **Output** | Where results are delivered (Slack, email, file) | Business, Tech |

### Translation at Boundaries

| Process Engine Says | Agent Context Understands |
|---------------------|---------------------------|
| "Execute agent task" | "Chat with agent via MCP" |
| "Agent" | "Container with Claude/Gemini runtime" |
| "Task result" | "Chat response with cost/context" |

| Process Engine Says | Scheduling Context Understands |
|---------------------|--------------------------------|
| "Schedule trigger" | "Cron job" |
| "Timer step" | "Delayed execution" |

---

## 4. Domain Model

### Aggregates

#### ProcessDefinition (Aggregate Root)

```python
@dataclass
class ProcessDefinition:
    """
    Aggregate root for process definitions.
    Immutable once published - new version for changes.
    """
    id: ProcessId
    name: str
    description: str
    version: Version
    status: DefinitionStatus  # draft, published, archived
    
    # Composition
    steps: List[StepDefinition]
    triggers: List[Trigger]
    outputs: List[OutputConfig]
    
    # Metadata
    created_by: UserId
    created_at: datetime
    published_at: Optional[datetime]
    
    # Invariants enforced by aggregate
    def publish(self) -> 'ProcessDefinition':
        """Validate and publish definition"""
        self._validate_no_circular_dependencies()
        self._validate_all_references_exist()
        self._validate_gateways_have_routes()
        return replace(self, status=DefinitionStatus.PUBLISHED, published_at=datetime.now())
    
    def get_entry_steps(self) -> List[StepId]:
        """Steps with no dependencies - where execution starts"""
        ...
    
    def get_dependent_steps(self, step_id: StepId) -> List[StepId]:
        """Steps that depend on given step"""
        ...
```

#### ProcessExecution (Aggregate Root)

```python
@dataclass
class ProcessExecution:
    """
    Aggregate root for process execution state.
    Tracks all runtime state for a single execution.
    """
    id: ExecutionId
    process_id: ProcessId
    process_version: Version
    
    # State
    status: ExecutionStatus  # pending, running, paused, completed, failed, cancelled
    step_executions: Dict[StepId, StepExecution]
    
    # Tracking
    triggered_by: TriggeredBy
    started_at: datetime
    completed_at: Optional[datetime]
    
    # Observability
    total_cost: Money
    total_duration: Optional[Duration]
    
    # Domain events (for event sourcing or publishing)
    _pending_events: List[DomainEvent] = field(default_factory=list)
    
    def start(self) -> None:
        """Start the execution"""
        if self.status != ExecutionStatus.PENDING:
            raise InvalidStateTransition(f"Cannot start from {self.status}")
        self.status = ExecutionStatus.RUNNING
        self.started_at = datetime.now()
        self._pending_events.append(ProcessStarted(
            execution_id=self.id,
            process_id=self.process_id,
            triggered_by=self.triggered_by,
            timestamp=self.started_at
        ))
    
    def complete_step(self, step_id: StepId, output: StepOutput, cost: Money) -> None:
        """Mark a step as completed"""
        step_exec = self.step_executions[step_id]
        step_exec.complete(output, cost)
        self.total_cost = self.total_cost + cost
        self._pending_events.append(StepCompleted(
            execution_id=self.id,
            step_id=step_id,
            output=output,
            cost=cost,
            duration=step_exec.duration
        ))
    
    def fail_step(self, step_id: StepId, error: Error) -> None:
        """Mark a step as failed"""
        step_exec = self.step_executions[step_id]
        step_exec.fail(error)
        self._pending_events.append(StepFailed(
            execution_id=self.id,
            step_id=step_id,
            error=error,
            retry_count=step_exec.retry_count
        ))
    
    def request_approval(self, step_id: StepId, approvers: List[Email], deadline: datetime) -> None:
        """Request human approval for a step"""
        self._pending_events.append(ApprovalRequested(
            execution_id=self.id,
            step_id=step_id,
            approvers=approvers,
            deadline=deadline
        ))
    
    def complete(self) -> None:
        """Mark execution as completed"""
        self.status = ExecutionStatus.COMPLETED
        self.completed_at = datetime.now()
        self.total_duration = Duration(self.completed_at - self.started_at)
        self._pending_events.append(ProcessCompleted(
            execution_id=self.id,
            total_cost=self.total_cost,
            total_duration=self.total_duration
        ))
    
    def get_pending_events(self) -> List[DomainEvent]:
        """Get and clear pending domain events"""
        events = self._pending_events.copy()
        self._pending_events.clear()
        return events
```

### Entities

#### StepDefinition

```python
@dataclass
class StepDefinition:
    """Entity within ProcessDefinition aggregate"""
    id: StepId
    name: str
    type: StepType  # agent_task, human_approval, gateway, timer, notification
    config: StepConfig  # Polymorphic based on type
    dependencies: List[StepId]
    condition: Optional[str]  # Expression like "{{steps.review.decision}} == 'approved'"
```

#### StepExecution

```python
@dataclass
class StepExecution:
    """Entity within ProcessExecution aggregate"""
    step_id: StepId
    status: StepStatus  # pending, ready, running, completed, failed, skipped
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    output: Optional[StepOutput]
    error: Optional[Error]
    retry_count: int = 0
    
    @property
    def duration(self) -> Optional[Duration]:
        if self.started_at and self.completed_at:
            return Duration(self.completed_at - self.started_at)
        return None
    
    def complete(self, output: StepOutput, cost: Money) -> None:
        self.status = StepStatus.COMPLETED
        self.completed_at = datetime.now()
        self.output = output
    
    def fail(self, error: Error) -> None:
        self.status = StepStatus.FAILED
        self.completed_at = datetime.now()
        self.error = error
        self.retry_count += 1
```

### Value Objects

```python
# Identifiers
@dataclass(frozen=True)
class ProcessId:
    value: str

@dataclass(frozen=True)
class ExecutionId:
    value: str

@dataclass(frozen=True)
class StepId:
    value: str

# Domain concepts
@dataclass(frozen=True)
class Version:
    major: int
    minor: int = 0
    
    def __str__(self) -> str:
        return f"{self.major}.{self.minor}"

@dataclass(frozen=True)
class Money:
    amount: Decimal
    currency: str = "USD"
    
    def __add__(self, other: 'Money') -> 'Money':
        assert self.currency == other.currency
        return Money(self.amount + other.amount, self.currency)

@dataclass(frozen=True)
class Duration:
    seconds: int
    
    @classmethod
    def from_timedelta(cls, td: timedelta) -> 'Duration':
        return cls(int(td.total_seconds()))

# Step configurations (polymorphic)
@dataclass(frozen=True)
class AgentTaskConfig:
    agent_name: str
    message: str
    timeout: Duration
    max_cost: Optional[Money] = None

@dataclass(frozen=True)
class HumanApprovalConfig:
    approvers: List[str]
    timeout: Duration
    on_timeout: TimeoutAction  # notify, reject, auto_approve
    artifacts: List[str]

@dataclass(frozen=True)
class GatewayConfig:
    gateway_type: GatewayType  # exclusive, parallel, inclusive
    routes: List[GatewayRoute]

@dataclass(frozen=True)
class GatewayRoute:
    condition: Optional[str]  # None means default route
    target_step: StepId

@dataclass(frozen=True)
class TimerConfig:
    wait_duration: Optional[Duration]
    wait_until: Optional[str]  # Time expression
    timezone: str = "UTC"

# Union type for step config
StepConfig = Union[AgentTaskConfig, HumanApprovalConfig, GatewayConfig, TimerConfig]
```

---

## 5. Domain Events

### Event Definitions

```python
from abc import ABC
from dataclasses import dataclass
from datetime import datetime

class DomainEvent(ABC):
    """Base class for all domain events"""
    timestamp: datetime

# Process lifecycle events
@dataclass
class ProcessStarted(DomainEvent):
    execution_id: ExecutionId
    process_id: ProcessId
    process_name: str
    triggered_by: TriggeredBy
    timestamp: datetime

@dataclass
class ProcessCompleted(DomainEvent):
    execution_id: ExecutionId
    process_id: ProcessId
    total_cost: Money
    total_duration: Duration
    timestamp: datetime

@dataclass
class ProcessFailed(DomainEvent):
    execution_id: ExecutionId
    process_id: ProcessId
    failed_step_id: StepId
    error: Error
    timestamp: datetime

@dataclass
class ProcessCancelled(DomainEvent):
    execution_id: ExecutionId
    cancelled_by: UserId
    reason: str
    timestamp: datetime

# Step lifecycle events
@dataclass
class StepStarted(DomainEvent):
    execution_id: ExecutionId
    step_id: StepId
    step_name: str
    step_type: StepType
    timestamp: datetime

@dataclass
class StepCompleted(DomainEvent):
    execution_id: ExecutionId
    step_id: StepId
    output: StepOutput
    cost: Money
    duration: Duration
    timestamp: datetime

@dataclass
class StepFailed(DomainEvent):
    execution_id: ExecutionId
    step_id: StepId
    error: Error
    retry_count: int
    will_retry: bool
    timestamp: datetime

@dataclass
class StepSkipped(DomainEvent):
    execution_id: ExecutionId
    step_id: StepId
    reason: str  # "condition_not_met", "upstream_failed"
    timestamp: datetime

# Approval events
@dataclass
class ApprovalRequested(DomainEvent):
    execution_id: ExecutionId
    step_id: StepId
    approval_id: ApprovalId
    approvers: List[str]
    deadline: datetime
    artifacts: List[ArtifactRef]
    timestamp: datetime

@dataclass
class ApprovalDecided(DomainEvent):
    execution_id: ExecutionId
    step_id: StepId
    approval_id: ApprovalId
    decision: ApprovalDecision  # approved, rejected, needs_changes
    decided_by: str
    comment: Optional[str]
    timestamp: datetime

@dataclass
class ApprovalTimedOut(DomainEvent):
    execution_id: ExecutionId
    step_id: StepId
    approval_id: ApprovalId
    action_taken: TimeoutAction
    timestamp: datetime

# Gateway events
@dataclass
class GatewayEvaluated(DomainEvent):
    execution_id: ExecutionId
    step_id: StepId
    gateway_type: GatewayType
    selected_routes: List[StepId]
    evaluation_context: Dict[str, Any]
    timestamp: datetime
```

### Event Usage Patterns

#### 1. UI Updates (WebSocket)

```python
class WebSocketEventPublisher:
    async def handle(self, event: DomainEvent):
        if isinstance(event, StepCompleted):
            await self.broadcast({
                "type": "step_completed",
                "execution_id": str(event.execution_id),
                "step_id": str(event.step_id),
                "cost": str(event.cost),
            })
```

#### 2. Informed Agents (Agent Awareness)

```python
class InformedAgentNotifier:
    async def handle(self, event: DomainEvent):
        if isinstance(event, StepCompleted):
            informed_agents = self.get_informed_agents(event.execution_id, event.step_id)
            for agent in informed_agents:
                # Agent receives event to build situational awareness
                await self.notify_agent(agent, event)
```

#### 3. Audit Trail

```python
class AuditLogger:
    def handle(self, event: DomainEvent):
        self.audit_repo.save(AuditEntry(
            event_type=type(event).__name__,
            payload=asdict(event),
            timestamp=event.timestamp
        ))
```

#### 4. External Webhooks

```python
class WebhookPublisher:
    async def handle(self, event: DomainEvent):
        if isinstance(event, ProcessCompleted):
            webhooks = self.get_webhooks_for_process(event.process_id)
            for webhook in webhooks:
                await self.post(webhook.url, event)
```

---

## 6. Domain Services

### DependencyResolver

```python
class DependencyResolver:
    """
    Determines which steps are ready to execute based on
    completed dependencies and conditions.
    """
    
    def __init__(self, expression_evaluator: ExpressionEvaluator):
        self.evaluator = expression_evaluator
    
    def get_ready_steps(
        self, 
        definition: ProcessDefinition, 
        execution: ProcessExecution
    ) -> List[StepId]:
        """Return steps whose dependencies are satisfied"""
        ready = []
        
        for step in definition.steps:
            if self._is_already_processed(step.id, execution):
                continue
            
            if not self._dependencies_satisfied(step, execution):
                continue
            
            if not self._condition_met(step, execution):
                # Mark as skipped
                continue
            
            ready.append(step.id)
        
        return ready
    
    def _dependencies_satisfied(
        self, 
        step: StepDefinition, 
        execution: ProcessExecution
    ) -> bool:
        for dep_id in step.dependencies:
            dep_exec = execution.step_executions.get(dep_id)
            if not dep_exec or dep_exec.status != StepStatus.COMPLETED:
                return False
        return True
    
    def _condition_met(
        self, 
        step: StepDefinition, 
        execution: ProcessExecution
    ) -> bool:
        if not step.condition:
            return True
        context = self._build_context(execution)
        return self.evaluator.evaluate_bool(step.condition, context)
```

### ExpressionEvaluator

```python
class ExpressionEvaluator:
    """
    Evaluates expressions like {{steps.analyze.output.score}} >= 80
    Uses Jinja2-style syntax for familiarity.
    """
    
    def evaluate(self, expression: str, context: Dict[str, Any]) -> Any:
        """Evaluate expression and return result"""
        # Parse {{...}} expressions
        # Resolve variable references
        # Evaluate comparisons
        ...
    
    def evaluate_bool(self, expression: str, context: Dict[str, Any]) -> bool:
        """Evaluate expression expecting boolean result"""
        result = self.evaluate(expression, context)
        return bool(result)
    
    def substitute(self, template: str, context: Dict[str, Any]) -> str:
        """Substitute {{...}} placeholders in template string"""
        # Used for message templates like:
        # "Analyze this data: {{steps.research.output}}"
        ...
```

### GatewayRouter

```python
class GatewayRouter:
    """
    Determines which paths to take at a gateway.
    Implements BPMN gateway semantics.
    """
    
    def __init__(self, expression_evaluator: ExpressionEvaluator):
        self.evaluator = expression_evaluator
    
    def resolve_routes(
        self, 
        gateway: GatewayConfig, 
        context: Dict[str, Any]
    ) -> List[StepId]:
        """Return list of next steps based on gateway type"""
        
        if gateway.gateway_type == GatewayType.EXCLUSIVE:
            # XOR: First matching route wins
            return self._resolve_exclusive(gateway.routes, context)
        
        elif gateway.gateway_type == GatewayType.PARALLEL:
            # AND: All routes taken
            return [route.target_step for route in gateway.routes]
        
        elif gateway.gateway_type == GatewayType.INCLUSIVE:
            # OR: All matching routes taken
            return self._resolve_inclusive(gateway.routes, context)
    
    def _resolve_exclusive(
        self, 
        routes: List[GatewayRoute], 
        context: Dict[str, Any]
    ) -> List[StepId]:
        for route in routes:
            if route.condition is None:  # Default route
                continue
            if self.evaluator.evaluate_bool(route.condition, context):
                return [route.target_step]
        
        # Fall through to default
        default = next((r for r in routes if r.condition is None), None)
        if default:
            return [default.target_step]
        
        raise NoMatchingRoute("No route matched and no default defined")
```

### CostCalculator

```python
class CostCalculator:
    """
    Aggregates and validates costs across execution.
    """
    
    def calculate_total(self, execution: ProcessExecution) -> Money:
        """Sum costs from all completed steps"""
        total = Money(Decimal("0"))
        for step_exec in execution.step_executions.values():
            if step_exec.output and step_exec.output.cost:
                total = total + step_exec.output.cost
        return total
    
    def check_budget(
        self, 
        execution: ProcessExecution, 
        budget: Money
    ) -> BudgetStatus:
        """Check if execution is within budget"""
        current = self.calculate_total(execution)
        if current.amount >= budget.amount:
            return BudgetStatus.EXCEEDED
        elif current.amount >= budget.amount * Decimal("0.8"):
            return BudgetStatus.WARNING
        return BudgetStatus.OK
```

---

## 7. Repositories

### Interfaces (Domain Layer)

```python
from abc import ABC, abstractmethod

class ProcessDefinitionRepository(ABC):
    """Repository interface for process definitions"""
    
    @abstractmethod
    def save(self, definition: ProcessDefinition) -> None:
        """Save or update a process definition"""
        ...
    
    @abstractmethod
    def get_by_id(self, id: ProcessId) -> Optional[ProcessDefinition]:
        """Get definition by ID"""
        ...
    
    @abstractmethod
    def get_by_name(
        self, 
        name: str, 
        version: Optional[Version] = None
    ) -> Optional[ProcessDefinition]:
        """Get definition by name, optionally specific version"""
        ...
    
    @abstractmethod
    def get_latest_version(self, name: str) -> Optional[ProcessDefinition]:
        """Get latest published version of a process"""
        ...
    
    @abstractmethod
    def list_all(self, status: Optional[DefinitionStatus] = None) -> List[ProcessDefinition]:
        """List all definitions, optionally filtered by status"""
        ...


class ProcessExecutionRepository(ABC):
    """Repository interface for process executions"""
    
    @abstractmethod
    def save(self, execution: ProcessExecution) -> None:
        """Save execution state"""
        ...
    
    @abstractmethod
    def get_by_id(self, id: ExecutionId) -> Optional[ProcessExecution]:
        """Get execution by ID"""
        ...
    
    @abstractmethod
    def get_active_for_process(self, process_id: ProcessId) -> List[ProcessExecution]:
        """Get all active executions for a process"""
        ...
    
    @abstractmethod
    def get_history(
        self, 
        process_id: ProcessId, 
        limit: int = 100
    ) -> List[ProcessExecution]:
        """Get execution history for a process"""
        ...
```

### Implementations (Infrastructure Layer)

```python
class SqliteProcessDefinitionRepository(ProcessDefinitionRepository):
    """SQLite implementation for process definitions (durable storage)"""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
    
    def save(self, definition: ProcessDefinition) -> None:
        # Serialize to JSON, store in SQLite
        ...
    
    def get_by_id(self, id: ProcessId) -> Optional[ProcessDefinition]:
        # Query SQLite, deserialize from JSON
        ...


class RedisProcessExecutionRepository(ProcessExecutionRepository):
    """Redis implementation for execution state (fast runtime access)"""
    
    def __init__(self, redis_client: Redis):
        self.redis = redis_client
    
    def save(self, execution: ProcessExecution) -> None:
        # Serialize to JSON, store in Redis with TTL
        key = f"execution:{execution.id.value}"
        self.redis.set(key, self._serialize(execution))
    
    def get_by_id(self, id: ExecutionId) -> Optional[ProcessExecution]:
        key = f"execution:{id.value}"
        data = self.redis.get(key)
        if data:
            return self._deserialize(data)
        return None
```

---

## 8. Anti-Corruption Layer (ACL)

### AgentGateway

```python
class AgentGateway:
    """
    Anti-Corruption Layer between Process Engine and Agent Management context.
    Translates process concepts to agent operations.
    """
    
    def __init__(self, mcp_client: McpClient):
        self.mcp = mcp_client
    
    async def execute_task(
        self, 
        agent_name: str, 
        message: str,
        timeout: Duration
    ) -> AgentTaskResult:
        """
        Execute a task on an agent.
        Shields Process Engine from MCP/container details.
        """
        try:
            response = await self.mcp.chat_with_agent(
                agent_name=agent_name,
                message=message,
                timeout=timeout.seconds
            )
            return AgentTaskResult(
                success=True,
                output=response.content,
                cost=Money(Decimal(str(response.cost))),
                context_used=response.context_used
            )
        except AgentNotAvailable as e:
            return AgentTaskResult(
                success=False,
                error=Error(code="AGENT_UNAVAILABLE", message=str(e))
            )
        except AgentTimeout as e:
            return AgentTaskResult(
                success=False,
                error=Error(code="TIMEOUT", message=str(e))
            )
    
    async def get_agent_status(self, agent_name: str) -> AgentStatus:
        """Check if agent is available"""
        agent = await self.mcp.get_agent(agent_name)
        if agent and agent.status == "running":
            return AgentStatus.AVAILABLE
        return AgentStatus.UNAVAILABLE


@dataclass
class AgentTaskResult:
    success: bool
    output: Optional[str] = None
    cost: Optional[Money] = None
    context_used: Optional[int] = None
    error: Optional[Error] = None
```

### ApprovalGateway

```python
class ApprovalGateway:
    """
    Anti-Corruption Layer for human approval infrastructure.
    """
    
    def __init__(self, approval_repo: ApprovalRepository, notifier: NotificationService):
        self.repo = approval_repo
        self.notifier = notifier
    
    async def request_approval(
        self,
        execution_id: ExecutionId,
        step_id: StepId,
        config: HumanApprovalConfig
    ) -> ApprovalId:
        """Create approval request and notify approvers"""
        approval = Approval(
            id=ApprovalId.generate(),
            execution_id=execution_id,
            step_id=step_id,
            approvers=config.approvers,
            deadline=datetime.now() + config.timeout.to_timedelta(),
            status=ApprovalStatus.PENDING
        )
        self.repo.save(approval)
        
        # Send notifications
        for approver in config.approvers:
            await self.notifier.send_approval_request(approver, approval)
        
        return approval.id
    
    async def get_decision(self, approval_id: ApprovalId) -> Optional[ApprovalDecision]:
        """Check if approval has been decided"""
        approval = self.repo.get_by_id(approval_id)
        if approval and approval.status != ApprovalStatus.PENDING:
            return approval.decision
        return None
```

### SchedulerGateway

```python
class SchedulerGateway:
    """
    Anti-Corruption Layer for scheduling infrastructure.
    """
    
    def __init__(self, scheduler_service: SchedulerService):
        self.scheduler = scheduler_service
    
    async def schedule_timer(
        self,
        execution_id: ExecutionId,
        step_id: StepId,
        config: TimerConfig,
        callback: Callable
    ) -> TimerId:
        """Schedule a timer for delayed step execution"""
        if config.wait_duration:
            run_at = datetime.now() + config.wait_duration.to_timedelta()
        else:
            run_at = self._parse_time_expression(config.wait_until, config.timezone)
        
        return await self.scheduler.schedule_once(
            run_at=run_at,
            callback=callback,
            args=(execution_id, step_id)
        )
```

---

## 9. Application Layer

### Commands and Handlers

```python
# Commands (intentions)
@dataclass
class TriggerProcess:
    process_name: str
    version: Optional[Version] = None
    triggered_by: TriggeredBy = TriggeredBy.MANUAL
    input_data: Dict[str, Any] = field(default_factory=dict)

@dataclass
class CancelExecution:
    execution_id: ExecutionId
    cancelled_by: UserId
    reason: str

@dataclass
class SubmitApproval:
    approval_id: ApprovalId
    decision: ApprovalDecision
    decided_by: str
    comment: Optional[str] = None


# Command Handlers
class TriggerProcessHandler:
    def __init__(
        self,
        definition_repo: ProcessDefinitionRepository,
        execution_repo: ProcessExecutionRepository,
        coordinator: ExecutionCoordinator,
        event_publisher: EventPublisher
    ):
        self.definitions = definition_repo
        self.executions = execution_repo
        self.coordinator = coordinator
        self.events = event_publisher
    
    async def handle(self, command: TriggerProcess) -> ExecutionId:
        # Load definition
        definition = self.definitions.get_by_name(
            command.process_name, 
            command.version
        )
        if not definition:
            raise ProcessNotFound(command.process_name)
        
        # Create execution
        execution = ProcessExecution.create(
            process_id=definition.id,
            process_version=definition.version,
            triggered_by=command.triggered_by
        )
        
        # Start execution
        execution.start()
        self.executions.save(execution)
        
        # Publish events
        for event in execution.get_pending_events():
            await self.events.publish(event)
        
        # Begin execution (async)
        await self.coordinator.execute(definition, execution)
        
        return execution.id
```

### Queries

```python
@dataclass
class GetExecutionStatus:
    execution_id: ExecutionId

@dataclass
class GetProcessHistory:
    process_name: str
    limit: int = 100

@dataclass  
class GetPendingApprovals:
    approver_email: str


class GetExecutionStatusHandler:
    def __init__(self, execution_repo: ProcessExecutionRepository):
        self.executions = execution_repo
    
    def handle(self, query: GetExecutionStatus) -> ExecutionStatusDTO:
        execution = self.executions.get_by_id(query.execution_id)
        if not execution:
            raise ExecutionNotFound(query.execution_id)
        
        return ExecutionStatusDTO(
            id=str(execution.id),
            status=execution.status.value,
            progress=self._calculate_progress(execution),
            current_step=self._get_current_step(execution),
            total_cost=str(execution.total_cost),
            started_at=execution.started_at.isoformat(),
            step_statuses=[
                StepStatusDTO(
                    id=str(step_id),
                    status=step_exec.status.value,
                    duration=step_exec.duration.seconds if step_exec.duration else None
                )
                for step_id, step_exec in execution.step_executions.items()
            ]
        )
```

---

## 10. Proposed Directory Structure

```
src/backend/
├── domain/
│   └── process/                          # Process Engine Bounded Context
│       ├── __init__.py
│       ├── model/
│       │   ├── __init__.py
│       │   ├── aggregates.py             # ProcessDefinition, ProcessExecution
│       │   ├── entities.py               # StepDefinition, StepExecution
│       │   ├── value_objects.py          # ProcessId, Money, Duration, configs
│       │   ├── events.py                 # Domain events
│       │   └── exceptions.py             # Domain exceptions
│       ├── services/
│       │   ├── __init__.py
│       │   ├── dependency_resolver.py
│       │   ├── expression_evaluator.py
│       │   ├── gateway_router.py
│       │   └── cost_calculator.py
│       └── repositories.py               # Repository interfaces
│
├── application/
│   └── process/
│       ├── __init__.py
│       ├── commands.py                   # Command definitions
│       ├── queries.py                    # Query definitions
│       ├── handlers/
│       │   ├── __init__.py
│       │   ├── trigger_process.py
│       │   ├── cancel_execution.py
│       │   └── submit_approval.py
│       └── dto.py                        # Data transfer objects
│
├── infrastructure/
│   └── process/
│       ├── __init__.py
│       ├── persistence/
│       │   ├── __init__.py
│       │   ├── sqlite_definition_repo.py
│       │   └── redis_execution_repo.py
│       ├── gateways/
│       │   ├── __init__.py
│       │   ├── agent_gateway.py          # ACL to Agent context
│       │   ├── approval_gateway.py       # ACL to Approval infrastructure
│       │   └── scheduler_gateway.py      # ACL to Scheduling context
│       ├── event_publisher.py            # WebSocket, webhooks
│       └── coordinator.py                # ExecutionCoordinator implementation
│
└── api/
    └── routers/
        └── processes.py                  # HTTP endpoints
```

---

## 11. Pragmatic Integration with Existing Trinity

### ⚠️ Important: This is NOT a Full Rewrite

The DDD approach described in this document is **additive, not invasive**. We are NOT proposing to refactor all of Trinity to use DDD. The existing codebase stays as-is.

### Current Trinity Structure (Layered Architecture)

Trinity currently uses a standard, pragmatic FastAPI structure:

```
src/backend/
├── routers/          # HTTP endpoints
├── services/         # Business logic (including agent_service/)
├── db/               # Database access functions
├── models.py         # Pydantic request/response models
└── db_models.py      # Database models
```

This is **not DDD** — it's layered architecture. And it works well for Trinity's current features.

### Recommended Approach: DDD Only for Process Engine

The Process Engine would be a **new, isolated module** alongside existing code:

```
src/backend/
├── routers/              # Existing - UNCHANGED
├── services/             # Existing - UNCHANGED  
├── db/                   # Existing - UNCHANGED
├── models.py             # Existing - UNCHANGED
│
└── process_engine/       # NEW - DDD structured (isolated)
    ├── domain/
    ├── application/
    ├── infrastructure/
    └── api/
```

**Key points:**
- Existing code is NOT touched
- Process Engine lives in its own folder
- Integration happens via thin ACL gateways that import existing services

### Minimal Changes to Existing Code

| File | Change Required | What Changes |
|------|-----------------|--------------|
| `routers/*` | ❌ No | Untouched |
| `services/*` | ❌ No | Untouched (just imported by ACL) |
| `db/*` | ❌ No | Untouched |
| `models.py` | ❌ No | Untouched |
| `main.py` | ✅ Minimal | Add 2 lines to mount new router |
| `database.py` | ✅ Minimal | Add migrations for new tables |

### ACL Connects to Existing Services

The Process Engine talks to existing Trinity via **thin gateway wrappers**:

```python
# process_engine/infrastructure/gateways/agent_gateway.py
from services.agent_client import AgentClient  # Import EXISTING

class AgentGateway:
    def __init__(self):
        self.client = AgentClient()  # Reuse EXISTING
    
    async def execute_task(self, agent_name: str, message: str):
        # Translate and delegate - no changes to AgentClient
        return await self.client.chat(agent_name, message)
```

### Alternative: Match Existing Style Completely

If even a separate `process_engine/` folder feels too different, we can match the existing pattern:

```
src/backend/
├── routers/
│   └── processes.py          # NEW - same style as others
├── services/
│   └── process_service/      # NEW - like agent_service/
│       ├── __init__.py
│       ├── definitions.py
│       ├── execution.py
│       ├── coordinator.py
│       └── handlers.py
├── db/
│   └── processes.py          # NEW - same style as others
└── models.py                  # Add new Pydantic models
```

This uses DDD **concepts** internally (aggregates, events, services) but keeps **folder structure** consistent with existing Trinity conventions.

### Team Communication Framing

When discussing with the team:

> "We're adding a **new Process Engine module** using some DDD patterns because process orchestration is complex enough to warrant it. **Nothing existing changes.** It's just a new folder that imports existing services where needed."

This is:
- ✅ **Additive, not rewrite** — no existing code changes
- ✅ **Isolated, not invasive** — bounded to new folder
- ✅ **Pragmatic, not dogmatic** — can adapt folder structure to match existing style
- ✅ **Low risk** — if it doesn't work out, it's contained

### Recommendation

**Start with the simpler approach** (match existing style):
1. Add `routers/processes.py`
2. Add `services/process_service/` folder
3. Add `db/processes.py`

Use DDD **concepts** internally but keep **folder structure** consistent. If complexity grows, we can always extract to a dedicated module later.

---

## 12. Benefits Summary

| DDD Benefit | How It Helps Process Engine |
|-------------|----------------------------|
| **Bounded Contexts** | Process Engine isolated from agent/credential/scheduling internals |
| **Ubiquitous Language** | Clear communication with business stakeholders |
| **Aggregates** | ProcessExecution encapsulates all execution state, enforces invariants |
| **Domain Events** | Natural fit for UI updates, agent awareness, audit, webhooks |
| **Value Objects** | Immutable, type-safe domain concepts (Money, Duration, StepConfig) |
| **Repositories** | Testable, swappable persistence (Redis, SQLite, etc.) |
| **ACL** | Clean integration with existing Trinity without coupling |
| **Domain Services** | Complex logic (dependency resolution, routing) isolated and testable |

---

## 12. Open Questions

1. **Event Sourcing**: Should ProcessExecution be fully event-sourced (rebuild from events)?
   - Pro: Perfect audit trail, time-travel debugging
   - Con: Complexity, eventual consistency
   
2. **CQRS**: Separate read/write models for execution status?
   - Pro: Optimized reads, scale independently
   - Con: Complexity for current scale
   
3. **Saga Pattern**: Use explicit saga for long-running processes?
   - Pro: Clear compensation, distributed transactions
   - Con: Another pattern to implement

4. **Domain Events Persistence**: Store all events or just current state?
   - Recommendation: Start with state, add event log for audit

---

## 13. Next Steps

1. [ ] Implement core value objects (ProcessId, Money, Duration)
2. [ ] Implement ProcessDefinition aggregate
3. [ ] Implement ProcessExecution aggregate with domain events
4. [ ] Implement DependencyResolver service
5. [ ] Implement repositories (SQLite + Redis)
6. [ ] Implement AgentGateway ACL
7. [ ] Create IT4 with implementation details

---

## Document History

| Date | Change |
|------|--------|
| 2026-01-14 | DDD integration design (IT3) |
| 2026-01-14 | Added Section 11: Pragmatic Integration — clarifying this is additive, not a rewrite |
