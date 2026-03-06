# Feature: Process Templates

> Bundled and user-created process templates for quick-start workflows

---

## Overview

Process Templates provide starting points for common workflows. Users can:
- Browse and filter templates by category
- Preview template YAML before using
- Create processes from templates
- Save their own processes as reusable templates

**Template Sources:**
- **Bundled**: Pre-configured templates in `config/process-templates/`
- **User**: Custom templates saved to SQLite database

---

## User Story

As a **process designer**, I want to **start from a template** so that **I can quickly create workflows without writing YAML from scratch**.

---

## Entry Points

| Type | Location | Description |
|------|----------|-------------|
| **UI** | `src/frontend/src/views/ProcessEditor.vue:158-163` | TemplateSelector shown for new processes |
| **UI** | `src/frontend/src/views/ProcessList.vue:219-274` | Quick Start Templates in empty state |
| **UI** | `src/frontend/src/views/ProcessEditor.vue:132-142` | "Save as Template" button for published processes |
| **API** | `GET /api/process-templates` | List all templates |
| **API** | `GET /api/process-templates/categories` | List available categories |
| **API** | `GET /api/process-templates/{id}` | Get template detail |
| **API** | `GET /api/process-templates/{id}/preview` | Get YAML for preview |
| **API** | `POST /api/process-templates/{id}/use` | Create process from template |
| **API** | `POST /api/process-templates` | Create user template |
| **API** | `DELETE /api/process-templates/{id}` | Delete user template |

---

## Frontend Layer

### Components

#### TemplateSelector.vue
**File**: `src/frontend/src/components/process/TemplateSelector.vue`

| Line | Function | Description |
|------|----------|-------------|
| 8-16 | Category dropdown | Filter templates by category |
| 39-111 | Template grid | Display template cards with selection |
| 41-61 | Blank process option | "Start from scratch" card |
| 64-110 | Template cards | Individual template cards |
| 113-174 | Preview modal | Full template preview with YAML |

**Props:**
```javascript
// Line 189-194
props: {
  selectedId: {
    type: String,
    default: null,
  },
}
```

**Events emitted:**
- `@select(templateId)` - Template selected (null for blank)

#### ProcessEditor.vue Template Integration
**File**: `src/frontend/src/views/ProcessEditor.vue`

| Line | Function | Description |
|------|----------|-------------|
| 158-163 | TemplateSelector | Component for selecting templates |
| 186-200 | Continue button | Load template and proceed to editor |
| 648-735 | Save Template Dialog | Modal for saving process as template |
| 1166-1200 | handleTemplateSelect() | Handle template selection |
| 1171-1200 | proceedWithTemplate() | Load template YAML into editor |
| 1489-1524 | saveAsTemplate() | Save current process as user template |

#### ProcessList.vue Quick Start Templates
**File**: `src/frontend/src/views/ProcessList.vue`

| Line | Function | Description |
|------|----------|-------------|
| 219-274 | Quick Start Templates | Inline templates in empty state |
| 371-376 | useTemplate() | Navigate to editor with template query param |

### State Management

The processes store does not manage template state directly. Templates are loaded on-demand via API calls.

### API Calls

**List templates:**
```javascript
// TemplateSelector.vue:227-239
async function fetchTemplates() {
  const response = await axios.get('/api/process-templates', {
    headers: { Authorization: `Bearer ${token}` },
  })
  templates.value = response.data.templates || []
}
```

**Get categories:**
```javascript
// TemplateSelector.vue:242-251
async function fetchCategories() {
  const response = await axios.get('/api/process-templates/categories', {
    headers: { Authorization: `Bearer ${token}` },
  })
  categories.value = response.data.categories || []
}
```

**Load template preview:**
```javascript
// ProcessEditor.vue:1181
const response = await api.get(`/api/process-templates/${selectedTemplateId.value}/preview`)
```

**Save as template:**
```javascript
// ProcessEditor.vue:1500-1506
await api.post('/api/process-templates', {
  name: templateForm.value.name,
  display_name: templateForm.value.displayName || templateForm.value.name,
  description: templateForm.value.description,
  category: templateForm.value.category,
  tags: tags,
  definition_yaml: yamlContent.value,
})
```

---

## Backend Layer

### Router Endpoints
**File**: `src/backend/routers/process_templates.py`

| Line | Method | Path | Handler | Description |
|------|--------|------|---------|-------------|
| 106-124 | GET | `/api/process-templates` | `list_templates()` | List templates with filters |
| 128-144 | GET | `/api/process-templates/categories` | `list_categories()` | Get available categories |
| 149-169 | GET | `/api/process-templates/{id}/preview` | `get_template_preview()` | Get YAML for preview |
| 172-243 | POST | `/api/process-templates/{id}/use` | `use_template()` | Create process from template |
| 246-273 | POST | `/api/process-templates` | `create_template()` | Create user template |
| 277-294 | GET | `/api/process-templates/{id}` | `get_template()` | Get full template detail |
| 297-323 | DELETE | `/api/process-templates/{id}` | `delete_template()` | Delete user template |

### Request/Response Models
**File**: `src/backend/routers/process_templates.py:28-83`

