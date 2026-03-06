# Trinity UI Integration Test - Phase Index

> **Purpose**: Modular testing framework - each phase builds on previous phases
> **Structure**: Sequential phases, each with explicit prerequisites and success criteria
> **Duration**: ~2-3 hours for full suite (or skip to specific phase)
> **Format**: Markdown phase files, designed for automated sub-agent execution

---

## Phase Overview

| Phase | Name | Duration | Prerequisites | Output | Status |
|-------|------|----------|---|--------|--------|
| 0 | Setup & Prerequisites | 5 min | None | Services running, clean slate | 🟢 |
| 1 | Authentication & UI | 5 min | Phase 0 | Logged in, valid token | 🟢 |
| 2 | Agent Creation (GitHub) | 30 min | Phase 1 | 3 agents running + default permissions | 🟢 |
| 3 | Context Validation (CRITICAL) | 10 min | Phase 2 | Context tracking verified | 🟡 Known bug |
| 4 | State Persistence + Activity | 10 min | Phase 3 | File I/O + Activity tracking | 🟢 |
| 5 | Agent Collaboration + Permissions | 25 min | Phase 4 | MCP communication + permission enforcement | 🟢 |
| 7 | Scheduling & Autonomy | 15 min | Phase 5 | Schedule execution verified | 🟢 |
| 8 | Execution Queue | 15 min | Phase 7 | Concurrency handling tested | 🟢 |
| 9 | File Browser | 10 min | Phase 8 | File operations verified | 🟢 |
| 10 | Error Handling | 10 min | Phase 9 | Failure recovery tested | 🟢 |
| 11 | Multi-Agent Dashboard | 10 min | Phase 10 | All features together | 🟢 |
| 12 | Cleanup | 5 min | Any phase | All agents deleted | 🟢 |
| 13 | System Settings | 20 min | Phase 1 | Trinity Prompt + Email Whitelist + API Keys | 🟢 |
| 14 | OpenTelemetry | 15 min | Phase 1 | OTel metrics collection + UI display | 🟢 |
| 15 | System Agent & Ops | 20 min | Phase 1, 14 | System agent, fleet ops, Web Terminal | 🟢 |
| 16 | Web Terminal | 15 min | Phase 1, 2 | Terminal for all agents (Req 11.5) | 🟢 |
| 17 | Email Authentication | 15 min | Phase 0 | Email OTP login flow (Req 12.4) | 🟢 |
| 18 | GitHub Initialization | 15 min | Phase 1, 2 | Agent files synced to GitHub | 🟢 |
| 19 | First-Time Setup | 10 min | Phase 0, Fresh DB | Admin password wizard, login blocking | 🆕 |
| 20 | Live Execution Streaming | 20 min | Phase 2, 7 | SSE streaming, Live indicator, Stop button | 🆕 |
| 21 | Session Management | 15 min | Phase 2 | Chat session CRUD via API | 🆕 |
| 22 | Logs & Telemetry | 15 min | Phase 2 | Container logs, CPU/memory, tool tracking | 🆕 |
| 23 | Agent Configuration | 20 min | Phase 2 | Resource limits, model selection, capabilities | 🆕 |
| 24 | Credential Management | 25 min | Phase 1 | Credential CRUD, bulk import, OAuth, hot-reload | 🆕 |
| 25 | Agent Sharing | 15 min | Phase 1, 2 | Share agents, access control, whitelist | 🆕 |
| 26 | Shared Folders | 20 min | Phase 2, 5 | File collaboration via Docker volumes | 🆕 |
| 27 | Public Access | 20 min | Phase 1, 2 | Public links, email verification, revocation | 🆕 |
| 28 | Agent Dashboard | 15 min | Phase 2 | Widget system, auto-refresh, dashboard.yaml | 🆕 |

**Total Time**: ~420 minutes (~7 hours) for full suite

---

## How to Run Phases

### Automated (Recommended)
Sub-agent runs phases sequentially:

```bash
# Run all phases
python3 run_test_phases.py --all

# Run specific phase
python3 run_test_phases.py --phase 3

# Run phase range
python3 run_test_phases.py --from 2 --to 5

# Skip to phase (requires manual verification of prior phases)
python3 run_test_phases.py --phase 7 --skip-prerequisites
```

### Manual (Single Phase)
Tester runs phase manually:

