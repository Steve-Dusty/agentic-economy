# Human-Cognitive-Aware Agent Design

**Design principles for multi-agent systems that preserve human cognitive depth**

## The Problem

Working with multiple AI agents simultaneously creates a hidden cognitive cost. Each agent takes time to execute, creating "waiting gaps" that tempt humans to start other tasks. This forces frequent context-switching - one of the most cognitively draining activities for humans.

**The pattern:**
1. Human initiates agent task
2. Agent executes (30 seconds to several minutes)
3. Human feels compelled to fill the gap with other work
4. Agent completes - human must context-switch back
5. Repeat across multiple agents = cognitive fragmentation

**Research context:** Studies suggest 15-23 minutes to fully re-engage after switching tasks. Parallel agent work can force dozens of switches per hour.

## Core Principle

> **Decouple agent execution timing from human attention.**

The optimal human-AI workflow isn't "maximize parallelism" but "maximize depth per context." Design systems where:

- Parallelism happens behind the scenes, not in human awareness
- Human touchpoints are batched, not streaming
- Agent wait time becomes consolidation time, not dead time to fill

## Design Patterns

### Pattern 1: Single Orchestrator Interface

Human interacts with ONE agent that coordinates all others. Parallelism is invisible to the human.

```yaml
# system-manifest.yaml
name: research-system
description: Single-interface research coordination

agents:
  coordinator:
    template: orchestrator-template
    description: Human's sole interface

  researcher:
    template: research-agent

  analyst:
    template: analysis-agent

  synthesizer:
    template: synthesis-agent

permissions:
  coordinator: [researcher, analyst, synthesizer]
  # Human only talks to coordinator
  # Coordinator delegates and consolidates
```

**Human experience:** One conversation, one context. Results arrive consolidated.

**Implementation notes:**
- Coordinator's CLAUDE.md should include instructions to batch delegate and consolidate results
- Use `chat_with_agent` with `parallel: true` for concurrent sub-agent work
- Return unified response only when all sub-tasks complete

### Pattern 2: Batched Human Touchpoints

Use Process Engine to sequence agent work with minimal human interruption.

```yaml
# process-definition.yaml
name: content-research-pipeline
description: Multiple agents, single review point

triggers:
  - type: manual

steps:
  - id: gather-sources
    name: Gather Sources
    type: agent_task
    agent: researcher
    task: "Find relevant sources for: ${topic}"

  - id: analyze-sources
    name: Analyze Sources
    type: agent_task
    agent: analyst
    task: "Analyze sources and extract key insights"
    depends_on: [gather-sources]

  - id: synthesize
    name: Synthesize Findings
    type: agent_task
    agent: synthesizer
    task: "Create comprehensive synthesis"
    depends_on: [analyze-sources]

  - id: human-review
    name: Review Complete Analysis
    type: human_approval
    title: "Review Research Results"
    description: "All agent work complete. Review consolidated findings."
    timeout: 24h
    depends_on: [synthesize]

  - id: finalize
    name: Finalize Output
    type: agent_task
    agent: synthesizer
    task: "Incorporate feedback and finalize"
    depends_on: [human-review]
```

**Human experience:** Initiate process, do deep work elsewhere, receive single notification when ready for review.

### Pattern 3: Scheduled Asynchronous Execution

Agents work during off-hours or scheduled windows. Human reviews in dedicated sessions.

```yaml
# system-manifest.yaml
name: daily-intelligence
description: Overnight agent work, morning human review

agents:
  intelligence-gatherer:
    template: research-agent
    schedules:
      - name: overnight-research
        cron: "0 2 * * *"  # 2 AM
        message: "Gather intelligence on tracked topics"

  morning-briefer:
    template: synthesis-agent
    schedules:
      - name: morning-brief
        cron: "0 7 * * *"  # 7 AM
        message: "Synthesize overnight findings into briefing"
```

**Human experience:** Wake up to completed briefing. No real-time waiting. Review in single focused session.

