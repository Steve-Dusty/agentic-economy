'use client';

import type { EconomyStats } from '@/types/graph';

interface Props {
  stats: EconomyStats | null;
  connected: boolean;
  nodeCount: number;
  linkCount: number;
}

export default function StatsOverlay({ stats, connected, nodeCount, linkCount }: Props) {
  return (
    <div className="flex items-center gap-4 text-xs">
      <div className="flex items-center gap-1.5">
        <div className={`w-2 h-2 rounded-full ${connected ? 'bg-emerald-400 animate-pulse-glow' : 'bg-red-400'}`} />
        <span className="text-slate-400">{connected ? 'Live' : 'Offline'}</span>
      </div>
      {stats && (
        <>
          <div className="text-slate-600">|</div>
          <div>
            <span className="text-amber-400 font-medium">{stats.sellers}</span>
            <span className="text-slate-500 ml-1">sellers</span>
          </div>
          <div>
            <span className="text-cyan-400 font-medium">{stats.buyers}</span>
            <span className="text-slate-500 ml-1">buyers</span>
          </div>
          <div>
            <span className="text-indigo-400 font-medium">{stats.teams}</span>
            <span className="text-slate-500 ml-1">teams</span>
          </div>
          <div className="text-slate-600">|</div>
          <div>
            <span className="text-cyan-300 font-medium">{stats.supplyChainDepth}</span>
            <span className="text-slate-500 ml-1">suppliers</span>
          </div>
          <div>
            <span className="text-amber-300 font-medium">{stats.revenueStreams}</span>
            <span className="text-slate-500 ml-1">customers</span>
          </div>
        </>
      )}
    </div>
  );
}
