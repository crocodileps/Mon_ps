'use client'

import { Activity, Calendar, Target, TrendingUp, Wallet, Zap } from 'lucide-react'

import { Badge } from '@/components/ui/badge'
import { Card } from '@/components/ui/card'

const stats = [
  { label: 'Bankroll', value: '10,500€', change: '+3.4%', icon: Wallet },
  { label: 'ROI', value: '5.2%', change: '+1.2%', icon: TrendingUp },
  { label: 'CLV', value: '2.1%', change: '+0.6%', icon: Target },
  { label: 'Sharpe Ratio', value: '1.35', change: '+0.2%', icon: Activity },
]

const topBookmakers = [
  { name: 'Bet365', profit: 2237 },
  { name: 'Pinnacle', profit: 1490 },
]

const daysInMonth = [
  { date: 1, profit: 45.2, bets: 3 },
  { date: 2, profit: -12.5, bets: 2 },
  { date: 3, profit: 78.3, bets: 5 },
  { date: 4, profit: 0, bets: 0 },
  { date: 5, profit: 125.4, bets: 4 },
  { date: 6, profit: -34.2, bets: 2 },
  { date: 7, profit: 56.8, bets: 3 },
  { date: 8, profit: 0, bets: 0 },
  { date: 9, profit: 92.1, bets: 6 },
  { date: 10, profit: -18.4, bets: 1 },
  { date: 11, profit: 145.6, bets: 7 },
  { date: 12, profit: 34.2, bets: 2 },
  { date: 13, profit: 0, bets: 0 },
  { date: 14, profit: -45.3, bets: 3 },
  { date: 15, profit: 67.5, bets: 4 },
  { date: 16, profit: 23.4, bets: 2 },
  { date: 17, profit: 0, bets: 0 },
  { date: 18, profit: 156.7, bets: 8 },
  { date: 19, profit: -28.9, bets: 2 },
  { date: 20, profit: 89.2, bets: 5 },
  { date: 21, profit: 0, bets: 0 },
  { date: 22, profit: 112.3, bets: 6 },
  { date: 23, profit: 45.6, bets: 3 },
  { date: 24, profit: 0, bets: 0 },
  { date: 25, profit: -56.7, bets: 4 },
  { date: 26, profit: 78.9, bets: 4 },
  { date: 27, profit: 134.2, bets: 7 },
  { date: 28, profit: 23.4, bets: 2 },
  { date: 29, profit: 0, bets: 0 },
  { date: 30, profit: 67.8, bets: 3 },
]

