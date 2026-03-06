# Database.py Refactoring Plan

**Document**: DATABASE_REFACTORING_PLAN.md
**Created**: 2026-02-22
**Status**: DRAFT
**Priority**: P0 (Critical - 1326 lines, blocks AI maintenance)

---

## Problem Statement

`src/backend/database.py` is 1326 lines with a 528-line `init_database()` function. This exceeds the AI context threshold and makes maintenance difficult.

### Current Issues

| Issue | Location | Lines | Severity |
|-------|----------|-------|----------|
| File too large | Full file | 1326 | Critical |
| `init_database()` too long | 469-998 | 528 | Critical |
| 17 migration functions inline | 112-467 | ~355 | High |

### What's Working Well

- **Delegation pattern already implemented**: Operations in `db/*.py` submodules
- **Model re-exports at top**: Backward compatible imports
- **DatabaseManager as facade**: Clean public interface

---

## Refactoring Goals

1. **Fully backward compatible** - No changes to external code
2. **Same public interface** - `db.method()` calls unchanged
3. **Same imports work** - `from database import db, UserCreate, ...`
4. **Incremental** - Can be done in small PRs

---

## Architecture After Refactoring

```
src/backend/
├── database.py          # ~150 lines (facade + re-exports only)
└── db/
    ├── __init__.py      # Package marker
    ├── connection.py    # DB connection utilities (exists)
    ├── migrations.py    # NEW: All migration functions (~400 lines)
    ├── schema.py        # NEW: Schema creation functions (~350 lines)
    ├── users.py         # User operations (exists)
    ├── agents.py        # Agent operations (exists)
    ├── ... (other operation modules)
```

---

## Phase 1: Extract Migrations (PR 1)

### Objective
Move all `_migrate_*` functions to `db/migrations.py`.

### Files Changed
- `src/backend/db/migrations.py` (NEW)
- `src/backend/database.py` (MODIFIED - remove migrations, add import)

### New File: `db/migrations.py`

```python
"""
Database migrations for Trinity platform.

Each migration function handles a specific schema change.
Migrations are idempotent - safe to run multiple times.
"""

from db.connection import get_db_connection


def run_all_migrations(cursor, conn):
    """Run all migrations in order. Called from init_database()."""
    migrations = [
        ("agent_sharing", migrate_agent_sharing_table),
        ("schedule_executions_observability", migrate_schedule_executions_observability),
        ("mcp_api_keys_agent_scope", migrate_mcp_api_keys_agent_scope),
        ("agent_ownership_system_flag", migrate_agent_ownership_system_flag),
        ("agent_ownership_platform_key", migrate_agent_ownership_platform_key),
        ("agent_git_config_source_branch", migrate_agent_git_config_source_branch),
        ("agent_ownership_autonomy", migrate_agent_ownership_autonomy),
        ("agent_ownership_resource_limits", migrate_agent_ownership_resource_limits),
        ("agent_skills", migrate_agent_skills_table),
        ("agent_ownership_full_capabilities", migrate_agent_ownership_full_capabilities),
        ("agent_ownership_read_only_mode", migrate_agent_ownership_read_only_mode),
        ("agent_schedules_execution_config", migrate_agent_schedules_execution_config),
        ("agent_notifications", migrate_agent_notifications_table),
        ("execution_origin_tracking", migrate_execution_origin_tracking),
        ("execution_session_tracking", migrate_execution_session_tracking),
        ("subscription_credentials", migrate_subscription_credentials_table),
        ("agent_ownership_subscription_id", migrate_agent_ownership_subscription_id),
    ]

    for name, migration_fn in migrations:
        try:
            migration_fn(cursor, conn)
        except Exception as e:
            print(f"Migration check ({name}): {e}")


def migrate_agent_sharing_table(cursor, conn):
    """Migrate agent_sharing table from user_id based to email based."""
    # ... (existing implementation)


def migrate_schedule_executions_observability(cursor, conn):
    """Add observability columns to schedule_executions table."""
    # ... (existing implementation)


# ... (all other migration functions)
```

### Changes to `database.py`

