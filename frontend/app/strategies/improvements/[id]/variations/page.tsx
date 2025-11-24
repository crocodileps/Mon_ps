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
  ExternalLink, Crosshair, Shield, Flame, Clock,
  ChevronRight, AlertCircle, Home, Users, Scale
} from 'lucide-react';

// ================== INTERFACES ==================
interface Variation {
  id: number;
  name: string;
  description: string;
  enabled_factors: string[];
  traffic_percentage: number;
  is_control: boolean;
  is_active: boolean;
  matches_tested: number;
  wins: number;
  losses: number;
  win_rate: number;
  total_profit: number;
  roi: number;
  bayesian?: { alpha: number; beta: number; expected_win_rate: number; confidence_lower: number; confidence_upper: number; };
}

interface TrafficRecommendation {
  variation_id: number;
  recommended_traffic: number;
  traffic_change: number;
  current_alpha: number;
  current_beta: number;
  expected_win_rate: number;
  confidence_interval: [number, number];
}

interface MonitoringOverview {
  total_signals: number;
  total_wins: number;
  avg_win_rate: number;
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
  home_team: string | null;
}

interface Analytics {
  global_stats: { total_predictions: number; resolved: number; wins: number; losses: number; win_rate: number; };
  confidence_breakdown: Array<{ confidence_level: string; total: number; wins: number; win_rate: number; }>;
  outcome_breakdown: Array<{ predicted_outcome: string; total: number; wins: number; win_rate: number; }>;
  insights: Array<{ icon: string; title: string; description: string; recommendation: string; }>;
}

interface FactorAnalysis {
  factor: string;
  display_name: string;
  status: 'success' | 'failure' | 'warning' | 'neutral';
  impact_score: number;
  contribution: string;
  detail: string;
  icon: string;
}

interface DetailedMatch {
  id: number;
  match_id: string;
  home_team: string;
  away_team: string;
  sport: string;
  result: 'WIN' | 'LOSS';
  was_correct: boolean;
  score: string;
  confidence: number;
  edge: number;
  profit_loss: number;
  odds: number;
  date: string;
  predicted_outcome: string;
  factors_analysis: FactorAnalysis[];
  summary: { total_positive: number; total_negative: number; avg_impact: number; };
  lesson: string;
}

interface MatchesDetailed {
  variation_name: string;
  enabled_factors: string[];
  stats: { total_matches: number; wins: number; losses: number; win_rate: number; };
  matches: DetailedMatch[];
}

interface VariationDetails {
  variation: any;
  assigned_matches: Array<{ id: number; match_id: string; home_team: string; away_team: string; sport: string; outcome: string | null; created_at: string; }>;
  factor_analysis: Array<{ factor: string; contribution: string; impact_score: number; success_rate: number; description: string; }>;
  performance_analysis: { total_matches: number; wins: number; losses: number; win_rate: number; profitability: { net_profit: number; roi: number; }; };
  comparison_to_baseline: { vs_baseline_wr: number; vs_baseline_roi: number; vs_baseline_profit: number; is_better: boolean; } | null;
}

