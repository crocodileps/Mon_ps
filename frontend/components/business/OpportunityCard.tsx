'use client';
import { formatNumber } from "@/lib/format";

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { TrendingUp, Clock, Target } from 'lucide-react';

interface OpportunityCardProps {
  match_id: string;
  home_team: string;
  away_team: string;
  sport: string;
  commence_time: string;
  outcome: string;
  best_odd: string;
  bookmaker_best: string;
  spread_pct: number;
  nb_bookmakers: number;
  onPlaceBet?: () => void;
}

export function OpportunityCard(props: OpportunityCardProps) {
  const { home_team, away_team, sport, commence_time, outcome, best_odd, bookmaker_best, spread_pct, nb_bookmakers, onPlaceBet } = props;
  
  const date = new Date(commence_time);
  const dateStr = date.toLocaleDateString('fr-FR', { day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit' });
  const badgeColor = spread_pct >= 15 ? 'bg-green-500/20 text-green-500' : spread_pct >= 10 ? 'bg-yellow-500/20 text-yellow-500' : 'bg-blue-500/20 text-blue-500';

  return (
    <Card className="hover:shadow-lg transition-shadow">
      <CardHeader className="pb-3">
        <div className="flex items-start justify-between">
          <div className="flex-1">
            <CardTitle className="text-lg font-bold">{home_team} vs {away_team}</CardTitle>
            <div className="flex items-center gap-2 mt-1 text-sm text-muted-foreground">
              <Badge variant="outline" className="text-xs">{sport}</Badge>
              <span className="flex items-center gap-1"><Clock className="h-3 w-3" />{dateStr}</span>
            </div>
          </div>
          <Badge className={badgeColor}><TrendingUp className="h-3 w-3 mr-1" />{formatNumber(spread_pct, 1)}%</Badge>
        </div>
      </CardHeader>
      <CardContent className="space-y-3">
        <div className="flex items-center justify-between p-3 bg-secondary/50 rounded-lg">
          <div><p className="text-xs text-muted-foreground mb-1">Pronostic</p><p className="font-semibold">{outcome}</p></div>
          <div className="text-right"><p className="text-xs text-muted-foreground mb-1">Meilleure cote</p><p className="text-2xl font-bold">{formatNumber(best_odd, 2)}</p></div>
        </div>
        <div className="flex items-center justify-between text-sm">
          <div className="flex items-center gap-2"><Target className="h-4 w-4 text-muted-foreground" /><span className="text-muted-foreground">Bookmaker:</span><span className="font-medium">{bookmaker_best}</span></div>
          <span className="text-xs text-muted-foreground">{nb_bookmakers} bookmakers</span>
        </div>
        {onPlaceBet && <Button className="w-full" onClick={onPlaceBet}>Placer un pari</Button>}
      </CardContent>
    </Card>
  );
}
