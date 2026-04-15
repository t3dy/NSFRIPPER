import React from 'react';

export default async function DriversPage() {
  let drivers = [];
  try {
    const res = await fetch('http://127.0.0.1:8000/api/drivers', { cache: 'no-store' });
    drivers = await res.json();
  } catch (err) {
    console.error("API error", err);
  }

  return (
    <main className="p-8 max-w-7xl mx-auto space-y-12">
      <header className="space-y-4">
        <h1 className="text-5xl font-extrabold tracking-tight bg-clip-text text-transparent bg-gradient-to-r from-purple-400 to-indigo-600">
          Driver Formalizations
        </h1>
        <p className="text-indigo-200/80 text-lg">Architectural boundaries dictating NES APU animation capabilities and extraction validation limits.</p>
      </header>

      <section className="grid grid-cols-1 lg:grid-cols-2 xl:grid-cols-3 gap-8">
        {drivers.length === 0 ? (
          <div className="glass-card p-8 col-span-full flex justify-center text-gray-500 italic">No formal drivers defined in Ontology.</div>
        ) : (
          drivers.map((driver: any) => (
            <div key={driver.slug} className="glass-card p-6 flex flex-col space-y-4 border-t-4" style={{borderTopColor: 'var(--accent)'}}>
              <div className="flex justify-between items-start">
                <h2 className="text-2xl font-bold text-white tracking-wide uppercase">{driver.slug}</h2>
                <span className={`px-2 py-1 text-xs font-semibold rounded-full border ${driver.nsf_trust_level === 'High' ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/50' : 'bg-amber-500/10 text-amber-400 border-amber-500/50'}`}>
                  NSF Trust: {driver.nsf_trust_level}
                </span>
              </div>
              
              <div className="bg-black/40 rounded-xl p-4 flex flex-col space-y-3">
                <div className="flex justify-between font-mono text-sm border-b border-white/5 pb-2">
                  <span className="text-gray-400">CC11 Range</span>
                  <span className="text-purple-300">{driver.cc11_range}</span>
                </div>
                <div className="flex justify-between font-mono text-sm">
                  <span className="text-gray-400">CC12 Range</span>
                  <span className="text-pink-300">{driver.cc12_range}</span>
                </div>
              </div>

              <div className="space-y-2 flex-grow">
                <div className="flex items-center space-x-2">
                  <span className={`h-2 w-2 rounded-full ${driver.uses_hardware_envelope ? 'bg-green-500' : 'bg-gray-600'}`}></span>
                  <span className="text-sm text-gray-300">Hardware Envelopes</span>
                </div>
                <div className="flex items-center space-x-2">
                  <span className={`h-2 w-2 rounded-full ${driver.animates_duty ? 'bg-green-500' : 'bg-gray-600'}`}></span>
                  <span className="text-sm text-gray-300">Duty Animation</span>
                </div>
                <div className="flex items-center space-x-2">
                  <span className={`h-2 w-2 rounded-full ${driver.high_density_volume ? 'bg-green-500' : 'bg-gray-600'}`}></span>
                  <span className="text-sm text-gray-300">High Density Volume</span>
                </div>
              </div>

              <div className="pt-4 border-t border-white/10">
                <h4 className="text-xs uppercase tracking-widest text-indigo-400 font-bold mb-2">Implications</h4>
                <p className="text-sm text-gray-400 leading-relaxed">{driver.validation_implications}</p>
              </div>
            </div>
          ))
        )}
      </section>
    </main>
  );
}
