# File Manager - Full Page with Preview

> **Status**: Draft
> **Created**: 2025-12-27
> **Author**: Claude (requirements research)
> **Priority**: High
> **Effort**: Medium (3-5 days implementation)
> **Depends On**: CONTENT_FOLDER_CONVENTION.md

## Problem Statement

The current file browser is limited:
1. **Cramped UI** - Embedded in agent detail tab (~300px width)
2. **No preview** - Can't view images, videos, audio without downloading
3. **Download only** - No delete, rename, or organize capabilities
4. **Single agent** - Must navigate to each agent to see files

Users generating content (video, audio, images) need a proper file manager to:
- Preview files before deciding what to keep
- Delete unwanted generated content
- Navigate large folder structures efficiently
- Manage files across multiple agents

## Solution Overview

Create a **dedicated File Manager page** (`/files`) with:
- **Agent selector dropdown** - Switch between agents
- **Two-panel layout** - Tree on left, preview on right
- **Rich previews** - Images, video, audio, text, PDF
- **File operations** - Delete files and folders
- **Full-width design** - Uses entire viewport for maximum usability

---

## User Stories

### US-1: View Files Across Agents
> As a user with multiple agents, I want to quickly switch between agents' file systems without navigating to each agent's detail page.

### US-2: Preview Generated Content
> As a user reviewing agent-generated content, I want to preview images, videos, and audio directly in the browser before deciding what to keep.

### US-3: Delete Unwanted Files
> As a user managing disk space, I want to delete files and folders that I no longer need.

### US-4: Navigate Large Trees
> As a user with deep folder structures, I want an efficient tree navigation with expand/collapse and search.

---

## Technical Analysis

### Current Implementation

**File Browser** (`views/AgentDetail.vue:765-830`):
- Tree view using recursive `FileTreeNode` component
- Search filtering with auto-expand
- Download via blob URL
- No preview, no delete

**Backend API** (`services/agent_service/files.py`):
- `GET /api/agents/{name}/files` - List files as tree
- `GET /api/agents/{name}/files/download` - Download as plain text
- No delete endpoint
- No binary file handling (reads all as UTF-8)

**Agent Server** (`agent_server/routers/files.py`):
- Security: Only `/home/developer` accessible
- 100MB file size limit
- Skips hidden files (`.` prefix)
- No delete capability

### Required Backend Changes

**New Endpoints**:

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/agents/{name}/files` | DELETE | Delete file or folder |
| `/api/agents/{name}/files/preview` | GET | Get file with proper MIME type |

**Agent Server Additions** (`agent_server/routers/files.py`):

```python
@router.delete("/api/files")
async def delete_file(path: str):
    """Delete a file or directory from workspace."""
    # Security checks (workspace only)
    # Delete file or recursively delete directory
    # Return success/failure

@router.get("/api/files/preview")
async def preview_file(path: str):
    """Get file content with appropriate MIME type for preview."""
    # Security checks
    # Detect MIME type
    # Return FileResponse with correct Content-Type
```

### Frontend Architecture

**New Route**: `/files`

```javascript
// router/index.js
{
  path: '/files',
  name: 'FileManager',
  component: () => import('../views/FileManager.vue'),
  meta: { requiresAuth: true }
}
```

**New View**: `views/FileManager.vue`

```
┌─────────────────────────────────────────────────────────────────────────┐
│  NavBar                                                                  │
├─────────────────────────────────────────────────────────────────────────┤
│  File Manager          [Agent: agent-ruby ▼]  [Refresh]                 │
├─────────────────────────────────────────────────────────────────────────┤
│                        │                                                 │
│  📁 workspace          │   ┌───────────────────────────────────────┐    │
│    📁 scripts          │   │                                       │    │
│    📄 CLAUDE.md        │   │         [Preview Area]                │    │
│                        │   │                                       │    │
│  📁 content            │   │   Image / Video / Audio / Text        │    │
│    📁 videos           │   │                                       │    │
│      🎬 demo.mp4 ◀─────│   │   ▶ 00:00 ━━━━━━━━━━ 02:34           │    │
│      🎬 tutorial.mp4   │   │                                       │    │
│    📁 audio            │   └───────────────────────────────────────┘    │
│    📁 images           │                                                 │
│                        │   Filename: demo.mp4                           │
│                        │   Size: 45.2 MB                                │
│  [Search...]           │   Modified: 2 hours ago                        │
│                        │   Path: content/videos/demo.mp4                │
│                        │                                                 │
│                        │   [Download]  [Delete]                         │
│                        │                                                 │
├────────────────────────┴─────────────────────────────────────────────────┤
│  12 files • 892 MB total                            [Selected: demo.mp4] │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Requirements

