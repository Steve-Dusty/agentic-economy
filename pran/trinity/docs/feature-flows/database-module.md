# Feature: Database Module Architecture

## Overview

Modular database architecture with extracted migrations and schema definitions, reducing the main `database.py` from 1326 to 966 lines while maintaining full backward compatibility.

## User Story

As a developer, I want the database code organized into maintainable modules so that I can easily add migrations, modify schema, and understand the codebase without navigating a 1300+ line file.

## Architecture

```
src/backend/
├── database.py           # 966 lines - Facade + re-exports + DatabaseManager
├── db_models.py          # Pydantic models (unchanged)
└── db/
    ├── __init__.py       # Re-exports for backward compatibility
    ├── connection.py     # DB connection utilities
    ├── migrations.py     # 17 migrations (415 lines)
    ├── schema.py         # All CREATE TABLE/INDEX (538 lines)
    ├── users.py          # UserOperations class
    ├── agents.py         # AgentOperations class
    ├── mcp_keys.py       # McpKeyOperations class
    ├── schedules.py      # ScheduleOperations class
    ├── chat.py           # ChatOperations class
    ├── activities.py     # ActivityOperations class
    ├── permissions.py    # PermissionOperations class
    ├── shared_folders.py # SharedFolderOperations class
    ├── settings.py       # SettingsOperations class
    ├── public_links.py   # PublicLinkOperations class
    ├── email_auth.py     # EmailAuthOperations class
    ├── skills.py         # SkillsOperations class
    ├── public_chat.py    # PublicChatOperations class
    ├── tags.py           # TagOperations class
    ├── system_views.py   # SystemViewOperations class
    ├── notifications.py  # NotificationOperations class
    └── subscriptions.py  # SubscriptionOperations class
```

## Initialization Flow

```
Application Start
       │
       ▼
DatabaseManager.__init__()
       │
       ▼
init_database()
       │
       ├─► db_path.parent.mkdir(parents=True, exist_ok=True)
       │
       ├─► run_all_migrations(cursor, conn)  ── from db/migrations.py
       │         │
       │         └─► 17 migrations in order (idempotent)
       │
       ├─► init_schema(cursor, conn)  ── from db/schema.py
       │         │
       │         ├─► create_all_tables(cursor)  ── 20 tables
       │         └─► create_all_indexes(cursor) ── 40+ indexes
       │
       └─► _ensure_admin_user(cursor, conn)
                 │
                 └─► Create/update admin user with bcrypt hash
```

## Key Files

| File | Lines | Purpose |
|------|-------|---------|
| `src/backend/database.py` | 966 | Facade class, re-exports, init_database() |
| `src/backend/db/migrations.py` | 415 | 17 migration functions |
| `src/backend/db/schema.py` | 538 | TABLES dict, INDEXES list, init_schema() |
| `src/backend/db/__init__.py` | 35 | Re-exports for backward compatibility |

---

## Migrations System

### Location
`src/backend/db/migrations.py`

### Entry Point
```python
# src/backend/database.py:128
run_all_migrations(cursor, conn)
```

### Migration List (in order)
```python
# src/backend/db/migrations.py:34-52
migrations = [
    ("agent_sharing", _migrate_agent_sharing_table),
    ("schedule_executions_observability", _migrate_schedule_executions_observability),
    ("mcp_api_keys_agent_scope", _migrate_mcp_api_keys_agent_scope),
    ("agent_ownership_system_flag", _migrate_agent_ownership_system_flag),
    ("agent_ownership_platform_key", _migrate_agent_ownership_platform_key),
    ("agent_git_config_source_branch", _migrate_agent_git_config_source_branch),
    ("agent_ownership_autonomy", _migrate_agent_ownership_autonomy),
    ("agent_ownership_resource_limits", _migrate_agent_ownership_resource_limits),
    ("agent_skills", _migrate_agent_skills_table),
    ("agent_ownership_full_capabilities", _migrate_agent_ownership_full_capabilities),
    ("agent_ownership_read_only_mode", _migrate_agent_ownership_read_only_mode),
    ("agent_schedules_execution_config", _migrate_agent_schedules_execution_config),
    ("agent_notifications", _migrate_agent_notifications_table),
    ("execution_origin_tracking", _migrate_execution_origin_tracking),
    ("execution_session_tracking", _migrate_execution_session_tracking),
    ("subscription_credentials", _migrate_subscription_credentials_table),
    ("agent_ownership_subscription_id", _migrate_agent_ownership_subscription_id),
]
```

