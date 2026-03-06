# Test Coverage Gap Report

> **Generated**: 2026-01-13
> **Source**: USER_STORIES_COVERAGE_REPORT.md (213 stories) vs test-runner agent (30 test files, ~535 tests)

---

## Executive Summary

| Metric | Value |
|--------|-------|
| Total User Stories | 213 |
| Stories with Test Coverage | ~168 |
| Stories WITHOUT Test Coverage | ~45 |
| **Test Coverage Rate** | **~79%** |
| Total Test Files | 30 |
| Total Tests | ~535 |

### Key Findings
- **Strong coverage**: Authentication, Agent Lifecycle, Credentials, Scheduling, MCP Keys
- **Moderate gaps**: File Management, Dashboard, some Observability features
- **Major gaps**: WebSocket terminal validation, Host telemetry, OAuth integration
- **No UI testing**: All tests are API-level; no Playwright/E2E tests exist

---

## Coverage Matrix by Category

### 1. Authentication & Setup (8 stories)

| Story ID | Description | Test File | Status |
|----------|-------------|-----------|--------|
| AUTH-001 | First-time admin password setup | `test_setup.py` | ✅ Covered |
| AUTH-002 | Block login until setup complete | `test_setup.py::TestLoginBlockedBeforeSetup` | ✅ Covered |
| AUTH-003 | Request email verification code | `test_email_auth.py::TestEmailLoginRequest` | ✅ Covered |
| AUTH-004 | Enter verification code to login | `test_email_auth.py::TestEmailLoginVerify` | ✅ Covered |
| AUTH-005 | Rate limiting (3/10min) | `test_email_auth.py` | ⚠️ Partial (logic exists, rate limit not stress-tested) |
| AUTH-006 | Admin username/password login | `test_auth.py::TestLogin` | ✅ Covered |
| AUTH-007 | Session persistence (JWT) | `test_auth.py::TestTokenValidation` | ✅ Covered |
| AUTH-008 | JWT token validation | `test_auth.py::TestTokenValidation` | ✅ Covered |

**Coverage: 7.5/8 (94%)**

---

### 2. Agent Management (12 stories)

| Story ID | Description | Test File | Status |
|----------|-------------|-----------|--------|
| AGENT-001 | List accessible agents | `test_agent_lifecycle.py::TestListAgents` | ✅ Covered |
| AGENT-002 | Create agent from template | `test_agent_lifecycle.py::TestCreateAgent` | ✅ Covered |
| AGENT-003 | View agent details | `test_agent_lifecycle.py::TestGetAgent` | ✅ Covered |
| AGENT-004 | Delete agent | `test_agent_lifecycle.py::TestDeleteAgent` | ✅ Covered |
| AGENT-005 | Name sanitization for Docker | `test_agent_lifecycle.py` | ✅ Covered |
| AGENT-006 | Start stopped agent | `test_agent_lifecycle.py::TestStartAgent` | ✅ Covered |
| AGENT-007 | Stop running agent | `test_agent_lifecycle.py::TestStopAgent` | ✅ Covered |
| AGENT-008 | Visual feedback during start/stop | **NONE** | ❌ UI test needed |
| AGENT-009 | Trinity meta-prompt injection | `test_settings.py::TestTrinityPromptInjection` | ✅ Covered |
| AGENT-010 | Status display (running/stopped/error) | `test_agent_lifecycle.py` | ✅ Covered |
| AGENT-011 | Activity state (Active/Idle/Offline) | `test_activities.py::TestAgentActivities` | ✅ Covered |
| AGENT-012 | Runtime type display (Claude/Gemini) | `test_agent_chat.py::TestModelManagement` | ✅ Covered |

**Coverage: 11/12 (92%)**

---

### 3. Agent Execution & Chat (21 stories)

