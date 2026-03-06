"""
Process Engine Value Objects

Immutable domain primitives that represent concepts in the process domain.
All value objects are frozen dataclasses for immutability.

Reference: IT3 Section 4.3 (Value Objects)
"""

from __future__ import annotations

import re
import uuid
from dataclasses import dataclass
from decimal import Decimal
from typing import Optional


# =============================================================================
# Identifiers
# =============================================================================


@dataclass(frozen=True)
class ProcessId:
    """
    Unique identifier for a process definition.
    Wraps UUID with validation.
    """
    value: str

    def __post_init__(self) -> None:
        """Validate UUID format."""
        try:
            uuid.UUID(self.value)
        except ValueError as e:
            raise ValueError(f"Invalid ProcessId: {self.value}") from e

    @classmethod
    def generate(cls) -> ProcessId:
        """Generate a new unique ProcessId."""
        return cls(str(uuid.uuid4()))

    @classmethod
    def from_string(cls, value: str) -> ProcessId:
        """Create ProcessId from string."""
        return cls(value)

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True)
class ExecutionId:
    """
    Unique identifier for a process execution instance.
    Wraps UUID with validation.
    """
    value: str

    def __post_init__(self) -> None:
        """Validate UUID format."""
        try:
            uuid.UUID(self.value)
        except ValueError as e:
            raise ValueError(f"Invalid ExecutionId: {self.value}") from e

    @classmethod
    def generate(cls) -> ExecutionId:
        """Generate a new unique ExecutionId."""
        return cls(str(uuid.uuid4()))

    @classmethod
    def from_string(cls, value: str) -> ExecutionId:
        """Create ExecutionId from string."""
        return cls(value)

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True)
class StepId:
    """
    Identifier for a step within a process.
    Must be a valid identifier (alphanumeric, hyphens, underscores).
    """
    value: str

    # Valid pattern: lowercase letters, numbers, hyphens, underscores
    # Must start with a letter
    _PATTERN = re.compile(r"^[a-z][a-z0-9_-]*$")

    def __post_init__(self) -> None:
        """Validate step ID format."""
        if not self.value:
            raise ValueError("StepId cannot be empty")
        if len(self.value) > 64:
            raise ValueError(f"StepId too long (max 64): {self.value}")
        if not self._PATTERN.match(self.value):
            raise ValueError(
                f"Invalid StepId '{self.value}': must start with lowercase letter, "
                "contain only lowercase letters, numbers, hyphens, underscores"
            )

    @classmethod
    def from_string(cls, value: str) -> StepId:
        """Create StepId from string."""
        return cls(value)

    def __str__(self) -> str:
        return self.value


# =============================================================================
# Versioning
# =============================================================================


@dataclass(frozen=True)
class Version:
    """
    Process definition version.
    Simple integer versioning (1, 2, 3, ...).
    """
    major: int
    minor: int = 0

    def __post_init__(self) -> None:
        """Validate version numbers."""
        if self.major < 1:
            raise ValueError(f"Major version must be >= 1, got {self.major}")
        if self.minor < 0:
            raise ValueError(f"Minor version must be >= 0, got {self.minor}")

    @classmethod
    def initial(cls) -> Version:
        """Create initial version (1.0)."""
        return cls(major=1, minor=0)

    @classmethod
    def from_string(cls, value: str) -> Version:
        """
        Parse version from string.
        Supports "1", "1.0", "1.2" formats.
        """
        if not value:
            raise ValueError("Version string cannot be empty")

        parts = value.split(".")
        if len(parts) == 1:
            return cls(major=int(parts[0]))
        elif len(parts) == 2:
            return cls(major=int(parts[0]), minor=int(parts[1]))
        else:
            raise ValueError(f"Invalid version format: {value}")

    def increment_major(self) -> Version:
        """Return new version with incremented major."""
        return Version(major=self.major + 1, minor=0)

    def increment_minor(self) -> Version:
        """Return new version with incremented minor."""
        return Version(major=self.major, minor=self.minor + 1)

    def __str__(self) -> str:
        if self.minor == 0:
            return str(self.major)
        return f"{self.major}.{self.minor}"

    def __lt__(self, other: Version) -> bool:
        if not isinstance(other, Version):
            return NotImplemented
        return (self.major, self.minor) < (other.major, other.minor)

    def __le__(self, other: Version) -> bool:
        if not isinstance(other, Version):
            return NotImplemented
        return (self.major, self.minor) <= (other.major, other.minor)

    def __gt__(self, other: Version) -> bool:
        if not isinstance(other, Version):
            return NotImplemented
        return (self.major, self.minor) > (other.major, other.minor)

    def __ge__(self, other: Version) -> bool:
        if not isinstance(other, Version):
            return NotImplemented
        return (self.major, self.minor) >= (other.major, other.minor)


