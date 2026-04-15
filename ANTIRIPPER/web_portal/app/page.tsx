import React from 'react';

export default async function Dashboard() {
  // Fetch data directly from our Python API Oracle
  let data = null;
  try {
    const res = await fetch('http://127.0.0.1:8000/api/dashboard', { cache: 'no-store' });
    data = await res.json();
  } catch (err) {
    console.error("Failed to fetch data", err);
  }

  if (!data) {
    return (
      <div className="flex items-center justify-center min-h-screen text-red-400">
        <h1>Failed to connect to Oracle API on port 8000.</h1>
      </div>
    );
  }

  return (
    <main className="p-8 max-w-7xl mx-auto space-y-12">
      <header className="space-y-4">
        <h1 className="text-5xl font-extrabold tracking-tight bg-clip-text text-transparent bg-gradient-to-r from-purple-400 to-pink-600">
          ANTIRIPPER Oracle Dash
        </h1>
        <p className="text-gray-400 text-lg">Agentic Knowledge Base & Sound Driver Analytics</p>
      </header>

      <section>
        <h2 className="text-2xl font-bold mb-6 text-purple-200">Driver Families Discovered</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {data.driver_families.map((driver: any) => (
            <div key={driver.slug} className="glass-card p-6 flex flex-col space-y-3">
              <h3 className="text-xl font-semibold text-white">{driver.name}</h3>
              <p className="text-sm text-gray-300 leading-relaxed flex-grow">{driver.description}</p>
              
              <div className="bg-black/30 p-3 rounded-lg space-y-2 mt-4">
                <div className="flex justify-between items-center text-sm">
                  <span className="text-gray-400">CC11 Density (Events/Note)</span>
                  <span className="font-mono text-purple-300">{driver.cc11_per_note}</span>
                </div>
                <div className="flex justify-between items-center text-sm">
                  <span className="text-gray-400">CC12 Density</span>
                  <span className="font-mono text-pink-300">{driver.cc12_per_note}</span>
                </div>
              </div>
              
              <div className="pt-2 border-t border-white/10 text-xs text-gray-400">
                <span className="block font-medium mb-1 text-gray-300">Games:</span>
                {driver.examples}
              </div>
            </div>
          ))}
        </div>
      </section>

      <section className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        <div>
          <h2 className="text-2xl font-bold mb-6 text-purple-200">APU Immutable Facts</h2>
          <div className="space-y-4">
            {data.apu_facts.map((fact: any) => (
              <div key={fact.id} className="glass-card p-5 border-l-4 border-l-purple-500">
                <h4 className="text-lg font-bold text-white uppercase tracking-wider mb-2">{fact.component}</h4>
                <p className="text-gray-300 text-sm mb-3">{fact.fact}</p>
                <code className="block bg-black/40 text-pink-200 text-xs p-3 rounded-md font-mono">{fact.formula}</code>
                <p className="mt-3 text-xs text-red-300">⚠️ {fact.gotchas}</p>
              </div>
            ))}
          </div>
        </div>

        <div>
          <h2 className="text-2xl font-bold mb-6 text-purple-200">Known Blunders (Avoid!)</h2>
          <div className="space-y-4">
            {data.blunders.map((b: any) => (
              <div key={b.id} className="glass-card p-5 border-l-4 border-l-rose-500">
                <h4 className="text-sm font-monospace text-rose-300 mb-1">Cost: {b.prompts_wasted} Prompts</h4>
                <h3 className="text-lg font-bold text-white mb-2">{b.symptom}</h3>
                <p className="text-sm text-gray-300 mb-2"><strong className="text-white">Cause:</strong> {b.root_cause}</p>
                <div className="bg-rose-950/30 p-3 rounded-md mt-2 text-sm text-rose-200 border border-rose-900/50">
                  <strong>Prevention: </strong> {b.prevention}
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>
    </main>
  );
}