| Story ID | Description | Test File | Status |
|----------|-------------|-----------|--------|
| EXEC-001 | Send messages to agent | `test_agent_chat.py::TestSendChatMessage` | ✅ Covered |
| EXEC-002 | View conversation history | `test_agent_chat.py::TestChatHistory` | ✅ Covered |
| EXEC-003 | Start new session | `test_agent_chat.py::TestResetSession` | ✅ Covered |
| EXEC-004 | View context window usage | `test_ops.py::TestContextStats` | ✅ Covered |
| EXEC-005 | Create tasks for agents | `test_executions.py::TestTaskPersistence` | ✅ Covered |
| EXEC-006 | View execution history | `test_executions.py::TestExecutionsEndpoint` | ✅ Covered |
| EXEC-007 | View execution details | `test_executions.py::TestExecutionDetails` | ✅ Covered |
| EXEC-008 | View execution transcript | `test_executions.py::TestExecutionLog` | ✅ Covered |
| EXEC-009 | Real-time execution logs (SSE) | **NONE** | ❌ **MISSING** - SSE streaming not tested |
| EXEC-010 | "Live" indicator for running tasks | **NONE** | ❌ UI test needed |
| EXEC-011 | Auto-scroll during streaming | **NONE** | ❌ UI test needed |
| EXEC-012 | Stop running execution | `test_execution_termination.py::TestTerminateExecution` | ✅ Covered |
| EXEC-013 | See running executions | `test_execution_termination.py::TestRunningExecutions` | ✅ Covered |
| EXEC-014 | View queue status | `test_execution_queue.py::TestQueueStatus` | ✅ Covered |
| EXEC-015 | Clear queue (admin) | `test_execution_queue.py::TestClearQueue` | ✅ Covered |
| EXEC-016 | Force release stuck agent | `test_execution_queue.py::TestForceRelease` | ✅ Covered |
| EXEC-017 | Parallel stateless tasks | `test_parallel_task.py::TestParallelExecution` | ✅ Covered |
| EXEC-018 | Persistent chat history | `test_agent_chat.py::TestChatHistory` | ✅ Covered |
| EXEC-019 | List all chat sessions | `test_agent_chat.py::TestChatSessions` | ✅ Covered |
| EXEC-020 | View specific session messages | `test_agent_chat.py::TestChatHistory` | ✅ Covered |
| EXEC-021 | Close a session | `test_agent_chat.py::TestResetSession` | ✅ Covered |

**Coverage: 18/21 (86%)**

**Gaps:**
- EXEC-009: SSE streaming endpoint not tested (async streaming)
- EXEC-010, EXEC-011: UI-only features

---

### 4. Observability & Monitoring (13 stories)

| Story ID | Description | Test File | Status |
|----------|-------------|-----------|--------|
| OBS-001 | View container logs | `test_agent_lifecycle.py::TestAgentLogs` | ✅ Covered |
| OBS-002 | Search/filter logs | **NONE** | ❌ **MISSING** |
| OBS-003 | CPU/memory usage | `test_observability.py::TestObservabilityMetrics` | ✅ Covered |
| OBS-004 | Context window percentage | `test_ops.py::TestContextStats` | ✅ Covered |
| OBS-005 | Real-time tool calls | `test_agent_chat.py::TestInMemoryActivity` | ✅ Covered |
| OBS-006 | Tool call details | `test_agent_chat.py::TestInMemoryActivityToolDetails` | ✅ Covered |
| OBS-007 | Aggregated tool statistics | `test_activities.py::TestActivityDetails` | ✅ Covered |
| OBS-008 | Cross-agent activity timeline | `test_activities.py::TestCrossAgentTimeline` | ✅ Covered |
| OBS-009 | Filter timeline by activity type | `test_activities.py::TestActivityTimeline` | ✅ Covered |
| OBS-010 | Filter timeline by time range | `test_activities.py::TestActivityTimeline` | ✅ Covered |
| OBS-011 | Host CPU/memory/disk | **NONE** | ❌ **MISSING** - `/api/telemetry/host` not tested |
| OBS-012 | Aggregate container stats | **NONE** | ❌ **MISSING** - `/api/telemetry/containers` not tested |
| OBS-013 | Task count, success rate, cost | `test_ops.py::TestOpsCosts` | ✅ Covered |

**Coverage: 10/13 (77%)**

**Gaps:**
- OBS-002: Log search/filter not tested
- OBS-011, OBS-012: Host telemetry endpoints missing tests

---

