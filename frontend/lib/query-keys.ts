export const queryKeys = {
  opportunities: {
    all: ['opportunities'] as const,
    list: (filters?: Record<string, unknown>) =>
      ['opportunities', { ...filters }] as const,
    detail: (id: string | number) => ['opportunities', id] as const,
  },
  bets: {
    all: ['bets'] as const,
    list: (filters?: Record<string, unknown>) => ['bets', { ...filters }] as const,
  },
  analytics: {
    summary: ['analytics', 'summary'] as const,
    clvTrend: ['analytics', 'clv-trend'] as const,
    bankroll: ['analytics', 'bankroll'] as const,
  },
  dashboard: {
    metrics: ['dashboard', 'metrics'] as const,
    performance: ['dashboard', 'performance'] as const,
    bankroll: ['dashboard', 'bankroll'] as const,
    heatmap: ['dashboard', 'heatmap'] as const,
    topOpportunities: ['dashboard', 'top-opportunities'] as const,
  },
} as const

