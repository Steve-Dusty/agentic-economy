# Troubleshooting Guide

This guide helps you diagnose and fix common issues when working with Trinity. Issues are organized by category with clear symptoms, causes, and solutions.

---

## Table of Contents

1. [Installation Issues](#installation-issues)
2. [Agent Startup Issues](#agent-startup-issues)
3. [Agent Runtime Issues](#agent-runtime-issues)
4. [Communication Issues](#communication-issues)
5. [Credential Issues](#credential-issues)
6. [Schedule Issues](#schedule-issues)
7. [Performance Issues](#performance-issues)
8. [Data & Storage Issues](#data--storage-issues)
9. [Network Issues](#network-issues)
10. [Getting More Help](#getting-more-help)

---

## Installation Issues

### Issue: Docker Compose Fails to Start

**Symptoms**:
- `docker compose up` exits with error
- Services fail to start
- "Port already in use" errors

**Diagnosis**:
```bash
# Check if ports are available
netstat -an | grep LISTEN | grep -E "3000|8000|8080|6379|8001"

# Check Docker is running
docker info

# Check disk space
df -h
```

**Solutions**:

**If ports are in use**:
```bash
# Find what's using the port
lsof -i :3000
lsof -i :8000

# Kill the process or change Trinity ports in docker-compose.yml
```

**If Docker isn't running**:
```bash
# macOS
open -a Docker

# Linux
sudo systemctl start docker
```

**If out of disk space**:
```bash
# Clean up Docker
docker system prune -a --volumes

# Remove old images
docker image prune -a
```

---

### Issue: Base Image Build Fails

**Symptoms**:
- `build-base-image.sh` script fails
- "No space left on device"
- Network timeout errors

**Diagnosis**:
```bash
# Check Docker disk usage
docker system df

# Check build logs
docker compose logs backend
```

**Solutions**:

**Out of space**:
```bash
# Free up space
docker system prune -a --volumes

# Increase Docker Desktop disk limit (Settings → Resources)
```

**Network issues**:
```bash
# Retry with verbose output
./scripts/deploy/build-base-image.sh 2>&1 | tee build.log

# Check internet connection
ping google.com
```

**Corrupted cache**:
```bash
# Build with no cache
docker compose build --no-cache backend
```

---

### Issue: Permission Denied Errors

**Symptoms**:
- "Permission denied" when running scripts
- "Cannot connect to Docker daemon"

**Solutions**:

**Script permissions**:
```bash
# Make scripts executable
chmod +x scripts/deploy/*.sh
```

**Docker permissions (Linux)**:
```bash
# Add user to docker group
sudo usermod -aG docker $USER

# Apply immediately
newgrp docker

# Verify
docker ps
```

**macOS/Windows**: Ensure Docker Desktop is running with proper permissions.

---

## Agent Startup Issues

### Issue: Agent Stuck in "Starting" State

**Symptoms**:
- Agent shows "Starting..." for > 2 minutes
- Never transitions to "Running"

**Diagnosis**:
```bash
# Check agent logs
docker logs agent-AGENT-NAME

# Check if container is running
docker ps -a | grep agent-AGENT-NAME
```

**Common Causes & Solutions**:

**1. Anthropic API Key Missing/Invalid**:
```bash
# Check backend logs
docker logs trinity-backend | grep "ANTHROPIC"

# Verify key is set
docker exec trinity-backend env | grep ANTHROPIC_API_KEY
```
**Fix**: Set key in Settings → API Keys or in `.env` file.

**2. Claude Code Image Download Failing**:
```bash
# Check if download is progressing
docker exec agent-AGENT-NAME ps aux

# Check network
docker exec agent-AGENT-NAME ping google.com
```
**Fix**: Wait for download to complete (can take 5-10 minutes first time) or check network.

**3. Port Conflict**:
```bash
# Check if agent's port is available
docker logs agent-AGENT-NAME | grep "address already in use"
```
**Fix**: Trinity auto-assigns ports, but if you have many agents, you might hit limits. Delete unused agents.

**4. Resource Constraints**:
```bash
# Check if host is low on resources
docker stats
free -h  # Linux
```
**Fix**: Close other applications or increase Docker Desktop resources.

---

### Issue: Agent Exits Immediately After Starting

**Symptoms**:
- Agent starts then immediately stops
- Status shows "Exited (1)" or similar

**Diagnosis**:
```bash
# View exit logs
docker logs agent-AGENT-NAME

# Check exit code
docker inspect agent-AGENT-NAME | grep ExitCode
```

**Common Causes**:

**Missing template files**:
```
Error: CLAUDE.md not found
```
**Fix**: Ensure template repository has `CLAUDE.md` file.

**Invalid template.yaml**:
```
Error: Failed to parse template.yaml
```
**Fix**: Validate YAML syntax, check required fields.

**Credential injection failed**:
```
Error: Missing required credential: TWITTER_API_KEY
```
**Fix**: Add required credentials before creating agent.

---

### Issue: Agent Container Not Created

**Symptoms**:
- Create agent button succeeds
- No container appears in `docker ps -a`
- Backend logs show errors

**Diagnosis**:
```bash
# Check backend logs for agent creation
docker logs trinity-backend | tail -100

# Check if Docker socket is accessible
docker exec trinity-backend ls -la /var/run/docker.sock
```

**Solutions**:

**Docker socket permission issues**:
```bash
# Check backend can access Docker
docker exec trinity-backend docker ps
```

**Base image missing**:
```bash
# Check if base image exists
docker images | grep trinity-agent-base

# Rebuild if missing
./scripts/deploy/build-base-image.sh
```

---

## Agent Runtime Issues

### Issue: Agent Not Responding to Messages

**Symptoms**:
- Chat messages stuck in "Sending..." state
- No response after several minutes
- No errors in UI

**Diagnosis**:
```bash
# Check if agent is actually running
docker ps | grep agent-AGENT-NAME

# Check agent logs
docker logs -f agent-AGENT-NAME

# Check backend logs
docker logs -f trinity-backend
```

**Solutions**:

**Agent crashed**:
```bash
# Restart agent
docker restart agent-AGENT-NAME

# Or via UI: Stop → Start
```

**Context window full**:
- Check context bar in UI
- If near 100%, reset context: Agent → Reset Context

**Agent busy with long-running task**:
- Wait for current task to complete
- Check Activity tab to see what it's doing
- Cancel task if stuck (restart agent)

**API rate limit hit**:
```bash
# Check logs for rate limit errors
docker logs agent-AGENT-NAME | grep -i "rate limit"
```
**Fix**: Wait for rate limit to reset, or add delay between requests.

---

### Issue: Agent Giving Nonsensical Responses

**Symptoms**:
- Agent responses don't make sense
- Agent confused about context
- Agent repeating same responses

**Solutions**:

**1. Context Window Polluted**:
- **Fix**: Reset context via UI

**2. Conflicting Instructions**:
- Check `CLAUDE.md` for contradictions
- Simplify instructions
- Remove ambiguous guidance

**3. Too Many Tools**:
- Agent overwhelmed by options
- **Fix**: Reduce number of MCP servers
- Be more specific in instructions about when to use which tool

**4. Memory Issues**:
```bash
# Check if agent is hitting memory limits
docker stats agent-AGENT-NAME
```
**Fix**: Increase memory in template.yaml and recreate agent.

---

### Issue: Agent Not Using MCP Tools

**Symptoms**:
- Agent says "I don't have access to that tool"
- No MCP tool calls in Activity tab
- Expected MCP functionality not working

**Diagnosis**:
```bash
# Check if MCP config exists
docker exec agent-AGENT-NAME cat /home/developer/.mcp.json

# Check for MCP errors in logs
docker logs agent-AGENT-NAME | grep -i mcp
```

**Solutions**:

**MCP config not generated**:
- Check if `.mcp.json.template` exists in template
- Verify credentials are injected
- Restart agent

**MCP server failed to start**:
```bash
# Check Claude Code logs for server errors
docker logs agent-AGENT-NAME | grep -i "failed to start"
```
**Fix**: Check MCP server configuration syntax, verify credentials.

**Agent not instructed to use tools**:
- Update `CLAUDE.md` to explicitly mention available tools
- Give examples of when/how to use them

---

## Communication Issues

### Issue: Agents Can't See Each Other

**Symptoms**:
- Agent A tries to list agents, doesn't see Agent B
- "Permission denied" when trying to chat
- Trinity MCP tools return empty lists

**Diagnosis**:
```bash
# Check permissions
curl http://localhost:8000/api/agents/agent-a/permissions \
  -H "Authorization: Bearer $TOKEN"

# Check both agents are running
docker ps | grep agent-
```

**Solutions**:

**Missing permissions**:
1. Go to Agent A → Permissions tab
2. Grant permission to Agent B
3. Repeat in reverse if bidirectional needed

**Agent not running**:
```bash
# Start the target agent
docker start agent-AGENT-B
```

**Network isolation issue**:
```bash
# Check agents are on same Docker network
docker network inspect trinity-agent-network
```
All agents should be listed. If not:
```bash
# Recreate agent to attach to network
docker stop agent-AGENT-NAME
docker rm agent-AGENT-NAME
# Create again via Trinity UI
```

---

### Issue: Shared Folders Empty or Not Accessible

**Symptoms**:
- `shared-in/other-agent/` directory empty
- Files not appearing that should be there
- Permission denied reading shared files

**Diagnosis**:
```bash
# Check if source agent has sharing enabled
curl http://localhost:8000/api/agents/source-agent/folders \
  -H "Authorization: Bearer $TOKEN"

# Check if target agent has consume enabled
curl http://localhost:8000/api/agents/target-agent/folders \
  -H "Authorization: Bearer $TOKEN"

# Check folder contents in source
docker exec agent-source-agent ls -la /home/developer/shared-out

# Check folder mount in target
docker exec agent-target-agent ls -la /home/developer/shared-in
```

**Solutions**:

**Sharing not enabled**:
1. Source agent → Shared Folders → Enable "Expose"
2. Target agent → Shared Folders → Enable "Consume"
3. **Restart both agents** (required!)

**Permission not granted**:
- Sharing only works between agents with granted permissions
- Grant permission from source to target

**Files in wrong location**:
- Source agent must write to `/home/developer/shared-out/`
- Not `workspace/` or other directories

**Agent not restarted**:
- Folder mounts only apply after restart
- Always restart agents after changing folder settings

---

## Credential Issues

### Issue: Credentials Not Found

**Symptoms**:
- Agent errors about missing API keys
- MCP server fails to start
- "Missing required credential" errors

**Diagnosis**:
```bash
# Check credential status
curl http://localhost:8000/api/agents/AGENT-NAME/credentials/status \
  -H "Authorization: Bearer $TOKEN"

# Check .mcp.json generation
docker exec agent-AGENT-NAME cat /home/developer/.mcp.json

# Check .env file
docker exec agent-AGENT-NAME cat /home/developer/.env
```

**Solutions**:

**Credentials not stored**:
1. Go to Settings → Credentials
2. Add the missing credentials
3. Reload agent credentials

**Placeholder mismatch**:
- `.mcp.json.template` has `${TWITTER_API_KEY}`
- But credential stored as `TWITTER_KEY`
- **Fix**: Names must match exactly (case-sensitive)

**Credentials not injected**:
```bash
# Manually reload
curl -X POST http://localhost:8000/api/agents/AGENT-NAME/credentials/reload \
  -H "Authorization: Bearer $TOKEN"
```

---

### Issue: Hot-Reload Not Working

**Symptoms**:
- Updated credentials via hot-reload
- Agent still using old values
- MCP tools still failing with auth errors

**Solutions**:

**1. MCP server needs restart**:
- Some MCP servers cache credentials
- **Fix**: Stop and start agent (not just hot-reload)

**2. .mcp.json not regenerated**:
```bash
# Check if .mcp.json updated
docker exec agent-AGENT-NAME cat /home/developer/.mcp.json
```
**Fix**: Reload via API instead of UI.

**3. Credential format wrong**:
- Hot-reload expects `KEY=VALUE` format
- One per line
- No quotes around values

---

## Schedule Issues

### Issue: Schedule Not Running

**Symptoms**:
- Expected schedule execution never happens
- Execution history empty
- No errors shown

**Diagnosis**:
```bash
# Check schedule configuration
curl http://localhost:8000/api/agents/AGENT-NAME/schedules \
  -H "Authorization: Bearer $TOKEN"

# Check backend scheduler logs
docker logs trinity-backend | grep -i schedule

# Check if agent is running
docker ps | grep agent-AGENT-NAME
```

**Solutions**:

**Schedule disabled**:
- Check **Enabled** toggle is ON

**Cron expression invalid**:
- Test at [crontab.guru](https://crontab.guru/)
- Common mistake: Wrong field count (must be 5 fields)

**Timezone mismatch**:
- Schedule says "9 AM" but set to wrong timezone
- **Fix**: Update timezone to match your location

**Agent stopped**:
- Schedules only run if agent is running
- **Fix**: Start the agent

**Backend scheduler crashed**:
```bash
# Restart backend
docker restart trinity-backend
```

---

### Issue: Schedule Executes But Agent Does Nothing

**Symptoms**:
- Execution history shows "Success"
- But agent didn't do expected work
- No errors logged

**Solutions**:

**1. Check message content**:
- Schedule message might be vague
- **Fix**: Be specific: "Run daily report workflow: gather data, analyze, create summary.md"

**2. Check agent's CLAUDE.md**:
- Agent might not understand what to do
- **Fix**: Add workflow documentation for scheduled tasks

**3. Check Activity tab**:
- Agent might have done something, just not what you expected
- Review what tools were called

---

### Issue: Schedule Execution Fails

**Symptoms**:
- Execution history shows "Failed"
- Errors in execution log

**Diagnosis**:
```bash
# View failed execution details
# Via UI: Schedules → Click schedule → Execution History → Click failed execution

# Or check agent logs at time of execution
docker logs agent-AGENT-NAME --since "2025-12-23T09:00:00"
```

**Common Causes**:
- Credential expired/missing
- External API down
- Agent hit context limit
- File permission issue

**Fix**: Address the specific error shown in logs.

---

## Performance Issues

### Issue: System Very Slow

**Symptoms**:
- UI laggy
- Agents respond slowly
- Commands take forever

**Diagnosis**:
```bash
# Check system resources
docker stats

# Check disk usage
docker system df
df -h

# Check network latency
ping api.anthropic.com
```

**Solutions**:

**High CPU usage**:
```bash
# See which container is using CPU
docker stats --no-stream | sort -k3 -h
```
- Stop unused agents
- Restart problematic agent
- Increase Docker CPU limit

**High memory usage**:
- Close unused agents
- Restart agents periodically
- Increase Docker memory limit
- Check for memory leaks (agent running for weeks)

**Disk full**:
```bash
# Clean up Docker
docker system prune -a --volumes

# Check agent workspaces
du -sh /var/lib/docker/volumes/*
```

**Network issues**:
- Check internet connection
- Try different network
- Check if Anthropic API is down: [status.anthropic.com](https://status.anthropic.com)

---

### Issue: Agent Using Too Much Memory

**Symptoms**:
- Agent container killed with OOM
- "Out of memory" in logs
- Agent keeps restarting

**Diagnosis**:
```bash
# Check memory usage
docker stats agent-AGENT-NAME

# Check memory limit
docker inspect agent-AGENT-NAME | grep Memory
```

**Solutions**:

**1. Increase memory limit**:
- Edit template.yaml: `memory: "8g"` (was 4g)
- Recreate agent

**2. Reset context regularly**:
- Context bloat causes memory issues
- Use `/trinity-plan-*` commands to persist outside context
- Reset context after major workflows

**3. Optimize agent behavior**:
- Store data in files, not in context
- Use vector memory for large datasets
- Avoid loading huge files into memory

**4. Check for leaks**:
```bash
# Restart agent
docker restart agent-AGENT-NAME

# If memory grows again quickly, might be a leak
# Report to Trinity team
```

---

### Issue: Slow API Responses

**Symptoms**:
- Agent takes 30+ seconds to respond
- Other agents timing out waiting
- High latency

**Causes & Solutions**:

**Context window too large**:
- Check context bar in UI
- **Fix**: Reset context

**Using wrong Claude model**:
- Sonnet is faster than Opus
- Check which model agent is using

**Complex tool chains**:
- Agent making 10+ tool calls per response
- **Fix**: Simplify workflows, batch operations

**Rate limiting**:
```bash
# Check logs for rate limit errors
docker logs agent-AGENT-NAME | grep "429"
```
**Fix**: Add delays between requests, use cheaper models for non-critical tasks.

---

## Data & Storage Issues

### Issue: Vector Memory Not Persisting

**Symptoms**:
- Agent forgets stored knowledge after restart
- Vector queries return empty results
- `vector-store/` directory empty

**Diagnosis**:
```bash
# Check if vector-store exists
docker exec agent-AGENT-NAME ls -la /home/developer/vector-store

# Check Chroma files
docker exec agent-AGENT-NAME ls -la /home/developer/vector-store/chroma.sqlite3
```

**Solutions**:

**Database not created**:
- Agent needs to use Chroma MCP tools to create collections
- Check if agent ever called vector memory tools

**Volume not persisting**:
```bash
# Check Docker volumes
docker volume ls | grep agent-AGENT-NAME
```
If no volume, agent might be using ephemeral storage.

**Agent recreated without preserving data**:
- When you delete and recreate agent, data is lost
- **Fix**: Backup before deleting

---

### Issue: Files Disappearing from Agent Workspace

**Symptoms**:
- Files agent created are gone after restart
- Workspace resets to initial state

**Cause**: Agent is being fully recreated (not just restarted).

**Solutions**:

**Use persistent directories**:
- `workspace/` should persist across restarts
- Check if Docker volume is attached

**Backup important data**:
```bash
# Regular backups
docker exec agent-AGENT-NAME tar czf /tmp/backup.tar.gz /home/developer/workspace
docker cp agent-AGENT-NAME:/tmp/backup.tar.gz ./backups/
```

**Use external storage**:
- Shared folders (persist as Docker volumes)
- External databases
- Cloud storage via APIs

---

## Network Issues

### Issue: Agent Can't Reach External APIs

**Symptoms**:
- MCP tools fail with connection errors
- "Network unreachable" in logs
- Timeouts connecting to external services

**Diagnosis**:
```bash
# Test network from agent
docker exec agent-AGENT-NAME ping google.com
docker exec agent-AGENT-NAME curl https://api.anthropic.com
docker exec agent-AGENT-NAME nslookup google.com
```

**Solutions**:

**Docker network issue**:
```bash
# Restart Docker networking
docker network disconnect trinity-agent-network agent-AGENT-NAME
docker network connect trinity-agent-network agent-AGENT-NAME
```

**Firewall blocking**:
- Check if corporate firewall blocks API endpoints
- Try from host machine: `curl https://api.anthropic.com`

**DNS resolution failing**:
```bash
# Add custom DNS to docker-compose.yml
dns:
  - 8.8.8.8
  - 8.8.4.4
```

---

### Issue: Can't Access Trinity UI

**Symptoms**:
- `http://localhost:3000` doesn't load
- "Connection refused"
- Page never loads

**Diagnosis**:
```bash
# Check if frontend is running
docker ps | grep trinity-frontend

# Check frontend logs
docker logs trinity-frontend

# Check if port is open
curl http://localhost:3000
```

**Solutions**:

**Frontend not started**:
```bash
docker compose up -d frontend
```

**Port conflict**:
```bash
# Check what's using port 3000
lsof -i :3000

# Change port in docker-compose.yml if needed
```

**Backend not reachable**:
- Frontend needs backend at `http://localhost:8000`
- Check backend is running: `docker ps | grep trinity-backend`

---

## Getting More Help

### Diagnostic Information to Collect

When asking for help, gather:

```bash
# Trinity version
git log -1 --oneline

# Docker version
docker --version
docker compose version

# System info
uname -a
docker info

# Service status
docker compose ps

# Recent logs
docker compose logs --tail=100 backend > backend.log
docker compose logs --tail=100 frontend > frontend.log
docker logs --tail=100 agent-AGENT-NAME > agent.log
```

### Where to Get Help

1. **Documentation**:
   - [Trinity Compatible Agent Guide](../TRINITY_COMPATIBLE_AGENT_GUIDE.md)
   - [Multi-Agent System Guide](../MULTI_AGENT_SYSTEM_GUIDE.md)
   - [Development Workflow](../DEVELOPMENT_WORKFLOW.md)

2. **GitHub Issues**:
   - Search existing issues: https://github.com/abilityai/trinity/issues
   - Create new issue with diagnostic info
   - Use issue templates

3. **API Documentation**:
   - Interactive docs: http://localhost:8000/docs
   - Try API calls directly to debug

4. **Community**:
   - Check GitHub discussions
   - Review example agent templates

### Reporting Bugs

When filing a bug report, include:

- [ ] Trinity version (git commit hash)
- [ ] Docker version
- [ ] Operating system
- [ ] Steps to reproduce
- [ ] Expected behavior
- [ ] Actual behavior
- [ ] Relevant logs (backend, frontend, agent)
- [ ] Screenshots if applicable

### Commercial Support

For commercial licensing and priority support:
- Email: hello@ability.ai

---

## Quick Checklist for Common Issues

When something goes wrong, work through this checklist:

- [ ] Check all containers are running: `docker compose ps`
- [ ] Check logs for errors: `docker compose logs`
- [ ] Check agent is running: `docker ps | grep agent-NAME`
- [ ] Check agent logs: `docker logs agent-NAME`
- [ ] Try restarting agent: `docker restart agent-NAME`
- [ ] Check credentials are loaded
- [ ] Check permissions are granted (if multi-agent)
- [ ] Check shared folders are enabled (if using them)
- [ ] Check schedules are enabled (if automated)
- [ ] Check disk space: `df -h`
- [ ] Check Docker resources: `docker stats`
- [ ] Try restarting Trinity: `docker compose restart`
- [ ] Check for updates: `git pull`

---

**Most issues can be resolved by carefully checking logs and verifying configuration. When in doubt, restart the problematic component.** 🔧





