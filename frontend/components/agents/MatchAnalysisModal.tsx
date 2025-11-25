'use client';

import { useQuery } from '@tanstack/react-query';
import { api } from '@/lib/api';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { 
  Brain, 
  TrendingUp, 
  AlertTriangle, 
  CheckCircle2, 
  XCircle,
  Loader2,
  Target,
  BarChart3,
  Search,
  LineChart
} from 'lucide-react';

import { HelpCircle } from 'lucide-react';
import { AgentDetailedAnalysis } from './AgentDetailedAnalysis';
import { PatronAnalysisCard } from './PatronAnalysisCard'

interface AgentAnalysis {
  agent_id: string;
  agent_name: string;
  icon: string;
  status: string;
  recommendation: string;
  confidence: number;
  reason: string;
  details: Record<string, any>;
}

interface MatchAnalysisData {
  match: {
    match_id: string;
    home_team: string;
    away_team: string;
    sport: string;
    commence_time: string;
    odds: {
      home: { best: number; worst: number; spread_pct: number };
      away: { best: number; worst: number; spread_pct: number };
      draw: { best: number; worst: number; spread_pct: number };
    };
    bookmaker_count: number;
  };
  agents: AgentAnalysis[];
  global_score: {
    average_confidence: number;
    total_confidence: number;
    active_agents: number;
    recommendation: string;
  };
  timestamp: string;
}

interface MatchAnalysisModalProps {
  matchId: string;
  matchName: string;
  isOpen: boolean;
  onClose: () => void;
}
const getRecommendationColor = (rec: string) => {
  switch (rec) {
    case 'STRONG BET': return 'bg-green-500 text-white';
    case 'CONSIDER': return 'bg-blue-500 text-white';
    case 'CAUTION': return 'bg-yellow-500 text-black';
    default: return 'bg-gray-500 text-white';
  }
};

const getAgentIcon = (agentId: string) => {
  switch (agentId) {
    case 'anomaly_detector': return <Search className="w-6 h-6" />;
    case 'spread_optimizer': return <BarChart3 className="w-6 h-6" />;
    case 'pattern_matcher': return <Target className="w-6 h-6" />;
    case 'backtest_engine': return <LineChart className="w-6 h-6" />;
    default: return <Brain className="w-6 h-6" />;
  }
};

const getConfidenceColor = (confidence: number) => {
  if (confidence >= 7) return 'text-green-400';
  if (confidence >= 5) return 'text-blue-400';
  if (confidence >= 3) return 'text-yellow-400';
  return 'text-red-400';
};

const getRecommendationBadge = (rec: string) => {
  const colors: Record<string, string> = {
    'REVIEW': 'bg-yellow-500/20 text-yellow-400 border-yellow-500/30',
    'HOME': 'bg-green-500/20 text-green-400 border-green-500/30',
    'AWAY': 'bg-blue-500/20 text-blue-400 border-blue-500/30',
    'PASS': 'bg-gray-500/20 text-gray-400 border-gray-500/30',
    'PATTERNS FOUND': 'bg-cyan-500/20 text-cyan-400 border-cyan-500/30',
    'POSITIVE': 'bg-green-500/20 text-green-400 border-green-500/30',
    'NEUTRAL': 'bg-gray-500/20 text-gray-400 border-gray-500/30',
  };
  return colors[rec] || 'bg-slate-500/20 text-slate-400 border-slate-500/30';
};

const agentDescriptions: Record<string, string> = {
  'anomaly_detector': 'Détecte les écarts de cotes anormaux entre bookmakers. Un score élevé indique une opportunité inhabituelle.',
  'spread_optimizer': 'Calcule la valeur espérée (EV) et la mise optimale selon le critère de Kelly.',
  'pattern_matcher': 'Identifie des patterns historiques dans la ligue, équipe ou type de match.',
  'backtest_engine': 'Analyse la performance historique de paris similaires pour estimer la rentabilité.',
};

const globalScoreExplanation = "Moyenne des scores de confiance des 4 agents ML. Plus le score est élevé, plus l'opportunité est prometteuse.";

