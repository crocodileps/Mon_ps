import type { Bet } from '@/types/api'

const strategies = ['tabac', 'ligne'] as const
const bookmakers = [
  'Bet365',
  'Pinnacle',
  'FanDuel',
  'DraftKings',
  'Unibet',
  'Betway',
  'Caesars',
  'BetMGM',
]

const results: Array<Bet['result']> = ['won', 'lost', 'pending']

const outcomes = [
  'PSG -1.5',
  'Over 224.5',
  'Moneyline',
  'Under 2.5',
  'Total > 5.5',
  'First half -3.5',
  'Both teams to score',
  'Player prop',
  'Clean sheet',
  'Overtime yes',
]

export const mockBets: Bet[] = Array.from({ length: 50 }, (_, index) => {
  const strategy = strategies[index % strategies.length]
  const result = results[index % results.length]
  const stake = 50 + (index % 5) * 10
  const profit =
    result === 'won' ? Number((stake * (0.8 + (index % 4) * 0.2)).toFixed(2)) : result === 'lost' ? -stake : null

  return {
    id: index + 1,
    match_id: `MATCH-${index + 1}`,
    outcome: outcomes[index % outcomes.length],
    bookmaker: bookmakers[index % bookmakers.length],
    odds_value: Number((1.7 + (index % 6) * 0.15).toFixed(2)),
    stake,
    bet_type: strategy,
    status: result === 'pending' ? 'open' : 'closed',
    result,
    actual_profit: profit,
    clv: Number((0.8 + (index % 5) * 0.1).toFixed(2)),
    market_type: 'main',
    created_at: new Date(2025, 10, (index % 28) + 1).toISOString(),
  }
})

