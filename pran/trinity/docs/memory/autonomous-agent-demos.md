# Autonomous Agent Demo: Research Network

> **Purpose**: Step-by-step guide to deploy an autonomous multi-agent research system on Trinity.
> **Setup Time**: 2-3 hours
> **Agents**: 2 (researcher + analyst)
>
> **Created**: 2025-12-14
> **Updated**: 2026-01-01 - Simplified to focused Research Network demo

---

## Demo Overview

A two-agent autonomous research network that demonstrates:
- **Scheduled execution** - Researcher runs on cron schedule
- **Shared folders** - Findings passed between agents via files
- **Agent collaboration** - Analyst can query researcher via MCP
- **Real-time dashboard** - Watch collaboration edges light up

```
┌─────────────────────────────────────────────────────────────────┐
│                    RESEARCH NETWORK                              │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│   ┌─────────────────┐                                            │
│   │    RESEARCHER   │  ◀── Scheduled: Every 4 hours              │
│   │                 │      Task: Research trending topics         │
│   │  - Web search   │      Output: findings.md in shared folder  │
│   │  - Summarize    │                                            │
│   │  - Write report │                                            │
│   └────────┬────────┘                                            │
│            │                                                      │
│            │ writes to                                            │
│            ▼                                                      │
│   ┌─────────────────┐                                            │
│   │  SHARED FOLDER  │  /shared-out/findings/                     │
│   │                 │  - YYYY-MM-DD-findings.md                  │
│   │                 │  - summary.md (rolling)                    │
│   └────────┬────────┘                                            │
│            │                                                      │
│            │ reads from                                           │
│            ▼                                                      │
│   ┌─────────────────┐                                            │
│   │     ANALYST     │  ◀── On-demand or scheduled daily          │
│   │                 │      Task: Synthesize findings, answer Qs  │
│   │  - Read findings│      Can also call researcher via MCP      │
│   │  - Synthesize   │                                            │
│   │  - Report       │                                            │
│   └─────────────────┘                                            │
│                                                                   │
└─────────────────────────────────────────────────────────────────┘
```

---

## What You'll See in the Demo

1. **Dashboard**: Two agent nodes with status indicators
2. **Scheduled Execution**: Researcher auto-runs every 4 hours (or manual trigger)
3. **Collaboration Edge**: Animated connection when analyst calls researcher
4. **File Output**: Research findings accumulating in shared folder
5. **Execution Stats**: Task counts, success rates, costs on agent cards

---

## Implementation

### Step 1: Create Agent Templates

Create two template directories in `config/agent-templates/`:

#### 1.1 Researcher Template

**File: `config/agent-templates/demo-researcher/template.yaml`**
```yaml
name: demo-researcher
display_name: Research Agent
description: Autonomous researcher that gathers and summarizes information on trending topics
version: "1.0.0"
author: Trinity Demo

resources:
  cpu: "1"
  memory: "2g"

capabilities:
  - web-search
  - summarization
  - report-generation

# Default schedule (can be overridden in manifest)
schedules:
  - name: research-cycle
    cron: "0 */4 * * *"  # Every 4 hours
    message: "/research"
    description: Regular research cycle
```

**File: `config/agent-templates/demo-researcher/CLAUDE.md`**
```markdown
# Research Agent

You are an autonomous research agent. Your job is to discover and summarize interesting trends, opportunities, and insights.

## Your Mission

When triggered (via schedule or manual), you should:
1. Search for trending topics in technology, startups, and AI
2. Identify interesting patterns or opportunities
3. Write a structured findings report
4. Save it to your shared folder for the analyst

## Output Location

Save all findings to: `/home/developer/shared-out/findings/`

File naming:
- Daily findings: `YYYY-MM-DD-findings.md`
- Rolling summary: `summary.md` (updated each run)

## Report Format

```markdown
# Research Findings - [DATE]

## Key Trends
- Trend 1: [description]
- Trend 2: [description]

## Opportunities Identified
1. **[Opportunity Name]**
   - Description: ...
   - Why interesting: ...
   - Complexity: Low/Medium/High