### Pattern 4: Consolidation Timer

Insert deliberate gaps between agent work and human review.

```yaml
steps:
  - id: agent-work
    type: agent_task
    agent: worker
    task: "Complete analysis"

  - id: consolidation-period
    name: Consolidation Period
    type: timer
    duration: 15m  # Forced gap
    depends_on: [agent-work]

  - id: human-review
    type: human_approval
    title: "Review with fresh perspective"
    depends_on: [consolidation-period]
```

**Rationale:** Even when human is available, forcing a gap allows mental consolidation and prevents reactive engagement.

### Pattern 5: Notification-Based Async

Break the real-time expectation entirely. Agents complete work, human engages when ready.

```yaml
steps:
  - id: complex-analysis
    type: agent_task
    agent: analyst
    task: "Deep analysis (may take 10+ minutes)"

  - id: notify-complete
    type: notification
    channel: email  # Or slack, webhook, etc.
    message: "Analysis complete. Review when ready."
    depends_on: [complex-analysis]
```

**Human experience:** No waiting. Notification arrives. Human chooses when to engage based on their cognitive state.

## Anti-Patterns to Avoid

### Anti-Pattern 1: Real-Time Multi-Agent Dashboard

Watching multiple agents work in real-time creates anxiety and temptation to intervene or context-switch.

**Instead:** Use Process Engine with batched human touchpoints.

### Anti-Pattern 2: Immediate Response Expectation

Designing for instant human response to agent completion.

**Instead:** Use notification + inbox pattern. Human reviews when ready.

### Anti-Pattern 3: Parallel Human Conversations

Human simultaneously chatting with multiple agents on different tasks.

**Instead:** Single orchestrator or sequential engagement.

## Implementation Checklist

When designing a multi-agent system, verify:

- [ ] Human has single primary interface (orchestrator pattern)
- [ ] Agent parallelism happens behind the scenes
- [ ] Human touchpoints are batched, not streaming
- [ ] Notifications replace real-time waiting
- [ ] Process definitions include consolidation gaps
- [ ] Scheduled work happens asynchronously when possible

## Template: Cognitive-Aware Research System

Complete system manifest implementing these principles:

```yaml
name: cognitive-aware-research
description: Research system designed for human cognitive depth

agents:
  # Human's sole interface
  coordinator:
    template: github:abilityai/agent-corbin
    resources:
      cpu: "2"
      memory: "4g"
    folders:
      expose: true
      consume: true

  # Background workers - human never interacts directly
  researcher:
    template: research-worker
    folders:
      expose: true

  analyst:
    template: analysis-worker
    folders:
      consume: true
      expose: true

  synthesizer:
    template: synthesis-worker
    folders:
      consume: true
      expose: true

# Only coordinator can delegate
permissions:
  coordinator: [researcher, analyst, synthesizer]

shared_folders:
  - name: research-artifacts
    path: /shared/research
```

Coordinator's CLAUDE.md should include:

```markdown
## Cognitive-Aware Coordination Protocol

When human requests research:
1. Acknowledge request briefly
2. Delegate to sub-agents using parallel execution
3. DO NOT stream intermediate updates
4. Consolidate ALL results before responding
5. Present unified synthesis, not fragmented updates

Human should experience: one request in, one comprehensive response out.
```

## Measuring Success

Track these metrics to validate cognitive-aware design:

1. **Human touchpoints per task** - Lower is better
2. **Average time between human interactions** - Longer focused blocks indicate success
3. **Task completion without context switches** - Higher percentage = better design
4. **Human-reported cognitive load** - Subjective but valuable

## Further Reading

- Original insight: Agent wait time should be rest, not work
- Related concept: Ultradian rhythms (~90 min focus cycles)
- Research: Context-switching costs (15-23 minutes to re-engage)

---

*This design guide emerged from observing the hidden cognitive costs of parallel agent work. The core insight: human brains are deep processors, not schedulers. Design agent systems accordingly.*
