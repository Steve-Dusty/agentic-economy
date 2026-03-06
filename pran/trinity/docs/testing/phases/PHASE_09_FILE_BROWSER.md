# Phase 9: File Browser & Persistence (test-files)

> **Purpose**: Validate file operations, tree structure, and persistent storage
> **Duration**: ~10 minutes
> **Assumes**: Phase 8 PASSED (queue working, test-files running)
> **Output**: File browser and persistence verified

---

## Background

**Persistent Memory (Pillar III)**:
- Agents have virtual filesystems in containers
- Shared directory accessible via UI file browser
- Files survive agent restarts
- Tree structure navigation and download

---

## Test: File Browser Navigation

### Step 1: Navigate to test-files
**Action**:
- Go to http://localhost/agents
- Click test-files
- Wait for detail page to load

**Expected**:
- [ ] Agent detail page loads
- [ ] Chat tab active
- [ ] Status: "Running" (green)
- [ ] Context: 0% (fresh agent)

---

### Step 2: Click Files Tab
**Action**:
- Click "Files" tab in agent detail page
- Wait 3 seconds for file tree to load

**Expected**:
- [ ] Files tab active
- [ ] File tree structure visible
- [ ] Root directory shows
- [ ] Folder icons for directories
- [ ] File icons for documents

**Verify**:
- [ ] Tree structure renders
- [ ] Expandable folders shown with chevrons
- [ ] No loading errors

---

### Step 3: Explore Directory Structure
**Action**:
- Click to expand `/home/developer/` folder
- Wait 1 second
- Click to expand `workspace/` folder
- Look at available files/folders

**Expected**:
```
📁 home/
  📁 developer/
    📁 workspace/
      📄 README.md
      📄 data.json
      📁 uploads/
      📁 cache/
```

**Verify**:
- [ ] Folders expand/collapse correctly
- [ ] Subfolder visible
- [ ] Files listed with names
- [ ] Folder icons distinguished from file icons

---

## Test: File Creation and Content

### Step 4: Create File via Chat
**Action**:
- Type in chat: "create file config.yaml with content: database: postgres, host: localhost, port: 5432"
- Press Enter
- Wait 10 seconds

**Expected Response**:
```
File created successfully
Path: /home/developer/workspace/config.yaml
Size: 52 bytes
Timestamp: [current time]
```

**Verify**:
- [ ] File created successfully
- [ ] Correct path shown
- [ ] File size shown
- [ ] Timestamp recorded

---

### Step 5: Verify File in Browser
**Action**:
- Look at Files tab (may need refresh: F5)
- Wait 2 seconds
- Expand workspace folder
- Look for config.yaml

**Expected**:
- [ ] config.yaml appears in file tree
- [ ] Listed with other files
- [ ] File icon shown
- [ ] Size displayed (52 bytes)

**Verify**:
- [ ] New file visible in browser
- [ ] File tree updates automatically
- [ ] Metadata correct

---

### Step 6: Download File
**Action**:
- Right-click on config.yaml in file tree
- Select "Download" (if UI provides)
- Or: Type in chat "download config.yaml"
- Press Enter
- Wait 5 seconds

**Expected**:
```
File ready for download
URL: http://localhost/api/agents/test-files/files/workspace/config.yaml
Size: 52 bytes
```

**Verify**:
- [ ] Download link generated
- [ ] File accessible via HTTP
- [ ] Correct file size

---

## Test: File Modification

### Step 7: Append to File
**Action**:
- Type: "append to config.yaml: database_pool: 10"
- Press Enter
- Wait 5 seconds

**Expected Response**:
```
File updated successfully
Path: /home/developer/workspace/config.yaml
New size: 67 bytes (was 52)
Timestamp: [updated time]
```

**Verify**:
- [ ] File updated
- [ ] Size increased (52 → 67 bytes)
- [ ] Timestamp changed
- [ ] No errors

---

### Step 8: Verify Update in Browser
**Action**:
- Look at Files tab
- Check config.yaml size
- If possible, click on file to view content

**Expected**:
- [ ] File size updated to 67 bytes
- [ ] Timestamp shows recent modification
- [ ] Content accessible if UI supports preview

**Verify**:
- [ ] File browser reflects changes
- [ ] Size accurate
- [ ] Modification time current

---

## Test: Directory Operations

### Step 9: Create Subdirectory
**Action**:
- Type: "create directory reports under workspace"
- Press Enter
- Wait 5 seconds

**Expected Response**:
```
Directory created successfully
Path: /home/developer/workspace/reports
Timestamp: [current time]
```

**Verify**:
- [ ] Directory created
- [ ] Path correct
- [ ] No errors

---

