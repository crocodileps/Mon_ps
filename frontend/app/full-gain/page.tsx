'use client';

import { useState, useEffect, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Diamond,
  TrendingUp,
  Target,
  Zap,
  RefreshCw,
  ChevronDown,
  ChevronUp,
  Eye,
  BarChart3,
  Percent,
  Goal,
  Flame,
  Star,
  X,
  Activity,
  Layers,
  Search,
  Brain,
  Sparkles,
  AlertCircle,
  MessageSquare
} from 'lucide-react';


// 📊 Market display names - Noms clairs pour tous les marchés
const MARKET_LABELS: Record<string, string> = {
  'BTTS': 'BTTS Oui',
  'BTTS No': 'BTTS Non',
  'O1.5': 'Over 1.5',
  'U1.5': 'Under 1.5',
  'O2.5': 'Over 2.5',
  'U2.5': 'Under 2.5',
  'O3.5': 'Over 3.5',
  'U3.5': 'Under 3.5',
  'DC 1X': 'Dom/Nul',
  'DC X2': 'Nul/Ext',
  'DC 12': 'Dom/Ext',
  'DNB H': 'Dom (0 si nul)',
  'DNB A': 'Ext (0 si nul)',
};

// 🏆 ANALYSE SMART 2.0 - Analyse complète des 13 marchés avec détection de combinés
const generateSmartAnalysis = (analysis: MatchAnalysis): {
  context: string;
  top3: Array<{name: string; score: number; reasoning: string}>;
  combos: Array<{name: string; markets: string[]; confidence: number; reasoning: string}>;
  alerts: string[];
  bestBet: string;
  worstBet: string;
} => {
  const totalXG = analysis.poisson.total_xg;
  const homeXG = analysis.poisson.home_xg;
  const awayXG = analysis.poisson.away_xg;
  const xgDiff = Math.abs(homeXG - awayXG);
  
  // Scores des marchés
  const btts = analysis.btts?.score || 0;
  const bttsNo = analysis.btts_no?.score || 0;
  const o15 = analysis.over15?.score || 0;
  const u15 = analysis.under15?.score || 0;
  const o25 = analysis.over25?.score || 0;
  const u25 = analysis.under25?.score || 0;
  const o35 = analysis.over35?.score || 0;
  const u35 = analysis.under35?.score || 0;
  const dc1x = analysis.double_chance?.['1x']?.score || 0;
  const dcx2 = analysis.double_chance?.['x2']?.score || 0;
  const dc12 = analysis.double_chance?.['12']?.score || 0;
  const dnbH = analysis.draw_no_bet?.home?.score || 0;
  const dnbA = analysis.draw_no_bet?.away?.score || 0;
  
  const home1x2 = analysis.poisson['1x2']?.home || 0;
  const draw1x2 = analysis.poisson['1x2']?.draw || 0;
  const away1x2 = analysis.poisson['1x2']?.away || 0;
  
  // 📊 CONTEXTE DU MATCH
  let context = '';
  if (totalXG >= 3.5) {
    context = `🔥 Match EXPLOSIF (${totalXG.toFixed(2)} xG) - Fort potentiel offensif.`;
  } else if (totalXG >= 2.8) {
    context = `⚽ Match OFFENSIF (${totalXG.toFixed(2)} xG) - Buts attendus.`;
  } else if (totalXG >= 2.2) {
    context = `📊 Match ÉQUILIBRÉ (${totalXG.toFixed(2)} xG) - Issue incertaine.`;
  } else if (totalXG >= 1.5) {
    context = `🛡️ Match FERMÉ (${totalXG.toFixed(2)} xG) - Défenses solides.`;
  } else {
    context = `🔒 Match TRÈS DÉFENSIF (${totalXG.toFixed(2)} xG) - Peu de buts.`;
  }
  
  // Domination
  if (xgDiff >= 1.5) {
    const dom = homeXG > awayXG ? analysis.home_team : analysis.away_team;
    context += ` ${dom} DOMINE nettement.`;
  } else if (xgDiff >= 0.8) {
    const dom = homeXG > awayXG ? analysis.home_team : analysis.away_team;
    context += ` Léger avantage ${dom}.`;
  } else {
    context += ` Match très serré.`;
  }

  // 🏆 TOP 3 MARCHÉS avec reasoning
  const allMarkets = [
    { name: 'BTTS Oui', score: btts, reasoning: btts >= 65 ? 'Deux équipes offensives' : btts >= 50 ? 'Possible mais risqué' : 'Défenses solides' },
    { name: 'BTTS Non', score: bttsNo, reasoning: bttsNo >= 65 ? 'Une équipe ne marquera pas' : 'Incertain' },
    { name: 'Over 1.5', score: o15, reasoning: o15 >= 70 ? 'Quasi-certain, au moins 2 buts' : 'Probable' },
    { name: 'Under 1.5', score: u15, reasoning: u15 >= 50 ? 'Match très fermé possible' : 'Peu probable' },
    { name: 'Over 2.5', score: o25, reasoning: o25 >= 65 ? 'Match ouvert, 3+ buts attendus' : o25 >= 50 ? 'Possible' : 'Défensif' },
    { name: 'Under 2.5', score: u25, reasoning: u25 >= 60 ? 'Match fermé prévu' : 'Risqué' },
    { name: 'Over 3.5', score: o35, reasoning: o35 >= 50 ? 'Festival de buts possible' : 'Ambitieux' },
    { name: 'Under 3.5', score: u35, reasoning: u35 >= 70 ? 'Très sûr, max 3 buts' : 'Probable' },
    { name: 'Dom/Nul (1X)', score: dc1x, reasoning: dc1x >= 70 ? `${analysis.home_team} favori ou nul` : 'Risqué' },
    { name: 'Nul/Ext (X2)', score: dcx2, reasoning: dcx2 >= 70 ? `${analysis.away_team} peut surprendre` : 'Outsider' },
    { name: 'Dom/Ext (12)', score: dc12, reasoning: dc12 >= 70 ? 'Pas de nul attendu' : 'Nul possible' },
    { name: 'DNB Dom', score: dnbH, reasoning: dnbH >= 65 ? `${analysis.home_team} gagne ou remboursé` : 'Incertain' },
    { name: 'DNB Ext', score: dnbA, reasoning: dnbA >= 50 ? `${analysis.away_team} peut gagner` : 'Difficile' },
  ].filter(m => m.score > 0).sort((a, b) => b.score - a.score);
  
  const top3 = allMarkets.slice(0, 3);

  // 🎯 DÉTECTION DE COMBINÉS COHÉRENTS
  const combos: Array<{name: string; markets: string[]; confidence: number; reasoning: string}> = [];
  
  // Combo 1: BTTS + Over 2.5 (classique)
  if (btts >= 60 && o25 >= 60) {
    const conf = Math.min(btts, o25);
    combos.push({
      name: '🔥 BTTS + Over 2.5',
      markets: ['BTTS Oui', 'Over 2.5'],
      confidence: conf,
      reasoning: `Combo classique - Les deux équipes marquent dans un match ouvert (${conf.toFixed(0)}%)`
    });
  }
  
  // Combo 2: BTTS + Over 1.5 (sécurisé)
  if (btts >= 55 && o15 >= 75) {
    const conf = Math.min(btts, o15) - 5;
    combos.push({
      name: '✅ BTTS + Over 1.5',
      markets: ['BTTS Oui', 'Over 1.5'],
      confidence: conf,
      reasoning: `Combo sécurisé - Au moins 2 buts avec les deux qui marquent (${conf.toFixed(0)}%)`
    });
  }
  
  // Combo 3: DC 1X + Under 2.5 (défensif domicile)
  if (dc1x >= 65 && u25 >= 55 && totalXG < 2.5) {
    const conf = Math.min(dc1x, u25) - 5;
    combos.push({
      name: '🛡️ Dom/Nul + Under 2.5',
      markets: ['Dom/Nul (1X)', 'Under 2.5'],
      confidence: conf,
      reasoning: `${analysis.home_team} tient le résultat dans un match fermé (${conf.toFixed(0)}%)`
    });
  }
  
  // Combo 4: DC 12 + Over 1.5 (match décisif)
  if (dc12 >= 70 && o15 >= 80) {
    const conf = Math.min(dc12, o15) - 10;
    combos.push({
      name: '⚡ Pas de Nul + Over 1.5',
      markets: ['Dom/Ext (12)', 'Over 1.5'],
      confidence: conf,
      reasoning: `Un vainqueur clair avec au moins 2 buts (${conf.toFixed(0)}%)`
    });
  }
  
  // Combo 5: DNB + BTTS (favori offensif)
  if (dnbH >= 60 && btts >= 55 && homeXG > awayXG + 0.5) {
    const conf = Math.min(dnbH, btts) - 5;
    combos.push({
      name: '💎 DNB Dom + BTTS',
      markets: ['DNB Dom', 'BTTS Oui'],
      confidence: conf,
      reasoning: `${analysis.home_team} gagne dans un match ouvert (${conf.toFixed(0)}%)`
    });
  }
  
  // Combo 6: Under 3.5 + Over 1.5 (range sécurisé)
  if (u35 >= 70 && o15 >= 75) {
    const conf = Math.min(u35, o15) - 5;
    combos.push({
      name: '🎯 2-3 Buts (Range)',
      markets: ['Over 1.5', 'Under 3.5'],
      confidence: conf,
      reasoning: `Match avec 2-3 buts attendus - Range optimal (${conf.toFixed(0)}%)`
    });
  }

  // Trier les combos par confiance
  combos.sort((a, b) => b.confidence - a.confidence);

  // ⚠️ ALERTES - Contradictions détectées
  const alerts: string[] = [];
  
  if (btts >= 65 && u15 >= 40) {
    alerts.push(`⚠️ Contradiction: BTTS élevé (${btts.toFixed(0)}%) mais Under 1.5 notable (${u15.toFixed(0)}%)`);
  }
  if (o25 >= 60 && bttsNo >= 55) {
    alerts.push(`⚠️ Attention: Over 2.5 probable mais BTTS Non aussi (une équipe domine)`);
  }
  if (dc1x >= 70 && dcx2 >= 50) {
    alerts.push(`⚠️ Match incertain malgré les scores DC élevés`);
  }
  if (totalXG >= 3.0 && u25 >= 50) {
    alerts.push(`⚠️ xG élevé (${totalXG.toFixed(2)}) mais Under 2.5 notable - Vérifier les stats défensives`);
  }

  // 🏆 BEST & WORST
  const bestBet = top3[0] ? `🏆 ${top3[0].name} (${top3[0].score.toFixed(0)}%) - ${top3[0].reasoning}` : 'Aucun pari clair';
  const worstMarket = allMarkets[allMarkets.length - 1];
  const worstBet = worstMarket ? `❌ Éviter: ${worstMarket.name} (${worstMarket.score.toFixed(0)}%)` : '';

  return { context, top3, combos, alerts, bestBet, worstBet };
};