### Migration Pattern
Each migration is idempotent - safe to run multiple times:

```python
# Example: Adding a column (db/migrations.py:147-166)
def _migrate_agent_ownership_system_flag(cursor, conn):
    """Add is_system column to agent_ownership table."""
    cursor.execute("PRAGMA table_info(agent_ownership)")
    columns = {row[1] for row in cursor.fetchall()}

    if "is_system" not in columns:
        print("Adding is_system column...")
        cursor.execute("ALTER TABLE agent_ownership ADD COLUMN is_system INTEGER DEFAULT 0")
        conn.commit()
```

### Error Handling
```python
# db/migrations.py:54-58
for name, migration_fn in migrations:
    try:
        migration_fn(cursor, conn)
    except Exception as e:
        print(f"Migration check ({name}): {e}")
```
Migrations log errors but continue - allows partial recovery.

---

## Schema System

### Location
`src/backend/db/schema.py`

### Entry Point
```python
# src/backend/database.py:131
init_schema(cursor, conn)
```

### Table Definitions
```python
# db/schema.py:29-418
TABLES = {
    "users": """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            ...
        )
    """,
    "agent_ownership": """...""",
    "agent_sharing": """...""",
    # ... 17 more tables
}
```

### Index Definitions
```python
# db/schema.py:424-512
INDEXES = [
    "CREATE INDEX IF NOT EXISTS idx_users_username ON users(username)",
    "CREATE INDEX IF NOT EXISTS idx_users_auth0_sub ON users(auth0_sub)",
    # ... 40+ indexes
]
```

### Schema Functions
```python
# db/schema.py:519-538
def create_all_tables(cursor):
    """Create all tables. Uses IF NOT EXISTS."""
    for table_name, create_sql in TABLES.items():
        cursor.execute(create_sql)

def create_all_indexes(cursor):
    """Create all indexes. Uses IF NOT EXISTS."""
    for index_sql in INDEXES:
        cursor.execute(index_sql)

def init_schema(cursor, conn):
    """Initialize complete database schema."""
    create_all_tables(cursor)
    create_all_indexes(cursor)
    conn.commit()
```

---

## How To: Add a New Migration

### Step 1: Create Migration Function
Add to `src/backend/db/migrations.py`:

```python
def _migrate_your_feature_name(cursor, conn):
    """Description of what this migration does."""
    cursor.execute("PRAGMA table_info(target_table)")
    columns = {row[1] for row in cursor.fetchall()}

    if "new_column" not in columns:
        print("Adding new_column to target_table...")
        cursor.execute("ALTER TABLE target_table ADD COLUMN new_column TEXT")
        conn.commit()
```

### Step 2: Register in Migration List
Add to `run_all_migrations()` list:

```python
# db/migrations.py:34-52
migrations = [
    # ... existing migrations ...
    ("your_feature_name", _migrate_your_feature_name),  # Add at end
]
```

### Step 3: Update Schema (if new default)
Update `TABLES` dict in `db/schema.py` to include the column for fresh installs:

```python
"target_table": """
    CREATE TABLE IF NOT EXISTS target_table (
        ...
        new_column TEXT,  -- Add here
        ...
    )
""",
```

### Migration Types

| Type | Pattern | Example |
|------|---------|---------|
| Add column | `ALTER TABLE ... ADD COLUMN` | `_migrate_agent_ownership_system_flag` |
| Create table | `CREATE TABLE IF NOT EXISTS` | `_migrate_agent_notifications_table` |
| Migrate data | SELECT, DROP, CREATE, INSERT | `_migrate_agent_sharing_table` |
| Add multiple columns | Loop over columns | `_migrate_agent_ownership_resource_limits` |

---

## How To: Add a New Table

### Step 1: Add Table Definition
Add to `TABLES` dict in `src/backend/db/schema.py`:

```python
TABLES = {
    # ... existing tables ...

    "your_new_table": """
        CREATE TABLE IF NOT EXISTS your_new_table (
            id TEXT PRIMARY KEY,
            agent_name TEXT NOT NULL,
            some_field TEXT,
            created_at TEXT NOT NULL,
            FOREIGN KEY (agent_name) REFERENCES agent_ownership(agent_name)
        )
    """,
}
```

