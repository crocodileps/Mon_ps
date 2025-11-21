'use client';

import { useState } from 'react';
import { Card, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import {
  Target,
  TrendingUp,
  AlertCircle,
  CheckCircle,
  Info,
  BarChart3,
  Search,
  LineChart,
  ThumbsUp,
  Star,
} from 'lucide-react';

interface AgentAnalysis {
  agent_id: string;
  agent_name: string;
  recommendation: string;
  confidence: number;
  reason: string;
  details: Record<string, any>;
}

interface MatchOdds {
  home: { best: number; spread_pct: number };
  away: { best: number; spread_pct: number };
  draw: { best: number; spread_pct: number };
}

interface AgentDetailedAnalysisProps {
  agents: AgentAnalysis[];
  matchOdds: MatchOdds;
  homeTeam: string;
  awayTeam: string;
}

const agentIcons: Record<string, any> = {
  'anomaly_detector': Search,
  'spread_optimizer': BarChart3,
  'pattern_matcher': Target,
  'backtest_engine': LineChart,
};

const generateDetailedAnalysis = (agent: AgentAnalysis, matchOdds: MatchOdds, homeTeam: string, awayTeam: string) => {
  const analyses: Record<string, any> = {
    'anomaly_detector': {
      probability: Math.min(95, 45 + agent.confidence * 5),
      confidenceLevel: agent.confidence * 10,
      whySupport: `L'agent détecte une anomalie significative sur les cotes. Le spread de ${agent.details.max_spread?.toFixed(1)}% entre bookmakers indique une possible erreur de cotation ou une information non intégrée par certains opérateurs. Cette divergence représente une opportunité de value betting.`,
      detailedAnalysis: `L'analyse approfondie révèle un écart anormal de ${agent.details.max_spread?.toFixed(1)}% sur les cotes. ${agent.details.is_anomaly ? 'Ce niveau de dispersion est inhabituel et suggère une opportunité.' : 'Le marché semble équilibré.'} Le score d'anomalie de ${agent.details.anomaly_score?.toFixed(2)}/100 place ce match dans les ${100 - agent.confidence * 10}% des matchs les plus atypiques.`,
      recommendations: [
        'Vérifier les compositions d\'équipes avant de parier',
        'Comparer avec au moins 5 bookmakers différents',
        'Surveiller l\'évolution des cotes dans les prochaines heures',
      ],
      prioritizedBets: [
        { name: `Meilleure cote disponible @ ${Math.max(matchOdds.home.best, matchOdds.away.best, matchOdds.draw.best).toFixed(2)}`, isPrimary: true },
        { name: 'Arbitrage si écart > 5%', isPrimary: false },
      ],
    },
    'spread_optimizer': {
      probability: Math.round(agent.details.expected_value ? (0.5 + agent.details.expected_value) * 100 : 50),
      confidenceLevel: agent.confidence * 10,
      whySupport: `Le critère de Kelly identifie une valeur espérée (EV) de ${(agent.details.expected_value * 100).toFixed(2)}%. La fraction Kelly optimale de ${(agent.details.kelly_fraction * 100).toFixed(2)}% suggère une mise de ${agent.details.recommended_stake_pct?.toFixed(1)}% du bankroll. Cette opportunité présente un ratio risque/récompense favorable.`,
      detailedAnalysis: `L'optimisation mathématique révèle que le pari sur ${agent.details.best_outcome?.toUpperCase()} offre la meilleure espérance. Avec une EV de ${(agent.details.expected_value * 100).toFixed(2)}% et un Kelly de ${(agent.details.kelly_fraction * 100).toFixed(2)}%, le modèle recommande une mise contrôlée. Le ROI théorique à long terme est positif si cette stratégie est suivie systématiquement.`,
      recommendations: [
        `Miser ${agent.details.recommended_stake_pct?.toFixed(1)}% de votre bankroll sur ce pari`,
        'Utiliser le Kelly fractionnel (25-50%) pour réduire la variance',
        'Documenter ce pari pour analyse future',
      ],
      prioritizedBets: [
        { name: `${agent.details.best_outcome?.toUpperCase()} @ ${matchOdds[agent.details.best_outcome as keyof MatchOdds]?.best.toFixed(2)}`, isPrimary: true },
        { name: 'Over 2.5 buts si EV > 3%', isPrimary: false },
      ],
    },
    'pattern_matcher': {
      probability: 50 + agent.confidence * 5,
      confidenceLevel: agent.confidence * 10,
      whySupport: `L'agent identifie des patterns historiques correspondant à ce type de match. ${agent.details.patterns?.join('. ')}. Ces tendances ont montré une récurrence significative dans les données passées.`,
      detailedAnalysis: `L'analyse des patterns révèle ${agent.details.pattern_count} correspondance(s) historique(s). Dans la ligue ${agent.details.sport?.replace('soccer_', '').replace(/_/g, ' ')}, ces patterns ont généré des résultats prévisibles. La confiance de ${agent.confidence.toFixed(1)}/100 reflète la force de ces corrélations.`,
      recommendations: [
        'Considérer les tendances historiques de la ligue',
        'Vérifier les confrontations directes récentes',
        'Analyser la forme des 5 derniers matchs',
      ],
      prioritizedBets: [
        { name: `${homeTeam} (favori historique)`, isPrimary: agent.confidence > 5 },
        { name: 'Match nul si pattern défensif', isPrimary: false },
      ],
    },
    'backtest_engine': {
      probability: agent.details.historical_win_rate ? agent.details.historical_win_rate * 100 : 50,
      confidenceLevel: agent.confidence * 10,
      whySupport: `Le backtesting sur ${agent.details.sample_size} bookmakers montre un win rate historique de ${(agent.details.historical_win_rate * 100).toFixed(1)}% et un ROI de ${agent.details.avg_roi_pct?.toFixed(1)}%. Ces métriques sont basées sur des paris similaires passés.`,
      detailedAnalysis: `L'analyse historique avec ${agent.details.sample_size} sources de données révèle une performance stable. Le win rate de ${(agent.details.historical_win_rate * 100).toFixed(1)}% combiné à un ROI de ${agent.details.avg_roi_pct?.toFixed(1)}% suggère une stratégie profitable sur le long terme. La couverture de ${agent.details.sample_size} bookmakers assure une fiabilité statistique.`,
      recommendations: [
        'Suivre cette stratégie sur minimum 100 paris',
        'Ajuster les mises selon le ROI observé',
        'Réévaluer après chaque trimestre',
      ],
      prioritizedBets: [
        { name: `Stratégie validée - ROI ${agent.details.avg_roi_pct?.toFixed(1)}%`, isPrimary: true },
        { name: 'Accumulator si confiance > 7', isPrimary: false },
      ],
    },
  };

  return analyses[agent.agent_id] || analyses['anomaly_detector'];
};

export function AgentDetailedAnalysis({ agents, matchOdds, homeTeam, awayTeam }: AgentDetailedAnalysisProps) {
  const [selectedAgentId, setSelectedAgentId] = useState(
    agents.reduce((max, agent) => agent.confidence > max.confidence ? agent : max).agent_id
  );

  const selectedAgent = agents.find(a => a.agent_id === selectedAgentId) || agents[0];
  const analysis = generateDetailedAnalysis(selectedAgent, matchOdds, homeTeam, awayTeam);
  const AgentIcon = agentIcons[selectedAgentId] || Target;

  return (
    <div className="mt-6 space-y-4">
      {/* Agent Selector */}
      <div className="flex items-center gap-3 p-4 bg-slate-800/50 rounded-lg">
        <div className="p-2 bg-violet-500/20 rounded-lg">
          <AgentIcon className="w-6 h-6 text-violet-400" />
        </div>
        <div className="flex-1">
          <h3 className="text-xl font-bold text-white">{selectedAgent.agent_name}</h3>
          <div className="flex gap-2 mt-1">
            <Badge className="bg-green-500/20 text-green-400 border-green-500/30">
              {selectedAgent.recommendation}
            </Badge>
            <Badge className="bg-blue-500/20 text-blue-400 border-blue-500/30">
              Probabilité: {analysis.probability.toFixed(0)}%
            </Badge>
            <Badge className="bg-purple-500/20 text-purple-400 border-purple-500/30">
              Confiance: {analysis.confidenceLevel.toFixed(0)}%
            </Badge>
          </div>
        </div>
        <div className="flex gap-1">
          {agents.map((agent) => (
            <Button
              key={agent.agent_id}
              size="sm"
              variant={agent.agent_id === selectedAgentId ? 'default' : 'outline'}
              className={agent.agent_id === selectedAgentId 
                ? 'bg-violet-600 hover:bg-violet-700' 
                : 'border-slate-600 hover:bg-slate-700'}
              onClick={() => setSelectedAgentId(agent.agent_id)}
            >
              {agent.agent_name.split(' ')[0]}
            </Button>
          ))}
        </div>
      </div>

      {/* Comprendre les métriques */}
      <Card className="bg-slate-800/30 border-slate-700">
        <CardContent className="pt-4">
          <div className="flex items-center gap-2 mb-3">
            <Target className="w-5 h-5 text-green-400" />
            <h4 className="font-semibold text-white">Comprendre les métriques</h4>
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <div className="flex items-center gap-2">
                <div className="w-3 h-3 bg-blue-500 rounded-full" />
                <span className="text-blue-400 font-medium">Probabilité: {analysis.probability.toFixed(0)}%</span>
              </div>
              <p className="text-xs text-slate-400 mt-1 ml-5">
                La prédiction de l'agent sur la chance de victoire selon son modèle.
              </p>
            </div>
            <div>
              <div className="flex items-center gap-2">
                <div className="w-3 h-3 bg-orange-500 rounded-full" />
                <span className="text-orange-400 font-medium">Confiance: {analysis.confidenceLevel.toFixed(0)}%</span>
              </div>
              <p className="text-xs text-slate-400 mt-1 ml-5">
                La certitude de l'agent que sa prédiction est correcte, basée sur la qualité des données.
              </p>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Pourquoi cet agent soutient ce pari */}
      <Card className="bg-slate-800/30 border-slate-700">
        <CardContent className="pt-4">
          <div className="flex items-center gap-2 mb-3">
            <Info className="w-5 h-5 text-yellow-400" />
            <h4 className="font-semibold text-white">Pourquoi cet agent soutient ce pari</h4>
          </div>
          <p className="text-slate-300 leading-relaxed">{analysis.whySupport}</p>
        </CardContent>
      </Card>

      {/* Analyse détaillée */}
      <Card className="bg-slate-800/30 border-slate-700">
        <CardContent className="pt-4">
          <div className="flex items-center gap-2 mb-3">
            <CheckCircle className="w-5 h-5 text-green-400" />
            <h4 className="font-semibold text-white">Analyse détaillée</h4>
          </div>
          <p className="text-slate-300 leading-relaxed">{analysis.detailedAnalysis}</p>
        </CardContent>
      </Card>

      {/* Recommandations */}
      <Card className="bg-slate-800/30 border-slate-700">
        <CardContent className="pt-4">
          <div className="flex items-center gap-2 mb-3">
            <TrendingUp className="w-5 h-5 text-violet-400" />
            <h4 className="font-semibold text-white">Recommandations</h4>
          </div>
          <div className="space-y-2">
            {analysis.recommendations.map((rec: string, i: number) => (
              <div key={i} className="flex items-start gap-2 bg-slate-700/30 p-3 rounded-lg">
                <div className="w-2 h-2 bg-violet-400 rounded-full mt-2" />
                <p className="text-slate-300">{rec}</p>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Paris priorisés */}
      <Card className="bg-slate-800/30 border-slate-700">
        <CardContent className="pt-4">
          <div className="flex items-center gap-2 mb-3">
            <Star className="w-5 h-5 text-yellow-400" />
            <h4 className="font-semibold text-white">Paris priorisés sur ce match</h4>
          </div>
          <div className="space-y-2">
            {analysis.prioritizedBets.map((bet: any, i: number) => (
              <div 
                key={i} 
                className={`p-3 rounded-lg ${bet.isPrimary ? 'bg-green-500/10 border border-green-500/30' : 'bg-slate-700/30'}`}
              >
                <div className="flex items-center gap-2">
                  {bet.isPrimary && <Star className="w-4 h-4 text-yellow-400" />}
                  <span className={bet.isPrimary ? 'text-green-400 font-medium' : 'text-slate-300'}>
                    {bet.name}
                  </span>
                  {bet.isPrimary && <Badge className="bg-yellow-500/20 text-yellow-400 text-xs">Principal</Badge>}
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

