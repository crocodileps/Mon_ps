import { useQuery } from '@tanstack/react-query';
import { api } from '@/lib/api';

interface Opportunity {
  id: string;
  match_id: string;
  home_team: string;
  away_team: string;
  sport: string;
  commence_time: string;
  outcome: string;
  best_odds: number;
  worst_odds: number;
  bookmaker_best: string;
  bookmaker_worst: string;
  edge_pct: number;
  nb_bookmakers: number;
}

interface OpportunitiesParams {
  limit?: number;
  min_edge?: number;
  sport?: string;
}

/**
 * Hook pour récupérer les opportunités de paris
 */
export function useOpportunities(params?: OpportunitiesParams) {
  return useQuery<Opportunity[]>({
    queryKey: ['opportunities', params],
    queryFn: async () => {
      const { data } = await api.get<Opportunity[]>('/opportunities/opportunities/', {
        params,
      });
      return data;
    },
    // Rafraîchir toutes les 2 minutes (les cotes changent souvent)
    refetchInterval: 120000,
    staleTime: 60000, // Considéré frais pendant 1 minute
  });
}

/**
 * Hook pour récupérer une opportunité spécifique
 */
export function useOpportunity(id: string | null) {
  return useQuery<Opportunity>({
    queryKey: ['opportunity', id],
    queryFn: async () => {
      if (!id) throw new Error('ID required');
      const { data } = await api.get<Opportunity>(`/opportunities/opportunities/${id}`);
      return data;
    },
    enabled: !!id, // Ne fetch que si l'ID existe
    staleTime: 30000, // Considéré frais pendant 30 secondes
  });
}

/**
 * Hook pour obtenir le nombre d'opportunités
 */
export function useOpportunitiesCount(params?: OpportunitiesParams) {
  return useQuery<number>({
    queryKey: ['opportunities-count', params],
    queryFn: async () => {
      const { data } = await api.get<Opportunity[]>('/opportunities/opportunities/', {
        params,
      });
      return data.length;
    },
    refetchInterval: 120000,
  });
}
