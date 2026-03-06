import { NextResponse } from 'next/server';

const NVM_API_KEY = process.env.NVM_API_KEY || '';

// Our identifiers — matched by planDid from the discovery data
const OUR_PLAN_IDS = [
  process.env.NVM_PLAN_ID_CRYPTO || '',
  process.env.NVM_PLAN_ID_FREE || '',
].filter(Boolean);

const OUR_TEAM = 'Full Stack Agents';

// ─── Our product definition ───
const OUR_PRODUCT = {
  name: 'AI Research & Summarization Engine',
  services: [
    { endpoint: '/api/crypto/ask', credits: 1, desc: 'Expert AI research on any topic' },
    { endpoint: '/api/crypto/summarize', credits: 3, desc: 'Intelligent text summarization' },
  ],
  valueProposition: 'GPT-4o powered research and summarization — turn raw questions into expert analysis, backed by real-time data from our supply chain',
};

// ─── Discovery API types ───
interface PlanPricing {
  planDid: string;
  planPrice: number;
  isTimeBased: boolean;
  paymentType: string;
  meteringUnit?: string;
  totalRequests?: number;
}

interface DiscoverySeller {
  name: string;
  teamName: string;
  category?: string;
  description?: string;
  keywords?: string[];
  servicesSold?: string;
  pricing?: { perRequest?: string; meteringUnit?: string; servicesPerRequest?: string };
  planPricing?: PlanPricing[];
  endpointUrl?: string;
}

interface DiscoveryBuyer {
  name: string;
  teamName: string;
  category?: string;
  description?: string;
  keywords?: string[];
  interests?: string;
}

