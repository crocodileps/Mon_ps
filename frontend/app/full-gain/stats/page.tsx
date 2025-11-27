"use client";

import React, { useState, useEffect, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  TrendingUp, TrendingDown, Target, Percent, DollarSign,
  BarChart3, PieChart, Activity, AlertTriangle, RefreshCw,
  Zap, Brain, GitBranch, Calculator, Flame, Snowflake,
  Trophy, AlertCircle, ArrowUpRight, ArrowDownRight, Minus,
  CheckCircle, Clock, Play, RotateCcw, Info
} from "lucide-react";
import {
  BarChart, Bar, AreaChart, Area, XAxis, YAxis,
  CartesianGrid, Tooltip, ResponsiveContainer, Cell,
  LineChart, Line, ScatterChart, Scatter, ZAxis,
  RadarChart, Radar, PolarGrid, PolarAngleAxis, PolarRadiusAxis
} from "recharts";

// ============================================================
// TYPES
// ============================================================

interface GlobalPerformance {
  total_matches: number;
  total_predictions: number;
  resolved_predictions: number;
  wins: number;
  losses: number;
  win_rate: number;
  roi_pct: number;
  total_profit: number;
  avg_clv: number;
  clv_positive_rate: number;
}

interface MarketPerformance {
  market_type: string;
  total_predictions: number;
  resolved: number;
  wins: number;
  losses: number;
  win_rate: number;
  roi_pct: number;
  avg_clv: number;
  avg_kelly: number;
  current_streak: number;
}

interface DailyPerformance {
  date: string;
  wins: number;
  losses: number;
  total_profit: number;
  cumulative_profit: number;
}

interface Alert {
  alert_type: string;
  subject: string;
  message: string;
  severity: string;
}

interface Combo {
  market_a: string;
  market_b: string;
  both_win_rate: number;
  correlation: number;
}

interface CLVStats {
  avg_clv: number;
  std_clv: number;
  median_clv: number;
  positive_rate: number;
  beat_closing_rate: number;
  clv_sharpe: number;
  total_clv_edge: number;
}

interface CLVByTiming {
  timing_window: string;
  total_picks: number;
  avg_clv: number;
  beat_closing_rate: number;
}

interface CLVByMarket {
  market_type: string;
  total_picks: number;
  avg_clv: number;
  positive_rate: number;
  beat_closing_rate: number;
}

interface RiskMetrics {
  sharpe_ratio: number;
  sortino_ratio: number;
  max_drawdown_pct: number;
  max_drawdown_duration_days: number;
  current_drawdown_pct: number;
  profit_factor: number;
  win_loss_ratio: number;
  kelly_optimal: number;
  volatility: number;
}

interface KellyResult {
  kelly_full_pct: number;
  kelly_recommended_pct: number;
  stake_units: number;
  stake_pct_of_bankroll: number;
  risk_of_ruin_pct: number;
}

interface EVResult {
  ev_units: number;
  is_positive_ev: boolean;
  edge_pct: number;
  required_win_rate: number;
  breakeven_odds: number;
  value_rating: string;
}

interface MonteCarloResult {
  simulations: number;
  expected_profit: number;
  median_profit: number;
  percentile_5_worst_case: number;
  percentile_95_best_case: number;
  probability_profit_pct: number;
  probability_double_pct: number;
  probability_ruin_pct: number;
  avg_max_drawdown_pct: number;
}

interface BiasReport {
  type: string;
  severity: string;
  description: string;
  impact_estimate: number;
  recommendation: string;
}

// ============================================================

// Sweet Spot Types
interface SweetSpotPick {
  match_id: string;
  home_team: string;
  away_team: string;
  match_name: string;
  market_type: string;
  score: number;
  odds: number;
  probability: number;
  edge_pct: number;
  kelly_pct: number;
  recommendation: string;
  factors: Record<string, any>;
  commence_time: string;
}

interface SweetSpotStats {
  global: {
    total_picks: number;
    resolved: number;
    wins: number;
    losses: number;
    win_rate: number;
    roi_pct: number;
    avg_score: number;
    avg_edge: number;
    avg_odds: number;
    total_profit: number;
  };
  by_market: Array<{
    market_type: string;
    total: number;
    resolved: number;
    wins: number;
    win_rate: number;
    avg_edge: number;
    profit: number;
  }>;
}

interface SweetSpotUpcoming {
  matches: Array<{
    match_name: string;
    home_team: string;
    away_team: string;
    commence_time: string;
    picks: Array<{
      market_type: string;
      score: number;
      odds: number;
      edge_pct: number;
      kelly_pct: number;
      recommendation: string;
    }>;
  }>;
  total_matches: number;
  total_picks: number;
}

// CONSTANTS
// ============================================================

const TABS = [
  { id: "sweetspot", label: "🎯 Sweet Spot", icon: Target },
  { id: "dashboard", label: "Dashboard", icon: BarChart3 },
  { id: "markets", label: "Par Marché", icon: PieChart },
  { id: "clv", label: "CLV", icon: TrendingUp },
  { id: "correlations", label: "Corrélations", icon: GitBranch },
  { id: "pro", label: "Pro Tools", icon: Brain },
];

const PERIODS = [
  { value: 7, label: "7j" },
  { value: 30, label: "30j" },
  { value: 90, label: "90j" },
  { value: 365, label: "1an" },
];

const MARKET_LABELS: Record<string, string> = {
  home: "Victoire Dom", away: "Victoire Ext", draw: "Match Nul",
  dc_1x: "DC 1X", dc_x2: "DC X2", dc_12: "DC 12",
  btts_yes: "BTTS Oui", btts_no: "BTTS Non",
  over_15: "Over 1.5", under_15: "Under 1.5",
  over_25: "Over 2.5", under_25: "Under 2.5",
  over_35: "Over 3.5", under_35: "Under 3.5",
  over15: "Over 1.5", under15: "Under 1.5",
  over25: "Over 2.5", under25: "Under 2.5",
  over35: "Over 3.5", under35: "Under 3.5",
  dnb_home: "DNB Dom", dnb_away: "DNB Ext",
};

const MARKETS_LIST = Object.keys(MARKET_LABELS);
const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://91.98.131.218:8001";

// ============================================================
// COMPONENTS RÉUTILISABLES
// ============================================================

// KPI Card
interface KPICardProps {
  title: string;
  value: string | number;
  subtitle?: string;
  trend?: number;
  icon: React.ElementType;
  color: string;
  loading?: boolean;
}

const KPICard: React.FC<KPICardProps> = ({ title, value, subtitle, trend, icon: Icon, color, loading }) => {
  const colorClasses: Record<string, string> = {
    cyan: "from-cyan-500/20 to-cyan-600/10 border-cyan-500/30",
    violet: "from-violet-500/20 to-violet-600/10 border-violet-500/30",
    green: "from-green-500/20 to-green-600/10 border-green-500/30",
    emerald: "from-emerald-500/20 to-emerald-600/10 border-emerald-500/30",
    amber: "from-amber-500/20 to-amber-600/10 border-amber-500/30",
    red: "from-red-500/20 to-red-600/10 border-red-500/30",
    blue: "from-blue-500/20 to-blue-600/10 border-blue-500/30",
  };

  const iconColors: Record<string, string> = {
    cyan: "text-cyan-400 bg-cyan-500/20",
    violet: "text-violet-400 bg-violet-500/20",
    green: "text-green-400 bg-green-500/20",
    emerald: "text-emerald-400 bg-emerald-500/20",
    amber: "text-amber-400 bg-amber-500/20",
    red: "text-red-400 bg-red-500/20",
    blue: "text-blue-400 bg-blue-500/20",
  };

  return (
    <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}
      className={`relative overflow-hidden rounded-2xl p-5 bg-gradient-to-br ${colorClasses[color]} border backdrop-blur-xl`}>
      <div className={`inline-flex p-2.5 rounded-xl ${iconColors[color]} mb-3`}>
        <Icon className="w-5 h-5" />
      </div>
      <p className="text-gray-400 text-sm font-medium mb-1">{title}</p>
      {loading ? (
        <div className="h-8 w-24 bg-gray-700 animate-pulse rounded" />
      ) : (
        <div className="flex items-end gap-2">
          <p className="text-2xl font-bold text-white">{value}</p>
          {trend !== undefined && (
            trend > 0 ? <ArrowUpRight className="w-4 h-4 text-green-400" /> :
            trend < 0 ? <ArrowDownRight className="w-4 h-4 text-red-400" /> :
            <Minus className="w-4 h-4 text-gray-400" />
          )}
        </div>
      )}
      {subtitle && <p className="text-gray-500 text-xs mt-1">{subtitle}</p>}
    </motion.div>
  );
};

// Alert Card
const AlertCard: React.FC<{ alert: Alert }> = ({ alert }) => {
  const severityStyles: Record<string, string> = {
    high: "border-red-500/50 bg-red-500/10",
    medium: "border-yellow-500/50 bg-yellow-500/10",
    info: "border-cyan-500/50 bg-cyan-500/10",
  };
  const Icon = alert.severity === "high" ? AlertTriangle : AlertCircle;
  return (
    <div className={`p-3 rounded-xl border ${severityStyles[alert.severity] || severityStyles.info} flex items-start gap-3`}>
      <Icon className={`w-4 h-4 mt-0.5 ${alert.severity === "high" ? "text-red-400" : alert.severity === "medium" ? "text-yellow-400" : "text-cyan-400"}`} />
      <div>
        <p className="font-medium text-white text-sm">{alert.subject}</p>
        <p className="text-gray-400 text-xs mt-0.5">{alert.message}</p>
      </div>
    </div>
  );
};

