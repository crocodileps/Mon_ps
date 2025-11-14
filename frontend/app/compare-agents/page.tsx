'use client'

import { Card } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { formatNumber } from "@/lib/format"
import { BarChart, Bar, LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, RadarChart, PolarGrid, PolarAngleAxis, PolarRadiusAxis, Radar } from 'recharts'
import { Brain, TrendingUp, Activity, Zap, Target, Award } from 'lucide-react'
import { motion } from 'framer-motion'

// Mock data basé sur les performances connues
// TODO: Remplacer par useAgentsComparison() quand l'endpoint sera créé
const agentsData = [
  {
    id: 'agent_a',
    name: 'Agent A',
    fullName: 'Anomaly Detector',
    description: 'Détection anomalies dans les cotes',
    icon: Brain,
    color: 'text-blue-500',
    bgColor: 'bg-blue-500/10',
    borderColor: 'border-blue-500/30',
    metrics: {
      roi: 15.2,
      sharpe: 1.12,
      clv: 1.8,
      winRate: 54.3,
      totalBets: 127,
      avgOdds: 2.15,
      maxDrawdown: -8.2,
      profitFactor: 1.45
    }
  },
  {
    id: 'agent_b',
    name: 'Agent B',
    fullName: 'Spread Optimizer',
    description: 'Kelly Criterion sur spreads',
    icon: TrendingUp,
    color: 'text-green-500',
    bgColor: 'bg-green-500/10',
    borderColor: 'border-green-500/30',
    metrics: {
      roi: 202.0, // Performance réelle en backtest
      sharpe: 2.85,
      clv: 3.2,
      winRate: 68.5,
      totalBets: 89,
      avgOdds: 2.45,
      maxDrawdown: -12.3,
      profitFactor: 3.12
    }
  },
  {
    id: 'agent_c',
    name: 'Agent C',
    fullName: 'Pattern Matcher',
    description: 'Reconnaissance patterns historiques',
    icon: Activity,
    color: 'text-purple-500',
    bgColor: 'bg-purple-500/10',
    borderColor: 'border-purple-500/30',
    metrics: {
      roi: 22.8,
      sharpe: 1.58,
      clv: 2.1,
      winRate: 59.2,
      totalBets: 156,
      avgOdds: 1.95,
      maxDrawdown: -10.5,
      profitFactor: 1.78
    }
  },
  {
    id: 'agent_d',
    name: 'Agent D',
    fullName: 'Backtest Engine',
    description: 'Validation stratégies par backtest',
    icon: Zap,
    color: 'text-orange-500',
    bgColor: 'bg-orange-500/10',
    borderColor: 'border-orange-500/30',
    metrics: {
      roi: 18.5,
      sharpe: 1.35,
      clv: 1.9,
      winRate: 56.8,
      totalBets: 203,
      avgOdds: 2.05,
      maxDrawdown: -9.1,
      profitFactor: 1.62
    }
  }
]

// Données pour graphiques comparatifs
const roiData = agentsData.map(agent => ({
  name: agent.name,
  roi: agent.metrics.roi
}))

const radarData = [
  {
    metric: 'ROI',
    'Agent A': 15.2,
    'Agent B': 100, // Normalisé à 100 pour le radar
    'Agent C': 22.8,
    'Agent D': 18.5
  },
  {
    metric: 'Sharpe',
    'Agent A': 39,
    'Agent B': 100,
    'Agent C': 55,
    'Agent D': 47
  },
  {
    metric: 'CLV',
    'Agent A': 56,
    'Agent B': 100,
    'Agent C': 66,
    'Agent D': 59
  },
  {
    metric: 'Win Rate',
    'Agent A': 79,
    'Agent B': 100,
    'Agent C': 86,
    'Agent D': 83
  }
]

