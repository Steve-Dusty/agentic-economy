# Trinity Roadmap

> **Purpose**: Phased implementation plan derived from requirements.
> Work topmost incomplete items. All items must trace to `requirements.md`.
>
> **Vision**: Trinity implements the Four Pillars of Deep Agency for System 2 AI.

---

## Current Priority Queue

### 🐛 Bug Fixes (Priority)

| Status | Item | Description | Priority |
|--------|------|-------------|----------|
| ✅ | **SSH Connection String Returns Localhost** | **Fixed 2026-02-13**: Added `FRONTEND_URL` domain extraction as priority #2 in `get_ssh_host()`. Production deployments now correctly return domain (e.g., `trinity.abilityai.dev`) instead of `localhost`. See `ssh_service.py:479-567`. | **HIGH** |
| ✅ | **Execution Queue Race Conditions** | **Fixed 2026-01-14**: (1) `submit()` now uses atomic `SET NX EX` for slot acquisition, (2) `complete()` uses Lua script for atomic pop-and-set, (3) `get_all_busy_agents()` uses `SCAN` instead of blocking `KEYS`. All 20 queue tests pass. See `docs/memory/feature-flows/execution-queue.md` (EQ-H1, EQ-H2, EQ-M1 from audit report). | **HIGH** |
| ✅ | **Missing Auth on Lifecycle Endpoints** | **Fixed 2026-01-21**: Verified endpoints `start_agent` (line 316), `stop_agent` (line 343), and `get_logs` (line 368) all use `AuthorizedAgentByName` dependency which calls `db.can_user_access_agent()`. See `dependencies.py:228-255` (AL-H1, AL-H2). | **HIGH** |
| ✅ | **Container Security Inconsistency** | **Fixed 2026-01-14**: Added `RESTRICTED_CAPABILITIES` and `FULL_CAPABILITIES` constants in `lifecycle.py:31-49`. Both `crud.py` and `lifecycle.py` now use these constants with consistent security: always `cap_drop=['ALL']`, always `apparmor:docker-default`, always `tmpfs noexec,nosuid`. See `lifecycle.py:343-368`, `crud.py:462-464` (AL-H3). | **HIGH** |
| ✅ | **Duplicate Schedule Execution** | **Fixed 2026-01-13**: Implemented dedicated scheduler service with Redis distributed locking. See `src/scheduler/`, `docs/memory/feature-flows/scheduler-service.md`. | **HIGH** |
| ✅ | **Process Engine: Template Variables Not Substituted** | **Fixed 2026-01-23**: Added `ExpressionEvaluator` to `HumanApprovalHandler`. `_evaluate_template()` method creates `EvaluationContext` from step context and calls `evaluate()` on `title` and `description` before creating `ApprovalRequest`. See `human_approval.py:106-126, 186-188`. Unit tests added in `test_approval_handler.py`. | **HIGH** |
| ✅ | **Shared Folders: Template Config Not Extracted** | **Fixed 2026-01-23**: Added `shared_folders` extraction from `template.yaml` (lines 173-179) and DB upsert before container creation (lines 394-404). Now templates with `shared_folders: expose: true` correctly get `/shared-out/` mounted. See `crud.py:92,173-179,394-404`. Impacts 13 templates: `dd-*`, `demo-researcher`, `demo-analyst`. | **HIGH** |
| ✅ | Executions 404 for Non-Existent Agent | **Verified 2026-01-27**: Already fixed. `AuthorizedAgent` dependency validates agent existence via `db.get_agent_owner()` and returns 404 "Agent not found" for non-existent agents. See `dependencies.py:198-202`. | LOW |
| ✅ | Test Client Headers Bug | **Fixed 2026-01-27**: Added header merging to `AsyncTrinityApiClient` methods (get, post, put, delete) matching sync client pattern. Now pops `headers` from kwargs and merges with auth headers. See `tests/utils/api_client.py:208-280`. | LOW |
| ✅ | Emergency Stop Test Timeout | **Fixed 2026-01-27**: Added `system_prefix` query parameter to `POST /api/ops/emergency-stop` endpoint. Test now uses `system_prefix=nonexistent-test-prefix-xyz` to verify structure without stopping agents. Test completes in 0.25s (was timing out). See `routers/ops.py:607-682`, `tests/test_ops.py:367-391`. | LOW |
| ✅ | Context % Calculation Bug | **Fixed 2025-12-12**: Main bug was in agent_server/routers/chat.py incorrectly summing input_tokens + cache_creation_tokens + cache_read_tokens, causing >100% display (130%, 289%). cache_creation and cache_read are billing SUBSETS, not additional tokens. Now uses metadata.input_tokens directly (authoritative total from modelUsage). Also fixed in scheduler_service.py (2 locations, 2025-12-06) and claude_code.py logging. | HIGH |
| ✅ | Template Detail Endpoint 404 | **Fixed 2025-12-22**: `GET /api/templates/{id}` returned 404 for GitHub templates like `github:org/repo`. Root cause: The `/` in the template ID was interpreted as path separator. Fix: Changed route from `{template_id}` to `{template_id:path}` to capture full path including slashes. | MEDIUM |
| ✅ | .env Template Endpoint Bug | **Verified 2025-12-22**: Endpoint works correctly. Code at lines 110-130 already handles both string credentials (GitHub templates) and dict credentials (local templates). Tested all GitHub templates + local templates - all pass. | MEDIUM |

---

### Phase 9: Deep Agent Core Infrastructure (Pillar I - Explicit Planning)
🚧 **In Progress** — *Critical for Deep Agent positioning*

