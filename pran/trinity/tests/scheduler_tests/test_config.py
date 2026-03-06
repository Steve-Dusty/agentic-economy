"""
Tests for scheduler configuration.
"""

import os
import pytest
from unittest.mock import patch

from scheduler.config import SchedulerConfig


class TestSchedulerConfig:
    """Tests for SchedulerConfig."""

    def test_default_values(self):
        """Test that default config values are set correctly."""
        with patch.dict(os.environ, {}, clear=True):
            config = SchedulerConfig()

            assert config.database_path == "/data/trinity.db"
            assert config.redis_url == "redis://redis:6379"
            assert config.lock_timeout == 600
            assert config.lock_auto_renewal is True
            assert config.health_port == 8001
            assert config.default_timezone == "UTC"

    def test_env_override(self):
        """Test that environment variables override defaults."""
        env = {
            "DATABASE_PATH": "/custom/path.db",
            "REDIS_URL": "redis://custom:6380",
            "LOCK_TIMEOUT": "120",
            "LOCK_AUTO_RENEWAL": "false",
            "HEALTH_PORT": "9000",
            "LOG_LEVEL": "DEBUG"
        }
        with patch.dict(os.environ, env, clear=True):
            config = SchedulerConfig.from_env()

            assert config.database_path == "/custom/path.db"
            assert config.redis_url == "redis://custom:6380"
            assert config.lock_timeout == 120
            assert config.lock_auto_renewal is False
            assert config.health_port == 9000
            assert config.log_level == "DEBUG"

    def test_agent_timeout(self):
        """Test agent timeout configuration."""
        with patch.dict(os.environ, {"AGENT_TIMEOUT": "1800"}, clear=True):
            config = SchedulerConfig()
            assert config.agent_timeout == 1800.0

    def test_publish_events_default(self):
        """Test event publishing is enabled by default."""
        with patch.dict(os.environ, {}, clear=True):
            config = SchedulerConfig()
            assert config.publish_events is True

    def test_publish_events_disabled(self):
        """Test event publishing can be disabled."""
        with patch.dict(os.environ, {"PUBLISH_EVENTS": "false"}, clear=True):
            config = SchedulerConfig()
            assert config.publish_events is False