// Market Row
const MarketRow: React.FC<{ market: MarketPerformance; rank: number }> = ({ market, rank }) => {
  const streak = market.current_streak || 0;
  return (
    <tr className="border-b border-gray-800/50 hover:bg-gray-800/30 transition-colors">
      <td className="py-3 px-4 text-gray-500 text-sm">#{rank}</td>
      <td className="py-3 px-4">
        <div className="flex items-center gap-2">
          <span className="font-medium text-white">{MARKET_LABELS[market.market_type] || market.market_type}</span>
          {streak >= 5 && <Flame className="w-4 h-4 text-orange-400" />}
          {streak <= -5 && <Snowflake className="w-4 h-4 text-blue-400" />}
        </div>
      </td>
      <td className="py-3 px-4 text-center text-gray-300">{market.resolved || 0}</td>
      <td className="py-3 px-4 text-center">
        <span className="text-green-400">{market.wins || 0}</span>
        <span className="text-gray-600 mx-1">/</span>
        <span className="text-red-400">{market.losses || 0}</span>
      </td>
      <td className="py-3 px-4 text-center">
        <span className={`font-medium ${(market.win_rate || 0) >= 55 ? "text-green-400" : (market.win_rate || 0) >= 50 ? "text-cyan-400" : "text-red-400"}`}>
          {market.win_rate?.toFixed(1) || "0.0"}%
        </span>
      </td>
      <td className="py-3 px-4 text-center">
        <span className={`font-bold ${(market.roi_pct || 0) >= 5 ? "text-green-400" : (market.roi_pct || 0) >= 0 ? "text-cyan-400" : (market.roi_pct || 0) >= -5 ? "text-yellow-400" : "text-red-400"}`}>
          {(market.roi_pct || 0) >= 0 ? "+" : ""}{market.roi_pct?.toFixed(1) || "0.0"}%
        </span>
      </td>
      <td className="py-3 px-4 text-center">
        <span className={(market.avg_clv || 0) > 0 ? "text-green-400" : "text-red-400"}>
          {(market.avg_clv || 0) >= 0 ? "+" : ""}{market.avg_clv?.toFixed(2) || "0.00"}%
        </span>
      </td>
      <td className="py-3 px-4 text-center text-gray-400">{market.avg_kelly?.toFixed(1) || "0.0"}%</td>
    </tr>
  );
};

// Heatmap Cell
const HeatmapCell: React.FC<{ value: number | null; size: number }> = ({ value, size }) => {
  if (value === null || value === undefined) return <div className="w-full h-full bg-gray-800/50" style={{ width: size, height: size }} />;
  
  const getColor = (v: number) => {
    if (v >= 0.7) return "bg-red-500";
    if (v >= 0.5) return "bg-orange-500";
    if (v >= 0.3) return "bg-yellow-500";
    if (v >= 0.1) return "bg-green-500";
    if (v >= -0.1) return "bg-gray-500";
    if (v >= -0.3) return "bg-cyan-500";
    return "bg-blue-500";
  };
  
  const opacity = Math.min(Math.abs(value) + 0.3, 1);
  
  return (
    <div 
      className={`${getColor(value)} rounded-sm flex items-center justify-center text-xs font-medium text-white`}
      style={{ width: size, height: size, opacity }}
      title={`Corrélation: ${value.toFixed(2)}`}
    >
      {size > 30 && value.toFixed(2)}
    </div>
  );
};

// Input avec label
const InputField: React.FC<{
  label: string;
  value: number;
  onChange: (v: number) => void;
  min?: number;
  max?: number;
  step?: number;
  suffix?: string;
}> = ({ label, value, onChange, min = 0, max = 100, step = 1, suffix = "" }) => (
  <div>
    <label className="text-gray-400 text-sm mb-1 block">{label}</label>
    <div className="relative">
      <input
        type="number"
        value={value}
        onChange={(e) => onChange(Number(e.target.value))}
        min={min}
        max={max}
        step={step}
        className="w-full bg-gray-800/50 border border-gray-700 rounded-lg px-3 py-2 text-white focus:border-cyan-500 focus:outline-none"
      />
      {suffix && <span className="absolute right-3 top-2 text-gray-500">{suffix}</span>}
    </div>
  </div>
);

// ============================================================
// MAIN COMPONENT
// ============================================================

