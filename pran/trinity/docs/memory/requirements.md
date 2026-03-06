# Trinity Deep Agent Orchestration Platform - Requirements

> **SINGLE SOURCE OF TRUTH** - All development must trace back to this document.
> Update this file BEFORE implementing any new feature.

## Vision: The Four Pillars of Deep Agency

Trinity implements infrastructure for "System 2" AI — Deep Agents that plan, reason, and execute autonomously.

| Pillar | Description | Implementation Status |
|--------|-------------|----------------------|
| **I. Explicit Planning** | Task DAGs persisting outside context window | ❌ REMOVED (2025-12-23) - Deferred to orchestrator-level |
| **II. Hierarchical Delegation** | Orchestrator-Worker with context quarantine | ✅ Agent-to-Agent via MCP |
| **III. Persistent Memory** | Virtual filesystems, memory folding | ✅ Chat persistence, file browser |
| **IV. Extreme Context Engineering** | High-Order Prompts defining reasoning | ✅ Templates with CLAUDE.md |

## Status Labels
- ⏳ Not Started
- 🚧 In Progress
- ✅ Implemented
- ❌ Removed

---

## 1. Core Agent Management

### 1.1 Agent Creation
- **Status**: ✅ Implemented
- **Description**: Create agents from templates (GitHub or local) or from scratch
- **Key Features**: Web UI, REST API, GitHub templates (`github:Org/repo`), local templates, credential schema auto-detection

### 1.2 Agent Start/Stop Toggle
- **Status**: ✅ Implemented (Updated 2026-01-26)
- **Description**: Start and stop agent containers via unified toggle control
- **Key Features**: Toggle switch shows Running/Stopped state, loading spinner during action, consistent UI across Dashboard, Agents page, and Agent Detail page
- **Components**: `RunningStateToggle.vue` - Reusable toggle component with size variants (sm/md/lg)

### 1.3 Agent Rename (RENAME-001)
- **Status**: ✅ Implemented (2026-03-01)
- **Description**: Rename agents via UI or MCP without deleting and recreating
- **Key Features**: Inline editing with pencil icon, `rename_agent` MCP tool, atomic DB updates, Docker container rename, WebSocket broadcast
- **Restrictions**: System agents cannot be renamed, only owners/admins can rename
- **API**: `PUT /api/agents/{name}/rename` with `{new_name: string}`

### 1.4 Agent Deletion
- **Status**: ✅ Implemented
- **Description**: Delete agents and cleanup resources
- **Key Features**: Container cleanup, network cleanup, cascade delete sharing records

### 1.5 Agent Logs Viewing
- **Status**: ✅ Implemented
- **Description**: View container logs for debugging
- **Key Features**: Logs tab, fixed-height scrollable container, auto-refresh, smart auto-scroll

### 1.6 Agent Live Telemetry
- **Status**: ✅ Implemented
- **Description**: Real-time container metrics in agent header
- **Key Features**: CPU/memory usage, network I/O, uptime display, auto-refresh every 10 seconds

---

## 2. Authentication & Authorization

### 2.1 Email-Based Authentication
- **Status**: ✅ Implemented (2025-12-26)
- **Description**: Passwordless email login with 6-digit verification codes
- **Key Features**: 2-step verification, admin-managed whitelist, auto-whitelist on agent sharing, rate limiting
- **Flow**: `docs/memory/feature-flows/email-authentication.md`

### 2.2 Admin Password Login
- **Status**: ✅ Implemented
- **Description**: Password-based fallback for admin user
- **Key Features**: Bcrypt hashing, first-time setup wizard

### 2.3 Session Persistence
- **Status**: ✅ Implemented
- **Description**: User profile survives page refresh via localStorage JWT

### 2.4 Agent Sharing
- **Status**: ✅ Implemented
- **Description**: Share agents with team members
- **Key Features**: Share via email, access levels (Owner/Shared/Admin), sharing tab for owners

### 2.5 Auth0 OAuth
- **Status**: ❌ Removed (2026-01-01)
- **Reason**: Auth0 SDK caused blank pages on HTTP LAN access. Email auth is simpler and works everywhere.

---

## 3. Credential Management

### 3.1 Manual Credential Entry
- **Status**: ✅ Implemented
- **Description**: Add credentials via UI form with name, value, service

### 3.2 OAuth2 Flows
- **Status**: ✅ Implemented
- **Description**: OAuth2 authentication for Google, Slack, GitHub, Notion
- **Key Features**: MCP-compatible credential normalization

### 3.3 Credential Hot-Reload
- **Status**: ✅ Implemented
- **Description**: Update credentials on running agents without restart
- **Key Features**: Hot-reload via UI paste, writes `.env` and regenerates `.mcp.json`

### 3.4 Bulk Credential Import
- **Status**: ✅ Implemented
- **Description**: Paste `.env`-style KEY=VALUE pairs with template selector

### 3.5 Credential Requirements Extraction
- **Status**: ✅ Implemented
- **Description**: Extract from `.mcp.json.template` and show configured vs missing status

---

## 4. Template System

### 4.1 Local Templates
- **Status**: ✅ Implemented
- **Description**: Auto-discovery from `config/agent-templates/`

### 4.2 GitHub Templates
- **Status**: ✅ Implemented
- **Description**: Clone via `github:Org/repo` format with PAT authentication

### 4.2.1 Admin-Configurable GitHub Templates (TMPL-001)
- **Status**: ✅ Implemented
- **Description**: Admin can configure which GitHub repos appear as agent templates via Settings UI. All metadata (display name, description, resources, MCP servers) is fetched from each repo's `template.yaml` via GitHub API (cached 10 min).
- **Key Features**: `config.py` holds default repo list (no metadata), `system_settings` table (`github_templates` key) stores admin overrides, `GET/PUT/DELETE /api/settings/github-templates` endpoints, Settings UI with add/remove/save/reset
- **Behavior**: `None` (key missing) = use defaults, `[]` = no GitHub templates, `[{...}]` = custom list. Admin-provided display_name overrides repo's template.yaml value.

