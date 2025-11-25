import { useQuery } from '@tanstack/react-query'
import { api } from '@/lib/api'

interface PatronScore {
  score: number
  label: string
  color: string
}

interface PatronScoresResponse {
  [matchId: string]: PatronScore
}

export function usePatronScores(matchIds: string[]) {
  return useQuery<PatronScoresResponse>({
    queryKey: ['patron-scores', matchIds],
    queryFn: async () => {
      if (matchIds.length === 0) return {}
      
      const response = await api.post('/agents/patron/batch', matchIds)
      return response.data
    },
    enabled: matchIds.length > 0,
    staleTime: 300000, // 5 minutes
    cacheTime: 600000, // 10 minutes
    refetchInterval: 180000, // 3 minutes
    refetchOnWindowFocus: false, // Pas de refetch au focus
  })
}
