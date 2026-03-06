'use client';

import type { AgentNode, AgentLink } from '@/types/graph';

interface Props {
  node: AgentNode | null;
  links: AgentLink[];
  allNodes: AgentNode[];
  onClose: () => void;
}

const ROLE_STYLES: Record<string, { bg: string; text: string; label: string; icon: string }> = {
  our_seller: { bg: 'bg-emerald-900/60', text: 'text-emerald-300', label: 'OUR PRODUCT', icon: '\u2302' },
  our_buyer: { bg: 'bg-emerald-900/60', text: 'text-emerald-300', label: 'OUR BUYER', icon: '\u2941' },
  supplier: { bg: 'bg-cyan-900/60', text: 'text-cyan-300', label: 'SUPPLIER TO US', icon: '\u25B6' },
  customer: { bg: 'bg-amber-900/60', text: 'text-amber-300', label: 'OUR CUSTOMER', icon: '\u25C0' },
  peer: { bg: 'bg-slate-700', text: 'text-slate-300', label: 'MARKETPLACE', icon: '\u25CB' },
};

const TYPE_BADGES: Record<string, { bg: string; text: string; label: string }> = {
  seller: { bg: 'bg-amber-900/40', text: 'text-amber-300', label: 'SELLER' },
  buyer: { bg: 'bg-cyan-900/40', text: 'text-cyan-300', label: 'BUYER' },
  team: { bg: 'bg-indigo-900/40', text: 'text-indigo-300', label: 'TEAM' },
};

const PRIORITY_COLORS: Record<string, string> = {
  CRITICAL: 'text-red-400 bg-red-900/40',
  HIGH: 'text-amber-400 bg-amber-900/40',
  MEDIUM: 'text-blue-400 bg-blue-900/40',
  LOW: 'text-slate-400 bg-slate-800',
};

