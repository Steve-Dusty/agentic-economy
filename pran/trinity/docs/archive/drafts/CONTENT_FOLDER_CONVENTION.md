# Content Folder Convention

> **Status**: Draft
> **Created**: 2025-12-27
> **Author**: Claude (requirements research)
> **Priority**: High
> **Effort**: Low (1-2 hours implementation)

## Problem Statement

Agents generate large files (video, audio, images, exports) that:
1. **Bloat Git repositories** - Video files can be 100s of MB, inappropriate for version control
2. **Slow down GitHub sync** - Large binary files make `git push` slow and wasteful
3. **Risk accidental commits** - Without clear convention, users may accidentally commit large assets

Meanwhile, these files **must persist** across container rebuilds and restarts.

## Solution Overview

Establish a **standard convention** where:
- Generated content goes in `/home/developer/content/`
- The `content/` folder is automatically added to `.gitignore`
- Files in `content/` persist on the agent's Docker volume (survives restarts)
- Files in `content/` are NOT synced to GitHub

This is a **convention + automation** approach - simple but effective.

---

## Technical Analysis

### Current State

**Volume Persistence** (`agent-lifecycle.md:404-412`):
```python
# Each agent has a persistent Docker volume
agent_volume_name = f"agent-{config.name}-workspace"
volumes = {
    agent_volume_name: {'bind': '/home/developer', 'mode': 'rw'}
}
```
- All files in `/home/developer` already persist across restarts

**Git Sync** (`agent_server/routers/git.py:174-184`):
```python
# git add -A stages all non-ignored files
add_result = subprocess.run(
    ["git", "add", "-A"],
    capture_output=True,
    ...
)
```
- Git sync uses `git add -A` which **respects .gitignore**
- No code changes needed if `.gitignore` includes `content/`

**Current .gitignore handling** (`startup.sh:66-70`):
```bash
if [ ! -f /home/developer/.gitignore ]; then
    echo "# Trinity agent infrastructure files" > /home/developer/.gitignore
fi
grep -q ".local/" /home/developer/.gitignore || echo ".local/" >> /home/developer/.gitignore
```
- Already creates `.gitignore` if missing
- Already adds `.local/` to ignore Python packages

### Proposed Change

Add `content/` to the default `.gitignore` during startup:

```bash
# In startup.sh, after the .local/ line:
grep -q "content/" /home/developer/.gitignore || echo "content/" >> /home/developer/.gitignore
```

Also update Trinity injection to create the `content/` directory:

```python
# In trinity.py inject_trinity():
content_dir = workspace / "content"
content_dir.mkdir(parents=True, exist_ok=True)
directories_created.append("content")
```

---

## Requirements

### REQ-CC-1: Default .gitignore Entry
- **Status**: Not Started
- **Priority**: High
- **Description**: Automatically add `content/` to `.gitignore` for all agents

**Acceptance Criteria**:
- [ ] New agents have `content/` in `.gitignore` after startup
- [ ] Existing agents get `content/` added on next restart
- [ ] Entry is idempotent (not duplicated on multiple restarts)
- [ ] Works for both GitHub-native and local template agents

**Implementation**:
- File: `docker/base-image/startup.sh`
- Add line after `.local/` handling (~line 70):
  ```bash
  grep -q "content/" /home/developer/.gitignore || echo "content/" >> /home/developer/.gitignore
  ```

### REQ-CC-2: Create content/ Directory
- **Status**: Not Started
- **Priority**: Medium
- **Description**: Automatically create the `content/` directory structure

**Acceptance Criteria**:
- [ ] `content/` directory exists after Trinity injection
- [ ] Directory has standard subdirectories: `videos/`, `audio/`, `images/`, `exports/`
- [ ] Creation is idempotent (doesn't fail if already exists)

**Implementation Options**:

**Option A** - Via Trinity injection (`agent_server/routers/trinity.py:inject_trinity()`):
```python
# After creating .trinity directory
content_dir = workspace / "content"
for subdir in ["videos", "audio", "images", "exports"]:
    (content_dir / subdir).mkdir(parents=True, exist_ok=True)
directories_created.append("content")
```

**Option B** - Via startup.sh (simpler):
```bash
mkdir -p /home/developer/content/{videos,audio,images,exports}
```

**Recommendation**: Option B (simpler, runs earlier in boot process)

### REQ-CC-3: Documentation
- **Status**: Not Started
- **Priority**: Medium
- **Description**: Document the content folder convention for template authors

**Acceptance Criteria**:
- [ ] Update `docs/AGENT_TEMPLATE_SPEC.md` with content folder section
- [ ] Add recommendation in Trinity prompt (`.trinity/prompt.md`)
- [ ] Example in agent instructions

**Suggested Documentation**:
```markdown
## Content Folder Convention

Generated content (videos, audio, images, exports) should be saved to:

```
/home/developer/content/
├── videos/      # Generated video files
├── audio/       # Generated audio files
├── images/      # Generated images
└── exports/     # Data exports, reports, etc.
```

**Why?**
- Files in `content/` persist across restarts
- Files in `content/` are NOT synced to GitHub
- Keeps your Git repository lean and fast
```

---

## Testing Plan

### Test 1: New Agent Creation
1. Create a new agent from a GitHub template
2. Verify `.gitignore` contains `content/`
3. Verify `content/` directory exists with subdirectories
4. Create a file in `content/videos/test.mp4`
5. Run git sync - verify `test.mp4` is NOT committed

### Test 2: Existing Agent Restart
1. Take an existing agent without `content/` in `.gitignore`
2. Restart the agent
3. Verify `content/` is added to `.gitignore`
4. Verify directory structure created

### Test 3: Git Status Display
1. Create files in `content/` and in `workspace/`
2. Check git status in UI
3. Verify `content/` files don't appear in "pending changes"

---

## Files to Modify

| File | Change |
|------|--------|
| `docker/base-image/startup.sh` | Add `content/` to .gitignore, create directory |
| `docs/AGENT_TEMPLATE_SPEC.md` | Document convention |
| `config/trinity-meta-prompt/prompt.md` | Recommend content folder usage |

---

## Rollout Plan

1. **Implement** startup.sh changes
2. **Rebuild** base image: `./scripts/deploy/build-base-image.sh`
3. **Test** with new agent
4. **Restart** existing agents to pick up changes
5. **Document** in template spec

---

## Future Considerations

### Content Quota (Future)
Could add per-agent content quotas:
- Track `content/` folder size
- Alert when approaching limit
- Configurable per template

### Content Backup (Future)
Dedicated backup for content folder:
- Separate from Git
- Cloud storage integration (S3, GCS)
- Scheduled backups

### Content Cleanup (Future)
Auto-cleanup old content:
- Configurable retention policy
- "Archive to cloud" before delete

---

## Related Documents

- `docs/memory/feature-flows/file-browser.md` - Current file browser
- `docs/memory/feature-flows/github-sync.md` - Git sync flow
- `docs/memory/feature-flows/agent-lifecycle.md` - Agent creation/startup
- `docs/AGENT_TEMPLATE_SPEC.md` - Template authoring guide

---

## Revision History

| Date | Author | Changes |
|------|--------|---------|
| 2025-12-27 | Claude | Initial requirements draft |
