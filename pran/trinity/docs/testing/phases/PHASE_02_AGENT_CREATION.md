# Phase 2: Agent Creation (Local Templates)

> **Purpose**: Validate agent creation from local templates for test agents
> **Duration**: ~15 minutes (agents need time to initialize)
> **Assumes**: Phase 1 PASSED (logged in, clean slate)
> **Output**: 3 agents created from local templates, all running

---

## Prerequisites

- ✅ Phase 1 PASSED
- ✅ Logged in as admin
- ✅ Dashboard shows "No agents"
- ✅ Local templates available (test-echo, test-counter, test-delegator)

---

## Overview

You will create 3 agents from available local templates:
1. test-echo - Basic terminal commands
2. test-counter - State persistence
3. test-delegator - Agent-to-agent communication

**Timeline**: Each agent takes 30-60 seconds to create and ~10-15 seconds to initialize.

---

## Agent Creation Procedure (Repeat 3 times)

### For Each Agent:

#### Step 1: Via API (Recommended)
**Action**: Create agent via API endpoint

```bash
TOKEN="<from Phase 1>"
AGENT_NAME="test-echo"  # change for each agent
TEMPLATE="local:test-echo"  # change for each agent

curl -X POST http://localhost:8000/api/agents \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{
    \"name\": \"$AGENT_NAME\",
    \"template\": \"$TEMPLATE\"
  }"
```

**Expected Response**:
```json
{
  "name": "test-echo",
  "status": "starting",
  "type": "business-assistant",
  "template": "local:test-echo",
  "port": 2290
}
```

**Verify**:
- [ ] HTTP 201 (Created) status
- [ ] `name` matches request
- [ ] `template` = `local:test-*`
- [ ] `status` = "starting"
- [ ] `port` assigned (2290+)

---

#### Step 2: Verify in UI
**Action**: Navigate to http://localhost/agents

**Expected**:
- [ ] Agent card appears in list
- [ ] Status shows "Starting" (yellow badge)
- [ ] Agent name displayed: "test-echo"
- [ ] "No agents" message gone

**Wait 10-15 seconds** for agent to initialize

**After Wait**:
- [ ] Status transitions to "Running" (green badge)
- [ ] Telemetry appears: CPU, MEM, NET, Uptime

---

#### Step 3: Verify Docker Container
**Action**: Check container created
```bash
docker ps --filter "label=trinity.agent-name=test-echo"
```

**Expected**:
```
CONTAINER ID   IMAGE                    STATUS         PORTS
abc123...      trinity-agent-base:...   Up 20 seconds  0.0.0.0:2290->22/tcp
```

**Verify**:
- [ ] Container exists
- [ ] Status = "Up X seconds"
- [ ] Port mapping correct (2290->22)
- [ ] Image = trinity-agent-base:latest

---

#### Step 4: Verify Template in Container Labels
**Action**: Check Docker labels

```bash
docker inspect agent-test-echo --format='{{json .Config.Labels}}' | jq .
```

**Expected Output** (partial):
```json
{
  "trinity.template": "local:test-echo",
  "trinity.agent-name": "test-echo",
  "trinity.platform": "agent"
}
```

**Verify**:
- [ ] `trinity.template` = `local:test-echo`
- [ ] `trinity.agent-name` matches
- [ ] `trinity.platform` = "agent"

---

#### Step 5: Verify Trinity Injection
**Action**: Check meta-prompt was injected

```bash
docker exec agent-test-echo cat /home/developer/.trinity/prompt.md | head -5
```

**Expected**: First few lines of Trinity meta-prompt

```
# Trinity Planning System
...
```

**Verify**:
- [ ] `.trinity/prompt.md` exists
- [ ] File contains planning prompt text

---

#### Step 6: Verify API Metadata
**Action**: Get agent details

```bash
curl http://localhost:8000/api/agents/test-echo \
  -H "Authorization: Bearer $TOKEN"
```

**Expected Response**:
```json
{
  "name": "test-echo",
  "status": "running",
  "type": "business-assistant",
  "template": "local:test-echo",
  "owner": "admin",
  "created_at": "2026-01-14T...",
  "port": 2290,
  ...
}
```

