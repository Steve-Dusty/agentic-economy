import { NextResponse } from 'next/server';

/**
 * Mindra Agents Knowledge Graph API
 *
 * Simplified to match reality: 1 orchestrator + 4 leaf agents connected via Nevermined x402.
 * Based on the actual TrinityOS agent registry (screenshot shows Writer, QA Checker, Nexus, Researcher).
 */

const AGENTS = {
  researcher: {
    agent_id: '102575793179870454885693749389321147500444253017787287080547662366660764018939',
    endpoint: 'https://us14.abilityai.dev/api/paid/researcher/chat',
    credits: 1,
    role: 'Web research and fact-finding',
    capabilities: ['Web search', 'Fact extraction', 'Source validation', 'Topic deep-dives'],
    color: '#22d3ee',
  },
  nexus: {
    agent_id: '38193170898726307123033205989462035601957241449542699022794362936331517059909',
    endpoint: 'https://us14.abilityai.dev/api/paid/nexus/chat',
    credits: 1,
    role: 'Data analysis, competitive intelligence, technical advisory',
    capabilities: ['Data analysis', 'Competitive intel', 'Technical advisory', 'Market sizing'],
    color: '#818cf8',
  },
  writer: {
    agent_id: '739071533822469363454794813167578815978480755573494968808789634091211405280',
    endpoint: 'https://us14.abilityai.dev/api/paid/writer/chat',
    credits: 1,
    role: 'Content generation — reports, articles, copy',
    capabilities: ['Report writing', 'Article generation', 'Copywriting', 'Summarization'],
    color: '#fbbf24',
  },
  'qa-checker': {
    agent_id: '34717900564144577384221620768773912527087254723894341195443997683755291677420',
    endpoint: 'https://us14.abilityai.dev/api/paid/qa-checker/chat',
    credits: 1,
    role: 'Fact-checking, quality assurance, validation',
    capabilities: ['Fact-checking', 'Quality assurance', 'Claim validation', 'Error detection'],
    color: '#f472b6',
  },
};

