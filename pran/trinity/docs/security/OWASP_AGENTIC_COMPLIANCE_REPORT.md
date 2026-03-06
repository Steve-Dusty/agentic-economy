# OWASP Top 10 for Agentic Applications - Trinity Compliance Report

> **Report Date**: 2025-12-23
> **Framework**: OWASP Top 10 for Agentic Applications 2026
> **Platform**: Trinity Deep Agent Orchestration Platform
> **Scope**: Platform-level security (agent templates are user responsibility)
> **Deployment Model**: On-Premises / Intranet (not SaaS)

---

## Deployment Context

**Trinity is designed for on-premises, intranet deployment** — not as a multi-tenant SaaS platform. This fundamentally changes the threat model and security priorities.

### Threat Model Assumptions

| Factor | Assumption | Security Impact |
|--------|------------|-----------------|
| **Network** | Trusted corporate intranet | No internet-facing attack surface for agents |
| **Users** | Authenticated employees | Insider threat model, not external attackers |
| **Multi-tenancy** | Single organization | No cross-tenant isolation required |
| **Templates** | Internal repos (GitLab, GitHub Enterprise) | Controlled supply chain |
| **Public Links** | Internal access only (if used) | No internet exposure |

### What This Means

- **External attackers** must first breach the corporate network
- **Prompt injection** requires a malicious insider or compromised internal system
- **Agent-to-agent communication** stays within trusted network boundaries
- **Supply chain attacks** are limited to internal repository compromise

---

## Executive Summary

This report analyzes Trinity's compliance with the OWASP Top 10 for Agentic Applications 2026, released at Black Hat Europe (December 2025). The framework addresses security risks specific to autonomous AI agents that plan, execute, and delegate tasks independently.

### Risk Overview

The table below shows risk ratings for both deployment models. **On-Prem ratings reflect the reduced attack surface of intranet deployment.**

| ASI | Category | SaaS Risk | On-Prem Risk | Findings |
|-----|----------|-----------|--------------|----------|
| ASI01 | Agent Goal Hijack | MEDIUM | **LOW** | No prompt injection detection; requires insider |
| ASI02 | Tool Misuse | HIGH | **MEDIUM** | Tool allowlist not enforced; affects internal systems |
| ASI03 | Identity/Privilege Abuse | HIGH | **MEDIUM** | Permission gaps; compliance requirement |
| ASI04 | Supply Chain | MEDIUM | **LOW** | Internal repos controlled; no public dependencies |
| ASI05 | Code Execution (RCE) | HIGH | **MEDIUM** | Affects internal systems; container isolation helps |
| ASI06 | Memory Poisoning | MEDIUM | **LOW** | Single org; insider threat only |
| ASI07 | Insecure Inter-Agent Comm | CRITICAL | **LOW** | Trusted network; no internet exposure |
| ASI08 | Cascading Failures | MEDIUM | **MEDIUM** | Reliability concern regardless of deployment |
| ASI09 | Human Trust Exploitation | HIGH | **LOW** | Public links internal-only or disabled |
| ASI10 | Rogue Agents | HIGH | **MEDIUM** | Resource governance; ops efficiency |

### On-Premises Risk Adjustment Rationale

| Original Rating | On-Prem Rating | Categories | Rationale |
|-----------------|----------------|------------|-----------|
| CRITICAL → LOW | ASI07 | Inter-agent communication on trusted network; header spoofing requires authenticated insider |
| HIGH → LOW | ASI09 | Public links only accessible internally; may be disabled entirely |
| HIGH → MEDIUM | ASI02, ASI03, ASI05, ASI10 | Still matters for compliance, ops efficiency, and internal system protection |
| MEDIUM → LOW | ASI01, ASI04, ASI06 | Insider threat model; controlled supply chain; single-org context |
| MEDIUM → MEDIUM | ASI08 | Reliability matters regardless of deployment model |

### Platform vs. Agent Responsibility

Trinity is a **platform** that deploys and orchestrates agents. Security responsibilities are split:

| Responsibility | Owner | Notes |
|----------------|-------|-------|
| Container isolation | **Platform** | Docker security, network isolation |
| Credential management | **Platform** | Redis storage, injection, hot-reload |
| Agent-to-agent auth | **Platform** | MCP keys, permission model |
| Inter-agent communication | **Platform** | HTTP routing, WebSocket events |
| Emergency controls | **Platform** | Stop, restart, kill switches |
| Tool selection | **Agent Template** | CLAUDE.md, MCP servers configured by user |
| Prompt injection defense | **Agent Template** | System prompts, guardrails in template |
| Memory management | **Agent Template** | How agent uses Chroma, context handling |
| Behavioral constraints | **Agent Template** | Custom instructions, allowed actions |

