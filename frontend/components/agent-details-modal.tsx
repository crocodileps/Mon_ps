'use client'

import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent } from '@/components/ui/card'
import { TrendingUp, Target, Brain, BarChart3, Shield, Zap } from 'lucide-react'

interface AgentDetailsModalProps {
  isOpen: boolean
  onClose: () => void
  agent: {
    id: string
    name: string
    successRate: number
    riskProfile: string
    performance: string
    color: string
  } | null
}

const agentStrategies = {
  titan: {
    methodology: "Titan utilise un modèle statistique pur (simulations de Monte Carlo) pour identifier les value bets à long terme.",
    strengths: [
      "Analyse statistique approfondie avec 10 000+ simulations par match",
      "Identification précise des inefficacités de marché",
      "Historique de 92.4% de réussite sur 3 ans",
      "Gestion rigoureuse du risque avec bankroll management"
    ],
    weaknesses: [
      "Sensible aux événements imprévisibles (blessures de dernière minute)",
      "Peut sous-performer sur des marchés à faible liquidité",
      "Temps de calcul élevé pour les décisions complexes"
    ],
    focus: "Sports à haute volumétrie de données (NBA, NFL, Tennis Grand Chelem)",
    updateFrequency: "Temps réel avec réévaluation toutes les 15 minutes"
  },
  oracle: {
    methodology: "Oracle combine l'analyse statistique avec des facteurs contextuels (météo, historique des confrontations, forme récente).",
    strengths: [
      "Équilibre parfait entre statistiques et contexte",
      "Adaptation rapide aux changements de conditions",
      "88.1% de taux de réussite avec risque modéré",
      "Intégration de flux de news en temps réel via API"
    ],
    weaknesses: [
      "Moins performant sur les cotes extrêmes (< 1.20)",
      "Nécessite une supervision humaine légère (8% des cas)",
      "Dépendance aux sources de données externes"
    ],
    focus: "Football européen, Basketball NBA, Rugby",
    updateFrequency: "Ajustement des probabilités 1h avant le match"
  },
  momentum: {
    methodology: "Momentum se concentre sur les paris à haute volatilité avec des gains potentiels élevés.",
    strengths: [
      "ROI élevé sur les paris réussis (+150% en moyenne)",
      "Excellente détection des opportunités de trading live",
      "Spécialiste des paris combinés à forte cote",
      "Réactivité instantanée aux mouvements de marché"
    ],
    weaknesses: [
      "Taux de réussite plus faible (75%) compensé par des gains élevés",
      "Risque de pertes importantes en période de volatilité",
      "Nécessite un bankroll conséquent pour absorber la variance"
    ],
    focus: "Tous sports, spécialisation sur les paris live et combinés",
    updateFrequency: "Surveillance continue 24/7 avec alertes instantanées"
  }
}

