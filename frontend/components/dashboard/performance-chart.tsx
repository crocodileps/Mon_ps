'use client'

import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import type { PerformancePoint } from '@/types/api'

interface PerformanceChartProps {
  data: PerformancePoint[]
}

export function PerformanceChart({ data }: PerformanceChartProps) {
  return (
    <Card className="card-hover border border-purple-500/20 bg-gradient-to-br from-purple-500/10 via-surface/80 to-pink-500/10">
      <CardHeader className="pb-0">
        <CardTitle className="text-lg font-semibold text-text-primary">
          Performance Tabac vs Ligne
        </CardTitle>
        <CardDescription className="text-text-muted">Derniers 30 jours</CardDescription>
      </CardHeader>
      <CardContent className="pt-6">
        <div className="h-[320px] w-full">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={data}>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(30, 41, 59, 0.45)" />
              <XAxis dataKey="date" stroke="rgba(148, 163, 184, 0.8)" tickLine={false} />
              <YAxis stroke="rgba(148, 163, 184, 0.8)" tickLine={false} tickFormatter={(value) => `${value}%`} />
              <Tooltip
                contentStyle={{
                  backgroundColor: '#141419',
                  border: '1px solid rgba(30, 41, 59, 0.6)',
                  borderRadius: 12,
                  color: '#f8fafc',
                }}
                labelStyle={{ color: '#94a3b8' }}
              />
              <Legend />
              <Line
                type="monotone"
                dataKey="tabac_roi"
                name="ROI Tabac"
                stroke="#8b5cf6"
                strokeWidth={2.4}
                dot={{ fill: '#8b5cf6', r: 4 }}
                activeDot={{ r: 6 }}
              />
              <Line
                type="monotone"
                dataKey="ligne_roi"
                name="ROI Ligne"
                stroke="#10b981"
                strokeWidth={2.4}
                dot={{ fill: '#10b981', r: 4 }}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </CardContent>
    </Card>
  )
}

