"""
Database schema definitions for Trinity platform.

Contains all CREATE TABLE and CREATE INDEX statements.
Schema creation is idempotent via IF NOT EXISTS.

Tables are organized by feature area:
- Core: users, agent_ownership, agent_sharing
- Auth: mcp_api_keys, email_whitelist, email_login_codes
- Schedules: agent_schedules, schedule_executions
- Chat: chat_sessions, chat_messages
- Activities: agent_activities
- Permissions: agent_permissions
- Shared Folders: agent_shared_folder_config
- Settings: system_settings
- Public Links: agent_public_links, public_link_verifications, public_link_usage
- Public Chat: public_chat_sessions, public_chat_messages
- Git: agent_git_config
- Skills: agent_skills
- Tags: agent_tags
- System Views: system_views
- Subscriptions: subscription_credentials
- Dashboard History: agent_dashboard_values
"""

# =============================================================================
# Table Definitions
# =============================================================================

TABLES = {
    # -------------------------------------------------------------------------
    # Core Tables
    # -------------------------------------------------------------------------
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

    "agent_ownership": """
        CREATE TABLE IF NOT EXISTS agent_ownership (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            agent_name TEXT UNIQUE NOT NULL,
            owner_id INTEGER NOT NULL,
            created_at TEXT NOT NULL,
            is_system INTEGER DEFAULT 0,
            use_platform_api_key INTEGER DEFAULT 1,
            autonomy_enabled INTEGER DEFAULT 0,
            memory_limit TEXT,
            cpu_limit TEXT,
            read_only_mode INTEGER DEFAULT 0,
            read_only_config TEXT,
            subscription_id TEXT,
            max_parallel_tasks INTEGER DEFAULT 3,
            FOREIGN KEY (owner_id) REFERENCES users(id),
            FOREIGN KEY (subscription_id) REFERENCES subscription_credentials(id)
        )
    """,

    "agent_sharing": """
        CREATE TABLE IF NOT EXISTS agent_sharing (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            agent_name TEXT NOT NULL,
            shared_with_email TEXT NOT NULL,
            shared_by_id INTEGER NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY (shared_by_id) REFERENCES users(id),
            UNIQUE(agent_name, shared_with_email)
        )
    """,

    # -------------------------------------------------------------------------
    # Auth Tables
    # -------------------------------------------------------------------------
    "mcp_api_keys": """
        CREATE TABLE IF NOT EXISTS mcp_api_keys (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            description TEXT,
            key_prefix TEXT NOT NULL,
            key_hash TEXT UNIQUE NOT NULL,
            created_at TEXT NOT NULL,
            last_used_at TEXT,
            usage_count INTEGER DEFAULT 0,
            is_active INTEGER DEFAULT 1,
            user_id INTEGER NOT NULL,
            agent_name TEXT,
            scope TEXT DEFAULT 'user',
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """,

    "email_whitelist": """
        CREATE TABLE IF NOT EXISTS email_whitelist (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            added_by TEXT NOT NULL,
            added_at TEXT NOT NULL,
            source TEXT NOT NULL,
            FOREIGN KEY (added_by) REFERENCES users(id)
        )
    """,

    "email_login_codes": """
        CREATE TABLE IF NOT EXISTS email_login_codes (
            id TEXT PRIMARY KEY,
            email TEXT NOT NULL,
            code TEXT NOT NULL,
            created_at TEXT NOT NULL,
            expires_at TEXT NOT NULL,
            verified INTEGER DEFAULT 0,
            used_at TEXT
        )
    """,

    # -------------------------------------------------------------------------
    # Schedule Tables
    # -------------------------------------------------------------------------
    "agent_schedules": """
        CREATE TABLE IF NOT EXISTS agent_schedules (
            id TEXT PRIMARY KEY,
            agent_name TEXT NOT NULL,
            name TEXT NOT NULL,
            cron_expression TEXT NOT NULL,
            message TEXT NOT NULL,
            enabled INTEGER DEFAULT 1,
            timezone TEXT DEFAULT 'UTC',
            description TEXT,
            owner_id INTEGER NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            last_run_at TEXT,
            next_run_at TEXT,
            timeout_seconds INTEGER DEFAULT 900,
            allowed_tools TEXT,
            model TEXT,
            FOREIGN KEY (owner_id) REFERENCES users(id)
        )
    """,

    "schedule_executions": """
        CREATE TABLE IF NOT EXISTS schedule_executions (
            id TEXT PRIMARY KEY,
            schedule_id TEXT NOT NULL,
            agent_name TEXT NOT NULL,
            status TEXT NOT NULL,
            started_at TEXT NOT NULL,
            completed_at TEXT,
            duration_ms INTEGER,
            message TEXT NOT NULL,
            response TEXT,
            error TEXT,
            triggered_by TEXT NOT NULL,
            context_used INTEGER,
            context_max INTEGER,
            cost REAL,
            tool_calls TEXT,
            execution_log TEXT,
            model_used TEXT,
            FOREIGN KEY (schedule_id) REFERENCES agent_schedules(id)
        )
    """,

    # -------------------------------------------------------------------------
    # Chat Tables
    # -------------------------------------------------------------------------
    "chat_sessions": """
        CREATE TABLE IF NOT EXISTS chat_sessions (
            id TEXT PRIMARY KEY,
            agent_name TEXT NOT NULL,
            user_id INTEGER NOT NULL,
            user_email TEXT NOT NULL,
            started_at TEXT NOT NULL,
            last_message_at TEXT NOT NULL,
            message_count INTEGER DEFAULT 0,
            total_cost REAL DEFAULT 0.0,
            total_context_used INTEGER DEFAULT 0,
            total_context_max INTEGER DEFAULT 200000,
            status TEXT DEFAULT 'active',
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """,

    "chat_messages": """
        CREATE TABLE IF NOT EXISTS chat_messages (
            id TEXT PRIMARY KEY,
            session_id TEXT NOT NULL,
            agent_name TEXT NOT NULL,
            user_id INTEGER NOT NULL,
            user_email TEXT NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            cost REAL,
            context_used INTEGER,
            context_max INTEGER,
            tool_calls TEXT,
            execution_time_ms INTEGER,
            FOREIGN KEY (session_id) REFERENCES chat_sessions(id),
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """,

    # -------------------------------------------------------------------------
    # Activity Tables
    # -------------------------------------------------------------------------
    "agent_activities": """
        CREATE TABLE IF NOT EXISTS agent_activities (
            id TEXT PRIMARY KEY,
            agent_name TEXT NOT NULL,
            activity_type TEXT NOT NULL,
            activity_state TEXT NOT NULL,
            parent_activity_id TEXT,
            started_at TEXT NOT NULL,
            completed_at TEXT,
            duration_ms INTEGER,
            user_id INTEGER,
            triggered_by TEXT NOT NULL,
            related_chat_message_id TEXT,
            related_execution_id TEXT,
            details TEXT,
            error TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id),
            FOREIGN KEY (parent_activity_id) REFERENCES agent_activities(id),
            FOREIGN KEY (related_chat_message_id) REFERENCES chat_messages(id),
            FOREIGN KEY (related_execution_id) REFERENCES schedule_executions(id)
        )
    """,

    # -------------------------------------------------------------------------
    # Permission Tables
    # -------------------------------------------------------------------------
    "agent_permissions": """
        CREATE TABLE IF NOT EXISTS agent_permissions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source_agent TEXT NOT NULL,
            target_agent TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            created_by TEXT NOT NULL,
            UNIQUE(source_agent, target_agent)
        )
    """,

    # -------------------------------------------------------------------------
    # Shared Folder Tables
    # -------------------------------------------------------------------------
    "agent_shared_folder_config": """
        CREATE TABLE IF NOT EXISTS agent_shared_folder_config (
            agent_name TEXT PRIMARY KEY,
            expose_enabled INTEGER DEFAULT 0,
            consume_enabled INTEGER DEFAULT 0,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
    """,

    # -------------------------------------------------------------------------
    # Settings Tables
    # -------------------------------------------------------------------------
    "system_settings": """
        CREATE TABLE IF NOT EXISTS system_settings (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
    """,

    # -------------------------------------------------------------------------
    # Public Links Tables
    # -------------------------------------------------------------------------
    "agent_public_links": """
        CREATE TABLE IF NOT EXISTS agent_public_links (
            id TEXT PRIMARY KEY,
            agent_name TEXT NOT NULL,
            token TEXT UNIQUE NOT NULL,
            created_by TEXT NOT NULL,
            created_at TEXT NOT NULL,
            expires_at TEXT,
            enabled INTEGER DEFAULT 1,
            name TEXT,
            require_email INTEGER DEFAULT 0,
            FOREIGN KEY (agent_name) REFERENCES agent_ownership(agent_name) ON DELETE CASCADE,
            FOREIGN KEY (created_by) REFERENCES users(id)
        )
    """,

    "public_link_verifications": """
        CREATE TABLE IF NOT EXISTS public_link_verifications (
            id TEXT PRIMARY KEY,
            link_id TEXT NOT NULL,
            email TEXT NOT NULL,
            code TEXT NOT NULL,
            created_at TEXT NOT NULL,
            expires_at TEXT NOT NULL,
            verified INTEGER DEFAULT 0,
            session_token TEXT,
            session_expires_at TEXT,
            FOREIGN KEY (link_id) REFERENCES agent_public_links(id) ON DELETE CASCADE
        )
    """,

    "public_link_usage": """
        CREATE TABLE IF NOT EXISTS public_link_usage (
            id TEXT PRIMARY KEY,
            link_id TEXT NOT NULL,
            email TEXT,
            ip_address TEXT,
            message_count INTEGER DEFAULT 0,
            created_at TEXT NOT NULL,
            last_used_at TEXT,
            FOREIGN KEY (link_id) REFERENCES agent_public_links(id) ON DELETE CASCADE
        )
    """,

    # -------------------------------------------------------------------------
    # Public Chat Tables
    # -------------------------------------------------------------------------
    "public_chat_sessions": """
        CREATE TABLE IF NOT EXISTS public_chat_sessions (
            id TEXT PRIMARY KEY,
            link_id TEXT NOT NULL,
            session_identifier TEXT NOT NULL,
            identifier_type TEXT NOT NULL,
            created_at TEXT NOT NULL,
            last_message_at TEXT NOT NULL,
            message_count INTEGER DEFAULT 0,
            total_cost REAL DEFAULT 0.0,
            FOREIGN KEY (link_id) REFERENCES agent_public_links(id) ON DELETE CASCADE,
            UNIQUE(link_id, session_identifier)
        )
    """,

    "public_chat_messages": """
        CREATE TABLE IF NOT EXISTS public_chat_messages (
            id TEXT PRIMARY KEY,
            session_id TEXT NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            cost REAL,
            FOREIGN KEY (session_id) REFERENCES public_chat_sessions(id) ON DELETE CASCADE
        )
    """,

    # -------------------------------------------------------------------------
    # Git Tables
    # -------------------------------------------------------------------------
    "agent_git_config": """
        CREATE TABLE IF NOT EXISTS agent_git_config (
            id TEXT PRIMARY KEY,
            agent_name TEXT UNIQUE NOT NULL,
            github_repo TEXT NOT NULL,
            working_branch TEXT NOT NULL,
            instance_id TEXT NOT NULL,
            source_branch TEXT DEFAULT 'main',
            source_mode INTEGER DEFAULT 0,
            created_at TEXT NOT NULL,
            last_sync_at TEXT,
            last_commit_sha TEXT,
            sync_enabled INTEGER DEFAULT 1,
            sync_paths TEXT,
            FOREIGN KEY (agent_name) REFERENCES agent_ownership(agent_name)
        )
    """,

    # -------------------------------------------------------------------------
    # Skills Tables
    # -------------------------------------------------------------------------
    "agent_skills": """
        CREATE TABLE IF NOT EXISTS agent_skills (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            agent_name TEXT NOT NULL,
            skill_name TEXT NOT NULL,
            assigned_by TEXT NOT NULL,
            assigned_at TEXT NOT NULL,
            UNIQUE(agent_name, skill_name)
        )
    """,

    # -------------------------------------------------------------------------
    # Tags Tables
    # -------------------------------------------------------------------------
    "agent_tags": """
        CREATE TABLE IF NOT EXISTS agent_tags (
            agent_name TEXT NOT NULL,
            tag TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (agent_name, tag),
            FOREIGN KEY (agent_name) REFERENCES agent_ownership(agent_name) ON DELETE CASCADE
        )
    """,

    # -------------------------------------------------------------------------
    # System Views Tables
    # -------------------------------------------------------------------------
    "system_views": """
        CREATE TABLE IF NOT EXISTS system_views (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            description TEXT,
            icon TEXT,
            color TEXT,
            filter_tags TEXT NOT NULL,
            owner_id TEXT NOT NULL,
            is_shared INTEGER DEFAULT 0,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (owner_id) REFERENCES users(id)
        )
    """,

    # -------------------------------------------------------------------------
    # Monitoring Tables (MON-001)
    # -------------------------------------------------------------------------
    "agent_health_checks": """
        CREATE TABLE IF NOT EXISTS agent_health_checks (
            id TEXT PRIMARY KEY,
            agent_name TEXT NOT NULL,
            check_type TEXT NOT NULL,
            status TEXT NOT NULL,
            container_status TEXT,
            cpu_percent REAL,
            memory_percent REAL,
            memory_mb REAL,
            restart_count INTEGER,
            oom_killed INTEGER,
            reachable INTEGER,
            latency_ms REAL,
            runtime_available INTEGER,
            claude_available INTEGER,
            context_percent REAL,
            active_executions INTEGER,
            error_rate REAL,
            error_message TEXT,
            checked_at TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """,

    "monitoring_alert_cooldowns": """
        CREATE TABLE IF NOT EXISTS monitoring_alert_cooldowns (
            id TEXT PRIMARY KEY,
            agent_name TEXT NOT NULL,
            condition TEXT NOT NULL,
            last_alert_at TEXT NOT NULL,
            UNIQUE(agent_name, condition)
        )
    """,

    # -------------------------------------------------------------------------
    # Dashboard History Tables (DASH-001)
    # -------------------------------------------------------------------------
    "agent_dashboard_values": """
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
    """,

    # -------------------------------------------------------------------------
    # Slack Integration Tables (SLACK-001)
    # -------------------------------------------------------------------------
    "slack_link_connections": """
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
    """,

    "slack_user_verifications": """
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
    """,

    "slack_pending_verifications": """
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
    """,

    # Nevermined Payment Integration (NVM-001)
    "nevermined_agent_config": """
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
    """,

    "nevermined_payment_log": """
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
    """,
}

