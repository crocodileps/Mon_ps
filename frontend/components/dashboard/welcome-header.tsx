'use client'

import { motion } from 'framer-motion'
import { DollarSign, TrendingUp } from 'lucide-react'

import { Card } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { cn } from '@/lib/utils'

interface Highlight {
  bookmaker: string
  profit: number
}

interface WelcomeHeaderProps {
  userName: string
  openBets: number
  openExposure: number
  potentialReturn: number
  highlights: Highlight[]
}

const currency = (value: number) =>
  Intl.NumberFormat('fr-FR', {
    style: 'currency',
    currency: 'EUR',
    maximumFractionDigits: 0,
  }).format(value)

export function WelcomeHeader({
  userName,
  openBets,
  openExposure,
  potentialReturn,
  highlights,
}: WelcomeHeaderProps) {
  return (
    <Card className="relative overflow-hidden border border-purple-500/20 bg-gradient-to-br from-purple-500/10 via-background to-pink-500/10">
      <div className="absolute inset-0 bg-gradient-to-r from-purple-500/10 to-pink-500/10 blur-3xl" />
      <div className="relative space-y-6 p-8">
        <motion.div
          initial={{ opacity: 0, x: -20 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ duration: 0.5 }}
          className="space-y-4"
        >
          <div className="flex flex-wrap items-center gap-3">
            <span className="rounded-full border border-primary/30 bg-primary/10 px-3 py-1 text-xs font-semibold uppercase tracking-widest text-primary">
              Dashboard Quant
            </span>
            <div className="flex items-center gap-2 text-xs uppercase tracking-widest text-text-muted">
              <DollarSign className="h-4 w-4 text-success" />
              Performances en direct
            </div>
          </div>
          <h1 className="text-4xl font-bold leading-tight text-text-primary sm:text-5xl">
            Heureux retour,{' '}
            <span className="bg-gradient-to-r from-purple-400 to-pink-400 bg-clip-text text-transparent">
              {userName}
            </span>
            .
          </h1>
          <p className="text-lg text-text-secondary">
            Vous avez{' '}
            <span className="text-success font-semibold">{openBets} paris</span> ouverts, exposant{' '}
            <span className="text-primary font-semibold">{currency(openExposure)}</span>, pour un retour potentiel de{' '}
            <span className="text-success font-semibold">{currency(potentialReturn)}</span>.
          </p>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.4, delay: 0.1 }}
          className="flex flex-wrap items-center gap-3"
        >
          <div className="flex items-center gap-2 text-sm text-text-muted">
            <TrendingUp className="h-4 w-4 text-success" />
            Bookmakers les plus performants :
          </div>
          <div className="flex flex-wrap gap-2">
            {highlights.map((item, index) => (
              <motion.div
                key={item.bookmaker}
                initial={{ opacity: 0, scale: 0.85 }}
                animate={{ opacity: 1, scale: 1 }}
                transition={{ duration: 0.3, delay: 0.1 + index * 0.08 }}
              >
                <Badge
                  className={cn(
                    'rounded-full border border-success/30 bg-success/15 px-4 py-1 text-sm font-semibold text-success shadow-sm shadow-success/30',
                  )}
                >
                  {item.bookmaker} +{currency(item.profit)}
                </Badge>
              </motion.div>
            ))}
          </div>
        </motion.div>
      </div>
    </Card>
  )
}

