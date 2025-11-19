import { useQuery } from '@tanstack/react-query'
import { getBetsHistory, getBetsStats } from '@/lib/api'

export const useBets = (limit = 50, status?: string) => {
  return useQuery({
    queryKey: ['bets', limit, status],
    queryFn: () => getBetsHistory(limit, status),
    refetchInterval: 30000
  })
}

export const useBetsStats = () => {
  return useQuery({
    queryKey: ['bets-stats'],
    queryFn: getBetsStats,
    refetchInterval: 30000
  })
}