const getMarketLabel = (key: string): string => MARKET_LABELS[key] || key;

// Types
interface PoissonData {
  home_xg: number;
  away_xg: number;
  total_xg: number;
  btts_prob: number;
  btts_no_prob?: number;
  over25_prob: number;
  over15_prob: number;
  over35_prob: number;
  under15_prob?: number;
  under25_prob?: number;
  under35_prob?: number;
  '1x2': { home: number; draw: number; away: number };
  double_chance?: { '1x': number; 'x2': number; '12': number };
  draw_no_bet?: { home: number; away: number };
  most_likely_scores: [string, number][];
}

interface MarketAnalysis {
  score: number;
  probability: number;
  recommendation: string;
  confidence: number;
  value_rating: string;
  kelly_pct: number;
  factors: Record<string, number>;
  reasoning: string;
}

interface MatchAnalysis {
  match_id: string;
  home_team: string;
  away_team: string;
  poisson: PoissonData;
  btts: MarketAnalysis;
  btts_no?: MarketAnalysis;
  over25: MarketAnalysis;
  under25?: MarketAnalysis;
  over15?: MarketAnalysis;
  under15?: MarketAnalysis;
  over35?: MarketAnalysis;
  under35?: MarketAnalysis;
  double_chance?: {
    '1x': MarketAnalysis;
    'x2': MarketAnalysis;
    '12': MarketAnalysis;
  };
  draw_no_bet?: {
    home: MarketAnalysis;
    away: MarketAnalysis;
  };
  best_market?: { type: string; score: number; recommendation: string };
  worst_market?: { type: string; score: number; recommendation: string };
  patron: { score: number; match_interest: string; data_quality: { home_stats: boolean; away_stats: boolean; h2h: boolean } };
  generated_at: string;
  league?: string;
  interpretation?: MatchInterpretation;
}

interface MatchInterpretation {
  summary: string;
  btts_verdict: string;
  over_verdict: string;
  best_bet: string;
  confidence_level: 'HIGH' | 'MEDIUM' | 'LOW';
  detailed_analysis: string;
}

interface Opportunity {
  match_id: string;
  home_team: string;
  away_team: string;
  sport: string;
}

// 🧠 LLM Analysis Generator - Génère une analyse textuelle détaillée
const generateDetailedAnalysis = (analysis: MatchAnalysis): string => {
  const bttsScore = analysis.btts.score;
  const overScore = analysis.over25.score;
  const totalXG = analysis.poisson.total_xg;
  const homeXG = analysis.poisson.home_xg;
  const awayXG = analysis.poisson.away_xg;
  const bttsProb = analysis.poisson.btts_prob;
  const overProb = analysis.poisson.over25_prob;
  const home1x2 = analysis.poisson['1x2'].home;
  const away1x2 = analysis.poisson['1x2'].away;
  
  const parts: string[] = [];
  
  // Context du match
  if (totalXG >= 3.5) {
    parts.push(`🔥 Match à très haut potentiel offensif avec ${totalXG.toFixed(2)} buts attendus (xG).`);
  } else if (totalXG >= 2.8) {
    parts.push(`⚽ Match offensif prévu avec ${totalXG.toFixed(2)} buts attendus.`);
  } else if (totalXG >= 2.2) {
    parts.push(`📊 Match équilibré avec ${totalXG.toFixed(2)} buts attendus.`);
  } else {
    parts.push(`🛡️ Match plutôt défensif avec seulement ${totalXG.toFixed(2)} buts attendus.`);
  }
  
  // Domination
  const xgDiff = Math.abs(homeXG - awayXG);
  if (xgDiff >= 1.5) {
    const dominant = homeXG > awayXG ? analysis.home_team : analysis.away_team;
    const weak = homeXG > awayXG ? analysis.away_team : analysis.home_team;
    parts.push(`${dominant} domine nettement avec ${Math.max(homeXG, awayXG).toFixed(2)} xG contre ${Math.min(homeXG, awayXG).toFixed(2)} pour ${weak}.`);
  } else if (xgDiff >= 0.8) {
    const slight = homeXG > awayXG ? analysis.home_team : analysis.away_team;
    parts.push(`${slight} a un avantage offensif notable.`);
  }
  
  // BTTS Analysis
  if (bttsScore >= 70) {
    parts.push(`✅ BTTS très probable (${bttsScore.toFixed(0)}%, Poisson: ${bttsProb}%) - Les deux équipes devraient marquer.`);
  } else if (bttsScore >= 60) {
    parts.push(`📈 BTTS probable (${bttsScore.toFixed(0)}%) - Bonne opportunité pour parier BTTS OUI.`);
  } else if (bttsScore >= 50) {
    parts.push(`⚠️ BTTS incertain (${bttsScore.toFixed(0)}%) - Match difficile à prédire.`);
  } else if (bttsScore < 40) {
    if (homeXG > awayXG + 1) {
      parts.push(`❌ BTTS peu probable (${bttsScore.toFixed(0)}%) - ${analysis.away_team} risque de ne pas marquer.`);
    } else if (awayXG > homeXG + 1) {
      parts.push(`❌ BTTS peu probable (${bttsScore.toFixed(0)}%) - ${analysis.home_team} risque de ne pas marquer.`);
    } else {
      parts.push(`❌ BTTS peu probable (${bttsScore.toFixed(0)}%) - Match serré, peu de buts attendus.`);
    }
  }
  
  // Over 2.5 Analysis
  if (overScore >= 70) {
    parts.push(`✅ Over 2.5 très probable (${overScore.toFixed(0)}%, Poisson: ${overProb}%) - Match à buts.`);
  } else if (overScore >= 60) {
    parts.push(`📈 Over 2.5 probable (${overScore.toFixed(0)}%) - Le xG de ${totalXG.toFixed(2)} suggère des buts.`);
  } else if (overScore >= 50) {
    parts.push(`⚠️ Over 2.5 incertain (${overScore.toFixed(0)}%) - Peut aller dans les deux sens.`);
  } else if (overScore < 40) {
    parts.push(`❌ Under 2.5 plus probable (Over: ${overScore.toFixed(0)}%) - Match fermé prévu.`);
  }
  
  // Final Recommendation
  const maxScore = Math.max(bttsScore, overScore);
  
  parts.push('');  // Line break
  parts.push('💎 RECOMMANDATION:');
  
  if (maxScore >= 70) {
    if (bttsScore >= 70 && overScore >= 70) {
      parts.push(`🔥 DOUBLE DIAMOND - Combo BTTS + Over 2.5 recommandé ! Confiance ÉLEVÉE.`);
    } else if (overScore > bttsScore) {
      parts.push(`💎 OVER 2.5 est le meilleur pari. Confiance ÉLEVÉE.`);
    } else {
      parts.push(`💎 BTTS OUI est le meilleur pari. Confiance ÉLEVÉE.`);
    }
  } else if (maxScore >= 60) {
    if (overScore > bttsScore) {
      parts.push(`✅ OVER 2.5 recommandé. Confiance MOYENNE.`);
    } else {
      parts.push(`✅ BTTS OUI recommandé. Confiance MOYENNE.`);
    }
  } else if (maxScore >= 50) {
    parts.push(`⚠️ Match risqué - Pas de recommandation claire.`);
    if (overScore < 45 && bttsScore < 45) {
      parts.push(`Alternative: Under 2.5 ou BTTS NON peut être envisagé.`);
    }
  } else {
    parts.push(`❌ ÉVITER ce match pour BTTS/Over.`);
    if (bttsScore < 35) parts.push(`Alternative: BTTS NON intéressant.`);
    if (overScore < 35) parts.push(`Alternative: Under 2.5 favorable.`);
  }
  
  return parts.join(' ');
};