### REQ-FM-1: File Manager Page
- **Status**: Not Started
- **Priority**: High
- **Description**: Dedicated full-page file manager accessible from navigation

**Acceptance Criteria**:
- [ ] New route `/files` added to router
- [ ] Navigation link in NavBar (between Agents and Credentials)
- [ ] Full viewport width (not constrained like agent detail)
- [ ] Responsive layout for different screen sizes

**Implementation**:
- File: `src/frontend/src/router/index.js` - Add route
- File: `src/frontend/src/components/NavBar.vue` - Add nav link
- File: `src/frontend/src/views/FileManager.vue` - New view

### REQ-FM-2: Agent Selector
- **Status**: Not Started
- **Priority**: High
- **Description**: Dropdown to select which agent's files to view

**Acceptance Criteria**:
- [ ] Dropdown lists all running agents user has access to
- [ ] Shows agent name and status indicator
- [ ] Remembers last selected agent (localStorage)
- [ ] Updates file tree when agent changes
- [ ] Shows "Select an agent" prompt if none selected
- [ ] Only shows running agents (files require running container)

**Implementation**:
- Use `agentsStore.agents` filtered by `status === 'running'`
- Persist selection: `localStorage.setItem('fileManager.selectedAgent', name)`

### REQ-FM-3: Two-Panel Layout
- **Status**: Not Started
- **Priority**: High
- **Description**: Split view with file tree on left, preview on right

**Acceptance Criteria**:
- [ ] Left panel: File tree (resizable, ~300px default)
- [ ] Right panel: Preview area (fills remaining space)
- [ ] Divider between panels (draggable resize - future)
- [ ] Tree panel scrollable independently
- [ ] Preview panel scrollable independently

**Implementation**:
- CSS Grid or Flexbox layout
- Left panel: `min-width: 250px; max-width: 400px`
- Right panel: `flex: 1`

### REQ-FM-4: File Tree
- **Status**: Not Started
- **Priority**: High
- **Description**: Hierarchical file tree with expand/collapse

**Acceptance Criteria**:
- [ ] Reuse existing `FileTreeNode` component from AgentDetail
- [ ] Click folder to expand/collapse
- [ ] Click file to select and preview
- [ ] Visual indicator for selected item
- [ ] File icons based on type (folder, video, audio, image, text)
- [ ] File size displayed
- [ ] Search/filter box above tree
- [ ] Show total file count and size in footer

**Implementation**:
- Extract `FileTreeNode` from AgentDetail.vue to separate component
- Add `selected` prop and `@select` event
- Add file type icons mapping

### REQ-FM-5: File Preview - Images
- **Status**: Not Started
- **Priority**: High
- **Description**: Preview image files inline

**Acceptance Criteria**:
- [ ] Support formats: jpg, jpeg, png, gif, webp, svg
- [ ] Display image scaled to fit preview area
- [ ] Show actual dimensions
- [ ] Click to open full-size in new tab (optional)

**Implementation**:
- New endpoint: `GET /api/agents/{name}/files/preview?path=...`
- Returns file with `Content-Type: image/*`
- Frontend: `<img :src="previewUrl" />`

