"""
Unit tests for Process Engine Value Objects

Tests for: ProcessId, ExecutionId, StepId, Version, Duration, Money
Reference: E1-06 Acceptance Criteria
"""

import uuid
from decimal import Decimal

import pytest

from services.process_engine.domain.value_objects import (
    ProcessId,
    ExecutionId,
    StepId,
    Version,
    Duration,
    Money,
)


# =============================================================================
# ProcessId Tests
# =============================================================================


class TestProcessId:
    """Tests for ProcessId value object."""

    def test_create_with_valid_uuid(self):
        """ProcessId accepts valid UUID string."""
        valid_uuid = str(uuid.uuid4())
        pid = ProcessId(valid_uuid)
        assert pid.value == valid_uuid

    def test_create_with_invalid_uuid(self):
        """ProcessId rejects invalid UUID string."""
        with pytest.raises(ValueError, match="Invalid ProcessId"):
            ProcessId("not-a-uuid")

    def test_generate_creates_unique_ids(self):
        """ProcessId.generate() creates unique IDs."""
        id1 = ProcessId.generate()
        id2 = ProcessId.generate()
        assert id1 != id2

    def test_from_string(self):
        """ProcessId.from_string() works correctly."""
        valid_uuid = str(uuid.uuid4())
        pid = ProcessId.from_string(valid_uuid)
        assert pid.value == valid_uuid

    def test_str_returns_value(self):
        """str(ProcessId) returns the UUID string."""
        valid_uuid = str(uuid.uuid4())
        pid = ProcessId(valid_uuid)
        assert str(pid) == valid_uuid

    def test_immutable(self):
        """ProcessId is immutable (frozen)."""
        pid = ProcessId.generate()
        with pytest.raises(AttributeError):
            pid.value = "new-value"

    def test_equality(self):
        """ProcessIds with same value are equal."""
        value = str(uuid.uuid4())
        pid1 = ProcessId(value)
        pid2 = ProcessId(value)
        assert pid1 == pid2

    def test_hashable(self):
        """ProcessId can be used in sets and as dict keys."""
        pid = ProcessId.generate()
        s = {pid}
        assert pid in s
        d = {pid: "test"}
        assert d[pid] == "test"


# =============================================================================
# ExecutionId Tests
# =============================================================================


class TestExecutionId:
    """Tests for ExecutionId value object."""

    def test_create_with_valid_uuid(self):
        """ExecutionId accepts valid UUID string."""
        valid_uuid = str(uuid.uuid4())
        eid = ExecutionId(valid_uuid)
        assert eid.value == valid_uuid

    def test_create_with_invalid_uuid(self):
        """ExecutionId rejects invalid UUID string."""
        with pytest.raises(ValueError, match="Invalid ExecutionId"):
            ExecutionId("not-a-uuid")

    def test_generate_creates_unique_ids(self):
        """ExecutionId.generate() creates unique IDs."""
        id1 = ExecutionId.generate()
        id2 = ExecutionId.generate()
        assert id1 != id2


# =============================================================================
# StepId Tests
# =============================================================================


class TestStepId:
    """Tests for StepId value object."""

    def test_valid_step_id(self):
        """StepId accepts valid identifiers."""
        valid_ids = ["research", "step-1", "analyze_data", "a1", "step-with-numbers-123"]
        for sid in valid_ids:
            step = StepId(sid)
            assert step.value == sid

    def test_empty_step_id(self):
        """StepId rejects empty string."""
        with pytest.raises(ValueError, match="cannot be empty"):
            StepId("")

    def test_invalid_start_character(self):
        """StepId must start with lowercase letter."""
        invalid_ids = ["1step", "-step", "_step", "Step", "STEP"]
        for sid in invalid_ids:
            with pytest.raises(ValueError, match="must start with lowercase"):
                StepId(sid)

    def test_invalid_characters(self):
        """StepId rejects invalid characters."""
        invalid_ids = ["step.name", "step name", "step@name", "step/name"]
        for sid in invalid_ids:
            with pytest.raises(ValueError):
                StepId(sid)

    def test_too_long(self):
        """StepId rejects strings longer than 64 characters."""
        long_id = "a" * 65
        with pytest.raises(ValueError, match="too long"):
            StepId(long_id)

    def test_max_length_allowed(self):
        """StepId accepts strings of exactly 64 characters."""
        max_id = "a" * 64
        step = StepId(max_id)
        assert len(step.value) == 64

    def test_str_returns_value(self):
        """str(StepId) returns the step ID string."""
        step = StepId("my-step")
        assert str(step) == "my-step"


# =============================================================================
# Version Tests
# =============================================================================


