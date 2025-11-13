'use client';

import { useState } from 'react';
import { Card, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Badge } from '@/components/ui/badge';
import { Filter, X, RefreshCw } from 'lucide-react';

interface OpportunityFiltersProps {
  onFilterChange: (filters: FilterState) => void;
  initialFilters?: Partial<FilterState>;
}

export interface FilterState {
  sport?: string;
  minEdge: number;
  bookmaker?: string;
  minOdds?: number;
  maxOdds?: number;
}

const SPORTS = [
  { value: 'all', label: 'Tous les sports' },
  { value: 'soccer_france_ligue_one', label: '⚽ Ligue 1' },
  { value: 'soccer_spain_la_liga', label: '⚽ La Liga' },
  { value: 'soccer_epl', label: '⚽ Premier League' },
  { value: 'soccer_germany_bundesliga', label: '⚽ Bundesliga' },
  { value: 'basketball_nba', label: '🏀 NBA' },
  { value: 'tennis_atp', label: '🎾 Tennis ATP' },
];

const BOOKMAKERS = [
  'Tous',
  'Betclic',
  'Unibet',
  'Winamax',
  'Betsson',
  'ParionsSport',
  'Betfair',
];

export function OpportunityFilters({
  onFilterChange,
  initialFilters = {},
}: OpportunityFiltersProps) {
  const [filters, setFilters] = useState<FilterState>({
    sport: initialFilters.sport || 'all',
    minEdge: initialFilters.minEdge || 5,
    bookmaker: initialFilters.bookmaker || 'Tous',
    minOdds: initialFilters.minOdds,
    maxOdds: initialFilters.maxOdds,
  });

  const [isExpanded, setIsExpanded] = useState(false);

  // Apply filters
  const handleApplyFilters = () => {
    const cleanFilters: FilterState = {
      ...filters,
      sport: filters.sport === 'all' ? undefined : filters.sport,
      bookmaker: filters.bookmaker === 'Tous' ? undefined : filters.bookmaker,
    };
    onFilterChange(cleanFilters);
  };

  // Reset filters
  const handleReset = () => {
    const defaultFilters: FilterState = {
      sport: 'all',
      minEdge: 5,
      bookmaker: 'Tous',
      minOdds: undefined,
      maxOdds: undefined,
    };
    setFilters(defaultFilters);
    onFilterChange({
      minEdge: 5,
      sport: undefined,
      bookmaker: undefined,
    });
  };

  // Count active filters
  const activeFiltersCount =
    (filters.sport !== 'all' ? 1 : 0) +
    (filters.bookmaker !== 'Tous' ? 1 : 0) +
    (filters.minEdge !== 5 ? 1 : 0) +
    (filters.minOdds ? 1 : 0) +
    (filters.maxOdds ? 1 : 0);

  return (
    <Card>
      <CardContent className="pt-6">
        {/* Header */}
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-2">
            <Filter className="h-5 w-5 text-blue-500" />
            <h3 className="text-lg font-semibold text-white">Filtres</h3>
            {activeFiltersCount > 0 && (
              <Badge variant="secondary" className="bg-blue-500/20 text-blue-400">
                {activeFiltersCount}
              </Badge>
            )}
          </div>
          <Button
            variant="ghost"
            size="sm"
            onClick={() => setIsExpanded(!isExpanded)}
          >
            {isExpanded ? 'Réduire' : 'Développer'}
          </Button>
        </div>

        {/* Basic Filters (Always visible) */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-4">
          {/* Sport */}
          <div className="space-y-2">
            <Label htmlFor="sport">Sport</Label>
            <Select
              value={filters.sport}
              onValueChange={(value) => setFilters({ ...filters, sport: value })}
            >
              <SelectTrigger id="sport">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {SPORTS.map((sport) => (
                  <SelectItem key={sport.value} value={sport.value}>
                    {sport.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          {/* Min Edge */}
          <div className="space-y-2">
            <Label htmlFor="minEdge">Edge minimum (%)</Label>
            <Input
              id="minEdge"
              type="number"
              step="0.1"
              value={filters.minEdge}
              onChange={(e) =>
                setFilters({ ...filters, minEdge: parseFloat(e.target.value) || 0 })
              }
              placeholder="5.0"
            />
          </div>

          {/* Bookmaker */}
          <div className="space-y-2">
            <Label htmlFor="bookmaker">Bookmaker</Label>
            <Select
              value={filters.bookmaker}
              onValueChange={(value) => setFilters({ ...filters, bookmaker: value })}
            >
              <SelectTrigger id="bookmaker">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {BOOKMAKERS.map((bk) => (
                  <SelectItem key={bk} value={bk}>
                    {bk}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </div>

        {/* Advanced Filters (Expandable) */}
        {isExpanded && (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4 p-4 bg-slate-800/30 rounded-lg border border-slate-700/50">
            <div className="space-y-2">
              <Label htmlFor="minOdds">Cote minimum</Label>
              <Input
                id="minOdds"
                type="number"
                step="0.1"
                value={filters.minOdds || ''}
                onChange={(e) =>
                  setFilters({
                    ...filters,
                    minOdds: e.target.value ? parseFloat(e.target.value) : undefined,
                  })
                }
                placeholder="ex: 1.50"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="maxOdds">Cote maximum</Label>
              <Input
                id="maxOdds"
                type="number"
                step="0.1"
                value={filters.maxOdds || ''}
                onChange={(e) =>
                  setFilters({
                    ...filters,
                    maxOdds: e.target.value ? parseFloat(e.target.value) : undefined,
                  })
                }
                placeholder="ex: 5.00"
              />
            </div>
          </div>
        )}

        {/* Actions */}
        <div className="flex gap-2">
          <Button onClick={handleApplyFilters} className="flex-1">
            <RefreshCw className="mr-2 h-4 w-4" />
            Appliquer
          </Button>
          {activeFiltersCount > 0 && (
            <Button variant="outline" onClick={handleReset}>
              <X className="mr-2 h-4 w-4" />
              Réinitialiser
            </Button>
          )}
        </div>
      </CardContent>
    </Card>
  );
}
