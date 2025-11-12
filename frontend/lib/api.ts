const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://monps_backend:8000'

interface ApiError {
  detail: string
  status: number
}

export class ApiClientError extends Error {
  status: number
  
  constructor(message: string, status: number) {
    super(message)
    this.name = 'ApiClientError'
    this.status = status
  }
}

export async function apiFetch<T>(
  endpoint: string,
  options: RequestInit & { query?: Record<string, any> } = {}
): Promise<T> {
  const { query, ...fetchOptions } = options
  
  let url = `${API_BASE_URL}${endpoint}`
  if (query) {
    const params = new URLSearchParams()
    Object.entries(query).forEach(([key, value]) => {
      if (value !== undefined && value !== null) {
        params.append(key, String(value))
      }
    })
    const queryString = params.toString()
    if (queryString) {
      url += `?${queryString}`
    }
  }
  
  const response = await fetch(url, {
    ...fetchOptions,
    headers: {
      'Content-Type': 'application/json',
      ...fetchOptions.headers,
    },
  })
  
  if (!response.ok) {
    const error: ApiError = await response.json().catch(() => ({
      detail: 'Unknown error',
      status: response.status,
    }))
    throw new ApiClientError(error.detail, response.status)
  }
  
  return response.json()
}

export async function checkHealth() {
  return apiFetch<{ status: string; timestamp: string }>('/health')
}

export async function getOpportunities(params?: any) {
  return apiFetch<any[]>('/opportunities/opportunities/', { query: params })
}

export async function getGlobalStats() {
  return apiFetch<any>('/stats/stats/global')
}

export async function getBankrollStats() {
  return apiFetch<any>('/stats/stats/bankroll')
}

export async function getBookmakerStats() {
  return apiFetch<any[]>('/stats/stats/bookmakers')
}

export async function getComprehensiveAnalytics() {
  return apiFetch<any>('/stats/stats/analytics/comprehensive')
}

// ============= BETS =============
export async function getBets(params?: { status?: string }) {
  return apiFetch<any[]>('/bets/bets/', { query: params })
}

export async function getBet(betId: string) {
  return apiFetch<any>(`/bets/bets/${betId}`)
}

export async function createBet(bet: any) {
  return apiFetch<any>('/bets/bets/', {
    method: 'POST',
    body: JSON.stringify(bet),
  })
}

export async function updateBet(betId: string, bet: any) {
  return apiFetch<any>(`/bets/bets/${betId}`, {
    method: 'PUT',
    body: JSON.stringify(bet),
  })
}

// ============= ODDS =============
export async function getOdds(params?: { sport?: string; bookmaker?: string }) {
  return apiFetch<any[]>('/odds/odds/', { query: params })
}

export async function getMatches() {
  return apiFetch<any[]>('/odds/odds/matches')
}

export async function getMatch(matchId: string) {
  return apiFetch<any>(`/odds/odds/matches/${matchId}`)
}

// ============= ARBITRAGE =============
export async function getArbitrageOpportunities() {
  return apiFetch<any[]>('/opportunities/opportunities/arbitrage')
}

// ============= METRICS =============
export async function getMetrics() {
  return apiFetch<any>('/metrics')
}

export async function getCollectorStats() {
  return apiFetch<any>('/metrics/collector/stats')
}
