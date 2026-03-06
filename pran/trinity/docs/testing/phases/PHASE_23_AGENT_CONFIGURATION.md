# Phase 23: Agent Configuration

> **Purpose**: Validate resource limits, model selection, capabilities mode, and autonomy toggle
> **Duration**: ~20 minutes
> **Assumes**: Phase 2 PASSED (agents running)
> **Output**: All agent configuration options verified

---

## Background

**Agent Configuration** (CFG-001 to CFG-008):
- Per-agent memory and CPU limits
- LLM model selection (Claude sonnet/opus/haiku, Gemini variants)
- Full capabilities mode for system access
- Autonomy mode toggle for scheduled execution

**User Stories**:
- CFG-001: View agent resource limits
- CFG-002: Set memory/CPU limits
- CFG-003: Agents restart on limit change
- CFG-004: Enable full capabilities mode
- CFG-005: View current model
- CFG-006: Change LLM model
- CFG-007: Enable/disable autonomy mode
- CFG-008: See autonomy status with counts

---

## Prerequisites

- [ ] Phase 2 PASSED (agents created and running)
- [ ] Admin user logged in (for some settings)
- [ ] At least one agent available for testing

---

## Test: Resource Limits

### Step 1: Open Resource Settings
**Action**:
- Navigate to agent detail page
- Look for gear icon or settings button in header
- Click to open Resource Limits modal

**Expected**:
- [ ] Modal/dialog opens
- [ ] Current memory limit displayed
- [ ] Current CPU limit displayed
- [ ] Input fields for modification

**Verify**:
- [ ] Values match container configuration
- [ ] Fields are editable

---

### Step 2: View Current Limits
**Action**:
- Note the current values
- Default: Memory 2G, CPU 2.0 (or similar)

**Expected**:
- [ ] Memory shown in GB or MB
- [ ] CPU shown as core count or percentage
- [ ] Values reflect actual container limits

**Verify via Docker**:
```bash
docker inspect agent-{name} --format='{{.HostConfig.Memory}} {{.HostConfig.NanoCpus}}'
```

---

### Step 3: Change Memory Limit
**Action**:
- Change memory to different value (e.g., 4G)
- Click Save or Apply
- Confirm if prompted

**Expected**:
- [ ] Confirmation dialog if agent running
- [ ] Warning: "Agent will restart to apply changes"
- [ ] Save button becomes active

**Verify**:
- [ ] Change acknowledged
- [ ] Database updated

---

### Step 4: Verify Restart on Limit Change
**Action**:
- Confirm the restart
- Watch agent status

**Expected**:
- [ ] Agent stops briefly
- [ ] Container recreated with new limits
- [ ] Agent restarts automatically
- [ ] Status returns to "Running"

**Verify**:
```bash
docker inspect agent-{name} --format='{{.HostConfig.Memory}}'
# Should show new limit
```

---

### Step 5: Change CPU Limit
**Action**:
- Open Resource Settings again
- Change CPU limit (e.g., 4.0 cores)
- Save and confirm restart

**Expected**:
- [ ] Same flow as memory change
- [ ] Agent restarts
- [ ] New CPU limit applied

**Verify**:
```bash
docker inspect agent-{name} --format='{{.HostConfig.NanoCpus}}'
# Should show new limit (in nanocpus)
```

---

## Test: Full Capabilities Mode

### Step 6: Check Current Capabilities
**Action**:
- Look for "Full Capabilities" toggle in settings
- Or check Agent Info tab for current mode

**Expected**:
- [ ] Toggle or checkbox visible
- [ ] Current state shown (enabled/disabled)
- [ ] Default: Disabled (secure mode)

---

### Step 7: Enable Full Capabilities
**Action**:
- Toggle Full Capabilities ON
- Save changes
- Confirm if prompted

**Expected**:
- [ ] Warning displayed about security implications
- [ ] "Full capabilities allows apt-get and system access"
- [ ] Agent will restart

**Verify**:
- [ ] Container recreated with capabilities
- [ ] CAP_ADD includes necessary caps

```bash
docker inspect agent-{name} --format='{{.HostConfig.CapAdd}}'
```

---

### Step 8: Test Capabilities Work
**Action**:
- In Terminal, send: "Run apt-get update"
- Wait for response

**Expected with Full Capabilities**:
- [ ] apt-get command runs
- [ ] Package lists updated
- [ ] No permission errors

**Expected without Full Capabilities**:
- [ ] Permission denied or command blocked

---

### Step 9: Disable Full Capabilities
**Action**:
- Toggle Full Capabilities OFF
- Save and restart agent

**Expected**:
- [ ] Container returns to secure mode
- [ ] apt-get commands fail again
- [ ] Security settings restored

---

## Test: Model Selection

### Step 10: View Current Model
**Action**:
- Look for Model selector in agent settings
- Or check Info tab for current model

**Expected**:
- [ ] Current model displayed (e.g., "claude-sonnet-4-20250514")
- [ ] Dropdown or selection available
- [ ] Available models listed

**Available Claude Models**:
- claude-sonnet-4-20250514 (default)
- claude-opus-4-20250514
- claude-haiku-3-5

**Available Gemini Models** (if runtime is gemini):
- gemini-2.0-flash
- gemini-1.5-pro

