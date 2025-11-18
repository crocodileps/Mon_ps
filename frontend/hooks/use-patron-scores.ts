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
    staleTime: 60000, // 1 minute
    refetchInterval: 120000, // 2 minutes
  })
}
