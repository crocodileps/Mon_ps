'use client'

import { useState } from 'react'
import { 
  Search, 
  TrendingUp, 
  Target, 
  BarChart3,
  Brain,
  Shield,
  Lightbulb,
  AlertTriangle,
  ChevronDown,
  Crown
} from 'lucide-react'
import { 
  LineChart, 
  Line, 
  XAxis, 
  YAxis, 
  CartesianGrid, 
  Tooltip, 
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
  BarChart,
  Bar
} from 'recharts'

// Générateur de données P&L réalistes
function generatePnLData(initial: number, avgReturn: number, numBets: number) {
  const data = []
  let capital = initial
  for (let i = 1; i <= numBets; i++) {
    const randomReturn = (Math.random() - 0.4) * avgReturn * 2
    capital = capital * (1 + randomReturn)
    if (i % 5 === 0) {
      data.push({
        bet: i,
        capital: Math.round(capital * 100) / 100
      })
    }
  }
  return data
}

const COLORS = ['#f97316', '#a78bfa', '#22d3ee', '#94a3b8']

// Données des 4 agents
const AGENTS_DATA = {
  'anomaly-detector': {
    id: 'anomaly-detector',
    name: 'Anomaly Detector',
    icon: Search,
    color: '#ef4444',
    bgColor: 'bg-red-500/10',
    borderColor: 'border-red-500/30',
    textColor: 'text-red-400',
    understanding: {
      role: "Détecteur d'Anomalies de Cotes",
      mission: "Identifier les écarts de cotes significatifs entre bookmakers qui indiquent une possible erreur de cotation ou une information non encore intégrée par le marché.",
      howItWorks: "Utilise l'algorithme Isolation Forest pour analyser les distributions de cotes et détecter les outliers statistiques. Un spread > 10% entre bookmakers déclenche une alerte.",
      keyMetrics: ["Score d'anomalie (0-10)", "Spread maximum (%)", "Nombre de bookmakers analysés"],
      bestFor: "Marchés avec forte liquidité où les erreurs de cotation sont rapidement corrigées. Idéal pour le football européen majeur."
    },
    strategy: "L'agent Anomaly Detector utilise un modèle statistique d'Isolation Forest pour identifier les opportunités de value betting. En analysant les écarts de cotes entre 23 bookmakers, il détecte les anomalies qui représentent souvent des erreurs de cotation temporaires ou des informations non intégrées. L'agent se concentre sur les spreads > 10% qui offrent le meilleur ratio risque/récompense.",
    reflections: "Le modèle détecte efficacement les anomalies (score moyen 7.2/10), mais 15% des signaux sont des faux positifs liés à des marchés peu liquides. Une validation supplémentaire par volume de paris serait bénéfique. Les meilleures performances sont observées sur la Premier League et la Liga où la liquidité est maximale.",
    improvements: "Intégrer un filtre de liquidité pour éliminer les faux positifs sur marchés mineurs. Ajouter une analyse temporelle pour détecter la vitesse de correction des anomalies. Implémenter un système de scoring par bookmaker fiable vs non-fiable.",
    recentLoss: "La dernière perte significative (PSG vs Monaco, -150€) était due à une anomalie détectée sur un bookmaker offshore peu fiable. Le spread de 25% était artificiel et non représentatif du marché réel. Leçon : filtrer les bookmakers par réputation.",
    pnlData: generatePnLData(1000, 0.08, 200),
    dnaData: [
      { name: 'Football', value: 55, profit: 420 },
      { name: 'Basketball', value: 25, profit: 180 },
      { name: 'Tennis', value: 12, profit: -45 },
      { name: 'Autres', value: 8, profit: 25 }
    ]
  },
'spread-optimizer': {
    id: 'spread-optimizer',
    name: 'Spread Optimizer',
    icon: TrendingUp,
    color: '#10b981',
    bgColor: 'bg-green-500/10',
    borderColor: 'border-green-500/30',
    textColor: 'text-green-400',
    understanding: {
      role: "Optimiseur de Mise par Critère de Kelly",
      mission: "Calculer la mise optimale pour chaque opportunité en fonction de l'edge détecté et du risque associé, maximisant ainsi la croissance du capital à long terme.",
      howItWorks: "Applique la formule de Kelly : f* = (bp - q) / b, où b = cote-1, p = probabilité de gain, q = 1-p. Utilise une fraction de Kelly (25%) pour réduire la variance.",
      keyMetrics: ["Expected Value (EV)", "Kelly Fraction (%)", "Mise recommandée (% bankroll)", "ROI potentiel"],
      bestFor: "Toutes les opportunités validées par les autres agents. Particulièrement efficace quand combiné avec l'Anomaly Detector pour maximiser le profit sur les erreurs de cotation."
    },
    strategy: "Le Spread Optimizer est le cerveau financier du système. Il transforme les probabilités brutes en décisions de mise optimales via le critère de Kelly. En utilisant une fraction conservatrice (25%), il équilibre croissance et préservation du capital. L'agent calcule l'Expected Value pour chaque pari et recommande uniquement ceux avec EV > 3%.",
    reflections: "Le ROI moyen de 218% sur 200 paris valide l'efficacité du modèle Kelly. Cependant, les périodes de drawdown (max -12%) suggèrent qu'une gestion plus dynamique de la fraction Kelly serait bénéfique. Les paris à haute EV (>10%) ont un win rate de 67%, confirmant la robustesse du modèle.",
    improvements: "Implémenter un Kelly dynamique qui s'ajuste selon le drawdown actuel. Ajouter un système de corrélation entre paris pour éviter la surexposition. Intégrer la volatilité historique par type de pari pour affiner les mises.",
    recentLoss: "La perte sur Real Madrid vs Barcelona (-200€) malgré un EV de 8% illustre la variance normale. Le modèle avait correctement identifié l'edge, mais le résultat était dans les 35% de probabilité de perte. Aucun ajustement nécessaire.",
    pnlData: generatePnLData(1000, 0.12, 200),
    dnaData: [
      { name: 'Football', value: 45, profit: 890 },
      { name: 'Basketball', value: 30, profit: 650 },
      { name: 'Tennis', value: 15, profit: 280 },
      { name: 'Autres', value: 10, profit: 120 }
    ]
  },
  'pattern-matcher': {
    id: 'pattern-matcher',
    name: 'Pattern Matcher',
    icon: Target,
    color: '#3b82f6',
    bgColor: 'bg-blue-500/10',
    borderColor: 'border-blue-500/30',
    textColor: 'text-blue-400',
    understanding: {
      role: "Détecteur de Patterns Historiques",
      mission: "Identifier les récurrences statistiques et tendances par équipe, ligue ou type de match pour exploiter les biais du marché.",
      howItWorks: "Analyse les 100 derniers matchs similaires pour détecter des patterns récurrents. Calcule la fréquence de résultats similaires et compare avec les cotes proposées.",
      keyMetrics: ["Nombre de patterns trouvés", "Confiance du pattern (%)", "Historique de succès", "Force de la tendance"],
      bestFor: "Équipes avec historique stable, derbys régionaux, matchs à domicile/extérieur. Excellent pour les ligues avec peu de turnover d'effectif."
    },
    strategy: "Le Pattern Matcher exploite les inefficiences du marché liées aux biais cognitifs des bookmakers. En analysant les tendances historiques (équipe à domicile imbattue, série de victoires, head-to-head), il identifie les situations où le marché sous-estime ou surestime les probabilités. Focus sur les patterns avec >70% de récurrence.",
    reflections: "Les patterns sur les équipes à domicile sont les plus fiables (78% de précision). Les derbys montrent une volatilité plus élevée malgré des patterns apparents. La saisonnalité (début/fin de saison) impacte significativement la fiabilité des patterns détectés.",
    improvements: "Intégrer l'analyse de momentum (forme récente vs historique long terme). Ajouter des patterns conditionnels (si pluie + équipe X = pattern Y). Développer un système de pondération temporelle pour privilégier les patterns récents.",
    recentLoss: "Match Liverpool vs Everton : le pattern 'Liverpool gagne le derby' (85% historique) a échoué. La blessure de Salah (non intégrée) a cassé le pattern. Leçon : croiser avec données temps réel.",
    pnlData: generatePnLData(1000, 0.06, 200),
    dnaData: [
      { name: 'Football', value: 60, profit: 520 },
      { name: 'Basketball', value: 20, profit: 180 },
      { name: 'Tennis', value: 10, profit: 90 },
      { name: 'Autres', value: 10, profit: 45 }
    ]
  },
'backtest-engine': {
    id: 'backtest-engine',
    name: 'Backtest Engine',
    icon: BarChart3,
    color: '#8b5cf6',
    bgColor: 'bg-purple-500/10',
    borderColor: 'border-purple-500/30',
    textColor: 'text-purple-400',
    understanding: {
      role: "Moteur de Validation Historique",
      mission: "Valider chaque stratégie et signal sur données historiques avant exécution réelle, assurant la robustesse statistique des décisions.",
      howItWorks: "Simule 1000+ scénarios basés sur l'historique des cotes et résultats. Calcule le win rate, ROI, drawdown maximum et Sharpe Ratio pour chaque type de pari.",
      keyMetrics: ["Win Rate (%)", "ROI historique (%)", "Max Drawdown (%)", "Sharpe Ratio", "Nombre de simulations"],
      bestFor: "Validation de toute nouvelle stratégie avant mise en production. Essentiel pour éviter l'overfitting et confirmer l'edge statistique."
    },
    strategy: "Le Backtest Engine est le gardien de la qualité. Avant qu'un signal soit validé, il est testé contre l'historique. Seuls les paris avec un track record prouvé (>55% win rate sur 100+ simulations) passent le filtre. L'agent utilise le walk-forward analysis pour éviter l'overfitting et garantir la robustesse out-of-sample.",
    reflections: "Le backtesting a évité 23% de paris qui auraient été perdants (faux positifs des autres agents). Le win rate de 62% sur paris validés vs 48% sur paris non-validés confirme la valeur ajoutée. Attention : les conditions de marché évoluent, backtests > 2 ans perdent en pertinence.",
    improvements: "Implémenter le Monte Carlo simulation pour stress-testing. Ajouter l'analyse de régime de marché (bull/bear/volatile). Développer un système d'alerte quand les performances réelles divergent significativement des backtests.",
    recentLoss: "Le backtest sur 'Juventus gagne à domicile' montrait 72% win rate historique. La perte contre Empoli révèle un changement de régime (nouvel entraîneur). Ajustement : réduire le poids de l'historique > 6 mois lors de changements majeurs.",
    pnlData: generatePnLData(1000, 0.09, 200),
    dnaData: [
      { name: 'Football', value: 50, profit: 680 },
      { name: 'Basketball', value: 28, profit: 420 },
      { name: 'Tennis', value: 14, profit: 190 },
      { name: 'Autres', value: 8, profit: 85 }
    ]  
  },
  'agent-patron': {
    id: 'agent-patron',
    name: 'Agent Patron',
    icon: Crown,
    color: '#f59e0b',
    bgColor: 'bg-amber-500/10',
    borderColor: 'border-amber-500/30',
    textColor: 'text-amber-400',
    understanding: {
      role: "Meta-Analyste & Synthétiseur d'Intelligence Multi-Agent",
      mission: "Agréger, pondérer et synthétiser les analyses des 4 agents spécialisés pour produire une recommandation finale optimale basée sur le consensus et la gestion des conflits inter-agents.",
      howItWorks: "Applique une pondération dynamique basée sur la performance récente de chaque agent. Calcule un score composite : Score = Σ(W_i * Score_i) * Facteur_Consensus * Facteur_Risque. Détecte les niveaux de consensus (4/4 Fort, 3/4 Majoritaire, 2/2 Divisé) et arbitre les conflits.",
      keyMetrics: ["Score Global Composite (0-100)", "Niveau de Consensus", "Confiance Agrégée (%)", "Mise Finale Recommandée", "Points de Vigilance"],
      bestFor: "Toutes les opportunités. Indispensable pour la décision finale car il synthétise l'intelligence collective des 4 agents et élimine les biais individuels."
    },
    strategy: "L'Agent Patron est le cerveau stratégique ultime. Il ne génère pas ses propres signaux mais orchestre et synthétise ceux des 4 agents spécialisés. Sa force réside dans la pondération dynamique : chaque agent a un poids ajusté selon sa performance récente (rolling 50 paris), sa fiabilité historique et sa concordance avec les autres. En cas de consensus fort (4/4), la confiance est maximale. En cas de conflit, il applique des règles d'arbitrage scientifiques pour résoudre les désaccords.",
    reflections: "Le système de pondération a prouvé son efficacité : les décisions basées sur consensus 4/4 ont 78% de win rate vs 52% pour les décisions en conflit. Cependant, le modèle peut être trop conservateur en réduisant systématiquement les mises lors de désaccords, perdant ainsi certaines opportunités valides. La réévaluation des poids tous les 50 paris semble optimale pour capturer les changements de régime.",
    improvements: "Implémenter un système d'apprentissage automatique pour ajuster les poids en temps réel. Ajouter une analyse de corrélation temporelle entre les agents (certains performent mieux à certaines heures/jours). Développer un 'mode agressif' qui accepte les signaux 2/2 si l'EV est exceptionnellement haute (>15%). Intégrer le sentiment du marché comme 5ème input.",
    recentLoss: "La perte sur Barcelone vs Atletico (-180€) illustre la limite du consensus. Les 4 agents étaient d'accord (signal fort), mais tous ont sous-estimé l'impact du nouveau système tactique d'Atletico. Leçon : le consensus ne garantit pas la victoire si tous les agents partagent le même biais (données historiques obsolètes). Solution : ajouter un facteur de 'nouveauté tactique' qui réduit la confiance lors de changements récents.",
    pnlData: generatePnLData(1000, 0.15, 200),
    dnaData: [
      { name: 'Consensus 4/4', value: 35, profit: 1250 },
      { name: 'Majoritaire 3/4', value: 40, profit: 680 },
      { name: 'Divisé 2/2', value: 15, profit: -120 },
      { name: 'Conflictuel', value: 10, profit: -85 }
    ]
  }
}



