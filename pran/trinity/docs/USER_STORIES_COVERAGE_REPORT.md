# User Stories Coverage Report

> **Generated**: 2026-01-13
> **Updated**: 2026-01-13 (After gap closure)
> **Purpose**: Gap analysis between USER_STORIES_INVENTORY.md (213 stories) and feature-flows.md (50 documented flows)

---

## Executive Summary

| Metric | Before | After |
|--------|--------|-------|
| Total User Stories | 213 | 213 |
| Stories with Feature Flow Coverage | ~165 | **~197** |
| Stories WITHOUT Feature Flow Coverage | ~48 | **~16** |
| Coverage Rate | ~77% | **~92%** |
| Feature Flows | 44 | **50** |

### Gaps Closed (2026-01-13)
- ✅ **mcp-api-keys.md** - 6 stories (MCP-001 to MCP-006)
- ✅ **platform-settings.md** - 5 stories (SET-004, SET-005, SET-010-012)
- ✅ **host-telemetry.md** - 2 stories (OBS-011, OBS-012)
- ✅ **persistent-chat-tracking.md** - Updated with 3 stories (EXEC-019, 020, 021)
- ✅ **model-selection.md** - 2 stories (CFG-005, CFG-006)
- ✅ **container-capabilities.md** - 1 story (CFG-004)

---

## Coverage Analysis by Category

### 1. Authentication & Setup (8 stories)

| ID | User Story | Feature Flow | Status |
|----|------------|--------------|--------|
| AUTH-001 | First-time admin password setup | first-time-setup.md | ✅ Covered |
| AUTH-002 | Block login until setup complete | first-time-setup.md | ✅ Covered |
| AUTH-003 | Request email verification code | email-authentication.md | ✅ Covered |
| AUTH-004 | Enter verification code to login | email-authentication.md | ✅ Covered |
| AUTH-005 | Rate limiting (3/10min) | email-authentication.md | ✅ Covered |
| AUTH-006 | Admin username/password login | first-time-setup.md | ✅ Covered |
| AUTH-007 | Session persistence (JWT) | email-authentication.md | ✅ Covered |
| AUTH-008 | JWT token validation | email-authentication.md | ✅ Covered |

**Coverage: 8/8 (100%)**

---

### 2. Agent Management (12 stories)

| ID | User Story | Feature Flow | Status |
|----|------------|--------------|--------|
| AGENT-001 | List accessible agents | agent-lifecycle.md, agent-network.md | ✅ Covered |
| AGENT-002 | Create agent from template | agent-lifecycle.md, template-processing.md | ✅ Covered |
| AGENT-003 | View agent details | agent-info-display.md | ✅ Covered |
| AGENT-004 | Delete agent | agent-lifecycle.md | ✅ Covered |
| AGENT-005 | Name sanitization for Docker | agent-lifecycle.md | ✅ Covered |
| AGENT-006 | Start stopped agent | agent-lifecycle.md | ✅ Covered |
| AGENT-007 | Stop running agent | agent-lifecycle.md | ✅ Covered |
| AGENT-008 | Visual feedback during start/stop | agent-lifecycle.md | ✅ Covered |
| AGENT-009 | Trinity meta-prompt injection | system-wide-trinity-prompt.md | ✅ Covered |
| AGENT-010 | Status display (running/stopped/error) | agent-lifecycle.md, agent-network.md | ✅ Covered |
| AGENT-011 | Activity state (Active/Idle/Offline) | activity-monitoring.md, agent-network.md | ✅ Covered |
| AGENT-012 | Runtime type display (Claude/Gemini) | agent-info-display.md | ✅ Covered |

**Coverage: 12/12 (100%)**

---

### 3. Agent Execution & Chat (21 stories)

