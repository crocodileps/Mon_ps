'use client';

import { X, TrendingUp, AlertTriangle, CheckCircle2, BarChart3 } from 'lucide-react';
import { GlassCard } from '@/components/ui/glass-card';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, AreaChart, Area } from 'recharts';
import { CustomTooltip } from '@/components/ui/custom-tooltip';

interface BetAnalysisModalProps {
  isOpen: boolean;
  onClose: () => void;
  analysis: {
    betTitle: string;
    match: string;
    expectedValue: number;
    kellyFraction: number;
    confidence: number;
    oddsMovement: Array<{ time: string; odds: number }>;
    probabilities: {
      win: number;
      draw: number;
      lose: number;
    };
    historicalPerformance: Array<{ date: string; roi: number }>;
    risks: string[];
    opportunities: string[];
    recommendation: 'strong_buy' | 'buy' | 'hold' | 'avoid';
  };
}

export function BetAnalysisModal({ isOpen, onClose, analysis }: BetAnalysisModalProps) {
  if (!isOpen) return null;

  const getRecommendationColor = () => {
    switch (analysis.recommendation) {
      case 'strong_buy':
        return 'bg-green-500/20 text-green-400 border-green-500/50';
      case 'buy':
        return 'bg-blue-500/20 text-blue-400 border-blue-500/50';
      case 'hold':
        return 'bg-yellow-500/20 text-yellow-400 border-yellow-500/50';
      case 'avoid':
        return 'bg-red-500/20 text-red-400 border-red-500/50';
      default:
        return 'bg-slate-500/20 text-slate-400 border-slate-500/50';
    }
  };

  const getRecommendationLabel = () => {
    switch (analysis.recommendation) {
      case 'strong_buy':
        return 'Achat Fort Recommandé';
      case 'buy':
        return 'Achat Recommandé';
      case 'hold':
        return 'Attendre';
      case 'avoid':
        return 'Éviter';
      default:
        return 'Neutre';
    }
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm"
      onClick={onClose}
    >
      <GlassCard
        className="w-full max-w-5xl max-h-[90vh] overflow-y-auto"
        onClick={(e: React.MouseEvent) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between mb-6">
          <div>
            <h2 className="text-2xl font-bold text-white mb-1">{analysis.betTitle}</h2>
            <p className="text-slate-400">{analysis.match}</p>
          </div>
          <button
            onClick={onClose}
            className="p-2 rounded-lg hover:bg-slate-700/50 transition-colors"
          >
            <X className="h-6 w-6 text-slate-400" />
          </button>
        </div>

        {/* Key Metrics */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
          <div className="bg-slate-800/50 rounded-xl p-4 border border-slate-700/50">
            <div className="flex items-center gap-2 mb-2">
              <TrendingUp className="h-4 w-4 text-green-400" />
              <p className="text-xs text-slate-400">Expected Value</p>
            </div>
            <p className="text-2xl font-bold text-green-400">+{analysis.expectedValue.toFixed(2)}%</p>
          </div>
          <div className="bg-slate-800/50 rounded-xl p-4 border border-slate-700/50">
            <div className="flex items-center gap-2 mb-2">
              <BarChart3 className="h-4 w-4 text-blue-400" />
              <p className="text-xs text-slate-400">Kelly Fraction</p>
            </div>
            <p className="text-2xl font-bold text-blue-400">{(analysis.kellyFraction * 100).toFixed(1)}%</p>
          </div>
          <div className="bg-slate-800/50 rounded-xl p-4 border border-slate-700/50">
            <div className="flex items-center gap-2 mb-2">
              <CheckCircle2 className="h-4 w-4 text-purple-400" />
              <p className="text-xs text-slate-400">Confiance</p>
            </div>
            <p className="text-2xl font-bold text-purple-400">{analysis.confidence}%</p>
          </div>
          <div className={`rounded-xl p-4 border-2 ${getRecommendationColor()}`}>
            <p className="text-xs mb-2">Recommandation</p>
            <p className="text-lg font-bold">{getRecommendationLabel()}</p>
          </div>
        </div>

        {/* Odds Movement Chart */}
        <div className="mb-6">
          <h3 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
            📈 Mouvement des Cotes
          </h3>
          <ResponsiveContainer width="100%" height={200}>
            <LineChart data={analysis.oddsMovement}>
              <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
              <XAxis dataKey="time" stroke="#94A3B8" />
              <YAxis stroke="#94A3B8" />
              <Tooltip content={<CustomTooltip />} />
              <Line
                type="monotone"
                dataKey="odds"
                stroke="#3B82F6"
                strokeWidth={2}
                dot={{ fill: '#3B82F6', r: 4 }}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>

        {/* Probabilities */}
        <div className="mb-6 p-4 bg-slate-800/50 rounded-xl border border-slate-700/50">
          <h3 className="text-lg font-semibold text-white mb-4">Probabilités Estimées</h3>
          <div className="space-y-3">
            <div>
              <div className="flex items-center justify-between mb-2">
                <span className="text-sm text-slate-300">Victoire</span>
                <span className="text-sm font-semibold text-green-400">{analysis.probabilities.win}%</span>
              </div>
              <div className="w-full h-2 bg-slate-700 rounded-full overflow-hidden">
                <div
                  className="h-full bg-green-500"
                  style={{ width: `${analysis.probabilities.win}%` }}
                />
              </div>
            </div>
            <div>
              <div className="flex items-center justify-between mb-2">
                <span className="text-sm text-slate-300">Match Nul</span>
                <span className="text-sm font-semibold text-yellow-400">{analysis.probabilities.draw}%</span>
              </div>
              <div className="w-full h-2 bg-slate-700 rounded-full overflow-hidden">
                <div
                  className="h-full bg-yellow-500"
                  style={{ width: `${analysis.probabilities.draw}%` }}
                />
              </div>
            </div>
            <div>
              <div className="flex items-center justify-between mb-2">
                <span className="text-sm text-slate-300">Défaite</span>
                <span className="text-sm font-semibold text-red-400">{analysis.probabilities.lose}%</span>
              </div>
              <div className="w-full h-2 bg-slate-700 rounded-full overflow-hidden">
                <div
                  className="h-full bg-red-500"
                  style={{ width: `${analysis.probabilities.lose}%` }}
                />
              </div>
            </div>
          </div>
        </div>

        {/* Historical Performance */}
        <div className="mb-6">
          <h3 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
            📊 Performance Historique (Paris Similaires)
          </h3>
          <ResponsiveContainer width="100%" height={180}>
            <AreaChart data={analysis.historicalPerformance}>
              <defs>
                <linearGradient id="roiGradient" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#3B82F6" stopOpacity={0.3} />
                  <stop offset="95%" stopColor="#3B82F6" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
              <XAxis dataKey="date" stroke="#94A3B8" />
              <YAxis stroke="#94A3B8" />
              <Tooltip content={<CustomTooltip />} />
              <Area
                type="monotone"
                dataKey="roi"
                stroke="#3B82F6"
                fillOpacity={1}
                fill="url(#roiGradient)"
              />
            </AreaChart>
          </ResponsiveContainer>
        </div>

        {/* Risks & Opportunities */}
        <div className="grid md:grid-cols-2 gap-6 mb-6">
          <div>
            <h3 className="text-lg font-semibold text-red-400 mb-3 flex items-center gap-2">
              <AlertTriangle className="h-5 w-5" />
              Risques Identifiés
            </h3>
            <ul className="space-y-2">
              {analysis.risks.map((risk, idx) => (
                <li key={idx} className="flex items-start gap-2 text-slate-300">
                  <span className="text-red-400 mt-1">⚠</span>
                  <span className="text-sm">{risk}</span>
                </li>
              ))}
            </ul>
          </div>
          <div>
            <h3 className="text-lg font-semibold text-green-400 mb-3 flex items-center gap-2">
              <CheckCircle2 className="h-5 w-5" />
              Opportunités
            </h3>
            <ul className="space-y-2">
              {analysis.opportunities.map((opp, idx) => (
                <li key={idx} className="flex items-start gap-2 text-slate-300">
                  <span className="text-green-400 mt-1">✓</span>
                  <span className="text-sm">{opp}</span>
                </li>
              ))}
            </ul>
          </div>
        </div>

        {/* Action Buttons */}
        <div className="flex gap-3 justify-end">
          <button
            onClick={onClose}
            className="px-6 py-2 rounded-lg bg-slate-700/50 hover:bg-slate-700 text-white transition-colors"
          >
            Fermer
          </button>
          <button
            className="px-6 py-2 rounded-lg bg-blue-600 hover:bg-blue-700 text-white transition-colors"
          >
            Placer ce Pari
          </button>
        </div>
      </GlassCard>
    </div>
  );
}
