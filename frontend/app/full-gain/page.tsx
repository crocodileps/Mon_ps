'use client';

import { useState, useEffect, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Diamond,
  TrendingUp,
  Target,
  Zap,
  RefreshCw,
  ChevronDown,
  ChevronUp,
  Eye,
  BarChart3,
  Percent,
  Goal,
  Flame,
  Star,
  X,
  Activity,
  Layers,
  Search,
  Brain,
  Sparkles,
  AlertCircle,
  XCircle,
  Info
} from 'lucide-react';

// Types
interface PoissonData {
  home_xg: number;
  away_xg: number;
  total_xg: number;
  btts_prob: number;
  over25_prob: number;
  over15_prob: number;
  over35_prob: number;
  '1x2': {
    home: number;
    draw: number;
    away: number;
  };
  most_likely_scores: [string, number][];
}

interface MarketAnalysis {
  score: number;
  probability: number;
  recommendation: string;
  confidence: number;
  value_rating: string;
  kelly_pct: number;
  factors: Record<string, number>;
  reasoning: string;
}

interface MatchAnalysis {
  match_id: string;
  home_team: string;
  away_team: string;
  poisson: PoissonData;
  btts: MarketAnalysis;
  over25: MarketAnalysis;
  patron: {
    score: number;
    match_interest: string;
    data_quality: {
      home_stats: boolean;
      away_stats: boolean;
      h2h: boolean;
    };
  };
  generated_at: string;
  league?: string;
  interpretation?: MatchInterpretation;
}

interface MatchInterpretation {
  summary: string;
  btts_verdict: string;
  over_verdict: string;
  best_bet: string;
  confidence_level: 'HIGH' | 'MEDIUM' | 'LOW';
}

interface Opportunity {
  match_id: string;
  home_team: string;
  away_team: string;
  sport: string;
}

// Generate AI Interpretation
const generateInterpretation = (analysis: MatchAnalysis): MatchInterpretation => {
  const bttsScore = analysis.btts.score;
  const overScore = analysis.over25.score;
  const totalXG = analysis.poisson.total_xg;
  
  let bestBet = '';
  let confidenceLevel: 'HIGH' | 'MEDIUM' | 'LOW' = 'LOW';
  const maxScore = Math.max(bttsScore, overScore);
  
  if (maxScore >= 70) {
    confidenceLevel = 'HIGH';
    bestBet = bttsScore > overScore ? 'BTTS OUI' : 'OVER 2.5';
  } else if (maxScore >= 55) {
    confidenceLevel = 'MEDIUM';
    if (bttsScore >= 55 && overScore >= 55) {
      bestBet = 'BTTS + OVER 2.5';
    } else if (bttsScore >= 55) {
      bestBet = 'BTTS OUI';
    } else {
      bestBet = 'OVER 2.5';
    }
  } else {
    confidenceLevel = 'LOW';
    bestBet = bttsScore < 40 && overScore < 40 ? 'UNDER 2.5' : 'ÉVITER';
  }
  
  let bttsVerdict = bttsScore >= 70 ? `💎 DIAMOND (${bttsScore.toFixed(0)}%)` :
                    bttsScore >= 60 ? `✅ STRONG (${bttsScore.toFixed(0)}%)` :
                    bttsScore >= 50 ? `📈 POSSIBLE (${bttsScore.toFixed(0)}%)` :
                    `⏭️ SKIP (${bttsScore.toFixed(0)}%)`;
  
  let overVerdict = overScore >= 70 ? `💎 DIAMOND (${overScore.toFixed(0)}%)` :
                    overScore >= 60 ? `✅ STRONG (${overScore.toFixed(0)}%)` :
                    overScore >= 50 ? `📈 POSSIBLE (${overScore.toFixed(0)}%)` :
                    `⏭️ SKIP (${overScore.toFixed(0)}%)`;
  
  let summary = totalXG >= 3.5 ? `Match offensif (xG: ${totalXG.toFixed(2)})` :
                totalXG >= 2.8 ? `Match équilibré (xG: ${totalXG.toFixed(2)})` :
                totalXG >= 2.2 ? `Match modéré (xG: ${totalXG.toFixed(2)})` :
                `Match défensif (xG: ${totalXG.toFixed(2)})`;
  
  return { summary, btts_verdict: bttsVerdict, over_verdict: overVerdict, best_bet: bestBet, confidence_level: confidenceLevel };
};

