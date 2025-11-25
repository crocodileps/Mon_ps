'use client'

import { useState } from 'react'
import { Sparkles, TrendingUp, AlertTriangle, AlertCircle } from 'lucide-react'

interface FeuxItem {
  titre: string
  detail: string
}

interface Synthesis {
  feux_verts: FeuxItem[]
  feux_orange: FeuxItem[]
  feux_rouges: FeuxItem[]
  recommandation: string
  narrative: string
  risk_level: 'FAIBLE' | 'MODÉRÉ' | 'ÉLEVÉ'
  confidence_narrative: 'HIGH' | 'MEDIUM' | 'LOW'
}

interface Props {
  matchId: string
}

export function DiamondSynthesis({ matchId }: Props) {
  const [loading, setLoading] = useState(false)
  const [synthesis, setSynthesis] = useState<Synthesis | null>(null)
  const [error, setError] = useState<string | null>(null)

  const fetchSynthesis = async () => {
    setLoading(true)
    setError(null)
    try {
      const response = await fetch(`http://91.98.131.218:8001/agents/diamond/synthesize?match_id=${matchId}`, {
        method: 'POST'
      })
      if (!response.ok) throw new Error('Erreur API')
      const data = await response.json()
      if (data.error) throw new Error(data.error)
      setSynthesis(data.synthesis)
    } catch (err: any) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  const getRiskColor = (level: string) => {
    switch (level) {
      case 'FAIBLE': return 'text-green-400'
      case 'MODÉRÉ': return 'text-orange-400'
      case 'ÉLEVÉ': return 'text-red-400'
      default: return 'text-gray-400'
    }
  }

  const getConfidenceColor = (conf: string) => {
    switch (conf) {
      case 'HIGH': return 'text-green-400'
      case 'MEDIUM': return 'text-yellow-400'
      case 'LOW': return 'text-orange-400'
      default: return 'text-gray-400'
    }
  }

  if (!synthesis) {
    return (
      <div className="bg-gradient-to-r from-cyan-900/20 to-blue-900/20 rounded-xl p-6 border border-cyan-500/30 mb-6">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-3">
            <Sparkles className="text-cyan-400" size={28} />
            <h3 className="text-xl font-bold text-cyan-400">💎 Diamond Synthesis</h3>
          </div>
          <button
            onClick={fetchSynthesis}
            disabled={loading}
            className="px-4 py-2 bg-cyan-500 hover:bg-cyan-600 text-black font-semibold rounded-lg transition-colors disabled:opacity-50"
          >
            {loading ? '⏳ Génération...' : '✨ Générer Synthèse IA'}
          </button>
        </div>
        <p className="text-gray-400 text-sm">
          Synthèse qualitative générée par GPT-4o analysant tous les signaux des agents ML.
        </p>
        {error && <p className="text-red-400 mt-2 text-sm">❌ {error}</p>}
      </div>
    )
  }

  return (
    <div className="bg-gradient-to-r from-cyan-900/20 to-blue-900/20 rounded-xl p-6 border border-cyan-500/30 space-y-6 mb-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Sparkles className="text-cyan-400" size={28} />
          <h3 className="text-xl font-bold text-cyan-400">💎 Diamond Synthesis</h3>
        </div>
        <div className="flex gap-4 text-sm">
          <span className={`font-semibold ${getRiskColor(synthesis.risk_level)}`}>
            Risque: {synthesis.risk_level}
          </span>
          <span className={`font-semibold ${getConfidenceColor(synthesis.confidence_narrative)}`}>
            Conf: {synthesis.confidence_narrative}
          </span>
        </div>
      </div>

      {/* Narrative */}
      <div className="bg-slate-900/60 rounded-lg p-4 border border-slate-700">
        <p className="text-white text-base leading-relaxed">{synthesis.narrative}</p>
      </div>

      {/* Feux Verts */}
      {synthesis.feux_verts && synthesis.feux_verts.length > 0 && (
        <div>
          <h4 className="text-green-400 font-semibold mb-3 flex items-center gap-2">
            <TrendingUp size={18} />
            ✅ Feux Verts (Arguments Forts)
          </h4>
          <div className="space-y-2">
            {synthesis.feux_verts.map((item, i) => (
              <div key={i} className="bg-green-900/20 rounded-lg p-3 border border-green-500/30">
                <div className="text-white font-medium mb-1">✅ {item.titre}</div>
                <p className="text-gray-400 text-sm">{item.detail}</p>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Feux Orange */}
      {synthesis.feux_orange && synthesis.feux_orange.length > 0 && (
        <div>
          <h4 className="text-orange-400 font-semibold mb-3 flex items-center gap-2">
            <AlertTriangle size={18} />
            ⚠️ Feux Orange (Points d'Attention)
          </h4>
          <div className="space-y-2">
            {synthesis.feux_orange.map((item, i) => (
              <div key={i} className="bg-orange-900/20 rounded-lg p-3 border border-orange-500/30">
                <div className="text-white font-medium mb-1">⚠️ {item.titre}</div>
                <p className="text-gray-400 text-sm">{item.detail}</p>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Feux Rouges */}
      {synthesis.feux_rouges && synthesis.feux_rouges.length > 0 && (
        <div>
          <h4 className="text-red-400 font-semibold mb-3 flex items-center gap-2">
            <AlertCircle size={18} />
            ❌ Feux Rouges (Risques Clés)
          </h4>
          <div className="space-y-2">
            {synthesis.feux_rouges.map((item, i) => (
              <div key={i} className="bg-red-900/20 rounded-lg p-3 border border-red-500/30">
                <div className="text-white font-medium mb-1">❌ {item.titre}</div>
                <p className="text-gray-400 text-sm">{item.detail}</p>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Recommandation Finale */}
      <div className="bg-cyan-900/30 rounded-lg p-4 border border-cyan-500/50">
        <h4 className="text-cyan-400 font-semibold mb-2">⚡ Recommandation Finale</h4>
        <p className="text-white text-base">{synthesis.recommandation}</p>
      </div>
    </div>
  )
}