class TestVersion:
    """Tests for Version value object."""

    def test_create_version(self):
        """Version accepts valid major/minor numbers."""
        v = Version(major=1, minor=0)
        assert v.major == 1
        assert v.minor == 0

    def test_major_only(self):
        """Version with major only defaults minor to 0."""
        v = Version(major=2)
        assert v.major == 2
        assert v.minor == 0

    def test_invalid_major(self):
        """Version rejects major < 1."""
        with pytest.raises(ValueError, match="Major version must be >= 1"):
            Version(major=0)

    def test_invalid_minor(self):
        """Version rejects minor < 0."""
        with pytest.raises(ValueError, match="Minor version must be >= 0"):
            Version(major=1, minor=-1)

    def test_initial(self):
        """Version.initial() returns 1.0."""
        v = Version.initial()
        assert v.major == 1
        assert v.minor == 0

    def test_from_string_major_only(self):
        """Version.from_string() parses '1' format."""
        v = Version.from_string("1")
        assert v.major == 1
        assert v.minor == 0

    def test_from_string_major_minor(self):
        """Version.from_string() parses '1.2' format."""
        v = Version.from_string("1.2")
        assert v.major == 1
        assert v.minor == 2

    def test_from_string_invalid(self):
        """Version.from_string() rejects invalid formats."""
        with pytest.raises(ValueError):
            Version.from_string("1.2.3")
        with pytest.raises(ValueError):
            Version.from_string("")

    def test_increment_major(self):
        """increment_major() increases major and resets minor."""
        v = Version(major=1, minor=5)
        v2 = v.increment_major()
        assert v2.major == 2
        assert v2.minor == 0

    def test_increment_minor(self):
        """increment_minor() increases minor only."""
        v = Version(major=1, minor=5)
        v2 = v.increment_minor()
        assert v2.major == 1
        assert v2.minor == 6

    def test_str_major_only(self):
        """str(Version) omits minor if 0."""
        v = Version(major=2, minor=0)
        assert str(v) == "2"

    def test_str_major_minor(self):
        """str(Version) includes minor if non-zero."""
        v = Version(major=2, minor=3)
        assert str(v) == "2.3"

    def test_comparison(self):
        """Version comparison works correctly."""
        v1 = Version(1, 0)
        v1_1 = Version(1, 1)
        v2 = Version(2, 0)

        assert v1 < v1_1 < v2
        assert v2 > v1_1 > v1
        assert v1 <= v1
        assert v1 >= v1


# =============================================================================
# Duration Tests
# =============================================================================


class TestDuration:
    """Tests for Duration value object."""

    def test_create_duration(self):
        """Duration accepts valid seconds."""
        d = Duration(seconds=60)
        assert d.seconds == 60

    def test_negative_duration(self):
        """Duration rejects negative seconds."""
        with pytest.raises(ValueError, match="cannot be negative"):
            Duration(seconds=-1)

    def test_from_string_seconds(self):
        """Duration.from_string() parses '30s' format."""
        d = Duration.from_string("30s")
        assert d.seconds == 30

    def test_from_string_minutes(self):
        """Duration.from_string() parses '5m' format."""
        d = Duration.from_string("5m")
        assert d.seconds == 300

    def test_from_string_hours(self):
        """Duration.from_string() parses '2h' format."""
        d = Duration.from_string("2h")
        assert d.seconds == 7200

    def test_from_string_days(self):
        """Duration.from_string() parses '1d' format."""
        d = Duration.from_string("1d")
        assert d.seconds == 86400

    def test_from_string_integer(self):
        """Duration.from_string() parses plain integer as seconds."""
        d = Duration.from_string("120")
        assert d.seconds == 120

    def test_from_string_invalid(self):
        """Duration.from_string() rejects invalid formats."""
        with pytest.raises(ValueError, match="Invalid duration format"):
            Duration.from_string("5x")
        with pytest.raises(ValueError):
            Duration.from_string("")

    def test_from_minutes(self):
        """Duration.from_minutes() converts correctly."""
        d = Duration.from_minutes(5)
        assert d.seconds == 300

    def test_from_hours(self):
        """Duration.from_hours() converts correctly."""
        d = Duration.from_hours(2)
        assert d.seconds == 7200

    def test_to_timedelta(self):
        """Duration.to_timedelta() converts correctly."""
        from datetime import timedelta
        d = Duration(seconds=90)
        td = d.to_timedelta()
        assert td == timedelta(seconds=90)

    def test_str_seconds(self):
        """str(Duration) formats seconds correctly."""
        d = Duration(seconds=30)
        assert str(d) == "30s"

    def test_str_minutes(self):
        """str(Duration) formats minutes correctly."""
        d = Duration(seconds=300)
        assert str(d) == "5m"

    def test_str_complex(self):
        """str(Duration) formats complex durations."""
        d = Duration(seconds=3661)  # 1h 1m 1s
        assert str(d) == "1h1m1s"

    def test_str_zero(self):
        """str(Duration) handles zero."""
        d = Duration(seconds=0)
        assert str(d) == "0s"

    def test_addition(self):
        """Duration addition works correctly."""
        d1 = Duration(seconds=30)
        d2 = Duration(seconds=60)
        d3 = d1 + d2
        assert d3.seconds == 90

    def test_comparison(self):
        """Duration comparison works correctly."""
        d1 = Duration(seconds=30)
        d2 = Duration(seconds=60)
        assert d1 < d2
        assert d2 > d1
        assert d1 <= d1
        assert d1 >= d1


