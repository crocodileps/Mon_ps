'use client'

import { Card } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { formatNumber } from "@/lib/format"
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts'
import { Brain, TrendingUp, Activity, Zap, Target, Award, Loader2 } from 'lucide-react'
import { motion } from 'framer-motion'
import { useAgentSignals, useAgentPerformance } from '@/hooks/use-agents'

export default function CompareAgentsPage() {
  const { data: signals, isLoading: loadingSignals } = useAgentSignals()
  const { data: performance, isLoading: loadingPerf } = useAgentPerformance()

  const isLoading = loadingSignals || loadingPerf

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-screen">
        <Loader2 className="w-8 h-8 animate-spin text-violet-500" />
      </div>
    )
  }

  // Préparer données pour graphiques
  const roiData = performance?.map(p => ({
    name: p.agent_name,
    ev: p.avg_ev,
    kelly: p.avg_kelly,
    signals: p.total_signals
  })) || []

  const topSignal = performance?.[0]?.top_signal

  return (
    <div className="min-h-screen bg-black p-6 md:p-8">
      <div className="max-w-7xl mx-auto space-y-6">
        
        {/* Header */}
        <div>
          <h1 className="text-4xl font-bold text-white mb-2">
            🤖 Compare Agents ML
          </h1>
          <p className="text-gray-400">
            Signaux de trading en temps réel basés sur l'analyse ML
          </p>
        </div>

        {/* Top Signal Highlight */}
        {topSignal && (
          <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
          >
            <Card className="bg-gradient-to-br from-green-900/20 to-gray-900/50 border-green-500/30 backdrop-blur-sm">
              <div className="p-6">
                <div className="flex items-center gap-4 mb-4">
                  <div className="p-3 rounded-lg bg-green-500/10">
                    <Award className="w-8 h-8 text-green-500" />
                  </div>
                  <div>
                    <h2 className="text-2xl font-bold text-white">{topSignal.match}</h2>
                    <p className="text-gray-400">🏆 Meilleur Signal : {formatNumber(topSignal.spread_pct || 0, 2)}% spread</p>
                  </div>
                </div>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                  <div>
                    <p className="text-sm text-gray-400">Direction</p>
                    <p className="text-lg font-bold text-yellow-400">{topSignal.direction}</p>
                  </div>
                  <div>
                    <p className="text-sm text-gray-400">EV</p>
                    <p className="text-lg font-bold text-green-400">{formatNumber(topSignal.expected_value || 0, 2)}</p>
                  </div>
                  <div>
                    <p className="text-sm text-gray-400">Kelly %</p>
                    <p className="text-lg font-bold text-blue-400">{formatNumber((topSignal.kelly_fraction || 0) * 100, 1)}%</p>
                  </div>
                  <div>
                    <p className="text-sm text-gray-400">Bookmakers</p>
                    <p className="text-lg font-bold text-purple-400">{topSignal.bookmaker_count}</p>
                  </div>
                </div>
              </div>
            </Card>
          </motion.div>
        )}

        {/* Agent Performance Cards */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {performance?.map((agent, index) => (
            <motion.div
              key={agent.agent_id}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: index * 0.1 }}
            >
              <Card className="bg-gradient-to-br from-gray-900/90 to-gray-900/50 border-gray-800 hover:border-violet-500/50 transition-all duration-300">
                <div className="p-6">
                  <div className="flex items-center gap-3 mb-4">
                    <div className="p-2 rounded-lg bg-violet-500/10">
                      <TrendingUp className="w-5 h-5 text-violet-500" />
                    </div>
                    <div>
                      <h3 className="font-semibold text-white">{agent.agent_name}</h3>
                      <p className="text-xs text-gray-400">{agent.total_signals} signaux</p>
                    </div>
                  </div>
                  
                  <div className="space-y-3">
                    <div className="flex justify-between">
                      <span className="text-sm text-gray-400">Confidence</span>
                      <span className="text-sm font-bold text-green-400">
                        {formatNumber(agent.avg_confidence, 0)}%
                      </span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-sm text-gray-400">Avg EV</span>
                      <span className="text-sm font-medium text-blue-400">
                        {formatNumber(agent.avg_ev, 2)}
                      </span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-sm text-gray-400">Avg Kelly</span>
                      <span className="text-sm font-medium text-purple-400">
                        {formatNumber(agent.avg_kelly, 1)}%
                      </span>
                    </div>
                  </div>
                </div>
              </Card>
            </motion.div>
          ))}
        </div>

        {/* Signals Table */}
        <Card className="bg-gradient-to-br from-gray-900/90 to-gray-900/50 border-gray-800">
          <div className="p-6">
            <h2 className="text-xl font-semibold text-white mb-4">📊 Signaux ML en Temps Réel</h2>
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="border-b border-gray-800">
                    <th className="text-left py-3 text-gray-400">Match</th>
                    <th className="text-right py-3 text-gray-400">Direction</th>
                    <th className="text-right py-3 text-gray-400">Spread %</th>
                    <th className="text-right py-3 text-gray-400">EV</th>
                    <th className="text-right py-3 text-gray-400">Kelly %</th>
                  </tr>
                </thead>
                <tbody>
                  {signals?.slice(0, 10).map((signal, idx) => (
                    <tr key={idx} className="border-b border-gray-800/50">
                      <td className="py-3">
                        <div>
                          <p className="text-white font-medium">{signal.match}</p>
                          <p className="text-xs text-gray-500">{signal.sport}</p>
                        </div>
                      </td>
                      <td className="text-right">
                        <Badge className={signal.direction === 'BACK_AWAY' ? 'bg-yellow-500/20 text-yellow-400' : 'bg-blue-500/20 text-blue-400'}>
                          {signal.direction}
                        </Badge>
                      </td>
                      <td className="text-right text-green-400 font-bold">
                        {formatNumber(signal.spread_pct || 0, 2)}%
                      </td>
                      <td className="text-right text-blue-400">
                        {formatNumber(signal.expected_value || 0, 2)}
                      </td>
                      <td className="text-right text-purple-400">
                        {formatNumber((signal.kelly_fraction || 0) * 100, 1)}%
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <p className="text-sm text-gray-500 mt-4">
              Affichage des 10 premiers signaux sur {signals?.length || 0} disponibles
            </p>
          </div>
        </Card>

        {/* Note */}
        <Card className="bg-gradient-to-br from-green-900/20 to-gray-900/50 border-green-500/30">
          <div className="p-4">
            <p className="text-sm text-gray-400">
              <span className="text-green-400 font-medium">✅ Données Réelles:</span> Ces signaux sont générés en temps réel par les agents ML 
              analysant {signals?.[0]?.bookmaker_count || 0}+ bookmakers via Kelly Criterion et analyse des spreads.
            </p>
          </div>
        </Card>

      </div>
    </div>
  )
}
