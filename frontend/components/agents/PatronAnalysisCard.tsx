'use client'
import { FactorsAnalysis } from './FactorsAnalysis'

import { useState, useEffect } from 'react'
import { Crown, TrendingUp, TrendingDown, Target } from 'lucide-react'

interface Variation {
  id: number
  name: string
  description: string
  factors: string[]
  matches_tested: number
  wins: number
  losses: number
  win_rate: number
  total_profit: number
  roi: number
  is_best: boolean
}

interface ScoreV2 {
  score: number
  grade: string
  verdict: string
  verdict_color: string
  verdict_message: string
  factors_positive: Array<{ label: string; points: number; detail: string }>
  factors_negative: Array<{ label: string; points: number; detail: string }>
  historical_reference: {
    zone: string
    win_rate: number
    sample: string
    quality: string
  }
  predicted_outcome: string
  agent_confidence: number
}

interface PatronAnalysisV2 {
  match_id: string
  score_v2: ScoreV2
  variation: Variation
  score_global: number
  consensus: string
}

interface Props {
  matchId: string
}

export function PatronAnalysisCard({ matchId }: Props) {
  const [variations, setVariations] = useState<Variation[]>([])
  const [selectedVariationId, setSelectedVariationId] = useState<number | null>(null)
  const [analysis, setAnalysis] = useState<PatronAnalysisV2 | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // Charger les variations au montage
  useEffect(() => {
    fetchVariations()
  }, [])

  const fetchVariations = async () => {
    try {
      const response = await fetch('http://91.98.131.218:8001/agents/patron/variations')
      if (!response.ok) throw new Error('Erreur chargement variations')
      const data = await response.json()
      setVariations(data.variations || [])
      if (data.best_variation_id) {
        setSelectedVariationId(data.best_variation_id)
      }
    } catch (err) {
      console.error('Erreur variations:', err)
    }
  }

  const fetchAnalysis = async () => {
    setLoading(true)
    setError(null)
    try {
      const url = selectedVariationId
        ? `http://91.98.131.218:8001/agents/patron/analyze/${matchId}?variation_id=${selectedVariationId}`
        : `http://91.98.131.218:8001/agents/patron/analyze/${matchId}`
      
      const response = await fetch(url)
      if (!response.ok) throw new Error('Erreur API')
      const data = await response.json()
      setAnalysis(data)
    } catch (err) {
      setError('Impossible de charger l\'analyse')
    } finally {
      setLoading(false)
    }
  }

  const getVerdictIcon = (verdict: string) => {
    if (verdict.includes('EXCELLENT') || verdict.includes('RECOMMANDE')) {
      return '🟢'
    } else if (verdict.includes('FAVORABLE') || verdict.includes('MODERE')) {
      return '🟡'
    } else if (verdict.includes('RISQUE') || verdict.includes('DEFAVORABLE')) {
      return '🟠'
    }
    return '🔴'
  }

  const getQualityColor = (quality: string) => {
    switch (quality) {
      case 'DIAMANT': return 'text-cyan-400'
      case 'OR': return 'text-yellow-400'
      case 'BRONZE': return 'text-orange-400'
      case 'CRITIQUE': return 'text-red-400'
      default: return 'text-gray-400'
    }
  }

  if (!analysis) {
    return (
      <div className="bg-gradient-to-r from-amber-900/20 to-amber-800/10 rounded-xl p-6 border border-amber-500/30">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-3">
            <Crown className="text-amber-400" size={28} />
            <h3 className="text-xl font-bold text-amber-400">Agent Patron Diamond+ V2.0</h3>
          </div>
          <button
            onClick={fetchAnalysis}
            disabled={loading}
            className="px-4 py-2 bg-amber-500 hover:bg-amber-600 text-black font-semibold rounded-lg transition-colors disabled:opacity-50"
          >
            {loading ? 'Analyse en cours...' : 'Lancer l\'Analyse Patron'}
          </button>
        </div>
        <p className="text-gray-400 text-sm">
          L'Agent Patron synthétise les analyses avec un score basé sur 60 matchs réels et 5 variations testées.
        </p>
        {error && <p className="text-red-400 mt-2 text-sm">{error}</p>}
      </div>
    )
  }

  const { score_v2, variation } = analysis
  const progressPercent = score_v2.score

  return (
    <div className="bg-gradient-to-r from-amber-900/20 to-amber-800/10 rounded-xl p-6 border border-amber-500/30 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Crown className="text-amber-400" size={28} />
          <h3 className="text-xl font-bold text-amber-400">Verdict Agent Patron</h3>
        </div>
        <button
          onClick={fetchAnalysis}
          disabled={loading}
          className="px-3 py-1 bg-amber-500/20 hover:bg-amber-500/30 text-amber-400 text-sm rounded-lg transition-colors"
        >
          Rafraîchir
        </button>
      </div>

      {/* Card Status */}
      <div className="bg-slate-900/60 rounded-lg p-6 border border-slate-700">
        {/* Dropdown Variation */}
        <div className="mb-6">
          <label className="text-gray-400 text-sm mb-2 block">Stratégie :</label>
          <select
            value={selectedVariationId || ''}
            onChange={(e) => {
              setSelectedVariationId(Number(e.target.value))
              setTimeout(fetchAnalysis, 100)
            }}
            className="w-full bg-slate-800 text-white px-4 py-2 rounded-lg border border-slate-600 focus:border-amber-500 focus:outline-none"
          >
            {variations.map((v) => (
              <option key={v.id} value={v.id}>
                {v.is_best && '⭐ '}{v.name} - {v.win_rate}% WR {v.is_best && ' (MEILLEURE)'}
              </option>
            ))}
          </select>
        </div>

        {/* Score + Note + Barre */}
        <div className="flex items-center gap-6 mb-6">
          <div className="text-center">
            <div className={`text-5xl font-bold ${score_v2.verdict_color === 'green-500' || score_v2.verdict_color === 'green-400' || score_v2.verdict_color === 'green-300' ? 'text-green-400' : score_v2.verdict_color === 'yellow-400' ? 'text-yellow-400' : score_v2.verdict_color.includes('orange') ? 'text-orange-400' : 'text-red-400'}`}>
              {score_v2.score}
            </div>
            <div className="text-gray-500 text-sm">/100</div>
          </div>
          <div className="flex-1">
            <div className="flex items-center justify-between mb-2">
              <span className="text-2xl font-bold text-white">Note {score_v2.grade}</span>
            </div>
            <div className="w-full bg-slate-700 rounded-full h-3">
              <div
                className={`h-3 rounded-full transition-all ${progressPercent >= 80 ? 'bg-green-400' : progressPercent >= 60 ? 'bg-yellow-400' : progressPercent >= 40 ? 'bg-orange-400' : 'bg-red-400'}`}
                style={{ width: `${progressPercent}%` }}
              ></div>
            </div>
          </div>
        </div>

        {/* Verdict */}
        <div className="bg-slate-800/50 rounded-lg p-4 mb-6">
          <div className="flex items-center gap-3">
            <span className="text-3xl">{getVerdictIcon(score_v2.verdict)}</span>
            <div>
              <div className="text-xl font-bold text-white">{score_v2.verdict}</div>
              <div className="text-gray-400 text-sm">{score_v2.verdict_message}</div>
            </div>
          </div>
        </div>

        {/* Variation Info */}
        {variation && (
          <div className="bg-slate-800/30 rounded-lg p-4 mb-6">
            <h4 className="text-white font-semibold mb-2 flex items-center gap-2">
              <Target size={18} className="text-amber-400" />
              Facteurs de la Variation
            </h4>
            <div className="flex flex-wrap gap-2 mb-3">
              {variation.factors.map((factor, i) => (
                <span key={i} className="px-3 py-1 bg-amber-500/20 text-amber-300 text-xs rounded-full border border-amber-500/30">
                  {factor.replace(/_/g, ' ')}
                </span>
              ))}
            </div>
            <div className="grid grid-cols-4 gap-2 text-xs">
              <div className="bg-slate-900/50 p-2 rounded text-center">
                <div className="text-gray-400">Matchs</div>
                <div className="text-white font-bold">{variation.matches_tested}</div>
              </div>
              <div className="bg-slate-900/50 p-2 rounded text-center">
                <div className="text-gray-400">WR</div>
                <div className="text-green-400 font-bold">{variation.win_rate}%</div>
              </div>
              <div className="bg-slate-900/50 p-2 rounded text-center">
                <div className="text-gray-400">Profit</div>
                <div className={`font-bold ${variation.total_profit >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                  {variation.total_profit > 0 ? '+' : ''}{variation.total_profit}€
                </div>
              </div>
              <div className="bg-slate-900/50 p-2 rounded text-center">
                <div className="text-gray-400">ROI</div>
                <div className={`font-bold ${variation.roi >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                  {variation.roi > 0 ? '+' : ''}{variation.roi}%
                </div>
              </div>
            </div>
          </div>
        )}
        {/* Analyse des Facteurs pour ce Match */}
        <FactorsAnalysis matchId={matchId} />


        {/* Facteurs Positifs */}
        {score_v2.factors_positive.length > 0 && (
          <div className="mb-4">
            <h4 className="text-green-400 font-semibold mb-2 flex items-center gap-2">
              <TrendingUp size={18} />
              Facteurs Positifs (Score)
            </h4>
            <div className="space-y-2">
              {score_v2.factors_positive.map((factor, i) => (
                <div key={i} className="bg-green-900/20 rounded-lg p-3 border border-green-500/30">
                  <div className="flex justify-between items-center mb-1">
                    <span className="text-white font-medium">{factor.label}</span>
                    <span className="text-green-400 font-bold">+{factor.points} pts</span>
                  </div>
                  <p className="text-gray-400 text-xs">{factor.detail}</p>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Facteurs Négatifs */}
        {score_v2.factors_negative.length > 0 && (
          <div className="mb-4">
            <h4 className="text-orange-400 font-semibold mb-2 flex items-center gap-2">
              <TrendingDown size={18} />
              Facteurs Négatifs (Score)
            </h4>
            <div className="space-y-2">
              {score_v2.factors_negative.map((factor, i) => (
                <div key={i} className="bg-orange-900/20 rounded-lg p-3 border border-orange-500/30">
                  <div className="flex justify-between items-center mb-1">
                    <span className="text-white font-medium">{factor.label}</span>
                    <span className="text-orange-400 font-bold">{factor.points} pts</span>
                  </div>
                  <p className="text-gray-400 text-xs">{factor.detail}</p>
                </div>
              ))}
            </div>
          </div>
        )}

        {score_v2.factors_negative.length === 0 && (
          <div className="mb-4 bg-slate-800/30 rounded-lg p-3 text-center">
            <p className="text-gray-400 text-sm">✅ Aucun facteur négatif majeur</p>
          </div>
        )}

        {/* Référence Historique */}
        <div className="bg-slate-800/30 rounded-lg p-4 border border-slate-700">
          <h4 className="text-white font-semibold mb-2">📊 Référence Historique</h4>
          <div className="grid grid-cols-2 gap-3 text-sm">
            <div>
              <span className="text-gray-400">Zone : </span>
              <span className="text-white font-medium">{score_v2.historical_reference.zone}</span>
            </div>
            <div>
              <span className="text-gray-400">Qualité : </span>
              <span className={`font-bold ${getQualityColor(score_v2.historical_reference.quality)}`}>
                {score_v2.historical_reference.quality}
              </span>
            </div>
            <div className="col-span-2">
              <span className="text-gray-400">Win Rate : </span>
              <span className="text-white font-bold">{score_v2.historical_reference.win_rate}%</span>
              <span className="text-gray-500 text-xs ml-2">({score_v2.historical_reference.sample})</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
