'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Archive, RotateCcw, Play, Trash2, Check, X,
  Filter, Search, AlertCircle, Clock, Zap,
  ChevronRight, Loader2, CheckSquare, Square,
  TrendingUp, Award, Target, Activity, Settings
} from 'lucide-react';

// ============================================================================
// TYPES TYPESCRIPT STRICTS
// ============================================================================

interface Improvement {
  id: number;
  agent_name: string;
  strategy_name: string;
  baseline_win_rate: number;
  new_threshold: number;
  failure_pattern: string;
  missing_factors: string[];
  recommended_adjustments: string[];
  llm_reasoning: string;
  status?: 'proposed' | 'active' | 'applied' | 'archived';
  ab_test_active: boolean;
  improvement_applied: boolean;
  archived_at: string | null;
  archived_reason: string | null;
  ab_test_start: string | null;
  created_at: string;
}

type FilterType = 'all' | 'proposed' | 'active' | 'archived';

interface Stats {
  total: number;
  proposed: number;
  active: number;
  archived: number;
  avgGain: number;
}

// ============================================================================
// COMPOSANT PRINCIPAL
// ============================================================================

export default function ManageImprovementsPage() {
  const router = useRouter();
  
  // États
  const [improvements, setImprovements] = useState<Improvement[]>([]);
  const [archivedImprovements, setArchivedImprovements] = useState<Improvement[]>([]);
  const [selectedIds, setSelectedIds] = useState<Set<number>>(new Set());
  const [filter, setFilter] = useState<FilterType>('all');
  const [searchQuery, setSearchQuery] = useState('');
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState<number | string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [stats, setStats] = useState<Stats>({ total: 0, proposed: 0, active: 0, archived: 0, avgGain: 0 });

  // ============================================================================
  // CHARGEMENT DONNÉES
  // ============================================================================

  useEffect(() => {
    fetchAllImprovements();
  }, []);

  const fetchAllImprovements = async () => {
    try {
      setLoading(true);
      setError(null);

      // Charger améliorations actives/proposées
      const responseActive = await fetch('http://91.98.131.218:8001/strategies/improvements');
      if (!responseActive.ok) throw new Error('Erreur chargement améliorations actives');
      const dataActive = await responseActive.json();

      // Charger améliorations archivées
      const responseArchived = await fetch('http://91.98.131.218:8001/strategies/improvements/archived');
      if (!responseArchived.ok) throw new Error('Erreur chargement améliorations archivées');
      const dataArchived = await responseArchived.json();

      const activeImps = dataActive.improvements || [];
      const archivedImps = dataArchived.improvements || [];

      setImprovements(activeImps);
      setArchivedImprovements(archivedImps);

      // Calculer stats
      const allImps = [...activeImps, ...archivedImps];
      const proposed = activeImps.filter((i: Improvement) => !i.ab_test_active).length;
      const active = activeImps.filter((i: Improvement) => i.ab_test_active).length;
      const avgGain = allImps.length > 0
        ? allImps.reduce((sum: number, i: Improvement) => sum + (i.new_threshold - i.baseline_win_rate), 0) / allImps.length
        : 0;

      setStats({
        total: allImps.length,
        proposed,
        active,
        archived: archivedImps.length,
        avgGain
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Erreur inconnue');
    } finally {
      setLoading(false);
    }
  };

  // ============================================================================
  // ACTIONS
  // ============================================================================

  const handleArchive = async (id: number, reason: string = 'Archivage manuel') => {
    try {
      setActionLoading(id);
      const response = await fetch(
        `http://91.98.131.218:8001/strategies/improvements/${id}/archive?reason=${encodeURIComponent(reason)}`,
        { method: 'POST' }
      );
      
      if (!response.ok) throw new Error('Erreur archivage');
      
      await fetchAllImprovements();
      setSelectedIds(prev => {
        const newSet = new Set(prev);
        newSet.delete(id);
        return newSet;
      });
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Erreur archivage');
    } finally {
      setActionLoading(null);
    }
  };

  const handleReactivate = async (id: number) => {
    try {
      setActionLoading(id);
      const response = await fetch(
        `http://91.98.131.218:8001/strategies/improvements/${id}/reactivate`,
        { method: 'POST' }
      );
      
      if (!response.ok) throw new Error('Erreur réactivation');
      
      await fetchAllImprovements();
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Erreur réactivation');
    } finally {
      setActionLoading(null);
    }
  };

  const handleActivateSelected = async () => {
    if (selectedIds.size === 0) {
      alert('Aucune amélioration sélectionnée');
      return;
    }

    try {
      setActionLoading('batch-activate');
      const response = await fetch(
        'http://91.98.131.218:8001/strategies/improvements/activate-selected',
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ improvement_ids: Array.from(selectedIds) })
        }
      );
      
      if (!response.ok) {
        const data = await response.json();
        throw new Error(data.detail || 'Erreur activation');
      }
      
      await fetchAllImprovements();
      setSelectedIds(new Set());
      alert(`✅ ${selectedIds.size} amélioration(s) activée(s) avec succès !`);
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Erreur activation');
    } finally {
      setActionLoading(null);
    }
  };

  // ============================================================================
  // FILTRAGE ET RECHERCHE
  // ============================================================================

  const allImprovements = [...improvements, ...archivedImprovements];
  
  const filteredImprovements = allImprovements.filter(imp => {
    // Déterminer status
    const status = imp.archived_at ? 'archived' : (imp.ab_test_active ? 'active' : 'proposed');
    
    // Filtre par status
    if (filter !== 'all' && status !== filter) return false;

    // Filtre par recherche
    if (searchQuery) {
      const query = searchQuery.toLowerCase();
      return (
        imp.agent_name.toLowerCase().includes(query) ||
        imp.failure_pattern.toLowerCase().includes(query) ||
        imp.missing_factors.some(f => f.toLowerCase().includes(query))
      );
    }

    return true;
  });

  // ============================================================================
  // SÉLECTION
  // ============================================================================

  const toggleSelection = (id: number, status: string) => {
    // Seulement les "proposed" peuvent être sélectionnées
    if (status !== 'proposed') return;

    setSelectedIds(prev => {
      const newSet = new Set(prev);
      if (newSet.has(id)) {
        newSet.delete(id);
      } else {
        newSet.add(id);
      }
      return newSet;
    });
  };

  const selectAllProposed = () => {
    const proposedIds = filteredImprovements
      .filter(imp => !imp.archived_at && !imp.ab_test_active)
      .map(imp => imp.id);
    setSelectedIds(new Set(proposedIds));
  };

  const deselectAll = () => {
    setSelectedIds(new Set());
  };

  // ============================================================================
  // RENDER - LOADING
  // ============================================================================

  if (loading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-900 via-purple-900/20 to-slate-900 flex items-center justify-center">
        <motion.div
          initial={{ opacity: 0, scale: 0.9 }}
          animate={{ opacity: 1, scale: 1 }}
          className="text-center"
        >
          <motion.div
            animate={{ rotate: 360 }}
            transition={{ duration: 2, repeat: Infinity, ease: "linear" }}
            className="w-16 h-16 border-4 border-purple-500 border-t-transparent rounded-full mx-auto mb-6"
          />
          <p className="text-slate-300 text-lg font-semibold">Chargement des améliorations...</p>
          <p className="text-slate-500 text-sm mt-2">Analyse en cours</p>
        </motion.div>
      </div>
    );
  }

  // ============================================================================
  // RENDER - ERROR
  // ============================================================================

  if (error) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-900 via-purple-900/20 to-slate-900 flex items-center justify-center p-8">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="bg-red-500/10 border border-red-500/30 rounded-xl p-8 max-w-md"
        >
          <AlertCircle className="w-12 h-12 text-red-400 mx-auto mb-4" />
          <h2 className="text-xl font-bold text-white text-center mb-2">Erreur de chargement</h2>
          <p className="text-red-300 text-center mb-6">{error}</p>
          <button
            onClick={fetchAllImprovements}
            className="w-full px-4 py-3 bg-red-500 hover:bg-red-600 text-white rounded-lg font-semibold transition-colors"
          >
            Réessayer
          </button>
        </motion.div>
      </div>
    );
  }

  // ============================================================================
  // RENDER - PAGE PRINCIPALE
  // ============================================================================

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-purple-900/20 to-slate-900 p-8">
      {/* Header Futuriste */}
      <motion.div
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        className="mb-8"
      >
        <div className="flex items-center justify-between mb-4">
          <div>
            <h1 className="text-5xl font-bold bg-gradient-to-r from-purple-400 via-violet-400 to-purple-400 text-transparent bg-clip-text mb-2">
              Gestion des Améliorations
            </h1>
            <p className="text-slate-400 text-lg">
              Système d'auto-amélioration GPT-4o • Intelligence Quantitative
            </p>
          </div>
          <button
            onClick={() => router.push('/strategies')}
            className="px-6 py-3 bg-slate-800/50 hover:bg-slate-700/50 backdrop-blur-xl border border-slate-700/50 text-slate-300 rounded-xl transition-all hover:scale-105 flex items-center gap-2"
          >
            <ChevronRight className="w-5 h-5 rotate-180" />
            Dashboard
          </button>
        </div>
      </motion.div>

      {/* Stats Cards Futuristes */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.1 }}
        className="grid grid-cols-1 md:grid-cols-5 gap-4 mb-8"
      >
        <motion.div
          whileHover={{ scale: 1.02, y: -5 }}
          className="bg-gradient-to-br from-purple-500/20 to-violet-500/20 backdrop-blur-xl border border-purple-500/30 rounded-xl p-6 relative overflow-hidden"
        >
          <div className="absolute top-0 right-0 w-32 h-32 bg-purple-500/10 rounded-full blur-3xl" />
          <Activity className="w-8 h-8 text-purple-400 mb-3" />
          <div className="text-3xl font-bold text-white mb-1">{stats.total}</div>
          <div className="text-sm text-purple-300 font-medium">Total Améliorations</div>
        </motion.div>

        <motion.div
          whileHover={{ scale: 1.02, y: -5 }}
          className="bg-gradient-to-br from-yellow-500/20 to-amber-500/20 backdrop-blur-xl border border-yellow-500/30 rounded-xl p-6 relative overflow-hidden"
        >
          <div className="absolute top-0 right-0 w-32 h-32 bg-yellow-500/10 rounded-full blur-3xl" />
          <Clock className="w-8 h-8 text-yellow-400 mb-3" />
          <div className="text-3xl font-bold text-white mb-1">{stats.proposed}</div>
          <div className="text-sm text-yellow-300 font-medium">Proposées</div>
        </motion.div>

        <motion.div
          whileHover={{ scale: 1.02, y: -5 }}
          className="bg-gradient-to-br from-green-500/20 to-emerald-500/20 backdrop-blur-xl border border-green-500/30 rounded-xl p-6 relative overflow-hidden"
        >
          <div className="absolute top-0 right-0 w-32 h-32 bg-green-500/10 rounded-full blur-3xl" />
          <Zap className="w-8 h-8 text-green-400 mb-3" />
          <div className="text-3xl font-bold text-white mb-1">{stats.active}</div>
          <div className="text-sm text-green-300 font-medium">Tests A/B Actifs</div>
        </motion.div>

        <motion.div
          whileHover={{ scale: 1.02, y: -5 }}
          className="bg-gradient-to-br from-slate-500/20 to-gray-500/20 backdrop-blur-xl border border-slate-500/30 rounded-xl p-6 relative overflow-hidden"
        >
          <div className="absolute top-0 right-0 w-32 h-32 bg-slate-500/10 rounded-full blur-3xl" />
          <Archive className="w-8 h-8 text-slate-400 mb-3" />
          <div className="text-3xl font-bold text-white mb-1">{stats.archived}</div>
          <div className="text-sm text-slate-300 font-medium">Archivées</div>
        </motion.div>

        <motion.div
          whileHover={{ scale: 1.02, y: -5 }}
          className="bg-gradient-to-br from-blue-500/20 to-cyan-500/20 backdrop-blur-xl border border-blue-500/30 rounded-xl p-6 relative overflow-hidden"
        >
          <div className="absolute top-0 right-0 w-32 h-32 bg-blue-500/10 rounded-full blur-3xl" />
          <TrendingUp className="w-8 h-8 text-blue-400 mb-3" />
          <div className="text-3xl font-bold text-white mb-1">+{stats.avgGain.toFixed(1)}%</div>
          <div className="text-sm text-blue-300 font-medium">Gain Moyen</div>
        </motion.div>
      </motion.div>

      {/* Filtres et Recherche */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.2 }}
        className="mb-6 space-y-4"
      >
        <div className="flex flex-col md:flex-row gap-4">
          {/* Filtres */}
          <div className="flex gap-2 flex-wrap">
            {(['all', 'proposed', 'active', 'archived'] as FilterType[]).map(f => {
              const count = f === 'all' ? stats.total :
                           f === 'proposed' ? stats.proposed :
                           f === 'active' ? stats.active :
                           stats.archived;
              
              return (
                <motion.button
                  key={f}
                  whileHover={{ scale: 1.05 }}
                  whileTap={{ scale: 0.95 }}
                  onClick={() => setFilter(f)}
                  className={`px-5 py-3 rounded-xl font-semibold transition-all flex items-center gap-2 ${
                    filter === f
                      ? 'bg-gradient-to-r from-purple-600 to-violet-600 text-white shadow-lg shadow-purple-500/30'
                      : 'bg-slate-800/30 backdrop-blur-xl border border-slate-700/50 text-slate-400 hover:text-white hover:border-slate-600'
                  }`}
                >
                  {f === 'all' && <Activity className="w-4 h-4" />}
                  {f === 'proposed' && <Clock className="w-4 h-4" />}
                  {f === 'active' && <Zap className="w-4 h-4" />}
                  {f === 'archived' && <Archive className="w-4 h-4" />}
                  {f === 'all' ? 'Toutes' : f === 'proposed' ? 'Proposées' : f === 'active' ? 'Actives' : 'Archivées'}
                  <span className={`text-xs px-2 py-0.5 rounded-full ${filter === f ? 'bg-white/20' : 'bg-slate-700'}`}>
                    {count}
                  </span>
                </motion.button>
              );
            })}
          </div>

          {/* Recherche */}
          <div className="flex-1 relative">
            <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-400" />
            <input
              type="text"
              placeholder="Rechercher par agent, pattern ou facteur..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-12 pr-4 py-3 bg-slate-800/30 backdrop-blur-xl border border-slate-700/50 rounded-xl text-white placeholder-slate-500 focus:outline-none focus:border-purple-500 focus:ring-2 focus:ring-purple-500/20 transition-all"
            />
          </div>
        </div>

        {/* Barre de sélection multiple */}
        <AnimatePresence>
          {selectedIds.size > 0 && (
            <motion.div
              initial={{ opacity: 0, y: -10, height: 0 }}
              animate={{ opacity: 1, y: 0, height: 'auto' }}
              exit={{ opacity: 0, y: -10, height: 0 }}
              className="bg-gradient-to-r from-purple-600/20 via-violet-600/20 to-purple-600/20 backdrop-blur-xl border border-purple-500/50 rounded-xl p-5 flex items-center justify-between shadow-lg"
            >
              <div className="flex items-center gap-6">
                <div className="flex items-center gap-3">
                  <CheckSquare className="w-6 h-6 text-purple-400" />
                  <span className="text-white font-bold text-lg">
                    {selectedIds.size} amélioration{selectedIds.size > 1 ? 's' : ''} sélectionnée{selectedIds.size > 1 ? 's' : ''}
                  </span>
                </div>
                <button
                  onClick={deselectAll}
                  className="text-purple-300 hover:text-white transition-colors font-medium flex items-center gap-2"
                >
                  <X className="w-4 h-4" />
                  Tout désélectionner
                </button>
              </div>
              <motion.button
                whileHover={{ scale: 1.05 }}
                whileTap={{ scale: 0.95 }}
                onClick={handleActivateSelected}
                disabled={actionLoading === 'batch-activate'}
                className="px-8 py-3 bg-gradient-to-r from-purple-600 to-violet-600 hover:from-purple-500 hover:to-violet-500 text-white rounded-xl font-bold flex items-center gap-3 transition-all shadow-lg shadow-purple-500/30 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {actionLoading === 'batch-activate' ? (
                  <Loader2 className="w-5 h-5 animate-spin" />
                ) : (
                  <Play className="w-5 h-5" />
                )}
                Activer la sélection
              </motion.button>
            </motion.div>
          )}
        </AnimatePresence>

        {/* Sélection rapide */}
        {filter === 'proposed' && filteredImprovements.length > 0 && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="flex justify-end"
          >
            <button
              onClick={selectAllProposed}
              className="text-purple-400 hover:text-purple-300 font-medium text-sm flex items-center gap-2 transition-colors"
            >
              <CheckSquare className="w-4 h-4" />
              Sélectionner toutes les proposées
            </button>
          </motion.div>
        )}
      </motion.div>

      {/* Liste des améliorations */}
      <div className="space-y-4">
        <AnimatePresence mode="popLayout">
          {filteredImprovements.map((imp, index) => {
            const status = imp.archived_at ? 'archived' : (imp.ab_test_active ? 'active' : 'proposed');
            const isSelected = selectedIds.has(imp.id);
            const canSelect = status === 'proposed';
            const gain = imp.new_threshold - imp.baseline_win_rate;

            return (
              <motion.div
                key={imp.id}
                layout
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, scale: 0.95 }}
                transition={{ delay: Math.min(index * 0.03, 0.3) }}
                whileHover={{ y: -2 }}
                className={`bg-slate-800/30 backdrop-blur-xl border rounded-xl p-6 transition-all ${
                  isSelected
                    ? 'border-purple-500 shadow-xl shadow-purple-500/20'
                    : 'border-slate-700/50 hover:border-slate-600/50'
                }`}
              >
                <div className="flex items-start gap-5">
                  {/* Checkbox de sélection */}
                  {canSelect && (
                    <motion.div
                      whileHover={{ scale: 1.1 }}
                      whileTap={{ scale: 0.9 }}
                      className="pt-1"
                    >
                      <button
                        onClick={() => toggleSelection(imp.id, status)}
                        className="w-6 h-6 rounded-lg border-2 flex items-center justify-center transition-all"
                        style={{
                          borderColor: isSelected ? '#a855f7' : '#475569',
                          backgroundColor: isSelected ? '#a855f7' : 'transparent'
                        }}
                      >
                        {isSelected && <Check className="w-4 h-4 text-white" />}
                      </button>
                    </motion.div>
                  )}

                  {/* Contenu principal */}
                  <div className="flex-1 min-w-0">
                    {/* Header avec nom et status */}
                    <div className="flex items-start justify-between mb-4">
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-3 mb-2 flex-wrap">
                          <h3 className="text-xl font-bold text-white truncate">
                            {imp.agent_name}
                          </h3>
                          <motion.span
                            initial={{ scale: 0 }}
                            animate={{ scale: 1 }}
                            className={`px-3 py-1 rounded-full text-xs font-bold uppercase tracking-wider ${
                              status === 'active'
                                ? 'bg-gradient-to-r from-green-500/20 to-emerald-500/20 text-green-400 border border-green-500/30'
                                : status === 'archived'
                                ? 'bg-slate-500/20 text-slate-400 border border-slate-500/30'
                                : 'bg-gradient-to-r from-yellow-500/20 to-amber-500/20 text-yellow-400 border border-yellow-500/30'
                            }`}
                          >
                            {status === 'active' && '⚡ Test A/B'}
                            {status === 'archived' && '📦 Archivée'}
                            {status === 'proposed' && '💡 Proposée'}
                          </motion.span>
                        </div>
                        <p className="text-sm text-slate-400 line-clamp-2">
                          {imp.failure_pattern}
                        </p>
                      </div>

                      {/* Gain attendu */}
                      <motion.div
                        initial={{ scale: 0 }}
                        animate={{ scale: 1 }}
                        className="text-right ml-4 flex-shrink-0"
                      >
                        <div className="text-xs text-slate-500 mb-1 font-medium uppercase tracking-wider">Gain attendu</div>
                        <div className={`text-3xl font-black ${gain > 0 ? 'text-green-400' : 'text-slate-400'}`}>
                          {gain > 0 && '+'}{gain.toFixed(1)}%
                        </div>
                        <div className="text-xs text-slate-500 mt-1">
                          {imp.baseline_win_rate.toFixed(1)}% → {imp.new_threshold.toFixed(1)}%
                        </div>
                      </motion.div>
                    </div>

                    {/* Facteurs manquants */}
                    <div className="mb-4">
                      <div className="text-xs text-slate-500 mb-2 font-medium uppercase tracking-wider flex items-center gap-2">
                        <Target className="w-3 h-3" />
                        Facteurs manquants ({imp.missing_factors.length})
                      </div>
                      <div className="flex flex-wrap gap-2">
                        {imp.missing_factors.slice(0, 4).map((factor, i) => (
                          <motion.span
                            key={i}
                            initial={{ opacity: 0, x: -10 }}
                            animate={{ opacity: 1, x: 0 }}
                            transition={{ delay: i * 0.05 }}
                            className="px-3 py-1.5 bg-slate-700/50 backdrop-blur-sm text-slate-300 rounded-lg text-sm font-medium border border-slate-600/30"
                          >
                            {factor}
                          </motion.span>
                        ))}
                        {imp.missing_factors.length > 4 && (
                          <span className="px-3 py-1.5 bg-slate-700/30 text-slate-400 rounded-lg text-sm">
                            +{imp.missing_factors.length - 4} autres
                          </span>
                        )}
                      </div>
                    </div>

                    {/* Métadonnées */}
                    <div className="flex items-center gap-4 text-xs text-slate-500 mb-4">
                      <div className="flex items-center gap-1">
                        <Clock className="w-3 h-3" />
                        Créée {new Date(imp.created_at).toLocaleDateString('fr-FR')}
                      </div>
                      {imp.ab_test_start && (
                        <div className="flex items-center gap-1">
                          <Zap className="w-3 h-3" />
                          Test démarré {new Date(imp.ab_test_start).toLocaleDateString('fr-FR')}
                        </div>
                      )}
                      {imp.archived_at && (
                        <div className="flex items-center gap-1">
                          <Archive className="w-3 h-3" />
                          Archivée {new Date(imp.archived_at).toLocaleDateString('fr-FR')}
                          {imp.archived_reason && ` • ${imp.archived_reason}`}
                        </div>
                      )}
                    </div>

                    {/* Actions */}
                    <div className="flex items-center gap-3 flex-wrap">
                      {status === 'proposed' && (
                        <motion.button
                          whileHover={{ scale: 1.05 }}
                          whileTap={{ scale: 0.95 }}
                          onClick={() => handleArchive(imp.id)}
                          disabled={actionLoading === imp.id}
                          className="px-4 py-2 bg-slate-700/50 hover:bg-slate-600/50 backdrop-blur-sm text-slate-300 hover:text-white rounded-lg flex items-center gap-2 transition-all font-medium disabled:opacity-50"
                        >
                          {actionLoading === imp.id ? (
                            <Loader2 className="w-4 h-4 animate-spin" />
                          ) : (
                            <Archive className="w-4 h-4" />
                          )}
                          Archiver
                        </motion.button>
                      )}

                      {status === 'archived' && (
                        <motion.button
                          whileHover={{ scale: 1.05 }}
                          whileTap={{ scale: 0.95 }}
                          onClick={() => handleReactivate(imp.id)}
                          disabled={actionLoading === imp.id}
                          className="px-4 py-2 bg-gradient-to-r from-purple-600/20 to-violet-600/20 hover:from-purple-600/30 hover:to-violet-600/30 backdrop-blur-sm text-purple-400 hover:text-purple-300 rounded-lg flex items-center gap-2 transition-all font-medium border border-purple-500/30 disabled:opacity-50"
                        >
                          {actionLoading === imp.id ? (
                            <Loader2 className="w-4 h-4 animate-spin" />
                          ) : (
                            <RotateCcw className="w-4 h-4" />
                          )}
                          Réactiver
                        </motion.button>
                      )}

                      {status === 'active' && (
                        <motion.button
                          whileHover={{ scale: 1.05 }}
                          whileTap={{ scale: 0.95 }}
                          onClick={() => router.push(`/strategies/improvements/${imp.id}/variations`)}
                          className="px-4 py-2 bg-green-500/10 hover:bg-green-500/20 border border-green-500/30 rounded-lg flex items-center gap-2 cursor-pointer transition-all"
                        >
                          <div className="w-2 h-2 bg-green-400 rounded-full animate-pulse" />
                          <span className="text-green-400 font-medium text-sm">🏎️ Test A/B en cours</span>
                        </motion.button>
                      )}
                          <span className="text-green-400 font-medium text-sm">Test A/B en cours</span>
                        </motion.button>
                      )}

                      <motion.button
                        whileHover={{ scale: 1.05 }}
                        whileTap={{ scale: 0.95 }}
                        onClick={() => router.push(`/strategies/improvements/${imp.id}`)}
                        className="px-4 py-2 bg-slate-700/30 hover:bg-slate-600/30 backdrop-blur-sm text-slate-300 hover:text-white rounded-lg flex items-center gap-2 transition-all font-medium"
                      >
                        Voir détails
                        <ChevronRight className="w-4 h-4" />
                      </motion.button>

                      {status === 'active' && (
                        <motion.button
                          whileHover={{ scale: 1.05 }}
                          whileTap={{ scale: 0.95 }}
                          onClick={() => router.push(`/strategies/improvements/${imp.id}/variations`)}
                          className="px-4 py-2 bg-purple-600 hover:bg-purple-500 text-white rounded-lg flex items-center gap-2 font-bold shadow-lg"
                        >
                          🏎️ Variations Ferrari
                        </motion.button>
                      )}
                    </div>
                  </div>
                </div>
              </motion.div>
            );
          })}
        </AnimatePresence>

        {/* Aucun résultat */}
        {filteredImprovements.length === 0 && !loading && (
          <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            className="text-center py-16"
          >
            <motion.div
              animate={{ y: [0, -10, 0] }}
              transition={{ duration: 2, repeat: Infinity }}
            >
              <AlertCircle className="w-16 h-16 text-slate-600 mx-auto mb-6" />
            </motion.div>
            <h3 className="text-xl font-bold text-slate-400 mb-2">Aucune amélioration trouvée</h3>
            <p className="text-slate-500">
              {searchQuery
                ? 'Essayez une autre recherche'
                : filter !== 'all'
                ? `Aucune amélioration ${filter === 'proposed' ? 'proposée' : filter === 'active' ? 'active' : 'archivée'}`
                : 'Aucune amélioration disponible'}
            </p>
          </motion.div>
        )}
      </div>
    </div>
  );
}
