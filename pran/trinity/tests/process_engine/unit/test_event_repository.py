"""
Unit tests for SqliteEventRepository
"""

import pytest
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from services.process_engine.domain import (
    ProcessId,
    ExecutionId,
    StepId,
    ProcessStarted,
    StepCompleted,
    Money,
    Duration,
)
from services.process_engine.repositories.sqlite_events import SqliteEventRepository


@pytest.fixture
def repo():
    """Create a repository with in-memory database."""
    return SqliteEventRepository(":memory:")


def test_save_and_retrieve_event(repo):
    """Test saving and retrieving events."""
    execution_id = ExecutionId.generate()
    process_id = ProcessId.generate()
    
    event = ProcessStarted(
        execution_id=execution_id,
        process_id=process_id,
        process_name="test-process",
        triggered_by="test"
    )
    
    repo.save(event)
    
    events = repo.get_by_execution_id(execution_id)
    assert len(events) == 1
    loaded = events[0]
    
    assert isinstance(loaded, ProcessStarted)
    assert loaded.execution_id == execution_id
    assert loaded.process_id == process_id
    assert loaded.process_name == "test-process"
    assert loaded.triggered_by == "test"
    # Timestamps should match (isoformat roundtrip might lose microsecond precision depending on impl, 
    # but python isoformat keeps it)
    assert loaded.timestamp == event.timestamp


def test_save_step_event(repo):
    """Test saving a step event with complex value objects."""
    execution_id = ExecutionId.generate()
    step_id = StepId("step-1")
    
    event = StepCompleted(
        execution_id=execution_id,
        step_id=step_id,
        step_name="Step 1",
        output={"result": "success"},
        cost=Money.from_string("1.50"),
        duration=Duration(seconds=30)
    )
    
    repo.save(event)
    
    events = repo.get_by_execution_id(execution_id)
    assert len(events) == 1
    loaded = events[0]
    
    assert isinstance(loaded, StepCompleted)
    assert loaded.execution_id == execution_id
    assert loaded.step_id == step_id
    assert loaded.output == {"result": "success"}
    assert loaded.cost == Money.from_string("1.50")
    assert loaded.duration == Duration(seconds=30)


def test_multiple_events_ordering(repo):
    """Test that events are retrieved in order."""
    execution_id = ExecutionId.generate()
    process_id = ProcessId.generate()
    
    event1 = ProcessStarted(
        execution_id=execution_id,
        process_id=process_id,
        process_name="test",
        timestamp=datetime(2023, 1, 1, 10, 0, 0, tzinfo=timezone.utc)
    )
    
    event2 = StepCompleted(
        execution_id=execution_id,
        step_id=StepId("step-1"),
        step_name="step",
        timestamp=datetime(2023, 1, 1, 10, 0, 1, tzinfo=timezone.utc)
    )
    
    repo.save(event2)  # Save out of order
    repo.save(event1)
    
    events = repo.get_by_execution_id(execution_id)
    assert len(events) == 2
    assert isinstance(events[0], ProcessStarted)
    assert isinstance(events[1], StepCompleted)
