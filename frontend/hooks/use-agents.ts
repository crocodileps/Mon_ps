'use client'

import { useQuery } from '@tanstack/react-query'
import { api } from '@/lib/api'

// Types pour les signaux agents
export interface AgentSignal {
  agent: string
  match: string
  sport: string
  direction: string
  confidence: number
  odds?: {
    max: number
    min: number
    avg: number
  }
  spread_pct?: number
  win_probability?: number
  kelly_fraction?: number
  expected_value?: number
  recommended_stake_pct?: number
  bookmaker_count?: number
  reason: string
}

export interface AgentPerformance {
  agent_id: string
  agent_name: string
  total_signals: number
  avg_confidence: number
  avg_ev: number
  avg_kelly: number
  top_signal?: AgentSignal
}

export interface AgentHealth {
  status: string
  agents: string[]
  db_connected: boolean
}

// Hook pour récupérer les signaux des agents
export function useAgentSignals() {
  return useQuery<AgentSignal[]>({
    queryKey: ['agent-signals'],
    queryFn: async () => {
      const response = await api.get('/agents/signals')
      return response.data
    },
    staleTime: 60 * 1000, // 1 minute
    refetchInterval: 5 * 60 * 1000, // Refresh toutes les 5 minutes
  })
}

// Hook pour récupérer les performances des agents
export function useAgentPerformance() {
  return useQuery<AgentPerformance[]>({
    queryKey: ['agent-performance'],
    queryFn: async () => {
      const response = await api.get('/agents/performance')
      return response.data
    },
    staleTime: 60 * 1000,
  })
}

// Hook pour vérifier l'état des agents
export function useAgentHealth() {
  return useQuery<AgentHealth>({
    queryKey: ['agent-health'],
    queryFn: async () => {
      const response = await api.get('/agents/health')
      return response.data
    },
    staleTime: 30 * 1000,
  })
}
