import React from 'react';

export default async function GamesPage() {
  let games = [];
  try {
    const res = await fetch('http://127.0.0.1:8000/api/games', { cache: 'no-store' });
    games = await res.json();
  } catch (err) {
    console.error("API error", err);
  }

  return (
    <main className="p-8 max-w-7xl mx-auto space-y-12">
      <header className="space-y-4">
        <h1 className="text-5xl font-extrabold tracking-tight bg-clip-text text-transparent bg-gradient-to-r from-emerald-400 to-teal-600">
          Extraction Targets
        </h1>
        <p className="text-teal-200/80 text-lg">Tracks active game subjects bridging specific validation rules against execution evidence.</p>
      </header>

      <section>
        {games.length === 0 ? (
          <div className="glass-card p-12 text-center text-gray-500 italic max-w-2xl mx-auto">
            No pipeline executions mapped natively to the V2 boundary yet. 
            <p className="text-xs mt-2 text-gray-600">Run 'python scripts/nes_rom_capture.py &lt;rom&gt;' to see evidence spawn here natively.</p>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {games.map((g: any) => (
              <div key={g.slug} className="glass-card p-6 flex flex-col space-y-4 relative overflow-hidden group hover:border-emerald-500/50 transition-colors">
                <div className="absolute top-0 right-0 w-32 h-32 bg-emerald-500/5 rounded-full blur-2xl -mr-16 -mt-16 group-hover:bg-emerald-500/10 transition-colors"></div>
                
                <h2 className="text-2xl font-bold text-white z-10">{g.slug.replace(/_/g, ' ')}</h2>
                
                <div className="flex space-x-2 z-10">
                  <span className={`px-2 py-1 text-xs font-semibold rounded-full border ${g.validation_level === 'High' ? 'bg-emerald-500/20 text-emerald-300 border-emerald-500/50' : 'bg-amber-500/20 text-amber-300 border-amber-500/50'}`}>
                    Level: {g.validation_level}
                  </span>
                  <span className="px-2 py-1 text-xs font-semibold rounded-full border bg-blue-500/20 text-blue-300 border-blue-500/50">
                    Evidence: {g.evidence_count} traces
                  </span>
                </div>

                <div className="flex-grow z-10">
                  {g.claims.length > 0 ? (
                    <div className="space-y-2 mt-2">
                       <p className="text-xs text-gray-400 uppercase tracking-wider font-bold mb-1">Active Claims</p>
                       {g.claims.map((c: any, i: number) => (
                         <div key={i} className="text-sm text-gray-300 bg-black/40 p-2 rounded border border-white/5 line-clamp-2">"{c.statement}"</div>
                       ))}
                    </div>
                  ) : (
                    <p className="text-sm text-gray-500 italic mt-4">No active claims tracking this subject.</p>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </section>
    </main>
  );
}
