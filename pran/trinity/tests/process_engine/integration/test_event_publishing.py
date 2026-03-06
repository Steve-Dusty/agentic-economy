"""
Integration Tests for Event Publishing

Tests domain event emission during process execution.

Reference: BACKLOG_RELIABILITY_IMPROVEMENTS.md - RI-08
"""

import pytest

from services.process_engine.domain import (
    ExecutionStatus,
    StepStatus,
    ProcessDefinition,
    StepDefinition,
    ProcessStarted,
    ProcessCompleted,
    ProcessFailed,
    StepStarted,
    StepCompleted,
    StepFailed,
)

from .conftest import (
    create_single_step_definition,
    create_sequential_definition,
    assert_event_sequence,
)


# =============================================================================
# Test: Event Sequence for Successful Execution
# =============================================================================


class TestSuccessfulExecutionEvents:
    """Tests for events during successful execution."""

    @pytest.mark.asyncio
    async def test_event_sequence_for_successful_execution(self, integration_engine):
        """Events should be emitted in correct sequence for successful execution."""
        ctx = integration_engine

        # Arrange: 2-step sequential process
        definition = create_sequential_definition(
            name="event-sequence-test",
            num_steps=2,
        )

        # Act
        execution = await ctx.start(definition, input_data={"topic": "events"})

        # Assert: Correct event sequence
        expected = [
            "ProcessStarted",
            "StepStarted", "StepCompleted",   # Step 1
            "StepStarted", "StepCompleted",   # Step 2
            "ProcessCompleted",
        ]
        assert_event_sequence(ctx.event_bus, expected)

        # Assert: ProcessStarted event details
        start_events = ctx.event_bus.get_events_of_type("ProcessStarted")
        assert len(start_events) == 1
        start_event = start_events[0]
        assert start_event.execution_id == execution.id
        assert start_event.process_name == "event-sequence-test"

        # Assert: ProcessCompleted event details
        complete_events = ctx.event_bus.get_events_of_type("ProcessCompleted")
        assert len(complete_events) == 1
        complete_event = complete_events[0]
        assert complete_event.execution_id == execution.id


# =============================================================================
# Test: Step Failed Event Contains Error
# =============================================================================


class TestFailureEvents:
    """Tests for events during failed execution."""

    @pytest.mark.asyncio
    async def test_step_failed_event_contains_error(self, integration_engine):
        """StepFailed event should contain error details."""
        ctx = integration_engine

        # Arrange: Configure agent to fail
        ctx.gateway.fail_agents.add("error-agent")

        definition = create_single_step_definition(
            name="error-event-test",
            agent="error-agent",
        )

        # Act
        execution = await ctx.start(definition)

        # Assert: Execution failed
        assert execution.status == ExecutionStatus.FAILED

        # Assert: StepFailed event emitted
        failed_events = ctx.event_bus.get_events_of_type("StepFailed")
        assert len(failed_events) == 1

        # Assert: Event contains error info
        failed_event = failed_events[0]
        assert failed_event.execution_id == execution.id
        assert str(failed_event.step_id) == "step-1" or failed_event.step_id.value == "step-1"
        # Error info can be in error_message or error attribute depending on event type
        error_str = getattr(failed_event, 'error_message', None) or getattr(failed_event, 'error', None)
        assert error_str is not None
        assert len(str(error_str)) > 0

        # Assert: ProcessFailed also emitted
        process_failed = ctx.event_bus.get_events_of_type("ProcessFailed")
        assert len(process_failed) == 1

    @pytest.mark.asyncio
    async def test_failed_sequence_includes_partial_success_events(self, integration_engine):
        """When a step fails mid-sequence, earlier success events should be present."""
        ctx = integration_engine

        # Arrange: Second agent fails
        ctx.gateway.fail_agents.add("agent-2")

        definition = create_sequential_definition(
            name="partial-fail-test",
            num_steps=3,
            agents=["agent-1", "agent-2", "agent-3"],
        )

        # Act
        execution = await ctx.start(definition, input_data={"topic": "test"})

        # Assert: Execution failed
        assert execution.status == ExecutionStatus.FAILED

        # Assert: First step success events present
        event_types = ctx.event_bus.get_event_types()
        assert "ProcessStarted" in event_types

        # Count completed vs failed
        step_completed = event_types.count("StepCompleted")
        step_failed = event_types.count("StepFailed")

        assert step_completed >= 1  # At least first step completed
        assert step_failed == 1     # Second step failed
        assert "ProcessFailed" in event_types


# =============================================================================
# Test: Events Contain Execution Context
# =============================================================================


class TestEventContext:
    """Tests for event context and metadata."""

    @pytest.mark.asyncio
    async def test_events_contain_execution_context(self, integration_engine):
        """All events should contain execution IDs and timestamps."""
        ctx = integration_engine

        # Arrange
        definition = create_single_step_definition(name="context-test")

        # Act
        execution = await ctx.start(definition)

        # Assert: All events have execution_id
        for event in ctx.event_bus.captured_events:
            assert hasattr(event, "execution_id"), f"Event {type(event).__name__} missing execution_id"
            assert event.execution_id == execution.id

        # Assert: Events have timestamps
        for event in ctx.event_bus.captured_events:
            assert hasattr(event, "timestamp"), f"Event {type(event).__name__} missing timestamp"
            assert event.timestamp is not None

        # Assert: Step events have step_id
        step_events = [e for e in ctx.event_bus.captured_events
                       if type(e).__name__.startswith("Step")]
        for event in step_events:
            assert hasattr(event, "step_id"), f"Event {type(event).__name__} missing step_id"
            assert event.step_id is not None

    @pytest.mark.asyncio
    async def test_events_ordered_by_timestamp(self, integration_engine):
        """Events should be ordered by timestamp."""
        ctx = integration_engine

        # Arrange
        definition = create_sequential_definition(num_steps=3)

        # Act
        execution = await ctx.start(definition, input_data={"topic": "test"})

        # Assert: Timestamps are monotonically increasing
        timestamps = [e.timestamp for e in ctx.event_bus.captured_events]
        for i in range(1, len(timestamps)):
            assert timestamps[i] >= timestamps[i-1], (
                f"Event {i} timestamp {timestamps[i]} is before event {i-1} timestamp {timestamps[i-1]}"
            )