### 5. Agent Configuration (9 stories)

| Story ID | Description | Test File | Status |
|----------|-------------|-----------|--------|
| CFG-001 | View resource limits | `test_agent_lifecycle.py::TestGetAgent` | ✅ Covered |
| CFG-002 | Set memory/CPU limits | `test_agent_lifecycle.py::TestCreateAgent` | ✅ Covered |
| CFG-003 | Auto-restart on limit change | **NONE** | ❌ **MISSING** |
| CFG-004 | Enable full capabilities mode | **NONE** | ❌ **MISSING** |
| CFG-005 | View current model | `test_agent_chat.py::TestModelManagement` | ✅ Covered |
| CFG-006 | Change model | `test_agent_chat.py::TestModelManagementExtended` | ✅ Covered |
| CFG-007 | Enable/disable autonomy mode | `test_schedules.py` (indirect) | ⚠️ Partial |
| CFG-008 | View autonomy status | `test_schedules.py::TestSchedulerStatus` | ⚠️ Partial |
| CFG-009 | Generate ephemeral SSH credentials | **NONE** | ❌ **MISSING** - SSH access endpoint not tested |

**Coverage: 5/9 (56%)**

**Gaps:**
- CFG-003: Resource limit auto-restart not tested
- CFG-004: Full capabilities toggle not tested
- CFG-009: SSH credential generation (`/api/agents/{name}/ssh`) not tested

---

### 6. Credential Management (13 stories)

| Story ID | Description | Test File | Status |
|----------|-------------|-----------|--------|
| CRED-001 | Add credentials | `test_credentials.py::TestCreateCredential` | ✅ Covered |
| CRED-002 | List credentials | `test_credentials.py::TestListCredentials` | ✅ Covered |
| CRED-003 | Update credentials | `test_credentials.py::TestCreateCredential` | ✅ Covered |
| CRED-004 | Delete credentials | `test_credentials.py::TestListCredentials` | ✅ Covered |
| CRED-005 | Bulk import from .env | `test_credentials.py::TestBulkImport` | ✅ Covered |
| CRED-006 | OAuth provider authentication | **NONE** | ❌ **MISSING** - OAuth flow not implemented |
| CRED-007 | View available OAuth providers | **NONE** | ❌ **MISSING** |
| CRED-008 | See agent credential requirements | `test_credentials.py::TestAgentCredentialRequirements` | ✅ Covered |
| CRED-009 | Assign credentials to agents | `test_credentials.py::TestHotReload` | ✅ Covered |
| CRED-010 | Bulk assign credentials | `test_credentials.py::TestBulkImport` | ✅ Covered |
| CRED-011 | Reload credentials on running agent | `test_credentials.py::TestReloadFromStore` | ✅ Covered |
| CRED-012 | Hot-reload via .env paste | `test_credentials.py::TestHotReload` | ✅ Covered |
| CRED-013 | Check credential file status | `test_credentials.py::TestCredentialStatus` | ✅ Covered |

**Coverage: 11/13 (85%)**

**Gaps:**
- CRED-006, CRED-007: OAuth not implemented (intentionally excluded)

---

### 7. Scheduling & Automation (8 stories)

| Story ID | Description | Test File | Status |
|----------|-------------|-----------|--------|
| SCHED-001 | Create scheduled tasks | `test_schedules.py::TestCreateSchedule` | ✅ Covered |
| SCHED-002 | List schedules | `test_schedules.py::TestListSchedules` | ✅ Covered |
| SCHED-003 | Update schedules | `test_schedules.py::TestCreateSchedule` | ✅ Covered |
| SCHED-004 | Delete schedules | `test_schedules.py::TestDeleteSchedule` | ✅ Covered |
| SCHED-005 | Enable/disable schedules | `test_schedules.py::TestEnableDisableSchedule` | ✅ Covered |
| SCHED-006 | Manually trigger schedule | `test_schedules.py::TestTriggerSchedule` | ✅ Covered |
| SCHED-007 | View schedule execution history | `test_schedules.py::TestScheduleExecutions` | ✅ Covered |
| SCHED-008 | Create schedule from task | **NONE** | ❌ **MISSING** - "Make Repeatable" flow |