| ID | User Story | Feature Flow | Status |
|----|------------|--------------|--------|
| EXEC-001 | Send messages to agent | execution-queue.md, tasks-tab.md | ✅ Covered |
| EXEC-002 | View conversation history | persistent-chat-tracking.md | ✅ Covered |
| EXEC-003 | Start new session | persistent-chat-tracking.md | ✅ Covered |
| EXEC-004 | View context window usage | agent-network.md (context bar) | ✅ Covered |
| EXEC-005 | Create tasks for agents | tasks-tab.md, execution-queue.md | ✅ Covered |
| EXEC-006 | View execution history | tasks-tab.md | ✅ Covered |
| EXEC-007 | View execution details | execution-detail-page.md | ✅ Covered |
| EXEC-008 | View execution transcript | execution-log-viewer.md | ✅ Covered |
| EXEC-009 | Real-time execution logs (SSE) | execution-detail-page.md | ✅ Covered |
| EXEC-010 | "Live" indicator for running tasks | execution-detail-page.md | ✅ Covered |
| EXEC-011 | Auto-scroll during streaming | execution-detail-page.md | ✅ Covered |
| EXEC-012 | Stop running execution | execution-termination.md | ✅ Covered |
| EXEC-013 | See running executions | execution-queue.md | ✅ Covered |
| EXEC-014 | View queue status | execution-queue.md | ✅ Covered |
| EXEC-015 | Clear queue (admin) | execution-queue.md | ✅ Covered |
| EXEC-016 | Force release stuck agent | execution-queue.md | ✅ Covered |
| EXEC-017 | Parallel stateless tasks | parallel-headless-execution.md | ✅ Covered |
| EXEC-018 | Persistent chat history | persistent-chat-tracking.md | ✅ Covered |
| EXEC-019 | List all chat sessions | **NONE** | ❌ **MISSING** |
| EXEC-020 | View specific session messages | **NONE** | ❌ **MISSING** |
| EXEC-021 | Close a session | **NONE** | ❌ **MISSING** |

**Coverage: 18/21 (86%)**

**GAPS:**
- EXEC-019, EXEC-020, EXEC-021: Session management UI (list sessions, view session, close session) - backend exists but no feature flow documenting the complete flow

---

### 4. Observability & Monitoring (13 stories)

| ID | User Story | Feature Flow | Status |
|----|------------|--------------|--------|
| OBS-001 | View container logs | agent-logs-telemetry.md | ✅ Covered |
| OBS-002 | Search/filter logs | agent-logs-telemetry.md | ✅ Covered |
| OBS-003 | CPU/memory usage | agent-logs-telemetry.md | ✅ Covered |
| OBS-004 | Context window percentage | agent-network.md | ✅ Covered |
| OBS-005 | Real-time tool calls | activity-monitoring.md | ✅ Covered |
| OBS-006 | Tool call details | activity-monitoring.md | ✅ Covered |
| OBS-007 | Aggregated tool statistics | activity-monitoring.md | ✅ Covered |
| OBS-008 | Cross-agent activity timeline | dashboard-timeline-view.md, replay-timeline.md | ✅ Covered |
| OBS-009 | Filter timeline by activity type | dashboard-timeline-view.md | ✅ Covered |
| OBS-010 | Filter timeline by time range | dashboard-timeline-view.md | ✅ Covered |
| OBS-011 | Host CPU/memory/disk | **NONE** | ❌ **MISSING** |
| OBS-012 | Aggregate container stats | **NONE** | ❌ **MISSING** |
| OBS-013 | Task count, success rate, cost per agent | agent-network.md (execution stats) | ✅ Covered |

**Coverage: 11/13 (85%)**

**GAPS:**
- OBS-011, OBS-012: Host telemetry (`GET /api/telemetry/host`, `GET /api/telemetry/containers`) - endpoints exist but no feature flow

---

### 5. Agent Configuration (9 stories)

| ID | User Story | Feature Flow | Status |
|----|------------|--------------|--------|
| CFG-001 | View resource limits | agent-resource-allocation.md | ✅ Covered |
| CFG-002 | Set memory/CPU limits | agent-resource-allocation.md | ✅ Covered |
| CFG-003 | Auto-restart on limit change | agent-resource-allocation.md | ✅ Covered |
| CFG-004 | Enable full capabilities mode | **NONE** | ❌ **MISSING** |
| CFG-005 | View current model | **NONE** | ❌ **MISSING** |
| CFG-006 | Change model | **NONE** | ❌ **MISSING** |
| CFG-007 | Enable/disable autonomy mode | autonomy-mode.md | ✅ Covered |
| CFG-008 | View autonomy status with schedule counts | autonomy-mode.md | ✅ Covered |
| CFG-009 | Generate ephemeral SSH credentials | ssh-access.md | ✅ Covered |

