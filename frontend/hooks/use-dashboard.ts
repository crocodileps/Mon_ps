'use client'

import { useQuery, UseQueryOptions } from '@tanstack/react-query'

import { apiFetch } from '@/lib/api'
import { queryKeys } from '@/lib/query-keys'
import type {
  BankrollPoint,
  DashboardMetrics,
  HeatmapDay,
  PerformancePoint,
} from '@/types/api'

type MetricsQueryOptions = Omit<
  UseQueryOptions<DashboardMetrics, Error, DashboardMetrics, typeof queryKeys.dashboard.metrics>,
  'queryKey' | 'queryFn'
>

type PerformanceQueryOptions = Omit<
  UseQueryOptions<PerformancePoint[], Error, PerformancePoint[], typeof queryKeys.dashboard.performance>,
  'queryKey' | 'queryFn'
>

type BankrollQueryOptions = Omit<
  UseQueryOptions<BankrollPoint[], Error, BankrollPoint[], typeof queryKeys.dashboard.bankroll>,
  'queryKey' | 'queryFn'
>

type HeatmapQueryOptions = Omit<
  UseQueryOptions<HeatmapDay[], Error, HeatmapDay[], typeof queryKeys.dashboard.heatmap>,
  'queryKey' | 'queryFn'
>

export function useDashboardMetrics(options?: MetricsQueryOptions) {
  return useQuery({
    queryKey: queryKeys.dashboard.metrics,
    queryFn: () => apiFetch<DashboardMetrics>('/dashboard/metrics'),
    ...options,
  })
}

export function useDashboardPerformance(options?: PerformanceQueryOptions) {
  return useQuery({
    queryKey: queryKeys.dashboard.performance,
    queryFn: () => apiFetch<PerformancePoint[]>('/dashboard/performance'),
    ...options,
  })
}

export function useDashboardBankroll(options?: BankrollQueryOptions) {
  return useQuery({
    queryKey: queryKeys.dashboard.bankroll,
    queryFn: () => apiFetch<BankrollPoint[]>('/dashboard/bankroll'),
    ...options,
  })
}

export function useDashboardHeatmap(options?: HeatmapQueryOptions) {
  return useQuery({
    queryKey: queryKeys.dashboard.heatmap,
    queryFn: () => apiFetch<HeatmapDay[]>('/dashboard/heatmap'),
    ...options,
  })
}

