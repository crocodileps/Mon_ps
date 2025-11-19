'use client'

import { useState, useEffect } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { ChevronDown, ChevronUp, TrendingUp, TrendingDown, AlertCircle, CheckCircle2, Filter } from 'lucide-react'
import { RadarChart, Radar, PolarGrid, PolarAngleAxis, PolarRadiusAxis, ResponsiveContainer, Legend, Tooltip, LineChart, Line, XAxis, YAxis, CartesianGrid } from 'recharts'

interface AgentData {
  agent_name: string
  total_signals: number
  avg_confidence: string
  avg_edge: string
  avg_kelly: string | null
  bets_placed: number
  wins: number
  losses: number
  pending: number
  win_rate: string | null
  outcomes: string[]
  roi: number
  perf_3m: string
  sharpe_ratio: number
  max_drawdown: number
  strengths: string[]
  weaknesses: string[]
  recent_bets: any[]
}

export default function AgentsComparisonPage() {
  const [agents, setAgents] = useState<AgentData[]>([])
  const [selectedAgent1, setSelectedAgent1] = useState<string>('')
  const [selectedAgent2, setSelectedAgent2] = useState<string>('')
  const [sportFilter, setSportFilter] = useState<string>('')
  const [minEdge, setMinEdge] = useState<number>(0)
  const [days, setDays] = useState<number>(90)
  const [loading, setLoading] = useState(true)
  const [showFilters, setShowFilters] = useState(true)
  const [betsLimit, setBetsLimit] = useState<number>(10)
  const [correlation, setCorrelation] = useState<number>(0)

  useEffect(() => {
    fetchAgents()
  }, [sportFilter, minEdge, days])

  const fetchAgents = async () => {
    try {
      setLoading(true)
      const params = new URLSearchParams()
      if (sportFilter) params.append('sport', sportFilter)
      if (selectedAgent1) params.append('agent1', selectedAgent1)
      if (selectedAgent2) params.append('agent2', selectedAgent2)
      params.append('min_edge', minEdge.toString())
      params.append('days', days.toString())
      
      const response = await fetch(`http://91.98.131.218:8001/agents/comparison?${params}`)
      const data = await response.json()
      setAgents(data.agents || [])
      setCorrelation(data.correlation || 0)
      
      if (data.agents && data.agents.length >= 2) {
        if (!selectedAgent1) setSelectedAgent1(data.agents[0].agent_name)
        if (!selectedAgent2 && data.agents.length > 1) setSelectedAgent2(data.agents[1].agent_name)
      }
    } catch (error) {
      console.error('Erreur fetch agents:', error)
    } finally {
      setLoading(false)
    }
  }

  const agent1 = agents.find(a => a.agent_name === selectedAgent1)
  const agent2 = agents.find(a => a.agent_name === selectedAgent2)

  const formatNumber = (val: any) => {
    const num = parseFloat(val || '0')
    return isNaN(num) ? '0' : num.toFixed(1)
  }

  const radarData = agent1 && agent2 ? [
    { metric: 'Win Rate', [agent1.agent_name]: parseFloat(agent1.win_rate || '0'), [agent2.agent_name]: parseFloat(agent2.win_rate || '0') },
    { metric: 'Confidence', [agent1.agent_name]: parseFloat(agent1.avg_confidence || '0'), [agent2.agent_name]: parseFloat(agent2.avg_confidence || '0') },
    { metric: 'Edge', [agent1.agent_name]: parseFloat(agent1.avg_edge || '0'), [agent2.agent_name]: parseFloat(agent2.avg_edge || '0') },
    { metric: 'Volume', [agent1.agent_name]: Math.min((agent1.total_signals / 50), 100), [agent2.agent_name]: Math.min((agent2.total_signals / 50), 100) },
  ] : []

  if (loading) {
  }
return (
    <div className="min-h-screen bg-gradient-to-br from-slate-950 via-slate-900 to-violet-950 p-8">
      {/* Navigation */}
      <div className="mb-6">
        <a href="/" className="text-violet-400 hover:text-violet-300 flex items-center gap-2">
          ← Retour au Dashboard
        </a>
      </div>
      <div className="max-w-7xl mx-auto space-y-6">
        
        {/* Header avec Toggle Filtres */}
        <div className="flex justify-between items-center">
          <div>
            <h1 className="text-4xl font-bold text-white mb-2">Comparaison Agents ML</h1>
            <p className="text-slate-400">Analyse comparative professionnelle avec métriques avancées</p>
          </div>
          <Button 
            onClick={() => setShowFilters(!showFilters)}
            variant="outline"
            className="bg-violet-500/20 border-violet-500/30 text-violet-300 hover:bg-violet-500/30"
          >
            <Filter className="w-4 h-4 mr-2" />
            {showFilters ? 'Masquer Filtres' : 'Afficher Filtres'}
            {showFilters ? <ChevronUp className="w-4 h-4 ml-2" /> : <ChevronDown className="w-4 h-4 ml-2" />}
          </Button>
        </div>

        {/* Filtres Collapsibles */}
        {showFilters && (
          <Card className="bg-slate-900/80 border-violet-500/30 backdrop-blur-xl shadow-2xl">
            <CardContent className="pt-6">
              <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                <div>
                  <label className="text-sm font-semibold text-violet-300 mb-2 block">Sport</label>
                  <Select value={sportFilter} onValueChange={setSportFilter}>
                    <SelectTrigger className="bg-slate-800/80 border-slate-700 text-white">
                      <SelectValue placeholder="Tous les sports" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="">Tous</SelectItem>
                      <SelectItem value="soccer_italy_serie_a">🇮🇹 Serie A</SelectItem>
                      <SelectItem value="soccer_uefa_europa_league">🏆 Europa League</SelectItem>
                      <SelectItem value="soccer_germany_bundesliga">🇩🇪 Bundesliga</SelectItem>
                    </SelectContent>
                  </Select>
                </div>

                <div>
                  <label className="text-sm font-semibold text-violet-300 mb-2 block">Période</label>
                  <Select value={days.toString()} onValueChange={(v) => setDays(parseInt(v))}>
                    <SelectTrigger className="bg-slate-800/80 border-slate-700 text-white">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="7">7 jours</SelectItem>
                      <SelectItem value="30">30 jours</SelectItem>
                      <SelectItem value="90">90 jours</SelectItem>
                    </SelectContent>
                  </Select>
                </div>

                <div>
                  <label className="text-sm font-semibold text-violet-300 mb-2 block">Edge Min (%)</label>
                  <Select value={minEdge.toString()} onValueChange={(v) => setMinEdge(parseFloat(v))}>
                    <SelectTrigger className="bg-slate-800/80 border-slate-700 text-white">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="0">Tous (0%)</SelectItem>
                      <SelectItem value="10">≥ 10%</SelectItem>
                      <SelectItem value="20">≥ 20%</SelectItem>
                      <SelectItem value="30">≥ 30%</SelectItem>
                    </SelectContent>
                  </Select>
                </div>

                <div className="flex items-end">
                  <Badge className="bg-violet-500/30 text-violet-200 border-violet-500/50 text-lg px-4 py-2">
                    {agents.length} agents disponibles
                  </Badge>
                </div>
              </div>
            </CardContent>
          </Card>
        )}

        {/* Sélecteurs Agents */}
        <div className="grid md:grid-cols-3 gap-6">
          <Card className="bg-gradient-to-br from-violet-900/50 to-slate-900/80 border-violet-500/40 backdrop-blur">
            <CardHeader>
              <CardTitle className="text-violet-300 text-xl">�� Agent 1</CardTitle>
            </CardHeader>
            <CardContent>
              <Select value={selectedAgent1} onValueChange={setSelectedAgent1}>
                <SelectTrigger className="bg-slate-800 border-violet-500/30 text-white">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {agents.map(agent => (
                    <SelectItem key={agent.agent_name} value={agent.agent_name}>
                      {agent.agent_name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </CardContent>
          </Card>

          <div className="flex items-center justify-center">
            <div className="text-7xl font-black text-transparent bg-clip-text bg-gradient-to-r from-violet-500 to-blue-500">
              VS
            </div>
          </div>

          <Card className="bg-gradient-to-br from-blue-900/50 to-slate-900/80 border-blue-500/40 backdrop-blur">
            <CardHeader>
              <CardTitle className="text-blue-300 text-xl">🤖 Agent 2</CardTitle>
            </CardHeader>
            <CardContent>
              <Select value={selectedAgent2} onValueChange={setSelectedAgent2}>
                <SelectTrigger className="bg-slate-800 border-blue-500/30 text-white">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {agents.map(agent => (
                    <SelectItem key={agent.agent_name} value={agent.agent_name}>
                      {agent.agent_name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </CardContent>
          </Card>
        </div>

        {agent1 && agent2 && (
          <>
            {/* Corrélation Badge */}
            <div className="flex justify-center">
              <Card className="bg-slate-900/80 border-slate-700 backdrop-blur inline-block">
                <CardContent className="pt-4 px-6">
                  <div className="text-center">
                    <div className="text-sm text-slate-400 mb-1">Corrélation (Overlap Matchs)</div>
                    <div className={`text-3xl font-bold ${correlation < 20 ? 'text-green-400' : correlation < 50 ? 'text-yellow-400' : 'text-red-400'}`}>
                      {correlation.toFixed(1)}%
                    </div>
                    <div className="text-xs text-slate-500 mt-1">
                      {correlation < 20 ? '✅ Excellente diversification' : correlation < 50 ? '⚠️ Diversification moyenne' : '❌ Forte corrélation'}
                    </div>
                  </div>
                </CardContent>
              </Card>
            </div>
{/* Cartes Comparatives PRO */}
            <div className="grid md:grid-cols-2 gap-6">
              {/* Agent 1 Card */}
              <Card className="bg-gradient-to-br from-violet-900/40 to-slate-900/60 border-violet-500/40 backdrop-blur-xl shadow-2xl">
                <CardHeader>
                  <CardTitle className="text-violet-300 text-2xl font-bold">{agent1.agent_name}</CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="grid grid-cols-2 gap-4">
                    <div className="bg-slate-800/50 p-4 rounded-lg">
                      <div className="text-sm text-slate-400 mb-1">Win Rate</div>
                      <div className="text-3xl font-bold text-green-400">{agent1.win_rate || '0'}%</div>
                      <div className="text-xs text-slate-500 mt-1">{agent1.wins}W / {agent1.losses}L</div>
                    </div>
                    <div className="bg-slate-800/50 p-4 rounded-lg">
                      <div className="text-sm text-slate-400 mb-1">ROI</div>
                      <div className="text-3xl font-bold text-blue-400">{agent1.roi.toFixed(1)}%</div>
                      <div className="text-xs text-slate-500 mt-1">Return on Investment</div>
                    </div>
                    <div className="bg-slate-800/50 p-4 rounded-lg">
                      <div className="text-sm text-slate-400 mb-1">Sharpe Ratio</div>
                      <div className="text-2xl font-bold text-violet-400">{agent1.sharpe_ratio.toFixed(2)}</div>
                      <div className="text-xs text-slate-500 mt-1">Risque ajusté</div>
                    </div>
                    <div className="bg-slate-800/50 p-4 rounded-lg">
                      <div className="text-sm text-slate-400 mb-1">Max Drawdown</div>
                      <div className="text-2xl font-bold text-red-400">{agent1.max_drawdown.toFixed(1)}%</div>
                      <div className="text-xs text-slate-500 mt-1">Pire chute</div>
                    </div>
                  </div>
                  
                  <div className="grid grid-cols-3 gap-3 text-center">
                    <div>
                      <div className="text-xs text-slate-400">Signaux</div>
                      <Badge className="bg-violet-500/30 text-violet-200 mt-1">{agent1.total_signals}</Badge>
                    </div>
                    <div>
                      <div className="text-xs text-slate-400">Confidence</div>
                      <div className="text-white font-bold mt-1">{agent1.avg_confidence}%</div>
                    </div>
                    <div>
                      <div className="text-xs text-slate-400">Edge</div>
                      <div className="text-green-400 font-bold mt-1">{agent1.avg_edge}%</div>
                    </div>
                  </div>

                  <div>
                    <div className="text-xs text-slate-400 mb-1">Kelly Fraction</div>
                    <div className="text-blue-400 font-mono">{agent1.avg_kelly || 'N/A'}</div>
                  </div>
                </CardContent>
              </Card>

              {/* Agent 2 Card */}
              <Card className="bg-gradient-to-br from-blue-900/40 to-slate-900/60 border-blue-500/40 backdrop-blur-xl shadow-2xl">
                <CardHeader>
                  <CardTitle className="text-blue-300 text-2xl font-bold">{agent2.agent_name}</CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="grid grid-cols-2 gap-4">
                    <div className="bg-slate-800/50 p-4 rounded-lg">
                      <div className="text-sm text-slate-400 mb-1">Win Rate</div>
                      <div className="text-3xl font-bold text-green-400">{agent2.win_rate || '0'}%</div>
                      <div className="text-xs text-slate-500 mt-1">{agent2.wins}W / {agent2.losses}L</div>
                    </div>
                    <div className="bg-slate-800/50 p-4 rounded-lg">
                      <div className="text-sm text-slate-400 mb-1">ROI</div>
                      <div className="text-3xl font-bold text-blue-400">{agent2.roi.toFixed(1)}%</div>
                      <div className="text-xs text-slate-500 mt-1">Return on Investment</div>
                    </div>
                    <div className="bg-slate-800/50 p-4 rounded-lg">
                      <div className="text-sm text-slate-400 mb-1">Sharpe Ratio</div>
                      <div className="text-2xl font-bold text-violet-400">{agent2.sharpe_ratio.toFixed(2)}</div>
                      <div className="text-xs text-slate-500 mt-1">Risque ajusté</div>
                    </div>
                    <div className="bg-slate-800/50 p-4 rounded-lg">
                      <div className="text-sm text-slate-400 mb-1">Max Drawdown</div>
                      <div className="text-2xl font-bold text-red-400">{agent2.max_drawdown.toFixed(1)}%</div>
                      <div className="text-xs text-slate-500 mt-1">Pire chute</div>
                    </div>
                  </div>
                  
                  <div className="grid grid-cols-3 gap-3 text-center">
                    <div>
                      <div className="text-xs text-slate-400">Signaux</div>
                      <Badge className="bg-blue-500/30 text-blue-200 mt-1">{agent2.total_signals}</Badge>
                    </div>
                    <div>
                      <div className="text-xs text-slate-400">Confidence</div>
                      <div className="text-white font-bold mt-1">{agent2.avg_confidence}%</div>
                    </div>
                    <div>
                      <div className="text-xs text-slate-400">Edge</div>
                      <div className="text-green-400 font-bold mt-1">{agent2.avg_edge}%</div>
                    </div>
                  </div>

                  <div>
                    <div className="text-xs text-slate-400 mb-1">Kelly Fraction</div>
                    <div className="text-blue-400 font-mono">{agent2.avg_kelly || 'N/A'}</div>
                  </div>
                </CardContent>
              </Card>
            </div>

            {/* Forces/Faiblesses */}
            <div className="grid md:grid-cols-2 gap-6">
              <Card className="bg-slate-900/80 border-violet-500/30 backdrop-blur">
                <CardHeader>
                  <CardTitle className="text-violet-300">{agent1.agent_name.split(' - ')[1]}</CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div>
                    <h4 className="text-sm font-semibold text-green-400 mb-2 flex items-center gap-2">
                      <CheckCircle2 className="w-4 h-4" /> Forces
                    </h4>
                    <ul className="space-y-1">
                      {agent1.strengths.map((s, i) => (
                        <li key={i} className="text-sm text-slate-300 pl-4">• {s}</li>
                      ))}
                    </ul>
                  </div>
                  <div>
                    <h4 className="text-sm font-semibold text-red-400 mb-2 flex items-center gap-2">
                      <AlertCircle className="w-4 h-4" /> Faiblesses
                    </h4>
                    <ul className="space-y-1">
                      {agent1.weaknesses.map((w, i) => (
                        <li key={i} className="text-sm text-slate-400 pl-4">• {w}</li>
                      ))}
                    </ul>
                  </div>
                </CardContent>
              </Card>

              <Card className="bg-slate-900/80 border-blue-500/30 backdrop-blur">
                <CardHeader>
                  <CardTitle className="text-blue-300">{agent2.agent_name.split(' - ')[1]}</CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div>
                    <h4 className="text-sm font-semibold text-green-400 mb-2 flex items-center gap-2">
                      <CheckCircle2 className="w-4 h-4" /> Forces
                    </h4>
                    <ul className="space-y-1">
                      {agent2.strengths.map((s, i) => (
                        <li key={i} className="text-sm text-slate-300 pl-4">• {s}</li>
                      ))}
                    </ul>
                  </div>
                  <div>
                    <h4 className="text-sm font-semibold text-red-400 mb-2 flex items-center gap-2">
                      <AlertCircle className="w-4 h-4" /> Faiblesses
                    </h4>
                    <ul className="space-y-1">
                      {agent2.weaknesses.map((w, i) => (
                        <li key={i} className="text-sm text-slate-400 pl-4">• {w}</li>
                      ))}
                    </ul>
                  </div>
                </CardContent>
              </Card>
            </div>

            {/* Graphique Radar */}
            <Card className="bg-slate-900/80 border-slate-700 backdrop-blur">
              <CardHeader>
                <CardTitle className="text-white">📊 Performance Comparative</CardTitle>
              </CardHeader>
              <CardContent>
                <ResponsiveContainer width="100%" height={400}>
                  <RadarChart data={radarData}>
                    <PolarGrid stroke="#334155" />
                    <PolarAngleAxis dataKey="metric" stroke="#94a3b8" />
                    <PolarRadiusAxis stroke="#64748b" />
                    <Radar name={agent1.agent_name} dataKey={agent1.agent_name} stroke="#8b5cf6" fill="#8b5cf6" fillOpacity={0.5} />
                    <Radar name={agent2.agent_name} dataKey={agent2.agent_name} stroke="#3b82f6" fill="#3b82f6" fillOpacity={0.5} />
                    <Legend />
                    <Tooltip contentStyle={{ backgroundColor: '#1e293b', border: '1px solid #334155' }} />
                  </RadarChart>
                </ResponsiveContainer>
              </CardContent>
            </Card>

            {/* Tableaux Paris avec sélecteur */}
            <div className="grid md:grid-cols-2 gap-6">
              {/* Tableau Agent 1 */}
              <Card className="bg-slate-900/80 border-violet-500/30 backdrop-blur">
                <CardHeader>
                  <div className="flex justify-between items-center">
                    <CardTitle className="text-violet-300">📜 Paris - {agent1.agent_name.split(' - ')[1]}</CardTitle>
                    <Select value={betsLimit.toString()} onValueChange={(v) => setBetsLimit(parseInt(v))}>
                      <SelectTrigger className="w-24 bg-slate-800 border-slate-700 text-white">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="10">10</SelectItem>
                        <SelectItem value="50">50</SelectItem>
                        <SelectItem value="100">100</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                </CardHeader>
                <CardContent>
                  <div className="overflow-x-auto">
                    <Table>
                      <TableHeader>
                        <TableRow className="border-slate-800">
                          <TableHead className="text-slate-400">Sport</TableHead>
                          <TableHead className="text-slate-400">Outcome</TableHead>
                          <TableHead className="text-slate-400">Edge</TableHead>
                          <TableHead className="text-slate-400">Résultat</TableHead>
                        </TableRow>
                      </TableHeader>
                      <TableBody>
                        {agent1.recent_bets.slice(0, betsLimit).map((bet, i) => (
                          <TableRow key={i} className="border-slate-800">
                            <TableCell className="text-xs text-slate-400">{bet.sport?.split('_').pop()}</TableCell>
                            <TableCell>
                              <Badge className="bg-violet-500/20 text-violet-300 text-xs">
                                {bet.recommended_outcome}
                              </Badge>
                            </TableCell>
                            <TableCell className="text-green-400 text-sm font-mono">{parseFloat(bet.edge_percent).toFixed(1)}%</TableCell>
                            <TableCell>
                              {bet.actual_result === 'won' && <Badge className="bg-green-500/20 text-green-400 border-green-500/30">✓ Won</Badge>}
                              {bet.actual_result === 'lost' && <Badge className="bg-red-500/20 text-red-400 border-red-500/30">✗ Lost</Badge>}
                              {!bet.actual_result && <Badge className="bg-slate-500/20 text-slate-400">○ Pending</Badge>}
                            </TableCell>
                          </TableRow>
                        ))}
                      </TableBody>
                    </Table>
                  </div>
                </CardContent>
              </Card>

              {/* Tableau Agent 2 */}
              <Card className="bg-slate-900/80 border-blue-500/30 backdrop-blur">
                <CardHeader>
                  <CardTitle className="text-blue-300">📜 Paris - {agent2.agent_name.split(' - ')[1]}</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="overflow-x-auto">
                    <Table>
                      <TableHeader>
                        <TableRow className="border-slate-800">
                          <TableHead className="text-slate-400">Sport</TableHead>
                          <TableHead className="text-slate-400">Outcome</TableHead>
                          <TableHead className="text-slate-400">Edge</TableHead>
                          <TableHead className="text-slate-400">Résultat</TableHead>
                        </TableRow>
                      </TableHeader>
                      <TableBody>
                        {agent2.recent_bets.slice(0, betsLimit).map((bet, i) => (
                          <TableRow key={i} className="border-slate-800">
                            <TableCell className="text-xs text-slate-400">{bet.sport?.split('_').pop()}</TableCell>
                            <TableCell>
                              <Badge className="bg-blue-500/20 text-blue-300 text-xs">
                                {bet.recommended_outcome}
                              </Badge>
                            </TableCell>
                            <TableCell className="text-green-400 text-sm font-mono">{parseFloat(bet.edge_percent).toFixed(1)}%</TableCell>
                            <TableCell>
                              {bet.actual_result === 'won' && <Badge className="bg-green-500/20 text-green-400 border-green-500/30">✓ Won</Badge>}
                              {bet.actual_result === 'lost' && <Badge className="bg-red-500/20 text-red-400 border-red-500/30">✗ Lost</Badge>}
                              {!bet.actual_result && <Badge className="bg-slate-500/20 text-slate-400">○ Pending</Badge>}
                            </TableCell>
                          </TableRow>
                        ))}
                      </TableBody>
                    </Table>
                  </div>
                </CardContent>
              </Card>
            </div>
          </>
        )}
      </div>
    </div>
  )
}

