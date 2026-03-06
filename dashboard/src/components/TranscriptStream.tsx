'use client';

import { useEffect, useRef, useState } from 'react';
import type { TranscriptEntry } from '@/types/graph';

interface Props {
  entries: TranscriptEntry[];
}

const LEVEL_STYLES: Record<string, { badge: string; color: string }> = {
  system:   { badge: 'bg-slate-700 text-slate-300',       color: 'text-slate-400' },
  strategy: { badge: 'bg-emerald-900/60 text-emerald-300', color: 'text-emerald-200' },
  supply:   { badge: 'bg-cyan-900/60 text-cyan-300',       color: 'text-cyan-200' },
  revenue:  { badge: 'bg-amber-900/60 text-amber-300',     color: 'text-amber-200' },
  decide:   { badge: 'bg-violet-900/60 text-violet-300',   color: 'text-violet-200' },
  evaluate: { badge: 'bg-sky-900/60 text-sky-300',         color: 'text-sky-200' },
  action:   { badge: 'bg-indigo-900/60 text-indigo-300',   color: 'text-indigo-200' },
  success:  { badge: 'bg-emerald-900/60 text-emerald-300', color: 'text-emerald-200' },
  error:    { badge: 'bg-red-900/60 text-red-300',         color: 'text-red-200' },
  info:     { badge: 'bg-slate-700/60 text-slate-400',     color: 'text-slate-400' },
};

const LEVEL_ICONS: Record<string, string> = {
  system:   '\u25CF',
  strategy: '\u2726',
  supply:   '\u2190',
  revenue:  '\u2192',
  decide:   '\u2605',
  evaluate: '\u25B6',
  action:   '\u26A1',
  success:  '\u2713',
  error:    '\u2717',
  info:     '\u25CB',
};

export default function TranscriptStream({ entries }: Props) {
  const scrollRef = useRef<HTMLDivElement>(null);
  const [autoScroll, setAutoScroll] = useState(true);
  const [collapsed, setCollapsed] = useState(false);

  useEffect(() => {
    if (autoScroll && scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [entries, autoScroll]);

  const formatTime = (iso: string) => {
    const d = new Date(iso);
    return d.toLocaleTimeString('en-US', { hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit' });
  };

  return (
    <div className={`glass-panel rounded-xl transition-all duration-300 ${collapsed ? 'w-80' : 'w-[720px]'}`}>
      <div
        className="flex items-center justify-between px-4 py-2.5 border-b border-slate-700/30 cursor-pointer select-none"
        onClick={() => setCollapsed(!collapsed)}
      >
        <div className="flex items-center gap-2">
          <span className="text-xs font-mono text-emerald-400 animate-pulse-glow">{'\u25CF'}</span>
          <h3 className="text-sm font-semibold text-slate-200">Agent Decision Transcript</h3>
          <span className="text-xs text-slate-500">({entries.length})</span>
        </div>
        <div className="flex items-center gap-2">
          {!collapsed && (
            <button
              onClick={(e) => { e.stopPropagation(); setAutoScroll(!autoScroll); }}
              className={`text-xs px-2 py-0.5 rounded ${autoScroll ? 'bg-emerald-900/40 text-emerald-300' : 'bg-slate-800 text-slate-400'}`}
            >
              {autoScroll ? 'Auto-scroll ON' : 'Auto-scroll OFF'}
            </button>
          )}
          <span className="text-slate-500 text-xs">{collapsed ? '\u25B2' : '\u25BC'}</span>
        </div>
      </div>

      {!collapsed && (
        <div ref={scrollRef} className="max-h-52 overflow-y-auto p-2 space-y-0.5 font-mono text-xs">
          {entries.length === 0 && (
            <div className="text-slate-600 italic p-2">Waiting for agent activity...</div>
          )}
          {entries.map((entry, i) => {
            const style = LEVEL_STYLES[entry.level] || LEVEL_STYLES.info;
            const icon = LEVEL_ICONS[entry.level] || '\u25CB';
            return (
              <div key={i} className="flex items-start gap-2 py-0.5 animate-fade-in-up">
                <span className="text-slate-600 shrink-0">{formatTime(entry.timestamp)}</span>
                <span className={`shrink-0 px-1.5 py-0 rounded text-[10px] font-medium uppercase ${style.badge}`}>
                  {icon} {entry.level}
                </span>
                <span className={`${style.color} break-all`}>{entry.message}</span>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