### REQ-FM-6: File Preview - Video
- **Status**: Not Started
- **Priority**: High
- **Description**: Preview video files with player controls

**Acceptance Criteria**:
- [ ] Support formats: mp4, webm, mov
- [ ] HTML5 video player with controls
- [ ] Play/pause, seek, volume
- [ ] Show duration and current time
- [ ] Poster frame (first frame or loading state)

**Implementation**:
- Same preview endpoint with `Content-Type: video/*`
- Frontend: `<video :src="previewUrl" controls />`
- Consider video.js or native HTML5 video

### REQ-FM-7: File Preview - Audio
- **Status**: Not Started
- **Priority**: High
- **Description**: Preview audio files with player controls

**Acceptance Criteria**:
- [ ] Support formats: mp3, wav, ogg, m4a
- [ ] HTML5 audio player with controls
- [ ] Play/pause, seek, volume
- [ ] Show duration

**Implementation**:
- Same preview endpoint with `Content-Type: audio/*`
- Frontend: `<audio :src="previewUrl" controls />`

### REQ-FM-8: File Preview - Text/Code
- **Status**: Not Started
- **Priority**: Medium
- **Description**: Preview text files with syntax highlighting

**Acceptance Criteria**:
- [ ] Support: .txt, .md, .json, .yaml, .py, .js, .ts, .sh, etc.
- [ ] Syntax highlighting based on file extension
- [ ] Line numbers
- [ ] Max preview size: 1MB (show warning for larger)
- [ ] Scrollable content area

**Implementation**:
- Use existing download endpoint (returns plain text)
- Frontend: Prism.js or highlight.js for syntax highlighting
- Consider Monaco editor (read-only) for better UX

### REQ-FM-9: File Preview - PDF
- **Status**: Not Started
- **Priority**: Low
- **Description**: Preview PDF files inline

**Acceptance Criteria**:
- [ ] Embedded PDF viewer
- [ ] Page navigation
- [ ] Zoom controls

**Implementation**:
- Preview endpoint with `Content-Type: application/pdf`
- Frontend: `<embed>` or PDF.js library

### REQ-FM-10: File Preview - Fallback
- **Status**: Not Started
- **Priority**: High
- **Description**: Fallback display for unsupported file types

**Acceptance Criteria**:
- [ ] Show file icon based on type
- [ ] Show filename, size, modified date, path
- [ ] Show "Preview not available" message
- [ ] Download button prominently displayed

### REQ-FM-11: Delete Files
- **Status**: Not Started
- **Priority**: High
- **Description**: Delete individual files

**Acceptance Criteria**:
- [ ] Delete button in preview panel (when file selected)
- [ ] Confirmation dialog: "Delete [filename]?"
- [ ] Success notification on delete
- [ ] Tree refreshes after delete
- [ ] Cannot delete protected paths (CLAUDE.md, .trinity/, etc.)
- [ ] Audit log entry for file deletion

**Implementation**:

Agent Server (`agent_server/routers/files.py`):
```python
@router.delete("/api/files")
async def delete_file(path: str):
    """Delete a file from workspace."""
    allowed_base = Path("/home/developer")
    requested_path = (allowed_base / path).resolve()

    # Security: workspace only
    if not str(requested_path).startswith(str(allowed_base)):
        raise HTTPException(403, "Access denied")

    # Protection: prevent deleting critical files
    protected = [".trinity", "CLAUDE.md", ".git", ".gitignore"]
    for p in protected:
        if requested_path.name == p or str(requested_path).endswith(f"/{p}"):
            raise HTTPException(403, f"Cannot delete protected path: {p}")

    if not requested_path.exists():
        raise HTTPException(404, "File not found")

    if requested_path.is_dir():
        shutil.rmtree(requested_path)
    else:
        requested_path.unlink()

    return {"success": True, "deleted": path}
```

Backend (`services/agent_service/files.py`):
```python
async def delete_agent_file_logic(agent_name: str, path: str, ...):
    """Proxy delete request to agent container."""
    # Auth checks
    # Proxy to agent: DELETE http://agent-{name}:8000/api/files?path=...
    # Audit log
```