export async function GET() {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const nodes: any[] = [];
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const links: any[] = [];

  // ─── Orchestrator Hub (center) ───
  nodes.push({
    id: 'orchestrator',
    name: 'Mindra Orchestrator',
    type: 'orchestrator',
    category: 'core',
    description: 'Central orchestrator — receives tasks, routes to the right agent(s), manages x402 payments, aggregates results',
    color: '#4ade80',
    val: 40,
    isCore: true,
  });

  // ─── The 4 Leaf Agents ───
  for (const [agentName, agent] of Object.entries(AGENTS)) {
    nodes.push({
      id: `agent-${agentName}`,
      name: agentName.split('-').map(w => w.charAt(0).toUpperCase() + w.slice(1)).join(' '),
      type: 'agent',
      category: 'leaf_agent',
      description: agent.role,
      endpoint: agent.endpoint,
      credits: agent.credits,
      capabilities: agent.capabilities,
      color: agent.color,
      val: 22,
    });
  }

  // ─── Nevermined Payment Node ───
  nodes.push({
    id: 'nevermined',
    name: 'Nevermined x402',
    type: 'payment',
    category: 'infrastructure',
    description: 'Payment & settlement layer — x402 access tokens, credit burning, on-chain settlement on Base L2',
    color: '#c084fc',
    val: 20,
  });

  // ─── Client I/O ───
  nodes.push({
    id: 'client',
    name: 'Client Request',
    type: 'client',
    category: 'external',
    description: 'Incoming task — the orchestrator decides which agent(s) to call',
    color: '#60a5fa',
    val: 18,
  });

  nodes.push({
    id: 'output',
    name: 'Final Output',
    type: 'output',
    category: 'external',
    description: 'Aggregated and verified deliverable returned to the client',
    color: '#4ade80',
    val: 18,
  });

  // ═══════════════ LINKS ═══════════════

  // Client → Orchestrator → Output
  links.push({
    source: 'client',
    target: 'orchestrator',
    type: 'request',
    label: 'Task request',
    reason: 'Client submits task — orchestrator decides which agents to invoke',
    weight: 5,
    color: 'rgba(96, 165, 250, 0.5)',
  });

  links.push({
    source: 'orchestrator',
    target: 'output',
    type: 'delivery',
    label: 'Final result',
    reason: 'Orchestrator aggregates all agent outputs into a single deliverable',
    weight: 5,
    color: 'rgba(74, 222, 128, 0.5)',
  });

  // Orchestrator → each agent (task routing)
  for (const [agentName, agent] of Object.entries(AGENTS)) {
    links.push({
      source: 'orchestrator',
      target: `agent-${agentName}`,
      type: 'routes_to',
      label: `Dispatches to ${agentName.split('-').map(w => w.charAt(0).toUpperCase() + w.slice(1)).join(' ')}`,
      reason: agent.role,
      weight: 4,
      color: `${agent.color}50`,
    });
  }

  // Each agent → Orchestrator (returns results)
  for (const [agentName, agent] of Object.entries(AGENTS)) {
    links.push({
      source: `agent-${agentName}`,
      target: 'orchestrator',
      type: 'result',
      label: 'Returns result',
      reason: `${agentName.split('-').map(w => w.charAt(0).toUpperCase() + w.slice(1)).join(' ')} sends output back to orchestrator`,
      weight: 3,
      color: `${agent.color}30`,
    });
  }

  // Orchestrator → Nevermined (pays)
  links.push({
    source: 'orchestrator',
    target: 'nevermined',
    type: 'payment',
    label: 'x402 token request',
    reason: 'Orchestrator requests x402 access tokens from Nevermined before calling each agent',
    weight: 4,
    color: 'rgba(192, 132, 252, 0.5)',
  });

  // Nevermined → each agent (authorizes)
  for (const [agentName, agent] of Object.entries(AGENTS)) {
    links.push({
      source: 'nevermined',
      target: `agent-${agentName}`,
      type: 'x402_auth',
      label: `${agent.credits} credit`,
      reason: `x402 token authorizes ${agent.credits} credit per call to ${agentName.split('-').map(w => w.charAt(0).toUpperCase() + w.slice(1)).join(' ')}`,
      weight: 2,
      color: 'rgba(192, 132, 252, 0.3)',
    });
  }

  // Agent-to-agent collaboration links (typical pipelines)
  // Researcher → Writer (research feeds content)
  links.push({
    source: 'agent-researcher',
    target: 'agent-writer',
    type: 'feeds',
    label: 'Research → Content',
    reason: 'Researcher findings are passed to Writer for report/article generation',
    weight: 3,
    color: 'rgba(34, 211, 238, 0.3)',
  });

  // Writer → QA Checker (content gets verified)
  links.push({
    source: 'agent-writer',
    target: 'agent-qa-checker',
    type: 'feeds',
    label: 'Content → QA',
    reason: 'Writer output is sent to QA Checker for fact-checking and quality assurance',
    weight: 3,
    color: 'rgba(251, 191, 36, 0.3)',
  });

  // Nexus → Writer (analysis feeds reports)
  links.push({
    source: 'agent-nexus',
    target: 'agent-writer',
    type: 'feeds',
    label: 'Analysis → Content',
    reason: 'Nexus analysis and competitive intel is sent to Writer for report generation',
    weight: 2,
    color: 'rgba(129, 140, 248, 0.3)',
  });

  // Researcher → Nexus (raw data feeds analysis)
  links.push({
    source: 'agent-researcher',
    target: 'agent-nexus',
    type: 'feeds',
    label: 'Data → Analysis',
    reason: 'Researcher raw data is sent to Nexus for deeper analysis and competitive intel',
    weight: 2,
    color: 'rgba(34, 211, 238, 0.25)',
  });

  const totalCreditsPerFullRun = Object.values(AGENTS).reduce((sum, a) => sum + a.credits, 0);

  const stats = {
    totalAgents: Object.keys(AGENTS).length,
    departments: 0, // flat structure, no departments
    workflows: 0,
    creditsPerFullRun: totalCreditsPerFullRun,
    platform: 'TrinityOS (AbilityAI)',
    paymentLayer: 'Nevermined x402',
    settlement: 'Base L2',
  };

  return NextResponse.json({
    nodes,
    links,
    stats,
    agents: AGENTS,
    timestamp: new Date().toISOString(),
  });
}
