'use client';

import { X, Briefcase, Star, AlertCircle, ThumbsDown, TrendingUp, Calendar } from 'lucide-react';
import { GlassCard } from '@/components/ui/glass-card';

interface CategoryDetailModalProps {
  isOpen: boolean;
  onClose: () => void;
  category: {
    id: string;
    name: string;
    icon: 'briefcase' | 'star' | 'alert' | 'thumbsdown';
    color: string;
    bets: Array<{
      id: string;
      match: string;
      bet: string;
      odds: number;
      stake: number;
      expectedValue: number;
      date: string;
      status: 'pending' | 'won' | 'lost';
    }>;
  };
}

export function CategoryDetailModal({ isOpen, onClose, category }: CategoryDetailModalProps) {
  if (!isOpen) return null;

  const getIcon = () => {
    switch (category.icon) {
      case 'briefcase':
        return Briefcase;
      case 'star':
        return Star;
      case 'alert':
        return AlertCircle;
      case 'thumbsdown':
        return ThumbsDown;
      default:
        return Briefcase;
    }
  };

  const Icon = getIcon();

  const getCategoryColor = () => {
    switch (category.icon) {
      case 'briefcase':
        return 'text-blue-400 bg-blue-500/20 border-blue-500/50';
      case 'star':
        return 'text-yellow-400 bg-yellow-500/20 border-yellow-500/50';
      case 'alert':
        return 'text-orange-400 bg-orange-500/20 border-orange-500/50';
      case 'thumbsdown':
        return 'text-red-400 bg-red-500/20 border-red-500/50';
      default:
        return 'text-slate-400 bg-slate-500/20 border-slate-500/50';
    }
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'won':
        return (
          <span className="px-2 py-1 text-xs font-semibold rounded-lg bg-green-500/20 text-green-400 border border-green-500/50">
            ✓ Gagné
          </span>
        );
      case 'lost':
        return (
          <span className="px-2 py-1 text-xs font-semibold rounded-lg bg-red-500/20 text-red-400 border border-red-500/50">
            ✗ Perdu
          </span>
        );
      case 'pending':
        return (
          <span className="px-2 py-1 text-xs font-semibold rounded-lg bg-yellow-500/20 text-yellow-400 border border-yellow-500/50">
            ⏳ En cours
          </span>
        );
      default:
        return null;
    }
  };

  const calculateStats = () => {
    const totalStake = category.bets.reduce((sum, bet) => sum + bet.stake, 0);
    const avgOdds = category.bets.reduce((sum, bet) => sum + bet.odds, 0) / category.bets.length;
    const avgEV = category.bets.reduce((sum, bet) => sum + bet.expectedValue, 0) / category.bets.length;
    const wonBets = category.bets.filter(bet => bet.status === 'won').length;
    const lostBets = category.bets.filter(bet => bet.status === 'lost').length;
    const pendingBets = category.bets.filter(bet => bet.status === 'pending').length;

    return { totalStake, avgOdds, avgEV, wonBets, lostBets, pendingBets };
  };

  const stats = calculateStats();

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm"
      onClick={onClose}
    >
      <GlassCard
        className="w-full max-w-4xl max-h-[90vh] overflow-y-auto"
        onClick={(e: React.MouseEvent) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center gap-4">
            <div className={`p-3 rounded-xl border-2 ${getCategoryColor()}`}>
              <Icon className="h-8 w-8" />
            </div>
            <div>
              <h2 className="text-2xl font-bold text-white">{category.name}</h2>
              <p className="text-slate-400">{category.bets.length} paris dans cette catégorie</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-2 rounded-lg hover:bg-slate-700/50 transition-colors"
          >
            <X className="h-6 w-6 text-slate-400" />
          </button>
        </div>

        {/* Stats Summary */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
          <div className="bg-slate-800/50 rounded-xl p-4 border border-slate-700/50">
            <p className="text-xs text-slate-400 mb-1">Mise Totale</p>
            <p className="text-xl font-bold text-white">{stats.totalStake.toFixed(2)}€</p>
          </div>
          <div className="bg-slate-800/50 rounded-xl p-4 border border-slate-700/50">
            <p className="text-xs text-slate-400 mb-1">Cote Moyenne</p>
            <p className="text-xl font-bold text-blue-400">{stats.avgOdds.toFixed(2)}</p>
          </div>
          <div className="bg-slate-800/50 rounded-xl p-4 border border-slate-700/50">
            <p className="text-xs text-slate-400 mb-1">EV Moyen</p>
            <p className="text-xl font-bold text-green-400">+{stats.avgEV.toFixed(2)}%</p>
          </div>
          <div className="bg-slate-800/50 rounded-xl p-4 border border-slate-700/50">
            <p className="text-xs text-slate-400 mb-1">Résultats</p>
            <div className="flex items-center gap-2 text-sm">
              <span className="text-green-400 font-semibold">{stats.wonBets}W</span>
              <span className="text-slate-400">-</span>
              <span className="text-red-400 font-semibold">{stats.lostBets}L</span>
              <span className="text-slate-400">-</span>
              <span className="text-yellow-400 font-semibold">{stats.pendingBets}P</span>
            </div>
          </div>
        </div>

        {/* Bets List */}
        <div className="space-y-3">
          {category.bets.map((bet) => (
            <div
              key={bet.id}
              className="p-4 bg-slate-800/50 rounded-xl border border-slate-700/50 hover:border-slate-600/50 transition-all duration-200 hover:shadow-lg hover:shadow-slate-900/50"
            >
              <div className="flex items-start justify-between mb-3">
                <div className="flex-1">
                  <h4 className="text-base font-semibold text-white mb-1">{bet.match}</h4>
                  <p className="text-sm text-slate-300">{bet.bet}</p>
                </div>
                <div className="ml-4">
                  {getStatusBadge(bet.status)}
                </div>
              </div>

              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <div>
                  <p className="text-xs text-slate-400 mb-1">Cote</p>
                  <p className="text-lg font-bold text-blue-400">{bet.odds.toFixed(2)}</p>
                </div>
                <div>
                  <p className="text-xs text-slate-400 mb-1">Mise</p>
                  <p className="text-lg font-bold text-white">{bet.stake.toFixed(2)}€</p>
                </div>
                <div>
                  <p className="text-xs text-slate-400 mb-1">Expected Value</p>
                  <div className="flex items-center gap-1">
                    <TrendingUp className="h-4 w-4 text-green-400" />
                    <p className="text-lg font-bold text-green-400">+{bet.expectedValue.toFixed(2)}%</p>
                  </div>
                </div>
                <div>
                  <p className="text-xs text-slate-400 mb-1">Date</p>
                  <div className="flex items-center gap-1">
                    <Calendar className="h-4 w-4 text-slate-400" />
                    <p className="text-sm text-slate-300">
                      {new Date(bet.date).toLocaleDateString('fr-FR', { 
                        day: '2-digit', 
                        month: 'short' 
                      })}
                    </p>
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>

        {/* Empty State */}
        {category.bets.length === 0 && (
          <div className="text-center py-12">
            <div className="mb-4">
              <Icon className="h-16 w-16 mx-auto text-slate-600" />
            </div>
            <p className="text-lg font-semibold text-slate-400 mb-2">
              Aucun pari dans cette catégorie
            </p>
            <p className="text-sm text-slate-500">
              Les paris que vous classez ici apparaîtront dans cette liste
            </p>
          </div>
        )}

        {/* Action Buttons */}
        <div className="mt-6 flex gap-3 justify-end">
          <button
            onClick={onClose}
            className="px-6 py-2 rounded-lg bg-slate-700/50 hover:bg-slate-700 text-white transition-colors"
          >
            Fermer
          </button>
          {category.bets.length > 0 && (
            <button
              className="px-6 py-2 rounded-lg bg-blue-600 hover:bg-blue-700 text-white transition-colors flex items-center gap-2"
            >
              <span>📊</span>
              Exporter CSV
            </button>
          )}
        </div>
      </GlassCard>
    </div>
  );
}
