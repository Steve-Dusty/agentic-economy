"""
Scheduler service configuration.

All configuration is loaded from environment variables with sensible defaults.
"""

import os
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class SchedulerConfig:
    """Configuration for the scheduler service."""

    # Database
    database_path: str = field(default_factory=lambda: os.getenv(
        "DATABASE_PATH", "/data/trinity.db"
    ))

    # Redis
    redis_url: str = field(default_factory=lambda: os.getenv(
        "REDIS_URL", "redis://redis:6379"
    ))

    # Lock settings
    lock_timeout: int = field(default_factory=lambda: int(os.getenv(
        "LOCK_TIMEOUT", "600"
    )))  # 10 minutes default
    lock_auto_renewal: bool = field(default_factory=lambda: os.getenv(
        "LOCK_AUTO_RENEWAL", "true"
    ).lower() == "true")

    # Health server
    health_port: int = field(default_factory=lambda: int(os.getenv(
        "HEALTH_PORT", "8001"
    )))
    health_host: str = field(default_factory=lambda: os.getenv(
        "HEALTH_HOST", "0.0.0.0"
    ))

    # Scheduler settings
    default_timezone: str = field(default_factory=lambda: os.getenv(
        "DEFAULT_TIMEZONE", "UTC"
    ))
    schedule_reload_interval: int = field(default_factory=lambda: int(os.getenv(
        "SCHEDULE_RELOAD_INTERVAL", "60"
    )))  # seconds

    # Agent communication
    agent_timeout: float = field(default_factory=lambda: float(os.getenv(
        "AGENT_TIMEOUT", "900"
    )))  # 15 minutes

    # Backend API (for process executions)
    backend_url: str = field(default_factory=lambda: os.getenv(
        "BACKEND_URL", "http://backend:8000"
    ))

    # Logging
    log_level: str = field(default_factory=lambda: os.getenv(
        "LOG_LEVEL", "INFO"
    ))

    # Event publishing (for WebSocket compatibility)
    publish_events: bool = field(default_factory=lambda: os.getenv(
        "PUBLISH_EVENTS", "true"
    ).lower() == "true")

    @classmethod
    def from_env(cls) -> "SchedulerConfig":
        """Create config from environment variables."""
        return cls()


# Global config instance
config = SchedulerConfig.from_env()
