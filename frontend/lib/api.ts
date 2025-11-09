import { getSession } from 'next-auth/react';
import { Opportunity, Bet, Bankroll } from '@/types';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://91.98.131.218:8000';

async function getAuthHeaders() {
  const session = await getSession();
  const headers: HeadersInit = {
    'Content-Type': 'application/json',
  };
  
  if (session?.accessToken) {
    headers['Authorization'] = `Bearer ${session.accessToken}`;
  }
  
  return headers;
}

export const api = {
  // Opportunities
  getOpportunities: async (): Promise<Opportunity[]> => {
    const headers = await getAuthHeaders();
    const response = await fetch(`${API_BASE_URL}/opportunities/realistic`, { headers });
    if (!response.ok) throw new Error('Failed to fetch opportunities');
    return response.json();
  },

  getTopOpportunities: async (limit: number = 10): Promise<Opportunity[]> => {
    const headers = await getAuthHeaders();
    const response = await fetch(`${API_BASE_URL}/opportunities/top/${limit}`, { headers });
    if (!response.ok) throw new Error('Failed to fetch top opportunities');
    return response.json();
  },

  // Bets
  getBets: async (): Promise<Bet[]> => {
    const headers = await getAuthHeaders();
    const response = await fetch(`${API_BASE_URL}/bets`, { headers });
    if (!response.ok) throw new Error('Failed to fetch bets');
    return response.json();
  },

  createBet: async (bet: Partial<Bet>): Promise<Bet> => {
    const headers = await getAuthHeaders();
    const response = await fetch(`${API_BASE_URL}/bets`, {
      method: 'POST',
      headers,
      body: JSON.stringify(bet),
    });
    if (!response.ok) throw new Error('Failed to create bet');
    return response.json();
  },

  updateBet: async (id: number, data: Partial<Bet>): Promise<Bet> => {
    const headers = await getAuthHeaders();
    const response = await fetch(`${API_BASE_URL}/bets/${id}`, {
      method: 'PUT',
      headers,
      body: JSON.stringify(data),
    });
    if (!response.ok) throw new Error('Failed to update bet');
    return response.json();
  },

  deleteBet: async (id: number): Promise<void> => {
    const headers = await getAuthHeaders();
    const response = await fetch(`${API_BASE_URL}/bets/${id}`, {
      method: 'DELETE',
      headers,
    });
    if (!response.ok) throw new Error('Failed to delete bet');
  },

  // Bankroll
  getBankroll: async (): Promise<Bankroll> => {
    const headers = await getAuthHeaders();
    const response = await fetch(`${API_BASE_URL}/bankroll`, { headers });
    if (!response.ok) throw new Error('Failed to fetch bankroll');
    return response.json();
  },

  updateBankroll: async (amount: number): Promise<Bankroll> => {
    const headers = await getAuthHeaders();
    const response = await fetch(`${API_BASE_URL}/bankroll`, {
      method: 'POST',
      headers,
      body: JSON.stringify({ amount }),
    });
    if (!response.ok) throw new Error('Failed to update bankroll');
    return response.json();
  },

  // Stats
  getStats: async (): Promise<any> => {
    const headers = await getAuthHeaders();
    const response = await fetch(`${API_BASE_URL}/stats/summary`, { headers });
    if (!response.ok) throw new Error('Failed to fetch stats');
    return response.json();
  },
};
