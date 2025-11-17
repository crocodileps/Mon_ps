'use client'

import { MatchAnalysisModal } from '@/components/agents/MatchAnalysisModal';
import { useMemo, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
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

interface Opportunity {
  id: string;
  match_id: string;
  home_team: string;
  away_team: string;
  sport: string;
  commence_time: string;
  outcome: string;
  best_odds: number;
  bookmaker_best: string;
  edge_pct: number;
}

const edgeBadgeVariant = (edge: number) => {
  if (edge > 15) return 'bg-green-500/20 text-green-400'
  if (edge >= 10) return 'bg-yellow-500/20 text-yellow-400'
  return 'bg-slate-500/20 text-slate-400'
}

export default function OpportunitiesPage() {
  const [sportFilter, setSportFilter] = useState<string>('all')
  const [bookmakerFilter, setBookmakerFilter] = useState<string>('all')
  const [minEdge, setMinEdge] = useState<number>(10)
  const [selectedMatch, setSelectedMatch] = useState<{id: string, name: string} | null>(null)

  const { data, isLoading, refetch } = useQuery<Opportunity[]>({
    queryKey: ['opportunities'],
    queryFn: getOpportunities,
    refetchInterval: 30000,
    staleTime: 20000,
  })

  const opportunities = data ?? []

  const filteredData = useMemo(() => {
    return opportunities.filter((opp) => {
      if (sportFilter !== 'all' && opp.sport !== sportFilter) return false
      if (bookmakerFilter !== 'all' && opp.bookmaker_best !== bookmakerFilter) return false
      if (opp.edge_pct < minEdge) return false
      return true
    })
  }, [opportunities, sportFilter, bookmakerFilter, minEdge])

  const sports = useMemo(() => {
    const set = new Set(opportunities.map((o) => o.sport))
    return Array.from(set).sort()
  }, [opportunities])

  const bookmakers = useMemo(() => {
    const set = new Set(opportunities.map((o) => o.bookmaker_best))
    return Array.from(set).sort()
  }, [opportunities])

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <div className="p-3 bg-violet-500/20 rounded-xl">
            <Target className="w-8 h-8 text-violet-400" />
          </div>
          <div>
            <h1 className="text-3xl font-bold text-white">Opportunités</h1>
            <p className="text-slate-400">Surveillance temps réel des edges détectés</p>
          </div>
        </div>
        <Button onClick={() => refetch()} variant="outline" className="border-violet-500">
          <RefreshCw className="w-4 h-4 mr-2" />
          Rafraîchir
        </Button>
      </div>

      <Card className="bg-slate-800/50 border-slate-700 p-6">
        <h3 className="text-lg font-semibold mb-4">Filtres</h3>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div>
            <label className="text-sm text-slate-400">SPORT</label>
            <select
              value={sportFilter}
              onChange={(e) => setSportFilter(e.target.value)}
              className="w-full mt-1 bg-slate-700 border-slate-600 rounded p-2 text-white"
            >
              <option value="all">Tous</option>
              {sports.map((s) => (
                <option key={s} value={s}>{s}</option>
              ))}
            </select>
          </div>
<div>
            <label className="text-sm text-slate-400">BOOKMAKER</label>
            <select
              value={bookmakerFilter}
              onChange={(e) => setBookmakerFilter(e.target.value)}
              className="w-full mt-1 bg-slate-700 border-slate-600 rounded p-2 text-white"
            >
              <option value="all">Tous</option>
              {bookmakers.map((b) => (
                <option key={b} value={b}>{b}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="text-sm text-slate-400">EDGE MINIMUM</label>
            <div className="flex items-center gap-3 mt-1">
              <input
                type="range"
                min="0"
                max="50"
                step="0.5"
                value={minEdge}
                onChange={(e) => setMinEdge(parseFloat(e.target.value))}
                className="flex-1"
              />
              <span className="text-violet-400 font-bold">{minEdge.toFixed(1)}%</span>
            </div>
          </div>
        </div>
      </Card>

      <Card className="bg-slate-800/50 border-slate-700">
        <div className="p-6">
          <div className="flex justify-between items-center mb-4">
            <h3 className="text-lg font-semibold">{filteredData.length} opportunités</h3>
            <span className="text-xs text-slate-400">ACTUALISATION AUTOMATIQUE TOUTES LES 30 SECONDES</span>
          </div>

          <Table>
            <TableHeader>
              <TableRow className="border-slate-700">
                <TableHead className="text-slate-400">Match</TableHead>
                <TableHead className="text-slate-400">Sport</TableHead>
                <TableHead className="text-slate-400">Outcome</TableHead>
                <TableHead className="text-slate-400 text-right">Best Odds</TableHead>
                <TableHead className="text-slate-400">Bookmaker</TableHead>
                <TableHead className="text-slate-400 text-right">Edge %</TableHead>
                <TableHead className="text-slate-400 text-right">Action</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {filteredData.map((opp) => (
                <TableRow key={opp.id} className="border-slate-700 hover:bg-slate-800/50">
                  <TableCell>
                    <div>
                      <p className="font-medium text-white">{opp.home_team} vs {opp.away_team}</p>
                      <p className="text-xs text-slate-500">
                        {new Date(opp.commence_time).toLocaleDateString('fr-FR', { day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' })}
                      </p>
                    </div>
                  </TableCell>
                  <TableCell>
                    <Badge variant="secondary" className="bg-slate-700 text-xs">
                      {opp.sport.replace('soccer_', '').replace(/_/g, ' ')}
                    </Badge>
                  </TableCell>
                  <TableCell className="text-slate-300">{opp.outcome}</TableCell>
                  <TableCell className="text-right font-bold text-white">{opp.best_odds.toFixed(2)}</TableCell>
                  <TableCell className="text-slate-300">{opp.bookmaker_best}</TableCell>
                  <TableCell className="text-right">
                    <Badge className={`${edgeBadgeVariant(opp.edge_pct)} font-bold`}>
                      {opp.edge_pct.toFixed(1)}%
                    </Badge>
                  </TableCell>
                  <TableCell className="text-right">
                    <div className="flex gap-2 justify-end">
                      <Button
                        size="sm"
                        variant="outline"
                        className="rounded-full px-3 border-violet-500 text-violet-400 hover:bg-violet-500/20"
                        onClick={() => setSelectedMatch({ id: opp.match_id, name: `${opp.home_team} vs ${opp.away_team}` })}
                      >
                        Analyser
                      </Button>
                      <Button size="sm" className="rounded-full px-4 bg-violet-600 hover:bg-violet-700">
                        Place Bet
                      </Button>
                    </div>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
{isLoading && (
            <div className="flex items-center justify-center py-10 text-slate-400">
              Chargement des opportunités...
            </div>
          )}
          {!isLoading && filteredData.length === 0 && (
            <div className="flex items-center justify-center py-10 text-slate-400">
              Aucune opportunité avec ces filtres.
            </div>
          )}
        </div>
      </Card>

      {/* Modal Analyse Agents */}
      {selectedMatch && (
        <MatchAnalysisModal
          matchId={selectedMatch.id}
          matchName={selectedMatch.name}
          isOpen={!!selectedMatch}
          onClose={() => setSelectedMatch(null)}
        />
      )}
    </div>
  )
}

