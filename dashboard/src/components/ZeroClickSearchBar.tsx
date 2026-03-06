'use client';

import { useState, useRef, useEffect, useCallback, useMemo } from 'react';

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

interface SearchResult {
  type: 'node' | 'link' | 'answer';
  node?: ZCNode;
  link?: ZCLink;
  title: string;
  subtitle: string;
  detail?: string;
  badge?: { label: string; className: string };
}

interface Props {
  nodes: ZCNode[];
  links: ZCLink[];
  onSelectNode: (node: ZCNode) => void;
}

const CATEGORY_BADGES: Record<string, { label: string; className: string }> = {
  core: { label: 'CORE', className: 'bg-emerald-900/60 text-emerald-300' },
  signal: { label: 'SIGNAL', className: 'bg-cyan-900/60 text-cyan-300' },
  revenue: { label: 'REVENUE', className: 'bg-amber-900/60 text-amber-300' },
  endpoint: { label: 'API', className: 'bg-indigo-900/60 text-indigo-300' },
  advertisers: { label: 'ADVERTISER', className: 'bg-yellow-900/60 text-yellow-300' },
  users: { label: 'USERS', className: 'bg-blue-900/60 text-blue-300' },
  ai: { label: 'AI', className: 'bg-purple-900/60 text-purple-300' },
  our_product: { label: 'OURS', className: 'bg-emerald-900/60 text-emerald-300' },
  infrastructure: { label: 'INFRA', className: 'bg-slate-600 text-slate-300' },
};