### 4.3 Template Metadata
- **Status**: ✅ Implemented
- **Description**: Read template.yaml for display name, description, resources, credentials

---

## 5. Agent Chat & Terminal

### 5.1 Agent Terminal
- **Status**: ✅ Implemented (2025-12-25)
- **Description**: Browser-based xterm.js terminal with Claude Code TUI
- **Key Features**: PTY forwarding, mode toggle (Claude/Gemini/Bash), resize support
- **Flow**: `docs/memory/feature-flows/agent-terminal.md`

### 5.2 Chat via Backend API
- **Status**: ✅ Implemented
- **Description**: `/api/agents/{name}/chat` endpoint with stream-json output parsing

### 5.3 Conversation History
- **Status**: ✅ Implemented
- **Description**: Persistent chat history per agent stored in database

### 5.4 Context Window Tracking
- **Status**: ✅ Implemented
- **Description**: Token usage display (e.g., "45.5K / 200K") with color-coded progress bar

### 5.5 Session Cost Tracking
- **Status**: ✅ Implemented
- **Description**: Cumulative cost display across conversation

### 5.6 Authenticated Chat Tab
- **Status**: ✅ Implemented (2026-02-19)
- **Description**: Dedicated Chat tab in Agent Detail with simple bubble UI for authenticated users
- **Key Features**: Session selector dropdown, New Chat button, Dashboard activity tracking (uses `/task` endpoint), shared components with PublicChat
- **Spec**: `docs/requirements/AUTHENTICATED_CHAT_TAB.md`
- **Flow**: `docs/memory/feature-flows/authenticated-chat-tab.md`

### 5.7 Dynamic Thinking Status (THINK-001)
- **Status**: ✅ Implemented (2026-03-03, extended 2026-03-04)
- **Description**: Real-time status labels in Chat tab and Public Chat reflecting agent activity (replaces static "Thinking...")
- **Key Features**: SSE stream subscription, tool-name-to-label mapping, 500ms anti-flicker, 10s heartbeat timeout, async_mode task execution with session persistence
- **Scope**: Authenticated Chat tab + Public Chat links (both use async_mode + SSE streaming)
- **Spec**: `docs/requirements/DYNAMIC_THINKING_STATUS.md`
- **Flow**: `docs/memory/feature-flows/authenticated-chat-tab.md`

---

## 6. Activity Monitoring

### 6.1 Unified Activity Panel
- **Status**: ✅ Implemented
- **Description**: Real-time tool execution tracking with `--output-format stream-json --verbose`

### 6.2 Tool Chips with Counts
- **Status**: ✅ Implemented
- **Description**: Visual counts per tool type, sorted by frequency

### 6.3 Expandable Timeline
- **Status**: ✅ Implemented
- **Description**: List of all tool calls with timestamps and durations

### 6.4 Unified Activity Stream
- **Status**: ✅ Implemented (2025-12-02)
- **Description**: Centralized `agent_activities` table for all runtime activities
- **Flow**: `docs/memory/feature-flows/activity-stream.md`

---

## 7. MCP Server

### 7.1 Trinity MCP Server
- **Status**: ✅ Implemented
- **Description**: Agent orchestration via Model Context Protocol
- **Key Features**: FastMCP with Streamable HTTP, 55 tools, API key authentication
- **Flow**: `docs/memory/feature-flows/mcp-orchestration.md`

### 7.2 Per-User API Keys
- **Status**: ✅ Implemented
- **Description**: Generate, revoke, and track usage per key

---

## 8. Infrastructure

### 8.1 Docker as Source of Truth
- **Status**: ✅ Implemented
- **Description**: No in-memory registry; query Docker directly with container labels

### 8.2 SQLite Data Persistence
- **Status**: ✅ Implemented
- **Description**: Users, ownership, API keys, chat sessions via bind mount

### 8.3 Redis for Secrets
- **Status**: ✅ Implemented
- **Description**: Credential storage, OAuth state with AOF persistence

### 8.4 Audit Logging
- **Status**: ✅ Implemented
- **Description**: Security event tracking via Vector log aggregation

### 8.5 Container Security
- **Status**: ✅ Implemented
- **Description**: Non-root execution, CAP_DROP ALL, isolated network
- **Key Features**: Optional full capabilities mode for containers needing system access

### 8.6 GCP Production Deployment
- **Status**: ✅ Implemented
- **Description**: SSL/TLS via Let's Encrypt, nginx reverse proxy

### 8.7 Vector Log Aggregation
- **Status**: ✅ Implemented (2025-12-31)
- **Description**: Centralized log aggregation via Vector replacing audit-logger
- **Key Features**: Docker socket capture, VRL transforms, platform.json/agents.json output
- **Flow**: `docs/memory/feature-flows/vector-logging.md`

---

## 9. Agent Collaboration

### 9.1 Agent-to-Agent Communication
- **Status**: ✅ Implemented (2025-11-29)
- **Description**: Agents communicate via Trinity MCP with agent-scoped API keys
- **Flow**: `docs/memory/feature-flows/agent-to-agent-collaboration.md`

### 9.2 Agent Permissions
- **Status**: ✅ Implemented (2025-12-10, Updated 2026-02-19)
- **Description**: Explicit permission model controlling which agents can call which
- **Key Features**: Permissions tab in UI, restrictive default (no auto-grant), explicit opt-in
- **Flow**: `docs/memory/feature-flows/agent-permissions.md`

### 9.3 Agent Shared Folders
- **Status**: ✅ Implemented (2025-12-13)
- **Description**: File-based collaboration via shared Docker volumes
- **Key Features**: Expose/consume toggles, permission-gated mounting
- **Flow**: `docs/memory/feature-flows/agent-shared-folders.md`

