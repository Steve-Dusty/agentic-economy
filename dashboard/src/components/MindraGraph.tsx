'use client';

import { useState, useCallback, useEffect, useRef, useMemo } from 'react';
import dynamic from 'next/dynamic';
import * as THREE from 'three';
import TranscriptStream from './TranscriptStream';
import MindraSearchBar from './MindraSearchBar';
import type { TranscriptEntry } from '@/types/graph';

const ForceGraph3DComponent = dynamic(
  () => import('react-force-graph-3d').then(mod => mod.default || mod),
  { ssr: false }
);

interface MindraNode {
  id: string;
  name: string;
  type: string;
  category: string;
  description: string;
  color: string;
  val: number;
  isCore?: boolean;
  credits?: number;
  department?: string;
  capabilities?: string[];
  steps?: string[];
  agentCount?: number;
  endpoint?: string;
}

interface MindraLink {
  source: string;
  target: string;
  type: string;
  label: string;
  reason: string;
  weight: number;
  color: string;
}

interface MindraStats {
  totalAgents: number;
  departments: number;
  workflows: number;
  creditsPerFullRun: number;
  platform: string;
  paymentLayer: string;
  settlement: string;
}

export default function MindraGraph() {
  const [graphData, setGraphData] = useState<{ nodes: MindraNode[]; links: MindraLink[] }>({ nodes: [], links: [] });
  const [stats, setStats] = useState<MindraStats | null>(null);
  const [selectedNode, setSelectedNode] = useState<MindraNode | null>(null);
  const [transcript, setTranscript] = useState<TranscriptEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [dimensions, setDimensions] = useState<{ width: number; height: number } | null>(null);
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const fgRef = useRef<any>(null);
  const hasZoomedRef = useRef(false);

  const addLog = useCallback((level: TranscriptEntry['level'], message: string, data?: Record<string, unknown>) => {
    setTranscript(prev => [...prev, { timestamp: new Date().toISOString(), level, message, data }]);
  }, []);

  useEffect(() => {
    function updateSize() {
      setDimensions({ width: window.innerWidth, height: window.innerHeight });
    }
    updateSize();
    window.addEventListener('resize', updateSize);
    return () => window.removeEventListener('resize', updateSize);
  }, []);

  const loadData = useCallback(async () => {
    addLog('system', 'Initializing Mindra agent orchestration graph...');
    try {
      addLog('evaluate', 'Fetching Mindra agent network topology...');
      const resp = await fetch('/api/mindra');
      if (!resp.ok) throw new Error(`API error: ${resp.status}`);
      const data = await resp.json();
      setGraphData({ nodes: data.nodes, links: data.links });
      setStats(data.stats);
      addLog('success', `Loaded ${data.nodes.length} nodes and ${data.links.length} connections`, { nodes: data.nodes.length, links: data.links.length });
      addLog('info', `1 orchestrator + ${data.stats.totalAgents} leaf agents: Researcher, Nexus, Writer, QA Checker`);
      addLog('supply', `Payment: ${data.stats.paymentLayer} → ${data.stats.settlement}`);
      addLog('revenue', `${data.stats.creditsPerFullRun} credits per full orchestration run (1 credit/agent)`);
      addLog('strategy', 'Rendering 3D agent orchestration graph...');
      setLoading(false);
    } catch (err) {
      console.error('Failed to load Mindra data:', err);
      addLog('error', `Failed to load Mindra data: ${err}`);
      setLoading(false);
    }
  }, [addLog]);

  useEffect(() => { loadData(); }, [loadData]);

  useEffect(() => {
    const timer = setTimeout(() => {
      const fg = fgRef.current;
      if (fg?.zoomToFit) {
        fg.zoomToFit(1200, 80);
        hasZoomedRef.current = true;
      }
    }, 1200);
    return () => clearTimeout(timer);
  }, [graphData.nodes.length]);

  // Custom force: pull orchestrator toward center
  useEffect(() => {
    const fg = fgRef.current;
    if (!fg) return;
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    fg.d3Force('center-orch', (alpha: number) => {
      graphData.nodes.forEach((node) => {
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        const n = node as any;
        if (n.isCore && n.x !== undefined) {
          n.vx -= n.x * alpha * 0.1;
          n.vy -= n.y * alpha * 0.1;
          n.vz -= n.z * alpha * 0.1;
        }
      });
    });
  }, [graphData.nodes]);

  const glowTextureCache = useRef<Map<string, THREE.Texture>>(new Map());

  const getGlowTexture = useCallback((hex: string) => {
    if (glowTextureCache.current.has(hex)) return glowTextureCache.current.get(hex)!;
    const s = 256;
    const c = document.createElement('canvas');
    c.width = s; c.height = s;
    const ctx = c.getContext('2d')!;
    const g = ctx.createRadialGradient(s / 2, s / 2, 0, s / 2, s / 2, s / 2);
    g.addColorStop(0, hex + '80');
    g.addColorStop(0.2, hex + '50');
    g.addColorStop(0.5, hex + '18');
    g.addColorStop(1, hex + '00');
    ctx.fillStyle = g;
    ctx.fillRect(0, 0, s, s);
    const tex = new THREE.CanvasTexture(c);
    glowTextureCache.current.set(hex, tex);
    return tex;
  }, []);

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const createNodeObject = useCallback((node: any) => {
    const group = new THREE.Group();
    const isCore = node.isCore;
    const isDept = node.type === 'department';
    const isAgent = node.type === 'agent';
    const isWorkflow = node.type === 'workflow';
    const isPayment = node.type === 'payment' || node.type === 'wallet';

    const coreSize = isCore ? 8 : isDept ? 5.5 : isAgent ? 4 : isWorkflow ? 3.5 : isPayment ? 4.5 : 4;
    const baseHex = node.color || '#22d3ee';

    // Core sphere
    const segments = isCore ? 64 : 32;
    const geo = isCore
      ? new THREE.IcosahedronGeometry(coreSize, 2)
      : isDept
        ? new THREE.OctahedronGeometry(coreSize, 1)
        : new THREE.SphereGeometry(coreSize, segments, segments);

    const mat = new THREE.MeshBasicMaterial({
      color: new THREE.Color(baseHex),
      transparent: true,
      opacity: isCore ? 0.95 : isDept ? 0.85 : 0.8,
    });
    group.add(new THREE.Mesh(geo, mat));

    // Glow
    const glowSprite = new THREE.Sprite(
      new THREE.SpriteMaterial({
        map: getGlowTexture(baseHex),
        transparent: true,
        depthWrite: false,
        blending: THREE.AdditiveBlending,
      })
    );
    const glowScale = coreSize * (isCore ? 10 : isDept ? 7 : 5);
    glowSprite.scale.set(glowScale, glowScale, 1);
    group.add(glowSprite);

    // Rings for orchestrator
    if (isCore) {
      for (let i = 0; i < 3; i++) {
        const ringGeo = new THREE.RingGeometry(coreSize * (1.4 + i * 0.35), coreSize * (1.5 + i * 0.35), 64);
        const ringMat = new THREE.MeshBasicMaterial({
          color: new THREE.Color('#4ade80'),
          transparent: true,
          opacity: 0.25 - i * 0.07,
          side: THREE.DoubleSide,
        });
        const ring = new THREE.Mesh(ringGeo, ringMat);
        ring.rotation.x = Math.PI * 0.3 * i;
        ring.rotation.y = Math.PI * 0.4 * i;
        group.add(ring);
      }
    }

    // Credit badge for agents
    if (isAgent && node.credits) {
      const badgeGeo = new THREE.RingGeometry(coreSize * 1.15, coreSize * 1.3, 32);
      const badgeMat = new THREE.MeshBasicMaterial({
        color: new THREE.Color('#fbbf24'),
        transparent: true,
        opacity: 0.3,
        side: THREE.DoubleSide,
      });
      group.add(new THREE.Mesh(badgeGeo, badgeMat));
    }

    // Label
    const labelCanvas = document.createElement('canvas');
    const ctx = labelCanvas.getContext('2d')!;
    labelCanvas.width = 512;
    labelCanvas.height = 96;

    const fontSize = isCore ? 28 : isDept ? 22 : 18;
    ctx.font = `${isCore || isDept ? '600' : '400'} ${fontSize}px -apple-system, BlinkMacSystemFont, "SF Pro Text", "Inter", sans-serif`;
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    ctx.shadowColor = 'rgba(0,0,0,0.9)';
    ctx.shadowBlur = 12;
    ctx.fillStyle = isCore ? 'rgba(134,239,172,0.95)' : 'rgba(226,232,240,0.85)';
    const name = (node.name || '').length > 22 ? (node.name || '').slice(0, 20) + '\u2026' : (node.name || '');
    ctx.fillText(name, 256, 36);

    // Sub-label
    if (isAgent) {
      ctx.font = '400 13px -apple-system, sans-serif';
      ctx.fillStyle = 'rgba(251,191,36,0.8)';
      ctx.fillText(`${node.credits || 1} credit${(node.credits || 1) > 1 ? 's' : ''}/call`, 256, 72);
    } else if (isDept) {
      ctx.font = '400 13px -apple-system, sans-serif';
      ctx.fillStyle = `rgba(226,232,240,0.5)`;
      ctx.fillText(`${node.agentCount || 0} agents`, 256, 72);
    }

    const labelTex = new THREE.CanvasTexture(labelCanvas);
    labelTex.minFilter = THREE.LinearFilter;
    const labelSprite = new THREE.Sprite(
      new THREE.SpriteMaterial({ map: labelTex, transparent: true, depthTest: false })
    );
    const lw = coreSize * 6;
    labelSprite.scale.set(lw, lw * (96 / 512), 1);
    labelSprite.position.y = -coreSize - 3;
    group.add(labelSprite);

    return group;
  }, [getGlowTexture]);

  const data = useMemo(() => ({
    nodes: graphData.nodes.map(n => ({ ...n })),
    links: graphData.links.map(l => ({
      ...l,
      source: typeof l.source === 'object' ? (l.source as unknown as { id: string }).id : l.source,
      target: typeof l.target === 'object' ? (l.target as unknown as { id: string }).id : l.target,
    })),
  }), [graphData]);

  const flyToNode = useCallback((nodeId: string) => {
    const fg = fgRef.current;
    if (!fg) return;
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const gfxNode = data.nodes.find((n: any) => n.id === nodeId);
    if (!gfxNode) return;
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const n = gfxNode as any;
    if (fg.cameraPosition && n.x !== undefined) {
      const distance = 80;
      const distRatio = 1 + distance / Math.hypot(n.x || 0.1, n.y || 0.1, n.z || 0.1);
      fg.cameraPosition(
        { x: (n.x || 0) * distRatio, y: (n.y || 0) * distRatio, z: (n.z || 0) * distRatio },
        { x: n.x || 0, y: n.y || 0, z: n.z || 0 },
        800
      );
    }
  }, [data.nodes]);

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const handleNodeClick = useCallback((node: any) => {
    const mNode = graphData.nodes.find(n => n.id === node.id);
    if (mNode) {
      setSelectedNode(mNode);
      addLog('action', `Inspecting: ${mNode.name}`, { type: mNode.type, category: mNode.category });
      if (mNode.credits) addLog('revenue', `Credit cost: ${mNode.credits}/call`);
      if (mNode.capabilities?.length) addLog('info', `Capabilities: ${mNode.capabilities.join(', ')}`);
      if (mNode.steps?.length) addLog('info', `Pipeline: ${mNode.steps.join(' → ')}`);
      if (mNode.endpoint) addLog('supply', `Endpoint: ${mNode.endpoint}`);
    }

    const fg = fgRef.current;
    if (fg?.cameraPosition) {
      const distance = 80;
      const distRatio = 1 + distance / Math.hypot(node.x || 0.1, node.y || 0.1, node.z || 0.1);
      fg.cameraPosition(
        { x: (node.x || 0) * distRatio, y: (node.y || 0) * distRatio, z: (node.z || 0) * distRatio },
        { x: node.x || 0, y: node.y || 0, z: node.z || 0 },
        800
      );
    }
  }, [graphData, addLog]);

  const handleSearchSelect = useCallback((node: MindraNode) => {
    setSelectedNode(node);
    addLog('action', `Searched → ${node.name}`, { type: node.type, category: node.category });
    flyToNode(node.id);
  }, [addLog, flyToNode]);

  // Link style helpers
  const LINK_TYPE_STYLES: Record<string, { particles: number; particleColor: string; speed: number }> = {
    routes_to: { particles: 3, particleColor: '#4ade80', speed: 0.01 },
    result: { particles: 2, particleColor: '#94a3b8', speed: 0.008 },
    payment: { particles: 4, particleColor: '#fbbf24', speed: 0.012 },
    x402_auth: { particles: 2, particleColor: '#c084fc', speed: 0.006 },
    request: { particles: 4, particleColor: '#60a5fa', speed: 0.01 },
    delivery: { particles: 4, particleColor: '#4ade80', speed: 0.01 },
    feeds: { particles: 2, particleColor: '#22d3ee', speed: 0.008 },
  };

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const FG = ForceGraph3DComponent as any;

  if (!dimensions) return null;

  if (loading) {
    return (
      <div className="h-full w-full bg-[#050510] flex items-center justify-center">
        <div className="text-center">
          <div className="w-16 h-16 border-4 border-violet-400/30 border-t-violet-400 rounded-full animate-spin mb-4 mx-auto" />
          <p className="text-violet-400 text-lg font-medium">Loading Mindra Agents...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="h-full w-full bg-[#050510] relative overflow-hidden">
      {data.nodes.length > 0 && (
        <FG
          ref={fgRef}
          graphData={data}
          width={dimensions.width}
          height={dimensions.height - 56}
          backgroundColor="#050510"
          nodeThreeObject={createNodeObject}
          nodeThreeObjectExtend={false}
          onNodeClick={handleNodeClick}
          linkColor={(link: MindraLink) => link.color || 'rgba(100,116,139,0.1)'}
          linkWidth={(link: MindraLink) => Math.max(0.3, link.weight * 0.45)}
          linkDirectionalParticles={(link: MindraLink) => LINK_TYPE_STYLES[link.type]?.particles || 0}
          linkDirectionalParticleWidth={1.5}
          linkDirectionalParticleSpeed={(link: MindraLink) => LINK_TYPE_STYLES[link.type]?.speed || 0.005}
          linkDirectionalParticleColor={(link: MindraLink) => LINK_TYPE_STYLES[link.type]?.particleColor || '#64748b'}
          linkCurvature={0.15}
          linkOpacity={0.7}
          d3AlphaDecay={0.012}
          d3VelocityDecay={0.22}
          warmupTicks={100}
          cooldownTime={5000}
          onEngineStop={() => {
            if (hasZoomedRef.current) return;
            const fg = fgRef.current;
            if (fg?.zoomToFit) {
              fg.zoomToFit(800, 80);
              hasZoomedRef.current = true;
            }
          }}
        />
      )}

      {/* Search Bar */}
      <div className="absolute top-4 left-1/2 -translate-x-1/2 z-50 pointer-events-auto">
        <MindraSearchBar
          nodes={graphData.nodes}
          links={graphData.links}
          onSelectNode={handleSearchSelect}
        />
      </div>

      {/* Stats Bar */}
      {stats && (
        <div className="absolute top-16 left-4 pointer-events-none z-40">
          <div className="glass-panel rounded-lg px-4 py-3 pointer-events-auto">
            <div className="flex items-center gap-2 mb-2">
              <div className="w-2 h-2 rounded-full bg-violet-400 animate-pulse-glow" />
              <span className="text-xs font-bold text-violet-400 uppercase tracking-widest">Mindra Agent Network</span>
            </div>
            <div className="grid grid-cols-2 gap-x-6 gap-y-1 text-xs">
              <div>
                <span className="text-emerald-400 font-medium">{stats.totalAgents}</span>
                <span className="text-slate-500 ml-1">leaf agents</span>
              </div>
              <div>
                <span className="text-amber-400 font-medium">{stats.creditsPerFullRun}</span>
                <span className="text-slate-500 ml-1">credits/full run</span>
              </div>
              <div className="col-span-2">
                <span className="text-violet-400 font-medium">{stats.paymentLayer}</span>
                <span className="text-slate-500 ml-1">→ {stats.settlement}</span>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Legend */}
      <div className="absolute top-16 right-4 pointer-events-none z-40">
        <div className="glass-panel rounded-lg px-3 py-2.5 space-y-1.5 text-xs pointer-events-auto">
          <div className="text-[10px] uppercase tracking-widest text-slate-500 font-bold mb-1">Nodes</div>
          <LegendItem color="#4ade80" label="Orchestrator" />
          <LegendItem color="#22d3ee" label="Researcher" />
          <LegendItem color="#818cf8" label="Nexus" />
          <LegendItem color="#fbbf24" label="Writer" />
          <LegendItem color="#f472b6" label="QA Checker" />
          <LegendItem color="#c084fc" label="Nevermined x402" />
          <LegendItem color="#60a5fa" label="Client I/O" />
          <div className="border-t border-slate-700/30 my-1" />
          <div className="text-[10px] uppercase tracking-widest text-slate-500 font-bold mb-1">Connections</div>
          <div className="flex items-center gap-2">
            <div className="w-6 h-0.5 bg-emerald-400 rounded" />
            <span className="text-slate-400">Task dispatch</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-6 h-0.5 bg-violet-400 rounded" />
            <span className="text-slate-400">Payment (x402)</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-6 h-0.5 bg-cyan-400/50 rounded" />
            <span className="text-slate-400">Agent ↔ Agent</span>
          </div>
        </div>
      </div>

      {/* Node Detail Panel */}
      {selectedNode && (
        <div className="absolute bottom-4 left-4 pointer-events-auto z-40 max-w-md">
          <div className="glass-panel rounded-xl p-4 animate-fade-in-up">
            <div className="flex items-center justify-between mb-2">
              <div className="flex items-center gap-2">
                <div className="w-3 h-3 rounded-full" style={{ backgroundColor: selectedNode.color }} />
                <h3 className="text-sm font-bold text-white">{selectedNode.name}</h3>
              </div>
              <button onClick={() => setSelectedNode(null)} className="text-slate-500 hover:text-white text-xs">✕</button>
            </div>
            <span className={`text-[10px] px-2 py-0.5 rounded-full font-bold tracking-wider mb-2 inline-block ${
              selectedNode.isCore ? 'bg-emerald-900/60 text-emerald-300' :
              selectedNode.type === 'department' ? 'bg-indigo-900/60 text-indigo-300' :
              selectedNode.type === 'agent' ? 'bg-cyan-900/60 text-cyan-300' :
              selectedNode.type === 'workflow' ? 'bg-fuchsia-900/60 text-fuchsia-300' :
              selectedNode.type === 'payment' || selectedNode.type === 'wallet' ? 'bg-violet-900/60 text-violet-300' :
              'bg-slate-700 text-slate-300'
            }`}>
              {selectedNode.type.toUpperCase()}
            </span>
            <p className="text-xs text-slate-300 leading-relaxed mt-1">{selectedNode.description}</p>

            {selectedNode.credits && (
              <div className="mt-2 flex items-center gap-2">
                <span className="text-[10px] text-slate-500">Cost:</span>
                <span className="text-xs text-amber-400 font-bold">{selectedNode.credits} credit{selectedNode.credits > 1 ? 's' : ''}/call</span>
              </div>
            )}

            {selectedNode.capabilities && selectedNode.capabilities.length > 0 && (
              <div className="mt-2">
                <span className="text-[10px] text-slate-500 block mb-1">Capabilities:</span>
                <div className="flex flex-wrap gap-1">
                  {selectedNode.capabilities.map((cap, i) => (
                    <span key={i} className="text-[10px] px-1.5 py-0.5 rounded bg-slate-800 text-slate-400">{cap}</span>
                  ))}
                </div>
              </div>
            )}

            {selectedNode.steps && selectedNode.steps.length > 0 && (
              <div className="mt-2">
                <span className="text-[10px] text-slate-500 block mb-1">Pipeline Steps:</span>
                <div className="flex items-center gap-1 text-[10px] text-slate-400">
                  {selectedNode.steps.map((step, i) => (
                    <span key={i} className="flex items-center gap-1">
                      <span className="px-1.5 py-0.5 rounded bg-fuchsia-900/40 text-fuchsia-300">{step}</span>
                      {i < selectedNode.steps!.length - 1 && <span className="text-slate-600">→</span>}
                    </span>
                  ))}
                </div>
              </div>
            )}

            {selectedNode.endpoint && (
              <p className="text-[10px] text-cyan-400 mt-2 font-mono break-all">{selectedNode.endpoint}</p>
            )}
          </div>
        </div>
      )}

      {/* Transcript Stream */}
      <div className="absolute bottom-4 right-4 z-40 pointer-events-auto">
        <TranscriptStream entries={transcript} />
      </div>
    </div>
  );
}

function LegendItem({ color, label }: { color: string; shape?: string; label: string }) {
  return (
    <div className="flex items-center gap-2">
      <div className="w-3 h-3 rounded-full" style={{ backgroundColor: color }} />
      <span className="text-slate-400">{label}</span>
    </div>
  );
}
