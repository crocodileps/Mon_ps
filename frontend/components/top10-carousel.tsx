'use client'

import { useState, useMemo } from 'react'
import { useRouter } from 'next/navigation'
import { Card } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { ArrowUpRight, Star, ChevronLeft, ChevronRight } from 'lucide-react'
import { useClassification } from '@/lib/context/classification-context'

const allOpportunities = [
  {
    id: 1,
    type: 'Value Bet',
    risk: 'Moyen',
    sport: 'Tennis',
    title: 'Djokovic Gagne',
    match: 'Djokovic vs Nadal',
    odds: '1.70',
    recentForm: ['W', 'W', 'W', 'W', 'W', 'W', 'L', 'W', 'W', 'W'],
    agent: 'Titan',
    confidence: 96,
    safetyScore: 96,
  },
  {
    id: 2,
    type: 'Value Bet',
    risk: 'Faible',
    sport: 'Football',
    title: 'Man City Gagne',
    match: 'Manchester City vs Liverpool',
    odds: '1.85',
    recentForm: ['W', 'W', 'W', 'W', 'L', 'W', 'W', 'W', 'W', 'W'],
    agent: 'Titan',
    confidence: 94,
    safetyScore: 94,
  },
  {
    id: 3,
    type: 'IA Signal',
    risk: 'Faible',
    sport: 'Football',
    title: 'Bayern Munich Gagne',
    match: 'Bayern vs Dortmund',
    odds: '1.60',
    recentForm: ['W', 'W', 'W', 'W', 'W', 'L', 'W', 'W', 'W', 'W'],
    agent: 'Oracle',
    confidence: 93,
    safetyScore: 93,
  },
  {
    id: 4,
    type: 'Value Bet',
    risk: 'Faible',
    sport: 'Tennis',
    title: 'Alcaraz -2.5 Sets',
    match: 'Alcaraz vs Sinner',
    odds: '2.50',
    recentForm: ['W', 'W', 'W', 'L', 'W', 'W', 'W', 'L', 'W', 'W'],
    agent: 'Momentum',
    confidence: 92,
    safetyScore: 92,
  },
  {
    id: 5,
    type: 'IA Signal',
    risk: 'Faible',
    sport: 'NBA',
    title: 'Lakers Gagne',
    match: 'Lakers vs Celtics',
    odds: '2.05',
    recentForm: ['W', 'W', 'W', 'L', 'W', 'W', 'W', 'W', 'L', 'W'],
    agent: 'Oracle',
    confidence: 90,
    safetyScore: 90,
  },
]
export function Top10Carousel() {
  const router = useRouter()
  const { addBet, isClassified } = useClassification()
  const [scrollPosition, setScrollPosition] = useState(0)

  const availableOpportunities = useMemo(() => {
    return allOpportunities
      .filter((opp) => !isClassified(opp.id))
      .sort((a, b) => b.safetyScore - a.safetyScore)
      .slice(0, 10)
  }, [isClassified])

  const handleScroll = (direction: 'left' | 'right') => {
    const container = document.getElementById('carousel-container')
    if (!container) return

    const scrollAmount = 400
    const newPosition = direction === 'left' 
      ? Math.max(0, scrollPosition - scrollAmount)
      : Math.min(container.scrollWidth - container.clientWidth, scrollPosition + scrollAmount)

    container.scrollTo({ left: newPosition, behavior: 'smooth' })
    setScrollPosition(newPosition)
  }

  const handleAnalyse = (oppId: number) => {
    router.push(`/opportunities/${oppId}`)
  }

  const handleClassify = (opp: typeof allOpportunities[0]) => {
    addBet({
      id: opp.id,
      type: opp.type,
      risk: opp.risk,
      sport: opp.sport,
      title: opp.title,
      match: opp.match,
      odds: opp.odds,
      recentForm: opp.recentForm,
      agent: opp.agent,
      confidence: opp.confidence,
    })
    router.push('/classification')
  }

  if (availableOpportunities.length === 0) {
    return (
      <div className="backdrop-blur-md border border-white/20 bg-card/50 rounded-2xl p-8 text-center">
        <p className="text-slate-400">Toutes les opportunités ont été classifiées</p>
      </div>
    )
  }

  return (
    <div className="relative">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-2xl font-bold text-white">Top 10 Opportunités Sûres</h2>
        <div className="flex gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={() => handleScroll('left')}
            disabled={scrollPosition === 0}
            className="bg-slate-800/50 border-slate-700 hover:bg-slate-700 disabled:opacity-50"
          >
            <ChevronLeft size={20} />
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={() => handleScroll('right')}
            className="bg-slate-800/50 border-slate-700 hover:bg-slate-700"
          >
            <ChevronRight size={20} />
          </Button>
        </div>
      </div>

      <div
        id="carousel-container"
        className="flex gap-6 overflow-x-auto scrollbar-hide scroll-smooth pb-4"
        style={{ scrollbarWidth: 'none', msOverflowStyle: 'none' }}
      >
{availableOpportunities.map((opp) => (
          <Card
            key={opp.id}
            className="flex-shrink-0 w-[350px] backdrop-blur-md border-2 border-purple-500/30 bg-slate-900/50 rounded-2xl p-6 space-y-4 hover:border-purple-500/50 transition-all shadow-lg shadow-purple-500/10"
          >
            <div className="flex items-center justify-between">
              <Badge
                variant="secondary"
                className={`${
                  opp.type === 'Value Bet'
                    ? 'bg-purple-500/20 text-purple-300'
                    : 'bg-blue-500/20 text-blue-300'
                } border-0 text-xs font-medium px-3 py-1`}
              >
                {opp.type}
              </Badge>
              <div className="flex gap-2">
                <Badge variant="secondary" className="bg-slate-700/50 text-slate-300 border-0 text-xs px-3 py-1">
                  {opp.risk}
                </Badge>
                <Badge variant="secondary" className="bg-slate-700/50 text-slate-300 border-0 text-xs px-3 py-1">
                  {opp.sport}
                </Badge>
              </div>
            </div>

            <div>
              <h3 className="text-xl font-bold text-white mb-1">{opp.title}</h3>
              <p className="text-sm text-slate-400">{opp.match}</p>
            </div>

            <div className="flex items-center justify-between py-2 px-3 bg-slate-800/30 rounded-lg border border-slate-700/50">
              <div>
                <p className="text-xs text-slate-500 mb-0.5">Agent recommandant</p>
                <Badge
                  variant="secondary"
                  className={`${
                    opp.agent === 'Oracle'
                      ? 'bg-purple-500/20 text-purple-300 border-purple-500/30'
                      : opp.agent === 'Titan'
                      ? 'bg-blue-500/20 text-blue-300 border-blue-500/30'
                      : 'bg-pink-500/20 text-pink-300 border-pink-500/30'
                  } border text-xs font-semibold px-2 py-0.5`}
                >
                  {opp.agent}
                </Badge>
              </div>
              <div className="text-right">
                <p className="text-xs text-slate-500 mb-0.5">Confiance IA</p>
                <div
                  className={`text-lg font-bold ${
                    opp.confidence >= 80 ? 'text-emerald-400' : opp.confidence >= 65 ? 'text-cyan-400' : 'text-yellow-400'
                  }`}
                >
                  {opp.confidence}%
                </div>
              </div>
            </div>

            <div className="flex items-center justify-between">
              <div className="text-3xl font-bold text-emerald-400">@ {opp.odds}</div>
              <div className="text-right">
                <div className="flex gap-0.5 mb-1">
                  {opp.recentForm.map((result, idx) => (
                    <div
                      key={idx}
                      className={`w-2 h-8 rounded-sm ${
                        result === 'W' ? 'bg-emerald-500' : result === 'L' ? 'bg-red-500' : 'bg-yellow-500'
                      }`}
                    />
                  ))}
                </div>
                <p className="text-xs text-slate-500">Forme récente</p>
              </div>
            </div>

            <div className="space-y-2 pt-2">
              <div className="grid grid-cols-2 gap-2">
                <Button
                  variant="outline"
                  className="bg-slate-700/50 hover:bg-slate-700 border-slate-600 text-white"
                  onClick={() => handleAnalyse(opp.id)}
                >
                  Analyser <ArrowUpRight size={14} className="ml-1" />
                </Button>
                <Button
                  variant="outline"
                  className="bg-slate-700/50 hover:bg-slate-700 border-slate-600 text-yellow-400"
                  onClick={() => handleClassify(opp)}
                >
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