### 9.4 Collaboration Dashboard
- **Status**: ✅ Implemented (2025-12-02)
- **Description**: Real-time visual graph showing agents and animated connections
- **Key Features**: Vue Flow, draggable nodes, context progress bars, replay mode
- **Flow**: `docs/memory/feature-flows/agent-network.md`

### 9.5 Dashboard Timeline View
- **Status**: ✅ Implemented (2026-01-10)
- **Description**: Graph/Timeline mode toggle with execution visualization
- **Key Features**: Execution boxes (color-coded by trigger), collaboration arrows, live streaming
- **Flow**: `docs/memory/feature-flows/dashboard-timeline-view.md`

### 9.6 Replay Timeline Component
- **Status**: ✅ Implemented (2026-01-04)
- **Description**: Waterfall-style timeline visualization of agent activities
- **Key Features**: Zoom controls (50%-2000%), agent rows, activity bars, communication arrows
- **Flow**: `docs/memory/feature-flows/replay-timeline.md`

### 9.7 Task DAG System
- **Status**: ❌ Removed (2025-12-23)
- **Reason**: Individual agent planning deferred to orchestrator-level. Claude Code handles task management internally.

---

## 10. Scheduling & Autonomy

### 10.1 Agent Scheduling
- **Status**: ✅ Implemented (2025-11-28)
- **Description**: Cron-based automation with APScheduler
- **Key Features**: Schedule CRUD, timezone support, execution history, manual trigger
- **Flow**: `docs/memory/feature-flows/scheduling.md`

### 10.2 Autonomy Mode
- **Status**: ✅ Implemented (2026-01-01)
- **Description**: Master toggle for agent autonomous operation
- **Key Features**: Dashboard toggle, enables/disables all schedules
- **Flow**: `docs/memory/feature-flows/autonomy-mode.md`

### 10.3 Execution Queue
- **Status**: ✅ Implemented
- **Description**: Redis-based queue preventing parallel execution conflicts
- **Flow**: `docs/memory/feature-flows/execution-queue.md`

### 10.4 Execution Termination
- **Status**: ✅ Implemented (2026-01-12)
- **Description**: Stop running executions via process registry
- **Key Features**: SIGINT/SIGKILL flow, queue release, activity tracking
- **Flow**: `docs/memory/feature-flows/execution-termination.md`

### 10.5 Model Selection for Tasks & Schedules (MODEL-001)
- **Status**: ✅ Implemented (2026-03-02)
- **Description**: Select which Claude model to use for task execution and scheduled runs
- **Key Features**: ModelSelector combobox with presets (Opus 4.5/4.6, Sonnet 4.5/4.6, Haiku 4.5), custom model input, localStorage persistence, model_used audit trail in execution records
- **Requirements**: `docs/requirements/MODEL_SELECTION_TASKS_SCHEDULES.md`

---

## 11. GitHub Integration

### 11.1 GitHub Sync
- **Status**: ✅ Implemented (2025-11-29, Updated 2026-02-28)
- **Description**: Two sync modes - Source (pull-only, default) and Working Branch (bidirectional)
- **Key Features**: Pull button, sync button, content folder gitignored, branch selection via URL syntax or parameter
- **Branch Selection** (GIT-002): URL syntax `github:owner/repo@branch` or explicit `source_branch` parameter in MCP create_agent tool
- **Flow**: `docs/memory/feature-flows/github-sync.md`

### 11.2 GitHub Repository Initialization
- **Status**: ✅ Implemented
- **Description**: Initialize GitHub sync for existing agents
- **Flow**: `docs/memory/feature-flows/github-repo-initialization.md`

---

## 12. Platform Operations

### 12.1 Internal System Agent
- **Status**: ✅ Implemented (2025-12-20)
- **Description**: Auto-deployed platform orchestrator (`trinity-system`)
- **Key Features**: Deletion-protected, system-scoped MCP key, permission bypass, ops commands
- **Flow**: `docs/memory/feature-flows/internal-system-agent.md`

### 12.2 System Agent Operations Scope
- **Status**: ✅ Implemented (2025-12-20)
- **Description**: Fleet ops, health monitoring, schedule control, emergency stop
- **Key Features**: `/ops/*` slash commands, configurable thresholds
- **Guiding Principle**: "The system agent manages the orchestra, not the music."

### 12.3 Web Terminal for System Agent
- **Status**: ✅ Implemented (2025-12-25)
- **Description**: Admin-only browser terminal for System Agent
- **Flow**: `docs/memory/feature-flows/web-terminal.md`

### 12.4 System Agent UI Page
- **Status**: ✅ Implemented (2025-12-20)
- **Description**: Admin-only `/system-agent` page with fleet overview and operations console
- **Key Features**: Fleet cards, Emergency Stop, Restart All, Pause/Resume Schedules
- **Flow**: `docs/memory/feature-flows/system-agent-ui.md`

### 12.5 OpenTelemetry Integration
- **Status**: ✅ Implemented (2025-12-20)
- **Description**: OTel metrics export from Claude Code agents
- **Key Features**: Cost, tokens, productivity metrics in Dashboard
- **Flow**: `docs/memory/feature-flows/opentelemetry-integration.md`

### 12.6 System-Wide Trinity Prompt
- **Status**: ✅ Implemented (2025-12-14)
- **Description**: Admin-configurable prompt injected into all agents' CLAUDE.md
- **Flow**: `docs/memory/feature-flows/system-wide-trinity-prompt.md`

### 12.7 Vector Memory
- **Status**: ❌ Removed (2025-12-24)
- **Reason**: Templates should define their own memory. Platform should not inject agent capabilities.

### 12.8 Agent Monitoring Service (MON-001)
- **Status**: ✅ Implemented (2026-02-23)
- **Requirement ID**: MON-001
- **Description**: Multi-layer health monitoring for agent fleet with real-time alerts
- **Key Features**:
  - Docker layer: Container status, CPU/memory, restart count, OOM detection
  - Network layer: Agent HTTP reachability with latency tracking
  - Business layer: Runtime availability, context usage, error rates
  - Real-time WebSocket updates for health state changes
  - Alert cooldowns to prevent notification spam
  - Fleet dashboard with health summary (admin-only)
  - 3 MCP tools: `get_fleet_health`, `get_agent_health`, `trigger_health_check`
