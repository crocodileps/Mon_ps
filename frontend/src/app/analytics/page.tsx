'use client';

import { useEffect, useState } from 'react';
import { useSession } from 'next-auth/react';
import { useRouter } from 'next/navigation';
import Navbar from '@/components/Navbar';
import StatsCard from '@/components/StatsCard';
import { api } from '@/lib/api';
import { Bankroll, Bet } from '@/types';

export default function AnalyticsPage() {
  const { data: session, status } = useSession();
  const router = useRouter();
  const [bankroll, setBankroll] = useState<Bankroll | null>(null);
  const [bets, setBets] = useState<Bet[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (status === 'unauthenticated') {
      router.push('/login');
    }
  }, [status, router]);

  useEffect(() => {
    if (session) {
      loadData();
    }
  }, [session]);

  const loadData = async () => {
    try {
      setLoading(true);
      const [bankrollData, betsData] = await Promise.all([
        api.getBankroll(),
        api.getBets(),
      ]);
      setBankroll(bankrollData);
      setBets(betsData);
    } catch (error) {
      console.error('Error loading analytics data:', error);
    } finally {
      setLoading(false);
    }
  };

  const getBookmakerStats = () => {
    const stats: { [key: string]: { bets: number; won: number; profit: number } } = {};
    
    bets.forEach((bet) => {
      if (!stats[bet.bookmaker]) {
        stats[bet.bookmaker] = { bets: 0, won: 0, profit: 0 };
      }
      stats[bet.bookmaker].bets++;
      if (bet.status === 'won') stats[bet.bookmaker].won++;
      if (bet.profit_loss) stats[bet.bookmaker].profit += bet.profit_loss;
    });

    return Object.entries(stats).map(([bookmaker, data]) => ({
      bookmaker,
      bets: data.bets,
      winRate: ((data.won / data.bets) * 100).toFixed(1),
      profit: data.profit.toFixed(2),
    }));
  };

  const getSportStats = () => {
    const stats: { [key: string]: { bets: number; won: number } } = {};
    
    bets.forEach((bet) => {
      if (!stats[bet.sport]) {
        stats[bet.sport] = { bets: 0, won: 0 };
      }
      stats[bet.sport].bets++;
      if (bet.status === 'won') stats[bet.sport].won++;
    });

    return Object.entries(stats).map(([sport, data]) => ({
      name: sport,
      value: data.bets,
      winRate: ((data.won / data.bets) * 100).toFixed(1),
    }));
  };

  if (status === 'loading' || loading) {
    return (
      <div className="min-h-screen bg-gray-50">
        <Navbar />
        <div className="flex items-center justify-center h-screen">
          <div className="text-center">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary mx-auto"></div>
            <p className="mt-4 text-gray-600">Chargement...</p>
          </div>
        </div>
      </div>
    );
  }

  const bookmakerStats = getBookmakerStats();
  const sportStats = getSportStats();

  return (
    <div className="min-h-screen bg-gray-50">
      <Navbar />
      
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900">Analytics</h1>
          <p className="text-gray-600 mt-1">Analyse détaillée de vos performances</p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
          <StatsCard
            title="Profit Total"
            value={`${bankroll?.profit_loss.toFixed(2) || '0.00'} €`}
            trend={bankroll && bankroll.profit_loss > 0 ? 'up' : 'down'}
          />
          <StatsCard
            title="ROI Moyen"
            value={`${bankroll?.roi.toFixed(2) || '0.00'}%`}
          />
          <StatsCard
            title="Paris Gagnés"
            value={bankroll?.winning_bets || 0}
            subtitle={`sur ${bankroll?.total_bets || 0} paris`}
          />
          <StatsCard
            title="Win Rate"
            value={`${bankroll?.win_rate.toFixed(1) || '0.0'}%`}
          />
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 mb-8">
          <div className="bg-white rounded-lg shadow-md p-6">
            <h2 className="text-xl font-bold text-gray-900 mb-4">Performance par Bookmaker</h2>
            {bookmakerStats.length === 0 ? (
              <p className="text-gray-500 text-center py-8">Aucune donnée disponible</p>
            ) : (
              <div className="space-y-4">
                {bookmakerStats.map((stat) => (
                  <div key={stat.bookmaker} className="border-b border-gray-200 pb-4 last:border-0">
                    <div className="flex items-center justify-between mb-2">
                      <h3 className="font-semibold text-gray-900">{stat.bookmaker}</h3>
                      <span className={`font-bold ${parseFloat(stat.profit) > 0 ? 'text-success' : 'text-danger'}`}>
                        {parseFloat(stat.profit) > 0 ? '+' : ''}{stat.profit} €
                      </span>
                    </div>
                    <div className="flex items-center justify-between text-sm text-gray-600">
                      <span>{stat.bets} paris</span>
                      <span>Win rate: {stat.winRate}%</span>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          <div className="bg-white rounded-lg shadow-md p-6">
            <h2 className="text-xl font-bold text-gray-900 mb-4">Statistiques par Sport</h2>
            {sportStats.length === 0 ? (
              <p className="text-gray-500 text-center py-8">Aucune donnée disponible</p>
            ) : (
              <div className="overflow-x-auto">
                <table className="min-w-full divide-y divide-gray-200">
                  <thead className="bg-gray-50">
                    <tr>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Sport</th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Paris</th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Win Rate</th>
                    </tr>
                  </thead>
                  <tbody className="bg-white divide-y divide-gray-200">
                    {sportStats.map((stat) => (
                      <tr key={stat.name}>
                        <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">{stat.name}</td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">{stat.value}</td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">{stat.winRate}%</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </div>
      </main>
    </div>
  );
}
