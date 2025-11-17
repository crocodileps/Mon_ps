'use client';

import { useState } from 'react';
import { useManualBets, useManualBetsStats, useCalculateCLV, useUpdateBetResult } from '@/hooks/use-manual-bets';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { 
  TrendingUp, 
  TrendingDown, 
  Calculator, 
  RefreshCw,
  Trophy,
  Target,
  DollarSign,
  Percent
} from 'lucide-react';

export default function ManualBetsPage() {
  const [filter, setFilter] = useState<string>('all');
  
  const { data: bets, isLoading: betsLoading, refetch: refetchBets } = useManualBets();
  const { data: stats, isLoading: statsLoading } = useManualBetsStats();
  const calculateCLV = useCalculateCLV();
  const updateResult = useUpdateBetResult();

  const handleCalculateCLV = async () => {
    try {
      const result = await calculateCLV.mutateAsync();
      alert(`CLV calculé pour ${result.updated} paris`);
    } catch (error) {
      alert('Erreur lors du calcul CLV');
    }
  };

  const handleUpdateResult = async (betId: number, result: string, stake: number, odds: number) => {
    const profit = result === 'win' ? stake * (odds - 1) : -stake;
    try {
      await updateResult.mutateAsync({ id: betId, result, profit_loss: profit });
    } catch (error) {
      alert('Erreur lors de la mise à jour');
    }
  };

  const formatCLV = (clv: number | null) => {
    if (clv === null) return 'En attente';
    const prefix = clv > 0 ? '+' : '';
    return `${prefix}${clv.toFixed(2)}%`;
  };

  const getCLVColor = (clv: number | null) => {
    if (clv === null) return 'text-gray-400';
    if (clv > 2) return 'text-green-400';
    if (clv > 0) return 'text-green-300';
    if (clv > -2) return 'text-yellow-400';
    return 'text-red-400';
  };

  const filteredBets = bets?.filter(bet => {
    if (filter === 'all') return true;
    if (filter === 'pending') return bet.result === null;
    if (filter === 'completed') return bet.result !== null;
    if (filter === 'positive-clv') return bet.clv_percent !== null && bet.clv_percent > 0;
    return true;
  });

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900 p-6">
      <div className="max-w-7xl mx-auto space-y-6">
        {/* Header */}
        <div className="flex justify-between items-center">
          <div>
            <h1 className="text-3xl font-bold text-white">Paris Manuels & CLV</h1>
            <p className="text-slate-400 mt-1">Tracking de vos paris avec Closing Line Value automatique</p>
          </div>
          <div className="flex gap-3">
            <Button
              onClick={() => refetchBets()}
              variant="outline"
              className="bg-slate-800/50 border-slate-600 text-white hover:bg-slate-700"
            >
              <RefreshCw className="w-4 h-4 mr-2" />
              Rafraîchir
            </Button>
            <Button
              onClick={handleCalculateCLV}
              disabled={calculateCLV.isPending}
              className="bg-violet-600 hover:bg-violet-700 text-white"
            >
              <Calculator className="w-4 h-4 mr-2" />
              {calculateCLV.isPending ? 'Calcul...' : 'Calculer CLV'}
            </Button>
          </div>
        </div>

        {/* Stats Cards */}
        {!statsLoading && stats && (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            <Card className="bg-slate-800/60 backdrop-blur-sm border-slate-700">
              <CardHeader className="pb-2">
                <CardTitle className="text-sm text-slate-400 flex items-center gap-2">
                  <Target className="w-4 h-4" />
                  Total Paris
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold text-white">{stats.total_bets}</div>
                <p className="text-xs text-slate-400">
                  {stats.wins}W - {stats.losses}L
                </p>
              </CardContent>
            </Card>

            <Card className="bg-slate-800/60 backdrop-blur-sm border-slate-700">
              <CardHeader className="pb-2">
                <CardTitle className="text-sm text-slate-400 flex items-center gap-2">
                  <TrendingUp className="w-4 h-4" />
                  CLV Moyen
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className={`text-2xl font-bold ${getCLVColor(stats.avg_clv_percent)}`}>
                  {stats.avg_clv_percent !== null ? formatCLV(stats.avg_clv_percent) : 'N/A'}
                </div>
                <p className="text-xs text-slate-400">
                  Objectif: &gt; 1%
                </p>
              </CardContent>
            </Card>

            <Card className="bg-slate-800/60 backdrop-blur-sm border-slate-700">
              <CardHeader className="pb-2">
                <CardTitle className="text-sm text-slate-400 flex items-center gap-2">
                  <DollarSign className="w-4 h-4" />
                  Profit Total
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className={`text-2xl font-bold ${
                  (stats.total_profit || 0) >= 0 ? 'text-green-400' : 'text-red-400'
                }`}>
                  {stats.total_profit !== null ? `${stats.total_profit.toFixed(2)}€` : '0€'}
                </div>
                <p className="text-xs text-slate-400">
                  Misé: {stats.total_staked?.toFixed(2) || '0'}€
                </p>
              </CardContent>
            </Card>

            <Card className="bg-slate-800/60 backdrop-blur-sm border-slate-700">
              <CardHeader className="pb-2">
                <CardTitle className="text-sm text-slate-400 flex items-center gap-2">
                  <Percent className="w-4 h-4" />
                  ROI
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className={`text-2xl font-bold ${
                  (stats.roi_percent || 0) >= 0 ? 'text-green-400' : 'text-red-400'
                }`}>
                  {stats.roi_percent !== null ? `${stats.roi_percent.toFixed(2)}%` : '0%'}
                </div>
                <p className="text-xs text-slate-400">
                  Return on Investment
                </p>
              </CardContent>
            </Card>
          </div>
        )}

        {/* Filters */}
        <div className="flex gap-2">
          {['all', 'pending', 'completed', 'positive-clv'].map((f) => (
            <Button
              key={f}
              onClick={() => setFilter(f)}
              variant={filter === f ? 'default' : 'outline'}
              size="sm"
              className={filter === f 
                ? 'bg-violet-600 text-white' 
                : 'bg-slate-800/50 border-slate-600 text-slate-300 hover:bg-slate-700'
              }
            >
              {f === 'all' && 'Tous'}
              {f === 'pending' && 'En attente'}
              {f === 'completed' && 'Terminés'}
              {f === 'positive-clv' && 'CLV Positif'}
            </Button>
          ))}
        </div>

        {/* Bets List */}
        <div className="space-y-4">
          {betsLoading ? (
            <div className="text-center text-slate-400 py-10">Chargement...</div>
          ) : filteredBets?.length === 0 ? (
            <div className="text-center text-slate-400 py-10">Aucun pari trouvé</div>
          ) : (
            filteredBets?.map((bet) => (
              <Card key={bet.id} className="bg-slate-800/60 backdrop-blur-sm border-slate-700">
                <CardContent className="p-4">
                  <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4">
                    {/* Match Info */}
                    <div className="flex-1">
                      <div className="flex items-center gap-2 mb-2">
                        <Badge variant="outline" className="text-xs border-slate-600 text-slate-300">
                          {bet.sport.replace('soccer_', '').replace(/_/g, ' ').toUpperCase()}
                        </Badge>
                        <Badge 
                          variant={bet.market_type === 'totals' ? 'default' : 'secondary'}
                          className={bet.market_type === 'totals' ? 'bg-blue-600' : 'bg-purple-600'}
                        >
                          {bet.market_type === 'totals' ? 'Over/Under' : '1X2'}
                        </Badge>
                        {bet.result && (
                          <Badge 
                            variant={bet.result === 'win' ? 'default' : 'destructive'}
                            className={bet.result === 'win' ? 'bg-green-600' : 'bg-red-600'}
                          >
                            {bet.result.toUpperCase()}
                          </Badge>
                        )}
                      </div>
                      <h3 className="text-lg font-semibold text-white">{bet.match_name}</h3>
                      <p className="text-slate-400 text-sm">
                        {new Date(bet.kickoff_time).toLocaleString('fr-FR')} • {bet.bookmaker}
                      </p>
                    </div>

                    {/* Bet Details */}
                    <div className="flex flex-wrap gap-6 items-center">
                      <div className="text-center">
                        <p className="text-xs text-slate-400">Sélection</p>
                        <p className="text-white font-medium">{bet.selection}</p>
                      </div>
                      <div className="text-center">
                        <p className="text-xs text-slate-400">Cote</p>
                        <p className="text-white font-medium">{bet.odds_obtained.toFixed(2)}</p>
                      </div>
                      <div className="text-center">
                        <p className="text-xs text-slate-400">Mise</p>
                        <p className="text-white font-medium">{bet.stake}€</p>
                      </div>
                      <div className="text-center">
                        <p className="text-xs text-slate-400">Pinnacle</p>
                        <p className="text-slate-300 font-medium">
                          {bet.closing_odds ? bet.closing_odds.toFixed(3) : '-'}
                        </p>
                      </div>
                      <div className="text-center">
                        <p className="text-xs text-slate-400">CLV</p>
                        <p className={`font-bold text-lg ${getCLVColor(bet.clv_percent)}`}>
                          {formatCLV(bet.clv_percent)}
                        </p>
                      </div>
                      
                      {/* Actions */}
                      {!bet.result && new Date(bet.kickoff_time) < new Date() && (
                        <div className="flex gap-2">
                          <Button
                            size="sm"
                            onClick={() => handleUpdateResult(bet.id, 'win', bet.stake, bet.odds_obtained)}
                            className="bg-green-600 hover:bg-green-700"
                          >
                            <Trophy className="w-3 h-3 mr-1" />
                            Win
                          </Button>
                          <Button
                            size="sm"
                            onClick={() => handleUpdateResult(bet.id, 'loss', bet.stake, bet.odds_obtained)}
                            variant="destructive"
                          >
                            <TrendingDown className="w-3 h-3 mr-1" />
                            Loss
                          </Button>
                        </div>
                      )}
                    </div>
                  </div>
                  
                  {/* Notes */}
                  {bet.notes && (
                    <div className="mt-3 pt-3 border-t border-slate-700">
                      <p className="text-xs text-slate-400">Notes: {bet.notes}</p>
                    </div>
                  )}
                </CardContent>
              </Card>
            ))
          )}
        </div>
      </div>
    </div>
  );
}
