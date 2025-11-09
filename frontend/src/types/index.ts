export interface Opportunity {
  id: number;
  sport: string;
  league: string;
  home_team: string;
  away_team: string;
  bookmaker: string;
  market_type: string;
  outcome: string;
  odds: number;
  probability?: number;
  expected_value?: number;
  detected_at: string;
  match_time?: string;
  is_arbitrage: boolean;
  edge_percentage?: number;
}

export interface Bet {
  id: number;
  opportunity_id?: number;
  bookmaker: string;
  sport: string;
  event_description: string;
  odds: number;
  stake: number;
  potential_return: number;
  status: 'pending' | 'won' | 'lost' | 'void';
  placed_at: string;
  settled_at?: string;
  result?: string;
  profit_loss?: number;
}

export interface Bankroll {
  current_balance: number;
  initial_balance: number;
  total_staked: number;
  total_returned: number;
  profit_loss: number;
  roi: number;
  total_bets: number;
  winning_bets: number;
  losing_bets: number;
  win_rate: number;
}

export interface User {
  username: string;
  email: string;
}

export interface LoginCredentials {
  username: string;
  password: string;
}

export interface ApiResponse<T> {
  data?: T;
  error?: string;
  message?: string;
}
