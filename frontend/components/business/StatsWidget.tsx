'use client';
import { formatNumber } from "@/lib/format";

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { TrendingUp, TrendingDown, Minus, LucideIcon } from 'lucide-react';
import { cn } from '@/lib/utils';

interface StatsWidgetProps {
  title: string;
  value: string | number;
  change?: number;
  changeLabel?: string;
  icon: LucideIcon;
  iconColor?: string;
  iconBgColor?: string;
  format?: 'number' | 'currency' | 'percentage';
  decimals?: number;
  loading?: boolean;
}

export function StatsWidget({
  title,
  value,
  change,
  changeLabel = '24h',
  icon: Icon,
  iconColor = 'text-blue-500',
  iconBgColor = 'bg-blue-500/10',
  format = 'number',
  decimals = 2,
  loading = false,
}: StatsWidgetProps) {
  // Formater la valeur selon le type
  const formatValue = (val: string | number): string => {
    const numValue = typeof val === 'string' ? parseFloat(val) : val;
    
    if (isNaN(numValue)) return val.toString();
    
    switch (format) {
      case 'currency':
        return `${formatNumber(numValue, decimals)}€`;
      case 'percentage':
        return `${formatNumber(numValue, decimals)}%`;
      default:
        return numValue.toLocaleString('fr-FR', {
          minimumFractionDigits: 0,
          maximumFractionDigits: decimals,
        });
    }
  };

  // Déterminer l'icône et la couleur de la tendance
  const getTrendIcon = () => {
    if (!change || change === 0) return Minus;
    return change > 0 ? TrendingUp : TrendingDown;
  };

  const getTrendColor = () => {
    if (!change || change === 0) return 'text-slate-400';
    return change > 0 ? 'text-green-500' : 'text-red-500';
  };

  const TrendIcon = getTrendIcon();
  const trendColor = getTrendColor();

  if (loading) {
    return (
      <Card>
        <CardHeader className="flex flex-row items-center justify-between pb-2">
          <CardTitle className="text-sm font-medium text-muted-foreground">
            {title}
          </CardTitle>
          <div className={cn('p-2 rounded-lg', iconBgColor)}>
            <Icon className={cn('h-4 w-4', iconColor)} />
          </div>
        </CardHeader>
        <CardContent>
          <div className="h-8 bg-slate-700/50 rounded animate-pulse mb-2" />
          <div className="h-4 bg-slate-700/30 rounded animate-pulse w-20" />
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className="hover:shadow-lg transition-shadow">
      <CardHeader className="flex flex-row items-center justify-between pb-2">
        <CardTitle className="text-sm font-medium text-muted-foreground">
          {title}
        </CardTitle>
        <div className={cn('p-2 rounded-lg', iconBgColor)}>
          <Icon className={cn('h-4 w-4', iconColor)} />
        </div>
      </CardHeader>
      <CardContent>
        <div className="text-2xl font-bold text-white mb-1">
          {formatValue(value)}
        </div>
        {change !== undefined && (
          <div className="flex items-center gap-1 text-xs">
            <TrendIcon className={cn('h-3 w-3', trendColor)} />
            <span className={trendColor}>
              {change > 0 ? '+' : ''}{formatNumber(change || 0, 2)}%
            </span>
            <span className="text-muted-foreground ml-1">{changeLabel}</span>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
