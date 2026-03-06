# Phase 28: Agent Dashboard

> **Purpose**: Validate agent-defined dashboard widget system via dashboard.yaml
> **Duration**: ~15 minutes
> **Assumes**: Phase 2 PASSED (agent running), dashboard.yaml in agent workspace
> **Output**: Widget rendering and auto-refresh verified

---

## Background

**Agent Dashboard** (DASH-001 to DASH-003):
- Agents define custom dashboards in `dashboard.yaml`
- 11 widget types: metric, status, progress, text, markdown, table, list, link, image, divider, spacer
- Auto-refresh configurable per widget or globally
- Dashboard tab replaces generic Metrics tab

**User Stories**:
- DASH-001: See agent-defined dashboards
- DASH-002: Define widgets in dashboard.yaml
- DASH-003: Auto-refresh dashboards

---

## Prerequisites

- [ ] Phase 2 PASSED (agent running)
- [ ] Agent has `dashboard.yaml` file OR ability to create one
- [ ] Access to agent Terminal for file creation

---

## Test: Create Dashboard Configuration

### Step 1: Create dashboard.yaml via Terminal
**Action**:
- Navigate to agent detail page
- Open Terminal tab
- Send message: "Create a file at ~/dashboard.yaml with comprehensive widget examples"

**Or create manually**:
- Create file with this content:

```yaml
title: "Agent Status Dashboard"
description: "Real-time metrics and status"
config:
  refresh: 30  # seconds

widgets:
  - type: metric
    title: "Total Tasks"
    value: "42"
    unit: "tasks"
    trend: "up"
    icon: "chart"

  - type: status
    title: "Agent Health"
    status: "healthy"
    message: "All systems operational"

  - type: progress
    title: "Daily Progress"
    value: 75
    max: 100
    label: "75% complete"

  - type: text
    title: "Last Updated"
    content: "2026-01-14 10:30:00"

  - type: markdown
    content: |
      ## Quick Stats
      - **Uptime**: 99.9%
      - **Response Time**: 1.2s
      - **Active Sessions**: 5

  - type: table
    title: "Recent Activity"
    headers: ["Time", "Action", "Status"]
    rows:
      - ["10:30", "Task completed", "Success"]
      - ["10:25", "API call", "Success"]
      - ["10:20", "Schedule triggered", "Success"]

  - type: list
    title: "Pending Items"
    items:
      - "Review pull request"
      - "Update documentation"
      - "Run test suite"

  - type: link
    title: "Documentation"
    url: "https://docs.example.com"
    label: "View Docs"

  - type: divider

  - type: image
    title: "Architecture Diagram"
    url: "/api/agents/{name}/files/workspace/diagram.png"
    alt: "System architecture"

  - type: spacer
    height: 20
```

**Verify**:
```bash
docker exec agent-{name} cat /home/developer/dashboard.yaml
```

---

### Step 2: Verify File Created
**Action**:
- Check file exists in agent workspace

**Expected**:
- [ ] File created at ~/dashboard.yaml or ~/workspace/dashboard.yaml
- [ ] YAML syntax valid
- [ ] All widget types included

---

## Test: View Dashboard Tab

### Step 3: Navigate to Dashboard Tab
**Action**:
- In agent detail page
- Click "Dashboard" tab

**Expected**:
- [ ] Dashboard tab loads
- [ ] Title displayed: "Agent Status Dashboard"
- [ ] Description shown
- [ ] Widgets rendered

**Verify**:
- [ ] No YAML parse errors
- [ ] Layout renders correctly

---

### Step 4: Verify Widget Types

**Check each widget renders:**

**Metric Widget**:
- [ ] Title: "Total Tasks"
- [ ] Value: "42"
- [ ] Unit displayed
- [ ] Trend indicator (up arrow)

**Status Widget**:
- [ ] Title: "Agent Health"
- [ ] Status: "healthy" with green indicator
- [ ] Message text displayed

**Progress Widget**:
- [ ] Title: "Daily Progress"
- [ ] Progress bar at 75%
- [ ] Label: "75% complete"

**Text Widget**:
- [ ] Title: "Last Updated"
- [ ] Content displayed as plain text

**Markdown Widget**:
- [ ] Markdown rendered (headers, bold, lists)
- [ ] Proper formatting

**Table Widget**:
- [ ] Title: "Recent Activity"
- [ ] Headers displayed
- [ ] 3 rows of data
- [ ] Proper table formatting

**List Widget**:
- [ ] Title: "Pending Items"
- [ ] 3 bullet items
- [ ] List formatting

**Link Widget**:
- [ ] Title: "Documentation"
- [ ] Clickable link
- [ ] Opens in new tab

**Divider Widget**:
- [ ] Horizontal line rendered
- [ ] Visual separation

**Image Widget** (if image exists):
- [ ] Title: "Architecture Diagram"
- [ ] Image displayed or placeholder

**Spacer Widget**:
- [ ] Vertical space added
- [ ] Height: 20px

---

## Test: Widget Validation

