'use client';
import { formatNumber, formatEuro } from '@/lib/format';

import { useBets } from '@/hooks/use-bets';
import { Card, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { ChevronRight, Clock } from 'lucide-react';
import Link from 'next/link';

interface ActiveBetsPreviewProps {
  limit?: number;
}

export function ActiveBetsPreview({ limit = 5 }: ActiveBetsPreviewProps) {
  const { data: bets = [], isLoading, error } = useBets();

  // Filtrer les paris actifs (pending) et prendre les N derniers
  const activeBets = bets
    .filter((bet) => bet.result === 'pending' || !bet.result)
    .slice(0, limit);

  const getTypeBadge = (type: string) => {
    if (type === 'tabac') {
      return <Badge variant="outline">🏪 Tabac</Badge>;
    }
    if (type === 'ligne') {
      return <Badge variant="outline">📱 Ligne</Badge>;
    }
    return <Badge variant="outline">{type}</Badge>;
  };

  if (isLoading) {
    return (
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Clock className="h-5 w-5 text-yellow-500" />
              <CardTitle>Paris Actifs</CardTitle>
            </div>
          </div>
        </CardHeader>
        <div className="p-6">
          <div className="space-y-3">
            {[1, 2, 3].map((i) => (
              <div key={i} className="h-12 bg-slate-800/50 rounded animate-pulse" />
            ))}
          </div>
        </div>
      </Card>
    );
  }

  if (error) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Paris Actifs</CardTitle>
        </CardHeader>
        <div className="p-6 text-center text-red-400">
          Erreur lors du chargement des paris
        </div>
      </Card>
    );
  }

  if (activeBets.length === 0) {
    return (
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <div className="flex items-center gap-2">
                <Clock className="h-5 w-5 text-yellow-500" />
                <CardTitle>Paris Actifs</CardTitle>
              </div>
              <CardDescription className="mt-1">
                Aucun pari en cours
              </CardDescription>
            </div>
            <Link href="/bets">
              <Button variant="ghost" size="sm">
                Historique
                <ChevronRight className="ml-1 h-4 w-4" />
              </Button>
            </Link>
          </div>
        </CardHeader>
        <div className="p-6 text-center text-slate-400">
          <p>Vous n'avez aucun pari en cours</p>
          <Link href="/opportunities">
            <Button className="mt-4">
              Trouver des opportunités
            </Button>
          </Link>
        </div>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div>
            <div className="flex items-center gap-2">
              <Clock className="h-5 w-5 text-yellow-500" />
              <CardTitle>Paris Actifs</CardTitle>
            </div>
            <CardDescription className="mt-1">
              {activeBets.length} pari{activeBets.length > 1 ? 's' : ''} en cours
            </CardDescription>
          </div>
          <Link href="/bets">
            <Button variant="ghost" size="sm">
              Voir tout
              <ChevronRight className="ml-1 h-4 w-4" />
            </Button>
          </Link>
        </div>
      </CardHeader>
      <div className="p-6 pt-0">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Pronostic</TableHead>
              <TableHead>Bookmaker</TableHead>
              <TableHead>Cote</TableHead>
              <TableHead>Mise</TableHead>
              <TableHead>Type</TableHead>
              <TableHead>Date</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {activeBets.map((bet) => (
              <TableRow key={bet.id}>
                <TableCell className="font-medium max-w-xs truncate">
                  {bet.outcome}
                </TableCell>
                <TableCell>{bet.bookmaker}</TableCell>
                <TableCell>{formatNumber(bet.odds_value, 2)}</TableCell>
                <TableCell>{formatEuro(bet.stake, 2)}</TableCell>
                <TableCell>{getTypeBadge(bet.bet_type)}</TableCell>
                <TableCell className="text-sm text-slate-400">
                  {new Date(bet.created_at).toLocaleDateString('fr-FR')}
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>
    </Card>
  );
}