// Animated Counter
const AnimatedCounter = ({ value, suffix = '' }: { value: number; suffix?: string }) => {
  const [displayValue, setDisplayValue] = useState(0);
  useEffect(() => {
    const timer = setInterval(() => {
      setDisplayValue(prev => {
        if (prev >= value) return value;
        return prev + value / 30;
      });
    }, 33);
    return () => clearInterval(timer);
  }, [value]);
  return <span>{displayValue.toFixed(1)}{suffix}</span>;
};

// Score Badge
const ScoreBadge = ({ score, size = 'md' }: { score: number; size?: 'sm' | 'md' }) => {
  const getColor = () => {
    if (score >= 70) return 'from-emerald-500 to-cyan-400';
    if (score >= 60) return 'from-cyan-500 to-blue-400';
    if (score >= 50) return 'from-yellow-500 to-orange-400';
    return 'from-red-500 to-pink-400';
  };
  const sizes = { sm: 'w-10 h-10 text-xs', md: 'w-14 h-14 text-sm' };
  return (
    <div className={`${sizes[size]} rounded-full bg-gradient-to-br ${getColor()} flex items-center justify-center font-bold text-white shadow-lg`}>
      {score.toFixed(0)}
    </div>
  );
};

// Confidence Badge
const ConfidenceBadge = ({ level }: { level: 'HIGH' | 'MEDIUM' | 'LOW' }) => {
  const styles = {
    HIGH: 'bg-emerald-500/20 text-emerald-400',
    MEDIUM: 'bg-yellow-500/20 text-yellow-400',
    LOW: 'bg-slate-700 text-slate-400'
  };
  return <span className={`px-2 py-1 rounded-full text-xs font-medium ${styles[level]}`}>{level}</span>;
};

// Recommendation Badge
const RecommendationBadge = ({ recommendation }: { recommendation: string }) => {
  const getStyle = () => {
    if (recommendation.includes('DIAMOND')) return 'bg-gradient-to-r from-purple-600 to-pink-500 text-white';
    if (recommendation.includes('STRONG')) return 'bg-gradient-to-r from-emerald-600 to-cyan-500 text-white';
    if (recommendation.includes('LEAN')) return 'bg-gradient-to-r from-yellow-600 to-orange-500 text-white';
    return 'bg-slate-700 text-slate-300';
  };
  return <span className={`px-2 py-1 rounded-full text-xs font-medium ${getStyle()}`}>{recommendation.replace(/[^\w\s]/g, '').trim()}</span>;
};

// Factor Bar
const FactorBar = ({ label, value, icon: Icon }: { label: string; value: number; icon: any }) => {
  const getColor = () => value >= 70 ? 'from-emerald-500 to-cyan-400' : value >= 50 ? 'from-yellow-500 to-orange-400' : 'from-red-500 to-pink-400';
  return (
    <div className="space-y-1">
      <div className="flex justify-between text-xs">
        <span className="flex items-center gap-1 text-slate-400"><Icon className="w-3 h-3" />{label}</span>
        <span className="font-bold text-white">{value.toFixed(0)}%</span>
      </div>
      <div className="h-2 bg-slate-800 rounded-full overflow-hidden">
        <motion.div initial={{ width: 0 }} animate={{ width: `${value}%` }} className={`h-full rounded-full bg-gradient-to-r ${getColor()}`} />
      </div>
    </div>
  );
};

// xG Visual
const XGVisual = ({ homeXG, awayXG, homeTeam, awayTeam }: { homeXG: number; awayXG: number; homeTeam: string; awayTeam: string }) => {
  const total = homeXG + awayXG;
  const homePercent = (homeXG / total) * 100;
  return (
    <div className="space-y-2">
      <div className="flex justify-between text-xs text-slate-400"><span>{homeTeam}</span><span>{awayTeam}</span></div>
      <div className="h-8 bg-slate-800 rounded-lg overflow-hidden flex">
        <div style={{ width: `${homePercent}%` }} className="bg-gradient-to-r from-cyan-600 to-cyan-400 flex items-center justify-center">
          <span className="text-xs font-bold text-white">{homeXG.toFixed(2)}</span>
        </div>
        <div style={{ width: `${100 - homePercent}%` }} className="bg-gradient-to-r from-pink-400 to-pink-600 flex items-center justify-center">
          <span className="text-xs font-bold text-white">{awayXG.toFixed(2)}</span>
        </div>
      </div>
      <div className="text-center text-sm font-bold text-white">Total xG: <span className="text-cyan-400">{total.toFixed(2)}</span></div>
    </div>
  );
};

