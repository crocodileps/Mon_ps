'use client';

import { useState, useEffect } from 'react';
import { useRouter, useParams } from 'next/navigation';
import { motion, AnimatePresence } from 'framer-motion';
import {
  ArrowLeft, Activity, TrendingUp, Zap, Target,
  BarChart3, AlertCircle, CheckCircle, Play, Pause,
  Settings, ChevronRight, Loader2, RefreshCw, Info
} from 'lucide-react';

interface Variation {
  id: number;
  name: string;
  description: string;
  enabled_factors: string[];
  use_new_threshold: boolean;
  custom_threshold: number | null;
  traffic_percentage: number;
  is_control: boolean;
  is_active: boolean;
  matches_tested: number;
  wins: number;
  losses: number;
  win_rate: number;
  total_profit: number;
  roi: number;
}

interface BayesianStats {
  alpha: number;
  beta: number;
  expected_win_rate: number;
  confidence_lower: number;
  confidence_upper: number;
}

interface TrafficRecommendation {
  variation_id: number;
  variation_name: string;
  current_alpha: number;
  current_beta: number;
  expected_win_rate: number;
  confidence_interval: [number, number];
  recommended_traffic: number;
}

export default function VariationsFerrariPage() {
  const router = useRouter();
  const params = useParams();
  const improvementId = params.id as string;
  
  const [variations, setVariations] = useState<Variation[]>([]);
  const [recommendations, setRecommendations] = useState<TrafficRecommendation[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  useEffect(() => {
    fetchVariations();
    fetchRecommendations();
  }, [improvementId]);

  const fetchVariations = async () => {
    try {
      const response = await fetch(`http://91.98.131.218:8001/strategies/improvements/${improvementId}/variations`);
      const data = await response.json();
      if (data.success) {
        setVariations(data.variations);
      }
    } catch (error) {
      console.error('Erreur fetch variations:', error);
    } finally {
      setLoading(false);
    }
  };

  const fetchRecommendations = async () => {
    try {
      const response = await fetch(`http://91.98.131.218:8001/ferrari/improvements/${improvementId}/traffic-recommendation`);
      const data = await response.json();
      if (data.success) {
        setRecommendations(data.recommendations);
      }
    } catch (error) {
      console.error('Erreur fetch recommendations:', error);
    }
  };

  const handleRefresh = async () => {
    setRefreshing(true);
    await Promise.all([fetchVariations(), fetchRecommendations()]);
    setRefreshing(false);
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-950 via-slate-900 to-purple-950 flex items-center justify-center">
        <Loader2 className="w-12 h-12 text-purple-400 animate-spin" />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-950 via-slate-900 to-purple-950 p-6">
      {/* Header */}
      <div className="max-w-7xl mx-auto mb-8">
        <motion.div
          initial={{ opacity: 0, y: -20 }}
          animate={{ opacity: 1, y: 0 }}
          className="flex items-center justify-between"
        >
          <div className="flex items-center gap-4">
            <button
              onClick={() => router.back()}
              className="p-2 bg-slate-800/50 hover:bg-slate-700/50 rounded-lg transition-colors"
            >
              <ArrowLeft className="w-5 h-5 text-slate-300" />
            </button>
            <div>
              <h1 className="text-3xl font-black text-transparent bg-clip-text bg-gradient-to-r from-purple-400 via-violet-400 to-purple-600">
                🏎️ FERRARI 2.0 - Variations A/B
              </h1>
              <p className="text-slate-400 mt-1">Thompson Sampling • Multi-Armed Bandit</p>
            </div>
          </div>

          <motion.button
            whileHover={{ scale: 1.05 }}
            whileTap={{ scale: 0.95 }}
            onClick={handleRefresh}
            disabled={refreshing}
            className="px-4 py-2 bg-purple-600/20 hover:bg-purple-600/30 border border-purple-500/30 rounded-lg text-purple-400 font-semibold flex items-center gap-2 transition-all disabled:opacity-50"
          >
            <RefreshCw className={`w-5 h-5 ${refreshing ? 'animate-spin' : ''}`} />
            Actualiser
          </motion.button>
        </motion.div>
      </div>

      <div className="max-w-7xl mx-auto space-y-6">
        {/* Stats Cards */}
        <div className="grid grid-cols-4 gap-4">
          <motion.div
            initial={{ opacity: 0, scale: 0.9 }}
            animate={{ opacity: 1, scale: 1 }}
            className="bg-slate-800/30 backdrop-blur-xl border border-purple-500/20 rounded-xl p-6"
          >
            <div className="flex items-center gap-3 mb-2">
              <Activity className="w-5 h-5 text-purple-400" />
              <span className="text-slate-400 text-sm font-medium">Total Variations</span>
            </div>
            <div className="text-3xl font-black text-white">{variations.length}</div>
          </motion.div>

          <motion.div
            initial={{ opacity: 0, scale: 0.9 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ delay: 0.1 }}
            className="bg-slate-800/30 backdrop-blur-xl border border-green-500/20 rounded-xl p-6"
          >
            <div className="flex items-center gap-3 mb-2">
              <CheckCircle className="w-5 h-5 text-green-400" />
              <span className="text-slate-400 text-sm font-medium">Actives</span>
            </div>
            <div className="text-3xl font-black text-green-400">
              {variations.filter(v => v.is_active).length}
            </div>
          </motion.div>

          <motion.div
            initial={{ opacity: 0, scale: 0.9 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ delay: 0.2 }}
            className="bg-slate-800/30 backdrop-blur-xl border border-blue-500/20 rounded-xl p-6"
          >
            <div className="flex items-center gap-3 mb-2">
              <BarChart3 className="w-5 h-5 text-blue-400" />
              <span className="text-slate-400 text-sm font-medium">Matchs Testés</span>
            </div>
            <div className="text-3xl font-black text-blue-400">
              {variations.reduce((sum, v) => sum + v.matches_tested, 0)}
            </div>
          </motion.div>

          <motion.div
            initial={{ opacity: 0, scale: 0.9 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ delay: 0.3 }}
            className="bg-slate-800/30 backdrop-blur-xl border border-emerald-500/20 rounded-xl p-6"
          >
            <div className="flex items-center gap-3 mb-2">
              <TrendingUp className="w-5 h-5 text-emerald-400" />
              <span className="text-slate-400 text-sm font-medium">Profit Total</span>
            </div>
            <div className="text-3xl font-black text-emerald-400">
              {variations.reduce((sum, v) => sum + (v.total_profit || 0), 0).toFixed(2)}€
            </div>
          </motion.div>
        </div>

        {/* Variations List */}
        <div className="space-y-4">
          <AnimatePresence>
            {variations.map((variation, index) => {
              const recommendation = recommendations.find(r => r.variation_id === variation.id);
              const trafficDiff = recommendation 
                ? recommendation.recommended_traffic - variation.traffic_percentage
                : 0;

              return (
                <motion.div
                  key={variation.id}
                  initial={{ opacity: 0, x: -20 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: index * 0.1 }}
                  className={`bg-slate-800/30 backdrop-blur-xl border rounded-xl p-6 ${
                    variation.is_control 
                      ? 'border-amber-500/50 shadow-lg shadow-amber-500/10'
                      : 'border-slate-700/50'
                  }`}
                >
                  <div className="flex items-start justify-between">
                    {/* Left: Variation Info */}
                    <div className="flex-1">
                      <div className="flex items-center gap-3 mb-3">
                        <h3 className="text-xl font-bold text-white">{variation.name}</h3>
                        
                        {variation.is_control && (
                          <span className="px-3 py-1 bg-amber-500/20 text-amber-400 rounded-full text-xs font-bold border border-amber-500/30">
                            🎯 CONTRÔLE
                          </span>
                        )}
                        
                        <span className={`px-3 py-1 rounded-full text-xs font-bold ${
                          variation.is_active
                            ? 'bg-green-500/20 text-green-400 border border-green-500/30'
                            : 'bg-slate-500/20 text-slate-400 border border-slate-500/30'
                        }`}>
                          {variation.is_active ? '✓ Active' : '✗ Inactive'}
                        </span>
                      </div>

                      <p className="text-slate-400 text-sm mb-4">{variation.description}</p>

                      {/* Facteurs */}
                      {variation.enabled_factors && variation.enabled_factors.length > 0 && (
                        <div className="mb-4">
                          <div className="text-xs text-slate-500 mb-2 flex items-center gap-2">
                            <Target className="w-3 h-3" />
                            Facteurs activés ({variation.enabled_factors.length})
                          </div>
                          <div className="flex flex-wrap gap-2">
                            {variation.enabled_factors.map((factor, i) => (
                              <span
                                key={i}
                                className="px-2 py-1 bg-purple-500/10 text-purple-300 rounded text-xs border border-purple-500/20"
                              >
                                {factor}
                              </span>
                            ))}
                          </div>
                        </div>
                      )}

                      {/* Stats Performance */}
                      <div className="grid grid-cols-5 gap-4">
                        <div>
                          <div className="text-xs text-slate-500 mb-1">Matchs</div>
                          <div className="text-lg font-bold text-white">{variation.matches_tested}</div>
                        </div>
                        <div>
                          <div className="text-xs text-slate-500 mb-1">Victoires</div>
                          <div className="text-lg font-bold text-green-400">{variation.wins}</div>
                        </div>
                        <div>
                          <div className="text-xs text-slate-500 mb-1">Win Rate</div>
                          <div className="text-lg font-bold text-blue-400">
                            {variation.win_rate?.toFixed(1) || 0}%
                          </div>
                        </div>
                        <div>
                          <div className="text-xs text-slate-500 mb-1">Profit</div>
                          <div className={`text-lg font-bold ${
                            (variation.total_profit || 0) >= 0 ? 'text-emerald-400' : 'text-red-400'
                          }`}>
                            {(variation.total_profit || 0).toFixed(2)}€
                          </div>
                        </div>
                        <div>
                          <div className="text-xs text-slate-500 mb-1">ROI</div>
                          <div className={`text-lg font-bold ${
                            (variation.roi || 0) >= 0 ? 'text-emerald-400' : 'text-red-400'
                          }`}>
                            {(variation.roi || 0).toFixed(1)}%
                          </div>
                        </div>
                      </div>
                    </div>

                    {/* Right: Bayesian Stats */}
                    {recommendation && (
                      <div className="ml-6 w-64 bg-slate-900/50 rounded-lg p-4 border border-purple-500/20">
                        <div className="text-xs text-purple-400 mb-3 font-bold uppercase tracking-wider">
                          Thompson Sampling
                        </div>
                        
                        <div className="space-y-3">
                          <div>
                            <div className="text-xs text-slate-500 mb-1">Beta(α, β)</div>
                            <div className="text-sm font-mono text-white">
                              ({recommendation.current_alpha.toFixed(1)}, {recommendation.current_beta.toFixed(1)})
                            </div>
                          </div>

                          <div>
                            <div className="text-xs text-slate-500 mb-1">Expected WR</div>
                            <div className="text-2xl font-black text-purple-400">
                              {recommendation.expected_win_rate.toFixed(1)}%
                            </div>
                          </div>

                          <div>
                            <div className="text-xs text-slate-500 mb-1">IC 95%</div>
                            <div className="text-xs font-mono text-slate-300">
                              [{(recommendation.confidence_interval[0] * 100).toFixed(1)}%, {(recommendation.confidence_interval[1] * 100).toFixed(1)}%]
                            </div>
                          </div>

                          <div className="pt-3 border-t border-slate-700">
                            <div className="text-xs text-slate-500 mb-2">Allocation Trafic</div>
                            <div className="flex items-center justify-between mb-1">
                              <span className="text-xs text-slate-400">Actuel</span>
                              <span className="text-sm font-bold text-white">{variation.traffic_percentage}%</span>
                            </div>
                            <div className="flex items-center justify-between">
                              <span className="text-xs text-slate-400">Recommandé</span>
                              <span className={`text-sm font-bold ${
                                trafficDiff > 0 ? 'text-green-400' : trafficDiff < 0 ? 'text-red-400' : 'text-slate-400'
                              }`}>
                                {recommendation.recommended_traffic.toFixed(1)}%
                                {trafficDiff !== 0 && (
                                  <span className="text-xs ml-1">
                                    ({trafficDiff > 0 ? '+' : ''}{trafficDiff.toFixed(1)}%)
                                  </span>
                                )}
                              </span>
                            </div>
                          </div>
                        </div>
                      </div>
                    )}
                  </div>
                </motion.div>
              );
            })}
          </AnimatePresence>
        </div>

        {/* Info Thompson Sampling */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.5 }}
          className="bg-blue-500/10 border border-blue-500/30 rounded-xl p-4"
        >
          <div className="flex items-start gap-3">
            <Info className="w-5 h-5 text-blue-400 flex-shrink-0 mt-0.5" />
            <div>
              <h4 className="text-blue-400 font-bold mb-2">🧠 Thompson Sampling Actif</h4>
              <p className="text-slate-300 text-sm leading-relaxed">
                Le système alloue automatiquement plus de trafic aux variations performantes. 
                Les paramètres Beta(α, β) s'ajustent après chaque match : α augmente à chaque victoire, 
                β augmente à chaque défaite. L'allocation recommandée est recalculée en temps réel.
              </p>
            </div>
          </div>
        </motion.div>
      </div>
    </div>
  );
}
