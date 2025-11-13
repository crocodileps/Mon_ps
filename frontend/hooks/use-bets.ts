import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '@/lib/api';
import { toast } from 'react-hot-toast';

interface Bet {
  id: number;
  match_id: string;
  outcome: string;
  bookmaker: string;
  odds_value: number;
  stake: number;
  bet_type: 'tabac' | 'ligne';
  status: string;
  result: 'won' | 'lost' | 'pending' | null;
  actual_profit: number | null;
  clv: number | null;
  market_type: string | null;
  created_at: string;
}

interface CreateBetPayload {
  match_id: string;
  outcome: string;
  bookmaker: string;
  odds_value: number;
  stake: number;
  bet_type: 'tabac' | 'ligne';
  market_type?: string;
}

interface UpdateBetPayload {
  status?: string;
  result?: 'won' | 'lost' | 'pending';
  actual_profit?: number;
}

interface BetsParams {
  limit?: number;
  bet_type?: 'tabac' | 'ligne';
  status?: string;
  result?: 'won' | 'lost' | 'pending';
}

/**
 * Hook pour récupérer tous les paris
 */
export function useBets(params?: BetsParams) {
  return useQuery<Bet[]>({
    queryKey: ['bets', params],
    queryFn: async () => {
      const { data } = await api.get<Bet[]>('/bets/bets/', { params });
      return data;
    },
    staleTime: 30000, // 30 secondes
  });
}

/**
 * Hook pour récupérer un pari spécifique
 */
export function useBet(id: number | null) {
  return useQuery<Bet>({
    queryKey: ['bet', id],
    queryFn: async () => {
      if (!id) throw new Error('ID required');
      const { data } = await api.get<Bet>(`/bets/bets/${id}`);
      return data;
    },
    enabled: !!id,
  });
}

/**
 * Hook pour créer un nouveau pari
 */
export function useCreateBet() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (payload: CreateBetPayload) => {
      const { data } = await api.post<Bet>('/bets/bets/', payload);
      return data;
    },
    onSuccess: () => {
      // Invalider le cache pour forcer le rafraîchissement
      queryClient.invalidateQueries({ queryKey: ['bets'] });
      queryClient.invalidateQueries({ queryKey: ['stats'] });
      toast.success('Pari créé avec succès !');
    },
    onError: (error: any) => {
      const message = error.response?.data?.detail || 'Erreur lors de la création du pari';
      toast.error(message);
    },
  });
}

/**
 * Hook pour mettre à jour un pari
 */
export function useUpdateBet() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({ id, payload }: { id: number; payload: UpdateBetPayload }) => {
      const { data } = await api.put<Bet>(`/bets/bets/${id}`, payload);
      return data;
    },
    onSuccess: (data) => {
      // Invalider le cache
      queryClient.invalidateQueries({ queryKey: ['bets'] });
      queryClient.invalidateQueries({ queryKey: ['bet', data.id] });
      queryClient.invalidateQueries({ queryKey: ['stats'] });
      toast.success('Pari mis à jour avec succès !');
    },
    onError: (error: any) => {
      const message = error.response?.data?.detail || 'Erreur lors de la mise à jour du pari';
      toast.error(message);
    },
  });
}

/**
 * Hook pour supprimer un pari
 */
export function useDeleteBet() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (id: number) => {
      await api.delete(`/bets/bets/${id}`);
      return id;
    },
    onSuccess: () => {
      // Invalider le cache
      queryClient.invalidateQueries({ queryKey: ['bets'] });
      queryClient.invalidateQueries({ queryKey: ['stats'] });
      toast.success('Pari supprimé avec succès !');
    },
    onError: (error: any) => {
      const message = error.response?.data?.detail || 'Erreur lors de la suppression du pari';
      toast.error(message);
    },
  });
}

/**
 * Hook pour obtenir le nombre de paris actifs
 */
export function useActiveBetsCount() {
  return useQuery<number>({
    queryKey: ['bets-active-count'],
    queryFn: async () => {
      const { data } = await api.get<Bet[]>('/bets/bets/', {
        params: { status: 'active' },
      });
      return data.length;
    },
    refetchInterval: 60000, // Rafraîchir toutes les minutes
  });
}
