# Refactor Audit Report

**Generated**: 2026-02-22 17:41
**Scope**: src/backend/
**Tool**: /refactor-audit

---

## Summary

| Severity | Count | Description |
|----------|-------|-------------|
| Critical | 9 | Must fix - blocks AI maintenance |
| High | 27 | Strongly recommended |
| Medium | 112 | Recommended |
| Low | 0 | Nice to have |

**Total issues**: 148
**AI-Refactorable**: ~90% - Most issues are function extraction and file splitting

---

## Critical Issues (P0)

These files/functions exceed thresholds that block effective AI maintenance (>1000 lines or >200 line functions).

### src/backend/database.py
| Issue | Metric | Line | Recommendation |
|-------|--------|------|----------------|
| File too large | 1326 lines | 1 | Split into modules: migrations.py, queries.py, wrappers.py |
| Function too long | 528 lines | 469 | `init_database()` - Extract migration logic into separate functions |

### src/backend/routers/chat.py
| Issue | Metric | Line | Recommendation |
|-------|--------|------|----------------|
| File too large | 1222 lines | 1 | Split into: chat_core.py, task_execution.py, session_management.py |
| Function too long | 322 lines | 108 | `chat_with_agent()` - Extract parsing, streaming, persistence logic |
| Function too long | 360 lines | 546 | `execute_parallel_task()` - Extract async handling, persistence |

### src/backend/routers/system_agent.py
| Issue | Metric | Line | Recommendation |
|-------|--------|------|----------------|
| Function too long | 265 lines | 264 | `system_agent_terminal()` - Extract PTY handling, message processing |

### src/backend/services/agent_service/crud.py
| Issue | Metric | Line | Recommendation |
|-------|--------|------|----------------|
| Function too long | 455 lines | 48 | `create_agent_internal()` - Extract template processing, container creation, volume mounting |

### src/backend/services/agent_service/deploy.py
| Issue | Metric | Line | Recommendation |
|-------|--------|------|----------------|
| Function too long | 259 lines | 183 | `deploy_local_agent_logic()` - Extract tar validation, git setup, credential injection |

### src/backend/services/agent_service/terminal.py
| Issue | Metric | Line | Recommendation |
|-------|--------|------|----------------|
| Function too long | 262 lines | 57 | `handle_terminal_session()` - Extract PTY setup, message routing, cleanup |

---

## High Priority Issues (P1)

### Large Files (800-1000 lines)

| File | Lines | Recommendation |
|------|-------|----------------|
| routers/agents.py | 952 | Split: agent_crud.py, agent_operations.py, agent_resources.py |
| services/process_engine/engine/execution_engine.py | 826 | Split: state_machine.py, step_executor.py, compensation.py |

### Long Functions (100-200 lines)

| File | Function | Lines | Line # |
|------|----------|-------|--------|
| routers/agents.py | `create_ssh_access` | 160 | 1121 |
| routers/chat.py | `_execute_task_background` | 109 | 433 |
| routers/git.py | `initialize_github_sync` | 136 | 252 |
| routers/ops.py | `restart_fleet` | 101 | 227 |
| routers/ops.py | `get_ops_costs` | 142 | 741 |
| routers/public.py | `public_chat` | 155 | 215 |
| routers/systems.py | `deploy_system` | 187 | 34 |
| routers/templates.py | `get_template_env_template` | 108 | 63 |
| services/agent_service/lifecycle.py | `recreate_container_with_updated_config` | 144 | 277 |
| services/git_service.py | `initialize_git_in_container` | 141 | 262 |
| services/process_engine/engine/execution_engine.py | `_execute_step` | 157 | 386 |
| services/process_engine/engine/execution_engine.py | `_execute_compensation` | 101 | 881 |
| services/process_engine/engine/handlers/sub_process.py | `execute` | 112 | 85 |
| services/process_engine/services/analytics.py | `get_step_performance` | 100 | 346 |
| services/process_engine/services/recovery.py | `_recover_execution` | 124 | 254 |
| services/system_agent_service.py | `_create_system_agent` | 151 | 120 |
| services/system_service.py | `validate_manifest` | 101 | 93 |
| services/system_service.py | `export_manifest` | 148 | 565 |

### Too Many Parameters (10+)

