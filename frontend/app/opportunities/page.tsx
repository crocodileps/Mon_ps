'use client'

import { MatchAnalysisModal } from '@/components/agents/MatchAnalysisModal'
import { useMemo, useState } from 'react'
import { usePatronScores } from '@/hooks/use-patron-scores'
import { useQuery } from '@tanstack/react-query'
import { RefreshCw, Target, FilterX } from 'lucide-react'
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

// Interface stricte pour TypeScript
interface Opportunity {
  id: string
  match_id: string
  home_team: string
  away_team: string
  sport: string
  commence_time: string
  outcome: string
  best_odds: number
  bookmaker_best: string
  edge_pct: number
}

const edgeBadgeVariant = (edge: number) => {
  if (edge > 15) return 'bg-green-500/20 text-green-400'
  if (edge >= 10) return 'bg-yellow-500/20 text-yellow-400'
  return 'bg-slate-500/20 text-slate-400'
}

// --- LA CLÉ DU SUCCÈS : Fonction de date robuste ---
const getDateKey = (dateInput: string | Date) => {
  try {
    const d = new Date(dateInput)
    // Retourne toujours YYYY-MM-DD
    return d.toISOString().split('T')[0]
  } catch (e) {
    return "INVALID_DATE"
  }
}

export default function OpportunitiesPage() {
  const [sportFilter, setSportFilter] = useState<string>('all')
  const [bookmakerFilter, setBookmakerFilter] = useState<string>('all')
  const [minEdge, setMinEdge] = useState<number>(10)
  const [dateFilter, setDateFilter] = useState<string>('today') // Par défaut sur Aujourd'hui
  const [selectedMatch, setSelectedMatch] = useState<{id: string, name: string} | null>(null)

  const { data, isLoading, refetch } = useQuery<Opportunity[]>({
    queryKey: ['opportunities'],
    queryFn: getOpportunities,
    refetchInterval: 30000,
    staleTime: 20000,
  })

  const rawOpportunities = data ?? []

  // --- LOGIQUE FILTRÉE ET VALIDÉE ---
  const filteredData = useMemo(() => {
    const todayKey = getDateKey(new Date())
    
    return rawOpportunities.filter((opp: Opportunity) => {
      // 1. EDGE
      if (opp.edge_pct < minEdge) return false

      // 2. SPORT
      if (sportFilter !== 'all' && opp.sport.trim() !== sportFilter.trim()) return false
      
      // 3. BOOKMAKER
      if (bookmakerFilter !== 'all' && opp.bookmaker_best !== bookmakerFilter) return false
      
      // 4. DATE (Logique réparée)
      if (dateFilter !== 'all') {
        const matchKey = getDateKey(opp.commence_time)
        
        if (dateFilter === 'today') {
           if (matchKey !== todayKey) return false
        }
        else if (dateFilter === 'tomorrow') {
           const d = new Date()
           d.setDate(d.getDate() + 1)
           const tomorrowKey = getDateKey(d)
           if (matchKey !== tomorrowKey) return false
        }
        else if (dateFilter === 'week') {
            const matchTime = new Date(opp.commence_time).getTime()
            const todayTime = new Date().setHours(0,0,0,0)
            const nextWeekTime = new Date().setDate(new Date().getDate() + 7)
            if (matchTime < todayTime || matchTime > nextWeekTime) return false
        }
      }
      
      return true
    })
  }, [rawOpportunities, sportFilter, bookmakerFilter, minEdge, dateFilter])

  const sports = useMemo(() => {
    const set = new Set(rawOpportunities.map((o) => o.sport))
    return Array.from(set).sort()
  }, [rawOpportunities])

  const bookmakers = useMemo(() => {
    const set = new Set(rawOpportunities.map((o) => o.bookmaker_best))
    return Array.from(set).sort()
  }, [rawOpportunities])

  const matchIds = useMemo(() => filteredData.map(opp => opp.match_id), [filteredData])
  const { data: patronScores } = usePatronScores(matchIds)

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
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
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
          <div>
            <label className="text-sm text-slate-400">DATE DES MATCHS</label>
            <select
              value={dateFilter}
              onChange={(e) => setDateFilter(e.target.value)}
              className="w-full mt-1 bg-slate-700 border-slate-600 rounded p-2 text-white"
            >
              <option value="all">Tous</option>
              <option value="today">Aujourd'hui</option>
              <option value="tomorrow">Demain</option>
              <option value="week">Cette semaine</option>
            </select>
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
                <TableHead className="text-slate-400">Pari Recommande</TableHead>
                <TableHead className="text-slate-400">Score Patron</TableHead>
                <TableHead className="text-slate-400 text-right">Action</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {filteredData.length > 0 ? (
                filteredData.map((opp) => (
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
                    <TableCell>
                      <Badge className="bg-blue-500/20 text-blue-400 border-blue-500/30">
                        1X2 {opp.outcome === 'home' ? 'Home' : opp.outcome === 'away' ? 'Away' : 'Draw'} @ {opp.best_odds.toFixed(2)}
                      </Badge>
                    </TableCell>
                    <TableCell>
                      {patronScores?.[opp.match_id] ? (
                        <span className={`font-medium text-sm ${patronScores[opp.match_id].color}`}>
                          {patronScores[opp.match_id].label}
                        </span>
                      ) : (
                        <span className="font-medium text-sm text-gray-500">
                          Chargement...
                        </span>
                      )}
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
                ))
              ) : (
                <TableRow>
                   <TableCell colSpan={9} className="h-24 text-center text-slate-400">
                      <div className="flex flex-col items-center justify-center gap-2">
                        <FilterX className="w-8 h-8 opacity-50" />
                        <p>Aucune opportunité trouvée avec ces filtres.</p>
                      </div>
                   </TableCell>
                </TableRow>
              )}
            </TableBody>
          </Table>
          
          {isLoading && (
            <div className="flex items-center justify-center py-10 text-slate-400">
              Chargement des données...
            </div>
          )}
        </div>
      </Card>

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

