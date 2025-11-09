'use client';

import { useEffect, useState } from 'react';
import { useSession } from 'next-auth/react';
import { useRouter } from 'next/navigation';
import Navbar from '@/components/Navbar';
import { api } from '@/lib/api';
import { Bet } from '@/types';
import { CheckCircleIcon, XCircleIcon, ClockIcon, TrashIcon } from 'lucide-react';

export default function BetsPage() {
  const { data: session, status } = useSession();
  const router = useRouter();
  const [bets, setBets] = useState<Bet[]>([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState<'all' | 'pending' | 'won' | 'lost'>('all');

  useEffect(() => {
    if (status === 'unauthenticated') {
      router.push('/login');
    }
  }, [status, router]);

  useEffect(() => {
    if (session) {
      loadBets();
    }
  }, [session]);

  const loadBets = async () => {
    try {
      setLoading(true);
      const data = await api.getBets();
      setBets(data);
    } catch (error) {
      console.error('Error loading bets:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleDeleteBet = async (id: number) => {
    if (!confirm('Êtes-vous sûr de vouloir supprimer ce pari ?')) return;
    
    try {
      await api.deleteBet(id);
      setBets(bets.filter((bet) => bet.id !== id));
    } catch (error) {
      console.error('Error deleting bet:', error);
      alert('Erreur lors de la suppression du pari');
    }
  };

  const filteredBets = filter === 'all' ? bets : bets.filter((bet) => bet.status === filter);

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'won':
        return <CheckCircleIcon className="text-success" size={20} />;
      case 'lost':
        return <XCircleIcon className="text-danger" size={20} />;
      case 'pending':
        return <ClockIcon className="text-warning" size={20} />;
      default:
        return null;
    }
  };

  const getStatusLabel = (status: string) => {
    const labels = {
      pending: 'En attente',
      won: 'Gagné',
      lost: 'Perdu',
      void: 'Annulé',
    };
    return labels[status as keyof typeof labels] || status;
  };

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
          <h1 className="text-3xl font-bold text-gray-900">Mes Paris</h1>
          <p className="text-gray-600 mt-1">{filteredBets.length} paris</p>
        </div>

        <div className="bg-white rounded-lg shadow-md p-4 mb-6">
          <div className="flex gap-2">
            <button
              onClick={() => setFilter('all')}
              className={`px-4 py-2 rounded-md font-medium transition-colors ${
                filter === 'all' ? 'bg-primary text-white' : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
              }`}
            >
              Tous
            </button>
            <button
              onClick={() => setFilter('pending')}
              className={`px-4 py-2 rounded-md font-medium transition-colors ${
                filter === 'pending' ? 'bg-warning text-white' : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
              }`}
            >
              En attente
            </button>
            <button
              onClick={() => setFilter('won')}
              className={`px-4 py-2 rounded-md font-medium transition-colors ${
                filter === 'won' ? 'bg-success text-white' : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
              }`}
            >
              Gagnés
            </button>
            <button
              onClick={() => setFilter('lost')}
              className={`px-4 py-2 rounded-md font-medium transition-colors ${
                filter === 'lost' ? 'bg-danger text-white' : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
              }`}
            >
              Perdus
            </button>
          </div>
        </div>

        <div className="space-y-4">
          {filteredBets.length === 0 ? (
            <div className="bg-white rounded-lg shadow-md p-12 text-center">
              <p className="text-gray-500 text-lg">Aucun pari pour le moment</p>
            </div>
          ) : (
            filteredBets.map((bet) => (
              <div key={bet.id} className="bg-white rounded-lg shadow-md p-6 hover:shadow-lg transition-shadow">
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <div className="flex items-center gap-3 mb-2">
                      {getStatusIcon(bet.status)}
                      <span className="font-semibold text-gray-900">{getStatusLabel(bet.status)}</span>
                      <span className="px-3 py-1 bg-gray-100 text-gray-700 text-xs font-medium rounded-full">{bet.sport}</span>
                      <span className="text-sm text-gray-500">{bet.bookmaker}</span>
                    </div>
                    <h3 className="text-lg font-semibold text-gray-900 mb-2">{bet.event_description}</h3>
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
                      <div>
                        <p className="text-gray-500">Cote</p>
                        <p className="font-semibold text-gray-900">{bet.odds.toFixed(2)}</p>
                      </div>
                      <div>
                        <p className="text-gray-500">Mise</p>
                        <p className="font-semibold text-gray-900">{bet.stake.toFixed(2)} €</p>
                      </div>
                      <div>
                        <p className="text-gray-500">Gain potentiel</p>
                        <p className="font-semibold text-gray-900">{bet.potential_return.toFixed(2)} €</p>
                      </div>
                      <div>
                        <p className="text-gray-500">Résultat</p>
                        <p className={`font-semibold ${
                          bet.profit_loss && bet.profit_loss > 0 ? 'text-success' : 
                          bet.profit_loss && bet.profit_loss < 0 ? 'text-danger' : 
                          'text-gray-900'
                        }`}>
                          {bet.profit_loss ? `${bet.profit_loss > 0 ? '+' : ''}${bet.profit_loss.toFixed(2)} €` : '-'}
                        </p>
                      </div>
                    </div>
                    <p className="text-xs text-gray-500 mt-3">
                      Placé le {new Date(bet.placed_at).toLocaleString('fr-FR')}
                      {bet.settled_at && ` • Réglé le ${new Date(bet.settled_at).toLocaleString('fr-FR')}`}
                    </p>
                  </div>
                  <button
                    onClick={() => handleDeleteBet(bet.id)}
                    className="ml-4 p-2 text-danger hover:bg-danger/10 rounded-md transition-colors"
                    title="Supprimer le pari"
                  >
                    <TrashIcon size={20} />
                  </button>
                </div>
              </div>
            ))
          )}
        </div>
      </main>
    </div>
  );
}