# =============================================================================
# Time & Duration
# =============================================================================


@dataclass(frozen=True)
class Duration:
    """
    Represents a time duration for timeouts, delays, etc.
    Stored as seconds internally (with millisecond precision via float).

    Supports parsing from human-readable strings:
    - "100ms" = 0.1 seconds
    - "30s" = 30 seconds
    - "5m" = 5 minutes
    - "2h" = 2 hours
    - "1d" = 1 day
    """
    seconds: float  # Changed from int to float for millisecond precision

    # Pattern for parsing duration strings
    _PATTERN = re.compile(r"^(\d+)(ms|s|m|h|d)$")

    # Multipliers for each unit
    _UNITS = {
        "ms": 0.001,
        "s": 1,
        "m": 60,
        "h": 3600,
        "d": 86400,
    }

    def __post_init__(self) -> None:
        """Validate duration."""
        if self.seconds < 0:
            raise ValueError(f"Duration cannot be negative: {self.seconds}")

    @classmethod
    def from_string(cls, value: str) -> Duration:
        """
        Parse duration from string.

        Examples:
            Duration.from_string("100ms") -> Duration(seconds=0.1)
            Duration.from_string("30s") -> Duration(seconds=30)
            Duration.from_string("5m") -> Duration(seconds=300)
            Duration.from_string("2h") -> Duration(seconds=7200)
            Duration.from_string("1d") -> Duration(seconds=86400)
        """
        if not value:
            raise ValueError("Duration string cannot be empty")

        value = value.strip().lower()

        # Try parsing as just seconds (integer)
        if value.isdigit():
            return cls(seconds=int(value))

        # Try parsing with unit suffix
        match = cls._PATTERN.match(value)
        if not match:
            raise ValueError(
                f"Invalid duration format '{value}'. "
                "Use format like '100ms', '30s', '5m', '2h', '1d'"
            )

        amount = int(match.group(1))
        unit = match.group(2)
        multiplier = cls._UNITS[unit]

        return cls(seconds=amount * multiplier)

    @classmethod
    def from_seconds(cls, seconds: float) -> Duration:
        """Create Duration from seconds."""
        return cls(seconds=seconds)

    @classmethod
    def from_milliseconds(cls, ms: int) -> Duration:
        """Create Duration from milliseconds."""
        return cls(seconds=ms / 1000.0)

    @classmethod
    def from_minutes(cls, minutes: int) -> Duration:
        """Create Duration from minutes."""
        return cls(seconds=minutes * 60)

    @classmethod
    def from_hours(cls, hours: int) -> Duration:
        """Create Duration from hours."""
        return cls(seconds=hours * 3600)

    def to_timedelta(self):
        """Convert to Python timedelta."""
        from datetime import timedelta
        return timedelta(seconds=self.seconds)

    def __str__(self) -> str:
        """Return human-readable representation."""
        if self.seconds == 0:
            return "0s"

        # Handle sub-second durations
        if self.seconds < 1:
            ms = int(self.seconds * 1000)
            return f"{ms}ms"

        total_seconds = int(self.seconds)
        days, remainder = divmod(total_seconds, 86400)
        hours, remainder = divmod(remainder, 3600)
        minutes, seconds = divmod(remainder, 60)

        parts = []
        if days:
            parts.append(f"{int(days)}d")
        if hours:
            parts.append(f"{int(hours)}h")
        if minutes:
            parts.append(f"{int(minutes)}m")
        if seconds:
            parts.append(f"{int(seconds)}s")

        return "".join(parts)

    def __add__(self, other: Duration) -> Duration:
        if not isinstance(other, Duration):
            return NotImplemented
        return Duration(seconds=self.seconds + other.seconds)

    def __lt__(self, other: Duration) -> bool:
        if not isinstance(other, Duration):
            return NotImplemented
        return self.seconds < other.seconds

    def __le__(self, other: Duration) -> bool:
        if not isinstance(other, Duration):
            return NotImplemented
        return self.seconds <= other.seconds

    def __gt__(self, other: Duration) -> bool:
        if not isinstance(other, Duration):
            return NotImplemented
        return self.seconds > other.seconds

    def __ge__(self, other: Duration) -> bool:
        if not isinstance(other, Duration):
            return NotImplemented
        return self.seconds >= other.seconds


