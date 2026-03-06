"""
Database migrations for Trinity platform.

Each migration function handles a specific schema change.
Migrations are idempotent - safe to run multiple times.

Migration Order (as of 2026-02-28):
1. agent_sharing - Email-based sharing (from user_id)
2. schedule_executions_observability - Context/cost/tools columns
3. mcp_api_keys_agent_scope - Agent collaboration support
4. agent_ownership_system_flag - System agent protection
5. agent_ownership_platform_key - Per-agent API key control
6. agent_git_config_source_branch - GitHub source tracking
7. agent_ownership_autonomy - Autonomous scheduling control
8. agent_ownership_resource_limits - Memory/CPU configuration
9. agent_skills - Skill ID to skill_name migration
10. agent_ownership_full_capabilities - Container security settings
11. agent_ownership_read_only_mode - Code protection mode
12. agent_schedules_execution_config - Per-schedule timeout/tools
13. agent_notifications - Notification table creation
14. execution_origin_tracking - AUDIT-001 origin fields
15. execution_session_tracking - EXEC-023 session resume
16. subscription_credentials - SUB-001 subscription table
17. agent_ownership_subscription_id - SUB-001 subscription FK
18. agent_dashboard_values - DASH-001 dashboard history table
19. setup_completed_backfill - Auto-complete setup for existing installs
20. slack_integration_tables - SLACK-001 Slack integration tables
21. agent_ownership_parallel_capacity - CAPACITY-001 parallel execution slots
22. schedule_model_selection - MODEL-001 model selection for tasks/schedules
23. nevermined_tables - NVM-001 Nevermined payment integration tables
"""


def run_all_migrations(cursor, conn):
    """Run all migrations in order. Called from init_database().

    Each migration is wrapped in try/except to log errors but continue.
    Migrations are idempotent - safe to run on existing databases.
    """
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
        ("agent_dashboard_values", _migrate_agent_dashboard_values_table),
        ("setup_completed_backfill", _migrate_setup_completed_backfill),
        ("slack_integration_tables", _migrate_slack_integration_tables),
        ("agent_ownership_parallel_capacity", _migrate_agent_ownership_parallel_capacity),
        ("schedule_model_selection", _migrate_schedule_model_selection),
        ("nevermined_tables", _migrate_nevermined_tables),
    ]

    for name, migration_fn in migrations:
        try:
            migration_fn(cursor, conn)
        except Exception as e:
            print(f"Migration check ({name}): {e}")


def _migrate_agent_sharing_table(cursor, conn):
    """Migrate agent_sharing table from user_id based to email based."""
    # Check if old schema exists (with shared_with_id column)
    cursor.execute("PRAGMA table_info(agent_sharing)")
    columns = {row[1] for row in cursor.fetchall()}

    if "shared_with_id" in columns and "shared_with_email" not in columns:
        print("Migrating agent_sharing table to email-based schema...")

        # Migrate existing data: join with users to get emails
        cursor.execute("""
            SELECT s.id, s.agent_name, u.email, s.shared_by_id, s.created_at
            FROM agent_sharing s
            JOIN users u ON s.shared_with_id = u.id
        """)
        existing_shares = cursor.fetchall()

        # Drop old table
        cursor.execute("DROP TABLE agent_sharing")

        # Create new table with email
        cursor.execute("""
            CREATE TABLE agent_sharing (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                agent_name TEXT NOT NULL,
                shared_with_email TEXT NOT NULL,
                shared_by_id INTEGER NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY (shared_by_id) REFERENCES users(id),
                UNIQUE(agent_name, shared_with_email)
            )
        """)

        # Re-insert migrated data
        for share in existing_shares:
            if share[2]:  # email exists
                cursor.execute("""
                    INSERT INTO agent_sharing (agent_name, shared_with_email, shared_by_id, created_at)
                    VALUES (?, ?, ?, ?)
                """, (share[1], share[2].lower(), share[3], share[4]))

        conn.commit()
        print(f"Migrated {len(existing_shares)} sharing records to email-based schema")