| Status | Item | Description | Priority |
|--------|------|-------------|----------|
| ✅ | Task DAG Engine (Backend) | External task graph representation - API + storage | HIGH |
| ✅ | Task State Tracking | pending → active → completed → failed state machine | HIGH |
| ✅ | Plan Persistence | Store/restore task DAGs across sessions | HIGH |
| ✅ | Trinity Meta-Prompt Injection | Platform injects planning commands at startup | HIGH |
| ✅ | Task DAG Visualization (Dashboard) | AgentNode shows current task + progress bar in Collaboration Dashboard | HIGH |
| ✅ | **AgentDetail Plans UI** | Plans tab showing plan list, task details, status badges (2025-12-07) | HIGH |
| ✅ | **Agent Permissions (9.10)** | Permission grants control which agents can call each other (2025-12-13) | HIGH |
| ✅ | **Agent Shared Folders (9.11)** | File-based collaboration via shared Docker volumes (2025-12-13) | HIGH |
| ⏳ | Task Actions UI | Manual complete/fail/re-run buttons for tasks | LOW |
| ⏳ | Failure Recovery | Plan restructuring when steps fail (add debug nodes) | MEDIUM |
| ⏳ | Sentinel/Watchdog Agents | Low-cost monitors detecting infinite loops, human escalation | MEDIUM |
| ⏳ | Thinking Budget | Cost limits per reasoning task ($X max spend) | MEDIUM |

### Phase 10: Deep Agent Memory & Observability (Pillar III Enhancement)
🚧 **In Progress**

| Status | Item | Description | Priority |
|--------|------|-------------|----------|
| ❌ | ~~Agent Vector Memory (Chroma)~~ | REMOVED (2025-12-24) - Templates should define their own memory | ~~MEDIUM~~ |
| ❌ | ~~Chroma MCP Server~~ | REMOVED (2025-12-24) - Platform should not inject agent capabilities | ~~HIGH~~ |
| ⏳ | Memory Folding | Periodic context compression to summary files | HIGH |
| ⏳ | Reasoning Chain Logs | Capture "why" decisions, not just tool calls | MEDIUM |
| ⏳ | Cognitive Rollback | Git-based agent state restoration | MEDIUM |
| ⏳ | Vectorized Episodic Memory | Auto-store conversations for "Have I solved this before?" | LOW |

### Phase 11: Ecosystem & Enterprise
🚧 **In Progress**

| Status | Item | Description | Priority |
|--------|------|-------------|----------|
| ✅ | **System Manifest (10.7)** | Recipe-based multi-agent deployment via YAML - complete (agent creation, conflict resolution, trinity_prompt, folders, schedules, permissions, auto-start). Completed 2025-12-18. | HIGH |
| ✅ | **OpenTelemetry Integration** | OTel Collector + env var injection for Claude Code metrics export. Completed 2025-12-20. | HIGH |
| ✅ | **OpenTelemetry UI (10.8)** | Display OTel metrics in Dashboard - cost, tokens, productivity. Backend API + header summary + panel detail. Completed 2025-12-20. | HIGH |
| ✅ | **Internal System Agent (11.1)** | Auto-deployed platform orchestrator (`trinity-system`) with deletion protection, system-scoped MCP key, permission bypass. Completed 2025-12-20. | HIGH |
| ✅ | **Parallel Headless Execution (12.1)** | Stateless parallel task execution - enables orchestrator to spawn N worker tasks simultaneously. `POST /api/agents/{name}/task` bypasses queue. MCP `chat_with_agent(parallel=true)`. Completed 2025-12-22. | **HIGH** |
| ✅ | **OWASP Security Hardening** | Fixed 7/14 OWASP Top 10:2025 issues - SECRET_KEY, password hashing, Redis auth, WebSocket auth, CORS, error sanitization. Completed 2025-12-23. | **HIGH** |
| ✅ | **Web Terminal for System Agent (11.5)** | Browser-based xterm.js terminal with PTY forwarding via Docker exec. Full Claude Code TUI. Admin-only, no SSH exposure. Completed 2025-12-25. | **HIGH** |
| ✅ | **Dedicated Scheduler Service (11.6)** | **Completed 2026-01-13**: Standalone scheduler in `src/scheduler/`. Redis distributed locks, 71 tests, Docker deployment. See `docs/memory/feature-flows/scheduler-service.md`. | **HIGH** |
| ⏳ | **Audit Trail System (SEC-001)** | Comprehensive audit logging for user/agent actions with full actor attribution. Append-only `audit_log` table, MCP tool call tracking, hash chain for tamper evidence. See `docs/requirements/AUDIT_TRAIL_ARCHITECTURE.md`. | **HIGH** |
| ⏳ | System Manifest UI | Upload YAML, view deployment results, group agents by system prefix | MEDIUM |
| ⏳ | A2A Protocol Support | Agent discovery and negotiation across boundaries | LOW |
| ⏳ | Agent collaboration execution tracking | Extend schedule_executions | LOW |
| ⏳ | Automated sync modes (scheduled, on-stop) | GitOps enhancement | LOW |
| ⏳ | Automated secret rotation | Security enhancement | LOW |

### Phase 11.5: Content Management & File Operations
🚧 **In Progress** — *Essential for agents generating large assets (video, audio, exports)*

| Status | Item | Description | Priority |
|--------|------|-------------|----------|
| ✅ | **Content Folder Convention (12.1)** | `content/` directory gitignored by default, persists across restarts. Implemented 2025-12-27. | **HIGH** |
| ✅ | **File Manager Page (12.2)** | Dedicated `/files` page with agent selector, two-panel layout (tree + preview), delete operations. Implemented 2025-12-27. | **HIGH** |
| ✅ | File Preview Support | Preview images, video, audio, text/code, PDF in right panel. Implemented 2025-12-27. | HIGH |
| ✅ | Delete Operations | Delete file/folder with confirmation, protected file warnings. Implemented 2025-12-27. | HIGH |
| ⏳ | Create Folder | Create new directories in agent workspace | MEDIUM |

