'use client';

import { useState, useEffect } from 'react';
import { useRouter, useParams } from 'next/navigation';
import { motion, AnimatePresence } from 'framer-motion';
import {
  ArrowLeft, Activity, TrendingUp, Zap, Target,
  BarChart3, CheckCircle, Loader2, RefreshCw, Info,
  Award, TrendingDown, Brain, Trophy, Medal, Eye,
  AlertTriangle, Lightbulb, PieChart, Calendar,
  ChevronDown, ChevronUp, Filter, X, Check,
  ExternalLink, Crosshair, Shield, Flame, Clock
} from 'lucide-react';

// ================== INTERFACES ==================
interface Variation {
  id: number;
  name: string;
  description: string;
  enabled_factors: string[];
  enabled_adjustments: string[];
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
  bayesian?: {
    alpha: number;
    beta: number;
    expected_win_rate: number;
    confidence_lower: number;
    confidence_upper: number;
  };
}

interface TrafficRecommendation {
  variation_id: number;
  variation_name: string;
  current_alpha: number;
  current_beta: number;
  expected_win_rate: number;
  confidence_interval: [number, number];
  recommended_traffic: number;
  traffic_change: number;
}

interface MonitoringOverview {
  total_variations: number;
  active_variations: number;
  total_signals: number;
  total_wins: number;
  avg_win_rate: number;
  avg_roi: number;
  total_profit: number;
}

interface Match {
  id: number;
  match_id: string;
  predicted_outcome: string;
  confidence: number;
  edge_detected: number;
  kelly_fraction: number;
  was_correct: boolean;
  profit_loss: number;
  predicted_at: string;
  home_team: string | null;
  away_team: string | null;
}

interface Analytics {
  global_stats: {
    total_predictions: number;
    resolved: number;
    wins: number;
    losses: number;
    win_rate: number;
  };
  confidence_breakdown: Array<{
    confidence_level: string;
    total: number;
    wins: number;
    win_rate: number;
    avg_confidence: number;
  }>;
  outcome_breakdown: Array<{
    predicted_outcome: string;
    total: number;
    wins: number;
    win_rate: number;
  }>;
  insights: Array<{
    type: string;
    icon: string;
    title: string;
    description: string;
    recommendation: string;
  }>;
}

interface VariationDetails {
  variation: any;
  assigned_matches: Array<{
    id: number;
    match_id: string;
    home_team: string;
    away_team: string;
    sport: string;
    outcome: string | null;
    profit: number | null;
    assignment_method: string;
    created_at: string;
  }>;
  factor_analysis: Array<{
    factor: string;
    contribution: string;
    impact_score: number;
    matches_influenced: number;
    success_rate: number;
    description: string;
  }>;
  performance_analysis: {
    total_matches: number;
    wins: number;
    losses: number;
    win_rate: number;
    profitability: {
      total_staked: number;
      total_returned: number;
      net_profit: number;
      roi: number;
    };
  };
  comparison_to_baseline: {
    vs_baseline_wr: number;
    vs_baseline_roi: number;
    vs_baseline_profit: number;
    is_better: boolean;
  } | null;
}