def _migrate_schedule_executions_observability(cursor, conn):
    """Add observability columns to schedule_executions table."""
    cursor.execute("PRAGMA table_info(schedule_executions)")
    columns = {row[1] for row in cursor.fetchall()}

    # Add new columns if they don't exist
    new_columns = [
        ("context_used", "INTEGER"),
        ("context_max", "INTEGER"),
        ("cost", "REAL"),
        ("tool_calls", "TEXT"),
        ("execution_log", "TEXT")  # Full Claude Code execution transcript (JSON)
    ]

    for col_name, col_type in new_columns:
        if col_name not in columns:
            print(f"Adding {col_name} column to schedule_executions...")
            cursor.execute(f"ALTER TABLE schedule_executions ADD COLUMN {col_name} {col_type}")

    conn.commit()


def _migrate_mcp_api_keys_agent_scope(cursor, conn):
    """Add agent_name and scope columns to mcp_api_keys table for agent-to-agent collaboration."""
    cursor.execute("PRAGMA table_info(mcp_api_keys)")
    columns = {row[1] for row in cursor.fetchall()}

    # Add new columns if they don't exist
    new_columns = [
        ("agent_name", "TEXT"),  # Which agent owns this key (NULL for user keys)
        ("scope", "TEXT DEFAULT 'user'")  # "user" or "agent"
    ]

    for col_name, col_type in new_columns:
        if col_name not in columns:
            print(f"Adding {col_name} column to mcp_api_keys for agent collaboration...")
            cursor.execute(f"ALTER TABLE mcp_api_keys ADD COLUMN {col_name} {col_type}")

    conn.commit()


def _migrate_agent_ownership_system_flag(cursor, conn):
    """Add is_system column to agent_ownership table for system agent protection."""
    cursor.execute("PRAGMA table_info(agent_ownership)")
    columns = {row[1] for row in cursor.fetchall()}

    if "is_system" not in columns:
        print("Adding is_system column to agent_ownership for system agent protection...")
        cursor.execute("ALTER TABLE agent_ownership ADD COLUMN is_system INTEGER DEFAULT 0")
        conn.commit()


def _migrate_agent_ownership_platform_key(cursor, conn):
    """Add use_platform_api_key column to agent_ownership table for per-agent API key control."""
    cursor.execute("PRAGMA table_info(agent_ownership)")
    columns = {row[1] for row in cursor.fetchall()}

    if "use_platform_api_key" not in columns:
        print("Adding use_platform_api_key column to agent_ownership for per-agent API key control...")
        cursor.execute("ALTER TABLE agent_ownership ADD COLUMN use_platform_api_key INTEGER DEFAULT 1")
        conn.commit()


def _migrate_agent_git_config_source_branch(cursor, conn):
    """Add source_branch and source_mode columns to agent_git_config for GitHub source tracking."""
    cursor.execute("PRAGMA table_info(agent_git_config)")
    columns = {row[1] for row in cursor.fetchall()}

    new_columns = [
        ("source_branch", "TEXT DEFAULT 'main'"),  # Branch to pull from
        ("source_mode", "INTEGER DEFAULT 0")  # 1 = track source branch directly, 0 = legacy working branch
    ]

    for col_name, col_type in new_columns:
        if col_name not in columns:
            print(f"Adding {col_name} column to agent_git_config for GitHub source tracking...")
            cursor.execute(f"ALTER TABLE agent_git_config ADD COLUMN {col_name} {col_type}")

    conn.commit()


def _migrate_agent_ownership_autonomy(cursor, conn):
    """Add autonomy_enabled column to agent_ownership table for autonomous scheduling control."""
    cursor.execute("PRAGMA table_info(agent_ownership)")
    columns = {row[1] for row in cursor.fetchall()}

    if "autonomy_enabled" not in columns:
        print("Adding autonomy_enabled column to agent_ownership for autonomous scheduling...")
        cursor.execute("ALTER TABLE agent_ownership ADD COLUMN autonomy_enabled INTEGER DEFAULT 0")
        conn.commit()


