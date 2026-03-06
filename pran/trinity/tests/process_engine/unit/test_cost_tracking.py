"""
Unit Tests for Cost Tracking Feature (E11-01)

Tests TokenUsage value object and cost tracking in step executions.
"""

import pytest
from decimal import Decimal

from services.process_engine.domain import (
    Money,
    StepId,
    StepStatus,
)
from services.process_engine.domain.value_objects import TokenUsage
from services.process_engine.domain.entities import StepExecution


class TestTokenUsage:
    """Tests for TokenUsage value object."""

    def test_create_basic(self):
        """Test creating a basic TokenUsage."""
        usage = TokenUsage(
            input_tokens=100,
            output_tokens=50,
        )

        assert usage.input_tokens == 100
        assert usage.output_tokens == 50
        assert usage.total_tokens == 150  # Auto-calculated

    def test_create_with_total(self):
        """Test creating TokenUsage with explicit total."""
        usage = TokenUsage(
            input_tokens=100,
            output_tokens=50,
            total_tokens=160,  # Explicit (may include other tokens)
        )

        assert usage.total_tokens == 160

    def test_create_with_model(self):
        """Test creating TokenUsage with model name."""
        usage = TokenUsage(
            input_tokens=100,
            output_tokens=50,
            model="gpt-4",
        )

        assert usage.model == "gpt-4"

    def test_create_empty(self):
        """Test creating empty TokenUsage."""
        usage = TokenUsage()

        assert usage.input_tokens == 0
        assert usage.output_tokens == 0
        assert usage.total_tokens == 0

    def test_from_dict(self):
        """Test creating TokenUsage from dictionary."""
        data = {
            "input_tokens": 500,
            "output_tokens": 200,
            "total_tokens": 700,
            "model": "claude-3",
        }

        usage = TokenUsage.from_dict(data)

        assert usage.input_tokens == 500
        assert usage.output_tokens == 200
        assert usage.total_tokens == 700
        assert usage.model == "claude-3"

    def test_from_dict_empty(self):
        """Test creating TokenUsage from empty dict."""
        usage = TokenUsage.from_dict({})

        assert usage.input_tokens == 0
        assert usage.output_tokens == 0

    def test_to_dict(self):
        """Test serializing TokenUsage to dictionary."""
        usage = TokenUsage(
            input_tokens=100,
            output_tokens=50,
            total_tokens=150,
            model="gpt-4",
        )

        result = usage.to_dict()

        assert result["input_tokens"] == 100
        assert result["output_tokens"] == 50
        assert result["total_tokens"] == 150
        assert result["model"] == "gpt-4"

    def test_to_dict_without_model(self):
        """Test serializing TokenUsage without model."""
        usage = TokenUsage(input_tokens=100, output_tokens=50)

        result = usage.to_dict()

        assert "model" not in result

    def test_add(self):
        """Test adding two TokenUsage objects."""
        usage1 = TokenUsage(input_tokens=100, output_tokens=50)
        usage2 = TokenUsage(input_tokens=200, output_tokens=100)

        result = usage1 + usage2

        assert result.input_tokens == 300
        assert result.output_tokens == 150
        assert result.total_tokens == 450

    def test_str(self):
        """Test string representation."""
        usage = TokenUsage(input_tokens=100, output_tokens=50)

        result = str(usage)

        assert "150 tokens" in result
        assert "in: 100" in result
        assert "out: 50" in result

    def test_negative_tokens_raises(self):
        """Test that negative tokens raise ValueError."""
        with pytest.raises(ValueError):
            TokenUsage(input_tokens=-1)

        with pytest.raises(ValueError):
            TokenUsage(output_tokens=-1)

    def test_immutability(self):
        """Test that TokenUsage is immutable (frozen)."""
        usage = TokenUsage(input_tokens=100)

        with pytest.raises(AttributeError):
            usage.input_tokens = 200