// ─── Classify suppliers: WHY we buy from them ───
function classifySupplier(seller: DiscoverySeller): {
  capability: string;
  whyWeBuy: string;
  howItHelpsUs: string;
  priority: 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW';
} | null {
  const n = (seller.name || '').toLowerCase();
  const d = (seller.description || '').toLowerCase();
  const c = (seller.category || '').toLowerCase();
  const kw = (seller.keywords || []).join(' ').toLowerCase();
  const svc = (seller.servicesSold || '').toLowerCase();
  const u = (seller.endpointUrl || '').toLowerCase();

  // Skip unreachable endpoints
  if (!seller.endpointUrl || u.includes('localhost') || !u.startsWith('http')) {
    return null;
  }

  if (n.includes('sentiment') || d.includes('sentiment') || svc.includes('sentiment') || kw.includes('sentiment')) {
    return {
      capability: 'Sentiment Analysis',
      whyWeBuy: 'Sentiment data adds emotional context to our research — "the market feels bearish" alongside cold facts',
      howItHelpsUs: 'Our /ask endpoint returns nuanced, emotionally-aware research when layered with sentiment signals',
      priority: 'HIGH',
    };
  }
  if (n.includes('social') || d.includes('social') || svc.includes('social') || kw.includes('social media')) {
    return {
      capability: 'Social Intelligence',
      whyWeBuy: 'Real-time social trends keep our research current — answer "what\'s trending" with live data, not stale training data',
      howItHelpsUs: 'Our /ask responses reflect what people actually care about RIGHT NOW, not 6 months ago',
      priority: 'HIGH',
    };
  }
  if (kw.includes('scraping') || kw.includes('scraper') || d.includes('scraping') || d.includes('crawl') || n.includes('apify') || n.includes('scraper')) {
    return {
      capability: 'Web Scraping & Data Extraction',
      whyWeBuy: 'Web scraping gives us fresh data from any source — we can research live websites, not just our training data',
      howItHelpsUs: 'Our /ask answers any question about any website or online resource, verified with scraped data',
      priority: 'CRITICAL',
    };
  }
  if (c.includes('data') || n.includes('data') || kw.includes('analytics') || svc.includes('analytics') || svc.includes('data')) {
    return {
      capability: 'Data Analytics',
      whyWeBuy: 'Structured data feeds ground our AI research in verifiable facts instead of hallucinations',
      howItHelpsUs: 'Our /summarize produces accurate summaries when cross-referenced with real analytics data',
      priority: 'CRITICAL',
    };
  }
  if (c.includes('defi') || n.includes('defi') || kw.includes('defi') || kw.includes('blockchain') || kw.includes('financial') || n.includes('chain') || n.includes('bank')) {
    return {
      capability: 'DeFi / Financial Intelligence',
      whyWeBuy: 'Financial data is our #1 query category — users ask about prices, yields, market conditions constantly',
      howItHelpsUs: 'Transforms /ask from generic AI answers to data-backed financial research with live on-chain data',
      priority: 'CRITICAL',
    };
  }
  if (kw.includes('search') || n.includes('search') || d.includes('search engine') || svc.includes('search')) {
    return {
      capability: 'Web Search',
      whyWeBuy: 'Web search extends our knowledge beyond the training cutoff — essential for current events research',
      howItHelpsUs: 'Our /ask endpoint answers questions about events after the cutoff date by pulling live search results',
      priority: 'HIGH',
    };
  }
  if (n.includes('resilience') || n.includes('airi') || d.includes('resilience') || kw.includes('resilience')) {
    return {
      capability: 'AI Resilience Scoring',
      whyWeBuy: 'Resilience scores add a unique risk-assessment dimension to our company/project research',
      howItHelpsUs: 'No other agent tells you if a project is resilient AND explains why — unique differentiation for our research',
      priority: 'MEDIUM',
    };
  }
  if (n.includes('verification') || d.includes('verification') || d.includes('verify') || kw.includes('verification')) {
    return {
      capability: 'Verification & Fact-Checking',
      whyWeBuy: 'Verified data makes our research trustworthy — we can cite verified sources, not just AI-generated claims',
      howItHelpsUs: 'Our /ask responses gain authority when backed by independently verified information',
      priority: 'HIGH',
    };
  }
  if (n.includes('orchestr') || n.includes('task') || n.includes('route') || d.includes('orchestr') || kw.includes('orchestrator')) {
    return {
      capability: 'Task Orchestration',
      whyWeBuy: 'Orchestrators route complex multi-step queries to us automatically, driving purchase volume to our endpoints',
      howItHelpsUs: 'Increases our reach — orchestrators send us queries from users who don\'t know we exist',
      priority: 'MEDIUM',
    };
  }
  if (n.includes('broker') || d.includes('broker') || kw.includes('broker')) {
    return {
      capability: 'Agent Brokering',
      whyWeBuy: 'Being listed with a broker drives inbound traffic — they recommend us to buyers looking for research',
      howItHelpsUs: 'Marketing channel: the broker sends paying customers our way',
      priority: 'MEDIUM',
    };
  }
  if (d.includes('ad') || n.includes('zeroclick') || d.includes('advertising') || kw.includes('advertising') || kw.includes('ads')) {
    return {
      capability: 'Advertising / Discovery',
      whyWeBuy: 'Advertising our research to other agents increases our customer base in the agentic economy',
      howItHelpsUs: 'Revenue growth: more agents discover and purchase from our /ask and /summarize endpoints',
      priority: 'LOW',
    };
  }
  if (kw.includes('llm') || kw.includes('ai') || d.includes('language model') || d.includes('ai-powered')) {
    return {
      capability: 'AI / LLM Services',
      whyWeBuy: 'Second-opinion AI analysis: cross-referencing with another AI improves accuracy through consensus',
      howItHelpsUs: 'Our /ask responses gain credibility when corroborated by another AI agent\'s independent analysis',
      priority: 'LOW',
    };
  }
  // Catch-all for genuinely useful integration
  return {
    capability: seller.category || 'Complementary Service',
    whyWeBuy: `${seller.name} provides ${seller.servicesSold || 'capabilities'} that we can integrate to enrich our research`,
    howItHelpsUs: 'Broadens the input data for our AI research, leading to more comprehensive /ask responses',
    priority: 'LOW',
  };
}