def _migrate_agent_ownership_resource_limits(cursor, conn):
    """Add memory_limit and cpu_limit columns to agent_ownership table for per-agent resource configuration."""
    cursor.execute("PRAGMA table_info(agent_ownership)")
    columns = {row[1] for row in cursor.fetchall()}

    new_columns = [
        ("memory_limit", "TEXT"),  # e.g., "4g", "8g", "16g"
        ("cpu_limit", "TEXT")  # e.g., "2", "4", "8"
    ]

    for col_name, col_type in new_columns:
        if col_name not in columns:
            print(f"Adding {col_name} column to agent_ownership for resource configuration...")
            cursor.execute(f"ALTER TABLE agent_ownership ADD COLUMN {col_name} {col_type}")

    conn.commit()


def _migrate_agent_ownership_full_capabilities(cursor, conn):
    """Add full_capabilities column to agent_ownership table for container security settings."""
    cursor.execute("PRAGMA table_info(agent_ownership)")
    columns = {row[1] for row in cursor.fetchall()}

    if "full_capabilities" not in columns:
        print("Adding full_capabilities column to agent_ownership for container security settings...")
        cursor.execute("ALTER TABLE agent_ownership ADD COLUMN full_capabilities INTEGER DEFAULT 0")
        conn.commit()


def _migrate_agent_ownership_read_only_mode(cursor, conn):
    """Add read_only_mode and read_only_config columns to agent_ownership table for code protection."""
    cursor.execute("PRAGMA table_info(agent_ownership)")
    columns = {row[1] for row in cursor.fetchall()}

    new_columns = [
        ("read_only_mode", "INTEGER DEFAULT 0"),  # 0 = disabled, 1 = enabled
        ("read_only_config", "TEXT")  # JSON config for blocked/allowed patterns
    ]

    for col_name, col_def in new_columns:
        if col_name not in columns:
            print(f"Adding {col_name} column to agent_ownership for read-only mode...")
            cursor.execute(f"ALTER TABLE agent_ownership ADD COLUMN {col_name} {col_def}")

    conn.commit()


def _migrate_agent_schedules_execution_config(cursor, conn):
    """Add timeout_seconds and allowed_tools columns to agent_schedules table for per-schedule execution config."""
    cursor.execute("PRAGMA table_info(agent_schedules)")
    columns = {row[1] for row in cursor.fetchall()}

    new_columns = [
        ("timeout_seconds", "INTEGER DEFAULT 900"),  # Default 15 minutes
        ("allowed_tools", "TEXT")  # JSON array of allowed tools, NULL = all tools
    ]

    for col_name, col_type in new_columns:
        if col_name not in columns:
            print(f"Adding {col_name} column to agent_schedules for execution configuration...")
            cursor.execute(f"ALTER TABLE agent_schedules ADD COLUMN {col_name} {col_type}")

    conn.commit()


def _migrate_agent_notifications_table(cursor, conn):
    """Create agent_notifications table if it doesn't exist (NOTIF-001)."""
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS agent_notifications (
            id TEXT PRIMARY KEY,
            agent_name TEXT NOT NULL,
            notification_type TEXT NOT NULL,
            title TEXT NOT NULL,
            message TEXT,
            priority TEXT DEFAULT 'normal',
            category TEXT,
            metadata TEXT,
            status TEXT DEFAULT 'pending',
            created_at TEXT NOT NULL,
            acknowledged_at TEXT,
            acknowledged_by TEXT
        )
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_notifications_agent ON agent_notifications(agent_name, created_at DESC)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_notifications_status ON agent_notifications(status)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_notifications_priority ON agent_notifications(priority)")
    conn.commit()


