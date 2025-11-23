"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { BarChart3, Home, Target, Activity, Settings } from "lucide-react";

export default function StatsPage() {
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch("http://91.98.131.218:8001/stats/agents")
      .then((res) => res.json())
      .then((data) => {
        setData(data);
        setLoading(false);
      })
      .catch(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-950 via-purple-950 to-slate-950">
        <div className="p-8 text-white">Chargement...</div>
      </div>
    );
  }

  if (!data) return null;

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-950 via-purple-950 to-slate-950">
      {/* Menu Navigation */}
      <nav className="bg-black/20 backdrop-blur-xl border-b border-white/10 px-6 py-4">
        <div className="max-w-7xl mx-auto flex items-center gap-6">
          <Link href="/" className="flex items-center gap-2 text-white hover:text-violet-400 transition-all">
            <Home size={20} />
            <span className="font-medium">Dashboard</span>
          </Link>
          <Link href="/opportunities" className="flex items-center gap-2 text-white hover:text-violet-400 transition-all">
            <Target size={20} />
            <span className="font-medium">Opportunités</span>
          </Link>
          <Link href="/stats" className="flex items-center gap-2 text-violet-400 font-bold border-b-2 border-violet-400 pb-1">
            <BarChart3 size={20} />
            <span>Stats Agents</span>
          </Link>
          <Link href="/agents" className="flex items-center gap-2 text-white hover:text-violet-400 transition-all">
            <Activity size={20} />
            <span className="font-medium">Agents</span>
          </Link>
          <Link href="/settings" className="flex items-center gap-2 text-white hover:text-violet-400 transition-all ml-auto">
            <Settings size={20} />
          </Link>
        </div>
      </nav>

      {/* Contenu */}
      <div className="p-8">
        <h1 className="text-4xl font-bold text-white mb-8">
          📊 Statistiques Agents Learning System
        </h1>
        
        {/* Cards Agents */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-8">
          {data.agents_summary.map((agent: any, i: number) => (
            <div key={i} className="bg-white/10 backdrop-blur-xl p-6 rounded-xl border border-white/20 hover:border-violet-400/40 transition-all">
              <div className="text-sm text-violet-300 mb-2 font-semibold">
                {agent.agent_name}
              </div>
              <div className="text-5xl font-bold text-white mb-2">
                {agent.total_analyses}
              </div>
              <div className="text-sm text-slate-300">
                Confiance: {agent.avg_confidence?.toFixed(1)}%
              </div>
            </div>
          ))}
        </div>

        {/* Tableau Analyses */}
        <div className="bg-white/10 backdrop-blur-xl rounded-xl border border-white/20 overflow-hidden">
          <div className="p-6">
            <h2 className="text-2xl font-bold text-white mb-4">📝 Dernières Analyses</h2>
            <div className="space-y-2">
              {data.recent_analyses?.slice(0, 10).map((a: any, i: number) => (
                <div key={i} className="flex items-center justify-between p-4 bg-white/5 rounded-lg hover:bg-white/10 transition-all">
                  <span className="text-white font-medium w-48">{a.agent_name}</span>
                  <span className="text-slate-300 w-64">{a.home_team} vs {a.away_team}</span>
                  <span className="px-3 py-1 rounded-full text-xs bg-violet-500/20 text-violet-300 w-32 text-center">
                    {a.recommendation}
                  </span>
                  <span className="text-white font-bold w-16 text-right">{a.confidence_score}%</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