export function AgentDetailsModal({ isOpen, onClose, agent }: AgentDetailsModalProps) {
  if (!agent) return null

  const strategy = agentStrategies[agent.id as keyof typeof agentStrategies]

  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="max-w-[90vw] md:max-w-[1400px] max-h-[90vh] overflow-y-auto bg-[#0a1128]/95 backdrop-blur-xl border border-white/20">
        <DialogHeader className="sticky top-0 bg-[#0a1128]/95 backdrop-blur-xl pb-4 z-10 border-b border-white/10">
          <div className="flex items-center gap-3">
            <Brain className="w-8 h-8 text-cyan-400" />
            <div>
              <DialogTitle className="text-3xl font-bold bg-gradient-to-r from-cyan-400 to-blue-500 bg-clip-text text-transparent">
                Agent {agent.name}
              </DialogTitle>
              <p className="text-sm text-muted-foreground mt-1">Stratégie & Méthodologie Détaillée</p>
            </div>
          </div>
          
          <div className="flex flex-wrap gap-3 mt-4">
            <Badge className={`px-3 py-1.5 ${
              agent.riskProfile === 'Faible' ? 'bg-green-500/20 text-green-300 border-green-500/30' :
              agent.riskProfile === 'Moyen' ? 'bg-yellow-500/20 text-yellow-300 border-yellow-500/30' :
              'bg-red-500/20 text-red-300 border-red-500/30'
            }`}>
              <Shield className="w-3 h-3 mr-1" />
              Risque: {agent.riskProfile}
            </Badge>
            <Badge className="px-3 py-1.5 bg-cyan-500/20 text-cyan-300 border-cyan-500/30">
              <Target className="w-3 h-3 mr-1" />
              Succès: {agent.successRate}%
            </Badge>
            <Badge className={`px-3 py-1.5 ${agent.performance.includes('-') ? 'bg-red-500/20 text-red-300 border-red-500/30' : 'bg-green-500/20 text-green-300 border-green-500/30'}`}>
              <TrendingUp className="w-3 h-3 mr-1" />
              Perf: {agent.performance}
            </Badge>
          </div>
        </DialogHeader>

        <div className="space-y-6 py-4">
          <Card className="border border-cyan-500/30 bg-gradient-to-br from-cyan-500/10 to-blue-500/5">
            <CardContent className="p-6">
              <div className="flex items-center gap-2 mb-4">
                <BarChart3 className="w-6 h-6 text-cyan-400" />
                <h3 className="text-xl font-bold text-cyan-400">Stratégie Détaillée</h3>
              </div>
              <p className="text-sm leading-relaxed text-foreground/90">
                {strategy?.methodology || "Stratégie non disponible"}
              </p>
            </CardContent>
          </Card>

          <div className="grid md:grid-cols-2 gap-4">
            <Card className="border border-green-500/30 bg-green-500/5">
              <CardContent className="p-5">
                <h4 className="text-lg font-semibold text-green-400 mb-3 flex items-center gap-2">
                  <Zap className="w-5 h-5" />
                  Forces
                </h4>
                <ul className="space-y-2">
                  {strategy?.strengths.map((strength, index) => (
                    <li key={index} className="flex items-start gap-2 text-sm text-foreground/80">
                      <span className="text-green-400 mt-0.5">✓</span>
                      <span>{strength}</span>
                    </li>
                  ))}
                </ul>
              </CardContent>
            </Card>

            <Card className="border border-red-500/30 bg-red-500/5">
              <CardContent className="p-5">
                <h4 className="text-lg font-semibold text-red-400 mb-3 flex items-center gap-2">
                  <Shield className="w-5 h-5" />
                  Faiblesses & Limites
                </h4>
                <ul className="space-y-2">
                  {strategy?.weaknesses.map((weakness, index) => (
                    <li key={index} className="flex items-start gap-2 text-sm text-foreground/80">
                      <span className="text-red-400 mt-0.5">✗</span>
                      <span>{weakness}</span>
                    </li>
                  ))}
                </ul>
              </CardContent>
            </Card>
          </div>

          <div className="grid md:grid-cols-2 gap-4">
            <Card className="border border-violet-500/30 bg-violet-500/5">
              <CardContent className="p-5">
                <h4 className="text-sm font-semibold text-violet-400 mb-2 uppercase tracking-wider">Focus Sportif</h4>
                <p className="text-sm text-foreground/80">{strategy?.focus || "Non défini"}</p>
              </CardContent>
            </Card>

            <Card className="border border-blue-500/30 bg-blue-500/5">
              <CardContent className="p-5">
                <h4 className="text-sm font-semibold text-blue-400 mb-2 uppercase tracking-wider">Fréquence de Mise à Jour</h4>
                <p className="text-sm text-foreground/80">{strategy?.updateFrequency || "Non défini"}</p>
              </CardContent>
            </Card>
          </div>

          <Card className="border border-cyan-500/30 bg-gradient-to-r from-cyan-500/10 to-violet-500/10">
            <CardContent className="p-5">
              <h4 className="text-sm font-semibold text-cyan-400 mb-2 uppercase tracking-wider">💡 Recommandation</h4>
              <p className="text-sm text-foreground/80 leading-relaxed">
                {agent.riskProfile === 'Faible' && "Idéal pour les parieurs conservateurs cherchant une croissance stable."}
                {agent.riskProfile === 'Moyen' && "Parfait équilibre pour les parieurs intermédiaires."}
                {agent.riskProfile === 'Élevé' && "Recommandé pour les traders expérimentés avec capital suffisant."}
              </p>
            </CardContent>
          </Card>
        </div>
      </DialogContent>
    </Dialog>
  )
}
