# Feature: Human Approval Gates

> Human-in-the-loop approval steps within process workflows with inbox UI, timeout handling, and decision tracking.

---

## Overview

Human Approval provides a mechanism for processes to pause and wait for human decisions. When an execution reaches a `human_approval` step, it pauses until an authorized user approves or rejects through the Approvals inbox.

**Key Capabilities:**
- Approval gates that pause execution
- Assignee-based authorization (or open to all if no assignees)
- Configurable timeout with expiration
- Approval inbox UI with status filtering
- Decision tracking (who, when, comments)
- **Template variable substitution** in `title` and `description` fields (`{{input.*}}`, `{{steps.*}}`)

---

## User Story

As a **process designer**, I want to **add human approval gates** to my workflows so that **critical decisions require human sign-off before proceeding**.

As a **reviewer**, I want to **see pending approvals in an inbox** so that **I can efficiently review and decide on requests**.

---

## Entry Points

| Entry Point | Location | Description |
|-------------|----------|-------------|
| **UI: Approvals Page** | NavBar -> Approvals -> `Approvals.vue` | Main inbox for reviewing approval requests |
| **UI: Execution Detail** | ProcessExecutionDetail.vue | Shows "Waiting for approval" status on paused step |
| **API: List Approvals** | `GET /api/approvals` | List all approval requests with optional filters |
| **API: Approve** | `POST /api/approvals/{id}/approve` | Approve a pending request |
| **API: Reject** | `POST /api/approvals/{id}/reject` | Reject a pending request |

---

## Architecture

```
+-----------------------------------------------------------------------------------+
|                              Frontend (Approvals.vue)                              |
|  +-----------------------------------------------------------------------------+  |
|  | - Filter by status (pending/approved/rejected)                              |  |
|  | - Stats cards (total, pending, approved, rejected)                          |  |
|  | - Table with approval requests                                              |  |
|  | - Approve button (green checkmark)                                          |  |
|  | - Reject button with required comment modal                                 |  |
|  +-----------------------------------------------------------------------------+  |
|                                     |                                             |
|                                     | POST /api/approvals/{id}/approve            |
|                                     v                                             |
+-----------------------------------------------------------------------------------+
|                              Backend (routers/approvals.py)                        |
|  +-----------------------------------------------------------------------------+  |
|  | list_approvals()          :62   - GET all requests with filters             |  |
|  | get_approval()            :92   - GET single request by ID                  |  |
|  | get_approval_by_step()    :104  - GET by execution_id + step_id             |  |
|  | approve()                 :116  - POST approve decision, resume execution   |  |
|  | reject()                  :168  - POST reject decision, resume execution    |  |
|  +-----------------------------------------------------------------------------+  |
|                                     |                                             |
|                                     | Updates ApprovalRequest, resumes engine     |
|                                     v                                             |
|  +-----------------------------------------------------------------------------+  |
|  | engine/handlers/human_approval.py                                           |  |
|  | +-------------------------------------------------------------------------+ |  |
|  | | ApprovalStore          :27-76  - In-memory singleton for requests       | |  |
|  | | HumanApprovalHandler   :79-213 - Creates requests, checks decisions     | |  |
|  | | _evaluate_template()   :106-126 - Template variable substitution        | |  |
|  | +-------------------------------------------------------------------------+ |  |
|  +-----------------------------------------------------------------------------+  |
|                                     |                                             |
|  +-----------------------------------------------------------------------------+  |
|  | domain/entities.py - ApprovalRequest :429-543                               |  |
|  | +-------------------------------------------------------------------------+ |  |
|  | | create()             :450-469  - Factory method with UUID               | |  |
|  | | approve()            :471-476  - Mark as approved                       | |  |
|  | | reject()             :478-483  - Mark as rejected                       | |  |
|  | | expire()             :485-488  - Mark as expired (timeout)              | |  |
|  | | is_pending()         :490-492  - Check if still pending                 | |  |
|  | | can_be_decided_by()  :494-499  - Authorization check                    | |  |
|  | +-------------------------------------------------------------------------+ |  |
|  +-----------------------------------------------------------------------------+  |
+-----------------------------------------------------------------------------------+
```

