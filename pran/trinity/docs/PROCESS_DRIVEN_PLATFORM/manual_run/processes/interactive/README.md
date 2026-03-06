# Interactive Test Scenarios

These scenarios are designed for **live testing with a human approver**.

## Available Scenarios

| ID | Name | Complexity | Approvals | Description |
|----|------|------------|-----------|-------------|
| I1 | Approval Routes | Medium | 1 | Approval decision routes to publish/revise paths |
| I2 | Multi-Stage Approval | High | 2 | Sequential Manager → Director approval chain |
| I3 | Complex Workflow | High | 0-1 | Gateway routes high scores to approval, low to archive |
| I4 | Parallel Work + Approval | High | 1 | 3 parallel agents → combine → executive review |

## How to Run

### Via API
```bash
# Get token
TOKEN=$(curl -s -X POST 'http://localhost:8000/token' \
  -d 'username=admin&password=xcyqG7uQxKaH4fR6' | jq -r '.access_token')

# Create and publish process
PROCESS_ID=$(curl -s -X POST 'http://localhost:8000/api/processes' \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{\"yaml_content\": \"$(cat i1-approval-routes.yaml | sed 's/"/\\"/g' | tr '\n' ' ')\"}" | jq -r '.id')

curl -s -X POST "http://localhost:8000/api/processes/$PROCESS_ID/publish" \
  -H "Authorization: Bearer $TOKEN"

# Start execution
EXEC_ID=$(curl -s -X POST "http://localhost:8000/api/executions/processes/$PROCESS_ID/execute" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"input": {}}' | jq -r '.id')

echo "Open: http://localhost:5173/executions/$EXEC_ID"
```

## Expected Behaviors

### I1 - Approval Routes
- **APPROVE**: `publish-content` runs → `notify-complete`
- **REJECT**: `revise-content` runs → `notify-complete`

### I2 - Multi-Stage Approval
- **Manager APPROVE** → Director review appears
- **Director APPROVE** → `project-approved` runs
- **Manager REJECT** → `manager-rejected` runs, skips Director
- **Director REJECT** → `director-rejected` runs

### I3 - Complex Workflow
- Score ≥ 70: Goes to `quality-review` approval
- Score < 70: Goes straight to `auto-archive`
- If approved: `publish-high-quality`
- If rejected: `decline-high-quality`

### I4 - Parallel Work + Approval
- 3 agents run in parallel after kickoff
- All complete → `combine-outputs`
- Executive review
- APPROVE → `publish-report`
- REJECT → `archive-draft`

## Test Results Log

| Date | Scenario | Tester | Decision | Path Taken | Status |
|------|----------|--------|----------|------------|--------|
| | | | | | |
