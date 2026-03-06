"""
Unit tests for Domain Events and Event Bus.

Tests for: Domain events, InMemoryEventBus
Reference: E15-01 Acceptance Criteria
"""

import asyncio
import pytest
from datetime import datetime, timezone
from decimal import Decimal

from services.process_engine.domain import (
    ProcessId,
    ExecutionId,
    StepId,
    Duration,
    Money,
    StepType,
    ProcessStarted,
    ProcessCompleted,
    ProcessFailed,
    ProcessCancelled,
    StepStarted,
    StepCompleted,
    StepFailed,
    StepSkipped,
    ApprovalRequested,
    ApprovalDecided,
    DomainEvent,
)
from services.process_engine.events import InMemoryEventBus


# =============================================================================
# Domain Event Tests
# =============================================================================


class TestProcessEvents:
    """Tests for process lifecycle events."""

    def test_process_started_creation(self):
        """ProcessStarted event can be created with required fields."""
        event = ProcessStarted(
            execution_id=ExecutionId.generate(),
            process_id=ProcessId.generate(),
            process_name="test-process",
            triggered_by="api",
        )
        
        assert event.event_type == "ProcessStarted"
        assert event.process_name == "test-process"
        assert event.triggered_by == "api"
        assert event.timestamp is not None

    def test_process_started_to_dict(self):
        """ProcessStarted serializes to dict correctly."""
        exec_id = ExecutionId.generate()
        proc_id = ProcessId.generate()
        
        event = ProcessStarted(
            execution_id=exec_id,
            process_id=proc_id,
            process_name="test-process",
        )
        
        d = event.to_dict()
        
        assert d["event_type"] == "ProcessStarted"
        assert d["execution_id"] == str(exec_id)
        assert d["process_id"] == str(proc_id)
        assert d["process_name"] == "test-process"
        assert "timestamp" in d

    def test_process_completed_with_cost_and_duration(self):
        """ProcessCompleted includes cost and duration."""
        event = ProcessCompleted(
            execution_id=ExecutionId.generate(),
            process_id=ProcessId.generate(),
            process_name="test-process",
            total_cost=Money.from_float(1.50),
            total_duration=Duration.from_minutes(5),
            output_data={"result": "success"},
        )
        
        d = event.to_dict()
        
        assert d["total_cost"] == "$1.50"
        assert d["total_duration_seconds"] == 300
        assert d["output_data"] == {"result": "success"}

    def test_process_failed_includes_error(self):
        """ProcessFailed includes error information."""
        event = ProcessFailed(
            execution_id=ExecutionId.generate(),
            process_id=ProcessId.generate(),
            process_name="test-process",
            failed_step_id=StepId("failing-step"),
            error_message="Something went wrong",
            error_code="ERR_001",
        )
        
        d = event.to_dict()
        
        assert d["failed_step_id"] == "failing-step"
        assert d["error_message"] == "Something went wrong"
        assert d["error_code"] == "ERR_001"

    def test_process_cancelled_includes_reason(self):
        """ProcessCancelled includes cancellation info."""
        event = ProcessCancelled(
            execution_id=ExecutionId.generate(),
            process_id=ProcessId.generate(),
            process_name="test-process",
            cancelled_by="user@example.com",
            reason="No longer needed",
        )
        
        d = event.to_dict()
        
        assert d["cancelled_by"] == "user@example.com"
        assert d["reason"] == "No longer needed"


class TestStepEvents:
    """Tests for step lifecycle events."""

    def test_step_started_creation(self):
        """StepStarted event can be created."""
        event = StepStarted(
            execution_id=ExecutionId.generate(),
            step_id=StepId("research"),
            step_name="Research Topic",
            step_type=StepType.AGENT_TASK,
        )
        
        d = event.to_dict()
        
        assert d["event_type"] == "StepStarted"
        assert d["step_id"] == "research"
        assert d["step_type"] == "agent_task"

    def test_step_completed_with_output(self):
        """StepCompleted includes output and metrics."""
        event = StepCompleted(
            execution_id=ExecutionId.generate(),
            step_id=StepId("research"),
            step_name="Research",
            output={"summary": "Findings..."},
            cost=Money.from_float(0.05),
            duration=Duration.from_seconds(45),
        )
        
        d = event.to_dict()
        
        assert d["output"] == {"summary": "Findings..."}
        assert d["cost"] == "$0.05"
        assert d["duration_seconds"] == 45

    def test_step_failed_with_retry_info(self):
        """StepFailed includes retry information."""
        event = StepFailed(
            execution_id=ExecutionId.generate(),
            step_id=StepId("failing-step"),
            step_name="Failing Step",
            error_message="Timeout exceeded",
            retry_count=2,
            will_retry=True,
        )
        
        d = event.to_dict()
        
        assert d["retry_count"] == 2
        assert d["will_retry"] is True

    def test_step_skipped_with_reason(self):
        """StepSkipped includes skip reason."""
        event = StepSkipped(
            execution_id=ExecutionId.generate(),
            step_id=StepId("conditional-step"),
            step_name="Conditional Step",
            reason="condition_not_met",
        )
        
        d = event.to_dict()
        
        assert d["reason"] == "condition_not_met"


