# Feature: Templates Page

## Overview
The Templates Page (`/templates`) provides a dedicated UI for browsing and selecting agent templates. Users can view available GitHub and local templates, see metadata (description, MCP servers, credentials, resources), and create new agents from selected templates.

## User Story
As a platform user, I want to browse available agent templates so that I can understand what pre-configured agents are available and quickly create one with the right capabilities.

## Entry Points

### Navigation
- **Primary**: AgentSubNav tab "Templates" at `/templates`
- **Secondary**: NavBar "Agents" section (highlights when on `/templates`, `/agents`, `/files`)
- **Redirect**: CreateAgentModal "Use Template" button on any template

### Routes
| Route | Component | Auth Required |
|-------|-----------|---------------|
| `/templates` | `Templates.vue` | Yes |

---

## Frontend Layer

### Route Definition (`src/frontend/src/router/index.js:60-64`)
```javascript
{
  path: '/templates',
  name: 'Templates',
  component: () => import('../views/Templates.vue'),
  meta: { requiresAuth: true }
}
```

### AgentSubNav Component (`src/frontend/src/components/AgentSubNav.vue`)
Sub-navigation bar with three tabs: Agents, Files, Templates.

| Line | Element | Purpose |
|------|---------|---------|
| 35-50 | `navItems` array | Defines tabs: `/agents`, `/files`, `/templates` |
| 47-50 | Templates item | `{ path: '/templates', label: 'Templates', icon: DocumentDuplicateIcon }` |
| 53-58 | `isActive()` | Active state for current route |

### Templates.vue (`src/frontend/src/views/Templates.vue`)
Main view for browsing templates.

| Line | Element | Purpose |
|------|---------|---------|
| 3 | NavBar | Top navigation bar |
| 4 | AgentSubNav | Agents/Files/Templates tabs |
| 8-14 | Page header | Title "Agent Templates" with description |
| 15-25 | Refresh button | `@click="fetchTemplates"` with loading spinner |
| 29-37 | Loading state | Shows when `loading && templates.length === 0` |
| 40-50 | Error state | Shows error message with retry button |
| 54-134 | GitHub Templates section | Grid of GitHub template cards |
| 137-216 | Local Templates section | Grid of local template cards |
| 218-247 | Custom Agent section | "Blank Agent" card option |
| 250-256 | Empty state | Shows when no templates configured |
| 262-267 | CreateAgentModal | Opens with `initial-template` prop |
| 283-296 | Computed properties | `githubTemplates`, `localTemplates` filters |
| 299-302 | `getDisplayName()` | Removes "(GitHub)" suffix for cleaner display |
| 304-318 | `fetchTemplates()` | API call to `GET /api/templates` |
| 320-323 | `useTemplate()` | Sets `selectedTemplateId`, opens modal |
| 325-332 | `onAgentCreated()` | Navigates to `/agents/{name}` after creation |

### Template Card Layout
Each template card displays:
```
+----------------------------------+
| [Icon]  Template Name            |
|         github-repo or id        |
|                                  |
| Description (3 line clamp)       |
|                                  |
| MCP Servers: [tag] [tag] +N more |
|                                  |
| [CPU icon] 2 CPU, 4g  [Key] 3    |
|                                  |
| [  Use Template  ]               |
+----------------------------------+
```

**Visual Differentiation:**
- **GitHub templates**: Black GitHub icon background, shows `github_repo`
- **Local templates**: Indigo document icon background, shows `display_name`
- **Blank Agent**: Gray plus icon, dashed border

### Computed Properties (`Templates.vue:289-296`)
```javascript
const githubTemplates = computed(() => {
  return templates.value.filter(t => t.source === 'github')
})

const localTemplates = computed(() => {
  return templates.value.filter(t => t.source === 'local' || !t.source)
})
```