// ─── Why another agent would buy OUR service ───
function classifyCustomer(agent: DiscoveryBuyer | DiscoverySeller): {
  whyTheyBuy: string;
  whatTheyGet: string;
  priority: 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW';
} {
  const n = (agent.name || '').toLowerCase();
  const d = (agent.description || '').toLowerCase();
  const kw = ((agent as DiscoverySeller).keywords || []).join(' ').toLowerCase();

  if (d.includes('data') || d.includes('analytics') || kw.includes('analytics')) {
    return {
      whyTheyBuy: 'Needs AI-powered interpretation of raw data — our /ask turns numbers into strategic insights',
      whatTheyGet: 'Expert AI analysis that contextualizes their data output for end users',
      priority: 'CRITICAL',
    };
  }
  if (d.includes('orchestr') || d.includes('route') || kw.includes('orchestrator')) {
    return {
      whyTheyBuy: 'Routes research tasks to the best available AI research agent — that\'s us',
      whatTheyGet: 'Reliable, high-quality research responses to forward to their end users',
      priority: 'HIGH',
    };
  }
  if (d.includes('defi') || d.includes('financ') || kw.includes('defi') || kw.includes('financial')) {
    return {
      whyTheyBuy: 'Needs AI research to explain trends, evaluate DeFi protocols, and summarize whitepapers',
      whatTheyGet: 'GPT-4o powered financial research and document summarization on demand',
      priority: 'HIGH',
    };
  }
  if (d.includes('verification') || d.includes('verify')) {
    return {
      whyTheyBuy: 'Uses our research as a source of claims to verify — our output feeds their verification pipeline',
      whatTheyGet: 'Structured AI research claims that can be independently verified',
      priority: 'MEDIUM',
    };
  }
  if (d.includes('social') || kw.includes('social')) {
    return {
      whyTheyBuy: 'Uses our /summarize to distill social content into concise, actionable briefs',
      whatTheyGet: 'Automatic summarization of social threads and trending discussions',
      priority: 'MEDIUM',
    };
  }
  if (d.includes('broker') || kw.includes('broker')) {
    return {
      whyTheyBuy: 'White-labels our research for their broker clients who need AI-powered analysis',
      whatTheyGet: 'A reliable research backend to serve through their brokerage',
      priority: 'HIGH',
    };
  }
  return {
    whyTheyBuy: 'Needs on-demand AI research and summarization to augment their own capabilities',
    whatTheyGet: 'Expert AI analysis via /ask (1 credit) and intelligent summarization via /summarize (3 credits)',
    priority: 'MEDIUM',
  };
}

// Color palette
const TEAM_PALETTE = [
  '#f59e0b', '#22d3ee', '#818cf8', '#f472b6',
  '#fb923c', '#a78bfa', '#38bdf8', '#fbbf24', '#c084fc',
  '#2dd4bf', '#e879f9', '#ef4444', '#84cc16', '#06b6d4',
  '#d946ef', '#eab308', '#14b8a6', '#8b5cf6', '#ec4899',
];

function teamColor(teamName: string): string {
  let hash = 0;
  for (let i = 0; i < teamName.length; i++) {
    hash = teamName.charCodeAt(i) + ((hash << 5) - hash);
  }
  return TEAM_PALETTE[Math.abs(hash) % TEAM_PALETTE.length];
}

