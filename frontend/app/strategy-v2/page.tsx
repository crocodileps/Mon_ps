'use client';

import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Brain, Zap, TrendingUp, TrendingDown, AlertTriangle,
  Target, Activity, BarChart3, Shield, Eye, Sparkles,
  ChevronRight, RefreshCw, Settings, Info, CheckCircle,
  XCircle, Clock, Layers, GitBranch, Award, Ghost
} from 'lucide-react';

// Types
interface TierDiagnostic {
  strategy_id: string;
  status: string;
  roi_percent: number;
  clv_percent: number;
  sample_size: number;
  statistical_significance: string;
  stake_multiplier: number;
  confidence_score: number;
  trend: string;
  issues: string[];
  improvements: string[];
  is_shadow_mode: boolean;
  shadow_reason?: string;
  recent_roi_7d: number;
  recent_roi_14d: number;
  wilson_interval: {
    center: number;
    lower: number;
    upper: number;
    confidence: number;
  };
  breakeven: {
    avg_odds: number;
    breakeven_win_rate: number;
    actual_win_rate: number;
    edge_vs_breakeven: number;
    is_profitable_structure: boolean;
  };
}

interface OptimalPick {
  id: number;
  match: string;
  market: string;
  prediction: string;
  score: number;
  tier: string;
  odds: number;
  stake_multiplier: number;
  reason: string;
  commence_time: string;
}

interface StrategyConfig {
  version: string;
  system_health: {
    status: string;
    score: number;
    interpretation: string;
  };
  rankings: {
    tiers: string[];
    markets: string[];
  };
  tier_diagnostics: Record<string, TierDiagnostic>;
  market_diagnostics: Record<string, TierDiagnostic>;
  optimal_combinations: Array<{
    tier: string;
    market: string;
    score: number;
  }>;
  shadow_strategies: {
    count: number;
    strategies: string[];
  };
  global_recommendations: string[];
}

interface OptimalPicksData {
  date: string;
  system_health: string;
  summary: {
    total_picks: number;
    real_bets: number;
    shadow_tracking: number;
    rejected: number;
  };
  real_bets: {
    count: number;
    picks: OptimalPick[];
  };
  shadow_tracking: {
    count: number;
    picks: OptimalPick[];
  };
}

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://91.98.131.218:8001';

// Status colors and icons
const statusConfig: Record<string, { color: string; bg: string; icon: React.ReactNode }> = {
  champion: { color: 'text-amber-400', bg: 'bg-amber-500/20', icon: <Award className="w-4 h-4" /> },
  profitable: { color: 'text-emerald-400', bg: 'bg-emerald-500/20', icon: <CheckCircle className="w-4 h-4" /> },
  neutral: { color: 'text-slate-400', bg: 'bg-slate-500/20', icon: <Activity className="w-4 h-4" /> },
  struggling: { color: 'text-orange-400', bg: 'bg-orange-500/20', icon: <AlertTriangle className="w-4 h-4" /> },
  recovering: { color: 'text-cyan-400', bg: 'bg-cyan-500/20', icon: <RefreshCw className="w-4 h-4" /> },
  shadow: { color: 'text-purple-400', bg: 'bg-purple-500/20', icon: <Ghost className="w-4 h-4" /> },
};

const trendConfig: Record<string, { color: string; icon: React.ReactNode }> = {
  improving: { color: 'text-emerald-400', icon: <TrendingUp className="w-4 h-4" /> },
  stable: { color: 'text-slate-400', icon: <Activity className="w-4 h-4" /> },
  declining: { color: 'text-red-400', icon: <TrendingDown className="w-4 h-4" /> },
};

