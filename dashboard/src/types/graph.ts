export interface AgentNode {
  id: string;
  name: string;
  type: 'team' | 'seller' | 'buyer';
  team: string;
  agentId?: string;
  wallet?: string;
  endpointUrl?: string;
  pricing?: { perRequest?: string; model?: string };
  planIds?: string[];
  description?: string;
  isOurs?: boolean;
  category?: string;
  keywords?: string[];
  servicesSold?: string;
  agentCount?: number;
  // Our product-specific fields
  role?: 'our_seller' | 'our_buyer' | 'supplier' | 'customer' | 'peer';
  strategicValue?: string;
  // Rendering
  val?: number;
  color?: string;
  fx?: number;
  fy?: number;
  fz?: number;
}

export interface AgentLink {
  source: string;
  target: string;
  type: 'owns' | 'supply' | 'customer' | 'we_buy' | 'they_buy' | 'peer_trade';
  weight: number;
  reason: string;
  strategicValue?: string;
  priority?: 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW';
  costPerCycle?: string;
  color?: string;
}

export interface GraphData {
  nodes: AgentNode[];
  links: AgentLink[];
}

export interface EconomyStats {
  sellers: number;
  buyers: number;
  teams: number;
  totalAgents: number;
  supplyChainDepth: number;
  revenueStreams: number;
  supplyCost: string;
  revenuePerCycle: string;
}

export interface TranscriptEntry {
  timestamp: string;
  level: 'system' | 'evaluate' | 'decide' | 'action' | 'success' | 'error' | 'info' | 'strategy' | 'supply' | 'revenue';
  message: string;
  data?: Record<string, unknown>;
}

export interface EconomyResponse {
  nodes: AgentNode[];
  links: AgentLink[];
  stats: EconomyStats;
  supplyChain: SupplyChainEntry[];
  timestamp: string;
}

export interface SupplyChainEntry {
  direction: 'inbound' | 'outbound';
  agentName: string;
  team: string;
  reason: string;
  value: string;
  priority: string;
}
