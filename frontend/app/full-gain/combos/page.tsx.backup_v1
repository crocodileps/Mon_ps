'use client';

import { useState, useEffect, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Layers,
  TrendingUp,
  Target,
  Zap,
  RefreshCw,
  ChevronDown,
  ChevronUp,
  Plus,
  Minus,
  Calculator,
  Brain,
  AlertTriangle,
  CheckCircle,
  XCircle,
  Sparkles,
  BarChart3,
  Grid3X3,
  Trophy,
  Shield,
  Flame,
  Star,
  ArrowRight,
  Info
} from 'lucide-react';

// ============================================================
// TYPES
// ============================================================

interface MarketStats {
  market_type: string;
  total_picks: number;
  wins: number;
  win_rate: number;
  avg_odds: number;
  total_profit: number;
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

interface SelectedPick {
  id: string;
  match: string;
  market: string;
  odds: number;
  score: number;
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

// 📊 Stat Card
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

// 🏆 Market Tier Badge
const TierBadge = ({ tier }: { tier: string }) => (
  <span className={`px-2 py-0.5 rounded text-xs font-bold bg-gradient-to-r ${TIER_COLORS[tier] || 'from-slate-500 to-slate-600'} text-white`}>
    {tier}
  </span>
);

// 🎯 Risk Badge
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

// ============================================================
// MAIN PAGE
// ============================================================

export default function CombosPage() {
  // State
  const [suggestions, setSuggestions] = useState<ComboSuggestion[]>([]);
  const [markets, setMarkets] = useState<MarketStats[]>([]);
  const [selectedPicks, setSelectedPicks] = useState<SelectedPick[]>([]);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<'suggestions' | 'builder' | 'markets'>('suggestions');
  const [riskFilter, setRiskFilter] = useState<string>('ALL');
  const [stake, setStake] = useState<number>(10);

  // Fetch data
  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      const [suggestionsRes, marketsRes] = await Promise.all([
        fetch(`${API_BASE}/api/combos/suggestions?limit=20`),
        fetch(`${API_BASE}/api/combos/profitable-markets`)
      ]);

      if (suggestionsRes.ok) {
        const data = await suggestionsRes.json();
        setSuggestions(data.suggestions || []);
      }

      if (marketsRes.ok) {
        const data = await marketsRes.json();
        setMarkets(data.markets || []);
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
      ? selectedPicks.reduce((acc, p) => acc + p.score, 0) / selectedPicks.length
      : 0
  };

  // Filtrer suggestions par risque
  const filteredSuggestions = riskFilter === 'ALL' 
    ? suggestions 
    : suggestions.filter(s => s.risk_level === riskFilter);

  // Ajouter/Retirer un pick
  const togglePick = (pick: SelectedPick) => {
    setSelectedPicks(prev => {
      const exists = prev.find(p => p.id === pick.id);
      if (exists) {
        return prev.filter(p => p.id !== pick.id);
      }
      if (prev.length >= 10) return prev;
      return [...prev, pick];
    });
  };

  // Stats globales
  const globalStats = {
    totalSuggestions: suggestions.length,
    lowRisk: suggestions.filter(s => s.risk_level === 'LOW').length,
    mediumRisk: suggestions.filter(s => s.risk_level === 'MEDIUM').length,
    highRisk: suggestions.filter(s => s.risk_level === 'HIGH').length,
    topMarkets: markets.filter(m => m.tier === 'S').length,
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
                Combinés Intelligents • Corrélations • Value Betting
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
        <div className="grid grid-cols-2 md:grid-cols-5 gap-4 mb-8">
          <StatCard
            icon={Layers}
            label="Suggestions"
            value={globalStats.totalSuggestions}
            color="text-purple-400"
          />
          <StatCard
            icon={Shield}
            label="Low Risk"
            value={globalStats.lowRisk}
            color="text-emerald-400"
          />
          <StatCard
            icon={AlertTriangle}
            label="Medium Risk"
            value={globalStats.mediumRisk}
            color="text-amber-400"
          />
          <StatCard
            icon={Flame}
            label="High Risk"
            value={globalStats.highRisk}
            color="text-red-400"
          />
          <StatCard
            icon={Trophy}
            label="Marchés S-Tier"
            value={globalStats.topMarkets}
            color="text-yellow-400"
          />
        </div>

        {/* 🔀 TABS */}
        <div className="flex gap-2 mb-6 overflow-x-auto pb-2">
          {[
            { id: 'suggestions', label: 'Suggestions IA', icon: Brain },
            { id: 'builder', label: 'Combo Builder', icon: Calculator },
            { id: 'markets', label: 'Marchés Rentables', icon: BarChart3 },
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
          {/* TAB: SUGGESTIONS IA */}
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
                    <p className="text-slate-400">Chargement des suggestions...</p>
                  </div>
                ) : filteredSuggestions.length === 0 ? (
                  <div className="text-center py-12 bg-slate-800/30 rounded-xl">
                    <AlertTriangle className="w-12 h-12 text-amber-400 mx-auto mb-4" />
                    <p className="text-slate-400">Aucune suggestion disponible</p>
                    <p className="text-slate-500 text-sm mt-1">Les suggestions sont générées à partir des picks trackés</p>
                  </div>
                ) : (
                  filteredSuggestions.map((suggestion, idx) => (
                    <motion.div
                      key={idx}
                      initial={{ opacity: 0, y: 20 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ delay: idx * 0.05 }}
                      className="bg-slate-800/50 backdrop-blur-sm border border-slate-700/50 rounded-xl p-5 hover:border-purple-500/30 transition-all"
                    >
                      <div className="flex items-start justify-between mb-4">
                        <div>
                          <h3 className="text-lg font-semibold text-white">
                            {suggestion.match_name}
                          </h3>
                          <p className="text-slate-500 text-sm">
                            {new Date(suggestion.commence_time).toLocaleString('fr-FR', {
                              weekday: 'short',
                              day: 'numeric',
                              month: 'short',
                              hour: '2-digit',
                              minute: '2-digit'
                            })}
                          </p>
                        </div>
                        <RiskBadge level={suggestion.risk_level} />
                      </div>

                      {/* Picks du combo */}
                      <div className="flex flex-wrap gap-2 mb-4">
                        {suggestion.picks.map((pick, pidx) => (
                          <div
                            key={pidx}
                            className="flex items-center gap-2 bg-slate-700/50 rounded-lg px-3 py-2"
                          >
                            <span className="text-slate-300 text-sm font-medium">
                              {MARKET_LABELS[pick.market] || pick.market}
                            </span>
                            <span className="text-cyan-400 font-bold">
                              @{pick.odds.toFixed(2)}
                            </span>
                            {pick.score >= 70 && (
                              <Star className="w-3 h-3 text-yellow-400" />
                            )}
                          </div>
                        ))}
                      </div>

                      {/* Stats du combo */}
                      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 p-3 bg-slate-900/50 rounded-lg">
                        <div>
                          <p className="text-slate-500 text-xs">Cote Combinée</p>
                          <p className="text-xl font-bold text-cyan-400">
                            {suggestion.combined_odds.toFixed(2)}
                          </p>
                        </div>
                        <div>
                          <p className="text-slate-500 text-xs">Win Rate Estimé</p>
                          <p className="text-xl font-bold text-emerald-400">
                            {suggestion.expected_win_rate.toFixed(1)}%
                          </p>
                        </div>
                        <div>
                          <p className="text-slate-500 text-xs">Corrélation</p>
                          <p className={`text-xl font-bold ${
                            suggestion.correlation_score < 0.4 ? 'text-emerald-400' :
                            suggestion.correlation_score < 0.6 ? 'text-amber-400' :
                            'text-red-400'
                          }`}>
                            {(suggestion.correlation_score * 100).toFixed(0)}%
                          </p>
                        </div>
                        <div>
                          <p className="text-slate-500 text-xs">Gain (10€)</p>
                          <p className="text-xl font-bold text-purple-400">
                            {(10 * suggestion.combined_odds).toFixed(2)}€
                          </p>
                        </div>
                      </div>

                      {/* Recommandation */}
                      <div className="mt-4 p-3 bg-gradient-to-r from-purple-900/30 to-pink-900/30 rounded-lg border border-purple-500/20">
                        <p className="text-sm text-slate-300">{suggestion.recommendation}</p>
                      </div>
                    </motion.div>
                  ))
                )}
              </div>
            </motion.div>
          )}

