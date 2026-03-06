# Agent Systems & Tags

> **Requirement ID**: ORG-001
> **Priority**: MEDIUM
> **Status**: PHASE 4 COMPLETE | All phases implemented
> **Created**: 2026-02-17

## Overview

Lightweight organizational layer for grouping agents into logical systems using tags and saved filter views. Enables agents to belong to multiple systems without adding security or configuration complexity.

## Problem Statement

As agent fleets grow, users need to:
- Group related agents visually (e.g., "Due Diligence Team", "Content Operations")
- Reuse the same agent across multiple workflows/systems
- Filter the Dashboard to focus on specific agent groups
- Quickly understand which agents work together

## Design Principles

1. **Tags, not folders** - Agents can have multiple tags, enabling multi-system membership
2. **Views, not entities** - Systems are saved filters, not security boundaries
3. **Organization only** - No impact on permissions, credentials, or agent behavior
4. **Additive** - Builds on existing Dashboard; doesn't replace it

## Relationship to Existing Multi-Agent Features

Tags/System Views is an **organization layer** that complements existing infrastructure:

```
┌─────────────────────────────────────────────────────────────────┐
│                        DEPLOYMENT                                │
│  System Manifest → Creates agents with system_prefix             │
│  (dd-researcher, dd-writer, dd-analyst)                         │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                     ORGANIZATION (THIS SPEC)                     │
│  Tags → Auto-tagged from prefix OR manually added                │
│  System Views → Saved filters for Dashboard                      │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                       SECURITY                                   │
│  Permissions → Controls actual agent-to-agent calls              │
│  (Unchanged - Tags don't affect permissions)                     │
└─────────────────────────────────────────────────────────────────┘
```

### Existing Features Comparison

| Feature | Purpose | Scope | Relationship to Tags |
|---------|---------|-------|---------------------|
| **System Manifest** | Deploy N agents from YAML | Deployment-time | Auto-tag on deploy |
| **`system_prefix`** | Naming convention (`dd-*`) | Naming only | Extract as tag |
| **Agent Permissions** | Who can call whom | Security | Unchanged |
| **Shared Folders** | File collaboration | Data sharing | Unchanged |
| **Dashboard** | Visualize agents + connections | All agents | Filter by System View |

### Integration Points

| Existing Feature | How Tags Integrates |
|-----------------|---------------------|
| **System Manifest** | Add optional `tags` field per agent in manifest YAML. Auto-apply `system_prefix` as tag. |
| **`system_prefix`** | Migration script extracts prefix as tag (`dd-researcher` → tag `dd`) |
| **Dashboard** | System Views sidebar filters which agents appear |
| **Permissions** | No change - tags are visual organization, not security boundaries |

### Example: Due Diligence System

**Deployment** (System Manifest - unchanged):
```yaml
system_prefix: dd
agents:
  - name: researcher
  - name: writer
  - name: reviewer
```
Creates: `dd-researcher`, `dd-writer`, `dd-reviewer`

**Organization** (Tags - new):
```
dd-researcher  → tags: [dd, research]
dd-writer      → tags: [dd, content]
dd-reviewer    → tags: [dd, review]
shared-helper  → tags: [dd, content, support]  # Reused across systems!
```

**Visualization** (System View - new):
- "Due Diligence" view filters to `#dd` tag → shows 4 agents
- "Content Team" view filters to `#content` tag → shows `dd-writer`, `shared-helper`

### What Changes vs What Stays the Same

| Aspect | Changes? | Details |
|--------|----------|---------|
| Agent creation | ❌ No | Still via Manifest or manual |
| Permissions | ❌ No | Still explicit agent-to-agent grants |
| Shared folders | ❌ No | Still per-agent configuration |
| Credentials | ❌ No | Still per-agent |
| Dashboard default | ❌ No | Still shows all agents |
| **Dashboard filtered** | ✅ Yes | New System Views sidebar |
| **Agent reuse** | ✅ Yes | Multi-tag enables appearing in multiple views |
| **Visual grouping** | ✅ Yes | Color-coded tags, named views |

## Data Model

### Database Schema

