'use client';

import { useState, useRef, useEffect, useCallback, useMemo } from 'react';

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

interface SearchResult {
  type: 'node' | 'link' | 'answer';
  node?: MindraNode;
  link?: MindraLink;
  title: string;
  subtitle: string;
  detail?: string;
  badge?: { label: string; className: string };
}

interface Props {
  nodes: MindraNode[];
  links: MindraLink[];
  onSelectNode: (node: MindraNode) => void;
}

const TYPE_BADGES: Record<string, { label: string; className: string }> = {
  orchestrator: { label: 'ORCHESTRATOR', className: 'bg-emerald-900/60 text-emerald-300' },
  agent: { label: 'AGENT', className: 'bg-cyan-900/60 text-cyan-300' },
  department: { label: 'DEPARTMENT', className: 'bg-indigo-900/60 text-indigo-300' },
  workflow: { label: 'WORKFLOW', className: 'bg-fuchsia-900/60 text-fuchsia-300' },
  payment: { label: 'PAYMENT', className: 'bg-violet-900/60 text-violet-300' },
  wallet: { label: 'WALLET', className: 'bg-amber-900/60 text-amber-300' },
  platform: { label: 'PLATFORM', className: 'bg-orange-900/60 text-orange-300' },
  client: { label: 'CLIENT', className: 'bg-blue-900/60 text-blue-300' },
  output: { label: 'OUTPUT', className: 'bg-emerald-900/60 text-emerald-300' },
};