### REQ-FM-12: Delete Folders
- **Status**: Not Started
- **Priority**: High
- **Description**: Delete folders recursively

**Acceptance Criteria**:
- [ ] Delete button when folder is selected
- [ ] Confirmation dialog with file count: "Delete [folder] and 15 files?"
- [ ] Recursive deletion
- [ ] Cannot delete root folders (workspace, content)

**Implementation**:
- Same endpoint as file delete
- `shutil.rmtree()` for directories
- Frontend: Show file count in confirmation

### REQ-FM-13: Preview Endpoint
- **Status**: Not Started
- **Priority**: High
- **Description**: Backend endpoint for file preview with proper MIME type

**Acceptance Criteria**:
- [ ] Returns file content with correct Content-Type header
- [ ] Supports range requests for video seeking
- [ ] Respects 100MB size limit
- [ ] Security: workspace only access

**Implementation**:

Agent Server:
```python
@router.get("/api/files/preview")
async def preview_file(path: str):
    """Get file with proper MIME type for preview."""
    import mimetypes

    # Security checks...

    mime_type, _ = mimetypes.guess_type(str(requested_path))
    if mime_type is None:
        mime_type = "application/octet-stream"

    return FileResponse(
        requested_path,
        media_type=mime_type,
        filename=requested_path.name
    )
```

Backend Proxy:
```python
@router.get("/{agent_name}/files/preview")
async def preview_agent_file(agent_name: str, path: str, ...):
    """Proxy preview request with streaming response."""
    # Stream response from agent container
```

### REQ-FM-14: Keyboard Navigation
- **Status**: Not Started
- **Priority**: Low
- **Description**: Keyboard shortcuts for power users

**Acceptance Criteria**:
- [ ] Arrow keys: Navigate tree
- [ ] Enter: Expand folder / Select file
- [ ] Delete/Backspace: Delete selected (with confirmation)
- [ ] Cmd/Ctrl+F: Focus search
- [ ] Escape: Clear selection

---

## UI/UX Design

### Color Scheme
Follow existing Trinity dark mode support:
- Tree panel: `bg-gray-50 dark:bg-gray-900`
- Preview panel: `bg-white dark:bg-gray-800`
- Selected item: `bg-indigo-100 dark:bg-indigo-900/30`

### File Type Icons
| Type | Icon | Color |
|------|------|-------|
| Folder | `FolderIcon` | Yellow |
| Video | `FilmIcon` | Purple |
| Audio | `MusicalNoteIcon` | Green |
| Image | `PhotoIcon` | Blue |
| Code | `CodeBracketIcon` | Gray |
| Text | `DocumentTextIcon` | Gray |
| PDF | `DocumentIcon` | Red |
| Other | `DocumentIcon` | Gray |

### Loading States
- Tree loading: Skeleton with animated bars
- Preview loading: Centered spinner
- Delete in progress: Button disabled with spinner

### Empty States
- No agent selected: "Select an agent to browse files"
- Agent not running: "Start agent to browse files"
- Empty folder: "This folder is empty"
- No preview: "Select a file to preview"

---

## Testing Plan

### Test 1: Basic Navigation
1. Navigate to `/files`
2. Select an agent from dropdown
3. Verify file tree loads
4. Click folder to expand
5. Click file to preview

### Test 2: Image Preview
1. Navigate to image in content folder
2. Click to select
3. Verify image displays in preview panel
4. Verify dimensions and size shown

### Test 3: Video Preview
1. Navigate to video file
2. Click to select
3. Verify video player appears
4. Play video, seek, adjust volume

### Test 4: Delete File
1. Select a test file
2. Click Delete button
3. Confirm in dialog
4. Verify file removed from tree
5. Verify file no longer on agent filesystem

