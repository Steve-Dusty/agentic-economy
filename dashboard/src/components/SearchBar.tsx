'use client';

import { useState, useRef, useEffect, useCallback, useMemo } from 'react';
import type { AgentNode, AgentLink } from '@/types/graph';

interface SearchResult {
  type: 'node' | 'link' | 'answer';
  node?: AgentNode;
  link?: AgentLink;
  title: string;
  subtitle: string;
  reason?: string;
  badge?: { label: string; className: string };
  sourceNode?: AgentNode;
  targetNode?: AgentNode;
}

interface Props {
  nodes: AgentNode[];
  links: AgentLink[];
  onSelectNode: (node: AgentNode) => void;
  onSelectLink: (link: AgentLink) => void;
}

export default function SearchBar({ nodes, links, onSelectNode, onSelectLink }: Props) {
  const [query, setQuery] = useState('');
  const [focused, setFocused] = useState(false);
  const [selectedIdx, setSelectedIdx] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);
  const resultsRef = useRef<HTMLDivElement>(null);

  // Resolve node ID → node
  const nodeMap = useMemo(() => {
    const m = new Map<string, AgentNode>();
    for (const n of nodes) m.set(n.id, n);
    return m;
  }, [nodes]);

  const resolveId = useCallback((id: string): AgentNode | undefined => {
    // Direct match
    if (nodeMap.has(id)) return nodeMap.get(id);
    // Partial match on source/target strings (which might be objects after graph resolves)
    for (const n of nodes) {
      if (n.id === id) return n;
    }
    return undefined;
  }, [nodeMap, nodes]);

  const linkSourceId = (l: AgentLink) => typeof l.source === 'object' ? (l.source as unknown as { id: string }).id : l.source;
  const linkTargetId = (l: AgentLink) => typeof l.target === 'object' ? (l.target as unknown as { id: string }).id : l.target;

  // ─── Search engine ───
  const results = useMemo((): SearchResult[] => {
    const q = query.trim().toLowerCase();
    if (q.length < 2) return [];

    const out: SearchResult[] = [];
    const ourNodes = nodes.filter(n => n.isOurs);
    const isOurNode = (id: string) => {
      const n = resolveId(id);
      return n?.isOurs;
    };

    // ─── Natural language patterns ───

    // "why did we buy X" / "why do we buy from X" / "why we buy X"
    const whyWeBuyMatch = q.match(/why\s+(?:did|do)?\s*we\s+buy\s+(?:from\s+)?(.+)/);
    if (whyWeBuyMatch) {
      const target = whyWeBuyMatch[1].trim();
      const supplyLinks = links.filter(l => {
        if (l.type !== 'supply') return false;
        const targetNode = resolveId(linkTargetId(l));
        if (!targetNode?.isOurs) return false;
        const sourceNode = resolveId(linkSourceId(l));
        return sourceNode?.name.toLowerCase().includes(target) ||
               sourceNode?.team.toLowerCase().includes(target);
      });
      for (const link of supplyLinks) {
        const src = resolveId(linkSourceId(link));
        const tgt = resolveId(linkTargetId(link));
        if (src) {
          out.push({
            type: 'link',
            link,
            title: `Why we buy from ${src.name}`,
            subtitle: link.reason,
            reason: link.strategicValue,
            badge: { label: link.priority || 'SUPPLY', className: priorityClass(link.priority) },
            sourceNode: src,
            targetNode: tgt,
          });
        }
      }
      if (out.length > 0) return out.slice(0, 8);
    }

    // "why does X buy from us" / "why X buys" / "who buys from us"
    const whyBuyFromUsMatch = q.match(/why\s+(?:does|did)?\s*(.+?)\s+buy\s+(?:from\s+us|our)/);
    const whoBuysMatch = q.match(/who\s+buys?\s+(?:from\s+us|our)/);
    if (whyBuyFromUsMatch || whoBuysMatch) {
      const target = whyBuyFromUsMatch ? whyBuyFromUsMatch[1].trim() : '';
      const custLinks = links.filter(l => {
        if (l.type !== 'customer') return false;
        const sourceNode = resolveId(linkSourceId(l));
        if (!sourceNode?.isOurs) return false;
        if (!target) return true;
        const targetNode = resolveId(linkTargetId(l));
        return targetNode?.name.toLowerCase().includes(target) ||
               targetNode?.team.toLowerCase().includes(target);
      });
      for (const link of custLinks) {
        const src = resolveId(linkSourceId(link));
        const tgt = resolveId(linkTargetId(link));
        if (tgt) {
          out.push({
            type: 'link',
            link,
            title: `${tgt.name} buys from us`,
            subtitle: link.reason,
            reason: link.strategicValue,
            badge: { label: link.priority || 'CUSTOMER', className: priorityClass(link.priority) },
            sourceNode: src,
            targetNode: tgt,
          });
        }
      }
      if (out.length > 0) return out.slice(0, 8);
    }

    // "what do we sell" / "our product" / "our services"
    if (q.match(/(?:what\s+(?:do\s+)?we\s+sell|our\s+product|our\s+service|what\s+(?:are\s+)?we\s+selling)/)) {
      for (const n of ourNodes.filter(n => n.type === 'seller')) {
        out.push({
          type: 'node',
          node: n,
          title: n.name,
          subtitle: n.strategicValue || n.description || 'Our seller agent',
          badge: { label: 'OUR PRODUCT', className: 'bg-emerald-900/60 text-emerald-300' },
        });
      }
      return out;
    }

    // "who supplies" / "our suppliers" / "supply chain"
    if (q.match(/(?:who\s+supplies|our\s+supplier|supply\s+chain|what\s+(?:do\s+)?we\s+buy|who\s+(?:do\s+)?we\s+buy\s+from)/)) {
      const supplyLinks = links.filter(l => {
        if (l.type !== 'supply') return false;
        const tgt = resolveId(linkTargetId(l));
        return tgt?.isOurs;
      });
      for (const link of supplyLinks) {
        const src = resolveId(linkSourceId(link));
        if (src) {
          out.push({
            type: 'link',
            link,
            title: src.name,
            subtitle: link.reason,
            reason: link.strategicValue,
            badge: { label: link.priority || 'SUPPLIER', className: priorityClass(link.priority) },
            sourceNode: src,
            targetNode: resolveId(linkTargetId(link)),
          });
        }
      }
      return out.slice(0, 10);
    }

    // "our customers" / "revenue" / "who pays us"
    if (q.match(/(?:our\s+customer|revenue|who\s+pays|who\s+bought|our\s+buyer)/)) {
      const custLinks = links.filter(l => {
        if (l.type !== 'customer') return false;
        const src = resolveId(linkSourceId(l));
        return src?.isOurs;
      });
      for (const link of custLinks) {
        const tgt = resolveId(linkTargetId(link));
        if (tgt) {
          out.push({
            type: 'link',
            link,
            title: tgt.name,
            subtitle: link.reason,
            reason: link.strategicValue,
            badge: { label: link.priority || 'CUSTOMER', className: priorityClass(link.priority) },
            sourceNode: resolveId(linkSourceId(link)),
            targetNode: tgt,
          });
        }
      }
      return out.slice(0, 10);
    }

    // "critical" / "high priority" — filter by priority
    if (q.match(/^(critical|high\s+priority)$/)) {
      const prio = q.includes('critical') ? 'CRITICAL' : 'HIGH';
      const prioLinks = links.filter(l => l.priority === prio && (l.type === 'supply' || l.type === 'customer'));
      for (const link of prioLinks) {
        const src = resolveId(linkSourceId(link));
        const tgt = resolveId(linkTargetId(link));
        out.push({
          type: 'link',
          link,
          title: `${src?.name || '?'} \u2192 ${tgt?.name || '?'}`,
          subtitle: link.reason,
          badge: { label: `${prio} ${link.type.toUpperCase()}`, className: priorityClass(prio) },
          sourceNode: src,
          targetNode: tgt,
        });
      }
      return out.slice(0, 10);
    }

    // ─── Plan ID search ───
    if (q.length > 10 && /^\d+$/.test(q.replace(/\.\.\./g, ''))) {
      for (const n of nodes) {
        if (n.planIds?.some(pid => pid.includes(q.replace(/\.\.\./g, '')))) {
          out.push({
            type: 'node',
            node: n,
            title: n.name,
            subtitle: `Plan match: ${n.planIds?.find(p => p.includes(q.replace(/\.\.\./g, '')))?.slice(0, 24)}...`,
            badge: { label: n.type.toUpperCase(), className: n.isOurs ? 'bg-emerald-900/60 text-emerald-300' : 'bg-slate-700 text-slate-300' },
          });
        }
      }
      if (out.length > 0) return out;
    }

    // ─── Wallet / hash search ───
    if (q.startsWith('0x') && q.length > 6) {
      for (const n of nodes) {
        if (n.wallet?.toLowerCase().includes(q)) {
          out.push({
            type: 'node',
            node: n,
            title: n.name,
            subtitle: `Wallet: ${n.wallet?.slice(0, 20)}...`,
            badge: { label: n.type.toUpperCase(), className: n.isOurs ? 'bg-emerald-900/60 text-emerald-300' : 'bg-slate-700 text-slate-300' },
          });
        }
      }
      if (out.length > 0) return out;
    }

    // ─── Fuzzy name / team / description / keyword search ───
    const terms = q.split(/\s+/).filter(Boolean);
    const scored: { result: SearchResult; score: number }[] = [];

    for (const n of nodes) {
      if (n.type === 'team' && n.agentCount === 0) continue;
      let score = 0;
      const hay = [n.name, n.team, n.description || '', n.category || '', ...(n.keywords || []), n.servicesSold || '']
        .join(' ').toLowerCase();

      for (const t of terms) {
        if (n.name.toLowerCase().includes(t)) score += 10;
        if (n.team.toLowerCase().includes(t)) score += 5;
        if (hay.includes(t)) score += 2;
      }

      if (score > 0) {
        // Also find links involving this node to show WHY context
        const relatedLinks = links.filter(l =>
          (linkSourceId(l) === n.id || linkTargetId(l) === n.id) &&
          l.type !== 'owns' && l.type !== 'peer_trade'
        );

        const bestLink = relatedLinks.sort((a, b) => {
          const pa = priorityRank(a.priority);
          const pb = priorityRank(b.priority);
          return pa - pb;
        })[0];

        let subtitle = n.description || n.team;
        let reason: string | undefined;
        if (bestLink) {
          subtitle = bestLink.reason;
          reason = bestLink.strategicValue;
        }

        const badge = n.isOurs
          ? { label: n.role === 'our_seller' ? 'OUR PRODUCT' : 'OURS', className: 'bg-emerald-900/60 text-emerald-300' }
          : n.role === 'supplier'
            ? { label: 'SUPPLIER', className: 'bg-cyan-900/60 text-cyan-300' }
            : n.role === 'customer'
              ? { label: 'CUSTOMER', className: 'bg-amber-900/60 text-amber-300' }
              : { label: n.type.toUpperCase(), className: 'bg-slate-700 text-slate-300' };

        scored.push({
          result: { type: 'node', node: n, title: n.name, subtitle, reason, badge },
          score: score + (n.isOurs ? 20 : 0) + (n.role === 'supplier' ? 5 : 0) + (n.role === 'customer' ? 5 : 0),
        });
      }
    }

    scored.sort((a, b) => b.score - a.score);
    return scored.slice(0, 8).map(s => s.result);

  }, [query, nodes, links, resolveId]);

  // Reset index on new results
  useEffect(() => { setSelectedIdx(0); }, [results.length]);

  // Keyboard nav
  const handleKeyDown = useCallback((e: React.KeyboardEvent) => {
    if (e.key === 'ArrowDown') {
      e.preventDefault();
      setSelectedIdx(i => Math.min(i + 1, results.length - 1));
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      setSelectedIdx(i => Math.max(i - 1, 0));
    } else if (e.key === 'Enter' && results[selectedIdx]) {
      e.preventDefault();
      selectResult(results[selectedIdx]);
    } else if (e.key === 'Escape') {
      setQuery('');
      inputRef.current?.blur();
    }
  }, [results, selectedIdx]);

  const selectResult = useCallback((r: SearchResult) => {
    if (r.type === 'link' && r.link) {
      // Navigate to the most relevant node for context
      const targetNode = r.targetNode || r.sourceNode;
      if (targetNode) onSelectNode(targetNode);
      onSelectLink(r.link);
    } else if (r.node) {
      onSelectNode(r.node);
    }
    setQuery('');
    inputRef.current?.blur();
  }, [onSelectNode, onSelectLink]);

  // Global shortcut: / to focus
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
          placeholder='Search agents, plans, or ask "why did we buy from..."'
          className="w-full h-9 pl-10 pr-10 rounded-lg glass-panel text-sm text-slate-200 placeholder:text-slate-600 outline-none focus:border-emerald-500/50 transition-colors"
        />
        {query && (
          <button
            onClick={() => setQuery('')}
            className="absolute right-2 top-1/2 -translate-y-1/2 text-slate-500 hover:text-slate-300 p-1"
          >
            <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        )}
        {!query && (
          <kbd className="absolute right-3 top-1/2 -translate-y-1/2 text-[10px] text-slate-600 bg-slate-800/60 px-1.5 py-0.5 rounded border border-slate-700/30 font-mono">
            /
          </kbd>
        )}
      </div>

      {/* Results dropdown */}
      {showResults && (
        <div ref={resultsRef} className="absolute top-full mt-1 w-full glass-panel rounded-xl overflow-hidden shadow-2xl z-50 max-h-[420px] overflow-y-auto">
          {/* Quick suggestions */}
          {query.length < 4 && (
            <div className="px-3 py-2 border-b border-slate-700/30">
              <p className="text-[10px] uppercase tracking-widest text-slate-600 font-bold">Try asking</p>
              <div className="flex flex-wrap gap-1 mt-1">
                {['why did we buy', 'who buys from us', 'our suppliers', 'critical', 'supply chain'].map(s => (
                  <button
                    key={s}
                    onClick={() => setQuery(s)}
                    className="text-[10px] px-2 py-0.5 rounded-full bg-slate-800 text-slate-400 hover:text-slate-200 hover:bg-slate-700 transition-colors"
                  >
                    {s}
                  </button>
                ))}
              </div>
            </div>
          )}

          {results.map((r, i) => (
            <button
              key={i}
              className={`w-full text-left px-3 py-2.5 transition-colors border-b border-slate-800/50 last:border-0 ${
                i === selectedIdx ? 'bg-slate-800/60' : 'hover:bg-slate-800/30'
              }`}
              onMouseEnter={() => setSelectedIdx(i)}
              onClick={() => selectResult(r)}
            >
              <div className="flex items-center gap-2 mb-0.5">
                {r.badge && (
                  <span className={`text-[9px] px-1.5 py-0 rounded font-bold shrink-0 ${r.badge.className}`}>
                    {r.badge.label}
                  </span>
                )}
                <span className="text-sm font-medium text-slate-200 truncate">{r.title}</span>
              </div>
              <p className="text-xs text-slate-400 line-clamp-2 leading-relaxed">{r.subtitle}</p>
              {r.reason && (
                <p className="text-[11px] text-cyan-400/70 mt-0.5 line-clamp-1 italic">{'\u2192'} {r.reason}</p>
              )}
            </button>
          ))}
        </div>
      )}

      {showEmpty && (
        <div className="absolute top-full mt-1 w-full glass-panel rounded-xl p-4 shadow-2xl z-50">
          <p className="text-sm text-slate-500">No results for &ldquo;{query}&rdquo;</p>
          <p className="text-xs text-slate-600 mt-1">
            Try: agent names, team names, plan IDs, wallet addresses, or questions like &ldquo;why did we buy from X&rdquo;
          </p>
        </div>
      )}
    </div>
  );
}

function priorityClass(p?: string): string {
  if (p === 'CRITICAL') return 'bg-red-900/50 text-red-300';
  if (p === 'HIGH') return 'bg-amber-900/50 text-amber-300';
  if (p === 'MEDIUM') return 'bg-blue-900/50 text-blue-300';
  return 'bg-slate-700 text-slate-400';
}

function priorityRank(p?: string): number {
  if (p === 'CRITICAL') return 0;
  if (p === 'HIGH') return 1;
  if (p === 'MEDIUM') return 2;
  return 3;
}
