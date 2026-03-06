'use client';

import dynamic from 'next/dynamic';

const GraphContainer = dynamic(() => import('@/components/GraphContainer'), {
  ssr: false,
  loading: () => (
    <div className="h-screen w-screen bg-[#050510] flex items-center justify-center">
      <div className="text-center">
        <div className="w-16 h-16 border-4 border-emerald-400/30 border-t-emerald-400 rounded-full animate-spin mb-4 mx-auto" />
        <p className="text-emerald-400 text-lg font-medium">Loading dashboard...</p>
      </div>
    </div>
  ),
});

export default function Home() {
  return <GraphContainer />;
}