// ================== MAIN COMPONENT ==================
export default function VariationsFerrariPage() {
  const router = useRouter();
  const params = useParams();
  const improvementId = params.id as string;

  // Data States
  const [variations, setVariations] = useState<Variation[]>([]);
  const [recommendations, setRecommendations] = useState<TrafficRecommendation[]>([]);
  const [monitoringData, setMonitoringData] = useState<MonitoringOverview | null>(null);
  const [matches, setMatches] = useState<Match[]>([]);
  const [analytics, setAnalytics] = useState<Analytics | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  
  // UI States
  const [activeTab, setActiveTab] = useState<'variations' | 'matches' | 'analytics'>('variations');
  const [matchFilter, setMatchFilter] = useState<'all' | 'win' | 'loss'>('all');
  
  // Modal States
  const [selectedVariation, setSelectedVariation] = useState<Variation | null>(null);
  const [variationDetails, setVariationDetails] = useState<VariationDetails | null>(null);
  const [loadingDetails, setLoadingDetails] = useState(false);

  useEffect(() => {
    fetchAllData();
  }, [improvementId]);

  const fetchAllData = async () => {
    setLoading(true);
    await Promise.all([
      fetchVariations(),
      fetchRecommendations(),
      fetchMonitoringOverview(),
      fetchMatches(),
      fetchAnalytics()
    ]);
    setLoading(false);
  };

  const fetchVariations = async () => {
    try {
      const response = await fetch(`http://91.98.131.218:8001/api/ferrari/improvements/${improvementId}/ferrari-variations`);
      const data = await response.json();
      if (data.success) {
        const sorted = (data.variations || []).sort((a: Variation, b: Variation) => 
          (b.win_rate || 0) - (a.win_rate || 0)
        );
        setVariations(sorted);
      }
    } catch (error) {
      console.error('Erreur fetch variations:', error);
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

  const fetchMatches = async () => {
    try {
      const response = await fetch(`http://91.98.131.218:8001/api/ferrari/matches/history?limit=50`);
      const data = await response.json();
      if (data.success) {
        setMatches(data.matches || []);
      }
    } catch (error) {
      console.error('Erreur fetch matches:', error);
    }
  };

  const fetchAnalytics = async () => {
    try {
      const response = await fetch(`http://91.98.131.218:8001/api/ferrari/matches/analytics`);
      const data = await response.json();
      if (data.success) {
        setAnalytics(data);
      }
    } catch (error) {
      console.error('Erreur fetch analytics:', error);
    }
  };

  const fetchVariationDetails = async (variation: Variation) => {
    setSelectedVariation(variation);
    setLoadingDetails(true);
    try {
      const response = await fetch(`http://91.98.131.218:8001/api/ferrari/variations/${variation.id}/details`);
      const data = await response.json();
      if (data.success) {
        setVariationDetails(data);
      }
    } catch (error) {
      console.error('Erreur fetch variation details:', error);
    } finally {
      setLoadingDetails(false);
    }
  };

  const closeModal = () => {
    setSelectedVariation(null);
    setVariationDetails(null);
  };

  const handleRefresh = async () => {
    setRefreshing(true);
    await fetchAllData();
    setRefreshing(false);
  };

  const getRankIcon = (index: number) => {
    if (index === 0) return <Trophy className="w-5 h-5 text-yellow-400" />;
    if (index === 1) return <Medal className="w-5 h-5 text-slate-300" />;
    if (index === 2) return <Medal className="w-5 h-5 text-amber-600" />;
    return <span className="w-5 h-5 flex items-center justify-center text-slate-500 font-bold">#{index + 1}</span>;
  };

  const getPerformanceColor = (winRate: number) => {
    if (winRate >= 30) return 'from-green-500/20 to-emerald-500/20 border-green-500/40';
    if (winRate >= 20) return 'from-yellow-500/20 to-orange-500/20 border-yellow-500/40';
    if (winRate >= 15) return 'from-orange-500/20 to-red-500/20 border-orange-500/40';
    return 'from-red-500/20 to-pink-500/20 border-red-500/40';
  };

  const filteredMatches = matches.filter(m => {
    if (matchFilter === 'win') return m.was_correct === true;
    if (matchFilter === 'loss') return m.was_correct === false;
    return true;
  });

  if (loading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-950 via-slate-900 to-purple-950 flex items-center justify-center">
        <motion.div animate={{ rotate: 360 }} transition={{ duration: 1, repeat: Infinity, ease: "linear" }}>
          <Loader2 className="w-16 h-16 text-purple-400" />
        </motion.div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-950 via-slate-900 to-purple-950 p-6">
      <div className="max-w-7xl mx-auto">

        {/* Header */}
        <motion.div initial={{ opacity: 0, y: -20 }} animate={{ opacity: 1, y: 0 }} className="flex items-center justify-between mb-8">
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
              <h1 className="text-4xl font-black text-transparent bg-clip-text bg-gradient-to-r from-yellow-400 via-orange-500 to-red-500">
                🏎️ FERRARI 3.0 - DASHBOARD PRO
              </h1>
              <p className="text-slate-400 mt-1 flex items-center gap-2">
                <Brain className="w-4 h-4" />
                {analytics?.global_stats?.total_predictions || 0} prédictions • {analytics?.global_stats?.resolved || 0} résolues • {variations.length} variations
              </p>
            </div>
          </div>
          <motion.button
            whileHover={{ scale: 1.05 }}
            whileTap={{ scale: 0.95 }}
            onClick={handleRefresh}
            disabled={refreshing}
            className="px-6 py-3 bg-gradient-to-r from-purple-600 to-pink-600 rounded-xl font-bold text-white flex items-center gap-2"
          >
            <RefreshCw className={`w-5 h-5 ${refreshing ? 'animate-spin' : ''}`} />
            Actualiser
          </motion.button>
        </motion.div>

        {/* Tabs */}
        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="flex gap-2 mb-6">
          {[
            { id: 'variations', label: 'Variations A/B', icon: Target },
            { id: 'matches', label: 'Historique Matchs', icon: Calendar },
            { id: 'analytics', label: 'Analytics & Insights', icon: PieChart }
          ].map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id as any)}
              className={`flex items-center gap-2 px-5 py-3 rounded-xl font-bold transition-all ${
                activeTab === tab.id
                  ? 'bg-gradient-to-r from-purple-600 to-pink-600 text-white shadow-lg'
                  : 'bg-slate-800/50 text-slate-400 hover:bg-slate-700/50'
              }`}
            >
              <tab.icon className="w-5 h-5" />
              {tab.label}
            </button>
          ))}
        </motion.div>

        {/* Performance Globale */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
          className="mb-8 p-6 bg-gradient-to-r from-slate-800/50 via-purple-900/30 to-slate-800/50 backdrop-blur-xl rounded-2xl border border-purple-500/20"
        >
          <div className="flex items-center gap-3 mb-6">
            <Award className="w-6 h-6 text-yellow-400" />
            <h2 className="text-xl font-bold text-yellow-400">Performance Globale - Agent B</h2>
            <span className="px-3 py-1 bg-green-500/20 text-green-400 text-xs font-bold rounded-full">✓ DONNÉES RÉELLES</span>
          </div>
          <div className="grid grid-cols-5 gap-4">
            <div className="bg-slate-900/50 rounded-xl p-4 border border-slate-700/50">
              <div className="text-xs text-slate-500 mb-1">Prédictions</div>
              <div className="text-2xl font-black text-white">{analytics?.global_stats?.total_predictions || 0}</div>
              <div className="text-xs text-slate-500">{analytics?.global_stats?.resolved || 0} résolues</div>
            </div>
            <div className="bg-slate-900/50 rounded-xl p-4 border border-green-500/30">
              <div className="text-xs text-slate-500 mb-1">Victoires</div>
              <div className="text-2xl font-black text-green-400">{analytics?.global_stats?.wins || 0}</div>
            </div>
            <div className="bg-slate-900/50 rounded-xl p-4 border border-red-500/30">
              <div className="text-xs text-slate-500 mb-1">Défaites</div>
              <div className="text-2xl font-black text-red-400">{analytics?.global_stats?.losses || 0}</div>
            </div>
            <div className="bg-slate-900/50 rounded-xl p-4 border border-purple-500/30">
              <div className="text-xs text-slate-500 mb-1">Win Rate</div>
              <div className="text-2xl font-black text-purple-400">{(analytics?.global_stats?.win_rate || 0).toFixed(1)}%</div>
            </div>
            <div className="bg-slate-900/50 rounded-xl p-4 border border-emerald-500/30">
              <div className="text-xs text-slate-500 mb-1">Profit Total</div>
              <div className={`text-2xl font-black ${(monitoringData?.total_profit || 0) >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                {(monitoringData?.total_profit || 0) >= 0 ? '+' : ''}{(monitoringData?.total_profit || 0).toFixed(0)}€
              </div>
            </div>
          </div>
        </motion.div>

        {/* TAB: VARIATIONS */}
        <AnimatePresence mode="wait">
          {activeTab === 'variations' && (
            <motion.div key="variations" initial={{ opacity: 0, x: -20 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: 20 }}>
              <div className="flex items-center gap-3 mb-4">
                <Target className="w-6 h-6 text-purple-400" />
                <h2 className="text-2xl font-black text-transparent bg-clip-text bg-gradient-to-r from-purple-400 to-pink-400">
                  VARIATIONS A/B - CLASSEMENT
                </h2>
                <span className="text-sm text-slate-400">(Cliquez pour voir les détails)</span>
              </div>

              <div className="space-y-4">
                {variations.map((variation, index) => {
                  const recommendation = recommendations.find(r => r.variation_id === variation.id);
                  const trafficDiff = recommendation ? recommendation.traffic_change : 0;
                  const bayesian = variation.bayesian;

                  return (
                    <motion.div
                      key={variation.id}
                      initial={{ opacity: 0, x: -20 }}
                      animate={{ opacity: 1, x: 0 }}
                      transition={{ delay: 0.05 * index }}
                      onClick={() => fetchVariationDetails(variation)}
                      className={`bg-gradient-to-r ${getPerformanceColor(variation.win_rate)} backdrop-blur-xl rounded-xl p-6 border transition-all hover:scale-[1.01] cursor-pointer group`}
                    >
                      <div className="flex items-start justify-between">
                        <div className="flex-1">
                          <div className="flex items-center gap-3 mb-2">
                            {getRankIcon(index)}
                            <h3 className="text-xl font-bold text-white group-hover:text-yellow-400 transition-colors">{variation.name}</h3>
                            {variation.is_control && (
                              <span className="px-2 py-1 bg-red-500/20 text-red-400 text-xs font-bold rounded-full">🎯 BASELINE</span>
                            )}
                            {variation.is_active && (
                              <span className="px-2 py-1 bg-green-500/20 text-green-400 text-xs font-bold rounded-full flex items-center gap-1">
                                <div className="w-1.5 h-1.5 bg-green-400 rounded-full animate-pulse" /> Active
                              </span>
                            )}
                            {index === 0 && variation.roi > 0 && (
                              <span className="px-2 py-1 bg-yellow-500/20 text-yellow-400 text-xs font-bold rounded-full">⭐ MEILLEURE</span>
                            )}
                            <Eye className="w-4 h-4 text-slate-500 group-hover:text-yellow-400 ml-auto transition-colors" />
                          </div>
                          <p className="text-sm text-slate-400 mb-4">{variation.description}</p>

                          {variation.enabled_factors && variation.enabled_factors.length > 0 && (
                            <div className="flex flex-wrap gap-2 mb-4">
                              {variation.enabled_factors.map((factor, i) => (
                                <span key={i} className="px-2 py-1 bg-slate-700/50 text-slate-300 text-xs rounded-lg">{factor}</span>
                              ))}
                            </div>
                          )}

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
                              <div className={`text-lg font-bold ${variation.win_rate >= 25 ? 'text-green-400' : 'text-yellow-400'}`}>
                                {variation.win_rate.toFixed(1)}%
                              </div>
                            </div>
                            <div>
                              <div className="text-xs text-slate-500 mb-1">Profit</div>
                              <div className={`text-lg font-bold ${variation.total_profit >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                                {variation.total_profit >= 0 ? '+' : ''}{variation.total_profit.toFixed(2)}€
                              </div>
                            </div>
                            <div>
                              <div className="text-xs text-slate-500 mb-1">ROI</div>
                              <div className={`text-lg font-bold ${variation.roi >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                                {variation.roi >= 0 ? '+' : ''}{variation.roi.toFixed(1)}%
                              </div>
                            </div>
                          </div>
                        </div>

                        <div className="ml-6 w-56 bg-slate-900/80 rounded-xl p-4 border border-purple-500/30">
                          <div className="text-xs text-purple-400 mb-3 font-bold uppercase flex items-center gap-2">
                            <Brain className="w-4 h-4" /> Thompson Sampling
                          </div>
                          <div className="space-y-2">
                            <div className="flex justify-between">
                              <span className="text-xs text-slate-500">Beta(α, β)</span>
                              <span className="text-sm font-mono text-white">({bayesian?.alpha?.toFixed(1) || '1.0'}, {bayesian?.beta?.toFixed(1) || '1.0'})</span>
                            </div>
                            <div>
                              <div className="text-xs text-slate-500">Expected WR</div>
                              <div className="text-xl font-black text-purple-400">{(bayesian?.expected_win_rate || 50).toFixed(1)}%</div>
                            </div>
                            <div className="pt-2 border-t border-slate-700">
                              <div className="flex justify-between">
                                <span className="text-xs text-slate-400">Trafic</span>
                                <span className="text-sm font-bold text-white">{(recommendation?.recommended_traffic || 20).toFixed(0)}%</span>
                              </div>
                              <div className="mt-1 h-1.5 bg-slate-700 rounded-full overflow-hidden">
                                <motion.div
                                  initial={{ width: 0 }}
                                  animate={{ width: `${recommendation?.recommended_traffic || 20}%` }}
                                  className={`h-full rounded-full ${index === 0 ? 'bg-yellow-500' : 'bg-purple-500'}`}
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

          {/* TAB: MATCHES */}
          {activeTab === 'matches' && (
            <motion.div key="matches" initial={{ opacity: 0, x: -20 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: 20 }}>
              <div className="flex items-center justify-between mb-4">
                <div className="flex items-center gap-3">
                  <Calendar className="w-6 h-6 text-blue-400" />
                  <h2 className="text-2xl font-black text-transparent bg-clip-text bg-gradient-to-r from-blue-400 to-cyan-400">
                    HISTORIQUE DES MATCHS
                  </h2>
                </div>
                <div className="flex gap-2">
                  {[
                    { id: 'all', label: 'Tous', count: matches.length },
                    { id: 'win', label: 'Victoires', count: matches.filter(m => m.was_correct).length },
                    { id: 'loss', label: 'Défaites', count: matches.filter(m => !m.was_correct).length }
                  ].map((filter) => (
                    <button
                      key={filter.id}
                      onClick={() => setMatchFilter(filter.id as any)}
                      className={`px-4 py-2 rounded-lg font-medium transition-all flex items-center gap-2 ${
                        matchFilter === filter.id
                          ? filter.id === 'win' ? 'bg-green-500/20 text-green-400 border border-green-500/50'
                          : filter.id === 'loss' ? 'bg-red-500/20 text-red-400 border border-red-500/50'
                          : 'bg-purple-500/20 text-purple-400 border border-purple-500/50'
                          : 'bg-slate-800/50 text-slate-400 border border-slate-700/50'
                      }`}
                    >
                      {filter.label}
                      <span className="px-2 py-0.5 bg-slate-900/50 rounded text-xs">{filter.count}</span>
                    </button>
                  ))}
                </div>
              </div>

              <div className="bg-slate-800/30 backdrop-blur-xl rounded-xl border border-slate-700/50 overflow-hidden">
                <div className="grid grid-cols-7 gap-4 p-4 bg-slate-900/50 border-b border-slate-700/50 text-xs font-bold text-slate-400 uppercase">
                  <div>Match</div><div>Prédiction</div><div>Confiance</div><div>Edge</div><div>Kelly</div><div>Résultat</div><div>P&L</div>
                </div>
                <div className="max-h-[400px] overflow-y-auto">
                  {filteredMatches.map((match, index) => (
                    <motion.div
                      key={match.id}
                      initial={{ opacity: 0 }}
                      animate={{ opacity: 1 }}
                      transition={{ delay: 0.02 * index }}
                      className={`grid grid-cols-7 gap-4 p-4 border-b border-slate-700/30 hover:bg-slate-800/50 ${match.was_correct ? 'bg-green-500/5' : 'bg-red-500/5'}`}
                    >
                      <div className="text-white font-medium truncate">{match.home_team || match.match_id.substring(0, 12)}...</div>
                      <div>
                        <span className={`px-2 py-1 rounded text-xs font-bold ${
                          match.predicted_outcome === 'home' ? 'bg-blue-500/20 text-blue-400' :
                          match.predicted_outcome === 'away' ? 'bg-orange-500/20 text-orange-400' : 'bg-purple-500/20 text-purple-400'
                        }`}>{match.predicted_outcome?.toUpperCase()}</span>
                      </div>
                      <div className={`font-mono ${match.confidence >= 50 ? 'text-green-400' : 'text-slate-400'}`}>{match.confidence?.toFixed(0)}%</div>
                      <div className="text-slate-400 font-mono">{((match.edge_detected || 0) * 100).toFixed(1)}%</div>
                      <div className="text-slate-400 font-mono">{((match.kelly_fraction || 0) * 100).toFixed(2)}%</div>
                      <div>{match.was_correct ? <span className="flex items-center gap-1 text-green-400"><Check className="w-4 h-4" /> WIN</span> : <span className="flex items-center gap-1 text-red-400"><X className="w-4 h-4" /> LOSS</span>}</div>
                      <div className={`font-bold ${(match.profit_loss || 0) >= 0 ? 'text-green-400' : 'text-red-400'}`}>{(match.profit_loss || 0) >= 0 ? '+' : ''}{(match.profit_loss || -10).toFixed(0)}€</div>
                    </motion.div>
                  ))}
                </div>
              </div>
            </motion.div>
          )}

          {/* TAB: ANALYTICS */}
          {activeTab === 'analytics' && analytics && (
            <motion.div key="analytics" initial={{ opacity: 0, x: -20 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: 20 }}>
              <div className="flex items-center gap-3 mb-6">
                <PieChart className="w-6 h-6 text-emerald-400" />
                <h2 className="text-2xl font-black text-transparent bg-clip-text bg-gradient-to-r from-emerald-400 to-cyan-400">ANALYTICS & INSIGHTS</h2>
              </div>

              {analytics.insights && analytics.insights.length > 0 && (
                <div className="grid grid-cols-2 gap-4 mb-8">
                  {analytics.insights.map((insight, index) => (
                    <motion.div key={index} initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1 * index }}
                      className="bg-gradient-to-r from-yellow-500/10 to-orange-500/10 rounded-xl p-5 border border-yellow-500/30">
                      <div className="flex items-start gap-3">
                        <div className="text-3xl">{insight.icon}</div>
                        <div>
                          <h4 className="text-lg font-bold text-yellow-400 mb-1">{insight.title}</h4>
                          <p className="text-sm text-slate-300 mb-2">{insight.description}</p>
                          <p className="text-xs text-emerald-400 flex items-center gap-1"><Lightbulb className="w-3 h-3" />{insight.recommendation}</p>
                        </div>
                      </div>
                    </motion.div>
                  ))}
                </div>
              )}

              <div className="grid grid-cols-2 gap-6">
                <div className="bg-slate-800/30 rounded-xl p-6 border border-slate-700/50">
                  <h3 className="text-lg font-bold text-white mb-4 flex items-center gap-2"><Target className="w-5 h-5 text-purple-400" />Win Rate par Confiance</h3>
                  <div className="space-y-3">
                    {analytics.confidence_breakdown.map((item, index) => (
                      <div key={index} className="flex items-center gap-3">
                        <div className="w-32 text-sm text-slate-400 truncate">{item.confidence_level}</div>
                        <div className="flex-1 h-6 bg-slate-700 rounded-full overflow-hidden">
                          <motion.div initial={{ width: 0 }} animate={{ width: `${item.win_rate}%` }} transition={{ duration: 1, delay: 0.1 * index }}
                            className={`h-full rounded-full ${item.win_rate >= 50 ? 'bg-green-500' : item.win_rate >= 25 ? 'bg-yellow-500' : 'bg-red-500'}`} />
                        </div>
                        <div className={`w-16 text-right font-bold ${item.win_rate >= 50 ? 'text-green-400' : 'text-red-400'}`}>{item.win_rate}%</div>
                      </div>
                    ))}
                  </div>
                </div>

                <div className="bg-slate-800/30 rounded-xl p-6 border border-slate-700/50">
                  <h3 className="text-lg font-bold text-white mb-4 flex items-center gap-2"><BarChart3 className="w-5 h-5 text-blue-400" />Win Rate par Type</h3>
                  <div className="space-y-4">
                    {analytics.outcome_breakdown.map((item, index) => (
                      <div key={index} className="flex items-center gap-4">
                        <div className={`w-20 px-3 py-2 rounded-lg text-center font-bold text-sm ${
                          item.predicted_outcome === 'home' ? 'bg-blue-500/20 text-blue-400' :
                          item.predicted_outcome === 'away' ? 'bg-orange-500/20 text-orange-400' : 'bg-purple-500/20 text-purple-400'
                        }`}>{item.predicted_outcome?.toUpperCase()}</div>
                        <div className="flex-1 h-8 bg-slate-700 rounded-full overflow-hidden">
                          <motion.div initial={{ width: 0 }} animate={{ width: `${item.win_rate}%` }} transition={{ duration: 1 }}
                            className={`h-full rounded-full ${item.win_rate >= 40 ? 'bg-green-500' : item.win_rate >= 20 ? 'bg-yellow-500' : 'bg-red-500'}`} />
                        </div>
                        <div className={`w-20 text-right font-bold ${item.win_rate >= 30 ? 'text-green-400' : 'text-red-400'}`}>{item.win_rate}%</div>
                      </div>
                    ))}
                  </div>
                  {analytics.outcome_breakdown.find(o => o.predicted_outcome === 'away' && o.win_rate === 0) && (
                    <div className="mt-4 p-3 bg-red-500/10 rounded-lg border border-red-500/30 flex items-center gap-2">
                      <AlertTriangle className="w-5 h-5 text-red-400" />
                      <span className="text-sm text-red-400">⚠️ Paris AWAY = 0% réussite - Désactiver</span>
                    </div>
                  )}
                </div>
              </div>
            </motion.div>
          )}
        </AnimatePresence>

        {/* ================== MODAL DÉTAILS VARIATION ================== */}
        <AnimatePresence>
          {selectedVariation && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="fixed inset-0 bg-black/80 backdrop-blur-sm z-50 flex items-center justify-center p-4"
              onClick={closeModal}
            >
              <motion.div
                initial={{ scale: 0.9, opacity: 0 }}
                animate={{ scale: 1, opacity: 1 }}
                exit={{ scale: 0.9, opacity: 0 }}
                className="bg-gradient-to-br from-slate-900 via-slate-800 to-purple-900 rounded-2xl border border-purple-500/30 w-full max-w-5xl max-h-[90vh] overflow-hidden shadow-2xl"
                onClick={(e) => e.stopPropagation()}
              >
                {/* Modal Header */}
                <div className="p-6 border-b border-slate-700/50 flex items-center justify-between bg-slate-900/50">
                  <div className="flex items-center gap-4">
                    <div className="p-3 bg-purple-500/20 rounded-xl">
                      <Crosshair className="w-8 h-8 text-purple-400" />
                    </div>
                    <div>
                      <h2 className="text-2xl font-black text-white flex items-center gap-3">
                        {selectedVariation.name}
                        {selectedVariation.is_control && <span className="px-2 py-1 bg-red-500/20 text-red-400 text-xs rounded-full">BASELINE</span>}
                      </h2>
                      <p className="text-slate-400">{selectedVariation.description}</p>
                    </div>
                  </div>
                  <button onClick={closeModal} className="p-2 hover:bg-slate-700/50 rounded-lg transition-colors">
                    <X className="w-6 h-6 text-slate-400" />
                  </button>
                </div>

                {/* Modal Content */}
                <div className="p-6 overflow-y-auto max-h-[calc(90vh-100px)]">
                  {loadingDetails ? (
                    <div className="flex items-center justify-center py-20">
                      <Loader2 className="w-12 h-12 text-purple-400 animate-spin" />
                    </div>
                  ) : variationDetails ? (
                    <div className="space-y-6">
                      {/* Stats Row */}
                      <div className="grid grid-cols-5 gap-4">
                        <div className="bg-slate-800/50 rounded-xl p-4 text-center border border-slate-700/50">
                          <div className="text-3xl font-black text-white">{variationDetails.performance_analysis.total_matches}</div>
                          <div className="text-xs text-slate-400">Matchs Testés</div>
                        </div>
                        <div className="bg-green-500/10 rounded-xl p-4 text-center border border-green-500/30">
                          <div className="text-3xl font-black text-green-400">{variationDetails.performance_analysis.wins}</div>
                          <div className="text-xs text-slate-400">Victoires</div>
                        </div>
                        <div className="bg-red-500/10 rounded-xl p-4 text-center border border-red-500/30">
                          <div className="text-3xl font-black text-red-400">{variationDetails.performance_analysis.losses}</div>
                          <div className="text-xs text-slate-400">Défaites</div>
                        </div>
                        <div className="bg-purple-500/10 rounded-xl p-4 text-center border border-purple-500/30">
                          <div className="text-3xl font-black text-purple-400">{variationDetails.performance_analysis.win_rate}%</div>
                          <div className="text-xs text-slate-400">Win Rate</div>
                        </div>
                        <div className={`rounded-xl p-4 text-center border ${variationDetails.performance_analysis.profitability.net_profit >= 0 ? 'bg-emerald-500/10 border-emerald-500/30' : 'bg-red-500/10 border-red-500/30'}`}>
                          <div className={`text-3xl font-black ${variationDetails.performance_analysis.profitability.net_profit >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                            {variationDetails.performance_analysis.profitability.net_profit >= 0 ? '+' : ''}{variationDetails.performance_analysis.profitability.net_profit}€
                          </div>
                          <div className="text-xs text-slate-400">Profit Net</div>
                        </div>
                      </div>

                      {/* Comparaison Baseline */}
                      {variationDetails.comparison_to_baseline && (
                        <div className={`p-4 rounded-xl border ${variationDetails.comparison_to_baseline.is_better ? 'bg-green-500/10 border-green-500/30' : 'bg-red-500/10 border-red-500/30'}`}>
                          <div className="flex items-center gap-2 mb-2">
                            {variationDetails.comparison_to_baseline.is_better ? <TrendingUp className="w-5 h-5 text-green-400" /> : <TrendingDown className="w-5 h-5 text-red-400" />}
                            <span className="font-bold text-white">Comparaison vs Baseline</span>
                          </div>
                          <div className="grid grid-cols-3 gap-4 text-center">
                            <div>
                              <div className={`text-xl font-bold ${variationDetails.comparison_to_baseline.vs_baseline_wr >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                                {variationDetails.comparison_to_baseline.vs_baseline_wr >= 0 ? '+' : ''}{variationDetails.comparison_to_baseline.vs_baseline_wr}%
                              </div>
                              <div className="text-xs text-slate-400">Win Rate</div>
                            </div>
                            <div>
                              <div className={`text-xl font-bold ${variationDetails.comparison_to_baseline.vs_baseline_roi >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                                {variationDetails.comparison_to_baseline.vs_baseline_roi >= 0 ? '+' : ''}{variationDetails.comparison_to_baseline.vs_baseline_roi}%
                              </div>
                              <div className="text-xs text-slate-400">ROI</div>
                            </div>
                            <div>
                              <div className={`text-xl font-bold ${variationDetails.comparison_to_baseline.vs_baseline_profit >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                                {variationDetails.comparison_to_baseline.vs_baseline_profit >= 0 ? '+' : ''}{variationDetails.comparison_to_baseline.vs_baseline_profit}€
                              </div>
                              <div className="text-xs text-slate-400">Profit</div>
                            </div>
                          </div>
                        </div>
                      )}

                      {/* Facteurs Analysis */}
                      {variationDetails.factor_analysis.length > 0 && (
                        <div className="bg-slate-800/30 rounded-xl p-5 border border-slate-700/50">
                          <h3 className="text-lg font-bold text-white mb-4 flex items-center gap-2">
                            <Flame className="w-5 h-5 text-orange-400" />
                            Analyse des Facteurs
                          </h3>
                          <div className="space-y-3">
                            {variationDetails.factor_analysis.map((factor, index) => (
                              <div key={index} className="flex items-center gap-4 p-3 bg-slate-900/50 rounded-lg">
                                <div className={`w-2 h-10 rounded-full ${
                                  factor.contribution === 'positive' ? 'bg-green-500' :
                                  factor.contribution === 'negative' ? 'bg-red-500' : 'bg-yellow-500'
                                }`} />
                                <div className="flex-1">
                                  <div className="font-medium text-white">{factor.factor}</div>
                                  <div className="text-xs text-slate-400">{factor.description}</div>
                                </div>
                                <div className="text-center px-4">
                                  <div className={`text-lg font-bold ${factor.contribution === 'positive' ? 'text-green-400' : 'text-red-400'}`}>
                                    {factor.impact_score}/10
                                  </div>
                                  <div className="text-xs text-slate-500">Impact</div>
                                </div>
                                <div className="text-center px-4">
                                  <div className="text-lg font-bold text-purple-400">{factor.success_rate}%</div>
                                  <div className="text-xs text-slate-500">Succès</div>
                                </div>
                              </div>
                            ))}
                          </div>
                        </div>
                      )}

                      {/* Matchs Assignés */}
                      {variationDetails.assigned_matches.length > 0 && (
                        <div className="bg-slate-800/30 rounded-xl p-5 border border-slate-700/50">
                          <h3 className="text-lg font-bold text-white mb-4 flex items-center gap-2">
                            <Calendar className="w-5 h-5 text-blue-400" />
                            Matchs Assignés ({variationDetails.assigned_matches.length})
                          </h3>
                          <div className="space-y-2 max-h-60 overflow-y-auto">
                            {variationDetails.assigned_matches.map((match, index) => (
                              <div key={index} className="flex items-center justify-between p-3 bg-slate-900/50 rounded-lg">
                                <div className="flex items-center gap-3">
                                  <Shield className="w-4 h-4 text-slate-500" />
                                  <span className="font-medium text-white">{match.home_team || 'TBD'}</span>
                                  <span className="text-slate-500">vs</span>
                                  <span className="font-medium text-white">{match.away_team || 'TBD'}</span>
                                </div>
                                <div className="flex items-center gap-4">
                                  <span className="text-xs text-slate-400">{match.sport}</span>
                                  <span className={`px-2 py-1 rounded text-xs font-bold ${
                                    match.outcome === 'win' ? 'bg-green-500/20 text-green-400' :
                                    match.outcome === 'loss' ? 'bg-red-500/20 text-red-400' :
                                    'bg-yellow-500/20 text-yellow-400'
                                  }`}>
                                    {match.outcome || 'En attente'}
                                  </span>
                                </div>
                              </div>
                            ))}
                          </div>
                        </div>
                      )}

                      {/* Thompson Sampling Details */}
                      <div className="bg-gradient-to-r from-purple-500/10 to-pink-500/10 rounded-xl p-5 border border-purple-500/30">
                        <h3 className="text-lg font-bold text-white mb-4 flex items-center gap-2">
                          <Brain className="w-5 h-5 text-purple-400" />
                          Paramètres Thompson Sampling
                        </h3>
                        <div className="grid grid-cols-4 gap-4 text-center">
                          <div>
                            <div className="text-2xl font-mono font-bold text-purple-400">α = {variationDetails.variation.alpha?.toFixed(1) || 1}</div>
                            <div className="text-xs text-slate-400">Succès + 1</div>
                          </div>
                          <div>
                            <div className="text-2xl font-mono font-bold text-pink-400">β = {variationDetails.variation.beta?.toFixed(1) || 1}</div>
                            <div className="text-xs text-slate-400">Échecs + 1</div>
                          </div>
                          <div>
                            <div className="text-2xl font-bold text-yellow-400">{variationDetails.variation.expected_win_rate?.toFixed(1) || 50}%</div>
                            <div className="text-xs text-slate-400">Expected WR</div>
                          </div>
                          <div>
                            <div className="text-lg font-bold text-slate-300">
                              [{variationDetails.variation.confidence_lower?.toFixed(0) || 10}% - {variationDetails.variation.confidence_upper?.toFixed(0) || 90}%]
                            </div>
                            <div className="text-xs text-slate-400">IC 95%</div>
                          </div>
                        </div>
                      </div>
                    </div>
                  ) : (
                    <div className="text-center py-20 text-slate-400">Erreur de chargement</div>
                  )}
                </div>
              </motion.div>
            </motion.div>
          )}
        </AnimatePresence>

      </div>
    </div>
  );
}
