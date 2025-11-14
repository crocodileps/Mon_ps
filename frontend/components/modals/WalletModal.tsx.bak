'use client';

import { X, TrendingUp } from 'lucide-react';
import { GlassCard } from '@/components/ui/glass-card';
import { PieChart, Pie, Cell, ResponsiveContainer, BarChart, Bar, XAxis, YAxis, Tooltip } from 'recharts';
import { CustomTooltip } from '@/components/ui/custom-tooltip';

interface WalletModalProps {
  isOpen: boolean;
  onClose: () => void;
  walletData: {
    roi: number;
    won: number;
    lost: number;
    pending: number;
    pnlByAgent: Array<{ name: string; value: number; color: string }>;
    roiByType: Array<{ type: string; roi: number }>;
  };
}

export function WalletModal({ isOpen, onClose, walletData }: WalletModalProps) {
  if (!isOpen) return null;

  return (
    <div 
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm"
      onClick={onClose}
    >
      <GlassCard 
        className="w-full max-w-4xl max-h-[90vh] overflow-y-auto"
        onClick={(e: React.MouseEvent) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-2xl font-bold text-white">💰 Portefeuille Détaillé</h2>
          <button
            onClick={onClose}
            className="p-2 rounded-lg hover:bg-slate-700/50 transition-colors"
          >
            <X className="h-6 w-6 text-slate-400" />
          </button>
        </div>

        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
          <div className="bg-slate-800/50 rounded-xl p-4 border border-slate-700/50">
            <p className="text-sm text-slate-400 mb-1">ROI Global</p>
            <p className="text-2xl font-bold text-green-400 flex items-center gap-2">
              <TrendingUp className="h-5 w-5" />
              {walletData.roi.toFixed(2)}%
            </p>
          </div>
          <div className="bg-slate-800/50 rounded-xl p-4 border border-slate-700/50">
            <p className="text-sm text-slate-400 mb-1">Paris Gagnés</p>
            <p className="text-2xl font-bold text-green-400">{walletData.won}</p>
          </div>
          <div className="bg-slate-800/50 rounded-xl p-4 border border-slate-700/50">
            <p className="text-sm text-slate-400 mb-1">Paris Perdus</p>
            <p className="text-2xl font-bold text-red-400">{walletData.lost}</p>
          </div>
          <div className="bg-slate-800/50 rounded-xl p-4 border border-slate-700/50">
            <p className="text-sm text-slate-400 mb-1">En Cours</p>
            <p className="text-2xl font-bold text-yellow-400">{walletData.pending}</p>
          </div>
        </div>

        <div className="grid md:grid-cols-2 gap-6">
          <div>
            <h3 className="text-lg font-semibold text-white mb-4">P&L par Agent</h3>
            <ResponsiveContainer width="100%" height={250}>
              <PieChart>
                <Pie
                  data={walletData.pnlByAgent}
                  cx="50%"
                  cy="50%"
                  labelLine={false}
                  label={(entry) => `${entry.name}: ${entry.value}€`}
                  outerRadius={80}
                  fill="#8884d8"
                  dataKey="value"
                >
                  {walletData.pnlByAgent.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={entry.color} />
                  ))}
                </Pie>
                <Tooltip content={<CustomTooltip />} />
              </PieChart>
            </ResponsiveContainer>
          </div>

          <div>
            <h3 className="text-lg font-semibold text-white mb-4">ROI par Type</h3>
            <ResponsiveContainer width="100%" height={250}>
              <BarChart data={walletData.roiByType}>
                <XAxis dataKey="type" stroke="#94A3B8" />
                <YAxis stroke="#94A3B8" />
                <Tooltip content={<CustomTooltip />} />
                <Bar dataKey="roi" fill="#3B82F6" />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      </GlassCard>
    </div>
  );
}