**Content Convention**:
```
/home/developer/
├── [workspace files]     # Synced to Git
├── content/              # NOT synced - videos, audio, exports
│   ├── videos/
│   ├── audio/
│   └── exports/
└── .gitignore            # Includes: content/
```

### Phase 12: Agent Perception & Attention (Cognitive Patterns)
⏳ **Pending** — *Emergent coordination via event-driven cognition*

| Status | Item | Description | Priority |
|--------|------|-------------|----------|
| ⏳ | **Event Bus Infrastructure** | Platform-wide pub/sub system for agent event broadcasting and subscription | HIGH |
| ⏳ | Event Types & Schema | Define standard event types (task_completed, anomaly_detected, resource_available, attention_required) | HIGH |
| ⏳ | Agent Event Subscriptions | Agents declare interest in event types via template.yaml or runtime API | MEDIUM |
| ⏳ | Event Persistence & Replay | Store events for late-joining agents and debugging | MEDIUM |
| ⏳ | **Attention Amplification Pattern** | Cognitive pattern: agents select salient events from perception and amplify to others | HIGH |
| ⏳ | Salience Scoring | Agents assign importance scores to perceived events based on relevance to their goals | MEDIUM |
| ⏳ | Broadcast Amplification | High-salience events re-broadcast with amplification metadata (source_agent, salience_score, reasoning) | MEDIUM |
| ⏳ | Attention Cascade Detection | Platform detects when multiple agents amplify same event (emergent consensus) | LOW |
| ⏳ | Attention Dashboard | Visualize event flow and amplification patterns in Collaboration Dashboard | LOW |

**Cognitive Pattern: Attention Amplification**
```
1. Agent perceives events from subscribed channels
2. Agent evaluates salience: "Does this require attention?"
3. High-salience events are re-broadcast with amplification:
   {
     "type": "attention_required",
     "original_event": {...},
     "amplified_by": "agent-name",
     "salience_score": 0.92,
     "reasoning": "Anomaly in data pipeline may affect downstream agents"
   }
4. Other agents see amplified events with social proof
5. Platform tracks amplification cascades for emergent coordination
```

---

## Completed Phases

### Phase 7: GitHub Sync (Source Mode + Working Branch Mode)
✅ **Completed: 2025-11-29, Updated: 2025-12-30**

**Architecture Document**: `docs/GITHUB_NATIVE_AGENTS.md`

| Status | Item | Completed |
|--------|------|-----------|
| ✅ | Database schema: `agent_git_config` table | 2025-11-29 |
| ✅ | Working branch mode: Create branch on GitHub-template creation | 2025-11-29 |
| ✅ | Store repo URL, branch name, instance ID in database | 2025-11-29 |
| ✅ | POST `/api/agents/{name}/git/sync` endpoint (push) | 2025-11-29 |
| ✅ | POST `/api/agents/{name}/git/pull` endpoint | 2025-11-29 |
| ✅ | Git operations: stage, commit, force push | 2025-11-29 |
| ✅ | "Sync to GitHub" button in agent detail UI | 2025-11-29 |
| ✅ | Track last commit SHA and push timestamp | 2025-11-29 |
| ✅ | "Git" tab in agent detail page | 2025-11-29 |
| ✅ | Show repo, branch, last sync, commit history | 2025-11-29 |
| ✅ | Sync status indicator | 2025-11-29 |
| ✅ | **Source mode (default)**: Track source branch, pull-only | 2025-12-30 |
| ✅ | **Pull button**: Blue "Pull" button in agent header | 2025-12-30 |
| ✅ | **source_branch/source_mode fields**: DB schema update | 2025-12-30 |
| ✅ | **Content folder convention**: `content/` gitignored for large files | 2025-12-30 |

### Phase 6: Agent Scheduling & Autonomy
✅ **Completed: 2025-11-28**

| Status | Item | Completed |
|--------|------|-----------|
| ✅ | Platform scheduler service (APScheduler) | 2025-11-28 |
| ✅ | Schedule CRUD API endpoints | 2025-11-28 |
| ✅ | Cron-style scheduling support | 2025-11-28 |
| ✅ | Schedule UI on agent detail page | 2025-11-28 |
| ✅ | Scheduled executions list & logs | 2025-11-28 |
| ✅ | Enable/disable & manual trigger | 2025-11-28 |
| ✅ | Timezone support | 2025-11-28 |
| ✅ | WebSocket broadcast for execution events | 2025-11-28 |

### Phase 5: Agent Sharing & Observability
✅ **Completed: 2025-11-28**

| Status | Item | Completed |
|--------|------|-----------|
| ✅ | Agent sharing (Owner/Shared/Admin access) | 2025-11-28 |
| ✅ | Context window tracking in chat header | 2025-11-28 |
| ✅ | Agent live telemetry (CPU, memory, network, uptime) | 2025-11-28 |
| ✅ | Unified activity panel for tool calls | 2025-11-28 |
| ✅ | Session cost tracking | 2025-11-28 |
| ✅ | New session reset button | 2025-11-28 |
| ✅ | Markdown rendering in chat | 2025-11-28 |

### Phase 4: Multi-Agent Support
✅ **Completed: 2025-11-27**