### API Call (`Templates.vue:304-318`)
```javascript
const fetchTemplates = async () => {
  loading.value = true
  error.value = ''
  try {
    const response = await axios.get('/api/templates', {
      headers: authStore.authHeader
    })
    templates.value = response.data
  } catch (err) {
    error.value = err.response?.data?.detail || 'Failed to load templates'
  } finally {
    loading.value = false
  }
}
```

---

## Backend Layer

### Templates Router (`src/backend/routers/templates.py`)

| Line | Endpoint | Purpose |
|------|----------|---------|
| 14 | Router prefix | `APIRouter(prefix="/api/templates", tags=["templates"])` |
| 17-26 | `GET /api/templates` | List templates (DB-configured or config.py defaults) |
| 29-41 | `GET /api/templates/{template_id:path}` | Get single template details |

### List Templates Endpoint (`routers/templates.py:17-26`)
```python
@router.get("")
async def list_templates(current_user: User = Depends(get_current_user)):
    """List available agent templates (GitHub-based only)."""
    # Use DB-configured list if set, else hardcoded defaults
    db_templates = get_github_templates_from_db()
    templates = db_templates if db_templates is not None else list(ALL_GITHUB_TEMPLATES)

    # Sort by priority (lower = higher in list), then by display_name
    templates.sort(key=lambda t: (t.get("priority", 100), t.get("display_name", "")))
    return templates
```

> **TMPL-001 (2026-03-04)**: Template list now checks DB-configured templates first (set via Settings → GitHub Templates). If the admin has configured a custom list, only those templates are shown. Otherwise falls back to hardcoded `ALL_GITHUB_TEMPLATES` from `config.py`. Local template scanning was removed.

### Template Response Schema
```json
{
  "id": "github:abilityai/agent-ruby",
  "display_name": "Ruby - Content & Publishing",
  "description": "Content creation and multi-platform social media distribution agent",
  "github_repo": "abilityai/agent-ruby",
  "source": "github",
  "resources": {"cpu": "2", "memory": "4g"},
  "mcp_servers": ["heygen", "twitter-mcp"],
  "required_credentials": [
    {"name": "HEYGEN_API_KEY", "source": "mcp:heygen"},
    {"name": "TWITTER_API_KEY", "source": "mcp:twitter"}
  ],
  "priority": 100
}
```

### Local Template Response Schema
```json
{
  "id": "local:demo-analyst",
  "display_name": "Analysis Agent",
  "description": "Synthesizes research findings and answers strategic questions",
  "source": "local",
  "resources": {"cpu": "1", "memory": "2g"},
  "mcp_servers": [],
  "required_credentials": [],
  "priority": 100
}
```

---

## Template Sources

### GitHub Templates

**Source priority** (TMPL-001):
1. **DB-configured list** — set via Settings → GitHub Templates (`system_settings` key `github_templates`)
2. **Hardcoded defaults** — `config.py` `ALL_GITHUB_TEMPLATES` (fallback when no DB config)

DB templates are stored as minimal entries `{github_repo, display_name, description}` and expanded at runtime via `expand_github_template()` in `template_service.py:14-32`.

**Hardcoded defaults** (`src/backend/config.py`):

```python
GITHUB_TEMPLATES = [
    {
        "id": "github:abilityai/agent-ruby",
        "display_name": "Ruby - Content & Publishing",
        "description": "Content creation and multi-platform...",
        "github_repo": "abilityai/agent-ruby",
        "github_credential_id": GITHUB_PAT_CREDENTIAL_ID,
        "source": "github",
        "resources": {"cpu": "2", "memory": "4g"},
        "mcp_servers": [],
        "required_credentials": ["HEYGEN_API_KEY", "TWITTER_API_KEY", "CLOUDINARY_API_KEY"]
    },
    # ... more templates
]
```

**Current GitHub Templates (config.py):**
- `github:abilityai/agent-ruby` - Content & Publishing
- `github:abilityai/agent-cornelius` - Knowledge Manager
- `github:abilityai/agent-corbin` - Business Assistant
- `github:abilityai/ruby-orchestrator` - Calendar & State Manager
- `github:abilityai/ruby-content` - Discovery & Production
- `github:abilityai/ruby-engagement` - Social & Growth

