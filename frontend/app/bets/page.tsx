'use client'

import { useMemo, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { format } from 'date-fns'
import { fr } from 'date-fns/locale'
import { TrendingUp, Activity, Target, CalendarDays, Filter, RefreshCw } from 'lucide-react'

import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { getBets } from '@/lib/api'
import { mockBets } from '@/lib/mock/bets'
import { queryKeys } from '@/lib/query-keys'
import { cn } from '@/lib/utils'
import type { Bet } from '@/types/api'

type TabFilter = 'all' | 'active' | 'settled' | 'won' | 'lost'

const resultClassNames = (bet: Bet) =>
  cn(
    'rounded-2xl border border-border/60 bg-surface/80 p-5 transition-all duration-300',
    bet.result === 'won' && 'border-success/40 bg-success/10 shadow-lg shadow-success/20',
    bet.result === 'lost' && 'border-danger/40 bg-danger/10 shadow-lg shadow-danger/20',
    bet.result === 'pending' && 'border-warning/40 bg-warning/10 shadow-lg shadow-warning/20',
  )

const betTypeBadge = (betType: Bet['bet_type']) =>
  cn(
    'rounded-full px-3 py-1 text-xs font-semibold uppercase tracking-wide',
    betType === 'tabac'
      ? 'border border-purple-400/40 bg-purple-400/15 text-purple-200'
      : 'border border-green-400/40 bg-green-400/15 text-green-200',
  )

const computeStats = (bets: Bet[]) => {
  const totalBets = bets.length
  const settledBets = bets.filter((bet) => bet.result === 'won' || bet.result === 'lost')
  const wins = settledBets.filter((bet) => bet.result === 'won')
  const totalProfit = settledBets.reduce((acc, bet) => acc + (bet.actual_profit ?? 0), 0)
  const totalStake = settledBets.reduce((acc, bet) => acc + bet.stake, 0)

  const winRate = settledBets.length > 0 ? (wins.length / settledBets.length) * 100 : 0
  const roi = totalStake > 0 ? (totalProfit / totalStake) * 100 : 0

  return {
    totalBets,
    settledBets: settledBets.length,
    winRate,
    totalProfit,
    roi,
  }
}

export default function BetsPage() {
  const [tab, setTab] = useState<TabFilter>('all')
  const [strategyFilter, setStrategyFilter] = useState<'all' | Bet['bet_type']>('all')
  const [bookmakerFilter, setBookmakerFilter] = useState<string>('all')
  const [startDate, setStartDate] = useState<string>('')
  const [endDate, setEndDate] = useState<string>('')

  const { data, isLoading, isRefetching, refetch } = useQuery<Bet[]>({
    queryKey: queryKeys.bets.all,
    queryFn: () => getBets(),
    refetchInterval: 60_000,
    staleTime: 30_000,
    retry: 1,
    initialData: mockBets,
  })

  const bets = data ?? mockBets
  const stats = computeStats(bets)

  const bookmakers = useMemo(() => Array.from(new Set(bets.map((bet) => bet.bookmaker))), [bets])

  const filteredBets = useMemo(() => {
    return bets.filter((bet) => {
      const matchesTab =
        tab === 'all'
          ? true
          : tab === 'active'
            ? bet.result === 'pending'
            : tab === 'settled'
              ? bet.result === 'won' || bet.result === 'lost'
              : bet.result === tab

      const matchesStrategy = strategyFilter === 'all' || bet.bet_type === strategyFilter
      const matchesBookmaker = bookmakerFilter === 'all' || bet.bookmaker === bookmakerFilter

      const createdAt = new Date(bet.created_at)
      const afterStart = startDate ? createdAt >= new Date(startDate) : true
      const beforeEnd = endDate ? createdAt <= new Date(endDate) : true

      return matchesTab && matchesStrategy && matchesBookmaker && afterStart && beforeEnd
    })
  }, [bets, tab, strategyFilter, bookmakerFilter, startDate, endDate])

  return (
    <div className="min-h-screen bg-background p-4 sm:p-6 lg:p-8">
      <div className="mx-auto flex max-w-7xl flex-col gap-6">
        <Card className="border-green-500/20 bg-gradient-to-br from-green-500/5 via-background to-transparent p-6 md:p-8">
          <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
            <div className="flex items-center gap-3">
              <div className="rounded-2xl bg-green-500/15 p-3 text-green-400">
                <TrendingUp className="h-7 w-7" />
              </div>
              <div>
                <h1 className="text-3xl font-bold">Historique des paris</h1>
                <p className="text-sm text-muted-foreground">
                  Suivi détaillé des paris Tabac et Ligne, résultats et performances.
                </p>
              </div>
            </div>
            <Button
              variant="default"
              className="flex items-center gap-2 rounded-full px-5 py-2"
              onClick={() => refetch()}
              disabled={isRefetching}
            >
              <RefreshCw className="h-4 w-4" />
              Rafraîchir
            </Button>
          </div>
        </Card>

        <div className="grid grid-cols-1 gap-6 md:grid-cols-3">
          <Card className="border border-border/60 bg-surface/80 p-6 shadow-lg shadow-primary/10">
            <div className="flex items-center gap-2 text-sm text-muted-foreground">
              <TrendingUp className="h-4 w-4 text-primary" />
              ROI total
            </div>
            <p className="mt-3 text-3xl font-semibold text-primary">{stats.roi.toFixed(2)}%</p>
            <p className="mt-1 text-xs text-muted-foreground">{stats.settledBets} paris réglés</p>
          </Card>
          <Card className="border border-border/60 bg-surface/80 p-6 shadow-lg shadow-success/10">
            <div className="flex items-center gap-2 text-sm text-muted-foreground">
              <Activity className="h-4 w-4 text-success" />
              Win rate
            </div>
            <p className="mt-3 text-3xl font-semibold text-success">{stats.winRate.toFixed(1)}%</p>
            <p className="mt-1 text-xs text-muted-foreground">{stats.totalBets} paris totaux</p>
          </Card>
          <Card className="border border-border/60 bg-surface/80 p-6 shadow-lg shadow-success/10">
            <div className="flex items-center gap-2 text-sm text-muted-foreground">
              <Target className="h-4 w-4 text-success" />
              Profit total
            </div>
            <p
              className={cn(
                'mt-3 text-3xl font-semibold',
                stats.totalProfit >= 0 ? 'text-success' : 'text-danger',
              )}
            >
              {stats.totalProfit >= 0 ? '+' : ''}
              {stats.totalProfit.toFixed(2)} €
            </p>
            <p className="mt-1 text-xs text-muted-foreground">Depuis le début</p>
          </Card>
        </div>

        <Card className="border border-border/60 bg-surface/80 p-6">
          <div className="flex flex-wrap items-center gap-2">
            {(['all', 'active', 'settled', 'won', 'lost'] as TabFilter[]).map((tabKey) => (
              <Button
                key={tabKey}
                variant={tabKey === tab ? 'default' : 'ghost'}
                className={cn(
                  'rounded-full px-4 py-2 text-sm capitalize',
                  tabKey === tab
                    ? 'bg-primary text-primary-foreground shadow-md'
                    : 'border border-border/60 text-text-secondary hover:text-text-primary',
                )}
                onClick={() => setTab(tabKey)}
              >
                {tabKey}
              </Button>
            ))}
          </div>

          <div className="mt-6 grid gap-4 md:grid-cols-2 lg:grid-cols-4">
            <div className="flex flex-col gap-2">
              <label className="text-xs uppercase tracking-wide text-text-muted">Stratégie</label>
              <select
                className="rounded-xl border border-border bg-surface-hover px-3 py-2 text-sm text-text-primary"
                value={strategyFilter}
                onChange={(event) => setStrategyFilter(event.target.value as 'all' | Bet['bet_type'])}
              >
                <option value="all">Toutes</option>
                <option value="tabac">Tabac</option>
                <option value="ligne">Ligne</option>
              </select>
            </div>
            <div className="flex flex-col gap-2">
              <label className="text-xs uppercase tracking-wide text-text-muted">Bookmaker</label>
              <select
                className="rounded-xl border border-border bg-surface-hover px-3 py-2 text-sm text-text-primary"
                value={bookmakerFilter}
                onChange={(event) => setBookmakerFilter(event.target.value)}
              >
                <option value="all">Tous</option>
                {bookmakers.map((bookmaker) => (
                  <option key={bookmaker} value={bookmaker}>
                    {bookmaker}
                  </option>
                ))}
              </select>
            </div>
            <div className="flex flex-col gap-2">
              <label className="flex items-center gap-2 text-xs uppercase tracking-wide text-text-muted">
                <CalendarDays className="h-4 w-4" />
                Date début
              </label>
              <input
                type="date"
                value={startDate}
                onChange={(event) => setStartDate(event.target.value)}
                className="rounded-xl border border-border bg-surface-hover px-3 py-2 text-sm text-text-primary"
              />
            </div>
            <div className="flex flex-col gap-2">
              <label className="flex items-center gap-2 text-xs uppercase tracking-wide text-text-muted">
                <Filter className="h-4 w-4" />
                Date fin
              </label>
              <input
                type="date"
                value={endDate}
                onChange={(event) => setEndDate(event.target.value)}
                className="rounded-xl border border-border bg-surface-hover px-3 py-2 text-sm text-text-primary"
              />
            </div>
          </div>
        </Card>

        <Card className="border border-border/60 bg-surface/80 p-6">
          {isLoading ? (
            <div className="flex items-center justify-center py-12 text-text-muted">
              Chargement des paris…
            </div>
          ) : filteredBets.length === 0 ? (
            <div className="flex items-center justify-center py-12 text-text-muted">
              Aucun pari ne correspond à ces filtres.
            </div>
          ) : (
            <div className="grid gap-4">
              {filteredBets.map((bet) => (
                <div key={bet.id} className={resultClassNames(bet)}>
                  <div className="flex flex-col gap-4 md:flex-row md:items-start md:justify-between">
                    <div className="space-y-3">
                      <div className="flex flex-wrap items-center gap-2">
                        <Badge className={betTypeBadge(bet.bet_type)}>{bet.bet_type}</Badge>
                        <Badge variant="secondary" className="rounded-full bg-surface-hover px-3 py-1 text-xs">
                          {bet.bookmaker}
                        </Badge>
                        <span className="text-xs text-text-muted">
                          {format(new Date(bet.created_at), 'dd MMM yyyy · HH:mm', { locale: fr })}
                        </span>
                      </div>
                      <div>
                        <h3 className="text-lg font-semibold text-text-primary">{bet.match_id}</h3>
                        <p className="text-sm text-text-secondary">
                          {bet.outcome} @{' '}
                          <span className="number text-primary">{bet.odds_value.toFixed(2)}</span>
                        </p>
                      </div>
                    </div>
                    <div className="space-y-3 text-right">
                      <div>
                        <p className="text-xs uppercase tracking-wide text-text-muted">Stake</p>
                        <p className="number text-lg text-text-primary">{bet.stake.toFixed(2)} €</p>
                      </div>
                      {bet.actual_profit !== null && (
                        <p
                          className={cn(
                            'number text-lg font-semibold',
                            bet.actual_profit > 0 ? 'text-success' : 'text-danger',
                          )}
                        >
                          {bet.actual_profit > 0 ? '+' : ''}
                          {bet.actual_profit.toFixed(2)} €
                        </p>
                      )}
                      <p className="text-xs text-text-muted">
                        CLV {bet.clv !== null ? bet.clv.toFixed(2) : '-'}
                      </p>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </Card>
      </div>
    </div>
  )
}