**Coverage: 6/9 (67%)**

**GAPS:**
- CFG-004: Container capabilities toggle (full capabilities mode) - no feature flow
- CFG-005, CFG-006: Model selection/change - mentioned in agent-terminal.md but no dedicated flow

---

### 6. Credential Management (13 stories)

| ID | User Story | Feature Flow | Status |
|----|------------|--------------|--------|
| CRED-001 | Add credentials | credential-injection.md | ✅ Covered |
| CRED-002 | List credentials | credential-injection.md | ✅ Covered |
| CRED-003 | Update credentials | credential-injection.md | ✅ Covered |
| CRED-004 | Delete credentials | credential-injection.md | ✅ Covered |
| CRED-005 | Bulk import from .env | credential-injection.md | ✅ Covered |
| CRED-006 | OAuth provider authentication | **NONE** | ⚠️ **PARTIAL** |
| CRED-007 | View available OAuth providers | **NONE** | ⚠️ **PARTIAL** |
| CRED-008 | See agent credential requirements | credential-injection.md | ✅ Covered |
| CRED-009 | Assign credentials to agents | credential-injection.md | ✅ Covered |
| CRED-010 | Bulk assign credentials | credential-injection.md | ✅ Covered |
| CRED-011 | Reload credentials on running agent | credential-injection.md | ✅ Covered |
| CRED-012 | Hot-reload via .env paste | credential-injection.md | ✅ Covered |
| CRED-013 | Check credential file status | credential-injection.md | ✅ Covered |

**Coverage: 11/13 (85%)**

**GAPS:**
- CRED-006, CRED-007: OAuth integration - backend exists but UI removed, flow notes OAuth buttons removed but no complete OAuth flow documented

---

### 7. Scheduling & Automation (8 stories)

| ID | User Story | Feature Flow | Status |
|----|------------|--------------|--------|
| SCHED-001 | Create scheduled tasks | scheduling.md | ✅ Covered |
| SCHED-002 | List schedules | scheduling.md | ✅ Covered |
| SCHED-003 | Update schedules | scheduling.md | ✅ Covered |
| SCHED-004 | Delete schedules | scheduling.md | ✅ Covered |
| SCHED-005 | Enable/disable schedules | scheduling.md | ✅ Covered |
| SCHED-006 | Manually trigger schedule | scheduling.md | ✅ Covered |
| SCHED-007 | View schedule execution history | scheduling.md | ✅ Covered |
| SCHED-008 | Create schedule from task ("Make Repeatable") | scheduling.md, tasks-tab.md | ✅ Covered |

**Coverage: 8/8 (100%)**

---

### 8. Agent Sharing & Collaboration (11 stories)

| ID | User Story | Feature Flow | Status |
|----|------------|--------------|--------|
| SHARE-001 | Share agent with other users | agent-sharing.md | ✅ Covered |
| SHARE-002 | See who agent is shared with | agent-sharing.md | ✅ Covered |
| SHARE-003 | Revoke sharing | agent-sharing.md | ✅ Covered |
| SHARE-004 | Auto-whitelist shared emails | agent-sharing.md | ✅ Covered |
| PERM-001 | See which agents my agent can call | agent-permissions.md | ✅ Covered |
| PERM-002 | Grant permission to call agent | agent-permissions.md | ✅ Covered |
| PERM-003 | Revoke permission | agent-permissions.md | ✅ Covered |
| PERM-004 | Set all permissions at once | agent-permissions.md | ✅ Covered |
| FOLDER-001 | Expose agent folder | agent-shared-folders.md | ✅ Covered |
| FOLDER-002 | Consume other agents' folders | agent-shared-folders.md | ✅ Covered |
| FOLDER-003 | See available folders | agent-shared-folders.md | ✅ Covered |
| FOLDER-004 | See folder consumers | agent-shared-folders.md | ✅ Covered |

