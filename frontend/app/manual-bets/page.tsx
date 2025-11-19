'use client'

import { useState } from 'react'
import { useBets, useBetsStats } from '@/hooks/use-bets'
import { LayoutWrapper } from '@/app/layout-wrapper'
import { Card } from '@/components/ui/card'
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
  TrendingUp,
  TrendingDown,
  DollarSign,
  Target,
  Trophy,
  RefreshCw,
  CheckCircle,
  XCircle,
  Clock
} from 'lucide-react'

export default function PnLPage() {
  const [statusFilter, setStatusFilter] = useState<string>('all')
  const { data: statsData, refetch: refetchStats } = useBetsStats()
  const { data: betsData, refetch: refetchBets, isLoading } = useBets(50, statusFilter === 'all' ? undefined : statusFilter)

  const stats = statsData || {
    total_bets: 0,
    wins: 0,
    losses: 0,
    pending: 0,
    total_staked: 0,
    total_profit: 0,
    roi_pct: 0,
    win_rate: 0
  }

  const bets = betsData?.bets || []

  const handleRefresh = () => {
    refetchStats()
    refetchBets()
  }

  return (
    <LayoutWrapper>
      <div className="space-y-6 pb-10">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold text-white tracking-tight">P&L Dashboard</h1>
            <p className="text-slate-400">Suivi en temps réel de vos performances</p>
          </div>
          <Button onClick={handleRefresh} variant="outline">
            <RefreshCw className="w-4 h-4 mr-2" />
            Rafraîchir
          </Button>
        </div>

        {/* Stats Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          <Card className="bg-gradient-to-br from-blue-500/10 to-blue-600/5 border-blue-500/20 p-6">
            <div className="flex items-center justify-between mb-4">
              <DollarSign className="w-8 h-8 text-blue-400" />
              <Badge variant="outline" className="border-blue-500/30 text-blue-400">
                {stats.total_bets} paris
              </Badge>
            </div>
            <p className="text-sm text-slate-400 mb-1">Mise Totale</p>
            <p className="text-3xl font-bold text-white">{stats.total_staked.toFixed(2)}€</p>
          </Card>

          <Card className={`bg-gradient-to-br ${stats.total_profit >= 0 ? 'from-green-500/10 to-green-600/5 border-green-500/20' : 'from-red-500/10 to-red-600/5 border-red-500/20'} p-6`}>
            <div className="flex items-center justify-between mb-4">
              {stats.total_profit >= 0 ? (
                <TrendingUp className="w-8 h-8 text-green-400" />
              ) : (
                <TrendingDown className="w-8 h-8 text-red-400" />
              )}
              <Badge variant="outline" className={stats.total_profit >= 0 ? 'border-green-500/30 text-green-400' : 'border-red-500/30 text-red-400'}>
                {stats.roi_pct.toFixed(1)}% ROI
              </Badge>
            </div>
            <p className="text-sm text-slate-400 mb-1">Profit Net</p>
            <p className={`text-3xl font-bold ${stats.total_profit >= 0 ? 'text-green-400' : 'text-red-400'}`}>
              {stats.total_profit >= 0 ? '+' : ''}{stats.total_profit.toFixed(2)}€
            </p>
          </Card>

          <Card className="bg-gradient-to-br from-violet-500/10 to-violet-600/5 border-violet-500/20 p-6">
            <div className="flex items-center justify-between mb-4">
              <Trophy className="w-8 h-8 text-violet-400" />
              <Badge variant="outline" className="border-violet-500/30 text-violet-400">
                {stats.wins}W / {stats.losses}L
              </Badge>
            </div>
            <p className="text-sm text-slate-400 mb-1">Taux de Réussite</p>
            <p className="text-3xl font-bold text-white">{stats.win_rate.toFixed(1)}%</p>
          </Card>

          <Card className="bg-gradient-to-br from-orange-500/10 to-orange-600/5 border-orange-500/20 p-6">
            <div className="flex items-center justify-between mb-4">
              <Clock className="w-8 h-8 text-orange-400" />
              <Badge variant="outline" className="border-orange-500/30 text-orange-400">
                En attente
              </Badge>
            </div>
            <p className="text-sm text-slate-400 mb-1">Paris Actifs</p>
            <p className="text-3xl font-bold text-white">{stats.pending}</p>
          </Card>
        </div>

        {/* Filters */}
        <Card className="bg-slate-900/50 border-slate-800 p-4">
          <div className="flex items-center gap-3">
            <span className="text-sm text-slate-400 font-medium">Statut :</span>
            {['all', 'pending', 'won', 'lost'].map((status) => (
              <Button
                key={status}
                size="sm"
                variant={statusFilter === status ? 'default' : 'ghost'}
                onClick={() => setStatusFilter(status)}
                className={statusFilter === status ? 'bg-violet-600' : ''}
              >
                {status === 'all' ? 'Tous' : status === 'pending' ? 'En attente' : status === 'won' ? 'Gagnés' : 'Perdus'}
              </Button>
            ))}
          </div>
        </Card>

        {/* Table */}
        <Card className="bg-slate-900/50 border-slate-800 overflow-hidden">
          <div className="p-6 border-b border-slate-800">
            <h3 className="text-lg font-semibold text-white">Historique des Paris</h3>
          </div>

          <Table>
            <TableHeader className="bg-slate-950/50">
              <TableRow className="border-slate-800 hover:bg-transparent">
                <TableHead className="text-slate-400">Match</TableHead>
                <TableHead className="text-slate-400">Sélection</TableHead>
                <TableHead className="text-slate-400 text-right">Cote</TableHead>
                <TableHead className="text-slate-400 text-right">Mise</TableHead>
                <TableHead className="text-slate-400">Bookmaker</TableHead>
                <TableHead className="text-slate-400 text-right">Edge</TableHead>
                <TableHead className="text-slate-400 text-right">CLV</TableHead>
                <TableHead className="text-slate-400">Patron</TableHead>
                <TableHead className="text-slate-400">Statut</TableHead>
                <TableHead className="text-slate-400 text-right">P&L</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {isLoading ? (
                <TableRow>
                  <TableCell colSpan={9} className="h-32 text-center text-slate-400">
                    Chargement...
                  </TableCell>
                </TableRow>
              ) : bets.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={9} className="h-32 text-center text-slate-400">
                    Aucun pari
                  </TableCell>
                </TableRow>
              ) : (
                bets.map((bet: any) => (
                  <TableRow key={bet.id} className="border-slate-800 hover:bg-slate-800/40">
                    <TableCell>
                      <div>
                        <p className="font-bold text-white text-sm">{bet.home_team} vs {bet.away_team}</p>
                        <p className="text-xs text-slate-500">
                          {new Date(bet.commence_time).toLocaleDateString('fr-FR')}
                        </p>
                      </div>
                    </TableCell>
                    <TableCell>
                      <Badge className="bg-blue-500/10 text-blue-400 capitalize">
                        {bet.outcome}
                      </Badge>
                    </TableCell>
                    <TableCell className="text-right font-mono font-bold text-white">
                      {bet.odds.toFixed(2)}
                    </TableCell>
                    <TableCell className="text-right font-medium text-white">
                      {bet.stake.toFixed(2)}€
                    </TableCell>
                    <TableCell className="text-slate-300 text-sm">
                      {bet.bookmaker}
                    </TableCell>
                    <TableCell className="text-right">
                      {bet.edge_pct ? (
                    <TableCell className="text-right">
                      {bet.clv_percent !== null ? (
                        <Badge className={bet.clv_percent >= 0 ? 'bg-green-500/20 text-green-400' : 'bg-red-500/20 text-red-400'}>
                          {bet.clv_percent >= 0 ? '+' : ''}{bet.clv_percent.toFixed(2)}%
                        </Badge>
                      ) : <span className="text-slate-600">--</span>}
                    </TableCell>
                        <Badge className="bg-green-500/20 text-green-400">
                    <TableCell className="text-right">
                      {bet.clv_percent !== null ? (
                        <Badge className={bet.clv_percent >= 0 ? 'bg-green-500/20 text-green-400' : 'bg-red-500/20 text-red-400'}>
                          {bet.clv_percent >= 0 ? '+' : ''}{bet.clv_percent.toFixed(2)}%
                        </Badge>
                      ) : <span className="text-slate-600">--</span>}
                    </TableCell>
                          {bet.edge_pct.toFixed(1)}%
                    <TableCell className="text-right">
                      {bet.clv_percent !== null ? (
                        <Badge className={bet.clv_percent >= 0 ? 'bg-green-500/20 text-green-400' : 'bg-red-500/20 text-red-400'}>
                          {bet.clv_percent >= 0 ? '+' : ''}{bet.clv_percent.toFixed(2)}%
                        </Badge>
                      ) : <span className="text-slate-600">--</span>}
                    </TableCell>
                        </Badge>
                      ) : <span className="text-slate-600">--</span>}
                    </TableCell>
                    <TableCell>
                      {bet.patron_score && (
                        <Badge className={bet.patron_score === 'ANALYSER' ? 'bg-green-500/20 text-green-400' : 'bg-red-500/20 text-red-400'}>
                          {bet.patron_score}
                        </Badge>
                      )}
                    </TableCell>
                    <TableCell>
                      {bet.status === 'pending' && (
                        <Badge className="bg-orange-500/20 text-orange-400">
                          <Clock className="w-3 h-3 mr-1" />
                          En attente
                        </Badge>
                      )}
                      {bet.status === 'won' && (
                        <Badge className="bg-green-500/20 text-green-400">
                          <CheckCircle className="w-3 h-3 mr-1" />
                          Gagné
                        </Badge>
                      )}
                      {bet.status === 'lost' && (
                        <Badge className="bg-red-500/20 text-red-400">
                          <XCircle className="w-3 h-3 mr-1" />
                          Perdu
                        </Badge>
                      )}
                    </TableCell>
                    <TableCell className="text-right">
                      {bet.profit !== null ? (
                        <span className={`font-bold ${bet.profit >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                          {bet.profit >= 0 ? '+' : ''}{bet.profit.toFixed(2)}€
                        </span>
                      ) : <span className="text-slate-600">--</span>}
                    </TableCell>
                  </TableRow>
                ))
              )}
            </TableBody>
          </Table>
        </Card>
      </div>
    </LayoutWrapper>
  )
}
