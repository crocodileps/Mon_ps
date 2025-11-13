'use client';

import { useState } from 'react';
import { DashboardStats } from '@/components/dashboard/DashboardStats';
import { RecentOpportunities } from '@/components/dashboard/RecentOpportunities';
import { ActiveBetsPreview } from '@/components/dashboard/ActiveBetsPreview';
import { BetForm } from '@/components/business';
import { Button } from '@/components/ui/button';
import { Plus, RefreshCw } from 'lucide-react';

export default function DashboardPage() {
  const [showBetForm, setShowBetForm] = useState(false);
  const [selectedOpportunity, setSelectedOpportunity] = useState<string | null>(null);

  const handlePlaceBet = (opportunityId: string) => {
    setSelectedOpportunity(opportunityId);
    setShowBetForm(true);
  };

  const handleBetFormClose = () => {
    setShowBetForm(false);
    setSelectedOpportunity(null);
  };

  return (
    <div className="container mx-auto p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-white">
            📊 Dashboard
          </h1>
          <p className="text-slate-400 mt-1">
            Vue d'ensemble de votre système de paris sportifs
          </p>
        </div>
        <div className="flex gap-3">
          <Button variant="outline" onClick={() => window.location.reload()}>
            <RefreshCw className="mr-2 h-4 w-4" />
            Actualiser
          </Button>
          <Button onClick={() => setShowBetForm(true)}>
            <Plus className="mr-2 h-4 w-4" />
            Nouveau Pari
          </Button>
        </div>
      </div>

      {/* Stats Row */}
      <DashboardStats />

      {/* Bet Form Modal (si ouvert) */}
      {showBetForm && (
        <div className="fixed inset-0 bg-black/50 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="max-w-2xl w-full max-h-[90vh] overflow-y-auto">
            <BetForm
              mode="create"
              initialData={
                selectedOpportunity
                  ? { match_id: selectedOpportunity }
                  : undefined
              }
              onSuccess={handleBetFormClose}
              onCancel={handleBetFormClose}
            />
          </div>
        </div>
      )}

      {/* Opportunités Récentes */}
      <RecentOpportunities
        limit={3}
        onPlaceBet={handlePlaceBet}
      />

      {/* Paris Actifs */}
      <ActiveBetsPreview limit={5} />

      {/* Quick Links */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <a
          href="/opportunities"
          className="p-6 bg-gradient-to-br from-blue-500/10 to-blue-600/10 border border-blue-500/50 rounded-xl hover:border-blue-400 transition-colors"
        >
          <div className="text-2xl mb-2">🎯</div>
          <h3 className="text-lg font-semibold text-white mb-1">
            Opportunités
          </h3>
          <p className="text-sm text-slate-400">
            Découvrir toutes les opportunités de paris
          </p>
        </a>

        <a
          href="/bets"
          className="p-6 bg-gradient-to-br from-green-500/10 to-green-600/10 border border-green-500/50 rounded-xl hover:border-green-400 transition-colors"
        >
          <div className="text-2xl mb-2">💰</div>
          <h3 className="text-lg font-semibold text-white mb-1">
            Mes Paris
          </h3>
          <p className="text-sm text-slate-400">
            Gérer l'historique complet de vos paris
          </p>
        </a>

        <a
          href="/analytics"
          className="p-6 bg-gradient-to-br from-purple-500/10 to-purple-600/10 border border-purple-500/50 rounded-xl hover:border-purple-400 transition-colors"
        >
          <div className="text-2xl mb-2">📈</div>
          <h3 className="text-lg font-semibold text-white mb-1">
            Analytiques
          </h3>
          <p className="text-sm text-slate-400">
            Statistiques avancées et performances
          </p>
        </a>
      </div>
    </div>
  );
}
