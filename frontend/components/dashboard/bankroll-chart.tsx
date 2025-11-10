'use client'

import {
  Area,
  AreaChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import type { BankrollPoint } from '@/types/api'

interface BankrollChartProps {
  data: BankrollPoint[]
}

export function BankrollChart({ data }: BankrollChartProps) {
  return (
    <Card className="card-hover border border-primary/20 bg-gradient-to-br from-primary/10 via-surface/80 to-success/10">
      <CardHeader className="pb-0">
        <CardTitle className="text-lg font-semibold text-text-primary">
          Évolution de la bankroll
        </CardTitle>
        <CardDescription className="text-text-muted">90 derniers jours</CardDescription>
      </CardHeader>
      <CardContent className="pt-6">
        <div className="h-[320px] w-full">
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={data}>
              <defs>
                <linearGradient id="bankrollGradient" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#8b5cf6" stopOpacity={0.65} />
                  <stop offset="95%" stopColor="#8b5cf6" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(30, 41, 59, 0.4)" />
              <XAxis dataKey="date" stroke="rgba(148, 163, 184, 0.8)" tickLine={false} />
              <YAxis
                stroke="rgba(148, 163, 184, 0.8)"
                tickLine={false}
                tickFormatter={(value) =>
                  Intl.NumberFormat('fr-FR', { style: 'currency', currency: 'EUR', maximumFractionDigits: 0 }).format(
                    value,
                  )
                }
              />
              <Tooltip
                contentStyle={{
                  backgroundColor: '#141419',
                  border: '1px solid rgba(30, 41, 59, 0.6)',
                  borderRadius: 12,
                  color: '#f8fafc',
                }}
                labelStyle={{ color: '#94a3b8' }}
                formatter={(value: number) =>
                  Intl.NumberFormat('fr-FR', { style: 'currency', currency: 'EUR', maximumFractionDigits: 0 }).format(
                    value,
                  )
                }
              />
              <Area
                type="monotone"
                dataKey="balance"
                stroke="#8b5cf6"
                strokeWidth={2.4}
                fill="url(#bankrollGradient)"
              />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      </CardContent>
    </Card>
  )
}