| File | Function | Params | Line # |
|------|----------|--------|--------|
| database.py | `create_schedule_execution` | 10 | 1332 |
| database.py | `update_execution_status` | 11 | 1353 |
| database.py | `add_chat_message` | 12 | 1424 |
| db/chat.py | `add_chat_message` | 12 | 92 |
| db/schedules.py | `create_schedule_execution` | 10 | 497 |
| db/schedules.py | `update_execution_status` | 11 | 557 |
| services/process_engine/services/templates.py | `create_template` | 10 | 375 |

---

## Medium Priority Issues (P2)

### Large Files (500-800 lines)

| File | Lines |
|------|-------|
| db/schedules.py | 716 |
| routers/executions.py | 662 |
| routers/ops.py | 780 |
| routers/processes.py | 734 |
| services/process_engine/domain/aggregates.py | 523 |
| services/process_engine/services/validator.py | 609 |

### Functions 50-100 Lines (Top 20)

| File | Function | Lines |
|------|----------|-------|
| routers/ops.py | `get_fleet_health` | 98 |
| routers/settings.py | `test_github_pat` | 96 |
| routers/system_agent.py | `reinitialize_system_agent` | 97 |
| services/log_archive_service.py | `archive_old_logs` | 98 |
| services/process_engine/domain/entities.py | `from_dict` | 99 |
| routers/ops.py | `stop_fleet` | 89 |
| services/agent_service/dashboard.py | `get_agent_dashboard_logic` | 88 |
| routers/observability.py | `parse_prometheus_metrics` | 87 |
| services/github_service.py | `create_repository` | 87 |
| services/process_engine/services/analytics.py | `get_trend_data` | 87 |
| routers/chat.py | `terminate_agent_execution` | 84 |
| services/process_engine/engine/handlers/human_approval.py | `execute` | 85 |
| services/process_engine/services/validator.py | `_validate_step_roles` | 85 |

---

## Hotspots (Files with Multiple Issues)

Files appearing multiple times - prioritize these:

| File | Issues | Severity Score |
|------|--------|----------------|
| database.py | 7 | 18 (2 critical + 4 high + 1 medium) |
| routers/chat.py | 8 | 17 (3 critical + 1 high + 4 medium) |
| services/process_engine/engine/execution_engine.py | 7 | 15 (2 high + 5 medium) |
| routers/ops.py | 6 | 11 (1 high + 5 medium) |
| db/schedules.py | 8 | 10 (2 high + 6 medium) |
| services/process_engine/services/validator.py | 5 | 7 (5 medium) |
| routers/agents.py | 4 | 7 (1 high + 3 medium) |

---

## Recommendations

### Quick Wins (Low Risk, High Impact)

1. **Extract `database.py` migrations** - Move `init_database()` migrations to `db/migrations.py` with individual migration functions
2. **Split `chat.py` endpoints** - Separate `/chat` and `/task` into `routers/chat_core.py` and `routers/task_execution.py`
3. **Create parameter dataclasses** - Convert 10+ parameter functions to use dataclasses:
   ```python
   @dataclass
   class ExecutionConfig:
       agent_name: str
       schedule_id: str
       ...
   ```

### Requires Tests First

1. **`create_agent_internal()` refactor** - 455 lines, critical path - needs comprehensive test coverage
2. **`chat_with_agent()` refactor** - 322 lines, user-facing - needs integration tests
3. **`execute_parallel_task()` refactor** - 360 lines, async code - needs async test coverage

### Architectural Changes

1. **Process Engine modularization** - The process engine has grown to 826+ lines. Consider:
   - Extract state machine to `state_machine.py`
   - Extract step executor to `step_executor.py`
   - Extract compensation logic to `compensation.py`

2. **Router consolidation** - Several routers exceed 500 lines:
   - `ops.py` (780 lines) → Split by operation type
   - `processes.py` (734 lines) → Split CRUD from execution

---

## Next Steps

1. **Priority 1**: Refactor `database.py` (critical hotspot, 7 issues)
2. **Priority 2**: Split `routers/chat.py` (3 critical issues)
3. **Priority 3**: Refactor `create_agent_internal()` in crud.py
4. **Priority 4**: Create dataclasses for high-parameter functions

Run `/refactor-audit backend --quick` after changes to verify improvements.

---

## Appendix: Analysis Tools

Analysis performed using custom script with fallback to manual inspection.
- radon: Not installed (would provide cyclomatic complexity)
- vulture: Not installed (would detect dead code)

To enhance analysis:
```bash
pipx install radon vulture
```
