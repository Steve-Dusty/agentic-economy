# Phase 26: Shared Folders

> **Purpose**: Validate file-based collaboration between agents via shared Docker volumes
> **Duration**: ~20 minutes
> **Assumes**: Phase 2 PASSED (agents running), Phase 5 PASSED (permissions set)
> **Output**: Shared folder expose/consume flow verified

---

## Background

**Shared Folders** (FOLDER-001 to FOLDER-004):
- Agents expose a `shared-out` folder via Docker volume
- Consuming agents mount exposed folders as `shared-in/{agent-name}`
- Permission-gated: only permitted agents can mount
- Container recreation required when mount config changes

**User Stories**:
- FOLDER-001: Expose shared folder
- FOLDER-002: Consume other agents' folders
- FOLDER-003: See available folders
- FOLDER-004: See folder consumers

---

## Prerequisites

- [ ] Phase 2 PASSED (multiple agents running)
- [ ] Phase 5 PASSED (agent permissions configured)
- [ ] At least 2 agents owned by same user (or with permissions)

**Setup**: Use test-echo (will expose) and test-worker (will consume)

---

## Test: Expose Shared Folder

### Step 1: Navigate to Folders Tab
**Action**:
- Go to agent detail page for test-echo
- Click "Folders" tab

**Expected**:
- [ ] Folders tab loads
- [ ] "Expose Folder" toggle visible
- [ ] "Consume Folders" toggle visible
- [ ] Current status displayed

---

### Step 2: Enable Expose
**Action**:
- Toggle "Expose Folder" ON
- Confirm if prompted

**Expected**:
- [ ] Toggle switches to ON
- [ ] Message: "Agent will restart to apply changes"
- [ ] Status shows exposing enabled

**Verify**:
- [ ] Database updated
- [ ] Container recreated with volume

```bash
# Check volume exists
docker volume ls | grep test-echo
```

---

### Step 3: Verify Expose Directory
**Action**:
- In Terminal, send: "List files in /home/developer/shared-out"

**Expected**:
- [ ] Directory exists
- [ ] Empty or has default files
- [ ] Writable by agent

**Verify**:
```bash
docker exec agent-test-echo ls -la /home/developer/shared-out
```

---

### Step 4: Create File in Shared Folder
**Action**:
- In Terminal, send: "Create a file at shared-out/data.txt with content: Hello from test-echo"

**Expected**:
- [ ] File created
- [ ] Path: /home/developer/shared-out/data.txt
- [ ] Content written

**Verify**:
```bash
docker exec agent-test-echo cat /home/developer/shared-out/data.txt
# Should output: Hello from test-echo
```

---

## Test: Consume Shared Folder

### Step 5: Navigate to Consumer Agent Folders
**Action**:
- Go to test-worker agent detail
- Click "Folders" tab

**Expected**:
- [ ] Folders tab loads
- [ ] "Available Folders" section
- [ ] test-echo folder listed (if permissions allow)

---

### Step 6: Check Available Folders
**Action**:
- Look at "Available Folders" section

**Expected**:
- [ ] test-echo listed
- [ ] Status: exposing
- [ ] Mount path shown

**Note**: Only folders from permitted agents shown.

---

### Step 7: Enable Consume
**Action**:
- Toggle "Consume Folders" ON
- Confirm restart prompt

**Expected**:
- [ ] Toggle switches to ON
- [ ] Agent restarts
- [ ] Volume mounted at /home/developer/shared-in/test-echo

**Verify**:
```bash
docker exec agent-test-worker ls -la /home/developer/shared-in/
# Should show test-echo directory
```

---

### Step 8: Verify File Access
**Action**:
- In test-worker Terminal, send: "Read the file at shared-in/test-echo/data.txt"

**Expected**:
- [ ] File readable
- [ ] Content: "Hello from test-echo"
- [ ] Cross-agent file sharing works

**Verify**:
```bash
docker exec agent-test-worker cat /home/developer/shared-in/test-echo/data.txt
```

---

## Test: Bidirectional File Sharing

### Step 9: Write from Consumer
**Action**:
- In test-worker Terminal, send: "Create file at shared-in/test-echo/response.txt with content: Response from test-worker"

**Expected**:
- [ ] File created in shared folder
- [ ] Visible from test-echo as well

**Verify**:
```bash
# From test-echo container
docker exec agent-test-echo cat /home/developer/shared-out/response.txt
```

---

### Step 10: Verify from Exposer
**Action**:
- In test-echo Terminal, send: "List files in shared-out/"