---

### Step 11: Change Model
**Action**:
- Select different model (e.g., claude-opus)
- Save changes

**Expected**:
- [ ] Model selection saved
- [ ] No restart required (applies to next message)
- [ ] Success confirmation

**Verify**:
- [ ] Check database or API for model setting
- [ ] Next message uses new model

---

### Step 12: Verify Model in Use
**Action**:
- Send message: "What model are you?"
- Wait for response

**Expected**:
- [ ] Response identifies as selected model
- [ ] Cost may differ between models
- [ ] Response style may vary (opus more verbose)

---

### Step 13: Test Model Validation
**Action**:
- Try to select invalid model for runtime
- (e.g., Gemini model for Claude runtime)

**Expected**:
- [ ] Validation error
- [ ] "Model not available for this runtime"
- [ ] Selection rejected

---

## Test: Autonomy Mode

### Step 14: Check Autonomy Status in Dashboard
**Action**:
- Navigate to Dashboard (http://localhost/)
- Find agent tile
- Look for autonomy indicator

**Expected**:
- [ ] "AUTO" badge if autonomy enabled
- [ ] No badge if disabled
- [ ] Toggle switch visible

---

### Step 15: Toggle Autonomy from Dashboard
**Action**:
- Click autonomy toggle on agent tile
- Wait for response

**Expected**:
- [ ] Toggle switches state
- [ ] API call made (PUT /api/agents/{name}/autonomy)
- [ ] Badge updates accordingly
- [ ] All schedules enabled/disabled

**Verify**:
- [ ] Toggle reflects new state
- [ ] Toast notification confirms change

---

### Step 16: Check Autonomy in Agent Detail
**Action**:
- Navigate to agent detail page
- Look for autonomy toggle in header

**Expected**:
- [ ] Toggle present in header
- [ ] State matches Dashboard toggle
- [ ] Schedule count shown (e.g., "3 schedules")

---

### Step 17: Toggle Autonomy from Agent Detail
**Action**:
- Click autonomy toggle in agent header
- Wait for response

**Expected**:
- [ ] Same behavior as Dashboard toggle
- [ ] State synchronized everywhere
- [ ] Schedules enabled/disabled

---

### Step 18: Check Autonomy in Agents Page
**Action**:
- Navigate to /agents
- Find agent card
- Look for autonomy toggle

**Expected**:
- [ ] Toggle present on agent cards
- [ ] State consistent with other views
- [ ] Can toggle from Agents page

---

### Step 19: Verify Schedule State
**Action**:
- Navigate to agent Schedules tab
- Check schedule enabled/disabled state

**Expected**:
- [ ] All schedules disabled when autonomy OFF
- [ ] All schedules enabled when autonomy ON
- [ ] Schedule toggle linked to autonomy

**Verify**:
- [ ] Schedules don't fire when autonomy OFF
- [ ] Schedules execute when autonomy ON

---

## Critical Validations

### Resource Limits Persistence
**Validation**: Limits survive restart

```bash
# Check database
sqlite3 ~/trinity-data/trinity.db "SELECT memory_limit, cpu_limit FROM agent_ownership WHERE agent_name='{name}'"
```

### Model Persistence
**Validation**: Model selection persists

- [ ] Change model
- [ ] Restart agent
- [ ] Model still selected

### Autonomy State
**Validation**: Autonomy state consistent

```bash
curl -H "Authorization: Bearer {token}" \
  http://localhost:8000/api/agents/{name}/autonomy
```

Expected:
```json
{
  "enabled": true,
  "enabled_schedules": 3,
  "total_schedules": 3
}
```

---

## Success Criteria

Phase 23 is **PASSED** when:
- [ ] Resource limits modal opens from gear icon
- [ ] Current memory/CPU limits displayed correctly
- [ ] Memory limit can be changed
- [ ] CPU limit can be changed
- [ ] Agent restarts when limits changed
- [ ] New limits applied to container
- [ ] Full capabilities toggle works
- [ ] apt-get works with full capabilities
- [ ] apt-get blocked without full capabilities
- [ ] Current model displayed
- [ ] Model can be changed
- [ ] Invalid model rejected
- [ ] Autonomy toggle works from Dashboard
- [ ] Autonomy toggle works from Agent Detail
- [ ] Autonomy toggle works from Agents page
- [ ] Autonomy state controls all schedules

---

## Troubleshooting

**Gear icon not visible**:
- May be owner-only feature
- Check user owns the agent
- Admin should see all settings

**Restart not happening**:
- Check backend logs for errors
- Verify Docker socket access
- Container may be in bad state

**Model change not taking effect**:
- Model applies to next message, not current session
- Check Claude Code respects model flag
- Verify model parameter passed correctly

**Autonomy toggle not working**:
- Check API endpoint exists
- Verify database has autonomy_enabled column
- Check for JavaScript errors

**Capabilities not applying**:
- Container must be recreated
- Check Docker security options
- Verify backend applies caps correctly

---

## Next Phase

Once Phase 23 is **PASSED**, proceed to:
- **Phase 24**: Credential Management

---

**Status**: Ready for Testing
**Last Updated**: 2026-01-14
**User Stories**: CFG-001 to CFG-008