export default function TrackingCLVStats() {
  // Tab & Period State
  const [activeTab, setActiveTab] = useState("dashboard");
  const [period, setPeriod] = useState(30);
  const [loading, setLoading] = useState(true);
  const [lastUpdate, setLastUpdate] = useState<Date>(new Date());
  const [autoRefresh, setAutoRefresh] = useState(true);

  // Dashboard Data States
  const [globalPerf, setGlobalPerf] = useState<GlobalPerformance | null>(null);
  const [marketPerf, setMarketPerf] = useState<MarketPerformance[]>([]);
  const [dailyPerf, setDailyPerf] = useState<DailyPerformance[]>([]);
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [combos, setCombos] = useState<Combo[]>([]);

  // CLV Tab States
  const [clvStats, setClvStats] = useState<CLVStats | null>(null);
  const [clvByTiming, setClvByTiming] = useState<CLVByTiming[]>([]);
  const [clvByMarket, setClvByMarket] = useState<CLVByMarket[]>([]);

  // Correlations Tab States
  const [correlationMatrix, setCorrelationMatrix] = useState<Record<string, Record<string, number>>>({});

  // Pro Tools States
  const [riskMetrics, setRiskMetrics] = useState<RiskMetrics | null>(null);
  const [biases, setBiases] = useState<BiasReport[]>([]);
  
  // Calculator States
  const [kellyInputs, setKellyInputs] = useState({ probability: 55, odds: 1.90, bankroll: 1000, drawdown: 0 });
  const [kellyResult, setKellyResult] = useState<KellyResult | null>(null);
  const [evInputs, setEvInputs] = useState({ probability: 55, odds: 1.90, stake: 1 });
  const [evResult, setEvResult] = useState<EVResult | null>(null);
  const [mcInputs, setMcInputs] = useState({ bankroll: 1000, bets: 500, minScore: 70 });
  const [mcResult, setMcResult] = useState<MonteCarloResult | null>(null);
  const [mcLoading, setMcLoading] = useState(false);

  // Sweet Spot States
  const [sweetSpotPicks, setSweetSpotPicks] = useState<SweetSpotPick[]>([]);
  const [sweetSpotStats, setSweetSpotStats] = useState<SweetSpotStats | null>(null);
  const [sweetSpotUpcoming, setSweetSpotUpcoming] = useState<SweetSpotUpcoming | null>(null);
  const [sweetSpotLoading, setSweetSpotLoading] = useState(false);
  // Markets 2.0 States
  const [marketSortBy, setMarketSortBy] = useState<"roi" | "winrate" | "picks">("roi");
  const [selectedMarket, setSelectedMarket] = useState<MarketPerformance | null>(null);

  // ============================================================
  // FETCH FUNCTIONS
  // ============================================================

  const fetchDashboard = useCallback(async () => {
    setLoading(true);
    try {
      const response = await fetch(`${API_BASE}/api/tracking-clv/dashboard`);
      const data = await response.json();
      setGlobalPerf(data.global);
      setMarketPerf(data.by_market || []);
      setAlerts(data.alerts || []);
      setCombos(data.best_combos || []);
      setLastUpdate(new Date());
    } catch (error) {
      console.error("Error fetching dashboard:", error);
    } finally {
      setLoading(false);
    }
  }, []);

  const fetchDailyPerformance = useCallback(async () => {
    try {
      const startDate = new Date(Date.now() - period * 24 * 60 * 60 * 1000).toISOString().split('T')[0];
      const endDate = new Date().toISOString().split('T')[0];
      const response = await fetch(`${API_BASE}/api/tracking-clv/performance/by-date?start_date=${startDate}&end_date=${endDate}`);
      const data = await response.json();
      setDailyPerf(data || []);
    } catch (error) {
      console.error("Error:", error);
    }
  }, [period]);

  const fetchCLVStats = useCallback(async () => {
    try {
      const response = await fetch(`${API_BASE}/api/tracking-clv/clv/stats?days=${period}`);
      const data = await response.json();
      setClvStats(data.global_stats);
      setClvByTiming(data.by_timing || []);
      setClvByMarket(data.by_market || []);
    } catch (error) {
      console.error("Error:", error);
    }
  }, [period]);

  const fetchCorrelations = useCallback(async () => {
    try {
      const response = await fetch(`${API_BASE}/api/tracking-clv/correlations/matrix`);
      const data = await response.json();
      setCorrelationMatrix(data.matrix || {});
    } catch (error) {
      console.error("Error:", error);
    }
  }, []);

  const fetchRiskMetrics = useCallback(async () => {
    try {
      const response = await fetch(`${API_BASE}/api/tracking-clv/risk/metrics?days=${period}`);
      const data = await response.json();
      setRiskMetrics(data);
    } catch (error) {
      console.error("Error:", error);
    }
  }, [period]);

  const fetchBiases = useCallback(async () => {
    try {
      const response = await fetch(`${API_BASE}/api/tracking-clv/pro/bias-detection`);
      const data = await response.json();
      setBiases(data || []);
    } catch (error) {
      console.error("Error:", error);
    }
  }, []);


  // Sweet Spot Fetch Functions
  const fetchSweetSpotData = useCallback(async () => {
    setSweetSpotLoading(true);
    try {
      // Fetch picks
      const picksRes = await fetch(`${API_BASE}/api/tracking-clv/sweet-spot/picks?hours_ahead=48&limit=50`);
      if (picksRes.ok) {
        const picksData = await picksRes.json();
        setSweetSpotPicks(picksData.picks || []);
      }
      
      // Fetch stats
      const statsRes = await fetch(`${API_BASE}/api/tracking-clv/sweet-spot/stats?days=${period}`);
      if (statsRes.ok) {
        const statsData = await statsRes.json();
        setSweetSpotStats(statsData);
      }
      
      // Fetch upcoming
      const upcomingRes = await fetch(`${API_BASE}/api/tracking-clv/sweet-spot/upcoming?hours=24`);
      if (upcomingRes.ok) {
        const upcomingData = await upcomingRes.json();
        setSweetSpotUpcoming(upcomingData);
      }
    } catch (error) {
      console.error('Error fetching sweet spot data:', error);
    } finally {
      setSweetSpotLoading(false);
    }
  }, [period]);

  const calculateKelly = async () => {
    try {
      const params = new URLSearchParams({
        probability: kellyInputs.probability.toString(),
        odds: kellyInputs.odds.toString(),
        bankroll: kellyInputs.bankroll.toString(),
        current_drawdown: kellyInputs.drawdown.toString(),
        market_type: "over_25"
      });
      const response = await fetch(`${API_BASE}/api/tracking-clv/pro/kelly-calculator?${params}`);
      const data = await response.json();
      setKellyResult(data);
    } catch (error) {
      console.error("Error:", error);
    }
  };

  const calculateEV = async () => {
    try {
      const params = new URLSearchParams({
        probability: evInputs.probability.toString(),
        odds: evInputs.odds.toString(),
        stake: evInputs.stake.toString()
      });
      const response = await fetch(`${API_BASE}/api/tracking-clv/pro/ev-calculator?${params}`);
      const data = await response.json();
      setEvResult(data);
    } catch (error) {
      console.error("Error:", error);
    }
  };

  const runMonteCarlo = async () => {
    setMcLoading(true);
    try {
      const params = new URLSearchParams({
        initial_bankroll: mcInputs.bankroll.toString(),
        num_bets: mcInputs.bets.toString(),
        min_score: mcInputs.minScore.toString()
      });
      const response = await fetch(`${API_BASE}/api/tracking-clv/pro/monte-carlo?${params}`);
      const data = await response.json();
      setMcResult(data);
    } catch (error) {
      console.error("Error:", error);
    } finally {
      setMcLoading(false);
    }
  };

  // ============================================================
  // EFFECTS
  // ============================================================

  useEffect(() => {
    fetchDashboard();
    fetchDailyPerformance();
    fetchCLVStats();
    fetchCorrelations();
    fetchRiskMetrics();
    fetchBiases();
    fetchSweetSpotData();
  }, [fetchDashboard, fetchDailyPerformance, fetchCLVStats, fetchCorrelations, fetchRiskMetrics, fetchBiases, fetchSweetSpotData]);

  useEffect(() => {
    if (!autoRefresh) return;
    const interval = setInterval(fetchDashboard, 5 * 60 * 1000);
    return () => clearInterval(interval);
  }, [autoRefresh, fetchDashboard]);

  useEffect(() => {
    fetchDailyPerformance();
    fetchCLVStats();
    fetchRiskMetrics();
  }, [period, fetchDailyPerformance, fetchCLVStats, fetchRiskMetrics]);

  // ============================================================
  // RENDER HEADER & TABS
  // ============================================================

  const renderHeader = () => (
    <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4 mb-6">
      <div>
        <h1 className="text-2xl font-bold text-white flex items-center gap-3">
          <Activity className="w-7 h-7 text-cyan-400" />
          Tracking CLV 2.0
        </h1>
        <p className="text-gray-400 text-sm mt-1">Performance et analyses • 13 marchés</p>
      </div>
      <div className="flex items-center gap-3">
        <div className="flex bg-gray-800/50 rounded-xl p-1">
          {PERIODS.map((p) => (
            <button key={p.value} onClick={() => setPeriod(p.value)}
              className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-all ${period === p.value ? "bg-cyan-500 text-white" : "text-gray-400 hover:text-white"}`}>
              {p.label}
            </button>
          ))}
        </div>
        <button onClick={() => setAutoRefresh(!autoRefresh)}
          className={`p-2.5 rounded-xl transition-all ${autoRefresh ? "bg-cyan-500/20 text-cyan-400" : "bg-gray-800/50 text-gray-400"}`}
          title={autoRefresh ? "Auto-refresh ON" : "Auto-refresh OFF"}>
          <RefreshCw className={`w-4 h-4 ${autoRefresh ? "animate-spin" : ""}`} style={{ animationDuration: "3s" }} />
        </button>
        <span className="text-xs text-gray-500">Màj: {lastUpdate.toLocaleTimeString()}</span>
      </div>
    </div>
  );

  const renderTabs = () => (
    <div className="flex gap-2 mb-6 overflow-x-auto pb-2">
      {TABS.map((tab) => {
        const Icon = tab.icon;
        return (
          <button key={tab.id} onClick={() => setActiveTab(tab.id)}
            className={`flex items-center gap-2 px-4 py-2.5 rounded-xl font-medium transition-all whitespace-nowrap ${
              activeTab === tab.id
                ? "bg-gradient-to-r from-cyan-500 to-violet-500 text-white shadow-lg shadow-cyan-500/25"
                : "bg-gray-800/50 text-gray-400 hover:bg-gray-700/50 hover:text-white"
            }`}>
            <Icon className="w-4 h-4" />
            {tab.label}
          </button>
        );
      })}
    </div>
  );

  // ============================================================
  // TAB 1: DASHBOARD
  // ============================================================


  // ============================================================
  // 🎯 RENDER SWEET SPOT
  // ============================================================

  const renderSweetSpot = () => {
    if (sweetSpotLoading) {
      return (
        <div className="flex items-center justify-center h-64">
          <RefreshCw className="w-8 h-8 animate-spin text-cyan-400" />
        </div>
      );
    }

    return (
      <div className="space-y-6">
        {/* Header Stats */}
        <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="rounded-2xl bg-gradient-to-br from-emerald-500/20 to-emerald-600/10 border border-emerald-500/30 p-4"
          >
            <div className="flex items-center gap-2 mb-2">
              <Target className="w-5 h-5 text-emerald-400" />
              <span className="text-slate-400 text-sm">Sweet Spots</span>
            </div>
            <div className="text-2xl font-bold text-white">{sweetSpotStats?.global.total_picks || 0}</div>
            <div className="text-xs text-slate-500">picks identifiés</div>
          </motion.div>

          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.1 }}
            className="rounded-2xl bg-gradient-to-br from-cyan-500/20 to-cyan-600/10 border border-cyan-500/30 p-4"
          >
            <div className="flex items-center gap-2 mb-2">
              <TrendingUp className="w-5 h-5 text-cyan-400" />
              <span className="text-slate-400 text-sm">Edge Moyen</span>
            </div>
            <div className="text-2xl font-bold text-cyan-400">+{sweetSpotStats?.global.avg_edge?.toFixed(1) || 0}%</div>
            <div className="text-xs text-slate-500">vs closing line</div>
          </motion.div>

          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.2 }}
            className="rounded-2xl bg-gradient-to-br from-violet-500/20 to-violet-600/10 border border-violet-500/30 p-4"
          >
            <div className="flex items-center gap-2 mb-2">
              <Percent className="w-5 h-5 text-violet-400" />
              <span className="text-slate-400 text-sm">Score Moyen</span>
            </div>
            <div className="text-2xl font-bold text-violet-400">{sweetSpotStats?.global.avg_score?.toFixed(0) || 0}</div>
            <div className="text-xs text-slate-500">/ 100</div>
          </motion.div>

          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.3 }}
            className="rounded-2xl bg-gradient-to-br from-amber-500/20 to-amber-600/10 border border-amber-500/30 p-4"
          >
            <div className="flex items-center gap-2 mb-2">
              <DollarSign className="w-5 h-5 text-amber-400" />
              <span className="text-slate-400 text-sm">Cote Moyenne</span>
            </div>
            <div className="text-2xl font-bold text-amber-400">{sweetSpotStats?.global.avg_odds?.toFixed(2) || 0}</div>
            <div className="text-xs text-slate-500">sweet spot</div>
          </motion.div>

          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.4 }}
            className="rounded-2xl bg-gradient-to-br from-green-500/20 to-green-600/10 border border-green-500/30 p-4"
          >
            <div className="flex items-center gap-2 mb-2">
              <Trophy className="w-5 h-5 text-green-400" />
              <span className="text-slate-400 text-sm">Win Rate</span>
            </div>
            <div className="text-2xl font-bold text-green-400">{sweetSpotStats?.global.win_rate?.toFixed(1) || 0}%</div>
            <div className="text-xs text-slate-500">{sweetSpotStats?.global.wins || 0}W / {sweetSpotStats?.global.losses || 0}L</div>
          </motion.div>
        </div>

        {/* Upcoming Matches */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2 }}
          className="rounded-2xl border border-slate-700/50 bg-slate-800/30 p-6"
        >
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-semibold text-white flex items-center gap-2">
              <Flame className="w-5 h-5 text-orange-400" />
              🎯 Picks Sweet Spot - Prochains Matchs
            </h3>
            <span className="text-sm text-slate-400">
              {sweetSpotUpcoming?.total_picks || 0} picks sur {sweetSpotUpcoming?.total_matches || 0} matchs
            </span>
          </div>

          <div className="space-y-4">
            {sweetSpotUpcoming?.matches?.slice(0, 10).map((match, idx) => (
              <motion.div
                key={idx}
                initial={{ opacity: 0, x: -20 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: idx * 0.05 }}
                className="rounded-xl bg-slate-900/50 border border-slate-700/30 p-4"
              >
                <div className="flex items-center justify-between mb-3">
                  <div>
                    <h4 className="font-medium text-white">{match.match_name}</h4>
                    <span className="text-xs text-slate-500">
                      {match.commence_time ? new Date(match.commence_time).toLocaleString('fr-FR', {
                        day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit'
                      }) : 'N/A'}
                    </span>
                  </div>
                  <span className="px-2 py-1 rounded-lg bg-emerald-500/20 text-emerald-400 text-xs">
                    {match.picks.length} sweet spot{match.picks.length > 1 ? 's' : ''}
                  </span>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-2">
                  {match.picks.map((pick, pIdx) => (
                    <div
                      key={pIdx}
                      className="flex items-center justify-between rounded-lg bg-slate-800/50 px-3 py-2"
                    >
                      <div className="flex items-center gap-2">
                        <span className="text-xs font-medium text-cyan-400 uppercase">
                          {MARKET_LABELS[pick.market_type] || pick.market_type}
                        </span>
                        <span className="text-xs text-slate-500">@{pick.odds.toFixed(2)}</span>
                      </div>
                      <div className="flex items-center gap-2">
                        <span className={`text-xs font-bold ${pick.edge_pct >= 15 ? 'text-green-400' : pick.edge_pct >= 10 ? 'text-cyan-400' : 'text-slate-300'}`}>
                          +{pick.edge_pct.toFixed(1)}%
                        </span>
                        <span className="text-xs px-1.5 py-0.5 rounded bg-violet-500/20 text-violet-400">
                          {pick.score}
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              </motion.div>
            ))}

            {(!sweetSpotUpcoming?.matches || sweetSpotUpcoming.matches.length === 0) && (
              <div className="text-center py-8 text-slate-500">
                <Target className="w-12 h-12 mx-auto mb-2 opacity-50" />
                <p>Aucun pick sweet spot pour les prochaines 24h</p>
              </div>
            )}
          </div>
        </motion.div>

        {/* Performance par Marché */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.3 }}
          className="rounded-2xl border border-slate-700/50 bg-slate-800/30 p-6"
        >
          <h3 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
            <BarChart3 className="w-5 h-5 text-cyan-400" />
            Performance Sweet Spot par Marché
          </h3>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            {sweetSpotStats?.by_market?.map((market, idx) => (
              <motion.div
                key={market.market_type}
                initial={{ opacity: 0, scale: 0.95 }}
                animate={{ opacity: 1, scale: 1 }}
                transition={{ delay: idx * 0.05 }}
                className="rounded-xl bg-slate-900/50 border border-slate-700/30 p-4"
              >
                <div className="flex items-center justify-between mb-2">
                  <span className="font-medium text-white">
                    {MARKET_LABELS[market.market_type] || market.market_type}
                  </span>
                  <span className={`text-sm font-bold ${market.avg_edge >= 10 ? 'text-green-400' : 'text-cyan-400'}`}>
                    +{market.avg_edge.toFixed(1)}%
                  </span>
                </div>
                <div className="flex items-center justify-between text-xs text-slate-400">
                  <span>{market.total} picks</span>
                  <span>{market.win_rate > 0 ? `${market.win_rate.toFixed(0)}% WR` : 'En attente'}</span>
                </div>
                <div className="mt-2 h-1.5 bg-slate-700 rounded-full overflow-hidden">
                  <div
                    className="h-full bg-gradient-to-r from-cyan-500 to-emerald-500 rounded-full"
                    style={{ width: `${Math.min(market.avg_edge * 5, 100)}%` }}
                  />
                </div>
              </motion.div>
            ))}
          </div>
        </motion.div>

        {/* Info Box */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.4 }}
          className="rounded-2xl border border-cyan-500/30 bg-cyan-500/10 p-4"
        >
          <div className="flex items-start gap-3">
            <Info className="w-5 h-5 text-cyan-400 flex-shrink-0 mt-0.5" />
            <div>
              <h4 className="font-medium text-cyan-400 mb-1">Qu'est-ce que le Sweet Spot ?</h4>
              <p className="text-sm text-slate-300">
                Les picks <strong>Sweet Spot</strong> sont identifiés par notre algorithme V7 comme ayant le meilleur rapport risque/rendement.
                Critères : Score entre 60-79 + Cotes inférieures à 2.5. Ces picks ont historiquement montré le meilleur ROI (+19.1 sur le score 60-69).
              </p>
            </div>
          </div>
        </motion.div>
      </div>
    );
  };

  const renderDashboard = () => (
    <div className="space-y-6">
      {/* KPI Cards */}
      <div className="grid grid-cols-2 lg:grid-cols-5 gap-4">
        <KPICard title="Win Rate" value={`${globalPerf?.win_rate?.toFixed(1) || "0.0"}%`}
          subtitle={`${globalPerf?.wins || 0}W / ${globalPerf?.losses || 0}L`} icon={Target} color="cyan" loading={loading} />
        <KPICard title="ROI" value={`${(globalPerf?.roi_pct || 0) >= 0 ? "+" : ""}${globalPerf?.roi_pct?.toFixed(1) || "0.0"}%`}
          icon={Percent} color="violet" loading={loading} />
        <KPICard title="Profit" value={`${(globalPerf?.total_profit || 0) >= 0 ? "+" : ""}${globalPerf?.total_profit?.toFixed(1) || "0.0"}u`}
          icon={DollarSign} color="green" loading={loading} />
        <KPICard title="CLV Moyen" value={`${(globalPerf?.avg_clv || 0) >= 0 ? "+" : ""}${globalPerf?.avg_clv?.toFixed(2) || "0.00"}%`}
          subtitle={`${globalPerf?.clv_positive_rate?.toFixed(0) || "0"}% positif`} icon={TrendingUp} color="emerald" loading={loading} />
        <KPICard title="Picks" value={globalPerf?.resolved_predictions || 0}
          subtitle={`sur ${globalPerf?.total_predictions || 0} total`} icon={BarChart3} color="amber" loading={loading} />
      </div>

      {/* Charts Row */}
      <div className="grid lg:grid-cols-2 gap-6">
        <div className="bg-gray-900/50 rounded-2xl border border-gray-800/50 p-5">
          <h3 className="text-base font-semibold text-white mb-4 flex items-center gap-2">
            <TrendingUp className="w-5 h-5 text-cyan-400" />Évolution P&L
          </h3>
          <ResponsiveContainer width="100%" height={220}>
            <AreaChart data={dailyPerf.slice().reverse()}>
              <defs>
                <linearGradient id="profitGradient" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#06b6d4" stopOpacity={0.3}/>
                  <stop offset="95%" stopColor="#06b6d4" stopOpacity={0}/>
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
              <XAxis dataKey="date" stroke="#6b7280" tick={{ fontSize: 10 }}
                tickFormatter={(v) => new Date(v).toLocaleDateString('fr-FR', { day: '2-digit', month: '2-digit' })} />
              <YAxis stroke="#6b7280" tick={{ fontSize: 10 }} />
              <Tooltip contentStyle={{ backgroundColor: "#1f2937", border: "1px solid #374151", borderRadius: "8px" }}
                formatter={(value: number) => [`${value?.toFixed(2)}u`, "P&L"]} />
              <Area type="monotone" dataKey="cumulative_profit" stroke="#06b6d4" fill="url(#profitGradient)" strokeWidth={2} />
            </AreaChart>
          </ResponsiveContainer>
        </div>
        <div className="bg-gray-900/50 rounded-2xl border border-gray-800/50 p-5">
          <h3 className="text-base font-semibold text-white mb-4 flex items-center gap-2">
            <BarChart3 className="w-5 h-5 text-violet-400" />ROI par Marché
          </h3>
          <ResponsiveContainer width="100%" height={220}>
            <BarChart data={marketPerf.slice(0, 8)} layout="vertical" margin={{ left: 50 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
              <XAxis type="number" stroke="#6b7280" tick={{ fontSize: 10 }} />
              <YAxis type="category" dataKey="market_type" stroke="#6b7280" tick={{ fontSize: 10 }}
                tickFormatter={(v) => MARKET_LABELS[v] || v} />
              <Tooltip contentStyle={{ backgroundColor: "#1f2937", border: "1px solid #374151", borderRadius: "8px" }}
                formatter={(value: number) => [`${value?.toFixed(1)}%`, "ROI"]} />
              <Bar dataKey="roi_pct" radius={[0, 4, 4, 0]}>
                {marketPerf.slice(0, 8).map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={(entry.roi_pct || 0) >= 0 ? "#06b6d4" : "#ef4444"} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Table & Alerts */}
      <div className="grid lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 bg-gray-900/50 rounded-2xl border border-gray-800/50 p-5">
          <h3 className="text-base font-semibold text-white mb-4 flex items-center gap-2">
            <Trophy className="w-5 h-5 text-amber-400" />Performance par Marché
          </h3>
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="text-gray-400 text-xs uppercase border-b border-gray-800">
                  <th className="py-2 px-4 text-left">#</th>
                  <th className="py-2 px-4 text-left">Marché</th>
                  <th className="py-2 px-4 text-center">Picks</th>
                  <th className="py-2 px-4 text-center">W/L</th>
                  <th className="py-2 px-4 text-center">Win%</th>
                  <th className="py-2 px-4 text-center">ROI</th>
                  <th className="py-2 px-4 text-center">CLV</th>
                  <th className="py-2 px-4 text-center">Kelly</th>
                </tr>
              </thead>
              <tbody>
                {marketPerf.slice(0, 8).map((market, index) => (
                  <MarketRow key={market.market_type} market={market} rank={index + 1} />
                ))}
              </tbody>
            </table>
          </div>
        </div>
        <div className="bg-gray-900/50 rounded-2xl border border-gray-800/50 p-5">
          <h3 className="text-base font-semibold text-white mb-4 flex items-center gap-2">
            <AlertTriangle className="w-5 h-5 text-amber-400" />Alertes
          </h3>
          <div className="space-y-2">
            {alerts.length > 0 ? alerts.slice(0, 5).map((alert, i) => <AlertCard key={i} alert={alert} />) 
              : <p className="text-gray-500 text-center py-6 text-sm">Aucune alerte</p>}
          </div>
        </div>
      </div>

      {/* Combos */}
      <div className="bg-gray-900/50 rounded-2xl border border-gray-800/50 p-5">
        <h3 className="text-base font-semibold text-white mb-4 flex items-center gap-2">
          <GitBranch className="w-5 h-5 text-violet-400" />Meilleurs Combos
        </h3>
        <div className="grid md:grid-cols-2 lg:grid-cols-5 gap-3">
          {combos.slice(0, 5).map((combo, i) => (
            <div key={i} className="p-3 rounded-xl bg-gray-800/30 border border-gray-700/30">
              <div className="text-sm font-medium text-white mb-1">
                {MARKET_LABELS[combo.market_a]} + {MARKET_LABELS[combo.market_b]}
              </div>
              <div className="flex items-center justify-between">
                <span className="text-cyan-400 font-bold">{(combo.both_win_rate * 100).toFixed(0)}%</span>
                <span className={`text-xs px-2 py-0.5 rounded ${
                  combo.correlation < 0.3 ? "bg-green-500/20 text-green-400" :
                  combo.correlation < 0.5 ? "bg-yellow-500/20 text-yellow-400" : "bg-red-500/20 text-red-400"
                }`}>r={combo.correlation?.toFixed(2)}</span>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );

  // ============================================================
  // ============================================================
  // TAB 2: MARKETS 2.0
  // ============================================================
  
  // Fonction de tri des marchés
  const getSortedMarkets = () => {
    if (!marketPerf) return [];
    return [...marketPerf].sort((a, b) => {
      switch (marketSortBy) {
        case "roi": return (b.roi_pct || 0) - (a.roi_pct || 0);
        case "winrate": return (b.win_rate || 0) - (a.win_rate || 0);
        case "picks": return (b.resolved || 0) - (a.resolved || 0);
        default: return 0;
      }
    });
  };

  // Déterminer le badge d'un marché
  const getMarketBadge = (market: MarketPerformance) => {
    if ((market.resolved || 0) < 3) return null; // Pas assez de données
    if ((market.roi_pct || 0) >= 20 && (market.win_rate || 0) >= 50) return { type: "top", label: "🏆 TOP" };
    if ((market.roi_pct || 0) <= -20 || (market.win_rate || 0) < 35) return { type: "avoid", label: "⚠️ À ÉVITER" };
    if ((market.roi_pct || 0) >= 10) return { type: "good", label: "✅ BON" };
    return null;
  };

  const renderMarkets = () => (
    <div className="space-y-6">
      {/* Header avec titre et tri */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <h2 className="text-xl font-bold text-white flex items-center gap-2">
          <PieChart className="w-6 h-6 text-cyan-400" />
          Détail par Marché
          <span className="text-sm font-normal text-gray-400">({marketPerf?.length || 0} marchés)</span>
        </h2>
        
        {/* Boutons de tri */}
        <div className="flex items-center gap-2">
          <span className="text-sm text-gray-400">Trier par:</span>
          {[
            { key: "roi", label: "ROI", icon: TrendingUp },
            { key: "winrate", label: "Win Rate", icon: Target },
            { key: "picks", label: "Picks", icon: BarChart3 },
          ].map(({ key, label, icon: Icon }) => (
            <button
              key={key}
              onClick={() => setMarketSortBy(key as "roi" | "winrate" | "picks")}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm font-medium transition-all ${
                marketSortBy === key
                  ? "bg-cyan-500/20 text-cyan-400 border border-cyan-500/50"
                  : "bg-gray-800/50 text-gray-400 border border-gray-700/50 hover:border-gray-600"
              }`}
            >
              <Icon className="w-4 h-4" />
              {label}
            </button>
          ))}
        </div>
      </div>

      {/* Grille des marchés */}
      <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
        {getSortedMarkets().map((market, index) => {
          const badge = getMarketBadge(market);
          const isTopPerformer = badge?.type === "top";
          const isToAvoid = badge?.type === "avoid";
          
          return (
            <motion.div
              key={market.market_type}
              initial={{ opacity: 0, scale: 0.95, y: 20 }}
              animate={{ opacity: 1, scale: 1, y: 0 }}
              transition={{ delay: index * 0.03 }}
              onClick={() => setSelectedMarket(market)}
              className={`relative bg-gray-900/50 rounded-2xl border p-5 cursor-pointer transition-all hover:scale-[1.02] ${
                isTopPerformer
                  ? "border-green-500/50 hover:border-green-400 shadow-lg shadow-green-500/10"
                  : isToAvoid
                  ? "border-red-500/30 hover:border-red-400"
                  : "border-gray-800/50 hover:border-cyan-500/30"
              }`}
            >
              {/* Badge */}
              {badge && (
                <div className={`absolute -top-2 -right-2 px-2 py-0.5 rounded-full text-xs font-bold ${
                  badge.type === "top" ? "bg-green-500/20 text-green-400 border border-green-500/50" :
                  badge.type === "avoid" ? "bg-red-500/20 text-red-400 border border-red-500/50" :
                  "bg-cyan-500/20 text-cyan-400 border border-cyan-500/50"
                }`}>
                  {badge.label}
                </div>
              )}

              {/* En-tête */}
              <div className="flex items-center justify-between mb-4">
                <h3 className="font-semibold text-lg text-white">
                  {MARKET_LABELS[market.market_type] || market.market_type}
                </h3>
                <span className={`text-xl font-bold ${(market.roi_pct || 0) >= 0 ? "text-green-400" : "text-red-400"}`}>
                  {(market.roi_pct || 0) >= 0 ? "+" : ""}{(market.roi_pct || 0).toFixed(1)}%
                </span>
              </div>

              {/* Stats */}
              <div className="grid grid-cols-2 gap-3 text-sm">
                <div>
                  <span className="text-gray-400">Win Rate</span>
                  <p className="font-medium text-white">{(market.win_rate || 0).toFixed(1)}%</p>
                </div>
                <div>
                  <span className="text-gray-400">CLV</span>
                  <p className={`font-medium ${(market.avg_clv || 0) >= 0 ? "text-green-400" : "text-red-400"}`}>
                    {(market.avg_clv || 0) >= 0 ? "+" : ""}{(market.avg_clv || 0).toFixed(2)}%
                  </p>
                </div>
                <div>
                  <span className="text-gray-400">Picks</span>
                  <p className="font-medium text-white">
                    {market.resolved || 0}
                    <span className="text-gray-500 text-xs"> / {market.total_predictions || 0}</span>
                  </p>
                </div>
                <div>
                  <span className="text-gray-400">Kelly</span>
                  <p className="font-medium text-white">{(market.avg_kelly || 0).toFixed(1)}%</p>
                </div>
              </div>

              {/* Progress bar Win Rate */}
              <div className="mt-4 h-2 bg-gray-800 rounded-full overflow-hidden">
                <div
                  className={`h-full rounded-full transition-all ${
                    isTopPerformer ? "bg-gradient-to-r from-green-500 to-emerald-400" :
                    isToAvoid ? "bg-gradient-to-r from-red-500 to-orange-400" :
                    "bg-gradient-to-r from-cyan-500 to-violet-500"
                  }`}
                  style={{ width: `${Math.min((market.win_rate || 0), 100)}%` }}
                />
              </div>

              {/* Indicateur cliquable */}
              <div className="mt-3 text-center">
                <span className="text-xs text-gray-500 hover:text-cyan-400 transition-colors">
                  Cliquer pour détails →
                </span>
              </div>
            </motion.div>
          );
        })}
      </div>

      {/* Modal détails marché */}
      <AnimatePresence>
        {selectedMarket && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 bg-black/80 backdrop-blur-sm z-50 flex items-center justify-center p-4"
            onClick={() => setSelectedMarket(null)}
          >
            <motion.div
              initial={{ scale: 0.9, y: 20 }}
              animate={{ scale: 1, y: 0 }}
              exit={{ scale: 0.9, y: 20 }}
              onClick={(e) => e.stopPropagation()}
              className="bg-gray-900 rounded-2xl border border-gray-700 p-6 max-w-lg w-full max-h-[80vh] overflow-y-auto"
            >
              {/* Header Modal */}
              <div className="flex items-center justify-between mb-6">
                <h3 className="text-2xl font-bold text-white">
                  {MARKET_LABELS[selectedMarket.market_type] || selectedMarket.market_type}
                </h3>
                <button
                  onClick={() => setSelectedMarket(null)}
                  className="p-2 rounded-full hover:bg-gray-800 transition-colors"
                >
                  <RotateCcw className="w-5 h-5 text-gray-400" />
                </button>
              </div>

              {/* Stats détaillées */}
              <div className="space-y-4">
                {/* ROI & Win Rate */}
                <div className="grid grid-cols-2 gap-4">
                  <div className="bg-gray-800/50 rounded-xl p-4 text-center">
                    <div className="text-gray-400 text-sm mb-1">ROI</div>
                    <div className={`text-3xl font-bold ${(selectedMarket.roi_pct || 0) >= 0 ? "text-green-400" : "text-red-400"}`}>
                      {(selectedMarket.roi_pct || 0) >= 0 ? "+" : ""}{(selectedMarket.roi_pct || 0).toFixed(1)}%
                    </div>
                  </div>
                  <div className="bg-gray-800/50 rounded-xl p-4 text-center">
                    <div className="text-gray-400 text-sm mb-1">Win Rate</div>
                    <div className="text-3xl font-bold text-white">{(selectedMarket.win_rate || 0).toFixed(1)}%</div>
                  </div>
                </div>

                {/* Picks détails */}
                <div className="bg-gray-800/50 rounded-xl p-4">
                  <div className="text-gray-400 text-sm mb-3">Répartition des picks</div>
                  <div className="flex items-center justify-between">
                    <div className="text-center">
                      <div className="text-2xl font-bold text-white">{selectedMarket.total_predictions || 0}</div>
                      <div className="text-xs text-gray-500">Total</div>
                    </div>
                    <div className="text-center">
                      <div className="text-2xl font-bold text-cyan-400">{selectedMarket.resolved || 0}</div>
                      <div className="text-xs text-gray-500">Résolus</div>
                    </div>
                    <div className="text-center">
                      <div className="text-2xl font-bold text-green-400">{selectedMarket.wins || 0}</div>
                      <div className="text-xs text-gray-500">Gagnés</div>
                    </div>
                    <div className="text-center">
                      <div className="text-2xl font-bold text-red-400">{selectedMarket.losses || 0}</div>
                      <div className="text-xs text-gray-500">Perdus</div>
                    </div>
                  </div>
                </div>

                {/* Métriques avancées */}
                <div className="grid grid-cols-2 gap-4">
                  <div className="bg-gray-800/50 rounded-xl p-4">
                    <div className="text-gray-400 text-sm mb-1">CLV Moyen</div>
                    <div className={`text-xl font-bold ${(selectedMarket.avg_clv || 0) >= 0 ? "text-green-400" : "text-red-400"}`}>
                      {(selectedMarket.avg_clv || 0) >= 0 ? "+" : ""}{(selectedMarket.avg_clv || 0).toFixed(3)}%
                    </div>
                  </div>
                  <div className="bg-gray-800/50 rounded-xl p-4">
                    <div className="text-gray-400 text-sm mb-1">Kelly Optimal</div>
                    <div className="text-xl font-bold text-violet-400">{(selectedMarket.avg_kelly || 0).toFixed(2)}%</div>
                  </div>
                </div>

                {/* Streak */}
                <div className="bg-gray-800/50 rounded-xl p-4">
                  <div className="text-gray-400 text-sm mb-1">Série actuelle</div>
                  <div className={`text-xl font-bold ${(selectedMarket.current_streak || 0) >= 0 ? "text-green-400" : "text-red-400"}`}>
                    {(selectedMarket.current_streak || 0) >= 0 ? `🔥 ${selectedMarket.current_streak || 0}W` : `❄️ ${Math.abs(selectedMarket.current_streak || 0)}L`}
                  </div>
                </div>

                {/* Recommandation */}
                <div className={`rounded-xl p-4 ${
                  (selectedMarket.roi_pct || 0) >= 10 ? "bg-green-500/10 border border-green-500/30" :
                  (selectedMarket.roi_pct || 0) <= -10 ? "bg-red-500/10 border border-red-500/30" :
                  "bg-gray-800/50"
                }`}>
                  <div className="text-gray-400 text-sm mb-1">💡 Recommandation</div>
                  <div className="text-white">
                    {(selectedMarket.roi_pct || 0) >= 20 && (selectedMarket.win_rate || 0) >= 50
                      ? "🏆 Marché très performant - Continuer à exploiter"
                      : (selectedMarket.roi_pct || 0) >= 10
                      ? "✅ Bon marché - Maintenir les positions"
                      : (selectedMarket.roi_pct || 0) <= -20
                      ? "⚠️ Marché en difficulté - Réduire l'exposition"
                      : (selectedMarket.resolved || 0) < 5
                      ? "📊 Données insuffisantes - Attendre plus de résultats"
                      : "�� Marché neutre - Surveiller l'évolution"
                    }
                  </div>
                </div>
              </div>

              {/* Footer */}
              <div className="mt-6 pt-4 border-t border-gray-800">
                <button
                  onClick={() => setSelectedMarket(null)}
                  className="w-full py-3 bg-cyan-500/20 text-cyan-400 rounded-xl hover:bg-cyan-500/30 transition-colors font-medium"
                >
                  Fermer
                </button>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );

  // TAB 3: CLV (COMPLET)
  // ============================================================

  const renderCLV = () => {
    // Préparer les données pour les graphiques
    const clvDistribution = [
      { range: "< -2%", count: 0, color: "#ef4444" },
      { range: "-2 à -1%", count: 0, color: "#f97316" },
      { range: "-1 à 0%", count: 0, color: "#eab308" },
      { range: "0 à 1%", count: 0, color: "#22c55e" },
      { range: "1 à 2%", count: 0, color: "#06b6d4" },
      { range: "> 2%", count: 0, color: "#8b5cf6" },
    ];

    const timingData = clvByTiming.map(t => ({
      ...t,
      fill: t.avg_clv >= 0 ? "#06b6d4" : "#ef4444"
    }));

    return (
      <div className="space-y-6">
        <h2 className="text-xl font-bold text-white">Analyse CLV (Closing Line Value)</h2>
        
        {/* KPI Cards CLV */}
        <div className="grid grid-cols-2 lg:grid-cols-6 gap-4">
          <KPICard title="CLV Moyen" value={`${(clvStats?.avg_clv || 0) >= 0 ? "+" : ""}${clvStats?.avg_clv?.toFixed(2) || "0.00"}%`}
            icon={TrendingUp} color="cyan" />
          <KPICard title="CLV Médian" value={`${(clvStats?.median_clv || 0) >= 0 ? "+" : ""}${clvStats?.median_clv?.toFixed(2) || "0.00"}%`}
            icon={Target} color="violet" />
          <KPICard title="CLV Positif" value={`${clvStats?.positive_rate?.toFixed(0) || "0"}%`}
            subtitle="des picks" icon={CheckCircle} color="green" />
          <KPICard title="Beat Closing" value={`${clvStats?.beat_closing_rate?.toFixed(0) || "0"}%`}
            icon={Trophy} color="amber" />
          <KPICard title="CLV Sharpe" value={clvStats?.clv_sharpe?.toFixed(2) || "0.00"}
            icon={Activity} color="blue" />
          <KPICard title="Edge Total" value={`${(clvStats?.total_clv_edge || 0) >= 0 ? "+" : ""}${clvStats?.total_clv_edge?.toFixed(1) || "0"}%`}
            icon={DollarSign} color="emerald" />
        </div>

        {/* Graphiques */}
        <div className="grid lg:grid-cols-2 gap-6">
          {/* CLV par Timing */}
          <div className="bg-gray-900/50 rounded-2xl border border-gray-800/50 p-5">
            <h3 className="text-base font-semibold text-white mb-4 flex items-center gap-2">
              <Clock className="w-5 h-5 text-cyan-400" />CLV par Timing
            </h3>
            <ResponsiveContainer width="100%" height={250}>
              <BarChart data={timingData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                <XAxis dataKey="timing_window" stroke="#6b7280" tick={{ fontSize: 10 }} />
                <YAxis stroke="#6b7280" tick={{ fontSize: 10 }} />
                <Tooltip contentStyle={{ backgroundColor: "#1f2937", border: "1px solid #374151", borderRadius: "8px" }}
                  formatter={(value: number) => [`${value?.toFixed(2)}%`, "CLV Moyen"]} />
                <Bar dataKey="avg_clv" radius={[4, 4, 0, 0]}>
                  {timingData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={entry.fill} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
            <p className="text-gray-500 text-xs mt-2 text-center">
              💡 La fenêtre optimale est généralement 6-24h avant le match
            </p>
          </div>

          {/* CLV par Marché */}
          <div className="bg-gray-900/50 rounded-2xl border border-gray-800/50 p-5">
            <h3 className="text-base font-semibold text-white mb-4 flex items-center gap-2">
              <PieChart className="w-5 h-5 text-violet-400" />CLV par Marché
            </h3>
            <ResponsiveContainer width="100%" height={250}>
              <BarChart data={clvByMarket.slice(0, 8)} layout="vertical" margin={{ left: 50 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                <XAxis type="number" stroke="#6b7280" tick={{ fontSize: 10 }} />
                <YAxis type="category" dataKey="market_type" stroke="#6b7280" tick={{ fontSize: 10 }}
                  tickFormatter={(v) => MARKET_LABELS[v] || v} />
                <Tooltip contentStyle={{ backgroundColor: "#1f2937", border: "1px solid #374151", borderRadius: "8px" }}
                  formatter={(value: number) => [`${value?.toFixed(2)}%`, "CLV"]} />
                <Bar dataKey="avg_clv" radius={[0, 4, 4, 0]}>
                  {clvByMarket.slice(0, 8).map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={(entry.avg_clv || 0) >= 0 ? "#06b6d4" : "#ef4444"} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Beat Closing Rate & Insights */}
        <div className="grid lg:grid-cols-3 gap-6">
          {/* Beat Closing par Marché */}
          <div className="lg:col-span-2 bg-gray-900/50 rounded-2xl border border-gray-800/50 p-5">
            <h3 className="text-base font-semibold text-white mb-4 flex items-center gap-2">
              <Target className="w-5 h-5 text-green-400" />Beat Closing Rate par Marché
            </h3>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
              {clvByMarket.map((m) => (
                <div key={m.market_type} className="p-3 rounded-xl bg-gray-800/30">
                  <div className="text-sm text-gray-400 mb-1">{MARKET_LABELS[m.market_type]}</div>
                  <div className={`text-xl font-bold ${(m.beat_closing_rate || 0) >= 50 ? "text-green-400" : "text-red-400"}`}>
                    {m.beat_closing_rate?.toFixed(0) || 0}%
                  </div>
                  <div className="text-xs text-gray-500">{m.total_picks} picks</div>
                </div>
              ))}
            </div>
          </div>

          {/* CLV Insights */}
          <div className="bg-gray-900/50 rounded-2xl border border-gray-800/50 p-5">
            <h3 className="text-base font-semibold text-white mb-4 flex items-center gap-2">
              <Info className="w-5 h-5 text-cyan-400" />Insights CLV
            </h3>
            <div className="space-y-3">
              <div className={`p-3 rounded-lg ${(clvStats?.avg_clv || 0) >= 1 ? "bg-green-500/10 border border-green-500/30" : (clvStats?.avg_clv || 0) >= 0 ? "bg-cyan-500/10 border border-cyan-500/30" : "bg-red-500/10 border border-red-500/30"}`}>
                <div className="text-sm font-medium text-white">CLV Global</div>
                <div className="text-xs text-gray-400">
                  {(clvStats?.avg_clv || 0) >= 1 ? "🎯 Excellent ! Vous battez le marché de >1%" :
                   (clvStats?.avg_clv || 0) >= 0 ? "✅ Bon, CLV positif" : "⚠️ CLV négatif, revoir le timing"}
                </div>
              </div>
              <div className={`p-3 rounded-lg ${(clvStats?.beat_closing_rate || 0) >= 55 ? "bg-green-500/10 border border-green-500/30" : "bg-yellow-500/10 border border-yellow-500/30"}`}>
                <div className="text-sm font-medium text-white">Beat Closing</div>
                <div className="text-xs text-gray-400">
                  {(clvStats?.beat_closing_rate || 0) >= 55 ? "🏆 Vous battez la closing >55% du temps" : "📊 Amélioration possible"}
                </div>
              </div>
              <div className={`p-3 rounded-lg ${(clvStats?.clv_sharpe || 0) >= 1 ? "bg-green-500/10 border border-green-500/30" : "bg-gray-500/10 border border-gray-500/30"}`}>
                <div className="text-sm font-medium text-white">Sharpe CLV</div>
                <div className="text-xs text-gray-400">
                  {(clvStats?.clv_sharpe || 0) >= 1 ? "📈 Ratio risque/rendement excellent" : "📊 Ratio acceptable"}
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    );
  };

  // ============================================================
  // TAB 4: CORRELATIONS (COMPLET)
  // ============================================================

  const renderCorrelations = () => {
    const markets = Object.keys(correlationMatrix);
    const cellSize = markets.length > 10 ? 35 : 45;

    return (
      <div className="space-y-6">
        <h2 className="text-xl font-bold text-white">Corrélations & Combos</h2>

        {/* Heatmap */}
        <div className="bg-gray-900/50 rounded-2xl border border-gray-800/50 p-5">
          <h3 className="text-base font-semibold text-white mb-4 flex items-center gap-2">
            <GitBranch className="w-5 h-5 text-violet-400" />Matrice de Corrélation (13x13)
          </h3>
          
          {markets.length > 0 ? (
            <div className="overflow-x-auto">
              <div className="inline-block">
                {/* Header Row */}
                <div className="flex">
                  <div style={{ width: 70 }} />
                  {markets.map((m) => (
                    <div key={m} className="text-xs text-gray-400 text-center font-medium"
                      style={{ width: cellSize, transform: "rotate(-45deg)", transformOrigin: "center", height: 60 }}>
                      {MARKET_LABELS[m]?.split(" ")[0] || m}
                    </div>
                  ))}
                </div>
                
                {/* Data Rows */}
                {markets.map((row) => (
                  <div key={row} className="flex items-center">
                    <div className="text-xs text-gray-400 font-medium pr-2" style={{ width: 70 }}>
                      {MARKET_LABELS[row]?.substring(0, 8) || row}
                    </div>
                    {markets.map((col) => (
                      <HeatmapCell 
                        key={`${row}-${col}`}
                        value={row === col ? 1 : correlationMatrix[row]?.[col]}
                        size={cellSize}
                      />
                    ))}
                  </div>
                ))}
              </div>
              
              {/* Legend */}
              <div className="flex items-center justify-center gap-4 mt-6">
                <span className="text-xs text-gray-400">Corrélation:</span>
                <div className="flex items-center gap-1">
                  <div className="w-4 h-4 bg-blue-500 rounded-sm" />
                  <span className="text-xs text-gray-500">-1</span>
                </div>
                <div className="flex items-center gap-1">
                  <div className="w-4 h-4 bg-cyan-500 rounded-sm" />
                  <span className="text-xs text-gray-500">-0.3</span>
                </div>
                <div className="flex items-center gap-1">
                  <div className="w-4 h-4 bg-gray-500 rounded-sm" />
                  <span className="text-xs text-gray-500">0</span>
                </div>
                <div className="flex items-center gap-1">
                  <div className="w-4 h-4 bg-yellow-500 rounded-sm" />
                  <span className="text-xs text-gray-500">0.3</span>
                </div>
                <div className="flex items-center gap-1">
                  <div className="w-4 h-4 bg-orange-500 rounded-sm" />
                  <span className="text-xs text-gray-500">0.5</span>
                </div>
                <div className="flex items-center gap-1">
                  <div className="w-4 h-4 bg-red-500 rounded-sm" />
                  <span className="text-xs text-gray-500">1</span>
                </div>
              </div>
            </div>
          ) : (
            <p className="text-gray-500 text-center py-10">Chargement de la matrice...</p>
          )}
        </div>

        {/* Best & Worst Combos */}
        <div className="grid lg:grid-cols-2 gap-6">
          {/* Meilleurs Combos */}
          <div className="bg-gray-900/50 rounded-2xl border border-gray-800/50 p-5">
            <h3 className="text-base font-semibold text-white mb-4 flex items-center gap-2">
              <CheckCircle className="w-5 h-5 text-green-400" />Meilleurs Combos (faible corrélation)
            </h3>
            <div className="space-y-2">
              {combos.filter(c => c.correlation < 0.4).slice(0, 8).map((combo, i) => (
                <div key={i} className="flex items-center justify-between p-3 rounded-xl bg-green-500/5 border border-green-500/20">
                  <div>
                    <span className="font-medium text-white">
                      {MARKET_LABELS[combo.market_a]} + {MARKET_LABELS[combo.market_b]}
                    </span>
                  </div>
                  <div className="flex items-center gap-3">
                    <span className="text-green-400 font-bold">{(combo.both_win_rate * 100).toFixed(0)}%</span>
                    <span className="text-xs px-2 py-1 rounded bg-green-500/20 text-green-400">
                      r={combo.correlation?.toFixed(2)}
                    </span>
                  </div>
                </div>
              ))}
              {combos.filter(c => c.correlation < 0.4).length === 0 && (
                <p className="text-gray-500 text-sm text-center py-4">Aucun combo optimal trouvé</p>
              )}
            </div>
          </div>

          {/* Combos à éviter */}
          <div className="bg-gray-900/50 rounded-2xl border border-gray-800/50 p-5">
            <h3 className="text-base font-semibold text-white mb-4 flex items-center gap-2">
              <AlertTriangle className="w-5 h-5 text-red-400" />Combos à Éviter (forte corrélation)
            </h3>
            <div className="space-y-2">
              {combos.filter(c => c.correlation >= 0.6).slice(0, 8).map((combo, i) => (
                <div key={i} className="flex items-center justify-between p-3 rounded-xl bg-red-500/5 border border-red-500/20">
                  <div>
                    <span className="font-medium text-white">
                      {MARKET_LABELS[combo.market_a]} + {MARKET_LABELS[combo.market_b]}
                    </span>
                  </div>
                  <div className="flex items-center gap-3">
                    <span className="text-red-400 font-bold">{(combo.both_win_rate * 100).toFixed(0)}%</span>
                    <span className="text-xs px-2 py-1 rounded bg-red-500/20 text-red-400">
                      r={combo.correlation?.toFixed(2)}
                    </span>
                  </div>
                </div>
              ))}
              {combos.filter(c => c.correlation >= 0.6).length === 0 && (
                <p className="text-gray-500 text-sm text-center py-4">Aucun combo à éviter</p>
              )}
            </div>
          </div>
        </div>

        {/* Correlation Insights */}
        <div className="bg-gray-900/50 rounded-2xl border border-gray-800/50 p-5">
          <h3 className="text-base font-semibold text-white mb-4 flex items-center gap-2">
            <Info className="w-5 h-5 text-cyan-400" />Guide des Corrélations
          </h3>
          <div className="grid md:grid-cols-3 gap-4">
            <div className="p-4 rounded-xl bg-green-500/10 border border-green-500/30">
              <div className="font-medium text-green-400 mb-2">✅ Combo Optimal</div>
              <p className="text-sm text-gray-400">
                Corrélation {"<"} 0.3 = Diversification maximale. Les deux marchés gagnent/perdent indépendamment.
              </p>
            </div>
            <div className="p-4 rounded-xl bg-yellow-500/10 border border-yellow-500/30">
              <div className="font-medium text-yellow-400 mb-2">⚠️ Corrélation Modérée</div>
              <p className="text-sm text-gray-400">
                0.3 - 0.6 = Acceptable mais attention. Une partie des gains/pertes seront liés.
              </p>
            </div>
            <div className="p-4 rounded-xl bg-red-500/10 border border-red-500/30">
              <div className="font-medium text-red-400 mb-2">❌ À Éviter</div>
              <p className="text-sm text-gray-400">
                Corrélation {">"} 0.6 = Pas de diversification. Vous doublez le risque sans doubler l'edge.
              </p>
            </div>
          </div>
        </div>
      </div>
    );
  };

  // ============================================================
  // TAB 5: PRO TOOLS (COMPLET)
  // ============================================================

  const renderProTools = () => (
    <div className="space-y-6">
      <h2 className="text-xl font-bold text-white">Pro Tools</h2>

      {/* Risk Metrics KPIs */}
      <div className="grid grid-cols-2 lg:grid-cols-6 gap-4">
        <KPICard title="Sharpe Ratio" value={riskMetrics?.sharpe_ratio?.toFixed(2) || "0.00"}
          subtitle={riskMetrics?.sharpe_ratio && riskMetrics.sharpe_ratio >= 1 ? "Excellent" : "Acceptable"}
          icon={Activity} color="cyan" />
        <KPICard title="Sortino Ratio" value={riskMetrics?.sortino_ratio?.toFixed(2) || "0.00"}
          icon={TrendingUp} color="violet" />
        <KPICard title="Max Drawdown" value={`${riskMetrics?.max_drawdown_pct?.toFixed(1) || "0.0"}%`}
          subtitle={`${riskMetrics?.max_drawdown_duration_days || 0}j durée`}
          icon={TrendingDown} color="red" />
        <KPICard title="DD Actuel" value={`${riskMetrics?.current_drawdown_pct?.toFixed(1) || "0.0"}%`}
          icon={AlertTriangle} color="amber" />
        <KPICard title="Profit Factor" value={riskMetrics?.profit_factor?.toFixed(2) || "0.00"}
          icon={DollarSign} color="green" />
        <KPICard title="Kelly Optimal" value={`${riskMetrics?.kelly_optimal?.toFixed(1) || "0.0"}%`}
          icon={Calculator} color="blue" />
      </div>

      {/* Calculators Row */}
      <div className="grid lg:grid-cols-2 gap-6">
        {/* Kelly Calculator */}
        <div className="bg-gray-900/50 rounded-2xl border border-gray-800/50 p-5">
          <h3 className="text-base font-semibold text-white mb-4 flex items-center gap-2">
            <Calculator className="w-5 h-5 text-cyan-400" />Kelly Calculator
          </h3>
          <div className="grid grid-cols-2 gap-4 mb-4">
            <InputField label="Probabilité (%)" value={kellyInputs.probability}
              onChange={(v) => setKellyInputs({ ...kellyInputs, probability: v })} min={1} max={99} suffix="%" />
            <InputField label="Cote" value={kellyInputs.odds}
              onChange={(v) => setKellyInputs({ ...kellyInputs, odds: v })} min={1.01} max={100} step={0.01} />
            <InputField label="Bankroll" value={kellyInputs.bankroll}
              onChange={(v) => setKellyInputs({ ...kellyInputs, bankroll: v })} min={1} max={1000000} suffix="€" />
            <InputField label="Drawdown actuel (%)" value={kellyInputs.drawdown}
              onChange={(v) => setKellyInputs({ ...kellyInputs, drawdown: v })} min={0} max={100} suffix="%" />
          </div>
          <button onClick={calculateKelly}
            className="w-full py-2.5 rounded-xl bg-gradient-to-r from-cyan-500 to-violet-500 text-white font-medium hover:opacity-90 transition-all">
            Calculer Kelly
          </button>
          {kellyResult && (
            <div className="mt-4 p-4 rounded-xl bg-gray-800/50 space-y-2">
              <div className="flex justify-between">
                <span className="text-gray-400">Kelly Complet:</span>
                <span className="text-white font-medium">{kellyResult.kelly_full_pct?.toFixed(2)}%</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-400">Kelly Recommandé:</span>
                <span className="text-cyan-400 font-bold text-lg">{kellyResult.kelly_recommended_pct?.toFixed(2)}%</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-400">Mise suggérée:</span>
                <span className="text-green-400 font-medium">{kellyResult.stake_units?.toFixed(2)}€</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-400">Risque de ruine:</span>
                <span className={`font-medium ${kellyResult.risk_of_ruin_pct < 1 ? "text-green-400" : "text-red-400"}`}>
                  {kellyResult.risk_of_ruin_pct?.toFixed(4)}%
                </span>
              </div>
            </div>
          )}
        </div>

        {/* EV Calculator */}
        <div className="bg-gray-900/50 rounded-2xl border border-gray-800/50 p-5">
          <h3 className="text-base font-semibold text-white mb-4 flex items-center gap-2">
            <Zap className="w-5 h-5 text-violet-400" />EV Calculator
          </h3>
          <div className="grid grid-cols-3 gap-4 mb-4">
            <InputField label="Probabilité (%)" value={evInputs.probability}
              onChange={(v) => setEvInputs({ ...evInputs, probability: v })} min={1} max={99} suffix="%" />
            <InputField label="Cote" value={evInputs.odds}
              onChange={(v) => setEvInputs({ ...evInputs, odds: v })} min={1.01} max={100} step={0.01} />
            <InputField label="Mise" value={evInputs.stake}
              onChange={(v) => setEvInputs({ ...evInputs, stake: v })} min={0.1} max={1000} step={0.1} suffix="u" />
          </div>
          <button onClick={calculateEV}
            className="w-full py-2.5 rounded-xl bg-gradient-to-r from-violet-500 to-pink-500 text-white font-medium hover:opacity-90 transition-all">
            Calculer EV
          </button>
          {evResult && (
            <div className="mt-4 p-4 rounded-xl bg-gray-800/50 space-y-2">
              <div className="flex justify-between">
                <span className="text-gray-400">Expected Value:</span>
                <span className={`font-bold text-lg ${evResult.is_positive_ev ? "text-green-400" : "text-red-400"}`}>
                  {evResult.ev_units >= 0 ? "+" : ""}{evResult.ev_units?.toFixed(3)}u
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-400">Edge:</span>
                <span className={`font-medium ${evResult.edge_pct >= 0 ? "text-green-400" : "text-red-400"}`}>
                  {evResult.edge_pct >= 0 ? "+" : ""}{evResult.edge_pct?.toFixed(2)}%
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-400">Win Rate requis:</span>
                <span className="text-white font-medium">{evResult.required_win_rate?.toFixed(1)}%</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-400">Cote breakeven:</span>
                <span className="text-white font-medium">{evResult.breakeven_odds?.toFixed(2)}</span>
              </div>
              <div className="mt-2 p-2 rounded-lg bg-gray-700/50">
                <span className={`text-sm font-medium ${evResult.is_positive_ev ? "text-green-400" : "text-red-400"}`}>
                  {evResult.value_rating}
                </span>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Monte Carlo Simulator */}
      <div className="bg-gray-900/50 rounded-2xl border border-gray-800/50 p-5">
        <h3 className="text-base font-semibold text-white mb-4 flex items-center gap-2">
          <Brain className="w-5 h-5 text-amber-400" />Monte Carlo Simulator
        </h3>
        <div className="grid md:grid-cols-4 gap-4 mb-4">
          <InputField label="Bankroll initial" value={mcInputs.bankroll}
            onChange={(v) => setMcInputs({ ...mcInputs, bankroll: v })} min={100} max={100000} suffix="€" />
          <InputField label="Nombre de paris" value={mcInputs.bets}
            onChange={(v) => setMcInputs({ ...mcInputs, bets: v })} min={50} max={5000} />
          <InputField label="Score minimum" value={mcInputs.minScore}
            onChange={(v) => setMcInputs({ ...mcInputs, minScore: v })} min={0} max={100} />
          <div className="flex items-end">
            <button onClick={runMonteCarlo} disabled={mcLoading}
              className="w-full py-2.5 rounded-xl bg-gradient-to-r from-amber-500 to-orange-500 text-white font-medium hover:opacity-90 transition-all disabled:opacity-50 flex items-center justify-center gap-2">
              {mcLoading ? <RefreshCw className="w-4 h-4 animate-spin" /> : <Play className="w-4 h-4" />}
              {mcLoading ? "Simulation..." : "Simuler"}
            </button>
          </div>
        </div>
        {mcResult && (
          <div className="grid md:grid-cols-4 gap-4 mt-4">
            <div className="p-4 rounded-xl bg-gray-800/50">
              <div className="text-sm text-gray-400 mb-1">Profit Médian</div>
              <div className={`text-xl font-bold ${mcResult.median_profit >= 0 ? "text-green-400" : "text-red-400"}`}>
                {mcResult.median_profit >= 0 ? "+" : ""}{mcResult.median_profit?.toFixed(0)}€
              </div>
            </div>
            <div className="p-4 rounded-xl bg-gray-800/50">
              <div className="text-sm text-gray-400 mb-1">P(Profit)</div>
              <div className="text-xl font-bold text-cyan-400">{mcResult.probability_profit_pct?.toFixed(1)}%</div>
            </div>
            <div className="p-4 rounded-xl bg-gray-800/50">
              <div className="text-sm text-gray-400 mb-1">P(Double)</div>
              <div className="text-xl font-bold text-violet-400">{mcResult.probability_double_pct?.toFixed(1)}%</div>
            </div>
            <div className="p-4 rounded-xl bg-gray-800/50">
              <div className="text-sm text-gray-400 mb-1">P(Ruine)</div>
              <div className={`text-xl font-bold ${mcResult.probability_ruin_pct < 5 ? "text-green-400" : "text-red-400"}`}>
                {mcResult.probability_ruin_pct?.toFixed(2)}%
              </div>
            </div>
            <div className="md:col-span-2 p-4 rounded-xl bg-gray-800/50">
              <div className="text-sm text-gray-400 mb-1">Intervalle de confiance 90%</div>
              <div className="flex items-center gap-2">
                <span className="text-red-400">{mcResult.percentile_5_worst_case?.toFixed(0)}€</span>
                <div className="flex-1 h-2 bg-gray-700 rounded-full overflow-hidden">
                  <div className="h-full bg-gradient-to-r from-red-500 via-cyan-500 to-green-500" style={{ width: "100%" }} />
                </div>
                <span className="text-green-400">{mcResult.percentile_95_best_case?.toFixed(0)}€</span>
              </div>
            </div>
            <div className="md:col-span-2 p-4 rounded-xl bg-gray-800/50">
              <div className="text-sm text-gray-400 mb-1">Max Drawdown Moyen</div>
              <div className="text-xl font-bold text-amber-400">{mcResult.avg_max_drawdown_pct?.toFixed(1)}%</div>
            </div>
          </div>
        )}
      </div>

      {/* Bias Detection */}
      <div className="bg-gray-900/50 rounded-2xl border border-gray-800/50 p-5">
        <h3 className="text-base font-semibold text-white mb-4 flex items-center gap-2">
          <AlertCircle className="w-5 h-5 text-red-400" />Détection des Biais
        </h3>
        {biases.length > 0 ? (
          <div className="space-y-3">
            {biases.map((bias, i) => (
              <div key={i} className={`p-4 rounded-xl border ${
                bias.severity === "critical" ? "bg-red-500/10 border-red-500/30" :
                bias.severity === "warning" ? "bg-yellow-500/10 border-yellow-500/30" :
                "bg-cyan-500/10 border-cyan-500/30"
              }`}>
                <div className="flex items-start justify-between">
                  <div>
                    <div className="font-medium text-white mb-1">{bias.type}</div>
                    <p className="text-sm text-gray-400">{bias.description}</p>
                    <p className="text-xs text-gray-500 mt-2">💡 {bias.recommendation}</p>
                  </div>
                  <span className={`text-sm font-bold ${
                    bias.impact_estimate >= 0 ? "text-green-400" : "text-red-400"
                  }`}>
                    {bias.impact_estimate >= 0 ? "+" : ""}{bias.impact_estimate?.toFixed(1)}% ROI
                  </span>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <p className="text-gray-500 text-center py-6">✅ Aucun biais significatif détecté</p>
        )}
      </div>
    </div>
  );

  // ============================================================
  // MAIN RETURN
  // ============================================================

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-950 via-gray-900 to-gray-950 p-4 md:p-6">
      <div className="max-w-7xl mx-auto">
        {renderHeader()}
        {renderTabs()}
        <AnimatePresence mode="wait">
          <motion.div
            key={activeTab}
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -20 }}
            transition={{ duration: 0.2 }}
          >
            {activeTab === "sweetspot" && renderSweetSpot()}
            {activeTab === "dashboard" && renderDashboard()}
            {activeTab === "markets" && renderMarkets()}
            {activeTab === "clv" && renderCLV()}
            {activeTab === "correlations" && renderCorrelations()}
            {activeTab === "pro" && renderProTools()}
          </motion.div>
        </AnimatePresence>
      </div>
    </div>
  );
}