**Verify**:
- [ ] `status` = "running"
- [ ] `template` = "local:test-echo"
- [ ] `owner` = "admin"

---

#### Step 7: Verify Default Permissions Granted (Req 9.10)
**Action**: Check agent received default permissions for same-owner agents

```bash
curl http://localhost:8000/api/agents/test-echo/permissions \
  -H "Authorization: Bearer $TOKEN" | jq .
```

**Expected Response** (after first agent - minimal):
```json
{
  "source_agent": "test-echo",
  "permitted_agents": [],
  "available_agents": []
}
```

**Expected Response** (after multiple agents created):
```json
{
  "source_agent": "test-echo",
  "permitted_agents": [
    {"name": "test-counter", "status": "running", "permitted": true},
    {"name": "test-delegator", "status": "running", "permitted": true}
  ],
  "available_agents": [...]
}
```

**Verify**:
- [ ] HTTP 200 response
- [ ] `source_agent` matches agent name
- [ ] Other same-owner agents appear in `permitted_agents`
- [ ] Permissions are bidirectional (if test-echo can see test-counter, test-counter can see test-echo)

**Note**: As each new agent is created, it automatically receives bidirectional permissions with all existing same-owner agents.

---

### Repeat Steps 1-7 for Each Agent

Create agents in this order:

| Agent | Template | Notes |
|-------|----------|-------|
| test-echo | local:test-echo | Basic chat, no special setup |
| test-counter | local:test-counter | Stateful, file I/O |
| test-delegator | local:test-delegator | Requires Trinity MCP injection |

---

## Dashboard Verification

Once all 3 agents created:

**Action**: Navigate to http://localhost/ (Dashboard)

**Expected**:
- [ ] 3 agent nodes visible in graph
- [ ] All nodes show green status (running)
- [ ] All show "Idle" state
- [ ] Context shows 0% for each
- [ ] Tasks show "—" for each
- [ ] Stats bar shows: "3 agents · 3 running · 0 messages"
- [ ] No overlapping nodes
- [ ] Mini-map visible in corner

---

## Agents Page Verification

**Action**: Navigate to http://localhost/agents

**Expected**:
- [ ] 3 agent cards in list
- [ ] All show "running" status (green)
- [ ] Each shows correct port (2290-2292)
- [ ] Each shows "Context 0%"
- [ ] Each shows template name
- [ ] Newest first sorting shows: test-delegator, test-counter, test-echo

---

## Critical Validations

### Local Templates
**Validation**: EVERY agent must have local template

For each agent:
```bash
curl http://localhost:8000/api/agents/$AGENT_NAME \
  -H "Authorization: Bearer $TOKEN" \
  | jq .template
```

**Expected**:
```
"local:test-echo"  ✅
"local:test-counter"  ✅
"local:test-delegator"  ✅
```

### Docker Labels Verification
```bash
for agent in test-echo test-counter test-delegator; do
  echo "=== $agent ==="
  docker inspect agent-$agent --format='{{index .Config.Labels "trinity.template"}}'
done
```

**Expected**: All show `local:test-*`

---

## Success Criteria

Phase 2 is **PASSED** when:
- ✅ 3 agents created successfully
- ✅ All agents use local templates (local:test-*)
- ✅ All agents show "running" status
- ✅ All have Trinity meta-prompt injected
- ✅ Dashboard shows all 3 nodes
- ✅ All initialized (green status, CPU/MEM visible)
- ✅ **Default permissions granted** - Each agent has bidirectional permissions with other same-owner agents (Req 9.10)

---

## Troubleshooting

**Agent stuck on "Starting"**:
- Wait 20-30 seconds
- Check logs: `docker logs agent-test-echo | tail -20`
- If persistent, delete and recreate

**Template not found**:
- Check available templates: `curl http://localhost:8000/api/templates`
- Verify template directory exists in config/agent-templates/

**Port conflict**:
- Verify no other containers using 2290-2297
- Docker automatically assigns next available

---

## Next Phase

Once Phase 2 is **PASSED**, proceed to:
- **Phase 3**: Basic Chat & Context Validation (test-echo)
- **Phase 4**: State Persistence (test-counter)
- ... (other phases in order)

---

**Status**: Ready for Testing
**Last Updated**: 2026-01-14
