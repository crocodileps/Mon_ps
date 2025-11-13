import { useQuery } from '@tanstack/react-query';
import { api } from '@/lib/api';

interface HealthResponse {
  status: string;
  timestamp: string;
  version?: string;
}

/**
 * Hook pour vérifier la santé du backend
 * Utilisé pour tester la connexion
 */
export function useHealth() {
  return useQuery<HealthResponse>({
    queryKey: ['health'],
    queryFn: async () => {
      const { data } = await api.get<HealthResponse>('/health');
      return data;
    },
    // Rafraîchir toutes les 30 secondes
    refetchInterval: 30000,
    // Toujours fetch en background
    refetchOnWindowFocus: true,
    // Ne pas désactiver si erreur
    retry: 3,
  });
}