export default function DashboardPage() {

  const getColorClass = (profit: number) => {
    if (profit === 0) return 'bg-surface hover:bg-surface-hover'
    if (profit > 100) return 'bg-green-500/40 hover:bg-green-500/60'
    if (profit > 50) return 'bg-green-500/30 hover:bg-green-500/50'
    if (profit > 0) return 'bg-green-500/20 hover:bg-green-500/40'
    if (profit > -50) return 'bg-red-500/20 hover:bg-red-500/40'
    return 'bg-red-500/40 hover:bg-red-500/60'
  }

  return (
    <div className="min-h-screen bg-background p-4 sm:p-6 lg:p-8">
      <div className="mx-auto max-w-7xl space-y-8">
        <div>
          <Card className="relative overflow-hidden border-purple-500/20 bg-gradient-to-br from-purple-500/10 via-background to-pink-500/10 p-8">
            <div className="absolute inset-0 bg-gradient-to-r from-purple-500/5 to-pink-500/5 blur-3xl" />
            <div className="relative space-y-6">
              <div>
                <h1 className="text-3xl font-bold md:text-4xl">
                  Heureux retour,
                  <span className="bg-gradient-to-r from-purple-400 to-pink-400 bg-clip-text text-transparent">
                    {' '}
                    Mya
                  </span>
                  .
                </h1>
                <p className="mt-3 text-base text-muted-foreground md:text-lg">
                  Vous avez <span className="text-green-400 font-semibold">14 paris</span> ouverts, exposant{' '}
                  <span className="text-purple-400 font-semibold">34€</span>, pour un retour potentiel de{' '}
                  <span className="text-green-400 font-semibold">516€</span>.
                </p>
              </div>
              <div className="flex flex-wrap items-center gap-3">
                <div className="flex items-center gap-2">
                  <Zap className="h-4 w-4 text-yellow-400" />
                  <span className="text-sm text-muted-foreground">Bookmakers les plus performants :</span>
                </div>
                {topBookmakers.map((item) => (
                  <Badge
                    key={item.name}
                    variant="default"
                    className="border-green-500/30 bg-green-500/20 text-green-400"
                  >
                    {item.name} +{item.profit}€
                  </Badge>
                ))}
              </div>
            </div>
          </Card>
        </div>

        <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-4">
          {stats.map((stat) => {
            const Icon = stat.icon
            return (
              <div key={stat.label}>
                <Card className="group relative overflow-hidden border border-border/60 bg-surface/80 p-6 transition-all duration-300 hover:shadow-2xl hover:shadow-purple-500/20">
                  <div className="pointer-events-none absolute inset-0 bg-gradient-to-br from-purple-500/5 to-transparent opacity-0 transition-opacity duration-300 group-hover:opacity-100" />
                  <div className="relative space-y-3">
                    <div className="flex items-center justify-between">
                      <span className="text-sm font-medium text-muted-foreground">{stat.label}</span>
                      <div className="rounded-lg bg-purple-500/10 p-2 text-purple-400 transition-colors duration-300 group-hover:bg-purple-500/20">
                        <Icon className="h-5 w-5" />
                      </div>
                    </div>
                    <div className="text-3xl font-bold">{stat.value}</div>
                    <div className="flex items-center gap-2 text-sm font-semibold text-green-400">
                      <TrendingUp className="h-4 w-4" />
                      {stat.change}
                    </div>
                  </div>
                </Card>
              </div>
            )
          })}
        </div>

        <div>
          <Card className="p-6 md:p-8">
            <div className="mb-6 flex items-center gap-3">
              <Calendar className="h-6 w-6 text-purple-400" />
              <div>
                <h2 className="text-2xl font-bold">Activité – Novembre 2025</h2>
                <p className="text-sm text-muted-foreground">Calendrier de vos performances quotidiennes</p>
              </div>
            </div>

            <div className="mb-2 grid grid-cols-7 gap-2">
              {['Lun', 'Mar', 'Mer', 'Jeu', 'Ven', 'Sam', 'Dim'].map((day) => (
                <div key={day} className="text-center text-xs font-medium text-muted-foreground">
                  {day}
                </div>
              ))}
            </div>

            <div className="grid grid-cols-7 gap-2">
              {daysInMonth.map((day) => (
                <div key={day.date} className="group relative">
                  <div
                    className={`relative flex aspect-square items-center justify-center rounded-lg text-sm font-semibold transition-all duration-200 ${getColorClass(day.profit)}`}
                  >
                    {day.date}
                    <div className="pointer-events-none absolute -top-3 left-1/2 z-10 w-max -translate-x-1/2 -translate-y-full rounded-xl border border-border bg-surface/95 px-3 py-2 text-left text-xs opacity-0 shadow-2xl transition-opacity duration-200 group-hover:opacity-100">
                      <p className="font-semibold text-white">{day.date} novembre 2025</p>
                      <p
                        className={`mt-1 font-bold ${
                          day.profit > 0 ? 'text-green-400' : day.profit < 0 ? 'text-red-400' : 'text-muted-foreground'
                        }`}
                      >
                        {day.profit > 0 ? '+' : ''}
                        {day.profit.toFixed(2)}€
                      </p>
                      <p className="text-[11px] text-muted-foreground">{day.bets} paris</p>
                    </div>
                  </div>
                </div>
              ))}
            </div>

            <div className="mt-6 flex items-center justify-between text-xs text-muted-foreground">
              <span>Moins de profit</span>
              <div className="flex gap-1">
                <div className="h-4 w-4 rounded bg-surface" />
                <div className="h-4 w-4 rounded bg-green-500/20" />
                <div className="h-4 w-4 rounded bg-green-500/30" />
                <div className="h-4 w-4 rounded bg-green-500/40" />
              </div>
              <span>Plus de profit</span>
            </div>
          </Card>
        </div>
      </div>
    </div>
  )
}
