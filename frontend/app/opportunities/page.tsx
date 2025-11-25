'use client'

import { MatchAnalysisModal } from '@/components/agents/MatchAnalysisModal'
import { useMemo, useState, useEffect } from 'react'
import { usePatronScores } from '@/hooks/use-patron-scores'
import { useQuery } from '@tanstack/react-query'
import { RefreshCw, Target, FilterX, ArrowUpDown, Clock, Trophy, Database } from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { PlaceBetModal } from '@/components/PlaceBetModal'
import { Toaster } from 'sonner'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import { getOpportunities } from '@/lib/api'

const TEAM_TRANSLATIONS: Record<string, string> = {
  "Pisa": "Pise", 
  "Wales": "Pays de Galles",
  "North Macedonia": "Macédoine du Nord",
  "Sweden": "Suède",
  "Slovenia": "Slovénie",
  "Spain": "Espagne",
  "Turkey": "Turquie",
  "Germany": "Allemagne",
  "France": "France",
  "Italy": "Italie",
  "England": "Angleterre",
  "Belgium": "Belgique",
  "Netherlands": "Pays-Bas",
  "Portugal": "Portugal",
  "Switzerland": "Suisse",
  "Croatia": "Croatie",
  "Denmark": "Danemark",
  "Poland": "Pologne",
  "Austria": "Autriche",
  "Hungary": "Hongrie",
  "Czech Republic": "République Tchèque",
  "Serbia": "Serbie",
  "Ukraine": "Ukraine",
  "Russia": "Russie",
  "Greece": "Grèce",
  "Norway": "Norvège",
  "Finland": "Finlande",
  "Ireland": "Irlande",
  "Scotland": "Écosse",
  "USA": "États-Unis",
  "Japan": "Japon",
  "South Korea": "Corée du Sud",
  "Brazil": "Brésil",
  "Argentina": "Argentine",
  "Munich": "Munich",
  "Napoli": "Naples",
  "Milan": "Milan",
  "Inter": "Inter Milan",
  "Benfica": "Benfica",
  "Sevilla": "Séville"
}

const translateTeam = (name: string) => TEAM_TRANSLATIONS[name] || name

const SPORT_CATEGORIES = [
  { id: 'all', label: 'Tous les sports', prefix: '' },
  { id: 'soccer', label: '⚽ Football', prefix: 'soccer' },
  { id: 'basketball', label: '🏀 Basket', prefix: 'basketball' },
  { id: 'tennis', label: '🎾 Tennis', prefix: 'tennis' },
  { id: 'americanfootball', label: '🏈 Football Américain', prefix: 'americanfootball' },
  { id: 'icehockey', label: '🏒 Hockey sur Glace', prefix: 'icehockey' },
  { id: 'baseball', label: '⚾ Baseball', prefix: 'baseball' },
  { id: 'rugby', label: '🏉 Rugby', prefix: 'rugby' },
  { id: 'mma', label: '🥊 MMA / Boxe', prefix: 'mma' }, 
  { id: 'boxing', label: '🥊 Boxe', prefix: 'boxing' },
  { id: 'golf', label: '⛳ Golf', prefix: 'golf' },
  { id: 'cricket', label: '🏏 Cricket', prefix: 'cricket' },
]

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

const formatSportName = (sportKey: string) => {
  return sportKey
    .replace(/^(soccer|basketball|tennis|americanfootball|icehockey|baseball|rugby|mma|boxing|golf|cricket)_/, '')
    .replace(/_/g, ' ')
    .replace(/\b\w/g, l => l.toUpperCase())
}

const TimeUntil = ({ dateStr }: { dateStr: string }) => {
  const [timeLeft, setTimeLeft] = useState('')
  const [isUrgent, setIsUrgent] = useState(false)

  useEffect(() => {
    const updateTimer = () => {
      const now = new Date().getTime()
      const target = new Date(dateStr).getTime()
      const diff = target - now
      if (diff < 0) { setTimeLeft("Terminé"); return }
      const hours = Math.floor((diff % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60))
      const minutes = Math.floor((diff % (1000 * 60 * 60)) / (1000 * 60))
      setIsUrgent(diff < 3600000)
      setTimeLeft(`${hours}h ${minutes}min`)
    }
    updateTimer()
    const interval = setInterval(updateTimer, 60000)
    return () => clearInterval(interval)
  }, [dateStr])

  const matchTime = new Date(dateStr).toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit' })
  
  return (
    <div className="flex flex-col gap-0.5">
      <div className={`text-xs font-mono flex items-center gap-1 ${isUrgent ? 'text-red-400 animate-pulse font-bold' : 'text-slate-400'}`}>
        <Clock className="w-3 h-3" />
        {timeLeft}
      </div>
      <div className="text-[10px] text-slate-500">{matchTime}</div>
    </div>
  )
}