class TestApprovalEvents:
    """Tests for approval events."""

    def test_approval_requested(self):
        """ApprovalRequested includes approval details."""
        event = ApprovalRequested(
            execution_id=ExecutionId.generate(),
            step_id=StepId("review"),
            step_name="Manager Review",
            title="Document Review Required",
            description="Please review the attached document",
            assignees=["manager@example.com", "lead@example.com"],
        )
        
        d = event.to_dict()
        
        assert d["title"] == "Document Review Required"
        assert len(d["assignees"]) == 2

    def test_approval_decided(self):
        """ApprovalDecided includes decision details."""
        event = ApprovalDecided(
            execution_id=ExecutionId.generate(),
            step_id=StepId("review"),
            decision="approved",
            decided_by="manager@example.com",
            comment="Looks good!",
        )
        
        d = event.to_dict()
        
        assert d["decision"] == "approved"
        assert d["decided_by"] == "manager@example.com"
        assert d["comment"] == "Looks good!"


# =============================================================================
# Event Bus Tests
# =============================================================================


class TestInMemoryEventBus:
    """Tests for InMemoryEventBus."""

    @pytest.fixture
    def bus(self):
        """Create a fresh event bus."""
        return InMemoryEventBus()

    @pytest.fixture
    def sample_event(self):
        """Create a sample event."""
        return ProcessStarted(
            execution_id=ExecutionId.generate(),
            process_id=ProcessId.generate(),
            process_name="test-process",
        )

    @pytest.mark.asyncio
    async def test_publish_with_no_handlers(self, bus, sample_event):
        """Publishing with no handlers doesn't raise."""
        await bus.publish(sample_event)
        # Should complete without error

    @pytest.mark.asyncio
    async def test_subscribe_and_receive_event(self, bus, sample_event):
        """Subscribed handler receives published event."""
        received = []
        
        async def handler(event: DomainEvent):
            received.append(event)
        
        bus.subscribe(ProcessStarted, handler)
        await bus.publish(sample_event)
        await bus.wait_for_pending()
        
        assert len(received) == 1
        assert received[0] is sample_event

    @pytest.mark.asyncio
    async def test_handler_receives_correct_event_type(self, bus):
        """Handler only receives subscribed event types."""
        started_received = []
        completed_received = []
        
        async def started_handler(event: DomainEvent):
            started_received.append(event)
        
        async def completed_handler(event: DomainEvent):
            completed_received.append(event)
        
        bus.subscribe(ProcessStarted, started_handler)
        bus.subscribe(ProcessCompleted, completed_handler)
        
        # Publish ProcessStarted
        await bus.publish(ProcessStarted(
            execution_id=ExecutionId.generate(),
            process_id=ProcessId.generate(),
            process_name="test",
        ))
        
        await bus.wait_for_pending()
        
        assert len(started_received) == 1
        assert len(completed_received) == 0

    @pytest.mark.asyncio
    async def test_subscribe_all(self, bus):
        """Global handler receives all events."""
        received = []
        
        async def handler(event: DomainEvent):
            received.append(event)
        
        bus.subscribe_all(handler)
        
        exec_id = ExecutionId.generate()
        proc_id = ProcessId.generate()
        
        # Publish different event types
        await bus.publish(ProcessStarted(
            execution_id=exec_id,
            process_id=proc_id,
            process_name="test",
        ))
        await bus.publish(StepStarted(
            execution_id=exec_id,
            step_id=StepId("step-a"),
            step_name="Step A",
            step_type=StepType.AGENT_TASK,
        ))
        
        await bus.wait_for_pending()
        
        assert len(received) == 2

    @pytest.mark.asyncio
    async def test_multiple_handlers_same_event(self, bus, sample_event):
        """Multiple handlers can subscribe to same event type."""
        received1 = []
        received2 = []
        
        async def handler1(event: DomainEvent):
            received1.append(event)
        
        async def handler2(event: DomainEvent):
            received2.append(event)
        
        bus.subscribe(ProcessStarted, handler1)
        bus.subscribe(ProcessStarted, handler2)
        
        await bus.publish(sample_event)
        await bus.wait_for_pending()
        
        assert len(received1) == 1
        assert len(received2) == 1

    @pytest.mark.asyncio
    async def test_unsubscribe(self, bus, sample_event):
        """Unsubscribed handler no longer receives events."""
        received = []
        
        async def handler(event: DomainEvent):
            received.append(event)
        
        bus.subscribe(ProcessStarted, handler)
        await bus.publish(sample_event)
        await bus.wait_for_pending()
        
        assert len(received) == 1
        
        bus.unsubscribe(ProcessStarted, handler)
        await bus.publish(sample_event)
        await bus.wait_for_pending()
        
        # Should still be 1
        assert len(received) == 1

    @pytest.mark.asyncio
    async def test_unsubscribe_all_handler(self, bus, sample_event):
        """Can unsubscribe global handler."""
        received = []
        
        async def handler(event: DomainEvent):
            received.append(event)
        
        bus.subscribe_all(handler)
        await bus.publish(sample_event)
        await bus.wait_for_pending()
        
        bus.unsubscribe_all(handler)
        await bus.publish(sample_event)
        await bus.wait_for_pending()
        
        assert len(received) == 1

    @pytest.mark.asyncio
    async def test_clear(self, bus, sample_event):
        """Clear removes all subscriptions."""
        received = []
        
        async def handler(event: DomainEvent):
            received.append(event)
        
        bus.subscribe(ProcessStarted, handler)
        bus.subscribe_all(handler)
        
        bus.clear()
        
        await bus.publish(sample_event)
        await bus.wait_for_pending()
        
        assert len(received) == 0
        assert bus.handler_count == 0

    @pytest.mark.asyncio
    async def test_handler_error_doesnt_stop_others(self, bus, sample_event):
        """Error in one handler doesn't stop other handlers."""
        received = []
        
        async def failing_handler(event: DomainEvent):
            raise Exception("Handler error")
        
        async def good_handler(event: DomainEvent):
            received.append(event)
        
        bus.subscribe(ProcessStarted, failing_handler)
        bus.subscribe(ProcessStarted, good_handler)
        
        await bus.publish(sample_event)
        await bus.wait_for_pending()
        
        # Good handler should still receive event
        assert len(received) == 1

    def test_handler_count(self, bus):
        """handler_count returns correct count."""
        async def handler1(event): pass
        async def handler2(event): pass
        
        assert bus.handler_count == 0
        
        bus.subscribe(ProcessStarted, handler1)
        assert bus.handler_count == 1
        
        bus.subscribe(ProcessCompleted, handler2)
        assert bus.handler_count == 2
        
        bus.subscribe_all(handler1)
        assert bus.handler_count == 3

    def test_get_handlers_for(self, bus):
        """get_handlers_for returns correct handlers."""
        async def type_handler(event): pass
        async def global_handler(event): pass
        
        bus.subscribe(ProcessStarted, type_handler)
        bus.subscribe_all(global_handler)
        
        handlers = bus.get_handlers_for(ProcessStarted)
        
        assert type_handler in handlers
        assert global_handler in handlers
        assert len(handlers) == 2

    @pytest.mark.asyncio
    async def test_async_dispatch(self, bus, sample_event):
        """Events are dispatched asynchronously."""
        order = []
        
        async def slow_handler(event: DomainEvent):
            await asyncio.sleep(0.01)
            order.append("slow")
        
        async def fast_handler(event: DomainEvent):
            order.append("fast")
        
        bus.subscribe(ProcessStarted, slow_handler)
        bus.subscribe(ProcessStarted, fast_handler)
        
        await bus.publish(sample_event)
        
        # Handlers are started but we continue immediately
        # Fast handler should complete first even if subscribed second
        await bus.wait_for_pending()
        
        # Both should complete
        assert "slow" in order
        assert "fast" in order