## Notable Signals
- [Signal 1]
- [Signal 2]

## Raw Sources
- [URL 1]
- [URL 2]
```

## Slash Commands

### /research
Run a full research cycle on current trends.

### /research [topic]
Research a specific topic in depth.

### /status
Report on recent research activity and findings count.
```

**File: `config/agent-templates/demo-researcher/.claude/commands/research.md`**
```markdown
---
description: Run a research cycle on trending topics
allowed-tools: WebSearch, WebFetch, Write, Read
---

# Research Cycle

Execute a research cycle:

1. **Discover**: Search for trending topics in:
   - AI and machine learning developments
   - Startup ecosystem news
   - Developer tools and productivity

2. **Analyze**: For each interesting finding:
   - Summarize the key points
   - Assess potential opportunity
   - Rate complexity to pursue

3. **Document**: Write findings to `/home/developer/shared-out/findings/`:
   - Create `[DATE]-findings.md` with today's findings
   - Update `summary.md` with cumulative insights

4. **Report**: Output a brief summary of what was found

Start the research now.
```

#### 1.2 Analyst Template

**File: `config/agent-templates/demo-analyst/template.yaml`**
```yaml
name: demo-analyst
display_name: Analysis Agent
description: Synthesizes research findings and answers strategic questions
version: "1.0.0"
author: Trinity Demo

resources:
  cpu: "1"
  memory: "2g"

capabilities:
  - synthesis
  - strategic-analysis
  - report-generation

schedules:
  - name: daily-briefing
    cron: "0 9 * * *"  # Daily at 9 AM
    message: "/briefing"
    description: Daily synthesis of research findings
```

**File: `config/agent-templates/demo-analyst/CLAUDE.md`**
```markdown
# Analysis Agent

You are a strategic analyst. You synthesize research findings and provide actionable insights.

## Your Mission

1. Read research findings from the shared folder
2. Identify patterns across multiple research cycles
3. Prioritize opportunities by potential impact
4. Answer strategic questions from users

## Input Location

Research findings are at: `/home/developer/shared-in/demo-researcher/findings/`

## Capabilities

### Reading Research
- Access all findings via the shared folder mount
- The researcher agent writes daily findings there
- Look for `summary.md` for the rolling summary

### Calling the Researcher
If you need fresh research on a specific topic, you can call the researcher directly:
```
Use Trinity MCP tool: chat_with_agent
Target: demo-researcher
Message: /research [specific topic]
```

## Slash Commands

### /briefing
Generate a daily briefing from recent findings.

### /opportunities
List and rank all identified opportunities.

### /ask [question]
Answer a strategic question using accumulated research.

### /request-research [topic]
Ask the researcher to investigate a specific topic.
```

**File: `config/agent-templates/demo-analyst/.claude/commands/briefing.md`**
```markdown
---
description: Generate daily briefing from research findings
allowed-tools: Read, Glob, Write
---

# Daily Briefing

Generate a briefing from recent research:

1. **Read** all findings from `/home/developer/shared-in/demo-researcher/findings/`
2. **Identify** the top 3-5 most significant trends
3. **Prioritize** opportunities by impact potential
4. **Synthesize** into an executive briefing format

Output format:
```markdown
# Daily Briefing - [DATE]

## Executive Summary
[2-3 sentence overview]

## Top Trends
1. [Trend with brief explanation]
2. [Trend with brief explanation]
3. [Trend with brief explanation]

## Recommended Actions
- [ ] Action 1
- [ ] Action 2

## Opportunities to Watch
| Opportunity | Potential | Effort | Priority |
|-------------|-----------|--------|----------|
| ... | High/Med/Low | High/Med/Low | 1-5 |
```

Generate the briefing now.
```

---

### Step 2: Create System Manifest