### Test 5: Delete Folder
1. Create test folder with files
2. Select folder
3. Click Delete
4. Confirm (shows file count)
5. Verify folder and contents removed

### Test 6: Protected Paths
1. Try to delete CLAUDE.md
2. Verify error: "Cannot delete protected path"
3. Try to delete .trinity folder
4. Verify error

### Test 7: Agent Switching
1. Select agent A
2. Navigate to folder
3. Switch to agent B
4. Verify tree refreshes with agent B's files
5. Switch back to agent A
6. Verify state preserved (optional)

---

## Files to Create/Modify

### New Files
| File | Purpose |
|------|---------|
| `src/frontend/src/views/FileManager.vue` | Main file manager page |
| `src/frontend/src/components/file-manager/FileTree.vue` | Extracted tree component |
| `src/frontend/src/components/file-manager/FilePreview.vue` | Preview panel component |
| `src/frontend/src/components/file-manager/PreviewImage.vue` | Image preview |
| `src/frontend/src/components/file-manager/PreviewVideo.vue` | Video preview |
| `src/frontend/src/components/file-manager/PreviewAudio.vue` | Audio preview |
| `src/frontend/src/components/file-manager/PreviewText.vue` | Text/code preview |
| `src/frontend/src/components/file-manager/PreviewFallback.vue` | Fallback preview |

### Modified Files
| File | Change |
|------|--------|
| `src/frontend/src/router/index.js` | Add `/files` route |
| `src/frontend/src/components/NavBar.vue` | Add "Files" nav link |
| `src/frontend/src/stores/agents.js` | Add preview/delete methods |
| `src/backend/routers/agents.py` | Add delete/preview endpoints |
| `src/backend/services/agent_service/files.py` | Add delete/preview logic |
| `docker/base-image/agent_server/routers/files.py` | Add DELETE and preview endpoints |

---

## Security Considerations

### Path Traversal Prevention
- All paths resolved via `Path.resolve()`
- Must start with `/home/developer`
- Reject paths with `..` traversal

### Protected Paths
Cannot delete:
- `CLAUDE.md` - Agent instructions
- `.trinity/` - Trinity system files
- `.git/` - Git repository
- `.gitignore` - Git configuration
- `.env` - Environment secrets
- `.mcp.json` - MCP configuration

### Audit Logging
Log all delete operations:
```python
await log_audit_event(
    event_type="file_access",
    action="file_delete",
    user_id=current_user.username,
    agent_name=agent_name,
    metadata={"path": path, "type": "file|directory"},
    result="success|failed"
)
```

### Size Limits
- Preview: 100MB max (existing limit)
- Video streaming: Use range requests, no full buffer

---

## Performance Considerations

### Lazy Loading
- Don't load entire tree at once for huge workspaces
- Consider paginated tree loading for 1000+ files
- Load preview on demand (not on hover)

### Caching
- Cache file tree for 30 seconds
- Cache MIME type detection
- Use browser cache for preview URLs

### Video Streaming
- Support HTTP Range requests for video seeking
- Don't buffer entire video in memory

---

## Future Enhancements (Not in v1)

1. **File Upload** - Upload files to agent workspace
2. **Rename Files** - Rename files and folders inline
3. **Move Files** - Drag-and-drop to reorganize
4. **Multi-Select** - Select multiple files for bulk operations
5. **Bulk Download** - Download as ZIP
6. **File Versioning** - Track changes over time
7. **Search Content** - Full-text search within files
8. **Thumbnails** - Grid view with thumbnails

---

## Related Documents

- `docs/drafts/CONTENT_FOLDER_CONVENTION.md` - Content folder pattern (prerequisite)
- `docs/memory/feature-flows/file-browser.md` - Current file browser
- `docs/memory/feature-flows/github-sync.md` - Git sync integration
- `docs/memory/feature-flows/agent-lifecycle.md` - Agent container management

---

## Revision History

| Date | Author | Changes |
|------|--------|---------|
| 2025-12-27 | Claude | Initial requirements draft |
