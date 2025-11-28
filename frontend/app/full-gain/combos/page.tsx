'use client';

import { useState, useEffect, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Layers,
  TrendingUp,
  Target,
  Zap,
  RefreshCw,
  Plus,
  Minus,
  Calculator,
  Brain,
  AlertTriangle,
  CheckCircle,
  XCircle,
  BarChart3,
  Trophy,
  Shield,
  Flame,
  Star,
  History,
  Save,
  Trash2,
  Clock,
  DollarSign,
  Percent,
  GitBranch
} from 'lucide-react';

// ============================================================
// TYPES
// ============================================================

interface MarketStats {
  market_type: string;
  total_picks: number;
  wins: number;
  losses: number;
  win_rate: number;
  avg_odds: number;
  total_profit: number;
  avg_clv: number;
  tier: string;
  status: string;
}

interface ComboPick {
  market: string;
  odds: number;
  score: number;
  clv: number;
}

interface ComboSuggestion {
  match_name: string;
  home_team: string;
  away_team: string;
  commence_time: string;
  picks: ComboPick[];
  combined_odds: number;
  expected_win_rate: number;
  correlation_score: number;
  recommendation: string;
  risk_level: string;
}

interface ComboHistory {
  id: number;
  combo_id: string;
  selections: any[];
  total_odds: number;
  num_selections: number;
  combined_probability: number;
  kelly_combo: number;
  expected_value: number;
  status: string;
  outcome: string;
  winning_selections: number;
  stake: number;
  profit_loss: number;
  created_at: string;
  resolved_at: string;
}

interface Correlation {
  market_a: string;
  market_b: string;
  sample_size: number;
  wr_a: number;
  wr_b: number;
  both_wr: number;
  lift: number;
}

// ============================================================
// CONSTANTS
// ============================================================

const API_BASE = 'http://91.98.131.218:8001';

const MARKET_LABELS: Record<string, string> = {
  'dc_1x': 'Dom/Nul (1X)',
  'dc_x2': 'Nul/Ext (X2)',
  'dc_12': 'Dom/Ext (12)',
  'over_25': 'Over 2.5',
  'over_15': 'Over 1.5',
  'over_35': 'Over 3.5',
  'under_25': 'Under 2.5',
  'under_15': 'Under 1.5',
  'under_35': 'Under 3.5',
  'under35': 'Under 3.5',
  'btts_yes': 'BTTS Oui',
  'btts_no': 'BTTS Non',
  'home': 'Victoire Dom',
  'away': 'Victoire Ext',
  'draw': 'Match Nul',
  'dnb_home': 'DNB Dom',
  'dnb_away': 'DNB Ext',
};

const TIER_COLORS: Record<string, string> = {
  'S': 'from-yellow-500 to-amber-600',
  'A': 'from-emerald-500 to-green-600',
  'B': 'from-blue-500 to-cyan-600',
  'C': 'from-red-500 to-rose-600',
};

const RISK_COLORS: Record<string, { bg: string; text: string; icon: any }> = {
  'LOW': { bg: 'bg-emerald-500/20', text: 'text-emerald-400', icon: Shield },
  'MEDIUM': { bg: 'bg-amber-500/20', text: 'text-amber-400', icon: AlertTriangle },
  'HIGH': { bg: 'bg-red-500/20', text: 'text-red-400', icon: Flame },
};

// ============================================================
// COMPONENTS
// ============================================================

const StatCard = ({ icon: Icon, label, value, subvalue, color }: {
  icon: any;
  label: string;
  value: string | number;
  subvalue?: string;
  color: string;
}) => (
  <motion.div
    initial={{ opacity: 0, y: 20 }}
    animate={{ opacity: 1, y: 0 }}
    className="bg-slate-800/50 backdrop-blur-sm border border-slate-700/50 rounded-xl p-4"
  >
    <div className="flex items-center gap-2 mb-2">
      <Icon className={`w-4 h-4 ${color}`} />
      <span className="text-slate-400 text-sm">{label}</span>
    </div>
    <div className={`text-2xl font-bold ${color}`}>{value}</div>
    {subvalue && <div className="text-slate-500 text-xs mt-1">{subvalue}</div>}
  </motion.div>
);

