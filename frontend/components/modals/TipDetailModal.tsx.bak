'use client';

import { X, Lightbulb, TrendingUp, Users, Calendar } from 'lucide-react';
import { GlassCard } from '@/components/ui/glass-card';

interface TipDetailModalProps {
  isOpen: boolean;
  onClose: () => void;
  tip: {
    id: string;
    title: string;
    type: 'combiné' | 'système' | 'conseil';
    description: string;
    totalOdds: number;
    potentialReturn: number;
    stake: number;
    bets: Array<{
      id: string;
      match: string;
      selection: string;
      odds: number;
      status: 'pending' | 'won' | 'lost';
    }>;
    confidence: number;
    author: string;
    createdAt: string;
  };
}

export function TipDetailModal({ isOpen, onClose, tip }: TipDetailModalProps) {
  if (!isOpen) return null;

  const getTypeColor = () => {
    switch (tip.type) {
      case 'combiné':
        return 'bg-blue-500/20 text-blue-400 border-blue-500/50';
      case 'système':
        return 'bg-purple-500/20 text-purple-400 border-purple-500/50';
      case 'conseil':
        return 'bg-green-500/20 text-green-400 border-green-500/50';
      default:
        return 'bg-slate-500/20 text-slate-400 border-slate-500/50';
    }
  };

  const getTypeLabel = () => {
    switch (tip.type) {
      case 'combiné':
        return '🎯 Combiné';
      case 'système':
        return '⚙️ Système';
      case 'conseil':
        return '💡 Conseil';
      default:
        return 'Tip';
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'won':
        return 'text-green-400';
      case 'lost':
        return 'text-red-400';
      case 'pending':
        return 'text-yellow-400';
      default:
        return 'text-slate-400';
    }
  };

  const getStatusLabel = (status: string) => {
    switch (status) {
      case 'won':
        return '✓ Gagné';
      case 'lost':
        return '✗ Perdu';
      case 'pending':
        return '⏳ En cours';
      default:
        return 'Inconnu';
    }
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm"
      onClick={onClose}
    >
      <GlassCard
        className="w-full max-w-3xl max-h-[90vh] overflow-y-auto"
        onClick={(e: React.MouseEvent) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between mb-6">
          <div className="flex-1">
            <div className="flex items-center gap-3 mb-2">
              <h2 className="text-2xl font-bold text-white">{tip.title}</h2>
              <span className={`px-3 py-1 rounded-lg text-xs font-semibold border ${getTypeColor()}`}>
                {getTypeLabel()}
              </span>
            </div>
            <p className="text-slate-400">{tip.description}</p>
          </div>
          <button
            onClick={onClose}
            className="p-2 rounded-lg hover:bg-slate-700/50 transition-colors ml-4"
          >
            <X className="h-6 w-6 text-slate-400" />
          </button>
        </div>

        {/* Key Metrics */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
          <div className="bg-slate-800/50 rounded-xl p-4 border border-slate-700/50">
            <div className="flex items-center gap-2 mb-2">
              <TrendingUp className="h-4 w-4 text-blue-400" />
              <p className="text-xs text-slate-400">Cote Totale</p>
            </div>
            <p className="text-2xl font-bold text-blue-400">{tip.totalOdds.toFixed(2)}</p>
          </div>
          <div className="bg-slate-800/50 rounded-xl p-4 border border-slate-700/50">
            <div className="flex items-center gap-2 mb-2">
              <span className="text-green-400">💰</span>
              <p className="text-xs text-slate-400">Gain Potentiel</p>
            </div>
            <p className="text-2xl font-bold text-green-400">{tip.potentialReturn.toFixed(2)}€</p>
          </div>
          <div className="bg-slate-800/50 rounded-xl p-4 border border-slate-700/50">
            <div className="flex items-center gap-2 mb-2">
              <Lightbulb className="h-4 w-4 text-purple-400" />
              <p className="text-xs text-slate-400">Confiance</p>
            </div>
            <p className="text-2xl font-bold text-purple-400">{tip.confidence}%</p>
          </div>
          <div className="bg-slate-800/50 rounded-xl p-4 border border-slate-700/50">
            <div className="flex items-center gap-2 mb-2">
              <span className="text-yellow-400">🎲</span>
              <p className="text-xs text-slate-400">Mise</p>
            </div>
            <p className="text-2xl font-bold text-white">{tip.stake.toFixed(2)}€</p>
          </div>
        </div>

        {/* Bets List */}
        <div className="mb-6">
          <h3 className="text-lg font-semibold text-white mb-4">
            Paris Inclus ({tip.bets.length})
          </h3>
          <div className="space-y-3">
            {tip.bets.map((bet, idx) => (
              <div
                key={bet.id}
                className="p-4 bg-slate-800/50 rounded-xl border border-slate-700/50 hover:border-slate-600/50 transition-colors"
              >
                <div className="flex items-start justify-between mb-2">
                  <div className="flex-1">
                    <div className="flex items-center gap-2 mb-1">
                      <span className="text-sm font-semibold text-slate-400">#{idx + 1}</span>
                      <h4 className="text-base font-semibold text-white">{bet.match}</h4>
                    </div>
                    <p className="text-sm text-slate-300">{bet.selection}</p>
                  </div>
                  <div className="text-right ml-4">
                    <p className="text-lg font-bold text-blue-400">{bet.odds.toFixed(2)}</p>
                    <p className={`text-xs font-semibold ${getStatusColor(bet.status)}`}>
                      {getStatusLabel(bet.status)}
                    </p>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Author & Date */}
        <div className="flex items-center justify-between p-4 bg-slate-800/50 rounded-xl border border-slate-700/50 mb-6">
          <div className="flex items-center gap-3">
            <div className="flex items-center gap-2 text-slate-300">
              <Users className="h-4 w-4 text-slate-400" />
              <span className="text-sm">Par <span className="font-semibold text-white">{tip.author}</span></span>
            </div>
          </div>
          <div className="flex items-center gap-2 text-slate-300">
            <Calendar className="h-4 w-4 text-slate-400" />
            <span className="text-sm">{new Date(tip.createdAt).toLocaleDateString('fr-FR')}</span>
          </div>
        </div>

        {/* Calculation Breakdown */}
        {tip.type === 'combiné' && (
          <div className="p-4 bg-gradient-to-r from-blue-500/10 to-purple-500/10 rounded-xl border border-blue-500/30 mb-6">
            <h4 className="text-sm font-semibold text-white mb-2">💡 Calcul du Combiné</h4>
            <div className="text-sm text-slate-300 space-y-1">
              <p>
                Cote totale = {tip.bets.map(b => b.odds.toFixed(2)).join(' × ')} = <span className="font-semibold text-blue-400">{tip.totalOdds.toFixed(2)}</span>
              </p>
              <p>
                Gain si tous les paris gagnent = {tip.stake}€ × {tip.totalOdds.toFixed(2)} = <span className="font-semibold text-green-400">{tip.potentialReturn.toFixed(2)}€</span>
              </p>
              <p className="text-xs text-slate-400 mt-2">
                ⚠️ Attention : Un seul pari perdu = perte totale de la mise
              </p>
            </div>
          </div>
        )}

        {/* Action Buttons */}
        <div className="flex gap-3 justify-end">
          <button
            onClick={onClose}
            className="px-6 py-2 rounded-lg bg-slate-700/50 hover:bg-slate-700 text-white transition-colors"
          >
            Fermer
          </button>
          <button
            className="px-6 py-2 rounded-lg bg-blue-600 hover:bg-blue-700 text-white transition-colors flex items-center gap-2"
          >
            <span>📋</span>
            Copier les Paris
          </button>
        </div>
      </GlassCard>
    </div>
  );
}
