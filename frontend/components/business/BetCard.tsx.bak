'use client';

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { TrendingUp, TrendingDown, Clock, DollarSign } from 'lucide-react';

interface BetCardProps {
  id: number;
  outcome: string;
  bookmaker: string;
  odds_value: number;
  stake: number;
  bet_type: 'tabac' | 'ligne';
  result?: 'won' | 'lost' | 'pending' | null;
  actual_profit?: number | null;
  created_at: string;
  onEdit?: () => void;
  onDelete?: () => void;
}

export function BetCard(props: BetCardProps) {
  const { id, outcome, bookmaker, odds_value, stake, bet_type, result, actual_profit, created_at, onEdit, onDelete } = props;
  const date = new Date(created_at);
  const dateStr = date.toLocaleDateString('fr-FR', { day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit' });
  const resultBadge = result === 'won' ? 'bg-green-500/20 text-green-500' : result === 'lost' ? 'bg-red-500/20 text-red-500' : 'bg-yellow-500/20 text-yellow-500';
  const TrendIcon = result === 'won' ? TrendingUp : result === 'lost' ? TrendingDown : Clock;
  const resultText = result === 'won' ? 'Gagné' : result === 'lost' ? 'Perdu' : 'En cours';

  return (
    <Card className="hover:shadow-lg transition-shadow">
      <CardHeader className="pb-3">
        <div className="flex items-start justify-between">
          <div className="flex-1">
            <div className="flex items-center gap-2">
              <CardTitle className="text-lg font-bold">Pari #{id}</CardTitle>
              <Badge variant="outline" className="text-xs">{bet_type === 'tabac' ? '🏪 Tabac' : '📱 Ligne'}</Badge>
            </div>
            <p className="text-sm text-muted-foreground mt-1">{dateStr}</p>
          </div>
          {result && <Badge className={resultBadge}><TrendIcon className="h-3 w-3" /><span className="ml-1">{resultText}</span></Badge>}
        </div>
      </CardHeader>
      <CardContent className="space-y-3">
        <div className="grid grid-cols-2 gap-3">
          <div className="p-3 bg-secondary/50 rounded-lg"><p className="text-xs text-muted-foreground mb-1">Pronostic</p><p className="font-semibold">{outcome}</p></div>
          <div className="p-3 bg-secondary/50 rounded-lg"><p className="text-xs text-muted-foreground mb-1">Cote</p><p className="font-bold text-xl">{Number(odds_value).toFixed(2)}</p></div>
        </div>
        <div className="flex items-center justify-between p-3 bg-secondary/50 rounded-lg">
          <div><p className="text-xs text-muted-foreground mb-1">Mise</p><p className="font-semibold flex items-center gap-1"><DollarSign className="h-4 w-4" />{Number(stake).toFixed(2)}€</p></div>
          {actual_profit !== null && actual_profit !== undefined && <div className="text-right"><p className="text-xs text-muted-foreground mb-1">Profit</p><p className={`font-bold text-lg ${actual_profit >= 0 ? 'text-green-500' : 'text-red-500'}`}>{actual_profit >= 0 ? '+' : ''}{Number(actual_profit).toFixed(2)}€</p></div>}
        </div>
        <div className="flex items-center justify-between text-sm"><span className="text-muted-foreground">Bookmaker:</span><span className="font-medium">{bookmaker}</span></div>
        {(onEdit || onDelete) && <div className="flex gap-2 pt-2">{onEdit && <Button variant="outline" className="flex-1" onClick={onEdit}>Modifier</Button>}{onDelete && <Button variant="destructive" className="flex-1" onClick={onDelete}>Supprimer</Button>}</div>}
      </CardContent>
    </Card>
  );
}