export default function StrategyV2Page() {
  const [config, setConfig] = useState<StrategyConfig | null>(null);
  const [optimalPicks, setOptimalPicks] = useState<OptimalPicksData | null>(null);
  const [issues, setIssues] = useState<any>(null);
  const [shadowReport, setShadowReport] = useState<any>(null);
  const [breakeven, setBreakeven] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<'overview' | 'picks' | 'issues' | 'shadow' | 'breakeven'>('overview');
  const [refreshing, setRefreshing] = useState(false);

  useEffect(() => {
    fetchAllData();
  }, []);

  const fetchAllData = async (forceRefresh = false) => {
    setRefreshing(true);
    try {
      const [configRes, picksRes, issuesRes, shadowRes, breakevenRes] = await Promise.all([
        fetch(`${API_BASE}/api/pro/command-center/strategy/v2/config?force_refresh=${forceRefresh}`),
        fetch(`${API_BASE}/api/pro/command-center/strategy/v2/optimal-picks`),
        fetch(`${API_BASE}/api/pro/command-center/strategy/v2/issues`),
        fetch(`${API_BASE}/api/pro/command-center/strategy/v2/shadow-report`),
        fetch(`${API_BASE}/api/pro/command-center/strategy/v2/breakeven-analysis`),
      ]);

      const [configData, picksData, issuesData, shadowData, breakevenData] = await Promise.all([
        configRes.json(),
        picksRes.json(),
        issuesRes.json(),
        shadowRes.json(),
        breakevenRes.json(),
      ]);

      setConfig(configData);
      setOptimalPicks(picksData);
      setIssues(issuesData);
      setShadowReport(shadowData);
      setBreakeven(breakevenData);
    } catch (error) {
      console.error('Erreur fetch:', error);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-[#0a0a0f] flex items-center justify-center">
        <motion.div
          initial={{ opacity: 0, scale: 0.9 }}
          animate={{ opacity: 1, scale: 1 }}
          className="text-center"
        >
          <motion.div
            animate={{ rotate: 360 }}
            transition={{ duration: 2, repeat: Infinity, ease: "linear" }}
            className="w-16 h-16 mx-auto mb-4"
          >
            <Brain className="w-full h-full text-cyan-400" />
          </motion.div>
          <p className="text-slate-400 font-mono">Chargement du Moteur Adaptatif V2.0...</p>
        </motion.div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#0a0a0f] text-white overflow-hidden">
      {/* Background Effects */}
      <div className="fixed inset-0 pointer-events-none">
        <div className="absolute top-0 left-1/4 w-96 h-96 bg-cyan-500/10 rounded-full blur-3xl" />
        <div className="absolute bottom-0 right-1/4 w-96 h-96 bg-purple-500/10 rounded-full blur-3xl" />
        <div className="absolute inset-0 bg-[url('data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iNDAiIGhlaWdodD0iNDAiIHhtbG5zPSJodHRwOi8vd3d3LnczLm9yZy8yMDAwL3N2ZyI+PGRlZnM+PHBhdHRlcm4gaWQ9ImdyaWQiIHdpZHRoPSI0MCIgaGVpZ2h0PSI0MCIgcGF0dGVyblVuaXRzPSJ1c2VyU3BhY2VPblVzZSI+PHBhdGggZD0iTSAwIDEwIEwgNDAgMTAgTSAxMCAwIEwgMTAgNDAgTSAwIDIwIEwgNDAgMjAgTSAyMCAwIEwgMjAgNDAgTSAwIDMwIEwgNDAgMzAgTSAzMCAwIEwgMzAgNDAiIGZpbGw9Im5vbmUiIHN0cm9rZT0iIzFhMWEyZSIgc3Ryb2tlLXdpZHRoPSIxIi8+PC9wYXR0ZXJuPjwvZGVmcz48cmVjdCB3aWR0aD0iMTAwJSIgaGVpZ2h0PSIxMDAlIiBmaWxsPSJ1cmwoI2dyaWQpIi8+PC9zdmc+')] opacity-30" />
      </div>

      <div className="relative z-10 max-w-7xl mx-auto px-4 py-8">
        {/* Bouton retour */}
        <a href="/" className="inline-flex items-center gap-2 mb-4 px-4 py-2 bg-slate-800/50 hover:bg-slate-700/50 rounded-lg text-slate-300 hover:text-white transition-colors">
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 19l-7-7m0 0l7-7m-7 7h18" /></svg>
          Retour au Dashboard
        </a>
        {/* Header */}
        <motion.header
          initial={{ opacity: 0, y: -20 }}
          animate={{ opacity: 1, y: 0 }}
          className="mb-8"
        >
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <div className="relative">
                <motion.div
                  animate={{ rotate: [0, 360] }}
                  transition={{ duration: 20, repeat: Infinity, ease: "linear" }}
                  className="absolute inset-0 bg-gradient-to-r from-cyan-500 to-purple-500 rounded-xl blur-lg opacity-50"
                />
                <div className="relative bg-[#12121a] p-3 rounded-xl border border-slate-800">
                  <Brain className="w-8 h-8 text-cyan-400" />
                </div>
              </div>
              <div>
                <h1 className="text-2xl font-bold bg-gradient-to-r from-cyan-400 via-purple-400 to-pink-400 bg-clip-text text-transparent">
                  Moteur Adaptatif V2.0
                </h1>
                <p className="text-slate-500 text-sm font-mono">
                  ROI-Based • Wilson CI • Auto-Learning
                </p>
              </div>
            </div>

            <div className="flex items-center gap-4">
              {/* System Health Badge */}
              {config && (
                <motion.div
                  initial={{ scale: 0 }}
                  animate={{ scale: 1 }}
                  className={`px-4 py-2 rounded-full border ${
                    config.system_health.score >= 70
                      ? 'bg-emerald-500/20 border-emerald-500/50 text-emerald-400'
                      : config.system_health.score >= 50
                      ? 'bg-amber-500/20 border-amber-500/50 text-amber-400'
                      : 'bg-red-500/20 border-red-500/50 text-red-400'
                  }`}
                >
                  <div className="flex items-center gap-2">
                    <Activity className="w-4 h-4" />
                    <span className="font-mono font-bold">{config.system_health.score}%</span>
                    <span className="text-xs opacity-70">{config.system_health.status}</span>
                  </div>
                </motion.div>
              )}

              <motion.button
                whileHover={{ scale: 1.05 }}
                whileTap={{ scale: 0.95 }}
                onClick={() => fetchAllData(true)}
                disabled={refreshing}
                className="p-3 rounded-xl bg-slate-800/50 border border-slate-700 hover:border-cyan-500/50 transition-colors"
              >
                <RefreshCw className={`w-5 h-5 text-slate-400 ${refreshing ? 'animate-spin' : ''}`} />
              </motion.button>
            </div>
          </div>
        </motion.header>

        {/* Navigation Tabs */}
        <motion.nav
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
          className="flex gap-2 mb-8 p-1 bg-slate-900/50 rounded-xl border border-slate-800 overflow-x-auto"
        >
          {[
            { id: 'overview', label: 'Vue Globale', icon: <Layers className="w-4 h-4" /> },
            { id: 'picks', label: 'Picks Optimaux', icon: <Target className="w-4 h-4" /> },
            { id: 'issues', label: 'Diagnostics', icon: <AlertTriangle className="w-4 h-4" /> },
            { id: 'shadow', label: 'Shadow Tracking', icon: <Ghost className="w-4 h-4" /> },
            { id: 'breakeven', label: 'Breakeven', icon: <BarChart3 className="w-4 h-4" /> },
          ].map((tab) => (
            <motion.button
              key={tab.id}
              whileHover={{ scale: 1.02 }}
              whileTap={{ scale: 0.98 }}
              onClick={() => setActiveTab(tab.id as any)}
              className={`flex items-center gap-2 px-4 py-2 rounded-lg font-medium transition-all ${
                activeTab === tab.id
                  ? 'bg-gradient-to-r from-cyan-500/20 to-purple-500/20 text-white border border-cyan-500/30'
                  : 'text-slate-400 hover:text-white hover:bg-slate-800/50'
              }`}
            >
              {tab.icon}
              <span className="whitespace-nowrap">{tab.label}</span>
            </motion.button>
          ))}
        </motion.nav>

        {/* Content */}
        <AnimatePresence mode="wait">
          {activeTab === 'overview' && config && (
            <OverviewTab config={config} />
          )}
          {activeTab === 'picks' && optimalPicks && (
            <PicksTab data={optimalPicks} />
          )}
          {activeTab === 'issues' && issues && (
            <IssuesTab data={issues} />
          )}
          {activeTab === 'shadow' && shadowReport && (
            <ShadowTab data={shadowReport} />
          )}
          {activeTab === 'breakeven' && breakeven && (
            <BreakevenTab data={breakeven} />
          )}
        </AnimatePresence>
      </div>
    </div>
  );
}

// Overview Tab Component
function OverviewTab({ config }: { config: StrategyConfig }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -20 }}
      className="space-y-6"
    >
      {/* Rankings */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Tier Rankings */}
        <div className="bg-slate-900/50 rounded-2xl border border-slate-800 p-6">
          <h3 className="text-lg font-bold mb-4 flex items-center gap-2">
            <Layers className="w-5 h-5 text-cyan-400" />
            Ranking des Tiers
          </h3>
          <div className="space-y-3">
            {config.rankings.tiers.map((tier, index) => {
              const diag = config.tier_diagnostics[tier];
              const status = statusConfig[diag?.status || 'neutral'];
              return (
                <motion.div
                  key={tier}
                  initial={{ opacity: 0, x: -20 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: index * 0.1 }}
                  className={`flex items-center justify-between p-3 rounded-xl ${status.bg} border border-slate-700/50`}
                >
                  <div className="flex items-center gap-3">
                    <span className={`w-6 h-6 rounded-full bg-slate-800 flex items-center justify-center text-xs font-bold ${
                      index === 0 ? 'text-amber-400' : index === 1 ? 'text-slate-300' : index === 2 ? 'text-orange-400' : 'text-slate-500'
                    }`}>
                      {index + 1}
                    </span>
                    <span className="font-medium">{tier}</span>
                  </div>
                  <div className="flex items-center gap-4">
                    <span className={`font-mono text-sm ${diag?.roi_percent >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                      {diag?.roi_percent >= 0 ? '+' : ''}{diag?.roi_percent?.toFixed(1)}% ROI
                    </span>
                    <span className={`${status.color}`}>{status.icon}</span>
                  </div>
                </motion.div>
              );
            })}
          </div>
        </div>

        {/* Market Rankings */}
        <div className="bg-slate-900/50 rounded-2xl border border-slate-800 p-6">
          <h3 className="text-lg font-bold mb-4 flex items-center gap-2">
            <BarChart3 className="w-5 h-5 text-purple-400" />
            Ranking des Marchés
          </h3>
          <div className="space-y-3 max-h-[300px] overflow-y-auto pr-2">
            {config.rankings.markets.slice(0, 8).map((market, index) => {
              const diag = config.market_diagnostics[market];
              const status = statusConfig[diag?.status || 'neutral'];
              return (
                <motion.div
                  key={market}
                  initial={{ opacity: 0, x: 20 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: index * 0.1 }}
                  className={`flex items-center justify-between p-3 rounded-xl ${status.bg} border border-slate-700/50`}
                >
                  <div className="flex items-center gap-3">
                    <span className={`w-6 h-6 rounded-full bg-slate-800 flex items-center justify-center text-xs font-bold ${
                      index === 0 ? 'text-amber-400' : index === 1 ? 'text-slate-300' : index === 2 ? 'text-orange-400' : 'text-slate-500'
                    }`}>
                      {index + 1}
                    </span>
                    <span className="font-medium uppercase text-sm">{market.replace('_', ' ')}</span>
                  </div>
                  <div className="flex items-center gap-4">
                    <span className={`font-mono text-sm ${diag?.roi_percent >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                      {diag?.roi_percent >= 0 ? '+' : ''}{diag?.roi_percent?.toFixed(1)}%
                    </span>
                    <span className={`${status.color}`}>{status.icon}</span>
                  </div>
                </motion.div>
              );
            })}
          </div>
        </div>
      </div>

      {/* Optimal Combinations */}
      <div className="bg-slate-900/50 rounded-2xl border border-slate-800 p-6">
        <h3 className="text-lg font-bold mb-4 flex items-center gap-2">
          <Sparkles className="w-5 h-5 text-amber-400" />
          Combinaisons Optimales
        </h3>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {config.optimal_combinations.slice(0, 6).map((combo, index) => (
            <motion.div
              key={index}
              initial={{ opacity: 0, scale: 0.9 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ delay: index * 0.1 }}
              className="relative overflow-hidden rounded-xl bg-gradient-to-br from-slate-800/50 to-slate-900/50 border border-slate-700 p-4"
            >
              <div className="absolute top-0 right-0 w-20 h-20 bg-gradient-to-br from-cyan-500/10 to-purple-500/10 rounded-full blur-2xl" />
              <div className="relative">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-xs text-slate-500 font-mono">#{index + 1}</span>
                  <span className={`px-2 py-0.5 rounded-full text-xs font-bold ${
                    combo.score >= 80 ? 'bg-emerald-500/20 text-emerald-400' : 'bg-amber-500/20 text-amber-400'
                  }`}>
                    Score {combo.score}
                  </span>
                </div>
                <p className="font-medium text-white">{combo.tier}</p>
                <p className="text-sm text-cyan-400 uppercase">{combo.market?.replace('_', ' ')}</p>
              </div>
            </motion.div>
          ))}
        </div>
      </div>

      {/* Global Recommendations */}
      {config.global_recommendations.length > 0 && (
        <div className="bg-gradient-to-r from-cyan-500/10 to-purple-500/10 rounded-2xl border border-cyan-500/20 p-6">
          <h3 className="text-lg font-bold mb-4 flex items-center gap-2">
            <Info className="w-5 h-5 text-cyan-400" />
            Recommandations Globales
          </h3>
          <div className="space-y-2">
            {config.global_recommendations.map((rec, index) => (
              <motion.p
                key={index}
                initial={{ opacity: 0, x: -10 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: index * 0.1 }}
                className="text-slate-300 flex items-start gap-2"
              >
                <ChevronRight className="w-4 h-4 text-cyan-400 mt-1 flex-shrink-0" />
                {rec}
              </motion.p>
            ))}
          </div>
        </div>
      )}
    </motion.div>
  );
}

// Picks Tab Component
function PicksTab({ data }: { data: OptimalPicksData }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -20 }}
      className="space-y-6"
    >
      {/* Summary Stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {[
          { label: 'Total Picks', value: data.summary.total_picks, color: 'text-slate-400', bg: 'bg-slate-500/20' },
          { label: 'Paris Réels', value: data.summary.real_bets, color: 'text-emerald-400', bg: 'bg-emerald-500/20' },
          { label: 'Shadow Track', value: data.summary.shadow_tracking, color: 'text-purple-400', bg: 'bg-purple-500/20' },
          { label: 'Rejetés', value: data.summary.rejected, color: 'text-red-400', bg: 'bg-red-500/20' },
        ].map((stat, index) => (
          <motion.div
            key={stat.label}
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: index * 0.1 }}
            className={`${stat.bg} rounded-xl p-4 border border-slate-700/50`}
          >
            <p className="text-xs text-slate-500 mb-1">{stat.label}</p>
            <p className={`text-2xl font-bold font-mono ${stat.color}`}>{stat.value}</p>
          </motion.div>
        ))}
      </div>

      {/* Real Bets */}
      <div className="bg-slate-900/50 rounded-2xl border border-emerald-500/30 p-6">
        <h3 className="text-lg font-bold mb-4 flex items-center gap-2 text-emerald-400">
          <CheckCircle className="w-5 h-5" />
          Paris Recommandés ({data.real_bets.count})
        </h3>
        <div className="space-y-3">
          {data.real_bets.picks.map((pick, index) => (
            <motion.div
              key={pick.id}
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: index * 0.05 }}
              className="flex items-center justify-between p-4 rounded-xl bg-slate-800/50 border border-slate-700 hover:border-emerald-500/30 transition-colors"
            >
              <div className="flex-1">
                <p className="font-medium text-white">{pick.match}</p>
                <div className="flex items-center gap-2 mt-1">
                  <span className="text-xs px-2 py-0.5 rounded bg-cyan-500/20 text-cyan-400">{pick.market}</span>
                  <span className="text-xs px-2 py-0.5 rounded bg-purple-500/20 text-purple-400">{pick.prediction}</span>
                  <span className="text-xs text-slate-500">{pick.tier}</span>
                </div>
              </div>
              <div className="flex items-center gap-4">
                <div className="text-right">
                  <p className="font-mono text-amber-400">@{pick.odds.toFixed(2)}</p>
                  <p className="text-xs text-slate-500">Score {pick.score}</p>
                </div>
                <div className={`px-3 py-1 rounded-lg font-bold font-mono ${
                  pick.stake_multiplier >= 1.2 ? 'bg-emerald-500/20 text-emerald-400' :
                  pick.stake_multiplier >= 1.0 ? 'bg-cyan-500/20 text-cyan-400' :
                  'bg-amber-500/20 text-amber-400'
                }`}>
                  x{pick.stake_multiplier.toFixed(1)}
                </div>
              </div>
            </motion.div>
          ))}
        </div>
      </div>

      {/* Shadow Tracking */}
      {data.shadow_tracking.picks.length > 0 && (
        <div className="bg-slate-900/50 rounded-2xl border border-purple-500/30 p-6">
          <h3 className="text-lg font-bold mb-4 flex items-center gap-2 text-purple-400">
            <Ghost className="w-5 h-5" />
            Shadow Tracking ({data.shadow_tracking.count})
          </h3>
          <p className="text-xs text-slate-500 mb-4">Paper trading - On enregistre sans parier</p>
          <div className="space-y-2">
            {data.shadow_tracking.picks.map((pick, index) => (
              <motion.div
                key={pick.id}
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ delay: index * 0.05 }}
                className="flex items-center justify-between p-3 rounded-lg bg-slate-800/30 border border-slate-700/50"
              >
                <div>
                  <p className="font-medium text-slate-300">{pick.match}</p>
                  <p className="text-xs text-slate-500">{pick.market} • {pick.prediction}</p>
                </div>
                <div className="text-right">
                  <p className="font-mono text-slate-400">@{pick.odds.toFixed(2)}</p>
                  <p className="text-xs text-purple-400">Score {pick.score}</p>
                </div>
              </motion.div>
            ))}
          </div>
        </div>
      )}
    </motion.div>
  );
}