**Expected**:
- [ ] data.txt (created by test-echo)
- [ ] response.txt (created by test-worker)
- [ ] Both files visible

---

## Test: See Folder Consumers

### Step 11: Check Who Mounts Your Folder
**Action**:
- On test-echo Folders tab
- Look for "Consumers" or "Who's Mounting" section

**Expected**:
- [ ] test-worker listed as consumer
- [ ] Mount status: active
- [ ] Timestamp of mount

**API Check**:
```bash
curl -H "Authorization: Bearer {token}" \
  http://localhost:8000/api/agents/test-echo/folders/consumers
```

---

## Test: Permission Enforcement

### Step 12: Test Permission Denied
**Action**:
- Create new agent without permissions to test-echo
- Enable consume on new agent
- Check available folders

**Expected**:
- [ ] test-echo NOT in available folders list
- [ ] Permission required to mount

**Verify**:
- [ ] Volume not mounted
- [ ] shared-in/test-echo doesn't exist

---

### Step 13: Grant Permission and Retry
**Action**:
- Grant permission: test-echo can call new-agent (or vice versa)
- Refresh available folders

**Expected**:
- [ ] test-echo now appears in available folders
- [ ] Can enable consume
- [ ] Mount succeeds after restart

---

## Test: Disable Shared Folders

### Step 14: Disable Expose
**Action**:
- On test-echo, toggle "Expose Folder" OFF
- Confirm restart

**Expected**:
- [ ] Exposing disabled
- [ ] Agent restarts
- [ ] Volume no longer exposed

**Verify**:
- [ ] Consumers see folder unavailable
- [ ] Mount may fail or show empty

---

### Step 15: Disable Consume
**Action**:
- On test-worker, toggle "Consume Folders" OFF
- Confirm restart

**Expected**:
- [ ] Consuming disabled
- [ ] shared-in directory empty or removed

---

## Test: Edge Cases

### Step 16: Large File Transfer
**Action**:
- Create large file (10MB) in shared folder
- Access from consumer

**Expected**:
- [ ] Large file transfers work
- [ ] No timeout or corruption

---

### Step 17: Concurrent Access
**Action**:
- Both agents write to same file simultaneously

**Expected**:
- [ ] Last write wins (or conflict detected)
- [ ] No corruption
- [ ] System remains stable

---

## Critical Validations

### Volume Mounts
**Validation**: Docker volumes correctly configured

```bash
docker inspect agent-test-echo --format='{{json .Mounts}}' | jq
# Should show volume for shared-out

docker inspect agent-test-worker --format='{{json .Mounts}}' | jq
# Should show bind mount for shared-in/test-echo
```

### Permission Enforcement
**Validation**: Cannot mount without permission

- [ ] Remove permission between agents
- [ ] Restart consumer
- [ ] Verify mount fails or folder not present

### File Permissions
**Validation**: Files accessible by both agents

```bash
# Check owner is developer (UID 1000)
docker exec agent-test-echo ls -la /home/developer/shared-out/
docker exec agent-test-worker ls -la /home/developer/shared-in/test-echo/
```

---

## Success Criteria

Phase 26 is **PASSED** when:
- [ ] Folders tab loads for agents
- [ ] Expose toggle enables shared-out volume
- [ ] Files created in shared-out persist
- [ ] Available folders show permitted exposing agents
- [ ] Consume toggle mounts permitted folders
- [ ] Consumer can read files from shared-in/{agent}
- [ ] Consumer can write to shared folders
- [ ] Exposer sees files from consumers
- [ ] Folder consumers list displayed
- [ ] Permission enforcement prevents unauthorized mounts
- [ ] Granting permission enables mounting
- [ ] Disabling expose/consume works correctly

---

## Troubleshooting

**Folders tab not visible**:
- Feature may be disabled
- Check agent has folders config in database

**Expose not working**:
- Container may not have restarted
- Check Docker volume created
- Verify lifecycle recreates container

**Consume shows no available folders**:
- Permissions not granted
- Exposer hasn't enabled expose
- Same owner required or explicit permission

**Files not visible**:
- Volume mount may have failed
- Check UID 1000 ownership
- Verify volume path correct

**Permission denied on files**:
- UID mismatch between containers
- Check volume ownership
- May need `chown` fix in lifecycle

---

## Next Phase

Once Phase 26 is **PASSED**, proceed to:
- **Phase 27**: Public Access

---

**Status**: Ready for Testing
**Last Updated**: 2026-01-14
**User Stories**: FOLDER-001 to FOLDER-004
