'use client';

import { useState, useEffect } from 'react';
import { useRouter, useParams } from 'next/navigation';
import { motion, AnimatePresence } from 'framer-motion';
import {
  ArrowLeft, Activity, TrendingUp, Zap, Target,
  BarChart3, AlertCircle, CheckCircle, Play, Pause,
  Settings, ChevronRight, Loader2, RefreshCw, Info,
  Rocket, Award, Clock, TrendingDown, Brain, Cpu
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

interface CalibratedVariation {
  id: number;
  name: string;
  description: string;
  confidence_threshold: number;
  edge_threshold: number;
  is_active: boolean;
  matches_tested: number;
  wins: number;
  win_rate: number;
  total_profit: number;
  roi: number;
  traffic_percentage?: number;
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
  const [calibratedVariations, setCalibratedVariations] = useState<CalibratedVariation[]>([]);
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
      fetchCalibratedVariations(),
      fetchRecommendations(),
      fetchMonitoringOverview()
    ]);
  };

  const fetchVariations = async () => {
    try {
      const response = await fetch(`http://91.98.131.218:8001/api/ferrari/improvements/${improvementId}/ferrari-variations`);
      const data = await response.json();
      if (data.success) {
        setVariations(data.variations || []);
      }
    } catch (error) {
      console.error('Erreur fetch variations:', error);
    } finally {
      setLoading(false);
    }
  };

  const fetchCalibratedVariations = async () => {
    try {
      const response = await fetch(`http://91.98.131.218:8001/api/ferrari/improvements/${improvementId}/calibrated-variations`);
      const data = await response.json();
      if (data.success) {
        setCalibratedVariations(data.variations || []);
      }
    } catch (error) {
      console.error('Erreur fetch calibrated variations:', error);
    }
  };

  const fetchRecommendations = async () => {
    try {
      const response = await fetch(`http://91.98.131.218:8001/api/ferrari/improvements/${improvementId}/traffic-recommendation`);
      const data = await response.json();
      if (data.success) {
        setRecommendations(data.recommendations || []);
      }
    } catch (error) {
      console.error('Erreur fetch recommendations:', error);
    }
  };

  const fetchMonitoringOverview = async () => {
    try {
      const response = await fetch(`http://91.98.131.218:8001/api/ferrari/monitoring/overview`);
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

  // Séparer variations originales et calibrées
  const originalVariations = variations.filter(v => !v.name?.includes('CAL'));
  const allCalibratedVariations = calibratedVariations.length > 0 
    ? calibratedVariations 
    : variations.filter(v => v.name?.includes('CAL'));

  // Stats globales
  const totalVariations = variations.length + calibratedVariations.length;
  const activeVariations = variations.filter(v => v.is_active).length + calibratedVariations.filter(v => v.is_active).length;
  const totalMatches = variations.reduce((sum, v) => sum + (v.matches_tested || 0), 0) + calibratedVariations.reduce((sum, v) => sum + (v.matches_tested || 0), 0);
  const totalProfit = variations.reduce((sum, v) => sum + (v.total_profit || 0), 0) + calibratedVariations.reduce((sum, v) => sum + (v.total_profit || 0), 0);
  const avgWinRate = monitoringData?.avg_win_rate || 0;
  const avgROI = monitoringData?.avg_roi || 0;

  if (loading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-950 via-slate-900 to-purple-950 flex items-center justify-center">
        <motion.div
          animate={{ rotate: 360 }}
          transition={{ duration: 1, repeat: Infinity, ease: "linear" }}
        >
          <Loader2 className="w-16 h-16 text-purple-400" />
        </motion.div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-950 via-slate-900 to-purple-950 p-6">
      <div className="max-w-7xl mx-auto">
        
        {/* Header Futuriste */}
        <motion.div
          initial={{ opacity: 0, y: -20 }}
          animate={{ opacity: 1, y: 0 }}
          className="flex items-center justify-between mb-8"
        >
          <div className="flex items-center gap-4">
            <motion.button
              whileHover={{ scale: 1.1, x: -5 }}
              whileTap={{ scale: 0.95 }}
              onClick={() => router.push('/strategies/manage')}
              className="p-3 bg-slate-800/50 hover:bg-slate-700/50 rounded-xl border border-slate-700/50 transition-all"
            >
              <ArrowLeft className="w-5 h-5 text-slate-400" />
            </motion.button>
            <div>
              <h1 className="text-4xl font-black text-transparent bg-clip-text bg-gradient-to-r from-yellow-400 via-orange-500 to-red-500 flex items-center gap-3">
                🏎️ FERRARI 3.0 - AUTO-CALIBRATED
              </h1>
              <p className="text-slate-400 mt-1 flex items-center gap-2">
                <Brain className="w-4 h-4" />
                Thompson Sampling • Multi-Armed Bandit • AI-Powered
              </p>
            </div>
          </div>
          <motion.button
            whileHover={{ scale: 1.05 }}
            whileTap={{ scale: 0.95 }}
            onClick={handleRefresh}
            disabled={refreshing}
            className="px-6 py-3 bg-gradient-to-r from-purple-600 to-pink-600 hover:from-purple-500 hover:to-pink-500 rounded-xl font-bold text-white flex items-center gap-2 shadow-lg shadow-purple-500/25"
          >
            <RefreshCw className={`w-5 h-5 ${refreshing ? 'animate-spin' : ''}`} />
            Actualiser
          </motion.button>
        </motion.div>

        {/* Performance Globale - Cards Premium */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
          className="mb-8 p-6 bg-gradient-to-r from-slate-800/50 via-purple-900/30 to-slate-800/50 backdrop-blur-xl rounded-2xl border border-purple-500/20"
        >
          <div className="flex items-center gap-3 mb-6">
            <div className="p-2 bg-yellow-500/20 rounded-lg">
              <Award className="w-6 h-6 text-yellow-400" />
            </div>
            <h2 className="text-xl font-bold text-yellow-400">Performance Globale</h2>
          </div>
          
          <div className="grid grid-cols-4 gap-6">
            <div className="bg-slate-900/50 rounded-xl p-4 border border-slate-700/50">
              <div className="text-xs text-slate-500 mb-1">Signaux Détectés</div>
              <div className="text-3xl font-black text-white">{monitoringData?.total_signals || totalMatches}</div>
            </div>
            <div className="bg-slate-900/50 rounded-xl p-4 border border-slate-700/50">
              <div className="text-xs text-slate-500 mb-1">Victoires</div>
              <div className="text-3xl font-black text-green-400">{monitoringData?.total_wins || 0}</div>
            </div>
            <div className="bg-slate-900/50 rounded-xl p-4 border border-slate-700/50">
              <div className="text-xs text-slate-500 mb-1">Win Rate Moyen</div>
              <div className="text-3xl font-black text-purple-400">{avgWinRate.toFixed(1)}%</div>
            </div>
            <div className="bg-slate-900/50 rounded-xl p-4 border border-slate-700/50">
              <div className="text-xs text-slate-500 mb-1">ROI Moyen</div>
              <div className={`text-3xl font-black ${avgROI >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                {avgROI.toFixed(1)}%
              </div>
            </div>
          </div>
        </motion.div>

        {/* Stats Cards Secondaires */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2 }}
          className="grid grid-cols-4 gap-4 mb-8"
        >
          <div className="bg-slate-800/30 backdrop-blur-xl rounded-xl p-4 border border-slate-700/50">
            <div className="flex items-center gap-2 mb-2">
              <Activity className="w-4 h-4 text-purple-400" />
              <span className="text-xs text-slate-400">Total Variations</span>
            </div>
            <div className="text-2xl font-black text-white">{totalVariations}</div>
            <div className="text-xs text-slate-500">{originalVariations.length} originales + {allCalibratedVariations.length} calibrées</div>
          </div>
          
          <div className="bg-slate-800/30 backdrop-blur-xl rounded-xl p-4 border border-green-500/20">
            <div className="flex items-center gap-2 mb-2">
              <CheckCircle className="w-4 h-4 text-green-400" />
              <span className="text-xs text-slate-400">Actives</span>
            </div>
            <div className="text-2xl font-black text-green-400">{activeVariations}</div>
          </div>
          
          <div className="bg-slate-800/30 backdrop-blur-xl rounded-xl p-4 border border-blue-500/20">
            <div className="flex items-center gap-2 mb-2">
              <BarChart3 className="w-4 h-4 text-blue-400" />
              <span className="text-xs text-slate-400">Matchs Testés</span>
            </div>
            <div className="text-2xl font-black text-blue-400">{totalMatches}</div>
          </div>
          
          <div className="bg-slate-800/30 backdrop-blur-xl rounded-xl p-4 border border-emerald-500/20">
            <div className="flex items-center gap-2 mb-2">
              <TrendingUp className="w-4 h-4 text-emerald-400" />
              <span className="text-xs text-slate-400">Profit Total</span>
            </div>
            <div className={`text-2xl font-black ${totalProfit >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
              {totalProfit.toFixed(2)}€
            </div>
          </div>
        </motion.div>

        {/* Section Variations AUTO-CALIBRÉES */}
        {allCalibratedVariations.length > 0 && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.3 }}
            className="mb-8"
          >
            <div className="flex items-center gap-3 mb-4">
              <Zap className="w-6 h-6 text-yellow-400" />
              <div className="p-2 bg-yellow-500/20 rounded-lg">
                <Cpu className="w-5 h-5 text-yellow-400" />
              </div>
              <h2 className="text-2xl font-black text-transparent bg-clip-text bg-gradient-to-r from-yellow-400 to-orange-500">
                🤖 VARIATIONS AUTO-CALIBRÉES (IA)
              </h2>
            </div>

            <div className="space-y-4">
              {allCalibratedVariations.map((calibratedVar, index) => {
                const recommendation = recommendations.find(r => 
                  r.variation_name?.toLowerCase().includes(calibratedVar.name?.toLowerCase().split(' - ')[1]?.toLowerCase() || '')
                ) || recommendations[index];
                
                const currentTraffic = calibratedVar.traffic_percentage || 20;
                const trafficDiff = recommendation ? recommendation.recommended_traffic - currentTraffic : 0;

                return (
                  <motion.div
                    key={calibratedVar.id || index}
                    initial={{ opacity: 0, x: -20 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: 0.1 * index }}
                    className="bg-gradient-to-r from-slate-800/60 via-yellow-900/20 to-slate-800/60 backdrop-blur-xl rounded-xl p-6 border border-yellow-500/30 hover:border-yellow-400/50 transition-all"
                  >
                    <div className="flex items-start justify-between">
                      {/* Info Variation */}
                      <div className="flex-1">
                        <div className="flex items-center gap-3 mb-2">
                          <Rocket className="w-5 h-5 text-yellow-400" />
                          <h3 className="text-xl font-bold text-white">{calibratedVar.name}</h3>
                          <span className="px-2 py-1 bg-yellow-500/20 text-yellow-400 text-xs font-bold rounded-full border border-yellow-500/30">
                            🤖 AI-CALIBRATED
                          </span>
                          {calibratedVar.is_active && (
                            <span className="px-2 py-1 bg-green-500/20 text-green-400 text-xs font-bold rounded-full flex items-center gap-1">
                              <div className="w-1.5 h-1.5 bg-green-400 rounded-full animate-pulse" />
                              Active
                            </span>
                          )}
                        </div>
                        <p className="text-sm text-slate-400 mb-4">
                          {calibratedVar.description || `Auto-calibré sur ${calibratedVar.matches_tested || 178} prédictions`}
                        </p>

                        {/* Seuils Auto-ajustés */}
                        <div className="bg-slate-900/50 rounded-lg p-3 mb-4 border border-slate-700/50">
                          <div className="flex items-center gap-2 mb-2">
                            <Settings className="w-4 h-4 text-yellow-400" />
                            <span className="text-xs text-yellow-400 font-bold uppercase">Seuils Auto-Ajustés</span>
                          </div>
                          <div className="flex gap-6">
                            <div>
                              <span className="text-xs text-slate-500">Confidence:</span>
                              <span className="text-sm text-white ml-2 font-mono">≥{(calibratedVar.confidence_threshold || 40)}%</span>
                            </div>
                            <div>
                              <span className="text-xs text-slate-500">Edge:</span>
                              <span className="text-sm text-green-400 ml-2 font-mono">≥{(calibratedVar.edge_threshold || 1).toFixed(2)}%</span>
                            </div>
                          </div>
                        </div>

                        {/* Stats Performance */}
                        <div className="grid grid-cols-5 gap-4">
                          <div>
                            <div className="text-xs text-slate-500 mb-1">Matchs</div>
                            <div className="text-lg font-bold text-white">{calibratedVar.matches_tested || 0}</div>
                          </div>
                          <div>
                            <div className="text-xs text-slate-500 mb-1">Victoires</div>
                            <div className="text-lg font-bold text-green-400">{calibratedVar.wins || 0}</div>
                          </div>
                          <div>
                            <div className="text-xs text-slate-500 mb-1">Win Rate</div>
                            <div className="text-lg font-bold text-purple-400">{(calibratedVar.win_rate || 0).toFixed(1)}%</div>
                          </div>
                          <div>
                            <div className="text-xs text-slate-500 mb-1">Profit</div>
                            <div className={`text-lg font-bold ${(calibratedVar.total_profit || 0) >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                              {(calibratedVar.total_profit || 0).toFixed(2)}€
                            </div>
                          </div>
                          <div>
                            <div className="text-xs text-slate-500 mb-1">ROI</div>
                            <div className={`text-lg font-bold ${(calibratedVar.roi || 0) >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                              {(calibratedVar.roi || 0).toFixed(1)}%
                            </div>
                          </div>
                        </div>
                      </div>

                      {/* Thompson Sampling Stats - COMPLET */}
                      <div className="ml-6 w-72 bg-slate-900/80 rounded-xl p-5 border border-yellow-500/30 shadow-lg shadow-yellow-500/10">
                        <div className="text-xs text-yellow-400 mb-4 font-bold uppercase tracking-wider flex items-center gap-2">
                          <Brain className="w-4 h-4" />
                          Thompson Sampling
                        </div>
                        <div className="space-y-4">
                          <div>
                            <div className="text-xs text-slate-500 mb-1">Beta(α, β)</div>
                            <div className="text-lg font-mono text-white">
                              ({recommendation?.current_alpha?.toFixed(1) || '1.0'}, {recommendation?.current_beta?.toFixed(1) || '1.0'})
                            </div>
                          </div>
                          <div>
                            <div className="text-xs text-slate-500 mb-1">Expected WR</div>
                            <div className="text-3xl font-black text-yellow-400">
                              {recommendation?.expected_win_rate?.toFixed(1) || '50.0'}%
                            </div>
                          </div>
                          <div>
                            <div className="text-xs text-slate-500 mb-1">IC 95%</div>
                            <div className="text-sm font-mono text-slate-300">
                              [{((recommendation?.confidence_interval?.[0] || 0.025) * 100).toFixed(1)}%, {((recommendation?.confidence_interval?.[1] || 0.975) * 100).toFixed(1)}%]
                            </div>
                          </div>
                          <div className="pt-4 border-t border-slate-700">
                            <div className="text-xs text-slate-500 mb-3">Allocation Trafic</div>
                            <div className="flex items-center justify-between mb-2">
                              <span className="text-xs text-slate-400">Actuel</span>
                              <span className="text-lg font-bold text-white">{currentTraffic}%</span>
                            </div>
                            <div className="flex items-center justify-between">
                              <span className="text-xs text-slate-400">Recommandé</span>
                              <span className={`text-lg font-bold ${trafficDiff > 0 ? 'text-green-400' : trafficDiff < 0 ? 'text-red-400' : 'text-slate-400'}`}>
                                {recommendation?.recommended_traffic?.toFixed(1) || currentTraffic.toFixed(1)}%
                                {trafficDiff !== 0 && (
                                  <span className="text-xs ml-1">
                                    ({trafficDiff > 0 ? '+' : ''}{trafficDiff.toFixed(1)}%)
                                  </span>
                                )}
                              </span>
                            </div>
                            {/* Barre de progression */}
                            <div className="mt-3 h-2 bg-slate-700 rounded-full overflow-hidden">
                              <motion.div 
                                initial={{ width: 0 }}
                                animate={{ width: `${recommendation?.recommended_traffic || currentTraffic}%` }}
                                transition={{ duration: 1, ease: "easeOut" }}
                                className="h-full bg-gradient-to-r from-yellow-500 to-orange-500 rounded-full"
                              />
                            </div>
                          </div>
                        </div>
                      </div>
                    </div>
                  </motion.div>
                );
              })}
            </div>
          </motion.div>
        )}

        {/* Section Variations ORIGINALES */}
        {originalVariations.length > 0 && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.4 }}
            className="mb-8"
          >
            <div className="flex items-center gap-3 mb-4">
              <Target className="w-6 h-6 text-purple-400" />
              <h2 className="text-2xl font-black text-transparent bg-clip-text bg-gradient-to-r from-purple-400 to-pink-400">
                VARIATIONS ORIGINALES
              </h2>
            </div>

            <div className="space-y-4">
              {originalVariations.map((variation, index) => {
                const recommendation = recommendations.find(r => r.variation_id === variation.id);
                const trafficDiff = recommendation ? recommendation.recommended_traffic - variation.traffic_percentage : 0;

                return (
                  <motion.div
                    key={variation.id}
                    initial={{ opacity: 0, x: -20 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: 0.1 * index }}
                    className={`bg-slate-800/40 backdrop-blur-xl rounded-xl p-6 border transition-all ${
                      variation.is_control 
                        ? 'border-red-500/30 hover:border-red-400/50' 
                        : 'border-purple-500/30 hover:border-purple-400/50'
                    }`}
                  >
                    <div className="flex items-start justify-between">
                      {/* Info Variation */}
                      <div className="flex-1">
                        <div className="flex items-center gap-3 mb-2">
                          <h3 className="text-xl font-bold text-white">{variation.name}</h3>
                          {variation.is_control && (
                            <span className="px-2 py-1 bg-red-500/20 text-red-400 text-xs font-bold rounded-full border border-red-500/30">
                              🎯 CONTRÔLE
                            </span>
                          )}
                          {variation.is_active && (
                            <span className="px-2 py-1 bg-green-500/20 text-green-400 text-xs font-bold rounded-full flex items-center gap-1">
                              <div className="w-1.5 h-1.5 bg-green-400 rounded-full animate-pulse" />
                              Active
                            </span>
                          )}
                        </div>
                        <p className="text-sm text-slate-400 mb-4">{variation.description}</p>

                        {/* Facteurs Activés */}
                        {variation.enabled_factors && variation.enabled_factors.length > 0 && (
                          <div className="flex flex-wrap gap-2 mb-4">
                            {variation.enabled_factors.map((factor, i) => (
                              <span key={i} className="px-2 py-1 bg-slate-700/50 text-slate-300 text-xs rounded-lg">
                                {factor}
                              </span>
                            ))}
                          </div>
                        )}

                        {/* Stats Performance */}
                        <div className="grid grid-cols-5 gap-4">
                          <div>
                            <div className="text-xs text-slate-500 mb-1">Matchs</div>
                            <div className="text-lg font-bold text-white">{variation.matches_tested || 0}</div>
                          </div>
                          <div>
                            <div className="text-xs text-slate-500 mb-1">Victoires</div>
                            <div className="text-lg font-bold text-green-400">{variation.wins || 0}</div>
                          </div>
                          <div>
                            <div className="text-xs text-slate-500 mb-1">Win Rate</div>
                            <div className="text-lg font-bold text-purple-400">{(variation.win_rate || 0).toFixed(1)}%</div>
                          </div>
                          <div>
                            <div className="text-xs text-slate-500 mb-1">Profit</div>
                            <div className={`text-lg font-bold ${(variation.total_profit || 0) >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                              {(variation.total_profit || 0).toFixed(2)}€
                            </div>
                          </div>
                          <div>
                            <div className="text-xs text-slate-500 mb-1">ROI</div>
                            <div className={`text-lg font-bold ${(variation.roi || 0) >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                              {(variation.roi || 0).toFixed(1)}%
                            </div>
                          </div>
                        </div>
                      </div>

                      {/* Thompson Sampling Stats */}
                      {recommendation && (
                        <div className="ml-6 w-72 bg-slate-900/60 rounded-xl p-5 border border-purple-500/30">
                          <div className="text-xs text-purple-400 mb-4 font-bold uppercase tracking-wider flex items-center gap-2">
                            <Brain className="w-4 h-4" />
                            Thompson Sampling
                          </div>
                          <div className="space-y-4">
                            <div>
                              <div className="text-xs text-slate-500 mb-1">Beta(α, β)</div>
                              <div className="text-lg font-mono text-white">
                                ({recommendation.current_alpha.toFixed(1)}, {recommendation.current_beta.toFixed(1)})
                              </div>
                            </div>
                            <div>
                              <div className="text-xs text-slate-500 mb-1">Expected WR</div>
                              <div className="text-3xl font-black text-purple-400">
                                {recommendation.expected_win_rate.toFixed(1)}%
                              </div>
                            </div>
                            <div>
                              <div className="text-xs text-slate-500 mb-1">IC 95%</div>
                              <div className="text-sm font-mono text-slate-300">
                                [{(recommendation.confidence_interval[0] * 100).toFixed(1)}%, {(recommendation.confidence_interval[1] * 100).toFixed(1)}%]
                              </div>
                            </div>
                            <div className="pt-4 border-t border-slate-700">
                              <div className="text-xs text-slate-500 mb-3">Allocation Trafic</div>
                              <div className="flex items-center justify-between mb-2">
                                <span className="text-xs text-slate-400">Actuel</span>
                                <span className="text-lg font-bold text-white">{variation.traffic_percentage}%</span>
                              </div>
                              <div className="flex items-center justify-between">
                                <span className="text-xs text-slate-400">Recommandé</span>
                                <span className={`text-lg font-bold ${trafficDiff > 0 ? 'text-green-400' : trafficDiff < 0 ? 'text-red-400' : 'text-slate-400'}`}>
                                  {recommendation.recommended_traffic.toFixed(1)}%
                                  {trafficDiff !== 0 && (
                                    <span className="text-xs ml-1">
                                      ({trafficDiff > 0 ? '+' : ''}{trafficDiff.toFixed(1)}%)
                                    </span>
                                  )}
                                </span>
                              </div>
                              {/* Barre de progression */}
                              <div className="mt-3 h-2 bg-slate-700 rounded-full overflow-hidden">
                                <motion.div 
                                  initial={{ width: 0 }}
                                  animate={{ width: `${recommendation.recommended_traffic}%` }}
                                  transition={{ duration: 1, ease: "easeOut" }}
                                  className="h-full bg-gradient-to-r from-purple-500 to-pink-500 rounded-full"
                                />
                              </div>
                            </div>
                          </div>
                        </div>
                      )}
                    </div>
                  </motion.div>
                );
              })}
            </div>
          </motion.div>
        )}

        {/* Info Thompson Sampling */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.5 }}
          className="mt-8 p-6 bg-slate-800/30 backdrop-blur-xl rounded-xl border border-slate-700/50"
        >
          <div className="flex items-start gap-4">
            <div className="p-3 bg-purple-500/20 rounded-xl">
              <Info className="w-6 h-6 text-purple-400" />
            </div>
            <div>
              <h3 className="text-lg font-bold text-white mb-2">Comment ça fonctionne ?</h3>
              <p className="text-sm text-slate-400 leading-relaxed">
                <strong className="text-purple-400">Thompson Sampling</strong> : Algorithme Multi-Armed Bandit qui alloue dynamiquement le trafic aux variations les plus performantes.
                Les paramètres <strong className="text-yellow-400">Beta(α, β)</strong> sont mis à jour après chaque résultat pour une optimisation continue.
                L'<strong className="text-green-400">Expected WR</strong> représente le win rate attendu basé sur la distribution bayésienne,
                et l'<strong className="text-blue-400">IC 95%</strong> indique l'intervalle de confiance.
              </p>
            </div>
          </div>
        </motion.div>

      </div>
    </div>
  );
}