```python
class TemplateInfoResponse(BaseModel):
    """Template summary info."""
    id: str
    name: str
    display_name: str
    description: str
    category: str
    complexity: str
    version: str
    author: str
    tags: List[str]
    step_types_used: List[str]
    source: str

class TemplateDetailResponse(BaseModel):
    """Full template with definition."""
    # ... same fields plus:
    definition_yaml: str
    use_cases: List[str]
    created_at: Optional[str]
    created_by: Optional[str]

class CreateTemplateRequest(BaseModel):
    """Request body for creating a template."""
    name: str = Field(..., min_length=1, max_length=100)
    display_name: Optional[str]
    description: Optional[str]
    category: str = Field(default="general")
    complexity: str = Field(default="simple")
    tags: List[str] = Field(default_factory=list)
    use_cases: List[str] = Field(default_factory=list)
    definition_yaml: str
```

### Service Layer
**File**: `src/backend/services/process_engine/services/templates.py`

#### ProcessTemplateService

| Line | Method | Description |
|------|--------|-------------|
| 82-106 | `__init__()` | Initialize with templates dir and db path |
| 108-137 | `_ensure_tables()` | Create SQLite tables for user templates |
| 143-171 | `list_templates()` | List bundled + user templates |
| 173-219 | `_load_bundled_templates()` | Scan config/process-templates/ directory |
| 221-258 | `_load_user_templates()` | Query database for user templates |
| 264-283 | `get_template()` | Get template by ID (process: or user: prefix) |
| 285-332 | `_get_bundled_template()` | Load bundled template from filesystem |
| 334-369 | `_get_user_template()` | Load user template from database |
| 375-444 | `create_template()` | Create new user template |
| 446-460 | `delete_template()` | Delete user template |

#### Template ID Format

Templates use prefixed IDs to distinguish sources:
- `process:{name}` - Bundled template (e.g., `process:content-review`)
- `user:{name}` - User-created template (e.g., `user:my-workflow`)

```python
# templates.py:264-283
def get_template(self, template_id: str) -> Optional[ProcessTemplate]:
    if template_id.startswith("process:"):
        return self._get_bundled_template(template_id[8:])
    elif template_id.startswith("user:"):
        return self._get_user_template(template_id[5:])
    else:
        # Try both
        template = self._get_bundled_template(template_id)
        if not template:
            template = self._get_user_template(template_id)
        return template
```

---

## Bundled Templates

### Directory Structure
```
config/process-templates/
├── client-onboarding/
│   ├── template.yaml      # Metadata
│   └── definition.yaml    # Process definition
├── content-review/
│   ├── template.yaml
│   └── definition.yaml
├── customer-support/
│   ├── template.yaml
│   └── definition.yaml
├── data-analysis/
│   ├── template.yaml
│   └── definition.yaml
├── market-analysis/
│   ├── template.yaml
│   └── definition.yaml
├── vc-due-diligence/
│   ├── template.yaml
│   └── definition.yaml
└── weekly-brief/
    ├── template.yaml
    └── definition.yaml
```

### Current Bundled Templates

| Template | Category | Complexity | Step Types |
|----------|----------|------------|------------|
| client-onboarding | business | intermediate | agent_task, human_approval |
| content-review | content | intermediate | agent_task, user_task, condition |
| customer-support | support | intermediate | agent_task, human_approval |
| data-analysis | analytics | intermediate | agent_task |
| market-analysis | consulting | intermediate | agent_task, human_approval, gateway |
| vc-due-diligence | finance | advanced | agent_task, human_approval, gateway, notification |
| weekly-brief | business | simple | agent_task |

### Template Metadata Schema (template.yaml)

```yaml
name: market-analysis               # Slug (must match directory name)
display_name: Market Analysis Pipeline
description: Comprehensive market analysis workflow
category: consulting                # business, content, devops, analytics, support, finance
complexity: intermediate            # simple, intermediate, advanced
version: "1.0.0"
author: Acme Consulting

tags:
  - consulting
  - market-research
  - analysis

step_types_used:
  - agent_task
  - human_approval
  - gateway

use_cases:
  - "Market entry analysis"
  - "Competitive landscape assessment"

# Optional fields:
prerequisites:
  - "Deploy required agents"
estimated_duration: "2-5 minutes"
```

### Process Definition Schema (definition.yaml)

```yaml
name: market-analysis
version: 1
description: End-to-end market analysis

steps:
  - id: market-research
    name: Conduct Market Research
    type: agent_task
    agent: acme-scout
    message: |
      Research {{input.market}}
    timeout: 15m

  - id: quality-check
    name: Quality Review
    type: human_approval
    depends_on: market-research
    title: Review Market Analysis
    timeout: 48h

outputs:
  - name: report_status
    source: "{{steps.create-report.output}}"
```

---

## Database Schema

### User Templates Table
**File**: `src/backend/services/process_engine/services/templates.py:116-134`

