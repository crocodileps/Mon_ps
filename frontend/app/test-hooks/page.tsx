'use client';

import { useState } from 'react';
import { toast } from 'react-hot-toast';
import {
  useHealth,
  useDashboardStats,
  useOpportunities,
  useBets,
  useCreateBet,
  useUpdateBet,
  useDeleteBet,
} from '@/hooks';
import { GlassCard } from '@/components/ui/glass-card';
import { LoadingSpinner } from '@/components/ui/loading-spinner';

export default function TestHooksPage() {
  const [betToCreate, setBetToCreate] = useState({
    match_id: 'test_match_123',
    outcome: 'home',
    bookmaker: 'Bet365',
    odds_value: 2.5,
    stake: 10,
    bet_type: 'tabac' as 'tabac' | 'ligne',
  });

  // Hooks
  const health = useHealth();
  const stats = useDashboardStats();
  const opportunities = useOpportunities({ limit: 5 });
  const bets = useBets({ limit: 10 });

  // Mutations
  const createBet = useCreateBet();
  const updateBet = useUpdateBet();
  const deleteBet = useDeleteBet();

  const handleCreateBet = () => {
    createBet.mutate(betToCreate);
  };

  const handleUpdateBet = (id: number) => {
    updateBet.mutate({
      id,
      payload: { result: 'won', actual_profit: 15 },
    });
  };

  const handleDeleteBet = (id: number) => {
    if (confirm('Êtes-vous sûr de vouloir supprimer ce pari ?')) {
      deleteBet.mutate(id);
    }
  };

  return (
    <div className="min-h-screen bg-background p-6">
      <div className="mx-auto max-w-7xl space-y-6">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-4xl font-bold text-white mb-2">🧪 Test des Hooks React Query</h1>
          <p className="text-slate-400">Validation de la connexion backend et des opérations CRUD</p>
        </div>

        {/* 1. Health Check */}
        <GlassCard>
          <h2 className="text-2xl font-bold text-white mb-4">1. 🏥 Health Check Backend</h2>
          {health.isLoading ? (
            <LoadingSpinner />
          ) : health.isError ? (
            <div className="p-4 bg-red-500/20 border border-red-500/50 rounded-lg">
              <p className="text-red-400 font-semibold">❌ Backend inaccessible</p>
              <p className="text-sm text-slate-300 mt-2">Vérifiez que le backend tourne sur le port 8001</p>
            </div>
          ) : (
            <div className="p-4 bg-green-500/20 border border-green-500/50 rounded-lg">
              <p className="text-green-400 font-semibold">✅ Backend connecté</p>
              <p className="text-sm text-slate-300 mt-2">
                Status: {health.data?.status} | Time: {health.data?.timestamp}
              </p>
            </div>
          )}
        </GlassCard>

        {/* 2. Stats Dashboard */}
        <GlassCard>
          <h2 className="text-2xl font-bold text-white mb-4">2. 📊 Stats Dashboard</h2>
          {stats.isLoading ? (
            <LoadingSpinner />
          ) : stats.isError ? (
            <div className="text-red-400">❌ Erreur lors du chargement des stats</div>
          ) : (
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <div className="p-4 bg-slate-800/50 rounded-lg border border-slate-700/50">
                <p className="text-xs text-slate-400 mb-1">Bankroll</p>
                <p className="text-2xl font-bold text-white">
                  {stats.bankroll.data?.current_bankroll?.toFixed(2) || 0}€
                </p>
              </div>
              <div className="p-4 bg-slate-800/50 rounded-lg border border-slate-700/50">
                <p className="text-xs text-slate-400 mb-1">ROI</p>
                <p className="text-2xl font-bold text-green-400">
                  {stats.global.data?.roi?.toFixed(2) || 0}%
                </p>
              </div>
              <div className="p-4 bg-slate-800/50 rounded-lg border border-slate-700/50">
                <p className="text-xs text-slate-400 mb-1">Total Bets</p>
                <p className="text-2xl font-bold text-blue-400">
                  {stats.global.data?.total_bets || 0}
                </p>
              </div>
              <div className="p-4 bg-slate-800/50 rounded-lg border border-slate-700/50">
                <p className="text-xs text-slate-400 mb-1">Win Rate</p>
                <p className="text-2xl font-bold text-purple-400">
                  {stats.global.data?.win_rate?.toFixed(1) || 0}%
                </p>
              </div>
            </div>
          )}
          <button
            onClick={() => stats.refetch()}
            className="mt-4 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-colors"
          >
            🔄 Rafraîchir Stats
          </button>
        </GlassCard>

        {/* 3. Opportunities */}
        <GlassCard>
          <h2 className="text-2xl font-bold text-white mb-4">3. 🎯 Opportunités (Top 5)</h2>
          {opportunities.isLoading ? (
            <LoadingSpinner />
          ) : opportunities.isError ? (
            <div className="text-red-400">❌ Erreur lors du chargement des opportunités</div>
          ) : opportunities.data && opportunities.data.length > 0 ? (
            <div className="space-y-2">
              {opportunities.data.map((opp) => (
                <div
                  key={opp.id}
                  className="p-3 bg-slate-800/50 rounded-lg border border-slate-700/50 flex justify-between items-center"
                >
                  <div>
                    <p className="text-white font-semibold">
                      {opp.home_team} vs {opp.away_team}
                    </p>
                    <p className="text-sm text-slate-400">
                      {opp.outcome} @ {opp.best_odds} ({opp.bookmaker_best})
                    </p>
                  </div>
                  <div className="text-right">
                    <p className="text-green-400 font-bold">+{opp.edge_pct.toFixed(2)}%</p>
                    <p className="text-xs text-slate-400">{opp.nb_bookmakers} bookmakers</p>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-slate-400">Aucune opportunité trouvée</p>
          )}
        </GlassCard>

        {/* 4. Create Bet (Test CRUD) */}
        <GlassCard>
          <h2 className="text-2xl font-bold text-white mb-4">4. ➕ Créer un Pari (Test)</h2>
          <div className="grid grid-cols-2 md:grid-cols-3 gap-4 mb-4">
            <input
              type="text"
              placeholder="Match ID"
              value={betToCreate.match_id}
              onChange={(e) => setBetToCreate({ ...betToCreate, match_id: e.target.value })}
              className="px-3 py-2 bg-slate-800 border border-slate-700 rounded-lg text-white"
            />
            <input
              type="number"
              placeholder="Cote"
              value={betToCreate.odds_value}
              onChange={(e) =>
                setBetToCreate({ ...betToCreate, odds_value: parseFloat(e.target.value) })
              }
              className="px-3 py-2 bg-slate-800 border border-slate-700 rounded-lg text-white"
            />
            <input
              type="number"
              placeholder="Mise (€)"
              value={betToCreate.stake}
              onChange={(e) =>
                setBetToCreate({ ...betToCreate, stake: parseFloat(e.target.value) })
              }
              className="px-3 py-2 bg-slate-800 border border-slate-700 rounded-lg text-white"
            />
          </div>
          <button
            onClick={handleCreateBet}
            disabled={createBet.isPending}
            className="px-6 py-2 bg-green-600 hover:bg-green-700 disabled:bg-slate-700 text-white rounded-lg transition-colors"
          >
            {createBet.isPending ? 'Création...' : '✅ Créer le Pari'}
          </button>
        </GlassCard>

        {/* 5. Bets List (Test Update/Delete) */}
        <GlassCard>
          <h2 className="text-2xl font-bold text-white mb-4">5. 📋 Liste des Paris</h2>
          {bets.isLoading ? (
            <LoadingSpinner />
          ) : bets.isError ? (
            <div className="text-red-400">❌ Erreur lors du chargement des paris</div>
          ) : bets.data && bets.data.length > 0 ? (
            <div className="space-y-2">
              {bets.data.map((bet) => (
                <div
                  key={bet.id}
                  className="p-4 bg-slate-800/50 rounded-lg border border-slate-700/50"
                >
                  <div className="flex justify-between items-start mb-2">
                    <div>
                      <p className="text-white font-semibold">
                        Pari #{bet.id} - {bet.match_id}
                      </p>
                      <p className="text-sm text-slate-400">
                        {bet.outcome} @ {bet.odds_value} ({bet.bookmaker}) - {bet.stake}€
                      </p>
                    </div>
                    <span
                      className={`px-2 py-1 text-xs font-semibold rounded ${
                        bet.result === 'won'
                          ? 'bg-green-500/20 text-green-400'
                          : bet.result === 'lost'
                          ? 'bg-red-500/20 text-red-400'
                          : 'bg-yellow-500/20 text-yellow-400'
                      }`}
                    >
                      {bet.result || 'pending'}
                    </span>
                  </div>
                  <div className="flex gap-2">
                    <button
                      onClick={() => handleUpdateBet(bet.id)}
                      disabled={updateBet.isPending}
                      className="px-3 py-1 text-sm bg-blue-600 hover:bg-blue-700 disabled:bg-slate-700 text-white rounded transition-colors"
                    >
                      ✏️ Marquer Gagné
                    </button>
                    <button
                      onClick={() => handleDeleteBet(bet.id)}
                      disabled={deleteBet.isPending}
                      className="px-3 py-1 text-sm bg-red-600 hover:bg-red-700 disabled:bg-slate-700 text-white rounded transition-colors"
                    >
                      🗑️ Supprimer
                    </button>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-slate-400">Aucun pari trouvé</p>
          )}
        </GlassCard>

        {/* 6. Toast Tests */}
        <GlassCard>
          <h2 className="text-2xl font-bold text-white mb-4">6. 🔔 Test Notifications Toast</h2>
          <div className="flex flex-wrap gap-2">
            <button
              onClick={() => toast.success('✅ Notification de succès')}
              className="px-4 py-2 bg-green-600 hover:bg-green-700 text-white rounded-lg transition-colors"
            >
              Success Toast
            </button>
            <button
              onClick={() => toast.error('❌ Notification d\'erreur')}
              className="px-4 py-2 bg-red-600 hover:bg-red-700 text-white rounded-lg transition-colors"
            >
              Error Toast
            </button>
            <button
              onClick={() => toast('ℹ️ Notification standard')}
              className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-colors"
            >
              Info Toast
            </button>
            <button
              onClick={() => toast.loading('⏳ Chargement...')}
              className="px-4 py-2 bg-yellow-600 hover:bg-yellow-700 text-white rounded-lg transition-colors"
            >
              Loading Toast
            </button>
          </div>
        </GlassCard>
      </div>
    </div>
  );
}
