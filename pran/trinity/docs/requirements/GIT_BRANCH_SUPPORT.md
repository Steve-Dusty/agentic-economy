# Git Branch Support for Agent Creation (GIT-002)

> **Status**: Ready for Implementation
> **Priority**: P2
> **Created**: 2026-02-28

## Problem Statement

When creating agents via MCP `create_agent` tool, there's no way to specify which branch to use. The `source_branch` parameter exists in the backend but isn't exposed through MCP. Container restarts revert to `main` if a different branch was manually selected.

## Current Architecture

```
MCP Tool (agents.ts)           TypeScript Interface (types.ts)
         ↓                              ↓
    No source_branch              No source_branch
         ↓                              ↓
         └──────────────┬───────────────┘
                        ↓
              Backend AgentConfig (models.py:27)
                        ↓
               source_branch: "main"  ← Default
                        ↓
              crud.py:311 → GIT_SOURCE_BRANCH env var
                        ↓
              startup.sh:41-50 → git checkout $GIT_SOURCE_BRANCH
```

## Components & Required Changes

| Component | File | Current State | Change Needed |
|-----------|------|---------------|---------------|
| MCP Types | `src/mcp-server/src/types.ts:16-29` | No `source_branch` | Add `source_branch?: string` |
| MCP Tool | `src/mcp-server/src/tools/agents.ts:150-248` | No branch param | Add zod schema + pass to config |
| Template Parsing | `src/backend/services/agent_service/crud.py:121-128` | Parses `github:owner/repo` | Parse `github:owner/repo@branch` |
| Git Clone | `src/backend/services/template_service.py:37` | `git clone --depth 1` | Add `-b branch` when specified |
| Startup Script | `docker/base-image/startup.sh:41-50` | Reads `GIT_SOURCE_BRANCH` | **No change needed** |
| Feature Flow | `docs/memory/feature-flows/github-sync.md` | Documents source_branch config | Document URL syntax |

## Proposed Solution

Support both URL syntax AND explicit parameter. URL syntax takes precedence if both provided.

### URL-Based Syntax
Parse branch from template URL: `github:owner/repo@branch`

### Explicit Parameter
Add `source_branch` parameter to MCP `create_agent` tool.

### Example Usage

```javascript
// URL syntax
create_agent({name: "my-agent", template: "github:owner/repo@feature-branch"})

// Explicit parameter
create_agent({name: "my-agent", template: "github:owner/repo", source_branch: "feature-branch"})

// Both (URL wins)
create_agent({name: "my-agent", template: "github:owner/repo@develop", source_branch: "main"})
// → Uses "develop"
```

## Implementation Details

### 1. URL Parsing (crud.py)

```python
# Current: line 123
repo_path = config.template[7:]  # Remove "github:" prefix

# Proposed:
template_str = config.template[7:]  # Remove "github:" prefix
if "@" in template_str:
    repo_path, branch = template_str.rsplit("@", 1)
    config.source_branch = branch
else:
    repo_path = template_str
```

### 2. MCP Tool Parameter (agents.ts)

```typescript
source_branch: z
  .string()
  .optional()
  .describe(
    "Branch to track for this agent. Default: 'main'. " +
    "Can also be specified in template URL as 'github:owner/repo@branch'."
  ),
```

### 3. MCP Types (types.ts)

```typescript
export interface AgentConfig {
  // ... existing fields
  source_branch?: string;  // Branch to track (default: main)
}
```

### 4. Git Clone with Branch (template_service.py)

```python
def clone_github_repo(github_repo: str, github_pat: str, dest_path: Path, branch: str = None) -> bool:
    clone_cmd = ["git", "clone", "--depth", "1"]
    if branch:
        clone_cmd.extend(["-b", branch])
    clone_cmd.extend([clone_url, str(dest_path)])
```

## Testing Checklist

- [ ] Create agent with URL syntax: `github:owner/repo@feature-branch`
- [ ] Create agent with explicit param: `source_branch: "develop"`
- [ ] Container restart: Verify branch persists
- [ ] Pull operation: Verify pulls from correct branch
- [ ] Invalid branch: Handle gracefully with clear error
- [ ] Edge case: Repo name containing `@` character

## Database Impact

None - `source_branch` column already exists in `agent_git_config` table.

## Related Files

| Category | File | Lines |
|----------|------|-------|
| Backend model | `src/backend/models.py` | 27 |
| Agent creation | `src/backend/services/agent_service/crud.py` | 95-145, 301-314 |
| Git service | `src/backend/services/git_service.py` | - |
| Template service | `src/backend/services/template_service.py` | 22-61 |
| MCP tool | `src/mcp-server/src/tools/agents.ts` | 150-248 |
| MCP types | `src/mcp-server/src/types.ts` | 16-29 |
| Startup script | `docker/base-image/startup.sh` | 41-80 |
| Feature flow | `docs/memory/feature-flows/github-sync.md` | - |

## Acceptance Criteria

1. MCP `create_agent` accepts `source_branch` parameter
2. Template URL syntax `github:owner/repo@branch` is parsed correctly
3. Agent containers start on the specified branch
4. Container restarts preserve the branch setting
5. Git pull operations work on the specified branch
6. Documentation updated in github-sync.md feature flow
