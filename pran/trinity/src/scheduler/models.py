"""
Pydantic models for the scheduler service.

These are standalone models that mirror the main app's models
but are independent for the scheduler service.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List, Dict, Any
from enum import Enum


class ExecutionStatus(str, Enum):
    """Status of a schedule execution."""
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    CANCELLED = "cancelled"
    SKIPPED = "skipped"  # Added for Issue #46 - records when execution was dropped


class TriggerSource(str, Enum):
    """What triggered the execution."""
    SCHEDULE = "schedule"
    MANUAL = "manual"
    API = "api"


@dataclass
class Schedule:
    """A scheduled task definition."""
    id: str
    agent_name: str
    name: str
    cron_expression: str
    message: str
    enabled: bool
    timezone: str
    description: Optional[str]
    owner_id: Optional[int]
    created_at: datetime
    updated_at: datetime
    last_run_at: Optional[datetime] = None
    next_run_at: Optional[datetime] = None
    timeout_seconds: int = 900  # Default 15 minutes
    allowed_tools: Optional[List[str]] = None  # None = all tools allowed
    model: Optional[str] = None  # Model override (MODEL-001). None = agent default


@dataclass
class ScheduleExecution:
    """A record of a schedule execution."""
    id: str
    schedule_id: str
    agent_name: str
    status: str
    started_at: datetime
    message: str
    triggered_by: str
    completed_at: Optional[datetime] = None
    duration_ms: Optional[int] = None
    response: Optional[str] = None
    error: Optional[str] = None
    context_used: Optional[int] = None
    context_max: Optional[int] = None
    cost: Optional[float] = None
    tool_calls: Optional[str] = None
    execution_log: Optional[str] = None
    # Origin tracking fields (AUDIT-001)
    source_user_id: Optional[int] = None
    source_user_email: Optional[str] = None
    source_agent_name: Optional[str] = None
    source_mcp_key_id: Optional[str] = None
    source_mcp_key_name: Optional[str] = None


@dataclass
class AgentTaskMetrics:
    """Metrics extracted from agent task response."""
    context_used: int = 0
    context_max: int = 200000
    context_percent: float = 0.0
    cost_usd: Optional[float] = None
    tool_calls_json: Optional[str] = None
    execution_log_json: Optional[str] = None
    session_id: Optional[str] = None  # Claude Code session ID for --resume (EXEC-023)


@dataclass
class AgentTaskResponse:
    """Parsed response from agent task endpoint."""
    response_text: str
    metrics: AgentTaskMetrics
    raw_response: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SchedulerStatus:
    """Current status of the scheduler service."""
    running: bool
    jobs_count: int
    last_check: datetime
    uptime_seconds: float
    jobs: List[Dict[str, Any]] = field(default_factory=list)


# =============================================================================
# Process Scheduling Models
# =============================================================================


@dataclass
class ProcessSchedule:
    """
    A scheduled process trigger definition.

    Represents a schedule trigger defined in a process definition.
    When the cron fires, the scheduler executes the process.
    """
    id: str  # Unique schedule ID
    process_id: str  # Process definition ID
    process_name: str  # Process name (denormalized for display)
    trigger_id: str  # Trigger ID from process definition
    cron_expression: str
    enabled: bool
    timezone: str
    description: Optional[str]
    created_at: datetime
    updated_at: datetime
    last_run_at: Optional[datetime] = None
    next_run_at: Optional[datetime] = None


@dataclass
class ProcessScheduleExecution:
    """A record of a process schedule execution."""
    id: str
    schedule_id: str
    process_id: str
    process_name: str
    execution_id: Optional[str]  # Process execution ID returned by backend
    status: str
    started_at: datetime
    triggered_by: str
    completed_at: Optional[datetime] = None
    duration_ms: Optional[int] = None
    error: Optional[str] = None