class TestStepExecutionWithCost:
    """Tests for StepExecution with cost and token_usage."""

    def test_create_with_cost(self):
        """Test creating StepExecution with cost."""
        cost = Money.from_float(0.05)
        execution = StepExecution(
            step_id=StepId("test-step"),
            cost=cost,
        )

        assert execution.cost == cost
        assert str(execution.cost) == "$0.05"

    def test_create_with_token_usage(self):
        """Test creating StepExecution with token_usage."""
        token_usage = TokenUsage(input_tokens=100, output_tokens=50)
        execution = StepExecution(
            step_id=StepId("test-step"),
            token_usage=token_usage,
        )

        assert execution.token_usage == token_usage
        assert execution.token_usage.total_tokens == 150

    def test_create_with_both_cost_and_tokens(self):
        """Test creating StepExecution with both cost and token_usage."""
        cost = Money.from_float(0.10)
        token_usage = TokenUsage(input_tokens=500, output_tokens=200)

        execution = StepExecution(
            step_id=StepId("test-step"),
            cost=cost,
            token_usage=token_usage,
        )

        assert execution.cost.amount == Decimal("0.10")
        assert execution.token_usage.total_tokens == 700

    def test_to_dict_includes_cost(self):
        """Test that to_dict includes cost."""
        execution = StepExecution(
            step_id=StepId("test-step"),
            status=StepStatus.COMPLETED,
            cost=Money.from_float(0.05),
        )

        result = execution.to_dict()

        assert "cost" in result
        assert result["cost"] == "$0.05"

    def test_to_dict_includes_token_usage(self):
        """Test that to_dict includes token_usage."""
        execution = StepExecution(
            step_id=StepId("test-step"),
            status=StepStatus.COMPLETED,
            token_usage=TokenUsage(input_tokens=100, output_tokens=50),
        )

        result = execution.to_dict()

        assert "token_usage" in result
        assert result["token_usage"]["input_tokens"] == 100
        assert result["token_usage"]["output_tokens"] == 50

    def test_from_dict_restores_cost(self):
        """Test that from_dict restores cost."""
        data = {
            "step_id": "test-step",
            "status": "completed",
            "cost": "$0.05",
            "retry_count": 0,
        }

        execution = StepExecution.from_dict(data)

        assert execution.cost is not None
        assert execution.cost.amount == Decimal("0.05")

    def test_from_dict_restores_token_usage(self):
        """Test that from_dict restores token_usage."""
        data = {
            "step_id": "test-step",
            "status": "completed",
            "token_usage": {
                "input_tokens": 100,
                "output_tokens": 50,
                "total_tokens": 150,
                "model": "gpt-4",
            },
            "retry_count": 0,
        }

        execution = StepExecution.from_dict(data)

        assert execution.token_usage is not None
        assert execution.token_usage.input_tokens == 100
        assert execution.token_usage.output_tokens == 50
        assert execution.token_usage.model == "gpt-4"

    def test_from_dict_without_cost_or_tokens(self):
        """Test from_dict without cost or token_usage."""
        data = {
            "step_id": "test-step",
            "status": "pending",
            "retry_count": 0,
        }

        execution = StepExecution.from_dict(data)

        assert execution.cost is None
        assert execution.token_usage is None


class TestProcessExecutionCostAggregation:
    """Tests for cost aggregation in ProcessExecution."""

    def test_add_cost(self):
        """Test adding cost to execution total."""
        from services.process_engine.domain.aggregates import ProcessExecution
        from services.process_engine.domain import ProcessId, ExecutionId, Version

        execution = ProcessExecution(
            id=ExecutionId.generate(),
            process_id=ProcessId.generate(),
            process_version=Version.initial(),
            process_name="test",
        )

        assert execution.total_cost.amount == Decimal("0")

        execution.add_cost(Money.from_float(0.05))
        assert execution.total_cost.amount == Decimal("0.05")

        execution.add_cost(Money.from_float(0.10))
        assert execution.total_cost.amount == Decimal("0.15")

    def test_total_cost_in_dict(self):
        """Test that total_cost is included in to_dict."""
        from services.process_engine.domain.aggregates import ProcessExecution
        from services.process_engine.domain import ProcessId, ExecutionId, Version

        execution = ProcessExecution(
            id=ExecutionId.generate(),
            process_id=ProcessId.generate(),
            process_version=Version.initial(),
            process_name="test",
        )
        execution.add_cost(Money.from_float(0.25))

        result = execution.to_dict()

        assert result["total_cost"] == "$0.25"
