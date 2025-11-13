'use client';

import { useState, useMemo } from 'react';
import { useBets, useDeleteBet } from '@/hooks/use-bets';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Input } from '@/components/ui/input';
import {
  Edit,
  Trash2,
  TrendingUp,
  TrendingDown,
  Clock,
  Search,
  ChevronLeft,
  ChevronRight,
} from 'lucide-react';
import { Card } from '@/components/ui/card';

interface BetsTableProps {
  onEditBet?: (betId: number) => void;
}

type SortField = 'created_at' | 'odds_value' | 'stake' | 'actual_profit';
type SortOrder = 'asc' | 'desc';

export function BetsTable({ onEditBet }: BetsTableProps) {
  const [resultFilter, setResultFilter] = useState<string>('all');
  const [typeFilter, setTypeFilter] = useState<string>('all');
  const [searchQuery, setSearchQuery] = useState('');
  const [sortField, setSortField] = useState<SortField>('created_at');
  const [sortOrder, setSortOrder] = useState<SortOrder>('desc');
  const [currentPage, setCurrentPage] = useState(1);
  const itemsPerPage = 10;

  // Fetch bets
  const { data: bets = [], isLoading, error } = useBets();
  const deleteBet = useDeleteBet();

  // Filter and sort bets
  const filteredAndSortedBets = useMemo(() => {
    let filtered = [...bets];

    // Filter by result
    if (resultFilter !== 'all') {
      filtered = filtered.filter((bet) => bet.result === resultFilter);
    }

    // Filter by type
    if (typeFilter !== 'all') {
      filtered = filtered.filter((bet) => bet.bet_type === typeFilter);
    }

    // Search filter
    if (searchQuery) {
      const query = searchQuery.toLowerCase();
      filtered = filtered.filter(
        (bet) =>
          bet.outcome.toLowerCase().includes(query) ||
          bet.bookmaker.toLowerCase().includes(query) ||
          bet.match_id.toLowerCase().includes(query)
      );
    }

    // Sort
    filtered.sort((a, b) => {
      let aVal: any = a[sortField];
      let bVal: any = b[sortField];

      // Handle null values
      if (aVal === null) aVal = sortOrder === 'asc' ? -Infinity : Infinity;
      if (bVal === null) bVal = sortOrder === 'asc' ? -Infinity : Infinity;

      // Convert to numbers if needed
      if (sortField === 'odds_value' || sortField === 'stake' || sortField === 'actual_profit') {
        aVal = parseFloat(aVal) || 0;
        bVal = parseFloat(bVal) || 0;
      }

      if (sortOrder === 'asc') {
        return aVal > bVal ? 1 : -1;
      } else {
        return aVal < bVal ? 1 : -1;
      }
    });

    return filtered;
  }, [bets, resultFilter, typeFilter, searchQuery, sortField, sortOrder]);

  // Pagination
  const totalPages = Math.ceil(filteredAndSortedBets.length / itemsPerPage);
  const paginatedBets = filteredAndSortedBets.slice(
    (currentPage - 1) * itemsPerPage,
    currentPage * itemsPerPage
  );

  // Handle sort
  const handleSort = (field: SortField) => {
    if (sortField === field) {
      setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc');
    } else {
      setSortField(field);
      setSortOrder('desc');
    }
  };

  // Handle delete
  const handleDelete = async (betId: number) => {
    if (window.confirm('Êtes-vous sûr de vouloir supprimer ce pari ?')) {
      await deleteBet.mutateAsync(betId);
    }
  };

  // Get result badge
  const getResultBadge = (result?: string | null) => {
    if (result === 'won') {
      return (
        <Badge className="bg-green-500/20 text-green-400 border-green-500/50">
          <TrendingUp className="h-3 w-3 mr-1" />
          Gagné
        </Badge>
      );
    }
    if (result === 'lost') {
      return (
        <Badge className="bg-red-500/20 text-red-400 border-red-500/50">
          <TrendingDown className="h-3 w-3 mr-1" />
          Perdu
        </Badge>
      );
    }
    return (
      <Badge className="bg-yellow-500/20 text-yellow-400 border-yellow-500/50">
        <Clock className="h-3 w-3 mr-1" />
        En cours
      </Badge>
    );
  };

  // Get type badge
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
      <Card className="p-8 text-center">
        <p className="text-slate-400">Chargement des paris...</p>
      </Card>
    );
  }

  if (error) {
    return (
      <Card className="p-8 text-center">
        <p className="text-red-400">Erreur lors du chargement des paris</p>
      </Card>
    );
  }

  return (
    <div className="space-y-4">
      {/* Filters */}
      <Card className="p-4">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          {/* Search */}
          <div className="md:col-span-2">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-slate-400" />
              <Input
                placeholder="Rechercher un pari..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="pl-10"
              />
            </div>
          </div>

          {/* Result filter */}
          <Select value={resultFilter} onValueChange={setResultFilter}>
            <SelectTrigger>
              <SelectValue placeholder="Résultat" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">Tous les résultats</SelectItem>
              <SelectItem value="won">Gagnés</SelectItem>
              <SelectItem value="lost">Perdus</SelectItem>
              <SelectItem value="pending">En cours</SelectItem>
            </SelectContent>
          </Select>

          {/* Type filter */}
          <Select value={typeFilter} onValueChange={setTypeFilter}>
            <SelectTrigger>
              <SelectValue placeholder="Type" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">Tous les types</SelectItem>
              <SelectItem value="tabac">🏪 Tabac</SelectItem>
              <SelectItem value="ligne">📱 Ligne</SelectItem>
              <SelectItem value="value">💎 Value</SelectItem>
              <SelectItem value="arbitrage">⚖️ Arbitrage</SelectItem>
            </SelectContent>
          </Select>
        </div>
      </Card>

      {/* Table */}
      <Card>
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>ID</TableHead>
              <TableHead>Pronostic</TableHead>
              <TableHead>Bookmaker</TableHead>
              <TableHead
                className="cursor-pointer hover:text-blue-400"
                onClick={() => handleSort('odds_value')}
              >
                Cote {sortField === 'odds_value' && (sortOrder === 'asc' ? '↑' : '↓')}
              </TableHead>
              <TableHead
                className="cursor-pointer hover:text-blue-400"
                onClick={() => handleSort('stake')}
              >
                Mise {sortField === 'stake' && (sortOrder === 'asc' ? '↑' : '↓')}
              </TableHead>
              <TableHead
                className="cursor-pointer hover:text-blue-400"
                onClick={() => handleSort('actual_profit')}
              >
                Profit {sortField === 'actual_profit' && (sortOrder === 'asc' ? '↑' : '↓')}
              </TableHead>
              <TableHead>Type</TableHead>
              <TableHead>Résultat</TableHead>
              <TableHead
                className="cursor-pointer hover:text-blue-400"
                onClick={() => handleSort('created_at')}
              >
                Date {sortField === 'created_at' && (sortOrder === 'asc' ? '↑' : '↓')}
              </TableHead>
              <TableHead className="text-right">Actions</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {paginatedBets.length === 0 ? (
              <TableRow>
                <TableCell colSpan={10} className="text-center text-slate-400 py-8">
                  Aucun pari trouvé
                </TableCell>
              </TableRow>
            ) : (
              paginatedBets.map((bet) => (
                <TableRow key={bet.id}>
                  <TableCell className="font-medium">#{bet.id}</TableCell>
                  <TableCell className="max-w-xs truncate">{bet.outcome}</TableCell>
                  <TableCell>{bet.bookmaker}</TableCell>
                  <TableCell>{parseFloat(bet.odds_value as string).toFixed(2)}</TableCell>
                  <TableCell>{parseFloat(bet.stake as string).toFixed(2)}€</TableCell>
                  <TableCell>
                    <span
                      className={
                        bet.actual_profit && parseFloat(bet.actual_profit) > 0
                          ? 'text-green-400 font-semibold'
                          : bet.actual_profit && parseFloat(bet.actual_profit) < 0
                          ? 'text-red-400 font-semibold'
                          : 'text-slate-400'
                      }
                    >
                      {bet.actual_profit ? `${parseFloat(bet.actual_profit as string).toFixed(2)}€` : '-'}
                    </span>
                  </TableCell>
                  <TableCell>{getTypeBadge(bet.bet_type)}</TableCell>
                  <TableCell>{getResultBadge(bet.result)}</TableCell>
                  <TableCell className="text-sm text-slate-400">
                    {new Date(bet.created_at).toLocaleDateString('fr-FR')}
                  </TableCell>
                  <TableCell className="text-right">
                    <div className="flex gap-2 justify-end">
                      {onEditBet && (
                        <Button
                          variant="ghost"
                          size="icon"
                          onClick={() => onEditBet(bet.id)}
                        >
                          <Edit className="h-4 w-4" />
                        </Button>
                      )}
                      <Button
                        variant="ghost"
                        size="icon"
                        onClick={() => handleDelete(bet.id)}
                        className="text-red-400 hover:text-red-300 hover:bg-red-500/10"
                      >
                        <Trash2 className="h-4 w-4" />
                      </Button>
                    </div>
                  </TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </Card>

      {/* Pagination */}
      {totalPages > 1 && (
        <Card className="p-4">
          <div className="flex items-center justify-between">
            <p className="text-sm text-slate-400">
              Affichage de {(currentPage - 1) * itemsPerPage + 1} à{' '}
              {Math.min(currentPage * itemsPerPage, filteredAndSortedBets.length)} sur{' '}
              {filteredAndSortedBets.length} paris
            </p>
            <div className="flex gap-2">
              <Button
                variant="outline"
                size="sm"
                onClick={() => setCurrentPage(currentPage - 1)}
                disabled={currentPage === 1}
              >
                <ChevronLeft className="h-4 w-4" />
              </Button>
              <span className="px-4 py-2 text-sm">
                Page {currentPage} / {totalPages}
              </span>
              <Button
                variant="outline"
                size="sm"
                onClick={() => setCurrentPage(currentPage + 1)}
                disabled={currentPage === totalPages}
              >
                <ChevronRight className="h-4 w-4" />
              </Button>
            </div>
          </div>
        </Card>
      )}
    </div>
  );
}