### Step 5: Test Invalid YAML
**Action**:
- Create invalid dashboard.yaml:
```yaml
widgets:
  - type: invalid_type
    title: "Bad Widget"
```

**Expected**:
- [ ] Dashboard shows error message
- [ ] "Unknown widget type: invalid_type"
- [ ] Graceful degradation

---

### Step 6: Test Missing Required Fields
**Action**:
- Create widget missing required fields:
```yaml
widgets:
  - type: metric
    # missing: value
```

**Expected**:
- [ ] Validation error shown
- [ ] "Required field 'value' missing"
- [ ] Widget skipped or placeholder shown

---

## Test: Auto-Refresh

### Step 7: Check Auto-Refresh
**Action**:
- Watch the dashboard for 30+ seconds
- Or check config.refresh value

**Expected**:
- [ ] Dashboard refreshes automatically
- [ ] Data updated without manual refresh
- [ ] Refresh interval: 30 seconds (as configured)

**Verify**:
- [ ] Network requests visible in DevTools
- [ ] Timestamps update if dynamic

---

### Step 8: Test Custom Refresh Rate
**Action**:
- Update dashboard.yaml refresh to 10 seconds
- Reload page

**Expected**:
- [ ] Dashboard refreshes every 10 seconds
- [ ] Minimum refresh: 5 seconds (enforced)

---

## Test: Dynamic Dashboard Data

### Step 9: Update Widget Values
**Action**:
- Via Terminal, update dashboard.yaml:
- Change metric value from "42" to "50"
- Wait for auto-refresh

**Expected**:
- [ ] After refresh, value shows "50"
- [ ] Changes reflected automatically

---

### Step 10: Agent-Generated Dashboard
**Action**:
- Send message: "Update the dashboard to show current date and a random number"

**Expected**:
- [ ] Agent modifies dashboard.yaml
- [ ] Dashboard reflects agent's changes
- [ ] Dynamic values possible

---

## Test: Dashboard Without Configuration

### Step 11: Check Default Behavior
**Action**:
- Use agent without dashboard.yaml
- Click Dashboard tab

**Expected**:
- [ ] Empty state displayed
- [ ] "No dashboard configured"
- [ ] Instructions to create dashboard.yaml

---

## Test: Widget Styling

### Step 12: Verify Visual Styling
**Action**:
- Review overall dashboard appearance

**Expected**:
- [ ] Consistent styling
- [ ] Dark mode support
- [ ] Mobile responsive
- [ ] Widget cards well-separated
- [ ] Icons render correctly

---

## Critical Validations

### YAML Parsing
**Validation**: Backend correctly parses dashboard.yaml

```bash
curl -H "Authorization: Bearer {token}" \
  http://localhost:8000/api/agent-dashboard/{name}
```

Expected: Widget definitions returned as JSON

### Widget Type Coverage
**Validation**: All 11 widget types supported

- [ ] metric
- [ ] status
- [ ] progress
- [ ] text
- [ ] markdown
- [ ] table
- [ ] list
- [ ] link
- [ ] image
- [ ] divider
- [ ] spacer

### Error Handling
**Validation**: Graceful handling of:
- [ ] Missing dashboard.yaml
- [ ] Invalid YAML syntax
- [ ] Unknown widget types
- [ ] Missing required fields

---

## Success Criteria

Phase 28 is **PASSED** when:
- [ ] Dashboard tab loads for agents with dashboard.yaml
- [ ] All 11 widget types render correctly
- [ ] Metric widget shows value, unit, trend
- [ ] Status widget shows health indicator
- [ ] Progress widget shows bar and percentage
- [ ] Text widget displays content
- [ ] Markdown widget renders formatting
- [ ] Table widget displays rows and headers
- [ ] List widget shows bullet items
- [ ] Link widget is clickable
- [ ] Divider widget separates content
- [ ] Image widget displays images
- [ ] Spacer widget adds vertical space
- [ ] Auto-refresh works at configured interval
- [ ] Dashboard updates reflect file changes
- [ ] Invalid YAML shows error gracefully
- [ ] Agents without dashboard.yaml show empty state

---

## Troubleshooting

**Dashboard tab not visible**:
- Feature may be disabled
- Check feature flag
- Verify tab configuration in AgentDetail

**YAML parse errors**:
- Check YAML syntax (indentation, quotes)
- Validate with online YAML validator
- Check backend logs for parse errors

**Widgets not rendering**:
- Check widget type spelling
- Verify required fields present
- Check browser console for errors

**Auto-refresh not working**:
- Check config.refresh value
- Minimum is 5 seconds
- Verify API calls in Network tab

**Images not loading**:
- Check image path is accessible
- Verify agent has the image file
- Check CORS if external URL

**Table not displaying**:
- Verify headers array
- Verify rows array of arrays
- Check data types match

---

## Next Phase

Once Phase 28 is **PASSED**, the gap analysis phases are complete.

Consider running:
- **Full Test Suite**: Phases 0-28
- **Cleanup**: Phase 12

---

**Status**: Ready for Testing
**Last Updated**: 2026-01-14
**User Stories**: DASH-001, DASH-002, DASH-003
