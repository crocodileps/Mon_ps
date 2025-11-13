import { useQuery } from '@tanstack/react-query';
import { api } from '@/lib/api';

interface GlobalStats {
  total_bets: number;
  total_stake: number;
  total_return: number;
  total_profit: number;
  avg_odds: number;
  win_rate: number;
  roi: number;
  avg_clv: number;
  sharpe_ratio: number;
}

interface BankrollStats {
  current_bankroll: number;
  initial_bankroll: number;
  total_profit: number;
  roi_percentage: number;
  max_drawdown: number;
  current_exposure: number;
  available_balance: number;
}

interface BookmakerStats {
  bookmaker: string;
  total_bets: number;
  total_profit: number;
  roi: number;
  avg_clv: number;
  win_rate: number;
}

interface ComprehensiveAnalytics {
  global_stats: GlobalStats;
  bankroll_stats: BankrollStats;
  bookmaker_stats: BookmakerStats[];
  performance_by_type: {
    tabac: {
      total_bets: number;
      roi: number;
      avg_clv: number;
    };
    ligne: {
      total_bets: number;
      roi: number;
      avg_clv: number;
    };
  };
  monthly_performance: Array<{
    month: string;
    profit: number;
    roi: number;
    bets_count: number;
  }>;
}

/**
 * Hook pour récupérer les statistiques globales
 */
export function useGlobalStats() {
  return useQuery<GlobalStats>({
    queryKey: ['stats', 'global'],
    queryFn: async () => {
      const { data } = await api.get<GlobalStats>('/stats/stats/global');
      return data;
    },
    staleTime: 60000, // 1 minute
    refetchInterval: 120000, // Rafraîchir toutes les 2 minutes
  });
}

/**
 * Hook pour récupérer les stats de bankroll
 */
export function useBankrollStats() {
  return useQuery<BankrollStats>({
    queryKey: ['stats', 'bankroll'],
    queryFn: async () => {
      const { data } = await api.get<BankrollStats>('/stats/stats/bankroll');
      return data;
    },
    staleTime: 30000, // 30 secondes
    refetchInterval: 60000, // Rafraîchir toutes les minutes
  });
}

/**
 * Hook pour récupérer les stats par bookmaker
 */
export function useBookmakerStats() {
  return useQuery<BookmakerStats[]>({
    queryKey: ['stats', 'bookmakers'],
    queryFn: async () => {
      const { data } = await api.get<BookmakerStats[]>('/stats/stats/bookmakers');
      return data;
    },
    staleTime: 120000, // 2 minutes
  });
}

/**
 * Hook pour récupérer l'analyse complète (dashboard principal)
 */
export function useComprehensiveAnalytics() {
  return useQuery<ComprehensiveAnalytics>({
    queryKey: ['stats', 'comprehensive'],
    queryFn: async () => {
      const { data } = await api.get<ComprehensiveAnalytics>('/stats/stats/analytics/comprehensive');
      return data;
    },
    staleTime: 60000, // 1 minute
    refetchInterval: 180000, // Rafraîchir toutes les 3 minutes
  });
}

/**
 * Hook composite pour le dashboard
 * Combine plusieurs stats en un seul hook
 */
export function useDashboardStats() {
  const global = useGlobalStats();
  const bankroll = useBankrollStats();
  const bookmakers = useBookmakerStats();

  return {
    global,
    bankroll,
    bookmakers,
    isLoading: global.isLoading || bankroll.isLoading || bookmakers.isLoading,
    isError: global.isError || bankroll.isError || bookmakers.isError,
    refetch: () => {
      global.refetch();
      bankroll.refetch();
      bookmakers.refetch();
    },
  };
}
