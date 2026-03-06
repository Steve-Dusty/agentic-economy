# Trinity Platform - Complete User Stories Inventory

> **Purpose**: Comprehensive inventory of ALL business-valuable user stories extracted from the codebase.
> **Generated**: 2026-01-13
> **Source**: Code analysis of backend routers, frontend views, MCP server, agent server, and services.

---

## Table of Contents

1. [Authentication & Setup](#1-authentication--setup)
2. [Agent Management](#2-agent-management)
3. [Agent Execution & Chat](#3-agent-execution--chat)
4. [Observability & Monitoring](#4-observability--monitoring)
5. [Agent Configuration](#5-agent-configuration)
6. [Credential Management](#6-credential-management)
7. [Scheduling & Automation](#7-scheduling--automation)
8. [Agent Sharing & Collaboration](#8-agent-sharing--collaboration)
9. [Public Access](#9-public-access)
10. [Platform Settings](#10-platform-settings)
11. [Git Synchronization](#11-git-synchronization)
12. [MCP API Keys](#12-mcp-api-keys)
13. [Multi-Agent Systems](#13-multi-agent-systems)
14. [System Agent & Fleet Operations](#14-system-agent--fleet-operations)
15. [Templates](#15-templates)
16. [File Management](#16-file-management)
17. [Agent Dashboard](#17-agent-dashboard)
18. [MCP External Tools](#18-mcp-external-tools)
19. [Agent Server Internal Capabilities](#19-agent-server-internal-capabilities)

---

## 1. Authentication & Setup

### 1.1 First-Time Setup
| ID | User Story | Endpoints | Frontend |
|----|------------|-----------|----------|
| AUTH-001 | As a new admin, I want to set up the initial admin password so that I can secure my Trinity installation | `GET /api/setup/status`, `POST /api/setup/admin-password` | Login.vue (setup wizard) |
| AUTH-002 | As a system, I want to block login until setup is complete so that the platform is secured before use | `GET /api/auth/mode` returns `setup_completed` flag | Login.vue checks setup status |

### 1.2 Email Authentication (Primary)
| ID | User Story | Endpoints | Frontend |
|----|------------|-----------|----------|
| AUTH-003 | As a user, I want to request a verification code via email so that I can login without a password | `POST /api/auth/email/request` | Login.vue email input |
| AUTH-004 | As a user, I want to enter my verification code so that I can complete login | `POST /api/auth/email/verify` | Login.vue code input with countdown |
| AUTH-005 | As an admin, I want email login to be rate limited (3/10min) so that brute force is prevented | Rate limiting in backend | Error message on too many attempts |

### 1.3 Admin Authentication (Secondary)
| ID | User Story | Endpoints | Frontend |
|----|------------|-----------|----------|
| AUTH-006 | As an admin, I want to login with username/password so that I have a fallback authentication method | `POST /api/token` | Login.vue admin tab |
| AUTH-007 | As a user, I want my session to persist across page refreshes so that I don't have to re-login | JWT in localStorage | Auth store persistence |

### 1.4 Token Validation
| ID | User Story | Endpoints | Frontend |
|----|------------|-----------|----------|
| AUTH-008 | As a system, I want to validate JWT tokens so that only authenticated users access protected resources | `GET /api/auth/validate` | Axios interceptor |

---

## 2. Agent Management

### 2.1 Agent CRUD
| ID | User Story | Endpoints | Frontend |
|----|------------|-----------|----------|
| AGENT-001 | As a user, I want to see all agents I have access to so that I can manage my autonomous workers | `GET /api/agents` | Agents.vue grid, Dashboard.vue nodes |
| AGENT-002 | As a user, I want to create a new agent from a template so that I can quickly deploy specialized agents | `POST /api/agents` | CreateAgentModal |
| AGENT-003 | As a user, I want to view detailed information about an agent so that I understand its configuration | `GET /api/agents/{name}` | AgentDetail.vue |
| AGENT-004 | As an owner, I want to delete an agent so that I can clean up unused resources | `DELETE /api/agents/{name}` | Delete button with confirmation |
| AGENT-005 | As a user, I want agent names to be sanitized for Docker compatibility so that creation doesn't fail | Name validation in backend | Form validation feedback |

### 2.2 Agent Lifecycle
| ID | User Story | Endpoints | Frontend |
|----|------------|-----------|----------|
| AGENT-006 | As a user, I want to start a stopped agent so that it becomes available for tasks | `POST /api/agents/{name}/start` | Start button with spinner |
| AGENT-007 | As a user, I want to stop a running agent so that I can conserve resources | `POST /api/agents/{name}/stop` | Stop button with confirmation |
| AGENT-008 | As a user, I want visual feedback during start/stop operations so that I know the action is in progress | WebSocket status broadcasts | Loading spinners, toast notifications |
| AGENT-009 | As a system, I want Trinity meta-prompt injected on agent start so that agents have platform capabilities | Trinity injection in lifecycle service | N/A (automatic) |

### 2.3 Agent Status Display
| ID | User Story | Endpoints | Frontend |
|----|------------|-----------|----------|
| AGENT-010 | As a user, I want to see agent status (running/stopped/error) so that I know which agents are available | Status from Docker labels | Status badges (green/gray/red) |
| AGENT-011 | As a user, I want to see agent activity state (Active/Idle/Offline) so that I know what agents are doing | Activity tracking | Pulsing indicator on active agents |
| AGENT-012 | As a user, I want to see runtime type (Claude/Gemini) so that I know which LLM powers the agent | Runtime from template.yaml | Runtime badge |

---

## 3. Agent Execution & Chat

### 3.1 Interactive Chat
| ID | User Story | Endpoints | Frontend |
|----|------------|-----------|----------|
| EXEC-001 | As a user, I want to send messages to an agent so that I can interact with it conversationally | `POST /api/agents/{name}/chat` | TasksPanel text input |
| EXEC-002 | As a user, I want to see conversation history so that I can review past interactions | `GET /api/agents/{name}/chat/history` | Conversation display |
| EXEC-003 | As a user, I want to start a new session so that I can begin with fresh context | `DELETE /api/agents/{name}/chat/history` | New session button |
| EXEC-004 | As a user, I want to see context window usage so that I know how much capacity remains | `GET /api/agents/{name}/chat/session` | Context progress bar |

### 3.2 Task Execution
| ID | User Story | Endpoints | Frontend |
|----|------------|-----------|----------|
| EXEC-005 | As a user, I want to create tasks for agents so that they perform work autonomously | `POST /api/agents/{name}/chat` (via queue) | TasksPanel create task |
| EXEC-006 | As a user, I want to see task execution history so that I can review completed work | `GET /api/agents/{name}/executions` | TasksPanel history list |
| EXEC-007 | As a user, I want to view detailed execution results so that I can understand what the agent did | `GET /api/agents/{name}/executions/{id}` | ExecutionDetail.vue |
| EXEC-008 | As a user, I want to view the full execution transcript so that I can debug agent behavior | `GET /api/agents/{name}/executions/{id}/log` | ExecutionDetail transcript section |

### 3.3 Live Execution Streaming
| ID | User Story | Endpoints | Frontend |
|----|------------|-----------|----------|
| EXEC-009 | As a user, I want to see real-time execution logs so that I can monitor long-running tasks | `GET /api/agents/{name}/executions/{id}/stream` (SSE) | ExecutionDetail live streaming |
| EXEC-010 | As a user, I want a "Live" indicator for running tasks so that I know streaming is available | N/A | Green pulsing badge in TasksPanel |
| EXEC-011 | As a user, I want auto-scroll during streaming so that I see the latest output | N/A | Auto-scroll toggle |

### 3.4 Execution Control
| ID | User Story | Endpoints | Frontend |
|----|------------|-----------|----------|
| EXEC-012 | As a user, I want to stop a running execution so that I can cancel stuck or unwanted tasks | `POST /api/agents/{name}/executions/{id}/terminate` | Stop button in TasksPanel/ExecutionDetail |
| EXEC-013 | As a user, I want to see which executions are currently running so that I know agent utilization | `GET /api/agents/{name}/executions/running` | Running indicator |

### 3.5 Execution Queue
| ID | User Story | Endpoints | Frontend |
|----|------------|-----------|----------|
| EXEC-014 | As a user, I want to see queue status so that I know if my task is waiting | `GET /api/agents/{name}/queue` | Queue status display |
| EXEC-015 | As an admin, I want to clear the queue so that I can unblock stuck agents | `POST /api/agents/{name}/queue/clear` | Clear queue action |
| EXEC-016 | As an admin, I want to force release a stuck agent so that it can accept new tasks | `POST /api/agents/{name}/queue/release` | Force release action |

### 3.6 Parallel Task Execution
| ID | User Story | Endpoints | Frontend |
|----|------------|-----------|----------|
| EXEC-017 | As an orchestrator, I want to execute stateless tasks in parallel so that I can delegate work efficiently | `POST /api/agents/{name}/task` | N/A (MCP/API use) |

### 3.7 Persistent Chat History
| ID | User Story | Endpoints | Frontend |
|----|------------|-----------|----------|
| EXEC-018 | As a user, I want chat history to persist across sessions so that I don't lose conversation context | `GET /api/agents/{name}/chat/history/persistent` | Conversation display |
| EXEC-019 | As a user, I want to see all my chat sessions so that I can review past conversations | `GET /api/agents/{name}/chat/sessions` | Session list |
| EXEC-020 | As a user, I want to view a specific session's messages so that I can review a conversation | `GET /api/agents/{name}/chat/sessions/{id}` | Session detail |
| EXEC-021 | As a user, I want to close a session so that I can organize my conversation history | `POST /api/agents/{name}/chat/sessions/{id}/close` | Close session button |

---

## 4. Observability & Monitoring

### 4.1 Container Logs
| ID | User Story | Endpoints | Frontend |
|----|------------|-----------|----------|
| OBS-001 | As a user, I want to view agent container logs so that I can debug issues | `GET /api/agents/{name}/logs` | LogsPanel with auto-refresh |
| OBS-002 | As a user, I want to search/filter logs so that I can find specific entries | N/A | Log search box |

### 4.2 Live Telemetry
| ID | User Story | Endpoints | Frontend |
|----|------------|-----------|----------|
| OBS-003 | As a user, I want to see CPU/memory usage so that I know agent resource consumption | `GET /api/agents/{name}/stats` | AgentHeader sparklines |
| OBS-004 | As a user, I want to see context window percentage so that I know when agents need session reset | Context from chat session | Context progress bar (color-coded) |

### 4.3 Activity Monitoring
| ID | User Story | Endpoints | Frontend |
|----|------------|-----------|----------|
| OBS-005 | As a user, I want to see real-time tool calls so that I know what the agent is doing | `GET /api/agents/{name}/activity` | Activity panel |
| OBS-006 | As a user, I want to see tool call details so that I can debug tool behavior | `GET /api/agents/{name}/activity/{tool_id}` | Tool detail drill-down |
| OBS-007 | As a user, I want to see aggregated tool statistics so that I understand agent patterns | Activity summary | Tool chips with counts |

### 4.4 Activity Timeline
| ID | User Story | Endpoints | Frontend |
|----|------------|-----------|----------|
| OBS-008 | As a user, I want to see a cross-agent activity timeline so that I understand system-wide behavior | `GET /api/activities/timeline` | Dashboard timeline view |
| OBS-009 | As a user, I want to filter timeline by activity type so that I focus on relevant events | Query params: activity_types | Timeline filters |
| OBS-010 | As a user, I want to filter timeline by time range so that I see specific periods | Query params: start_time, end_time | Time range selector |

### 4.5 Host Telemetry
| ID | User Story | Endpoints | Frontend |
|----|------------|-----------|----------|
| OBS-011 | As an admin, I want to see host CPU/memory/disk so that I monitor infrastructure health | `GET /api/telemetry/host` | Dashboard stats header |
| OBS-012 | As an admin, I want to see aggregate container stats so that I understand resource distribution | `GET /api/telemetry/containers` | Container stats panel |

### 4.6 Execution Statistics
| ID | User Story | Endpoints | Frontend |
|----|------------|-----------|----------|
| OBS-013 | As a user, I want to see task count, success rate, and cost per agent so that I evaluate agent performance | `GET /api/agents/execution-stats` | Agent cards (tasks, %, $, time) |

---

## 5. Agent Configuration

### 5.1 Resource Limits
| ID | User Story | Endpoints | Frontend |
|----|------------|-----------|----------|
| CFG-001 | As a user, I want to view agent resource limits so that I know its capacity | `GET /api/agents/{name}/resources` | Resource display |
| CFG-002 | As an owner, I want to set agent memory/CPU limits so that I control resource allocation | `PUT /api/agents/{name}/resources` | Resource modal (gear button) |
| CFG-003 | As a user, I want agents to restart when resource limits change so that new limits take effect | Auto-restart on limit change | Restart confirmation |

### 5.2 Container Capabilities
| ID | User Story | Endpoints | Frontend |
|----|------------|-----------|----------|
| CFG-004 | As an owner, I want to enable full capabilities mode so that agents can install packages | `PUT /api/agents/{name}/capabilities` | Capabilities toggle |

### 5.3 Model Selection
| ID | User Story | Endpoints | Frontend |
|----|------------|-----------|----------|
| CFG-005 | As a user, I want to view the current model so that I know which LLM is being used | `GET /api/agents/{name}/model` | Model display |
| CFG-006 | As a user, I want to change the model so that I can use different LLM variants | `PUT /api/agents/{name}/model` | Model selector in Terminal tab |

### 5.4 Autonomy Mode
| ID | User Story | Endpoints | Frontend |
|----|------------|-----------|----------|
| CFG-007 | As an owner, I want to enable/disable autonomy mode so that I control whether schedules run | `PUT /api/agents/{name}/autonomy` | AUTO/Manual toggle (Dashboard, Agents, AgentDetail) |
| CFG-008 | As a user, I want to see autonomy status with schedule counts so that I know what will be affected | `GET /api/agents/{name}/autonomy` | Autonomy indicator |

### 5.5 SSH Access
| ID | User Story | Endpoints | Frontend |
|----|------------|-----------|----------|
| CFG-009 | As a developer, I want to generate ephemeral SSH credentials so that I can access agent containers directly | `POST /api/agents/{name}/ssh-access` | N/A (MCP tool) |

---

## 6. Credential Management

### 6.1 Global Credentials
| ID | User Story | Endpoints | Frontend |
|----|------------|-----------|----------|
| CRED-001 | As a user, I want to add credentials so that agents can access external services | `POST /api/credentials` | Credentials.vue add modal |
| CRED-002 | As a user, I want to list my credentials so that I can manage them | `GET /api/credentials` | Credentials.vue list |
| CRED-003 | As a user, I want to update credentials so that I can rotate secrets | `PUT /api/credentials/{id}` | Edit credential |
| CRED-004 | As a user, I want to delete credentials so that I can remove unused secrets | `DELETE /api/credentials/{id}` | Delete button |
| CRED-005 | As a user, I want to bulk import credentials from .env format so that I can quickly add multiple secrets | `POST /api/credentials/bulk` | Bulk import textarea |

### 6.2 OAuth Integration
| ID | User Story | Endpoints | Frontend |
|----|------------|-----------|----------|
| CRED-006 | As a user, I want to authenticate with OAuth providers so that agents can access Google/Slack/GitHub/Notion | `POST /api/oauth/{provider}/init`, `GET /api/oauth/{provider}/callback` | OAuth buttons (backend available) |
| CRED-007 | As a user, I want to see available OAuth providers so that I know what's configured | `GET /api/oauth/providers` | Provider status |

### 6.3 Agent Credential Assignment
| ID | User Story | Endpoints | Frontend |
|----|------------|-----------|----------|
| CRED-008 | As a user, I want to see what credentials an agent needs so that I know what to configure | `GET /api/agents/{name}/credentials` | CredentialsPanel requirements |
| CRED-009 | As a user, I want to assign credentials to agents so that they have access to required services | `POST /api/agents/{name}/credentials/assign` | Assign credential |
| CRED-010 | As a user, I want to bulk assign credentials so that I can quickly configure agents | `POST /api/agents/{name}/credentials/assign/bulk` | Bulk assign |
| CRED-011 | As a user, I want to reload credentials on a running agent so that I don't need to restart it | `POST /api/agents/{name}/credentials/reload` | Reload button |
| CRED-012 | As a user, I want to hot-reload credentials by pasting .env text so that I can quickly update secrets | `POST /api/agents/{name}/credentials/hot-reload` | Hot-reload textarea |
| CRED-013 | As a user, I want to check credential file status so that I verify secrets are configured | `GET /api/agents/{name}/credentials/status` | Status indicator |

---

## 7. Scheduling & Automation

### 7.1 Schedule CRUD
| ID | User Story | Endpoints | Frontend |
|----|------------|-----------|----------|
| SCHED-001 | As a user, I want to create scheduled tasks so that agents run automatically | `POST /api/agents/{name}/schedules` | SchedulesPanel create form |
| SCHED-002 | As a user, I want to list schedules so that I see what's configured | `GET /api/agents/{name}/schedules` | SchedulesPanel list |
| SCHED-003 | As a user, I want to update schedules so that I can change timing or messages | `PUT /api/agents/{name}/schedules/{id}` | Edit schedule |
| SCHED-004 | As a user, I want to delete schedules so that I remove unwanted automation | `DELETE /api/agents/{name}/schedules/{id}` | Delete button |

### 7.2 Schedule Control
| ID | User Story | Endpoints | Frontend |
|----|------------|-----------|----------|
| SCHED-005 | As a user, I want to enable/disable schedules individually so that I control which run | `POST /api/agents/{name}/schedules/{id}/enable`, `POST .../disable` | Enable/disable toggle |
| SCHED-006 | As a user, I want to manually trigger a schedule so that I test it | `POST /api/agents/{name}/schedules/{id}/trigger` | Trigger button |

### 7.3 Execution History
| ID | User Story | Endpoints | Frontend |
|----|------------|-----------|----------|
| SCHED-007 | As a user, I want to see schedule execution history so that I review past runs | `GET /api/agents/{name}/schedules/{id}/executions` | Execution history |

### 7.4 Make Repeatable
| ID | User Story | Endpoints | Frontend |
|----|------------|-----------|----------|
| SCHED-008 | As a user, I want to create a schedule from a task execution so that I can repeat successful tasks | N/A (frontend flow) | Calendar icon in TasksPanel → SchedulesPanel with pre-fill |

---

## 8. Agent Sharing & Collaboration

### 8.1 Agent Sharing
| ID | User Story | Endpoints | Frontend |
|----|------------|-----------|----------|
| SHARE-001 | As an owner, I want to share an agent with other users so that they can use it | `POST /api/agents/{name}/share` | SharingPanel add email |
| SHARE-002 | As an owner, I want to see who an agent is shared with so that I manage access | `GET /api/agents/{name}/shares` | SharingPanel list |
| SHARE-003 | As an owner, I want to revoke sharing so that I remove access | `DELETE /api/agents/{name}/share/{email}` | Remove share button |
| SHARE-004 | As a system, I want shared emails auto-added to whitelist so that they can login | Auto-whitelist on share | N/A (automatic) |

### 8.2 Agent Permissions
| ID | User Story | Endpoints | Frontend |
|----|------------|-----------|----------|
| PERM-001 | As an owner, I want to see which agents my agent can call so that I understand its capabilities | `GET /api/agents/{name}/permissions` | PermissionsPanel list |
| PERM-002 | As an owner, I want to grant permission to call another agent so that I enable collaboration | `POST /api/agents/{name}/permissions/{target}` | Add permission |
| PERM-003 | As an owner, I want to revoke permission so that I restrict collaboration | `DELETE /api/agents/{name}/permissions/{target}` | Remove permission |
| PERM-004 | As an owner, I want to set all permissions at once so that I configure the full network | `PUT /api/agents/{name}/permissions` | Bulk permission update |

### 8.3 Shared Folders
| ID | User Story | Endpoints | Frontend |
|----|------------|-----------|----------|
| FOLDER-001 | As an owner, I want to expose my agent's folder so that other agents can read files | `PUT /api/agents/{name}/folders` (expose_enabled) | FoldersPanel expose toggle |
| FOLDER-002 | As an owner, I want to consume other agents' folders so that my agent can read shared files | `PUT /api/agents/{name}/folders` (consume_enabled) | FoldersPanel consume toggle |
| FOLDER-003 | As a user, I want to see available folders from permitted agents so that I know what's mountable | `GET /api/agents/{name}/folders/available` | Available folders list |
| FOLDER-004 | As a user, I want to see who consumes my agent's folder so that I audit access | `GET /api/agents/{name}/folders/consumers` | Consumers list |

---

## 9. Public Access

### 9.1 Public Link Management
| ID | User Story | Endpoints | Frontend |
|----|------------|-----------|----------|
| PUB-001 | As an owner, I want to create a public link so that external users can access my agent | `POST /api/agents/{name}/public-links` | PublicLinksPanel create |
| PUB-002 | As an owner, I want to list public links so that I manage access | `GET /api/agents/{name}/public-links` | PublicLinksPanel list |
| PUB-003 | As an owner, I want to update link settings (expiry, email requirement) so that I control access | `PUT /api/agents/{name}/public-links/{id}` | Edit link |
| PUB-004 | As an owner, I want to revoke a public link so that I disable access | `DELETE /api/agents/{name}/public-links/{id}` | Revoke button |

### 9.2 Public Chat
| ID | User Story | Endpoints | Frontend |
|----|------------|-----------|----------|
| PUB-005 | As an external user, I want to access agent info via public link so that I know what I'm interacting with | `GET /api/public/link/{token}` | PublicChat.vue |
| PUB-006 | As an external user, I want to verify my email (if required) so that I can use the agent | `POST /api/public/verify/request`, `POST /api/public/verify/confirm` | Email verification flow |
| PUB-007 | As an external user, I want to chat with the agent so that I get assistance | `POST /api/public/chat/{token}` | PublicChat.vue chat |

---

## 10. Platform Settings

### 10.1 API Key Management
| ID | User Story | Endpoints | Frontend |
|----|------------|-----------|----------|
| SET-001 | As an admin, I want to view API key status so that I know what's configured | `GET /api/settings/api-keys` | Settings.vue API keys section |
| SET-002 | As an admin, I want to set the Anthropic API key so that agents can use Claude | `PUT /api/settings/api-keys/anthropic` | API key input |
| SET-003 | As an admin, I want to test the Anthropic API key so that I verify it works | `POST /api/settings/api-keys/anthropic/test` | Test button |
| SET-004 | As an admin, I want to set the GitHub PAT so that I can use GitHub templates | `PUT /api/settings/api-keys/github` | GitHub PAT input |
| SET-005 | As an admin, I want to test the GitHub PAT so that I verify permissions | `POST /api/settings/api-keys/github/test` | Test button |

### 10.2 Email Whitelist
| ID | User Story | Endpoints | Frontend |
|----|------------|-----------|----------|
| SET-006 | As an admin, I want to view the email whitelist so that I know who can login | `GET /api/settings/email-whitelist` | Settings.vue whitelist table |
| SET-007 | As an admin, I want to add emails to the whitelist so that users can login | `POST /api/settings/email-whitelist` | Add email form |
| SET-008 | As an admin, I want to remove emails from the whitelist so that I revoke access | `DELETE /api/settings/email-whitelist/{email}` | Remove button |

### 10.3 Trinity Prompt
| ID | User Story | Endpoints | Frontend |
|----|------------|-----------|----------|
| SET-009 | As an admin, I want to set a system-wide Trinity prompt so that all agents receive custom instructions | Settings API | Settings.vue Trinity prompt textarea |

### 10.4 Ops Settings
| ID | User Story | Endpoints | Frontend |
|----|------------|-----------|----------|
| SET-010 | As an admin, I want to view ops configuration so that I understand platform settings | `GET /api/settings/ops/config` | Settings display |
| SET-011 | As an admin, I want to update ops settings so that I tune platform behavior | `PUT /api/settings/ops/config` | Settings form |
| SET-012 | As an admin, I want to reset ops settings to defaults so that I restore standard configuration | `POST /api/settings/ops/reset` | Reset button |
| SET-013 | As an admin, I want to enable/disable SSH access so that I control terminal access capability | `ssh_access_enabled` setting | SSH toggle |

---

## 11. Git Synchronization

### 11.1 Git Status
| ID | User Story | Endpoints | Frontend |
|----|------------|-----------|----------|
| GIT-001 | As a user, I want to see git status so that I know if there are uncommitted changes | `GET /api/agents/{name}/git/status` | GitPanel status |
| GIT-002 | As a user, I want to see git configuration so that I know the repo and branch | `GET /api/agents/{name}/git/config` | GitPanel config |
| GIT-003 | As a user, I want to see recent commits so that I review change history | `GET /api/agents/{name}/git/log` | GitPanel commit list |

### 11.2 Git Operations
| ID | User Story | Endpoints | Frontend |
|----|------------|-----------|----------|
| GIT-004 | As an owner, I want to push changes to GitHub so that I version control agent updates | `POST /api/agents/{name}/git/sync` | Sync/Push button |
| GIT-005 | As an owner, I want to pull changes from GitHub so that I update the agent | `POST /api/agents/{name}/git/pull` | Pull button |
| GIT-006 | As an owner, I want to initialize GitHub sync so that I enable version control | `POST /api/agents/{name}/git/initialize` | Initialize button |
| GIT-007 | As a user, I want conflict resolution strategies so that I handle merge conflicts | Strategy params (force_push, force_reset, stash_reapply) | Conflict modal |

---

## 12. MCP API Keys

### 12.1 Key Management
| ID | User Story | Endpoints | Frontend |
|----|------------|-----------|----------|
| MCP-001 | As a user, I want to create MCP API keys so that I can integrate with Claude Code clients | `POST /api/mcp/keys` | ApiKeys.vue create modal |
| MCP-002 | As a user, I want to list my API keys so that I manage access | `GET /api/mcp/keys` | ApiKeys.vue list |
| MCP-003 | As a user, I want to revoke an API key so that I disable compromised keys | `POST /api/mcp/keys/{id}/revoke` | Revoke button |
| MCP-004 | As a user, I want to delete an API key so that I remove it permanently | `DELETE /api/mcp/keys/{id}` | Delete button |
| MCP-005 | As a user, I want to copy the MCP configuration so that I can paste it into Claude Code | N/A | Copy config button in key modal |
| MCP-006 | As a user, I want to ensure I have a default key so that MCP works automatically | `POST /api/mcp/keys/ensure-default` | Auto-creation |

---

## 13. Multi-Agent Systems

### 13.1 System Deployment
| ID | User Story | Endpoints | Frontend |
|----|------------|-----------|----------|
| SYS-001 | As a user, I want to deploy multi-agent systems from YAML manifests so that I quickly set up complex workflows | `POST /api/systems/deploy` | N/A (MCP/API) |
| SYS-002 | As a user, I want to validate manifests before deployment so that I catch errors early | `POST /api/systems/deploy` with dry_run=true | Validation feedback |

### 13.2 System Management
| ID | User Story | Endpoints | Frontend |
|----|------------|-----------|----------|
| SYS-003 | As a user, I want to list deployed systems so that I see my agent networks | `GET /api/systems` | Systems list |
| SYS-004 | As a user, I want to view system details so that I understand the agent topology | `GET /api/systems/{name}` | System detail |
| SYS-005 | As a user, I want to restart a system so that I apply configuration changes | `POST /api/systems/{name}/restart` | Restart button |
| SYS-006 | As a user, I want to export a system manifest so that I backup or replicate it | `GET /api/systems/{name}/manifest` | Export button |

---

## 14. System Agent & Fleet Operations

### 14.1 System Agent
| ID | User Story | Endpoints | Frontend |
|----|------------|-----------|----------|
| FLEET-001 | As an admin, I want to see system agent status so that I monitor platform health | `GET /api/system-agent/status` | Agents.vue (system agent pinned at top) |
| FLEET-002 | As an admin, I want to reinitialize the system agent so that I reset it to clean state | `POST /api/system-agent/reinitialize` | Reinitialize action |
| FLEET-003 | As an admin, I want to access the system agent terminal so that I run platform commands | `WS /api/system-agent/terminal` | AgentDetail.vue Terminal tab |

### 14.2 Fleet Status
| ID | User Story | Endpoints | Frontend |
|----|------------|-----------|----------|
| FLEET-004 | As an admin, I want to see fleet-wide status so that I monitor all agents | `GET /api/ops/fleet/status` | Dashboard stats |
| FLEET-005 | As an admin, I want to see fleet health so that I identify issues | `GET /api/ops/fleet/health` | Health indicators |
| FLEET-006 | As an admin, I want to see cost metrics so that I monitor spending | `GET /api/ops/costs` | Cost display |

### 14.3 Fleet Control
| ID | User Story | Endpoints | Frontend |
|----|------------|-----------|----------|
| FLEET-007 | As an admin, I want to restart all agents so that I apply platform updates | `POST /api/ops/fleet/restart` | Restart All action |
| FLEET-008 | As an admin, I want to stop all agents so that I shut down the platform | `POST /api/ops/fleet/stop` | Stop All action |
| FLEET-009 | As an admin, I want to emergency stop so that I immediately halt all activity | `POST /api/ops/emergency-stop` | Emergency Stop button |

### 14.4 Schedule Control
| ID | User Story | Endpoints | Frontend |
|----|------------|-----------|----------|
| FLEET-010 | As an admin, I want to list all schedules across agents so that I see all automation | `GET /api/ops/schedules` | Schedules list |
| FLEET-011 | As an admin, I want to pause all schedules so that I stop automation temporarily | `POST /api/ops/schedules/pause` | Pause All button |
| FLEET-012 | As an admin, I want to resume all schedules so that I restart automation | `POST /api/ops/schedules/resume` | Resume All button |

---

## 15. Templates

### 15.1 Template Browsing
| ID | User Story | Endpoints | Frontend |
|----|------------|-----------|----------|
| TPL-001 | As a user, I want to browse available templates so that I find the right agent type | `GET /api/templates` | Templates.vue grid |
| TPL-002 | As a user, I want to see template details so that I understand capabilities | `GET /api/templates/{id}` | Template cards |
| TPL-003 | As a user, I want to see template credential requirements so that I know what to configure | Template credentials field | Requirements list |
| TPL-004 | As a user, I want to refresh templates so that I see newly added ones | `POST /api/templates/refresh` | Refresh button |

### 15.2 Template Selection
| ID | User Story | Endpoints | Frontend |
|----|------------|-----------|----------|
| TPL-005 | As a user, I want to select a template when creating an agent so that I start with a configuration | Template selector in CreateAgentModal | Template dropdown/cards |

---

## 16. File Management

### 16.1 File Browser (Agent Scoped)
| ID | User Story | Endpoints | Frontend |
|----|------------|-----------|----------|
| FILE-001 | As a user, I want to browse agent files so that I see workspace contents | `GET /api/agents/{name}/files` | FilesPanel tree |
| FILE-002 | As a user, I want to download files so that I get a local copy | `GET /api/agents/{name}/files/download` | Download button |
| FILE-003 | As a user, I want to preview files so that I see contents without downloading | `GET /api/agents/{name}/files/preview` | Preview panel |
| FILE-004 | As a user, I want to edit text files so that I modify agent configuration | `PUT /api/agents/{name}/files` | Edit mode |
| FILE-005 | As a user, I want to delete files so that I clean up workspace | `DELETE /api/agents/{name}/files` | Delete with confirmation |
| FILE-006 | As a user, I want protected file warnings so that I don't accidentally delete critical files | Protected path logic | Disabled delete for protected files |

### 16.2 File Manager (Global)
| ID | User Story | Endpoints | Frontend |
|----|------------|-----------|----------|
| FILE-007 | As a user, I want a dedicated file manager page so that I manage files across agents | N/A | FileManager.vue |
| FILE-008 | As a user, I want to select which agent to browse so that I navigate workspaces | Agent dropdown | Agent selector |
| FILE-009 | As a user, I want two-panel layout so that I see tree and preview side-by-side | N/A | Two-panel layout |
| FILE-010 | As a user, I want to toggle hidden files so that I see/hide system files | show_hidden param | Hidden files toggle |

---

## 17. Agent Dashboard

### 17.1 Custom Dashboard
| ID | User Story | Endpoints | Frontend |
|----|------------|-----------|----------|
| DASH-001 | As a user, I want to see agent-defined dashboards so that I view custom metrics | `GET /api/agent-dashboard/{name}` | DashboardPanel |
| DASH-002 | As an agent developer, I want to define widgets in dashboard.yaml so that I customize the display | dashboard.yaml in agent workspace | Widget rendering |
| DASH-003 | As a user, I want auto-refresh on dashboards so that I see live data | Configurable refresh interval | Auto-refresh |

---

## 18. MCP External Tools

### 18.1 Agent Management Tools
| ID | User Story | Tool Name | Access Control |
|----|------------|-----------|----------------|
| MCP-T01 | As an orchestrator, I want to list all agents so that I know available resources | `list_agents` | Filtered by scope |
| MCP-T02 | As an orchestrator, I want to get agent details so that I understand configuration | `get_agent` | Permission check |
| MCP-T03 | As an orchestrator, I want to get agent template metadata so that I understand capabilities | `get_agent_info` | Permission check |
| MCP-T04 | As an orchestrator, I want to create agents programmatically so that I scale deployment | `create_agent` | Auth required |
| MCP-T05 | As an orchestrator, I want to delete agents so that I clean up | `delete_agent` | Admin required |
| MCP-T06 | As an orchestrator, I want to start agents so that I bring them online | `start_agent` | Permission check |
| MCP-T07 | As an orchestrator, I want to stop agents so that I conserve resources | `stop_agent` | Permission check |
| MCP-T08 | As an orchestrator, I want to list templates so that I know what's available | `list_templates` | No restriction |
| MCP-T09 | As an orchestrator, I want to reload credentials so that I update secrets at runtime | `reload_credentials` | Permission check |
| MCP-T10 | As an orchestrator, I want to check credential status so that I verify configuration | `get_credential_status` | Permission check |
| MCP-T11 | As an orchestrator, I want to get SSH access so that I can debug containers | `get_agent_ssh_access` | Permission check |

### 18.2 Deployment Tools
| ID | User Story | Tool Name | Access Control |
|----|------------|-----------|----------------|
| MCP-T12 | As a developer, I want to deploy local agents via archive so that I test without git | `deploy_local_agent` | Auth required |
| MCP-T13 | As a developer, I want to initialize GitHub sync so that I enable version control | `initialize_github_sync` | Owner required |

### 18.3 Communication Tools
| ID | User Story | Tool Name | Access Control |
|----|------------|-----------|----------------|
| MCP-T14 | As an orchestrator, I want to send messages to agents so that I delegate tasks | `chat_with_agent` | Permission matrix |
| MCP-T15 | As an orchestrator, I want to get chat history so that I review conversations | `get_chat_history` | Permission check |
| MCP-T16 | As an orchestrator, I want to get agent logs so that I debug issues | `get_agent_logs` | Permission check |

### 18.4 System Orchestration Tools
| ID | User Story | Tool Name | Access Control |
|----|------------|-----------|----------------|
| MCP-T17 | As an architect, I want to deploy multi-agent systems from manifests so that I codify topology | `deploy_system` | Auth required |
| MCP-T18 | As an operator, I want to list deployed systems so that I see networks | `list_systems` | Visibility filtered |
| MCP-T19 | As an operator, I want to restart systems so that I apply changes | `restart_system` | Permission check |
| MCP-T20 | As a DevOps engineer, I want to export system manifests so that I backup configuration | `get_system_manifest` | Visibility filtered |

### 18.5 Documentation Tool
| ID | User Story | Tool Name | Access Control |
|----|------------|-----------|----------------|
| MCP-T21 | As a developer, I want to access the agent guide so that I learn to build Trinity agents | `get_agent_requirements` | No auth required |

---

## 19. Agent Server Internal Capabilities

### 19.1 Chat & Execution (Inside Agent Container)
| ID | User Story | Endpoint | Purpose |
|----|------------|----------|---------|
| AS-001 | As the platform, I want to send chat messages to agents internally | `POST /api/chat` | Synchronous execution with lock |
| AS-002 | As the platform, I want to execute parallel tasks | `POST /api/task` | Stateless headless execution |
| AS-003 | As the platform, I want to get conversation history | `GET /api/chat/history` | Session transcript |
| AS-004 | As the platform, I want to get session stats | `GET /api/chat/session` | Token/cost tracking |
| AS-005 | As the platform, I want to terminate executions | `POST /api/executions/{id}/terminate` | Graceful/force kill |
| AS-006 | As the platform, I want to stream execution logs | `GET /api/executions/{id}/stream` | SSE real-time logs |

### 19.2 Agent Info & Health
| ID | User Story | Endpoint | Purpose |
|----|------------|----------|---------|
| AS-007 | As the platform, I want to check agent health | `GET /health` | Liveness probe |
| AS-008 | As the platform, I want to get agent metadata | `GET /api/agent/info` | Agent configuration |
| AS-009 | As the platform, I want to get template metadata | `GET /api/template/info` | Capabilities discovery |
| AS-010 | As the platform, I want to get custom metrics | `GET /api/metrics` | Agent-defined metrics |

### 19.3 Activity Monitoring
| ID | User Story | Endpoint | Purpose |
|----|------------|----------|---------|
| AS-011 | As the platform, I want to get real-time activity | `GET /api/activity` | Tool call tracking |
| AS-012 | As the platform, I want to get tool call details | `GET /api/activity/{id}` | Drill-down |

### 19.4 Credential Management
| ID | User Story | Endpoint | Purpose |
|----|------------|----------|---------|
| AS-013 | As the platform, I want to inject credentials | `POST /api/credentials/update` | .env and .mcp.json |
| AS-014 | As the platform, I want to check credential status | `GET /api/credentials/status` | File existence |

### 19.5 Git Operations
| ID | User Story | Endpoint | Purpose |
|----|------------|----------|---------|
| AS-015 | As the platform, I want to get git status | `GET /api/git/status` | Change detection |
| AS-016 | As the platform, I want to sync to GitHub | `POST /api/git/sync` | Push changes |
| AS-017 | As the platform, I want to pull from GitHub | `POST /api/git/pull` | Update workspace |
| AS-018 | As the platform, I want to get commit log | `GET /api/git/log` | History |

### 19.6 File Operations
| ID | User Story | Endpoint | Purpose |
|----|------------|----------|---------|
| AS-019 | As the platform, I want to list agent files | `GET /api/files` | Workspace tree |
| AS-020 | As the platform, I want to download files | `GET /api/files/download` | File content |
| AS-021 | As the platform, I want to preview files | `GET /api/files/preview` | MIME-typed preview |
| AS-022 | As the platform, I want to update files | `PUT /api/files` | Edit content |
| AS-023 | As the platform, I want to delete files | `DELETE /api/files` | Remove files |

### 19.7 Trinity Orchestration
| ID | User Story | Endpoint | Purpose |
|----|------------|----------|---------|
| AS-024 | As the platform, I want to check Trinity status | `GET /api/trinity/status` | Injection status |
| AS-025 | As the platform, I want to inject Trinity infrastructure | `POST /api/trinity/inject` | Meta-prompt + directories |
| AS-026 | As the platform, I want to reset Trinity | `POST /api/trinity/reset` | Clean state |

### 19.8 Dashboard Configuration
| ID | User Story | Endpoint | Purpose |
|----|------------|----------|---------|
| AS-027 | As the platform, I want to get dashboard config | `GET /api/dashboard` | Widget definitions |

### 19.9 Terminal Access
| ID | User Story | Endpoint | Purpose |
|----|------------|----------|---------|
| AS-028 | As the platform, I want WebSocket terminal access | `WS /api/agents/{name}/terminal` | Interactive PTY |

---

## Summary Statistics

| Category | Count |
|----------|-------|
| Authentication & Setup | 8 |
| Agent Management | 12 |
| Agent Execution & Chat | 21 |
| Observability & Monitoring | 13 |
| Agent Configuration | 9 |
| Credential Management | 13 |
| Scheduling & Automation | 8 |
| Agent Sharing & Collaboration | 11 |
| Public Access | 7 |
| Platform Settings | 13 |
| Git Synchronization | 7 |
| MCP API Keys | 6 |
| Multi-Agent Systems | 6 |
| System Agent & Fleet Operations | 12 |
| Templates | 5 |
| File Management | 10 |
| Agent Dashboard | 3 |
| MCP External Tools | 21 |
| Agent Server Internal | 28 |
| **TOTAL** | **213** |

---

## Next Steps

This inventory should be cross-referenced with:
1. **Feature Flows** (`docs/memory/feature-flows/`) - Ensure all user stories have documented flows
2. **Test Coverage** (`tests/`) - Ensure critical user stories have automated tests
3. **Requirements** (`docs/memory/requirements.md`) - Ensure all user stories trace to requirements

---

*Generated by Claude Code analysis of Trinity codebase on 2026-01-13*