- **Status Levels**: healthy → degraded → unhealthy → critical → unknown
- **Flow**: `docs/memory/feature-flows/agent-monitoring.md`

---

## 13. Content & File Management

### 13.1 Per-Agent File Manager
- **Status**: ✅ Implemented (Updated 2026-03-03, Issue #51)
- **Description**: Full-featured file manager in AgentDetail Files tab with two-panel layout (tree + preview)
- **Key Features**: Tree view with search, image/video/audio/PDF/text preview, inline text editing, delete with protected path warnings, show hidden files toggle
- **Components**: Reuses `file-manager/FileTreeNode.vue` and `file-manager/FilePreview.vue`
- **Flow**: `docs/memory/feature-flows/file-browser.md`

### 13.2 File Manager Page (Standalone - Deprecated)
- **Status**: 🗄️ Deprecated (2026-03-03, Issue #51)
- **Description**: Former dedicated `/files` page replaced by per-agent Files tab. Route removed, component preserved.
- **Flow**: `docs/memory/feature-flows/file-manager.md`

### 13.3 Content Folder Convention
- **Status**: ✅ Implemented (2025-12-27)
- **Description**: `content/` directory gitignored by default for large generated assets

### 13.4 Agent Dashboard
- **Status**: ✅ Implemented (2026-01-12, Updated 2026-02-23)
- **Description**: Agent-defined dashboard via `dashboard.yaml` with widget system
- **Key Features**: 11 widget types (metric, status, progress, table, etc.), auto-refresh, historical tracking with sparklines (DASH-001), platform metrics injection
- **DASH-001 Enhancements** (2026-02-23):
  - Historical value tracking in `agent_dashboard_values` table
  - Sparkline charts showing metric trends
  - Trend indicators (up/down/stable with percentage)
  - Auto-injected platform metrics section (Tasks 24h, Success Rate, Cost, Health)
  - Query params: `include_history`, `history_hours`, `include_platform_metrics`
- **Flow**: `docs/memory/feature-flows/agent-dashboard.md`

### 13.5 Tasks Tab
- **Status**: ✅ Implemented
- **Description**: Unified task execution UI in Agent Detail page
- **Key Features**: Trigger manual tasks, monitor queue, view history, stop running tasks, make repeatable
- **Flow**: `docs/memory/feature-flows/tasks-tab.md`

### 13.6 Execution Log Viewer
- **Status**: ✅ Implemented
- **Description**: Modal for viewing Claude Code execution transcripts
- **Flow**: `docs/memory/feature-flows/execution-log-viewer.md`

### 13.7 Execution Detail Page
- **Status**: ✅ Implemented (2026-01-10)
- **Description**: Dedicated page for execution details with metadata, timestamps, transcript
- **Flow**: `docs/memory/feature-flows/execution-detail-page.md`

### 13.8 Live Execution Streaming
- **Status**: ✅ Implemented (2026-01-13)
- **Description**: Real-time streaming of Claude Code execution logs to the Execution Detail page
- **Key Features**:
  - SSE streaming from agent server through backend proxy
  - Live log display with auto-scroll
  - "Live" indicator for running executions
  - "Live" button in TasksPanel (green pulsing badge) for running tasks
  - Stop button integration
  - Late joiner support (buffered entries)
- **Spec**: `docs/requirements/LIVE_EXECUTION_STREAMING.md`

### 13.9 Continue Execution as Chat (EXEC-023)
- **Status**: ✅ Implemented (2026-02-20)
- **Priority**: MEDIUM
- **Description**: Resume failed or completed executions as interactive chat conversations with full context preservation
- **Key Features**:
  - Store Claude Code `session_id` in execution records
  - "Continue as Chat" button on Execution Detail page
  - Uses `--resume {session_id}` for native Claude Code session continuity
  - Full 150K+ token context available without copying/injection
  - Resume banner in Chat tab showing execution context
- **Spec**: `docs/requirements/CONTINUE_EXECUTION_AS_CHAT.md`

---

## 14. Multi-Runtime Support

### 14.1 Runtime Adapter Architecture
- **Status**: ✅ Implemented (2025-12-28)
- **Description**: Abstract interface for agent execution engines
- **Key Features**: ClaudeCodeRuntime, GeminiRuntime, factory function

### 14.2 Gemini CLI Integration
- **Status**: ✅ Implemented (2025-12-28)
- **Description**: Google's Gemini CLI as alternative runtime
- **Key Features**: Free tier, 1M token context, native Google Search

### 14.3 Runtime Configuration
- **Status**: ✅ Implemented (2025-12-28)
- **Description**: Runtime selection via `template.yaml` `runtime:` field
- **Schema**: `runtime: {type: claude-code|gemini-cli, model: string}`

---

## 15. Public Access

### 15.1 Public Agent Links
- **Status**: ✅ Implemented (2025-12-22)
- **Description**: Shareable public links for unauthenticated agent access
- **Key Features**: Optional email verification, rate limiting, usage tracking
- **Flow**: `docs/memory/feature-flows/public-agent-links.md`

### 15.1a Public Chat Session Persistence (PUB-005)
- **Status**: ✅ Implemented (2026-02-17)
- **Description**: Multi-turn conversation persistence for public chat links
- **Key Features**: Session management (email-based or anonymous), message history, New Conversation button, page refresh recovery, context injection for continuity
- **Flow**: `docs/memory/feature-flows/public-agent-links.md#public-chat-session-persistence-pub-005`

### 15.1b Slack Integration for Public Links (SLACK-001)
- **Status**: 🚧 In Progress
- **Requirement ID**: SLACK-001
- **Priority**: P1
- **Description**: Enable Slack as a delivery channel for public agent links. Users chat with agents via DMs to a Slack bot.
- **Key Features**:
  - DMs only (no channel @mentions in Phase 1)
  - One Slack workspace = one public link (simple 1:1 mapping)
  - Email verification for Slack users (auto-verify via Slack profile or email code)
  - Session persistence (reuse `public_chat_sessions` with `slack` identifier type)
  - OAuth flow for workspace connection
  - Signature verification for Slack events
- **Database Tables**:
  - `slack_link_connections` - Connects workspace to public link
  - `slack_user_verifications` - Tracks verified Slack users
  - `slack_pending_verifications` - In-progress email verifications
- **API Endpoints**:
  - `POST /api/public/slack/events` - Slack event receiver
  - `GET /api/public/slack/oauth/callback` - OAuth completion
  - `GET/DELETE /api/agents/{name}/public-links/{id}/slack` - Connection status
  - `POST /api/agents/{name}/public-links/{id}/slack/connect` - Initiate OAuth
- **Spec**: `docs/requirements/SLACK_INTEGRATION.md`
- **Flow**: `docs/memory/feature-flows/slack-integration.md`

### 15.2 First-Time Setup
- **Status**: ✅ Implemented (2025-12-23)
- **Description**: Admin password wizard on fresh install
- **Key Features**: Bcrypt hashing, API key configuration in Settings
- **Flow**: `docs/memory/feature-flows/first-time-setup.md`

### 15.3 Per-Agent API Key Control
- **Status**: ✅ Implemented (2025-12-26)
- **Description**: Agents can use platform API key or user's own Claude subscription
- **Key Features**: Toggle in Terminal tab, container recreation on change

---

## 16. Advanced Features

### 16.1 Agent Resource Allocation
- **Status**: ✅ Implemented (2026-01-02)
- **Description**: Per-agent memory and CPU configuration
- **Flow**: `docs/memory/feature-flows/agent-resource-allocation.md`

### 16.1a Read-Only Mode
- **Status**: ✅ Implemented (2026-02-17)
- **Description**: Per-agent code protection preventing modification of source files
- **Key Features**: Toggle in AgentHeader, PreToolUse hooks intercept Write/Edit/NotebookEdit, blocked patterns (*.py, *.js, etc.), allowed patterns (output/*, content/*)
- **Flow**: `docs/memory/feature-flows/read-only-mode.md`
- **Spec**: `docs/requirements/READ_ONLY_MODE.md`

### 16.2 SSH Access
- **Status**: ✅ Implemented (2026-01-02)
- **Description**: Ephemeral SSH credentials via MCP tool
- **Key Features**: ED25519 keys, configurable TTL, ops setting controlled
- **Flow**: `docs/memory/feature-flows/ssh-access.md`

### 16.3 Agent Info Display
- **Status**: ✅ Implemented
- **Description**: Template metadata display in Info tab
- **Flow**: `docs/memory/feature-flows/agent-info-display.md`

### 16.4 Parallel Headless Execution
- **Status**: ✅ Implemented (2025-12-22)
- **Description**: Stateless parallel task execution via `POST /task` endpoint
- **Key Features**: Bypasses queue, enables orchestrator-worker patterns
- **Flow**: `docs/memory/feature-flows/parallel-headless-execution.md`

### 16.5 System Manifest Deployment
- **Status**: ✅ Implemented (2025-12-18)
- **Description**: Recipe-based multi-agent deployment via YAML manifest
- **Key Features**: Permission presets, shared folders, schedules, auto-start
- **Flow**: `docs/memory/feature-flows/system-manifest.md`

### 16.6 Local Agent Deployment via MCP
- **Status**: ✅ Implemented
- **Description**: Deploy local agents via MCP tool
- **Flow**: `docs/memory/feature-flows/local-agent-deploy.md`

### 16.7 Agents Page UI
- **Status**: ✅ Implemented (2026-01-09)
- **Description**: Grid layout with Dashboard parity for Agents list page
- **Key Features**: 3-column grid, autonomy toggle, execution stats, context bar
- **Flow**: `docs/memory/feature-flows/agents-page-ui-improvements.md`

### 16.8 Dark Mode / Theme Switching
- **Status**: ✅ Implemented (2025-12-14)
- **Description**: Client-side theme system with Light/Dark/System modes
- **Key Features**: localStorage persistence, Tailwind class strategy
- **Flow**: `docs/memory/feature-flows/dark-mode-theme.md`

### 16.9 Events Page UI
- **Status**: ✅ Implemented (2026-02-20)
- **Description**: Dedicated page for viewing and managing agent notifications
- **Key Features**: Filter controls (status, priority, agent, type), stats cards, notification cards with actions, bulk selection, real-time WebSocket updates, navigation badge
- **Spec**: `docs/requirements/EVENTS_PAGE_UI.md`
- **Flow**: `docs/memory/feature-flows/events-page.md`

---

## 17. Planned Features

### 17.1 Horizontal Agent Scalability
- **Status**: ⏳ Not Started
- **Priority**: High
- **Description**: Agent pools with N instances for parallel workloads
- **Key Concepts**: Pool configuration, load balancing, auto-scaling triggers

### 17.2 Event Bus Infrastructure
- **Status**: ⏳ Not Started
- **Priority**: High
- **Description**: Platform-wide pub/sub for agent event broadcasting
- **Key Concepts**: Redis Streams, permission-gated subscriptions, event persistence

### 17.3 Event Handlers & Reactions
- **Status**: ⏳ Not Started
- **Priority**: High
- **Description**: Configure automatic agent reactions to events
- **Key Concepts**: Event matching with filters, debouncing/throttling

### 17.4 Async MCP Chat Commands
- **Status**: ✅ Implemented (2026-01-30)
- **Priority**: High
- **Description**: Non-blocking MCP `chat_with_agent` for parallel multi-agent orchestration
- **Key Features**: `async=true` parameter (requires `parallel=true`), returns `execution_id` immediately, poll `GET /api/agents/{name}/executions/{id}` for results
- **Use Case**: Orchestrator sends tasks to 5 worker agents simultaneously, collects results as they complete

### 17.5 Automated Git Sync
- **Status**: ⏳ Not Started
- **Priority**: Medium
- **Description**: Sync modes - Manual / Scheduled / On Stop

### 17.6 Automated Secret Rotation
- **Status**: ⏳ Not Started
- **Priority**: Medium
- **Description**: Automatic credential rotation with notifications

### 17.7 Kubernetes Deployment
- **Status**: ⏳ Not Started
- **Priority**: Low
- **Description**: Helm charts, StatefulSet for agents

---

## 18. Process Engine (Business Process Orchestration)

> **Design Documents**: `docs/PROCESS_DRIVEN_PLATFORM/`
> **Feature Flows**: `docs/memory/feature-flows/process-engine/`

### 18.1 Process Definition & Storage
- **Status**: ✅ Implemented (2026-01-16)
- **Description**: YAML-based process definitions with validation and versioning
- **Key Features**: JSON schema validation, semantic validation, version management
- **Flow**: `docs/memory/feature-flows/process-engine/process-definition.md`

### 18.2 Process Execution Engine
- **Status**: ✅ Implemented (2026-01-16)
- **Description**: Core engine orchestrating step execution with state machine
- **Key Features**: Step handlers, dependency resolution, parallel branches, retry logic
- **Flow**: `docs/memory/feature-flows/process-engine/process-execution.md`

### 18.3 Process Monitoring
- **Status**: ✅ Implemented (2026-01-16)
- **Description**: Real-time execution monitoring via WebSocket events
- **Key Features**: Live step progress, execution timeline, breadcrumb navigation
- **Flow**: `docs/memory/feature-flows/process-engine/process-monitoring.md`

### 18.4 Human Approval Gates
- **Status**: ✅ Implemented (2026-01-16)
- **Description**: Human-in-the-loop approval steps within processes
- **Key Features**: Approval inbox, timeout handling, decision tracking
- **Flow**: `docs/memory/feature-flows/process-engine/human-approval.md`

### 18.5 Process Scheduling
- **Status**: ✅ Implemented (2026-01-16)
- **Description**: Cron-based schedule triggers and timer steps
- **Key Features**: Cron presets, timezone support, timer delays
- **Flow**: `docs/memory/feature-flows/process-engine/process-scheduling.md`

### 18.6 Process Analytics & Cost Tracking
- **Status**: ✅ Implemented (2026-01-16)
- **Description**: Metrics, trends, and cost threshold alerts
- **Key Features**: Success rates, duration trends, cost aggregation, alerts
- **Flow**: `docs/memory/feature-flows/process-engine/process-analytics.md`

### 18.7 Sub-Processes
- **Status**: ✅ Implemented (2026-01-16)
- **Description**: Calling other processes as steps with parent-child linking
- **Key Features**: Input mapping, output capture, breadcrumb navigation
- **Flow**: `docs/memory/feature-flows/process-engine/sub-processes.md`

### 18.8 Agent Roles (EMI Pattern)
- **Status**: ✅ Implemented (2026-01-16)
- **Description**: Executor/Monitor/Informed role assignments for steps
- **Key Features**: Role matrix UI, InformedAgentNotifier, NDJSON event persistence
- **Flow**: `docs/memory/feature-flows/process-engine/agent-roles-emi.md`

### 18.9 Process Templates
- **Status**: ✅ Implemented (2026-01-16)
- **Description**: Bundled and user-created process templates
- **Key Features**: Template selector, category filtering, user templates
- **Flow**: `docs/memory/feature-flows/process-engine/process-templates.md`

### 18.10 Step Types
The Process Engine supports six step types:

| Step Type | Description | Handler |
|-----------|-------------|---------|
| `agent_task` | Execute task via AI agent | `AgentTaskHandler` |
| `human_approval` | Pause for human decision | `HumanApprovalHandler` |
| `gateway` | Conditional branching | `GatewayHandler` |
| `timer` | Delay execution | `TimerHandler` |
| `notification` | Send notifications | `NotificationHandler` |
| `sub_process` | Call another process | `SubProcessHandler` |

---

## 19. Future Vision

### 19.1 Human-in-the-Loop Improvement
- **Status**: ⏳ Concept Phase
- **Description**: Feedback collection and continuous improvement of agent behavior

### 19.2 Compliance-Ready Methodology
- **Status**: ⏳ Concept Phase
- **Description**: SOC-2 and ISO 27001-compatible development practices
- **Location**: `dev-methodology-template/`

### 19.3 Process Designer UI
- **Status**: ⏳ Concept Phase
- **Description**: Visual drag-and-drop process builder
- **Note**: Currently using YAML editor with live preview

---

## 20. Security & Compliance

### 20.1 Audit Trail System (SEC-001)
- **Status**: ⏳ Pending Implementation
- **Requirement ID**: SEC-001
- **Priority**: HIGH
- **Description**: Comprehensive audit logging for all user and agent actions with full actor attribution. Enables investigation, compliance reporting, and accountability.
- **Key Features**:
  - Append-only `audit_log` table with immutability triggers
  - Full actor attribution (user, agent, MCP client, system)
  - MCP API key tracking per tool call
  - Hash chain for tamper evidence (optional compliance mode)
  - Query API with filters and export (CSV/JSON)
- **Event Categories**:
  - `AGENT_LIFECYCLE`: create, start, stop, delete, recreate
  - `EXECUTION`: task_triggered, chat_started, schedule_triggered
  - `AUTHENTICATION`: login_success, login_failed, logout
  - `AUTHORIZATION`: permission_grant, permission_revoke, share, unshare
  - `CONFIGURATION`: settings_change, resource_limits
  - `CREDENTIALS`: create, delete, reload
  - `MCP_OPERATION`: tool_call, key_create, key_revoke
  - `GIT_OPERATION`: sync, pull, init, commit
  - `SYSTEM`: startup, shutdown, emergency_stop
- **Architecture**: `docs/requirements/AUDIT_TRAIL_ARCHITECTURE.md`
- **Implementation Phases**:
  1. Core infrastructure (table, service, API)
  2. Backend integration (lifecycle, auth, permissions)
  3. MCP integration (tool call audit)
  4. Advanced features (hash chain, export, retention)

### 20.2 Execution Origin Tracking (AUDIT-001)
- **Status**: ⏳ Pending Implementation
- **Requirement ID**: AUDIT-001
- **Priority**: HIGH
- **Description**: Track WHO triggered each execution with full actor attribution. Captures user identity, MCP API key info, and source agent for agent-to-agent calls.
- **Key Features**:
  - Extended `schedule_executions` schema with origin columns
  - User ID and email captured for manual and MCP triggers
  - MCP API key ID and name tracked for external calls
  - Source agent name tracked for agent-to-agent collaboration
  - UI display of origin info on Execution Detail page
  - Filter executions by trigger type (manual/schedule/mcp/agent)
- **New Database Columns**:
  - `source_user_id` (INTEGER) - FK to users table
  - `source_user_email` (TEXT) - Denormalized for queries
  - `source_agent_name` (TEXT) - Calling agent for agent-to-agent
  - `source_mcp_key_id` (TEXT) - MCP API key ID used
  - `source_mcp_key_name` (TEXT) - MCP API key name
- **Spec**: `docs/requirements/EXECUTION_ORIGIN_TRACKING.md`
- **Implementation Phases**:
  1. Database migration and backend CRUD updates
  2. MCP server header integration
  3. Frontend display and filtering

### 20.3 Subscription Management (SUB-002 — replaces SUB-001)
- **Status**: ✅ Implemented (2026-03-03)
- **Requirement ID**: SUB-002
- **Priority**: HIGH
- **Replaces**: SUB-001 (`.credentials.json` injection — removed)
- **Description**: Centralized management of Claude Max/Pro subscription tokens. Register long-lived tokens from `claude setup-token` (~1 year lifetime), assign to multiple agents via `CLAUDE_CODE_OAUTH_TOKEN` env var injection.
- **Key Features**:
  - Subscription registry storing encrypted tokens (AES-256-GCM)
  - MCP tools: `register_subscription`, `list_subscriptions`, `assign_subscription`, `get_agent_auth`, `delete_subscription`
  - REST endpoints: `POST/GET/DELETE /api/subscriptions`, `PUT/DELETE/GET /api/subscriptions/agents/{name}`
  - Token injected as `CLAUDE_CODE_OAUTH_TOKEN` env var on container creation
  - No file injection — env var persists across restarts automatically
  - Auth detection endpoint showing which method each agent uses
  - Fleet auth report at `/api/ops/auth-report`
- **Workflow**:
  1. User runs `claude setup-token` locally to generate long-lived token
  2. Registers subscription via MCP: `register_subscription("name", "sk-ant-oat01-...")`
  3. Assigns to agents: `assign_subscription("agent-name", "subscription-name")`
  4. Agent container is (re)created with `CLAUDE_CODE_OAUTH_TOKEN` env var; `ANTHROPIC_API_KEY` removed
- **Database**: `subscription_credentials` table, `subscription_id` FK on `agent_ownership`
- **Files**:
  - `src/backend/db/subscriptions.py` - Database operations
  - `src/backend/routers/subscriptions.py` - REST API
  - `src/backend/services/subscription_service.py` - Auth mode detection
  - `src/mcp-server/src/tools/subscriptions.ts` - MCP tools

---

## Non-Functional Requirements

### Performance
- Agent creation: < 30 seconds
- Chat response: < 5 seconds for simple queries
- UI responsiveness: < 100ms for interactions
- WebSocket latency: < 500ms for status updates
- **Task list loading: < 1 second** (PERF-001)

### PERF-001: Task List Performance Optimization
- **Status**: ✅ Implemented (2026-02-21)
- **Requirement ID**: PERF-001
- **Priority**: MEDIUM
- **Description**: Optimize task loading on Agent Detail Tasks tab. Current implementation transfers full `execution_log` (100KB+ per execution) for list views that don't display it.
- **Key Features**:
  - Lightweight `ExecutionSummary` response model excluding heavy fields
  - Optimized SQL query selecting only needed columns
  - Composite index on `(agent_name, started_at DESC)`
  - On-demand detail loading when user expands a task
- **Achieved Impact**: 50-100x reduction in data transfer (10MB → 100KB)
- **Spec**: `docs/requirements/TASK_LIST_PERFORMANCE.md`

### Security
- All credentials encrypted at rest (Redis)
- HTTPS in production (Let's Encrypt)
- Container isolation (network, filesystem)
- Comprehensive audit logging via audit_log table (SEC-001)

### Scalability
- Support 50+ concurrent agents
- Multiple backend workers (uvicorn)
- Stateless backend (Docker as truth)

### Reliability
- Agent state survives backend restart
- SQLite persists across container recreation
- Redis AOF for secret durability

### Testing
- Feature flows include Testing sections
- Manual testing before marking complete
- Automated tests for critical paths only

---

## 21. Skills Management (GitHub-Based)

> **Simplified Design**: GitHub repository as the single source of truth for skills.
> No custom version control, no Docker volumes, no complex infrastructure.
> Spec: `docs/requirements/SKILLS_MANAGEMENT.md`

### 21.1 GitHub Skills Library
- **Status**: ⏳ Not Started
- **Description**: Platform syncs skills from a GitHub repository
- **Key Features**:
  - Configure library URL in Settings (admin)
  - `git clone/pull` to local `/data/skills-library/`
  - Auto-sync options: on-demand, on agent start, hourly, daily
  - Uses existing GitHub PAT for private repos

### 21.2 Skill Types (by Convention)
- **Status**: ⏳ Not Started
- **Description**: Three skill types via naming convention
- **Types**:
  - `policy-*` — Always active rules (e.g., `policy-code-review`)
  - `procedure-*` — Step-by-step instructions (e.g., `procedure-incident-response`)
  - (no prefix) — Methodologies/guidance (e.g., `verification`, `tdd`)

### 21.3 Agent Skill Assignment
- **Status**: ⏳ Not Started
- **Description**: Assign specific skills to individual agents
- **Key Features**:
  - Checkbox list in Agent Detail → Skills tab
  - Database stores assignments only (`agent_skills` table)
  - Bulk save via PUT `/api/agents/{name}/skills`

### 21.4 Skill Injection (Copy-Based)
- **Status**: ⏳ Not Started
- **Description**: Copy assigned skills to agent's `~/.claude/skills/` directory
- **Key Features**:
  - Copy on agent start (not symlinks)
  - Manual "Inject to Agent" button for running agents
  - "Sync All Agents" admin action after library update

### 21.5 MCP Tools (Simplified)
- **Status**: ⏳ Not Started
- **Description**: 4 essential MCP tools (reduced from 10)
- **Tools**:
  - `list_skills` — List available skills from library
  - `get_skill` — Get skill content
  - `assign_skill_to_agent` — Assign skill
  - `sync_agent_skills` — Re-inject skills to running agent
- **Removed**: create/update/delete (use GitHub), execute_procedure (use scheduling)

---

## 22. Playbooks Tab (Agent Local Skills)

> **Design**: Browse and invoke agent's local skills directly from UI.
> Spec: `docs/requirements/PLAYBOOKS_TAB.md`
> Flow: `docs/memory/feature-flows/playbooks-tab.md`

### 22.1 Playbooks Tab
- **Status**: ✅ Implemented (2026-02-27)
- **Requirement ID**: PLAYBOOK-001
- **Description**: UI tab to view and invoke agent's local `.claude/skills/` directory
- **Key Features**:
  - Grid display of skills parsed from SKILL.md YAML frontmatter
  - One-click run (sends `/{skill-name}` to `/task` endpoint)
  - Run with instructions (prefills Tasks tab input)
  - Search/filter by name or description
  - Automation badge (autonomous/gated/manual)
- **Agent Endpoint**: `GET /api/skills` - Lists skills from `.claude/skills/`
- **Backend Proxy**: `GET /api/agents/{name}/playbooks`
- **Frontend**: `PlaybooksPanel.vue` component

### 22.2 Skills Tab (Platform Library) - Hidden
- **Status**: ✅ Implemented (hidden)
- **Description**: Platform-level skill library assignment (existing feature)
- **Change**: Tab hidden from visibleTabs but component preserved for potential admin-only access

---

## 23. Nevermined Payment Integration (x402 Protocol)

> **Design**: Per-agent monetization via Nevermined x402 payment protocol.
> Spec: `docs/requirements/NEVERMINED_PAYMENT_INTEGRATION.md`
> Flow: `docs/memory/feature-flows/nevermined-payments.md`

### 23.1 Backend Foundation
- **Status**: ✅ Implemented (2026-03-04)
- **Requirement ID**: NVM-001
- **Description**: Database schema, encrypted credential storage, payment logging
- **Key Features**:
  - `nevermined_agent_config` table with AES-256-GCM encrypted NVM_API_KEY
  - `nevermined_payment_log` audit trail for verify/settle/reject actions
  - Migration #23 (idempotent)
  - `NeverminedOperations` DB module following subscription pattern

### 23.2 Payment Service
- **Status**: ✅ Implemented (2026-03-04)
- **Requirement ID**: NVM-001
- **Description**: Verify/settle lifecycle via payments-py SDK
- **Key Features**:
  - `NeverminedPaymentService` with lazy SDK imports (`NEVERMINED_AVAILABLE` flag)
  - `build_402_response()` using SDK's `build_payment_required()` helper
  - `verify_payment()` — 15s timeout, wrapped in `asyncio.to_thread()`
  - `settle_payment()` — 30s timeout, 3 retries with exponential backoff
  - Graceful degradation: 501 if SDK not installed

### 23.3 Paid Chat Endpoint
- **Status**: ✅ Implemented (2026-03-04)
- **Requirement ID**: NVM-001
- **Description**: Public x402 endpoint for external callers
- **Endpoints**:
  - `POST /api/paid/{agent_name}/chat` — 402/403/200 flow
  - `GET /api/paid/{agent_name}/info` — Public agent info + payment requirements
- **Flow**: No header → 402; invalid token → 403; valid → verify → execute → settle → receipt

### 23.4 Admin Configuration
- **Status**: ✅ Implemented (2026-03-04)
- **Requirement ID**: NVM-001
- **Description**: Authenticated CRUD for Nevermined config
- **Endpoints**:
  - `POST/GET/DELETE /api/nevermined/agents/{name}/config`
  - `PUT /api/nevermined/agents/{name}/config/toggle`
  - `GET /api/nevermined/agents/{name}/payments`
  - `GET /api/nevermined/settlement-failures` (admin)
  - `POST /api/nevermined/retry-settlement/{log_id}` (admin)

### 23.5 Frontend UI
- **Status**: ✅ Implemented (2026-03-04)
- **Description**: Payments tab in Agent Detail page
- **Component**: `NeverminedPanel.vue`
- **Features**: Config form, enable/disable toggle, paid endpoint URL display, payment log table

### 23.6 MCP Tools
- **Status**: ✅ Implemented (2026-03-04)
- **Description**: 4 MCP tools for Nevermined management
- **Tools**: `configure_nevermined`, `get_nevermined_config`, `toggle_nevermined`, `get_nevermined_payments`

---

## Out of Scope

- Multi-tenant deployment (single org only)
- Mobile application
- Fiat/Stripe payment integration (Nevermined handles crypto payments)
- Agent marketplace