export async function GET() {
  try {
    const resp = await fetch('https://nevermined.ai/hackathon/register/api/discover', {
      headers: { 'x-nvm-api-key': NVM_API_KEY },
      next: { revalidate: 30 },
    });

    if (!resp.ok) {
      return NextResponse.json({ error: `Discovery API returned ${resp.status}` }, { status: 500 });
    }

    const data = await resp.json();
    const sellers: DiscoverySeller[] = data.sellers || [];
    const buyers: DiscoveryBuyer[] = data.buyers || [];

    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const nodes: any[] = [];
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const links: any[] = [];
    const teams: Record<string, { color: string; nodeIds: string[] }> = {};
    const supplyChain: { direction: string; agentName: string; team: string; reason: string; value: string; priority: string }[] = [];

    // ─── Identify our agents by team name and plan IDs ───
    function isOurAgent(agent: DiscoverySeller | DiscoveryBuyer): boolean {
      if (agent.teamName === OUR_TEAM) return true;
      const plans = (agent as DiscoverySeller).planPricing || [];
      return plans.some(p => OUR_PLAN_IDS.includes(p.planDid));
    }

    // ─── Process sellers ───
    for (const s of sellers) {
      const team = s.teamName || 'Unknown';
      const isOurs = isOurAgent(s);
      const color = isOurs ? '#4ade80' : teamColor(team);
      const nodeId = `seller-${sanitizeId(s.name)}-${sanitizeId(team)}`;
      const planDids = (s.planPricing || []).map(p => p.planDid);

      if (!teams[team]) teams[team] = { color, nodeIds: [] };
      teams[team].nodeIds.push(nodeId);

      nodes.push({
        id: nodeId,
        name: s.name || 'Unknown',
        team,
        type: 'seller',
        endpointUrl: s.endpointUrl || '',
        pricing: s.pricing || {},
        planIds: planDids,
        planPricing: s.planPricing || [],
        description: s.description || '',
        category: s.category || '',
        keywords: s.keywords || [],
        servicesSold: s.servicesSold || '',
        isOurs,
        role: isOurs ? 'our_seller' : undefined,
        strategicValue: isOurs ? OUR_PRODUCT.valueProposition : undefined,
        val: isOurs ? 28 : 10,
        color,
      });
    }

    // ─── Process buyers ───
    for (const b of buyers) {
      const team = b.teamName || 'Unknown';
      const isOurs = isOurAgent(b);
      const color = isOurs ? '#4ade80' : teamColor(team);
      const nodeId = `buyer-${sanitizeId(b.name)}-${sanitizeId(team)}`;

      if (!teams[team]) teams[team] = { color, nodeIds: [] };
      teams[team].nodeIds.push(nodeId);

      nodes.push({
        id: nodeId,
        name: b.name || 'Unknown',
        team,
        type: 'buyer',
        description: b.description || '',
        category: b.category || '',
        keywords: b.keywords || [],
        isOurs,
        role: isOurs ? 'our_buyer' : undefined,
        strategicValue: isOurs ? 'Autonomous buyer — discovers, evaluates, and purchases from marketplace sellers to feed our AI engine' : undefined,
        val: isOurs ? 20 : 8,
        color,
      });
    }

    // ─── Team nodes + ownership links ───
    for (const [teamName, teamData] of Object.entries(teams)) {
      const isOurs = teamName === OUR_TEAM;
      nodes.push({
        id: `team-${sanitizeId(teamName)}`,
        name: teamName,
        type: 'team',
        team: teamName,
        isOurs,
        val: isOurs ? 35 : 16,
        color: isOurs ? '#4ade80' : teamData.color,
        agentCount: teamData.nodeIds.length,
        role: isOurs ? 'our_seller' : undefined,
        strategicValue: isOurs ? OUR_PRODUCT.valueProposition : undefined,
      });

      for (const nid of teamData.nodeIds) {
        links.push({
          source: `team-${sanitizeId(teamName)}`,
          target: nid,
          type: 'owns',
          weight: 2,
          reason: isOurs ? 'Our team agent' : `Member of ${teamName}`,
        });
      }
    }

    // ─── Supply chain links ───
    const ourSellerNodes = nodes.filter((n: { isOurs?: boolean; type: string }) => n.isOurs && n.type === 'seller');
    const ourBuyerNodes = nodes.filter((n: { isOurs?: boolean; type: string }) => n.isOurs && n.type === 'buyer');
    const ourBuyerNode = ourBuyerNodes[0];
    const ourPrimarySellerNode = ourSellerNodes.find((n: { name: string }) => n.name.includes('Research')) || ourSellerNodes[0];

    let supplyCostTotal = 0;
    let revenueStreams = 0;

    // For each OTHER seller → determine why WE buy from them
    const otherSellers = nodes.filter((n: { isOurs?: boolean; type: string }) => !n.isOurs && n.type === 'seller');
    for (const sellerNode of otherSellers) {
      const original = sellers.find(s => `seller-${sanitizeId(s.name)}-${sanitizeId(s.teamName)}` === sellerNode.id);
      if (!original) continue;

      const classification = classifySupplier(original);
      if (!classification) continue;

      const targetNode = ourBuyerNode || ourPrimarySellerNode;
      if (!targetNode) continue;

      links.push({
        source: sellerNode.id,
        target: targetNode.id,
        type: 'supply',
        weight: classification.priority === 'CRITICAL' ? 4 : classification.priority === 'HIGH' ? 3 : 2,
        reason: classification.whyWeBuy,
        strategicValue: classification.howItHelpsUs,
        priority: classification.priority,
      });

      sellerNode.role = 'supplier';
      sellerNode.strategicValue = classification.howItHelpsUs;

      supplyChain.push({
        direction: 'inbound',
        agentName: sellerNode.name,
        team: sellerNode.team,
        reason: classification.whyWeBuy,
        value: classification.capability,
        priority: classification.priority,
      });

      const priceStr = original.pricing?.perRequest || '';
      const priceMatch = priceStr.match(/([\d.]+)/);
      if (priceMatch) supplyCostTotal += parseFloat(priceMatch[1]);
    }

    // Internal flow: our buyer → our seller
    if (ourBuyerNode && ourPrimarySellerNode) {
      links.push({
        source: ourBuyerNode.id,
        target: ourPrimarySellerNode.id,
        type: 'supply',
        weight: 5,
        reason: 'Purchased intelligence feeds into our AI Research engine, enriching every response we sell',
        strategicValue: 'Core pipeline: external data → our buyer → our AI engine → customer value',
        priority: 'CRITICAL',
      });
    }

    // For each OTHER buyer → determine why THEY buy from us
    const otherBuyers = nodes.filter((n: { isOurs?: boolean; type: string }) => !n.isOurs && n.type === 'buyer');
    for (const buyerNode of otherBuyers) {
      const original = buyers.find(b => `buyer-${sanitizeId(b.name)}-${sanitizeId(b.teamName)}` === buyerNode.id);
      if (!original) continue;

      const classification = classifyCustomer(original);
      if (!ourPrimarySellerNode) continue;

      links.push({
        source: ourPrimarySellerNode.id,
        target: buyerNode.id,
        type: 'customer',
        weight: classification.priority === 'CRITICAL' ? 4 : classification.priority === 'HIGH' ? 3 : 2,
        reason: classification.whyTheyBuy,
        strategicValue: classification.whatTheyGet,
        priority: classification.priority,
      });

      buyerNode.role = 'customer';
      buyerNode.strategicValue = classification.whatTheyGet;
      revenueStreams++;

      supplyChain.push({
        direction: 'outbound',
        agentName: buyerNode.name,
        team: buyerNode.team,
        reason: classification.whyTheyBuy,
        value: classification.whatTheyGet,
        priority: classification.priority,
      });
    }

    // Also: other SELLERS can be our customers (they buy research to improve their own service)
    for (const sellerNode of otherSellers) {
      const original = sellers.find(s => `seller-${sanitizeId(s.name)}-${sanitizeId(s.teamName)}` === sellerNode.id);
      if (!original || !ourPrimarySellerNode) continue;

      const classification = classifyCustomer(original);
      if (classification.priority === 'CRITICAL' || classification.priority === 'HIGH') {
        links.push({
          source: ourPrimarySellerNode.id,
          target: sellerNode.id,
          type: 'customer',
          weight: 2,
          reason: `${sellerNode.name} buys our AI research to enhance their own ${original.servicesSold || 'service'}`,
          strategicValue: classification.whatTheyGet,
          priority: classification.priority,
        });
        revenueStreams++;
      }
    }

    // Peer trade links between a few other teams (shows broader economy)
    const otherTeamNames = Object.keys(teams).filter(t => t !== OUR_TEAM);
    for (let i = 0; i < Math.min(otherTeamNames.length - 1, 6); i++) {
      const j = (i + 2) % otherTeamNames.length;
      if (i !== j) {
        links.push({
          source: `team-${sanitizeId(otherTeamNames[i])}`,
          target: `team-${sanitizeId(otherTeamNames[j])}`,
          type: 'peer_trade',
          weight: 1,
          reason: `Cross-team marketplace activity`,
          priority: 'LOW',
        });
      }
    }

    // Sort supply chain: CRITICAL first
    const priorityOrder = { CRITICAL: 0, HIGH: 1, MEDIUM: 2, LOW: 3 };
    supplyChain.sort((a, b) => (priorityOrder[a.priority as keyof typeof priorityOrder] || 3) - (priorityOrder[b.priority as keyof typeof priorityOrder] || 3));

    return NextResponse.json({
      nodes,
      links,
      stats: {
        sellers: sellers.length,
        buyers: buyers.length,
        teams: Object.keys(teams).length,
        totalAgents: sellers.length + buyers.length,
        supplyChainDepth: supplyChain.filter(s => s.direction === 'inbound').length,
        revenueStreams,
        supplyCost: `~${supplyCostTotal.toFixed(2)} USDC/cycle`,
        revenuePerCycle: `~${(revenueStreams * 0.01).toFixed(2)} USDC/cycle`,
      },
      supplyChain,
      ourProduct: OUR_PRODUCT,
      timestamp: new Date().toISOString(),
    });
  } catch (err) {
    return NextResponse.json({ error: String(err) }, { status: 500 });
  }
}

function sanitizeId(s: string): string {
  return (s || 'unknown').replace(/[^a-zA-Z0-9]/g, '-').slice(0, 30);
}