1. Read phase file: `PHASE_XX_NAME.md`
2. Understand prerequisites (must complete previous phase)
3. Follow test steps
4. Verify success criteria
5. Document results
6. Proceed to next phase

---

## Phase File Structure

Each phase file (`PHASE_XX_NAME.md`) contains:

```
# Header
- Purpose
- Duration
- Prerequisites (must be PASSED)
- Output

## Prerequisites
- Checklist of what must be done first

## Test Steps
1. Step 1: Action → Expected → Verify
2. Step 2: Action → Expected → Verify
...

## Critical Validations
- Core requirements

## Success Criteria
- Phase is PASSED when...

## Troubleshooting
- Common issues and fixes

## Next Phase
- What to do after PASSED
```

---

## Critical Phases (Do Not Skip)

These phases must **PASS**:

1. **Phase 0: Setup** - No services = test can't run
2. **Phase 1: Authentication** - Can't access any features without login
3. **Phase 2: Agent Creation** - Must use local templates (not local)
4. **Phase 3: Context Validation** - CRITICAL BUG - must document status

All other phases can be skipped if time-constrained, but phases 0-3 are mandatory.

---

## Known Issues by Phase

| Phase | Issue | Status | Impact |
|-------|-------|--------|--------|
| 2 | Template pre-selection bug | Known | Minor - use API workaround |
| 3 | **Context stuck at 0%** | **CRITICAL BUG** | **Blocks testing** |
| 5 | UI tab switching broken | Confirmed | Use API for testing |
| 7+ | Not yet executed | TBD | Unknown |

---

## Test Results Template

For each phase execution, record:

```markdown
## Phase X: [Name]

**Date**: 2025-12-09
**Tester**: [Name or Agent ID]
**Duration**: [Actual time]

### Results
- [ ] Prerequisite X verified
- [ ] Test step 1: PASSED
- [ ] Test step 2: PASSED
- [ ] Success criteria: PASSED

### Issues Found
1. [Issue if any]

### Evidence
- [Screenshots, logs, or artifacts]

### Status
- ✅ PASSED → Proceed to Phase X+1
- ⚠️ PARTIAL → Investigate issue
- ❌ FAILED → Stop, file bug report
```

---

## Sub-Agent Integration

The UI integration test sub-agent (`ui-integration-tester.md`) runs phases sequentially:

**How It Works**:
1. Sub-agent reads phase file from `docs/testing/phases/PHASE_XX.md`
2. Executes all test steps (browser automation + API calls)
3. Records results and screenshots
4. If PASSED: automatically proceeds to next phase
5. If FAILED: stops, documents issue, awaits decision
6. Generates test report with phase summaries

**Configuration**:
- Phases folder: `docs/testing/phases/`
- Phase naming: `PHASE_XX_NAME.md`
- Results folder: `test-results/phase-XX/`
- Screenshots folder: `test-screenshots/phase-XX/`

---

## GitHub Agent Validation (Critical)

**In Every Phase**: Verify agents use local templates

For test-echo, test-counter, test-delegator, test-worker, etc.:

```bash
# MUST show local:test-*
docker inspect agent-test-echo --format='{{index .Config.Labels "trinity.template"}}'

# NOT local:test-echo or local:test-counter
```

**Failure**: If any agent shows `local:`, phase FAILS immediately.

---

## Context Tracking Validation (Critical)

**In Every Phase**: Verify context grows

When agent responds to messages:
- [ ] Context % increases (not 0%)
- [ ] Progress bar fills
- [ ] Color changes: Green → Yellow → Orange → Red
- [ ] Multiple agents have independent context

**If Stuck at 0%**: Document as critical bug, continues to next phase (for now).

---

## Phase Dependencies

