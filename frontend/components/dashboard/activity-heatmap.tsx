'use client'

import { useState } from 'react'
import { motion } from 'framer-motion'

import { Card } from '@/components/ui/card'
import { cn } from '@/lib/utils'
import type { HeatmapDay } from '@/types/api'

interface ActivityHeatmapProps {
  data: HeatmapDay[]
  monthLabel: string
}

const dayNames = ['Lun', 'Mar', 'Mer', 'Jeu', 'Ven', 'Sam', 'Dim']

const getColorIntensity = (profit: number) => {
  if (profit === 0) return 'bg-surface text-text-muted hover:bg-surface-hover'
  if (profit > 150) return 'bg-success/40 text-success hover:bg-success/60'
  if (profit > 80) return 'bg-success/30 text-success hover:bg-success/50'
  if (profit > 0) return 'bg-success/20 text-success hover:bg-success/40'
  if (profit > -50) return 'bg-danger/20 text-danger hover:bg-danger/40'
  return 'bg-danger/35 text-danger hover:bg-danger/55'
}

const currency = (value: number) =>
  Intl.NumberFormat('fr-FR', {
    style: 'currency',
    currency: 'EUR',
    maximumFractionDigits: 0,
  }).format(value)

export function ActivityHeatmap({ data, monthLabel }: ActivityHeatmapProps) {
  const [hoveredDay, setHoveredDay] = useState<string | null>(null)

  return (
    <Card className="relative overflow-hidden border border-border/60 bg-surface/85 p-6 shadow-inner-glow">
      <div className="absolute inset-0 bg-gradient-to-br from-primary/5 via-transparent to-success/10 opacity-0 blur-3xl transition-opacity duration-500 hover:opacity-100" />
      <div className="relative space-y-6">
        <div>
          <h3 className="text-xl font-bold text-text-primary">{monthLabel}</h3>
          <p className="text-sm text-text-muted">Activité quotidienne des performances</p>
        </div>

        <div className="grid grid-cols-7 gap-3 text-center text-xs font-medium uppercase tracking-wide text-text-muted">
          {dayNames.map((day) => (
            <div key={day}>{day}</div>
          ))}
        </div>

        <div className="grid grid-cols-7 gap-3">
          {data.map((day, index) => (
            <motion.div
              key={day.date}
              initial={{ opacity: 0, scale: 0.85 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ duration: 0.2, delay: index * 0.015 }}
              onMouseEnter={() => setHoveredDay(day.date)}
              onMouseLeave={() => setHoveredDay(null)}
              className="relative"
            >
              <div
                className={cn(
                  'flex aspect-square items-center justify-center rounded-xl text-sm font-semibold transition-all duration-200',
                  getColorIntensity(day.profit),
                  hoveredDay === day.date && 'scale-110 shadow-lg shadow-primary/30',
                )}
              >
                {day.day}
              </div>
              {hoveredDay === day.date ? (
                <motion.div
                  initial={{ opacity: 0, y: 8 }}
                  animate={{ opacity: 1, y: 0 }}
                  className="absolute -top-3 left-1/2 w-max -translate-x-1/2 -translate-y-full rounded-2xl border border-border bg-background/95 px-3 py-2 text-left text-xs shadow-lg"
                >
                  <p className="font-semibold text-text-primary">
                    {day.date}
                  </p>
                  <p
                    className={cn(
                      'mt-1 font-semibold',
                      day.profit > 0 ? 'text-success' : day.profit < 0 ? 'text-danger' : 'text-text-muted',
                    )}
                  >
                    {day.profit > 0 ? '+' : ''}
                    {currency(day.profit)}
                  </p>
                  <p className="text-[11px] text-text-muted">Paris analysés : {Math.max(1, Math.round(Math.abs(day.profit) / 40))}</p>
                </motion.div>
              ) : null}
            </motion.div>
          ))}
        </div>

        <div className="flex items-center justify-between text-xs text-text-muted">
          <span>Moins performant</span>
          <div className="flex items-center gap-2">
            <span className="h-3 w-6 rounded bg-danger/30" />
            <span className="h-3 w-6 rounded bg-surface" />
            <span className="h-3 w-6 rounded bg-success/25" />
            <span className="h-3 w-6 rounded bg-success/45" />
          </div>
          <span>Plus performant</span>
        </div>
      </div>
    </Card>
  )
}