---

## Detailed Findings

### ASI01 - Agent Goal Hijack

**Risk Level**: MEDIUM

**Description**: Attackers alter agent objectives through malicious text content. Agents struggle to distinguish instructions from data.

#### Current Mitigations

| Control | Location | Status |
|---------|----------|--------|
| Source agent verification | `chat.py:72-75` | ✅ Header validated |
| Session isolation | `chat.py:764-876` | ✅ Per-user message access |
| Public link rate limiting | `public.py:31-32` | ✅ 30 msg/min per IP |
| Email verification | `public_links.py:57-93` | ✅ Optional requirement |

#### Vulnerabilities Found

1. **No Prompt Injection Detection**
   - Location: `src/backend/routers/chat.py:166-167`
   - User messages passed directly to agent without validation
   - No escaping or filtering for malicious instructions
   - **Recommendation**: Add prompt injection detection library (e.g., rebuff, LLM Guard)

2. **System Prompt Override in Parallel Tasks**
   - Location: `src/backend/routers/chat.py:359-365`
   - `ParallelTaskRequest` allows `system_prompt` field from caller
   - Attacker could override agent's system prompt via API
   - **Recommendation**: Whitelist allowed system prompts or remove override capability

3. **Model Selection Bypass**
   - Location: `agent_server/routers/chat.py:159`
   - Model validated with `startswith("claude-")` - allows any claude model
   - **Recommendation**: Strict model allowlist per agent template

---

### ASI02 - Tool Misuse and Exploitation

**Risk Level**: HIGH

**Description**: Agents use legitimate tools unsafely due to ambiguous prompts, misalignment, or poisoned inputs.

#### Current Mitigations

| Control | Location | Status |
|---------|----------|--------|
| Container hardening | `agents.py:655-663` | ✅ CAP_DROP ALL, no-new-privileges |
| AppArmor profile | `agents.py:656` | ✅ docker-default profile |
| tmpfs noexec | `agents.py:659` | ✅ /tmp mounted noexec,nosuid |
| Tool call logging | `chat.py:206-220` | ✅ All tool calls audited |
| Memory/CPU limits | Container config | ✅ Enforced per agent |

#### Vulnerabilities Found

1. **Tool Allowlist Not Enforced**
   - Location: `ParallelTaskRequest.allowed_tools` field exists but not enforced
   - Claude Code can call any available tool regardless of allowlist
   - **Recommendation**: Implement tool execution middleware that validates against allowlist

2. **Credentials Exposed as Environment Variables**
   - Location: `agents.py:508-526`
   - All credentials available to subprocess and child processes
   - **Recommendation**: Use credential files with restricted permissions or in-memory secrets

3. **Shared Folder Write Access**
   - Location: `agents.py:633`
   - Shared folders mounted with 'rw' mode
   - Agent A can write executable, Agent B can execute
   - **Recommendation**: Add execution bit filtering or read-only sharing option

4. **GitHub PAT in Clone URL**
   - Location: `template_service.py:34`
   - PAT visible in process list and logs on failure
   - **Recommendation**: Use credential helper or SSH key authentication

---

### ASI03 - Identity and Privilege Abuse

**Risk Level**: HIGH

**Description**: Agents inherit high-privilege credentials which can be escalated or passed across agents without proper scoping.

#### Current Mitigations

| Control | Location | Status |
|---------|----------|--------|
| MCP key scoping | `mcp_keys.py:268-275` | ✅ "user" vs "agent" scope |
| Agent permission model | `db/permissions.py` | ✅ Explicit grants required |
| Credential ownership | `credentials.py:211-249` | ✅ User ID verified |
| Session-based access | `db/permissions.py:70-82` | ✅ Per-request checks |

#### Vulnerabilities Found

1. **Agent-to-Agent Permissions Not Enforced at Request Level**
   - Location: `chat.py:50-56`
   - `X-Source-Agent` header accepted without permission verification
   - Backend records source but doesn't check if source has permission to call target
   - **Recommendation**: Add permission check in chat endpoint before proxying

2. **Admin Credential Bypass**
   - Location: `agents.py:382-386`
   - GitHub credentials retrieved with hardcoded "admin" user ID
   - Any user creating GitHub-based agent accesses admin credentials
   - **Recommendation**: Use service account pattern with explicit credential assignment