| Status | Item | Completed |
|--------|------|-----------|
| ✅ | Trinity MCP server (12 tools) | 2025-11-27 |
| ✅ | MCP API key authentication | 2025-11-27 |
| ✅ | Per-user API keys | 2025-11-27 |
| ✅ | Inter-agent chat via MCP | 2025-11-27 |
| ✅ | MCP usage statistics | 2025-11-27 |
| ✅ | Credential hot-reload | 2025-11-28 |
| ✅ | Bulk credential import | 2025-11-27 |
| ✅ | Credential requirements visibility | 2025-11-27 |

### Phase 3.5: Credential Management
✅ **Completed: 2025-11-27**

| Status | Item | Completed |
|--------|------|-----------|
| ✅ | Redis-backed credential storage | 2025-11-25 |
| ✅ | OAuth2 flows (Google, Slack, GitHub, Notion) | 2025-11-25 |
| ✅ | Credential injection at agent creation | 2025-11-25 |
| ✅ | Manual credential entry | 2025-11-25 |
| ✅ | SQLite data persistence (users, ownership, API keys) | 2025-11-27 |

### Phase 3: Enhanced Security
✅ **Completed: 2025-11-27**

| Status | Item | Completed |
|--------|------|-----------|
| ✅ | Auth0 + Google OAuth integration | 2025-11-27 |
| ✅ | Domain restriction (@ability.ai) | 2025-11-27 |
| ✅ | Container security (non-root, cap-drop) | 2025-11-26 |
| ✅ | Audit logging service | 2025-11-26 |
| ✅ | Network isolation | 2025-11-26 |
| ✅ | Development mode bypass | 2025-11-27 |

### Phase 2: Web Management Interface
✅ **Completed: 2025-11-25**

| Status | Item | Completed |
|--------|------|-----------|
| ✅ | Vue.js frontend with Tailwind | 2025-11-22 |
| ✅ | Agent list dashboard | 2025-11-22 |
| ✅ | Agent creation UI | 2025-11-22 |
| ✅ | Agent start/stop controls | 2025-11-22 |
| ✅ | Real-time WebSocket updates | 2025-11-22 |
| ✅ | GCP production deployment | 2025-11-25 |
| ✅ | SSL/TLS via Let's Encrypt | 2025-11-25 |

### Phase 1: Base Infrastructure
✅ **Completed: 2025-11-22**

| Status | Item | Completed |
|--------|------|-----------|
| ✅ | Universal agent base image | 2025-11-20 |
| ✅ | Multi-runtime support (Python, Node, Go) | 2025-11-20 |
| ✅ | Claude Code installation | 2025-11-20 |
| ✅ | FastAPI backend | 2025-11-21 |
| ✅ | Docker SDK integration | 2025-11-21 |
| ✅ | Agent creation/deletion | 2025-11-21 |
| ✅ | Chat via backend API | 2025-11-22 |
| ✅ | Template system (GitHub + local) | 2025-11-22 |

---

### Phase 13: Agent Scalability & Event-Driven Architecture
⏳ **Pending** — *Foundation for process-driven systems*

| Status | Item | Description | Priority |
|--------|------|-------------|----------|
| ⏳ | **Horizontal Agent Scalability (13.1)** | Agent pools with N instances, load balancing, auto-scaling based on queue depth | HIGH |
| ⏳ | **Event Bus Infrastructure (13.2)** | Redis Streams pub/sub, permission-gated subscriptions, event persistence | HIGH |
| ⏳ | **Event Handlers & Reactions (13.3)** | Configure automatic agent reactions to events from permitted agents | HIGH |

### Phase 14: Process Engine (Business Process Orchestration)
✅ **Completed: 2026-01-16** — *BPMN-inspired workflow orchestration*

> **Design Documents**: `docs/PROCESS_DRIVEN_PLATFORM/`
> **Feature Flows**: `docs/memory/feature-flows/process-engine/`

| Status | Item | Description | Completed |
|--------|------|-------------|-----------|
| ✅ | **Process Definition & Storage (14.1)** | YAML-based definitions with JSON schema validation, versioning | 2026-01-16 |
| ✅ | **Sequential Execution Engine (14.2)** | Step handlers, state machine, dependency resolution | 2026-01-16 |
| ✅ | **Process Definition UI (14.3)** | YAML editor with live preview, validation feedback | 2026-01-16 |
| ✅ | **Execution Monitoring UI (14.4)** | Real-time step progress, WebSocket events, timeline | 2026-01-16 |
| ✅ | **Parallel Execution (14.5)** | Dependency-based parallel branches | 2026-01-16 |
| ✅ | **Human Approval Gates (14.6)** | Approval inbox, timeout handling, decision tracking | 2026-01-16 |
| ✅ | **Conditional Logic/Gateways (14.7)** | Expression evaluation, conditional branching | 2026-01-16 |
| ✅ | **Timer & Scheduling (14.8)** | Cron triggers, timer steps, timezone support | 2026-01-16 |
| ✅ | **Sub-Processes (14.9)** | Parent-child linking, input mapping, breadcrumbs | 2026-01-16 |
| ✅ | **Analytics & Cost Tracking (14.10)** | Metrics, trends, cost alerts | 2026-01-16 |
| ✅ | **Process Templates (14.11)** | Bundled templates, user templates, template selector | 2026-01-16 |
| ✅ | **Agent Roles - EMI Pattern (14.12)** | Executor/Monitor/Informed roles, InformedNotifier | 2026-01-16 |
| ✅ | **Error Handling & Retry (14.13)** | Retry policies, error boundaries | 2026-01-16 |
| ✅ | **Notification Steps (14.14)** | Notification handler for process events | 2026-01-16 |
| ✅ | **Event Publishing (14.15)** | WebSocket publisher, domain events | 2026-01-16 |
| ⏳ | **Process Designer UI (14.16)** | Visual drag-and-drop builder (nice-to-have) | Future |
| ⏳ | **Human-in-the-Loop Improvement** | Feedback collection, quality tracking | Future |

