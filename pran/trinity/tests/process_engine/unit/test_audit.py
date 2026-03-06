"""
Unit Tests for Audit Service

Tests audit logging and querying functionality.

Reference: BACKLOG_ACCESS_AUDIT.md - E18-02
"""

import pytest
import tempfile
import os
from datetime import datetime, timezone, timedelta

import sys
import types
from pathlib import Path

# Add src/backend to path for direct imports
_project_root = Path(__file__).resolve().parent.parent.parent.parent
_backend_path = str(_project_root / 'src' / 'backend')
_src_path = str(_project_root / 'src')

if _backend_path not in sys.path:
    sys.path.insert(0, _backend_path)
if _src_path not in sys.path:
    sys.path.insert(0, _src_path)

# Prevent services/__init__.py from being loaded (it has heavy dependencies)
if 'services' not in sys.modules:
    sys.modules['services'] = types.ModuleType('services')
    sys.modules['services'].__path__ = [str(Path(_backend_path) / 'services')]

from services.process_engine.services.audit import (
    AuditService,
    AuditEntry,
    AuditId,
    AuditAction,
    AuditFilter,
)
from services.process_engine.repositories.audit import SqliteAuditRepository


# =============================================================================
# Test Fixtures
# =============================================================================


@pytest.fixture
def temp_db_path():
    """Create a temporary database file."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        path = f.name
    yield path
    # Cleanup
    if os.path.exists(path):
        os.remove(path)


@pytest.fixture
def audit_repo(temp_db_path):
    """Create an audit repository."""
    return SqliteAuditRepository(temp_db_path)


@pytest.fixture
def audit_service(audit_repo):
    """Create an audit service."""
    return AuditService(audit_repo)


# =============================================================================
# Tests: AuditEntry
# =============================================================================


class TestAuditEntry:
    """Tests for AuditEntry dataclass."""

    def test_create_entry(self):
        """Create an audit entry."""
        entry = AuditEntry(
            id=AuditId.generate(),
            timestamp=datetime.now(timezone.utc),
            actor="user@example.com",
            action=AuditAction.PROCESS_CREATE.value,
            resource_type="process",
            resource_id="proc-123",
            details={"name": "test-process"},
        )

        assert entry.actor == "user@example.com"
        assert entry.action == "process.create"
        assert entry.resource_type == "process"
        assert entry.details["name"] == "test-process"

    def test_entry_to_dict(self):
        """AuditEntry can be converted to dict."""
        entry = AuditEntry(
            id=AuditId("test-id"),
            timestamp=datetime(2024, 1, 15, 10, 30, 0, tzinfo=timezone.utc),
            actor="admin@example.com",
            action="process.delete",
            resource_type="process",
            resource_id="proc-456",
            details={"reason": "cleanup"},
            ip_address="192.168.1.1",
            user_agent="Mozilla/5.0",
        )

        d = entry.to_dict()

        assert d["id"] == "test-id"
        assert d["actor"] == "admin@example.com"
        assert d["action"] == "process.delete"
        assert d["ip_address"] == "192.168.1.1"
        assert d["details"]["reason"] == "cleanup"

    def test_entry_from_dict(self):
        """AuditEntry can be created from dict."""
        data = {
            "id": "entry-123",
            "timestamp": "2024-01-15T10:30:00+00:00",
            "actor": "user@test.com",
            "action": "execution.trigger",
            "resource_type": "execution",
            "resource_id": "exec-789",
            "details": {"input": "test"},
        }

        entry = AuditEntry.from_dict(data)

        assert str(entry.id) == "entry-123"
        assert entry.actor == "user@test.com"
        assert entry.action == "execution.trigger"

    def test_entry_is_immutable(self):
        """AuditEntry is frozen (immutable)."""
        entry = AuditEntry(
            id=AuditId("test"),
            timestamp=datetime.now(timezone.utc),
            actor="user@example.com",
            action="process.create",
            resource_type="process",
            resource_id=None,
        )

        with pytest.raises(Exception):  # FrozenInstanceError
            entry.actor = "other@example.com"


# =============================================================================
# Tests: AuditId
# =============================================================================


class TestAuditId:
    """Tests for AuditId value object."""

    def test_generate_unique(self):
        """Generated IDs are unique."""
        ids = [AuditId.generate() for _ in range(100)]
        assert len(set(str(i) for i in ids)) == 100

    def test_str_conversion(self):
        """AuditId can be converted to string."""
        aid = AuditId("my-audit-id")
        assert str(aid) == "my-audit-id"


# =============================================================================
# Tests: AuditAction Enum
# =============================================================================


class TestAuditAction:
    """Tests for AuditAction enum."""

    def test_common_actions_defined(self):
        """Common actions are defined."""
        actions = [a.value for a in AuditAction]

        assert "process.create" in actions
        assert "process.update" in actions
        assert "process.delete" in actions
        assert "execution.trigger" in actions
        assert "execution.cancel" in actions
        assert "approval.decide" in actions

    def test_action_values_are_strings(self):
        """Action values are strings."""
        assert AuditAction.PROCESS_CREATE.value == "process.create"
        assert isinstance(AuditAction.EXECUTION_TRIGGER.value, str)


# =============================================================================
# Tests: AuditService
# =============================================================================


class TestAuditService:
    """Tests for AuditService."""

    @pytest.mark.asyncio
    async def test_log_creates_entry(self, audit_service):
        """Logging creates an audit entry."""
        audit_id = await audit_service.log(
            actor="test@example.com",
            action=AuditAction.PROCESS_CREATE,
            resource_type="process",
            resource_id="proc-001",
            details={"name": "My Process"},
        )

        assert audit_id is not None

        # Verify entry was stored
        entry = await audit_service.get_by_id(audit_id)
        assert entry is not None
        assert entry.actor == "test@example.com"
        assert entry.action == "process.create"

    @pytest.mark.asyncio
    async def test_log_with_custom_action(self, audit_service):
        """Logging works with custom action strings."""
        audit_id = await audit_service.log(
            actor="system",
            action="custom.action",
            resource_type="custom",
        )

        entry = await audit_service.get_by_id(audit_id)
        assert entry.action == "custom.action"

    @pytest.mark.asyncio
    async def test_query_all_entries(self, audit_service):
        """Query returns all entries."""
        # Create multiple entries
        for i in range(5):
            await audit_service.log(
                actor=f"user{i}@example.com",
                action="process.read",
                resource_type="process",
            )

        entries = await audit_service.query(limit=100)
        assert len(entries) == 5

    @pytest.mark.asyncio
    async def test_query_with_actor_filter(self, audit_service):
        """Query filters by actor."""
        await audit_service.log(actor="alice@example.com", action="test", resource_type="r")
        await audit_service.log(actor="bob@example.com", action="test", resource_type="r")
        await audit_service.log(actor="alice@example.com", action="test", resource_type="r")

        entries = await audit_service.query(
            filter=AuditFilter(actor="alice@example.com"),
        )

        assert len(entries) == 2
        assert all(e.actor == "alice@example.com" for e in entries)

    @pytest.mark.asyncio
    async def test_query_with_action_filter(self, audit_service):
        """Query filters by action."""
        await audit_service.log(actor="user", action="process.create", resource_type="process")
        await audit_service.log(actor="user", action="process.delete", resource_type="process")
        await audit_service.log(actor="user", action="process.create", resource_type="process")

        entries = await audit_service.query(
            filter=AuditFilter(action="process.create"),
        )

        assert len(entries) == 2

    @pytest.mark.asyncio
    async def test_query_with_resource_filter(self, audit_service):
        """Query filters by resource type and ID."""
        await audit_service.log(actor="user", action="test", resource_type="process", resource_id="p1")
        await audit_service.log(actor="user", action="test", resource_type="execution", resource_id="e1")
        await audit_service.log(actor="user", action="test", resource_type="process", resource_id="p2")

        entries = await audit_service.query(
            filter=AuditFilter(resource_type="process"),
        )
        assert len(entries) == 2

        entries = await audit_service.query(
            filter=AuditFilter(resource_type="process", resource_id="p1"),
        )
        assert len(entries) == 1

    @pytest.mark.asyncio
    async def test_query_with_date_filter(self, audit_service, audit_repo):
        """Query filters by date range."""
        # Create entries directly with specific timestamps
        old_entry = AuditEntry(
            id=AuditId.generate(),
            timestamp=datetime(2024, 1, 1, tzinfo=timezone.utc),
            actor="user",
            action="old",
            resource_type="test",
            resource_id=None,
        )
        await audit_repo.append(old_entry)

        new_entry = AuditEntry(
            id=AuditId.generate(),
            timestamp=datetime(2024, 6, 15, tzinfo=timezone.utc),
            actor="user",
            action="new",
            resource_type="test",
            resource_id=None,
        )
        await audit_repo.append(new_entry)

        # Filter by from_date
        entries = await audit_service.query(
            filter=AuditFilter(from_date=datetime(2024, 6, 1, tzinfo=timezone.utc)),
        )
        assert len(entries) == 1
        assert entries[0].action == "new"

    @pytest.mark.asyncio
    async def test_query_with_pagination(self, audit_service):
        """Query supports pagination."""
        # Create 10 entries
        for i in range(10):
            await audit_service.log(
                actor="user",
                action=f"action-{i}",
                resource_type="test",
            )

        # Get first page
        page1 = await audit_service.query(limit=3, offset=0)
        assert len(page1) == 3

        # Get second page
        page2 = await audit_service.query(limit=3, offset=3)
        assert len(page2) == 3

        # Pages should be different
        assert page1[0].id != page2[0].id

    @pytest.mark.asyncio
    async def test_count_entries(self, audit_service):
        """Count returns correct number."""
        for i in range(7):
            await audit_service.log(
                actor="user" if i % 2 == 0 else "admin",
                action="test",
                resource_type="test",
            )

        total = await audit_service.count()
        assert total == 7

        user_count = await audit_service.count(
            filter=AuditFilter(actor="user"),
        )
        assert user_count == 4  # 0, 2, 4, 6

    @pytest.mark.asyncio
    async def test_get_nonexistent_entry(self, audit_service):
        """Getting nonexistent entry returns None."""
        entry = await audit_service.get_by_id(AuditId("nonexistent-id"))
        assert entry is None


# =============================================================================
# Tests: SqliteAuditRepository
# =============================================================================


class TestSqliteAuditRepository:
    """Tests for SqliteAuditRepository."""

    def test_init_creates_table(self, temp_db_path):
        """Initialization creates the table."""
        import sqlite3

        repo = SqliteAuditRepository(temp_db_path)

        # Check table exists
        conn = sqlite3.connect(temp_db_path)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='audit_entries'"
        )
        assert cursor.fetchone() is not None
        conn.close()

    def test_append_sync(self, audit_repo):
        """Sync append works."""
        entry = AuditEntry(
            id=AuditId.generate(),
            timestamp=datetime.now(timezone.utc),
            actor="sync-user@example.com",
            action="sync.test",
            resource_type="test",
            resource_id=None,
        )

        audit_repo.append_sync(entry)

        # Verify stored
        import asyncio
        loop = asyncio.new_event_loop()
        stored = loop.run_until_complete(audit_repo.get_by_id(entry.id))
        loop.close()

        assert stored is not None
        assert stored.actor == "sync-user@example.com"

    @pytest.mark.asyncio
    async def test_entries_ordered_by_timestamp_desc(self, audit_repo):
        """Entries are ordered by timestamp descending."""
        # Create entries with different timestamps
        for i in range(3):
            entry = AuditEntry(
                id=AuditId.generate(),
                timestamp=datetime(2024, 1, i + 1, tzinfo=timezone.utc),
                actor="user",
                action=f"action-{i}",
                resource_type="test",
                resource_id=None,
            )
            await audit_repo.append(entry)

        entries = await audit_repo.list(limit=10)

        # Should be ordered newest first
        assert entries[0].action == "action-2"  # Jan 3
        assert entries[1].action == "action-1"  # Jan 2
        assert entries[2].action == "action-0"  # Jan 1

    @pytest.mark.asyncio
    async def test_details_serialization(self, audit_repo):
        """Details dict is properly serialized."""
        entry = AuditEntry(
            id=AuditId.generate(),
            timestamp=datetime.now(timezone.utc),
            actor="user",
            action="test",
            resource_type="test",
            resource_id=None,
            details={"nested": {"key": "value"}, "list": [1, 2, 3]},
        )
        await audit_repo.append(entry)

        stored = await audit_repo.get_by_id(entry.id)

        assert stored.details["nested"]["key"] == "value"
        assert stored.details["list"] == [1, 2, 3]