# =============================================================================
# Money & Cost
# =============================================================================


@dataclass(frozen=True)
class Money:
    """
    Represents a monetary amount with currency.
    Uses Decimal for precise arithmetic.

    Reference: IT3 Section 4.3 (Value Objects)
    """
    amount: Decimal
    currency: str = "USD"

    def __post_init__(self) -> None:
        """Validate money values."""
        # Convert amount to Decimal if needed (for frozen dataclass)
        if not isinstance(self.amount, Decimal):
            object.__setattr__(self, "amount", Decimal(str(self.amount)))

        if self.amount < 0:
            raise ValueError(f"Money amount cannot be negative: {self.amount}")

        if not self.currency or len(self.currency) != 3:
            raise ValueError(f"Currency must be 3-letter code: {self.currency}")

    @classmethod
    def zero(cls, currency: str = "USD") -> Money:
        """Create zero money value."""
        return cls(amount=Decimal("0"), currency=currency)

    @classmethod
    def from_float(cls, amount: float, currency: str = "USD") -> Money:
        """Create Money from float (use Decimal for precision)."""
        return cls(amount=Decimal(str(amount)), currency=currency)

    @classmethod
    def from_string(cls, value: str, currency: str = "USD") -> Money:
        """
        Parse Money from string.

        Examples:
            Money.from_string("1.50") -> Money(amount=Decimal('1.50'))
            Money.from_string("$1.50") -> Money(amount=Decimal('1.50'))
        """
        value = value.strip()
        if value.startswith("$"):
            value = value[1:]
        return cls(amount=Decimal(value), currency=currency)

    def __add__(self, other: Money) -> Money:
        """Add two Money values (must have same currency)."""
        if not isinstance(other, Money):
            return NotImplemented
        if self.currency != other.currency:
            raise ValueError(
                f"Cannot add different currencies: {self.currency} + {other.currency}"
            )
        return Money(amount=self.amount + other.amount, currency=self.currency)

    def __sub__(self, other: Money) -> Money:
        """Subtract Money values (must have same currency)."""
        if not isinstance(other, Money):
            return NotImplemented
        if self.currency != other.currency:
            raise ValueError(
                f"Cannot subtract different currencies: {self.currency} - {other.currency}"
            )
        result = self.amount - other.amount
        if result < 0:
            raise ValueError("Money subtraction would result in negative amount")
        return Money(amount=result, currency=self.currency)

    def __mul__(self, factor: int | float | Decimal) -> Money:
        """Multiply Money by a scalar."""
        if isinstance(factor, (int, float)):
            factor = Decimal(str(factor))
        return Money(amount=self.amount * factor, currency=self.currency)

    def __lt__(self, other: Money) -> bool:
        if not isinstance(other, Money):
            return NotImplemented
        if self.currency != other.currency:
            raise ValueError(f"Cannot compare different currencies")
        return self.amount < other.amount

    def __le__(self, other: Money) -> bool:
        if not isinstance(other, Money):
            return NotImplemented
        if self.currency != other.currency:
            raise ValueError(f"Cannot compare different currencies")
        return self.amount <= other.amount

    def __gt__(self, other: Money) -> bool:
        if not isinstance(other, Money):
            return NotImplemented
        if self.currency != other.currency:
            raise ValueError(f"Cannot compare different currencies")
        return self.amount > other.amount

    def __ge__(self, other: Money) -> bool:
        if not isinstance(other, Money):
            return NotImplemented
        if self.currency != other.currency:
            raise ValueError(f"Cannot compare different currencies")
        return self.amount >= other.amount

    def __str__(self) -> str:
        """Return formatted string representation."""
        return f"${self.amount:.2f}"

    def __repr__(self) -> str:
        return f"Money(amount={self.amount}, currency='{self.currency}')"


