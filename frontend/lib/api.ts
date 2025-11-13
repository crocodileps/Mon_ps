import axios from "axios";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://backend:8000";

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    "Content-Type": "application/json",
  },
});

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