3. **Credential Assignment Without Ownership Check**
   - Location: `credentials.py:251-259`
   - `assign_credential_to_agent()` doesn't verify agent ownership
   - **Recommendation**: Add ownership verification before credential assignment

---

### ASI04 - Agentic Supply Chain Vulnerabilities

**Risk Level**: MEDIUM

**Description**: Tools, plugins, prompt templates, and MCP servers fetched at runtime create compromise risks.

#### Current Mitigations

| Control | Location | Status |
|---------|----------|--------|
| YAML safe_load | `template_service.py:309-359` | ✅ No arbitrary deserialization |
| Template validation | `is_trinity_compatible()` | ✅ Structure checks |
| Git depth=1 clone | Template cloning | ✅ Minimal history |
| .git removal | `template_service.py:42-51` | ✅ Clean workspace |
| Local deploy limits | `deploy_local_agent` | ✅ Size, file count limits |

#### Vulnerabilities Found

1. **MCP Configuration Not Schema-Validated**
   - Location: `template_service.py:254-273`
   - .mcp.json template substituted without schema validation
   - Potential for path traversal in "args" fields
   - **Recommendation**: Add JSON schema validation for .mcp.json

2. **No Git Commit Verification**
   - Location: Template cloning flow
   - No checksum or signature verification of cloned repository
   - Malicious CLAUDE.md in repo trusted implicitly
   - **Recommendation**: Support signed commits or manifest checksums

3. **Local Templates Trusted Implicitly**
   - Location: `templates.py:33-54`
   - Any directory in `/agent-configs/templates/` accepted
   - No integrity verification
   - **Recommendation**: Add template signing for production deployments

---

### ASI05 - Unexpected Code Execution (RCE)

**Risk Level**: HIGH

**Description**: Agents generate or run code unsafely, including shell scripts and command execution.

#### Current Mitigations

| Control | Location | Status |
|---------|----------|--------|
| Docker isolation | Container architecture | ✅ Separate containers |
| Non-root execution | Dockerfile | ✅ developer:1000 user |
| Capability dropping | `agents.py:656-657` | ✅ CAP_DROP ALL |
| Single-threaded execution | `claude_code.py` | ✅ asyncio.Lock |
| AppArmor enforcement | Container security_opt | ✅ docker-default |

#### Vulnerabilities Found

1. **Claude Code Subprocess Unrestricted**
   - Location: `claude_code.py:8-12`
   - No seccomp profile or additional sandboxing
   - Full filesystem write access within container
   - **Recommendation**: Add seccomp profile, consider gVisor for high-security agents

2. **SSH Server Enabled in Containers**
   - Location: `Dockerfile:50-52`
   - SSH access available to all agents
   - Increases attack surface
   - **Recommendation**: Make SSH optional via template configuration

3. **Shared Folders Enable Cross-Agent RCE**
   - Location: `agents.py:633`
   - Agent A writes executable to shared-out
   - Agent B can execute from shared-in
   - **Recommendation**: Add noexec mount option for shared folders

4. **Read-Only Filesystem Not Enabled**
   - Location: `agents.py:659`
   - `read_only=False` allows full filesystem modification
   - **Recommendation**: Enable read-only root with explicit writable volumes

---

### ASI06 - Memory and Context Poisoning

**Risk Level**: MEDIUM

**Description**: Attackers poison agent memory systems to influence future decisions.

#### Current Mitigations

| Control | Location | Status |
|---------|----------|--------|
| Context monitoring | `ops.py:73-77` | ✅ 75%/90% thresholds |
| Session isolation | Chat persistence | ✅ Per-user sessions |
| Access control on history | `chat.py:791` | ✅ Owner-only by default |
| Chroma persistent storage | Trinity injection | ✅ Isolated directory |

#### Vulnerabilities Found

1. **No Vector Memory Provenance**
   - Location: `trinity.py:125-128`
   - Vectors stored without source tracking (which agent, user, timestamp)
   - Poisoned vectors indistinguishable from legitimate ones
   - **Recommendation**: Add metadata fields for provenance tracking

2. **No Agent Isolation in Chroma**
   - Location: `trinity.py:21-24`
   - All agents share vector store instance
   - No tenant separation
   - **Recommendation**: Implement collection-per-agent or separate Chroma instances

3. **Chat Messages Stored Without Validation**
   - Location: `chat.py:154-162`
   - No content filtering before persistence
   - Tool responses stored as-is
   - **Recommendation**: Add content validation layer before storage

