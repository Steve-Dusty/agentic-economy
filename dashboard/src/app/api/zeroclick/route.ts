import { NextResponse } from 'next/server';

/**
 * ZeroClick.ai Knowledge Graph API
 *
 * Builds a knowledge graph representing the ZeroClick ad revenue economy:
 * - Signal collection flow
 * - Offer matching engine
 * - Impression tracking & revenue attribution
 * - Advertiser ↔ Publisher relationships
 */

// Signal categories from the ZeroClick integration
const SIGNAL_CATEGORIES = [
  { id: 'interest', label: 'Interest', desc: 'General topic interest signals', color: '#22d3ee', weight: 3 },
  { id: 'evaluation', label: 'Evaluation', desc: 'Product/service comparison signals', color: '#818cf8', weight: 4 },
  { id: 'purchase_intent', label: 'Purchase Intent', desc: 'Active buying signals — highest monetization', color: '#4ade80', weight: 5 },
  { id: 'problem', label: 'Problem', desc: 'User pain points and needs', color: '#f472b6', weight: 3 },
  { id: 'price_sensitivity', label: 'Price Sensitivity', desc: 'Budget and price awareness signals', color: '#fbbf24', weight: 4 },
  { id: 'brand_affinity', label: 'Brand Affinity', desc: 'Brand preference and loyalty signals', color: '#fb923c', weight: 3 },
  { id: 'user_context', label: 'User Context', desc: 'Demographic and behavioral context', color: '#a78bfa', weight: 2 },
  { id: 'business_context', label: 'Business Context', desc: 'B2B intent and business need signals', color: '#38bdf8', weight: 4 },
  { id: 'recommendation_request', label: 'Recommendation', desc: 'Explicit ask for product recommendations', color: '#2dd4bf', weight: 5 },
];

// Revenue model tiers
const REVENUE_TIERS = [
  { id: 'cpc', label: 'CPC Revenue', desc: 'Cost-per-click: $0.50–$2.00 per click', color: '#4ade80', amount: '$0.50–$2.00/click' },
  { id: 'cpm', label: 'CPM Revenue', desc: 'Cost-per-mille: $5–$25 per 1000 impressions', color: '#22d3ee', amount: '$5–$25/1K views' },
  { id: 'cpa', label: 'CPA Revenue', desc: 'Cost-per-action: $5–$50 per conversion', color: '#fbbf24', amount: '$5–$50/conversion' },
];

// ZeroClick API endpoints (the real ones from the codebase)
const ZC_ENDPOINTS = [
  { id: 'offers_api', label: 'Offers API', url: 'zeroclick.dev/api/v2/offers', desc: 'Fetches personalized offers based on signals' },
  { id: 'signals_api', label: 'Signals API', url: 'zeroclick.dev/api/v2/signals', desc: 'Receives user intent signals via REST' },
  { id: 'mcp_server', label: 'MCP Signal Server', url: 'zeroclick.dev/mcp/v2', desc: 'Model Context Protocol for real-time signal broadcast' },
  { id: 'impressions_api', label: 'Impressions API', url: 'zeroclick.dev/api/v2/impressions', desc: 'Tracks offer views for revenue attribution' },
];

