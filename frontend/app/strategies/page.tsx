'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { motion } from 'framer-motion';
import { 
  TrendingUp, TrendingDown, Minus, Brain, Zap, 
  AlertCircle, CheckCircle, Clock, ArrowRight,
  Target, Activity, BarChart3
} from 'lucide-react';

interface Strategy {
  id: number;
  agent_name: string;
  strategy_name: string;
  win_rate: number | null;
  roi: number | null;
  total_predictions: number;
  tier: string;
  global_score: number;
  trend: 'up' | 'down' | 'stable';
  has_improvement_test: boolean;
}

interface Improvement {
  id: number;
  agent_name: string;
  strategy_name: string;
  baseline_win_rate: number;
  failure_pattern: string;
  missing_factors: string[];
  recommended_adjustments: string[];
  new_threshold: number;
  llm_reasoning: string;
  ab_test_active: boolean;
  improvement_applied: boolean;
  created_at: string;
}

export default function StrategiesPage() {
  const router = useRouter();
  const [strategies, setStrategies] = useState<Strategy[]>([]);
  const [improvements, setImprovements] = useState<Improvement[]>([]);
  const [selectedStrategy, setSelectedStrategy] = useState<number | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    try {
      // Fetch strategies
      const stratRes = await fetch('http://91.98.131.218:8001/strategies/ranking');
      const stratData = await stratRes.json();
      setStrategies(stratData.strategies || []);

      // Fetch improvements
      const impRes = await fetch('http://91.98.131.218:8001/strategies/improvements');
      const impData = await impRes.json();
      setImprovements(impData.improvements || []);
      
      setLoading(false);
    } catch (error) {
      console.error('Erreur fetch:', error);
      setLoading(false);
    }
  };

  const getTierColor = (tier: string) => {
    switch (tier) {
      case 'S': return 'from-yellow-400 to-orange-500';
      case 'A': return 'from-green-400 to-emerald-500';
      case 'B': return 'from-blue-400 to-cyan-500';
      case 'C': return 'from-orange-400 to-red-500';
      case 'D': return 'from-red-500 to-red-700';
      default: return 'from-gray-400 to-gray-600';
    }
  };

  const getTrendIcon = (trend: string) => {
    switch (trend) {
      case 'up': return <TrendingUp className="w-4 h-4 text-green-400" />;
      case 'down': return <TrendingDown className="w-4 h-4 text-red-400" />;
      default: return <Minus className="w-4 h-4 text-gray-400" />;
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-900 via-purple-900 to-slate-900 flex items-center justify-center">
        <div className="text-white text-xl">Chargement...</div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-purple-900 to-slate-900 p-8">
      {/* Header */}
      <motion.div
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        className="mb-8"
      >
        <div className="flex items-center gap-4 mb-4">
          <div className="p-3 bg-gradient-to-br from-violet-500/20 to-purple-500/20 rounded-xl backdrop-blur-sm border border-violet-500/30">
            <Brain className="w-8 h-8 text-violet-400" />
          </div>
          <div>
            <h1 className="text-4xl font-bold text-white mb-2">
              Strategies & Meta-Learning
            </h1>
            <p className="text-gray-400">
              Système d'auto-amélioration avec GPT-4o
            </p>
          </div>
        </div>

        {/* Stats globales */}
        <div className="grid grid-cols-4 gap-4 mt-6">
          <div className="bg-white/5 backdrop-blur-lg rounded-xl p-4 border border-white/10">
            <div className="flex items-center justify-between mb-2">
              <span className="text-gray-400 text-sm">Stratégies actives</span>
              <Activity className="w-4 h-4 text-violet-400" />
            </div>
            <div className="text-2xl font-bold text-white">{strategies.length}</div>
          </div>

          <div className="bg-white/5 backdrop-blur-lg rounded-xl p-4 border border-white/10">
            <div className="flex items-center justify-between mb-2">
              <span className="text-gray-400 text-sm">Tier S/A</span>
              <Target className="w-4 h-4 text-green-400" />
            </div>
            <div className="text-2xl font-bold text-white">
              {strategies.filter(s => ['S', 'A'].includes(s.tier)).length}
            </div>
          </div>

          <div className="bg-white/5 backdrop-blur-lg rounded-xl p-4 border border-white/10">
            <div className="flex items-center justify-between mb-2">
              <span className="text-gray-400 text-sm">Améliorations GPT</span>
              <Brain className="w-4 h-4 text-purple-400" />
            </div>
            <div className="text-2xl font-bold text-white">
              {improvements.length}
            </div>
          </div>

          <div className="bg-white/5 backdrop-blur-lg rounded-xl p-4 border border-white/10">
            <div className="flex items-center justify-between mb-2">
              <span className="text-gray-400 text-sm">Tests A/B actifs</span>
              <BarChart3 className="w-4 h-4 text-blue-400" />
            </div>
            <div className="text-2xl font-bold text-white">
              {improvements.filter(i => i.ab_test_active).length}
            </div>
          </div>
        </div>
      </motion.div>

      {/* Ranking des stratégies */}
      <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
        {/* Liste stratégies */}
        <div className="xl:col-span-2">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="bg-white/5 backdrop-blur-lg rounded-xl border border-white/10 overflow-hidden"
          >
            <div className="p-6 border-b border-white/10">
              <h2 className="text-2xl font-bold text-white flex items-center gap-2">
                <Zap className="w-6 h-6 text-violet-400" />
                Ranking des Stratégies
              </h2>
            </div>

            <div className="divide-y divide-white/10">
              {strategies.map((strategy, index) => (
                <motion.div
                  key={strategy.id}
                  initial={{ opacity: 0, x: -20 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: index * 0.05 }}
                  onClick={() => setSelectedStrategy(strategy.id)}
                  className={`p-6 cursor-pointer hover:bg-white/5 transition-all ${
                    selectedStrategy === strategy.id ? 'bg-violet-500/10' : ''
                  }`}
                >
                  <div className="flex items-center justify-between">
                    {/* Rank + Tier */}
                    <div className="flex items-center gap-4">
                      <div className="text-3xl font-bold text-gray-600">
                        #{index + 1}
                      </div>
                      
                      <div className={`px-3 py-1 rounded-lg bg-gradient-to-r ${getTierColor(strategy.tier)} text-white font-bold text-sm`}>
                        {strategy.tier}
                      </div>

                      <div>
                        <div className="text-white font-semibold mb-1">
                          {strategy.agent_name}
                        </div>
                        <div className="text-gray-400 text-sm">
                          {strategy.total_predictions} prédictions
                        </div>
                      </div>
                    </div>

                    {/* Métriques */}
                    <div className="flex items-center gap-6">
                      {/* Win rate */}
                      <div className="text-center">
                        <div className="text-gray-400 text-xs mb-1">Win Rate</div>
                        <div className="text-white font-bold text-lg">
                          {strategy.win_rate?.toFixed(1) || '0.0'}%
                        </div>
                      </div>

                      {/* ROI */}
                      <div className="text-center">
                        <div className="text-gray-400 text-xs mb-1">ROI</div>
                        <div className={`font-bold text-lg ${
                          (strategy.roi || 0) > 0 ? 'text-green-400' : 'text-red-400'
                        }`}>
                          {strategy.roi?.toFixed(1) || '0.0'}%
                        </div>
                      </div>

                      {/* Score */}
                      <div className="text-center">
                        <div className="text-gray-400 text-xs mb-1">Score</div>
                        <div className="text-violet-400 font-bold text-lg">
                          {strategy.global_score?.toFixed(1) || '0.0'}
                        </div>
                      </div>

                      {/* Trend */}
                      <div>
                        {getTrendIcon(strategy.trend)}
                      </div>

                      {/* Amélioration disponible */}
                      {strategy.has_improvement_test && (
                        <div className="px-2 py-1 bg-purple-500/20 rounded text-purple-400 text-xs font-semibold">
                          A/B Test
                        </div>
                      )}
                    </div>
                  </div>
                </motion.div>
              ))}
            </div>
          </motion.div>
        </div>

        {/* Détails / Améliorations GPT-4o */}
        <div>
          <motion.div
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            className="bg-white/5 backdrop-blur-lg rounded-xl border border-white/10 overflow-hidden sticky top-8"
          >
            <div className="p-6 border-b border-white/10 bg-gradient-to-r from-purple-500/20 to-violet-500/20">
              <h2 className="text-xl font-bold text-white flex items-center gap-2">
                <Brain className="w-5 h-5 text-purple-400" />
                Améliorations GPT-4o
              </h2>
            </div>

            {improvements.length === 0 ? (
              <div className="p-8 text-center text-gray-400">
                <AlertCircle className="w-12 h-12 mx-auto mb-4 opacity-50" />
                <p>Aucune amélioration disponible</p>
                <p className="text-sm mt-2">
                  GPT-4o analysera les échecs automatiquement
                </p>
              </div>
            ) : (
              <div className="p-6 space-y-4">
                {improvements.slice(0, 3).map((improvement) => (
                  <div
                    key={improvement.id}
                    className="p-4 bg-white/5 rounded-lg border border-purple-500/30"
                  >
                    <div className="flex items-center justify-between mb-3">
                      <div className="font-semibold text-white text-sm">
                        {improvement.agent_name}
                      </div>
                      {improvement.ab_test_active ? (
                        <div className="flex items-center gap-1 text-xs text-blue-400">
                          <Clock className="w-3 h-3" />
                          En test
                        </div>
                      ) : improvement.improvement_applied ? (
                        <div className="flex items-center gap-1 text-xs text-green-400">
                          <CheckCircle className="w-3 h-3" />
                          Appliquée
                        </div>
                      ) : (
                        <div className="flex items-center gap-1 text-xs text-yellow-400">
                          <AlertCircle className="w-3 h-3" />
                          Proposée
                        </div>
                      )}
                    </div>

                    <div className="text-gray-400 text-sm mb-3">
                      {improvement.failure_pattern.slice(0, 100)}...
                    </div>

                    <div className="flex items-center justify-between text-xs">
                      <div className="text-gray-500">
                        Seuil: {improvement.baseline_win_rate}% → {improvement.new_threshold}%
                      </div>
                      <button 
                        onClick={() => router.push(`/strategies/improvements/${improvement.id}`)}
                        className="px-3 py-1 bg-violet-500/20 hover:bg-violet-500/30 rounded text-violet-400 font-semibold transition-all flex items-center gap-1"
                      >
                        Détails
                        <ArrowRight className="w-3 h-3" />
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </motion.div>
        </div>
      </div>
    </div>
  );
}