const TierBadge = ({ tier }: { tier: string }) => (
  <span className={`px-2 py-0.5 rounded text-xs font-bold bg-gradient-to-r ${TIER_COLORS[tier] || 'from-slate-500 to-slate-600'} text-white`}>
    {tier}
  </span>
);

const RiskBadge = ({ level }: { level: string }) => {
  const config = RISK_COLORS[level] || RISK_COLORS['MEDIUM'];
  const Icon = config.icon;
  return (
    <span className={`flex items-center gap-1 px-2 py-1 rounded-lg text-xs font-semibold ${config.bg} ${config.text}`}>
      <Icon className="w-3 h-3" />
      {level}
    </span>
  );
};

const StatusBadge = ({ status }: { status: string }) => {
  const config: Record<string, { bg: string; text: string }> = {
    'pending': { bg: 'bg-amber-500/20', text: 'text-amber-400' },
    'won': { bg: 'bg-emerald-500/20', text: 'text-emerald-400' },
    'lost': { bg: 'bg-red-500/20', text: 'text-red-400' },
    'partial': { bg: 'bg-blue-500/20', text: 'text-blue-400' },
  };
  const c = config[status] || config['pending'];
  return (
    <span className={`px-2 py-1 rounded text-xs font-semibold ${c.bg} ${c.text} uppercase`}>
      {status}
    </span>
  );
};

// ============================================================
// MAIN PAGE
// ============================================================

