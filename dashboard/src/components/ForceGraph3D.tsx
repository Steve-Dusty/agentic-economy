'use client';

import { useRef, useCallback, useMemo, useEffect } from 'react';
import dynamic from 'next/dynamic';
import type { GraphData, AgentNode, AgentLink } from '@/types/graph';
import * as THREE from 'three';

const ForceGraph3DComponent = dynamic(
  () => import('react-force-graph-3d').then(mod => mod.default || mod),
  { ssr: false }
);

interface Props {
  graphData: GraphData;
  onNodeClick?: (node: AgentNode) => void;
  onLinkClick?: (link: AgentLink) => void;
  width: number;
  height: number;
}

// Link type → visual style
const LINK_STYLES: Record<string, { color: string; width: number; particles: number; particleColor: string; speed: number }> = {
  supply:     { color: 'rgba(34, 211, 238, 0.5)',  width: 1.8, particles: 3, particleColor: '#22d3ee', speed: 0.008 },
  customer:   { color: 'rgba(251, 191, 36, 0.5)',  width: 1.8, particles: 3, particleColor: '#fbbf24', speed: 0.008 },
  we_buy:     { color: 'rgba(74, 222, 128, 0.6)',  width: 2.0, particles: 4, particleColor: '#4ade80', speed: 0.01 },
  they_buy:   { color: 'rgba(251, 146, 60, 0.5)',  width: 1.5, particles: 2, particleColor: '#fb923c', speed: 0.006 },
  owns:       { color: 'rgba(148, 163, 184, 0.12)', width: 0.3, particles: 0, particleColor: '#64748b', speed: 0 },
  peer_trade: { color: 'rgba(100, 116, 139, 0.08)', width: 0.15, particles: 0, particleColor: '#475569', speed: 0 },
};