// Generate Interpretation
const generateInterpretation = (analysis: MatchAnalysis): MatchInterpretation => {
  const bttsScore = analysis.btts.score;
  const overScore = analysis.over25.score;
  const totalXG = analysis.poisson.total_xg;
  
  let bestBet = '';
  let confidenceLevel: 'HIGH' | 'MEDIUM' | 'LOW' = 'LOW';
  const maxScore = Math.max(bttsScore, overScore);
  
  if (maxScore >= 70) {
    confidenceLevel = 'HIGH';
    bestBet = bttsScore > overScore ? 'BTTS OUI' : 'OVER 2.5';
    if (bttsScore >= 70 && overScore >= 70) bestBet = 'BTTS + OVER 2.5';
  } else if (maxScore >= 55) {
    confidenceLevel = 'MEDIUM';
    if (bttsScore >= 55 && overScore >= 55) bestBet = 'BTTS + OVER 2.5';
    else if (bttsScore >= 55) bestBet = 'BTTS OUI';
    else bestBet = 'OVER 2.5';
  } else {
    confidenceLevel = 'LOW';
    bestBet = bttsScore < 40 && overScore < 40 ? 'UNDER 2.5' : 'ÉVITER';
  }
  
  let bttsVerdict = bttsScore >= 70 ? `💎 DIAMOND (${bttsScore.toFixed(0)}%)` :
                    bttsScore >= 60 ? `✅ STRONG (${bttsScore.toFixed(0)}%)` :
                    bttsScore >= 50 ? `📈 POSSIBLE (${bttsScore.toFixed(0)}%)` :
                    `⏭️ SKIP (${bttsScore.toFixed(0)}%)`;
  
  let overVerdict = overScore >= 70 ? `💎 DIAMOND (${overScore.toFixed(0)}%)` :
                    overScore >= 60 ? `✅ STRONG (${overScore.toFixed(0)}%)` :
                    overScore >= 50 ? `📈 POSSIBLE (${overScore.toFixed(0)}%)` :
                    `⏭️ SKIP (${overScore.toFixed(0)}%)`;
  
  let summary = totalXG >= 3.5 ? `Match offensif (xG: ${totalXG.toFixed(2)})` :
                totalXG >= 2.8 ? `Match équilibré (xG: ${totalXG.toFixed(2)})` :
                totalXG >= 2.2 ? `Match modéré (xG: ${totalXG.toFixed(2)})` :
                `Match défensif (xG: ${totalXG.toFixed(2)})`;
  
  // Generate detailed LLM analysis
  const detailed_analysis = generateDetailedAnalysis(analysis);
  
  return { summary, btts_verdict: bttsVerdict, over_verdict: overVerdict, best_bet: bestBet, confidence_level: confidenceLevel, detailed_analysis };
};

// Animated Counter
const AnimatedCounter = ({ value, suffix = '' }: { value: number; suffix?: string }) => {
  const [displayValue, setDisplayValue] = useState(0);
  useEffect(() => {
    const timer = setInterval(() => {
      setDisplayValue(prev => prev >= value ? value : prev + value / 30);
    }, 33);
    return () => clearInterval(timer);
  }, [value]);
  return <span>{displayValue.toFixed(1)}{suffix}</span>;
};

// Score Badge
const ScoreBadge = ({ score, size = 'md' }: { score: number; size?: 'sm' | 'md' }) => {
  const getColor = () => {
    if (score >= 70) return 'from-emerald-500 to-cyan-400';
    if (score >= 60) return 'from-cyan-500 to-blue-400';
    if (score >= 50) return 'from-yellow-500 to-orange-400';
    return 'from-red-500 to-pink-400';
  };
  const sizes = { sm: 'w-10 h-10 text-xs', md: 'w-14 h-14 text-sm' };
  return (
    <div className={`${sizes[size]} rounded-full bg-gradient-to-br ${getColor()} flex items-center justify-center font-bold text-white shadow-lg`}>
      {score.toFixed(0)}
    </div>
  );
};

// Confidence Badge
const ConfidenceBadge = ({ level }: { level: 'HIGH' | 'MEDIUM' | 'LOW' }) => {
  const styles = {
    HIGH: 'bg-emerald-500/20 text-emerald-400',
    MEDIUM: 'bg-yellow-500/20 text-yellow-400',
    LOW: 'bg-slate-700 text-slate-400'
  };
  return <span className={`px-2 py-1 rounded-full text-xs font-medium ${styles[level]}`}>{level}</span>;
};

// Recommendation Badge
const RecommendationBadge = ({ recommendation }: { recommendation: string }) => {
  const getStyle = () => {
    if (recommendation.includes('DIAMOND')) return 'bg-gradient-to-r from-purple-600 to-pink-500 text-white';
    if (recommendation.includes('STRONG')) return 'bg-gradient-to-r from-emerald-600 to-cyan-500 text-white';
    if (recommendation.includes('LEAN')) return 'bg-gradient-to-r from-yellow-600 to-orange-500 text-white';
    return 'bg-slate-700 text-slate-300';
  };
  return <span className={`px-2 py-1 rounded-full text-xs font-medium ${getStyle()}`}>{recommendation.replace(/[^\w\s]/g, '').trim()}</span>;
};

// Factor Bar
const FactorBar = ({ label, value, icon: Icon }: { label: string; value: number; icon: any }) => {
  const getColor = () => value >= 70 ? 'from-emerald-500 to-cyan-400' : value >= 50 ? 'from-yellow-500 to-orange-400' : 'from-red-500 to-pink-400';
  return (
    <div className="space-y-1">
      <div className="flex justify-between text-xs">
        <span className="flex items-center gap-1 text-slate-400"><Icon className="w-3 h-3" />{label}</span>
        <span className="font-bold text-white">{value.toFixed(0)}%</span>
      </div>
      <div className="h-2 bg-slate-800 rounded-full overflow-hidden">
        <motion.div initial={{ width: 0 }} animate={{ width: `${value}%` }} className={`h-full rounded-full bg-gradient-to-r ${getColor()}`} />
      </div>
    </div>
  );
};

// xG Visual
const XGVisual = ({ homeXG, awayXG, homeTeam, awayTeam }: { homeXG: number; awayXG: number; homeTeam: string; awayTeam: string }) => {
  const total = homeXG + awayXG;
  const homePercent = total > 0 ? (homeXG / total) * 100 : 50;
  return (
    <div className="space-y-2">
      <div className="flex justify-between text-xs text-slate-400"><span>{homeTeam}</span><span>{awayTeam}</span></div>
      <div className="h-8 bg-slate-800 rounded-lg overflow-hidden flex">
        <div style={{ width: `${homePercent}%` }} className="bg-gradient-to-r from-cyan-600 to-cyan-400 flex items-center justify-center">
          <span className="text-xs font-bold text-white">{homeXG.toFixed(2)}</span>
        </div>
        <div style={{ width: `${100 - homePercent}%` }} className="bg-gradient-to-r from-pink-400 to-pink-600 flex items-center justify-center">
          <span className="text-xs font-bold text-white">{awayXG.toFixed(2)}</span>
        </div>
      </div>
      <div className="text-center text-sm font-bold text-white">Total xG: <span className="text-cyan-400">{total.toFixed(2)}</span></div>
    </div>
  );
};