---

## Backend Layer

### API Endpoints (routers/approvals.py)

| Method | Path | Handler | Line | Description |
|--------|------|---------|------|-------------|
| GET | `/api/approvals` | `list_approvals()` | 62 | List requests with status/user filters |
| GET | `/api/approvals/{approval_id}` | `get_approval()` | 92 | Get single request details |
| GET | `/api/approvals/execution/{execution_id}/step/{step_id}` | `get_approval_by_step()` | 104 | Get by execution step |
| POST | `/api/approvals/{approval_id}/approve` | `approve()` | 116 | Approve and resume execution |
| POST | `/api/approvals/{approval_id}/reject` | `reject()` | 168 | Reject and resume execution |

### Request/Response Examples

**List Pending Approvals:**
```
GET /api/approvals?status=pending
```

```json
[
  {
    "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
    "execution_id": "exec_abc123def456",
    "step_id": "review",
    "title": "Approve Acme Corp for Series A?",
    "description": "Review intake results before proceeding.",
    "status": "pending",
    "assignees": ["deal-manager@example.com"],
    "created_at": "2026-01-23T10:00:00Z",
    "deadline": "2026-01-24T10:00:00Z"
  }
]
```

**Approve Request:**
```
POST /api/approvals/{id}/approve
Content-Type: application/json

{ "comment": "Approved - looks good" }
```

**Reject Request:**
```
POST /api/approvals/{id}/reject
Content-Type: application/json

{ "comment": "Needs more information on revenue projections" }
```

### Approval Handler (engine/handlers/human_approval.py)

**File**: `src/backend/services/process_engine/engine/handlers/human_approval.py`

| Component | Lines | Description |
|-----------|-------|-------------|
| `ApprovalStore` | 27-76 | In-memory singleton storing approval requests |
| `HumanApprovalHandler` | 79-213 | Step handler for `human_approval` type |
| `_evaluate_template()` | 106-126 | Template variable substitution |
| `execute()` | 128-213 | Main handler logic |

#### Template Variable Substitution

The handler evaluates template variables in `title` and `description` fields before creating the approval request:

```python
# human_approval.py:106-126

def _evaluate_template(self, template: str, context: StepContext) -> str:
    """
    Evaluate template variables in a string.

    Supports:
    - {{input.X}} - Process input data
    - {{steps.X.output}} - Step output
    - {{execution.id}} - Execution ID
    - {{process.name}} - Process name
    """
    if not template:
        return template

    eval_context = EvaluationContext(
        input_data=context.input_data,
        step_outputs=context.step_outputs,
        execution_id=str(context.execution.id),
        process_name=context.execution.process_name,
    )

    return self.expression_evaluator.evaluate(template, eval_context)
```

The handler calls `_evaluate_template()` on both fields at lines 187-188:

```python
# human_approval.py:187-198

# Evaluate template variables in title and description
evaluated_title = self._evaluate_template(config.title, context)
evaluated_description = self._evaluate_template(config.description, context) if config.description else None

# Create approval request with evaluated values
request = ApprovalRequest.create(
    execution_id=execution_id,
    step_id=step_id,
    title=evaluated_title,
    description=evaluated_description,
    assignees=config.assignees,
    deadline=deadline,
)
```

### Expression Evaluator (services/expression_evaluator.py)

**File**: `src/backend/services/process_engine/services/expression_evaluator.py`

The `ExpressionEvaluator` class handles template substitution using Jinja2-style `{{...}}` syntax.

| Component | Lines | Description |
|-----------|-------|-------------|
| `EvaluationContext` | 19-96 | Context dataclass with path resolution |
| `ExpressionEvaluator` | 99-250 | Main evaluator class |
| `EXPRESSION_PATTERN` | 126 | Regex: `\{\{([^}]+)\}\}` |
| `evaluate()` | 128-162 | Replace expressions in template string |
| `_value_to_string()` | 231-249 | Convert values (dict, list, etc.) to strings |