```sql
-- Agent tags (many-to-many)
CREATE TABLE agent_tags (
    agent_name TEXT NOT NULL,
    tag TEXT NOT NULL,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (agent_name, tag),
    FOREIGN KEY (agent_name) REFERENCES agent_ownership(agent_name) ON DELETE CASCADE
);

CREATE INDEX idx_agent_tags_tag ON agent_tags(tag);
CREATE INDEX idx_agent_tags_agent ON agent_tags(agent_name);

-- Saved system views
CREATE TABLE system_views (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT,
    icon TEXT,                    -- Optional emoji or icon identifier
    color TEXT,                   -- Optional hex color for UI
    filter_tags TEXT NOT NULL,    -- JSON array of tags (OR logic)
    owner_id TEXT NOT NULL,
    is_shared INTEGER DEFAULT 0,  -- Visible to all users?
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (owner_id) REFERENCES users(id)
);

CREATE INDEX idx_system_views_owner ON system_views(owner_id);
```

### Tag Conventions

- Tags are lowercase, alphanumeric with hyphens: `due-diligence`, `content-ops`, `shared`
- No `#` prefix in storage (added in UI display only)
- Reserved tags (optional, for future use): `_system`, `_archived`

## API Endpoints

### Tags

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/agents/{name}/tags` | List tags for an agent |
| PUT | `/api/agents/{name}/tags` | Set all tags for an agent (replace) |
| POST | `/api/agents/{name}/tags/{tag}` | Add single tag |
| DELETE | `/api/agents/{name}/tags/{tag}` | Remove single tag |
| GET | `/api/tags` | List all unique tags with agent counts |

**Request/Response Examples:**

```json
// PUT /api/agents/researcher/tags
// Request:
{ "tags": ["due-diligence", "content-ops", "shared"] }

// Response:
{ "agent_name": "researcher", "tags": ["content-ops", "due-diligence", "shared"] }
```

```json
// GET /api/tags
// Response:
{
  "tags": [
    { "tag": "due-diligence", "count": 5 },
    { "tag": "content-ops", "count": 3 },
    { "tag": "shared", "count": 2 }
  ]
}
```

### System Views

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/system-views` | List user's views + shared views |
| POST | `/api/system-views` | Create new view |
| GET | `/api/system-views/{id}` | Get view details |
| PUT | `/api/system-views/{id}` | Update view |
| DELETE | `/api/system-views/{id}` | Delete view |

**Request/Response Examples:**

```json
// POST /api/system-views
// Request:
{
  "name": "Due Diligence Team",
  "description": "Agents for DD workflows",
  "icon": "🔍",
  "color": "#8B5CF6",
  "filter_tags": ["due-diligence"],
  "is_shared": true
}

// Response:
{
  "id": "sv_abc123",
  "name": "Due Diligence Team",
  "description": "Agents for DD workflows",
  "icon": "🔍",
  "color": "#8B5CF6",
  "filter_tags": ["due-diligence"],
  "owner_id": "user_123",
  "is_shared": true,
  "agent_count": 5,
  "created_at": "2026-02-17T10:00:00Z"
}
```