def _migrate_execution_origin_tracking(cursor, conn):
    """Add execution origin tracking columns to schedule_executions table (AUDIT-001).

    Tracks WHO triggered each execution:
    - source_user_id: User who triggered (for manual and MCP user triggers)
    - source_user_email: User email (denormalized for queries)
    - source_agent_name: Calling agent (for agent-to-agent collaboration)
    - source_mcp_key_id: MCP API key ID used (for MCP calls)
    - source_mcp_key_name: MCP API key name (denormalized)
    """
    cursor.execute("PRAGMA table_info(schedule_executions)")
    columns = {row[1] for row in cursor.fetchall()}

    new_columns = [
        ("source_user_id", "INTEGER"),
        ("source_user_email", "TEXT"),
        ("source_agent_name", "TEXT"),
        ("source_mcp_key_id", "TEXT"),
        ("source_mcp_key_name", "TEXT"),
    ]

    for col_name, col_type in new_columns:
        if col_name not in columns:
            print(f"Adding {col_name} column to schedule_executions for origin tracking...")
            cursor.execute(f"ALTER TABLE schedule_executions ADD COLUMN {col_name} {col_type}")

    conn.commit()


def _migrate_execution_session_tracking(cursor, conn):
    """Add claude_session_id column to schedule_executions table (EXEC-023).

    Enables "Continue Execution as Chat" feature by storing Claude Code's
    session_id, which can be used with --resume to continue the session.
    """
    cursor.execute("PRAGMA table_info(schedule_executions)")
    columns = {row[1] for row in cursor.fetchall()}

    if "claude_session_id" not in columns:
        print("Adding claude_session_id column to schedule_executions for session resume...")
        cursor.execute("ALTER TABLE schedule_executions ADD COLUMN claude_session_id TEXT")

    conn.commit()


def _migrate_subscription_credentials_table(cursor, conn):
    """Create subscription_credentials table (SUB-001: Claude Max/Pro Subscription Management).

    Stores encrypted OAuth credentials from Claude Max/Pro subscriptions,
    enabling centralized subscription management and assignment to agents.
    """
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS subscription_credentials (
            id TEXT PRIMARY KEY,
            name TEXT UNIQUE NOT NULL,
            encrypted_credentials TEXT NOT NULL,
            subscription_type TEXT,
            rate_limit_tier TEXT,
            owner_id INTEGER NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY (owner_id) REFERENCES users(id)
        )
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_subscriptions_name ON subscription_credentials(name)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_subscriptions_owner ON subscription_credentials(owner_id)")
    conn.commit()


def _migrate_agent_ownership_subscription_id(cursor, conn):
    """Add subscription_id column to agent_ownership table (SUB-001).

    Links agents to their assigned subscription for Claude Max/Pro authentication.
    """
    cursor.execute("PRAGMA table_info(agent_ownership)")
    columns = {row[1] for row in cursor.fetchall()}

    if "subscription_id" not in columns:
        print("Adding subscription_id column to agent_ownership for subscription management...")
        cursor.execute("ALTER TABLE agent_ownership ADD COLUMN subscription_id TEXT REFERENCES subscription_credentials(id)")

    conn.commit()


def _migrate_agent_skills_table(cursor, conn):
    """Migrate agent_skills table if it has wrong schema (skill_id instead of skill_name)."""
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='agent_skills'")
    if not cursor.fetchone():
        return  # Table doesn't exist yet, will be created fresh

    cursor.execute("PRAGMA table_info(agent_skills)")
    columns = {row[1] for row in cursor.fetchall()}

    # Check if table has old schema (skill_id instead of skill_name)
    if "skill_id" in columns and "skill_name" not in columns:
        print("Migrating agent_skills table: renaming skill_id to skill_name...")

        # Get existing data
        cursor.execute("SELECT id, agent_name, skill_id, assigned_by, assigned_at FROM agent_skills")
        existing_data = cursor.fetchall()

        # Drop old table
        cursor.execute("DROP TABLE agent_skills")

        # Create new table with correct schema
        cursor.execute("""
            CREATE TABLE agent_skills (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                agent_name TEXT NOT NULL,
                skill_name TEXT NOT NULL,
                assigned_by TEXT NOT NULL,
                assigned_at TEXT NOT NULL,
                UNIQUE(agent_name, skill_name)
            )
        """)

        # Reinsert data
        for row in existing_data:
            cursor.execute("""
                INSERT INTO agent_skills (agent_name, skill_name, assigned_by, assigned_at)
                VALUES (?, ?, ?, ?)
            """, (row[1], row[2], row[3], row[4]))

        # Recreate indexes
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_agent_skills_agent ON agent_skills(agent_name)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_agent_skills_skill ON agent_skills(skill_name)")

        conn.commit()
        print(f"Migrated {len(existing_data)} agent_skills records")