### Local Templates (`config/agent-templates/`)
Scanned from filesystem at runtime. Each template folder must contain `template.yaml`.

**Template Directory Structure:**
```
config/agent-templates/
  demo-analyst/
    template.yaml       # Required: name, display_name, description, resources
    CLAUDE.md           # Required: agent instructions
    .mcp.json.template  # Optional: MCP server configuration
    .env.example        # Optional: environment variables
```

**Current Local Templates:**
- `trinity-system` - Internal platform operations agent
- `demo-analyst` - Analysis Agent (demo)
- `demo-researcher` - Research Agent (demo)
- `scout`, `sage`, `scribe` - Example multi-agent system
- `test-*` - Test agents for automated testing
- `dd-*` - Due diligence agents

### Template YAML Schema (`config/agent-templates/*/template.yaml`)
```yaml
name: demo-analyst                    # Required: unique identifier
display_name: Analysis Agent          # Required: UI display name
description: |                        # Required: description
  Synthesizes research findings...
version: "1.0.0"                      # Optional: version string
author: Trinity Demo                  # Optional: author

resources:                            # Required: container resources
  cpu: "1"
  memory: "2g"

capabilities:                         # Optional: capability tags
  - synthesis
  - strategic-analysis

use_cases:                            # Optional: usage examples
  - "/briefing - Generate a daily briefing"

shared_folders:                       # Optional: folder sharing config
  expose: false
  consume: true

commands:                             # Optional: slash commands
  - name: briefing
    description: Generate daily briefing

schedules:                            # Optional: auto-schedules
  - name: daily-briefing
    cron: "0 9 * * *"
    message: "/briefing"

metrics:                              # Optional: custom metrics
  - name: briefings_generated
    type: counter
    label: "Briefings"

priority: 100                         # Optional: sort order (lower = first)
```

---

## Credential Extraction (`src/backend/services/template_service.py`)

### extract_agent_credentials (`template_service.py:143-225`)
Extracts credential requirements from multiple sources:

1. **`.mcp.json` or `.mcp.json.template`** - Extracts `${VAR_NAME}` patterns
2. **`template.yaml` credentials section** - Explicit credential definitions
3. **`.env.example`** - Environment variable names

```python
def extract_agent_credentials(repo_path: Path) -> Dict:
    """
    Returns:
        {
            "required_credentials": [{"name": "VAR", "source": "mcp:server"}],
            "mcp_servers": {"server": ["VAR1", "VAR2"]},
            "env_file_vars": ["VAR3"]
        }
    """
```

### Pattern Extraction (`template_service.py:64-103`)
```python
pattern = r'\$\{([A-Z][A-Z0-9_]*)\}'  # Matches ${VAR_NAME}
```

---

## "Create Agent" Flow from Template Selection

### 1. User Clicks "Use Template"
```javascript
// Templates.vue:320-323
const useTemplate = (template) => {
  selectedTemplateId.value = template?.id || ''
  showCreateModal.value = true
}
```

### 2. CreateAgentModal Opens with Pre-Selected Template
```vue
<!-- Templates.vue:262-267 -->
<CreateAgentModal
  v-if="showCreateModal"
  :initial-template="selectedTemplateId"
  @close="showCreateModal = false"
  @created="onAgentCreated"
/>
```

### 3. Modal Pre-Fills Template Selection
```javascript
// CreateAgentModal.vue:207-210
watch(() => props.initialTemplate, (newVal) => {
  form.template = newVal || ''
})
```

### 4. User Submits Form
```javascript
// CreateAgentModal.vue:263-285
const createAgent = async () => {
  const payload = { name: form.name }
  if (form.template) {
    payload.template = form.template
  }
  const agent = await agentsStore.createAgent(payload)
  emit('created', agent)
  emit('close')
}
```