### Dashboard Integration

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/agents?tags=dd,content` | Filter agents by tags (OR logic) |
| GET | `/api/agents/context-stats?tags=dd` | Context stats filtered by tags |

## UI Components

### 1. Agent Tags (AgentDetail + AgentHeader)

**Location**: Agent Detail page, new "Tags" section in header or Info tab

**Features**:
- Display current tags as chips/badges
- Inline tag editor (click to add/remove)
- Autocomplete from existing tags
- Color-coded tags (optional, based on system view colors)

```
┌─────────────────────────────────────────────────────┐
│ researcher                              [Running ●] │
│ Tags: #due-diligence #content-ops #shared    [+ Add]│
└─────────────────────────────────────────────────────┘
```

### 2. System Views Sidebar (Dashboard)

**Location**: Left sidebar on Dashboard (collapsible)

**Features**:
- List of saved system views
- "All Agents" option (default, no filter)
- Click to filter Dashboard
- Visual indicator for active filter
- Quick create: "+ New System View"

```
┌──────────────────┐
│ SYSTEMS          │
│ ─────────────────│
│ ○ All Agents     │
│ ● Due Diligence  │  <- Active
│ ○ Content Ops    │
│ ○ Customer Svc   │
│ ─────────────────│
│ + New View       │
└──────────────────┘
```

### 3. System View Editor (Modal)

**Location**: Modal triggered from sidebar or Settings

**Fields**:
- Name (required)
- Description (optional)
- Icon picker (emoji)
- Color picker
- Tag selector (multi-select from existing tags)
- Share toggle (visible to all users)

### 4. Quick Tag Filter (Dashboard Header)

**Location**: Dashboard header, next to existing controls

**Features**:
- Tag dropdown/pills for quick filtering
- Works alongside System Views
- "Clear filter" button

```
┌─────────────────────────────────────────────────────────────┐
│ Dashboard    [Graph ▾] [Timeline]    Tags: #dd ✕  [+ Tag]  │
└─────────────────────────────────────────────────────────────┘
```

### 5. Agents Page Integration

**Location**: Agents list page (`/agents`)

**Features**:
- Same tag filter as Dashboard
- Tag chips displayed on agent cards
- Bulk tag operations (select multiple agents, add/remove tags)

## Implementation Phases

### Phase 1: Tags Backend + Basic UI
- [x] Database schema (agent_tags table) - 2026-02-17
- [x] Tag CRUD API endpoints (`/api/tags`, `/api/agents/{name}/tags`) - 2026-02-17
- [x] Tag display on AgentDetail (read-only) - 2026-02-17
- [x] Tag editor on AgentDetail - 2026-02-17 (TagsEditor.vue component)
- [x] `/api/agents?tags=` filter support - 2026-02-17

### Phase 2: System Views
- [x] Database schema (system_views table) - 2026-02-17
- [x] System Views CRUD API endpoints - 2026-02-17 (`routers/system_views.py`, `db/system_views.py`)
- [x] System Views sidebar on Dashboard - 2026-02-17 (`SystemViewsSidebar.vue`)
- [x] Dashboard filtering by view - 2026-02-17 (network store + API tags filter)
- [x] System View editor modal - 2026-02-17 (`SystemViewEditor.vue`)

### Phase 3: Polish & Integration
- [x] Tag autocomplete - 2026-02-17 (already exists in TagsEditor.vue)
- [x] Bulk tag operations on Agents page - 2026-02-17 (selection checkboxes, add/remove bulk tags)
- [ ] Tag colors synced with System View colors (deferred - nice-to-have)
- [x] Quick tag filter in Dashboard header - 2026-02-17 (inline tag pills)
- [x] MCP tools - 2026-02-17: `list_tags`, `get_agent_tags`, `tag_agent`, `untag_agent`, `set_agent_tags` (5 tools in `tools/tags.ts`)

### Phase 4: System Manifest Integration
- [x] Add `tags` field to manifest agent schema - 2026-02-17 (`models.py:SystemAgentConfig.tags`)
- [x] Auto-apply `system_prefix` as tag on deploy - 2026-02-17 (`system_service.py:configure_tags()`)
- [x] Migration script: extract existing prefixes as tags - 2026-02-17 (`scripts/management/migrate_prefixes_to_tags.py`)
- [x] Optional: Auto-create System View from manifest - 2026-02-17 (`system_service.py:create_system_view()`)

**System Manifest YAML Extension:**
```yaml
name: due-diligence-system
system_prefix: dd
default_tags: [due-diligence]  # Applied to all agents in manifest

agents:
  - name: researcher
    tags: [research, active]   # Additional tags for this agent
  - name: writer
    tags: [content]
  - name: reviewer
    tags: [review, qa]

# Optional: Auto-create System View on deploy
system_view:
  name: "Due Diligence Team"
  icon: "🔍"
  color: "#8B5CF6"
  shared: true
```

**Result after deploy:**
- `dd-researcher` → tags: `[due-diligence, research, active]`
- `dd-writer` → tags: `[due-diligence, content]`
- `dd-reviewer` → tags: `[due-diligence, review, qa]`
- System View "Due Diligence Team" created with filter `[due-diligence]`

## MCP Tools (Phase 3)

```typescript
// List all tags with counts
list_tags() -> { tags: [{ tag: string, count: number }] }

// Get tags for an agent
get_agent_tags(agent_name: string) -> { tags: string[] }

