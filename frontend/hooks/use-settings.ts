import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api, apiFetch } from '@/lib/api';

// Types pour Settings
export interface Setting {
  id: number;
  key: string;
  value: Record<string, any>;
  description: string | null;
  created_at: string;
  updated_at: string;
}

export interface BankrollSetting {
  amount: number;
  currency: string;
}

export interface ApiKeySetting {
  key: string;
  enabled: boolean;
}

export interface CollectFrequencySetting {
  hours: number;
  cache_minutes: number;
}

export interface EmailAlertsSetting {
  enabled: boolean;
  smtp_host: string;
  smtp_port: number;
  from: string;
  to: string;
}

export interface NotificationThresholdsSetting {
  min_edge_pct: number;
  min_odds: number;
  max_odds: number;
}

// Hook pour récupérer tous les settings
export function useSettings() {
  return useQuery<Setting[]>({
    queryKey: ['settings'],
    queryFn: () => apiFetch<Setting[]>('/settings/'),
  });
}

// Hook pour récupérer un setting spécifique
export function useSetting(key: string) {
  return useQuery<Setting>({
    queryKey: ['settings', key],
    queryFn: () => apiFetch<Setting>(`/settings/${key}`),
    enabled: !!key,
  });
}

// Hook pour mettre à jour un setting
export function useUpdateSetting() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({ key, value }: { key: string; value: Record<string, any> }) => {
      const { data } = await api.put<Setting>(`/settings/${key}`, { value });
      return data;
    },
    onSuccess: (data) => {
      // Invalider tous les settings pour refetch
      queryClient.invalidateQueries({ queryKey: ['settings'] });
      // Mettre à jour le cache du setting spécifique
      queryClient.setQueryData(['settings', data.key], data);
    },
  });
}

// Hook pour le health check
export function useSettingsHealth() {
  return useQuery<{ status: string; settings_count: number; timestamp: string }>({
    queryKey: ['settings', 'health'],
    queryFn: () => apiFetch('/settings/health'),
  });
}