export async function GET() {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const nodes: any[] = [];
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const links: any[] = [];

  // ─── Core Infrastructure Nodes ───
  nodes.push({
    id: 'zc-engine',
    name: 'ZeroClick.ai Engine',
    type: 'core',
    category: 'infrastructure',
    description: 'Core matching engine — connects user signals to relevant advertiser offers in real-time',
    color: '#4ade80',
    val: 35,
    isCore: true,
  });

  nodes.push({
    id: 'user-session',
    name: 'User Sessions',
    type: 'source',
    category: 'users',
    description: 'Active user conversations generating commercial intent signals',
    color: '#60a5fa',
    val: 20,
  });

  nodes.push({
    id: 'signal-extractor',
    name: 'LLM Signal Extractor',
    type: 'processor',
    category: 'ai',
    description: 'GPT-4o-mini powered extraction of commercial intent from natural conversation',
    color: '#c084fc',
    val: 22,
  });

  nodes.push({
    id: 'advertiser-pool',
    name: 'Advertiser Pool',
    type: 'source',
    category: 'advertisers',
    description: 'Brands and advertisers with active campaigns on ZeroClick network',
    color: '#fbbf24',
    val: 22,
  });

  nodes.push({
    id: 'revenue-pool',
    name: 'Revenue Pool',
    type: 'destination',
    category: 'revenue',
    description: 'Aggregated ad revenue from CPC, CPM, and CPA models',
    color: '#4ade80',
    val: 25,
  });

  nodes.push({
    id: 'publisher-share',
    name: 'Publisher Revenue Share',
    type: 'destination',
    category: 'revenue',
    description: 'Revenue distributed to agents/apps that surface ZeroClick offers',
    color: '#22d3ee',
    val: 18,
  });

  // ─── API Endpoint Nodes ───
  for (const ep of ZC_ENDPOINTS) {
    nodes.push({
      id: ep.id,
      name: ep.label,
      type: 'api',
      category: 'endpoint',
      description: ep.desc,
      url: ep.url,
      color: '#818cf8',
      val: 14,
    });
  }

  // ─── Signal Category Nodes ───
  for (const sig of SIGNAL_CATEGORIES) {
    nodes.push({
      id: `sig-${sig.id}`,
      name: sig.label,
      type: 'signal',
      category: 'signal',
      description: sig.desc,
      color: sig.color,
      val: 8 + sig.weight * 2,
      monetizationWeight: sig.weight,
    });
  }

  // ─── Revenue Tier Nodes ───
  for (const tier of REVENUE_TIERS) {
    nodes.push({
      id: `rev-${tier.id}`,
      name: tier.label,
      type: 'revenue_tier',
      category: 'revenue',
      description: tier.desc,
      color: tier.color,
      val: 14,
      amount: tier.amount,
    });
  }

  // Our agent integration node
  nodes.push({
    id: 'our-integration',
    name: 'Our NVM Terminal',
    type: 'integration',
    category: 'our_product',
    description: 'Our agent app integrates ZeroClick for native ad monetization inside conversational AI',
    color: '#4ade80',
    val: 20,
    isOurs: true,
  });

  // ─── Links: User Flow ───
  links.push({
    source: 'user-session',
    target: 'signal-extractor',
    type: 'data_flow',
    label: 'User messages',
    reason: 'User conversation text → LLM-based signal extraction',
    weight: 4,
    color: 'rgba(96, 165, 250, 0.5)',
  });

  links.push({
    source: 'signal-extractor',
    target: 'mcp_server',
    type: 'api_call',
    label: 'Broadcast signals',
    reason: 'Extracted signals broadcast to ZeroClick via MCP protocol (JSON-RPC)',
    weight: 3,
    color: 'rgba(192, 132, 252, 0.5)',
  });

  links.push({
    source: 'signal-extractor',
    target: 'signals_api',
    type: 'api_call',
    label: 'REST fallback',
    reason: 'REST API fallback when MCP is unavailable',
    weight: 2,
    color: 'rgba(192, 132, 252, 0.3)',
  });

  // Signals to engine
  links.push({
    source: 'mcp_server',
    target: 'zc-engine',
    type: 'data_flow',
    label: 'Signal ingestion',
    reason: 'MCP server feeds signals into the ZeroClick matching engine',
    weight: 4,
    color: 'rgba(129, 140, 248, 0.5)',
  });

  links.push({
    source: 'signals_api',
    target: 'zc-engine',
    type: 'data_flow',
    label: 'Signal ingestion',
    reason: 'REST signals feed into ZeroClick matching engine',
    weight: 3,
    color: 'rgba(129, 140, 248, 0.3)',
  });

  // Signal categories to engine
  for (const sig of SIGNAL_CATEGORIES) {
    links.push({
      source: `sig-${sig.id}`,
      target: 'zc-engine',
      type: 'signal_category',
      label: sig.label,
      reason: `${sig.desc} — monetization weight: ${sig.weight}/5`,
      weight: sig.weight,
      color: `${sig.color}40`,
    });
  }

  // Engine to offers
  links.push({
    source: 'zc-engine',
    target: 'offers_api',
    type: 'matching',
    label: 'Offer matching',
    reason: 'Engine matches user signals to relevant advertiser offers',
    weight: 5,
    color: 'rgba(74, 222, 128, 0.5)',
  });

  // Advertisers to engine
  links.push({
    source: 'advertiser-pool',
    target: 'zc-engine',
    type: 'supply',
    label: 'Ad campaigns',
    reason: 'Advertisers supply campaigns, bids, and targeting criteria',
    weight: 4,
    color: 'rgba(251, 191, 36, 0.5)',
  });

  // Offers to impressions
  links.push({
    source: 'offers_api',
    target: 'impressions_api',
    type: 'tracking',
    label: 'View tracking',
    reason: 'Each offer display triggers an impression event for revenue attribution',
    weight: 3,
    color: 'rgba(129, 140, 248, 0.4)',
  });

  // Impressions to revenue
  links.push({
    source: 'impressions_api',
    target: 'revenue-pool',
    type: 'revenue',
    label: 'Revenue attribution',
    reason: 'Impressions, clicks, and conversions generate revenue for the network',
    weight: 5,
    color: 'rgba(74, 222, 128, 0.6)',
  });

  // Revenue tiers to revenue pool
  for (const tier of REVENUE_TIERS) {
    links.push({
      source: `rev-${tier.id}`,
      target: 'revenue-pool',
      type: 'revenue_model',
      label: tier.label,
      reason: `${tier.desc}`,
      weight: 3,
      color: `${tier.color}50`,
    });
  }

  // Revenue distribution
  links.push({
    source: 'revenue-pool',
    target: 'publisher-share',
    type: 'payout',
    label: 'Publisher payout',
    reason: 'Revenue share distributed to publishers/agents who surfaced the offers',
    weight: 4,
    color: 'rgba(34, 211, 238, 0.5)',
  });

  links.push({
    source: 'revenue-pool',
    target: 'advertiser-pool',
    type: 'reporting',
    label: 'ROI reporting',
    reason: 'Campaign performance and ROI data flows back to advertisers',
    weight: 2,
    color: 'rgba(251, 191, 36, 0.3)',
  });

  // Our integration
  links.push({
    source: 'our-integration',
    target: 'signal-extractor',
    type: 'integration',
    label: 'Signal extraction',
    reason: 'Our NVM terminal extracts signals from user conversations',
    weight: 4,
    color: 'rgba(74, 222, 128, 0.5)',
  });

  links.push({
    source: 'offers_api',
    target: 'our-integration',
    type: 'delivery',
    label: 'Offer delivery',
    reason: 'Matched offers delivered as native ads inside our conversational AI',
    weight: 4,
    color: 'rgba(74, 222, 128, 0.5)',
  });

  links.push({
    source: 'publisher-share',
    target: 'our-integration',
    type: 'payout',
    label: 'Our revenue',
    reason: 'We earn revenue share for every impression and click from our users',
    weight: 4,
    color: 'rgba(74, 222, 128, 0.6)',
  });

  // Stats
  const stats = {
    signalCategories: SIGNAL_CATEGORIES.length,
    apiEndpoints: ZC_ENDPOINTS.length,
    revenueModels: REVENUE_TIERS.length,
    avgCPC: '$0.50–$2.00',
    avgCPM: '$5–$25',
    avgCPA: '$5–$50',
    totalNodes: nodes.length,
    totalLinks: links.length,
  };

  return NextResponse.json({
    nodes,
    links,
    stats,
    signalCategories: SIGNAL_CATEGORIES,
    revenueModel: REVENUE_TIERS,
    timestamp: new Date().toISOString(),
  });
}