export function MatchAnalysisModal({ matchId, matchName, isOpen, onClose }: MatchAnalysisModalProps) {
  const { data, isLoading, error } = useQuery<MatchAnalysisData>({
    queryKey: ['match-analysis', matchId],
    queryFn: async () => {
      const { data } = await api.get(`/agents/analyze/${matchId}`);
      return data;
    },
    enabled: isOpen && !!matchId,
    staleTime: 60000,
  });

  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="bg-slate-900 border-slate-700 text-white max-w-[95vw] max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="text-2xl font-bold flex items-center gap-3">
            <Brain className="w-7 h-7 text-violet-400" />
            Analyse des Agents ML
          </DialogTitle>
        </DialogHeader>

        {isLoading ? (
          <div className="flex flex-col items-center justify-center py-12 gap-4">
            <Loader2 className="w-12 h-12 animate-spin text-violet-400" />
            <p className="text-slate-400">Analyse en cours par les 4 agents...</p>
          </div>
        ) : error ? (
          <div className="flex flex-col items-center justify-center py-12 gap-4">
            <XCircle className="w-12 h-12 text-red-400" />
            <p className="text-red-400">Erreur lors de l analyse</p>
          </div>
        ) : data ? (
          <div className="space-y-6 mt-4">
{/* Match Info */}
            <Card className="bg-slate-800/50 border-slate-700">
              <CardContent className="pt-6">
                <div className="flex justify-between items-center">
                  <div>
                    <h3 className="text-xl font-bold text-white">
                      {data.match.home_team} vs {data.match.away_team}
                    </h3>
                    <p className="text-slate-400 text-sm mt-1">
                      {data.match.sport.replace('soccer_', '').replace(/_/g, ' ').toUpperCase()}
                    </p>
                  </div>
                  <div className="text-right">
                    <p className="text-sm text-slate-400">Bookmakers</p>
                    <p className="text-2xl font-bold text-violet-400">{data.match.bookmaker_count}</p>
                  </div>
                </div>
                <div className="grid grid-cols-3 gap-4 mt-6">
                  <div className="bg-slate-700/50 p-3 rounded-lg text-center">
                    <p className="text-xs text-slate-400">HOME</p>
                    <p className="text-lg font-bold text-white">{data.match.odds.home.best.toFixed(2)}</p>
                    <p className="text-xs text-slate-500">Spread: {data.match.odds.home.spread_pct.toFixed(1)}%</p>
                  </div>
                  <div className="bg-slate-700/50 p-3 rounded-lg text-center">
                    <p className="text-xs text-slate-400">DRAW</p>
                    <p className="text-lg font-bold text-white">{data.match.odds.draw.best.toFixed(2)}</p>
                    <p className="text-xs text-slate-500">Spread: {data.match.odds.draw.spread_pct.toFixed(1)}%</p>
                  </div>
                  <div className="bg-slate-700/50 p-3 rounded-lg text-center">
                    <p className="text-xs text-slate-400">AWAY</p>
                    <p className="text-lg font-bold text-white">{data.match.odds.away.best.toFixed(2)}</p>
                    <p className="text-xs text-slate-500">Spread: {data.match.odds.away.spread_pct.toFixed(1)}%</p>
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* Global Score */}
            <Card className="bg-gradient-to-r from-violet-900/50 to-purple-900/50 border-violet-500/30">
              <CardContent className="pt-6">
                <div className="flex justify-between items-center">
                  <div className="flex items-center gap-2">
                    <h4 className="text-lg font-semibold text-violet-200">Score Global</h4>
                    <div className="group relative">
                      <HelpCircle className="w-4 h-4 text-slate-400 cursor-help" />
                      <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 px-3 py-2 bg-slate-800 text-xs text-slate-300 rounded-lg opacity-0 group-hover:opacity-100 transition-opacity w-64 pointer-events-none z-50">
                        {globalScoreExplanation}
                        <div className="mt-2 text-xs">
                          <div className="text-green-400">70+ = EXCELLENT</div>
                          <div className="text-blue-400">50-70 = RECOMMANDÉ</div>
                          <div className="text-yellow-400">30-50 = MODÉRÉ</div>
                          <div className="text-red-400">&lt;30 = RISQUÉ</div>
                        </div>
                      </div>
                    </div>
                    <p className="text-slate-400 text-sm ml-2">{data.global_score.active_agents} agents actifs</p>
                  </div>
                  <div className="text-right">
                    <p className={`text-4xl font-bold ${getConfidenceColor(data.global_score.average_confidence)}`}>
                      {data.global_score.average_confidence.toFixed(1)}
                    </p>
                    <p className="text-xs text-slate-400">/ 100</p>
                  </div>
                </div>
                <div className="mt-4">
                </div>
              </CardContent>
            </Card>


            {/* Agents Grid */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {data.agents.map((agent) => (
                <Card key={agent.agent_id} className="bg-slate-800/80 border-slate-700 hover:border-violet-500/50 transition-all">
                  <CardHeader className="pb-3">
                    <CardTitle className="flex items-center justify-between">
                      <div className="flex items-center gap-3">
                        <div className="p-2 bg-slate-700 rounded-lg text-violet-400">
                          {getAgentIcon(agent.agent_id)}
                        </div>
                        <span className="text-base font-semibold">{agent.agent_name}</span>
                      </div>
                      <Badge className={`${getRecommendationBadge(agent.recommendation)} border`}>
                        {agent.recommendation}
                      </Badge>
                    </CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-3">
                    <div className="flex justify-between items-center">
                      <span className="text-sm text-slate-400">Confiance</span>
                      <span className={`text-xl font-bold ${getConfidenceColor(agent.confidence)}`}>
                        {agent.confidence.toFixed(1)}/100
                      </span>
                    </div>
                    <div className="bg-slate-700/50 p-3 rounded-lg">
                      <p className="text-sm text-slate-300">{agent.reason}</p>
                    </div>
                    {/* Description de l agent */}
                    <p className="text-xs text-slate-500 italic">
                      {agentDescriptions[agent.agent_id]}
                    </p>
{/* Agent-specific details */}
                    {agent.agent_id === 'spread_optimizer' && agent.details.expected_value > 0 && (
                      <div className="grid grid-cols-2 gap-2 text-xs">
                        <div className="bg-green-500/10 p-2 rounded">
                          <p className="text-slate-400">EV</p>
                          <p className="text-green-400 font-bold">{(agent.details.expected_value * 100).toFixed(2)}%</p>
                        </div>
                        <div className="bg-blue-500/10 p-2 rounded">
                          <p className="text-slate-400">Kelly</p>
                          <p className="text-blue-400 font-bold">{(agent.details.kelly_fraction * 100).toFixed(2)}%</p>
                        </div>
                        <div className="col-span-2 bg-violet-500/10 p-2 rounded">
                          <p className="text-slate-400">Mise recommandée</p>
                          <p className="text-violet-400 font-bold">{agent.details.recommended_stake_pct.toFixed(1)}% du bankroll</p>
                        </div>
                      </div>
                    )}

                    {agent.agent_id === 'backtest_engine' && agent.details.avg_roi_pct > 0 && (
                      <div className="grid grid-cols-2 gap-2 text-xs">
                        <div className="bg-green-500/10 p-2 rounded">
                          <p className="text-slate-400">Win Rate</p>
                          <p className="text-green-400 font-bold">{(agent.details.historical_win_rate * 100).toFixed(1)}%</p>
                        </div>
                        <div className="bg-blue-500/10 p-2 rounded">
                          <p className="text-slate-400">ROI Historique</p>
                          <p className="text-blue-400 font-bold">{agent.details.avg_roi_pct.toFixed(1)}%</p>
                        </div>
                      </div>
                    )}

                    {agent.agent_id === 'anomaly_detector' && agent.details.is_anomaly && (
                      <div className="bg-yellow-500/10 p-2 rounded text-xs">
                        <p className="text-slate-400">Score Anomalie</p>
                        <p className="text-yellow-400 font-bold">{agent.details.anomaly_score.toFixed(2)}/100</p>
                      </div>
                    )}

                    {agent.agent_id === 'pattern_matcher' && agent.details.patterns?.length > 0 && (
                      <div className="flex flex-wrap gap-1">
                        {agent.details.patterns.map((pattern: string, i: number) => (
                          <Badge key={i} variant="outline" className="text-xs border-cyan-500/30 text-cyan-400">
                            {pattern}
                          </Badge>
                        ))}
                      </div>
                    )}
                  </CardContent>
                </Card>
              ))}
            </div>
            {/* Analyse détaillée de l agent sélectionné */}
            <AgentDetailedAnalysis
              agents={data.agents}
              matchOdds={data.match.odds}
              homeTeam={data.match.home_team}
              awayTeam={data.match.away_team}
            />

          {/* Agent Patron - Meta-Analyse */}
          <div className="mt-6">
            <PatronAnalysisCard matchId={matchId} />
          </div>

            <p className="text-xs text-slate-500 text-center">
              Analyse effectuée le {new Date(data.timestamp).toLocaleString('fr-FR')}
            </p>
          </div>
        ) : null}

        <div className="flex justify-end mt-4">
          <Button onClick={onClose} variant="outline" className="border-slate-600 text-slate-300">
            Fermer
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
}