// 🧠 LLM Analysis Card - Nouvelle carte d'analyse textuelle
const LLMAnalysisCard = ({ analysis }: { analysis: string }) => {
  return (
    <div className="bg-gradient-to-br from-indigo-900/40 to-purple-900/40 rounded-xl p-4 border border-indigo-500/30">
      <div className="flex items-center gap-2 mb-3">
        <MessageSquare className="w-5 h-5 text-indigo-400" />
        <h3 className="text-sm font-semibold text-indigo-400">Analyse Détaillée</h3>
      </div>
      <div className="text-sm text-slate-300 leading-relaxed whitespace-pre-line">
        {analysis}
      </div>
    </div>
  );
};

// Detail Drawer
const DetailDrawer = ({ analysis, isOpen, onClose }: { analysis: MatchAnalysis | null; isOpen: boolean; onClose: () => void }) => {
  if (!analysis) return null;
  return (
    <AnimatePresence>
      {isOpen && (
        <>
          <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} onClick={onClose} className="fixed inset-0 bg-black/60 backdrop-blur-sm z-40" />
          <motion.div initial={{ x: '100%' }} animate={{ x: 0 }} exit={{ x: '100%' }} transition={{ type: 'spring', damping: 25 }} className="fixed right-0 top-0 h-full w-full max-w-xl bg-slate-900/95 backdrop-blur-xl border-l border-cyan-500/20 z-50 overflow-y-auto">
            <div className="sticky top-0 bg-slate-900/90 backdrop-blur-xl border-b border-slate-700/50 p-4 z-10">
              <div className="flex items-center justify-between">
                <div>
                  <h2 className="text-xl font-bold text-white">{analysis.home_team} vs {analysis.away_team}</h2>
                  <p className="text-sm text-slate-400">{analysis.league || 'Football'}</p>
                </div>
                <button onClick={onClose} className="p-2 rounded-lg bg-slate-800 hover:bg-slate-700"><X className="w-5 h-5 text-slate-400" /></button>
              </div>
            </div>
            <div className="p-4 space-y-6">
              {/* LLM Analysis - NEW */}
              {analysis.interpretation?.detailed_analysis && (
                <LLMAnalysisCard analysis={analysis.interpretation.detailed_analysis} />
              )}
              
              {/* Interpretation Quick */}
              {analysis.interpretation && (
                <div className="bg-gradient-to-br from-slate-800/80 to-slate-900/80 rounded-xl p-4 border border-cyan-500/30">
                  <div className="flex items-center gap-2 mb-3">
                    <Brain className="w-5 h-5 text-cyan-400" />
                    <span className="text-sm font-semibold text-cyan-400">Résumé</span>
                    <ConfidenceBadge level={analysis.interpretation.confidence_level} />
                  </div>
                  <p className="text-sm text-slate-300 mb-2">{analysis.interpretation.summary}</p>
                  <div className="space-y-1 text-sm text-slate-400 mb-3">
                    <div className="flex items-center gap-2"><Goal className="w-4 h-4 text-emerald-400" />{analysis.interpretation.btts_verdict}</div>
                    <div className="flex items-center gap-2"><TrendingUp className="w-4 h-4 text-blue-400" />{analysis.interpretation.over_verdict}</div>
                  </div>
                  <div className="flex items-center gap-2 bg-slate-900/50 rounded-lg p-3">
                    <Sparkles className="w-5 h-5 text-yellow-400" />
                    <span className="text-sm text-slate-400">Meilleur pari:</span>
                    <span className="font-bold text-lg text-yellow-400">{analysis.interpretation.best_bet}</span>
                  </div>
                </div>
              )}
              
              {/* xG */}
              <div className="bg-slate-800/50 rounded-xl p-4 border border-slate-700/50">
                <h3 className="text-sm font-semibold text-slate-400 mb-3 flex items-center gap-2"><Target className="w-4 h-4" />Expected Goals</h3>
                <XGVisual homeXG={analysis.poisson.home_xg} awayXG={analysis.poisson.away_xg} homeTeam={analysis.home_team} awayTeam={analysis.away_team} />
              </div>
              
              {/* 1X2 */}
              <div className="bg-slate-800/50 rounded-xl p-4 border border-slate-700/50">
                <h3 className="text-sm font-semibold text-slate-400 mb-3 flex items-center gap-2"><BarChart3 className="w-4 h-4" />Match Outcome</h3>
                <div className="grid grid-cols-3 gap-3">
                  <div className="text-center p-3 bg-slate-900/50 rounded-lg"><div className="text-2xl font-bold text-cyan-400">{analysis.poisson['1x2'].home}%</div><div className="text-xs text-slate-400">Home</div></div>
                  <div className="text-center p-3 bg-slate-900/50 rounded-lg"><div className="text-2xl font-bold text-yellow-400">{analysis.poisson['1x2'].draw}%</div><div className="text-xs text-slate-400">Draw</div></div>
                  <div className="text-center p-3 bg-slate-900/50 rounded-lg"><div className="text-2xl font-bold text-pink-400">{analysis.poisson['1x2'].away}%</div><div className="text-xs text-slate-400">Away</div></div>
                </div>
              </div>
              
              {/* BTTS */}
              <div className="bg-gradient-to-br from-emerald-900/30 to-cyan-900/30 rounded-xl p-4 border border-emerald-500/30">
                <div className="flex items-center justify-between mb-4">
                  <h3 className="text-sm font-semibold text-emerald-400 flex items-center gap-2"><Goal className="w-4 h-4" />BTTS</h3>
                  <ScoreBadge score={analysis.btts.score} size="sm" />
                </div>
                <div className="space-y-2 text-sm">
                  <div className="flex justify-between"><span className="text-slate-400">Recommendation</span><RecommendationBadge recommendation={analysis.btts.recommendation} /></div>
                  <div className="flex justify-between"><span className="text-slate-400">Probability</span><span className="font-bold text-white">{analysis.btts.probability}%</span></div>
                  <div className="flex justify-between"><span className="text-slate-400">Confidence</span><span className="font-bold text-white">{analysis.btts.confidence}%</span></div>
                </div>
                <div className="mt-4 pt-4 border-t border-slate-700/50 space-y-3">
                  {analysis.btts.factors.poisson && <FactorBar label="Poisson" value={analysis.btts.factors.poisson} icon={BarChart3} />}
                  {analysis.btts.factors.stats_global && <FactorBar label="Stats" value={analysis.btts.factors.stats_global} icon={Activity} />}
                  {analysis.btts.factors.form_l5 && <FactorBar label="Form L5" value={analysis.btts.factors.form_l5} icon={Flame} />}
                </div>
              </div>
              
              {/* Over 2.5 */}
              <div className="bg-gradient-to-br from-blue-900/30 to-purple-900/30 rounded-xl p-4 border border-blue-500/30">
                <div className="flex items-center justify-between mb-4">
                  <h3 className="text-sm font-semibold text-blue-400 flex items-center gap-2"><TrendingUp className="w-4 h-4" />Over 2.5</h3>
                  <ScoreBadge score={analysis.over25.score} size="sm" />
                </div>
                <div className="space-y-2 text-sm">
                  <div className="flex justify-between"><span className="text-slate-400">Recommendation</span><RecommendationBadge recommendation={analysis.over25.recommendation} /></div>
                  <div className="flex justify-between"><span className="text-slate-400">Probability</span><span className="font-bold text-white">{analysis.over25.probability}%</span></div>
                  <div className="flex justify-between"><span className="text-slate-400">xG Total</span><span className="font-bold text-cyan-400">{analysis.poisson.total_xg.toFixed(2)}</span></div>
                </div>
                <div className="mt-4 pt-4 border-t border-slate-700/50 space-y-3">
                  {analysis.over25.factors.poisson && <FactorBar label="Poisson" value={analysis.over25.factors.poisson} icon={BarChart3} />}
                  {analysis.over25.factors.xg_factor && <FactorBar label="xG Factor" value={analysis.over25.factors.xg_factor} icon={Target} />}
                  {analysis.over25.factors.stats_global && <FactorBar label="Stats" value={analysis.over25.factors.stats_global} icon={Activity} />}
                </div>
              </div>
              
              {/* Scores */}
              <div className="bg-slate-800/50 rounded-xl p-4 border border-slate-700/50">
                <h3 className="text-sm font-semibold text-slate-400 mb-3 flex items-center gap-2"><Star className="w-4 h-4" />Scores Probables</h3>
                <div className="space-y-2">
                  {analysis.poisson.most_likely_scores.slice(0, 5).map(([score, prob], idx) => (
                    <div key={score} className="flex items-center gap-3">
                      <span className="w-10 text-sm font-mono text-slate-400">{score}</span>
                      <div className="flex-1 h-5 bg-slate-800 rounded-full overflow-hidden">
                        <div style={{ width: `${prob * 3}%` }} className={`h-full rounded-full ${idx === 0 ? 'bg-gradient-to-r from-cyan-500 to-emerald-400' : 'bg-gradient-to-r from-slate-600 to-slate-500'}`} />
                      </div>
                      <span className="w-12 text-right text-sm font-bold text-white">{prob.toFixed(1)}%</span>
                    </div>
                  ))}
                </div>
              </div>
              
              {/* Over probs */}
              <div className="bg-slate-800/50 rounded-xl p-4 border border-slate-700/50">
                <h3 className="text-sm font-semibold text-slate-400 mb-3 flex items-center gap-2"><Percent className="w-4 h-4" />Goals Probabilities</h3>
                <div className="grid grid-cols-3 gap-2">
                  <div className="text-center p-2 bg-slate-900/50 rounded-lg"><div className="text-lg font-bold text-emerald-400">{analysis.poisson.over15_prob}%</div><div className="text-xs text-slate-500">Over 1.5</div></div>
                  <div className="text-center p-2 bg-slate-900/50 rounded-lg border border-cyan-500/30"><div className="text-lg font-bold text-cyan-400">{analysis.poisson.over25_prob}%</div><div className="text-xs text-slate-500">Over 2.5</div></div>
                  <div className="text-center p-2 bg-slate-900/50 rounded-lg"><div className="text-lg font-bold text-pink-400">{analysis.poisson.over35_prob}%</div><div className="text-xs text-slate-500">Over 3.5</div></div>
                </div>
              </div>
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
};

// Match Row

// 🏆 Helper: Get TOP 3 best markets from all 13 markets
const getTop3Markets = (analysis: MatchAnalysis): Array<{name: string; score: number; recommendation: string}> => {
  const markets: Array<{name: string; score: number; recommendation: string}> = [
    { name: 'BTTS', score: analysis.btts?.score || 0, recommendation: analysis.btts?.recommendation || 'N/A' },
    { name: 'BTTS No', score: analysis.btts_no?.score || 0, recommendation: analysis.btts_no?.recommendation || 'N/A' },
    { name: 'O1.5', score: analysis.over15?.score || 0, recommendation: analysis.over15?.recommendation || 'N/A' },
    { name: 'U1.5', score: analysis.under15?.score || 0, recommendation: analysis.under15?.recommendation || 'N/A' },
    { name: 'O2.5', score: analysis.over25?.score || 0, recommendation: analysis.over25?.recommendation || 'N/A' },
    { name: 'U2.5', score: analysis.under25?.score || 0, recommendation: analysis.under25?.recommendation || 'N/A' },
    { name: 'O3.5', score: analysis.over35?.score || 0, recommendation: analysis.over35?.recommendation || 'N/A' },
    { name: 'U3.5', score: analysis.under35?.score || 0, recommendation: analysis.under35?.recommendation || 'N/A' },
    { name: 'DC 1X', score: analysis.double_chance?.['1x']?.score || 0, recommendation: analysis.double_chance?.['1x']?.recommendation || 'N/A' },
    { name: 'DC X2', score: analysis.double_chance?.['x2']?.score || 0, recommendation: analysis.double_chance?.['x2']?.recommendation || 'N/A' },
    { name: 'DC 12', score: analysis.double_chance?.['12']?.score || 0, recommendation: analysis.double_chance?.['12']?.recommendation || 'N/A' },
    { name: 'DNB H', score: analysis.draw_no_bet?.home?.score || 0, recommendation: analysis.draw_no_bet?.home?.recommendation || 'N/A' },
    { name: 'DNB A', score: analysis.draw_no_bet?.away?.score || 0, recommendation: analysis.draw_no_bet?.away?.recommendation || 'N/A' },
  ].filter(m => m.score > 0);
  
  return markets.sort((a, b) => b.score - a.score).slice(0, 3);
};

const MatchRow = ({ analysis, onOpenDrawer, isExpanded, onToggleExpand }: { analysis: MatchAnalysis; onOpenDrawer: () => void; isExpanded: boolean; onToggleExpand: () => void }) => {
  const maxScore = Math.max(analysis.btts.score, analysis.over25.score);
  const interpretation = analysis.interpretation;
  const [selectedMarket, setSelectedMarket] = useState<{key: string; label: string; score: number; rec: string; value: string; kelly: number; matchName: string} | null>(null);
  const [llmNarrative, setLlmNarrative] = useState<string | null>(null);
  const [llmLoading, setLlmLoading] = useState(false);

  // 🧠 Fetch LLM analysis when expanded (avec cache)
  useEffect(() => {
    if (isExpanded && !llmNarrative && !llmLoading) {
      const fetchLLMAnalysis = async () => {
        setLlmLoading(true);
        try {
          const smart = generateSmartAnalysis(analysis);
          const payload = {
            home_team: analysis.home_team,
            away_team: analysis.away_team,
            league: analysis.league || 'Football',
            xg_home: analysis.poisson.home_xg,
            xg_away: analysis.poisson.away_xg,
            xg_total: analysis.poisson.total_xg,
            context: smart.context,
            top3: smart.top3,
            combos: smart.combos,
            alerts: smart.alerts,
            markets: {
              btts: { score: analysis.btts?.score, recommendation: analysis.btts?.recommendation },
              btts_no: { score: analysis.btts_no?.score, recommendation: analysis.btts_no?.recommendation },
              over15: { score: analysis.over15?.score, recommendation: analysis.over15?.recommendation },
              under15: { score: analysis.under15?.score, recommendation: analysis.under15?.recommendation },
              over25: { score: analysis.over25?.score, recommendation: analysis.over25?.recommendation },
              under25: { score: analysis.under25?.score, recommendation: analysis.under25?.recommendation },
              over35: { score: analysis.over35?.score, recommendation: analysis.over35?.recommendation },
              under35: { score: analysis.under35?.score, recommendation: analysis.under35?.recommendation },
              dc_1x: { score: analysis.double_chance?.['1x']?.score, recommendation: analysis.double_chance?.['1x']?.recommendation },
              dc_x2: { score: analysis.double_chance?.['x2']?.score, recommendation: analysis.double_chance?.['x2']?.recommendation },
              dc_12: { score: analysis.double_chance?.['12']?.score, recommendation: analysis.double_chance?.['12']?.recommendation },
              dnb_home: { score: analysis.draw_no_bet?.home?.score, recommendation: analysis.draw_no_bet?.home?.recommendation },
              dnb_away: { score: analysis.draw_no_bet?.away?.score, recommendation: analysis.draw_no_bet?.away?.recommendation },
            }
          };
          const res = await fetch(`http://91.98.131.218:8001/patron-diamond/analyze-llm/${analysis.match_id}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
          });
          const data = await res.json();
          if (data.narrative) {
            setLlmNarrative(data.narrative);
          }
        } catch (err) {
          console.error('LLM fetch error:', err);
        } finally {
          setLlmLoading(false);
        }
      };
      fetchLLMAnalysis();
    }
  }, [isExpanded, llmNarrative, llmLoading, analysis]);

  
  const getInterestColor = () => {
    if (maxScore >= 70) return 'border-l-purple-500';
    if (maxScore >= 60) return 'border-l-cyan-500';
    if (maxScore >= 50) return 'border-l-yellow-500';
    return 'border-l-slate-600';
  };
  
  return (
    <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className={`bg-slate-800/40 backdrop-blur-sm rounded-xl border border-slate-700/50 hover:border-cyan-500/30 transition-all border-l-4 ${getInterestColor()}`}>
      <div className="p-4 cursor-pointer" onClick={onToggleExpand}>
        <div className="flex items-center justify-between gap-4">
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2">
              <h3 className="font-semibold text-white truncate">{analysis.home_team} vs {analysis.away_team}</h3>
              {maxScore >= 70 && <Diamond className="w-4 h-4 text-purple-400 flex-shrink-0" />}
            </div>
            <p className="text-xs text-slate-500 mt-1">{analysis.league || 'Football'} • xG: {analysis.poisson.total_xg.toFixed(2)}</p>
          </div>
          {interpretation && (
            <div className="hidden md:block">
              <div className={`px-3 py-1 rounded-lg text-xs font-medium ${interpretation.confidence_level === 'HIGH' ? 'bg-emerald-500/20 text-emerald-400' : interpretation.confidence_level === 'MEDIUM' ? 'bg-yellow-500/20 text-yellow-400' : 'bg-slate-700 text-slate-400'}`}>
                {interpretation.best_bet}
              </div>
            </div>
          )}
          <div className="flex items-center gap-4">
            {/* 🏆 TOP 3 Markets */}
            {getTop3Markets(analysis).map((market, idx) => (
              <div key={market.name} className="text-center">
                <div className="text-xs text-slate-500 mb-1 flex items-center justify-center gap-1">
                  {idx === 0 && <span className="text-yellow-400">🏆</span>}
                  {market.name}
                </div>
                <ScoreBadge score={market.score} size="sm" />
              </div>
            ))}
            <div className="flex items-center gap-2">
              <button onClick={(e) => { e.stopPropagation(); onOpenDrawer(); }} className="p-2 rounded-lg bg-cyan-500/20 hover:bg-cyan-500/30 text-cyan-400"><Eye className="w-4 h-4" /></button>
              <button className="p-2 rounded-lg bg-slate-700/50 hover:bg-slate-700 text-slate-400">{isExpanded ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}</button>
            </div>
          </div>
        </div>
      </div>
      <AnimatePresence>
        {isExpanded && (
          <motion.div initial={{ height: 0, opacity: 0 }} animate={{ height: 'auto', opacity: 1 }} exit={{ height: 0, opacity: 0 }} className="overflow-hidden">
            <div className="px-4 pb-4 border-t border-slate-700/50">
              {/* 🏆 ANALYSE SMART 2.0 - 13 Marchés */}
              {(() => {
                const smart = generateSmartAnalysis(analysis);
                return (
                  <div className="mt-4 space-y-3">
                    <div className="p-3 bg-gradient-to-r from-slate-800/80 to-slate-900/80 rounded-lg border border-slate-700/50">
                      <p className="text-sm text-white font-medium">{smart.context}</p>
                    </div>
                    
                    {/* 🧠 Analyse LLM Pro */}
                    <div className="p-4 bg-gradient-to-r from-indigo-900/40 to-purple-900/40 rounded-lg border border-indigo-500/30">
                      <div className="flex items-center gap-2 mb-3">
                        <Brain className="w-4 h-4 text-indigo-400" />
                        <span className="text-sm font-semibold text-indigo-400">Analyse Pro IA</span>
                        {llmLoading && <RefreshCw className="w-3 h-3 text-indigo-400 animate-spin" />}
                      </div>
                      {llmLoading ? (
                        <div className="flex items-center gap-2 text-slate-400 text-sm">
                          <div className="w-2 h-2 bg-indigo-400 rounded-full animate-pulse" />
                          <span>Génération de l analyse en cours...</span>
                        </div>
                      ) : llmNarrative ? (
                        <div className="text-sm text-slate-300 leading-relaxed whitespace-pre-line">{llmNarrative}</div>
                      ) : (
                        <p className="text-sm text-slate-500">Analyse en attente...</p>
                      )}
                    </div>
                    <div className="p-4 bg-gradient-to-r from-emerald-900/30 to-cyan-900/30 rounded-lg border border-emerald-500/30">
                      <div className="flex items-center gap-2 mb-3">
                        <Star className="w-4 h-4 text-yellow-400" />
                        <span className="text-sm font-semibold text-emerald-400">TOP 3 Marchés</span>
                      </div>
                      <div className="grid grid-cols-1 md:grid-cols-3 gap-2 mb-3">
                        {smart.top3.map((m, idx) => (
                          <div key={m.name} className={['p-2 rounded-lg', idx === 0 ? 'bg-yellow-500/20 border border-yellow-500/30' : 'bg-slate-800/50'].join(' ')}>
                            <div className="flex items-center justify-between">
                              <span className="text-xs text-slate-400">{idx === 0 ? '🏆' : idx === 1 ? '🥈' : '🥉'} {m.name}</span>
                              <span className={['font-bold', m.score >= 70 ? 'text-emerald-400' : m.score >= 50 ? 'text-yellow-400' : 'text-red-400'].join(' ')}>{m.score.toFixed(0)}%</span>
                            </div>
                            <p className="text-xs text-slate-500 mt-1">{m.reasoning}</p>
                          </div>
                        ))}
                      </div>
                      <div className="text-sm text-emerald-300 font-medium">{smart.bestBet}</div>
                      {smart.worstBet && <div className="text-xs text-red-400 mt-1">{smart.worstBet}</div>}
                    </div>
                    {smart.combos.length > 0 && (
                      <div className="p-4 bg-gradient-to-r from-purple-900/30 to-pink-900/30 rounded-lg border border-purple-500/30">
                        <div className="flex items-center gap-2 mb-3">
                          <Zap className="w-4 h-4 text-purple-400" />
                          <span className="text-sm font-semibold text-purple-400">Combinés Intelligents</span>
                        </div>
                        <div className="space-y-2">
                          {smart.combos.slice(0, 3).map((combo, idx) => (
                            <div key={combo.name} className={['p-2 rounded-lg', idx === 0 ? 'bg-purple-500/20 border border-purple-500/30' : 'bg-slate-800/30'].join(' ')}>
                              <div className="flex items-center justify-between">
                                <span className="text-sm font-medium text-white">{combo.name}</span>
                                <span className={['text-sm font-bold', combo.confidence >= 65 ? 'text-emerald-400' : 'text-yellow-400'].join(' ')}>{combo.confidence.toFixed(0)}%</span>
                              </div>
                              <p className="text-xs text-slate-400 mt-1">{combo.reasoning}</p>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                    {smart.alerts.length > 0 && (
                      <div className="p-3 bg-orange-900/20 rounded-lg border border-orange-500/30">
                        <div className="flex items-center gap-2 mb-2">
                          <AlertCircle className="w-4 h-4 text-orange-400" />
                          <span className="text-xs font-semibold text-orange-400">Alertes</span>
                        </div>
                        {smart.alerts.map((alert, idx) => (
                          <p key={idx} className="text-xs text-orange-300">{alert}</p>
                        ))}
                      </div>
                    )}
                  </div>
                );
              })()}
              
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mt-4">
                <div className="space-y-2">
                  <h4 className="text-xs font-semibold text-slate-500 uppercase">Quick Stats</h4>
                  <div className="grid grid-cols-2 gap-2 text-sm">
                    <div className="flex justify-between"><span className="text-slate-400">Home xG</span><span className="text-cyan-400 font-bold">{analysis.poisson.home_xg.toFixed(2)}</span></div>
                    <div className="flex justify-between"><span className="text-slate-400">Away xG</span><span className="text-pink-400 font-bold">{analysis.poisson.away_xg.toFixed(2)}</span></div>
                  </div>
                </div>
                <div className="space-y-2">
                  <h4 className="text-xs font-semibold text-slate-500 uppercase">TOP 3 Recommandations</h4>
                  <div className="space-y-1">
                    {(() => {
                      const smart = generateSmartAnalysis(analysis);
                      return smart.top3.slice(0, 3).map((m, idx) => (
                        <div key={m.name} className="flex justify-between items-center">
                          <span className="text-slate-400 text-sm">{idx === 0 ? '🏆' : idx === 1 ? '🥈' : '🥉'} {m.name}</span>
                          <span className={['text-xs px-2 py-1 rounded font-medium', m.score >= 70 ? 'bg-purple-500/20 text-purple-400' : m.score >= 55 ? 'bg-emerald-500/20 text-emerald-400' : 'bg-yellow-500/20 text-yellow-400'].join(' ')}>{m.score.toFixed(0)}%</span>
                        </div>
                      ));
                    })()}
                  </div>
                </div>
                <div className="space-y-2">
                  <h4 className="text-xs font-semibold text-slate-500 uppercase">Top Scores</h4>
                  <div className="flex gap-2">
                    {analysis.poisson.most_likely_scores.slice(0, 3).map(([score, prob]) => (
                      <div key={score} className="flex-1 text-center p-2 bg-slate-900/50 rounded-lg"><div className="font-bold text-white">{score}</div><div className="text-xs text-slate-500">{prob.toFixed(1)}%</div></div>
                    ))}
                  </div>
                </div>
              </div>

              {/* 📊 ANALYSE SMART 2.0 - 13 Markets Grid */}
              <div className="mt-4 p-4 bg-slate-900/50 rounded-lg border border-slate-700/30">
                <h4 className="text-xs font-semibold text-slate-500 uppercase mb-3 flex items-center gap-2">
                  <Layers className="w-4 h-4" />
                  <span>Analyse Smart 2.0</span>
                  <span className="text-slate-600">• 13 Marchés</span>
                </h4>
                <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6 gap-2">
                  {[
                    { key: 'btts', label: 'BTTS Oui', data: analysis.btts },
                    { key: 'btts_no', label: 'BTTS Non', data: analysis.btts_no },
                    { key: 'over15', label: 'Over 1.5', data: analysis.over15 },
                    { key: 'under15', label: 'Under 1.5', data: analysis.under15 },
                    { key: 'over25', label: 'Over 2.5', data: analysis.over25 },
                    { key: 'under25', label: 'Under 2.5', data: analysis.under25 },
                    { key: 'over35', label: 'Over 3.5', data: analysis.over35 },
                    { key: 'under35', label: 'Under 3.5', data: analysis.under35 },
                    { key: 'dc_1x', label: 'Dom/Nul', data: analysis.double_chance?.['1x'] },
                    { key: 'dc_x2', label: 'Nul/Ext', data: analysis.double_chance?.['x2'] },
                    { key: 'dc_12', label: 'Dom/Ext', data: analysis.double_chance?.['12'] },
                    { key: 'dnb_home', label: 'DNB Dom', data: analysis.draw_no_bet?.home },
                    { key: 'dnb_away', label: 'DNB Ext', data: analysis.draw_no_bet?.away },
                  ].map((market) => {
                    const score = market.data?.score || 0;
                    const rec = market.data?.recommendation || '-';
                    const value = market.data?.value_rating || 'N/A';
                    const kelly = market.data?.kelly_pct || 0;
                    const isGood = score >= 65;
                    const isBad = score < 35;
                    return (
                      <div
                        key={market.key}
                        onClick={() => setSelectedMarket({ ...market, score, rec, value, kelly, matchName: `${analysis.home_team} vs ${analysis.away_team}` })}
                        className={[
                          'p-2 rounded-lg text-center cursor-pointer transition-all hover:scale-105',
                          isGood ? 'bg-emerald-900/30 border border-emerald-500/30 hover:border-emerald-400' :
                          isBad ? 'bg-red-900/20 border border-red-500/20 hover:border-red-400' :
                          'bg-slate-800/50 border border-slate-700/30 hover:border-cyan-400'
                        ].join(' ')}
                      >
                        <div className="text-xs text-slate-400">{market.label}</div>
                        <div className={['font-bold', isGood ? 'text-emerald-400' : isBad ? 'text-red-400' : 'text-white'].join(' ')}>{score.toFixed(0)}%</div>
                        <div className={['text-xs', rec === 'DIAMOND PICK' ? 'text-purple-400' : rec === 'STRONG BET' ? 'text-emerald-400' : rec === 'AVOID' ? 'text-red-400' : 'text-slate-500'].join(' ')}>{rec}</div>
                      </div>
                    );
                  })}
                </div>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Modal Détails Marché */}
      <AnimatePresence>
        {selectedMarket && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4"
            onClick={() => setSelectedMarket(null)}
          >
            <motion.div
              initial={{ scale: 0.9, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.9, opacity: 0 }}
              className="bg-slate-800 rounded-xl border border-slate-700 p-6 max-w-md w-full shadow-2xl"
              onClick={(e) => e.stopPropagation()}
            >
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-lg font-bold text-white">{selectedMarket.label}</h3>
                <button onClick={() => setSelectedMarket(null)} className="p-1 rounded-lg hover:bg-slate-700 text-slate-400">
                  <X className="w-5 h-5" />
                </button>
              </div>
              <p className="text-sm text-slate-400 mb-4">{selectedMarket.matchName}</p>
              <div className="space-y-3">
                <div className="flex justify-between items-center p-3 bg-slate-900/50 rounded-lg">
                  <span className="text-slate-400">Score</span>
                  <span className={['text-2xl font-bold', selectedMarket.score >= 65 ? 'text-emerald-400' : selectedMarket.score < 35 ? 'text-red-400' : 'text-white'].join(' ')}>{selectedMarket.score.toFixed(0)}%</span>
                </div>
                <div className="flex justify-between items-center p-3 bg-slate-900/50 rounded-lg">
                  <span className="text-slate-400">Recommandation</span>
                  <span className={['font-semibold', selectedMarket.rec === 'DIAMOND PICK' ? 'text-purple-400' : selectedMarket.rec === 'STRONG BET' ? 'text-emerald-400' : selectedMarket.rec === 'AVOID' ? 'text-red-400' : 'text-yellow-400'].join(' ')}>{selectedMarket.rec}</span>
                </div>
                <div className="flex justify-between items-center p-3 bg-slate-900/50 rounded-lg">
                  <span className="text-slate-400">Value Rating</span>
                  <span className="text-cyan-400 font-semibold">{selectedMarket.value}</span>
                </div>
                <div className="flex justify-between items-center p-3 bg-slate-900/50 rounded-lg">
                  <span className="text-slate-400">Kelly %</span>
                  <span className="text-emerald-400 font-semibold">{selectedMarket.kelly.toFixed(2)}%</span>
                </div>
              </div>
              <div className="mt-4 p-3 bg-gradient-to-r from-purple-900/30 to-cyan-900/30 rounded-lg border border-purple-500/20">
                <p className="text-xs text-slate-300">
                  {selectedMarket.score >= 70 ? '💎 Excellente opportunité - Confiance élevée' :
                   selectedMarket.score >= 55 ? '✅ Bonne opportunité - Confiance moyenne' :
                   selectedMarket.score >= 40 ? '⚠️ Risqué - Prudence recommandée' :
                   '❌ Éviter ce marché'}
                </p>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );
};

// Main Page
export default function FullGainPage() {
  const [analyses, setAnalyses] = useState<MatchAnalysis[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [selectedAnalysis, setSelectedAnalysis] = useState<MatchAnalysis | null>(null);
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [expandedRows, setExpandedRows] = useState<Set<string>>(new Set());
  const [progress, setProgress] = useState({ current: 0, total: 0 });
  const [error, setError] = useState<string | null>(null);
  const [filters, setFilters] = useState({ minScore: 0, market: 'all', search: '' });
  const [stats, setStats] = useState({ total: 0, diamond: 0, strong: 0, avgBtts: 0, avgOver: 0 });
  
  const fetchAnalyses = useCallback(async () => {
    try {
      setError(null);
      setProgress({ current: 0, total: 0 });
      
      const oppRes = await fetch('http://91.98.131.218:8001/opportunities/opportunities/?limit=100');
      if (!oppRes.ok) throw new Error(`API Error: ${oppRes.status}`);
      
      const oppData = await oppRes.json();
      const opportunities: Opportunity[] = Array.isArray(oppData) ? oppData : [];
      if (opportunities.length === 0) { setAnalyses([]); setLoading(false); return; }
      
      // Remove duplicates
      const seen = new Set<string>();
      const uniqueOpportunities = opportunities.filter(opp => {
        if (seen.has(opp.match_id)) return false;
        seen.add(opp.match_id);
        return true;
      });
      
      setProgress({ current: 0, total: uniqueOpportunities.length });
      
      const allAnalyses: MatchAnalysis[] = [];
      const batchSize = 5;
      
      for (let i = 0; i < uniqueOpportunities.length; i += batchSize) {
        const batch = uniqueOpportunities.slice(i, i + batchSize);
        
        const batchResults = await Promise.all(
          batch.map(async (opp) => {
            try {
              const res = await fetch(`http://91.98.131.218:8001/patron-diamond/analyze/${opp.match_id}`);
              if (!res.ok) return null;
              const analysis = await res.json();
              const interpretation = generateInterpretation(analysis);
              return { ...analysis, league: opp.sport?.replace('soccer_', '').replace(/_/g, ' ').toUpperCase(), interpretation };
            } catch { return null; }
          })
        );
        
        allAnalyses.push(...batchResults.filter(Boolean) as MatchAnalysis[]);
        setProgress({ current: Math.min(i + batchSize, uniqueOpportunities.length), total: uniqueOpportunities.length });
        
        if (i + batchSize < uniqueOpportunities.length) await new Promise(r => setTimeout(r, 50));
      }
      
      allAnalyses.sort((a, b) => Math.max(b.btts.score, b.over25.score) - Math.max(a.btts.score, a.over25.score));
      setAnalyses(allAnalyses);
      
      const diamond = allAnalyses.filter(a => a.btts.score >= 70 || a.over25.score >= 70).length;
      const strong = allAnalyses.filter(a => (a.btts.score >= 60 && a.btts.score < 70) || (a.over25.score >= 60 && a.over25.score < 70)).length;
      const avgBtts = allAnalyses.length > 0 ? allAnalyses.reduce((acc, a) => acc + a.btts.score, 0) / allAnalyses.length : 0;
      const avgOver = allAnalyses.length > 0 ? allAnalyses.reduce((acc, a) => acc + a.over25.score, 0) / allAnalyses.length : 0;
      setStats({ total: allAnalyses.length, diamond, strong, avgBtts, avgOver });
      
    } catch (err: any) {
      setError(err.message || 'Erreur de chargement');
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);
  
  useEffect(() => { fetchAnalyses(); }, [fetchAnalyses]);
  
  const handleRefresh = () => { setRefreshing(true); setLoading(true); fetchAnalyses(); };
  const toggleExpand = (id: string) => { setExpandedRows(prev => { const n = new Set(prev); n.has(id) ? n.delete(id) : n.add(id); return n; }); };
  const openDrawer = (a: MatchAnalysis) => { setSelectedAnalysis(a); setDrawerOpen(true); };
  
  const filteredAnalyses = analyses.filter(a => {
    const maxScore = Math.max(a.btts.score, a.over25.score);
    if (maxScore < filters.minScore) return false;
    if (filters.market === 'btts' && a.btts.score < 50) return false;
    if (filters.market === 'over25' && a.over25.score < 50) return false;
    if (filters.search && !a.home_team.toLowerCase().includes(filters.search.toLowerCase()) && !a.away_team.toLowerCase().includes(filters.search.toLowerCase())) return false;
    return true;
  });
  
  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-950 via-slate-900 to-slate-950">
      <div className="fixed inset-0 overflow-hidden pointer-events-none">
        <div className="absolute top-1/4 -left-1/4 w-96 h-96 bg-cyan-500/10 rounded-full blur-3xl animate-pulse" />
        <div className="absolute bottom-1/4 -right-1/4 w-96 h-96 bg-purple-500/10 rounded-full blur-3xl animate-pulse" style={{ animationDelay: '1s' }} />
      </div>
      
      <div className="relative z-10 max-w-7xl mx-auto px-4 py-8">
        <motion.div initial={{ opacity: 0, y: -20 }} animate={{ opacity: 1, y: 0 }} className="mb-8">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-4xl font-black text-transparent bg-clip-text bg-gradient-to-r from-cyan-400 via-purple-400 to-pink-400">FULL GAIN 2.0</h1>
              <p className="text-slate-400 mt-1">Multi-Market Analysis • BTTS & Over 2.5</p>
            </div>
            <button onClick={handleRefresh} disabled={refreshing} className="flex items-center gap-2 px-4 py-2 bg-cyan-500/20 hover:bg-cyan-500/30 text-cyan-400 rounded-lg disabled:opacity-50">
              <RefreshCw className={`w-4 h-4 ${refreshing ? 'animate-spin' : ''}`} />Refresh
            </button>
          </div>
        </motion.div>
        
        {error && (
          <div className="mb-6 p-4 bg-red-900/30 border border-red-500/50 rounded-xl text-red-400">
            <div className="flex items-center gap-2"><AlertCircle className="w-5 h-5" />{error}</div>
          </div>
        )}
        
        {loading && progress.total > 0 && (
          <div className="mb-6">
            <div className="flex justify-between text-sm text-slate-400 mb-2"><span>Analyse en cours...</span><span>{progress.current} / {progress.total}</span></div>
            <div className="h-2 bg-slate-800 rounded-full overflow-hidden"><div style={{ width: `${(progress.current / progress.total) * 100}%` }} className="h-full bg-gradient-to-r from-cyan-500 to-purple-500 transition-all" /></div>
          </div>
        )}
        
        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="grid grid-cols-2 md:grid-cols-5 gap-4 mb-8">
          <div className="bg-slate-800/50 rounded-xl p-4 border border-slate-700/50">
            <div className="flex items-center gap-2 text-slate-400 text-sm mb-2"><Activity className="w-4 h-4" />Matchs</div>
            <div className="text-3xl font-bold text-white"><AnimatedCounter value={stats.total} /></div>
          </div>
          <div className="bg-gradient-to-br from-purple-900/50 to-pink-900/50 rounded-xl p-4 border border-purple-500/30">
            <div className="flex items-center gap-2 text-purple-300 text-sm mb-2"><Diamond className="w-4 h-4" />Diamond</div>
            <div className="text-3xl font-bold text-white"><AnimatedCounter value={stats.diamond} /></div>
          </div>
          <div className="bg-gradient-to-br from-emerald-900/50 to-cyan-900/50 rounded-xl p-4 border border-emerald-500/30">
            <div className="flex items-center gap-2 text-emerald-300 text-sm mb-2"><Zap className="w-4 h-4" />Strong</div>
            <div className="text-3xl font-bold text-white"><AnimatedCounter value={stats.strong} /></div>
          </div>
          <div className="bg-slate-800/50 rounded-xl p-4 border border-slate-700/50">
            <div className="flex items-center gap-2 text-slate-400 text-sm mb-2"><Goal className="w-4 h-4" />Avg BTTS</div>
            <div className="text-3xl font-bold text-cyan-400"><AnimatedCounter value={stats.avgBtts} suffix="%" /></div>
          </div>
          <div className="bg-slate-800/50 rounded-xl p-4 border border-slate-700/50">
            <div className="flex items-center gap-2 text-slate-400 text-sm mb-2"><TrendingUp className="w-4 h-4" />Avg Over</div>
            <div className="text-3xl font-bold text-pink-400"><AnimatedCounter value={stats.avgOver} suffix="%" /></div>
          </div>
        </motion.div>
        
        <div className="flex flex-wrap items-center gap-4 mb-6">
          <div className="relative flex-1 min-w-[200px]">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
            <input type="text" placeholder="Search teams..." value={filters.search} onChange={(e) => setFilters(p => ({ ...p, search: e.target.value }))} className="w-full pl-10 pr-4 py-2 bg-slate-800/50 border border-slate-700/50 rounded-lg text-white placeholder-slate-500 focus:outline-none focus:border-cyan-500/50" />
          </div>
          <select value={filters.market} onChange={(e) => setFilters(p => ({ ...p, market: e.target.value }))} className="px-4 py-2 bg-slate-800/50 border border-slate-700/50 rounded-lg text-white">
            <option value="all">All Markets</option><option value="btts">BTTS Only</option><option value="over25">Over 2.5 Only</option>
          </select>
          <select value={filters.minScore} onChange={(e) => setFilters(p => ({ ...p, minScore: Number(e.target.value) }))} className="px-4 py-2 bg-slate-800/50 border border-slate-700/50 rounded-lg text-white">
            <option value={0}>All Scores</option><option value={50}>≥ 50</option><option value={60}>≥ 60</option><option value={70}>≥ 70 💎</option>
          </select>
        </div>
        
        <div className="space-y-4">
          {loading ? (
            <div className="flex flex-col items-center py-20">
              <RefreshCw className="w-10 h-10 text-cyan-400 animate-spin mb-4" />
              <p className="text-slate-400">Analyzing matches...</p>
            </div>
          ) : filteredAnalyses.length === 0 ? (
            <div className="text-center py-20"><Target className="w-16 h-16 text-slate-600 mx-auto mb-4" /><p className="text-slate-400">No matches found</p></div>
          ) : (
            filteredAnalyses.map((a, idx) => (
              <motion.div key={a.match_id} initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: Math.min(idx * 0.02, 0.5) }}>
                <MatchRow analysis={a} onOpenDrawer={() => openDrawer(a)} isExpanded={expandedRows.has(a.match_id)} onToggleExpand={() => toggleExpand(a.match_id)} />
              </motion.div>
            ))
          )}
        </div>
        
        {!loading && filteredAnalyses.length > 0 && (
          <div className="mt-8 text-center text-sm text-slate-500">
            {filteredAnalyses.length} / {analyses.length} matchs • {new Date().toLocaleTimeString()}
          </div>
        )}
      </div>
      
      <DetailDrawer analysis={selectedAnalysis} isOpen={drawerOpen} onClose={() => setDrawerOpen(false)} />
    </div>
  );
}