### Phase 15: Compliance-Ready Development Methodology
⏳ **Pending** — *SOC-2 and ISO-compatible AI development practices*

> **Template Location**: `dev-methodology-template/`

| Status | Item | Description | Priority |
|--------|------|-------------|----------|
| ⏳ | **SOC-2 Control Mapping** | Map methodology components to SOC-2 Trust Service Criteria (Security, Availability, Confidentiality) | HIGH |
| ⏳ | **ISO 27001 Alignment** | Align with ISO 27001:2022 controls for ISMS (A.8 Asset Management, A.14 System Dev) | HIGH |
| ⏳ | **Change Management Controls** | Formalize changelog, approval workflows, rollback procedures per SOC-2 CC8.1 | HIGH |
| ⏳ | **Access Control Documentation** | Document RBAC model, credential handling, audit trail requirements | MEDIUM |
| ⏳ | **Security Review Gates** | Mandatory `/security-check` before commits, OWASP compliance verification | MEDIUM |
| ⏳ | **Audit Trail Requirements** | Structured logging, immutable changelog, evidence retention policies | MEDIUM |
| ⏳ | **Incident Response Procedures** | Add `incidents.md` memory file, response playbooks, escalation paths | MEDIUM |
| ⏳ | **Compliance Evidence Generation** | Automated report generation for auditors (changelog → evidence, test runs → attestation) | LOW |

**Scope**: Extend `dev-methodology-template/` to produce development artifacts that satisfy:
- **SOC-2 Type II**: Trust Service Criteria for service organizations
- **ISO 27001**: Information Security Management System requirements
- **ISO 27701**: Privacy extension (GDPR alignment)

**Deliverables**:
- Control mapping documents (SOC-2, ISO 27001)
- Enhanced security-analyzer agent with compliance checks
- Audit-ready documentation templates
- Compliance dashboard/report generation

### Phase 16: Agent-as-a-Service & Commercialization
🚧 **In Progress** — *Path to revenue while building orchestration vision*

> **Planning Document**: `docs/planning/WORKFLOW_PRIORITIES_2026-02.md`

| Status | Item | Description | Spec | Priority |
|--------|------|-------------|------|----------|
| ⏳ | **Client/Viewer User Role** | Simplified user role using existing auth. Sees only basic UI (agent list, terminal, files). Hides advanced features (Collaboration Dashboard, Process Engine, Permissions, etc.). Enables sharing agents with paying clients. | [AUTH-002](../requirements/CLIENT_VIEWER_USER_ROLE.md) | **HIGH** |
| ✅ | **Encrypted Credentials in Git** | **Completed 2026-02-05**: CRED-002 implemented. New `CredentialEncryptionService` (AES-256-GCM), direct file injection endpoints, MCP tools, auto-import on startup. Removed: global `/credentials` page, Redis assignments. See `credential-injection.md`. | [CRED-002](../requirements/CREDENTIAL_SYSTEM_REFACTOR.md) | **HIGH** |
| ⏳ | **Subscription Management** | Centralized Claude Max/Pro subscription registry. MCP workflow: authenticate locally, register via `register_subscription`, assign to agents. Auto-inject `~/.claude/.credentials.json`. Auth detection endpoint. Fleet visibility. | [SUB-001](../requirements/SUBSCRIPTION_MANAGEMENT.md) | **HIGH** |
| ⏳ | **Unified Executions Dashboard** | Combined view of all executions across all agents. Filter by agent, time, trigger type. Real-time WebSocket updates. Click through to details. Extend existing `/executions` route. | [EXEC-022](../requirements/UNIFIED_EXECUTIONS_DASHBOARD.md) | **HIGH** |
| ⏳ | **MCP Execution Query Tools** | `list_recent_executions` - query what happened across fleet. `get_execution_result` - fetch specific output. `get_agent_activity_summary` - high-level status. | [MCP-007](../requirements/MCP_EXECUTION_QUERY_TOOLS.md) | **HIGH** |
| ✅ | **Continue Execution as Chat** | **Completed 2026-02-20**: Resume failed/completed executions as interactive chat with full context. Store Claude `session_id`, use `--resume` for native session continuity. "Continue as Chat" button on Execution Detail page, resume banner in Chat tab. | [EXEC-023](../requirements/CONTINUE_EXECUTION_AS_CHAT.md) | **MEDIUM** |
| ⏳ | **Quick Instance Deploy** | One-command agent creation from template with credentials. "Deploy Ruby for Client X" flow. Streamline System Manifest for single-agent case. | MEDIUM |
| ⏳ | **Execution Notifications** | Notify on task completion (success/failure). Start with webhook + UI toast. Email/Slack later. | MEDIUM |
| ⏳ | **Client Usage Dashboard** | Per-client view: executions, costs, outcomes. "What has this agent done for me?" Supports billing conversations. | MEDIUM |
| ⏳ | **Credential Usage Audit** | Log when credentials read, log external API calls where possible. Associate with executions. Foundation for SEC-001. | MEDIUM |
| ⏳ | **Monorepo Workspace Deploy** | Deploy entire directory of agents as cohesive system. Skills inherited from parent `.claude/skills/`. Credentials decrypted. MCP connections configured. | MEDIUM |
| ⏳ | **Platform Simplification Mode** | Hide advanced features (Collaboration Dashboard, Replay Timeline, Process Engine) behind toggle or role. Simpler default experience. | LOW |

