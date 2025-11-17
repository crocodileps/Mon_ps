'use client'

import { useState } from 'react'
import { Crown, AlertTriangle, CheckCircle, XCircle, TrendingUp, Shield } from 'lucide-react'

interface PatronAnalysis {
  match_id: string
  score_global: number
  consensus: string
  consensus_description: string
  confiance_agregee: number
  recommendation: string
  action: string
  mise_recommandee_pct: number
  synthese_agents: {
    [key: string]: {
      signal: string
      confiance: number
      poids: number
      contribution: number
    }
  }
  analyse_patron: {
    point_fort: string
    point_vigilance: string
    arbitrage: string
    decision_finale: string
  }
  recommandations: string[]
}

interface Props {
  matchId: string
}

export function PatronAnalysisCard({ matchId }: Props) {
  const [analysis, setAnalysis] = useState<PatronAnalysis | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const fetchAnalysis = async () => {
    setLoading(true)
    setError(null)
    try {
      const response = await fetch(`http://91.98.131.218:8001/agents/patron/analyze/${matchId}`)
      if (!response.ok) throw new Error('Erreur API')
      const data = await response.json()
      setAnalysis(data)
    } catch (err) {
      setError('Impossible de charger l\'analyse')
    } finally {
      setLoading(false)
    }
  }

  const getScoreColor = (score: number) => {
    if (score >= 70) return 'text-green-400'
    if (score >= 50) return 'text-yellow-400'
    if (score >= 30) return 'text-orange-400'
    return 'text-red-400'
  }

  const getRecommendationIcon = (rec: string) => {
    if (rec.includes('FORT')) return <CheckCircle className="text-green-400" size={24} />
    if (rec.includes('BON')) return <TrendingUp className="text-blue-400" size={24} />
    if (rec.includes('MOYEN')) return <Shield className="text-yellow-400" size={24} />
    if (rec.includes('FAIBLE')) return <AlertTriangle className="text-orange-400" size={24} />
    return <XCircle className="text-red-400" size={24} />
  }

  if (!analysis) {
    return (
      <div className="bg-gradient-to-r from-amber-900/20 to-amber-800/10 rounded-xl p-6 border border-amber-500/30">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-3">
            <Crown className="text-amber-400" size={28} />
            <h3 className="text-xl font-bold text-amber-400">Agent Patron</h3>
          </div>
          <button
            onClick={fetchAnalysis}
            disabled={loading}
            className="px-4 py-2 bg-amber-500 hover:bg-amber-600 text-black font-semibold rounded-lg transition-colors disabled:opacity-50"
          >
            {loading ? 'Analyse en cours...' : 'Lancer l\'Analyse Patron'}
          </button>
        </div>
        <p className="text-gray-400">
          L'Agent Patron synthétise les analyses des 4 agents pour une recommandation finale optimale.
        </p>
        {error && <p className="text-red-400 mt-2">{error}</p>}
      </div>
    )
  }

  return (
    <div className="bg-gradient-to-r from-amber-900/20 to-amber-800/10 rounded-xl p-6 border border-amber-500/30 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Crown className="text-amber-400" size={28} />
          <h3 className="text-xl font-bold text-amber-400">Analyse Agent Patron</h3>
        </div>
        <button
          onClick={fetchAnalysis}
          disabled={loading}
          className="px-3 py-1 bg-amber-500/20 hover:bg-amber-500/30 text-amber-400 text-sm rounded-lg transition-colors"
        >
          Rafraîchir
        </button>
      </div>

      {/* Score Global */}
      <div className="bg-black/40 rounded-lg p-4">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-gray-400 text-sm">Score Global</p>
            <p className={`text-4xl font-bold ${getScoreColor(analysis.score_global)}`}>
              {analysis.score_global.toFixed(1)}/100
            </p>
          </div>
          <div className="text-right">
            <p className="text-gray-400 text-sm">Consensus</p>
            <p className="text-white font-semibold">{analysis.consensus}</p>
          </div>
        </div>
        <p className="text-gray-500 text-sm mt-2">{analysis.consensus_description}</p>
      </div>

      {/* Recommandation Finale */}
      <div className="bg-slate-800/50 rounded-lg p-4">
        <div className="flex items-center gap-3 mb-2">
          {getRecommendationIcon(analysis.recommendation)}
          <div>
            <p className="text-white font-bold text-lg">{analysis.recommendation}</p>
            <p className="text-gray-300">{analysis.action}</p>
          </div>
        </div>
        {analysis.mise_recommandee_pct > 0 && (
          <p className="text-green-400 font-semibold mt-2">
            💰 Mise recommandée : {analysis.mise_recommandee_pct}% du bankroll
          </p>
        )}
      </div>

      {/* Synthèse des Agents */}
      <div>
        <h4 className="text-white font-semibold mb-3">Contribution des Agents</h4>
        <div className="grid grid-cols-2 gap-3">
          {Object.entries(analysis.synthese_agents).map(([agentId, data]) => (
            <div key={agentId} className="bg-slate-900/60 rounded-lg p-3">
              <p className="text-gray-400 text-xs capitalize">{agentId.replace('_', ' ')}</p>
              <div className="flex justify-between items-center mt-1">
                <span className="text-white font-medium">{data.confiance.toFixed(0)}%</span>
                <span className={`text-xs px-2 py-1 rounded ${
                  data.signal === 'FORT' ? 'bg-green-500/20 text-green-400' :
                  data.signal === 'MOYEN' ? 'bg-yellow-500/20 text-yellow-400' :
                  data.signal === 'FAIBLE' ? 'bg-orange-500/20 text-orange-400' :
                  'bg-red-500/20 text-red-400'
                }`}>
                  {data.signal}
                </span>
              </div>
              <div className="w-full bg-slate-700 rounded-full h-2 mt-2">
                <div 
                  className="bg-amber-500 h-2 rounded-full" 
                  style={{ width: `${data.confiance}%` }}
                ></div>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Analyse Détaillée */}
      <div className="space-y-3">
        <div className="bg-green-900/20 rounded-lg p-3 border border-green-500/30">
          <p className="text-green-400 font-medium text-sm">✅ Point Fort</p>
          <p className="text-gray-300 text-sm">{analysis.analyse_patron.point_fort}</p>
        </div>
        <div className="bg-orange-900/20 rounded-lg p-3 border border-orange-500/30">
          <p className="text-orange-400 font-medium text-sm">⚠️ Point de Vigilance</p>
          <p className="text-gray-300 text-sm">{analysis.analyse_patron.point_vigilance}</p>
        </div>
        <div className="bg-blue-900/20 rounded-lg p-3 border border-blue-500/30">
          <p className="text-blue-400 font-medium text-sm">⚖️ Arbitrage</p>
          <p className="text-gray-300 text-sm">{analysis.analyse_patron.arbitrage}</p>
        </div>
      </div>

      {/* Recommandations */}
      <div>
        <h4 className="text-white font-semibold mb-2">Recommandations</h4>
        <ul className="space-y-2">
          {analysis.recommandations.map((rec, i) => (
            <li key={i} className="flex items-start gap-2">
              <span className="text-amber-400 mt-1">•</span>
              <span className="text-gray-300 text-sm">{rec}</span>
            </li>
          ))}
        </ul>
      </div>
    </div>
  )
}