**File: `config/manifests/research-network.yaml`**
```yaml
# Research Network - Autonomous Demo System
# Deploy with: POST /api/systems/deploy

name: research-network
description: Two-agent autonomous research and analysis system

# System-wide instructions (injected into all agents)
prompt: |
  You are part of the Research Network - an autonomous system for discovering
  and analyzing opportunities. Work collaboratively with other agents.

  Key principles:
  - Be thorough but concise in reports
  - Always cite sources
  - Flag high-priority findings clearly
  - Maintain consistent formatting

agents:
  researcher:
    template: local:demo-researcher
    resources:
      cpu: "1"
      memory: "2g"
    folders:
      expose: true    # Shares /shared-out with analyst
      consume: false
    schedules:
      - name: research-cycle
        cron: "0 */4 * * *"  # Every 4 hours
        message: "/research"
        timezone: UTC

  analyst:
    template: local:demo-analyst
    resources:
      cpu: "1"
      memory: "2g"
    folders:
      expose: false
      consume: true   # Mounts researcher's shared folder
    schedules:
      - name: daily-briefing
        cron: "0 9 * * *"  # Daily at 9 AM UTC
        message: "/briefing"
        timezone: UTC

# Permission configuration
permissions:
  preset: full-mesh  # Both agents can call each other
```

---

### Step 3: Deploy the System

#### Option A: Via API (Recommended)

```bash
# Deploy the system
curl -X POST http://localhost:8000/api/systems/deploy \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d @config/manifests/research-network.yaml

# Or with dry-run first
curl -X POST "http://localhost:8000/api/systems/deploy?dry_run=true" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d @config/manifests/research-network.yaml
```

#### Option B: Via Trinity MCP

```
Use tool: deploy_system
manifest: [paste YAML content]
dry_run: false
```

#### Option C: Manual Setup

1. Create agents from templates via UI
2. Configure shared folders in each agent's Folders tab
3. Grant permissions in Permissions tab
4. Create schedules in Schedules tab

---

### Step 4: Verify Deployment

After deployment, verify:

1. **Dashboard** (`/`): Both agents visible as nodes
2. **Agent Status**: Both showing "running" (green)
3. **Permissions**: Check analyst can see researcher in permissions
4. **Shared Folders**:
   - Researcher: "Expose" enabled
   - Analyst: "Consume" enabled, shows researcher in available mounts
5. **Schedules**: Both agents have schedules visible in Schedules tab

---

### Step 5: Test the System

#### 5.1 Manual Trigger - Researcher

Open terminal for `research-network-researcher`:
```
/research
```

Watch:
- Research cycle executes
- Files appear in `/home/developer/shared-out/findings/`

#### 5.2 Manual Trigger - Analyst

Open terminal for `research-network-analyst`:
```
/briefing
```

Watch:
- Analyst reads from `/home/developer/shared-in/research-network-researcher/findings/`
- Generates briefing from findings

#### 5.3 Test Collaboration

In analyst terminal:
```
/request-research AI agents for content creation
```

Watch Dashboard:
- Collaboration edge lights up between analyst → researcher
- Researcher executes research task
- Results flow back

---

## Demo Script

### For Live Demo (15 minutes)

1. **Show Dashboard** (2 min)
   - Point out the two agent nodes
   - Explain the research → analyst flow

2. **Trigger Researcher** (3 min)
   - Open researcher terminal
   - Run `/research`
   - Show output being generated

3. **Check Shared Folder** (2 min)
   - Go to File Manager (`/files`)
   - Select researcher agent
   - Show findings file created

4. **Trigger Analyst** (3 min)
   - Open analyst terminal
   - Run `/briefing`
   - Show it reading researcher's findings

5. **Show Collaboration** (3 min)
   - In analyst, ask it to request specific research
   - Watch Dashboard light up with collaboration edge
   - Explain the MCP-based communication

6. **Show Schedules** (2 min)
   - Open each agent's Schedules tab
   - Show upcoming executions
   - Explain autonomous operation

### Key Talking Points

- "These agents run autonomously on schedule - no human in the loop"
- "They collaborate via shared folders and direct MCP calls"
- "The dashboard shows all collaboration in real-time"
- "Each agent has specialized capabilities defined in its template"
- "The system manifest deploys everything with one command"

