'use client'
import { formatNumber } from "@/lib/format";

import { motion } from 'framer-motion'
import { TrendingDown, TrendingUp, type LucideIcon } from 'lucide-react'

import { Card } from '@/components/ui/card'
import { AnimatedNumber } from '@/components/ui/animated-number'
import { cn } from '@/lib/utils'

type StatFormat = 'currency' | 'percentage' | 'number'

interface StatCardProps {
  label: string
  value: number
  change?: number
  trend?: 'up' | 'down'
  icon: LucideIcon
  format?: StatFormat
}

const formatConfig: Record<StatFormat, { prefix: string; suffix: string; decimals: number }> = {
  currency: { prefix: '', suffix: '€', decimals: 0 },
  percentage: { prefix: '', suffix: '%', decimals: 1 },
  number: { prefix: '', suffix: '', decimals: 2 },
}

export function StatCard({
  label,
  value,
  change,
  trend,
  icon: Icon,
  format = 'number',
}: StatCardProps) {
  const { prefix, suffix, decimals } = formatConfig[format]

  return (
    <motion.div whileHover={{ scale: 1.02, y: -4 }} transition={{ duration: 0.2 }}>
      <Card className="group relative overflow-hidden border border-border/60 bg-surface/80 transition-all duration-300 hover:shadow-2xl hover:shadow-primary/20">
        <div className="pointer-events-none absolute inset-0 bg-gradient-to-br from-primary/5 via-transparent to-transparent opacity-0 transition-opacity duration-300 group-hover:opacity-100" />
        <div className="relative p-6">
          <div className="mb-6 flex items-center justify-between">
            <span className="text-sm font-medium uppercase tracking-[0.3em] text-text-muted">{label}</span>
            <div className="rounded-xl border border-primary/20 bg-primary/10 p-2 text-primary transition-colors duration-300 group-hover:bg-primary/20">
              <Icon className="h-5 w-5" />
            </div>
          </div>
          <div className="space-y-3">
            <div className="text-3xl font-bold text-text-primary">
              <AnimatedNumber value={value} decimals={decimals} prefix={prefix} suffix={suffix} />
            </div>
            {typeof change === 'number' ? (
              <div className="flex items-center gap-2 text-sm font-semibold">
                {trend === 'down' ? (
                  <TrendingDown className="h-4 w-4 text-danger" />
                ) : (
                  <TrendingUp className="h-4 w-4 text-success" />
                )}
                <span className={cn(trend === 'down' ? 'text-danger' : 'text-success')}>
                  {trend === 'down' ? '' : '+'}
                  {formatNumber(change, 1)}%
                </span>
              </div>
            ) : null}
          </div>
        </div>
      </Card>
    </motion.div>
  )
}