export default function CombosPage() {
  // State
  const [suggestions, setSuggestions] = useState<ComboSuggestion[]>([]);
  const [markets, setMarkets] = useState<MarketStats[]>([]);
  const [history, setHistory] = useState<ComboHistory[]>([]);
  const [historyStats, setHistoryStats] = useState<any>({});
  const [correlations, setCorrelations] = useState<Correlation[]>([]);
  const [bestCombos, setBestCombos] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<'suggestions' | 'builder' | 'markets' | 'history' | 'correlations'>('suggestions');
  const [riskFilter, setRiskFilter] = useState<string>('ALL');
  const [stake, setStake] = useState<number>(10);
  const [selectedPicks, setSelectedPicks] = useState<any[]>([]);
  const [saving, setSaving] = useState(false);

  // Fetch data
  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      const [suggestionsRes, marketsRes, historyRes, correlationsRes] = await Promise.all([
        fetch(`${API_BASE}/api/combos/suggestions?limit=20`),
        fetch(`${API_BASE}/api/combos/stats-dynamic`),
        fetch(`${API_BASE}/api/combos/history?limit=50`),
        fetch(`${API_BASE}/api/combos/correlations-dynamic`)
      ]);

      if (suggestionsRes.ok) {
        const data = await suggestionsRes.json();
        setSuggestions(data.suggestions || []);
      }

      if (marketsRes.ok) {
        const data = await marketsRes.json();
        setMarkets(data.markets || []);
      }

      if (historyRes.ok) {
        const data = await historyRes.json();
        setHistory(data.combos || []);
        setHistoryStats(data.stats || {});
      }

      if (correlationsRes.ok) {
        const data = await correlationsRes.json();
        setCorrelations(data.correlations || []);
        setBestCombos(data.best_combos || []);
      }
    } catch (error) {
      console.error('Erreur fetch:', error);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  // Calculer les stats du combo builder
  const comboStats = {
    totalOdds: selectedPicks.reduce((acc, p) => acc * p.odds, 1),
    potentialWin: selectedPicks.length > 0 
      ? stake * selectedPicks.reduce((acc, p) => acc * p.odds, 1) 
      : 0,
    avgScore: selectedPicks.length > 0
      ? selectedPicks.reduce((acc, p) => acc + (p.score || 50), 0) / selectedPicks.length
      : 0
  };

  // Filtrer suggestions par risque
  const filteredSuggestions = riskFilter === 'ALL' 
    ? suggestions 
    : suggestions.filter(s => s.risk_level === riskFilter);

  // Sauvegarder un combo
  const saveCombo = async () => {
    if (selectedPicks.length < 2) return;
    
    setSaving(true);
    try {
      const response = await fetch(`${API_BASE}/api/combos/save`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          selections: selectedPicks.map(p => ({
            match: p.match,
            market: p.market,
            odds: p.odds,
            score: p.score,
            win_rate: p.win_rate || 50
          })),
          total_odds: comboStats.totalOdds,
          stake: stake
        })
      });
      
      const data = await response.json();
      if (data.success) {
        alert(`✅ Combo sauvegardé ! ID: ${data.combo_id}`);
        setSelectedPicks([]);
        fetchData(); // Refresh
      } else {
        alert(`❌ Erreur: ${data.error}`);
      }
    } catch (error) {
      console.error('Erreur save:', error);
    } finally {
      setSaving(false);
    }
  };

  // Ajouter une suggestion au builder
  const addSuggestionToBuilder = (suggestion: ComboSuggestion) => {
    const newPicks = suggestion.picks.map((p, idx) => ({
      id: `${suggestion.match_name}-${p.market}-${idx}`,
      match: suggestion.match_name,
      market: MARKET_LABELS[p.market] || p.market,
      odds: p.odds,
      score: p.score,
      win_rate: suggestion.expected_win_rate / suggestion.picks.length
    }));
    
    setSelectedPicks(prev => {
      const existing = prev.map(p => p.id);
      const toAdd = newPicks.filter(p => !existing.includes(p.id));
      return [...prev, ...toAdd].slice(0, 10);
    });
    
    setActiveTab('builder');
  };

  // Stats globales
  const globalStats = {
    totalSuggestions: suggestions.length,
    lowRisk: suggestions.filter(s => s.risk_level === 'LOW').length,
    mediumRisk: suggestions.filter(s => s.risk_level === 'MEDIUM').length,
    highRisk: suggestions.filter(s => s.risk_level === 'HIGH').length,
    topMarkets: markets.filter(m => m.tier === 'S').length,
    totalCombos: historyStats.total || 0,
    comboWinRate: historyStats.win_rate || 0,
    comboProfit: historyStats.total_profit || 0,
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-950 via-purple-950/20 to-slate-950 p-6">
      <div className="max-w-7xl mx-auto">
        
        {/* 🎯 HEADER */}
        <motion.div
          initial={{ opacity: 0, y: -20 }}
          animate={{ opacity: 1, y: 0 }}
          className="mb-8"
        >
          <div className="flex items-center justify-between flex-wrap gap-4">
            <div>
              <h1 className="text-4xl font-bold bg-gradient-to-r from-purple-400 via-pink-400 to-cyan-400 bg-clip-text text-transparent flex items-center gap-3">
                <Layers className="w-10 h-10 text-purple-400" />
                COMBOS 2.0
              </h1>
              <p className="text-slate-400 mt-1">
                Combinés Intelligents • Données Dynamiques • Historique
              </p>
            </div>
            
            <button
              onClick={fetchData}
              disabled={loading}
              className="flex items-center gap-2 px-4 py-2 bg-purple-600 hover:bg-purple-500 rounded-lg transition-all disabled:opacity-50"
            >
              <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
              Actualiser
            </button>
          </div>
        </motion.div>

        {/* 📊 STATS CARDS */}
        <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-8 gap-3 mb-8">
          <StatCard icon={Brain} label="Suggestions" value={globalStats.totalSuggestions} color="text-purple-400" />
          <StatCard icon={Shield} label="Low Risk" value={globalStats.lowRisk} color="text-emerald-400" />
          <StatCard icon={Flame} label="High Risk" value={globalStats.highRisk} color="text-red-400" />
          <StatCard icon={Trophy} label="S-Tier" value={globalStats.topMarkets} color="text-yellow-400" />
          <StatCard icon={History} label="Historique" value={globalStats.totalCombos} color="text-cyan-400" />
          <StatCard icon={Percent} label="Win Rate" value={`${globalStats.comboWinRate}%`} color="text-emerald-400" />
          <StatCard icon={DollarSign} label="Profit" value={`${globalStats.comboProfit > 0 ? '+' : ''}${globalStats.comboProfit}u`} color={globalStats.comboProfit >= 0 ? "text-emerald-400" : "text-red-400"} />
          <StatCard icon={GitBranch} label="Corrélations" value={correlations.length} color="text-pink-400" />
        </div>

        {/* 🔀 TABS */}
        <div className="flex gap-2 mb-6 overflow-x-auto pb-2">
          {[
            { id: 'suggestions', label: 'Suggestions IA', icon: Brain },
            { id: 'builder', label: `Builder (${selectedPicks.length})`, icon: Calculator },
            { id: 'history', label: 'Historique', icon: History },
            { id: 'markets', label: 'Marchés', icon: BarChart3 },
            { id: 'correlations', label: 'Corrélations', icon: GitBranch },
          ].map(tab => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id as any)}
              className={`flex items-center gap-2 px-4 py-2 rounded-lg font-medium transition-all whitespace-nowrap ${
                activeTab === tab.id
                  ? 'bg-purple-600 text-white'
                  : 'bg-slate-800/50 text-slate-400 hover:bg-slate-700/50'
              }`}
            >
              <tab.icon className="w-4 h-4" />
              {tab.label}
            </button>
          ))}
        </div>

        {/* 📋 CONTENT */}
        <AnimatePresence mode="wait">
          
          {/* TAB: SUGGESTIONS */}
          {activeTab === 'suggestions' && (
            <motion.div
              key="suggestions"
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: 20 }}
            >
              {/* Filtres */}
              <div className="flex gap-2 mb-4">
                {['ALL', 'LOW', 'MEDIUM', 'HIGH'].map(risk => (
                  <button
                    key={risk}
                    onClick={() => setRiskFilter(risk)}
                    className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-all ${
                      riskFilter === risk
                        ? 'bg-purple-600 text-white'
                        : 'bg-slate-800/50 text-slate-400 hover:bg-slate-700/50'
                    }`}
                  >
                    {risk === 'ALL' ? 'Tous' : risk}
                  </button>
                ))}
              </div>

              {/* Liste suggestions */}
              <div className="space-y-4">
                {loading ? (
                  <div className="text-center py-12">
                    <RefreshCw className="w-8 h-8 text-purple-400 animate-spin mx-auto mb-4" />
                    <p className="text-slate-400">Chargement...</p>
                  </div>
                ) : filteredSuggestions.length === 0 ? (
                  <div className="text-center py-12 bg-slate-800/30 rounded-xl">
                    <AlertTriangle className="w-12 h-12 text-amber-400 mx-auto mb-4" />
                    <p className="text-slate-400">Aucune suggestion disponible</p>
                  </div>
                ) : (
                  filteredSuggestions.map((suggestion, idx) => (
                    <motion.div
                      key={idx}
                      initial={{ opacity: 0, y: 20 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ delay: idx * 0.03 }}
                      className="bg-slate-800/50 backdrop-blur-sm border border-slate-700/50 rounded-xl p-5 hover:border-purple-500/30 transition-all"
                    >
                      <div className="flex items-start justify-between mb-4">
                        <div>
                          <h3 className="text-lg font-semibold text-white">{suggestion.match_name}</h3>
                          <p className="text-slate-500 text-sm">
                            {new Date(suggestion.commence_time).toLocaleString('fr-FR', {
                              weekday: 'short', day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit'
                            })}
                          </p>
                        </div>
                        <div className="flex items-center gap-2">
                          <RiskBadge level={suggestion.risk_level} />
                          <button
                            onClick={() => addSuggestionToBuilder(suggestion)}
                            className="p-2 bg-purple-600/20 text-purple-400 rounded-lg hover:bg-purple-600/40 transition-all"
                            title="Ajouter au Builder"
                          >
                            <Plus className="w-4 h-4" />
                          </button>
                        </div>
                      </div>

                      {/* Picks */}
                      <div className="flex flex-wrap gap-2 mb-4">
                        {suggestion.picks.map((pick, pidx) => (
                          <div key={pidx} className="flex items-center gap-2 bg-slate-700/50 rounded-lg px-3 py-2">
                            <span className="text-slate-300 text-sm font-medium">
                              {MARKET_LABELS[pick.market] || pick.market}
                            </span>
                            <span className="text-cyan-400 font-bold">@{pick.odds.toFixed(2)}</span>
                            {pick.score >= 70 && <Star className="w-3 h-3 text-yellow-400" />}
                          </div>
                        ))}
                      </div>

                      {/* Stats */}
                      <div className="grid grid-cols-4 gap-4 p-3 bg-slate-900/50 rounded-lg">
                        <div>
                          <p className="text-slate-500 text-xs">Cote</p>
                          <p className="text-xl font-bold text-cyan-400">{suggestion.combined_odds.toFixed(2)}</p>
                        </div>
                        <div>
                          <p className="text-slate-500 text-xs">Win Rate</p>
                          <p className="text-xl font-bold text-emerald-400">{suggestion.expected_win_rate.toFixed(1)}%</p>
                        </div>
                        <div>
                          <p className="text-slate-500 text-xs">Corrélation</p>
                          <p className={`text-xl font-bold ${suggestion.correlation_score < 0.4 ? 'text-emerald-400' : suggestion.correlation_score < 0.6 ? 'text-amber-400' : 'text-red-400'}`}>
                            {(suggestion.correlation_score * 100).toFixed(0)}%
                          </p>
                        </div>
                        <div>
                          <p className="text-slate-500 text-xs">Gain (10€)</p>
                          <p className="text-xl font-bold text-purple-400">{(10 * suggestion.combined_odds).toFixed(2)}€</p>
                        </div>
                      </div>

                      <div className="mt-3 p-3 bg-gradient-to-r from-purple-900/30 to-pink-900/30 rounded-lg border border-purple-500/20">
                        <p className="text-sm text-slate-300">{suggestion.recommendation}</p>
                      </div>
                    </motion.div>
                  ))
                )}
              </div>
            </motion.div>
          )}

          {/* TAB: BUILDER */}
          {activeTab === 'builder' && (
            <motion.div
              key="builder"
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: 20 }}
              className="grid md:grid-cols-3 gap-6"
            >
              {/* Sélections */}
              <div className="md:col-span-2 bg-slate-800/50 backdrop-blur-sm border border-slate-700/50 rounded-xl p-5">
                <h3 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
                  <Layers className="w-5 h-5 text-purple-400" />
                  Sélections ({selectedPicks.length}/10)
                </h3>
                
                {selectedPicks.length > 0 ? (
                  <div className="space-y-2">
                    {selectedPicks.map((pick, idx) => (
                      <div key={pick.id} className="flex items-center justify-between p-3 bg-slate-700/50 rounded-lg">
                        <div>
                          <p className="text-white font-medium">{pick.match}</p>
                          <p className="text-slate-400 text-sm">{pick.market}</p>
                        </div>
                        <div className="flex items-center gap-3">
                          <span className="text-cyan-400 font-bold">@{pick.odds.toFixed(2)}</span>
                          <button
                            onClick={() => setSelectedPicks(prev => prev.filter(p => p.id !== pick.id))}
                            className="p-1.5 bg-red-500/20 text-red-400 rounded hover:bg-red-500/30"
                          >
                            <Trash2 className="w-4 h-4" />
                          </button>
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="text-center py-8 text-slate-500">
                    <Layers className="w-12 h-12 mx-auto mb-4 opacity-30" />
                    <p>Ajoutez des sélections depuis les Suggestions</p>
                  </div>
                )}
              </div>

              {/* Calculateur */}
              <div className="bg-slate-800/50 backdrop-blur-sm border border-slate-700/50 rounded-xl p-5">
                <h3 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
                  <Calculator className="w-5 h-5 text-cyan-400" />
                  Calculateur
                </h3>

                <div className="space-y-4">
                  <div>
                    <label className="text-slate-400 text-sm">Mise (€)</label>
                    <input
                      type="number"
                      value={stake}
                      onChange={(e) => setStake(Number(e.target.value))}
                      min={1}
                      max={1000}
                      className="w-full mt-1 px-3 py-2 bg-slate-900/50 border border-slate-600 rounded-lg text-white focus:border-purple-500 focus:outline-none"
                    />
                  </div>

                  <div className="p-4 bg-gradient-to-br from-purple-900/30 to-cyan-900/30 rounded-lg space-y-3">
                    <div className="flex justify-between">
                      <span className="text-slate-400">Sélections</span>
                      <span className="text-white font-bold">{selectedPicks.length}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-slate-400">Cote Totale</span>
                      <span className="text-cyan-400 font-bold">{comboStats.totalOdds.toFixed(2)}</span>
                    </div>
                    <hr className="border-slate-700" />
                    <div className="flex justify-between">
                      <span className="text-slate-300 font-medium">Gain Potentiel</span>
                      <span className="text-2xl font-bold text-yellow-400">{comboStats.potentialWin.toFixed(2)}€</span>
                    </div>
                  </div>

                  <button
                    onClick={saveCombo}
                    disabled={selectedPicks.length < 2 || saving}
                    className="w-full py-3 bg-gradient-to-r from-purple-600 to-cyan-600 rounded-lg font-bold text-white disabled:opacity-50 disabled:cursor-not-allowed hover:from-purple-500 hover:to-cyan-500 transition-all flex items-center justify-center gap-2"
                  >
                    {saving ? <RefreshCw className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />}
                    {saving ? 'Sauvegarde...' : 'Sauvegarder le Combo'}
                  </button>
                </div>
              </div>
            </motion.div>
          )}

          {/* TAB: HISTORY */}
          {activeTab === 'history' && (
            <motion.div
              key="history"
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: 20 }}
            >
              {/* Stats historique */}
              <div className="grid grid-cols-2 md:grid-cols-5 gap-4 mb-6">
                <div className="bg-slate-800/50 rounded-xl p-4 text-center">
                  <p className="text-slate-400 text-sm">Total</p>
                  <p className="text-2xl font-bold text-white">{historyStats.total || 0}</p>
                </div>
                <div className="bg-emerald-500/10 border border-emerald-500/30 rounded-xl p-4 text-center">
                  <p className="text-emerald-400 text-sm">Gagnés</p>
                  <p className="text-2xl font-bold text-emerald-400">{historyStats.won || 0}</p>
                </div>
                <div className="bg-red-500/10 border border-red-500/30 rounded-xl p-4 text-center">
                  <p className="text-red-400 text-sm">Perdus</p>
                  <p className="text-2xl font-bold text-red-400">{historyStats.lost || 0}</p>
                </div>
                <div className="bg-amber-500/10 border border-amber-500/30 rounded-xl p-4 text-center">
                  <p className="text-amber-400 text-sm">En cours</p>
                  <p className="text-2xl font-bold text-amber-400">{historyStats.pending || 0}</p>
                </div>
                <div className={`${(historyStats.total_profit || 0) >= 0 ? 'bg-emerald-500/10 border-emerald-500/30' : 'bg-red-500/10 border-red-500/30'} border rounded-xl p-4 text-center`}>
                  <p className="text-slate-400 text-sm">Profit Total</p>
                  <p className={`text-2xl font-bold ${(historyStats.total_profit || 0) >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                    {(historyStats.total_profit || 0) >= 0 ? '+' : ''}{historyStats.total_profit || 0}u
                  </p>
                </div>
              </div>

              {/* Liste historique */}
              {history.length === 0 ? (
                <div className="text-center py-12 bg-slate-800/30 rounded-xl">
                  <History className="w-12 h-12 text-slate-500 mx-auto mb-4" />
                  <p className="text-slate-400">Aucun combo enregistré</p>
                  <p className="text-slate-500 text-sm mt-1">Sauvegardez des combos depuis le Builder</p>
                </div>
              ) : (
                <div className="space-y-3">
                  {history.map((combo, idx) => (
                    <motion.div
                      key={combo.id}
                      initial={{ opacity: 0, y: 10 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ delay: idx * 0.03 }}
                      className="bg-slate-800/50 border border-slate-700/50 rounded-xl p-4"
                    >
                      <div className="flex items-center justify-between mb-3">
                        <div className="flex items-center gap-3">
                          <StatusBadge status={combo.status} />
                          <span className="text-slate-400 text-sm">
                            {combo.num_selections} sélections
                          </span>
                          <span className="text-cyan-400 font-bold">
                            @{Number(combo.total_odds).toFixed(2)}
                          </span>
                        </div>
                        <div className="text-right">
                          {combo.profit_loss !== null && (
                            <span className={`text-lg font-bold ${Number(combo.profit_loss) >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                              {Number(combo.profit_loss) >= 0 ? '+' : ''}{Number(combo.profit_loss).toFixed(2)}u
                            </span>
                          )}
                        </div>
                      </div>
                      
                      {/* Sélections */}
                      <div className="flex flex-wrap gap-2 mb-3">
                        {(typeof combo.selections === 'string' ? JSON.parse(combo.selections) : combo.selections).map((sel: any, sidx: number) => (
                          <span key={sidx} className="text-xs bg-slate-700/50 px-2 py-1 rounded text-slate-300">
                            {sel.match} - {sel.market}
                          </span>
                        ))}
                      </div>

                      <div className="flex items-center justify-between text-xs text-slate-500">
                        <span>
                          <Clock className="w-3 h-3 inline mr-1" />
                          {new Date(combo.created_at).toLocaleString('fr-FR')}
                        </span>
                        <span>
                          Mise: {Number(combo.stake).toFixed(0)}€ | EV: {Number(combo.expected_value).toFixed(2)}
                        </span>
                      </div>
                    </motion.div>
                  ))}
                </div>
              )}
            </motion.div>
          )}

          {/* TAB: MARKETS */}
          {activeTab === 'markets' && (
            <motion.div
              key="markets"
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: 20 }}
            >
              <div className="mb-4 p-3 bg-emerald-500/10 border border-emerald-500/30 rounded-lg">
                <p className="text-emerald-400 text-sm">
                  📊 Données DYNAMIQUES - Calculées depuis {markets.reduce((a, m) => a + m.total_picks, 0)} picks réels
                </p>
              </div>
              
              <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
                {markets.map((market, idx) => (
                  <motion.div
                    key={market.market_type}
                    initial={{ opacity: 0, scale: 0.95 }}
                    animate={{ opacity: 1, scale: 1 }}
                    transition={{ delay: idx * 0.03 }}
                    className={`bg-slate-800/50 border rounded-xl p-4 ${
                      market.tier === 'S' ? 'border-yellow-500/50' :
                      market.tier === 'A' ? 'border-emerald-500/50' :
                      market.tier === 'B' ? 'border-blue-500/50' :
                      'border-red-500/50'
                    }`}
                  >
                    <div className="flex items-center justify-between mb-3">
                      <h4 className="text-white font-semibold">
                        {MARKET_LABELS[market.market_type] || market.market_type}
                      </h4>
                      <TierBadge tier={market.tier} />
                    </div>

                    <div className="grid grid-cols-2 gap-3 text-sm">
                      <div>
                        <p className="text-slate-500">Win Rate</p>
                        <p className={`font-bold ${market.win_rate >= 60 ? 'text-emerald-400' : market.win_rate >= 40 ? 'text-amber-400' : 'text-red-400'}`}>
                          {market.win_rate}%
                        </p>
                      </div>
                      <div>
                        <p className="text-slate-500">Profit</p>
                        <p className={`font-bold ${market.total_profit > 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                          {market.total_profit > 0 ? '+' : ''}{market.total_profit}u
                        </p>
                      </div>
                      <div>
                        <p className="text-slate-500">Picks</p>
                        <p className="text-white font-bold">{market.total_picks}</p>
                      </div>
                      <div>
                        <p className="text-slate-500">CLV Moy.</p>
                        <p className={`font-bold ${(market.avg_clv || 0) > 0 ? 'text-cyan-400' : 'text-slate-400'}`}>
                          {market.avg_clv > 0 ? '+' : ''}{market.avg_clv || 0}%
                        </p>
                      </div>
                    </div>

                    <div className="mt-3 pt-3 border-t border-slate-700">
                      <span className="text-xs">{market.status}</span>
                    </div>
                  </motion.div>
                ))}
              </div>
            </motion.div>
          )}

          {/* TAB: CORRELATIONS */}
          {activeTab === 'correlations' && (
            <motion.div
              key="correlations"
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: 20 }}
            >
              {/* Best combos */}
              {bestCombos.length > 0 && (
                <div className="mb-6">
                  <h3 className="text-lg font-semibold text-white mb-3 flex items-center gap-2">
                    <Trophy className="w-5 h-5 text-yellow-400" />
                    Meilleurs Combos (Synergie Positive)
                  </h3>
                  <div className="grid md:grid-cols-3 gap-3">
                    {bestCombos.map((combo, idx) => (
                      <div key={idx} className="bg-emerald-500/10 border border-emerald-500/30 rounded-lg p-4">
                        <p className="text-white font-semibold">{combo.pair}</p>
                        <div className="flex justify-between mt-2 text-sm">
                          <span className="text-emerald-400">WR: {combo.win_rate}%</span>
                          <span className="text-cyan-400">Lift: {combo.lift}x</span>
                          <span className="text-slate-400">n={combo.sample}</span>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Table correlations */}
              <h3 className="text-lg font-semibold text-white mb-3">
                Matrice de Corrélations ({correlations.length} paires)
              </h3>
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="text-slate-400 border-b border-slate-700">
                      <th className="text-left p-3">Marché A</th>
                      <th className="text-left p-3">Marché B</th>
                      <th className="text-center p-3">WR A</th>
                      <th className="text-center p-3">WR B</th>
                      <th className="text-center p-3">WR Combo</th>
                      <th className="text-center p-3">Lift</th>
                      <th className="text-center p-3">Sample</th>
                    </tr>
                  </thead>
                  <tbody>
                    {correlations.slice(0, 20).map((c, idx) => (
                      <tr key={idx} className="border-b border-slate-800 hover:bg-slate-800/30">
                        <td className="p-3 text-white">{MARKET_LABELS[c.market_a] || c.market_a}</td>
                        <td className="p-3 text-white">{MARKET_LABELS[c.market_b] || c.market_b}</td>
                        <td className="p-3 text-center text-slate-300">{c.wr_a}%</td>
                        <td className="p-3 text-center text-slate-300">{c.wr_b}%</td>
                        <td className="p-3 text-center">
                          <span className={`font-bold ${c.both_wr >= 30 ? 'text-emerald-400' : c.both_wr >= 15 ? 'text-amber-400' : 'text-red-400'}`}>
                            {c.both_wr}%
                          </span>
                        </td>
                        <td className="p-3 text-center">
                          <span className={`font-bold ${c.lift >= 1.2 ? 'text-emerald-400' : c.lift >= 0.8 ? 'text-slate-300' : 'text-red-400'}`}>
                            {c.lift}x
                          </span>
                        </td>
                        <td className="p-3 text-center text-slate-500">{c.sample_size}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              {/* Légende */}
              <div className="mt-4 p-4 bg-slate-800/30 rounded-xl">
                <h4 className="text-white font-semibold mb-2">📊 Interprétation du Lift</h4>
                <div className="flex flex-wrap gap-4 text-sm">
                  <span className="text-emerald-400">🟢 Lift &gt; 1.2 = Synergie positive</span>
                  <span className="text-slate-400">⚪ Lift 0.8-1.2 = Indépendant</span>
                  <span className="text-red-400">🔴 Lift &lt; 0.8 = Anti-corrélation</span>
                </div>
              </div>
            </motion.div>
          )}

        </AnimatePresence>
      </div>
    </div>
  );
}