---

### ASI07 - Insecure Inter-Agent Communication

**Risk Level**: CRITICAL

**Description**: Multi-agent message exchanges lack authentication, encryption, or semantic validation.

#### Current Mitigations

| Control | Location | Status |
|---------|----------|--------|
| MCP API key auth | `mcp_keys.py` | ✅ Bearer token validation |
| Agent permission model | `db/permissions.py` | ✅ Explicit grants |
| Source tracking | `chat.py:71-86` | ✅ ExecutionSource logged |
| Collaboration audit | `chat.py:107-130` | ✅ Events recorded |

#### Vulnerabilities Found

1. **No Message Signing or HMAC**
   - Location: `chat.py:172-178`
   - Agent-to-agent messages sent without cryptographic verification
   - **Recommendation**: Add HMAC signing with rotating shared secrets

2. **X-Source-Agent Header Spoofable**
   - Location: `chat.py:51-55`
   - Any authenticated user can set arbitrary X-Source-Agent header
   - No verification that header matches actual caller
   - **Recommendation**: Validate header against authentication context

3. **Plain HTTP Internal Communication**
   - Location: `chat.py:174`
   - Agent calls via `http://agent-{name}:8000`
   - No TLS on internal network
   - **Recommendation**: Implement mTLS or service mesh

4. **WebSocket Events Not Authenticated**
   - Location: `main.py:61-93`
   - WebSocket accepts optional auth
   - Unauthenticated clients see collaboration metadata
   - **Recommendation**: Require authentication for WebSocket connections

---

### ASI08 - Cascading Failures

**Risk Level**: MEDIUM

**Description**: Errors propagate across agents due to interconnected architecture.

#### Current Mitigations

| Control | Location | Status |
|---------|----------|--------|
| Execution queue limits | `execution_queue.py:32-34` | ✅ MAX_QUEUE_SIZE=3 |
| Backpressure (429) | Queue overflow | ✅ Immediate rejection |
| Timeout controls | `chat.py:176, 374` | ✅ 300s default |
| Error isolation | `chat.py:269-293` | ✅ Per-request handling |
| Fleet health monitoring | `ops.py:137-253` | ✅ Context/idle detection |

#### Vulnerabilities Found

1. **No Circuit Breaker Pattern**
   - Location: `execution_queue.py:155-189`
   - Failed agent continues accepting queue entries
   - No fast-fail for consistently failing agents
   - **Recommendation**: Implement circuit breaker with half-open state

2. **No Exponential Backoff**
   - Location: `chat.py:173` (httpx call)
   - Single attempt with no retry logic
   - Transient failures cause immediate error
   - **Recommendation**: Add retry with exponential backoff for agent calls

3. **Schedule Rate Limiting Gap**
   - Location: `scheduler_service.py`
   - Multiple schedules can overwhelm agent queue
   - 4th task rejected silently (429)
   - **Recommendation**: Add schedule-level rate limiting or priority queuing

---

### ASI09 - Human-Agent Trust Exploitation

**Risk Level**: HIGH

**Description**: Users over-trust agent recommendations, allowing manipulation.

#### Current Mitigations

| Control | Location | Status |
|---------|----------|--------|
| Public link ownership | `public_links.py:71` | ✅ Owner-only creation |
| Email verification | `public_links.py:91` | ✅ Optional requirement |
| Rate limiting | `public.py:31-32` | ✅ Per-IP limits |
| Audit logging | `audit_service.py` | ✅ All actions logged |
| Schedule execution tracking | Database schema | ✅ Status recorded |

#### Vulnerabilities Found

1. **No Confirmation Dialogs for Sensitive Actions**
   - Location: Public chat flow
   - Public agents can execute file operations without confirmation
   - No "are you sure" for destructive actions
   - **Recommendation**: Add confirmation step for file writes/deletes via public links

2. **Schedules Execute Without Approval**
   - Location: `schedules.py`
   - Automated execution with no preview or approval workflow
   - Modified schedule message executes without verification
   - **Recommendation**: Add approval workflow for schedule modifications

3. **No File Access Restrictions for Public Links**
   - Location: Trinity injection flow
   - If agent has file tools, public link can access files
   - No sampling of what's exposed
   - **Recommendation**: Add file access restrictions per public link

4. **Audit Log Fire-and-Forget**
   - Location: `audit_service.py:24-44`
   - 2-second timeout, operations continue if logger down
   - Malicious actor could disable logging
   - **Recommendation**: Make audit logging synchronous for critical operations

