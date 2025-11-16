'use client'
import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { Card } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { ArrowUpRight, Star, ChevronLeft, ChevronRight, Loader2 } from 'lucide-react'
import { useClassification } from '@/lib/context/classification-context'
import { useOpportunities } from '@/hooks/use-opportunities'

export function Top10Carousel() {
  const router = useRouter()
  const { addBet } = useClassification()
  const [startIndex, setStartIndex] = useState(0)
  
  const { data: opportunities, isLoading } = useOpportunities({ limit: 10, min_edge: 1.0 })

  const handleAnalyse = (id: string) => {
    router.push(`/opportunities/${id}`)
  }

  const handleClassify = (opp: any) => {
    addBet({
      id: opp.match_id,
      type: "Value Bet",
      sport: opp.sport,
      risk: "Moyen",
      title: `${opp.home_team} vs ${opp.away_team}`,
      match: opp.outcome,
      odds: parseFloat(opp.best_odd).toString(),
      recentForm: ["W", "W", "W", "W", "W"],
      confidence: Math.round(opp.spread_pct),
      agent: opp.bookmaker_best,
    })
  }

  const scrollLeft = () => {
    setStartIndex(Math.max(0, startIndex - 1))
  }

  const scrollRight = () => {
    if (opportunities) {
      setStartIndex(Math.min(opportunities.length - 5, startIndex + 1))
    }
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-48">
        <Loader2 className="w-8 h-8 animate-spin text-violet-500" />
      </div>
    )
  }

  if (!opportunities || opportunities.length === 0) {
    return (
      <div className="text-center py-8 text-muted-foreground">
        Aucune opportunité disponible
      </div>
    )
  }

  const visibleOpps = opportunities.slice(startIndex, startIndex + 5)

  return (
    <div className="relative">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-2xl font-bold">Top 10 Opportunités</h2>
        <div className="flex gap-2">
          <Button variant="outline" size="icon" onClick={scrollLeft} disabled={startIndex === 0}>
            <ChevronLeft size={20} />
          </Button>
          <Button variant="outline" size="icon" onClick={scrollRight} disabled={startIndex >= opportunities.length - 5}>
            <ChevronRight size={20} />
          </Button>
        </div>
      </div>

      <div className="flex gap-4 overflow-hidden">
        {visibleOpps.map((opp) => (
          <Card
            key={opp.match_id}
            className="flex-shrink-0 w-[350px] backdrop-blur-md border-2 border-purple-500/30 bg-slate-900/50 rounded-2xl p-6 space-y-4 hover:border-purple-500/50 transition-all shadow-lg shadow-purple-500/10"
          >
            <div className="flex items-center justify-between">
              <Badge variant="secondary" className="bg-purple-500/20 text-purple-300 border-0 text-xs font-medium px-3 py-1">
                {opp.sport}
              </Badge>
              <Badge variant="secondary" className="bg-slate-700/50 text-slate-300 border-0 text-xs px-3 py-1">
                {opp.nb_bookmakers} bookmakers
              </Badge>
            </div>

            <div>
              <h3 className="text-xl font-bold text-white mb-1">{opp.outcome}</h3>
              <p className="text-sm text-slate-400">{opp.home_team} vs {opp.away_team}</p>
            </div>

            <div className="flex items-center justify-between py-2 px-3 bg-slate-800/30 rounded-lg border border-slate-700/50">
              <div>
                <p className="text-xs text-slate-500 mb-0.5">Meilleur bookmaker</p>
                <Badge variant="secondary" className="bg-blue-500/20 text-blue-300 border-blue-500/30 border text-xs font-semibold px-2 py-0.5">
                  {opp.bookmaker_best}
                </Badge>
              </div>
              <div className="text-right">
                <p className="text-xs text-slate-500 mb-0.5">Edge</p>
                <div className=  {  `text-lg font-bold ${opp.spread_pct >= 5 ? 'text-emerald-400' : opp.spread_pct >= 2 ? 'text-cyan-400' : 'text-yellow-400'}`  }  >
                  {opp.spread_pct.toFixed(1)}%
                </div>
              </div>
            </div>

            <div className="flex items-center justify-between">
              <div className="text-3xl font-bold text-emerald-400">@ {parseFloat(opp.best_odd).toFixed(2)}</div>
              <div className="text-right">
                <p className="text-xs text-slate-500">Pire cote</p>
                <div className="text-lg text-red-400">@ {parseFloat(opp.worst_odd).toFixed(2)}</div>
              </div>
            </div>

            <div className="space-y-2 pt-2">
              <div className="grid grid-cols-2 gap-2">
                <Button variant="outline" className="bg-slate-700/50 hover:bg-slate-700 border-slate-600 text-white" onClick={() => handleAnalyse(opp.match_id)}>
                  Analyser <ArrowUpRight size={14} className="ml-1" />
                </Button>
                <Button variant="outline" className="bg-slate-700/50 hover:bg-slate-700 border-slate-600 text-yellow-400" onClick={() => handleClassify(opp)}>
                  Classifier <Star size={14} className="ml-1" />
                </Button>
              </div>
              <Button className="w-full bg-blue-600 hover:bg-blue-700 text-white font-semibold">
                Parier
              </Button>
            </div>
          </Card>
        ))}
      </div>
    </div>
  )
}
