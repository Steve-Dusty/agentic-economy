'use client';

import { useState, useCallback, useEffect, useRef, useMemo } from 'react';
import dynamic from 'next/dynamic';
import * as THREE from 'three';
import TranscriptStream from './TranscriptStream';
import ZeroClickSearchBar from './ZeroClickSearchBar';
import type { TranscriptEntry } from '@/types/graph';

const ForceGraph3DComponent = dynamic(
  () => import('react-force-graph-3d').then(mod => mod.default || mod),
  { ssr: false }
);

interface ZCNode {
  id: string;
  name: string;
  type: string;
  category: string;
  description: string;
  color: string;
  val: number;
  isCore?: boolean;
  isOurs?: boolean;
  monetizationWeight?: number;
  amount?: string;
  url?: string;
}

interface ZCLink {
  source: string;
  target: string;
  type: string;
  label: string;
  reason: string;
  weight: number;
  color: string;
}

interface ZCStats {
  signalCategories: number;
  apiEndpoints: number;
  revenueModels: number;
  avgCPC: string;
  avgCPM: string;
  avgCPA: string;
  totalNodes: number;
  totalLinks: number;
}

export default function ZeroClickGraph() {
  const [graphData, setGraphData] = useState<{ nodes: ZCNode[]; links: ZCLink[] }>({ nodes: [], links: [] });
  const [stats, setStats] = useState<ZCStats | null>(null);
  const [selectedNode, setSelectedNode] = useState<ZCNode | null>(null);
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
    addLog('system', 'Initializing ZeroClick.ai economy graph...');
    try {
      addLog('evaluate', 'Fetching ZeroClick.ai ad ecosystem data...');
      const resp = await fetch('/api/zeroclick');
      if (!resp.ok) throw new Error(`API error: ${resp.status}`);
      const data = await resp.json();
      setGraphData({ nodes: data.nodes, links: data.links });
      setStats(data.stats);
      addLog('success', `Loaded ${data.nodes.length} nodes and ${data.links.length} links`, { nodes: data.nodes.length, links: data.links.length });
      addLog('info', `Signal categories: ${data.stats.signalCategories} · APIs: ${data.stats.apiEndpoints} · Revenue models: ${data.stats.revenueModels}`);
      addLog('revenue', `Ad pricing — CPC: ${data.stats.avgCPC} · CPM: ${data.stats.avgCPM} · CPA: ${data.stats.avgCPA}`);
      addLog('strategy', 'Rendering 3D knowledge graph of ZeroClick.ai ad economy...');
      setLoading(false);
    } catch (err) {
      console.error('Failed to load ZeroClick data:', err);
      addLog('error', `Failed to load ZeroClick data: ${err}`);
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
    const isOurs = node.isOurs;
    const isSignal = node.type === 'signal';
    const isRevenue = node.category === 'revenue';
    const isApi = node.type === 'api';

    const coreSize = isCore ? 7 : isOurs ? 6 : isSignal ? 3 + (node.monetizationWeight || 1) * 0.5 : isRevenue ? 4.5 : isApi ? 3.5 : 4;
    const baseHex = node.color || '#22d3ee';

    // Core sphere
    const segments = isCore || isOurs ? 64 : 32;
    const coreGeo = new THREE.SphereGeometry(coreSize, segments, segments);
    const coreMat = new THREE.MeshBasicMaterial({
      color: new THREE.Color(baseHex),
      transparent: true,
      opacity: isCore ? 0.95 : 0.8,
    });
    group.add(new THREE.Mesh(coreGeo, coreMat));

    // Glow
    const glowSprite = new THREE.Sprite(
      new THREE.SpriteMaterial({
        map: getGlowTexture(baseHex),
        transparent: true,
        depthWrite: false,
        blending: THREE.AdditiveBlending,
      })
    );
    const glowScale = coreSize * (isCore ? 10 : isOurs ? 8 : 5);
    glowSprite.scale.set(glowScale, glowScale, 1);
    group.add(glowSprite);

    // Ring for core / our nodes
    if (isCore || isOurs) {
      const ringGeo = new THREE.RingGeometry(coreSize * 1.4, coreSize * 1.6, 64);
      const ringMat = new THREE.MeshBasicMaterial({
        color: new THREE.Color(baseHex),
        transparent: true,
        opacity: 0.3,
        side: THREE.DoubleSide,
      });
      group.add(new THREE.Mesh(ringGeo, ringMat));
    }

    // Revenue tier shape
    if (node.type === 'revenue_tier') {
      const ringGeo = new THREE.RingGeometry(coreSize * 1.2, coreSize * 1.35, 8);
      const ringMat = new THREE.MeshBasicMaterial({
        color: new THREE.Color(baseHex),
        transparent: true,
        opacity: 0.25,
        side: THREE.DoubleSide,
      });
      group.add(new THREE.Mesh(ringGeo, ringMat));
    }

    // Label
    const labelCanvas = document.createElement('canvas');
    const ctx = labelCanvas.getContext('2d')!;
    labelCanvas.width = 512;
    labelCanvas.height = 80;
    const fontSize = isCore ? 26 : isOurs ? 24 : 18;
    ctx.font = `${isCore || isOurs ? '600' : '400'} ${fontSize}px -apple-system, BlinkMacSystemFont, "SF Pro Text", "Inter", sans-serif`;
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    ctx.shadowColor = 'rgba(0,0,0,0.9)';
    ctx.shadowBlur = 12;
    ctx.fillStyle = isCore || isOurs ? 'rgba(134,239,172,0.95)' : 'rgba(226,232,240,0.85)';
    const name = (node.name || '').length > 24 ? (node.name || '').slice(0, 22) + '\u2026' : (node.name || '');
    ctx.fillText(name, 256, 40);

    const labelTex = new THREE.CanvasTexture(labelCanvas);
    labelTex.minFilter = THREE.LinearFilter;
    const labelSprite = new THREE.Sprite(
      new THREE.SpriteMaterial({ map: labelTex, transparent: true, depthTest: false })
    );
    const lw = coreSize * 6;
    labelSprite.scale.set(lw, lw * (80 / 512), 1);
    labelSprite.position.y = -coreSize - 2.5;
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
      const distance = 90;
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
    const zcNode = graphData.nodes.find(n => n.id === node.id);
    if (zcNode) {
      setSelectedNode(zcNode);
      addLog('action', `Inspecting node: ${zcNode.name}`, { type: zcNode.type, category: zcNode.category });
      if (zcNode.monetizationWeight) addLog('revenue', `Monetization weight: ${zcNode.monetizationWeight}/5`);
      if (zcNode.url) addLog('info', `API endpoint: ${zcNode.url}`);
      if (zcNode.amount) addLog('revenue', `Revenue metric: ${zcNode.amount}`);
    }

    const fg = fgRef.current;
    if (fg?.cameraPosition) {
      const distance = 90;
      const distRatio = 1 + distance / Math.hypot(node.x || 0.1, node.y || 0.1, node.z || 0.1);
      fg.cameraPosition(
        { x: (node.x || 0) * distRatio, y: (node.y || 0) * distRatio, z: (node.z || 0) * distRatio },
        { x: node.x || 0, y: node.y || 0, z: node.z || 0 },
        800
      );
    }
  }, [graphData, addLog]);

  const handleSearchSelect = useCallback((node: ZCNode) => {
    setSelectedNode(node);
    addLog('action', `Searched → ${node.name}`, { type: node.type, category: node.category });
    flyToNode(node.id);
  }, [addLog, flyToNode]);

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const FG = ForceGraph3DComponent as any;

  if (!dimensions) return null;

  if (loading) {
    return (
      <div className="h-full w-full bg-[#050510] flex items-center justify-center">
        <div className="text-center">
          <div className="w-16 h-16 border-4 border-cyan-400/30 border-t-cyan-400 rounded-full animate-spin mb-4 mx-auto" />
          <p className="text-cyan-400 text-lg font-medium">Loading ZeroClick.ai Economy...</p>
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
          linkColor={(link: ZCLink) => link.color || 'rgba(100,116,139,0.1)'}
          linkWidth={(link: ZCLink) => Math.max(0.3, link.weight * 0.4)}
          linkDirectionalParticles={(link: ZCLink) => link.type === 'revenue' || link.type === 'payout' ? 4 : link.weight > 3 ? 2 : 0}
          linkDirectionalParticleWidth={1.5}
          linkDirectionalParticleSpeed={0.008}
          linkDirectionalParticleColor={(link: ZCLink) => link.color?.replace(/[\d.]+\)$/, '1)') || '#4ade80'}
          linkCurvature={0.12}
          linkOpacity={0.7}
          d3AlphaDecay={0.015}
          d3VelocityDecay={0.25}
          warmupTicks={80}
          cooldownTime={4000}
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
        <ZeroClickSearchBar
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
              <div className="w-2 h-2 rounded-full bg-cyan-400 animate-pulse-glow" />
              <span className="text-xs font-bold text-cyan-400 uppercase tracking-widest">ZeroClick.ai Ad Economy</span>
            </div>
            <div className="grid grid-cols-2 gap-x-6 gap-y-1 text-xs">
              <div>
                <span className="text-cyan-400 font-medium">{stats.signalCategories}</span>
                <span className="text-slate-500 ml-1">signal types</span>
              </div>
              <div>
                <span className="text-indigo-400 font-medium">{stats.apiEndpoints}</span>
                <span className="text-slate-500 ml-1">API endpoints</span>
              </div>
              <div>
                <span className="text-amber-400 font-medium">{stats.avgCPC}</span>
                <span className="text-slate-500 ml-1">CPC</span>
              </div>
              <div>
                <span className="text-emerald-400 font-medium">{stats.avgCPA}</span>
                <span className="text-slate-500 ml-1">CPA</span>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Legend */}
      <div className="absolute top-4 right-4 pointer-events-none z-40">
        <div className="glass-panel rounded-lg px-3 py-2.5 space-y-1.5 text-xs pointer-events-auto">
          <div className="text-[10px] uppercase tracking-widest text-slate-500 font-bold mb-1">Node Types</div>
          <LegendItem color="#4ade80" label="Core Engine" />
          <LegendItem color="#60a5fa" label="Users" />
          <LegendItem color="#c084fc" label="AI Processor" />
          <LegendItem color="#818cf8" label="API Endpoints" />
          <LegendItem color="#22d3ee" label="Signal Categories" />
          <LegendItem color="#fbbf24" label="Advertisers" />
          <LegendItem color="#4ade80" label="Revenue" />
          <div className="border-t border-slate-700/30 my-1" />
          <div className="text-[10px] uppercase tracking-widest text-slate-500 font-bold mb-1">Flows</div>
          <div className="flex items-center gap-2">
            <div className="w-6 h-0.5 bg-emerald-400 rounded" />
            <span className="text-slate-400">Revenue flow</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-6 h-0.5 bg-indigo-400 rounded" />
            <span className="text-slate-400">Data flow</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-6 h-0.5 bg-amber-400 rounded" />
            <span className="text-slate-400">Ad supply</span>
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
              selectedNode.isOurs ? 'bg-emerald-900/60 text-emerald-300' :
              selectedNode.type === 'signal' ? 'bg-cyan-900/60 text-cyan-300' :
              selectedNode.category === 'revenue' ? 'bg-amber-900/60 text-amber-300' :
              'bg-slate-700 text-slate-300'
            }`}>
              {selectedNode.type.toUpperCase()}
            </span>
            <p className="text-xs text-slate-300 leading-relaxed mt-1">{selectedNode.description}</p>
            {selectedNode.url && (
              <p className="text-xs text-cyan-400 mt-2 font-mono">{selectedNode.url}</p>
            )}
            {selectedNode.amount && (
              <p className="text-xs text-emerald-400 mt-1 font-bold">{selectedNode.amount}</p>
            )}
            {selectedNode.monetizationWeight && (
              <div className="mt-2 flex items-center gap-1">
                <span className="text-[10px] text-slate-500">Monetization:</span>
                <div className="flex gap-0.5">
                  {Array.from({ length: 5 }).map((_, i) => (
                    <div key={i} className={`w-2 h-2 rounded-full ${i < selectedNode.monetizationWeight! ? 'bg-emerald-400' : 'bg-slate-700'}`} />
                  ))}
                </div>
              </div>
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

function LegendItem({ color, label }: { color: string; label: string }) {
  return (
    <div className="flex items-center gap-2">
      <div className="w-3 h-3 rounded-full" style={{ backgroundColor: color }} />
      <span className="text-slate-400">{label}</span>
    </div>
  );
}
