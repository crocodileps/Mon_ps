'use client';

import { X, TrendingUp, AlertCircle, CheckCircle2 } from 'lucide-react';
import { GlassCard } from '@/components/ui/glass-card';
import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip } from 'recharts';
import { CustomTooltip } from '@/components/ui/custom-tooltip';

interface OpportunityDetailModalProps {
  isOpen: boolean;
  onClose: () => void;
  opportunity: {
    match: string;
    bet: string;
    odds: number;
    aiSummary: string;
    agentConfidence: Array<{ name: string; value: number; color: string }>;
    strengths: string[];
    weaknesses: string[];
  };
}

export function OpportunityDetailModal({ isOpen, onClose, opportunity }: OpportunityDetailModalProps) {
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
          <div>
            <h2 className="text-2xl font-bold text-white mb-1">{opportunity.match}</h2>
            <p className="text-lg text-blue-400 flex items-center gap-2">
              <TrendingUp className="h-5 w-5" />
              {opportunity.bet} @ {opportunity.odds}
            </p>
          </div>
          <button
            onClick={onClose}
            className="p-2 rounded-lg hover:bg-slate-700/50 transition-colors"
          >
            <X className="h-6 w-6 text-slate-400" />
          </button>
        </div>

        <div className="mb-6 p-4 bg-slate-800/50 rounded-xl border border-slate-700/50">
          <h3 className="text-lg font-semibold text-white mb-2 flex items-center gap-2">
            <span className="text-2xl">🤖</span>
            Synthèse IA
          </h3>
          <p className="text-slate-300 leading-relaxed">{opportunity.aiSummary}</p>
        </div>

        <div className="mb-6">
          <h3 className="text-lg font-semibold text-white mb-4">Confiance des Agents</h3>
          <ResponsiveContainer width="100%" height={250}>
            <PieChart>
              <Pie
                data={opportunity.agentConfidence}
                cx="50%"
                cy="50%"
                labelLine={false}
                label={(entry) => `${entry.name}: ${entry.value}%`}
                outerRadius={80}
                fill="#8884d8"
                dataKey="value"
              >
                {opportunity.agentConfidence.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={entry.color} />
                ))}
              </Pie>
              <Tooltip content={<CustomTooltip />} />
            </PieChart>
          </ResponsiveContainer>
        </div>

        <div className="grid md:grid-cols-2 gap-6">
          <div>
            <h3 className="text-lg font-semibold text-green-400 mb-3 flex items-center gap-2">
              <CheckCircle2 className="h-5 w-5" />
              Points Forts
            </h3>
            <ul className="space-y-2">
              {opportunity.strengths.map((strength, idx) => (
                <li key={idx} className="flex items-start gap-2 text-slate-300">
                  <span className="text-green-400 mt-1">•</span>
                  <span>{strength}</span>
                </li>
              ))}
            </ul>
          </div>

          <div>
            <h3 className="text-lg font-semibold text-red-400 mb-3 flex items-center gap-2">
              <AlertCircle className="h-5 w-5" />
              Points Faibles
            </h3>
            <ul className="space-y-2">
              {opportunity.weaknesses.map((weakness, idx) => (
                <li key={idx} className="flex items-start gap-2 text-slate-300">
                  <span className="text-red-400 mt-1">•</span>
                  <span>{weakness}</span>
                </li>
              ))}
            </ul>
          </div>
        </div>

        <div className="mt-6 flex gap-3 justify-end">
          <button
            onClick={onClose}
            className="px-6 py-2 rounded-lg bg-slate-700/50 hover:bg-slate-700 text-white transition-colors"
          >
            Fermer
          </button>
          <button
            className="px-6 py-2 rounded-lg bg-blue-600 hover:bg-blue-700 text-white transition-colors"
          >
            Voir Analyse Complète
          </button>
        </div>
      </GlassCard>
    </div>
  );
}