// ================== MAIN COMPONENT ==================
export default function VariationsFerrariPage() {
  const router = useRouter();
  const params = useParams();
  const improvementId = params.id as string;

  const [variations, setVariations] = useState<Variation[]>([]);
  const [recommendations, setRecommendations] = useState<TrafficRecommendation[]>([]);
  const [monitoringData, setMonitoringData] = useState<MonitoringOverview | null>(null);
  const [matches, setMatches] = useState<Match[]>([]);
  const [analytics, setAnalytics] = useState<Analytics | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  
  const [activeTab, setActiveTab] = useState<'variations' | 'matches' | 'analytics'>('variations');
  const [matchFilter, setMatchFilter] = useState<'all' | 'win' | 'loss'>('all');
  
  // Modal States
  const [selectedVariation, setSelectedVariation] = useState<Variation | null>(null);
  const [variationDetails, setVariationDetails] = useState<VariationDetails | null>(null);
  const [matchesDetailed, setMatchesDetailed] = useState<MatchesDetailed | null>(null);
  const [loadingDetails, setLoadingDetails] = useState(false);
  const [expandedMatch, setExpandedMatch] = useState<number | null>(null);
  const [detailFilter, setDetailFilter] = useState<'all' | 'win' | 'loss'>('all');
  const [modalTab, setModalTab] = useState<'overview' | 'matches'>('overview');

  useEffect(() => { fetchAllData(); }, [improvementId]);

  const fetchAllData = async () => {
    setLoading(true);
    await Promise.all([fetchVariations(), fetchRecommendations(), fetchMonitoringOverview(), fetchMatches(), fetchAnalytics()]);
    setLoading(false);
  };

  const fetchVariations = async () => {
    try {
      const response = await fetch(`http://91.98.131.218:8001/api/ferrari/improvements/${improvementId}/ferrari-variations`);
      const data = await response.json();
      if (data.success) setVariations((data.variations || []).sort((a: Variation, b: Variation) => (b.win_rate || 0) - (a.win_rate || 0)));
    } catch (error) { console.error('Erreur:', error); }
  };

  const fetchRecommendations = async () => {
    try {
      const response = await fetch(`http://91.98.131.218:8001/api/ferrari/improvements/${improvementId}/traffic-recommendation`);
      const data = await response.json();
      if (data.success) setRecommendations(data.recommendations || []);
    } catch (error) { console.error('Erreur:', error); }
  };

  const fetchMonitoringOverview = async () => {
    try {
      const response = await fetch(`http://91.98.131.218:8001/api/ferrari/monitoring/overview`);
      const data = await response.json();
      if (data.success) setMonitoringData(data.overview);
    } catch (error) { console.error('Erreur:', error); }
  };

  const fetchMatches = async () => {
    try {
      const response = await fetch(`http://91.98.131.218:8001/api/ferrari/matches/history?limit=50`);
      const data = await response.json();
      if (data.success) setMatches(data.matches || []);
    } catch (error) { console.error('Erreur:', error); }
  };

  const fetchAnalytics = async () => {
    try {
      const response = await fetch(`http://91.98.131.218:8001/api/ferrari/matches/analytics`);
      const data = await response.json();
      if (data.success) setAnalytics(data);
    } catch (error) { console.error('Erreur:', error); }
  };

  const fetchVariationDetails = async (variation: Variation) => {
    setSelectedVariation(variation);
    setLoadingDetails(true);
    setExpandedMatch(null);
    setModalTab('overview');
    try {
      const [detailsRes, matchesRes] = await Promise.all([
        fetch(`http://91.98.131.218:8001/api/ferrari/variations/${variation.id}/details`),
        fetch(`http://91.98.131.218:8001/api/ferrari/variations/${variation.id}/matches-detailed`)
      ]);
      const detailsData = await detailsRes.json();
      const matchesData = await matchesRes.json();
      if (detailsData.success) setVariationDetails(detailsData);
      if (matchesData.success) setMatchesDetailed(matchesData);
    } catch (error) { console.error('Erreur:', error); }
    finally { setLoadingDetails(false); }
  };

  const closeModal = () => { setSelectedVariation(null); setVariationDetails(null); setMatchesDetailed(null); setExpandedMatch(null); };
  const handleRefresh = async () => { setRefreshing(true); await fetchAllData(); setRefreshing(false); };

  const getRankIcon = (index: number) => {
    if (index === 0) return <Trophy className="w-5 h-5 text-yellow-400" />;
    if (index === 1) return <Medal className="w-5 h-5 text-slate-300" />;
    if (index === 2) return <Medal className="w-5 h-5 text-amber-600" />;
    return <span className="text-slate-500 font-bold">#{index + 1}</span>;
  };

  const getPerformanceColor = (winRate: number) => {
    if (winRate >= 30) return 'from-green-500/20 to-emerald-500/20 border-green-500/40';
    if (winRate >= 20) return 'from-yellow-500/20 to-orange-500/20 border-yellow-500/40';
    return 'from-red-500/20 to-pink-500/20 border-red-500/40';
  };

  const getPredictionIcon = (prediction: string) => {
    if (prediction === 'home') return <Home className="w-4 h-4" />;
    if (prediction === 'away') return <Users className="w-4 h-4" />;
    return <Scale className="w-4 h-4" />;
  };

  const getPredictionColor = (prediction: string) => {
    if (prediction === 'home') return 'bg-blue-500/20 text-blue-400 border-blue-500/50';
    if (prediction === 'away') return 'bg-orange-500/20 text-orange-400 border-orange-500/50';
    return 'bg-purple-500/20 text-purple-400 border-purple-500/50';
  };

  const filteredMatches = matches.filter(m => matchFilter === 'win' ? m.was_correct : matchFilter === 'loss' ? !m.was_correct : true);
  const filteredDetailedMatches = matchesDetailed?.matches.filter(m => detailFilter === 'win' ? m.was_correct : detailFilter === 'loss' ? !m.was_correct : true) || [];

  if (loading) return <div className="min-h-screen bg-gradient-to-br from-slate-950 via-slate-900 to-purple-950 flex items-center justify-center"><Loader2 className="w-16 h-16 text-purple-400 animate-spin" /></div>;

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-950 via-slate-900 to-purple-950 p-6">
      <div className="max-w-7xl mx-auto">

        {/* Header */}
        <motion.div initial={{ opacity: 0, y: -20 }} animate={{ opacity: 1, y: 0 }} className="flex items-center justify-between mb-8">
          <div className="flex items-center gap-4">
            <motion.button whileHover={{ scale: 1.1 }} onClick={() => router.push('/strategies/manage')} className="p-3 bg-slate-800/50 hover:bg-slate-700/50 rounded-xl border border-slate-700/50">
              <ArrowLeft className="w-5 h-5 text-slate-400" />
            </motion.button>
            <div>
              <h1 className="text-4xl font-black text-transparent bg-clip-text bg-gradient-to-r from-yellow-400 via-orange-500 to-red-500">🏎️ FERRARI 3.0 - DASHBOARD PRO</h1>
              <p className="text-slate-400 mt-1 flex items-center gap-2"><Brain className="w-4 h-4" />{analytics?.global_stats?.total_predictions || 0} prédictions • {variations.length} variations</p>
            </div>
          </div>
          <motion.button whileHover={{ scale: 1.05 }} onClick={handleRefresh} disabled={refreshing} className="px-6 py-3 bg-gradient-to-r from-purple-600 to-pink-600 rounded-xl font-bold text-white flex items-center gap-2">
            <RefreshCw className={`w-5 h-5 ${refreshing ? 'animate-spin' : ''}`} /> Actualiser
          </motion.button>
        </motion.div>

        {/* Tabs */}
        <div className="flex gap-2 mb-6">
          {[{ id: 'variations', label: 'Variations A/B', icon: Target }, { id: 'matches', label: 'Historique Matchs', icon: Calendar }, { id: 'analytics', label: 'Analytics', icon: PieChart }].map((tab) => (
            <button key={tab.id} onClick={() => setActiveTab(tab.id as any)} className={`flex items-center gap-2 px-5 py-3 rounded-xl font-bold transition-all ${activeTab === tab.id ? 'bg-gradient-to-r from-purple-600 to-pink-600 text-white' : 'bg-slate-800/50 text-slate-400 hover:bg-slate-700/50'}`}>
              <tab.icon className="w-5 h-5" /> {tab.label}
            </button>
          ))}
        </div>

        {/* Performance Globale */}
        <div className="mb-8 p-6 bg-gradient-to-r from-slate-800/50 via-purple-900/30 to-slate-800/50 backdrop-blur-xl rounded-2xl border border-purple-500/20">
          <div className="flex items-center gap-3 mb-6">
            <Award className="w-6 h-6 text-yellow-400" />
            <h2 className="text-xl font-bold text-yellow-400">Performance Globale</h2>
            <span className="px-3 py-1 bg-green-500/20 text-green-400 text-xs font-bold rounded-full">✓ DONNÉES RÉELLES</span>
          </div>
          <div className="grid grid-cols-5 gap-4">
            <div className="bg-slate-900/50 rounded-xl p-4 border border-slate-700/50"><div className="text-xs text-slate-500 mb-1">Prédictions</div><div className="text-2xl font-black text-white">{analytics?.global_stats?.total_predictions || 0}</div></div>
            <div className="bg-slate-900/50 rounded-xl p-4 border border-green-500/30"><div className="text-xs text-slate-500 mb-1">Victoires</div><div className="text-2xl font-black text-green-400">{analytics?.global_stats?.wins || 0}</div></div>
            <div className="bg-slate-900/50 rounded-xl p-4 border border-red-500/30"><div className="text-xs text-slate-500 mb-1">Défaites</div><div className="text-2xl font-black text-red-400">{analytics?.global_stats?.losses || 0}</div></div>
            <div className="bg-slate-900/50 rounded-xl p-4 border border-purple-500/30"><div className="text-xs text-slate-500 mb-1">Win Rate</div><div className="text-2xl font-black text-purple-400">{(analytics?.global_stats?.win_rate || 0).toFixed(1)}%</div></div>
            <div className="bg-slate-900/50 rounded-xl p-4 border border-emerald-500/30"><div className="text-xs text-slate-500 mb-1">Profit</div><div className={`text-2xl font-black ${(monitoringData?.total_profit || 0) >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>{(monitoringData?.total_profit || 0) >= 0 ? '+' : ''}{(monitoringData?.total_profit || 0).toFixed(0)}€</div></div>
          </div>
        </div>

        {/* TAB: VARIATIONS */}
        <AnimatePresence mode="wait">
          {activeTab === 'variations' && (
            <motion.div key="variations" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
              <div className="flex items-center gap-3 mb-4">
                <Target className="w-6 h-6 text-purple-400" />
                <h2 className="text-2xl font-black text-transparent bg-clip-text bg-gradient-to-r from-purple-400 to-pink-400">VARIATIONS A/B</h2>
                <span className="text-sm text-slate-400 ml-2">👆 Cliquez pour voir les détails</span>
              </div>
              <div className="space-y-4">
                {variations.map((variation, index) => {
                  const recommendation = recommendations.find(r => r.variation_id === variation.id);
                  const bayesian = variation.bayesian;
                  return (
                    <motion.div key={variation.id} initial={{ opacity: 0, x: -20 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: 0.05 * index }}
                      onClick={() => fetchVariationDetails(variation)}
                      className={`bg-gradient-to-r ${getPerformanceColor(variation.win_rate)} backdrop-blur-xl rounded-xl p-6 border transition-all hover:scale-[1.01] cursor-pointer group`}>
                      <div className="flex items-start justify-between">
                        <div className="flex-1">
                          <div className="flex items-center gap-3 mb-2">
                            {getRankIcon(index)}
                            <h3 className="text-xl font-bold text-white group-hover:text-yellow-400 transition-colors">{variation.name}</h3>
                            {variation.is_control && <span className="px-2 py-1 bg-red-500/20 text-red-400 text-xs font-bold rounded-full">🎯 BASELINE</span>}
                            {variation.is_active && <span className="px-2 py-1 bg-green-500/20 text-green-400 text-xs font-bold rounded-full flex items-center gap-1"><div className="w-1.5 h-1.5 bg-green-400 rounded-full animate-pulse" /> Active</span>}
                            {index === 0 && variation.roi > 0 && <span className="px-2 py-1 bg-yellow-500/20 text-yellow-400 text-xs font-bold rounded-full">⭐ MEILLEURE</span>}
                            <Eye className="w-4 h-4 text-slate-500 group-hover:text-yellow-400 ml-auto" />
                          </div>
                          <p className="text-sm text-slate-400 mb-3">{variation.description}</p>
                          {variation.enabled_factors?.length > 0 && (
                            <div className="flex flex-wrap gap-2 mb-4">
                              {variation.enabled_factors.map((f, i) => <span key={i} className="px-2 py-1 bg-slate-700/50 text-slate-300 text-xs rounded-lg">{f}</span>)}
                            </div>
                          )}
                          <div className="grid grid-cols-5 gap-4">
                            <div><div className="text-xs text-slate-500">Matchs</div><div className="text-lg font-bold text-white">{variation.matches_tested}</div></div>
                            <div><div className="text-xs text-slate-500">Victoires</div><div className="text-lg font-bold text-green-400">{variation.wins}</div></div>
                            <div><div className="text-xs text-slate-500">Win Rate</div><div className={`text-lg font-bold ${variation.win_rate >= 25 ? 'text-green-400' : 'text-yellow-400'}`}>{variation.win_rate.toFixed(1)}%</div></div>
                            <div><div className="text-xs text-slate-500">Profit</div><div className={`text-lg font-bold ${variation.total_profit >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>{variation.total_profit >= 0 ? '+' : ''}{variation.total_profit.toFixed(2)}€</div></div>
                            <div><div className="text-xs text-slate-500">ROI</div><div className={`text-lg font-bold ${variation.roi >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>{variation.roi >= 0 ? '+' : ''}{variation.roi.toFixed(1)}%</div></div>
                          </div>
                        </div>
                        <div className="ml-6 w-52 bg-slate-900/80 rounded-xl p-4 border border-purple-500/30">
                          <div className="text-xs text-purple-400 mb-2 font-bold uppercase flex items-center gap-2"><Brain className="w-4 h-4" /> Thompson</div>
                          <div className="text-xl font-black text-purple-400 mb-2">{(bayesian?.expected_win_rate || 50).toFixed(1)}% WR</div>
                          <div className="text-xs text-slate-400">Trafic: {(recommendation?.recommended_traffic || 20).toFixed(0)}%</div>
                          <div className="mt-2 h-1.5 bg-slate-700 rounded-full overflow-hidden">
                            <div className={`h-full rounded-full ${index === 0 ? 'bg-yellow-500' : 'bg-purple-500'}`} style={{ width: `${recommendation?.recommended_traffic || 20}%` }} />
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
            <motion.div key="matches" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-2xl font-black text-transparent bg-clip-text bg-gradient-to-r from-blue-400 to-cyan-400 flex items-center gap-3"><Calendar className="w-6 h-6 text-blue-400" /> HISTORIQUE DES MATCHS</h2>
                <div className="flex gap-2">
                  {['all', 'win', 'loss'].map((f) => (
                    <button key={f} onClick={() => setMatchFilter(f as any)} className={`px-4 py-2 rounded-lg font-medium ${matchFilter === f ? (f === 'win' ? 'bg-green-500/20 text-green-400' : f === 'loss' ? 'bg-red-500/20 text-red-400' : 'bg-purple-500/20 text-purple-400') : 'bg-slate-800/50 text-slate-400'}`}>
                      {f === 'all' ? 'Tous' : f === 'win' ? 'Victoires' : 'Défaites'}
                    </button>
                  ))}
                </div>
              </div>
              <div className="bg-slate-800/30 rounded-xl border border-slate-700/50 overflow-hidden max-h-[500px] overflow-y-auto">
                {filteredMatches.map((match) => (
                  <div key={match.id} className={`grid grid-cols-6 gap-4 p-4 border-b border-slate-700/30 ${match.was_correct ? 'bg-green-500/5' : 'bg-red-500/5'}`}>
                    <div className="text-white truncate">{match.home_team || match.match_id.substring(0, 15)}...</div>
                    <div><span className={`px-2 py-1 rounded text-xs font-bold ${match.predicted_outcome === 'home' ? 'bg-blue-500/20 text-blue-400' : 'bg-orange-500/20 text-orange-400'}`}>{match.predicted_outcome?.toUpperCase()}</span></div>
                    <div className="text-slate-400">{match.confidence?.toFixed(0)}%</div>
                    <div className="text-slate-400">{((match.edge_detected || 0) * 100).toFixed(1)}%</div>
                    <div>{match.was_correct ? <span className="text-green-400 flex items-center gap-1"><Check className="w-4 h-4" /> WIN</span> : <span className="text-red-400 flex items-center gap-1"><X className="w-4 h-4" /> LOSS</span>}</div>
                    <div className={`font-bold ${(match.profit_loss || 0) >= 0 ? 'text-green-400' : 'text-red-400'}`}>{(match.profit_loss || -10).toFixed(0)}€</div>
                  </div>
                ))}
              </div>
            </motion.div>
          )}

          {/* TAB: ANALYTICS */}
          {activeTab === 'analytics' && analytics && (
            <motion.div key="analytics" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
              <h2 className="text-2xl font-black text-transparent bg-clip-text bg-gradient-to-r from-emerald-400 to-cyan-400 mb-6 flex items-center gap-3"><PieChart className="w-6 h-6 text-emerald-400" /> ANALYTICS</h2>
              <div className="grid grid-cols-2 gap-6">
                <div className="bg-slate-800/30 rounded-xl p-6 border border-slate-700/50">
                  <h3 className="font-bold text-white mb-4">Win Rate par Confiance</h3>
                  {analytics.confidence_breakdown.map((item, i) => (
                    <div key={i} className="flex items-center gap-3 mb-2">
                      <div className="w-28 text-sm text-slate-400 truncate">{item.confidence_level}</div>
                      <div className="flex-1 h-4 bg-slate-700 rounded-full overflow-hidden"><div className={`h-full ${item.win_rate >= 50 ? 'bg-green-500' : 'bg-red-500'}`} style={{ width: `${item.win_rate}%` }} /></div>
                      <div className={`w-12 text-right font-bold ${item.win_rate >= 50 ? 'text-green-400' : 'text-red-400'}`}>{item.win_rate}%</div>
                    </div>
                  ))}
                </div>
                <div className="bg-slate-800/30 rounded-xl p-6 border border-slate-700/50">
                  <h3 className="font-bold text-white mb-4">Win Rate par Type</h3>
                  {analytics.outcome_breakdown.map((item, i) => (
                    <div key={i} className="flex items-center gap-4 mb-3">
                      <div className={`w-16 px-2 py-1 rounded text-center font-bold text-xs ${item.predicted_outcome === 'home' ? 'bg-blue-500/20 text-blue-400' : 'bg-orange-500/20 text-orange-400'}`}>{item.predicted_outcome?.toUpperCase()}</div>
                      <div className="flex-1 h-6 bg-slate-700 rounded-full overflow-hidden"><div className={`h-full ${item.win_rate >= 30 ? 'bg-green-500' : 'bg-red-500'}`} style={{ width: `${item.win_rate}%` }} /></div>
                      <div className={`w-16 text-right font-bold ${item.win_rate >= 30 ? 'text-green-400' : 'text-red-400'}`}>{item.win_rate}%</div>
                    </div>
                  ))}
                </div>
              </div>
            </motion.div>
          )}
        </AnimatePresence>

        {/* ================== MODAL DÉTAILS VARIATION ================== */}
        <AnimatePresence>
          {selectedVariation && (
            <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="fixed inset-0 bg-black/80 backdrop-blur-sm z-50 flex items-center justify-center p-4" onClick={closeModal}>
              <motion.div initial={{ scale: 0.9, opacity: 0 }} animate={{ scale: 1, opacity: 1 }} exit={{ scale: 0.9, opacity: 0 }}
                className="bg-gradient-to-br from-slate-900 via-slate-800 to-purple-900 rounded-2xl border border-purple-500/30 w-full max-w-6xl max-h-[90vh] overflow-hidden"
                onClick={(e) => e.stopPropagation()}>
                
                {/* Modal Header */}
                <div className="p-6 border-b border-slate-700/50 flex items-center justify-between bg-slate-900/50">
                  <div className="flex items-center gap-4">
                    <div className="p-3 bg-purple-500/20 rounded-xl"><Crosshair className="w-8 h-8 text-purple-400" /></div>
                    <div>
                      <h2 className="text-2xl font-black text-white">{selectedVariation.name}</h2>
                      <p className="text-slate-400">{selectedVariation.description}</p>
                    </div>
                  </div>
                  <button onClick={closeModal} className="p-2 hover:bg-slate-700/50 rounded-lg"><X className="w-6 h-6 text-slate-400" /></button>
                </div>

                {/* Modal Tabs */}
                <div className="px-6 pt-4 flex gap-2 border-b border-slate-700/50">
                  <button onClick={() => setModalTab('overview')} className={`px-4 py-2 rounded-t-lg font-bold transition-all ${modalTab === 'overview' ? 'bg-purple-500/20 text-purple-400 border-b-2 border-purple-500' : 'text-slate-400 hover:text-white'}`}>
                    📊 Vue d'ensemble
                  </button>
                  <button onClick={() => setModalTab('matches')} className={`px-4 py-2 rounded-t-lg font-bold transition-all ${modalTab === 'matches' ? 'bg-green-500/20 text-green-400 border-b-2 border-green-500' : 'text-slate-400 hover:text-white'}`}>
                    🏆 Matchs WIN/LOSS ({matchesDetailed?.stats.total_matches || 0})
                  </button>
                </div>

                {/* Modal Content */}
                <div className="p-6 overflow-y-auto max-h-[calc(90vh-180px)]">
                  {loadingDetails ? (
                    <div className="flex items-center justify-center py-20"><Loader2 className="w-12 h-12 text-purple-400 animate-spin" /></div>
                  ) : (
                    <>
                      {/* TAB: VUE D'ENSEMBLE */}
                      {modalTab === 'overview' && variationDetails && (
                        <div className="space-y-6">
                          {/* Stats Row */}
                          <div className="grid grid-cols-5 gap-4">
                            <div className="bg-slate-800/50 rounded-xl p-4 text-center border border-slate-700/50">
                              <div className="text-3xl font-black text-white">{variationDetails.performance_analysis.total_matches}</div>
                              <div className="text-xs text-slate-400">Matchs</div>
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
                              <div className="text-xs text-slate-400">Profit</div>
                            </div>
                          </div>

                          {/* Comparaison vs Baseline */}
                          {variationDetails.comparison_to_baseline && (
                            <div className={`p-4 rounded-xl border ${variationDetails.comparison_to_baseline.is_better ? 'bg-green-500/10 border-green-500/30' : 'bg-red-500/10 border-red-500/30'}`}>
                              <div className="flex items-center gap-2 mb-2">
                                {variationDetails.comparison_to_baseline.is_better ? <TrendingUp className="w-5 h-5 text-green-400" /> : <TrendingDown className="w-5 h-5 text-red-400" />}
                                <span className="font-bold text-white">Comparaison vs Baseline</span>
                              </div>
                              <div className="grid grid-cols-3 gap-4 text-center">
                                <div>
                                  <div className={`text-xl font-bold ${variationDetails.comparison_to_baseline.vs_baseline_wr >= 0 ? 'text-green-400' : 'text-red-400'}`}>{variationDetails.comparison_to_baseline.vs_baseline_wr >= 0 ? '+' : ''}{variationDetails.comparison_to_baseline.vs_baseline_wr}%</div>
                                  <div className="text-xs text-slate-400">Win Rate</div>
                                </div>
                                <div>
                                  <div className={`text-xl font-bold ${variationDetails.comparison_to_baseline.vs_baseline_roi >= 0 ? 'text-green-400' : 'text-red-400'}`}>{variationDetails.comparison_to_baseline.vs_baseline_roi >= 0 ? '+' : ''}{variationDetails.comparison_to_baseline.vs_baseline_roi}%</div>
                                  <div className="text-xs text-slate-400">ROI</div>
                                </div>
                                <div>
                                  <div className={`text-xl font-bold ${variationDetails.comparison_to_baseline.vs_baseline_profit >= 0 ? 'text-green-400' : 'text-red-400'}`}>{variationDetails.comparison_to_baseline.vs_baseline_profit >= 0 ? '+' : ''}{variationDetails.comparison_to_baseline.vs_baseline_profit}€</div>
                                  <div className="text-xs text-slate-400">Profit</div>
                                </div>
                              </div>
                            </div>
                          )}

                          {/* Analyse des Facteurs (Vue Globale) */}
                          {variationDetails.factor_analysis.length > 0 && (
                            <div className="bg-slate-800/30 rounded-xl p-5 border border-slate-700/50">
                              <h3 className="text-lg font-bold text-white mb-4 flex items-center gap-2"><Flame className="w-5 h-5 text-orange-400" />Analyse Globale des Facteurs</h3>
                              <div className="space-y-3">
                                {variationDetails.factor_analysis.map((factor, i) => (
                                  <div key={i} className="flex items-center gap-4 p-3 bg-slate-900/50 rounded-lg">
                                    <div className={`w-2 h-10 rounded-full ${factor.contribution === 'positive' ? 'bg-green-500' : factor.contribution === 'negative' ? 'bg-red-500' : 'bg-yellow-500'}`} />
                                    <div className="flex-1">
                                      <div className="font-medium text-white">{factor.factor}</div>
                                      <div className="text-xs text-slate-400">{factor.description}</div>
                                    </div>
                                    <div className="text-center px-4">
                                      <div className={`text-lg font-bold ${factor.contribution === 'positive' ? 'text-green-400' : 'text-yellow-400'}`}>{factor.impact_score}/10</div>
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

                          {/* Matchs En Attente */}
                          {variationDetails.assigned_matches.filter(m => !m.outcome).length > 0 && (
                            <div className="bg-slate-800/30 rounded-xl p-5 border border-yellow-500/30">
                              <h3 className="text-lg font-bold text-white mb-4 flex items-center gap-2">
                                <Clock className="w-5 h-5 text-yellow-400" />
                                Matchs En Attente ({variationDetails.assigned_matches.filter(m => !m.outcome).length})
                              </h3>
                              <div className="space-y-2 max-h-40 overflow-y-auto">
                                {variationDetails.assigned_matches.filter(m => !m.outcome).map((match, i) => (
                                  <div key={i} className="flex items-center justify-between p-3 bg-slate-900/50 rounded-lg">
                                    <div className="flex items-center gap-3">
                                      <Shield className="w-4 h-4 text-slate-500" />
                                      <span className="font-medium text-white">{match.home_team || 'TBD'}</span>
                                      <span className="text-slate-500">vs</span>
                                      <span className="font-medium text-white">{match.away_team || 'TBD'}</span>
                                    </div>
                                    <div className="flex items-center gap-3">
                                      <span className="text-xs text-slate-400">{match.sport}</span>
                                      <span className="px-2 py-1 bg-yellow-500/20 text-yellow-400 text-xs font-bold rounded">⏳ En attente</span>
                                    </div>
                                  </div>
                                ))}
                              </div>
                            </div>
                          )}

                          {/* Thompson Sampling */}
                          <div className="bg-gradient-to-r from-purple-500/10 to-pink-500/10 rounded-xl p-5 border border-purple-500/30">
                            <h3 className="text-lg font-bold text-white mb-4 flex items-center gap-2"><Brain className="w-5 h-5 text-purple-400" />Paramètres Thompson Sampling</h3>
                            <div className="grid grid-cols-4 gap-4 text-center">
                              <div><div className="text-2xl font-mono font-bold text-purple-400">α = {variationDetails.variation.alpha?.toFixed(1) || 1}</div><div className="text-xs text-slate-400">Succès + 1</div></div>
                              <div><div className="text-2xl font-mono font-bold text-pink-400">β = {variationDetails.variation.beta?.toFixed(1) || 1}</div><div className="text-xs text-slate-400">Échecs + 1</div></div>
                              <div><div className="text-2xl font-bold text-yellow-400">{variationDetails.variation.expected_win_rate?.toFixed(1) || 50}%</div><div className="text-xs text-slate-400">Expected WR</div></div>
                              <div><div className="text-lg font-bold text-slate-300">[{variationDetails.variation.confidence_lower?.toFixed(0) || 10}% - {variationDetails.variation.confidence_upper?.toFixed(0) || 90}%]</div><div className="text-xs text-slate-400">IC 95%</div></div>
                            </div>
                          </div>
                        </div>
                      )}

                      {/* TAB: MATCHS WIN/LOSS */}
                      {modalTab === 'matches' && matchesDetailed && (
                        <div className="space-y-6">
                          {/* Stats Row */}
                          <div className="grid grid-cols-4 gap-4">
                            <div className="bg-slate-800/50 rounded-xl p-4 text-center border border-slate-700/50"><div className="text-3xl font-black text-white">{matchesDetailed.stats.total_matches}</div><div className="text-xs text-slate-400">Matchs</div></div>
                            <div className="bg-green-500/10 rounded-xl p-4 text-center border border-green-500/30"><div className="text-3xl font-black text-green-400">{matchesDetailed.stats.wins}</div><div className="text-xs text-slate-400">Victoires</div></div>
                            <div className="bg-red-500/10 rounded-xl p-4 text-center border border-red-500/30"><div className="text-3xl font-black text-red-400">{matchesDetailed.stats.losses}</div><div className="text-xs text-slate-400">Défaites</div></div>
                            <div className="bg-purple-500/10 rounded-xl p-4 text-center border border-purple-500/30"><div className="text-3xl font-black text-purple-400">{matchesDetailed.stats.win_rate}%</div><div className="text-xs text-slate-400">Win Rate</div></div>
                          </div>

                          {/* Filters */}
                          <div className="flex gap-2">
                            {[{ id: 'all', label: 'Tous', count: matchesDetailed.matches.length }, { id: 'win', label: '✅ Victoires', count: matchesDetailed.stats.wins }, { id: 'loss', label: '❌ Défaites', count: matchesDetailed.stats.losses }].map((f) => (
                              <button key={f.id} onClick={() => setDetailFilter(f.id as any)}
                                className={`px-4 py-2 rounded-lg font-medium transition-all ${detailFilter === f.id ? (f.id === 'win' ? 'bg-green-500/20 text-green-400 border border-green-500/50' : f.id === 'loss' ? 'bg-red-500/20 text-red-400 border border-red-500/50' : 'bg-purple-500/20 text-purple-400 border border-purple-500/50') : 'bg-slate-800/50 text-slate-400'}`}>
                                {f.label} ({f.count})
                              </button>
                            ))}
                          </div>

                          {/* Matchs détaillés */}
                          <div className="space-y-3">
                            {filteredDetailedMatches.map((match, index) => (
                              <motion.div key={match.id} initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.03 * index }}
                                className={`rounded-xl border overflow-hidden ${match.was_correct ? 'bg-green-500/5 border-green-500/30' : 'bg-red-500/5 border-red-500/30'}`}>
                                
                                {/* Match Header */}
                                <div className="p-4 flex items-center justify-between cursor-pointer hover:bg-slate-800/30 transition-colors" onClick={() => setExpandedMatch(expandedMatch === match.id ? null : match.id)}>
                                  <div className="flex items-center gap-4">
                                    <div className={`w-14 h-14 rounded-xl flex items-center justify-center font-black text-lg ${match.was_correct ? 'bg-green-500/20 text-green-400' : 'bg-red-500/20 text-red-400'}`}>
                                      {match.was_correct ? '✅' : '❌'}
                                    </div>
                                    <div>
                                      <div className="font-bold text-white text-lg">{match.home_team} vs {match.away_team}</div>
                                      <div className="text-sm text-slate-400 flex items-center gap-3">
                                        <span>📅 {match.date}</span>
                                        <span>⚽ {match.score}</span>
                                        {/* PARI CONSEILLÉ */}
                                        <span className={`px-2 py-0.5 rounded border flex items-center gap-1 ${getPredictionColor(match.predicted_outcome)}`}>
                                          {getPredictionIcon(match.predicted_outcome)}
                                          <span className="font-bold">{match.predicted_outcome?.toUpperCase()}</span>
                                        </span>
                                        <span className={match.was_correct ? 'text-green-400' : 'text-red-400'}>{match.was_correct ? '+' : ''}{match.profit_loss}€</span>
                                      </div>
                                    </div>
                                  </div>
                                  <div className="flex items-center gap-4">
                                    <div className="text-right"><div className="text-sm text-slate-400">Confiance</div><div className="font-bold text-white">{match.confidence}%</div></div>
                                    <div className="text-right"><div className="text-sm text-slate-400">Edge</div><div className="font-bold text-purple-400">{match.edge}%</div></div>
                                    <div className="text-right"><div className="text-sm text-slate-400">Cote</div><div className="font-bold text-yellow-400">{match.odds}</div></div>
                                    <ChevronDown className={`w-5 h-5 text-slate-400 transition-transform ${expandedMatch === match.id ? 'rotate-180' : ''}`} />
                                  </div>
                                </div>

                                {/* Expanded: Factor Analysis */}
                                <AnimatePresence>
                                  {expandedMatch === match.id && (
                                    <motion.div initial={{ height: 0, opacity: 0 }} animate={{ height: 'auto', opacity: 1 }} exit={{ height: 0, opacity: 0 }} className="border-t border-slate-700/50 overflow-hidden">
                                      <div className="p-4 bg-slate-900/50">
                                        <h4 className="font-bold text-white mb-4 flex items-center gap-2"><Flame className="w-5 h-5 text-orange-400" />Analyse des Facteurs pour ce Match</h4>
                                        <div className="grid grid-cols-2 gap-3">
                                          {match.factors_analysis.map((factor, fi) => (
                                            <div key={fi} className={`p-4 rounded-lg border ${factor.status === 'success' ? 'bg-green-500/10 border-green-500/30' : factor.status === 'failure' ? 'bg-red-500/10 border-red-500/30' : 'bg-yellow-500/10 border-yellow-500/30'}`}>
                                              <div className="flex items-center justify-between mb-2">
                                                <div className="flex items-center gap-2">
                                                  <span className="text-2xl">{factor.icon}</span>
                                                  <span className="font-bold text-white">{factor.display_name}</span>
                                                </div>
                                                <div className="flex items-center gap-3">
                                                  <div className="text-right">
                                                    <div className={`text-lg font-bold ${factor.status === 'success' ? 'text-green-400' : factor.status === 'failure' ? 'text-red-400' : 'text-yellow-400'}`}>{factor.impact_score}/10</div>
                                                    <div className="text-xs text-slate-500">Impact</div>
                                                  </div>
                                                  <div className={`px-2 py-1 rounded text-sm font-bold ${factor.status === 'success' ? 'bg-green-500/20 text-green-400' : factor.status === 'failure' ? 'bg-red-500/20 text-red-400' : 'bg-yellow-500/20 text-yellow-400'}`}>{factor.contribution}</div>
                                                </div>
                                              </div>
                                              <p className="text-sm text-slate-300">{factor.detail}</p>
                                            </div>
                                          ))}
                                        </div>
                                        <div className="mt-4 p-3 bg-slate-800/50 rounded-lg border border-slate-700/50">
                                          <div className="flex items-center justify-between">
                                            <div className="flex items-center gap-4">
                                              <span className="text-green-400">✓ {match.summary.total_positive} positifs</span>
                                              <span className="text-red-400">✗ {match.summary.total_negative} négatifs</span>
                                              <span className="text-purple-400">⌀ Impact: {match.summary.avg_impact}/10</span>
                                            </div>
                                            <div className={`px-3 py-1 rounded-lg text-sm font-medium ${match.was_correct ? 'bg-green-500/20 text-green-400' : 'bg-red-500/20 text-red-400'}`}>💡 {match.lesson}</div>
                                          </div>
                                        </div>
                                      </div>
                                    </motion.div>
                                  )}
                                </AnimatePresence>
                              </motion.div>
                            ))}
                          </div>
                        </div>
                      )}
                    </>
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