```python
# Remove all _migrate_* functions (lines 112-467)
# Add import at top:
from db.migrations import run_all_migrations

# In init_database(), replace individual migration calls with:
def init_database():
    """Initialize the SQLite database with all required tables."""
    db_path = Path(DB_PATH)
    db_path.parent.mkdir(parents=True, exist_ok=True)

    with get_db_connection() as conn:
        cursor = conn.cursor()

        # Run all migrations
        run_all_migrations(cursor, conn)

        # Create tables...
```

### Verification

```bash
# Start services
./scripts/deploy/start.sh

# Verify no errors in logs
docker compose logs backend | grep -i "migration"

# Verify database schema unchanged
sqlite3 ~/trinity-data/trinity.db ".schema" > /tmp/schema_after.sql
# Compare with pre-refactor schema
```

---

## Phase 2: Extract Schema (PR 2)

### Objective
Move CREATE TABLE/INDEX statements to `db/schema.py`.

### Files Changed
- `src/backend/db/schema.py` (NEW)
- `src/backend/database.py` (MODIFIED - use schema module)

### New File: `db/schema.py`

```python
"""
Database schema definitions for Trinity platform.

Contains all CREATE TABLE and CREATE INDEX statements.
Schema creation is idempotent via IF NOT EXISTS.
"""

# Table definitions as constants for documentation
TABLES = {
    "users": """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT,
            role TEXT NOT NULL DEFAULT 'user',
            auth0_sub TEXT UNIQUE,
            name TEXT,
            picture TEXT,
            email TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            last_login TEXT
        )
    """,
    # ... all other tables
}

INDEXES = [
    "CREATE INDEX IF NOT EXISTS idx_users_username ON users(username)",
    "CREATE INDEX IF NOT EXISTS idx_users_auth0_sub ON users(auth0_sub)",
    # ... all other indexes
]


def create_all_tables(cursor):
    """Create all tables. Safe to call multiple times."""
    for table_name, create_sql in TABLES.items():
        cursor.execute(create_sql)


def create_all_indexes(cursor):
    """Create all indexes. Safe to call multiple times."""
    for index_sql in INDEXES:
        cursor.execute(index_sql)


def init_schema(cursor, conn):
    """Initialize complete database schema."""
    create_all_tables(cursor)
    create_all_indexes(cursor)
    conn.commit()
```

### Changes to `database.py`

```python
# Add import:
from db.schema import init_schema

# In init_database(), replace CREATE TABLE/INDEX blocks with:
def init_database():
    """Initialize the SQLite database with all required tables."""
    db_path = Path(DB_PATH)
    db_path.parent.mkdir(parents=True, exist_ok=True)

    with get_db_connection() as conn:
        cursor = conn.cursor()

        # Run migrations first
        run_all_migrations(cursor, conn)

        # Create schema
        init_schema(cursor, conn)

        # Create default admin user
        _ensure_admin_user(cursor, conn)
```

### Verification

Same as Phase 1 - verify schema unchanged and no startup errors.

---

## Phase 3: Simplify `_ensure_admin_user` (PR 3)

### Objective
Move admin user creation to `db/users.py`.

### Changes

1. Move `_ensure_admin_user()` to `UserOperations.ensure_admin_user()`
2. Call from `DatabaseManager.__init__()` instead of `init_database()`

```python
# db/users.py
class UserOperations:
    def ensure_admin_user(self):
        """Ensure admin user exists with properly hashed password."""
        # ... (existing implementation)
```

```python
# database.py
class DatabaseManager:
    def __init__(self):
        init_database()  # Creates schema

        # Initialize operation handlers
        self._user_ops = UserOperations()
        self._user_ops.ensure_admin_user()  # Create admin if needed
        # ...
```

---

## Final State

After all phases, `database.py` will be ~150 lines:

