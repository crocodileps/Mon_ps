'use client'

import { Card } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { formatNumber } from "@/lib/format"
import { Brain, TrendingUp, Activity, Zap, Target, Award, Loader2, AlertTriangle, Search } from 'lucide-react'
import { motion } from 'framer-motion'
import { useAgentSignals, useAgentPerformance, useAgentHealth } from '@/hooks/use-agents'

export default function CompareAgentsPage() {
  const { data: signals, isLoading: loadingSignals } = useAgentSignals()
  const { data: performance, isLoading: loadingPerf } = useAgentPerformance()
  const { data: health, isLoading: loadingHealth } = useAgentHealth()

  const isLoading = loadingSignals || loadingPerf || loadingHealth

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-screen bg-black">
        <div className="text-center">
          <Loader2 className="w-12 h-12 animate-spin text-violet-500 mx-auto mb-4" />
          <p className="text-gray-400">Chargement des agents ML...</p>
        </div>
      </div>
    )
  }

  const agentIcons: Record<string, any> = {
    'Anomaly Detector': AlertTriangle,
    'Spread Optimizer': TrendingUp,
    'Pattern Matcher': Search,
    'Backtest Engine': Activity
  }

  const agentColors: Record<string, string> = {
    'Anomaly Detector': 'from-red-900/20 to-gray-900/50 border-red-500/30',
    'Spread Optimizer': 'from-green-900/20 to-gray-900/50 border-green-500/30',
    'Pattern Matcher': 'from-blue-900/20 to-gray-900/50 border-blue-500/30',
    'Backtest Engine': 'from-purple-900/20 to-gray-900/50 border-purple-500/30'
  }

  const topSignal = performance?.find(p => p.top_signal && p.avg_ev > 0)?.top_signal || signals?.[0]

  return (
    <div className="min-h-screen bg-black p-6 md:p-8">
      <div className="max-w-7xl mx-auto space-y-6">
        
        {/* Header */}
        <div className="flex justify-between items-center">
          <div>
            <h1 className="text-4xl font-bold text-white mb-2">
              🤖 Compare Agents ML
            </h1>
            <p className="text-gray-400">
              {health?.total_opportunities || 0} opportunités • {health?.agents?.length || 0} agents actifs
            </p>
          </div>
          <Badge className={health?.status === 'operational' ? 'bg-green-500/20 text-green-400' : 'bg-yellow-500/20 text-yellow-400'}>
            {health?.status || 'unknown'}
          </Badge>
        </div>

        {/* Top Signal Highlight */}
        {topSignal && (
          <motion.div initial={{ opacity: 0, scale: 0.95 }} animate={{ opacity: 1, scale: 1 }}>
            <Card className="bg-gradient-to-br from-yellow-900/20 to-gray-900/50 border-yellow-500/30 backdrop-blur-sm">
              <div className="p-6">
                <div className="flex items-center gap-4 mb-4">
                  <div className="p-3 rounded-lg bg-yellow-500/10">
                    <Award className="w-8 h-8 text-yellow-500" />
                  </div>
                  <div>
                    <h2 className="text-2xl font-bold text-white">{topSignal.match}</h2>
                    <p className="text-gray-400">🏆 Meilleur Signal Global</p>
                  </div>
                </div>
                <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
                  <div>
                    <p className="text-sm text-gray-400">Agent</p>
                    <p className="text-lg font-bold text-violet-400">{topSignal.agent}</p>
                  </div>
                  <div>
                    <p className="text-sm text-gray-400">Direction</p>
                    <p className="text-lg font-bold text-yellow-400">{topSignal.direction}</p>
                  </div>
                  <div>
                    <p className="text-sm text-gray-400">Spread</p>
                    <p className="text-lg font-bold text-green-400">{formatNumber(topSignal.spread_pct || 0, 2)}%</p>
                  </div>
                  <div>
                    <p className="text-sm text-gray-400">EV</p>
                    <p className="text-lg font-bold text-blue-400">{formatNumber(topSignal.expected_value || 0, 2)}</p>
                  </div>
                  <div>
                    <p className="text-sm text-gray-400">Kelly</p>
                    <p className="text-lg font-bold text-purple-400">{formatNumber((topSignal.kelly_fraction || 0) * 100, 1)}%</p>
                  </div>
                </div>
              </div>
            </Card>
          </motion.div>
        )}

        {/* 4 Agent Cards */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          {performance?.map((agent, index) => {
            const Icon = agentIcons[agent.agent_name] || Brain
            const colorClass = agentColors[agent.agent_name] || 'from-gray-900/90 to-gray-900/50 border-gray-800'
            
            return (
              <motion.div
                key={agent.agent_id}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: index * 0.1 }}
              >
                <Card className={`bg-gradient-to-br ${colorClass} backdrop-blur-sm h-full`}>
                  <div className="p-5">
                    <div className="flex items-center gap-3 mb-4">
                      <div className="p-2 rounded-lg bg-white/5">
                        <Icon className="w-6 h-6 text-white" />
                      </div>
                      <div>
                        <h3 className="font-semibold text-white text-sm">{agent.agent_name}</h3>
                        <Badge className={agent.status === 'active' ? 'bg-green-500/20 text-green-400 text-xs' : 'bg-gray-500/20 text-gray-400 text-xs'}>
                          {agent.status}
                        </Badge>
                      </div>
                    </div>
                    
                    <div className="space-y-2">
                      <div className="flex justify-between">
                        <span className="text-xs text-gray-400">Signaux</span>
                        <span className="text-sm font-bold text-white">{agent.total_signals}</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-xs text-gray-400">Confidence</span>
                        <span className="text-sm font-medium text-green-400">{formatNumber(agent.avg_confidence, 1)}%</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-xs text-gray-400">Avg EV</span>
                        <span className="text-sm font-medium text-blue-400">{formatNumber(agent.avg_ev, 2)}</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-xs text-gray-400">Avg Kelly</span>
                        <span className="text-sm font-medium text-purple-400">{formatNumber(agent.avg_kelly, 1)}%</span>
                      </div>
                    </div>
                  </div>
                </Card>
              </motion.div>
            )
          })}
        </div>

        {/* Signals Table by Agent */}
        <Card className="bg-gradient-to-br from-gray-900/90 to-gray-900/50 border-gray-800">
          <div className="p-6">
            <h2 className="text-xl font-semibold text-white mb-4">📊 Tous les Signaux ML ({signals?.length || 0})</h2>
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="border-b border-gray-800">
                    <th className="text-left py-3 text-gray-400 text-sm">Agent</th>
                    <th className="text-left py-3 text-gray-400 text-sm">Match</th>
                    <th className="text-right py-3 text-gray-400 text-sm">Direction</th>
                    <th className="text-right py-3 text-gray-400 text-sm">Confidence</th>
                    <th className="text-right py-3 text-gray-400 text-sm">Spread</th>
                  </tr>
                </thead>
                <tbody>
                  {signals?.slice(0, 15).map((signal, idx) => (
                    <tr key={idx} className="border-b border-gray-800/50 hover:bg-white/5">
                      <td className="py-3">
                        <Badge className="bg-violet-500/20 text-violet-400 text-xs">
                          {signal.agent?.split(' ')[0]}
                        </Badge>
                      </td>
                      <td className="py-3">
                        <div>
                          <p className="text-white font-medium text-sm">{signal.match}</p>
                          <p className="text-xs text-gray-500">{signal.sport?.replace('soccer_', '')}</p>
                        </div>
                      </td>
                      <td className="text-right">
                        <Badge className={signal.direction === 'BACK_AWAY' ? 'bg-yellow-500/20 text-yellow-400' : 'bg-blue-500/20 text-blue-400'}>
                          {signal.direction}
                        </Badge>
                      </td>
                      <td className="text-right text-green-400 font-medium">
                        {formatNumber(signal.confidence || 0, 1)}%
                      </td>
                      <td className="text-right text-purple-400">
                        {signal.spread_pct ? formatNumber(signal.spread_pct, 1) + '%' : '-'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <p className="text-sm text-gray-500 mt-4">
              Affichage des 15 premiers signaux sur {signals?.length || 0} disponibles
            </p>
          </div>
        </Card>

        {/* Stats Footer */}
        <Card className="bg-gradient-to-br from-green-900/20 to-gray-900/50 border-green-500/30">
          <div className="p-4">
            <p className="text-sm text-gray-400">
              <span className="text-green-400 font-medium">✅ Données Temps Réel:</span> 4 agents ML analysant {health?.total_opportunities || 0} opportunités sur 38+ ligues mondiales. 
              Auto-refresh toutes les 5 minutes.
            </p>
          </div>
        </Card>

      </div>
    </div>
  )
}