export default function AgentsPage() {
  const [selectedAgent, setSelectedAgent] = useState('spread-optimizer')
  const agent = AGENTS_DATA[selectedAgent as keyof typeof AGENTS_DATA]
  const Icon = agent.icon
  
  const totalProfit = agent.pnlData[agent.pnlData.length - 1].capital - 1000
  const roi = ((totalProfit / 1000) * 100).toFixed(2)

  return (
    <div className="min-h-screen bg-black p-6 space-y-6">
      {/* Header */}
      <div className="flex justify-between items-center">
        <h1 className="text-3xl font-bold text-white">Stratégie des Agents</h1>
        <div className="bg-slate-800/50 px-4 py-2 rounded-lg border border-slate-700">
          <span className="text-gray-400">💰</span>
          <span className="text-green-400 font-bold ml-2">$1,280.50</span>
        </div>
      </div>

      {/* Sélecteur d'Agent */}
      <div className="bg-slate-900/60 backdrop-blur-md rounded-xl p-6 border border-slate-700/50">
        <h2 className="text-xl font-semibold text-white mb-4">Analyse Stratégique des Agents</h2>
        <div className="relative w-full max-w-md">
          <label className="text-gray-400 text-sm mb-2 block">Sélectionner un Agent à Analyser</label>
          <select
            value={selectedAgent}
            onChange={(e) => setSelectedAgent(e.target.value)}
            className={`w-full bg-slate-800 ${agent.textColor} border ${agent.borderColor} rounded-lg p-3 appearance-none cursor-pointer focus:outline-none`}
          >
            {Object.values(AGENTS_DATA).map((a) => (
              <option key={a.id} value={a.id} className="bg-slate-800">
                {a.name}
              </option>
            ))}
          </select>
          <ChevronDown className="absolute right-3 top-10 text-gray-400 pointer-events-none" size={20} />
        </div>
      </div>
{/* Compréhension de l'Agent */}
      <div className={`bg-slate-900/60 backdrop-blur-md rounded-xl p-6 border ${agent.borderColor}`}>
        <div className="flex items-center gap-3 mb-4">
          <Brain className={agent.textColor} size={24} />
          <h3 className={`text-xl font-semibold ${agent.textColor}`}>Compréhension de l'Agent</h3>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div>
            <h4 className="text-white font-medium mb-2">🎯 Rôle</h4>
            <p className="text-gray-300">{agent.understanding.role}</p>
          </div>
          <div>
            <h4 className="text-white font-medium mb-2">🚀 Mission</h4>
            <p className="text-gray-300">{agent.understanding.mission}</p>
          </div>
          <div>
            <h4 className="text-white font-medium mb-2">⚙️ Comment ça marche</h4>
            <p className="text-gray-300">{agent.understanding.howItWorks}</p>
          </div>
          <div>
            <h4 className="text-white font-medium mb-2">📊 Métriques Clés</h4>
            <ul className="text-gray-300 space-y-1">
              {agent.understanding.keyMetrics.map((metric, i) => (
                <li key={i} className="flex items-center gap-2">
                  <span className="w-2 h-2 rounded-full" style={{ backgroundColor: agent.color }}></span>
                  {metric}
                </li>
              ))}
            </ul>
          </div>
        </div>
        <div className="mt-4 p-4 bg-slate-800/50 rounded-lg">
          <h4 className="text-white font-medium mb-2">✨ Meilleur pour</h4>
          <p className="text-gray-300">{agent.understanding.bestFor}</p>
        </div>
      </div>

      {/* Stratégie Détaillée */}
      <div className="bg-slate-900/60 backdrop-blur-md rounded-xl p-6 border border-slate-700/50">
        <div className="flex items-center gap-3 mb-4">
          <Shield className="text-green-400" size={24} />
          <h3 className="text-xl font-semibold text-green-400">Stratégie Détaillée</h3>
        </div>
        <p className="text-gray-300 leading-relaxed">{agent.strategy}</p>
      </div>

      {/* Réflexions & Pistes d'Amélioration */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="bg-slate-900/60 backdrop-blur-md rounded-xl p-6 border border-slate-700/50">
          <h3 className="text-lg font-semibold text-white mb-3">Réflexions & Remise en Cause</h3>
          <p className="text-gray-300 leading-relaxed">{agent.reflections}</p>
        </div>
        <div className="bg-slate-900/60 backdrop-blur-md rounded-xl p-6 border border-slate-700/50">
          <div className="flex items-center gap-2 mb-3">
            <Lightbulb className="text-amber-400" size={20} />
            <h3 className="text-lg font-semibold text-amber-400">Pistes d'Amélioration</h3>
          </div>
          <p className="text-gray-300 leading-relaxed">{agent.improvements}</p>
        </div>
      </div>

      {/* Analyse de Perte Récente */}
      <div className="bg-gradient-to-r from-red-900/30 to-red-800/20 backdrop-blur-md rounded-xl p-6 border border-red-500/30">
        <div className="flex items-center gap-2 mb-3">
          <AlertTriangle className="text-red-400" size={20} />
          <h3 className="text-lg font-semibold text-red-400">Analyse de Perte Récente</h3>
        </div>
        <p className="text-gray-300 leading-relaxed">{agent.recentLoss}</p>
      </div>
{/* Graphique P&L */}
      <div className="bg-slate-900/60 backdrop-blur-md rounded-xl p-6 border border-slate-700/50">
        <div className="flex justify-between items-center mb-4">
          <div>
            <h3 className="text-xl font-semibold text-white">Agent CV (P&L)</h3>
            <p className="text-gray-400 text-sm">
              Évolution du capital sur les derniers paris • ROI Moyen: 
              <span className="text-green-400 font-bold ml-1">+{roi}%</span>
            </p>
          </div>
          <select className="bg-slate-800 text-gray-300 border border-slate-600 rounded-lg px-3 py-2">
            <option>200 derniers paris</option>
            <option>100 derniers paris</option>
            <option>50 derniers paris</option>
          </select>
        </div>
        <div className="h-80">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={agent.pnlData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
              <XAxis dataKey="bet" stroke="#94a3b8" />
              <YAxis stroke="#94a3b8" />
              <Tooltip contentStyle={{ backgroundColor: '#1e293b', border: '1px solid #475569', borderRadius: '8px' }} />
              <Line type="monotone" dataKey="capital" stroke={agent.color} strokeWidth={2} dot={false} name="Capital" />
            </LineChart>
          </ResponsiveContainer>
        </div>
        <div className="grid grid-cols-4 gap-4 mt-6">
          <div className="bg-slate-800/50 p-4 rounded-lg">
            <p className="text-gray-400 text-sm">Capital Initial</p>
            <p className="text-white text-xl font-bold">$1000</p>
          </div>
          <div className="bg-slate-800/50 p-4 rounded-lg">
            <p className="text-gray-400 text-sm">Capital Actuel</p>
            <p className="text-blue-400 text-xl font-bold">${agent.pnlData[agent.pnlData.length - 1].capital.toFixed(2)}</p>
          </div>
          <div className="bg-slate-800/50 p-4 rounded-lg">
            <p className="text-gray-400 text-sm">Profit Total</p>
            <p className="text-green-400 text-xl font-bold">${totalProfit.toFixed(2)}</p>
          </div>
          <div className="bg-slate-800/50 p-4 rounded-lg">
            <p className="text-gray-400 text-sm">Nb de Paris</p>
            <p className="text-white text-xl font-bold">200</p>
          </div>
        </div>
      </div>

      {/* Agent DNA */}
      <div className="bg-slate-900/60 backdrop-blur-md rounded-xl p-6 border border-slate-700/50">
        <h3 className="text-xl font-semibold text-white mb-2">Agent DNA</h3>
        <p className="text-gray-400 text-sm mb-6">Répartition du volume de paris et performance par sport/ligue</p>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
          <div>
            <h4 className="text-white font-medium mb-4 text-center">Distribution du Volume de Paris</h4>
            <div className="h-64">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie data={agent.dnaData} cx="50%" cy="50%" innerRadius={60} outerRadius={100} paddingAngle={2} dataKey="value" label={({ value }) => `${value}%`}>
                    {agent.dnaData.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                    ))}
                  </Pie>
                  <Tooltip contentStyle={{ backgroundColor: '#1e293b', border: '1px solid #475569', borderRadius: '8px' }} />
                </PieChart>
              </ResponsiveContainer>
            </div>
            <div className="flex flex-wrap justify-center gap-4 mt-4">
              {agent.dnaData.map((item, index) => (
                <div key={item.name} className="flex items-center gap-2">
                  <div className="w-3 h-3 rounded-full" style={{ backgroundColor: COLORS[index] }}></div>
                  <span className="text-gray-300 text-sm">{item.name} ({item.value}%)</span>
                </div>
              ))}
            </div>
          </div>
          <div>
            <h4 className="text-white font-medium mb-4 text-center">Profit & Loss par Sport</h4>
            <div className="h-64">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={agent.dnaData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                  <XAxis dataKey="name" stroke="#94a3b8" />
                  <YAxis stroke="#94a3b8" />
                  <Tooltip contentStyle={{ backgroundColor: '#1e293b', border: '1px solid #475569', borderRadius: '8px' }} />
                  <Bar dataKey="profit" fill="#1e293b" name="P&L ($)" />
                </BarChart>
              </ResponsiveContainer>
            </div>
            <div className="grid grid-cols-2 gap-2 mt-4 text-sm">
              {agent.dnaData.map((item) => (
                <div key={item.name} className="flex justify-between">
                  <span className="text-gray-400">{item.name}</span>
                  <span className={item.profit >= 0 ? 'text-green-400' : 'text-red-400'}>
                    {item.profit >= 0 ? '+' : ''}${item.profit}
                  </span>
                </div>
              ))}
            </div>
          </div>
        </div>
        <div className="mt-6 p-4 bg-amber-900/20 rounded-lg border border-amber-500/30">
          <p className="text-amber-300">
            <span className="font-semibold">Analyse:</span> L'agent {agent.name} concentre {agent.dnaData[0].value}% de ses paris sur {agent.dnaData[0].name}. 
            {agent.dnaData.find(d => d.profit < 0) && (
              <> Attention aux pertes sur {agent.dnaData.find(d => d.profit < 0)?.name} qui représentent une fuite potentielle.</>
            )}
          </p>
        </div>
      </div>
    </div>
  )
}

