'use client';

import { useState, useEffect, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Diamond,
  TrendingUp,
  Target,
  Zap,
  Filter,
  RefreshCw,
  ChevronDown,
  ChevronUp,
  Eye,
  BarChart3,
  Percent,
  Goal,
  Shield,
  Flame,
  Star,
  X,
  ArrowUpRight,
  Activity,
  Layers,
  Search,
  SlidersHorizontal
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
  // Extra fields from opportunities
  league?: string;
  commence_time?: string;
  best_odds_btts?: number;
  best_odds_over25?: number;
}

interface Opportunity {
  match_id: string;
  home_team: string;
  away_team: string;
  sport: string;
  commence_time: string;
  best_odds: number;
  best_bookmaker: string;
  worst_odds: number;
  edge_pct: number;
}

// Animated Counter Component
const AnimatedCounter = ({ value, suffix = '', prefix = '' }: { value: number; suffix?: string; prefix?: string }) => {
  const [displayValue, setDisplayValue] = useState(0);
  
  useEffect(() => {
    const duration = 1000;
    const steps = 30;
    const increment = value / steps;
    let current = 0;
    
    const timer = setInterval(() => {
      current += increment;
      if (current >= value) {
        setDisplayValue(value);
        clearInterval(timer);
      } else {
        setDisplayValue(Math.floor(current));
      }
    }, duration / steps);
    
    return () => clearInterval(timer);
  }, [value]);
  
  return <span>{prefix}{displayValue.toFixed(1)}{suffix}</span>;
};

// Score Badge Component
const ScoreBadge = ({ score, size = 'md' }: { score: number; size?: 'sm' | 'md' | 'lg' }) => {
  const getColor = () => {
    if (score >= 75) return 'from-emerald-500 to-cyan-400';
    if (score >= 65) return 'from-cyan-500 to-blue-400';
    if (score >= 55) return 'from-yellow-500 to-orange-400';
    if (score >= 45) return 'from-orange-500 to-red-400';
    return 'from-red-500 to-pink-400';
  };
  
  const getGlow = () => {
    if (score >= 75) return 'shadow-emerald-500/50';
    if (score >= 65) return 'shadow-cyan-500/50';
    if (score >= 55) return 'shadow-yellow-500/50';
    return 'shadow-red-500/50';
  };
  
  const sizes = {
    sm: 'w-10 h-10 text-xs',
    md: 'w-14 h-14 text-sm',
    lg: 'w-20 h-20 text-lg'
  };
  
  return (
    <div className={`
      ${sizes[size]} rounded-full bg-gradient-to-br ${getColor()}
      flex items-center justify-center font-bold text-white
      shadow-lg ${getGlow()}
    `}>
      {score.toFixed(0)}
    </div>
  );
};

// Recommendation Badge
const RecommendationBadge = ({ recommendation }: { recommendation: string }) => {
  const getStyle = () => {
    if (recommendation.includes('DIAMOND')) return 'bg-gradient-to-r from-purple-600 to-pink-500 text-white';
    if (recommendation.includes('STRONG')) return 'bg-gradient-to-r from-emerald-600 to-cyan-500 text-white';
    if (recommendation.includes('LEAN')) return 'bg-gradient-to-r from-yellow-600 to-orange-500 text-white';
    if (recommendation.includes('SKIP')) return 'bg-slate-700 text-slate-300';
    return 'bg-red-900 text-red-300';
  };
  
  const getIcon = () => {
    if (recommendation.includes('DIAMOND')) return <Diamond className="w-3 h-3" />;
    if (recommendation.includes('STRONG')) return <Zap className="w-3 h-3" />;
    if (recommendation.includes('LEAN')) return <TrendingUp className="w-3 h-3" />;
    return null;
  };
  
  return (
    <span className={`
      inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs font-medium
      ${getStyle()}
    `}>
      {getIcon()}
      {recommendation.replace(/[^\w\s]/g, '').trim()}
    </span>
  );
};

