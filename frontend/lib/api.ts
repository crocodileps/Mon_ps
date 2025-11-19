import axios from 'axios';

// Utiliser l'IP publique par défaut
const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://91.98.131.218:8001';

export const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 30000,
});

// Intercepteur pour logger les erreurs
api.interceptors.response.use(
  (response) => response,
  (error) => {
    console.error('API Error:', error.response?.data || error.message);
    return Promise.reject(error);
  }
);

// Fonction générique pour fetch avec axios
export async function apiFetch<T>(endpoint: string, params?: any): Promise<T> {
  const { data } = await api.get<T>(endpoint, { params });
  return data;
}

// Stats Bankroll
export async function getBankrollStats() {
  const { data } = await api.get("/stats/stats/bankroll");
  return data;
}

// Stats Globales
export async function getGlobalStats() {
  const { data } = await api.get("/stats/stats/global");
  return data;
}

// Opportunités
export async function getOpportunities(params?: any) {
  const { data } = await api.get("/opportunities/opportunities/", { params });
  return data.map((opp: any) => ({
    id: opp.match_id,
    match_id: opp.match_id,
    home_team: opp.home_team,
    away_team: opp.away_team,
    sport: opp.sport,
    commence_time: opp.commence_time,
    outcome: opp.outcome,
    best_odds: parseFloat(opp.best_odd) || 0,
    worst_odds: parseFloat(opp.worst_odd) || 0,
    bookmaker_best: opp.bookmaker_best,
    bookmaker_worst: opp.bookmaker_worst,
    // La propriété edge_pct est bien créée ici à partir de spread_pct
    edge_pct: opp.spread_pct || 0, 
    nb_bookmakers: opp.nb_bookmakers,
  }));
}

// Bets
export async function getBets(params?: any) {
  const { data } = await api.get("/bets/bets/", { params });
  return data;
}

export default api;

// ============= BETS / P&L =============
export const placeBet = async (betData: {
  match_id: string
  opportunity_id?: string
  home_team: string
  away_team: string
  sport: string
  league?: string
  commence_time: string
  outcome: string
  odds: number
  stake: number
  bookmaker: string
  edge_pct?: number
  agent_recommended?: string
  patron_score?: string
  patron_confidence?: number
  notes?: string
}) => {
  const response = await fetch(`${API_BASE_URL}/bets/place`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(betData)
  })
  if (!response.ok) throw new Error('Failed to place bet')
  return response.json()
}

export const getBetsStats = async () => {
  const response = await fetch(`${API_BASE_URL}/bets/stats`)
  if (!response.ok) throw new Error('Failed to fetch stats')
  return response.json()
}

export const getBetsHistory = async (limit = 50, status?: string) => {
  const params = new URLSearchParams({ limit: limit.toString() })
  if (status) params.append('status', status)
  const response = await fetch(`${API_BASE_URL}/bets/history?${params}`)
  if (!response.ok) throw new Error('Failed to fetch history')
  return response.json()
}