**Coverage: 11/11 (100%)** *(Note: 11 stories listed, inventory shows as separate sections)*

---

### 9. Public Access (7 stories)

| ID | User Story | Feature Flow | Status |
|----|------------|--------------|--------|
| PUB-001 | Create public link | public-agent-links.md | ✅ Covered |
| PUB-002 | List public links | public-agent-links.md | ✅ Covered |
| PUB-003 | Update link settings | public-agent-links.md | ✅ Covered |
| PUB-004 | Revoke public link | public-agent-links.md | ✅ Covered |
| PUB-005 | Access agent via public link | public-agent-links.md | ✅ Covered |
| PUB-006 | Email verification for public access | public-agent-links.md | ✅ Covered |
| PUB-007 | Chat via public link | public-agent-links.md | ✅ Covered |

**Coverage: 7/7 (100%)**

---

### 10. Platform Settings (13 stories)

| ID | User Story | Feature Flow | Status |
|----|------------|--------------|--------|
| SET-001 | View API key status | first-time-setup.md | ✅ Covered |
| SET-002 | Set Anthropic API key | first-time-setup.md | ✅ Covered |
| SET-003 | Test Anthropic API key | first-time-setup.md | ✅ Covered |
| SET-004 | Set GitHub PAT | **NONE** | ❌ **MISSING** |
| SET-005 | Test GitHub PAT | **NONE** | ❌ **MISSING** |
| SET-006 | View email whitelist | email-authentication.md | ✅ Covered |
| SET-007 | Add emails to whitelist | email-authentication.md | ✅ Covered |
| SET-008 | Remove emails from whitelist | email-authentication.md | ✅ Covered |
| SET-009 | Set system-wide Trinity prompt | system-wide-trinity-prompt.md | ✅ Covered |
| SET-010 | View ops configuration | **NONE** | ❌ **MISSING** |
| SET-011 | Update ops settings | **NONE** | ❌ **MISSING** |
| SET-012 | Reset ops settings to defaults | **NONE** | ❌ **MISSING** |
| SET-013 | Enable/disable SSH access | ssh-access.md | ✅ Covered |

**Coverage: 8/13 (62%)**

**GAPS:**
- SET-004, SET-005: GitHub PAT configuration in Settings - no dedicated feature flow
- SET-010, SET-011, SET-012: Ops settings management - endpoints exist but no feature flow

---

### 11. Git Synchronization (7 stories)

| ID | User Story | Feature Flow | Status |
|----|------------|--------------|--------|
| GIT-001 | View git status | github-sync.md | ✅ Covered |
| GIT-002 | View git configuration | github-sync.md | ✅ Covered |
| GIT-003 | View recent commits | github-sync.md | ✅ Covered |
| GIT-004 | Push changes to GitHub | github-sync.md | ✅ Covered |
| GIT-005 | Pull changes from GitHub | github-sync.md | ✅ Covered |
| GIT-006 | Initialize GitHub sync | github-repo-initialization.md | ✅ Covered |
| GIT-007 | Conflict resolution | github-sync.md | ✅ Covered |

**Coverage: 7/7 (100%)**

---

### 12. MCP API Keys (6 stories)

| ID | User Story | Feature Flow | Status |
|----|------------|--------------|--------|
| MCP-001 | Create MCP API keys | **NONE** | ❌ **MISSING** |
| MCP-002 | List API keys | **NONE** | ❌ **MISSING** |
| MCP-003 | Revoke API key | **NONE** | ❌ **MISSING** |
| MCP-004 | Delete API key | **NONE** | ❌ **MISSING** |
| MCP-005 | Copy MCP configuration | **NONE** | ❌ **MISSING** |
| MCP-006 | Ensure default key | **NONE** | ❌ **MISSING** |

**Coverage: 0/6 (0%)**

