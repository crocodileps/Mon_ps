'use client'
import { useState } from 'react'
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Badge } from '@/components/ui/badge'
import { RefreshCw, TrendingUp, AlertTriangle } from 'lucide-react'

interface ConseilUltimModalProps {
  isOpen: boolean
  onClose: () => void
  matchId: string
  homeTeam: string
  awayTeam: string
}

export function ConseilUltimModal({ isOpen, onClose, matchId, homeTeam, awayTeam }: ConseilUltimModalProps) {
  const [data, setData] = useState<any>(null)
  const [loading, setLoading] = useState(false)

  const fetchAnalysis = async () => {
    setLoading(true)
    try {
      const response = await fetch(`http://91.98.131.218:8001/agents/conseil-ultim/analyze/${matchId}`, {
        method: 'POST'
      })
      const result = await response.json()
      setData(result)
    } catch (error) {
      console.error('Erreur:', error)
    }
    setLoading(false)
  }

  // Auto-fetch au montage
  if (isOpen && !data && !loading) {
    fetchAnalysis()
  }

  if (loading || !data) {
    return (
      <Dialog open={isOpen} onOpenChange={onClose}>
        <DialogContent className="max-w-4xl bg-slate-900 border-slate-800">
          <div className="flex items-center justify-center py-20">
            <RefreshCw className="w-8 h-8 animate-spin text-purple-500" />
            <span className="ml-3 text-slate-400">Analyse en cours...</span>
          </div>
        </DialogContent>
      </Dialog>
    )
  }

  const best = data.recommandation_finale
  const all = data.toutes_options

  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="max-w-5xl max-h-[90vh] overflow-y-auto bg-gradient-to-br from-slate-950 via-slate-900 to-slate-950 border-slate-800">
        <DialogHeader>
          <DialogTitle className="text-2xl font-bold text-white flex items-center gap-2">
            💎 Analyse Complète : {homeTeam} vs {awayTeam}
          </DialogTitle>
        </DialogHeader>

        {/* Recommandation Finale */}
        <div className="mt-6 p-6 rounded-xl bg-gradient-to-r from-purple-500/10 to-indigo-500/10 border-2 border-purple-500/30">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-xl font-bold text-white flex items-center gap-2">
              🎯 RECOMMANDATION FINALE
            </h3>
            <Badge className="text-lg px-4 py-2 bg-purple-500 text-white">
              Score: {best.score_final}/100
            </Badge>
          </div>

          <div className="grid grid-cols-2 gap-4 p-4 bg-slate-900/50 rounded-lg">
            <div>
              <div className="text-3xl font-black text-white mb-2">{best.label}</div>
              <div className="flex gap-2 items-center">
                <span className="text-2xl">{best.risque_emoji}</span>
                <Badge className={`${
                  best.risque === 'FAIBLE' ? 'bg-green-500/20 text-green-400' :
                  best.risque === 'MODÉRÉ' ? 'bg-yellow-500/20 text-yellow-400' :
                  'bg-red-500/20 text-red-400'
                }`}>
                  {best.risque}
                </Badge>
                <Badge className="bg-blue-500/20 text-blue-400">{best.conseil}</Badge>
              </div>
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div className="bg-slate-800/50 p-3 rounded">
                <div className="text-xs text-slate-400">Cote Moyenne</div>
                <div className="text-xl font-bold text-white">{best.cote_moyenne}</div>
              </div>
              <div className="bg-slate-800/50 p-3 rounded">
                <div className="text-xs text-slate-400">Probabilité</div>
                <div className="text-xl font-bold text-green-400">{best.notre_proba}%</div>
              </div>
              <div className="bg-slate-800/50 p-3 rounded">
                <div className="text-xs text-slate-400">Edge Réel</div>
                <div className={`text-xl font-bold ${best.edge_reel > 0 ? 'text-green-400' : 'text-red-400'}`}>
                  {best.edge_reel > 0 ? '+' : ''}{best.edge_reel}%
                </div>
              </div>
              <div className="bg-slate-800/50 p-3 rounded">
                <div className="text-xs text-slate-400">Gain Attendu</div>
                <div className={`text-xl font-bold ${best.gain_attendu > 0 ? 'text-green-400' : 'text-slate-400'}`}>
                  {best.gain_attendu > 0 ? '+' : ''}{best.gain_attendu}%
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Toutes les Options */}
        <div className="mt-6">
          <h3 className="text-lg font-bold text-white mb-4 flex items-center gap-2">
            📊 TOUTES LES OPTIONS ANALYSÉES
          </h3>

          <div className="space-y-3">
            {all.map((option: any, index: number) => (
              <div
                key={option.outcome}
                className={`p-4 rounded-lg border transition-all ${
                  index === 0 
                    ? 'bg-purple-500/5 border-purple-500/30' 
                    : 'bg-slate-800/30 border-slate-700'
                }`}
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <div className="text-3xl font-bold text-slate-600">#{index + 1}</div>
                    <div>
                      <div className="text-lg font-bold text-white">{option.label}</div>
                      <div className="flex gap-2 mt-1">
                        <span className="text-xl">{option.risque_emoji}</span>
                        <span className="text-sm text-slate-400">{option.risque}</span>
                        <span className="text-sm text-slate-500">•</span>
                        <span className="text-sm text-slate-400">{option.conseil}</span>
                      </div>
                    </div>
                  </div>

                  <div className="flex items-center gap-6">
                    <div className="text-center">
                      <div className="text-xs text-slate-400">Proba</div>
                      <div className="text-lg font-bold text-white">{option.notre_proba}%</div>
                    </div>
                    <div className="text-center">
                      <div className="text-xs text-slate-400">Edge</div>
                      <div className={`text-lg font-bold ${option.edge_reel > 0 ? 'text-green-400' : 'text-slate-400'}`}>
                        {option.edge_reel > 0 ? '+' : ''}{option.edge_reel}%
                      </div>
                    </div>
                    <Badge className="text-lg px-4 py-1 bg-slate-700 text-white">
                      {option.score_final}/100
                    </Badge>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Analyse Stratégique */}
        <div className="mt-6 p-4 bg-slate-800/30 rounded-lg border border-slate-700">
          <h4 className="text-sm font-bold text-white mb-3 flex items-center gap-2">
            💡 ANALYSE STRATÉGIQUE
          </h4>
          <div className="grid grid-cols-2 gap-3 text-sm">
            <div>
              <span className="text-slate-400">Agent Patron:</span>
              <span className="ml-2 text-white font-medium">
                Score {data.agent_patron.score}/100 ({data.agent_patron.predicted_outcome.toUpperCase()})
              </span>
            </div>
            <div>
              <span className="text-slate-400">Confiance Globale:</span>
              <span className="ml-2 text-white font-medium">
                {data.confiance_globale.score}/100 ({data.confiance_globale.label})
              </span>
            </div>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  )
}
