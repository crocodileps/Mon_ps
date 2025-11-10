import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { cn } from '@/lib/utils'
import type { Opportunity } from '@/types/api'

interface TopOpportunitiesProps {
  data: Opportunity[]
}

const formatDate = (value: string) =>
  new Date(value).toLocaleDateString('fr-FR', {
    day: '2-digit',
    month: 'short',
    hour: '2-digit',
    minute: '2-digit',
  })

export function TopOpportunities({ data }: TopOpportunitiesProps) {
  return (
    <Card className="card-hover border border-primary/20 bg-gradient-to-br from-primary/10 via-surface/70 to-emerald-500/10">
      <CardHeader className="pb-0">
        <CardTitle className="text-lg font-semibold text-text-primary">🎯 Top opportunités</CardTitle>
        <CardDescription className="text-text-muted">Edge supérieur à 10%</CardDescription>
      </CardHeader>
      <CardContent className="pt-6">
        <div className="space-y-3">
          {data.map((opp) => {
            const edgeTone = opp.edge_pct > 15 ? 'bg-success/15 text-success' : opp.edge_pct > 10 ? 'bg-warning/15 text-warning' : 'bg-surface-hover text-text-secondary'

            return (
              <div
                key={opp.id}
                className="flex items-center gap-4 rounded-2xl border border-border/60 bg-surface-hover/40 p-4 transition-colors hover:border-primary/40 hover:bg-surface-hover/80"
              >
                <div>
                  <p className="text-sm font-semibold text-text-primary">
                    {opp.home_team} vs {opp.away_team}
                  </p>
                  <p className="mt-1 text-xs text-text-muted uppercase tracking-wide">
                    {opp.sport} · {formatDate(opp.commence_time)}
                  </p>
                  <p className="mt-2 text-sm text-text-secondary">
                    {opp.outcome}{' '}
                    <span className="number text-primary">
                      {opp.best_odds.toFixed(2)}
                    </span>{' '}
                    @ {opp.bookmaker_best}
                  </p>
                </div>
                <div className="flex items-center gap-3">
                  <Badge variant="secondary" className={cn('rounded-full px-3 py-1 text-sm font-semibold', edgeTone)}>
                    {opp.edge_pct.toFixed(1)}% Edge
                  </Badge>
                  <Button size="sm" className="rounded-full px-4">
                    Place Bet
                  </Button>
                </div>
              </div>
            )
          })}
        </div>
      </CardContent>
    </Card>
  )
}