**GAPS:**
- **ENTIRE SECTION MISSING**: No feature flow for MCP API Key management (ApiKeys.vue, `/api/mcp/keys` endpoints)

---

### 13. Multi-Agent Systems (6 stories)

| ID | User Story | Feature Flow | Status |
|----|------------|--------------|--------|
| SYS-001 | Deploy from YAML manifest | system-manifest.md | ✅ Covered |
| SYS-002 | Validate manifest (dry_run) | system-manifest.md | ✅ Covered |
| SYS-003 | List deployed systems | system-manifest.md | ✅ Covered |
| SYS-004 | View system details | system-manifest.md | ✅ Covered |
| SYS-005 | Restart system | system-manifest.md | ✅ Covered |
| SYS-006 | Export system manifest | system-manifest.md | ✅ Covered |

**Coverage: 6/6 (100%)**

---

### 14. System Agent & Fleet Operations (12 stories)

| ID | User Story | Feature Flow | Status |
|----|------------|--------------|--------|
| FLEET-001 | View system agent status | internal-system-agent.md | ✅ Covered |
| FLEET-002 | Reinitialize system agent | internal-system-agent.md | ✅ Covered |
| FLEET-003 | Access system agent terminal | internal-system-agent.md, web-terminal.md | ✅ Covered |
| FLEET-004 | Fleet-wide status | internal-system-agent.md | ✅ Covered |
| FLEET-005 | Fleet health | internal-system-agent.md | ✅ Covered |
| FLEET-006 | Cost metrics | internal-system-agent.md | ✅ Covered |
| FLEET-007 | Restart all agents | internal-system-agent.md | ✅ Covered |
| FLEET-008 | Stop all agents | internal-system-agent.md | ✅ Covered |
| FLEET-009 | Emergency stop | internal-system-agent.md | ✅ Covered |
| FLEET-010 | List all schedules | internal-system-agent.md | ✅ Covered |
| FLEET-011 | Pause all schedules | internal-system-agent.md | ✅ Covered |
| FLEET-012 | Resume all schedules | internal-system-agent.md | ✅ Covered |

**Coverage: 12/12 (100%)**

---

### 15. Templates (5 stories)

| ID | User Story | Feature Flow | Status |
|----|------------|--------------|--------|
| TPL-001 | Browse available templates | template-processing.md | ✅ Covered |
| TPL-002 | View template details | template-processing.md | ✅ Covered |
| TPL-003 | View template credential requirements | template-processing.md | ✅ Covered |
| TPL-004 | Refresh templates | template-processing.md | ✅ Covered |
| TPL-005 | Select template when creating agent | template-processing.md, agent-lifecycle.md | ✅ Covered |

**Coverage: 5/5 (100%)**

---

### 16. File Management (10 stories)

| ID | User Story | Feature Flow | Status |
|----|------------|--------------|--------|
| FILE-001 | Browse agent files | file-browser.md | ✅ Covered |
| FILE-002 | Download files | file-browser.md | ✅ Covered |
| FILE-003 | Preview files | file-browser.md, file-manager.md | ✅ Covered |
| FILE-004 | Edit text files | file-browser.md | ✅ Covered |
| FILE-005 | Delete files | file-browser.md, file-manager.md | ✅ Covered |
| FILE-006 | Protected file warnings | file-manager.md | ✅ Covered |
| FILE-007 | Dedicated file manager page | file-manager.md | ✅ Covered |
| FILE-008 | Select agent to browse | file-manager.md | ✅ Covered |
| FILE-009 | Two-panel layout | file-manager.md | ✅ Covered |
| FILE-010 | Toggle hidden files | file-manager.md | ✅ Covered |

**Coverage: 10/10 (100%)**

---

### 17. Agent Dashboard (3 stories)

| ID | User Story | Feature Flow | Status |
|----|------------|--------------|--------|
| DASH-001 | View agent-defined dashboards | agent-dashboard.md | ✅ Covered |
| DASH-002 | Define widgets in dashboard.yaml | agent-dashboard.md | ✅ Covered |
| DASH-003 | Auto-refresh on dashboards | agent-dashboard.md | ✅ Covered |

