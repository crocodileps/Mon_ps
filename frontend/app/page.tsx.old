'use client'

import { Activity, Target, TrendingUp, Wallet, Loader2, ArrowUpRight } from 'lucide-react'
import { formatNumber } from "@/lib/format"
import { Badge } from '@/components/ui/badge'
import { Card } from '@/components/ui/card'
import { useBankrollStats, useGlobalStats } from '@/hooks/use-stats'
import { useOpportunities } from '@/hooks/use-opportunities'
import { LineChart, Line, ResponsiveContainer } from 'recharts'
import { motion } from 'framer-motion'

export default function DashboardPage() {
  const { data: bankroll, isLoading: loadingBankroll } = useBankrollStats()
  const { data: global, isLoading: loadingGlobal } = useGlobalStats()
  const { data: opportunities, isLoading: loadingOpps } = useOpportunities({ limit: 10, min_edge: 1.0 })

  const isLoading = loadingBankroll || loadingGlobal || loadingOpps

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-screen">
        <Loader2 className="w-8 h-8 animate-spin text-violet-500" />
      </div>
    )
  }

  const stats = [
    {
      label: 'Bankroll',
      value: `${formatNumber(bankroll?.current_bankroll ?? 0, 0)}€`,
      change: bankroll?.roi ? `+${formatNumber(bankroll.roi, 1)}%` : '0%',
      icon: Wallet,
      color: 'text-green-500'
    },
    {
      label: 'ROI',
      value: `${formatNumber(bankroll?.roi ?? 0, 1)}%`,
      change: bankroll?.total_bets ? `${bankroll.total_bets} paris` : '0 paris',
      icon: TrendingUp,
      color: 'text-blue-500'
    },
    {
      label: 'Win Rate',
      value: `${formatNumber(bankroll?.win_rate ?? 0, 1)}%`,
      change: `${bankroll?.won_bets ?? 0}W / ${bankroll?.lost_bets ?? 0}L`,
      icon: Target,
      color: 'text-purple-500'
    },
    {
      label: 'Profit',
      value: `${formatNumber(bankroll?.total_profit ?? 0, 0)}€`,
      change: `${formatNumber(bankroll?.total_staked ?? 0, 0)}€ misé`,
      icon: Activity,
      color: 'text-orange-500'
    },
  ]

  const sparklineData = Array.from({ length: 10 }, (_, i) => ({
    value: 1000 + ((bankroll?.total_profit ?? 0) / 10) * (i + 1)
  }))

  return (
    <div className="min-h-screen bg-black p-6 md:p-8">
      <div className="max-w-7xl mx-auto space-y-6">
        
        <div>
          <h1 className="text-4xl font-bold text-white mb-2">
            Dashboard 📊
          </h1>
          <p className="text-gray-400">
            Vue d'ensemble de vos performances de trading
          </p>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {stats.map((stat, index) => (
            <motion.div
              key={stat.label}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: index * 0.1 }}
            >
              <Card className="relative overflow-hidden bg-gradient-to-br from-gray-900/90 to-gray-900/50 border-gray-800 backdrop-blur-sm hover:border-violet-500/50 transition-all duration-300">
                <div className="p-6">
                  <div className="flex items-center justify-between mb-4">
                    <div className={`p-2 rounded-lg bg-gray-800/50 ${stat.color}`}>
                      <stat.icon className="w-5 h-5" />
                    </div>
                    <Badge variant="outline" className="text-xs border-gray-700">
                      {stat.change}
                    </Badge>
                  </div>
                  <div>
                    <p className="text-sm text-gray-400 mb-1">{stat.label}</p>
                    <p className="text-2xl font-bold text-white">{stat.value}</p>
                  </div>
                  
                  <div className="mt-4 -mb-2 h-8">
                    <ResponsiveContainer width="100%" height="100%">
                      <LineChart data={sparklineData}>
                        <Line
                          type="monotone"
                          dataKey="value"
                          stroke="#8b5cf6"
                          strokeWidth={1.5}
                          dot={false}
                        />
                      </LineChart>
                    </ResponsiveContainer>
                  </div>
                </div>
              </Card>
            </motion.div>
          ))}
        </div>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.4 }}
        >
          <Card className="bg-gradient-to-br from-gray-900/90 to-gray-900/50 border-gray-800 backdrop-blur-sm">
            <div className="p-6">
              <div className="flex items-center justify-between mb-6">
                <h2 className="text-xl font-semibold text-white flex items-center gap-2">
                  ⚡ Opportunités Live
                </h2>
                <Badge className="bg-violet-500/20 text-violet-400 border-violet-500/30">
                  {opportunities?.length ?? 0} actives
                </Badge>
              </div>

              <div className="space-y-3">
                {opportunities?.slice(0, 5).map((opp: any, idx: number) => (
                  <motion.div
                    key={idx}
                    initial={{ opacity: 0, x: -20 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: 0.5 + idx * 0.1 }}
                    className="flex items-center justify-between p-4 rounded-lg bg-gray-800/30 border border-gray-700/50 hover:border-violet-500/50 transition-all"
                  >
                    <div className="flex-1">
                      <p className="text-white font-medium">{opp.match_id || 'Match'}</p>
                      <p className="text-sm text-gray-400">
                        {opp.outcome} • {opp.nb_bookmakers} bookmakers
                      </p>
                    </div>
                    <div className="text-right">
                      <div className="flex items-center gap-1 text-green-400 font-bold">
                        <ArrowUpRight className="w-4 h-4" />
                        {formatNumber(opp.edge_pct ?? 0, 1)}%
                      </div>
                      <p className="text-xs text-gray-500">
                        Cote: {formatNumber(opp.max_odds ?? 0, 2)}
                      </p>
                    </div>
                  </motion.div>
                ))}
                
                {(!opportunities || opportunities.length === 0) && (
                  <div className="text-center py-8 text-gray-500">
                    Aucune opportunité détectée actuellement
                  </div>
                )}
              </div>
            </div>
          </Card>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.6 }}
          className="grid grid-cols-1 md:grid-cols-3 gap-4"
        >
          <Card className="bg-gradient-to-br from-gray-900/90 to-gray-900/50 border-gray-800">
            <div className="p-6">
              <h3 className="text-lg font-semibold text-white mb-4">�� Paris</h3>
              <div className="space-y-3">
                <div className="flex justify-between">
                  <span className="text-gray-400">Total</span>
                  <span className="text-white font-medium">{bankroll?.total_bets ?? 0}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-400">Gagnés</span>
                  <span className="text-green-400 font-medium">{bankroll?.won_bets ?? 0}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-400">Perdus</span>
                  <span className="text-red-400 font-medium">{bankroll?.lost_bets ?? 0}</span>
                </div>
              </div>
            </div>
          </Card>

          <Card className="bg-gradient-to-br from-gray-900/90 to-gray-900/50 border-gray-800">
            <div className="p-6">
              <h3 className="text-lg font-semibold text-white mb-4">💰 Financier</h3>
              <div className="space-y-3">
                <div className="flex justify-between">
                  <span className="text-gray-400">Misé</span>
                  <span className="text-white font-medium">{formatNumber(bankroll?.total_staked ?? 0, 0)}€</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-400">Profit</span>
                  <span className="text-green-400 font-medium">+{formatNumber(bankroll?.total_profit ?? 0, 0)}€</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-400">ROI</span>
                  <span className="text-blue-400 font-medium">{formatNumber(bankroll?.roi ?? 0, 1)}%</span>
                </div>
              </div>
            </div>
          </Card>

          <Card className="bg-gradient-to-br from-gray-900/90 to-gray-900/50 border-gray-800">
            <div className="p-6">
              <h3 className="text-lg font-semibold text-white mb-4">�� Performance</h3>
              <div className="space-y-3">
                <div className="flex justify-between">
                  <span className="text-gray-400">Win Rate</span>
                  <span className="text-purple-400 font-medium">{formatNumber(bankroll?.win_rate ?? 0, 1)}%</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-400">Bankroll</span>
                  <span className="text-white font-medium">{formatNumber(bankroll?.current_bankroll ?? 0, 0)}€</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-400">Pending</span>
                  <span className="text-yellow-400 font-medium">{bankroll?.pending_bets ?? 0}</span>
                </div>
              </div>
            </div>
          </Card>
        </motion.div>

      </div>
    </div>
  )
}
