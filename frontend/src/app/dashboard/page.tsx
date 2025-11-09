'use client';

import { useEffect, useState } from 'react';
import { useSession } from 'next-auth/react';
import { useRouter } from 'next/navigation';
import Navbar from '@/components/Navbar';
import StatsCard from '@/components/StatsCard';
import { api } from '@/lib/api';
import { Bankroll, Opportunity } from '@/types';
import { WalletIcon, TrendingUpIcon, TargetIcon, PercentIcon } from 'lucide-react';

export default function DashboardPage() {
  const { data: session, status } = useSession();
  const router = useRouter();
  const [bankroll, setBankroll] = useState<Bankroll | null>(null);
  const [topOpportunities, setTopOpportunities] = useState<Opportunity[]>([]);
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
      const [bankrollData, opportunitiesData] = await Promise.all([
        api.getBankroll(),
        api.getTopOpportunities(5),
      ]);
      setBankroll(bankrollData);
      setTopOpportunities(opportunitiesData);
    } catch (error) {
      console.error('Error loading dashboard data:', error);
    } finally {
      setLoading(false);
    }
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

  return (
    <div className="min-h-screen bg-gray-50">
      <Navbar />
      
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900">Dashboard</h1>
          <p className="text-gray-600 mt-1">Bienvenue, {session?.user?.name}</p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
          <StatsCard
            title="Bankroll Actuel"
            value={`${bankroll?.current_balance.toFixed(2) || '0.00'} €`}
            subtitle={`Initial: ${bankroll?.initial_balance.toFixed(2) || '0.00'} €`}
            icon={<WalletIcon size={24} />}
            trend={bankroll && bankroll.profit_loss > 0 ? 'up' : bankroll && bankroll.profit_loss < 0 ? 'down' : 'neutral'}
            trendValue={`${bankroll?.profit_loss.toFixed(2) || '0.00'} €`}
          />
          
          <StatsCard
            title="ROI"
            value={`${bankroll?.roi.toFixed(2) || '0.00'}%`}
            subtitle={`${bankroll?.total_bets || 0} paris placés`}
            icon={<PercentIcon size={24} />}
            trend={bankroll && bankroll.roi > 0 ? 'up' : bankroll && bankroll.roi < 0 ? 'down' : 'neutral'}
          />
          
          <StatsCard
            title="Win Rate"
            value={`${bankroll?.win_rate.toFixed(1) || '0.0'}%`}
            subtitle={`${bankroll?.winning_bets || 0} / ${bankroll?.total_bets || 0} gagnés`}
            icon={<TargetIcon size={24} />}
          />
          
          <StatsCard
            title="Total Mise"
            value={`${bankroll?.total_staked.toFixed(2) || '0.00'} €`}
            subtitle={`Retourné: ${bankroll?.total_returned.toFixed(2) || '0.00'} €`}
            icon={<TrendingUpIcon size={24} />}
          />
        </div>

        <div className="bg-white rounded-lg shadow-md p-6">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-xl font-bold text-gray-900">Top 5 Opportunités</h2>
            <button
              onClick={() => router.push('/opportunities')}
              className="text-primary hover:text-blue-600 text-sm font-medium"
            >
              Voir toutes →
            </button>
          </div>
          
          {topOpportunities.length === 0 ? (
            <p className="text-gray-500 text-center py-8">Aucune opportunité disponible</p>
          ) : (
            <div className="space-y-4">
              {topOpportunities.map((opp) => (
                <div
                  key={opp.id}
                  className="border border-gray-200 rounded-lg p-4 hover:border-primary transition-colors"
                >
                  <div className="flex items-center justify-between">
                    <div className="flex-1">
                      <div className="flex items-center gap-2 mb-1">
                        <span className="text-xs font-semibold text-gray-500 uppercase">{opp.sport}</span>
                        <span className="text-xs text-gray-400">•</span>
                        <span className="text-xs text-gray-500">{opp.league}</span>
                      </div>
                      <h3 className="font-semibold text-gray-900">
                        {opp.home_team} vs {opp.away_team}
                      </h3>
                      <p className="text-sm text-gray-600 mt-1">
                        {opp.market_type} - {opp.outcome}
                      </p>
                    </div>
                    <div className="text-right">
                      <p className="text-2xl font-bold text-primary">{opp.odds.toFixed(2)}</p>
                      <p className="text-xs text-gray-500">{opp.bookmaker}</p>
                      {opp.edge_percentage && (
                        <p className="text-xs font-semibold text-success mt-1">
                          Edge: +{opp.edge_percentage.toFixed(1)}%
                        </p>
                      )}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </main>
    </div>
  );
}
