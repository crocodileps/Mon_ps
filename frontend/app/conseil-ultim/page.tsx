'use client'

import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { DashboardLayout } from '@/components/dashboard-layout'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { RefreshCw, TrendingUp, Target, Clock, CheckCircle, XCircle } from 'lucide-react'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://91.98.131.218:8001'

interface HistoryItem {
  id: number
  match_id: string
  home_team: string
  away_team: string
  sport: string
  recommended_outcome: string
  recommended_label: string
  score: number
  edge_reel: number
  notre_proba: number
  risque: string
  conseil: string
  actual_outcome: string | null
  is_win: boolean | null
  status: string
  created_at: string
  resolved_at: string | null
}

interface Performance {
  global: {
    total_recommendations: number
    pending: number
    resolved: number
    wins: number
    losses: number
    win_rate: number | null
    avg_score: number | null
    avg_edge: number | null
  }
  by_score_range: Array<{
    score_range: string
    total: number
    wins: number
    win_rate: number | null
  }>
  by_conseil: Array<{
    conseil: string
    total: number
    wins: number
    win_rate: number | null
  }>
}

function ConseilUltimContent() {
  const [statusFilter, setStatusFilter] = useState<string>('all')
  const [limit, setLimit] = useState<number>(50)

  const { data: historyData, isLoading: historyLoading, refetch: refetchHistory } = useQuery({
    queryKey: ['conseil-history', statusFilter, limit],
    queryFn: async () => {
      const params = new URLSearchParams()
      if (statusFilter !== 'all') params.append('status', statusFilter)
      params.append('limit', limit.toString())
      const res = await fetch(`${API_URL}/agents/conseil-ultim/history?${params}`)
      return res.json()
    }
  })

  const { data: perfData, refetch: refetchPerf } = useQuery({
    queryKey: ['conseil-performance'],
    queryFn: async () => {
      const res = await fetch(`${API_URL}/agents/conseil-ultim/performance`)
      return res.json() as Promise<Performance>
    }
  })

  const handleResolve = async () => {
    const res = await fetch(`${API_URL}/agents/conseil-ultim/resolve`, { method: 'POST' })
    const data = await res.json()
    alert(`${data.resolved} recommandations résolues!\nWins: ${data.wins} | Losses: ${data.losses}`)
    refetchHistory()
    refetchPerf()
  }

  const getStatusBadge = (status: string, isWin: boolean | null) => {
    if (status === 'pending') {
      return <Badge className="bg-yellow-500/20 text-yellow-400 border-yellow-500/30">⏳ En attente</Badge>
    }
    if (isWin === true) {
      return <Badge className="bg-green-500/20 text-green-400 border-green-500/30">✅ Gagné</Badge>
    }
    return <Badge className="bg-red-500/20 text-red-400 border-red-500/30">❌ Perdu</Badge>
  }

  const getScoreColor = (score: number) => {
    if (score >= 75) return 'text-green-400'
    if (score >= 60) return 'text-blue-400'
    if (score >= 50) return 'text-yellow-400'
    return 'text-red-400'
  }

  const total = perfData?.global?.total_recommendations ?? 0
  const pending = perfData?.global?.pending ?? 0
  const wins = perfData?.global?.wins ?? 0
  const losses = perfData?.global?.losses ?? 0
  const winRate = perfData?.global?.win_rate
  const avgScore = perfData?.global?.avg_score
  const byScoreRange = perfData?.by_score_range ?? []

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-white flex items-center gap-3">
            🎯 Agent Conseil Ultim 2.0
            <Badge className="bg-purple-500/20 text-purple-400 border-purple-500/30">Historique</Badge>
          </h1>
          <p className="text-slate-400 mt-1">Tracking automatique des recommandations</p>
        </div>
        <div className="flex gap-2">
          <Button onClick={handleResolve} className="bg-blue-600 hover:bg-blue-700">
            <CheckCircle className="w-4 h-4 mr-2" />
            Résoudre Matchs
          </Button>
          <Button onClick={() => { refetchHistory(); refetchPerf(); }} variant="outline" className="border-slate-700">
            <RefreshCw className="w-4 h-4 mr-2" />
            Rafraîchir
          </Button>
        </div>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-4">
        <Card className="bg-slate-900/50 border-slate-800">
          <CardContent className="p-4">
            <div className="flex items-center gap-2 text-slate-400 text-sm"><Target className="w-4 h-4" />Total</div>
            <p className="text-2xl font-bold text-white mt-1">{total}</p>
          </CardContent>
        </Card>
        <Card className="bg-slate-900/50 border-slate-800">
          <CardContent className="p-4">
            <div className="flex items-center gap-2 text-yellow-400 text-sm"><Clock className="w-4 h-4" />En attente</div>
            <p className="text-2xl font-bold text-yellow-400 mt-1">{pending}</p>
          </CardContent>
        </Card>
        <Card className="bg-slate-900/50 border-slate-800">
          <CardContent className="p-4">
            <div className="flex items-center gap-2 text-green-400 text-sm"><CheckCircle className="w-4 h-4" />Gagnés</div>
            <p className="text-2xl font-bold text-green-400 mt-1">{wins}</p>
          </CardContent>
        </Card>
        <Card className="bg-slate-900/50 border-slate-800">
          <CardContent className="p-4">
            <div className="flex items-center gap-2 text-red-400 text-sm"><XCircle className="w-4 h-4" />Perdus</div>
            <p className="text-2xl font-bold text-red-400 mt-1">{losses}</p>
          </CardContent>
        </Card>
        <Card className="bg-slate-900/50 border-slate-800">
          <CardContent className="p-4">
            <div className="flex items-center gap-2 text-purple-400 text-sm"><TrendingUp className="w-4 h-4" />Win Rate</div>
            <p className="text-2xl font-bold text-purple-400 mt-1">{winRate !== null && winRate !== undefined ? `${winRate}%` : '—'}</p>
          </CardContent>
        </Card>
        <Card className="bg-slate-900/50 border-slate-800">
          <CardContent className="p-4">
            <div className="flex items-center gap-2 text-blue-400 text-sm"><Target className="w-4 h-4" />Score Moy.</div>
            <p className="text-2xl font-bold text-blue-400 mt-1">{avgScore ? avgScore.toFixed(1) : '—'}</p>
          </CardContent>
        </Card>
      </div>

      {byScoreRange.length > 0 && (
        <Card className="bg-slate-900/50 border-slate-800">
          <CardHeader className="pb-2">
            <CardTitle className="text-white text-lg">Performance par Score</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              {byScoreRange.map((range) => (
                <div key={range.score_range} className="bg-slate-800/50 rounded-lg p-3">
                  <p className="text-slate-400 text-sm">{range.score_range.replace('_', ' ')}</p>
                  <p className="text-white font-bold">{range.total} reco</p>
                  <p className={range.win_rate !== null ? 'text-green-400' : 'text-slate-500'}>
                    {range.win_rate !== null ? `${range.win_rate}% WR` : 'Non résolu'}
                  </p>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      <div className="flex gap-4 items-center">
        <Select value={statusFilter} onValueChange={setStatusFilter}>
          <SelectTrigger className="w-40 bg-slate-900 border-slate-700">
            <SelectValue placeholder="Status" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">Tous</SelectItem>
            <SelectItem value="pending">En attente</SelectItem>
            <SelectItem value="resolved">Résolus</SelectItem>
          </SelectContent>
        </Select>
        <Select value={limit.toString()} onValueChange={(v) => setLimit(parseInt(v))}>
          <SelectTrigger className="w-32 bg-slate-900 border-slate-700">
            <SelectValue placeholder="Limite" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="20">20</SelectItem>
            <SelectItem value="50">50</SelectItem>
            <SelectItem value="100">100</SelectItem>
          </SelectContent>
        </Select>
        <span className="text-slate-400 text-sm">{historyData?.count ?? 0} résultats</span>
      </div>

      <Card className="bg-slate-900/50 border-slate-800">
        <CardContent className="p-0">
          <Table>
            <TableHeader>
              <TableRow className="border-slate-800 hover:bg-slate-800/50">
                <TableHead className="text-slate-400">Match</TableHead>
                <TableHead className="text-slate-400">Recommandation</TableHead>
                <TableHead className="text-slate-400 text-center">Score</TableHead>
                <TableHead className="text-slate-400 text-center">Edge</TableHead>
                <TableHead className="text-slate-400">Conseil</TableHead>
                <TableHead className="text-slate-400">Résultat</TableHead>
                <TableHead className="text-slate-400">Status</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {historyLoading ? (
                <TableRow>
                  <TableCell colSpan={7} className="text-center text-slate-400 py-8">Chargement...</TableCell>
                </TableRow>
              ) : !historyData?.history?.length ? (
                <TableRow>
                  <TableCell colSpan={7} className="text-center text-slate-400 py-8">Aucune recommandation</TableCell>
                </TableRow>
              ) : (
                historyData.history.map((item: HistoryItem) => (
                  <TableRow key={item.id} className="border-slate-800 hover:bg-slate-800/30">
                    <TableCell>
                      <div className="text-white font-medium">{item.home_team}</div>
                      <div className="text-slate-400 text-sm">vs {item.away_team}</div>
                    </TableCell>
                    <TableCell>
                      <Badge className="bg-slate-700 text-white border-slate-600">{item.recommended_label}</Badge>
                    </TableCell>
                    <TableCell className="text-center">
                      <span className={`font-bold ${getScoreColor(item.score)}`}>{item.score}</span>
                    </TableCell>
                    <TableCell className="text-center">
                      <span className={item.edge_reel >= 0 ? 'text-green-400' : 'text-red-400'}>
                        {item.edge_reel >= 0 ? '+' : ''}{item.edge_reel}%
                      </span>
                    </TableCell>
                    <TableCell>
                      <Badge className={
                        item.conseil === 'RECOMMANDÉ' ? 'bg-green-500/20 text-green-400 border-green-500/30' :
                        item.conseil === 'À CONSIDÉRER' ? 'bg-blue-500/20 text-blue-400 border-blue-500/30' :
                        'bg-orange-500/20 text-orange-400 border-orange-500/30'
                      }>{item.conseil}</Badge>
                    </TableCell>
                    <TableCell>
                      {item.actual_outcome ? <span className="text-white">{item.actual_outcome}</span> : <span className="text-slate-500">—</span>}
                    </TableCell>
                    <TableCell>{getStatusBadge(item.status, item.is_win)}</TableCell>
                  </TableRow>
                ))
              )}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </div>
  )
}

export default function ConseilUltimPage() {
  return (
    <DashboardLayout>
      <ConseilUltimContent />
    </DashboardLayout>
  )
}