// Add tag to agent
tag_agent(agent_name: string, tag: string) -> { success: boolean }

// Remove tag from agent
untag_agent(agent_name: string, tag: string) -> { success: boolean }

// List system views
list_system_views() -> { views: SystemView[] }
```

## Access Control

| Action | Owner | Shared User | Admin |
|--------|-------|-------------|-------|
| View agent tags | ✅ | ✅ | ✅ |
| Edit agent tags | ✅ | ❌ | ✅ |
| Create system view | ✅ | ✅ | ✅ |
| Edit own system view | ✅ | ✅ | ✅ |
| Delete own system view | ✅ | ✅ | ✅ |
| Share system view | ✅ | ✅ | ✅ |
| Edit shared view (not owner) | ❌ | ❌ | ✅ |

## Migration & Compatibility

### System Prefix Migration (Optional)

Existing agents using `system_prefix` convention (e.g., `dd-researcher`) can be auto-tagged:

```python
# One-time migration script
for agent in agents:
    if '-' in agent.name:
        prefix = agent.name.split('-')[0]
        add_tag(agent.name, prefix)
```

### Backward Compatibility

- All existing features unchanged
- Tags are optional (agents work fine with no tags)
- System Views are optional (Dashboard shows all agents by default)

## Testing

### Unit Tests
- Tag CRUD operations
- System View CRUD operations
- Filter logic (OR matching)

### Integration Tests
- Tag persistence across agent restart
- System View filtering on Dashboard
- Access control for shared views

### Manual Testing
1. Create agent, add tags, verify display
2. Create system view with tag filter
3. Apply view on Dashboard, verify filtering
4. Test with agents in multiple systems
5. Share system view, verify other users see it

## Non-Goals (Explicitly Out of Scope)

- **Permissions by system** - Keep permissions at agent level
- **System-level credentials** - Each agent manages its own
- **Nested systems/folders** - Flat tag structure only
- **Tag-based auto-permissions** - Manual permission grants only
- **System-level schedules** - Schedules remain per-agent

## Future Considerations

If needed later, these could be added:

1. **Tag inheritance from template** - Templates define default tags
2. **System View as deployment target** - "Deploy to Content Ops system"
3. **System-level metrics** - Aggregate cost/usage per system view
4. **Tag-based access control** - "Users with role X can see agents tagged Y"

## Related Documents

- [System Manifest](../memory/feature-flows/system-manifest.md) - YAML-based multi-agent deployment
- [Agent Permissions](../memory/feature-flows/agent-permissions.md) - Agent-to-agent access control
- [Dashboard Timeline View](../memory/feature-flows/dashboard-timeline-view.md) - Visualization to be filtered

## Revision History

| Date | Change |
|------|--------|
| 2026-02-17 | Initial spec created |
| 2026-02-17 | Added relationship mapping to existing multi-agent features |
| 2026-02-17 | Added Phase 4: System Manifest integration with YAML schema extension |
| 2026-02-17 | **Phase 1 COMPLETE**: Tags backend + basic UI implemented. Files: `db/tags.py`, `routers/tags.py`, `TagsEditor.vue`, updated `AgentHeader.vue`, `AgentDetail.vue`, `database.py`, `main.py` |
| 2026-02-17 | **Phase 2 COMPLETE**: System Views implemented. Files: `db/system_views.py`, `routers/system_views.py`, `SystemViewsSidebar.vue`, `SystemViewEditor.vue`, `stores/systemViews.js`, updated `Dashboard.vue`, `database.py`, `main.py`, `stores/network.js` |
| 2026-02-17 | **Phase 3 COMPLETE**: MCP tools (5 tools in `mcp-server/src/tools/tags.ts`), Quick tag filter in Dashboard header, Bulk tag operations on Agents page (selection + add/remove tags), Tag filter on Agents page |
| 2026-02-17 | **Phase 4 COMPLETE**: System Manifest Integration. Added `tags` to `SystemAgentConfig`, `default_tags` and `system_view` to `SystemManifest`, `configure_tags()` and `create_system_view()` to service layer, migration script at `scripts/management/migrate_prefixes_to_tags.py`. All ORG-001 phases now complete. |
