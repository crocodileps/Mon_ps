'use client'

import { useState } from 'react'
import { BarChart, Bar, LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, PieChart, Pie, Cell } from 'recharts'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Top10Carousel } from '@/components/top10-carousel'
import { ArrowUpRight, ArrowDownRight, TrendingUp } from 'lucide-react'
import { AgentDetailsModal } from '@/components/agent-details-modal'

const agentData = [
  { 
    id: 'titan',
    name: 'Titan', 
    successRate: 92.4, 
    riskProfile: 'Faible', 
    performance: '+12.8%', 
    color: 'blue'
  },
  { 
    id: 'oracle',
    name: 'Oracle', 
    successRate: 88.1, 
    riskProfile: 'Moyen', 
    performance: '+9.2%', 
    color: 'purple'
  },
  { 
    id: 'momentum',
    name: 'Momentum', 
    successRate: 75, 
    riskProfile: 'Élevé', 
    performance: '-2.5%', 
    color: 'pink'
  },
]

const performanceData = [
  { month: 'Jan', value: 8.2 },
  { month: 'Fév', value: 10.5 },
  { month: 'Mar', value: 9.8 },
  { month: 'Avr', value: 12.3 },
  { month: 'Mai', value: 12.8 },
  { month: 'Juin', value: 9.2 },
]

const statsData = [
  { name: 'Gagnées', value: 45, fill: '#10b981' },
  { name: 'Perdues', value: 12, fill: '#ef4444' },
  { name: 'En attente', value: 8, fill: '#f59e0b' },
]
export function AgentDashboard() {
  const [selectedAgent, setSelectedAgent] = useState<typeof agentData[0] | null>(null)
  const [isModalOpen, setIsModalOpen] = useState(false)

  const handleDetailsClick = (agent: typeof agentData[0]) => {
    setSelectedAgent(agent)
    setIsModalOpen(true)
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-col md:flex-row md:items-end md:justify-between gap-4 mb-6">
        <div>
          <h1 className="text-4xl font-bold text-foreground mb-2">Dashboard Agents IA</h1>
          <p className="text-muted-foreground text-sm">Suivi en temps réel de la performance des agents traders</p>
        </div>
      </div>

      <div>
        <Top10Carousel />
      </div>

      <Card className="backdrop-blur-md border border-white/20 bg-card/50">
        <CardHeader className="pb-4">
          <CardTitle className="text-xl">Comparatif des Agents</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-border/50">
                  <th className="text-left py-4 px-4 font-semibold text-muted-foreground uppercase text-xs tracking-wider">Agent</th>
                  <th className="text-left py-4 px-4 font-semibold text-muted-foreground uppercase text-xs tracking-wider">Profil Risque</th>
                  <th className="text-left py-4 px-4 font-semibold text-muted-foreground uppercase text-xs tracking-wider">Taux Succès</th>
                  <th className="text-left py-4 px-4 font-semibold text-muted-foreground uppercase text-xs tracking-wider">Perf. (3M)</th>
                  <th className="text-left py-4 px-4 font-semibold text-muted-foreground uppercase text-xs tracking-wider">Actions</th>
                </tr>
              </thead>
              <tbody>
                {agentData.map((agent) => (
                  <tr key={agent.id} className="border-b border-border/30 hover:bg-muted/20 transition-colors cursor-pointer group">
                    <td className="py-4 px-4">
                      <span className={`inline-block px-2.5 py-1 rounded-full text-xs font-bold border ${
                        agent.id === 'titan' ? 'bg-blue-500/20 text-blue-400 border-blue-500/30' :
                        agent.id === 'oracle' ? 'bg-purple-500/20 text-purple-400 border-purple-500/30' :
                        'bg-pink-500/20 text-pink-400 border-pink-500/30'
                      }`}>
                        {agent.name}
                      </span>
                    </td>
                    <td className="py-4 px-4">
                      <span className={`px-3 py-1 rounded-full text-xs font-semibold border ${
                        agent.riskProfile === 'Faible' ? 'bg-green-500/20 text-green-300 border-green-500/30' :
                        agent.riskProfile === 'Moyen' ? 'bg-yellow-500/20 text-yellow-300 border-yellow-500/30' :
                        'bg-red-500/20 text-red-300 border-red-500/30'
                      }`}>
                        {agent.riskProfile}
                      </span>
                    </td>
                    <td className="py-4 px-4">
                      <div className="flex items-center gap-2">
                        <div className="text-green-400 font-semibold">{agent.successRate}%</div>
                        <div className="w-20 h-1.5 bg-muted rounded-full overflow-hidden">
                          <div className="h-full bg-gradient-to-r from-green-500 to-cyan-500" style={{ width: `${agent.successRate}%` }} />
                        </div>
                      </div>
                    </td>
                    <td className="py-4 px-4">
                      <div className={`flex items-center gap-1 font-semibold ${agent.performance.includes('-') ? 'text-red-400' : 'text-green-400'}`}>
                        {agent.performance.includes('-') ? <ArrowDownRight size={16} /> : <ArrowUpRight size={16} />}
                        {agent.performance}
                      </div>
                    </td>
                    <td className="py-4 px-4">
                      <Button variant="outline" size="sm" className="border-border hover:bg-primary/10 hover:border-primary" onClick={() => handleDetailsClick(agent)}>
                        Détails
                      </Button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>
<div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card className="backdrop-blur-md border border-white/20 bg-card/50">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <TrendingUp size={20} className="text-primary" />
              Performance (3 Mois)
            </CardTitle>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={300}>
              <LineChart data={performanceData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                <XAxis dataKey="month" stroke="#94a3b8" />
                <YAxis stroke="#94a3b8" />
                <Tooltip contentStyle={{ backgroundColor: '#111c3d', border: '1px solid #1e293b', borderRadius: '8px' }} labelStyle={{ color: '#e8ebf7' }} />
                <Line type="monotone" dataKey="value" stroke="#06b6d4" strokeWidth={2} dot={{ fill: '#06b6d4', r: 4 }} />
              </LineChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>

        <Card className="backdrop-blur-md border border-white/20 bg-card/50">
          <CardHeader>
            <CardTitle>Distribution des Résultats</CardTitle>
          </CardHeader>
          <CardContent className="flex items-center justify-center">
            <ResponsiveContainer width="100%" height={300}>
              <PieChart>
                <Pie data={statsData} cx="50%" cy="50%" innerRadius={60} outerRadius={100} paddingAngle={2} dataKey="value">
                  {statsData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={entry.fill} />
                  ))}
                </Pie>
                <Tooltip contentStyle={{ backgroundColor: '#111c3d', border: '1px solid #1e293b', borderRadius: '8px' }} />
              </PieChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>
      </div>

      <AgentDetailsModal isOpen={isModalOpen} onClose={() => setIsModalOpen(false)} agent={selectedAgent} />
    </div>
  )
}

