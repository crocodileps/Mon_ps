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
  return data;
}

// Bets
export async function getBets(params?: any) {
  const { data } = await api.get("/bets/bets/", { params });
  return data;
}

export default api;
