'use client'

import { useQuery, UseQueryOptions } from '@tanstack/react-query'
import { apiFetch } from '@/lib/api'
import { queryKeys } from '@/lib/query-keys'
import type { Opportunity } from '@/types/api'

export interface OpportunitiesFilters {
  sport?: string
  bookmaker?: string
  minEdge?: number
  strategy?: 'tabac' | 'ligne'
  limit?: number
  [key: string]: string | number | undefined
}

type QueryOptions = Omit<UseQueryOptions<Opportunity[], Error, Opportunity[], ReturnType<typeof queryKeys.opportunities.list>>, 'queryKey' | 'queryFn'>

export function useOpportunities(filters?: OpportunitiesFilters, options?: QueryOptions) {
  return useQuery({
    queryKey: queryKeys.opportunities.list(filters),
    queryFn: () =>
      apiFetch<Opportunity[]>('/opportunities/opportunities/', {
        query: {
          sport: filters?.sport,
          bookmaker: filters?.bookmaker,
          min_edge: filters?.minEdge,
          strategy: filters?.strategy,
          limit: filters?.limit,
        },
      }),
    staleTime: 30_000,
    ...options,
  })
}