```python
"""
SQLite persistence layer for Trinity platform.

This module provides the DatabaseManager class - a facade for all database operations.
The actual implementations are organized in submodules under db/:
- db/migrations.py: Schema migrations
- db/schema.py: Table and index definitions
- db/users.py: User management
- db/agents.py: Agent ownership and sharing
- ... (other modules)

For backward compatibility, all models and the global `db` instance are
re-exported from this module.
"""

# Re-export models for backward compatibility (lines 1-55)
from db_models import (
    UserCreate, User, AgentOwnership, ...
)

# Re-export connection utilities
from db.connection import get_db_connection, DB_PATH

# Import operation classes
from db.users import UserOperations
from db.agents import AgentOperations
# ... (other imports)

# Import schema and migration utilities
from db.migrations import run_all_migrations
from db.schema import init_schema


def init_database():
    """Initialize the SQLite database."""
    from pathlib import Path
    db_path = Path(DB_PATH)
    db_path.parent.mkdir(parents=True, exist_ok=True)

    with get_db_connection() as conn:
        cursor = conn.cursor()
        run_all_migrations(cursor, conn)
        init_schema(cursor, conn)


class DatabaseManager:
    """Manages SQLite database operations for Trinity platform."""

    def __init__(self):
        init_database()

        # Initialize operation handlers
        self._user_ops = UserOperations()
        self._user_ops.ensure_admin_user()
        self._agent_ops = AgentOperations(self._user_ops)
        # ... (all handler initialization)

    # All delegation methods unchanged (~700 lines)


# Global database manager instance
db = DatabaseManager()
```

---

## Line Count Summary

| Component | Before | After | Change |
|-----------|--------|-------|--------|
| database.py | 1326 | ~850 | -476 |
| db/migrations.py | 0 | ~400 | +400 |
| db/schema.py | 0 | ~350 | +350 |
| **Total** | 1326 | ~1600 | +274 |

**Note**: Total lines increase because we're adding structure, but each file is now under 500 lines and AI-maintainable.

---

## Requirements

### Must Have
- [ ] All existing imports continue to work
- [ ] `from database import db` unchanged
- [ ] `from database import UserCreate, ...` unchanged
- [ ] No changes to any router, service, or test file
- [ ] Database schema identical before/after
- [ ] All tests pass

### Must NOT Do
- [ ] Change DatabaseManager method signatures
- [ ] Change model definitions
- [ ] Rename the `db` global instance
- [ ] Move models out of db_models.py
- [ ] Change any SQL queries

---

## Testing Checklist

### Per-Phase Testing

```bash
# 1. Export schema before refactoring
sqlite3 ~/trinity-data/trinity.db ".schema" > /tmp/schema_before.sql

# 2. Apply refactoring changes

# 3. Restart services
docker compose down && docker compose up -d

# 4. Export schema after
sqlite3 ~/trinity-data/trinity.db ".schema" > /tmp/schema_after.sql

# 5. Compare schemas (should be identical)
diff /tmp/schema_before.sql /tmp/schema_after.sql

# 6. Run API tests
cd tests && python -m pytest -v --tb=short

# 7. Manual smoke test
# - Login as admin
# - Create agent
# - View agent list
# - Delete agent
```

### Integration Points to Verify

| Component | Test |
|-----------|------|
| Routers | All `/api/*` endpoints work |
| MCP Server | Tool calls via MCP succeed |
| Scheduler | Scheduled executions run |
| WebSocket | Real-time updates work |

---

## Risk Assessment

| Risk | Mitigation |
|------|------------|
| Import breakage | Keep all re-exports at top of database.py |
| Schema drift | Compare `.schema` output before/after |
| Migration order | Numbered list ensures correct order |
| Admin user | Explicit test in checklist |

---

## Rollback Plan

If issues found after deployment:
1. Revert the PR
2. Restart services
3. Database schema is unchanged (migrations are idempotent)

---

## Implementation Order

1. **Phase 1**: Extract migrations (~1 hour)
   - Low risk - just moving functions
   - Easy to verify - migrations run on startup

2. **Phase 2**: Extract schema (~1 hour)
   - Medium risk - CREATE TABLE statements
   - Verify with `.schema` comparison

3. **Phase 3**: Move admin user logic (~30 min)
   - Low risk - small change
   - Verify admin login works

---

## Success Criteria

- [ ] `database.py` under 900 lines
- [ ] `init_database()` under 50 lines
- [ ] No migration function in `database.py`
- [ ] All tests pass
- [ ] No external code changes required