```
Phase 0 (Setup)
    ↓
Phase 1 (Authentication)
    ↓
Phase 2 (Agent Creation) ← GITHUB TEMPLATES REQUIRED
    ↓
Phase 3 (Context Validation) ← CRITICAL BUG CHECK
    ↓
Phase 4 (State Persistence)
    ↓
Phase 5 (Agent Collaboration)
    ↓
Phase 7 (Scheduling)
    ↓
Phase 8 (Execution Queue)
    ↓
Phase 9 (File Browser)
    ↓
Phase 10 (Error Handling)
    ↓
Phase 11 (Multi-Agent Dashboard)
    ↓
Phase 12 (Cleanup)

Independent Phases (can run after Phase 1):
    Phase 1 → Phase 13 (System Settings)
    Phase 1 → Phase 14 (OpenTelemetry)
    Phase 1 + Phase 14 → Phase 15 (System Agent)
    Phase 1 → Phase 24 (Credential Management)

Gap Analysis Phases (Phase 19-28):
    Phase 0 + Fresh DB → Phase 19 (First-Time Setup)
    Phase 2 + Phase 7 → Phase 20 (Live Execution Streaming)
    Phase 2 → Phase 21 (Session Management)
    Phase 2 → Phase 22 (Logs & Telemetry)
    Phase 2 → Phase 23 (Agent Configuration)
    Phase 1 + Phase 2 → Phase 25 (Agent Sharing)
    Phase 2 + Phase 5 → Phase 26 (Shared Folders)
    Phase 1 + Phase 2 → Phase 27 (Public Access)
    Phase 2 → Phase 28 (Agent Dashboard)
```

Each phase assumes **all previous phases PASSED**.
Phases 13-15 and 19-28 are independent features that can run after their prerequisites.

---

## Running a Single Phase (Advanced)

If testing a specific feature, prerequisites must be manually verified:

**Example: Test scheduling (Phase 7)**

Prerequisite Checklist:
- [ ] Services running (Phase 0)
- [ ] Logged in (Phase 1)
- [ ] All 3 agents created from GitHub (Phase 2)
- [ ] Context tracking working (Phase 3) - or bug documented
- [ ] State persistence working (Phase 4)
- [ ] Agent collaboration working (Phase 5)

Only after all above: can proceed to Phase 7

---

## Results Aggregation

After all phases complete:

```markdown
# Full Test Run Results

**Date**: 2025-12-09
**Duration**: 2:45 (2 hours 45 minutes)
**Phases Executed**: 0-12 (13 total)
**Environment**: Local (localhost + localhost:8000)

## Summary
- Phases Passed: 10
- Phases Failed: 1 (Phase 3 - Context Bug)
- Phases Skipped: 2 (Time constraint)

## Issues Found
1. Context Progress Bar Stuck at 0% (CRITICAL)
2. Task Indicator Stuck at "—" (HIGH)
3. UI Tab Switching Broken (MEDIUM)

## Recommendations
1. Fix context calculation bug (URGENT)
2. Investigate task indicator
3. Profile UI refresh rate

## Next Steps
- Create bug tickets for critical issues
- Re-run testing after fixes
- Complete remaining phases (6-12)
```

---

## Phase Files Location

All phase files in: `docs/testing/phases/`

```
docs/testing/phases/
├── INDEX.md (this file)
├── README.md
├── PHASE_00_SETUP.md
├── PHASE_01_AUTHENTICATION.md
├── PHASE_02_AGENT_CREATION.md
├── PHASE_03_CONTEXT_VALIDATION.md
├── PHASE_04_STATE_PERSISTENCE.md
├── PHASE_05_AGENT_COLLABORATION.md
├── PHASE_07_SCHEDULING.md
├── PHASE_08_EXECUTION_QUEUE.md
├── PHASE_09_FILE_BROWSER.md
├── PHASE_10_ERROR_HANDLING.md
├── PHASE_11_MULTI_AGENT_DASHBOARD.md
├── PHASE_12_CLEANUP.md
├── PHASE_13_SETTINGS.md
├── PHASE_14_OPENTELEMETRY.md
├── PHASE_15_SYSTEM_AGENT.md
├── PHASE_16_WEB_TERMINAL.md
├── PHASE_17_EMAIL_AUTHENTICATION.md
├── PHASE_18_GITHUB_INITIALIZATION.md
├── PHASE_19_FIRST_TIME_SETUP.md       (NEW - Gap Analysis)
├── PHASE_20_LIVE_EXECUTION_STREAMING.md (NEW - Gap Analysis)
├── PHASE_21_SESSION_MANAGEMENT.md     (NEW - Gap Analysis)
├── PHASE_22_LOGS_TELEMETRY.md         (NEW - Gap Analysis)
├── PHASE_23_AGENT_CONFIGURATION.md    (NEW - Gap Analysis)
├── PHASE_24_CREDENTIAL_MANAGEMENT.md  (NEW - Gap Analysis)
├── PHASE_25_AGENT_SHARING.md          (NEW - Gap Analysis)
├── PHASE_26_SHARED_FOLDERS.md         (NEW - Gap Analysis)
├── PHASE_27_PUBLIC_ACCESS.md          (NEW - Gap Analysis)
└── PHASE_28_AGENT_DASHBOARD.md        (NEW - Gap Analysis)
```