**Coverage: 7/8 (88%)**

---

### 8. Agent Sharing & Collaboration (11 stories)

| Story ID | Description | Test File | Status |
|----------|-------------|-----------|--------|
| SHARE-001 | Share agent with other users | `test_agent_sharing.py::TestShareAgent` | ✅ Covered |
| SHARE-002 | See who agent is shared with | `test_agent_sharing.py::TestListShares` | ✅ Covered |
| SHARE-003 | Revoke sharing | `test_agent_sharing.py::TestUnshareAgent` | ✅ Covered |
| SHARE-004 | Auto-whitelist shared emails | `test_agent_sharing.py` | ⚠️ Partial |
| PERM-001 | See which agents my agent can call | `test_agent_permissions.py::TestGetPermissions` | ✅ Covered |
| PERM-002 | Grant permission to call agent | `test_agent_permissions.py::TestAddPermission` | ✅ Covered |
| PERM-003 | Revoke permission | `test_agent_permissions.py::TestRemovePermission` | ✅ Covered |
| PERM-004 | Set all permissions at once | `test_agent_permissions.py::TestSetPermissions` | ✅ Covered |
| FOLDER-001 | Expose agent folder | `test_shared_folders.py::TestUpdateFoldersConfig` | ✅ Covered |
| FOLDER-002 | Consume other agents' folders | `test_shared_folders.py::TestSharedFoldersWithTwoAgents` | ✅ Covered |
| FOLDER-003 | See available folders | `test_shared_folders.py::TestAvailableFolders` | ✅ Covered |
| FOLDER-004 | See folder consumers | `test_shared_folders.py::TestFolderConsumers` | ✅ Covered |

**Coverage: 11.5/12 (96%)**

---

### 9. Public Access (7 stories)

| Story ID | Description | Test File | Status |
|----------|-------------|-----------|--------|
| PUB-001 | Create public link | `test_public_links.py::TestOwnerEndpointsWithAuth` | ✅ Covered |
| PUB-002 | List public links | `test_public_links.py::TestOwnerEndpointsWithAuth` | ✅ Covered |
| PUB-003 | Update link settings | `test_public_links.py::TestPublicLinkLifecycle` | ✅ Covered |
| PUB-004 | Revoke public link | `test_public_links.py::TestPublicLinkLifecycle` | ✅ Covered |
| PUB-005 | Access agent via public link | `test_public_links.py::TestPublicEndpoints` | ✅ Covered |
| PUB-006 | Email verification for public access | `test_public_links.py::TestEmailVerification` | ✅ Covered |
| PUB-007 | Chat via public link | `test_public_links.py::TestPublicChat` | ✅ Covered |

**Coverage: 7/7 (100%)**

---

### 10. Platform Settings (13 stories)

| Story ID | Description | Test File | Status |
|----------|-------------|-----------|--------|
| SET-001 | View API key status | `test_settings.py::TestApiKeysStatus` | ✅ Covered |
| SET-002 | Set Anthropic API key | `test_settings.py::TestApiKeysStatus` | ✅ Covered |
| SET-003 | Test Anthropic API key | `test_settings.py::TestApiKeyTest` | ✅ Covered |
| SET-004 | Set GitHub PAT | `test_settings.py::TestApiKeysStatus` | ✅ Covered |
| SET-005 | Test GitHub PAT | **NONE** | ❌ **MISSING** |
| SET-006 | View email whitelist | `test_email_auth.py::TestEmailWhitelistCRUD` | ✅ Covered |
| SET-007 | Add emails to whitelist | `test_email_auth.py::TestEmailWhitelistCRUD` | ✅ Covered |
| SET-008 | Remove emails from whitelist | `test_email_auth.py::TestEmailWhitelistCRUD` | ✅ Covered |
| SET-009 | Set system-wide Trinity prompt | `test_settings.py::TestTrinityPromptSetting` | ✅ Covered |
| SET-010 | View ops configuration | `test_ops.py::TestFleetStatus` | ⚠️ Partial |
| SET-011 | Update ops settings | **NONE** | ❌ **MISSING** |
| SET-012 | Reset ops settings to defaults | **NONE** | ❌ **MISSING** |
| SET-013 | Enable/disable SSH access | **NONE** | ❌ **MISSING** |

