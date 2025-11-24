'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { motion, AnimatePresence } from 'framer-motion';
import {
  ArrowLeft, Lightbulb, TrendingUp, Clock, Archive,
  ChevronRight, Search, Filter, Loader2, Zap,
  CheckCircle, AlertCircle, Play, Settings
} from 'lucide-react';

interface Improvement {
  id: number;
  agent_name: string;
  failure_pattern: string;
  proposed_improvement: string;
  expected_gain: number;
  status: string;
  missing_factors: string[];
  created_at: string;
  ab_test_started_at?: string;
  archived_at?: string;
  archived_reason?: string;
}

export default function ManageImprovementsPage() {
  const router = useRouter();
  const [improvements, setImprovements] = useState<Improvement[]>([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState<'all' | 'proposed' | 'active' | 'archived'>('all');
  const [searchQuery, setSearchQuery] = useState('');

  useEffect(() => {
    fetchImprovements();
  }, []);

  const fetchImprovements = async () => {
    try {
      const response = await fetch('http://91.98.131.218:8001/api/ferrari/improvements');
      const data = await response.json();
      if (data.success) {
        setImprovements(data.improvements || []);
      }
    } catch (error) {
      console.error('Erreur fetch improvements:', error);
    } finally {
      setLoading(false);
    }
  };

  const filteredImprovements = improvements.filter(imp => {
    const matchesFilter = filter === 'all' || imp.status === filter;
    const matchesSearch = searchQuery === '' || 
      imp.agent_name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      imp.failure_pattern.toLowerCase().includes(searchQuery.toLowerCase());
    return matchesFilter && matchesSearch;
  });

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'proposed': return 'text-yellow-400 bg-yellow-500/10 border-yellow-500/30';
      case 'active': return 'text-green-400 bg-green-500/10 border-green-500/30';
      case 'archived': return 'text-slate-400 bg-slate-500/10 border-slate-500/30';
      default: return 'text-slate-400 bg-slate-500/10 border-slate-500/30';
    }
  };

  const getStatusLabel = (status: string) => {
    switch (status) {
      case 'proposed': return '💡 Proposée';
      case 'active': return '⚡ Test A/B';
      case 'archived': return '📦 Archivée';
      default: return status;
    }
  };

  const stats = {
    total: improvements.length,
    proposed: improvements.filter(i => i.status === 'proposed').length,
    active: improvements.filter(i => i.status === 'active').length,
    archived: improvements.filter(i => i.status === 'archived').length,
    avgGain: improvements.length > 0 
      ? improvements.reduce((sum, i) => sum + (i.expected_gain || 0), 0) / improvements.length 
      : 0
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-950 via-slate-900 to-purple-950 flex items-center justify-center">
        <Loader2 className="w-12 h-12 text-purple-400 animate-spin" />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-950 via-slate-900 to-purple-950 p-6">
      {/* Header */}
      <div className="max-w-7xl mx-auto mb-8">
        <motion.div
          initial={{ opacity: 0, y: -20 }}
          animate={{ opacity: 1, y: 0 }}
          className="flex items-center justify-between"
        >
          <div>
            <h1 className="text-4xl font-black text-transparent bg-clip-text bg-gradient-to-r from-purple-400 via-violet-400 to-purple-600">
              Gestion des Améliorations
            </h1>
            <p className="text-slate-400 mt-2">Système d'auto-amélioration GPT-4o • Intelligence Quantitative</p>
          </div>
          <motion.button
            whileHover={{ scale: 1.05 }}
            whileTap={{ scale: 0.95 }}
            onClick={() => router.push('/strategies')}
            className="px-4 py-2 bg-slate-700/50 hover:bg-slate-600/50 rounded-lg text-slate-300 flex items-center gap-2"
          >
            <ArrowLeft className="w-4 h-4" />
            Dashboard
          </motion.button>
        </motion.div>
      </div>

      {/* Stats Cards */}
      <div className="max-w-7xl mx-auto mb-8 grid grid-cols-5 gap-4">
        <motion.div
          initial={{ opacity: 0, scale: 0.9 }}
          animate={{ opacity: 1, scale: 1 }}
          className="bg-slate-800/30 backdrop-blur-xl border border-purple-500/20 rounded-xl p-4"
        >
          <div className="flex items-center gap-2 mb-2">
            <Lightbulb className="w-4 h-4 text-purple-400" />
            <span className="text-slate-400 text-xs">Total Améliorations</span>
          </div>
          <div className="text-2xl font-black text-white">{stats.total}</div>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, scale: 0.9 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ delay: 0.1 }}
          className="bg-slate-800/30 backdrop-blur-xl border border-yellow-500/20 rounded-xl p-4"
        >
          <div className="flex items-center gap-2 mb-2">
            <Clock className="w-4 h-4 text-yellow-400" />
            <span className="text-slate-400 text-xs">Proposées</span>
          </div>
          <div className="text-2xl font-black text-yellow-400">{stats.proposed}</div>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, scale: 0.9 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ delay: 0.2 }}
          className="bg-slate-800/30 backdrop-blur-xl border border-green-500/20 rounded-xl p-4"
        >
          <div className="flex items-center gap-2 mb-2">
            <Zap className="w-4 h-4 text-green-400" />
            <span className="text-slate-400 text-xs">Tests A/B Actifs</span>
          </div>
          <div className="text-2xl font-black text-green-400">{stats.active}</div>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, scale: 0.9 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ delay: 0.3 }}
          className="bg-slate-800/30 backdrop-blur-xl border border-slate-500/20 rounded-xl p-4"
        >
          <div className="flex items-center gap-2 mb-2">
            <Archive className="w-4 h-4 text-slate-400" />
            <span className="text-slate-400 text-xs">Archivées</span>
          </div>
          <div className="text-2xl font-black text-slate-400">{stats.archived}</div>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, scale: 0.9 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ delay: 0.4 }}
          className="bg-slate-800/30 backdrop-blur-xl border border-emerald-500/20 rounded-xl p-4"
        >
          <div className="flex items-center gap-2 mb-2">
            <TrendingUp className="w-4 h-4 text-emerald-400" />
            <span className="text-slate-400 text-xs">Gain Moyen</span>
          </div>
          <div className="text-2xl font-black text-emerald-400">+{stats.avgGain.toFixed(1)}%</div>
        </motion.div>
      </div>

      {/* Filters */}
      <div className="max-w-7xl mx-auto mb-6">
        <div className="flex items-center gap-4">
          <div className="flex gap-2">
            {(['all', 'proposed', 'active', 'archived'] as const).map((f) => (
              <button
                key={f}
                onClick={() => setFilter(f)}
                className={`px-4 py-2 rounded-lg text-sm font-medium transition-all ${
                  filter === f
                    ? 'bg-purple-600 text-white'
                    : 'bg-slate-800/50 text-slate-400 hover:bg-slate-700/50'
                }`}
              >
                {f === 'all' && `⚡ Toutes ${stats.total}`}
                {f === 'proposed' && `💡 Proposées ${stats.proposed}`}
                {f === 'active' && `✅ Actives ${stats.active}`}
                {f === 'archived' && `📦 Archivées ${stats.archived}`}
              </button>
            ))}
          </div>
          <div className="flex-1 relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
            <input
              type="text"
              placeholder="Rechercher par agent, pattern ou facteur..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-10 pr-4 py-2 bg-slate-800/50 border border-slate-700/50 rounded-lg text-slate-200 placeholder-slate-500 focus:outline-none focus:border-purple-500/50"
            />
          </div>
        </div>
      </div>

      {/* Improvements List */}
      <div className="max-w-7xl mx-auto space-y-4">
        <AnimatePresence>
          {filteredImprovements.map((imp, index) => {
            const status = imp.status;
            const gain = imp.expected_gain || 0;

            return (
              <motion.div
                key={imp.id}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -20 }}
                transition={{ delay: index * 0.05 }}
                className="bg-slate-800/30 backdrop-blur-xl border border-slate-700/50 rounded-xl p-6 hover:border-purple-500/30 transition-all"
              >
                <div className="flex items-start gap-6">
                  {/* Main Content */}
                  <div className="flex-1">
                    <div className="flex items-center gap-3 mb-2">
                      <h3 className="text-xl font-bold text-white">{imp.agent_name}</h3>
                      <span className={`px-3 py-1 rounded-full text-xs font-bold border ${getStatusColor(status)}`}>
                        {getStatusLabel(status)}
                      </span>
                    </div>
                    <p className="text-sm text-slate-400 line-clamp-2 mb-4">
                      {imp.failure_pattern}
                    </p>

                    {/* Missing Factors */}
                    {imp.missing_factors && imp.missing_factors.length > 0 && (
                      <div className="mb-4">
                        <div className="text-xs text-slate-500 mb-2">⚙️ FACTEURS MANQUANTS ({imp.missing_factors.length})</div>
                        <div className="flex flex-wrap gap-2">
                          {imp.missing_factors.map((factor, i) => (
                            <span
                              key={i}
                              className="px-2 py-1 bg-slate-700/50 text-slate-300 rounded text-xs"
                            >
                              {factor}
                            </span>
                          ))}
                        </div>
                      </div>
                    )}

                    {/* Dates */}
                    <div className="flex items-center gap-4 text-xs text-slate-500">
                      <span>🕐 Créée {new Date(imp.created_at).toLocaleDateString('fr-FR')}</span>
                      {imp.ab_test_started_at && (
                        <span>⚡ Test démarré {new Date(imp.ab_test_started_at).toLocaleDateString('fr-FR')}</span>
                      )}
                      {imp.archived_at && (
                        <span>📦 Archivée {new Date(imp.archived_at).toLocaleDateString('fr-FR')} • {imp.archived_reason}</span>
                      )}
                    </div>
                  </div>

                  {/* Right Side - Gain & Actions */}
                  <div className="text-right">
                    <div className="text-xs text-slate-500 mb-1 uppercase">Gain attendu</div>
                    <div className={`text-3xl font-black ${gain > 0 ? 'text-green-400' : 'text-slate-400'}`}>
                      {gain > 0 && '+'}{gain.toFixed(1)}%
                    </div>
                    <div className="text-xs text-slate-500 mt-1">
                      0.0% → {gain.toFixed(1)}%
                    </div>
                  </div>
                </div>

                {/* Actions */}
                <div className="mt-4 pt-4 border-t border-slate-700/50 flex items-center justify-end gap-3">
                  {status === 'active' && (
                    <motion.button
                      whileHover={{ scale: 1.05 }}
                      whileTap={{ scale: 0.95 }}
                      onClick={() => router.push(`/strategies/improvements/${imp.id}/variations`)}
                      className="px-4 py-2 bg-green-500/10 hover:bg-green-500/20 border border-green-500/30 rounded-lg flex items-center gap-2 transition-all cursor-pointer"
                    >
                      <div className="w-2 h-2 bg-green-400 rounded-full animate-pulse" />
                      <span className="text-green-400 font-medium text-sm">🏎️ Test A/B en cours</span>
                    </motion.button>
                  )}

                  <motion.button
                    whileHover={{ scale: 1.05 }}
                    whileTap={{ scale: 0.95 }}
                    onClick={() => router.push(`/strategies/improvements/${imp.id}`)}
                    className="px-4 py-2 bg-slate-700/30 hover:bg-slate-600/30 text-slate-300 hover:text-white rounded-lg flex items-center gap-2 transition-all font-medium"
                  >
                    Voir détails
                    <ChevronRight className="w-4 h-4" />
                  </motion.button>
                </div>
              </motion.div>
            );
          })}
        </AnimatePresence>

        {/* Empty State */}
        {filteredImprovements.length === 0 && !loading && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="text-center py-16"
          >
            <Lightbulb className="w-16 h-16 text-slate-600 mx-auto mb-4" />
            <h3 className="text-xl font-bold text-slate-400 mb-2">Aucune amélioration trouvée</h3>
            <p className="text-slate-500">Modifiez vos filtres ou attendez de nouvelles propositions</p>
          </motion.div>
        )}
      </div>
    </div>
  );
}
