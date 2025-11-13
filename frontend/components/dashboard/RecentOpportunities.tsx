'use client';

import { useState } from 'react';
import { useOpportunities } from '@/hooks/use-opportunities';
import { OpportunityCard } from '@/components/business';
import { Card, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { TrendingUp, ChevronRight } from 'lucide-react';
import Link from 'next/link';

interface RecentOpportunitiesProps {
  limit?: number;
  onPlaceBet?: (opportunityId: string) => void;
}

export function RecentOpportunities({ limit = 3, onPlaceBet }: RecentOpportunitiesProps) {
  const { data: opportunities = [], isLoading, error } = useOpportunities();

  // Trier par edge décroissant et prendre les N meilleures
  const topOpportunities = [...opportunities]
    .sort((a, b) => (b.edge_pct || 0) - (a.edge_pct || 0))
    .slice(0, limit);

  if (isLoading) {
    return (
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <TrendingUp className="h-5 w-5 text-blue-500" />
              <CardTitle>Meilleures Opportunités</CardTitle>
            </div>
          </div>
        </CardHeader>
        <div className="p-6">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {[1, 2, 3].map((i) => (
              <div
                key={i}
                className="h-48 bg-slate-800/50 rounded-lg animate-pulse"
              />
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
          <CardTitle>Meilleures Opportunités</CardTitle>
        </CardHeader>
        <div className="p-6 text-center text-red-400">
          Erreur lors du chargement des opportunités
        </div>
      </Card>
    );
  }

  if (topOpportunities.length === 0) {
    return (
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <TrendingUp className="h-5 w-5 text-blue-500" />
              <CardTitle>Meilleures Opportunités</CardTitle>
            </div>
          </div>
        </CardHeader>
        <div className="p-6 text-center text-slate-400">
          <p>Aucune opportunité disponible pour le moment</p>
          <p className="text-sm mt-2">Les opportunités sont actualisées toutes les 2 heures</p>
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
              <TrendingUp className="h-5 w-5 text-blue-500" />
              <CardTitle>Meilleures Opportunités</CardTitle>
            </div>
            <CardDescription className="mt-1">
              Top {topOpportunities.length} opportunités par edge
            </CardDescription>
          </div>
          <Link href="/opportunities">
            <Button variant="ghost" size="sm">
              Voir tout
              <ChevronRight className="ml-1 h-4 w-4" />
            </Button>
          </Link>
        </div>
      </CardHeader>
      <div className="p-6 pt-0">
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {topOpportunities.map((opp) => (
            <OpportunityCard
              key={opp.match_id}
              {...opp}
              onPlaceBet={onPlaceBet ? () => onPlaceBet(opp.match_id) : undefined}
            />
          ))}
        </div>
      </div>
    </Card>
  );
}
