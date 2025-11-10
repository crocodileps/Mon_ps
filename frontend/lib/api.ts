import type { AnalyticsResponse, Bet, Opportunity } from '@/types/api'

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_URL ?? process.env.API_URL ?? 'http://10.10.0.1:8001'

interface ApiFetchOptions extends RequestInit {
  retries?: number
  retryDelay?: number
  query?: Record<string, string | number | boolean | undefined>
}

const defaultHeaders: HeadersInit = {
  'Content-Type': 'application/json',
}

const wait = (duration: number) =>
  new Promise((resolve) => {
    setTimeout(resolve, duration)
  })

const buildUrl = (endpoint: string, query?: ApiFetchOptions['query']) => {
  const url = new URL(endpoint, API_BASE_URL)
  if (query) {
    Object.entries(query).forEach(([key, value]) => {
      if (value !== undefined && value !== null) {
        url.searchParams.append(key, String(value))
      }
    })
  }
  return url.toString()
}

export async function apiFetch<T>(endpoint: string, options: ApiFetchOptions = {}): Promise<T> {
  const { retries = 2, retryDelay = 600, headers, query, ...rest } = options
  const url = buildUrl(endpoint, query)

  let attempt = 0
  let error: unknown

  while (attempt <= retries) {
    try {
      const response = await fetch(url, {
        cache: 'no-store',
        ...rest,
        headers: {
          ...defaultHeaders,
          ...headers,
        },
      })

      if (!response.ok) {
        throw new Error(`API request failed with status ${response.status}`)
      }

      const data = (await response.json()) as T
      return data
    } catch (err) {
      error = err
      attempt += 1
      if (attempt > retries) {
        break
      }
      await wait(retryDelay * attempt)
    }
  }

  throw error instanceof Error ? error : new Error('API request failed')
}

export async function getOpportunities(): Promise<Opportunity[]> {
  return apiFetch<Opportunity[]>('/opportunities/', {
    query: { min_spread_pct: 10 },
  })
}

export async function getBets(): Promise<Bet[]> {
  return apiFetch<Bet[]>('/bets/')
}

export async function getAnalytics(
  periodDays = 30,
): Promise<AnalyticsResponse> {
  return apiFetch<AnalyticsResponse>(
    '/stats/analytics/comprehensive',
    {
      query: { period_days: periodDays },
    },
  )
}
