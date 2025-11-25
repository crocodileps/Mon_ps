'use client'

import { useEffect, useState } from 'react'
import { TrendingUp, TrendingDown, Minus } from 'lucide-react'

interface Factor {
  name: string
  display_name: string
  score: number
  impact: number
  detail: string
  category: 'positive' | 'negative' | 'neutral'
}

interface FactorsData {
  factors: Factor[]
  summary: {
    positive_count: number
    negative_count: number
    neutral_count: number
    average_score: number
    average_impact: number
    overall_sentiment: string
  }
}

interface Props {
  matchId: string
}

export function FactorsAnalysis({ matchId }: Props) {
  const [data, setData] = useState<FactorsData | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetch(`http://91.98.131.218:8001/agents/patron/analyze-factors/${matchId}`)
      .then(res => res.json())
      .then(data => {
        setData(data)
        setLoading(false)
      })
      .catch(() => setLoading(false))
  }, [matchId])

  if (loading) {
    return <div className="text-gray-400 text-sm">Chargement analyse facteurs...</div>
  }

  if (!data) return null

  const getScoreColor = (score: number) => {
    if (score >= 7) return 'text-green-400'
    if (score >= 4) return 'text-yellow-400'
    return 'text-red-400'
  }

  const getImpactIcon = (category: string) => {
    switch (category) {
      case 'positive': return <TrendingUp size={16} className="text-green-400" />
      case 'negative': return <TrendingDown size={16} className="text-red-400" />
      default: return <Minus size={16} className="text-gray-400" />
    }
  }

  const getCategoryBg = (category: string) => {
    switch (category) {
      case 'positive': return 'bg-green-900/20 border-green-500/30'
      case 'negative': return 'bg-red-900/20 border-red-500/30'
      default: return 'bg-gray-900/20 border-gray-500/30'
    }
  }

  return (
    <div className="mt-6">
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <span className="text-lg">🔥</span>
          <h3 className="text-lg font-semibold text-purple-200">
            Analyse des Facteurs pour ce Match
          </h3>
        </div>
        <div className="text-sm text-gray-400">
          ✅ {data.summary.positive_count} facteurs positifs • 
          ❌ {data.summary.negative_count} facteurs négatifs • 
          Impact moyen: {data.summary.average_impact > 0 ? '+' : ''}{data.summary.average_impact}%
        </div>
      </div>

      <div className="grid grid-cols-2 gap-3">
        {data.factors.map((factor, index) => (
          <div 
            key={index}
            className={`rounded-lg p-4 border ${getCategoryBg(factor.category)}`}
          >
            <div className="flex items-center justify-between mb-2">
              <div className="flex items-center gap-2">
                {getImpactIcon(factor.category)}
                <span className="text-white font-medium text-sm">
                  {factor.display_name}
                </span>
              </div>
              <div className={`text-2xl font-bold ${getScoreColor(factor.score)}`}>
                {factor.score}/10
              </div>
            </div>
            
            <div className="text-xs text-gray-400 mb-2">
              {factor.detail}
            </div>
            
            {factor.impact !== 0 && (
              <div className="flex items-center gap-1 text-xs">
                <span className="text-gray-500">Impact:</span>
                <span className={factor.impact > 0 ? 'text-green-400' : 'text-red-400'}>
                  {factor.impact > 0 ? '+' : ''}{factor.impact}%
                </span>
              </div>
            )}
          </div>
        ))}
      </div>

      {/* Résumé global */}
      <div className="mt-3 bg-purple-900/20 rounded-lg p-3 border border-purple-500/30">
        <div className="flex items-center justify-between text-sm">
          <span className="text-purple-200">
            Score moyen des facteurs:
          </span>
          <span className={`font-bold text-lg ${getScoreColor(data.summary.average_score)}`}>
            {data.summary.average_score}/10
          </span>
        </div>
      </div>
    </div>
  )
}