// Issues Tab Component
function IssuesTab({ data }: { data: any }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -20 }}
      className="space-y-6"
    >
      {/* Summary */}
      <div className="grid grid-cols-3 gap-4">
        <div className="bg-red-500/10 rounded-xl p-4 border border-red-500/30">
          <p className="text-xs text-red-400 mb-1">Critiques</p>
          <p className="text-2xl font-bold text-red-400">{data.issues_summary.critical}</p>
        </div>
        <div className="bg-amber-500/10 rounded-xl p-4 border border-amber-500/30">
          <p className="text-xs text-amber-400 mb-1">Warnings</p>
          <p className="text-2xl font-bold text-amber-400">{data.issues_summary.warning}</p>
        </div>
        <div className="bg-cyan-500/10 rounded-xl p-4 border border-cyan-500/30">
          <p className="text-xs text-cyan-400 mb-1">Info</p>
          <p className="text-2xl font-bold text-cyan-400">{data.issues_summary.info}</p>
        </div>
      </div>

      {/* Issues List */}
      <div className="bg-slate-900/50 rounded-2xl border border-slate-800 p-6">
        <h3 className="text-lg font-bold mb-4 flex items-center gap-2">
          <AlertTriangle className="w-5 h-5 text-amber-400" />
          Problèmes Identifiés
        </h3>
        <div className="space-y-3">
          {data.issues.map((issue: any, index: number) => (
            <motion.div
              key={index}
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: index * 0.05 }}
              className={`p-4 rounded-xl border ${
                (issue.roi || 0) < -10 ? 'bg-red-500/10 border-red-500/30' :
                (issue.roi || 0) < 0 ? 'bg-amber-500/10 border-amber-500/30' :
                'bg-slate-800/50 border-slate-700'
              }`}
            >
              <div className="flex items-start justify-between">
                <div>
                  <p className="text-xs text-slate-500 mb-1">{issue.source}</p>
                  <p className="text-white">{issue.issue}</p>
                </div>
                <div className="text-right">
                  <span className={`font-mono text-sm ${(issue.roi || 0) >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                    {issue.roi >= 0 ? '+' : ''}{issue.roi?.toFixed(1)}% ROI
                  </span>
                  <p className="text-xs text-slate-500 mt-1">{issue.status}</p>
                </div>
              </div>
            </motion.div>
          ))}
        </div>
      </div>

      {/* Improvements */}
      {data.improvements.length > 0 && (
        <div className="bg-gradient-to-r from-emerald-500/10 to-cyan-500/10 rounded-2xl border border-emerald-500/20 p-6">
          <h3 className="text-lg font-bold mb-4 flex items-center gap-2 text-emerald-400">
            <Sparkles className="w-5 h-5" />
            Suggestions d'Amélioration
          </h3>
          <div className="space-y-2">
            {data.improvements.map((imp: any, index: number) => (
              <div key={index} className="flex items-start gap-2 text-slate-300">
                <ChevronRight className="w-4 h-4 text-emerald-400 mt-1 flex-shrink-0" />
                <div>
                  <span className="text-xs text-slate-500">{imp.source}: </span>
                  <span>{imp.suggestion}</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </motion.div>
  );
}

// Shadow Tab Component
function ShadowTab({ data }: { data: any }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -20 }}
      className="space-y-6"
    >
      <div className="bg-purple-500/10 rounded-2xl border border-purple-500/30 p-6">
        <h3 className="text-lg font-bold mb-2 flex items-center gap-2 text-purple-400">
          <Ghost className="w-5 h-5" />
          Shadow Tracking - Philosophie
        </h3>
        <p className="text-slate-400 text-sm">{data.philosophy}</p>
      </div>

      <div className="grid grid-cols-2 gap-4">
        <div className="bg-slate-900/50 rounded-xl p-4 border border-slate-700">
          <p className="text-xs text-slate-500 mb-1">Stratégies en Shadow</p>
          <p className="text-2xl font-bold text-purple-400">{data.shadow_count}</p>
        </div>
        <div className="bg-emerald-500/10 rounded-xl p-4 border border-emerald-500/30">
          <p className="text-xs text-emerald-400 mb-1">Candidats Réintégration</p>
          <p className="text-2xl font-bold text-emerald-400">{data.reintegration.candidates_count}</p>
        </div>
      </div>

      {/* Shadow Strategies */}
      <div className="bg-slate-900/50 rounded-2xl border border-slate-800 p-6">
        <h3 className="text-lg font-bold mb-4">Stratégies en Observation</h3>
        <div className="space-y-3">
          {data.shadow_strategies.map((strat: any, index: number) => (
            <motion.div
              key={index}
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ delay: index * 0.1 }}
              className={`p-4 rounded-xl border ${
                strat.recovering ? 'bg-emerald-500/10 border-emerald-500/30' : 'bg-slate-800/50 border-slate-700'
              }`}
            >
              <div className="flex items-center justify-between">
                <div>
                  <p className="font-medium text-white">{strat.name}</p>
                  <p className="text-xs text-slate-500">{strat.type} • {strat.reason}</p>
                </div>
                <div className="text-right">
                  <p className={`font-mono ${strat.roi >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                    {strat.roi >= 0 ? '+' : ''}{strat.roi?.toFixed(1)}% ROI
                  </p>
                  <p className="text-xs text-slate-500">7j: {strat.recent_roi_7d?.toFixed(1)}%</p>
                </div>
              </div>
              {strat.recommendation && (
                <p className={`mt-2 text-xs ${
                  strat.recommendation.includes('RÉINTÉGRATION') ? 'text-emerald-400' : 'text-amber-400'
                }`}>
                  {strat.recommendation}
                </p>
              )}
            </motion.div>
          ))}
        </div>
      </div>
    </motion.div>
  );
}

