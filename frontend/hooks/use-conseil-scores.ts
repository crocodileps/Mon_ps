import { useQuery } from '@tanstack/react-query'
import { api } from '@/lib/api'

interface ConseilScore {
  label: string
  score: number
  outcome: string
}

interface ConseilScoresResponse {
  [matchId: string]: ConseilScore
}

export function useConseilScores(matchIds: string[]) {
  return useQuery<ConseilScoresResponse>({
    queryKey: ['conseil-scores', matchIds],
    queryFn: async () => {
      if (matchIds.length === 0) return {}
      const response = await api.post('/agents/conseil-ultim/batch', matchIds)
      return response.data
    },
    enabled: matchIds.length > 0,
    staleTime: 300000, // 5 minutes
    cacheTime: 600000, // 10 minutes
    refetchInterval: 180000, // 3 minutes
    refetchOnWindowFocus: false,
  })
}
