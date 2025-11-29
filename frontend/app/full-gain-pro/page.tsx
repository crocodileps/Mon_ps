"use client"

import React, { useState, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import {
  Trophy, Diamond, TrendingUp, AlertTriangle, ChevronDown, ChevronUp,
  Target, Zap, BarChart3, Users, Clock, Filter, RefreshCw, X,
  Activity, DollarSign, Percent, Star, Info, ArrowRight, Check,
  AlertCircle, Flame, Shield, Eye, ChevronRight
} from 'lucide-react'

// Types
interface SweetSpot {
  market_type: string
  prediction: string
  odds: number
  score: number
  recommendation: string
  probability: number
  kelly_pct: number
  recommendation: string
  factors: Record<string, any>
}

interface MatchPick {
  match_name: string
  home_team: string
  away_team: string
  league: string
  commence_time: string
  picks: SweetSpot[]
}

interface ProScore {
  final_score: number
  tier: string
  tier_emoji: string
  base_score: number
  k_risk: number
  k_trend: number
  breakdown: {
    s_data: number
    s_value: number
    s_pattern: number
    s_ml: number
  }
  risk_factors: any[]
  trend_info: any
  ml_signal: any
  divergences: any[]
  volatility_warnings: any[]
  scorer_analysis: any
  team_intelligence: {
    home: any
    away: any
  }
}

interface MatchData {
  match_name: string
  home_team: string
  away_team: string
  league: string
  commence_time: string
  sweet_spots: SweetSpot[]
  pro_score?: ProScore
  expanded?: boolean
}

interface Stats {
  total_picks: number
  elite_100: number
  elite_90: number
  diamond_plus: number
  avg_score: number
}
// Configuration API
const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://91.98.131.218:8001'

// Couleurs par tier
const tierColors: Record<string, { bg: string; border: string; text: string }> = {
  'ELITE': { bg: 'from-yellow-500/20 to-orange-500/20', border: 'border-yellow-500', text: 'text-yellow-400' },
  'DIAMOND': { bg: 'from-purple-500/20 to-pink-500/20', border: 'border-purple-500', text: 'text-purple-400' },
  'STRONG': { bg: 'from-blue-500/20 to-cyan-500/20', border: 'border-blue-500', text: 'text-blue-400' },
  'STANDARD': { bg: 'from-gray-500/20 to-slate-500/20', border: 'border-gray-500', text: 'text-gray-400' },
  'SKIP': { bg: 'from-red-500/20 to-rose-500/20', border: 'border-red-500', text: 'text-red-400' },
}

// Composant Score Bar
const ScoreBar = ({ score, label }: { score: number; label: string }) => (
  <div className="space-y-1">
    <div className="flex justify-between text-xs">
      <span className="text-gray-400">{label}</span>
      <span className="text-white font-medium">{score.toFixed(1)}</span>
    </div>
    <div className="h-2 bg-gray-700 rounded-full overflow-hidden">
      <motion.div
        initial={{ width: 0 }}
        animate={{ width: `${score}%` }}
        transition={{ duration: 0.8, ease: "easeOut" }}
        className={`h-full rounded-full ${
          score >= 80 ? 'bg-gradient-to-r from-yellow-500 to-orange-500' :
          score >= 60 ? 'bg-gradient-to-r from-blue-500 to-cyan-500' :
          score >= 40 ? 'bg-gradient-to-r from-gray-500 to-slate-400' :
          'bg-gradient-to-r from-red-500 to-rose-500'
        }`}
      />
    </div>
  </div>
)

// Composant Stat Card
const StatCard = ({ 
  icon: Icon, 
  label, 
  value, 
  subtext,
  color = 'cyan',
  onClick,
  active = false
}: { 
  icon: any
  label: string
  value: string | number
  subtext?: string
  color?: string
  onClick?: () => void
  active?: boolean
}) => (
  <motion.div
    whileHover={{ scale: 1.02, y: -2 }}
    whileTap={{ scale: 0.98 }}
    onClick={onClick}
    className={`
      relative p-4 rounded-xl cursor-pointer transition-all duration-300
      bg-gradient-to-br from-gray-800/80 to-gray-900/80
      border ${active ? `border-${color}-500` : 'border-gray-700/50'}
      hover:border-${color}-500/50
      backdrop-blur-sm
      ${onClick ? 'cursor-pointer' : ''}
    `}
  >
    <div className="flex items-center gap-3">
      <div className={`p-2 rounded-lg bg-${color}-500/20`}>
        <Icon className={`w-5 h-5 text-${color}-400`} />
      </div>
      <div>
        <p className="text-gray-400 text-xs">{label}</p>
        <p className={`text-xl font-bold text-${color}-400`}>{value}</p>
        {subtext && <p className="text-gray-500 text-xs">{subtext}</p>}
      </div>
    </div>
    {active && (
      <motion.div
        layoutId="activeIndicator"
        className={`absolute inset-0 border-2 border-${color}-500 rounded-xl`}
      />
    )}
  </motion.div>
)
// Composant Modal Détails
const MatchModal = ({ 
  match, 
  proScore, 
  onClose 
}: { 
  match: MatchData
  proScore: ProScore | null
  onClose: () => void 
}) => (
  <motion.div
    initial={{ opacity: 0 }}
    animate={{ opacity: 1 }}
    exit={{ opacity: 0 }}
    className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm"
    onClick={onClose}
  >
    <motion.div
      initial={{ scale: 0.9, y: 20 }}
      animate={{ scale: 1, y: 0 }}
      exit={{ scale: 0.9, y: 20 }}
      onClick={(e) => e.stopPropagation()}
      className="w-full max-w-4xl max-h-[90vh] overflow-y-auto bg-gradient-to-br from-gray-900 to-gray-950 rounded-2xl border border-gray-700 shadow-2xl"
    >
      {/* Header Modal */}
      <div className="sticky top-0 z-10 flex items-center justify-between p-6 bg-gray-900/95 backdrop-blur border-b border-gray-700">
        <div>
          <h2 className="text-2xl font-bold text-white">{match.home_team} vs {match.away_team}</h2>
          <p className="text-gray-400">{match.league} • {new Date(match.commence_time).toLocaleString('fr-FR')}</p>
        </div>
        <button
          onClick={onClose}
          className="p-2 rounded-lg bg-gray-800 hover:bg-gray-700 transition-colors"
        >
          <X className="w-6 h-6 text-gray-400" />
        </button>
      </div>

      <div className="p-6 space-y-6">
        {/* Pro Score Section */}
        {proScore && (
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {/* Score Principal */}
            <div className="md:col-span-1 p-6 rounded-xl bg-gradient-to-br from-gray-800 to-gray-900 border border-gray-700">
              <div className="text-center">
                <p className="text-gray-400 text-sm mb-2">PRO SCORE</p>
                <div className={`text-6xl font-black ${
                  proScore.final_score >= 90 ? 'text-yellow-400' :
                  proScore.final_score >= 80 ? 'text-purple-400' :
                  proScore.final_score >= 70 ? 'text-blue-400' :
                  'text-gray-400'
                }`}>
                  {proScore.final_score.toFixed(0)}
                </div>
                <p className="text-2xl mt-1">{proScore.tier_emoji} {proScore.tier}</p>
                <div className="mt-4 text-xs text-gray-500">
                  BASE: {proScore.base_score.toFixed(1)} × K_RISK: {proScore.k_risk.toFixed(2)} × K_TREND: {proScore.k_trend.toFixed(2)}
                </div>
              </div>
            </div>

            {/* Breakdown */}
            <div className="md:col-span-2 p-6 rounded-xl bg-gradient-to-br from-gray-800 to-gray-900 border border-gray-700">
              <h3 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
                <BarChart3 className="w-5 h-5 text-cyan-400" />
                Score Breakdown
              </h3>
              <div className="space-y-3">
                <ScoreBar score={proScore.breakdown.s_data} label="📊 S_DATA (Stats & xG)" />
                <ScoreBar score={proScore.breakdown.s_value} label="💰 S_VALUE (CLV & Edge)" />
                <ScoreBar score={proScore.breakdown.s_pattern} label="🏎️ S_PATTERN (FERRARI)" />
                <ScoreBar score={proScore.breakdown.s_ml} label="🤖 S_ML (Agents Consensus)" />
              </div>
            </div>
          </div>
        )}

        {/* Sweet Spots */}
        <div className="p-6 rounded-xl bg-gradient-to-br from-gray-800 to-gray-900 border border-gray-700">
          <h3 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
            <Target className="w-5 h-5 text-green-400" />
            Sweet Spots ({match.sweet_spots.length} picks)
          </h3>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
            {match.sweet_spots.slice(0, 9).map((spot, idx) => (
              <div
                key={idx}
                className={`p-3 rounded-lg border ${
                  spot.score >= 90 ? 'bg-yellow-500/10 border-yellow-500/50' :
                  spot.score >= 80 ? 'bg-purple-500/10 border-purple-500/50' :
                  spot.score >= 60 ? 'bg-blue-500/10 border-blue-500/50' :
                  'bg-gray-700/50 border-gray-600'
                }`}
              >
                <div className="flex justify-between items-start">
                  <span className="font-medium text-white">{(spot.market_type || "unknown").toUpperCase()}</span>
                  <span className={`text-sm font-bold ${
                    spot.score >= 90 ? 'text-yellow-400' :
                    spot.score >= 80 ? 'text-purple-400' :
                    'text-gray-400'
                  }`}>
                    {spot.score}
                  </span>
                </div>
                <div className="mt-1 text-sm text-gray-400">
                  @{spot.odds?.toFixed(2) || 'N/A'} • {spot.probability?.toFixed(1) || 0}%
                </div>
                <div className="mt-1 text-xs">{spot.recommendation}</div>
              </div>
            ))}
          </div>
        </div>

        {/* ML Signal & Risk */}
        {proScore && (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {/* ML Signal */}
            <div className="p-6 rounded-xl bg-gradient-to-br from-gray-800 to-gray-900 border border-gray-700">
              <h3 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
                <Activity className="w-5 h-5 text-purple-400" />
                Signal ML
              </h3>
              <div className="space-y-2">
                <div className="flex justify-between">
                  <span className="text-gray-400">Type</span>
                  <span className="text-white font-medium">{proScore.ml_signal?.type || 'N/A'}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-400">Status</span>
                  <span className={`font-medium ${
                    proScore.ml_signal?.status === 'STRONG' ? 'text-green-400' : 'text-yellow-400'
                  }`}>{proScore.ml_signal?.status || 'N/A'}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-400">Consensus</span>
                  <span className="text-white">{proScore.ml_signal?.consensus_strength?.toFixed(1) || 'N/A'}</span>
                </div>
                <p className="text-sm text-gray-500 mt-2">{proScore.ml_signal?.insight}</p>
              </div>
            </div>

            {/* Risk Factors */}
            <div className="p-6 rounded-xl bg-gradient-to-br from-gray-800 to-gray-900 border border-gray-700">
              <h3 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
                <Shield className="w-5 h-5 text-orange-400" />
                Facteurs de Risque
              </h3>
              {proScore.risk_factors?.length > 0 ? (
                <div className="space-y-2">
                  {proScore.risk_factors.map((risk, idx) => (
                    <div key={idx} className="flex items-center gap-2 text-sm">
                      <span>{risk.icon}</span>
                      <span className="text-gray-300">{risk.reason}</span>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-green-400 flex items-center gap-2">
                  <Check className="w-4 h-4" /> Aucun risque détecté
                </p>
              )}
            </div>
          </div>
        )}

        {/* Volatility Warnings */}
        {proScore?.volatility_warnings?.length > 0 && (
          <div className="p-6 rounded-xl bg-gradient-to-br from-red-900/30 to-orange-900/30 border border-red-500/50">
            <h3 className="text-lg font-semibold text-red-400 mb-4 flex items-center gap-2">
              <AlertTriangle className="w-5 h-5" />
              Alertes Volatilité
            </h3>
            <div className="space-y-3">
              {proScore.volatility_warnings.slice(0, 3).map((warning, idx) => (
                <div key={idx} className="p-3 rounded-lg bg-black/30">
                  <div className="flex items-center gap-2 font-medium text-orange-400">
                    {warning.icon} {warning.pattern_name}
                  </div>
                  <p className="text-sm text-gray-400 mt-1">{warning.warning_message}</p>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </motion.div>
  </motion.div>
)
// Composant Match Card Expandable
const MatchCard = ({ 
  match, 
  onOpenModal,
  onToggleExpand,
  isExpanded
}: { 
  match: MatchData
  onOpenModal: () => void
  onToggleExpand: () => void
  isExpanded: boolean
}) => {
  const topPicks = match.sweet_spots.filter(s => s.score >= 80).slice(0, 3)
  const bestScore = match.sweet_spots[0]?.score || 0
  
  const tier = bestScore >= 100 ? 'ELITE' : bestScore >= 90 ? 'ELITE' : bestScore >= 80 ? 'DIAMOND' : 'STANDARD'
  const colors = tierColors[tier] || tierColors['STANDARD']

  return (
    <motion.div
      layout
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className={`
        rounded-xl border overflow-hidden
        bg-gradient-to-br ${colors.bg}
        ${colors.border} border-opacity-50
        hover:border-opacity-100 transition-all duration-300
      `}
    >
      {/* Header - Always Visible */}
      <div 
        className="p-4 cursor-pointer"
        onClick={onToggleExpand}
      >
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            {/* Tier Badge */}
            <div className={`
              px-3 py-1 rounded-full text-xs font-bold
              ${tier === 'ELITE' ? 'bg-yellow-500/20 text-yellow-400' : ''}
              ${tier === 'DIAMOND' ? 'bg-purple-500/20 text-purple-400' : ''}
              ${tier === 'STANDARD' ? 'bg-gray-500/20 text-gray-400' : ''}
            `}>
              {tier === 'ELITE' && '🏆'} {tier === 'DIAMOND' && '💎'} {tier}
            </div>
            
            {/* Match Info */}
            <div>
              <h3 className="text-lg font-bold text-white">
                {match.home_team} vs {match.away_team}
              </h3>
              <p className="text-sm text-gray-400 flex items-center gap-2">
                <Clock className="w-3 h-3" />
                {new Date(match.commence_time).toLocaleString('fr-FR', { 
                  hour: '2-digit', 
                  minute: '2-digit',
                  day: '2-digit',
                  month: '2-digit'
                })}
                {match.league && <span>• {match.league}</span>}
              </p>
            </div>
          </div>

          <div className="flex items-center gap-4">
            {/* Score Badge */}
            <div className={`text-3xl font-black ${colors.text}`}>
              {bestScore}
            </div>
            
            {/* Picks Count */}
            <div className="text-center">
              <div className="text-lg font-bold text-white">{match.sweet_spots.length}</div>
              <div className="text-xs text-gray-400">picks</div>
            </div>

            {/* Expand Icon */}
            <motion.div
              animate={{ rotate: isExpanded ? 180 : 0 }}
              transition={{ duration: 0.2 }}
            >
              <ChevronDown className="w-6 h-6 text-gray-400" />
            </motion.div>
          </div>
        </div>

        {/* Quick Picks Preview */}
        {!isExpanded && topPicks.length > 0 && (
          <div className="flex gap-2 mt-3 flex-wrap">
            {topPicks.map((pick, idx) => (
              <span
                key={idx}
                className={`
                  px-2 py-1 rounded text-xs font-medium
                  ${pick.score >= 90 ? 'bg-yellow-500/20 text-yellow-400' : 'bg-purple-500/20 text-purple-400'}
                `}
              >
                {(pick.market_type || "unknown").toUpperCase()} @{pick.odds?.toFixed(2) || 'N/A'} ({pick.score})
              </span>
            ))}
          </div>
        )}
      </div>

      {/* Expanded Content */}
      <AnimatePresence>
        {isExpanded && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.3 }}
            className="border-t border-gray-700/50"
          >
            <div className="p-4 space-y-4">
              {/* All Picks Grid */}
              <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-2">
                {match.sweet_spots.slice(0, 8).map((spot, idx) => (
                  <div
                    key={idx}
                    className={`
                      p-3 rounded-lg border transition-all
                      ${spot.score >= 90 ? 'bg-yellow-500/10 border-yellow-500/30 hover:border-yellow-500' : ''}
                      ${spot.score >= 80 && spot.score < 90 ? 'bg-purple-500/10 border-purple-500/30 hover:border-purple-500' : ''}
                      ${spot.score < 80 ? 'bg-gray-800/50 border-gray-700/30 hover:border-gray-600' : ''}
                    `}
                  >
                    <div className="flex justify-between items-center">
                      <span className="font-medium text-white text-sm">{(spot.market_type || "unknown").toUpperCase()}</span>
                      <span className={`text-xs font-bold px-1.5 py-0.5 rounded ${
                        spot.score >= 90 ? 'bg-yellow-500/30 text-yellow-400' :
                        spot.score >= 80 ? 'bg-purple-500/30 text-purple-400' :
                        'bg-gray-600/30 text-gray-400'
                      }`}>
                        {spot.score}
                      </span>
                    </div>
                    <div className="text-xs text-gray-400 mt-1">
                      @{spot.odds?.toFixed(2) || 'N/A'}
                    </div>
                    <div className="text-xs mt-1">{spot.recommendation}</div>
                  </div>
                ))}
              </div>

              {/* Action Buttons */}
              <div className="flex gap-3 pt-2">
                <button
                  onClick={(e) => { e.stopPropagation(); onOpenModal(); }}
                  className="flex-1 py-2 px-4 rounded-lg bg-gradient-to-r from-cyan-500 to-blue-500 text-white font-medium hover:from-cyan-600 hover:to-blue-600 transition-all flex items-center justify-center gap-2"
                >
                  <Eye className="w-4 h-4" />
                  Voir Analyse Complète
                </button>
                <button
                  onClick={(e) => { e.stopPropagation(); onOpenModal(); }}
                  className="py-2 px-4 rounded-lg bg-gradient-to-r from-orange-500 to-red-500 text-white font-medium hover:from-orange-600 hover:to-red-600 transition-all flex items-center justify-center gap-2"
                >
                  <Flame className="w-4 h-4" />
                  FERRARI
                </button>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  )
}
// Composant Principal
export default function FullGainProPage() {
  const [matches, setMatches] = useState<MatchData[]>([])
  const [stats, setStats] = useState<Stats | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [selectedMatch, setSelectedMatch] = useState<MatchData | null>(null)
  const [selectedProScore, setSelectedProScore] = useState<ProScore | null>(null)
  const [expandedMatches, setExpandedMatches] = useState<Set<string>>(new Set())
  const [filter, setFilter] = useState<'all' | 'elite' | 'diamond'>('all')
  const [showModal, setShowModal] = useState(false)

  // Fetch data
  const fetchData = async () => {
    setLoading(true)
    setError(null)
    
    try {
      // Fetch sweet spots elite
      const eliteRes = await fetch(`${API_BASE}/api/tracking-clv/sweet-spot/upcoming`)
      const eliteData = await eliteRes.json()
      
      // Fetch today stats
      const statsRes = await fetch(`${API_BASE}/api/tracking-clv/sweet-spot/picks`)
      const statsData = await statsRes.json()
      
      // Calculer les stats depuis les picks
      const allPicks = statsData.picks || []
      const calculatedStats = {
        total_picks: allPicks.length,
        elite_100: allPicks.filter((p: any) => p.score === 100).length,
        elite_90: allPicks.filter((p: any) => p.score >= 90).length,
        diamond_plus: allPicks.filter((p: any) => p.score >= 80).length,
        avg_score: allPicks.length > 0 ? allPicks.reduce((acc: number, p: any) => acc + (p.score || 0), 0) / allPicks.length : 0
      }
      setStats(calculatedStats)
      
      // Transform elite matches
      const matchesMap = new Map<string, MatchData>()
      
      for (const match of eliteData.matches || []) {
        const key = match.match_name
        if (!matchesMap.has(key)) {
          matchesMap.set(key, {
            match_name: match.match_name,
            home_team: match.home_team,
            away_team: match.away_team,
            league: match.league || '',
            commence_time: match.commence_time,
            sweet_spots: match.picks.map((p: any) => ({
              market_type: p.market,
              prediction: p.prediction,
              odds: p.odds,
              score: p.score,
              recommendation: p.recommendation,
              probability: 0,
              kelly_pct: 0,
              recommendation: '',
              factors: {}
            }))
          })
        }
      }
      
      // Also fetch all diamond+ picks to enrich
      const diamondRes = await fetch(`${API_BASE}/api/tracking-clv/sweet-spot/picks?min_score=80`)
      const diamondData = await diamondRes.json()
      
      for (const pick of diamondData.picks || []) {
        const key = pick.match_name
        if (!matchesMap.has(key)) {
          matchesMap.set(key, {
            match_name: pick.match_name,
            home_team: pick.home_team,
            away_team: pick.away_team,
            league: pick.league || '',
            commence_time: pick.commence_time,
            sweet_spots: []
          })
        }
        
        const match = matchesMap.get(key)!
        const exists = match.sweet_spots.some(s => 
          s.market_type === pick.market_type && s.score === pick.score
        )
        
        if (!exists) {
          match.sweet_spots.push({
            market_type: pick.market_type,
            prediction: pick.prediction,
            odds: pick.odds,
            score: pick.score,
            recommendation: pick.recommendation,
            probability: pick.probability,
            kelly_pct: pick.kelly_pct,
            recommendation: pick.recommendation,
            factors: pick.factors || {}
          })
        }
      }
      
      // Sort matches by best score
      const sortedMatches = Array.from(matchesMap.values())
        .map(m => ({
          ...m,
          sweet_spots: m.sweet_spots.sort((a, b) => b.score - a.score)
        }))
        .sort((a, b) => {
          const aScore = a.sweet_spots[0]?.score || 0
          const bScore = b.sweet_spots[0]?.score || 0
          return bScore - aScore
        })
      
      setMatches(sortedMatches)
      
    } catch (err) {
      console.error('Fetch error:', err)
      setError('Erreur de chargement des données')
    } finally {
      setLoading(false)
    }
  }

  // Fetch Pro Score for modal
  const fetchProScore = async (match: MatchData) => {
    try {
      const res = await fetch(
        `${API_BASE}/api/tracking-clv/sweet-spot/picks/${encodeURIComponent(match.home_team)}/${encodeURIComponent(match.away_team)}`
      )
      const data = await res.json()
      
      // Enrich match with all sweet spots
      if (data.picks) {
        match.sweet_spots = data.picks
      }
      
      // Try to get pro score
      try {
        const scoreRes = await fetch(
          `${API_BASE}/api/pro/match-score/${encodeURIComponent(match.home_team)}/${encodeURIComponent(match.away_team)}`
        )
        const scoreData = await scoreRes.json()
        setSelectedProScore(scoreData)
      } catch {
        setSelectedProScore(null)
      }
      
      setSelectedMatch(match)
      setShowModal(true)
    } catch (err) {
      console.error('Error fetching pro score:', err)
    }
  }

  // Toggle expand
  const toggleExpand = (matchName: string) => {
    setExpandedMatches(prev => {
      const next = new Set(prev)
      if (next.has(matchName)) {
        next.delete(matchName)
      } else {
        next.add(matchName)
      }
      return next
    })
  }

  // Filter matches
  const filteredMatches = matches.filter(m => {
    const bestScore = m.sweet_spots[0]?.score || 0
    if (filter === 'elite') return bestScore >= 90
    if (filter === 'diamond') return bestScore >= 80
    return true
  })

  // Initial fetch
  useEffect(() => {
    fetchData()
    // Refresh every 5 minutes
    const interval = setInterval(fetchData, 5 * 60 * 1000)
    return () => clearInterval(interval)
  }, [])
return (
    <div className="min-h-screen bg-gradient-to-br from-gray-950 via-gray-900 to-gray-950 text-white">
      {/* Header */}
      <div className="sticky top-0 z-40 bg-gray-950/90 backdrop-blur-lg border-b border-gray-800">
        <div className="max-w-7xl mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="p-2 rounded-xl bg-gradient-to-br from-orange-500 to-red-500">
                <Flame className="w-8 h-8 text-white" />
              </div>
              <div>
                <h1 className="text-2xl font-black bg-gradient-to-r from-orange-400 via-red-400 to-pink-400 bg-clip-text text-transparent">
                  FULL GAIN 3.0 PRO
                </h1>
                <p className="text-xs text-gray-400">Pro Score V3.1 • Sweet Spots • FERRARI Intelligence</p>
              </div>
            </div>
            
            <button
              onClick={fetchData}
              disabled={loading}
              className="flex items-center gap-2 px-4 py-2 rounded-lg bg-gray-800 hover:bg-gray-700 transition-colors disabled:opacity-50"
            >
              <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
              Actualiser
            </button>
          </div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-4 py-6">
        {/* Stats Cards */}
        {stats && (
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3 mb-6">
            <StatCard
              icon={Trophy}
              label="ELITE 100"
              value={stats.elite_100}
              subtext="Score parfait"
              color="yellow"
              onClick={() => setFilter('elite')}
              active={filter === 'elite'}
            />
            <StatCard
              icon={Diamond}
              label="ELITE 90+"
              value={stats.elite_90}
              subtext="Excellents"
              color="purple"
              onClick={() => setFilter('elite')}
              active={filter === 'elite'}
            />
            <StatCard
              icon={Star}
              label="DIAMOND+"
              value={stats.diamond_plus}
              subtext="Score ≥ 80"
              color="pink"
              onClick={() => setFilter('diamond')}
              active={filter === 'diamond'}
            />
            <StatCard
              icon={Target}
              label="Total Picks"
              value={stats.total_picks}
              subtext="Aujourd'hui"
              color="cyan"
              onClick={() => setFilter('all')}
              active={filter === 'all'}
            />
            <StatCard
              icon={BarChart3}
              label="Score Moyen"
              value={stats.avg_score?.toFixed(1) || '0'}
              subtext="/100"
              color="blue"
            />
            <StatCard
              icon={TrendingUp}
              label="Matchs"
              value={matches.length}
              subtext="Analysés"
              color="green"
            />
          </div>
        )}

        {/* Filter Buttons */}
        <div className="flex gap-2 mb-6 flex-wrap">
          <button
            onClick={() => setFilter('all')}
            className={`px-4 py-2 rounded-lg font-medium transition-all ${
              filter === 'all' 
                ? 'bg-cyan-500 text-white' 
                : 'bg-gray-800 text-gray-400 hover:bg-gray-700'
            }`}
          >
            🔥 Tous ({matches.length})
          </button>
          <button
            onClick={() => setFilter('elite')}
            className={`px-4 py-2 rounded-lg font-medium transition-all ${
              filter === 'elite' 
                ? 'bg-yellow-500 text-black' 
                : 'bg-gray-800 text-gray-400 hover:bg-gray-700'
            }`}
          >
            🏆 Elite ({matches.filter(m => (m.sweet_spots[0]?.score || 0) >= 90).length})
          </button>
          <button
            onClick={() => setFilter('diamond')}
            className={`px-4 py-2 rounded-lg font-medium transition-all ${
              filter === 'diamond' 
                ? 'bg-purple-500 text-white' 
                : 'bg-gray-800 text-gray-400 hover:bg-gray-700'
            }`}
          >
            💎 Diamond+ ({matches.filter(m => (m.sweet_spots[0]?.score || 0) >= 80).length})
          </button>
        </div>

        {/* Loading State */}
        {loading && (
          <div className="flex items-center justify-center py-20">
            <div className="text-center">
              <RefreshCw className="w-12 h-12 text-cyan-400 animate-spin mx-auto mb-4" />
              <p className="text-gray-400">Chargement des données...</p>
            </div>
          </div>
        )}

        {/* Error State */}
        {error && (
          <div className="p-6 rounded-xl bg-red-500/10 border border-red-500/50 text-center">
            <AlertCircle className="w-12 h-12 text-red-400 mx-auto mb-4" />
            <p className="text-red-400">{error}</p>
            <button
              onClick={fetchData}
              className="mt-4 px-4 py-2 rounded-lg bg-red-500 text-white hover:bg-red-600"
            >
              Réessayer
            </button>
          </div>
        )}

        {/* Matches List */}
        {!loading && !error && (
          <div className="space-y-4">
            {filteredMatches.length === 0 ? (
              <div className="text-center py-20 text-gray-400">
                <Target className="w-16 h-16 mx-auto mb-4 opacity-50" />
                <p>Aucun match trouvé pour ce filtre</p>
              </div>
            ) : (
              filteredMatches.map((match, idx) => (
                <MatchCard
                  key={match.match_name + idx}
                  match={match}
                  isExpanded={expandedMatches.has(match.match_name)}
                  onToggleExpand={() => toggleExpand(match.match_name)}
                  onOpenModal={() => fetchProScore(match)}
                />
              ))
            )}
          </div>
        )}
      </div>

      {/* Modal */}
      <AnimatePresence>
        {showModal && selectedMatch && (
          <MatchModal
            match={selectedMatch}
            proScore={selectedProScore}
            onClose={() => {
              setShowModal(false)
              setSelectedMatch(null)
              setSelectedProScore(null)
            }}
          />
        )}
      </AnimatePresence>
    </div>
  )
}

