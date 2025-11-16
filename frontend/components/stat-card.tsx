'use client'

import { Card, CardContent } from '@/components/ui/card'
import { type LucideIcon } from 'lucide-react'

interface StatCardProps {
  label: string
  value: string | number
  icon?: LucideIcon
  trend?: 'up' | 'down' | 'neutral'
  color?: 'primary' | 'secondary' | 'accent' | 'green' | 'red'
}

const colorMap = {
  primary: 'text-primary',
  secondary: 'text-secondary',
  accent: 'text-accent',
  green: 'text-green-400',
  red: 'text-red-400',
}

export function StatCard({ label, value, icon: Icon, trend, color = 'accent' }: StatCardProps) {
  return (
    <Card className="glass bg-card/50">
      <CardContent className="p-4">
        <div className="flex items-start justify-between">
          <div>
            <p className="text-sm text-muted-foreground mb-1">{label}</p>
            <p className={`text-2xl font-bold ${colorMap[color]}`}>{value}</p>
          </div>
          {Icon && <Icon className={`${colorMap[color]} opacity-60`} size={24} />}
        </div>
      </CardContent>
    </Card>
  )
}