const edgeBadgeVariant = (edge: number) => {
  if (edge > 15) return 'bg-green-500/20 text-green-400 hover:bg-green-500/30'
  if (edge >= 10) return 'bg-yellow-500/20 text-yellow-400 hover:bg-yellow-500/30'
  return 'bg-slate-500/20 text-slate-400'
}

const getDateKey = (dateInput: string | Date) => {
  try {
    const d = new Date(dateInput)
    return d.toISOString().split('T')[0]
  } catch (e) {
    return "INVALID_DATE"
  }
}


// Elite Stars Badge System V2.0 - Hybrid Pro
const calculateLocalBadge = (edge: number, outcome: string, odds: number): number => {
  let score = 50
  
  if (edge > 200) score -= 25
  else if (edge > 100) score -= 15
  else if (edge > 50) score += 5
  else if (edge > 20) score += 10
  else if (edge < 10) score -= 10
  
  if (outcome === 'draw') score -= 10
  if (outcome === 'home') score += 5
  
  if (odds > 10) score -= 20
  else if (odds > 5) score -= 10
  else if (odds < 2) score += 10
  
  return Math.max(10, Math.min(90, score))
}

const getConseilBadge = (outcome: string, homeTeam: string, awayTeam: string) => {
  const cleanHome = homeTeam.split(' ').slice(0, 2).join(' ').toUpperCase()
  const cleanAway = awayTeam.split(' ').slice(0, 2).join(' ').toUpperCase()
  
  if (outcome === 'home') {
    return {
      label: `🏠 ${cleanHome}`,
      colorClass: 'bg-blue-500/10 text-blue-400 border-blue-500/20'
    }
  } else if (outcome === 'away') {
    return {
      label: `✈️ ${cleanAway}`,
      colorClass: 'bg-purple-500/10 text-purple-400 border-purple-500/20'
    }
  } else {
    return {
      label: '⚖️ MATCH NUL',
      colorClass: 'bg-slate-500/10 text-slate-400 border-slate-500/20'
    }
  }
}

const getEliteStarBadge = (patronLabel: string | null, localScore?: number) => {
  let score = localScore || 50
  
  // Override avec Patron si disponible
  if (patronLabel) {
    const scoreMap: Record<string, number> = {
      'PRUDENCE': 85,
      'ANALYSER': 50,
      'EVITER': 20
    }
    score = scoreMap[patronLabel] || score
  }
  
  let stars = ''
  let emoji = ''
  let label = ''
  let colorClass = ''
  let bgClass = ''
  
  if (score >= 80) {
    stars = '⭐⭐⭐⭐⭐'
    emoji = '💎'
    label = 'ELITE'
    colorClass = 'text-yellow-400'
    bgClass = 'bg-yellow-500/10 border-yellow-500/30 shadow-lg shadow-yellow-900/20'
  } else if (score >= 60) {
    stars = '⭐⭐⭐⭐☆'
    emoji = '⚡'
    label = 'PRIME'
    colorClass = 'text-green-400'
    bgClass = 'bg-green-500/10 border-green-500/30 shadow-lg shadow-green-900/20'
  } else if (score >= 40) {
    stars = '⭐⭐⭐☆☆'
    emoji = '🎯'
    label = 'STANDARD'
    colorClass = 'text-yellow-500'
    bgClass = 'bg-yellow-500/10 border-yellow-500/30'
  } else if (score >= 20) {
    stars = '⭐⭐☆☆☆'
    emoji = '⚠️'
    label = 'RISKY'
    colorClass = 'text-orange-400'
    bgClass = 'bg-orange-500/10 border-orange-500/30'
  } else {
    stars = '⭐☆☆☆☆'
    emoji = '❌'
    label = 'AVOID'
    colorClass = 'text-red-400'
    bgClass = 'bg-red-500/10 border-red-500/30 shadow-lg shadow-red-900/20'
  }
  
  return { stars, emoji, label, score, colorClass, bgClass }
}