**Strategic Context**:
- **Short-term goal**: Agent-as-a-Service (e.g., Ruby for clients) generates revenue
- **Long-term goal**: Multi-agent orchestration ("run my company with AI")
- **Key insight**: Both paths share 80% of infrastructure work (visibility, credentials, deployment)
- **Sequencing**: Foundation → AaaS for revenue → Full orchestration

---

## Backlog

Items not yet scheduled. Will be prioritized as needed.

### Local-Remote Agent Sync (2026-02-05)
> Spec: `docs/requirements/TRINITY_CONNECT_LOCAL_REMOTE_SYNC.md`
> Feature Flow: `docs/memory/feature-flows/trinity-connect.md`

| Priority | Item | Description |
|----------|------|-------------|
| ✅ **HIGH** | **Trinity Connect (WebSocket Listener)** | **Implemented 2026-02-05**: Event-driven local↔remote agent sync. `/ws/events` endpoint with MCP API key auth. `trinity-listen.sh` script connects to Trinity WebSocket, wakes Claude Code when event arrives. |
| ✅ **HIGH** | **WebSocket API Key Auth** | **Implemented 2026-02-05**: MCP API key authentication on `/ws/events` endpoint. Server-side event filtering based on user's accessible agents. |
| MEDIUM | **Agent Notification Endpoint** | `POST /api/agents/{name}/notify` - explicit push notifications. MCP tool `notify_agent`. |
| LOW | **Trinity Connect Skill Template** | Packaged skill for local Claude Code with listener script and instructions. |

### Multi-Agent Systems Research (2026-02-05)
> Source: `~/Dropbox/Agents/Cornelius/resources/Multi-Agent-Systems-Research-Report-2026-02-05.md`

| Priority | Item | Rationale |
|----------|------|-----------|
| **HIGH** | **Agent Skills Spec Alignment** | Anthropic's Agent Skills standard adopted by Microsoft, OpenAI, GitHub, Cursor. Progressive disclosure (few tokens when summarized). Align our `SKILL.md` format with https://agentskills.io for cross-platform interoperability. |
| **HIGH** | **A2A Protocol Support** | Google's Agent-to-Agent protocol enables cross-platform agent collaboration at higher level than MCP (which is agent-to-tool). Required for true multi-agent ecosystems. |
| **HIGH** | **Platform Memory Primitives** | Research shows 3-tier memory (Episodic→Semantic→Procedural) with Zettelkasten-style gives **2x multi-hop reasoning improvement**. Platform should provide memory APIs, not just let templates own it. |
| **MEDIUM** | **Code Execution Mode** | Agents writing code to interact with MCP servers instead of direct tool calls achieves **98% token reduction**. New execution paradigm for tool-heavy workflows. |
| **MEDIUM** | **Smart Model Routing** | Route queries by complexity: haiku→sonnet→opus. **300x price variance** between models enables 60-95% cost savings. Dynamic routing based on task classification. |

### Orphaned Execution Recovery (2026-02-12)
> Problem: When backend/scheduler restarts, executions marked "running" become orphaned forever.

| Priority | Item | Description |
|----------|------|-------------|
| **HIGH** | **Orphaned Execution Recovery on Startup** | On scheduler startup, mark all "running" executions as failed before starting jobs. Update `status='failed'`, set `error='Orphaned execution - service restarted before completion'`, set `completed_at`. Log warning with count. Implementation: Add `recover_orphaned_executions(db)` call early in scheduler init, before `scheduler.start()`. |

### OpenClaw-Inspired Features (2026-02-13)
> Source: `docs/research/openclaw-vs-trinity-comparison.md`

| Priority | Item | Description |
|----------|------|-------------|
| **MEDIUM** | **MEMORY.md Convention** | Agents maintain curated long-term memory in `MEMORY.md` file. Two-layer system: (1) Daily logs at `memory/YYYY-MM-DD.md` - raw session notes, (2) Long-term memory at `MEMORY.md` - curated insights distilled from daily logs. Agents explicitly told "mental notes don't survive, write to file." Platform injects memory section into CLAUDE.md on startup. Enables agents to get better over time through accumulated corrections. |
| **MEDIUM** | **Telegram Channel Integration** | Mobile-first interface via Telegram bot. Agent executions send push notifications. Users can approve/reject task outputs, trigger manual executions, and chat with agents from phone. Start with one channel (Telegram), architecture should support adding WhatsApp/Discord/Slack later. Key UX: review agent work while drinking coffee. |

### Agent Systems & Tags (2026-02-17)
> Spec: `docs/requirements/AGENT_SYSTEMS_AND_TAGS.md`

| Status | Priority | Item | Description |
|--------|----------|------|-------------|
| ✅ | **MEDIUM** | **Agent Tags (Phase 1)** | Multi-tag support for agents. Tags enable flexible grouping (one agent can belong to multiple systems). API: GET/PUT `/api/agents/{name}/tags`, filter: `/api/agents?tags=dd,content`. Completed 2026-02-17. |
| ✅ | **MEDIUM** | **System Views (Phase 2)** | Saved filter views for Dashboard. Each view defines a tag filter + metadata (name, icon, color). Click view to filter Dashboard to matching agents. Completed 2026-02-17. |
| ✅ | **LOW** | **MCP Tag Tools (Phase 3)** | 5 tools: `list_tags`, `get_agent_tags`, `tag_agent`, `untag_agent`, `set_agent_tags`. Quick tag filter in Dashboard header. Bulk tag operations on Agents page. Completed 2026-02-17. |
| ✅ | **LOW** | **System Manifest Integration (Phase 4)** | Add `tags` field to manifest YAML, auto-apply `system_prefix` as tag, optional auto-create System View. Migration script for existing prefixes. Completed 2026-02-17. |