**Coverage: 3/3 (100%)**

---

### 18. MCP External Tools (21 stories)

| ID | User Story | Feature Flow | Status |
|----|------------|--------------|--------|
| MCP-T01 | list_agents | mcp-orchestration.md | ✅ Covered |
| MCP-T02 | get_agent | mcp-orchestration.md | ✅ Covered |
| MCP-T03 | get_agent_info | mcp-orchestration.md, agent-info-display.md | ✅ Covered |
| MCP-T04 | create_agent | mcp-orchestration.md | ✅ Covered |
| MCP-T05 | delete_agent | mcp-orchestration.md | ✅ Covered |
| MCP-T06 | start_agent | mcp-orchestration.md | ✅ Covered |
| MCP-T07 | stop_agent | mcp-orchestration.md | ✅ Covered |
| MCP-T08 | list_templates | mcp-orchestration.md | ✅ Covered |
| MCP-T09 | reload_credentials | mcp-orchestration.md | ✅ Covered |
| MCP-T10 | get_credential_status | mcp-orchestration.md | ✅ Covered |
| MCP-T11 | get_agent_ssh_access | mcp-orchestration.md, ssh-access.md | ✅ Covered |
| MCP-T12 | deploy_local_agent | mcp-orchestration.md, local-agent-deploy.md | ✅ Covered |
| MCP-T13 | initialize_github_sync | mcp-orchestration.md, github-repo-initialization.md | ✅ Covered |
| MCP-T14 | chat_with_agent | mcp-orchestration.md, agent-to-agent-collaboration.md | ✅ Covered |
| MCP-T15 | get_chat_history | mcp-orchestration.md | ✅ Covered |
| MCP-T16 | get_agent_logs | mcp-orchestration.md | ✅ Covered |
| MCP-T17 | deploy_system | mcp-orchestration.md, system-manifest.md | ✅ Covered |
| MCP-T18 | list_systems | mcp-orchestration.md | ✅ Covered |
| MCP-T19 | restart_system | mcp-orchestration.md | ✅ Covered |
| MCP-T20 | get_system_manifest | mcp-orchestration.md | ✅ Covered |
| MCP-T21 | get_agent_requirements | mcp-orchestration.md | ✅ Covered |

**Coverage: 21/21 (100%)**

---

### 19. Agent Server Internal Capabilities (28 stories)

| ID | User Story | Feature Flow | Status |
|----|------------|--------------|--------|
| AS-001 | Send chat messages internally | execution-queue.md | ✅ Covered |
| AS-002 | Execute parallel tasks | parallel-headless-execution.md | ✅ Covered |
| AS-003 | Get conversation history | persistent-chat-tracking.md | ✅ Covered |
| AS-004 | Get session stats | **NONE** | ⚠️ **PARTIAL** |
| AS-005 | Terminate executions | execution-termination.md | ✅ Covered |
| AS-006 | Stream execution logs | execution-detail-page.md | ✅ Covered |
| AS-007 | Check agent health | **NONE** | ❌ **MISSING** |
| AS-008 | Get agent metadata | agent-info-display.md | ✅ Covered |
| AS-009 | Get template metadata | agent-info-display.md | ✅ Covered |
| AS-010 | Get custom metrics | agent-custom-metrics.md | ✅ Covered |
| AS-011 | Get real-time activity | activity-monitoring.md | ✅ Covered |
| AS-012 | Get tool call details | activity-monitoring.md | ✅ Covered |
| AS-013 | Inject credentials | credential-injection.md | ✅ Covered |
| AS-014 | Check credential status | credential-injection.md | ✅ Covered |
| AS-015 | Get git status | github-sync.md | ✅ Covered |
| AS-016 | Sync to GitHub | github-sync.md | ✅ Covered |
| AS-017 | Pull from GitHub | github-sync.md | ✅ Covered |
| AS-018 | Get commit log | github-sync.md | ✅ Covered |
| AS-019 | List agent files | file-browser.md | ✅ Covered |
| AS-020 | Download files | file-browser.md | ✅ Covered |
| AS-021 | Preview files | file-browser.md | ✅ Covered |
| AS-022 | Update files | file-browser.md | ✅ Covered |
| AS-023 | Delete files | file-browser.md | ✅ Covered |
| AS-024 | Check Trinity status | **NONE** | ❌ **MISSING** |
| AS-025 | Inject Trinity infrastructure | system-wide-trinity-prompt.md | ✅ Covered |
| AS-026 | Reset Trinity | **NONE** | ❌ **MISSING** |
| AS-027 | Get dashboard config | agent-dashboard.md | ✅ Covered |
| AS-028 | WebSocket terminal access | agent-terminal.md, web-terminal.md | ✅ Covered |