export default function OpportunitiesPage() {
  const [categoryFilter, setCategoryFilter] = useState<string>('all')
  const [leagueFilter, setLeagueFilter] = useState<string>('all') 
  const [bookmakerFilter, setBookmakerFilter] = useState<string>('all')
  const [minEdge, setMinEdge] = useState<number>(10)
  const [dateFilter, setDateFilter] = useState<string>('all') 
  const [selectedMatch, setSelectedMatch] = useState<{id: string, name: string} | null>(null)
  const [selectedBet, setSelectedBet] = useState<any | null>(null)

  const [sortConfig, setSortConfig] = useState<{key: keyof Opportunity, direction: 'asc' | 'desc'}>({ key: 'commence_time', direction: 'asc' })

  const { data, isLoading, refetch } = useQuery<Opportunity[]>({
    queryKey: ['opportunities'],
    queryFn: getOpportunities,
    refetchInterval: 30000,
    staleTime: 20000,
  })

  const rawOpportunities = data ?? []

  const requestSort = (key: keyof Opportunity) => {
    let direction: 'asc' | 'desc' = 'desc'
    if (sortConfig.key === key && sortConfig.direction === 'desc') direction = 'asc'
    setSortConfig({ key, direction })
  }

  const filteredData = useMemo(() => {
    const todayKey = getDateKey(new Date())
    
    let res = rawOpportunities.filter((opp: Opportunity) => {
      // 1. Filtre edge minimum
      if (opp.edge_pct < minEdge) return false
      
      // 2. Filtre par Catégorie
      if (categoryFilter !== 'all') {
        const selectedCategory = SPORT_CATEGORIES.find(c => c.id === categoryFilter)
        if (selectedCategory && !opp.sport.startsWith(selectedCategory.prefix)) return false
      }

      // 3. Filtre Ligue
      if (leagueFilter !== 'all' && opp.sport !== leagueFilter) {
        return false
      }
      
      // 4. Filtre par Bookmaker
      if (bookmakerFilter !== 'all' && opp.bookmaker_best !== bookmakerFilter) return false
      
      // 5. Filtre par Date
      if (dateFilter !== 'all') {
        const matchKey = getDateKey(opp.commence_time)
        if (dateFilter === 'today') { 
          if (matchKey !== todayKey) return false 
        }
        else if (dateFilter === 'tomorrow') {
           const d = new Date()
           d.setDate(d.getDate() + 1)
           if (matchKey !== getDateKey(d)) return false
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

    // Tri chronologique (toujours du plus proche au plus lointain)
    res.sort((a, b) => {
const timeA = new Date(a.commence_time).getTime()
      const timeB = new Date(b.commence_time).getTime()
      return timeA - timeB  // Tri ascendant (plus proche en premier)
    })


    return res
  }, [rawOpportunities, categoryFilter, leagueFilter, bookmakerFilter, minEdge, dateFilter])

  const availableLeagues = useMemo(() => {
      if (categoryFilter === 'all') return []
      
      const selectedCategory = SPORT_CATEGORIES.find(c => c.id === categoryFilter)
      if (!selectedCategory) return []

      const filteredSports = rawOpportunities
        .filter(opp => opp.sport.startsWith(selectedCategory.prefix))
        .map(opp => opp.sport)
        
      return Array.from(new Set(filteredSports)).sort()
      
  }, [rawOpportunities, categoryFilter])

  const bookmakers = useMemo(() => Array.from(new Set(rawOpportunities.map(o => o.bookmaker_best))).sort(), [rawOpportunities])
  const matchIds = useMemo(() => filteredData.map(opp => opp.match_id), [filteredData])
  const { data: patronScores } = usePatronScores(matchIds)

  // Tri intelligent par risque (utilise Agent Patron)
  const sortedData = useMemo(() => {
    if (dateFilter !== 'risk_asc') {
      return filteredData
    }
    
    return [...filteredData].sort((a, b) => {
      let riskA = 50, riskB = 50
      
      // 1. PRIORITÉ : Score Agent Patron
      const patronA = patronScores?.[a.match_id]?.label || 'ANALYSER'
      const patronB = patronScores?.[b.match_id]?.label || 'ANALYSER'
      
      if (patronA === 'PRUDENCE') riskA = 20
      else if (patronA === 'EVITER') riskA = 80
      
      if (patronB === 'PRUDENCE') riskB = 20
      else if (patronB === 'EVITER') riskB = 80
      
      // 2. Ajustements secondaires
      if (a.edge_pct > 200) riskA += 15
      if (a.outcome === 'draw') riskA += 8
      if (a.best_odds > 10) riskA += 12
      
      if (b.edge_pct > 200) riskB += 15
      if (b.outcome === 'draw') riskB += 8
      if (b.best_odds > 10) riskB += 12
      
      return riskA - riskB
    })
  }, [filteredData, patronScores, dateFilter])


  return (
    <div className="space-y-6">
      
      <div className={`p-3 rounded text-sm text-white font-mono flex items-center gap-4 ${rawOpportunities.length === 0 ? 'bg-red-800/60 border border-red-700' : 'bg-green-800/60 border border-green-700'}`}>
          <Database className='w-5 h-5' />
          {isLoading && <span className='text-orange-300'>Chargement des données API...</span>}
          {!isLoading && rawOpportunities.length === 0 && <span className='font-bold text-yellow-300'>API VIDE. 0 opportunité brute reçue.</span>}
          {!isLoading && rawOpportunities.length > 0 && <span className='font-bold text-green-300'>API OK. {rawOpportunities.length} opportunités brutes reçues.</span>}
      </div>

      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <div className="p-3 bg-violet-500/20 rounded-xl border border-violet-500/30 shadow-[0_0_15px_rgba(139,92,246,0.3)]">
            <Trophy className="w-8 h-8 text-violet-400" />
          </div>
          <div>
            <h1 className="text-3xl font-bold text-white tracking-tight">Opportunités V5.3</h1>
            <p className="text-slate-400">Tri Chronologique Parfait</p>
          </div>
        </div>
        <Button onClick={() => refetch()} variant="outline" className="border-violet-500 hover:bg-violet-500/10 transition-all">
          <RefreshCw className="w-4 h-4 mr-2" />
          Rafraîchir
        </Button>
      </div>

      <Card className="bg-slate-900/50 border-slate-800 p-6 backdrop-blur-sm">
        <div className="flex items-center justify-between mb-4">
             <h3 className="text-lg font-semibold text-slate-200">Filtres Avancés</h3>
             <Badge variant="outline" className="text-violet-400 border-violet-500/50">{filteredData.length} trouvés</Badge>
        </div>
        
        <div className="grid grid-cols-1 md:grid-cols-5 gap-6">
          <div className="space-y-2">
            <label className="text-xs font-bold text-slate-500 tracking-wider">CATÉGORIE SPORT</label>
            <select
              value={categoryFilter}
              onChange={(e) => {
                  setCategoryFilter(e.target.value)
                  setLeagueFilter('all')
              }}
              className="w-full bg-slate-800 border-slate-700 rounded-lg p-2.5 text-white focus:ring-2 focus:ring-violet-500 focus:outline-none transition-all"
            >
              {SPORT_CATEGORIES.map((cat) => (
                <option key={cat.id} value={cat.id}>{cat.label}</option>
              ))}
            </select>
          </div>
          
          <div className="space-y-2">
            <label className="text-xs font-bold text-slate-500 tracking-wider">LIGUE SPÉCIFIQUE</label>
            <select
              value={leagueFilter}
              onChange={(e) => setLeagueFilter(e.target.value)}
              disabled={categoryFilter === 'all'}
              className={`w-full bg-slate-800 border-slate-700 rounded-lg p-2.5 text-white focus:ring-2 focus:ring-violet-500 focus:outline-none transition-all ${categoryFilter === 'all' ? 'opacity-50 cursor-not-allowed' : ''}`}
            >
              <option value="all">Toutes les ligues ({categoryFilter === 'all' ? 0 : availableLeagues.length})</option>
              {availableLeagues.map((leagueKey) => (
                <option key={leagueKey} value={leagueKey}>{formatSportName(leagueKey)}</option>
              ))}
            </select>
          </div>

          <div className="space-y-2">
            <label className="text-xs font-bold text-slate-500 tracking-wider">BOOKMAKER</label>
            <select
              value={bookmakerFilter}
              onChange={(e) => setBookmakerFilter(e.target.value)}
              className="w-full bg-slate-800 border-slate-700 rounded-lg p-2.5 text-white focus:ring-2 focus:ring-violet-500 focus:outline-none transition-all"
            >
              <option value="all">Tous</option>
              {bookmakers.map((b) => (
                <option key={b} value={b}>{b}</option>
              ))}
            </select>
          </div>
          
          <div className="space-y-2">
             <div className="flex justify-between">
                <label className="text-xs font-bold text-slate-500 tracking-wider">EDGE MIN</label>
                <span className="text-xs font-bold text-violet-400">{minEdge.toFixed(1)}%</span>
             </div>
            <input
                type="range" min="0" max="50" step="0.5" value={minEdge}
                onChange={(e) => setMinEdge(parseFloat(e.target.value))}
                className="w-full h-2 bg-slate-700 rounded-lg appearance-none cursor-pointer accent-violet-500"
              />
          </div>
          
          <div className="space-y-2">
            <label className="text-xs font-bold text-slate-500 tracking-wider">PÉRIODE</label>
            <select
              value={dateFilter}
              onChange={(e) => setDateFilter(e.target.value)}
              className="w-full bg-slate-800 border-slate-700 rounded-lg p-2.5 text-white focus:ring-2 focus:ring-violet-500 focus:outline-none transition-all"
            >
              <option value="all">Tout</option>
              <option value="today">Aujourd'hui</option>
              <option value="tomorrow">Demain</option>
              <option value="week">Cette semaine</option>
              <option value="risk_asc">🎯 Moins risqué d'abord</option>
            </select>
          </div>
        </div>
      </Card>

      <Card key={`table-${categoryFilter}-${leagueFilter}-${dateFilter}`} className="bg-slate-900/50 border-slate-800 overflow-hidden">
          <Table>
            <TableHeader className="bg-slate-950/50">
              <TableRow className="border-slate-800 hover:bg-transparent">
                <TableHead className="text-slate-400">
                    <div className="flex items-center gap-1">Match</div>
                </TableHead>
                <TableHead className="text-slate-400">Ligue</TableHead>
                <TableHead className="text-slate-400">Résultat</TableHead>
                <TableHead className="text-slate-400 text-right cursor-pointer hover:text-white" onClick={() => requestSort('best_odds')}>
                    <div className="flex items-center justify-end gap-1">Cote <ArrowUpDown className="w-3 h-3" /></div>
                </TableHead>
                <TableHead className="text-slate-400">Bookmaker</TableHead>
                <TableHead className="text-slate-400 text-right cursor-pointer hover:text-white" onClick={() => requestSort('edge_pct')}>
                     <div className="flex items-center justify-end gap-1">Edge <ArrowUpDown className="w-3 h-3" /></div>
                </TableHead>
                <TableHead className="text-slate-400">Conseil</TableHead>
                <TableHead className="text-slate-400">Patron</TableHead>
                <TableHead className="text-slate-400 text-right">Action</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {filteredData.length > 0 ? (
                sortedData.map((opp) => (
                  <TableRow key={opp.id} className="border-slate-800 hover:bg-slate-800/40 transition-colors">
                    <TableCell>
                      <div className="py-1">
                        <p className="font-bold text-white text-base">
                          {translateTeam(opp.home_team)} <span className="text-slate-500 font-normal text-sm">vs</span> {translateTeam(opp.away_team)}
                        </p>
                        <TimeUntil dateStr={opp.commence_time} />
                      </div>
                    </TableCell>
                    <TableCell>
                      <div className="flex flex-col gap-1">
                        <Badge variant="secondary" className="w-fit bg-slate-800 text-[10px] text-slate-400 border border-slate-700">
                           {SPORT_CATEGORIES.find(c => opp.sport.startsWith(c.prefix))?.label.split(' ')[0] || 'Sports'}
                        </Badge>
                        <span className="text-xs text-slate-400 font-medium">
                           {formatSportName(opp.sport)}
                        </span>
                      </div>
                    </TableCell>
                    <TableCell className="text-slate-300 capitalize font-medium">{opp.outcome}</TableCell>
                    <TableCell className="text-right font-mono font-bold text-lg text-white">{opp.best_odds.toFixed(2)}</TableCell>
                    <TableCell className="text-slate-300">{opp.bookmaker_best}</TableCell>
                    <TableCell className="text-right">
                      <Badge className={`${edgeBadgeVariant(opp.edge_pct)} font-bold text-sm px-3 py-1`}>
                        {opp.edge_pct.toFixed(1)}%
                      </Badge>
                    </TableCell>
                    <TableCell>
                      {(() => {
                        const conseil = getConseilBadge(opp.outcome, opp.home_team, opp.away_team)
                        return (
                          <Badge className={`${conseil.colorClass} border font-medium text-xs`}>
                            {conseil.label}
                          </Badge>
                        )
                      })()}
                    </TableCell>
                    <TableCell className="hidden">
                      <Badge className="bg-blue-500/10 text-blue-400 border border-blue-500/20 font-medium">
                        {opp.outcome === 'draw' ? 'Nul' : opp.outcome === 'home' ? 'Domicile' : 'Extérieur'}
                      </Badge>
                    </TableCell>
                    <TableCell>
                      {(() => {
                        const patronLabel = patronScores?.[opp.match_id]?.label || null
                        const localScore = calculateLocalBadge(opp.edge_pct, opp.outcome, opp.best_odds)
                        const badge = getEliteStarBadge(patronLabel, localScore)
                        const isLoading = !patronLabel
                        return (
                          <div className={`flex items-center gap-1.5 px-2.5 py-1 rounded-lg border backdrop-blur-sm transition-all duration-500 ${badge.bgClass} ${isLoading ? 'animate-pulse border-slate-600' : ''}`}>
                            <span className="text-base">{badge.emoji}</span>
                            <span className={`text-xs ${badge.colorClass}`}>{badge.stars}</span>
                            <span className={`text-[10px] font-bold ${badge.colorClass}`}>{badge.score}</span>
                            <span className={`text-[9px] font-black tracking-wider ${badge.colorClass}`}>
                              {badge.label}
                            </span>
                          </div>
                        )
                      })()}
                    </TableCell>
                    <TableCell className="text-right">
                      <div className="flex gap-2 justify-end">
                        <Button
                          size="sm"
                          variant="ghost"
                          className="rounded-full h-8 w-8 p-0 border border-slate-700 hover:bg-slate-700 text-slate-300"
                          onClick={() => setSelectedMatch({ id: opp.match_id, name: `${translateTeam(opp.home_team)} vs ${translateTeam(opp.away_team)}` })}
                        >
                          Analyser
                        </Button>
                        <Button 
                          size="sm" 
                          onClick={() => setSelectedBet(opp)}
                          className="rounded-full px-4 h-8 bg-gradient-to-r from-violet-600 to-indigo-600 hover:from-violet-500 hover:to-indigo-500 shadow-lg shadow-violet-900/20"
                        >  

                          Parier
                        </Button>
                      </div>
                    </TableCell>
                  </TableRow>
                ))
              ) : (
                <TableRow>
                   <TableCell colSpan={9} className="h-32 text-center text-slate-400">
                      <div className="flex flex-col items-center justify-center gap-3">
                        <div className="p-4 bg-slate-800/50 rounded-full">
                             <FilterX className="w-6 h-6 opacity-50" />
                        </div>
                        <p>Aucun match trouvé pour cette sélection.</p>
                        <p className="text-xs text-slate-500">Ajustez la catégorie, la ligue ou la période.</p>
                      </div>
                   </TableCell>
                </TableRow>
              )}
            </TableBody>
          </Table>
      </Card>

      {selectedMatch && (
        <MatchAnalysisModal
          matchId={selectedMatch.id}
          matchName={selectedMatch.name}
          isOpen={!!selectedMatch}
          onClose={() => setSelectedMatch(null)}
        />
      )}
      {selectedMatch && (
        <MatchAnalysisModal
          matchId={selectedMatch.id}
          matchName={selectedMatch.name}
          isOpen={!!selectedMatch}
          onClose={() => setSelectedMatch(null)}
        />
      )}

      {selectedBet && (
        <PlaceBetModal
          isOpen={!!selectedBet}
          onClose={() => setSelectedBet(null)}
          opportunity={selectedBet}
          patronScore={patronScores?.[selectedBet.match_id]?.label}
        />
      )}

      <Toaster position="top-right" richColors />
    </div>
  )
}
    