### Previous Backlog

| Priority | Item | Requirement |
|----------|------|-------------|
| ✅ | ~~**Async MCP Chat Commands**~~ | **Completed 2026-01-30**: `async=true` parameter on `chat_with_agent` MCP tool. Returns execution_id immediately; poll `/api/agents/{name}/executions/{id}` for results. |
| Low | **Create Schedule from Task** | UX: Add icon in Tasks tab to create schedule from execution - switches to Schedules tab with message pre-filled |
| **High** | **Horizontal Agent Scalability** | 13.1 - Agent pools with multiple instances for parallel workloads |
| **High** | **Event Bus Infrastructure** | 13.2 - Platform-wide pub/sub for agent event broadcasting/subscription |
| **High** | **Event Handlers & Reactions** | 13.3 - Automatic agent reactions to events from permitted agents |
| **High** | **Attention Amplification Pattern** | Phase 12 - Cognitive pattern for salience-based event amplification |
| Medium | **Process Designer UI** | 14.16 - Visual drag-and-drop process builder |
| Medium | **SOC-2/ISO Compliance Methodology** | 15.* - Extend dev-methodology-template for audit-ready practices |
| Low | Task DAG Graph Visualization | 9.8 - Visual dependency graph (Vue Flow) - backend ready, UI nice-to-have |
| Medium | Kubernetes deployment scripts | 10.3 Kubernetes Deployment |
| Medium | Helm charts | 10.3 Kubernetes Deployment |
| Low | Automated testing pipeline | Non-functional |
| Low | Performance monitoring dashboard | Non-functional |
| Low | Agent resource usage alerts | Non-functional |
| **High** | **Claude Code Hooks for State Persistence** | Use `.claude/hooks/` (`Stop`, `PreToolUse`, `PostToolUse`) to persist agent work state before context compaction. Enables work to survive context window resets. Inspired by Gastown. |
| Medium | **Convoy-like Work Bundles** | Group related tasks/executions into trackable units for multi-agent coordination. Track multi-agent projects as single unit. Inspired by Gastown. |
| Medium | **Ephemeral Agent Spawning** | Let System Agent spawn temporary worker agents on-demand (create → run task → auto-cleanup). No pre-creation required. Inspired by Gastown. |
| Low | **Ready Work Discovery MCP Tool** | `find_ready_work()` tool to discover unblocked tasks across fleet. System Agent can identify what can be worked on next. Inspired by Gastown. |
| ✅ **High** | **Bug: Live Execution Logs on Production** | **Fixed 2026-02-05**: nginx proxy buffering was preventing SSE events from streaming. Added `proxy_buffering off; proxy_cache off; chunked_transfer_encoding on;` to `/api/` location in `src/frontend/nginx.conf`. |
| **High** | **Git Worktrees for Task Isolation** | Each execution (Tasks tab) gets its own git worktree/branch. Enables parallel executions without interference. Human decides: merge to main or discard. Worktrees become audit trail. Significant architecture change - needs detailed design. |
| **High** | **MCP as Primary Integration Point** | Local Claude Code agents connect to Trinity via MCP, pull default skills, become Trinity-compatible with minimal setup. MCP becomes single integration point for local→remote workflow. Goal: just add MCP connection, do rest via MCP tools. |
| Medium | **Agent Org Structures (Hierarchy)** | Parent-child agent relationships. Parents can: delegate tasks, start/stop/delete, configure children. Parents cannot: access child credentials. Single-parent tree. Builds on current permissions model. Visual grouping on Dashboard. |
| Medium | **Any Repo / Empty Agent Creation** | Two new creation modes: (1) Create agent from any GitHub repo (clone as template OR work in-place), (2) Create empty Trinity-compatible agent with minimal scaffolding. |
| Medium | **Empty Agent → GitHub Safety** | Block "Initialize GitHub" to existing repos when agent workspace is empty. Only allow initialization to NEW repos. Prevents accidental repo wipe. |
| Medium | **Centralized MCP Server Management** | UI and MCP tools to manage MCP server connections for any agent. Add/remove MCP servers without editing templates. Design TBD - per-agent config vs platform-level library. |
| Low | **GitHub Issues for Roadmap** | Use GitHub Issues instead of roadmap.md for Trinity platform development tracking. Migrate existing items when implemented. |
| Low | **Agent History in GitHub** | Store agent history (chat transcripts, execution logs, config) in git repo. Repository becomes source of truth. History survives agent deletion. Design open. |
| Medium | **Dashboard Quick Chat/Terminal** | Popup terminal or chat modal from agent card on Dashboard. Quick interactions without navigating to Agent Detail page. UX improvement for multi-agent workflows. |

---

## Decision Log