// Poisson Chart Component
const PoissonChart = ({ scores }: { scores: [string, number][] }) => {
  const maxProb = Math.max(...scores.map(s => s[1]));
  
  return (
    <div className="space-y-2">
      {scores.slice(0, 5).map(([score, prob], idx) => (
        <div key={score} className="flex items-center gap-3">
          <span className="w-10 text-sm font-mono text-slate-400">{score}</span>
          <div className="flex-1 h-6 bg-slate-800 rounded-full overflow-hidden">
            <motion.div
              initial={{ width: 0 }}
              animate={{ width: `${(prob / maxProb) * 100}%` }}
              transition={{ duration: 0.5, delay: idx * 0.1 }}
              className={`h-full rounded-full ${
                idx === 0 ? 'bg-gradient-to-r from-cyan-500 to-emerald-400' :
                idx === 1 ? 'bg-gradient-to-r from-blue-500 to-cyan-400' :
                'bg-gradient-to-r from-slate-600 to-slate-500'
              }`}
            />
          </div>
          <span className="w-12 text-right text-sm font-bold text-white">{prob.toFixed(1)}%</span>
        </div>
      ))}
    </div>
  );
};

// Factor Bar Component
const FactorBar = ({ label, value, icon: Icon }: { label: string; value: number; icon: any }) => {
  const getColor = () => {
    if (value >= 70) return 'from-emerald-500 to-cyan-400';
    if (value >= 50) return 'from-yellow-500 to-orange-400';
    return 'from-red-500 to-pink-400';
  };
  
  return (
    <div className="space-y-1">
      <div className="flex items-center justify-between text-xs">
        <span className="flex items-center gap-1 text-slate-400">
          <Icon className="w-3 h-3" />
          {label}
        </span>
        <span className="font-bold text-white">{value.toFixed(0)}%</span>
      </div>
      <div className="h-2 bg-slate-800 rounded-full overflow-hidden">
        <motion.div
          initial={{ width: 0 }}
          animate={{ width: `${value}%` }}
          transition={{ duration: 0.5 }}
          className={`h-full rounded-full bg-gradient-to-r ${getColor()}`}
        />
      </div>
    </div>
  );
};

// xG Visual Component
const XGVisual = ({ homeXG, awayXG, homeTeam, awayTeam }: { 
  homeXG: number; 
  awayXG: number; 
  homeTeam: string; 
  awayTeam: string;
}) => {
  const total = homeXG + awayXG;
  const homePercent = (homeXG / total) * 100;
  
  return (
    <div className="space-y-2">
      <div className="flex justify-between text-xs text-slate-400">
        <span>{homeTeam}</span>
        <span>{awayTeam}</span>
      </div>
      <div className="h-8 bg-slate-800 rounded-lg overflow-hidden flex">
        <motion.div
          initial={{ width: 0 }}
          animate={{ width: `${homePercent}%` }}
          transition={{ duration: 0.8 }}
          className="bg-gradient-to-r from-cyan-600 to-cyan-400 flex items-center justify-center"
        >
          <span className="text-xs font-bold text-white">{homeXG.toFixed(2)}</span>
        </motion.div>
        <motion.div
          initial={{ width: 0 }}
          animate={{ width: `${100 - homePercent}%` }}
          transition={{ duration: 0.8 }}
          className="bg-gradient-to-r from-pink-400 to-pink-600 flex items-center justify-center"
        >
          <span className="text-xs font-bold text-white">{awayXG.toFixed(2)}</span>
        </motion.div>
      </div>
      <div className="flex justify-center">
        <span className="text-sm font-bold text-white">
          Total xG: <span className="text-cyan-400">{total.toFixed(2)}</span>
        </span>
      </div>
    </div>
  );
};