export default function ForceGraph3D({ graphData, onNodeClick, onLinkClick, width, height }: Props) {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const fgRef = useRef<any>(null);
  const hasZoomedRef = useRef(false);

  useEffect(() => {
    hasZoomedRef.current = false;
  }, [graphData.nodes.length]);

  useEffect(() => {
    const timer = setTimeout(() => {
      const fg = fgRef.current;
      if (fg?.zoomToFit) {
        fg.zoomToFit(1200, 60);
        hasZoomedRef.current = true;
      }
    }, 1000);
    return () => clearTimeout(timer);
  }, [graphData.nodes.length]);

  // Custom force: pull "our" nodes toward center
  useEffect(() => {
    const fg = fgRef.current;
    if (!fg) return;
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    fg.d3Force('center-ours', (alpha: number) => {
      graphData.nodes.forEach((node) => {
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        const n = node as any;
        if (n.isOurs && n.x !== undefined) {
          n.vx -= n.x * alpha * 0.08;
          n.vy -= n.y * alpha * 0.08;
          n.vz -= n.z * alpha * 0.08;
        }
      });
    });
  }, [graphData.nodes]);

  const data = useMemo(() => ({
    nodes: graphData.nodes.map(n => ({ ...n })),
    links: graphData.links.map(l => ({
      ...l,
      source: typeof l.source === 'object' ? (l.source as unknown as { id: string }).id : l.source,
      target: typeof l.target === 'object' ? (l.target as unknown as { id: string }).id : l.target,
    })),
  }), [graphData]);

  // Glow texture cache
  const glowTextureCache = useRef<Map<string, THREE.Texture>>(new Map());

  const getGlowTexture = useCallback((hex: string) => {
    if (glowTextureCache.current.has(hex)) return glowTextureCache.current.get(hex)!;
    const s = 256;
    const c = document.createElement('canvas');
    c.width = s; c.height = s;
    const ctx = c.getContext('2d')!;
    const g = ctx.createRadialGradient(s / 2, s / 2, 0, s / 2, s / 2, s / 2);
    g.addColorStop(0, hex + '90');
    g.addColorStop(0.15, hex + '60');
    g.addColorStop(0.4, hex + '20');
    g.addColorStop(0.7, hex + '08');
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
    const isTeam = node.type === 'team';
    const isSeller = node.type === 'seller';
    const isOurs = node.isOurs;

    const baseVal = node.val || 10;
    const coreSize = isTeam
      ? (isOurs ? 7 : 4.5)
      : isSeller
        ? (isOurs ? 5.5 : 2.8)
        : (isOurs ? 4.5 : 2.2);

    const baseHex = node.color || '#22d3ee';
    const brightHex = isOurs ? '#86efac' : lightenHex(baseHex, 50);

    // Core sphere
    const segments = isOurs ? 64 : 40;
    const coreGeo = new THREE.SphereGeometry(coreSize, segments, segments);
    const coreMat = new THREE.MeshBasicMaterial({
      color: new THREE.Color(baseHex),
      transparent: true,
      opacity: isOurs ? 0.95 : 0.82,
    });
    group.add(new THREE.Mesh(coreGeo, coreMat));

    // Inner highlight
    const hlGeo = new THREE.SphereGeometry(coreSize * 0.4, 24, 24);
    const hlMat = new THREE.MeshBasicMaterial({
      color: new THREE.Color(brightHex),
      transparent: true,
      opacity: isOurs ? 0.5 : 0.25,
    });
    const hl = new THREE.Mesh(hlGeo, hlMat);
    hl.position.set(coreSize * 0.2, coreSize * 0.25, coreSize * 0.2);
    group.add(hl);

    // Glow
    const glowSprite = new THREE.Sprite(
      new THREE.SpriteMaterial({
        map: getGlowTexture(baseHex),
        transparent: true,
        depthWrite: false,
        blending: THREE.AdditiveBlending,
      })
    );
    const glowScale = coreSize * (isOurs ? 10 : isTeam ? 7 : 5.5);
    glowSprite.scale.set(glowScale, glowScale, 1);
    group.add(glowSprite);

    // Pulsing ring for our agents
    if (isOurs) {
      const ringGeo = new THREE.RingGeometry(coreSize * 1.5, coreSize * 1.7, 64);
      const ringMat = new THREE.MeshBasicMaterial({
        color: new THREE.Color('#4ade80'),
        transparent: true,
        opacity: 0.35,
        side: THREE.DoubleSide,
      });
      group.add(new THREE.Mesh(ringGeo, ringMat));

      // Second outer ring
      const ring2Geo = new THREE.RingGeometry(coreSize * 2.0, coreSize * 2.1, 64);
      const ring2Mat = new THREE.MeshBasicMaterial({
        color: new THREE.Color('#4ade80'),
        transparent: true,
        opacity: 0.15,
        side: THREE.DoubleSide,
      });
      group.add(new THREE.Mesh(ring2Geo, ring2Mat));
    }

    // Role badge for supply chain nodes
    if (node.role === 'supplier') {
      const badgeGeo = new THREE.RingGeometry(coreSize * 1.2, coreSize * 1.35, 6); // hexagon
      const badgeMat = new THREE.MeshBasicMaterial({
        color: new THREE.Color('#22d3ee'),
        transparent: true,
        opacity: 0.25,
        side: THREE.DoubleSide,
      });
      group.add(new THREE.Mesh(badgeGeo, badgeMat));
    }
    if (node.role === 'customer') {
      const badgeGeo = new THREE.RingGeometry(coreSize * 1.2, coreSize * 1.35, 5); // pentagon
      const badgeMat = new THREE.MeshBasicMaterial({
        color: new THREE.Color('#fbbf24'),
        transparent: true,
        opacity: 0.25,
        side: THREE.DoubleSide,
      });
      group.add(new THREE.Mesh(badgeGeo, badgeMat));
    }

    // Label
    const labelCanvas = document.createElement('canvas');
    const ctx = labelCanvas.getContext('2d')!;
    labelCanvas.width = 512;
    labelCanvas.height = 96;

    const fontSize = isOurs ? 28 : isTeam ? 24 : 20;
    ctx.font = `${isOurs || isTeam ? '600' : '400'} ${fontSize}px -apple-system, BlinkMacSystemFont, "SF Pro Text", "Inter", sans-serif`;
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    ctx.shadowColor = 'rgba(0,0,0,0.9)';
    ctx.shadowBlur = 12;
    ctx.shadowOffsetY = 1;

    // Color: our agents = bright green, others = their color
    ctx.fillStyle = isOurs ? 'rgba(134,239,172,0.95)' : `rgba(226,232,240,0.8)`;
    const name = (node.name || '').length > 26 ? (node.name || '').slice(0, 24) + '\u2026' : (node.name || '');
    ctx.fillText(name, 256, 36);

    // Sub-label for role
    if (node.role && !isTeam) {
      ctx.font = `400 14px -apple-system, sans-serif`;
      const roleLabel = node.role === 'our_seller' ? '\u2302 OUR PRODUCT'
        : node.role === 'our_buyer' ? '\u2941 OUR BUYER'
        : node.role === 'supplier' ? '\u25B6 SUPPLIER'
        : node.role === 'customer' ? '\u25C0 CUSTOMER'
        : '';
      ctx.fillStyle = node.role === 'supplier' ? 'rgba(34,211,238,0.7)' :
                       node.role === 'customer' ? 'rgba(251,191,36,0.7)' :
                       'rgba(134,239,172,0.7)';
      ctx.fillText(roleLabel, 256, 72);
    }

    const labelTex = new THREE.CanvasTexture(labelCanvas);
    labelTex.minFilter = THREE.LinearFilter;
    const labelSprite = new THREE.Sprite(
      new THREE.SpriteMaterial({ map: labelTex, transparent: true, depthTest: false })
    );
    const lw = coreSize * 6.5;
    labelSprite.scale.set(lw, lw * (96 / 512), 1);
    labelSprite.position.y = -coreSize - 3;
    group.add(labelSprite);

    return group;
  }, [getGlowTexture]);

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const handleNodeClick = useCallback((node: any) => {
    if (!node.id) return;
    const agentNode = graphData.nodes.find(n => n.id === node.id);
    if (agentNode && onNodeClick) onNodeClick(agentNode);

    const fg = fgRef.current;
    if (fg?.cameraPosition) {
      const distance = 100;
      const distRatio = 1 + distance / Math.hypot(node.x || 0.1, node.y || 0.1, node.z || 0.1);
      fg.cameraPosition(
        { x: (node.x || 0) * distRatio, y: (node.y || 0) * distRatio, z: (node.z || 0) * distRatio },
        { x: node.x || 0, y: node.y || 0, z: node.z || 0 },
        1000
      );
    }
  }, [graphData, onNodeClick]);

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const handleLinkClick = useCallback((link: any) => {
    if (onLinkClick) {
      const agentLink = graphData.links.find(l => {
        const ls = typeof l.source === 'object' ? (l.source as unknown as { id: string }).id : l.source;
        const lt = typeof l.target === 'object' ? (l.target as unknown as { id: string }).id : l.target;
        const cs = typeof link.source === 'object' ? link.source.id : link.source;
        const ct = typeof link.target === 'object' ? link.target.id : link.target;
        return ls === cs && lt === ct && l.type === link.type;
      });
      if (agentLink) onLinkClick(agentLink);
    }
  }, [graphData, onLinkClick]);

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const getLinkColor = useCallback((link: any) => {
    return LINK_STYLES[link.type]?.color || 'rgba(100,116,139,0.05)';
  }, []);

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const getLinkWidth = useCallback((link: any) => {
    const base = LINK_STYLES[link.type]?.width || 0.2;
    // Scale by priority
    if (link.priority === 'CRITICAL') return base * 1.5;
    if (link.priority === 'HIGH') return base * 1.2;
    return base;
  }, []);

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const getLinkParticles = useCallback((link: any) => {
    const base = LINK_STYLES[link.type]?.particles || 0;
    if (link.priority === 'CRITICAL') return base + 2;
    return base;
  }, []);

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const getLinkParticleColor = useCallback((link: any) => {
    return LINK_STYLES[link.type]?.particleColor || '#475569';
  }, []);

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const getLinkParticleSpeed = useCallback((link: any) => {
    return LINK_STYLES[link.type]?.speed || 0.004;
  }, []);

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const FG = ForceGraph3DComponent as any;

  if (!data.nodes.length) return null;

  return (
    <FG
      ref={fgRef}
      graphData={data}
      width={width}
      height={height}
      backgroundColor="#050510"
      nodeThreeObject={createNodeObject}
      nodeThreeObjectExtend={false}
      onNodeClick={handleNodeClick}
      onLinkClick={handleLinkClick}
      linkColor={getLinkColor}
      linkWidth={getLinkWidth}
      linkDirectionalParticles={getLinkParticles}
      linkDirectionalParticleWidth={1.5}
      linkDirectionalParticleSpeed={getLinkParticleSpeed}
      linkDirectionalParticleColor={getLinkParticleColor}
      linkCurvature={0.15}
      linkOpacity={0.8}
      d3AlphaDecay={0.012}
      d3VelocityDecay={0.25}
      warmupTicks={100}
      cooldownTime={5000}
      onEngineStop={() => {
        if (hasZoomedRef.current) return;
        const fg = fgRef.current;
        if (fg?.zoomToFit) {
          fg.zoomToFit(800, 60);
          hasZoomedRef.current = true;
        }
      }}
    />
  );
}

function lightenHex(hex: string, amount: number): string {
  const c = parseInt(hex.replace('#', ''), 16);
  const r = Math.min(255, ((c >> 16) & 0xff) + amount);
  const g = Math.min(255, ((c >> 8) & 0xff) + amount);
  const b = Math.min(255, (c & 0xff) + amount);
  return `#${((r << 16) | (g << 8) | b).toString(16).padStart(6, '0')}`;
}