| Date | Decision | Rationale |
|------|----------|-----------|
| 2026-02-13 | OpenClaw-Inspired Features Added to Backlog | After analyzing OpenClaw (personal AI assistant platform), identified 2 features to adopt: (1) **MEMORY.md Convention** - MEDIUM, agents curate long-term memory with daily logs + distilled insights, gets better over time; (2) **Telegram Channel Integration** - MEDIUM, mobile-first interface for push notifications and approvals. OpenClaw's file-based coordination is elegantly simple. Key insight: "Files don't crash, files don't need auth." See `docs/research/openclaw-vs-trinity-comparison.md`. |
| 2026-02-05 | **Phase 16: Agent-as-a-Service & Commercialization** | Strategic planning session identified two business models: (1) Multi-agent orchestration ("run my company"), (2) Agent-as-a-Service (Ruby for clients). Decision: pursue both sequentially. AaaS provides faster path to revenue while building toward orchestration vision. Both share 80% of infrastructure needs. Key items: Client/Viewer user role (use existing auth, simplified UI), Encrypted credentials in git (portable agents), Unified Executions Dashboard (visibility), MCP execution tools (programmatic access). See `docs/planning/WORKFLOW_PRIORITIES_2026-02.md`. |
| 2026-02-05 | Multi-Agent Research Items Added | Added 5 items from Cornelius research report (`Multi-Agent-Systems-Research-Report-2026-02-05.md`): (1) **Agent Skills Spec** - HIGH, Anthropic standard adopted by Microsoft/OpenAI/GitHub; (2) **A2A Protocol** - HIGH, Google's agent-to-agent for cross-platform; (3) **Platform Memory Primitives** - HIGH, 3-tier memory with 2x reasoning improvement; (4) **Code Execution Mode** - MEDIUM, 98% token reduction; (5) **Smart Model Routing** - MEDIUM, 60-95% cost savings. Key insight: "Competitive advantage shifted from foundation models to orchestration and operations layers." |
| 2026-01-30 | Feature Requests Batch Added to Backlog | Added 10 items from planning session: (1) **Bug: Live logs** - HIGH, broken in production; (2) **Git worktrees** - HIGH, task isolation via branches, audit trail; (3) **MCP as primary integration** - HIGH, local agents connect via MCP, pull skills, minimal setup; (4) **Agent org structures** - MEDIUM, parent-child hierarchy; (5) **Any repo/empty agent** - MEDIUM, flexible creation modes; (6) **GitHub safety** - MEDIUM, prevent empty agent wiping repos; (7) **MCP server management** - MEDIUM, centralized UI; (8) **GitHub issues** - LOW, roadmap tracking; (9) **History in GitHub** - LOW, repo as source of truth. Theme: GitHub-centric workflow + MCP-first experience. |
| 2026-01-27 | Gastown-Inspired Features Added to Backlog | After analyzing Gastown (Steve Yegge's multi-agent CLI tool), identified 4 features to adopt: (1) Claude Code Hooks for state persistence (HIGH - enables work to survive context compaction), (2) Convoy-like work bundles (MEDIUM - track multi-agent projects as units), (3) Ephemeral agent spawning (MEDIUM - on-demand workers), (4) Ready work discovery (LOW - find unblocked tasks). See `docs/research/gastown-comparison.md`. |
| 2026-01-16 | Process Engine Completed (Phase 14) | Implemented full BPMN-inspired Process Engine with 15 sprints: YAML definitions, execution engine with 6 step handlers, human approvals, parallel execution, sub-processes, analytics/cost tracking, EMI roles, templates. Deferred Event Bus - using direct WebSocket broadcasting instead. Visual designer deferred (YAML editor with preview sufficient for now). See `docs/PROCESS_DRIVEN_PLATFORM/` and `docs/memory/feature-flows/process-engine/`. |
| 2026-01-09 | Compliance-Ready Development Methodology (Phase 15) | Extend `dev-methodology-template/` to produce SOC-2 and ISO 27001-compatible development artifacts. The existing methodology (slash commands, memory files, security-check, changelog) maps naturally to compliance controls. Formalizing this enables enterprise adoption and audit-ready AI development practices. |
| 2026-01-06 | Process-Driven Multi-Agent Vision | Evolution from agent management to business process orchestration. Processes define agents (not vice versa). RACI matrix for role assignment. System Agent as primary interface for design/test/monitor. Human-in-the-loop improvement cycles. See `docs/PROCESS_DRIVEN_PLATFORM/PROCESS_DRIVEN_AGENTS.md`. |
| 2026-01-06 | Event Bus with Permission-Gated Subscriptions | Agents subscribe to events from permitted agents only (reuses agent_permissions). Event handlers trigger agent execution like schedules but event-driven. Foundation for process-driven systems. |
| 2026-01-06 | Horizontal Agent Scalability | Agent pools with N instances for parallel task processing. Load balancing, auto-scaling, shared credentials. Enables high-throughput workflows. |
| 2025-12-22 | Parallel Headless Execution (12.1) | Two execution modes: Sequential Chat (maintains context with --continue) and Parallel Task (stateless, no lock). Enables orchestrators to spawn N parallel worker tasks. Based on Claude Code headless mode research. |
| 2025-12-20 | Internal System Agent (11.1) | Platform needs a privileged orchestrator that auto-deploys on startup, executes system-level user requests, and cannot be deleted. Enables unified multi-agent coordination. |
| 2025-12-08 | Deprioritize Task DAG Graph Viz | Backend workplan system complete; text-based UI sufficient for now; graph viz is nice-to-have |
| 2025-12-05 | Deep Agent positioning | Trinity = "Four Pillars of Deep Agency" platform. Pillar I (Explicit Planning) is the priority gap. |
| 2025-11-26 | Docker as source of truth | Eliminates in-memory registry issues with multiple workers |
| 2025-11-27 | SQLite + Redis hybrid | SQLite for relations, Redis for secrets - survives restarts |
| 2025-11-27 | No external agent UI ports | Security - all access via authenticated backend API |
| 2025-11-28 | Auth0 domain restriction | Enterprise security - @ability.ai only |

---

## How to Use This Document

1. **Check current phase** - Work on items in "Current Priority Queue"
2. **Pick topmost ⏳** - Start with first incomplete item
3. **Update on completion** - Change ⏳ to ✅, add date
4. **Move to completed** - Once all items done, move phase to "Completed Phases"
5. **Add new items** - Must trace to `requirements.md` requirement ID
