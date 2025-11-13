'use client';

import { OpportunityCard, BetCard, StatsWidget } from '@/components/business';
import { DollarSign, TrendingUp, Target, Activity } from 'lucide-react';

export default function TestBusinessComponentsPage() {
  const mockOpportunity = {
    match_id: 'test-1',
    home_team: 'Paris Saint Germain',
    away_team: 'Olympique de Marseille',
    sport: 'soccer_france_ligue_one',
    commence_time: new Date(Date.now() + 86400000).toISOString(),
    outcome: 'home',
    best_odds: 2.15,
    bookmaker_best: 'Betclic',
    edge_pct: 12.5,
    nb_bookmakers: 15,
  };

  const mockBet = {
    id: 1,
    outcome: 'Paris Saint Germain gagne',
    bookmaker: 'Betclic',
    odds_value: 2.15,
    stake: 50,
    bet_type: 'tabac' as const,
    result: 'won' as const,
    actual_profit: 57.5,
    created_at: new Date().toISOString(),
  };

  return (
    <div className="container mx-auto p-8 space-y-8">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-white mb-2">🧪 Test des Composants Business</h1>
        <p className="text-slate-400">Validation visuelle de tous les composants métier créés</p>
      </div>

      <section className="space-y-4">
        <h2 className="text-2xl font-semibold text-white">📊 StatsWidget</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          <StatsWidget title="Bankroll" value={1250.50} change={5.2} icon={DollarSign} format="currency" iconColor="text-green-500" iconBgColor="bg-green-500/10" />
          <StatsWidget title="ROI" value={12.5} change={2.1} icon={TrendingUp} format="percentage" iconColor="text-blue-500" iconBgColor="bg-blue-500/10" />
          <StatsWidget title="CLV Moyen" value={3.2} change={-0.5} icon={Target} format="percentage" iconColor="text-purple-500" iconBgColor="bg-purple-500/10" />
          <StatsWidget title="Paris Actifs" value={8} change={0} icon={Activity} format="number" iconColor="text-yellow-500" iconBgColor="bg-yellow-500/10" />
        </div>
      </section>

      <section className="space-y-4">
        <h2 className="text-2xl font-semibold text-white">🎯 OpportunityCard</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          <OpportunityCard {...mockOpportunity} onPlaceBet={() => alert('Placer ce pari')} />
          <OpportunityCard {...mockOpportunity} edge_pct={18.5} outcome="away" best_odds={3.40} />
          <OpportunityCard {...mockOpportunity} edge_pct={8.2} outcome="draw" best_odds={3.10} bookmaker_best="Unibet" />
        </div>
      </section>

      <section className="space-y-4">
        <h2 className="text-2xl font-semibold text-white">💰 BetCard</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          <BetCard {...mockBet} onEdit={() => alert('Éditer')} onDelete={() => alert('Supprimer')} />
          <BetCard {...mockBet} id={2} result="lost" actual_profit={-50} bet_type="ligne" />
          <BetCard {...mockBet} id={3} result="pending" actual_profit={null} bet_type="tabac" />
        </div>
      </section>

      <section className="mt-12 p-6 bg-slate-800/50 rounded-xl border border-slate-700">
        <h3 className="text-xl font-semibold text-white mb-4">✅ Résumé des Tests</h3>
        <div className="space-y-2 text-slate-300">
          <p>✅ StatsWidget : Affichage correct avec différents formats</p>
          <p>✅ OpportunityCard : Carte opportunité avec différents edges</p>
          <p>✅ BetCard : Affichage des 3 états (gagné/perdu/en cours)</p>
        </div>
      </section>
    </div>
  );
}