// Detail Drawer
const DetailDrawer = ({ analysis, isOpen, onClose }: { analysis: MatchAnalysis | null; isOpen: boolean; onClose: () => void }) => {
  if (!analysis) return null;
  return (
    <AnimatePresence>
      {isOpen && (
        <>
          <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} onClick={onClose} className="fixed inset-0 bg-black/60 backdrop-blur-sm z-40" />
          <motion.div initial={{ x: '100%' }} animate={{ x: 0 }} exit={{ x: '100%' }} transition={{ type: 'spring', damping: 25 }} className="fixed right-0 top-0 h-full w-full max-w-xl bg-slate-900/95 backdrop-blur-xl border-l border-cyan-500/20 z-50 overflow-y-auto">
            <div className="sticky top-0 bg-slate-900/90 backdrop-blur-xl border-b border-slate-700/50 p-4 z-10">
              <div className="flex items-center justify-between">
                <div>
                  <h2 className="text-xl font-bold text-white">{analysis.home_team} vs {analysis.away_team}</h2>
                  <p className="text-sm text-slate-400">{analysis.league || 'Football'}</p>
                </div>
                <button onClick={onClose} className="p-2 rounded-lg bg-slate-800 hover:bg-slate-700"><X className="w-5 h-5 text-slate-400" /></button>
              </div>
            </div>
            <div className="p-4 space-y-6">
              {/* Interpretation */}
              {analysis.interpretation && (
                <div className="bg-gradient-to-br from-slate-800/80 to-slate-900/80 rounded-xl p-4 border border-cyan-500/30">
                  <div className="flex items-center gap-2 mb-3">
                    <Brain className="w-5 h-5 text-cyan-400" />
                    <span className="text-sm font-semibold text-cyan-400">Analyse</span>
                    <ConfidenceBadge level={analysis.interpretation.confidence_level} />
                  </div>
                  <p className="text-sm text-slate-300 mb-2">{analysis.interpretation.summary}</p>
                  <div className="space-y-1 text-sm text-slate-400 mb-3">
                    <div className="flex items-center gap-2"><Goal className="w-4 h-4 text-emerald-400" />{analysis.interpretation.btts_verdict}</div>
                    <div className="flex items-center gap-2"><TrendingUp className="w-4 h-4 text-blue-400" />{analysis.interpretation.over_verdict}</div>
                  </div>
                  <div className="flex items-center gap-2 bg-slate-900/50 rounded-lg p-3">
                    <Sparkles className="w-5 h-5 text-yellow-400" />
                    <span className="text-sm text-slate-400">Meilleur pari:</span>
                    <span className="font-bold text-lg text-yellow-400">{analysis.interpretation.best_bet}</span>
                  </div>
                </div>
              )}
              {/* xG */}
              <div className="bg-slate-800/50 rounded-xl p-4 border border-slate-700/50">
                <h3 className="text-sm font-semibold text-slate-400 mb-3 flex items-center gap-2"><Target className="w-4 h-4" />Expected Goals</h3>
                <XGVisual homeXG={analysis.poisson.home_xg} awayXG={analysis.poisson.away_xg} homeTeam={analysis.home_team} awayTeam={analysis.away_team} />
              </div>
              {/* 1X2 */}
              <div className="bg-slate-800/50 rounded-xl p-4 border border-slate-700/50">
                <h3 className="text-sm font-semibold text-slate-400 mb-3 flex items-center gap-2"><BarChart3 className="w-4 h-4" />Match Outcome</h3>
                <div className="grid grid-cols-3 gap-3">
                  <div className="text-center p-3 bg-slate-900/50 rounded-lg"><div className="text-2xl font-bold text-cyan-400">{analysis.poisson['1x2'].home}%</div><div className="text-xs text-slate-400">Home</div></div>
                  <div className="text-center p-3 bg-slate-900/50 rounded-lg"><div className="text-2xl font-bold text-yellow-400">{analysis.poisson['1x2'].draw}%</div><div className="text-xs text-slate-400">Draw</div></div>
                  <div className="text-center p-3 bg-slate-900/50 rounded-lg"><div className="text-2xl font-bold text-pink-400">{analysis.poisson['1x2'].away}%</div><div className="text-xs text-slate-400">Away</div></div>
                </div>
              </div>
              {/* BTTS */}
              <div className="bg-gradient-to-br from-emerald-900/30 to-cyan-900/30 rounded-xl p-4 border border-emerald-500/30">
                <div className="flex items-center justify-between mb-4">
                  <h3 className="text-sm font-semibold text-emerald-400 flex items-center gap-2"><Goal className="w-4 h-4" />BTTS</h3>
                  <ScoreBadge score={analysis.btts.score} size="sm" />
                </div>
                <div className="space-y-2 text-sm">
                  <div className="flex justify-between"><span className="text-slate-400">Recommendation</span><RecommendationBadge recommendation={analysis.btts.recommendation} /></div>
                  <div className="flex justify-between"><span className="text-slate-400">Probability</span><span className="font-bold text-white">{analysis.btts.probability}%</span></div>
                  <div className="flex justify-between"><span className="text-slate-400">Confidence</span><span className="font-bold text-white">{analysis.btts.confidence}%</span></div>
                </div>
                <div className="mt-4 pt-4 border-t border-slate-700/50 space-y-3">
                  {analysis.btts.factors.poisson && <FactorBar label="Poisson" value={analysis.btts.factors.poisson} icon={BarChart3} />}
                  {analysis.btts.factors.stats_global && <FactorBar label="Stats" value={analysis.btts.factors.stats_global} icon={Activity} />}
                  {analysis.btts.factors.form_l5 && <FactorBar label="Form L5" value={analysis.btts.factors.form_l5} icon={Flame} />}
                </div>
              </div>
              {/* Over 2.5 */}
              <div className="bg-gradient-to-br from-blue-900/30 to-purple-900/30 rounded-xl p-4 border border-blue-500/30">
                <div className="flex items-center justify-between mb-4">
                  <h3 className="text-sm font-semibold text-blue-400 flex items-center gap-2"><TrendingUp className="w-4 h-4" />Over 2.5</h3>
                  <ScoreBadge score={analysis.over25.score} size="sm" />
                </div>
                <div className="space-y-2 text-sm">
                  <div className="flex justify-between"><span className="text-slate-400">Recommendation</span><RecommendationBadge recommendation={analysis.over25.recommendation} /></div>
                  <div className="flex justify-between"><span className="text-slate-400">Probability</span><span className="font-bold text-white">{analysis.over25.probability}%</span></div>
                  <div className="flex justify-between"><span className="text-slate-400">xG Total</span><span className="font-bold text-cyan-400">{analysis.poisson.total_xg.toFixed(2)}</span></div>
                </div>
                <div className="mt-4 pt-4 border-t border-slate-700/50 space-y-3">
                  {analysis.over25.factors.poisson && <FactorBar label="Poisson" value={analysis.over25.factors.poisson} icon={BarChart3} />}
                  {analysis.over25.factors.xg_factor && <FactorBar label="xG Factor" value={analysis.over25.factors.xg_factor} icon={Target} />}
                  {analysis.over25.factors.stats_global && <FactorBar label="Stats" value={analysis.over25.factors.stats_global} icon={Activity} />}
                </div>
              </div>
              {/* Scores probables */}
              <div className="bg-slate-800/50 rounded-xl p-4 border border-slate-700/50">
                <h3 className="text-sm font-semibold text-slate-400 mb-3 flex items-center gap-2"><Star className="w-4 h-4" />Most Likely Scores</h3>
                <div className="space-y-2">
                  {analysis.poisson.most_likely_scores.slice(0, 5).map(([score, prob], idx) => (
                    <div key={score} className="flex items-center gap-3">
                      <span className="w-10 text-sm font-mono text-slate-400">{score}</span>
                      <div className="flex-1 h-5 bg-slate-800 rounded-full overflow-hidden">
                        <div style={{ width: `${prob * 3}%` }} className={`h-full rounded-full ${idx === 0 ? 'bg-gradient-to-r from-cyan-500 to-emerald-400' : 'bg-gradient-to-r from-slate-600 to-slate-500'}`} />
                      </div>
                      <span className="w-12 text-right text-sm font-bold text-white">{prob.toFixed(1)}%</span>
                    </div>
                  ))}
                </div>
              </div>
              {/* Over probs */}
              <div className="bg-slate-800/50 rounded-xl p-4 border border-slate-700/50">
                <h3 className="text-sm font-semibold text-slate-400 mb-3 flex items-center gap-2"><Percent className="w-4 h-4" />Goals Probabilities</h3>
                <div className="grid grid-cols-3 gap-2">
                  <div className="text-center p-2 bg-slate-900/50 rounded-lg"><div className="text-lg font-bold text-emerald-400">{analysis.poisson.over15_prob}%</div><div className="text-xs text-slate-500">Over 1.5</div></div>
                  <div className="text-center p-2 bg-slate-900/50 rounded-lg border border-cyan-500/30"><div className="text-lg font-bold text-cyan-400">{analysis.poisson.over25_prob}%</div><div className="text-xs text-slate-500">Over 2.5</div></div>
                  <div className="text-center p-2 bg-slate-900/50 rounded-lg"><div className="text-lg font-bold text-pink-400">{analysis.poisson.over35_prob}%</div><div className="text-xs text-slate-500">Over 3.5</div></div>
                </div>
              </div>
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
};

// Match Row
const MatchRow = ({ analysis, onOpenDrawer, isExpanded, onToggleExpand }: { analysis: MatchAnalysis; onOpenDrawer: () => void; isExpanded: boolean; onToggleExpand: () => void }) => {
  const maxScore = Math.max(analysis.btts.score, analysis.over25.score);
  const interestLevel = analysis.patron?.match_interest || '';
  const interpretation = analysis.interpretation;
  
  const getInterestColor = () => {
    if (maxScore >= 70) return 'border-l-purple-500';
    if (maxScore >= 60) return 'border-l-cyan-500';
    if (maxScore >= 50) return 'border-l-yellow-500';
    return 'border-l-slate-600';
  };
  
  return (
    <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className={`bg-slate-800/40 backdrop-blur-sm rounded-xl border border-slate-700/50 hover:border-cyan-500/30 transition-all border-l-4 ${getInterestColor()}`}>
      <div className="p-4 cursor-pointer" onClick={onToggleExpand}>
        <div className="flex items-center justify-between gap-4">
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2">
              <h3 className="font-semibold text-white truncate">{analysis.home_team} vs {analysis.away_team}</h3>
              {maxScore >= 70 && <Diamond className="w-4 h-4 text-purple-400 flex-shrink-0" />}
            </div>
            <p className="text-xs text-slate-500 mt-1">{analysis.league || 'Football'} • xG: {analysis.poisson.total_xg.toFixed(2)}</p>
          </div>
          {interpretation && (
            <div className="hidden md:block">
              <div className={`px-3 py-1 rounded-lg text-xs font-medium ${interpretation.confidence_level === 'HIGH' ? 'bg-emerald-500/20 text-emerald-400' : interpretation.confidence_level === 'MEDIUM' ? 'bg-yellow-500/20 text-yellow-400' : 'bg-slate-700 text-slate-400'}`}>
                {interpretation.best_bet}
              </div>
            </div>
          )}
          <div className="flex items-center gap-4">
            <div className="text-center"><div className="text-xs text-slate-500 mb-1">BTTS</div><ScoreBadge score={analysis.btts.score} size="sm" /></div>
            <div className="text-center"><div className="text-xs text-slate-500 mb-1">Over 2.5</div><ScoreBadge score={analysis.over25.score} size="sm" /></div>
            <div className="flex items-center gap-2">
              <button onClick={(e) => { e.stopPropagation(); onOpenDrawer(); }} className="p-2 rounded-lg bg-cyan-500/20 hover:bg-cyan-500/30 text-cyan-400"><Eye className="w-4 h-4" /></button>
              <button className="p-2 rounded-lg bg-slate-700/50 hover:bg-slate-700 text-slate-400">{isExpanded ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}</button>
            </div>
          </div>
        </div>
      </div>
      <AnimatePresence>
        {isExpanded && (
          <motion.div initial={{ height: 0, opacity: 0 }} animate={{ height: 'auto', opacity: 1 }} exit={{ height: 0, opacity: 0 }} className="overflow-hidden">
            <div className="px-4 pb-4 border-t border-slate-700/50">
              {interpretation && (
                <div className="mt-4 p-3 bg-gradient-to-r from-cyan-900/30 to-purple-900/30 rounded-lg border border-cyan-500/20">
                  <div className="flex items-center gap-2 mb-2"><Brain className="w-4 h-4 text-cyan-400" /><span className="text-sm font-semibold text-cyan-400">Analyse</span><ConfidenceBadge level={interpretation.confidence_level} /></div>
                  <p className="text-sm text-slate-300 mb-2">{interpretation.summary}</p>
                  <div className="grid grid-cols-2 gap-2 text-xs text-slate-400">
                    <div>{interpretation.btts_verdict}</div>
                    <div>{interpretation.over_verdict}</div>
                  </div>
                  <div className="mt-2 flex items-center gap-2"><Sparkles className="w-4 h-4 text-yellow-400" /><span className="text-sm font-bold text-yellow-400">{interpretation.best_bet}</span></div>
                </div>
              )}
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mt-4">
                <div className="space-y-2">
                  <h4 className="text-xs font-semibold text-slate-500 uppercase">Quick Stats</h4>
                  <div className="grid grid-cols-2 gap-2 text-sm">
                    <div className="flex justify-between"><span className="text-slate-400">Home xG</span><span className="text-cyan-400 font-bold">{analysis.poisson.home_xg.toFixed(2)}</span></div>
                    <div className="flex justify-between"><span className="text-slate-400">Away xG</span><span className="text-pink-400 font-bold">{analysis.poisson.away_xg.toFixed(2)}</span></div>
                  </div>
                </div>
                <div className="space-y-2">
                  <h4 className="text-xs font-semibold text-slate-500 uppercase">Recommendations</h4>
                  <div className="space-y-1">
                    <div className="flex justify-between items-center"><span className="text-slate-400 text-sm">BTTS</span><RecommendationBadge recommendation={analysis.btts.recommendation} /></div>
                    <div className="flex justify-between items-center"><span className="text-slate-400 text-sm">Over</span><RecommendationBadge recommendation={analysis.over25.recommendation} /></div>
                  </div>
                </div>
                <div className="space-y-2">
                  <h4 className="text-xs font-semibold text-slate-500 uppercase">Top Scores</h4>
                  <div className="flex gap-2">
                    {analysis.poisson.most_likely_scores.slice(0, 3).map(([score, prob]) => (
                      <div key={score} className="flex-1 text-center p-2 bg-slate-900/50 rounded-lg"><div className="font-bold text-white">{score}</div><div className="text-xs text-slate-500">{prob.toFixed(1)}%</div></div>
                    ))}
                  </div>
                </div>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );
};

// Main Page
export default function FullGainPage() {
  const [analyses, setAnalyses] = useState<MatchAnalysis[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [selectedAnalysis, setSelectedAnalysis] = useState<MatchAnalysis | null>(null);
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [expandedRows, setExpandedRows] = useState<Set<string>>(new Set());
  const [progress, setProgress] = useState({ current: 0, total: 0 });
  const [error, setError] = useState<string | null>(null);
  const [filters, setFilters] = useState({ minScore: 0, market: 'all', search: '' });
  const [stats, setStats] = useState({ total: 0, diamond: 0, strong: 0, avgBtts: 0, avgOver: 0 });
  
  const fetchAnalyses = useCallback(async () => {
    try {
      setError(null);
      setProgress({ current: 0, total: 0 });
      
      // Get opportunities
      const oppRes = await fetch('http://91.98.131.218:8001/opportunities/opportunities/?limit=100');
      if (!oppRes.ok) throw new Error(`API Error: ${oppRes.status}`);
      
      const oppData = await oppRes.json();
      
      // Handle if response is not an array
      const opportunities: Opportunity[] = Array.isArray(oppData) ? oppData : [];
      if (opportunities.length === 0) {
        setAnalyses([]);
        setLoading(false);
        return;
      }
      
      // Remove duplicates
      const seen = new Set<string>();
      const uniqueOpportunities = opportunities.filter(opp => {
        if (seen.has(opp.match_id)) return false;
        seen.add(opp.match_id);
        return true;
      });
      
      setProgress({ current: 0, total: uniqueOpportunities.length });
      
      // Analyze in batches
      const allAnalyses: MatchAnalysis[] = [];
      const batchSize = 5;
      
      for (let i = 0; i < uniqueOpportunities.length; i += batchSize) {
        const batch = uniqueOpportunities.slice(i, i + batchSize);
        
        const batchResults = await Promise.all(
          batch.map(async (opp) => {
            try {
              const res = await fetch(`http://91.98.131.218:8001/patron-diamond/analyze/${opp.match_id}`);
              if (!res.ok) return null;
              const analysis = await res.json();
              const interpretation = generateInterpretation(analysis);
              return { ...analysis, league: opp.sport?.replace('soccer_', '').replace(/_/g, ' ').toUpperCase(), interpretation };
            } catch { return null; }
          })
        );
        
        allAnalyses.push(...batchResults.filter(Boolean) as MatchAnalysis[]);
        setProgress({ current: Math.min(i + batchSize, uniqueOpportunities.length), total: uniqueOpportunities.length });
        
        if (i + batchSize < uniqueOpportunities.length) await new Promise(r => setTimeout(r, 50));
      }
      
      // Sort by max score
      allAnalyses.sort((a, b) => Math.max(b.btts.score, b.over25.score) - Math.max(a.btts.score, a.over25.score));
      setAnalyses(allAnalyses);
      
      // Stats
      const diamond = allAnalyses.filter(a => a.btts.score >= 70 || a.over25.score >= 70).length;
      const strong = allAnalyses.filter(a => (a.btts.score >= 60 && a.btts.score < 70) || (a.over25.score >= 60 && a.over25.score < 70)).length;
      const avgBtts = allAnalyses.length > 0 ? allAnalyses.reduce((acc, a) => acc + a.btts.score, 0) / allAnalyses.length : 0;
      const avgOver = allAnalyses.length > 0 ? allAnalyses.reduce((acc, a) => acc + a.over25.score, 0) / allAnalyses.length : 0;
      setStats({ total: allAnalyses.length, diamond, strong, avgBtts, avgOver });
      
    } catch (err: any) {
      setError(err.message || 'Erreur de chargement');
      console.error('Error:', err);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);
  
  useEffect(() => { fetchAnalyses(); }, [fetchAnalyses]);
  
  const handleRefresh = () => { setRefreshing(true); setLoading(true); fetchAnalyses(); };
  const toggleExpand = (id: string) => { setExpandedRows(prev => { const n = new Set(prev); n.has(id) ? n.delete(id) : n.add(id); return n; }); };
  const openDrawer = (a: MatchAnalysis) => { setSelectedAnalysis(a); setDrawerOpen(true); };
  
  const filteredAnalyses = analyses.filter(a => {
    const maxScore = Math.max(a.btts.score, a.over25.score);
    if (maxScore < filters.minScore) return false;
    if (filters.market === 'btts' && a.btts.score < 50) return false;
    if (filters.market === 'over25' && a.over25.score < 50) return false;
    if (filters.search && !a.home_team.toLowerCase().includes(filters.search.toLowerCase()) && !a.away_team.toLowerCase().includes(filters.search.toLowerCase())) return false;
    return true;
  });
  
  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-950 via-slate-900 to-slate-950">
      <div className="fixed inset-0 overflow-hidden pointer-events-none">
        <div className="absolute top-1/4 -left-1/4 w-96 h-96 bg-cyan-500/10 rounded-full blur-3xl animate-pulse" />
        <div className="absolute bottom-1/4 -right-1/4 w-96 h-96 bg-purple-500/10 rounded-full blur-3xl animate-pulse" style={{ animationDelay: '1s' }} />
      </div>
      
      <div className="relative z-10 max-w-7xl mx-auto px-4 py-8">
        {/* Header */}
        <motion.div initial={{ opacity: 0, y: -20 }} animate={{ opacity: 1, y: 0 }} className="mb-8">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-4xl font-black text-transparent bg-clip-text bg-gradient-to-r from-cyan-400 via-purple-400 to-pink-400">FULL GAIN 2.0</h1>
              <p className="text-slate-400 mt-1">Multi-Market Analysis • BTTS & Over 2.5</p>
            </div>
            <button onClick={handleRefresh} disabled={refreshing} className="flex items-center gap-2 px-4 py-2 bg-cyan-500/20 hover:bg-cyan-500/30 text-cyan-400 rounded-lg disabled:opacity-50">
              <RefreshCw className={`w-4 h-4 ${refreshing ? 'animate-spin' : ''}`} />Refresh
            </button>
          </div>
        </motion.div>
        
        {/* Error */}
        {error && (
          <div className="mb-6 p-4 bg-red-900/30 border border-red-500/50 rounded-xl text-red-400">
            <div className="flex items-center gap-2"><AlertCircle className="w-5 h-5" />{error}</div>
          </div>
        )}
        
        {/* Progress */}
        {loading && progress.total > 0 && (
          <div className="mb-6">
            <div className="flex justify-between text-sm text-slate-400 mb-2"><span>Analyse en cours...</span><span>{progress.current} / {progress.total}</span></div>
            <div className="h-2 bg-slate-800 rounded-full overflow-hidden"><div style={{ width: `${(progress.current / progress.total) * 100}%` }} className="h-full bg-gradient-to-r from-cyan-500 to-purple-500 transition-all" /></div>
          </div>
        )}
        
        {/* Stats */}
        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="grid grid-cols-2 md:grid-cols-5 gap-4 mb-8">
          <div className="bg-slate-800/50 rounded-xl p-4 border border-slate-700/50">
            <div className="flex items-center gap-2 text-slate-400 text-sm mb-2"><Activity className="w-4 h-4" />Matchs</div>
            <div className="text-3xl font-bold text-white"><AnimatedCounter value={stats.total} /></div>
          </div>
          <div className="bg-gradient-to-br from-purple-900/50 to-pink-900/50 rounded-xl p-4 border border-purple-500/30">
            <div className="flex items-center gap-2 text-purple-300 text-sm mb-2"><Diamond className="w-4 h-4" />Diamond</div>
            <div className="text-3xl font-bold text-white"><AnimatedCounter value={stats.diamond} /></div>
          </div>
          <div className="bg-gradient-to-br from-emerald-900/50 to-cyan-900/50 rounded-xl p-4 border border-emerald-500/30">
            <div className="flex items-center gap-2 text-emerald-300 text-sm mb-2"><Zap className="w-4 h-4" />Strong</div>
            <div className="text-3xl font-bold text-white"><AnimatedCounter value={stats.strong} /></div>
          </div>
          <div className="bg-slate-800/50 rounded-xl p-4 border border-slate-700/50">
            <div className="flex items-center gap-2 text-slate-400 text-sm mb-2"><Goal className="w-4 h-4" />Avg BTTS</div>
            <div className="text-3xl font-bold text-cyan-400"><AnimatedCounter value={stats.avgBtts} suffix="%" /></div>
          </div>
          <div className="bg-slate-800/50 rounded-xl p-4 border border-slate-700/50">
            <div className="flex items-center gap-2 text-slate-400 text-sm mb-2"><TrendingUp className="w-4 h-4" />Avg Over</div>
            <div className="text-3xl font-bold text-pink-400"><AnimatedCounter value={stats.avgOver} suffix="%" /></div>
          </div>
        </motion.div>
        
        {/* Filters */}
        <div className="flex flex-wrap items-center gap-4 mb-6">
          <div className="relative flex-1 min-w-[200px]">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
            <input type="text" placeholder="Search teams..." value={filters.search} onChange={(e) => setFilters(p => ({ ...p, search: e.target.value }))} className="w-full pl-10 pr-4 py-2 bg-slate-800/50 border border-slate-700/50 rounded-lg text-white placeholder-slate-500 focus:outline-none focus:border-cyan-500/50" />
          </div>
          <select value={filters.market} onChange={(e) => setFilters(p => ({ ...p, market: e.target.value }))} className="px-4 py-2 bg-slate-800/50 border border-slate-700/50 rounded-lg text-white">
            <option value="all">All Markets</option><option value="btts">BTTS Only</option><option value="over25">Over 2.5 Only</option>
          </select>
          <select value={filters.minScore} onChange={(e) => setFilters(p => ({ ...p, minScore: Number(e.target.value) }))} className="px-4 py-2 bg-slate-800/50 border border-slate-700/50 rounded-lg text-white">
            <option value={0}>All Scores</option><option value={50}>≥ 50</option><option value={60}>≥ 60</option><option value={70}>≥ 70 💎</option>
          </select>
        </div>
        
        {/* List */}
        <div className="space-y-4">
          {loading ? (
            <div className="flex flex-col items-center py-20">
              <RefreshCw className="w-10 h-10 text-cyan-400 animate-spin mb-4" />
              <p className="text-slate-400">Analyzing matches...</p>
            </div>
          ) : filteredAnalyses.length === 0 ? (
            <div className="text-center py-20"><Target className="w-16 h-16 text-slate-600 mx-auto mb-4" /><p className="text-slate-400">No matches found</p></div>
          ) : (
            filteredAnalyses.map((a, idx) => (
              <motion.div key={a.match_id} initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: Math.min(idx * 0.02, 0.5) }}>
                <MatchRow analysis={a} onOpenDrawer={() => openDrawer(a)} isExpanded={expandedRows.has(a.match_id)} onToggleExpand={() => toggleExpand(a.match_id)} />
              </motion.div>
            ))
          )}
        </div>
        
        {!loading && filteredAnalyses.length > 0 && (
          <div className="mt-8 text-center text-sm text-slate-500">
            {filteredAnalyses.length} / {analyses.length} matchs • {new Date().toLocaleTimeString()}
          </div>
        )}
      </div>
      
      <DetailDrawer analysis={selectedAnalysis} isOpen={drawerOpen} onClose={() => setDrawerOpen(false)} />
    </div>
  );
}