**Supported Template Variables:**

| Pattern | Description | Example |
|---------|-------------|---------|
| `{{input.X}}` | Process input data field | `{{input.company_name}}` |
| `{{steps.X.output}}` | Full step output | `{{steps.research.output}}` |
| `{{steps.X.output.Y}}` | Nested field in step output | `{{steps.research.output.summary}}` |
| `{{execution.id}}` | Execution ID | `exec_abc123...` |
| `{{process.name}}` | Process name | `due-diligence-workflow` |

**Behavior for missing variables:** Left unchanged (non-strict mode).

### Domain Model (domain/entities.py)

**File**: `src/backend/services/process_engine/domain/entities.py`

#### ApprovalRequest Entity (lines 429-543)

```python
@dataclass
class ApprovalRequest:
    id: str                          # UUID
    execution_id: str                # Parent execution
    step_id: str                     # Step within execution
    title: str                       # Display title (supports templates)
    description: str                 # Details (supports templates)
    assignees: list[str]             # Users who can approve (empty = anyone)
    status: ApprovalStatus           # pending, approved, rejected, expired
    deadline: Optional[datetime]     # When request expires
    created_at: datetime
    decided_at: Optional[datetime]
    decided_by: Optional[str]
    decision_comment: Optional[str]
```

**Key Methods:**

| Method | Line | Description |
|--------|------|-------------|
| `create()` | 450-469 | Factory with UUID generation |
| `approve()` | 471-476 | Set status=APPROVED, record decision |
| `reject()` | 478-483 | Set status=REJECTED, require comment |
| `expire()` | 485-488 | Set status=EXPIRED (timeout) |
| `is_pending()` | 490-492 | Check if status == PENDING |
| `can_be_decided_by()` | 494-499 | Authorization: empty assignees = anyone |

#### ApprovalStatus Enum (domain/enums.py:55-60)

```python
class ApprovalStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"
```

### Step Configuration (domain/step_configs.py)

**File**: `src/backend/services/process_engine/domain/step_configs.py`

#### HumanApprovalConfig (lines 64-107)

```python
@dataclass(frozen=True)
class HumanApprovalConfig:
    title: str                       # Title shown in approval UI
    description: str                 # Description of what needs approval
    assignees: list[str]             # User IDs or emails (empty = anyone)
    timeout: Duration                # Default: 24h
    allow_comments: bool = True
    require_reason_on_reject: bool = True
```

---

## Frontend Layer

### Approvals.vue

**File**: `src/frontend/src/views/Approvals.vue`

| Section | Lines | Description |
|---------|-------|-------------|
| Header | 8-27 | Title, refresh button |
| Filter dropdown | 29-58 | Status filter (pending/approved/rejected) |
| Stats cards | 60-78 | Total, pending, approved, rejected counts |
| Table | 94-191 | List of requests with actions |
| Reject modal | 196-230 | Comment input for rejection |

**Key Methods:**

```javascript
// Load approvals with optional status filter
async function loadApprovals() {
  const params = new URLSearchParams()
  if (statusFilter.value) params.append('status', statusFilter.value)
  const response = await fetch(`/api/approvals?${params}`)
  approvals.value = data.sort((a, b) => new Date(b.created_at) - new Date(a.created_at))
}

// Approve request
async function approveRequest(approval) {
  await fetch(`/api/approvals/${approval.id}/approve`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ comment: '' })
  })
  await loadApprovals()
}

// Reject request (requires comment)
async function confirmReject() {
  await fetch(`/api/approvals/${rejectingApproval.value.id}/reject`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ comment: rejectReason.value })
  })
  await loadApprovals()
}
```

### ProcessSubNav Badge

Shows pending approval count in navigation:

```vue
<ProcessSubNav :pending-approvals="pendingCount" />
```

---

## Flow Details