# =============================================================================
# Money Tests
# =============================================================================


class TestMoney:
    """Tests for Money value object."""

    def test_create_money(self):
        """Money accepts valid amount and currency."""
        m = Money(amount=Decimal("10.50"), currency="USD")
        assert m.amount == Decimal("10.50")
        assert m.currency == "USD"

    def test_create_from_int(self):
        """Money converts int to Decimal."""
        m = Money(amount=10, currency="USD")
        assert m.amount == Decimal("10")

    def test_create_from_float(self):
        """Money converts float to Decimal."""
        m = Money(amount=10.50, currency="USD")
        assert m.amount == Decimal("10.5")

    def test_negative_amount(self):
        """Money rejects negative amounts."""
        with pytest.raises(ValueError, match="cannot be negative"):
            Money(amount=Decimal("-1"), currency="USD")

    def test_invalid_currency(self):
        """Money rejects invalid currency codes."""
        with pytest.raises(ValueError, match="3-letter code"):
            Money(amount=Decimal("10"), currency="US")

    def test_zero(self):
        """Money.zero() creates zero value."""
        m = Money.zero()
        assert m.amount == Decimal("0")
        assert m.currency == "USD"

    def test_from_float(self):
        """Money.from_float() converts correctly."""
        m = Money.from_float(10.50)
        assert m.amount == Decimal("10.5")

    def test_from_string(self):
        """Money.from_string() parses correctly."""
        m = Money.from_string("10.50")
        assert m.amount == Decimal("10.50")

    def test_from_string_with_dollar(self):
        """Money.from_string() handles dollar sign."""
        m = Money.from_string("$10.50")
        assert m.amount == Decimal("10.50")

    def test_addition(self):
        """Money addition works with same currency."""
        m1 = Money(amount=Decimal("10.00"), currency="USD")
        m2 = Money(amount=Decimal("5.50"), currency="USD")
        m3 = m1 + m2
        assert m3.amount == Decimal("15.50")
        assert m3.currency == "USD"

    def test_addition_different_currency(self):
        """Money addition rejects different currencies."""
        m1 = Money(amount=Decimal("10.00"), currency="USD")
        m2 = Money(amount=Decimal("10.00"), currency="EUR")
        with pytest.raises(ValueError, match="different currencies"):
            m1 + m2

    def test_subtraction(self):
        """Money subtraction works with same currency."""
        m1 = Money(amount=Decimal("10.00"), currency="USD")
        m2 = Money(amount=Decimal("3.50"), currency="USD")
        m3 = m1 - m2
        assert m3.amount == Decimal("6.50")

    def test_subtraction_negative_result(self):
        """Money subtraction rejects negative result."""
        m1 = Money(amount=Decimal("5.00"), currency="USD")
        m2 = Money(amount=Decimal("10.00"), currency="USD")
        with pytest.raises(ValueError, match="negative amount"):
            m1 - m2

    def test_multiplication(self):
        """Money multiplication by scalar works."""
        m = Money(amount=Decimal("10.00"), currency="USD")
        m2 = m * 2
        assert m2.amount == Decimal("20.00")

    def test_multiplication_float(self):
        """Money multiplication by float works."""
        m = Money(amount=Decimal("10.00"), currency="USD")
        m2 = m * 0.5
        assert m2.amount == Decimal("5.0")

    def test_comparison(self):
        """Money comparison works correctly."""
        m1 = Money(amount=Decimal("10.00"), currency="USD")
        m2 = Money(amount=Decimal("20.00"), currency="USD")
        assert m1 < m2
        assert m2 > m1
        assert m1 <= m1
        assert m1 >= m1

    def test_comparison_different_currency(self):
        """Money comparison rejects different currencies."""
        m1 = Money(amount=Decimal("10.00"), currency="USD")
        m2 = Money(amount=Decimal("10.00"), currency="EUR")
        with pytest.raises(ValueError, match="different currencies"):
            m1 < m2

    def test_str(self):
        """str(Money) formats correctly."""
        m = Money(amount=Decimal("10.50"), currency="USD")
        assert str(m) == "$10.50"

    def test_str_rounds_display(self):
        """str(Money) rounds to 2 decimal places for display."""
        m = Money(amount=Decimal("10.555"), currency="USD")
        # Note: the amount is preserved, just display is rounded
        assert str(m) == "$10.56"  # rounded for display