### Step 2: Add Indexes
Add to `INDEXES` list in `src/backend/db/schema.py`:

```python
INDEXES = [
    # ... existing indexes ...

    # Your new table indexes
    "CREATE INDEX IF NOT EXISTS idx_your_table_agent ON your_new_table(agent_name)",
    "CREATE INDEX IF NOT EXISTS idx_your_table_field ON your_new_table(some_field)",
]
```

### Step 3: Create Migration (for existing databases)
If this table needs to exist on upgrade (not just fresh install):

```python
# db/migrations.py
def _migrate_your_new_table(cursor, conn):
    """Create your_new_table if it doesn't exist."""
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS your_new_table (
            ...same as schema.py...
        )
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_your_table_agent ON your_new_table(agent_name)")
    conn.commit()
```

### Step 4: Create Operations Module
Create `src/backend/db/your_feature.py`:

```python
"""Your feature database operations."""

from db.connection import get_db_connection

class YourFeatureOperations:
    def create_record(self, agent_name: str, data: dict):
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""...""")
            conn.commit()

    def get_record(self, record_id: str):
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""...""")
            return cursor.fetchone()
```

### Step 5: Wire Up DatabaseManager
Add to `src/backend/database.py`:

```python
# Import at top
from db.your_feature import YourFeatureOperations

# In DatabaseManager.__init__
self._your_feature_ops = YourFeatureOperations()

# Add delegation methods
def create_your_record(self, agent_name: str, data: dict):
    return self._your_feature_ops.create_record(agent_name, data)
```

---

## Backward Compatibility

### All Existing Imports Work
```python
# These continue to work unchanged:
from database import db
from database import UserCreate, User, AgentOwnership
from database import get_db_connection, DB_PATH
```

### Re-exports in database.py
```python
# src/backend/database.py:28-84
from db_models import (
    UserCreate, User, AgentOwnership, AgentShare, ...
)

# src/backend/database.py:86-87
from db.connection import get_db_connection, DB_PATH

# src/backend/database.py:89-91
from db.migrations import run_all_migrations
from db.schema import init_schema
```

### DatabaseManager Interface Unchanged
All 100+ methods on `DatabaseManager` delegate to operation classes but maintain the same signatures:

```python
# Example delegation (src/backend/database.py:238-239)
def get_user_by_username(self, username: str):
    return self._user_ops.get_user_by_username(username)
```

---

## Database Path

```python
# db/connection.py
DB_PATH = os.getenv("TRINITY_DB_PATH", "~/trinity-data/trinity.db")
```

Default: `~/trinity-data/trinity.db`
Override: Set `TRINITY_DB_PATH` environment variable

---

## Testing After Changes

```bash
# 1. Export schema before changes
sqlite3 ~/trinity-data/trinity.db ".schema" > /tmp/schema_before.sql

# 2. Make changes

# 3. Restart backend
docker compose restart backend

# 4. Export schema after
sqlite3 ~/trinity-data/trinity.db ".schema" > /tmp/schema_after.sql

# 5. Verify no regressions (only additions expected)
diff /tmp/schema_before.sql /tmp/schema_after.sql

# 6. Check logs for migration errors
docker compose logs backend | grep -i migration
```

---

## Line Count Summary

| File | Before | After | Change |
|------|--------|-------|--------|
| `database.py` | 1326 | 966 | -360 |
| `db/migrations.py` | 0 | 415 | +415 |
| `db/schema.py` | 0 | 538 | +538 |
| **init_database()** | 528 | 24 | -504 |

Total code increased by ~600 lines, but:
- Each file is under 600 lines (AI-maintainable)
- Clear separation of concerns
- Migrations isolated from business logic
- Schema definitions documented in one place

---

## Related Documents

- **Requirements**: `/Users/eugene/Dropbox/trinity/trinity/docs/requirements/DATABASE_REFACTORING_PLAN.md`
- **Connection**: `/Users/eugene/Dropbox/trinity/trinity/src/backend/db/connection.py`
- **Models**: `/Users/eugene/Dropbox/trinity/trinity/src/backend/db_models.py`
