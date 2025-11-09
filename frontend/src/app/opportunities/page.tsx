'use client';

import { useEffect, useState } from 'react';
import { useSession } from 'next-auth/react';
import { useRouter } from 'next/navigation';
import Navbar from '@/components/Navbar';
import { api } from '@/lib/api';
import { Opportunity } from '@/types';
import { SearchIcon, FilterIcon } from 'lucide-react';

export default function OpportunitiesPage() {
  const { data: session, status } = useSession();
  const router = useRouter();
  const [opportunities, setOpportunities] = useState<Opportunity[]>([]);
  const [filteredOpportunities, setFilteredOpportunities] = useState<Opportunity[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedSport, setSelectedSport] = useState('all');
  const [selectedBookmaker, setSelectedBookmaker] = useState('all');

  useEffect(() => {
    if (status === 'unauthenticated') {
      router.push('/login');
    }
  }, [status, router]);

  useEffect(() => {
    if (session) {
      loadOpportunities();
    }
  }, [session]);

  useEffect(() => {
    filterOpportunities();
  }, [opportunities, searchTerm, selectedSport, selectedBookmaker]);

  const loadOpportunities = async () => {
    try {
      setLoading(true);
      const data = await api.getOpportunities();
      setOpportunities(data);
    } catch (error) {
      console.error('Error loading opportunities:', error);
    } finally {
      setLoading(false);
    }
  };

  const filterOpportunities = () => {
    let filtered = opportunities;

    if (searchTerm) {
      filtered = filtered.filter(
        (opp) =>
          opp.home_team.toLowerCase().includes(searchTerm.toLowerCase()) ||
          opp.away_team.toLowerCase().includes(searchTerm.toLowerCase()) ||
          opp.league.toLowerCase().includes(searchTerm.toLowerCase())
      );
    }

    if (selectedSport !== 'all') {
      filtered = filtered.filter((opp) => opp.sport === selectedSport);
    }

    if (selectedBookmaker !== 'all') {
      filtered = filtered.filter((opp) => opp.bookmaker === selectedBookmaker);
    }

    setFilteredOpportunities(filtered);
  };

  const uniqueSports = Array.from(new Set(opportunities.map((opp) => opp.sport)));
  const uniqueBookmakers = Array.from(new Set(opportunities.map((opp) => opp.bookmaker)));

  if (status === 'loading' || loading) {
    return (
      <div className="min-h-screen bg-gray-50">
        <Navbar />
        <div className="flex items-center justify-center h-screen">
          <div className="text-center">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary mx-auto"></div>
            <p className="mt-4 text-gray-600">Chargement...</p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <Navbar />
      
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900">Opportunités</h1>
          <p className="text-gray-600 mt-1">{filteredOpportunities.length} opportunités disponibles</p>
        </div>

        <div className="bg-white rounded-lg shadow-md p-6 mb-6">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">Recherche</label>
              <div className="relative">
                <input
                  type="text"
                  placeholder="Équipe, ligue..."
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-md focus:ring-primary focus:border-primary"
                />
                <SearchIcon className="absolute left-3 top-2.5 text-gray-400" size={20} />
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">Sport</label>
              <select
                value={selectedSport}
                onChange={(e) => setSelectedSport(e.target.value)}
                className="w-full px-4 py-2 border border-gray-300 rounded-md focus:ring-primary focus:border-primary"
              >
                <option value="all">Tous les sports</option>
                {uniqueSports.map((sport) => (
                  <option key={sport} value={sport}>{sport}</option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">Bookmaker</label>
              <select
                value={selectedBookmaker}
                onChange={(e) => setSelectedBookmaker(e.target.value)}
                className="w-full px-4 py-2 border border-gray-300 rounded-md focus:ring-primary focus:border-primary"
              >
                <option value="all">Tous les bookmakers</option>
                {uniqueBookmakers.map((bookmaker) => (
                  <option key={bookmaker} value={bookmaker}>{bookmaker}</option>
                ))}
              </select>
            </div>
          </div>
        </div>

        <div className="space-y-4">
          {filteredOpportunities.length === 0 ? (
            <div className="bg-white rounded-lg shadow-md p-12 text-center">
              <FilterIcon className="mx-auto text-gray-400 mb-4" size={48} />
              <p className="text-gray-500 text-lg">Aucune opportunité ne correspond à vos filtres</p>
            </div>
          ) : (
            filteredOpportunities.map((opp) => (
              <div key={opp.id} className="bg-white rounded-lg shadow-md p-6 hover:shadow-lg transition-shadow">
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <div className="flex items-center gap-3 mb-2">
                      <span className="px-3 py-1 bg-primary/10 text-primary text-xs font-semibold rounded-full">{opp.sport}</span>
                      <span className="text-sm text-gray-500">{opp.league}</span>
                      {opp.is_arbitrage && (
                        <span className="px-3 py-1 bg-success/10 text-success text-xs font-semibold rounded-full">ARBITRAGE</span>
                      )}
                    </div>
                    <h3 className="text-xl font-bold text-gray-900 mb-2">{opp.home_team} vs {opp.away_team}</h3>
                    <div className="flex items-center gap-4 text-sm text-gray-600">
                      <span>📊 {opp.market_type}</span>
                      <span>•</span>
                      <span>🎯 {opp.outcome}</span>
                      <span>•</span>
                      <span>🏪 {opp.bookmaker}</span>
                    </div>
                    {opp.match_time && (
                      <p className="text-sm text-gray-500 mt-2">🕐 {new Date(opp.match_time).toLocaleString('fr-FR')}</p>
                    )}
                  </div>
                  <div className="text-right ml-6">
                    <p className="text-4xl font-bold text-primary mb-2">{opp.odds.toFixed(2)}</p>
                    {opp.edge_percentage && (
                      <p className="text-lg font-semibold text-success">Edge: +{opp.edge_percentage.toFixed(1)}%</p>
                    )}
                    {opp.expected_value && (
                      <p className="text-sm text-gray-600 mt-1">EV: {opp.expected_value.toFixed(2)}%</p>
                    )}
                    <button className="mt-4 px-6 py-2 bg-primary text-white rounded-md hover:bg-blue-600 transition-colors font-medium">
                      Parier
                    </button>
                  </div>
                </div>
              </div>
            ))
          )}
        </div>
      </main>
    </div>
  );
}