---

## Troubleshooting

### Shared Folder Empty
- Verify researcher has "Expose Shared Folder" enabled
- Verify analyst has "Mount Shared Folders" enabled
- Restart both agents after changing folder config

### Collaboration Not Working
- Check Permissions tab - analyst needs permission to call researcher
- Verify both agents are running
- Check agent logs for MCP errors

### Schedule Not Firing
- Verify schedule is enabled (toggle in Schedules tab)
- Check timezone settings
- Manual trigger to verify command works

### Agent Won't Start
- Check Docker logs: `docker logs research-network-researcher`
- Verify base image exists: `docker images | grep trinity-agent-base`
- Rebuild if needed: `./scripts/deploy/build-base-image.sh`

---

## Extending the Demo

### Add More Researchers
Duplicate the researcher template with different focus areas:
- `demo-researcher-tech` - Technology trends
- `demo-researcher-market` - Market opportunities
- `demo-researcher-competitor` - Competitor analysis

### Add Alerting
Configure the analyst to detect high-priority findings and send notifications:
- Add Slack MCP for alerts
- Create `/alert` command that posts to channel

### Add Metrics
Define custom metrics in template.yaml:
```yaml
metrics:
  findings_count:
    type: counter
    label: Findings Discovered
  opportunities_high:
    type: gauge
    label: High-Priority Opportunities
```

---

## Files Summary

After implementation, you should have:

```
config/
├── agent-templates/
│   ├── demo-researcher/
│   │   ├── template.yaml
│   │   ├── CLAUDE.md
│   │   └── .claude/
│   │       └── commands/
│   │           └── research.md
│   └── demo-analyst/
│       ├── template.yaml
│       ├── CLAUDE.md
│       └── .claude/
│           └── commands/
│               └── briefing.md
└── manifests/
    └── research-network.yaml
```

---

## Success Criteria

The demo is successful when:

- [x] Both agents deployed and running
- [x] Researcher produces findings on schedule (or manual trigger)
- [x] Analyst can read researcher's findings
- [x] Collaboration edge visible on Dashboard when agents communicate
- [x] Schedules show next execution times
- [x] File Manager shows research output files

**All criteria validated 2026-01-01 12:45 UTC**

---

## Validation Log

**Validated**: 2026-01-01 12:45 UTC

### Deployment Results
```
System: research-network
Status: deployed
Agents created: research-network-researcher, research-network-analyst
Permissions configured: 2 (full-mesh)
Schedules created: 2
```

### Functional Tests

| Test | Command | Result |
|------|---------|--------|
| Research cycle | `/research` on researcher | ✅ Generated 8 trends, 6 opportunities, saved to shared folder |
| Shared folder access | Check analyst mount | ✅ `2026-01-01-findings.md` and `summary.md` visible |
| Briefing synthesis | `/briefing` on analyst | ✅ Read findings, generated executive briefing |
| Agent collaboration | `/request-research quantum computing` | ✅ Analyst called researcher via MCP, new `quantum-findings.md` created |

### Files Generated
```
/home/developer/shared-out/findings/
├── 2026-01-01-findings.md        (8.6 KB - initial research)
├── 2026-01-01-quantum-findings.md (9.1 KB - collaboration request)
└── summary.md                     (5.3 KB - rolling summary)
```

### Infrastructure Verification
| Check | Result |
|-------|--------|
| Researcher running | `docker ps` shows `agent-research-network-researcher` Up |
| Analyst running | `docker ps` shows `agent-research-network-analyst` Up |
| Researcher expose folder | `/home/developer/shared-out/findings/` exists |
| Analyst mount | `/home/developer/shared-in/research-network-researcher/` mounted |
| Researcher schedule | `research-cycle: 0 */4 * * *` - Next: 2026-01-01T20:00:00Z |
| Analyst schedule | `daily-briefing: 0 9 * * *` - Next: 2026-01-02T09:00:00Z |

### Issues Found
None - all demo scenarios executed successfully.