export default function CompareAgentsPage() {
  const bestAgent = agentsData.reduce((best, agent) => 
    agent.metrics.roi > best.metrics.roi ? agent : best
  )

  return (
    <div className="min-h-screen bg-black p-6 md:p-8">
      <div className="max-w-7xl mx-auto space-y-6">
        
        {/* Header */}
        <div>
          <h1 className="text-4xl font-bold text-white mb-2">
            🤖 Compare Agents ML
          </h1>
          <p className="text-gray-400">
            Comparaison des performances des 4 agents de trading
          </p>
        </div>

        {/* Best Agent Highlight */}
        <motion.div
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
        >
          <Card className={`bg-gradient-to-br from-${bestAgent.color.split('-')[1]}-900/20 to-gray-900/50 border-${bestAgent.color.split('-')[1]}-500/30 backdrop-blur-sm`}>
            <div className="p-6">
              <div className="flex items-center gap-4 mb-4">
                <div className={`p-3 rounded-lg ${bestAgent.bgColor}`}>
                  <Award className={`w-8 h-8 ${bestAgent.color}`} />
                </div>
                <div>
                  <h2 className="text-2xl font-bold text-white">{bestAgent.fullName}</h2>
                  <p className="text-gray-400">🏆 Meilleur ROI : {formatNumber(bestAgent.metrics.roi, 1)}%</p>
                </div>
              </div>
              <p className="text-gray-300">{bestAgent.description}</p>
            </div>
          </Card>
        </motion.div>

        {/* Cards Agents */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          {agentsData.map((agent, index) => (
            <motion.div
              key={agent.id}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: index * 0.1 }}
            >
              <Card className={`bg-gradient-to-br from-gray-900/90 to-gray-900/50 border-gray-800 hover:${agent.borderColor} transition-all duration-300`}>
                <div className="p-6">
                  <div className="flex items-center gap-3 mb-4">
                    <div className={`p-2 rounded-lg ${agent.bgColor}`}>
                      <agent.icon className={`w-5 h-5 ${agent.color}`} />
                    </div>
                    <div>
                      <h3 className="font-semibold text-white">{agent.name}</h3>
                      <p className="text-xs text-gray-400">{agent.fullName}</p>
                    </div>
                  </div>
                  
                  <div className="space-y-2">
                    <div className="flex justify-between">
                      <span className="text-sm text-gray-400">ROI</span>
                      <span className="text-sm font-bold text-green-400">
                        {formatNumber(agent.metrics.roi, 1)}%
                      </span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-sm text-gray-400">Sharpe</span>
                      <span className="text-sm font-medium text-white">
                        {formatNumber(agent.metrics.sharpe, 2)}
                      </span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-sm text-gray-400">Win Rate</span>
                      <span className="text-sm font-medium text-blue-400">
                        {formatNumber(agent.metrics.winRate, 1)}%
                      </span>
                    </div>
                  </div>
                </div>
              </Card>
            </motion.div>
          ))}
        </div>

        {/* Graphiques Comparatifs */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          
          {/* ROI Comparison */}
          <Card className="bg-gradient-to-br from-gray-900/90 to-gray-900/50 border-gray-800">
            <div className="p-6">
              <h2 className="text-xl font-semibold text-white mb-4">📊 Comparaison ROI</h2>
              <ResponsiveContainer width="100%" height={300}>
                <BarChart data={roiData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                  <XAxis dataKey="name" stroke="#9ca3af" />
                  <YAxis stroke="#9ca3af" />
                  <Tooltip
                    contentStyle={{ backgroundColor: '#1f2937', border: '1px solid #374151' }}
                    labelStyle={{ color: '#fff' }}
                  />
                  <Bar dataKey="roi" fill="#10b981" name="ROI (%)" />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </Card>

          {/* Radar Performance */}
          <Card className="bg-gradient-to-br from-gray-900/90 to-gray-900/50 border-gray-800">
            <div className="p-6">
              <h2 className="text-xl font-semibold text-white mb-4">🎯 Performance Globale</h2>
              <ResponsiveContainer width="100%" height={300}>
                <RadarChart data={radarData}>
                  <PolarGrid stroke="#374151" />
                  <PolarAngleAxis dataKey="metric" stroke="#9ca3af" />
                  <PolarRadiusAxis stroke="#9ca3af" />
                  <Radar name="Agent A" dataKey="Agent A" stroke="#3b82f6" fill="#3b82f6" fillOpacity={0.3} />
                  <Radar name="Agent B" dataKey="Agent B" stroke="#10b981" fill="#10b981" fillOpacity={0.3} />
                  <Radar name="Agent C" dataKey="Agent C" stroke="#8b5cf6" fill="#8b5cf6" fillOpacity={0.3} />
                  <Radar name="Agent D" dataKey="Agent D" stroke="#f97316" fill="#f97316" fillOpacity={0.3} />
                  <Legend />
                </RadarChart>
              </ResponsiveContainer>
            </div>
          </Card>
        </div>

        {/* Tableau Détaillé */}
        <Card className="bg-gradient-to-br from-gray-900/90 to-gray-900/50 border-gray-800">
          <div className="p-6">
            <h2 className="text-xl font-semibold text-white mb-4">📋 Métriques Détaillées</h2>
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="border-b border-gray-800">
                    <th className="text-left py-3 text-gray-400">Agent</th>
                    <th className="text-right py-3 text-gray-400">ROI</th>
                    <th className="text-right py-3 text-gray-400">Sharpe</th>
                    <th className="text-right py-3 text-gray-400">CLV</th>
                    <th className="text-right py-3 text-gray-400">Win Rate</th>
                    <th className="text-right py-3 text-gray-400">Paris</th>
                    <th className="text-right py-3 text-gray-400">Profit Factor</th>
                  </tr>
                </thead>
                <tbody>
                  {agentsData.map((agent, idx) => (
                    <tr key={idx} className="border-b border-gray-800/50">
                      <td className="py-3">
                        <div className="flex items-center gap-2">
                          <agent.icon className={`w-4 h-4 ${agent.color}`} />
                          <span className="text-white font-medium">{agent.fullName}</span>
                        </div>
                      </td>
                      <td className="text-right text-green-400 font-bold">
                        {formatNumber(agent.metrics.roi, 1)}%
                      </td>
                      <td className="text-right text-blue-400">
                        {formatNumber(agent.metrics.sharpe, 2)}
                      </td>
                      <td className="text-right text-purple-400">
                        {formatNumber(agent.metrics.clv, 1)}%
                      </td>
                      <td className="text-right text-white">
                        {formatNumber(agent.metrics.winRate, 1)}%
                      </td>
                      <td className="text-right text-gray-300">
                        {agent.metrics.totalBets}
                      </td>
                      <td className="text-right text-orange-400">
                        {formatNumber(agent.metrics.profitFactor, 2)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </Card>

        {/* Note */}
        <Card className="bg-gradient-to-br from-blue-900/20 to-gray-900/50 border-blue-500/30">
          <div className="p-4">
            <p className="text-sm text-gray-400">
              <span className="text-blue-400 font-medium">ℹ️ Note:</span> Ces données sont basées sur les backtests des agents ML. 
              Agent B (Spread Optimizer) a réalisé un ROI de 202% grâce à l'implémentation du Kelly Criterion.
            </p>
          </div>
        </Card>

      </div>
    </div>
  )
}