def _migrate_agent_dashboard_values_table(cursor, conn):
    """Create agent_dashboard_values table for dashboard history (DASH-001).

    Stores historical widget values from agent dashboards to support:
    - Sparkline visualizations showing value trends over time
    - Historical data analysis without agent being online
    - Platform metrics injection with trend calculation
    """
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS agent_dashboard_values (
            id TEXT PRIMARY KEY,
            agent_name TEXT NOT NULL,
            widget_key TEXT NOT NULL,
            widget_label TEXT,
            widget_type TEXT NOT NULL,
            value_numeric REAL,
            value_text TEXT,
            dashboard_mtime TEXT NOT NULL,
            captured_at TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_dashboard_values_agent_time ON agent_dashboard_values(agent_name, captured_at DESC)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_dashboard_values_widget ON agent_dashboard_values(agent_name, widget_key, captured_at DESC)")
    conn.commit()


def _migrate_setup_completed_backfill(cursor, conn):
    """Backfill setup_completed=true for existing installations.

    Prior to this migration, existing production deployments could have:
    - An admin user with a password hash
    - But no 'setup_completed' entry in system_settings

    This caused the setup wizard to appear on existing installations.
    This migration auto-completes setup for installations that already have
    an admin user with a password set.
    """
    from datetime import datetime

    # Check if setup_completed already exists
    cursor.execute("SELECT value FROM system_settings WHERE key = 'setup_completed'")
    existing = cursor.fetchone()

    if existing:
        # Already set, nothing to do
        return

    # Check if admin user exists with a password hash
    cursor.execute("""
        SELECT password_hash FROM users
        WHERE username = 'admin' AND password_hash IS NOT NULL AND password_hash != ''
    """)
    admin_with_password = cursor.fetchone()

    if admin_with_password:
        # Admin exists with password - mark setup as completed
        print("Backfilling setup_completed=true for existing installation with admin user...")
        cursor.execute("""
            INSERT OR REPLACE INTO system_settings (key, value, updated_at)
            VALUES ('setup_completed', 'true', ?)
        """, (datetime.utcnow().isoformat(),))
        conn.commit()
        print("Setup marked as completed.")


def _migrate_slack_integration_tables(cursor, conn):
    """Create Slack integration tables (SLACK-001).

    Creates three tables for Slack public link integration:
    - slack_link_connections: Links Slack workspaces to public links
    - slack_user_verifications: Tracks verified Slack users
    - slack_pending_verifications: In-progress email verifications
    """
    # Create slack_link_connections table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS slack_link_connections (
            id TEXT PRIMARY KEY,
            link_id TEXT NOT NULL UNIQUE,
            slack_team_id TEXT NOT NULL UNIQUE,
            slack_team_name TEXT,
            slack_bot_token TEXT NOT NULL,
            connected_by TEXT NOT NULL,
            connected_at TEXT NOT NULL,
            enabled INTEGER DEFAULT 1,
            FOREIGN KEY (link_id) REFERENCES agent_public_links(id) ON DELETE CASCADE,
            FOREIGN KEY (connected_by) REFERENCES users(id)
        )
    """)

    # Create slack_user_verifications table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS slack_user_verifications (
            id TEXT PRIMARY KEY,
            link_id TEXT NOT NULL,
            slack_user_id TEXT NOT NULL,
            slack_team_id TEXT NOT NULL,
            verified_email TEXT NOT NULL,
            verification_method TEXT NOT NULL,
            verified_at TEXT NOT NULL,
            FOREIGN KEY (link_id) REFERENCES agent_public_links(id) ON DELETE CASCADE,
            UNIQUE(link_id, slack_user_id, slack_team_id)
        )
    """)

    # Create slack_pending_verifications table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS slack_pending_verifications (
            id TEXT PRIMARY KEY,
            link_id TEXT NOT NULL,
            slack_user_id TEXT NOT NULL,
            slack_team_id TEXT NOT NULL,
            email TEXT,
            code TEXT,
            created_at TEXT NOT NULL,
            expires_at TEXT NOT NULL,
            state TEXT DEFAULT 'awaiting_email',
            FOREIGN KEY (link_id) REFERENCES agent_public_links(id) ON DELETE CASCADE
        )
    """)

    # Create indexes
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_slack_connections_team ON slack_link_connections(slack_team_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_slack_connections_link ON slack_link_connections(link_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_slack_verifications_user ON slack_user_verifications(slack_user_id, slack_team_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_slack_verifications_link ON slack_user_verifications(link_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_slack_pending_user ON slack_pending_verifications(slack_user_id, slack_team_id)")

    conn.commit()


def _migrate_agent_ownership_parallel_capacity(cursor, conn):
    """Add max_parallel_tasks column to agent_ownership table (CAPACITY-001).

    Configures per-agent parallel execution capacity for the /task endpoint.
    Range: 1-10, Default: 3.
    """
    cursor.execute("PRAGMA table_info(agent_ownership)")
    columns = {row[1] for row in cursor.fetchall()}

    if "max_parallel_tasks" not in columns:
        print("Adding max_parallel_tasks column to agent_ownership for parallel capacity...")
        cursor.execute("ALTER TABLE agent_ownership ADD COLUMN max_parallel_tasks INTEGER DEFAULT 3")

    conn.commit()


def _migrate_schedule_model_selection(cursor, conn):
    """Add model columns for MODEL-001: Model Selection for Tasks & Schedules.

    - agent_schedules.model: Model to use when schedule fires (NULL = agent default)
    - schedule_executions.model_used: Records which model was actually used
    """
    # Add model to agent_schedules
    cursor.execute("PRAGMA table_info(agent_schedules)")
    columns = {row[1] for row in cursor.fetchall()}

    if "model" not in columns:
        print("Adding model column to agent_schedules for model selection...")
        cursor.execute("ALTER TABLE agent_schedules ADD COLUMN model TEXT")

    # Add model_used to schedule_executions
    cursor.execute("PRAGMA table_info(schedule_executions)")
    columns = {row[1] for row in cursor.fetchall()}

    if "model_used" not in columns:
        print("Adding model_used column to schedule_executions for model audit...")
        cursor.execute("ALTER TABLE schedule_executions ADD COLUMN model_used TEXT")

    conn.commit()


def _migrate_nevermined_tables(cursor, conn):
    """Create Nevermined payment integration tables (NVM-001).

    - nevermined_agent_config: Per-agent payment configuration with encrypted NVM_API_KEY
    - nevermined_payment_log: Payment verification and settlement audit trail
    """
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS nevermined_agent_config (
            id TEXT PRIMARY KEY,
            agent_name TEXT UNIQUE NOT NULL,
            encrypted_credentials TEXT NOT NULL,
            nvm_environment TEXT NOT NULL,
            nvm_agent_id TEXT NOT NULL,
            nvm_plan_id TEXT NOT NULL,
            credits_per_request INTEGER NOT NULL DEFAULT 1,
            enabled INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS nevermined_payment_log (
            id TEXT PRIMARY KEY,
            agent_name TEXT NOT NULL,
            execution_id TEXT,
            action TEXT NOT NULL,
            subscriber_address TEXT,
            credits_amount INTEGER,
            tx_hash TEXT,
            remaining_balance INTEGER,
            success INTEGER NOT NULL DEFAULT 0,
            error TEXT,
            created_at TEXT NOT NULL
        )
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_nvm_config_agent ON nevermined_agent_config(agent_name)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_nvm_payment_log_agent ON nevermined_payment_log(agent_name, created_at DESC)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_nvm_payment_log_execution ON nevermined_payment_log(execution_id)")
    conn.commit()
