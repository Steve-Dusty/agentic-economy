'use client';

import { useState, useCallback, useEffect } from 'react';
import ForceGraph3D from './ForceGraph3D';
import AgentPanel from './AgentPanel';
import TranscriptStream from './TranscriptStream';
import StatsOverlay from './StatsOverlay';
import SearchBar from './SearchBar';
import type { AgentNode, AgentLink, GraphData, EconomyStats, TranscriptEntry, SupplyChainEntry } from '@/types/graph';

export default function GraphContainer() {
  const [graphData, setGraphData] = useState<GraphData>({ nodes: [], links: [] });
  const [stats, setStats] = useState<EconomyStats | null>(null);
  const [selectedNode, setSelectedNode] = useState<AgentNode | null>(null);
  const [selectedLink, setSelectedLink] = useState<AgentLink | null>(null);
  const [transcript, setTranscript] = useState<TranscriptEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [connected, setConnected] = useState(false);
  const [dimensions, setDimensions] = useState<{ width: number; height: number } | null>(null);

  useEffect(() => {
    function updateSize() {
      // Account for tab bar height (~56px)
      setDimensions({ width: window.innerWidth, height: window.innerHeight - 56 });
    }
    updateSize();
    window.addEventListener('resize', updateSize);
    return () => window.removeEventListener('resize', updateSize);
  }, []);

  const addLog = useCallback((level: TranscriptEntry['level'], message: string, data?: Record<string, unknown>) => {
    setTranscript(prev => [...prev, {
      timestamp: new Date().toISOString(),
      level,
      message,
      data,
    }]);
  }, []);

  const loadEconomy = useCallback(async () => {
    addLog('system', 'Initializing autonomous marketplace analysis...');
    addLog('system', 'Scanning Nevermined discovery API for registered agents...');

    try {
      const resp = await fetch('/api/economy');
      if (!resp.ok) throw new Error(`API error: ${resp.status}`);
      const data = await resp.json();

      setGraphData({ nodes: data.nodes as AgentNode[], links: data.links as AgentLink[] });
      setStats(data.stats);
      setConnected(true);
      setLoading(false);

      // ─── Strategic Transcript Narrative ───
      const { stats: s, supplyChain, ourProduct } = data;
      const nodes = data.nodes as AgentNode[];

      addLog('success', `Connected. ${s.sellers} sellers, ${s.buyers} buyers across ${s.teams} teams.`);

      // Our product
      setTimeout(() => {
        addLog('strategy', `OUR PRODUCT: ${ourProduct?.name || 'AI Research Engine'}`);
        addLog('info', ourProduct?.valueProposition || 'GPT-4o research and summarization');
      }, 300);

      // Supply chain analysis
      const inbound = (supplyChain as SupplyChainEntry[])?.filter((s: SupplyChainEntry) => s.direction === 'inbound') || [];
      const outbound = (supplyChain as SupplyChainEntry[])?.filter((s: SupplyChainEntry) => s.direction === 'outbound') || [];

      setTimeout(() => {
        addLog('strategy', `SUPPLY CHAIN: ${inbound.length} data suppliers identified`);
      }, 700);

      // Stagger supply chain entries
      inbound.forEach((entry: SupplyChainEntry, i: number) => {
        setTimeout(() => {
          addLog('supply',
            `\u2190 ${entry.agentName} (${entry.team}) \u2014 ${entry.value}`,
            { reason: entry.reason, priority: entry.priority }
          );
          if (i < 3) {
            // Show the WHY for top suppliers
            setTimeout(() => {
              addLog('info', `  \u2514 WHY: ${entry.reason}`);
            }, 80);
          }
        }, 1000 + i * 200);
      });

      const supplyDoneMs = 1200 + inbound.length * 200;

      // Revenue streams
      setTimeout(() => {
        addLog('strategy', `REVENUE: ${outbound.length} potential customer agents identified`);
      }, supplyDoneMs);

      outbound.slice(0, 6).forEach((entry: SupplyChainEntry, i: number) => {
        setTimeout(() => {
          addLog('revenue',
            `\u2192 ${entry.agentName} (${entry.team})`,
            { value: entry.value, priority: entry.priority }
          );
          if (i < 2) {
            setTimeout(() => {
              addLog('info', `  \u2514 WHY THEY BUY: ${entry.reason}`);
            }, 80);
          }
        }, supplyDoneMs + 300 + i * 180);
      });

      const revDoneMs = supplyDoneMs + 500 + Math.min(outbound.length, 6) * 180;

      // Economic summary
      setTimeout(() => {
        addLog('strategy', '\u2500\u2500\u2500 ECONOMY OPTIMIZATION SUMMARY \u2500\u2500\u2500');
        addLog('decide', `Supply cost: ${s.supplyCost} | Revenue streams: ${s.revenueStreams} agents`);
        addLog('decide', `Supply chain depth: ${s.supplyChainDepth} data sources \u2192 our AI engine \u2192 ${s.revenueStreams} customers`);

        const criticalSuppliers = inbound.filter((e: SupplyChainEntry) => e.priority === 'CRITICAL');
        if (criticalSuppliers.length > 0) {
          addLog('decide', `CRITICAL suppliers: ${criticalSuppliers.map((e: SupplyChainEntry) => e.agentName).join(', ')}`);
        }

        addLog('success', 'Autonomous economy analysis complete. Graph centered on our product.');
      }, revDoneMs);

    } catch (err) {
      addLog('error', `Failed: ${err}`);
      setLoading(false);
    }
  }, [addLog]);

  useEffect(() => {
    loadEconomy();
  }, [loadEconomy]);

  const handleNodeClick = useCallback((node: AgentNode) => {
    setSelectedNode(node);
    setSelectedLink(null);

    // Log what we're inspecting with context
    if (node.role === 'our_seller') {
      addLog('action', `Inspecting OUR PRODUCT: ${node.name}`);
    } else if (node.role === 'our_buyer') {
      addLog('action', `Inspecting OUR BUYER agent: ${node.name}`);
    } else if (node.role === 'supplier') {
      addLog('action', `Inspecting supplier: ${node.name} \u2014 ${node.strategicValue || ''}`);
    } else if (node.role === 'customer') {
      addLog('action', `Inspecting customer: ${node.name} \u2014 ${node.strategicValue || ''}`);
    } else {
      addLog('action', `Inspecting: ${node.name} (${node.type})`);
    }
  }, [addLog]);

  const handleLinkClick = useCallback((link: AgentLink) => {
    setSelectedLink(link);
    addLog('action', `Connection: ${link.type} \u2014 ${link.reason}`);
  }, [addLog]);

  const handleSearchSelectNode = useCallback((node: AgentNode) => {
    setSelectedNode(node);
    setSelectedLink(null);
    addLog('action', `Search \u2192 ${node.name} (${node.role || node.type})`);
  }, [addLog]);

  const handleSearchSelectLink = useCallback((link: AgentLink) => {
    setSelectedLink(link);
    addLog('action', `Search \u2192 connection: ${link.reason.slice(0, 60)}...`);
  }, [addLog]);

  const handleRefresh = useCallback(async () => {
    addLog('system', 'Refreshing marketplace data...');
    setLoading(true);
    setTranscript([]);
    await loadEconomy();
  }, [addLog, loadEconomy]);

  if (!dimensions) return null;

  if (loading) {
    return (
      <div className="h-screen w-screen bg-[#050510] flex items-center justify-center">
        <div className="text-center">
          <div className="w-20 h-20 border-4 border-emerald-400/30 border-t-emerald-400 rounded-full animate-spin mb-6 mx-auto" />
          <p className="text-emerald-400 text-xl font-semibold">Mapping the Agentic Economy</p>
          <p className="text-slate-500 text-sm mt-2">Analyzing supply chains, revenue streams, and market positions...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="h-screen w-screen bg-[#050510] relative overflow-hidden">
      <ForceGraph3D
        graphData={graphData}
        onNodeClick={handleNodeClick}
        onLinkClick={handleLinkClick}
        width={dimensions.width}
        height={dimensions.height}
      />

      {/* Title + Stats */}
      <div className="absolute top-4 left-4 right-4 flex items-start justify-between pointer-events-none z-40">
        <div className="pointer-events-auto">
          <div className="flex items-center gap-3">
            <h1 className="text-white font-bold text-xl tracking-tight">
              <span className="text-emerald-400">Agentic</span>Economy
            </h1>
            <button
              onClick={handleRefresh}
              className="p-1.5 rounded-md bg-slate-800/60 border border-slate-700/30 text-slate-400 hover:text-emerald-400 hover:border-emerald-500/30 transition-colors"
              title="Refresh marketplace"
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
              </svg>
            </button>
          </div>
          <p className="text-slate-600 text-xs mt-1">Live marketplace visualization centered on our AI Research product</p>
        </div>

        <div className="pointer-events-auto">
          <SearchBar
            nodes={graphData.nodes}
            links={graphData.links}
            onSelectNode={handleSearchSelectNode}
            onSelectLink={handleSearchSelectLink}
          />
        </div>

        <div className="pointer-events-auto glass-panel rounded-lg px-3 py-2">
          <StatsOverlay
            stats={stats}
            connected={connected}
            nodeCount={graphData.nodes.length}
            linkCount={graphData.links.length}
          />
        </div>
      </div>

      {/* Legend */}
      <div className="absolute top-20 left-4 pointer-events-none z-40">
        <div className="glass-panel rounded-lg px-3 py-2.5 space-y-2 text-xs">
          <div className="text-[10px] uppercase tracking-widest text-slate-500 font-bold mb-1">Supply Chain</div>
          <LegendItem color="#4ade80" ring label="Our Product" />
          <LegendItem color="#22d3ee" shape="hexagon" label="Suppliers (we buy)" />
          <LegendItem color="#fbbf24" shape="pentagon" label="Customers (they buy)" />
          <div className="border-t border-slate-700/30 my-1.5" />
          <div className="text-[10px] uppercase tracking-widest text-slate-500 font-bold mb-1">Links</div>
          <div className="flex items-center gap-2">
            <div className="w-6 h-0.5 bg-cyan-400 rounded" />
            <span className="text-slate-400">Supply flow</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-6 h-0.5 bg-amber-400 rounded" />
            <span className="text-slate-400">Revenue flow</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-6 h-0.5 bg-slate-600 rounded" />
            <span className="text-slate-400">Team ownership</span>
          </div>
        </div>
      </div>

      {/* Link detail tooltip */}
      {selectedLink && !selectedNode && (
        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 pointer-events-auto z-40">
          <div className="glass-panel rounded-xl p-4 max-w-sm animate-fade-in-up">
            <div className="flex items-center justify-between mb-2">
              <span className={`text-xs px-2 py-0.5 rounded font-bold ${
                selectedLink.type === 'supply' ? 'bg-cyan-900/40 text-cyan-300' :
                selectedLink.type === 'customer' ? 'bg-amber-900/40 text-amber-300' :
                'bg-slate-800 text-slate-400'
              }`}>
                {selectedLink.type === 'supply' ? 'SUPPLY CHAIN' :
                 selectedLink.type === 'customer' ? 'REVENUE STREAM' :
                 selectedLink.type.toUpperCase()}
              </span>
              <button onClick={() => setSelectedLink(null)} className="text-slate-500 hover:text-white text-xs">
                \u2715
              </button>
            </div>
            <p className="text-sm text-slate-200 leading-relaxed">{selectedLink.reason}</p>
            {selectedLink.strategicValue && (
              <p className="text-xs text-slate-400 mt-2 italic">{selectedLink.strategicValue}</p>
            )}
          </div>
        </div>
      )}

      {/* Transcript */}
      <div className="absolute bottom-4 left-4 pointer-events-auto z-40">
        <TranscriptStream entries={transcript} />
      </div>

      {/* Agent Inspector */}
      <AgentPanel
        node={selectedNode}
        links={graphData.links}
        allNodes={graphData.nodes}
        onClose={() => setSelectedNode(null)}
      />
    </div>
  );
}

function LegendItem({ color, ring, shape, label }: { color: string; ring?: boolean; shape?: string; label: string }) {
  return (
    <div className="flex items-center gap-2">
      <div
        className={`w-3 h-3 rounded-full ${ring ? 'ring-2 ring-offset-1 ring-offset-[#050510]' : ''}`}
        style={{
          backgroundColor: color,
          borderRadius: shape === 'hexagon' ? '2px' : shape === 'pentagon' ? '3px' : '50%',
        }}
      />
      <span className="text-slate-400">{label}</span>
    </div>
  );
}
