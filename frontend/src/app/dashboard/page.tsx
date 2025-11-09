'use client';

import { useEffect, useState } from 'react';
import { useSession } from 'next-auth/react';
import { useRouter } from 'next/navigation';

interface Opportunity {
  match_id: string;
  home_team: string;
  away_team: string;
  sport: string;
  outcome: string;
  best_odd: string;
  worst_odd: string;
  spread_pct: number;
  bookmaker_best: string;
  bookmaker_worst: string;
}

export default function Dashboard() {
  const { data: session, status } = useSession();
  const router = useRouter();
  const [opportunities, setOpportunities] = useState<Opportunity[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (status === 'unauthenticated') {
      router.push('/login');
    }
  }, [status, router]);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const response = await fetch('https://api.crocodile.ovh/opportunities/realistic');
        const data = await response.json();
        setOpportunities(data.slice(0, 10)); // Top 10
      } catch (error) {
        console.error('Erreur chargement:', error);
      } finally {
        setLoading(false);
      }
    };

    if (status === 'authenticated') {
      fetchData();
    }
  }, [status]);

  if (status === 'loading' || loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-xl">Chargement...</div>
      </div>
    );
  }

  return (
    <div className="p-8">
      <h1 className="text-3xl font-bold mb-8">Dashboard Mon_PS</h1>
      
      <p className="mb-8 text-lg">Bienvenue, {session?.user?.name} ��</p>

      {/* Stats rapides */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
        <div className="bg-white rounded-lg shadow p-6">
          <h3 className="text-gray-500 text-sm">Bankroll</h3>
          <p className="text-3xl font-bold">1011 €</p>
        </div>
        <div className="bg-white rounded-lg shadow p-6">
          <h3 className="text-gray-500 text-sm">Cotes</h3>
          <p className="text-3xl font-bold">2520</p>
        </div>
        <div className="bg-white rounded-lg shadow p-6">
          <h3 className="text-gray-500 text-sm">Paris</h3>
          <p className="text-3xl font-bold">4</p>
        </div>
        <div className="bg-white rounded-lg shadow p-6">
          <h3 className="text-gray-500 text-sm">ROI</h3>
          <p className="text-3xl font-bold text-green-600">+1.1%</p>
        </div>
      </div>

      {/* Top Opportunités */}
      <div className="bg-white rounded-lg shadow">
        <div className="p-6 border-b">
          <h2 className="text-2xl font-bold">🎯 Top 10 Opportunités</h2>
          <p className="text-gray-500 text-sm">Meilleures différences de cotes détectées</p>
        </div>
        
        <div className="overflow-x-auto">
          <table className="min-w-full">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Match</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Outcome</th>
                <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">Meilleure Cote</th>
                <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">Pire Cote</th>
                <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">Spread %</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200">
              {opportunities.map((opp, index) => (
                <tr key={index} className="hover:bg-gray-50">
                  <td className="px-6 py-4">
                    <div className="font-medium">{opp.home_team} vs {opp.away_team}</div>
                    <div className="text-sm text-gray-500">{opp.sport.replace('soccer_', '').toUpperCase()}</div>
                  </td>
                  <td className="px-6 py-4 text-sm">{opp.outcome}</td>
                  <td className="px-6 py-4 text-right">
                    <div className="font-bold text-green-600">{opp.best_odd}</div>
                    <div className="text-xs text-gray-500">{opp.bookmaker_best}</div>
                  </td>
                  <td className="px-6 py-4 text-right">
                    <div className="font-mono">{opp.worst_odd}</div>
                    <div className="text-xs text-gray-500">{opp.bookmaker_worst}</div>
                  </td>
                  <td className="px-6 py-4 text-right">
                    <span className={`inline-flex px-2 py-1 text-sm font-bold rounded ${
                      opp.spread_pct > 30 ? 'bg-green-100 text-green-800' :
                      opp.spread_pct > 20 ? 'bg-yellow-100 text-yellow-800' :
                      'bg-gray-100 text-gray-800'
                    }`}>
                      {opp.spread_pct.toFixed(1)}%
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