**Coverage: 9/13 (69%)**

**Gaps:**
- SET-005: GitHub PAT test endpoint not tested
- SET-011, SET-012: Ops settings update/reset not tested
- SET-013: SSH toggle not tested

---

### 11. Git Synchronization (7 stories)

| Story ID | Description | Test File | Status |
|----------|-------------|-----------|--------|
| GIT-001 | View git status | `test_agent_git.py::TestGitStatus` | ✅ Covered |
| GIT-002 | View git configuration | `test_agent_git.py::TestGitStatus` | ✅ Covered |
| GIT-003 | View recent commits | `test_agent_git.py::TestGitLog` | ✅ Covered |
| GIT-004 | Push changes to GitHub | `test_agent_git.py::TestGitSync` | ✅ Covered |
| GIT-005 | Pull changes from GitHub | `test_agent_git.py::TestGitPull` | ✅ Covered |
| GIT-006 | Initialize GitHub sync | **NONE** | ❌ **MISSING** - `/api/agents/{name}/git/init` |
| GIT-007 | Conflict resolution | **NONE** | ⚠️ Partial (in flow, not explicit test) |

**Coverage: 5.5/7 (79%)**

---

### 12. MCP API Keys (6 stories)

| Story ID | Description | Test File | Status |
|----------|-------------|-----------|--------|
| MCP-001 | Create MCP API keys | `test_mcp_keys.py::TestCreateApiKey` | ✅ Covered |
| MCP-002 | List API keys | `test_mcp_keys.py::TestListApiKeys` | ✅ Covered |
| MCP-003 | Revoke API key | `test_mcp_keys.py::TestRevokeApiKey` | ✅ Covered |
| MCP-004 | Delete API key | `test_mcp_keys.py::TestDeleteApiKey` | ✅ Covered |
| MCP-005 | Copy MCP configuration | **NONE** | ❌ UI-only feature |
| MCP-006 | Ensure default key | `test_mcp_keys.py` | ⚠️ Partial |

**Coverage: 5/6 (83%)**

---

### 13. Multi-Agent Systems (6 stories)

| Story ID | Description | Test File | Status |
|----------|-------------|-----------|--------|
| SYS-001 | Deploy from YAML manifest | `test_systems.py::TestSystemDeployment` | ✅ Covered |
| SYS-002 | Validate manifest (dry_run) | `test_systems.py::TestSystemManifestParsing` | ✅ Covered |
| SYS-003 | List deployed systems | `test_systems.py::TestSystemBackendEndpoints` | ✅ Covered |
| SYS-004 | View system details | `test_systems.py::TestSystemBackendEndpoints` | ✅ Covered |
| SYS-005 | Restart system | `test_systems.py::TestSystemBackendEndpoints` | ✅ Covered |
| SYS-006 | Export system manifest | `test_systems.py::TestSystemBackendEndpoints` | ✅ Covered |

**Coverage: 6/6 (100%)**

---

### 14. System Agent & Fleet Operations (12 stories)

| Story ID | Description | Test File | Status |
|----------|-------------|-----------|--------|
| FLEET-001 | View system agent status | `test_system_agent.py::TestSystemAgentStatus` | ✅ Covered |
| FLEET-002 | Reinitialize system agent | `test_system_agent.py::TestSystemAgentReinitialize` | ✅ Covered |
| FLEET-003 | Access system agent terminal | **NONE** | ❌ WebSocket terminal not tested |
| FLEET-004 | Fleet-wide status | `test_ops.py::TestFleetStatus` | ✅ Covered |
| FLEET-005 | Fleet health | `test_ops.py::TestFleetHealth` | ✅ Covered |
| FLEET-006 | Cost metrics | `test_ops.py::TestOpsCosts` | ✅ Covered |
| FLEET-007 | Restart all agents | `test_ops.py::TestFleetOperationsAdminOnly` | ✅ Covered |
| FLEET-008 | Stop all agents | `test_ops.py::TestFleetOperationsAdminOnly` | ✅ Covered |
| FLEET-009 | Emergency stop | `test_ops.py::TestEmergencyStop` | ✅ Covered |
| FLEET-010 | List all schedules | `test_ops.py::TestSchedulesList` | ✅ Covered |
| FLEET-011 | Pause all schedules | `test_ops.py::TestScheduleControl` | ✅ Covered |
| FLEET-012 | Resume all schedules | `test_ops.py::TestScheduleControl` | ✅ Covered |