### Step 10: Create Files in Subdirectory
**Action**:
- Type: "create file reports/summary.txt with content: Daily Report"
- Press Enter
- Wait 5 seconds

**Expected Response**:
```
File created successfully
Path: /home/developer/workspace/reports/summary.txt
Size: 14 bytes
```

**Verify**:
- [ ] File created in subdirectory
- [ ] Path includes parent folder
- [ ] Size correct

---

### Step 11: Verify Tree Structure
**Action**:
- Click to expand workspace folder in Files tab
- Look for reports subfolder
- Click to expand reports folder

**Expected**:
```
📁 workspace/
  📄 config.yaml
  📄 data.json
  📁 reports/
    📄 summary.txt
```

**Verify**:
- [ ] Nested folder structure visible
- [ ] All files and folders shown
- [ ] Hierarchy correctly represented

---

## Test: Activity Panel Tracking

### Step 12: Check Activity Panel
**Action**:
- Scroll to Activity section
- Look for file-related tool calls

**Expected**:
- [ ] `create_file` tool call
- [ ] `update_file` tool call
- [ ] `create_directory` tool call
- [ ] `get_file_tree` tool call
- [ ] `download_file` tool call

**Verify**:
- [ ] Tool calls recorded
- [ ] Parameters show file paths
- [ ] Timestamps match operations
- [ ] No errors logged

---

## Test: File Persistence

### Step 13: Stop and Restart Agent
**Action**:
- Type in chat: "stop agent"
- Press Enter
- Wait 10 seconds for agent to stop
- In agent list, restart test-files agent
- Wait 15 seconds for startup
- Click test-files again
- Click Files tab

**Expected**:
- [ ] Agent stops and restarts
- [ ] Files tab loads
- [ ] All files still present:
  - config.yaml
  - data.json
  - reports/summary.txt

**Verify**:
- [ ] Files persisted through restart
- [ ] File contents unchanged
- [ ] Timestamps preserved
- [ ] Directory structure intact

---

## Test: Context Growth with File Operations

### Step 14: Check Context After File Operations
**Action**:
- Look at context % in agent detail page header
- Compare to Phase 8 context level

**Expected**:
- [ ] Context % increased from Phase 8
- [ ] Noticeable increase from file operations
- [ ] Progress bar filled accordingly
- [ ] No agent exceeds 200K limit

**Verify**:
- [ ] Context grows with file operations
- [ ] Multiple operations add significant context
- [ ] Color progression visible

---

## Critical Validations

### File Permissions
**Validation**: Only agent can access its files

```bash
# Check file ownership in container
docker exec agent-test-files ls -la /home/developer/workspace/config.yaml
# Should show: developer as owner
```

### File Size Tracking
**Validation**: Reported sizes match actual sizes

```bash
# Check actual file sizes
docker exec agent-test-files stat /home/developer/workspace/config.yaml
# du -sh /home/developer/workspace/
```

### Directory Tree Completeness
**Validation**: All files and folders visible in browser

- [ ] Created files appear in tree
- [ ] Created directories appear in tree
- [ ] Nested structures shown correctly
- [ ] No files hidden or missing

---

## Success Criteria

Phase 9 is **PASSED** when:
- ✅ Files tab loads with directory tree
- ✅ Folder structure expandable/collapsible
- ✅ File created via chat command
- ✅ New file visible in file browser
- ✅ File download link works
- ✅ File modification updates size/timestamp
- ✅ Subdirectory created successfully
- ✅ Files created in subdirectories
- ✅ Nested folder structure visible
- ✅ Tool calls logged in activity panel
- ✅ Files persist after agent restart
- ✅ Context % increased with file operations

---

## Troubleshooting

**Files tab doesn't load**:
- Refresh page (F5)
- Wait 3-5 seconds for data fetch
- Check backend logs: `docker logs backend`

**File creation fails**:
- Check disk space: `docker exec agent-test-files df -h /home/developer/`
- Verify permissions: `docker exec agent-test-files whoami` (should be developer)
- Check logs: `docker logs agent-test-files`

**Files not visible after creation**:
- Refresh Files tab (F5)
- Wait 2 seconds for tree update
- Check actual file exists: `docker exec agent-test-files ls -la /home/developer/workspace/`

**Download link broken**:
- Verify file exists
- Check URL is correct
- Backend may not be serving files
- Check backend logs

**Files lost after restart**:
- Docker volume may not be mounted
- Check volume binding: `docker inspect agent-test-files | grep -i volume`
- Verify mount path: `/home/developer/` should persist

---

## Next Phase

Once Phase 9 is **PASSED**, proceed to:
- **Phase 10**: Error Handling (test-error)

---

**Status**: 🟢 File browser & persistence validated (Pillar III)
**Last Updated**: 2025-12-09
