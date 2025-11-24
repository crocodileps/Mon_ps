'use client';

import { useState, useEffect } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { motion } from 'framer-motion';
import {
  ArrowLeft, Brain, AlertTriangle, CheckCircle,
  Clock, XCircle, Play, Check, X, Zap, Target,
  Lightbulb, Activity, BarChart3, TrendingUp, Settings
} from 'lucide-react';

interface Improvement {
  id: number;
  agent_name: string;
  baseline_win_rate: number;
  failure_pattern: string;
  missing_factors: string[];
  recommended_adjustments: any[];
  new_threshold: number;
  llm_reasoning: string;
  ab_test_active: boolean;
  improvement_applied: boolean;
  ab_test_matches_a: number;
  ab_test_matches_b: number;
  ab_test_wins_a: number;
  ab_test_wins_b: number;
  ab_win_rate_a: number;
  ab_win_rate_b: number;
}

export default function ImprovementDetailsPage() {
  const params = useParams();
  const router = useRouter();
  const [improvement, setImprovement] = useState<Improvement | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchImprovement();
  }, []);

  const fetchImprovement = async () => {
    try {
      const res = await fetch(
        `http://91.98.131.218:8001/strategies/improvements/${params.id}`
      );
      const data = await res.json();
      setImprovement(data.improvement);
      setLoading(false);
    } catch (error) {
      console.error('Erreur:', error);
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-white text-xl">Chargement...</div>
      </div>
    );
  }

  if (!improvement) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-white text-xl">Amélioration non trouvée</div>
      </div>
    );
  }

  return (
    <div className="min-h-screen p-8">
      <button
        onClick={() => router.push('/strategies')}
        className="flex items-center gap-2 text-gray-400 hover:text-white transition-colors mb-6"
      >
        <ArrowLeft className="w-5 h-5" />
        Retour aux stratégies
      </button>

      <div className="flex items-center gap-4 mb-8">
        <div className="p-3 bg-gradient-to-br from-purple-500/20 to-violet-500/20 rounded-xl border border-purple-500/30">
          <Brain className="w-8 h-8 text-purple-400" />
        </div>
        <div>
          <h1 className="text-3xl font-bold text-white">
            Amélioration GPT-4o #{improvement.id}
          </h1>
          <p className="text-gray-400">{improvement.agent_name}</p>
        </div>
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
        <div className="xl:col-span-2 space-y-6">
          {/* Métriques */}
          <div className="bg-white/5 backdrop-blur-lg rounded-xl border border-white/10 p-6">
            <h2 className="text-xl font-bold text-white mb-4 flex items-center gap-2">
              <Activity className="w-5 h-5 text-violet-400" />
              État actuel
            </h2>
            <div className="grid grid-cols-3 gap-4">
              <div className="text-center">
                <div className="text-gray-400 text-sm mb-2">Win Rate</div>
                <div className="text-3xl font-bold text-white">
                  {improvement.baseline_win_rate?.toFixed(1)}%
                </div>
              </div>
              <div className="text-center">
                <div className="text-gray-400 text-sm mb-2">Nouveau seuil</div>
                <div className="text-3xl font-bold text-green-400">
                  {improvement.new_threshold}%
                </div>
              </div>
              <div className="text-center">
                <div className="text-gray-400 text-sm mb-2">Gain attendu</div>
                <div className="text-3xl font-bold text-purple-400">
                  +{(improvement.new_threshold - improvement.baseline_win_rate).toFixed(1)}%
                </div>
              </div>
            </div>
          </div>

          {/* Pattern */}
          <div className="bg-white/5 backdrop-blur-lg rounded-xl border border-white/10 p-6">
            <h2 className="text-xl font-bold text-white mb-4 flex items-center gap-2">
              <AlertTriangle className="w-5 h-5 text-red-400" />
              Pattern des échecs
            </h2>
            <p className="text-gray-300">{improvement.failure_pattern}</p>
          </div>

          {/* Facteurs manquants */}
          <div className="bg-white/5 backdrop-blur-lg rounded-xl border border-white/10 p-6">
            <h2 className="text-xl font-bold text-white mb-4 flex items-center gap-2">
              <Target className="w-5 h-5 text-orange-400" />
              Facteurs manquants ({improvement.missing_factors?.length || 0})
            </h2>
            <div className="grid grid-cols-2 gap-3">
              {improvement.missing_factors?.map((factor, index) => (
                <div
                  key={index}
                  className="p-3 bg-orange-500/10 border border-orange-500/30 rounded-lg"
                >
                  <div className="flex items-center gap-2">
                    <XCircle className="w-4 h-4 text-orange-400" />
                    <span className="text-gray-300 text-sm">{factor}</span>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Raisonnement GPT-4o */}
          <div className="bg-gradient-to-br from-purple-500/10 to-violet-500/10 backdrop-blur-lg rounded-xl border border-purple-500/30 p-6">
            <h2 className="text-xl font-bold text-white mb-4 flex items-center gap-2">
              <Brain className="w-5 h-5 text-purple-400" />
              Raisonnement GPT-4o
            </h2>
            <p className="text-gray-300 whitespace-pre-line">
              {improvement.llm_reasoning}
            </p>
          </div>
        </div>

        {/* Sidebar actions */}
        <div>
          <div className="bg-white/5 backdrop-blur-lg rounded-xl border border-white/10 overflow-hidden sticky top-8">
            <div className="p-6 border-b border-white/10 bg-gradient-to-r from-violet-500/20 to-purple-500/20">
              <h2 className="text-xl font-bold text-white">Actions</h2>
            </div>
            <div className="p-6">
              {!improvement.improvement_applied && !improvement.ab_test_active && (
                <div className="space-y-4">
                  <button className="w-full px-4 py-3 bg-gradient-to-r from-blue-500 to-cyan-500 rounded-lg text-white font-semibold flex items-center justify-center gap-2">
                    <Play className="w-5 h-5" />
                    Activer A/B Test
                  </button>
                  <button className="w-full px-4 py-3 bg-red-500/20 border border-red-500/30 rounded-lg text-red-400 font-semibold flex items-center justify-center gap-2">
                    <X className="w-5 h-5" />
                    Rejeter
                  </button>
                </div>
              )}
              {improvement.ab_test_active && (
                <div className="p-4 bg-blue-500/10 border border-blue-500/30 rounded-lg">
                  <div className="text-blue-400 text-sm font-semibold mb-2">
                    A/B Test en cours
                  </div>
                  <div className="text-gray-300 text-xs">
                    Collecte des données...
                  </div>
                </div>
              )}
              {improvement.improvement_applied && (
                <div className="p-4 bg-green-500/10 border border-green-500/30 rounded-lg">
                  <div className="text-green-400 font-semibold mb-2">
                    ✅ Appliquée
                  </div>
                </div>
              )}
              {/* Séparateur */}
              <div className="my-6 border-t border-white/10"></div>

              {/* Bouton Gérer les améliorations */}
              <button
                onClick={() => router.push("/strategies/manage")}
                className="w-full px-4 py-3 bg-violet-500/20 hover:bg-violet-500/30 border border-violet-500/30 rounded-lg text-violet-400 font-semibold flex items-center justify-center gap-2 transition-all"
              >
                <Settings className="w-5 h-5" />
                Gérer les améliorations
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