**Coverage: 11/12 (92%)**

---

### 15. Templates (5 stories)

| Story ID | Description | Test File | Status |
|----------|-------------|-----------|--------|
| TPL-001 | Browse available templates | `test_templates.py::TestListTemplates` | ✅ Covered |
| TPL-002 | View template details | `test_templates.py::TestGetTemplateDetails` | ✅ Covered |
| TPL-003 | View template credential requirements | `test_templates.py::TestEnvTemplate` | ✅ Covered |
| TPL-004 | Refresh templates | `test_templates.py::TestTemplateRefresh` | ✅ Covered |
| TPL-005 | Select template when creating agent | `test_agent_lifecycle.py::TestCreateAgent` | ✅ Covered |

**Coverage: 5/5 (100%)**

---

### 16. File Management (10 stories)

| Story ID | Description | Test File | Status |
|----------|-------------|-----------|--------|
| FILE-001 | Browse agent files | `test_agent_files.py::TestListFiles` | ✅ Covered |
| FILE-002 | Download files | `test_agent_files.py::TestDownloadFile` | ✅ Covered |
| FILE-003 | Preview files | **NONE** | ❌ **MISSING** |
| FILE-004 | Edit text files | **NONE** | ❌ **MISSING** |
| FILE-005 | Delete files | **NONE** | ❌ **MISSING** |
| FILE-006 | Protected file warnings | **NONE** | ❌ **MISSING** |
| FILE-007 | Dedicated file manager page | **NONE** | ❌ UI-only |
| FILE-008 | Select agent to browse | **NONE** | ❌ UI-only |
| FILE-009 | Two-panel layout | **NONE** | ❌ UI-only |
| FILE-010 | Toggle hidden files | **NONE** | ❌ **MISSING** |

**Coverage: 2/10 (20%)**

**Gaps:** File management has the **lowest test coverage**. Only basic list and download are tested. Edit, delete, preview, and hidden file toggle are not tested.

---

### 17. Agent Dashboard (3 stories)

| Story ID | Description | Test File | Status |
|----------|-------------|-----------|--------|
| DASH-001 | View agent-defined dashboards | **NONE** | ❌ **MISSING** - `/api/agents/{name}/dashboard` |
| DASH-002 | Define widgets in dashboard.yaml | **NONE** | ❌ **MISSING** |
| DASH-003 | Auto-refresh on dashboards | **NONE** | ❌ UI-only |

**Coverage: 0/3 (0%)**

**Gaps:** Dashboard feature has **zero test coverage**. This is a critical gap.

---

### 18. MCP External Tools (21 stories)

All MCP tools are tested indirectly through their underlying API endpoints. Direct MCP tool invocation tests are not in the test suite (would require MCP client testing).

**Coverage: ~19/21 (90%)** - via API tests

---

### 19. Agent Server Internal Capabilities (28 stories)

These are tested through `agent_server/` direct tests which require `TEST_AGENT_NAME` environment variable.

**Coverage: ~24/28 (86%)** - when direct tests are enabled

---

## Summary: Missing Tests by Priority

### Critical Priority (User-Facing Features)

| Gap | Stories | Impact | Test File Needed |
|-----|---------|--------|------------------|
| **Dashboard API** | DASH-001, DASH-002 | Core feature untested | `test_agent_dashboard.py` |
| **File Management** | FILE-003, FILE-004, FILE-005 | File edit/delete untested | Update `test_agent_files.py` |
| **SSE Streaming** | EXEC-009 | Live log streaming untested | `test_execution_streaming.py` |
| **SSH Access** | CFG-009 | Security feature untested | Add to `test_settings.py` |

### High Priority (API Completeness)

