'use client';

import { X, TrendingUp, Target, Activity } from 'lucide-react';
import { GlassCard } from '@/components/ui/glass-card';
import { RadarChart, PolarGrid, PolarAngleAxis, PolarRadiusAxis, Radar, ResponsiveContainer, Tooltip } from 'recharts';
import { CustomTooltip } from '@/components/ui/custom-tooltip';

interface PlayerDetailModalProps {
  isOpen: boolean;
  onClose: () => void;
  player: {
    name: string;
    position: string;
    team: string;
    stats: {
      goals: number;
      assists: number;
      matches: number;
      rating: number;
    };
    form: Array<{ match: string; performance: number }>;
    radarData: Array<{ attribute: string; value: number }>;
  };
}

export function PlayerDetailModal({ isOpen, onClose, player }: PlayerDetailModalProps) {
  if (!isOpen) return null;

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
          <div>
            <h2 className="text-2xl font-bold text-white mb-1">{player.name}</h2>
            <p className="text-slate-400">{player.position} - {player.team}</p>
          </div>
          <button
            onClick={onClose}
            className="p-2 rounded-lg hover:bg-slate-700/50 transition-colors"
          >
            <X className="h-6 w-6 text-slate-400" />
          </button>
        </div>

        {/* Stats Cards */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
          <div className="bg-slate-800/50 rounded-xl p-4 border border-slate-700/50">
            <div className="flex items-center gap-2 mb-2">
              <Target className="h-4 w-4 text-blue-400" />
              <p className="text-xs text-slate-400">Buts</p>
            </div>
            <p className="text-2xl font-bold text-white">{player.stats.goals}</p>
          </div>
          <div className="bg-slate-800/50 rounded-xl p-4 border border-slate-700/50">
            <div className="flex items-center gap-2 mb-2">
              <Activity className="h-4 w-4 text-green-400" />
              <p className="text-xs text-slate-400">Passes D.</p>
            </div>
            <p className="text-2xl font-bold text-white">{player.stats.assists}</p>
          </div>
          <div className="bg-slate-800/50 rounded-xl p-4 border border-slate-700/50">
            <div className="flex items-center gap-2 mb-2">
              <TrendingUp className="h-4 w-4 text-purple-400" />
              <p className="text-xs text-slate-400">Matchs</p>
            </div>
            <p className="text-2xl font-bold text-white">{player.stats.matches}</p>
          </div>
          <div className="bg-slate-800/50 rounded-xl p-4 border border-slate-700/50">
            <div className="flex items-center gap-2 mb-2">
              <span className="text-yellow-400">⭐</span>
              <p className="text-xs text-slate-400">Note</p>
            </div>
            <p className="text-2xl font-bold text-yellow-400">{player.stats.rating.toFixed(1)}</p>
          </div>
        </div>

        {/* Radar Chart */}
        <div className="mb-6">
          <h3 className="text-lg font-semibold text-white mb-4">Profil Joueur</h3>
          <ResponsiveContainer width="100%" height={300}>
            <RadarChart data={player.radarData}>
              <PolarGrid stroke="#475569" />
              <PolarAngleAxis dataKey="attribute" stroke="#94A3B8" />
              <PolarRadiusAxis angle={90} domain={[0, 100]} stroke="#94A3B8" />
              <Radar
                name={player.name}
                dataKey="value"
                stroke="#3B82F6"
                fill="#3B82F6"
                fillOpacity={0.3}
              />
              <Tooltip content={<CustomTooltip />} />
            </RadarChart>
          </ResponsiveContainer>
        </div>

        {/* Recent Form */}
        <div>
          <h3 className="text-lg font-semibold text-white mb-3">Forme Récente</h3>
          <div className="space-y-2">
            {player.form.map((match, idx) => (
              <div
                key={idx}
                className="flex items-center justify-between p-3 bg-slate-800/50 rounded-lg border border-slate-700/50"
              >
                <span className="text-sm text-slate-300">{match.match}</span>
                <div className="flex items-center gap-2">
                  <div className="w-24 h-2 bg-slate-700 rounded-full overflow-hidden">
                    <div
                      className="h-full bg-gradient-to-r from-blue-500 to-green-500"
                      style={{ width: `${match.performance}%` }}
                    />
                  </div>
                  <span className="text-sm font-semibold text-white w-12 text-right">
                    {match.performance}%
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Action Buttons */}
        <div className="mt-6 flex gap-3 justify-end">
          <button
            onClick={onClose}
            className="px-6 py-2 rounded-lg bg-slate-700/50 hover:bg-slate-700 text-white transition-colors"
          >
            Fermer
          </button>
        </div>
      </GlassCard>
    </div>
  );
}