```sql
CREATE TABLE IF NOT EXISTS process_templates (
    id TEXT PRIMARY KEY,
    name TEXT UNIQUE NOT NULL,
    display_name TEXT,
    description TEXT,
    category TEXT DEFAULT 'general',
    complexity TEXT DEFAULT 'simple',
    version TEXT DEFAULT '1.0.0',
    author TEXT,
    tags TEXT,               -- YAML serialized list
    step_types_used TEXT,    -- YAML serialized list
    use_cases TEXT,          -- YAML serialized list
    definition_yaml TEXT NOT NULL,
    created_by TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
)
```

**Database Location:** `~/trinity-data/trinity_templates.db`

---

## Template Categories

**File**: `src/backend/routers/process_templates.py:128-144`

```python
@router.get("/categories")
async def list_categories(current_user: CurrentUser):
    return {
        "categories": [
            {"id": "general", "name": "General", "description": "General-purpose workflows"},
            {"id": "business", "name": "Business", "description": "Business process automation"},
            {"id": "devops", "name": "DevOps", "description": "Development and operations"},
            {"id": "analytics", "name": "Analytics", "description": "Data analysis workflows"},
            {"id": "support", "name": "Support", "description": "Customer support workflows"},
            {"id": "content", "name": "Content", "description": "Content creation pipelines"},
        ]
    }
```

Note: Additional categories like `consulting` and `finance` are used in bundled templates but not in the static categories list.

---

## Use Template Flow

### Endpoint Handler
**File**: `src/backend/routers/process_templates.py:172-243`

```python
@router.post("/{template_id:path}/use")
async def use_template(
    template_id: str,
    request: UseTemplateRequest,
    current_user: CurrentUser,
):
    # 1. Load template
    template = service.get_template(template_id)

    # 2. Customize YAML with new process name
    yaml_content = template.definition_yaml
    yaml_content = yaml_content.replace("{{name}}", request.name)
    yaml_content = re.sub(r'^name:\s*.+$', f'name: {request.name}', yaml_content, flags=re.MULTILINE)

    # 3. Validate the customized YAML
    result = validator.validate_yaml(yaml_content, created_by=current_user.email)

    # 4. Save to repository
    repo.save(definition)

    # 5. Emit ProcessCreated event
    await publish_event(ProcessCreated(...))

    return {
        "process_id": str(definition.id),
        "process_name": definition.name,
        "template_id": template_id,
    }
```

---

## Error Handling

| Error Case | HTTP Status | Detail |
|------------|-------------|--------|
| Template not found | 404 | "Template not found" |
| Template name exists | 400 | "Template with name 'x' already exists" |
| Cannot delete bundled | 400 | "Cannot delete bundled templates" |
| Invalid definition YAML | 422 | "Template validation failed" with error list |
| Validation passed but no definition | 500 | "Validation passed but no definition created" |

---

## Side Effects

- **No WebSocket broadcasts** - Template operations do not broadcast events
- **No audit logging** - Template CRUD is not currently audited
- **Domain Event**: `ProcessCreated` emitted when using template to create process

---

## Security Considerations

1. **Authentication Required**: All endpoints require valid JWT token
2. **User Templates**: Only user-created templates can be deleted
3. **Bundled Protection**: Bundled templates cannot be modified or deleted via API
4. **Input Validation**: Template names validated for length (1-100 chars)

---

## Quick Start Templates (Inline)

ProcessList.vue provides inline quick-start templates for the empty state:

**File**: `src/frontend/src/views/ProcessList.vue:219-274`

| Template ID | Name | Steps |
|-------------|------|-------|
| content-pipeline | Content Pipeline | Research, Write, Review |
| data-report | Data Report | Gather, Analyze, Report |
| support-escalation | Support Escalation | Triage, Route, Resolve + approval |

ProcessEditor.vue provides corresponding YAML:

**File**: `src/frontend/src/views/ProcessEditor.vue:929-1071`

```javascript
const quickStartTemplates = {
  'content-pipeline': `name: content-pipeline\nversion: "1.0"\n...`,
  'data-report': `name: data-report\nversion: "1.0"\n...`,
  'support-escalation': `name: support-escalation\nversion: "1.0"\n...`,
}
```

---

## Creating a Bundled Template

1. Create directory:
   ```bash
   mkdir config/process-templates/my-template
   ```

2. Create `template.yaml`:
   ```yaml
   name: my-template
   display_name: My Template
   description: What this template does
   category: business
   complexity: simple
   version: "1.0.0"
   author: Your Name
   tags: [tag1, tag2]
   step_types_used: [agent_task]
   use_cases: ["Use case 1"]
   ```

3. Create `definition.yaml`:
   ```yaml
   name: "{{name}}"
   version: 1
   description: Process from my-template

   steps:
     - id: step1
       type: agent_task
       agent: your-agent
       message: Instructions

   outputs:
     - name: result
       source: "{{steps.step1.output}}"
   ```

4. Rebuild/restart backend to pick up new template

---

## Related Flows

- **Upstream**: [process-definition.md](./process-definition.md) - Process created from template
- **Downstream**: [process-execution.md](./process-execution.md) - Execute created process

---

## Document History

| Date | Change |
|------|--------|
| 2026-01-16 | Initial creation |
| 2026-01-23 | Rebuilt with accurate line numbers and complete file paths |