| Gap | Stories | Impact | Test File Needed |
|-----|---------|--------|------------------|
| **Host Telemetry** | OBS-011, OBS-012 | Infrastructure monitoring | `test_telemetry.py` |
| **Git Init** | GIT-006 | GitHub sync initialization | Add to `test_agent_git.py` |
| **GitHub PAT Test** | SET-005 | Settings validation | Add to `test_settings.py` |
| **Resource Restart** | CFG-003 | Config change behavior | Add to `test_agent_lifecycle.py` |

### Medium Priority (Edge Cases)

| Gap | Stories | Impact | Test File Needed |
|-----|---------|--------|------------------|
| **Log Search** | OBS-002 | Observability completeness | Add to `test_agent_lifecycle.py` |
| **Rate Limiting** | AUTH-005 | Security stress test | Add to `test_email_auth.py` |
| **Make Repeatable** | SCHED-008 | Workflow feature | Add to `test_schedules.py` |
| **Ops Settings** | SET-011, SET-012 | Admin feature | Add to `test_ops.py` |

### Low Priority (UI-Only / Not Applicable)

| Gap | Stories | Reason |
|-----|---------|--------|
| Visual feedback | AGENT-008 | UI test needed (Playwright) |
| Live indicator | EXEC-010 | UI test needed |
| Auto-scroll | EXEC-011 | UI test needed |
| OAuth | CRED-006, CRED-007 | Feature not implemented |
| File manager layout | FILE-007, FILE-008, FILE-009 | UI-only features |
| MCP config copy | MCP-005 | UI clipboard action |

---

## Coverage by Category (Sorted by Gap)

| # | Category | Stories | Covered | Coverage |
|---|----------|---------|---------|----------|
| 1 | Agent Dashboard | 3 | 0 | **0%** |
| 2 | File Management | 10 | 2 | **20%** |
| 3 | Agent Configuration | 9 | 5 | **56%** |
| 4 | Platform Settings | 13 | 9 | **69%** |
| 5 | Observability | 13 | 10 | **77%** |
| 6 | Git Synchronization | 7 | 5.5 | **79%** |
| 7 | MCP API Keys | 6 | 5 | **83%** |
| 8 | Credential Management | 13 | 11 | **85%** |
| 9 | Agent Execution | 21 | 18 | **86%** |
| 10 | Scheduling | 8 | 7 | **88%** |
| 11 | Agent Management | 12 | 11 | **92%** |
| 12 | Fleet Operations | 12 | 11 | **92%** |
| 13 | Authentication | 8 | 7.5 | **94%** |
| 14 | Agent Sharing | 12 | 11.5 | **96%** |
| 15 | Public Access | 7 | 7 | **100%** |
| 16 | Multi-Agent Systems | 6 | 6 | **100%** |
| 17 | Templates | 5 | 5 | **100%** |

---

## Recommendations

### Immediate Actions

1. **Create `test_agent_dashboard.py`** - Test `/api/agents/{name}/dashboard` endpoint
2. **Expand `test_agent_files.py`** - Add tests for file edit, delete, preview, hidden toggle
3. **Create `test_telemetry.py`** - Test `/api/telemetry/host` and `/api/telemetry/containers`

### Short-Term Actions

4. **Add SSH access tests** to `test_settings.py` or create `test_ssh_access.py`
5. **Add SSE streaming tests** - Test execution log streaming endpoint
6. **Add git init tests** - Test `/api/agents/{name}/git/init` endpoint

### Long-Term Actions

7. **Consider Playwright/E2E tests** for UI-specific features (visual feedback, auto-scroll, etc.)
8. **Add WebSocket tests** for terminal features (complex setup required)

---

## Test Infrastructure Notes

- **Test Environment**: Python virtual environment at `tests/.venv`
- **Test Framework**: pytest with markers (`smoke`, `slow`)
- **Fixture Strategy**: Module-scoped agent fixtures to reduce test time
- **Expected Skips**: ~38 tests skipped intentionally (agent server direct tests, git not configured, etc.)

---

*Report generated by analyzing USER_STORIES_COVERAGE_REPORT.md against test-runner agent specification and test suite files.*