export default function AgentPanel({ node, links, allNodes, onClose }: Props) {
  if (!node) return null;

  const roleMeta = ROLE_STYLES[node.role || 'peer'] || ROLE_STYLES.peer;
  const typeBadge = TYPE_BADGES[node.type] || TYPE_BADGES.seller;

  // Find connections involving this node
  const nodeId = node.id;
  const connectedLinks = links.filter(l => {
    const src = typeof l.source === 'object' ? (l.source as unknown as { id: string }).id : l.source;
    const tgt = typeof l.target === 'object' ? (l.target as unknown as { id: string }).id : l.target;
    return (src === nodeId || tgt === nodeId) && l.type !== 'owns' && l.type !== 'peer_trade';
  });

  // Resolve node names for links
  const resolveNodeName = (id: string) => {
    const n = allNodes.find(x => x.id === id);
    return n?.name || id;
  };

  return (
    <div className="fixed right-0 top-0 h-full w-[440px] glass-panel z-50 flex flex-col overflow-hidden shadow-2xl animate-slide-in-right">
      {/* Header */}
      <div className="flex items-center justify-between p-5 border-b border-slate-700/30">
        <div className="flex items-center gap-3 min-w-0">
          <div
            className="w-14 h-14 rounded-xl flex items-center justify-center text-2xl font-bold shadow-lg shrink-0"
            style={{ backgroundColor: node.color || '#22d3ee', color: '#0d1117' }}
          >
            {roleMeta.icon}
          </div>
          <div className="min-w-0">
            <h2 className="text-white font-semibold text-lg leading-tight truncate">{node.name}</h2>
            <div className="flex items-center gap-2 mt-1 flex-wrap">
              <span className={`text-[10px] px-2 py-0.5 rounded-full font-bold tracking-wider ${typeBadge.bg} ${typeBadge.text}`}>
                {typeBadge.label}
              </span>
              <span className={`text-[10px] px-2 py-0.5 rounded-full font-bold tracking-wider ${roleMeta.bg} ${roleMeta.text}`}>
                {roleMeta.label}
              </span>
            </div>
          </div>
        </div>
        <button
          onClick={onClose}
          className="text-slate-500 hover:text-white transition-colors p-2 rounded-lg hover:bg-slate-800/50 shrink-0"
        >
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
      </div>

      {/* Body */}
      <div className="flex-1 overflow-y-auto p-5 space-y-5">

        {/* Strategic Value — the WHY */}
        {node.strategicValue && (
          <Section title="Strategic Value">
            <div className="p-3 rounded-lg bg-emerald-950/30 border border-emerald-800/30">
              <p className="text-sm text-emerald-200 leading-relaxed">{node.strategicValue}</p>
            </div>
          </Section>
        )}

        {/* Supply Chain Connections — the HOW */}
        {connectedLinks.length > 0 && (
          <Section title={`Supply Chain Connections (${connectedLinks.length})`}>
            <div className="space-y-3">
              {connectedLinks.map((link, i) => {
                const src = typeof link.source === 'object' ? (link.source as unknown as { id: string }).id : link.source;
                const tgt = typeof link.target === 'object' ? (link.target as unknown as { id: string }).id : link.target;
                const isOutbound = src === nodeId;
                const otherName = isOutbound ? resolveNodeName(tgt) : resolveNodeName(src);
                const prioClass = PRIORITY_COLORS[link.priority || 'LOW'];

                return (
                  <div key={i} className="p-3 rounded-lg bg-slate-900/60 border border-slate-700/20 space-y-2">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2 min-w-0">
                        <span className="text-xs">{isOutbound ? '\u2192' : '\u2190'}</span>
                        <span className="text-sm font-medium text-slate-200 truncate">{otherName}</span>
                      </div>
                      {link.priority && (
                        <span className={`text-[9px] px-1.5 py-0.5 rounded font-bold ${prioClass}`}>
                          {link.priority}
                        </span>
                      )}
                    </div>

                    {/* Why this connection exists */}
                    <p className="text-xs text-slate-400 leading-relaxed">{link.reason}</p>

                    {/* Strategic value of this connection */}
                    {link.strategicValue && (
                      <p className="text-xs text-cyan-400/80 leading-relaxed italic">
                        {'\u2192'} {link.strategicValue}
                      </p>
                    )}

                    {/* Link type badge */}
                    <div className="flex items-center gap-2">
                      <span className={`text-[9px] px-1.5 py-0.5 rounded font-medium ${
                        link.type === 'supply' ? 'bg-cyan-900/40 text-cyan-300' :
                        link.type === 'customer' ? 'bg-amber-900/40 text-amber-300' :
                        'bg-slate-800 text-slate-400'
                      }`}>
                        {link.type === 'supply' ? 'SUPPLY CHAIN' :
                         link.type === 'customer' ? 'REVENUE STREAM' :
                         link.type.toUpperCase()}
                      </span>
                    </div>
                  </div>
                );
              })}
            </div>
          </Section>
        )}

        {/* Team */}
        {node.type !== 'team' && (
          <Section title="Team">
            <span className="text-sm text-slate-200">{node.team}</span>
          </Section>
        )}

        {node.type === 'team' && (
          <Section title="Overview">
            <div className="flex items-center justify-between py-1">
              <span className="text-xs text-slate-500">Agents</span>
              <span className="text-sm text-slate-200">{node.agentCount || 0}</span>
            </div>
          </Section>
        )}

        {/* Endpoint */}
        {node.endpointUrl && (
          <Section title="Endpoint">
            <a
              href={node.endpointUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="text-xs text-cyan-400 hover:text-cyan-300 break-all transition-colors"
            >
              {node.endpointUrl}
            </a>
          </Section>
        )}

        {/* Pricing */}
        {node.pricing?.perRequest && (
          <Section title="Pricing">
            <div className="flex items-center gap-2">
              <span className="text-2xl font-bold text-white">{node.pricing.perRequest}</span>
              <span className="text-xs text-slate-500">per request</span>
            </div>
          </Section>
        )}

        {/* Agent ID */}
        {node.agentId && (
          <Section title="Agent ID">
            <div className="font-mono text-[10px] text-slate-500 break-all bg-slate-900/50 p-2 rounded-lg">
              {node.agentId}
            </div>
          </Section>
        )}

        {/* Plans */}
        {node.planIds && node.planIds.length > 0 && (
          <Section title={`Plans (${node.planIds.length})`}>
            <div className="space-y-1">
              {node.planIds.map((pid, i) => (
                <div key={i} className="font-mono text-[10px] text-slate-500 bg-slate-900/50 p-2 rounded-lg break-all">
                  {pid}
                </div>
              ))}
            </div>
          </Section>
        )}

        {/* Description */}
        {node.description && (
          <Section title="Description">
            <p className="text-sm text-slate-300 leading-relaxed">{node.description}</p>
          </Section>
        )}

        {/* Wallet */}
        {node.wallet && (
          <Section title="Wallet">
            <div className="font-mono text-[10px] text-slate-500 break-all bg-slate-900/50 p-2 rounded-lg">
              {node.wallet}
            </div>
          </Section>
        )}
      </div>
    </div>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div>
      <h4 className="text-[10px] font-bold uppercase tracking-widest text-slate-500 mb-2">{title}</h4>
      {children}
    </div>
  );
}
