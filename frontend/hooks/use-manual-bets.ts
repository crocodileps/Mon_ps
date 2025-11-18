import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '@/lib/api';

// ============== INTERFACES ==============

export interface ManualBet {
  id: number;
  match_id: string | null;
  match_name: string;
  sport: string;
  kickoff_time: string;
  market_type: 'h2h' | 'totals';
  selection: string;
  line: number | null;
  bookmaker: string;
  odds_obtained: number;
  stake: number;
  closing_odds: number | null;
  clv_percent: number | null;
  clv_calculated_at: string | null;
  result: 'win' | 'loss' | 'push' | 'void' | null;
  profit_loss: number | null;
  notes: string | null;
  created_at: string;
  updated_at: string;
}

export interface ManualBetsStats {
  total_bets: number;
  wins: number;
  losses: number;
  avg_clv_percent: number | null;
  total_profit: number | null;
  total_staked: number | null;
  roi_percent: number | null;
}

export interface CLVCalculationResult {
  message: string;
  updated: number;
  results: Array<{
    bet_id: number;
    closing_odds: number;
    clv_percent: number;
  }>;
}

// ============== HOOKS ==============

export function useManualBets(params?: {
  limit?: number;
  offset?: number;
  sport?: string;
  market_type?: string;
  result?: string;
}) {
  const queryParams = new URLSearchParams();
  
  if (params?.limit) queryParams.append('limit', params.limit.toString());
  if (params?.offset) queryParams.append('offset', params.offset.toString());
  if (params?.sport) queryParams.append('sport', params.sport);
  if (params?.market_type) queryParams.append('market_type', params.market_type);
  if (params?.result) queryParams.append('result', params.result);

  const queryString = queryParams.toString();
  const url = queryString ? `/manual-bets/?${queryString}` : '/manual-bets/';

  return useQuery<ManualBet[]>({
    queryKey: ['manual-bets', params],
    queryFn: async () => { const { data } = await api.get(url); return data; },
    refetchInterval: 60000, // Refresh toutes les minutes
  });
}

export function useManualBetsStats() {
  return useQuery<ManualBetsStats>({
    queryKey: ['manual-bets-stats'],
    queryFn: async () => { const { data } = await api.get('/bets/stats'); return data; },
    refetchInterval: 60000,
  });
}

export function useManualBet(id: number) {
  return useQuery<ManualBet>({
    queryKey: ['manual-bet', id],
    queryFn: async () => { const { data } = await api.get(`/manual-bets/${id}`); return data; },
    enabled: !!id,
  });
}

export function useCalculateCLV() {
  const queryClient = useQueryClient();

  return useMutation<CLVCalculationResult>({
    mutationFn: async () => { const { data } = await api.post('/manual-bets/calculate-clv'); return data; },
    onSuccess: () => {
      // Invalider les queries pour rafraîchir les données
      queryClient.invalidateQueries({ queryKey: ['manual-bets'] });
      queryClient.invalidateQueries({ queryKey: ['manual-bets-stats'] });
    },
  });
}

export function useUpdateBetResult() {
  const queryClient = useQueryClient();

  return useMutation<ManualBet, Error, { id: number; result: string; profit_loss?: number }>({
    mutationFn: async ({ id, result, profit_loss }) =>
      {  const  { data } =  await  api.put ( `/manual-bets/$ {id} `,  {  result, profit_loss   } ) ;  return data ;  } ,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['manual-bets'] });
      queryClient.invalidateQueries({ queryKey: ['manual-bets-stats'] });
    },
  });
}
