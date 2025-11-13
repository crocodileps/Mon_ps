import { useQuery } from '@tanstack/react-query';
import { api } from '@/lib/api';

interface Odds {
  id: number;
  match_id: string;
  bookmaker: string;
  market: string;
  outcome: string;
  odds_value: number;
  timestamp: string;
  is_best: boolean;
}

interface Match {
  match_id: string;
  home_team: string;
  away_team: string;
  sport: string;
  league: string;
  commence_time: string;
  odds_count: number;
}

interface MatchWithOdds extends Match {
  odds: Odds[];
  best_odds: {
    [market: string]: {
      [outcome: string]: {
        bookmaker: string;
        odds_value: number;
      };
    };
  };
}

interface OddsParams {
  match_id?: string;
  bookmaker?: string;
  market?: string;
  limit?: number;
}

/**
 * Hook pour récupérer les cotes
 */
export function useOdds(params?: OddsParams) {
  return useQuery<Odds[]>({
    queryKey: ['odds', params],
    queryFn: async () => {
      const { data } = await api.get<Odds[]>('/odds/odds/', { params });
      return data;
    },
    // Les cotes changent rapidement
    staleTime: 30000, // 30 secondes
    refetchInterval: 60000, // Rafraîchir toutes les minutes
  });
}

/**
 * Hook pour récupérer tous les matchs disponibles
 */
export function useMatches() {
  return useQuery<Match[]>({
    queryKey: ['matches'],
    queryFn: async () => {
      const { data } = await api.get<Match[]>('/odds/odds/matches');
      return data;
    },
    staleTime: 120000, // 2 minutes
    refetchInterval: 300000, // Rafraîchir toutes les 5 minutes
  });
}

/**
 * Hook pour récupérer un match spécifique avec ses cotes
 */
export function useMatch(matchId: string | null) {
  return useQuery<MatchWithOdds>({
    queryKey: ['match', matchId],
    queryFn: async () => {
      if (!matchId) throw new Error('Match ID required');
      const { data } = await api.get<MatchWithOdds>(`/odds/odds/matches/${matchId}`);
      return data;
    },
    enabled: !!matchId, // Ne fetch que si matchId existe
    staleTime: 30000, // 30 secondes
    refetchInterval: 60000, // Rafraîchir toutes les minutes
  });
}

/**
 * Hook pour récupérer les meilleures cotes d'un match
 */
export function useBestOdds(matchId: string | null) {
  return useQuery({
    queryKey: ['best-odds', matchId],
    queryFn: async () => {
      if (!matchId) throw new Error('Match ID required');
      
      // Récupérer le match avec toutes ses cotes
      const { data } = await api.get<MatchWithOdds>(`/odds/odds/matches/${matchId}`);
      
      // Extraire uniquement les meilleures cotes
      return data.best_odds;
    },
    enabled: !!matchId,
    staleTime: 30000,
  });
}

/**
 * Hook pour récupérer le nombre de matchs disponibles
 */
export function useMatchesCount() {
  return useQuery<number>({
    queryKey: ['matches-count'],
    queryFn: async () => {
      const { data } = await api.get<Match[]>('/odds/odds/matches');
      return data.length;
    },
    staleTime: 120000,
    refetchInterval: 300000,
  });
}

/**
 * Hook pour les cotes live d'un match spécifique
 * Rafraîchit plus fréquemment que les autres
 */
export function useLiveOdds(matchId: string | null) {
  return useQuery<Odds[]>({
    queryKey: ['live-odds', matchId],
    queryFn: async () => {
      if (!matchId) throw new Error('Match ID required');
      const { data } = await api.get<Odds[]>('/odds/odds/', {
        params: { match_id: matchId },
      });
      return data;
    },
    enabled: !!matchId,
    staleTime: 15000, // 15 secondes (plus frais pour le live)
    refetchInterval: 30000, // Rafraîchir toutes les 30 secondes
  });
}
