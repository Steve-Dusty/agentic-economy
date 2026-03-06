'use client';

import { useState } from 'react';
import dynamic from 'next/dynamic';

const GraphContainer = dynamic(() => import('@/components/GraphContainer'), {
  ssr: false,
  loading: () => <TabLoading text="Loading Agent Economy..." color="emerald" />,
});

const ZeroClickGraph = dynamic(() => import('@/components/ZeroClickGraph'), {
  ssr: false,
  loading: () => <TabLoading text="Loading ZeroClick.ai..." color="cyan" />,
});

const MindraGraph = dynamic(() => import('@/components/MindraGraph'), {
  ssr: false,
  loading: () => <TabLoading text="Loading Mindra Agents..." color="violet" />,
});

type TabId = 'economy' | 'zeroclick' | 'mindra';

interface Tab {
  id: TabId;
  label: string;
  sublabel: string;
  icon: string;
  activeColor: string;
  activeBg: string;
  borderColor: string;
}

const TABS: Tab[] = [
  {
    id: 'economy',
    label: 'Agent Economy',
    sublabel: 'Nevermined marketplace',
    icon: '◈',
    activeColor: 'text-emerald-400',
    activeBg: 'bg-emerald-500/10',
    borderColor: 'border-emerald-400',
  },
  {
    id: 'zeroclick',
    label: 'ZeroClick.ai',
    sublabel: 'Ad revenue economy',
    icon: '⚡',
    activeColor: 'text-cyan-400',
    activeBg: 'bg-cyan-500/10',
    borderColor: 'border-cyan-400',
  },
  {
    id: 'mindra',
    label: 'Mindra Agents',
    sublabel: 'Multi-agent orchestration',
    icon: '⬡',
    activeColor: 'text-violet-400',
    activeBg: 'bg-violet-500/10',
    borderColor: 'border-violet-400',
  },
];

export default function Home() {
  const [activeTab, setActiveTab] = useState<TabId>('economy');

  return (
    <div className="h-screen w-screen bg-[#050510] flex flex-col overflow-hidden">
      {/* Tab Bar */}
      <div className="flex-none z-50 relative">
        <div className="flex items-center bg-[#0a0a1a]/95 backdrop-blur-xl border-b border-slate-800/60">
          {/* Logo */}
          <div className="px-4 py-2 border-r border-slate-800/40 flex items-center gap-2 shrink-0">
            <span className="text-emerald-400 font-bold text-sm tracking-tight">Agentic</span>
            <span className="text-white font-bold text-sm tracking-tight">Economy</span>
          </div>

          {/* Tabs */}
          <div className="flex items-center gap-0">
            {TABS.map((tab) => {
              const isActive = activeTab === tab.id;
              return (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id)}
                  className={`
                    relative px-5 py-2.5 flex items-center gap-2.5 transition-all duration-200 group
                    border-b-2
                    ${isActive
                      ? `${tab.activeBg} ${tab.borderColor} ${tab.activeColor}`
                      : 'border-transparent text-slate-500 hover:text-slate-300 hover:bg-slate-800/30'
                    }
                  `}
                >
                  <span className={`text-base ${isActive ? tab.activeColor : 'text-slate-600 group-hover:text-slate-400'}`}>
                    {tab.icon}
                  </span>
                  <div className="text-left">
                    <div className={`text-xs font-semibold leading-tight ${isActive ? 'text-white' : ''}`}>
                      {tab.label}
                    </div>
                    <div className={`text-[10px] leading-tight ${isActive ? tab.activeColor : 'text-slate-600'}`}>
                      {tab.sublabel}
                    </div>
                  </div>
                  {isActive && (
                    <span className={`absolute top-2 right-2 w-1.5 h-1.5 rounded-full ${tab.activeColor.replace('text-', 'bg-')} animate-pulse-glow`} />
                  )}
                </button>
              );
            })}
          </div>

          {/* Right spacer for balance */}
          <div className="flex-1" />

          {/* Status indicator */}
          <div className="px-4 flex items-center gap-2">
            <div className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse-glow" />
            <span className="text-[10px] text-slate-500 uppercase tracking-widest font-medium">Live</span>
          </div>
        </div>
      </div>

      {/* Tab Content */}
      <div className="flex-1 relative overflow-hidden">
        <div className={activeTab === 'economy' ? 'h-full' : 'hidden'}>
          <GraphContainer />
        </div>
        <div className={activeTab === 'zeroclick' ? 'h-full' : 'hidden'}>
          {activeTab === 'zeroclick' && <ZeroClickGraph />}
        </div>
        <div className={activeTab === 'mindra' ? 'h-full' : 'hidden'}>
          {activeTab === 'mindra' && <MindraGraph />}
        </div>
      </div>
    </div>
  );
}

function TabLoading({ text, color }: { text: string; color: string }) {
  return (
    <div className="h-full w-full bg-[#050510] flex items-center justify-center">
      <div className="text-center">
        <div className={`w-16 h-16 border-4 border-${color}-400/30 border-t-${color}-400 rounded-full animate-spin mb-4 mx-auto`} />
        <p className={`text-${color}-400 text-lg font-medium`}>{text}</p>
      </div>
    </div>
  );
}
