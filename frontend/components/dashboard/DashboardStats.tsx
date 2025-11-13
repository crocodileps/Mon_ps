'use client';

import { StatsWidget } from '@/components/business';
import { useDashboard } from '@/hooks/use-dashboard';
import { DollarSign, TrendingUp, Target, Activity } from 'lucide-react';

export function DashboardStats() {
  const { analytics: stats, isBackendOnline } = useDashboard();

  if (!stats) {
    return (
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {[1, 2, 3, 4].map((i) => (
          <StatsWidget
            key={i}
            title="Chargement..."
            value={0}
            icon={DollarSign}
            loading={true}
          />
        ))}
      </div>
    );
  }

  const bankroll = stats?.bankroll || 0;
  const roi = stats?.roi || 0;
  const avgClv = stats?.avg_clv || 0;
  const activeBets = stats?.active_bets_count || 0;

  // Calcul des variations (24h) - à connecter plus tard avec l'API
  const bankrollChange = stats?.bankroll_change_24h || 0;
  const roiChange = stats?.roi_change_24h || 0;
  const clvChange = stats?.clv_change_24h || 0;

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
      <StatsWidget
        title="Bankroll"
        value={bankroll}
        change={bankrollChange}
        icon={DollarSign}
        format="currency"
        iconColor="text-green-500"
        iconBgColor="bg-green-500/10"
      />
      <StatsWidget
        title="ROI"
        value={roi}
        change={roiChange}
        icon={TrendingUp}
        format="percentage"
        iconColor="text-blue-500"
        iconBgColor="bg-blue-500/10"
      />
      <StatsWidget
        title="CLV Moyen"
        value={avgClv}
        change={clvChange}
        icon={Target}
        format="percentage"
        iconColor="text-purple-500"
        iconBgColor="bg-purple-500/10"
      />
      <StatsWidget
        title="Paris Actifs"
        value={activeBets}
        change={0}
        icon={Activity}
        format="number"
        decimals={0}
        iconColor="text-yellow-500"
        iconBgColor="bg-yellow-500/10"
      />
    </div>
  );
}
