export type StrategyType = 'tabac' | 'ligne'

export interface Opportunity {
  id: string
  match_id: string
  home_team: string
  away_team: string
  sport: string
  commence_time: string
  outcome: string
  best_odds: number
  worst_odds: number
  bookmaker_best: string
  bookmaker_worst: string
  edge_pct: number
  nb_bookmakers: number
}

export interface Bet {
  id: number
  match_id: string
  outcome: string
  bookmaker: string
  odds_value: number
  stake: number
  bet_type: StrategyType
  status: string
  result: 'won' | 'lost' | 'pending' | null
  actual_profit: number | null
  clv: number | null
  market_type: string | null
  created_at: string
}

export interface AnalyticsResponse {
  status: string
  period_days: number
  bets_analyzed: number
  total_staked: number
  total_profit: number
}

export interface DashboardMetrics {
  bankroll: number
  bankrollChange: number
  roi: number
  roiChange: number
  clv: number
  clvChange: number
  sharpeRatio: number
  sharpeChange: number
  openBets: number
  openExposure: number
  potentialReturn: number
}

export interface PerformancePoint {
  date: string
  tabac_roi: number
  ligne_roi: number
}

export interface BankrollPoint {
  date: string
  balance: number
}

export interface HeatmapDay {
  date: string
  day: number
  profit: number
}