          {/* TAB: COMBO BUILDER */}
          {activeTab === 'builder' && (
            <motion.div
              key="builder"
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: 20 }}
              className="grid md:grid-cols-3 gap-6"
            >
              {/* Sélection */}
              <div className="md:col-span-2 bg-slate-800/50 backdrop-blur-sm border border-slate-700/50 rounded-xl p-5">
                <h3 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
                  <Plus className="w-5 h-5 text-purple-400" />
                  Construire votre Combiné
                </h3>
                
                <div className="mb-4 p-4 bg-slate-900/50 rounded-lg border border-dashed border-slate-600">
                  <p className="text-slate-400 text-sm text-center">
                    <Info className="w-4 h-4 inline mr-2" />
                    Sélectionnez des picks depuis la page Full Gain pour les ajouter ici
                  </p>
                </div>

                {selectedPicks.length > 0 ? (
                  <div className="space-y-2">
                    {selectedPicks.map((pick, idx) => (
                      <div
                        key={pick.id}
                        className="flex items-center justify-between p-3 bg-slate-700/50 rounded-lg"
                      >
                        <div>
                          <p className="text-white font-medium">{pick.match}</p>
                          <p className="text-slate-400 text-sm">{pick.market}</p>
                        </div>
                        <div className="flex items-center gap-3">
                          <span className="text-cyan-400 font-bold">@{pick.odds.toFixed(2)}</span>
                          <button
                            onClick={() => togglePick(pick)}
                            className="p-1.5 bg-red-500/20 text-red-400 rounded hover:bg-red-500/30"
                          >
                            <Minus className="w-4 h-4" />
                          </button>
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="text-slate-500 text-center py-8">
                    Aucun pick sélectionné
                  </p>
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
                      <span className="text-cyan-400 font-bold">
                        {comboStats.totalOdds.toFixed(2)}
                      </span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-slate-400">Score Moyen</span>
                      <span className="text-emerald-400 font-bold">
                        {comboStats.avgScore.toFixed(0)}%
                      </span>
                    </div>
                    <hr className="border-slate-700" />
                    <div className="flex justify-between">
                      <span className="text-slate-300 font-medium">Gain Potentiel</span>
                      <span className="text-2xl font-bold text-yellow-400">
                        {comboStats.potentialWin.toFixed(2)}€
                      </span>
                    </div>
                  </div>

                  <button
                    disabled={selectedPicks.length < 2}
                    className="w-full py-3 bg-gradient-to-r from-purple-600 to-cyan-600 rounded-lg font-bold text-white disabled:opacity-50 disabled:cursor-not-allowed hover:from-purple-500 hover:to-cyan-500 transition-all"
                  >
                    <Zap className="w-4 h-4 inline mr-2" />
                    Valider le Combiné
                  </button>
                </div>
              </div>
            </motion.div>
          )}

          {/* TAB: MARCHÉS RENTABLES */}
          {activeTab === 'markets' && (
            <motion.div
              key="markets"
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: 20 }}
            >
              <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
                {markets.map((market, idx) => (
                  <motion.div
                    key={market.market_type}
                    initial={{ opacity: 0, scale: 0.95 }}
                    animate={{ opacity: 1, scale: 1 }}
                    transition={{ delay: idx * 0.03 }}
                    className={`bg-slate-800/50 backdrop-blur-sm border rounded-xl p-4 ${
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
                        <p className={`font-bold ${
                          market.win_rate >= 60 ? 'text-emerald-400' :
                          market.win_rate >= 40 ? 'text-amber-400' :
                          'text-red-400'
                        }`}>
                          {market.win_rate}%
                        </p>
                      </div>
                      <div>
                        <p className="text-slate-500">Profit</p>
                        <p className={`font-bold ${
                          market.total_profit > 0 ? 'text-emerald-400' : 'text-red-400'
                        }`}>
                          {market.total_profit > 0 ? '+' : ''}{market.total_profit}u
                        </p>
                      </div>
                      <div>
                        <p className="text-slate-500">Picks</p>
                        <p className="text-white font-bold">{market.total_picks}</p>
                      </div>
                      <div>
                        <p className="text-slate-500">Cote Moy.</p>
                        <p className="text-cyan-400 font-bold">{market.avg_odds}</p>
                      </div>
                    </div>

                    <div className="mt-3 pt-3 border-t border-slate-700">
                      <span className="text-xs">{market.status}</span>
                    </div>
                  </motion.div>
                ))}
              </div>

              {/* Légende */}
              <div className="mt-6 p-4 bg-slate-800/30 rounded-xl">
                <h4 className="text-white font-semibold mb-3">📊 Légende des Tiers</h4>
                <div className="flex flex-wrap gap-4 text-sm">
                  <div className="flex items-center gap-2">
                    <TierBadge tier="S" />
                    <span className="text-slate-400">Top performers (+10u)</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <TierBadge tier="A" />
                    <span className="text-slate-400">Profitables (0-10u)</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <TierBadge tier="B" />
                    <span className="text-slate-400">Neutres (-10 à 0u)</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <TierBadge tier="C" />
                    <span className="text-slate-400">À éviter (-10u)</span>
                  </div>
                </div>
              </div>
            </motion.div>
          )}
        </AnimatePresence>

      </div>
    </div>
  );
}