// Detail Drawer Component
const DetailDrawer = ({ 
  analysis, 
  isOpen, 
  onClose 
}: { 
  analysis: MatchAnalysis | null; 
  isOpen: boolean; 
  onClose: () => void;
}) => {
  if (!analysis) return null;
  
  return (
    <AnimatePresence>
      {isOpen && (
        <>
          {/* Backdrop */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={onClose}
            className="fixed inset-0 bg-black/60 backdrop-blur-sm z-40"
          />
          
          {/* Drawer */}
          <motion.div
            initial={{ x: '100%' }}
            animate={{ x: 0 }}
            exit={{ x: '100%' }}
            transition={{ type: 'spring', damping: 25, stiffness: 200 }}
            className="fixed right-0 top-0 h-full w-full max-w-xl bg-slate-900/95 backdrop-blur-xl border-l border-cyan-500/20 z-50 overflow-y-auto"
          >
            {/* Header */}
            <div className="sticky top-0 bg-slate-900/90 backdrop-blur-xl border-b border-slate-700/50 p-4 z-10">
              <div className="flex items-center justify-between">
                <div>
                  <h2 className="text-xl font-bold text-white">
                    {analysis.home_team} vs {analysis.away_team}
                  </h2>
                  <p className="text-sm text-slate-400">{analysis.league || 'Football'}</p>
                </div>
                <button
                  onClick={onClose}
                  className="p-2 rounded-lg bg-slate-800 hover:bg-slate-700 transition-colors"
                >
                  <X className="w-5 h-5 text-slate-400" />
                </button>
              </div>
            </div>
            
            <div className="p-4 space-y-6">
              {/* xG Visual */}
              <div className="bg-slate-800/50 rounded-xl p-4 border border-slate-700/50">
                <h3 className="text-sm font-semibold text-slate-400 mb-3 flex items-center gap-2">
                  <Target className="w-4 h-4" />
                  Expected Goals (xG)
                </h3>
                <XGVisual 
                  homeXG={analysis.poisson.home_xg}
                  awayXG={analysis.poisson.away_xg}
                  homeTeam={analysis.home_team}
                  awayTeam={analysis.away_team}
                />
              </div>
              
              {/* 1X2 Probabilities */}
              <div className="bg-slate-800/50 rounded-xl p-4 border border-slate-700/50">
                <h3 className="text-sm font-semibold text-slate-400 mb-3 flex items-center gap-2">
                  <BarChart3 className="w-4 h-4" />
                  Match Outcome (Poisson)
                </h3>
                <div className="grid grid-cols-3 gap-3">
                  <div className="text-center p-3 bg-slate-900/50 rounded-lg">
                    <div className="text-2xl font-bold text-cyan-400">{analysis.poisson['1x2'].home}%</div>
                    <div className="text-xs text-slate-400">Home Win</div>
                  </div>
                  <div className="text-center p-3 bg-slate-900/50 rounded-lg">
                    <div className="text-2xl font-bold text-yellow-400">{analysis.poisson['1x2'].draw}%</div>
                    <div className="text-xs text-slate-400">Draw</div>
                  </div>
                  <div className="text-center p-3 bg-slate-900/50 rounded-lg">
                    <div className="text-2xl font-bold text-pink-400">{analysis.poisson['1x2'].away}%</div>
                    <div className="text-xs text-slate-400">Away Win</div>
                  </div>
                </div>
              </div>
              
              {/* BTTS Analysis */}
              <div className="bg-gradient-to-br from-emerald-900/30 to-cyan-900/30 rounded-xl p-4 border border-emerald-500/30">
                <div className="flex items-center justify-between mb-4">
                  <h3 className="text-sm font-semibold text-emerald-400 flex items-center gap-2">
                    <Goal className="w-4 h-4" />
                    BTTS Analysis
                  </h3>
                  <ScoreBadge score={analysis.btts.score} size="sm" />
                </div>
                
                <div className="space-y-3">
                  <div className="flex items-center justify-between">
                    <span className="text-slate-400">Recommendation</span>
                    <RecommendationBadge recommendation={analysis.btts.recommendation} />
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-slate-400">Poisson Probability</span>
                    <span className="font-bold text-white">{analysis.btts.probability}%</span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-slate-400">Confidence</span>
                    <span className="font-bold text-white">{analysis.btts.confidence}%</span>
                  </div>
                  {analysis.btts.kelly_pct > 0 && (
                    <div className="flex items-center justify-between">
                      <span className="text-slate-400">Kelly Stake</span>
                      <span className="font-bold text-emerald-400">{analysis.btts.kelly_pct.toFixed(2)}%</span>
                    </div>
                  )}
                </div>
                
                {/* BTTS Factors */}
                <div className="mt-4 pt-4 border-t border-slate-700/50 space-y-3">
                  <h4 className="text-xs font-semibold text-slate-500 uppercase">Factors</h4>
                  {analysis.btts.factors.poisson && (
                    <FactorBar label="Poisson Model" value={analysis.btts.factors.poisson} icon={BarChart3} />
                  )}
                  {analysis.btts.factors.stats_global && (
                    <FactorBar label="Global Stats" value={analysis.btts.factors.stats_global} icon={Activity} />
                  )}
                  {analysis.btts.factors.form_l5 && (
                    <FactorBar label="Last 5 Form" value={analysis.btts.factors.form_l5} icon={Flame} />
                  )}
                  {analysis.btts.factors.h2h && (
                    <FactorBar label="Head to Head" value={analysis.btts.factors.h2h} icon={Layers} />
                  )}
                </div>
                
                <p className="mt-4 text-xs text-slate-500 italic">{analysis.btts.reasoning}</p>
              </div>
              
              {/* Over 2.5 Analysis */}
              <div className="bg-gradient-to-br from-blue-900/30 to-purple-900/30 rounded-xl p-4 border border-blue-500/30">
                <div className="flex items-center justify-between mb-4">
                  <h3 className="text-sm font-semibold text-blue-400 flex items-center gap-2">
                    <TrendingUp className="w-4 h-4" />
                    Over 2.5 Analysis
                  </h3>
                  <ScoreBadge score={analysis.over25.score} size="sm" />
                </div>
                
                <div className="space-y-3">
                  <div className="flex items-center justify-between">
                    <span className="text-slate-400">Recommendation</span>
                    <RecommendationBadge recommendation={analysis.over25.recommendation} />
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-slate-400">Poisson Probability</span>
                    <span className="font-bold text-white">{analysis.over25.probability}%</span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-slate-400">Expected Goals</span>
                    <span className="font-bold text-cyan-400">{analysis.poisson.total_xg.toFixed(2)}</span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-slate-400">Confidence</span>
                    <span className="font-bold text-white">{analysis.over25.confidence}%</span>
                  </div>
                </div>
                
                {/* Over Factors */}
                <div className="mt-4 pt-4 border-t border-slate-700/50 space-y-3">
                  <h4 className="text-xs font-semibold text-slate-500 uppercase">Factors</h4>
                  {analysis.over25.factors.poisson && (
                    <FactorBar label="Poisson Model" value={analysis.over25.factors.poisson} icon={BarChart3} />
                  )}
                  {analysis.over25.factors.xg_factor && (
                    <FactorBar label="xG Factor" value={analysis.over25.factors.xg_factor} icon={Target} />
                  )}
                  {analysis.over25.factors.stats_global && (
                    <FactorBar label="Global Stats" value={analysis.over25.factors.stats_global} icon={Activity} />
                  )}
                  {analysis.over25.factors.form_l5 && (
                    <FactorBar label="Last 5 Form" value={analysis.over25.factors.form_l5} icon={Flame} />
                  )}
                </div>
                
                <p className="mt-4 text-xs text-slate-500 italic">{analysis.over25.reasoning}</p>
              </div>
              
              {/* Most Likely Scores */}
              <div className="bg-slate-800/50 rounded-xl p-4 border border-slate-700/50">
                <h3 className="text-sm font-semibold text-slate-400 mb-4 flex items-center gap-2">
                  <Star className="w-4 h-4" />
                  Most Likely Scores
                </h3>
                <PoissonChart scores={analysis.poisson.most_likely_scores} />
              </div>
              
              {/* Over/Under Probabilities */}
              <div className="bg-slate-800/50 rounded-xl p-4 border border-slate-700/50">
                <h3 className="text-sm font-semibold text-slate-400 mb-3 flex items-center gap-2">
                  <Percent className="w-4 h-4" />
                  Goals Probabilities
                </h3>
                <div className="grid grid-cols-3 gap-2">
                  <div className="text-center p-2 bg-slate-900/50 rounded-lg">
                    <div className="text-lg font-bold text-emerald-400">{analysis.poisson.over15_prob}%</div>
                    <div className="text-xs text-slate-500">Over 1.5</div>
                  </div>
                  <div className="text-center p-2 bg-slate-900/50 rounded-lg border border-cyan-500/30">
                    <div className="text-lg font-bold text-cyan-400">{analysis.poisson.over25_prob}%</div>
                    <div className="text-xs text-slate-500">Over 2.5</div>
                  </div>
                  <div className="text-center p-2 bg-slate-900/50 rounded-lg">
                    <div className="text-lg font-bold text-pink-400">{analysis.poisson.over35_prob}%</div>
                    <div className="text-xs text-slate-500">Over 3.5</div>
                  </div>
                </div>
              </div>
              
              {/* Data Quality */}
              <div className="flex items-center justify-center gap-4 text-xs text-slate-500">
                <span className={analysis.patron.data_quality.home_stats ? 'text-emerald-400' : ''}>
                  Home Stats {analysis.patron.data_quality.home_stats ? '✓' : '✗'}
                </span>
                <span className={analysis.patron.data_quality.away_stats ? 'text-emerald-400' : ''}>
                  Away Stats {analysis.patron.data_quality.away_stats ? '✓' : '✗'}
                </span>
                <span className={analysis.patron.data_quality.h2h ? 'text-emerald-400' : ''}>
                  H2H {analysis.patron.data_quality.h2h ? '✓' : '✗'}
                </span>
              </div>
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
};

// Match Row Component (with expansion)
const MatchRow = ({ 
  analysis, 
  onOpenDrawer,
  isExpanded,
  onToggleExpand
}: { 
  analysis: MatchAnalysis;
  onOpenDrawer: () => void;
  isExpanded: boolean;
  onToggleExpand: () => void;
}) => {
  const maxScore = Math.max(analysis.btts.score, analysis.over25.score);
  const interestLevel = analysis.patron.match_interest;
  
  const getInterestColor = () => {
    if (interestLevel.includes('DIAMOND')) return 'border-l-purple-500';
    if (interestLevel.includes('HIGH')) return 'border-l-cyan-500';
    if (interestLevel.includes('MEDIUM')) return 'border-l-yellow-500';
    return 'border-l-slate-600';
  };
  
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className={`
        bg-slate-800/40 backdrop-blur-sm rounded-xl border border-slate-700/50
        hover:border-cyan-500/30 transition-all duration-300
        border-l-4 ${getInterestColor()}
      `}
    >
      {/* Main Row */}
      <div 
        className="p-4 cursor-pointer"
        onClick={onToggleExpand}
      >
        <div className="flex items-center justify-between">
          {/* Match Info */}
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2">
              <h3 className="font-semibold text-white truncate">
                {analysis.home_team} vs {analysis.away_team}
              </h3>
              {interestLevel.includes('DIAMOND') && (
                <Diamond className="w-4 h-4 text-purple-400 flex-shrink-0" />
              )}
            </div>
            <p className="text-xs text-slate-500 mt-1">
              {analysis.league || 'Football'} • xG: {analysis.poisson.total_xg.toFixed(2)}
            </p>
          </div>
          
          {/* Scores */}
          <div className="flex items-center gap-4">
            {/* BTTS */}
            <div className="text-center">
              <div className="text-xs text-slate-500 mb-1">BTTS</div>
              <ScoreBadge score={analysis.btts.score} size="sm" />
            </div>
            
            {/* Over 2.5 */}
            <div className="text-center">
              <div className="text-xs text-slate-500 mb-1">Over 2.5</div>
              <ScoreBadge score={analysis.over25.score} size="sm" />
            </div>
            
            {/* Actions */}
            <div className="flex items-center gap-2">
              <button
                onClick={(e) => { e.stopPropagation(); onOpenDrawer(); }}
                className="p-2 rounded-lg bg-cyan-500/20 hover:bg-cyan-500/30 text-cyan-400 transition-colors"
              >
                <Eye className="w-4 h-4" />
              </button>
              <button className="p-2 rounded-lg bg-slate-700/50 hover:bg-slate-700 text-slate-400 transition-colors">
                {isExpanded ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
              </button>
            </div>
          </div>
        </div>
      </div>
      
      {/* Expanded Content */}
      <AnimatePresence>
        {isExpanded && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.3 }}
            className="overflow-hidden"
          >
            <div className="px-4 pb-4 pt-0 border-t border-slate-700/50">
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mt-4">
                {/* Quick Stats */}
                <div className="space-y-2">
                  <h4 className="text-xs font-semibold text-slate-500 uppercase">Quick Stats</h4>
                  <div className="grid grid-cols-2 gap-2 text-sm">
                    <div className="flex justify-between">
                      <span className="text-slate-400">Home xG</span>
                      <span className="text-cyan-400 font-bold">{analysis.poisson.home_xg.toFixed(2)}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-slate-400">Away xG</span>
                      <span className="text-pink-400 font-bold">{analysis.poisson.away_xg.toFixed(2)}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-slate-400">BTTS Prob</span>
                      <span className="text-white font-bold">{analysis.poisson.btts_prob}%</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-slate-400">Over 2.5</span>
                      <span className="text-white font-bold">{analysis.poisson.over25_prob}%</span>
                    </div>
                  </div>
                </div>
                
                {/* Recommendations */}
                <div className="space-y-2">
                  <h4 className="text-xs font-semibold text-slate-500 uppercase">Recommendations</h4>
                  <div className="space-y-2">
                    <div className="flex items-center justify-between">
                      <span className="text-slate-400 text-sm">BTTS</span>
                      <RecommendationBadge recommendation={analysis.btts.recommendation} />
                    </div>
                    <div className="flex items-center justify-between">
                      <span className="text-slate-400 text-sm">Over 2.5</span>
                      <RecommendationBadge recommendation={analysis.over25.recommendation} />
                    </div>
                  </div>
                </div>
                
                {/* Top Scores */}
                <div className="space-y-2">
                  <h4 className="text-xs font-semibold text-slate-500 uppercase">Most Likely</h4>
                  <div className="flex gap-2">
                    {analysis.poisson.most_likely_scores.slice(0, 3).map(([score, prob]) => (
                      <div key={score} className="flex-1 text-center p-2 bg-slate-900/50 rounded-lg">
                        <div className="font-bold text-white">{score}</div>
                        <div className="text-xs text-slate-500">{prob.toFixed(1)}%</div>
                      </div>
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

// Main Page Component
export default function FullGainPage() {
  const [analyses, setAnalyses] = useState<MatchAnalysis[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [selectedAnalysis, setSelectedAnalysis] = useState<MatchAnalysis | null>(null);
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [expandedRows, setExpandedRows] = useState<Set<string>>(new Set());
  
  // Filters
  const [filters, setFilters] = useState({
    minScore: 0,
    market: 'all',
    league: 'all',
    search: ''
  });
  const [showFilters, setShowFilters] = useState(false);
  
  // Stats
  const [stats, setStats] = useState({
    total: 0,
    diamond: 0,
    strong: 0,
    avgBtts: 0,
    avgOver: 0
  });
  
  // Fetch opportunities and analyze them
  const fetchAnalyses = useCallback(async () => {
    try {
      // Get opportunities first
      const oppRes = await fetch('http://91.98.131.218:8001/opportunities/opportunities/?limit=30');
      const opportunities: Opportunity[] = await oppRes.json();
      
      // Analyze each match
      const analysesPromises = opportunities.slice(0, 20).map(async (opp) => {
        try {
          const res = await fetch(`http://91.98.131.218:8001/patron-diamond/analyze/${opp.match_id}`);
          if (!res.ok) return null;
          const analysis = await res.json();
          return {
            ...analysis,
            league: opp.sport?.replace('soccer_', '').replace(/_/g, ' ').toUpperCase()
          };
        } catch {
          return null;
        }
      });
      
      const results = await Promise.all(analysesPromises);
      const validAnalyses = results.filter(Boolean) as MatchAnalysis[];
      
      // Sort by max score
      validAnalyses.sort((a, b) => {
        const maxA = Math.max(a.btts.score, a.over25.score);
        const maxB = Math.max(b.btts.score, b.over25.score);
        return maxB - maxA;
      });
      
      setAnalyses(validAnalyses);
      
      // Calculate stats
      const diamond = validAnalyses.filter(a => 
        a.btts.recommendation.includes('DIAMOND') || a.over25.recommendation.includes('DIAMOND')
      ).length;
      const strong = validAnalyses.filter(a => 
        a.btts.recommendation.includes('STRONG') || a.over25.recommendation.includes('STRONG')
      ).length;
      const avgBtts = validAnalyses.reduce((acc, a) => acc + a.btts.score, 0) / validAnalyses.length;
      const avgOver = validAnalyses.reduce((acc, a) => acc + a.over25.score, 0) / validAnalyses.length;
      
      setStats({
        total: validAnalyses.length,
        diamond,
        strong,
        avgBtts,
        avgOver
      });
      
    } catch (error) {
      console.error('Error fetching analyses:', error);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);
  
  useEffect(() => {
    fetchAnalyses();
  }, [fetchAnalyses]);
  
  const handleRefresh = () => {
    setRefreshing(true);
    fetchAnalyses();
  };
  
  const toggleExpand = (matchId: string) => {
    setExpandedRows(prev => {
      const next = new Set(prev);
      if (next.has(matchId)) {
        next.delete(matchId);
      } else {
        next.add(matchId);
      }
      return next;
    });
  };
  
  const openDrawer = (analysis: MatchAnalysis) => {
    setSelectedAnalysis(analysis);
    setDrawerOpen(true);
  };
  
  // Filter analyses
  const filteredAnalyses = analyses.filter(a => {
    const maxScore = Math.max(a.btts.score, a.over25.score);
    if (maxScore < filters.minScore) return false;
    
    if (filters.market === 'btts' && a.btts.score < 55) return false;
    if (filters.market === 'over25' && a.over25.score < 55) return false;
    
    if (filters.search) {
      const search = filters.search.toLowerCase();
      if (!a.home_team.toLowerCase().includes(search) && 
          !a.away_team.toLowerCase().includes(search)) return false;
    }
    
    return true;
  });
  
  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-950 via-slate-900 to-slate-950">
      {/* Animated Background */}
      <div className="fixed inset-0 overflow-hidden pointer-events-none">
        <div className="absolute top-1/4 -left-1/4 w-96 h-96 bg-cyan-500/10 rounded-full blur-3xl animate-pulse" />
        <div className="absolute bottom-1/4 -right-1/4 w-96 h-96 bg-purple-500/10 rounded-full blur-3xl animate-pulse" style={{ animationDelay: '1s' }} />
      </div>
      
      <div className="relative z-10 max-w-7xl mx-auto px-4 py-8">
        {/* Header */}
        <motion.div
          initial={{ opacity: 0, y: -20 }}
          animate={{ opacity: 1, y: 0 }}
          className="mb-8"
        >
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-4xl font-black text-transparent bg-clip-text bg-gradient-to-r from-cyan-400 via-purple-400 to-pink-400">
                FULL GAIN 2.0
              </h1>
              <p className="text-slate-400 mt-1">Multi-Market Analysis • BTTS & Over 2.5</p>
            </div>
            
            <button
              onClick={handleRefresh}
              disabled={refreshing}
              className="flex items-center gap-2 px-4 py-2 bg-cyan-500/20 hover:bg-cyan-500/30 
                         text-cyan-400 rounded-lg transition-colors disabled:opacity-50"
            >
              <RefreshCw className={`w-4 h-4 ${refreshing ? 'animate-spin' : ''}`} />
              Refresh
            </button>
          </div>
        </motion.div>
        
        {/* Stats Cards */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
          className="grid grid-cols-2 md:grid-cols-5 gap-4 mb-8"
        >
          <div className="bg-slate-800/50 backdrop-blur-sm rounded-xl p-4 border border-slate-700/50">
            <div className="flex items-center gap-2 text-slate-400 text-sm mb-2">
              <Activity className="w-4 h-4" />
              Matchs Analysés
            </div>
            <div className="text-3xl font-bold text-white">
              <AnimatedCounter value={stats.total} />
            </div>
          </div>
          
          <div className="bg-gradient-to-br from-purple-900/50 to-pink-900/50 backdrop-blur-sm rounded-xl p-4 border border-purple-500/30">
            <div className="flex items-center gap-2 text-purple-300 text-sm mb-2">
              <Diamond className="w-4 h-4" />
              Diamond Picks
            </div>
            <div className="text-3xl font-bold text-white">
              <AnimatedCounter value={stats.diamond} />
            </div>
          </div>
          
          <div className="bg-gradient-to-br from-emerald-900/50 to-cyan-900/50 backdrop-blur-sm rounded-xl p-4 border border-emerald-500/30">
            <div className="flex items-center gap-2 text-emerald-300 text-sm mb-2">
              <Zap className="w-4 h-4" />
              Strong Bets
            </div>
            <div className="text-3xl font-bold text-white">
              <AnimatedCounter value={stats.strong} />
            </div>
          </div>
          
          <div className="bg-slate-800/50 backdrop-blur-sm rounded-xl p-4 border border-slate-700/50">
            <div className="flex items-center gap-2 text-slate-400 text-sm mb-2">
              <Goal className="w-4 h-4" />
              Avg BTTS
            </div>
            <div className="text-3xl font-bold text-cyan-400">
              <AnimatedCounter value={stats.avgBtts} suffix="%" />
            </div>
          </div>
          
          <div className="bg-slate-800/50 backdrop-blur-sm rounded-xl p-4 border border-slate-700/50">
            <div className="flex items-center gap-2 text-slate-400 text-sm mb-2">
              <TrendingUp className="w-4 h-4" />
              Avg Over 2.5
            </div>
            <div className="text-3xl font-bold text-pink-400">
              <AnimatedCounter value={stats.avgOver} suffix="%" />
            </div>
          </div>
        </motion.div>
        
        {/* Filters */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2 }}
          className="mb-6"
        >
          <div className="flex flex-wrap items-center gap-4">
            {/* Search */}
            <div className="relative flex-1 min-w-[200px]">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
              <input
                type="text"
                placeholder="Search teams..."
                value={filters.search}
                onChange={(e) => setFilters(prev => ({ ...prev, search: e.target.value }))}
                className="w-full pl-10 pr-4 py-2 bg-slate-800/50 border border-slate-700/50 
                           rounded-lg text-white placeholder-slate-500 focus:outline-none 
                           focus:border-cyan-500/50 transition-colors"
              />
            </div>
            
            {/* Market Filter */}
            <select
              value={filters.market}
              onChange={(e) => setFilters(prev => ({ ...prev, market: e.target.value }))}
              className="px-4 py-2 bg-slate-800/50 border border-slate-700/50 rounded-lg 
                         text-white focus:outline-none focus:border-cyan-500/50"
            >
              <option value="all">All Markets</option>
              <option value="btts">BTTS Only</option>
              <option value="over25">Over 2.5 Only</option>
            </select>
            
            {/* Min Score Filter */}
            <select
              value={filters.minScore}
              onChange={(e) => setFilters(prev => ({ ...prev, minScore: Number(e.target.value) }))}
              className="px-4 py-2 bg-slate-800/50 border border-slate-700/50 rounded-lg 
                         text-white focus:outline-none focus:border-cyan-500/50"
            >
              <option value={0}>All Scores</option>
              <option value={50}>Score ≥ 50</option>
              <option value={60}>Score ≥ 60</option>
              <option value={70}>Score ≥ 70</option>
            </select>
            
            <button
              onClick={() => setShowFilters(!showFilters)}
              className="p-2 bg-slate-800/50 border border-slate-700/50 rounded-lg 
                         text-slate-400 hover:text-white transition-colors"
            >
              <SlidersHorizontal className="w-5 h-5" />
            </button>
          </div>
        </motion.div>
        
        {/* Matches List */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.3 }}
          className="space-y-4"
        >
          {loading ? (
            <div className="flex flex-col items-center justify-center py-20">
              <RefreshCw className="w-10 h-10 text-cyan-400 animate-spin mb-4" />
              <p className="text-slate-400">Analyzing matches...</p>
            </div>
          ) : filteredAnalyses.length === 0 ? (
            <div className="text-center py-20">
              <Target className="w-16 h-16 text-slate-600 mx-auto mb-4" />
              <p className="text-slate-400">No matches found with current filters</p>
            </div>
          ) : (
            filteredAnalyses.map((analysis, idx) => (
              <motion.div
                key={analysis.match_id}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: idx * 0.05 }}
              >
                <MatchRow
                  analysis={analysis}
                  onOpenDrawer={() => openDrawer(analysis)}
                  isExpanded={expandedRows.has(analysis.match_id)}
                  onToggleExpand={() => toggleExpand(analysis.match_id)}
                />
              </motion.div>
            ))
          )}
        </motion.div>
        
        {/* Footer Stats */}
        {!loading && filteredAnalyses.length > 0 && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.5 }}
            className="mt-8 text-center text-sm text-slate-500"
          >
            Showing {filteredAnalyses.length} of {analyses.length} matches • 
            Last updated: {new Date().toLocaleTimeString()}
          </motion.div>
        )}
      </div>
      
      {/* Detail Drawer */}
      <DetailDrawer
        analysis={selectedAnalysis}
        isOpen={drawerOpen}
        onClose={() => setDrawerOpen(false)}
      />
    </div>
  );
}
