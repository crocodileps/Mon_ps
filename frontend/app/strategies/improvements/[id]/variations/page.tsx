'use client';

import { useState, useEffect } from 'react';
import { useRouter, useParams } from 'next/navigation';
import { motion, AnimatePresence } from 'framer-motion';
import {
  ArrowLeft, Activity, TrendingUp, Zap, Target,
  BarChart3, AlertCircle, CheckCircle, Play, Pause,
  Settings, ChevronRight, Loader2, RefreshCw, Info,
  Rocket, Award, Clock, TrendingDown
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
  config?: any;
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

interface MonitoringOverview {
  total_variations: number;
  active_variations: number;
  variations_tested: number;
  total_signals: number;
  total_wins: number;
  avg_win_rate: number;
  avg_roi: number;
}

export default function VariationsFerrariPage() {
  const router = useRouter();
  const params = useParams();
  const improvementId = params.id as string;

  const [variations, setVariations] = useState<Variation[]>([]);
  const [recommendations, setRecommendations] = useState<TrafficRecommendation[]>([]);
  const [monitoringData, setMonitoringData] = useState<MonitoringOverview | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  useEffect(() => {
    fetchAllData();
  }, [improvementId]);

  const fetchAllData = async () => {
    await Promise.all([
      fetchVariations(),
      fetchRecommendations(),
      fetchMonitoringOverview()
    ]);
  };

  const fetchVariations = async () => {
    try {
      const response = await fetch(`http://91.98.131.218:8001/api/ferrari/improvements/${improvementId}/ferrari-variations`);
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
      const response = await fetch(`http://91.98.131.218:8001/api/ferrari/improvements/${improvementId}/traffic-recommendation`);
      const data = await response.json();
      if (data.success) {
        setRecommendations(data.recommendations);
      }
    } catch (error) {
      console.error('Erreur fetch recommendations:', error);
    }
  };

  const fetchMonitoringOverview = async () => {
    try {
      const response = await fetch('http://91.98.131.218:8001/api/ferrari/monitoring/overview');
      const data = await response.json();
      if (data.success) {
        setMonitoringData(data.overview);
      }
    } catch (error) {
      console.error('Erreur fetch monitoring:', error);
    }
  };

  const handleRefresh = async () => {
    setRefreshing(true);
    await fetchAllData();
    setRefreshing(false);
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-950 via-slate-900 to-purple-950 flex items-center justify-center">
        <div className="text-center">
          <Loader2 className="w-16 h-16 text-purple-400 animate-spin mx-auto mb-4" />
          <p className="text-purple-400 font-bold text-xl">🏎️ Chargement Ferrari 3.0...</p>
        </div>
      </div>
    );
  }

  // Séparer variations originales et calibrées
  const originalVariations = variations.filter(v => v.id <= 10);
  const calibratedVariations = variations.filter(v => v.id > 10);

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
              <h1 className="text-4xl font-black text-transparent bg-clip-text bg-gradient-to-r from-red-500 via-orange-500 to-yellow-500">
                🏎️ FERRARI 3.0 - AUTO-CALIBRATED
              </h1>
              <p className="text-slate-400 mt-1 flex items-center gap-2">
                <Rocket className="w-4 h-4" />
                Thompson Sampling • Multi-Armed Bandit • AI-Powered
              </p>
            </div>
          </div>

          <motion.button
            whileHover={{ scale: 1.05 }}
            whileTap={{ scale: 0.95 }}
            onClick={handleRefresh}
            disabled={refreshing}
            className="px-6 py-3 bg-gradient-to-r from-purple-600 to-pink-600 hover:from-purple-500 hover:to-pink-500 rounded-lg text-white font-bold flex items-center gap-2 transition-all disabled:opacity-50 shadow-lg shadow-purple-500/50"
          >
            <RefreshCw className={`w-5 h-5 ${refreshing ? 'animate-spin' : ''}`} />
            Actualiser
          </motion.button>
        </motion.div>
      </div>

      <div className="max-w-7xl mx-auto space-y-6">
        {/* Monitoring Stats - NOUVEAUX */}
        {monitoringData && (
          <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            className="bg-gradient-to-br from-purple-900/20 to-pink-900/20 backdrop-blur-xl border border-purple-500/30 rounded-2xl p-6"
          >
            <div className="flex items-center gap-3 mb-6">
              <Award className="w-6 h-6 text-yellow-400" />
              <h2 className="text-2xl font-black text-transparent bg-clip-text bg-gradient-to-r from-purple-400 to-pink-400">
                Performance Globale
              </h2>
            </div>
            
            <div className="grid grid-cols-4 gap-4">
              <div className="bg-slate-800/50 rounded-xl p-4">
                <div className="text-xs text-slate-400 mb-2">Signaux Détectés</div>
                <div className="text-3xl font-black text-purple-400">{monitoringData.total_signals}</div>
              </div>
              <div className="bg-slate-800/50 rounded-xl p-4">
                <div className="text-xs text-slate-400 mb-2">Victoires</div>
                <div className="text-3xl font-black text-green-400">{monitoringData.total_wins}</div>
              </div>
              <div className="bg-slate-800/50 rounded-xl p-4">
                <div className="text-xs text-slate-400 mb-2">Win Rate Moyen</div>
                <div className="text-3xl font-black text-blue-400">{monitoringData.avg_win_rate.toFixed(1)}%</div>
              </div>
              <div className="bg-slate-800/50 rounded-xl p-4">
                <div className="text-xs text-slate-400 mb-2">ROI Moyen</div>
                <div className={`text-3xl font-black ${monitoringData.avg_roi >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                  {monitoringData.avg_roi.toFixed(1)}%
                </div>
              </div>
            </div>
          </motion.div>
        )}

        {/* Stats Cards - ORIGINALES */}
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
            <div className="text-xs text-slate-500 mt-1">
              {originalVariations.length} originales + {calibratedVariations.length} calibrées
            </div>
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

        {/* NOUVELLES Variations Calibrées - Section Premium */}
        {calibratedVariations.length > 0 && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="space-y-4"
          >
            <div className="flex items-center gap-3">
              <Zap className="w-6 h-6 text-yellow-400" />
              <h2 className="text-2xl font-black text-transparent bg-clip-text bg-gradient-to-r from-yellow-400 to-orange-400">
                🤖 VARIATIONS AUTO-CALIBRÉES (IA)
              </h2>
            </div>
            
            {calibratedVariations.map((variation, index) => {
              const recommendation = recommendations.find(r => r.variation_id === variation.id);
              
              return (
                <motion.div
                  key={variation.id}
                  initial={{ opacity: 0, x: -20 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: index * 0.05 }}
                  className="bg-gradient-to-r from-yellow-900/20 to-orange-900/20 backdrop-blur-xl border-2 border-yellow-500/50 rounded-xl p-6 shadow-lg shadow-yellow-500/20"
                >
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <div className="flex items-center gap-3 mb-3">
                        <Rocket className="w-5 h-5 text-yellow-400" />
                        <h3 className="text-xl font-bold text-yellow-400">{variation.name}</h3>
                        <span className="px-3 py-1 bg-yellow-500/20 text-yellow-300 rounded-full text-xs font-bold border border-yellow-500/30">
                          🤖 AI-CALIBRATED
                        </span>
                        {variation.is_active && (
                          <span className="px-3 py-1 bg-green-500/20 text-green-400 rounded-full text-xs font-bold border border-green-500/30">
                            ✓ Active
                          </span>
                        )}
                      </div>

                      <p className="text-slate-300 text-sm mb-4">{variation.description}</p>

                      {/* Seuils Auto-calibrés */}
                      {variation.config?.seuils && (
                        <div className="mb-4 bg-slate-900/50 rounded-lg p-3 border border-yellow-500/20">
                          <div className="text-xs text-yellow-400 mb-2 font-bold">⚙️ SEUILS AUTO-AJUSTÉS</div>
                          <div className="flex gap-4 text-sm">
                            <div>
                              <span className="text-slate-400">Confidence:</span>
                              <span className="text-yellow-300 font-mono ml-2">
                                ≥{(variation.config.seuils.confidence_threshold * 100).toFixed(0)}%
                              </span>
                            </div>
                            <div>
                              <span className="text-slate-400">Edge:</span>
                              <span className="text-yellow-300 font-mono ml-2">
                                ≥{(variation.config.seuils.min_spread * 100).toFixed(2)}%
                              </span>
                            </div>
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

                    {/* Bayesian Stats */}
                    {recommendation && (
                      <div className="ml-6 w-64 bg-slate-900/80 rounded-lg p-4 border border-yellow-500/30">
                        <div className="text-xs text-yellow-400 mb-3 font-bold uppercase tracking-wider">
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
                            <div className="text-2xl font-black text-yellow-400">
                              {recommendation.expected_win_rate.toFixed(1)}%
                            </div>
                          </div>
                          <div>
                            <div className="text-xs text-slate-500 mb-1">IC 95%</div>
                            <div className="text-xs font-mono text-slate-300">
                              [{(recommendation.confidence_interval[0] * 100).toFixed(1)}%, {(recommendation.confidence_interval[1] * 100).toFixed(1)}%]
                            </div>
                          </div>
                        </div>
                      </div>
                    )}
                  </div>
                </motion.div>
              );
            })}
          </motion.div>
        )}

        {/* Variations Originales */}
        <div className="space-y-4">
          <div className="flex items-center gap-3">
            <Target className="w-6 h-6 text-purple-400" />
            <h2 className="text-2xl font-black text-transparent bg-clip-text bg-gradient-to-r from-purple-400 to-pink-400">
              VARIATIONS ORIGINALES
            </h2>
          </div>

          <AnimatePresence>
            {originalVariations.map((variation, index) => {
              const recommendation = recommendations.find(r => r.variation_id === variation.id);
              const trafficDiff = recommendation
                ? recommendation.recommended_traffic - variation.traffic_percentage
                : 0;

              return (
                <motion.div
                  key={variation.id}
                  initial={{ opacity: 0, x: -20 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: index * 0.05 }}
                  className={`bg-slate-800/30 backdrop-blur-xl border rounded-xl p-6 ${
                    variation.is_control
                      ? 'border-amber-500/50 shadow-lg shadow-amber-500/10'
                      : 'border-slate-700/50'
                  }`}
                >
                  <div className="flex items-start justify-between">
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

                    {/* Bayesian Stats */}
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
          className="bg-gradient-to-r from-blue-900/20 to-cyan-900/20 border border-blue-500/30 rounded-xl p-6"
        >
          <div className="flex items-start gap-3">
            <Info className="w-6 h-6 text-blue-400 flex-shrink-0 mt-0.5" />
            <div>
              <h4 className="text-blue-400 font-bold mb-2 text-lg">🧠 Ferrari 3.0 - Système Hybride Intelligent</h4>
              <p className="text-slate-300 text-sm leading-relaxed mb-3">
                <strong className="text-yellow-400">Variations Auto-Calibrées (IA)</strong> : Seuils ajustés automatiquement via analyse statistique de 178 prédictions historiques. 
                Les paramètres s'adaptent en temps réel aux conditions du marché.
              </p>
              <p className="text-slate-300 text-sm leading-relaxed">
                <strong className="text-purple-400">Thompson Sampling</strong> : Algorithme Multi-Armed Bandit qui alloue dynamiquement le trafic aux variations performantes. 
                Beta(α, β) mis à jour après chaque résultat pour optimisation continue.
              </p>
            </div>
          </div>
        </motion.div>
      </div>
    </div>
  );
}