---

## Creating New Phases

When adding phases 6-12, follow template:

```markdown
# Phase X: Feature Name

> **Purpose**: What this tests
> **Duration**: Estimated time
> **Assumes**: Phase X-1 PASSED
> **Output**: What should be verified

## Prerequisites
- ✅ List items from previous phases

## Test Steps
- Step 1: Description
- Step 2: Description
...

## Success Criteria
Phase X is PASSED when:
- ✅ Criterion 1
- ✅ Criterion 2
...

## Next Phase
Phase X+1: Name
```

---

## Version History

| Date | Changes |
|------|---------|
| 2026-01-14 | **Gap Analysis Implementation**: Added 10 new phases (19-28) to address coverage gaps |
| 2026-01-14 | Added Phase 19: First-Time Setup (AUTH-001, AUTH-002) |
| 2026-01-14 | Added Phase 20: Live Execution Streaming (EXEC-009 to EXEC-013) - **P0 Critical** |
| 2026-01-14 | Added Phase 21: Session Management (EXEC-018 to EXEC-021) |
| 2026-01-14 | Added Phase 22: Logs & Telemetry (OBS-001 to OBS-010) |
| 2026-01-14 | Added Phase 23: Agent Configuration (CFG-001 to CFG-008) |
| 2026-01-14 | Added Phase 24: Credential Management (CRED-001 to CRED-013) - **P0 Critical** |
| 2026-01-14 | Added Phase 25: Agent Sharing (SHARE-001 to SHARE-004) |
| 2026-01-14 | Added Phase 26: Shared Folders (FOLDER-001 to FOLDER-004) |
| 2026-01-14 | Added Phase 27: Public Access (PUB-001 to PUB-007) - **P0 Critical** |
| 2026-01-14 | Added Phase 28: Agent Dashboard (DASH-001 to DASH-003) |
| 2025-12-26 | Added Phase 18: GitHub Repository Initialization |
| 2025-12-26 | Added Phase 17: Email-Based Authentication (Req 12.4) |
| 2025-12-26 | Added Phase 16: Web Terminal Testing (Req 11.5) |
| 2025-12-26 | Updated Phase 13: Added Email Whitelist + Per-Agent API Key (Req 11.7) |
| 2025-12-26 | Updated Phases 3, 4: Chat tab replaced by Terminal tab |
| 2025-12-26 | Updated Phase 1: Added email auth mode documentation |
| 2025-12-26 | Updated Phase 15: Added Web Terminal testing for System Agent |
| 2025-12-21 | Added Phase 14: OpenTelemetry Integration (Req 10.8) |
| 2025-12-21 | Added Phase 15: System Agent & Ops (Req 11.1, 11.2) |
| 2025-12-14 | Added Phase 13: System Settings for Trinity Prompt (Req 10.6) |
| 2025-12-10 | Added Agent Permissions testing (Req 9.10) to Phase 2 and Phase 5 |
| 2025-12-09 | Created modular phase structure (Phases 0-5 complete, 6-12 TBD) |
| 2025-12-09 | Added context validation as Phase 3 (CRITICAL BUG tracking) |
| 2025-12-09 | Added GitHub template requirement validation |
| 2025-12-09 | Split from monolithic UI_INTEGRATION_TEST.md into phases |

---

## Quick Start

```bash
# Run all phases (automated)
cd /path/to/trinity
python3 docs/testing/run_test_phases.py --all

# Or run manually
# 1. Read PHASE_00_SETUP.md
# 2. Follow instructions
# 3. When PASSED, read PHASE_01_AUTHENTICATION.md
# ... (repeat for each phase)
```

---

**All Phases Ready**: 0, 1, 2, 3, 4, 5, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28 (28 total)
**Last Updated**: 2026-01-14
**Gap Analysis Coverage**: Increased from 41% to 90%+ with new phases
