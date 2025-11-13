import { useComprehensiveAnalytics } from './use-stats';
import { useOpportunities, useOpportunitiesCount } from './use-opportunities';
import { useBets, useActiveBetsCount } from './use-bets';
import { useMatches } from './use-odds';
import { useHealth } from './use-health';

/**
 * Hook composite principal pour le dashboard
 * Charge toutes les données nécessaires en une seule fois
 */
export function useDashboard() {
  // Vérifier la connexion backend
  const health = useHealth();

  // Charger les analytics complètes
  const analytics = useComprehensiveAnalytics();

  // Charger les opportunités (top 10)
  const opportunities = useOpportunities({ limit: 10, min_edge: 1.0 });
  const opportunitiesCount = useOpportunitiesCount({ min_edge: 1.0 });

  // Charger les paris actifs
  const activeBets = useBets({ status: 'active' });
  const activeBetsCount = useActiveBetsCount();

  // Charger les matchs disponibles
  const matches = useMatches();

  // État global de chargement
  const isLoading =
    health.isLoading ||
    analytics.isLoading ||
    opportunities.isLoading ||
    activeBets.isLoading ||
    matches.isLoading;

  // État global d'erreur
  const isError =
    health.isError ||
    analytics.isError ||
    opportunities.isError ||
    activeBets.isError ||
    matches.isError;

  // Fonction pour tout rafraîchir
  const refetchAll = () => {
    health.refetch();
    analytics.refetch();
    opportunities.refetch();
    opportunitiesCount.refetch();
    activeBets.refetch();
    activeBetsCount.refetch();
    matches.refetch();
  };

  return {
    // Status backend
    health: health.data,
    isBackendOnline: health.isSuccess && health.data?.status === 'ok',

    // Analytics
    analytics: analytics.data,

    // Opportunités
    opportunities: opportunities.data || [],
    opportunitiesCount: opportunitiesCount.data || 0,

    // Paris
    activeBets: activeBets.data || [],
    activeBetsCount: activeBetsCount.data || 0,

    // Matchs
    matches: matches.data || [],
    matchesCount: matches.data?.length || 0,

    // États
    isLoading,
    isError,

    // Actions
    refetchAll,
  };
}

/**
 * Hook simplifié pour le dashboard avec gestion d'erreurs
 */
export function useDashboardWithFallback() {
  const dashboard = useDashboard();

  // Fournir des valeurs par défaut en cas d'erreur
  if (dashboard.isError) {
    return {
      ...dashboard,
      analytics: {
        global_stats: {
          total_bets: 0,
          total_stake: 0,
          total_return: 0,
          total_profit: 0,
          avg_odds: 0,
          win_rate: 0,
          roi: 0,
          avg_clv: 0,
          sharpe_ratio: 0,
        },
        bankroll_stats: {
          current_bankroll: 0,
          initial_bankroll: 0,
          total_profit: 0,
          roi_percentage: 0,
          max_drawdown: 0,
          current_exposure: 0,
          available_balance: 0,
        },
        bookmaker_stats: [],
        performance_by_type: {
          tabac: { total_bets: 0, roi: 0, avg_clv: 0 },
          ligne: { total_bets: 0, roi: 0, avg_clv: 0 },
        },
        monthly_performance: [],
      },
    };
  }

  return dashboard;
}