export default function MindraSearchBar({ nodes, links, onSelectNode }: Props) {
  const [query, setQuery] = useState('');
  const [focused, setFocused] = useState(false);
  const [selectedIdx, setSelectedIdx] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);

  const nodeMap = useMemo(() => {
    const m = new Map<string, MindraNode>();
    for (const n of nodes) m.set(n.id, n);
    return m;
  }, [nodes]);

  const linkSourceId = (l: MindraLink) => typeof l.source === 'object' ? (l.source as unknown as { id: string }).id : l.source;
  const linkTargetId = (l: MindraLink) => typeof l.target === 'object' ? (l.target as unknown as { id: string }).id : l.target;

  const results = useMemo((): SearchResult[] => {
    const q = query.trim().toLowerCase();
    if (q.length < 2) return [];

    const out: SearchResult[] = [];

    // ─── "what agents" / "which agents" / "list agents" / "show agents" ───
    if (q.match(/(?:what\s+agents?|which\s+agents?|list\s+agents?|show\s+(?:me\s+)?agents?|all\s+agents?)/)) {
      const agents = nodes.filter(n => n.type === 'agent');
      for (const n of agents) {
        out.push({
          type: 'node', node: n, title: n.name, subtitle: n.description,
          detail: `${n.credits || 1} credit${(n.credits || 1) > 1 ? 's' : ''}/call · ${n.department || 'unknown'} dept`,
          badge: TYPE_BADGES.agent,
        });
      }
      return out;
    }

    // ─── "connections" / "how do they connect" / "agent to agent" / "feeds" ───
    if (q.match(/(?:connect|how\s+(?:do\s+)?(?:they|agents?)\s+connect|agent\s+to\s+agent|feeds?|between\s+agents?)/)) {
      const feedLinks = links.filter(l => l.type === 'feeds');
      for (const link of feedLinks) {
        const src = nodeMap.get(linkSourceId(link));
        const tgt = nodeMap.get(linkTargetId(link));
        out.push({
          type: 'link', link, title: `${src?.name || '?'} → ${tgt?.name || '?'}`,
          subtitle: link.reason, badge: { label: 'FEEDS', className: 'bg-cyan-900/60 text-cyan-300' },
        });
      }
      return out;
    }

    // ─── "how does orchestration work" / "how orchestrator" / "routing" ───
    if (q.match(/(?:how\s+(?:does\s+)?orchestrat|orchestrator|routing|how\s+(?:do\s+)?tasks?\s+(?:get\s+)?route)/)) {
      const orch = nodes.find(n => n.type === 'orchestrator');
      if (orch) {
        out.push({ type: 'node', node: orch, title: orch.name, subtitle: orch.description, badge: TYPE_BADGES.orchestrator });
      }
      // Show routing links
      const routeLinks = links.filter(l => l.type === 'routes_to');
      for (const link of routeLinks) {
        const tgt = nodeMap.get(linkTargetId(link));
        out.push({
          type: 'link', link, title: `Dispatches → ${tgt?.name || '?'}`,
          subtitle: link.reason, badge: { label: 'DISPATCH', className: 'bg-emerald-900/60 text-emerald-300' },
        });
      }
      return out;
    }

    // ─── "payments" / "x402" / "credits" / "how much" / "cost" ───
    if (q.match(/(?:payment|x402|credit|how\s+much|cost|price|billing|settlement|burn)/)) {
      const paymentNodes = nodes.filter(n => n.type === 'payment' || n.type === 'wallet');
      for (const n of paymentNodes) {
        out.push({ type: 'node', node: n, title: n.name, subtitle: n.description, badge: TYPE_BADGES[n.type] || TYPE_BADGES.payment });
      }
      // Show agent credit costs
      const agents = nodes.filter(n => n.type === 'agent');
      for (const n of agents) {
        out.push({
          type: 'node', node: n, title: n.name,
          subtitle: `${n.credits || 1} credit${(n.credits || 1) > 1 ? 's' : ''} per call`,
          detail: n.description,
          badge: { label: `${n.credits || 1} CR`, className: 'bg-amber-900/60 text-amber-300' },
        });
      }
      // Payment flow links
      const payLinks = links.filter(l => l.type === 'payment' || l.type === 'payment_init' || l.type === 'settlement' || l.type === 'x402_auth');
      for (const link of payLinks.slice(0, 3)) {
        const src = nodeMap.get(linkSourceId(link));
        const tgt = nodeMap.get(linkTargetId(link));
        out.push({
          type: 'link', link, title: `${src?.name || '?'} → ${tgt?.name || '?'}`,
          subtitle: link.reason, badge: { label: 'PAYMENT', className: 'bg-violet-900/60 text-violet-300' },
        });
      }
      return out.slice(0, 10);
    }

    // ─── "research" / "researcher" / "social monitor" (specific agents/depts) ───
    if (q.match(/(?:research(?:er)?(?:\s+dept)?)/)) {
      const matches = nodes.filter(n =>
        n.name.toLowerCase().includes('research') || n.id.includes('research')
      );
      for (const n of matches) {
        out.push({
          type: 'node', node: n, title: n.name, subtitle: n.description,
          badge: TYPE_BADGES[n.type] || { label: n.type.toUpperCase(), className: 'bg-slate-700 text-slate-300' },
        });
      }
      return out;
    }

    // ─── "writer" / "qa" / "quality" / "nexus" / "researcher" (specific agents) ───
    const agentNameMatch = q.match(/(?:writer|qa|quality|nexus|researcher|checker|fact)/);
    if (agentNameMatch) {
      const term = agentNameMatch[0];
      const matches = nodes.filter(n => n.name.toLowerCase().includes(term) || n.description.toLowerCase().includes(term));
      if (matches.length > 0) {
        for (const n of matches) {
          out.push({
            type: 'node', node: n, title: n.name, subtitle: n.description,
            detail: n.capabilities ? n.capabilities.join(', ') : undefined,
            badge: TYPE_BADGES[n.type] || { label: n.type.toUpperCase(), className: 'bg-slate-700 text-slate-300' },
          });
        }
        return out;
      }
    }

    // ─── "capabilities" / "what can X do" ───
    if (q.match(/(?:capabilit|what\s+can|skills?|abilities?)/)) {
      const agents = nodes.filter(n => n.type === 'agent' && n.capabilities && n.capabilities.length > 0);
      for (const n of agents) {
        out.push({
          type: 'node', node: n, title: n.name,
          subtitle: n.capabilities?.join(', ') || n.description,
          badge: TYPE_BADGES.agent,
        });
      }
      return out;
    }

    // ─── "what is X" / "explain X" / "tell me about X" ───
    const whatIsMatch = q.match(/(?:what\s+is|explain|tell\s+me\s+about|describe|show\s+me)\s+(.+)/);
    if (whatIsMatch) {
      const target = whatIsMatch[1].trim();
      const matched = nodes.filter(n =>
        n.name.toLowerCase().includes(target) ||
        n.description.toLowerCase().includes(target)
      );
      for (const n of matched) {
        out.push({
          type: 'node', node: n, title: n.name, subtitle: n.description,
          badge: TYPE_BADGES[n.type] || { label: n.type.toUpperCase(), className: 'bg-slate-700 text-slate-300' },
        });
      }
      if (out.length > 0) return out.slice(0, 8);
    }

    // ─── Fuzzy search fallback ───
    const terms = q.split(/\s+/).filter(Boolean);
    const scored: { result: SearchResult; score: number }[] = [];

    for (const n of nodes) {
      let score = 0;
      const hay = [n.name, n.description, n.category, n.type, n.department || '', ...(n.capabilities || []), ...(n.steps || [])].join(' ').toLowerCase();
      for (const t of terms) {
        if (n.name.toLowerCase().includes(t)) score += 10;
        if (n.type.toLowerCase().includes(t)) score += 5;
        if (hay.includes(t)) score += 2;
      }
      if (score > 0) {
        scored.push({
          result: {
            type: 'node', node: n, title: n.name, subtitle: n.description,
            detail: n.capabilities ? n.capabilities.join(', ') : n.steps ? n.steps.join(' → ') : undefined,
            badge: TYPE_BADGES[n.type] || { label: n.type.toUpperCase(), className: 'bg-slate-700 text-slate-300' },
          },
          score: score + (n.isCore ? 15 : 0) + (n.type === 'agent' ? 5 : 0),
        });
      }
    }

    scored.sort((a, b) => b.score - a.score);
    return scored.slice(0, 8).map(s => s.result);
  }, [query, nodes, links, nodeMap]);

  useEffect(() => { setSelectedIdx(0); }, [results.length]);

  const handleKeyDown = useCallback((e: React.KeyboardEvent) => {
    if (e.key === 'ArrowDown') { e.preventDefault(); setSelectedIdx(i => Math.min(i + 1, results.length - 1)); }
    else if (e.key === 'ArrowUp') { e.preventDefault(); setSelectedIdx(i => Math.max(i - 1, 0)); }
    else if (e.key === 'Enter' && results[selectedIdx]) { e.preventDefault(); selectResult(results[selectedIdx]); }
    else if (e.key === 'Escape') { setQuery(''); inputRef.current?.blur(); }
  }, [results, selectedIdx]);

  const selectResult = useCallback((r: SearchResult) => {
    if (r.node) onSelectNode(r.node);
    setQuery('');
    inputRef.current?.blur();
  }, [onSelectNode]);

  useEffect(() => {
    function handleGlobalKey(e: KeyboardEvent) {
      if (e.key === '/' && !e.ctrlKey && !e.metaKey && document.activeElement?.tagName !== 'INPUT') {
        e.preventDefault();
        inputRef.current?.focus();
      }
    }
    window.addEventListener('keydown', handleGlobalKey);
    return () => window.removeEventListener('keydown', handleGlobalKey);
  }, []);

  const showResults = focused && query.length >= 2 && results.length > 0;
  const showEmpty = focused && query.length >= 2 && results.length === 0;

  return (
    <div className="relative w-[420px]">
      <div className="relative">
        <svg className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
        </svg>
        <input
          ref={inputRef}
          type="text"
          value={query}
          onChange={e => setQuery(e.target.value)}
          onFocus={() => setFocused(true)}
          onBlur={() => setTimeout(() => setFocused(false), 200)}
          onKeyDown={handleKeyDown}
          placeholder='Ask "what agents?" or "how payments work"...'
          className="w-full h-9 pl-10 pr-10 rounded-lg glass-panel text-sm text-slate-200 placeholder:text-slate-600 outline-none focus:border-violet-500/50 transition-colors"
        />
        {query && (
          <button onClick={() => setQuery('')} className="absolute right-2 top-1/2 -translate-y-1/2 text-slate-500 hover:text-slate-300 p-1">
            <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        )}
        {!query && (
          <kbd className="absolute right-3 top-1/2 -translate-y-1/2 text-[10px] text-slate-600 bg-slate-800/60 px-1.5 py-0.5 rounded border border-slate-700/30 font-mono">/</kbd>
        )}
      </div>

      {showResults && (
        <div className="absolute top-full mt-1 w-full glass-panel rounded-xl overflow-hidden shadow-2xl z-50 max-h-[420px] overflow-y-auto">
          {query.length < 4 && (
            <div className="px-3 py-2 border-b border-slate-700/30">
              <p className="text-[10px] uppercase tracking-widest text-slate-600 font-bold">Try asking</p>
              <div className="flex flex-wrap gap-1 mt-1">
                {['what agents', 'connections', 'payments', 'capabilities', 'orchestrator', 'researcher'].map(s => (
                  <button key={s} onClick={() => setQuery(s)} className="text-[10px] px-2 py-0.5 rounded-full bg-slate-800 text-slate-400 hover:text-slate-200 hover:bg-slate-700 transition-colors">{s}</button>
                ))}
              </div>
            </div>
          )}
          {results.map((r, i) => (
            <button
              key={i}
              className={`w-full text-left px-3 py-2.5 transition-colors border-b border-slate-800/50 last:border-0 ${i === selectedIdx ? 'bg-slate-800/60' : 'hover:bg-slate-800/30'}`}
              onMouseEnter={() => setSelectedIdx(i)}
              onClick={() => selectResult(r)}
            >
              <div className="flex items-center gap-2 mb-0.5">
                {r.badge && <span className={`text-[9px] px-1.5 py-0 rounded font-bold shrink-0 ${r.badge.className}`}>{r.badge.label}</span>}
                <span className="text-sm font-medium text-slate-200 truncate">{r.title}</span>
              </div>
              <p className="text-xs text-slate-400 line-clamp-2 leading-relaxed">{r.subtitle}</p>
              {r.detail && <p className="text-[11px] text-violet-400/70 mt-0.5 line-clamp-1 italic">{'\u2192'} {r.detail}</p>}
            </button>
          ))}
        </div>
      )}

      {showEmpty && (
        <div className="absolute top-full mt-1 w-full glass-panel rounded-xl p-4 shadow-2xl z-50">
          <p className="text-sm text-slate-500">No results for &ldquo;{query}&rdquo;</p>
          <p className="text-xs text-slate-600 mt-1">Try: &ldquo;what agents&rdquo;, &ldquo;connections&rdquo;, &ldquo;payments&rdquo;, &ldquo;capabilities&rdquo;, &ldquo;writer&rdquo;, or &ldquo;orchestrator&rdquo;</p>
        </div>
      )}
    </div>
  );
}