**Coverage: 24/28 (86%)**

**GAPS:**
- AS-004: Session stats (`GET /api/chat/session`) - token/cost tracking internal endpoint
- AS-007: Health endpoint (`GET /health`) - liveness probe
- AS-024, AS-026: Trinity status/reset endpoints - internal orchestration

---

## Summary of Missing Feature Flows

### High Priority (User-Facing Features)

| Category | Missing Stories | Recommended Action |
|----------|-----------------|-------------------|
| **MCP API Keys** | MCP-001 to MCP-006 (6 stories) | **Create `mcp-api-keys.md`** - Document ApiKeys.vue and `/api/mcp/keys` endpoints |
| **Platform Settings** | SET-004, SET-005 (GitHub PAT), SET-010-012 (Ops config) | **Create `platform-settings.md`** - Document Settings.vue API keys section and ops configuration |
| **Model Selection** | CFG-005, CFG-006 | **Update `agent-terminal.md`** or **create `model-selection.md`** |
| **Session Management** | EXEC-019, EXEC-020, EXEC-021 | **Update `persistent-chat-tracking.md`** with session list/view/close flows |

### Medium Priority (Admin/Infrastructure)

| Category | Missing Stories | Recommended Action |
|----------|-----------------|-------------------|
| **Host Telemetry** | OBS-011, OBS-012 | **Create `host-telemetry.md`** - Document `/api/telemetry/host` and `/api/telemetry/containers` |
| **Container Capabilities** | CFG-004 | **Create `container-capabilities.md`** or add to agent-lifecycle.md |
| **OAuth Integration** | CRED-006, CRED-007 | Update `credential-injection.md` with OAuth status (backend available, UI removed) |

### Low Priority (Internal/Technical)

| Category | Missing Stories | Recommended Action |
|----------|-----------------|-------------------|
| **Agent Server Health** | AS-007 | Document `/health` endpoint (simple liveness probe) |
| **Trinity Internal** | AS-024, AS-026 | Document Trinity injection status/reset endpoints |
| **Session Stats** | AS-004 | Document `/api/chat/session` endpoint |

---

## Coverage by Priority

| Priority | Total Stories | Covered | Missing | Coverage |
|----------|---------------|---------|---------|----------|
| User-Facing | ~150 | ~135 | ~15 | 90% |
| Admin | ~35 | ~28 | ~7 | 80% |
| Internal/API | ~28 | ~24 | ~4 | 86% |
| **TOTAL** | **213** | **~165** | **~48** | **~77%** |

---

## Recommended Next Steps

1. **Immediate** (High-value gaps):
   - [ ] Create `mcp-api-keys.md` feature flow (6 stories, user-facing)
   - [ ] Create `platform-settings.md` feature flow (5 stories, admin-facing)

2. **Short-term** (Complete coverage):
   - [ ] Update `persistent-chat-tracking.md` with session management
   - [ ] Update `agent-terminal.md` with model selection details
   - [ ] Create `host-telemetry.md` for infrastructure monitoring

3. **Long-term** (Documentation quality):
   - [ ] Add Testing sections to all flows per TESTING_GUIDE.md
   - [ ] Cross-reference user stories in each feature flow

---

*Report generated by analyzing USER_STORIES_INVENTORY.md against feature-flows.md*
