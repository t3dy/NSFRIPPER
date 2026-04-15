import React from 'react';

export default async function AgentLogsPage() {
  let logs: any = { claims: [], decisions: [], prevention_patterns: [] };
  try {
    const res = await fetch('http://127.0.0.1:8000/api/agent-logs', { cache: 'no-store' });
    logs = await res.json();
  } catch (err) {
    console.error("API error", err);
  }

  return (
    <main className="p-8 max-w-7xl mx-auto space-y-12">
      <header className="space-y-4">
        <h1 className="text-5xl font-extrabold tracking-tight bg-clip-text text-transparent bg-gradient-to-r from-rose-400 to-orange-500">
          Agent Logs & Governance
        </h1>
        <p className="text-rose-200/80 text-lg">Tracks Oracle interaction hypotheses, formal claim lifecycles, and immutable fallback prevention boundaries.</p>
      </header>

      <section className="space-y-6">
        <h2 className="text-3xl font-bold text-white border-b border-white/10 pb-2">Active Prevention Boundaries</h2>
        {logs.prevention_patterns.length === 0 ? (
          <p className="text-gray-500 italic">No patterns recorded.</p>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {logs.prevention_patterns.map((p: any) => (
              <div key={p.id} className="glass-card p-6 border-l-4 border-l-rose-500 hover:border-l-rose-400 transition-all">
                <div className="flex justify-between items-center mb-3">
                  <h3 className="font-bold text-white text-lg">{p.trigger_condition}</h3>
                  <span className="bg-rose-900/50 text-rose-300 text-xs px-2 py-1 rounded font-mono border border-rose-700/50">
                    Subsystem: {p.affected_subsystem}
                  </span>
                </div>
                <p className="text-gray-300 text-sm mb-4">{p.description}</p>
                <div className="bg-black/50 p-4 rounded-xl">
                  <span className="block text-xs uppercase text-orange-400 font-bold mb-1">Required Override Action</span>
                  <p className="text-sm text-gray-200">{p.recommended_action}</p>
                </div>
                {p.example_failure && (
                  <p className="mt-4 text-xs text-rose-400/80 italic">Historical failure point: {p.example_failure}</p>
                )}
              </div>
            ))}
          </div>
        )}
      </section>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        <section className="space-y-6">
          <h2 className="text-2xl font-bold text-white">Proposed Claims</h2>
          <div className="bg-black/20 rounded-2xl p-6 space-y-4">
            {logs.claims.length === 0 ? (
              <p className="text-gray-500 text-sm">No claims have traversed the Oracle yet.</p>
            ) : (
              logs.claims.map((c: any) => (
                <div key={c.id} className="glass-card p-4 space-y-2">
                  <div className="flex justify-between">
                    <span className="text-xs uppercase font-bold text-blue-400">{c.subject_type}: {c.subject_id}</span>
                    <span className={`text-xs px-2 py-0.5 rounded-full ${c.status === 'proposed' ? 'bg-blue-500/20 text-blue-300' : 'bg-emerald-500/20 text-emerald-300'}`}>
                      {c.status}
                    </span>
                  </div>
                  <p className="text-sm text-gray-200 font-serif italic">"{c.statement}"</p>
                  <div className="text-xs text-gray-500 pt-2">Confidence Matrix: {(c.confidence * 100).toFixed(0)}%</div>
                </div>
              ))
            )}
          </div>
        </section>

        <section className="space-y-6">
          <h2 className="text-2xl font-bold text-white">Pipeline Decisions</h2>
          <div className="bg-black/20 rounded-2xl p-6 space-y-4">
            {logs.decisions.length === 0 ? (
              <p className="text-gray-500 text-sm">No decisions logged natively.</p>
            ) : (
              logs.decisions.map((d: any) => (
                <div key={d.id} className="glass-card p-4 border-l-2 border-l-emerald-500">
                  <div className="text-xs text-emerald-400 font-bold mb-1">{d.game_slug} — {d.decision_type}</div>
                  <p className="text-sm text-gray-300">{d.rationale}</p>
                  <p className="text-xs text-emerald-500/70 mt-2 uppercase font-mono">Outcome: {d.outcome}</p>
                </div>
              ))
            )}
          </div>
        </section>
      </div>
    </main>
  );
}