// Breakeven Tab Component
function BreakevenTab({ data }: { data: any }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -20 }}
      className="space-y-6"
    >
      {/* Insight */}
      <div className="bg-cyan-500/10 rounded-2xl border border-cyan-500/30 p-6">
        <h3 className="text-lg font-bold mb-2 flex items-center gap-2 text-cyan-400">
          <Info className="w-5 h-5" />
          Comprendre le Breakeven
        </h3>
        <p className="text-slate-400 text-sm">{data.insight}</p>
      </div>

      {/* Summary */}
      <div className="grid grid-cols-2 gap-4">
        <div className="bg-emerald-500/10 rounded-xl p-4 border border-emerald-500/30">
          <p className="text-xs text-emerald-400 mb-1">Stratégies Rentables</p>
          <p className="text-2xl font-bold text-emerald-400">{data.summary.profitable_strategies}</p>
        </div>
        <div className="bg-red-500/10 rounded-xl p-4 border border-red-500/30">
          <p className="text-xs text-red-400 mb-1">Sous le Seuil</p>
          <p className="text-2xl font-bold text-red-400">{data.summary.unprofitable_strategies}</p>
        </div>
      </div>

      {/* Profitable Strategies */}
      <div className="bg-slate-900/50 rounded-2xl border border-emerald-500/30 p-6">
        <h3 className="text-lg font-bold mb-4 flex items-center gap-2 text-emerald-400">
          <CheckCircle className="w-5 h-5" />
          Stratégies Rentables
        </h3>
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="text-xs text-slate-500 border-b border-slate-700">
                <th className="text-left py-2 px-3">Stratégie</th>
                <th className="text-right py-2 px-3">Cote Moy.</th>
                <th className="text-right py-2 px-3">BE WR</th>
                <th className="text-right py-2 px-3">WR Réel</th>
                <th className="text-right py-2 px-3">Edge</th>
              </tr>
            </thead>
            <tbody>
              {data.profitable.map((item: any, index: number) => (
                <motion.tr
                  key={index}
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  transition={{ delay: index * 0.05 }}
                  className="border-b border-slate-800 hover:bg-slate-800/30"
                >
                  <td className="py-3 px-3">
                    <span className="font-medium text-white">{item.strategy}</span>
                    <span className="text-xs text-slate-500 ml-2">({item.type})</span>
                  </td>
                  <td className="py-3 px-3 text-right font-mono text-amber-400">
                    @{item.avg_odds?.toFixed(2)}
                  </td>
                  <td className="py-3 px-3 text-right font-mono text-slate-400">
                    {item.breakeven_wr?.toFixed(1)}%
                  </td>
                  <td className="py-3 px-3 text-right font-mono text-emerald-400">
                    {item.actual_wr?.toFixed(1)}%
                  </td>
                  <td className="py-3 px-3 text-right">
                    <span className="font-mono font-bold text-emerald-400">
                      +{item.edge?.toFixed(1)}%
                    </span>
                  </td>
                </motion.tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Unprofitable Strategies */}
      {data.unprofitable.length > 0 && (
        <div className="bg-slate-900/50 rounded-2xl border border-red-500/30 p-6">
          <h3 className="text-lg font-bold mb-4 flex items-center gap-2 text-red-400">
            <XCircle className="w-5 h-5" />
            Sous le Seuil de Rentabilité
          </h3>
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="text-xs text-slate-500 border-b border-slate-700">
                  <th className="text-left py-2 px-3">Stratégie</th>
                  <th className="text-right py-2 px-3">BE WR Requis</th>
                  <th className="text-right py-2 px-3">WR Réel</th>
                  <th className="text-right py-2 px-3">Déficit</th>
                </tr>
              </thead>
              <tbody>
                {data.unprofitable.map((item: any, index: number) => (
                  <motion.tr
                    key={index}
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    transition={{ delay: index * 0.05 }}
                    className="border-b border-slate-800"
                  >
                    <td className="py-3 px-3 text-slate-300">{item.strategy}</td>
                    <td className="py-3 px-3 text-right font-mono text-slate-400">
                      {item.breakeven_wr?.toFixed(1)}%
                    </td>
                    <td className="py-3 px-3 text-right font-mono text-red-400">
                      {item.actual_wr?.toFixed(1)}%
                    </td>
                    <td className="py-3 px-3 text-right font-mono text-red-400">
                      {item.edge?.toFixed(1)}%
                    </td>
                  </motion.tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </motion.div>
  );
}