---

### ASI10 - Rogue Agents

**Risk Level**: HIGH

**Description**: Compromised or misaligned agents act harmfully while appearing legitimate.

#### Current Mitigations

| Control | Location | Status |
|---------|----------|--------|
| System agent protection | `system_agent_service.py` | ✅ Cannot be deleted |
| Emergency stop | `ops.py:598-664` | ✅ Admin-only manual trigger |
| Container labeling | Docker labels | ✅ Trinity agent identification |
| Activity monitoring | `chat.py:569-678` | ✅ Tool calls logged |
| Lifecycle controls | `agents.py` | ✅ Start/stop/delete |

#### Vulnerabilities Found

1. **No Automatic Emergency Triggers**
   - Location: `ops.py:608`
   - Emergency stop requires manual admin action
   - No automatic triggers for:
     - CPU exhaustion
     - Excessive API calls
     - Repeated crashes
   - **Recommendation**: Add automatic kill triggers based on resource/behavior thresholds

2. **No Behavioral Anomaly Detection**
   - Location: Activity logging
   - Only records actions, doesn't detect anomalies
   - No baseline comparison
   - **Recommendation**: Add ML-based behavioral monitoring

3. **No Network Isolation Between Agents**
   - Location: Docker network configuration
   - All agents on same network can reach each other
   - Compromised agent can scan/attack others
   - **Recommendation**: Implement network policies or service mesh

4. **Incomplete Credential Revocation on Delete**
   - Location: `agents.py:1176-1204`
   - MCP keys deleted, but external service credentials not revoked
   - **Recommendation**: Add external credential cleanup on agent deletion

5. **No Resource Quotas per Agent**
   - Location: Container creation
   - CPU/memory limits exist but no disk or network bandwidth limits
   - **Recommendation**: Add comprehensive resource quotas

---

## Recommendations Summary

### On-Premises Priority Matrix

For on-premises/intranet deployments, recommendations are reprioritized based on the revised threat model.

#### Priority 1: Operations & Reliability (Recommended)

These improve platform stability and ops efficiency:

| # | Issue | Recommendation | Effort | ASI |
|---|-------|----------------|--------|-----|
| 1 | Automatic emergency triggers | Add resource-based kill switches (CPU, memory, cost thresholds) | Medium | ASI10 |
| 2 | Circuit breaker pattern | Add per-agent circuit breaker with half-open state | Medium | ASI08 |
| 3 | Permission enforcement | Add permission check in chat endpoint (for access control, not security) | Low | ASI03 |
| 4 | System prompt override | Remove or restrict system_prompt in ParallelTaskRequest | Low | ASI01 |

#### Priority 2: Compliance & Governance (If Required)

These address audit and compliance requirements:

| # | Issue | Recommendation | Effort | ASI |
|---|-------|----------------|--------|-----|
| 5 | Credential scoping | Move credentials to secure files with restricted permissions | Medium | ASI02 |
| 6 | Audit log reliability | Make audit logging synchronous for critical operations | Low | ASI09 |
| 7 | Tool allowlist enforcement | Implement middleware validation (for governance, not security) | Medium | ASI02 |
| 8 | Vector memory provenance | Add source tracking metadata (for debugging) | Medium | ASI06 |

#### Priority 3: Nice-to-Have (Deprioritize for On-Prem)

These are less critical for intranet deployments:

| # | Issue | Original Priority | On-Prem Priority | Rationale |
|---|-------|-------------------|------------------|-----------|
| 9 | mTLS for agent communication | High | **Low** | Trusted network |
| 10 | Message signing/HMAC | High | **Low** | Header spoofing requires insider |
| 11 | Network isolation between agents | High | **Low** | Single org, trusted users |
| 12 | Prompt injection detection | Medium | **Low** | Insider threat only |
| 13 | Template signing | High | **Low** | Internal repos controlled |
| 14 | Public link hardening | High | **N/A** | Internal access only or disabled |

### SaaS Deployment Recommendations (If Applicable)

If Trinity were deployed as a SaaS platform, the original priorities would apply:

| Priority | Issue | Recommendation | Effort |
|----------|-------|----------------|--------|
| **Immediate** | Inter-agent header spoofing | Validate X-Source-Agent against auth context | Low |
| **Immediate** | Permission enforcement gap | Add permission check in chat endpoint | Low |
| **Immediate** | System prompt override | Remove or restrict system_prompt | Low |
| **Short-term** | mTLS for agent communication | Implement service mesh or direct mTLS | High |
| **Short-term** | Prompt injection detection | Integrate LLM Guard or similar library | Medium |
| **Short-term** | Network isolation | Docker network policies | High |
| **Medium-term** | Behavioral anomaly detection | ML-based monitoring system | High |
| **Medium-term** | Template signing | Implement signed manifests | High |

---

## Compliance Matrix

### On-Premises Compliance Status

| ASI | OWASP Recommendation | On-Prem Status | Gap | Action Needed |
|-----|---------------------|----------------|-----|---------------|
| ASI01 | Input validation, human approval | **Acceptable** | No prompt injection filtering | Low priority (insider only) |
| ASI02 | Sandboxing, argument validation | **Good** | Tool allowlist not enforced | Optional governance |
| ASI03 | Short-lived tokens, least privilege | **Acceptable** | Permission enforcement gap | Fix for access control |
| ASI04 | Signed manifests, kill switches | **Acceptable** | No signature verification | N/A (internal repos) |
| ASI05 | Sandbox, review before execute | **Good** | Shared folder RCE vector | Monitor only |
| ASI06 | Provenance tracking, segmentation | **Acceptable** | No vector provenance | Nice-to-have |
| ASI07 | mTLS, signed payloads | **Acceptable** | No message signing | N/A (trusted network) |
| ASI08 | Circuit breakers, isolation | **Needs Work** | No circuit breaker | Recommended |
| ASI09 | Confirmations, audit logs | **Acceptable** | No confirmation dialogs | N/A (internal only) |
| ASI10 | Behavioral monitoring, kill switch | **Needs Work** | Manual-only emergency stop | Recommended |

### Status Legend

| Status | Meaning |
|--------|---------|
| **Good** | Adequate controls in place |
| **Acceptable** | Gaps exist but low risk for on-prem |
| **Needs Work** | Recommended improvements for ops/reliability |

### SaaS Compliance Status (For Reference)

If deployed as SaaS, compliance would be evaluated differently:

| ASI | SaaS Status | Gap Severity |
|-----|-------------|--------------|
| ASI01 | Partial | Medium |
| ASI02 | Good | Low |
| ASI03 | **Poor** | High |
| ASI04 | Partial | Medium |
| ASI05 | Good | Low |
| ASI06 | Partial | Medium |
| ASI07 | **Poor** | Critical |
| ASI08 | Partial | Medium |
| ASI09 | **Poor** | High |
| ASI10 | Partial | High |

---

## References

- [OWASP Top 10 for Agentic Applications 2026](https://genai.owasp.org/resource/owasp-top-10-for-agentic-applications-for-2026/)
- [Trinity OWASP Top 10:2025 Compliance Report](./OWASP_COMPLIANCE_REPORT.md)
- [Trinity Architecture Documentation](../memory/architecture.md)
- [Trinity Security Hardening (2025-12-23)](../memory/changelog.md)

---

## Revision History

| Date | Author | Changes |
|------|--------|---------|
| 2025-12-23 | Claude Code | Added on-premises deployment context and revised risk ratings |
| 2025-12-23 | Claude Code | Initial report based on OWASP Agentic AI 2026 framework |

---

## Appendix: On-Premises Security Checklist

Quick checklist for on-premises Trinity deployments:

### Must Have (Operations)

- [ ] Emergency stop capability configured (manual is acceptable)
- [ ] Resource limits set per agent (CPU, memory)
- [ ] Execution queue enabled (prevents parallel execution)
- [ ] Audit logging enabled
- [ ] Admin password set (not default)
- [ ] SECRET_KEY configured (not default)

### Should Have (Reliability)

- [ ] Fleet health monitoring enabled
- [ ] Context threshold alerts configured (75%/90%)
- [ ] Backup strategy for SQLite database
- [ ] Redis persistence enabled (AOF)

### Nice to Have (Governance)

- [ ] Permission model configured for agent-to-agent calls
- [ ] Tool allowlist defined per agent template
- [ ] Credential scoping per agent
- [ ] Vector memory provenance tracking

### Not Required for On-Prem

- ~~mTLS between agents~~ (trusted network)
- ~~Message signing/HMAC~~ (trusted network)
- ~~Network isolation between agents~~ (single org)
- ~~Prompt injection detection~~ (insider threat only)
- ~~Template signing~~ (internal repos)
- ~~Public link hardening~~ (internal access only)