### 1. Create Approval Request Flow

When execution reaches a `human_approval` step:

```
ExecutionEngine                 HumanApprovalHandler           ApprovalStore
---------------                 --------------------           -------------
_execute_step()
  Get handler for HUMAN_APPROVAL
  handler.execute(context, config)
                            ->  execute()
                                1. Check existing request
                                2. Calculate deadline from config.timeout
                                3. Evaluate title template
                                4. Evaluate description template
                                5. ApprovalRequest.create()
                                   save(request)          ->   Store in memory
                            <-  StepResult.wait({approval_id, title})

_handle_step_waiting()
  step_exec.wait_for_approval()
  execution.pause()
  publish(StepWaitingApproval)
```

### 2. Approve/Reject Flow

When user makes a decision in the UI:

```
Approvals.vue                   Backend                         ExecutionEngine
-------------                   -------                         ---------------
User clicks Approve
POST /api/approvals/{id}/approve
  { comment: "Looks good" }
                            ->  approve()
                                1. Get ApprovalRequest from store
                                2. Validate still pending
                                3. request.approve(user, comment)
                                4. Store updated request
                                5. engine.resume(execution)
                                                            ->  resume()
                                                                1. Re-execute step
                                                                2. Handler sees "approved"
                                                                3. Return StepResult.ok()
```

### 3. Resume After Approval

When the step is re-executed after approval (lines 149-179):

```python
existing = self.approval_store.get_by_execution_step(execution_id, step_id)
if existing:
    if existing.is_pending():
        # Check timeout
        if existing.deadline and datetime.now(timezone.utc) > existing.deadline:
            existing.reject("SYSTEM", "Approval timed out - deadline exceeded")
            return StepResult.fail("Approval timed out", error_code="APPROVAL_TIMEOUT")
        # Still waiting
        return StepResult.wait({"approval_id": existing.id})
    elif existing.status.value == "approved":
        # Already approved - complete the step
        return StepResult.ok({
            "approval_id": existing.id,
            "decision": "approved",
            "decided_by": existing.decided_by,
            "comment": existing.decision_comment,
        })
    else:
        # Rejected - fail the step
        return StepResult.fail(
            f"Approval rejected by {existing.decided_by}: {existing.decision_comment}",
            error_code="APPROVAL_REJECTED",
        )
```

---

## YAML Configuration

### Basic Approval Step

```yaml
- id: review
  type: human_approval
  title: Review Content
  description: Please review the generated content before publishing
```

### With Assignees and Timeout

```yaml
- id: manager-approval
  type: human_approval
  title: Manager Approval Required
  description: This change requires manager sign-off
  assignees:
    - manager@example.com
    - supervisor@example.com
  timeout: 48h  # Auto-expires after 48 hours
```

### With Template Variables (Dynamic Content)

Template variables in `title` and `description` are evaluated at runtime:

```yaml
- id: intake
  type: agent_task
  agent: intake-agent
  message: Collect company info for {{input.company_name}}

- id: review-approval
  type: human_approval
  title: Approve {{input.company_name}} for {{input.deal_type}}?
  description: |
    Review the intake results before proceeding.

    **Company**: {{input.company_name}}
    **Deal Type**: {{input.deal_type}}
    **Intake Summary**: {{steps.intake.output.response}}
    **Risk Score**: {{steps.intake.output.score}}
  assignees:
    - deal-manager@example.com
  timeout: 24h
```

---

## Timeout Handling

### Deadline Calculation (lines 182-184)

```python
deadline = None
if config.timeout:
    deadline = datetime.now(timezone.utc) + timedelta(seconds=config.timeout.seconds)
```

### Duration Parsing

The `Duration` class supports human-readable formats:

| Format | Seconds |
|--------|---------|
| `30s` | 30 |
| `5m` | 300 |
| `2h` | 7200 |
| `24h` | 86400 |
| `48h` | 172800 |

### Expiration Check (lines 152-161)

When handler is re-executed, it checks if deadline has passed:

```python
if existing.deadline and datetime.now(timezone.utc) > existing.deadline:
    logger.info(f"Approval deadline passed for step '{step_id}', auto-rejecting")
    existing.reject("SYSTEM", "Approval timed out - deadline exceeded")
    self.approval_store.save(existing)
    return StepResult.fail(
        f"Approval timed out after deadline: {existing.deadline.isoformat()}",
        error_code="APPROVAL_TIMEOUT",
    )
```

---

## Authorization

### Assignee Check (lines 494-499)

```python
def can_be_decided_by(self, user: str) -> bool:
    """Check if the given user can decide on this request."""
    # If no assignees specified, anyone can approve
    if not self.assignees:
        return True
    return user in self.assignees
```

**Authorization Rules:**
- Empty `assignees` list = **anyone** can approve
- Non-empty `assignees` list = only listed users can approve
- Currently uses hardcoded "admin" user (TODO: get from auth context)

---

## Error Handling

| Error | HTTP Status | Cause |
|-------|-------------|-------|
| Approval not found | 404 | Invalid approval ID |
| Not authorized | 403 | User not in assignees list |
| Already decided | 400 | Approval already approved/rejected/expired |
| Comment required | 422 | Rejection without comment |

---

## Storage

### In-Memory Storage (ApprovalStore)

Currently uses singleton in-memory storage (lines 27-76):

```python
class ApprovalStore:
    _instance = None
    _requests: dict[str, ApprovalRequest] = {}

    def save(self, request: ApprovalRequest) -> None
    def get(self, request_id: str) -> Optional[ApprovalRequest]
    def get_by_execution_step(self, execution_id: str, step_id: str) -> Optional[ApprovalRequest]
    def get_pending_for_user(self, user: str) -> list[ApprovalRequest]
    def get_all_pending(self) -> list[ApprovalRequest]
```

**Note**: In production, this would be backed by database persistence.

---

## Testing

### Prerequisites
- Backend running at localhost:8000
- Published process with `human_approval` step
- User account for testing

### Test Cases

1. **Create approval request**
   - Action: Start process with human_approval step
   - Expected: Execution pauses, request appears in inbox
   - Verify: `GET /api/approvals?status=pending` returns new request

2. **Approve request**
   - Action: Click approve on pending request
   - Expected: Request marked approved, execution resumes, step completes
   - Verify: Step output contains `decision: approved`

3. **Reject request**
   - Action: Click reject, enter comment
   - Expected: Request marked rejected, step fails with APPROVAL_REJECTED
   - Verify: Process fails or handles rejection per error policy

4. **Template variable substitution**
   - Action: Start process with `{{input.X}}` in approval title
   - Expected: Title shows actual input value, not template
   - Verify: Approval request title is evaluated

5. **Missing template variable**
   - Action: Use `{{input.missing}}` in title
   - Expected: Variable left unchanged (non-strict mode)
   - Verify: Title shows `{{input.missing}}` literally

6. **Assignee authorization**
   - Action: Try to approve as non-assignee
   - Expected: 403 Forbidden error
   - Verify: Error message indicates not authorized

7. **Timeout expiration**
   - Action: Create approval with short timeout, wait for expiration
   - Expected: Request marked expired, step fails with APPROVAL_TIMEOUT
   - Verify: Status changes from `pending` to `expired`

---

## Related Flows

- **[process-execution.md](./process-execution.md)** - How execution pauses/resumes at approval steps
- **[process-monitoring.md](./process-monitoring.md)** - Viewing approval status in execution detail
- **[process-analytics.md](./process-analytics.md)** - Tracking approval wait times

---

## Document History

| Date | Change |
|------|--------|
| 2026-01-23 | **Rebuilt**: Complete rewrite with accurate line numbers, detailed template variable documentation, full API examples, testing section |
| 2026-01-23 | **Bug Fix (PE-H1)**: Documented template variable substitution in `title` and `description` fields |
| 2026-01-16 | Initial creation |