### 5. Store Action Posts to API
```javascript
// stores/agents.js:115-132
async createAgent(config) {
  const response = await axios.post('/api/agents', config, {
    headers: authStore.authHeader
  })
  return response.data
}
```

### 6. Navigation to New Agent
```javascript
// Templates.vue:325-332
const onAgentCreated = (agent) => {
  if (agent?.name) {
    router.push(`/agents/${agent.name}`)
  } else {
    router.push('/agents')
  }
}
```

---

## Error Handling

| Error Case | HTTP Status | User Message |
|------------|-------------|--------------|
| Not authenticated | 401 | Redirected to login |
| API timeout | - | "Failed to load templates" |
| API error | 500 | `err.response?.data?.detail` or fallback |
| No templates | - | "No templates configured" with config hint |

### Error State UI (`Templates.vue:40-50`)
```vue
<div v-else-if="error" class="text-center py-12">
  <p class="text-gray-600">{{ error }}</p>
  <button @click="fetchTemplates" class="text-indigo-600">
    Try again
  </button>
</div>
```

---

## Security Considerations

1. **Authentication Required**: Route has `meta: { requiresAuth: true }`
2. **Authorization Header**: API calls include `authStore.authHeader`
3. **No Sensitive Data**: Template list shows metadata only, not credentials
4. **GitHub PAT Hidden**: PAT values never exposed in API responses

---

## Testing

### Prerequisites
- Backend running at `localhost:8000`
- Frontend running at `localhost:3000` or via Docker at `localhost`
- Authenticated user session

### Test Steps

| Step | Action | Expected Result |
|------|--------|-----------------|
| 1 | Navigate to `/templates` | Page loads with template grid |
| 2 | Verify GitHub Templates section | Shows templates from `config.py` |
| 3 | Verify Local Templates section | Shows templates from `config/agent-templates/` |
| 4 | Click refresh button | Spinner shows, templates reload |
| 5 | Click "Use Template" on any card | CreateAgentModal opens with template pre-selected |
| 6 | Enter agent name, submit | Agent created, redirected to `/agents/{name}` |
| 7 | Click "Create Blank Agent" | Modal opens with no template selected |

### API Testing
```bash
# List all templates
curl http://localhost:8000/api/templates \
  -H "Authorization: Bearer $TOKEN"

# Get specific template details
curl http://localhost:8000/api/templates/local:demo-analyst \
  -H "Authorization: Bearer $TOKEN"

# Get env template for bulk import
curl "http://localhost:8000/api/templates/env-template?template_id=github:abilityai/agent-ruby" \
  -H "Authorization: Bearer $TOKEN"
```

### Edge Cases
- Templates with no description show "No description available"
- MCP servers list shows first 4, then "+N more" badge
- Long descriptions are truncated with `line-clamp-3`

---

## Status
**Working** - Templates page fully functional with dynamic loading

---

## Revision History

| Date | Changes |
|------|---------|
| 2026-03-04 | **TMPL-001 Configurable GitHub Templates**: Template list now uses DB-configured templates (via Settings → GitHub Templates) with fallback to `config.py` defaults. Local template scanning removed. `templates.py` simplified to 42 lines. Added `get_github_templates_from_db()` and `expand_github_template()` in `template_service.py`. Updated endpoint table, list endpoint code, template sources section, related flows. |
| 2026-01-21 | **Initial creation**: Documented complete vertical slice for Templates Page feature - navigation, UI components, API endpoints, template sources, credential extraction, create flow, error handling |

---

## Related Flows

- **Upstream**: Authentication (user must be logged in)
- **Upstream**: [platform-settings.md](platform-settings.md) - TMPL-001 GitHub Templates configuration
- **Downstream**: [template-processing.md](template-processing.md) - Deep dive on template processing during agent creation
- **Downstream**: [agent-lifecycle.md](agent-lifecycle.md) - Agent creation and container initialization
- **Related**: [credential-injection.md](credential-injection.md) - How template credentials are injected