# =============================================================================
# Index Definitions
# =============================================================================

INDEXES = [
    # Core indexes
    "CREATE INDEX IF NOT EXISTS idx_users_username ON users(username)",
    "CREATE INDEX IF NOT EXISTS idx_users_auth0_sub ON users(auth0_sub)",
    "CREATE INDEX IF NOT EXISTS idx_users_email ON users(email)",
    "CREATE INDEX IF NOT EXISTS idx_agent_ownership_owner ON agent_ownership(owner_id)",
    "CREATE INDEX IF NOT EXISTS idx_agent_ownership_name ON agent_ownership(agent_name)",
    "CREATE INDEX IF NOT EXISTS idx_agent_sharing_agent ON agent_sharing(agent_name)",
    "CREATE INDEX IF NOT EXISTS idx_agent_sharing_email ON agent_sharing(shared_with_email)",

    # MCP keys indexes
    "CREATE INDEX IF NOT EXISTS idx_mcp_keys_user ON mcp_api_keys(user_id)",
    "CREATE INDEX IF NOT EXISTS idx_mcp_keys_hash ON mcp_api_keys(key_hash)",
    "CREATE INDEX IF NOT EXISTS idx_mcp_keys_agent ON mcp_api_keys(agent_name)",

    # Schedule indexes
    "CREATE INDEX IF NOT EXISTS idx_schedules_agent ON agent_schedules(agent_name)",
    "CREATE INDEX IF NOT EXISTS idx_schedules_owner ON agent_schedules(owner_id)",
    "CREATE INDEX IF NOT EXISTS idx_schedules_enabled ON agent_schedules(enabled)",

    # Execution indexes
    "CREATE INDEX IF NOT EXISTS idx_executions_schedule ON schedule_executions(schedule_id)",
    "CREATE INDEX IF NOT EXISTS idx_executions_agent ON schedule_executions(agent_name)",
    "CREATE INDEX IF NOT EXISTS idx_executions_status ON schedule_executions(status)",
    # PERF-001: Composite index for Tasks list queries
    "CREATE INDEX IF NOT EXISTS idx_executions_agent_started ON schedule_executions(agent_name, started_at DESC)",

    # Git config indexes
    "CREATE INDEX IF NOT EXISTS idx_git_config_agent ON agent_git_config(agent_name)",
    "CREATE INDEX IF NOT EXISTS idx_git_config_repo ON agent_git_config(github_repo)",

    # Chat session indexes
    "CREATE INDEX IF NOT EXISTS idx_chat_sessions_agent ON chat_sessions(agent_name)",
    "CREATE INDEX IF NOT EXISTS idx_chat_sessions_user ON chat_sessions(user_id)",
    "CREATE INDEX IF NOT EXISTS idx_chat_sessions_status ON chat_sessions(status)",

    # Chat message indexes
    "CREATE INDEX IF NOT EXISTS idx_chat_messages_session ON chat_messages(session_id)",
    "CREATE INDEX IF NOT EXISTS idx_chat_messages_agent ON chat_messages(agent_name)",
    "CREATE INDEX IF NOT EXISTS idx_chat_messages_user ON chat_messages(user_id)",
    "CREATE INDEX IF NOT EXISTS idx_chat_messages_timestamp ON chat_messages(timestamp)",

    # Activity indexes
    "CREATE INDEX IF NOT EXISTS idx_activities_agent ON agent_activities(agent_name, created_at DESC)",
    "CREATE INDEX IF NOT EXISTS idx_activities_type ON agent_activities(activity_type)",
    "CREATE INDEX IF NOT EXISTS idx_activities_state ON agent_activities(activity_state)",
    "CREATE INDEX IF NOT EXISTS idx_activities_user ON agent_activities(user_id)",
    "CREATE INDEX IF NOT EXISTS idx_activities_parent ON agent_activities(parent_activity_id)",
    "CREATE INDEX IF NOT EXISTS idx_activities_chat_msg ON agent_activities(related_chat_message_id)",
    "CREATE INDEX IF NOT EXISTS idx_activities_execution ON agent_activities(related_execution_id)",

    # Permission indexes
    "CREATE INDEX IF NOT EXISTS idx_permissions_source ON agent_permissions(source_agent)",
    "CREATE INDEX IF NOT EXISTS idx_permissions_target ON agent_permissions(target_agent)",

    # Shared folder indexes
    "CREATE INDEX IF NOT EXISTS idx_shared_folders_expose ON agent_shared_folder_config(expose_enabled)",
    "CREATE INDEX IF NOT EXISTS idx_shared_folders_consume ON agent_shared_folder_config(consume_enabled)",

    # Public links indexes
    "CREATE INDEX IF NOT EXISTS idx_public_links_token ON agent_public_links(token)",
    "CREATE INDEX IF NOT EXISTS idx_public_links_agent ON agent_public_links(agent_name)",
    "CREATE INDEX IF NOT EXISTS idx_verifications_link ON public_link_verifications(link_id)",
    "CREATE INDEX IF NOT EXISTS idx_verifications_email ON public_link_verifications(email)",
    "CREATE INDEX IF NOT EXISTS idx_verifications_code ON public_link_verifications(code)",
    "CREATE INDEX IF NOT EXISTS idx_usage_link ON public_link_usage(link_id)",
    "CREATE INDEX IF NOT EXISTS idx_usage_ip ON public_link_usage(ip_address)",

    # Email auth indexes
    "CREATE INDEX IF NOT EXISTS idx_email_whitelist_email ON email_whitelist(email)",
    "CREATE INDEX IF NOT EXISTS idx_email_login_codes_email ON email_login_codes(email)",
    "CREATE INDEX IF NOT EXISTS idx_email_login_codes_code ON email_login_codes(code)",

    # Agent skills indexes
    "CREATE INDEX IF NOT EXISTS idx_agent_skills_agent ON agent_skills(agent_name)",
    "CREATE INDEX IF NOT EXISTS idx_agent_skills_skill ON agent_skills(skill_name)",

    # Agent tags indexes
    "CREATE INDEX IF NOT EXISTS idx_agent_tags_tag ON agent_tags(tag)",
    "CREATE INDEX IF NOT EXISTS idx_agent_tags_agent ON agent_tags(agent_name)",

    # Public chat indexes
    "CREATE INDEX IF NOT EXISTS idx_public_chat_sessions_link ON public_chat_sessions(link_id)",
    "CREATE INDEX IF NOT EXISTS idx_public_chat_sessions_identifier ON public_chat_sessions(session_identifier)",
    "CREATE INDEX IF NOT EXISTS idx_public_chat_messages_session ON public_chat_messages(session_id)",

    # System views indexes
    "CREATE INDEX IF NOT EXISTS idx_system_views_owner ON system_views(owner_id)",

    # Monitoring indexes (MON-001)
    "CREATE INDEX IF NOT EXISTS idx_health_agent_time ON agent_health_checks(agent_name, checked_at DESC)",
    "CREATE INDEX IF NOT EXISTS idx_health_status ON agent_health_checks(status)",
    "CREATE INDEX IF NOT EXISTS idx_health_type ON agent_health_checks(check_type)",
    "CREATE INDEX IF NOT EXISTS idx_health_checked_at ON agent_health_checks(checked_at)",
    "CREATE INDEX IF NOT EXISTS idx_alert_cooldowns_agent ON monitoring_alert_cooldowns(agent_name)",

    # Dashboard history indexes (DASH-001)
    "CREATE INDEX IF NOT EXISTS idx_dashboard_values_agent_time ON agent_dashboard_values(agent_name, captured_at DESC)",
    "CREATE INDEX IF NOT EXISTS idx_dashboard_values_widget ON agent_dashboard_values(agent_name, widget_key, captured_at DESC)",

    # Slack integration indexes (SLACK-001)
    "CREATE INDEX IF NOT EXISTS idx_slack_connections_team ON slack_link_connections(slack_team_id)",
    "CREATE INDEX IF NOT EXISTS idx_slack_connections_link ON slack_link_connections(link_id)",
    "CREATE INDEX IF NOT EXISTS idx_slack_verifications_user ON slack_user_verifications(slack_user_id, slack_team_id)",
    "CREATE INDEX IF NOT EXISTS idx_slack_verifications_link ON slack_user_verifications(link_id)",
    "CREATE INDEX IF NOT EXISTS idx_slack_pending_user ON slack_pending_verifications(slack_user_id, slack_team_id)",

    # Nevermined payment indexes (NVM-001)
    "CREATE INDEX IF NOT EXISTS idx_nvm_config_agent ON nevermined_agent_config(agent_name)",
    "CREATE INDEX IF NOT EXISTS idx_nvm_payment_log_agent ON nevermined_payment_log(agent_name, created_at DESC)",
    "CREATE INDEX IF NOT EXISTS idx_nvm_payment_log_execution ON nevermined_payment_log(execution_id)",
]


# =============================================================================
# Schema Functions
# =============================================================================

def create_all_tables(cursor):
    """Create all tables. Safe to call multiple times (uses IF NOT EXISTS)."""
    for table_name, create_sql in TABLES.items():
        cursor.execute(create_sql)


def create_all_indexes(cursor):
    """Create all indexes. Safe to call multiple times (uses IF NOT EXISTS)."""
    for index_sql in INDEXES:
        cursor.execute(index_sql)


def init_schema(cursor, conn):
    """Initialize complete database schema.

    Creates all tables and indexes. Safe to call on existing database.
    """
    create_all_tables(cursor)
    create_all_indexes(cursor)
    conn.commit()
