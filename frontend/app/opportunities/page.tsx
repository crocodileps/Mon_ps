'use client'

import { useMemo, useState } from 'react'
import { formatNumber } from "@/lib/format";
import { useQuery } from '@tanstack/react-query'
import { motion } from 'framer-motion'
import { RefreshCw, Target } from 'lucide-react'

import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import { getOpportunities } from '@/lib/api'
import { queryKeys } from '@/lib/query-keys'
import type { Opportunity } from '@/types/api'

type SortKey = 'match' | 'sport' | 'best_odds' | 'edge_pct'
type SortDirection = 'asc' | 'desc'

const edgeBadgeVariant = (edge: number) => {
  if (edge > 15) return 'bg-success/15 text-success'
  if (edge >= 10) return 'bg-warning/15 text-warning'
  return 'bg-surface-hover text-text-secondary'
}

export default function OpportunitiesPage() {
  const [sportFilter, setSportFilter] = useState<string>('all')
  const [bookmakerFilter, setBookmakerFilter] = useState<string>('all')
  const [minEdge, setMinEdge] = useState<number>(10)
  const [sortKey, setSortKey] = useState<SortKey>('edge_pct')
  const [sortDirection, setSortDirection] = useState<SortDirection>('desc')

  const { data, isLoading, isRefetching, refetch } = useQuery<Opportunity[]>({
    queryKey: queryKeys.opportunities.all,
    queryFn: getOpportunities,
    refetchInterval: 30_000,
    staleTime: 20_000,
    retry: 1,
  })

  const opportunities = data ?? []

  const filters = useMemo(() => {
    const sports = new Set<string>()
    const bookmakers = new Set<string>()

    opportunities.forEach((opp) => {
      sports.add(opp.sport)
      bookmakers.add(opp.bookmaker_best)
    })

    return {
      sports: Array.from(sports),
      bookmakers: Array.from(bookmakers),
    }
  }, [opportunities])

  const filteredData = useMemo(() => {
    const filtered = opportunities.filter((opp) => {
      const edgeOk = opp.edge_pct >= minEdge
      const sportOk = sportFilter === 'all' || opp.sport === sportFilter
      const bookmakerOk = bookmakerFilter === 'all' || opp.bookmaker_best === bookmakerFilter
      return edgeOk && sportOk && bookmakerOk
    })

    const sorted = [...filtered].sort((a, b) => {
      const direction = sortDirection === 'asc' ? 1 : -1

      switch (sortKey) {
        case 'match':
          return direction * `${a.home_team} ${a.away_team}`.localeCompare(`${b.home_team} ${b.away_team}`)
        case 'sport':
          return direction * a.sport.localeCompare(b.sport)
        case 'best_odds':
          return direction * (a.best_odds - b.best_odds)
        case 'edge_pct':
        default:
          return direction * (a.edge_pct - b.edge_pct)
      }
    })

    return sorted
  }, [opportunities, sportFilter, bookmakerFilter, minEdge, sortKey, sortDirection])

  const handleSort = (key: SortKey) => {
    if (sortKey === key) {
      setSortDirection((prev) => (prev === 'asc' ? 'desc' : 'asc'))
      return
    }
    setSortKey(key)
    setSortDirection('desc')
  }

  return (
    <div className="min-h-screen bg-background p-4 sm:p-6 lg:p-8">
      <div className="mx-auto flex max-w-7xl flex-col gap-6">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.4 }}
        >
          <Card className="border-purple-500/20 bg-gradient-to-br from-purple-500/5 via-background to-transparent p-6 md:p-8">
            <div className="flex flex-col gap-6 md:flex-row md:items-center md:justify-between">
              <div className="flex items-center gap-3">
                <div className="rounded-2xl bg-purple-500/15 p-3 text-purple-400">
                  <Target className="h-7 w-7" />
                </div>
                <div>
                  <h1 className="text-3xl font-bold">Opportunités</h1>
                  <p className="text-sm text-muted-foreground">
                    Surveillance temps réel des edges détectés sur les marchés principaux.
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
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.4, delay: 0.1 }}
        >
          <Card className="border-border/60 bg-surface/80">
            <div className="border-b border-border/70 px-6 py-5">
              <h2 className="text-lg font-semibold text-text-primary">Filtres</h2>
            </div>
            <div className="grid gap-4 px-6 py-6 md:grid-cols-2 lg:grid-cols-4">
              <div className="flex flex-col gap-2">
                <label className="text-xs uppercase tracking-wide text-text-muted">Sport</label>
                <select
                  className="rounded-xl border border-border bg-surface-hover px-3 py-2 text-sm text-text-primary"
                  value={sportFilter}
                  onChange={(event) => setSportFilter(event.target.value)}
                >
                  <option value="all">Tous</option>
                  {filters.sports.map((sport) => (
                    <option key={sport} value={sport}>
                      {sport}
                    </option>
                  ))}
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
                  {filters.bookmakers.map((bookmaker) => (
                    <option key={bookmaker} value={bookmaker}>
                      {bookmaker}
                    </option>
                  ))}
                </select>
              </div>
              <div className="flex flex-col gap-2 md:col-span-2 lg:col-span-1">
                <label className="text-xs uppercase tracking-wide text-text-muted">Edge minimum</label>
                <div className="flex items-center gap-4">
                  <input
                    type="range"
                    min={0}
                    max={25}
                    step={0.5}
                    value={minEdge}
                    onChange={(event) => setMinEdge(Number(event.target.value))}
                    className="flex-1 accent-primary"
                  />
                  <span className="number text-primary">{formatNumber(minEdge, 1)}%</span>
                </div>
              </div>
            </div>
          </Card>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.4, delay: 0.2 }}
        >
          <Card className="border-border/60 bg-surface/80">
            <div className="flex flex-col gap-2 border-b border-border/70 px-6 py-5 sm:flex-row sm:items-center sm:justify-between">
              <h2 className="text-lg font-semibold text-text-primary">{filteredData.length} opportunités</h2>
              <p className="text-xs uppercase tracking-wide text-text-muted">
                Actualisation automatique toutes les 30 secondes
              </p>
            </div>
            <div className="overflow-hidden px-2 py-4 sm:px-4">
              <div className="w-full overflow-x-auto rounded-2xl border border-border/50">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead className="cursor-pointer" onClick={() => handleSort('match')}>
                        Match
                      </TableHead>
                      <TableHead className="cursor-pointer" onClick={() => handleSort('sport')}>
                        Sport
                      </TableHead>
                      <TableHead>Outcome</TableHead>
                      <TableHead className="cursor-pointer text-right" onClick={() => handleSort('best_odds')}>
                        Best Odds
                      </TableHead>
                      <TableHead>Bookmaker</TableHead>
                      <TableHead className="cursor-pointer text-right" onClick={() => handleSort('edge_pct')}>
                        Edge %
                      </TableHead>
                      <TableHead className="text-right">Action</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {filteredData.map((opp) => (
                      <TableRow key={opp.id} className="hover:bg-surface-hover/60">
                        <TableCell>
                          <div className="flex flex-col">
                            <span className="text-sm font-semibold text-text-primary">
                              {opp.home_team} vs {opp.away_team}
                            </span>
                            <span className="text-xs text-text-muted">
                              {new Date(opp.commence_time).toLocaleString('fr-FR', {
                                day: '2-digit',
                                month: 'short',
                                hour: '2-digit',
                                minute: '2-digit',
                              })}
                            </span>
                          </div>
                        </TableCell>
                        <TableCell>
                          <Badge variant="secondary" className="rounded-full bg-surface-hover px-3 py-1 text-xs">
                            {opp.sport}
                          </Badge>
                        </TableCell>
                        <TableCell className="text-sm text-text-secondary">{opp.outcome}</TableCell>
                        <TableCell className="number text-right text-primary">{formatNumber(opp.best_odds, 2)}</TableCell>
                        <TableCell className="text-sm text-text-secondary">{opp.bookmaker_best}</TableCell>
                        <TableCell className="text-right">
                          <Badge
                            variant="secondary"
                            className={`rounded-full px-3 py-1 text-sm font-semibold ${edgeBadgeVariant(opp.edge_pct)}`}
                          >
                            {formatNumber(opp.edge_pct, 1)}%
                          </Badge>
                        </TableCell>
                        <TableCell className="text-right">
                          <Button size="sm" className="rounded-full px-4">
                            Place Bet
                          </Button>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
                {isLoading && (
                  <div className="flex items-center justify-center py-10 text-text-muted">
                    Chargement des opportunités…
                  </div>
                )}
                {!isLoading && filteredData.length === 0 && (
                  <div className="flex items-center justify-center py-10 text-text-muted">
                    Aucune opportunité avec ces filtres.
                  </div>
                )}
              </div>
            </div>
          </Card>
        </motion.div>
      </div>
    </div>
  )
}