export default function ZeroClickSearchBar({ nodes, links, onSelectNode }: Props) {
  const [query, setQuery] = useState('');
  const [focused, setFocused] = useState(false);
  const [selectedIdx, setSelectedIdx] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);

  const nodeMap = useMemo(() => {
    const m = new Map<string, ZCNode>();
    for (const n of nodes) m.set(n.id, n);
    return m;
  }, [nodes]);

  const linkSourceId = (l: ZCLink) => typeof l.source === 'object' ? (l.source as unknown as { id: string }).id : l.source;
  const linkTargetId = (l: ZCLink) => typeof l.target === 'object' ? (l.target as unknown as { id: string }).id : l.target;

  const results = useMemo((): SearchResult[] => {
    const q = query.trim().toLowerCase();
    if (q.length < 2) return [];

    const out: SearchResult[] = [];

    // ─── "how does revenue work" / "revenue flow" / "how we earn" / "monetization" ───
    if (q.match(/(?:revenue|how\s+(?:do\s+)?(?:we|ads?)\s+(?:earn|work|make\s+money)|monetiz|earning|payout|publisher\s+share)/)) {
      const revNodes = nodes.filter(n => n.category === 'revenue' || n.id === 'revenue-pool' || n.id === 'publisher-share');
      for (const n of revNodes) {
        out.push({
          type: 'node', node: n, title: n.name, subtitle: n.description,
          badge: CATEGORY_BADGES[n.category] || CATEGORY_BADGES.revenue,
        });
      }
      // Also show revenue links
      const revLinks = links.filter(l => l.type === 'revenue' || l.type === 'payout' || l.type === 'revenue_model');
      for (const link of revLinks.slice(0, 4)) {
        const src = nodeMap.get(linkSourceId(link));
        const tgt = nodeMap.get(linkTargetId(link));
        out.push({
          type: 'link', link, title: `${src?.name || '?'} → ${tgt?.name || '?'}`,
          subtitle: link.reason, badge: { label: 'FLOW', className: 'bg-emerald-900/60 text-emerald-300' },
        });
      }
      if (out.length > 0) return out.slice(0, 8);
    }

    // ─── "signals" / "what signals" / "signal categories" / "intent" ───
    if (q.match(/(?:signal|intent|what\s+(?:are\s+)?(?:the\s+)?signals?|signal\s+categor|types?\s+of\s+signal)/)) {
      const sigNodes = nodes.filter(n => n.type === 'signal');
      for (const n of sigNodes) {
        out.push({
          type: 'node', node: n, title: n.name, subtitle: n.description,
          detail: n.monetizationWeight ? `Monetization: ${'★'.repeat(n.monetizationWeight)}${'☆'.repeat(5 - n.monetizationWeight)}` : undefined,
          badge: CATEGORY_BADGES.signal,
        });
      }
      return out;
    }

    // ─── "CPC" / "CPM" / "CPA" / "pricing" / "cost per" ───
    if (q.match(/(?:cpc|cpm|cpa|cost\s+per|pricing|ad\s+(?:pricing|rates?|cost))/)) {
      const revTiers = nodes.filter(n => n.type === 'revenue_tier');
      for (const n of revTiers) {
        out.push({
          type: 'node', node: n, title: n.name, subtitle: n.description,
          detail: n.amount || undefined,
          badge: CATEGORY_BADGES.revenue,
        });
      }
      return out;
    }

    // ─── "APIs" / "endpoints" / "what APIs" ───
    if (q.match(/(?:api|endpoint|what\s+api|zeroclick\s+api|mcp|offers\s+api|signals?\s+api|impression)/)) {
      const apiNodes = nodes.filter(n => n.type === 'api');
      for (const n of apiNodes) {
        out.push({
          type: 'node', node: n, title: n.name, subtitle: n.description,
          detail: n.url || undefined,
          badge: CATEGORY_BADGES.endpoint,
        });
      }
      return out;
    }

    // ─── "how ads work" / "ad flow" / "offer matching" / "how offers" ───
    if (q.match(/(?:how\s+(?:do\s+)?ads?\s+work|ad\s+flow|offer\s+match|how\s+(?:do\s+)?offers?\s+work|matching\s+engine)/)) {
      const flowOrder = ['user-session', 'signal-extractor', 'mcp_server', 'zc-engine', 'offers_api', 'impressions_api', 'revenue-pool'];
      for (const id of flowOrder) {
        const n = nodeMap.get(id);
        if (n) {
          out.push({
            type: 'node', node: n, title: n.name, subtitle: n.description,
            badge: CATEGORY_BADGES[n.category] || { label: n.type.toUpperCase(), className: 'bg-slate-700 text-slate-300' },
          });
        }
      }
      return out;
    }

    // ─── "our integration" / "how we integrate" / "nvm terminal" ───
    if (q.match(/(?:our\s+integrat|how\s+(?:do\s+)?we\s+integrat|nvm\s+terminal|our\s+product|our\s+app)/)) {
      const ourNode = nodes.find(n => n.isOurs);
      if (ourNode) {
        out.push({
          type: 'node', node: ourNode, title: ourNode.name, subtitle: ourNode.description,
          badge: CATEGORY_BADGES.our_product,
        });
      }
      // Show links involving our integration
      const ourLinks = links.filter(l => linkSourceId(l) === 'our-integration' || linkTargetId(l) === 'our-integration');
      for (const link of ourLinks) {
        const src = nodeMap.get(linkSourceId(link));
        const tgt = nodeMap.get(linkTargetId(link));
        out.push({
          type: 'link', link, title: `${src?.name || '?'} → ${tgt?.name || '?'}`,
          subtitle: link.reason, badge: { label: 'INTEGRATION', className: 'bg-emerald-900/60 text-emerald-300' },
        });
      }
      return out;
    }

    // ─── "advertisers" / "brands" / "who advertises" ───
    if (q.match(/(?:advertiser|brand|who\s+advertise|ad\s+campaign|ad\s+supply)/)) {
      const advNode = nodes.find(n => n.category === 'advertisers');
      if (advNode) {
        out.push({
          type: 'node', node: advNode, title: advNode.name, subtitle: advNode.description,
          badge: CATEGORY_BADGES.advertisers,
        });
      }
      const advLinks = links.filter(l => linkSourceId(l) === 'advertiser-pool' || linkTargetId(l) === 'advertiser-pool');
      for (const link of advLinks) {
        const src = nodeMap.get(linkSourceId(link));
        const tgt = nodeMap.get(linkTargetId(link));
        out.push({
          type: 'link', link, title: `${src?.name || '?'} → ${tgt?.name || '?'}`,
          subtitle: link.reason, badge: { label: 'AD FLOW', className: 'bg-yellow-900/60 text-yellow-300' },
        });
      }
      return out;
    }

    // ─── "purchase intent" / specific signal search ───
    const signalMatch = q.match(/(?:purchase|interest|evaluation|problem|price|brand|context|business|recommendation)/);
    if (signalMatch) {
      const sigNodes = nodes.filter(n => n.type === 'signal' && n.name.toLowerCase().includes(signalMatch[0]));
      if (sigNodes.length > 0) {
        for (const n of sigNodes) {
          out.push({
            type: 'node', node: n, title: n.name, subtitle: n.description,
            detail: n.monetizationWeight ? `Monetization weight: ${n.monetizationWeight}/5` : undefined,
            badge: CATEGORY_BADGES.signal,
          });
        }
        return out;
      }
    }

    // ─── "what is X" / "explain X" ───
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
          badge: CATEGORY_BADGES[n.category] || { label: n.type.toUpperCase(), className: 'bg-slate-700 text-slate-300' },
        });
      }
      if (out.length > 0) return out.slice(0, 8);
    }

    // ─── "data flow" / "how data flows" ───
    if (q.match(/(?:data\s+flow|how\s+data|flow|pipeline|process)/)) {
      const flowLinks = links.filter(l => l.type === 'data_flow' || l.type === 'api_call');
      for (const link of flowLinks) {
        const src = nodeMap.get(linkSourceId(link));
        const tgt = nodeMap.get(linkTargetId(link));
        out.push({
          type: 'link', link, title: `${src?.name || '?'} → ${tgt?.name || '?'}`,
          subtitle: link.reason,
          badge: { label: 'DATA FLOW', className: 'bg-indigo-900/60 text-indigo-300' },
        });
      }
      return out.slice(0, 8);
    }

    // ─── Fuzzy name / description search ───
    const terms = q.split(/\s+/).filter(Boolean);
    const scored: { result: SearchResult; score: number }[] = [];

    for (const n of nodes) {
      let score = 0;
      const hay = [n.name, n.description, n.category, n.type, n.url || '', n.amount || ''].join(' ').toLowerCase();
      for (const t of terms) {
        if (n.name.toLowerCase().includes(t)) score += 10;
        if (n.category.toLowerCase().includes(t)) score += 5;
        if (hay.includes(t)) score += 2;
      }
      if (score > 0) {
        scored.push({
          result: {
            type: 'node', node: n, title: n.name, subtitle: n.description,
            badge: CATEGORY_BADGES[n.category] || { label: n.type.toUpperCase(), className: 'bg-slate-700 text-slate-300' },
          },
          score: score + (n.isCore ? 15 : 0) + (n.isOurs ? 12 : 0),
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
          placeholder='Ask "how does revenue work?" or search nodes...'
          className="w-full h-9 pl-10 pr-10 rounded-lg glass-panel text-sm text-slate-200 placeholder:text-slate-600 outline-none focus:border-cyan-500/50 transition-colors"
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
                {['how does revenue work', 'signal categories', 'CPC rates', 'ad flow', 'our integration', 'APIs'].map(s => (
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
              {r.detail && <p className="text-[11px] text-cyan-400/70 mt-0.5 line-clamp-1 italic">→ {r.detail}</p>}
            </button>
          ))}
        </div>
      )}

      {showEmpty && (
        <div className="absolute top-full mt-1 w-full glass-panel rounded-xl p-4 shadow-2xl z-50">
          <p className="text-sm text-slate-500">No results for &ldquo;{query}&rdquo;</p>
          <p className="text-xs text-slate-600 mt-1">Try: &ldquo;revenue flow&rdquo;, &ldquo;signal categories&rdquo;, &ldquo;CPC&rdquo;, &ldquo;how ads work&rdquo;, or node names</p>
        </div>
      )}
    </div>
  );
}