# =============================================================================
# Token Usage & Cost Tracking
# =============================================================================


@dataclass(frozen=True)
class TokenUsage:
    """
    Tracks token usage from LLM API calls.

    Used to track consumption and calculate costs for agent task steps.

    Reference: BACKLOG_ADVANCED.md - E11-01
    """
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0

    # Optional: model-specific fields
    model: Optional[str] = None

    def __post_init__(self) -> None:
        """Validate token counts."""
        if self.input_tokens < 0:
            raise ValueError(f"input_tokens cannot be negative: {self.input_tokens}")
        if self.output_tokens < 0:
            raise ValueError(f"output_tokens cannot be negative: {self.output_tokens}")
        if self.total_tokens < 0:
            raise ValueError(f"total_tokens cannot be negative: {self.total_tokens}")

        # Auto-calculate total if not provided
        if self.total_tokens == 0 and (self.input_tokens > 0 or self.output_tokens > 0):
            object.__setattr__(self, "total_tokens", self.input_tokens + self.output_tokens)

    @classmethod
    def from_dict(cls, data: dict) -> "TokenUsage":
        """Create TokenUsage from dictionary."""
        if not data:
            return cls()
        return cls(
            input_tokens=data.get("input_tokens", 0),
            output_tokens=data.get("output_tokens", 0),
            total_tokens=data.get("total_tokens", 0),
            model=data.get("model"),
        )

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        result = {
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "total_tokens": self.total_tokens,
        }
        if self.model:
            result["model"] = self.model
        return result

    def __add__(self, other: "TokenUsage") -> "TokenUsage":
        """Add two TokenUsage objects."""
        if not isinstance(other, TokenUsage):
            return NotImplemented
        return TokenUsage(
            input_tokens=self.input_tokens + other.input_tokens,
            output_tokens=self.output_tokens + other.output_tokens,
            total_tokens=self.total_tokens + other.total_tokens,
        )

    def __str__(self) -> str:
        """Return human-readable representation."""
        return f"{self.total_tokens} tokens (in: {self.input_tokens}, out: {self.output_tokens})"


# =============================================================================
# Error Handling Policies
# =============================================================================


@dataclass(frozen=True)
class RetryPolicy:
    """
    Configuration for step retries.
    """
    max_attempts: int = 3
    initial_delay: Duration = Duration(seconds=5)
    backoff_multiplier: float = 2.0

    @classmethod
    def default(cls) -> RetryPolicy:
        """Return default retry policy."""
        return cls()

    @classmethod
    def from_dict(cls, data: dict) -> RetryPolicy:
        """Create from dictionary."""
        if not data:
            return cls.default()

        return cls(
            max_attempts=data.get("max_attempts", 3),
            initial_delay=Duration.from_string(data.get("initial_delay", "5s")),
            backoff_multiplier=float(data.get("backoff_multiplier", 2.0)),
        )

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "max_attempts": self.max_attempts,
            "initial_delay": str(self.initial_delay),
            "backoff_multiplier": self.backoff_multiplier,
        }


@dataclass(frozen=True)
class ErrorPolicy:
    """
    Configuration for handling step failures after retries are exhausted.
    """
    from .enums import OnErrorAction

    action: OnErrorAction = OnErrorAction.FAIL_PROCESS
    target_step: Optional[StepId] = None

    @classmethod
    def default(cls) -> ErrorPolicy:
        """Return default error policy."""
        from .enums import OnErrorAction
        return cls(action=OnErrorAction.FAIL_PROCESS)

    @classmethod
    def from_dict(cls, data: dict) -> ErrorPolicy:
        """Create from dictionary."""
        from .enums import OnErrorAction
        if not data:
            return cls.default()

        if isinstance(data, str):
            # Simple format: just the action
            return cls(action=OnErrorAction(data))

        target_step = data.get("target_step")
        if target_step:
            target_step = StepId(target_step)

        return cls(
            action=OnErrorAction(data.get("action", "fail_process")),
            target_step=target_step,
        )

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        result = {"action": self.action.value}
        if self.target_step:
            result["target_step"] = str(self.target_step)
        return result
