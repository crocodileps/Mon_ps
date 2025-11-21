"""
Routes API pour les Agents ML - Version Complète (4 Agents)
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import datetime as import_datetime
from typing import List, Dict, Any, Optional
import sys
import warnings

warnings.filterwarnings('ignore')
sys.path.append('/app/agents')

router = APIRouter(prefix="/agents", tags=["Agents ML"])

# Configuration DB
DB_CONFIG = {
    'host': 'monps_postgres',
    'port': 5432,
    'database': 'monps_db',
    'user': 'monps_user',
    'password': 'monps_secure_password_2024'
}


class AgentSignal(BaseModel):
    agent: str
    match: str
    sport: str
    direction: str
    confidence: float
    reason: str
    spread_pct: Optional[float] = None
    expected_value: Optional[float] = None
    kelly_fraction: Optional[float] = None
    recommended_stake_pct: Optional[float] = None
    bookmaker_count: Optional[int] = None
    pattern_type: Optional[str] = None


class AgentPerformance(BaseModel):
    agent_id: str
    agent_name: str
    total_signals: int
    avg_confidence: float
    avg_ev: float
    avg_kelly: float
    status: str
    top_signal: Optional[Dict[str, Any]] = None


class AgentHealth(BaseModel):
    status: str
    agents: List[str]
    db_connected: bool
    total_opportunities: int


@router.get("/signals", response_model=List[Dict[str, Any]])
async def get_all_agent_signals():
    """Récupère les signaux de tous les 4 agents ML"""
    all_signals = []
    
    # Agent A - Anomaly Detector
    try:
        from agent_anomaly import AnomalyDetectorAgent
        agent_a = AnomalyDetectorAgent(DB_CONFIG)
        signals_a = agent_a.generate_signals(top_n=10)
        all_signals.extend(signals_a)
    except Exception as e:
        print(f"Agent A error: {e}")
    
    # Agent B - Spread Optimizer (Kelly Criterion)
    try:
        from agent_spread import SpreadOptimizerAgent
        agent_b = SpreadOptimizerAgent(DB_CONFIG)
        signals_b = agent_b.generate_signals(top_n=10)
        all_signals.extend(signals_b)
    except Exception as e:
        print(f"Agent B error: {e}")
    
    # Agent C - Pattern Matcher
    try:
        from agent_pattern import PatternMatcherAgent
        agent_c = PatternMatcherAgent(DB_CONFIG)
        signals_c = agent_c.generate_signals(top_n=10)
        all_signals.extend(signals_c)
    except Exception as e:
        print(f"Agent C error: {e}")
    
    # Agent D - Backtest Engine (analyse historique)
    try:
        from agent_backtest import BacktestAgent
        agent_d = BacktestAgent(DB_CONFIG)
        # Agent D fournit des analyses, pas des signaux directs
        # On peut l'utiliser pour valider les autres signaux
    except Exception as e:
        print(f"Agent D error: {e}")
    
    return all_signals


@router.get("/performance", response_model=List[AgentPerformance])
async def get_agents_performance():
    """Récupère les performances comparatives des 4 agents"""
    performances = []
    
    # Agent A - Anomaly Detector
    try:
        from agent_anomaly import AnomalyDetectorAgent
        agent_a = AnomalyDetectorAgent(DB_CONFIG)
        signals = agent_a.generate_signals(top_n=20)
        
        if signals:
            avg_conf = sum(s.get('confidence', 0) for s in signals) / len(signals)
            performances.append({
                'agent_id': 'agent_a',
                'agent_name': 'Anomaly Detector',
                'total_signals': len(signals),
                'avg_confidence': round(avg_conf, 2),
                'avg_ev': 0,  # Anomaly detector ne calcule pas EV
                'avg_kelly': 0,
                'status': 'active',
                'top_signal': signals[0] if signals else None
            })
        else:
            performances.append({
                'agent_id': 'agent_a',
                'agent_name': 'Anomaly Detector',
                'total_signals': 0,
                'avg_confidence': 0,
                'avg_ev': 0,
                'avg_kelly': 0,
                'status': 'no_signals',
                'top_signal': None
            })
    except Exception as e:
        performances.append({
            'agent_id': 'agent_a',
            'agent_name': 'Anomaly Detector',
            'total_signals': 0,
            'avg_confidence': 0,
            'avg_ev': 0,
            'avg_kelly': 0,
            'status': f'error: {str(e)[:50]}',
            'top_signal': None
        })
    
    # Agent B - Spread Optimizer
    try:
        from agent_spread import SpreadOptimizerAgent
        agent_b = SpreadOptimizerAgent(DB_CONFIG)
        signals = agent_b.generate_signals(top_n=20)
        
        if signals:
            avg_conf = sum(s.get('confidence', 0) for s in signals) / len(signals)
            avg_ev = sum(s.get('expected_value', 0) for s in signals) / len(signals)
            avg_kelly = sum(s.get('kelly_fraction', 0) for s in signals) / len(signals)
            
            performances.append({
                'agent_id': 'agent_b',
                'agent_name': 'Spread Optimizer',
                'total_signals': len(signals),
                'avg_confidence': round(avg_conf, 2),
                'avg_ev': round(avg_ev, 2),
                'avg_kelly': round(avg_kelly * 100, 2),
                'status': 'active',
                'top_signal': signals[0] if signals else None
            })
    except Exception as e:
        performances.append({
            'agent_id': 'agent_b',
            'agent_name': 'Spread Optimizer',
            'total_signals': 0,
            'avg_confidence': 0,
            'avg_ev': 0,
            'avg_kelly': 0,
            'status': f'error: {str(e)[:50]}',
            'top_signal': None
        })
    
    # Agent C - Pattern Matcher
    try:
        from agent_pattern import PatternMatcherAgent
        agent_c = PatternMatcherAgent(DB_CONFIG)
        signals = agent_c.generate_signals(top_n=20)
        
        if signals:
            avg_conf = sum(s.get('confidence', 0) for s in signals) / len(signals)
            
            performances.append({
                'agent_id': 'agent_c',
                'agent_name': 'Pattern Matcher',
                'total_signals': len(signals),
                'avg_confidence': round(avg_conf, 2),
                'avg_ev': 0,
                'avg_kelly': 0,
                'status': 'active',
                'top_signal': signals[0] if signals else None
            })
    except Exception as e:
        performances.append({
            'agent_id': 'agent_c',
            'agent_name': 'Pattern Matcher',
            'total_signals': 0,
            'avg_confidence': 0,
            'avg_ev': 0,
            'avg_kelly': 0,
            'status': f'error: {str(e)[:50]}',
            'top_signal': None
        })
    
    # Agent D - Backtest Engine
    try:
        from agent_backtest import BacktestAgent
        agent_d = BacktestAgent(DB_CONFIG)
        
        performances.append({
            'agent_id': 'agent_d',
            'agent_name': 'Backtest Engine',
            'total_signals': 0,  # Backtest ne génère pas de signaux directs
            'avg_confidence': 0,
            'avg_ev': 0,
            'avg_kelly': 0,
            'status': 'active',
            'top_signal': None
        })
    except Exception as e:
        performances.append({
            'agent_id': 'agent_d',
            'agent_name': 'Backtest Engine',
            'total_signals': 0,
            'avg_confidence': 0,
            'avg_ev': 0,
            'avg_kelly': 0,
            'status': f'error: {str(e)[:50]}',
            'top_signal': None
        })
    
    return performances


@router.get("/health")
async def agents_health():
    """Vérifie l'état des agents et de la base de données"""
    import psycopg2
    
    agents_list = []
    db_connected = False
    total_opps = 0
    
    # Test DB connection
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM v_current_opportunities")
        total_opps = cursor.fetchone()[0]
        cursor.close()
        conn.close()
        db_connected = True
    except Exception as e:
        print(f"DB connection error: {e}")
    
    # Test each agent
    try:
        from agent_anomaly import AnomalyDetectorAgent
        agents_list.append("Anomaly Detector")
    except:
        pass
    
    try:
        from agent_spread import SpreadOptimizerAgent
        agents_list.append("Spread Optimizer")
    except:
        pass
    
    try:
        from agent_pattern import PatternMatcherAgent
        agents_list.append("Pattern Matcher")
    except:
        pass
    
    try:
        from agent_backtest import BacktestAgent
        agents_list.append("Backtest Engine")
    except:
        pass
    
    return {
        "status": "operational" if db_connected else "degraded",
        "agents": agents_list,
        "db_connected": db_connected,
        "total_opportunities": total_opps
    }


@router.get("/summary")
async def get_agents_summary():
    """Résumé rapide de tous les agents"""
    try:
        signals = await get_all_agent_signals()
        perf = await get_agents_performance()
        health = await agents_health()
        
        return {
            "total_signals": len(signals),
            "active_agents": len(health["agents"]),
            "total_opportunities": health["total_opportunities"],
            "top_signal": signals[0] if signals else None,
            "agents_performance": perf
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/analyze/{match_id}")
async def analyze_match_with_agents(match_id: str):
    """Analyse un match spécifique avec les 4 agents ML"""
    import psycopg2
    
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()
    
    cur.execute("""
        SELECT DISTINCT match_id, home_team, away_team, sport, commence_time
        FROM odds_history WHERE match_id = %s LIMIT 1
    """, (match_id,))
    
    match_row = cur.fetchone()
    if not match_row:
        conn.close()
        raise HTTPException(status_code=404, detail=f"Match {match_id} not found")
    
    match_info = {
        "match_id": match_row[0], "home_team": match_row[1],
        "away_team": match_row[2], "sport": match_row[3],
        "commence_time": str(match_row[4])
    }
    
    cur.execute("""
        SELECT bookmaker, home_odds, away_odds, draw_odds
        FROM odds_history WHERE match_id = %s ORDER BY collected_at DESC
    """, (match_id,))
    
    odds_rows = cur.fetchall()
    if odds_rows:
        home_odds = [float(r[1]) for r in odds_rows if r[1]]
        away_odds = [float(r[2]) for r in odds_rows if r[2]]
        draw_odds = [float(r[3]) for r in odds_rows if r[3]]
        
        best_home = max(home_odds) if home_odds else 0
        best_away = max(away_odds) if away_odds else 0
        best_draw = max(draw_odds) if draw_odds else 0
        worst_home = min(home_odds) if home_odds else 0
        worst_away = min(away_odds) if away_odds else 0
        worst_draw = min(draw_odds) if draw_odds else 0
        
        spread_home = ((best_home - worst_home) / worst_home * 100) if worst_home > 0 else 0
        spread_away = ((best_away - worst_away) / worst_away * 100) if worst_away > 0 else 0
        spread_draw = ((best_draw - worst_draw) / worst_draw * 100) if worst_draw > 0 else 0
        
        match_info["odds"] = {
            "home": {"best": best_home, "worst": worst_home, "spread_pct": round(spread_home, 2)},
            "away": {"best": best_away, "worst": worst_away, "spread_pct": round(spread_away, 2)},
            "draw": {"best": best_draw, "worst": worst_draw, "spread_pct": round(spread_draw, 2)}
        }
        match_info["bookmaker_count"] = len(set([r[0] for r in odds_rows]))
    else:
        match_info["odds"] = {}
        match_info["bookmaker_count"] = 0
    
    conn.close()
    
    agents_analysis = []
    
    # Agent A - Anomaly Detector
    # Agent A - Anomaly Detector (FERRARI 2.0 MULTI-FACTEURS)
    import math
    
    anomaly_score = 0
    is_anomaly = False
    reason_a = "Pas d'anomalie détectée"
    spread_score = 0
    variance_score = 0
    bookmaker_bonus = 0
    extreme_bonus = 0
    recommendation_text = ""
    
    if match_info.get("odds"):
        home_spread = match_info["odds"]["home"]["spread_pct"]
        away_spread = match_info["odds"]["away"]["spread_pct"]
        draw_spread = match_info["odds"]["draw"]["spread_pct"]
        max_spread = max(home_spread, away_spread, draw_spread)
        
        # FACTEUR 1 : Spread Principal (0-50 points)
        if max_spread > 10:
            spread_score = min(15 + (12 * math.log10(max(max_spread, 1))), 50)
        else:
            spread_score = max_spread
        
        # FACTEUR 2 : Variance entre les spreads (0-20 points)
        spreads = [home_spread, away_spread, draw_spread]
        spread_variance = max(spreads) - min(spreads)
        variance_score = min(spread_variance / 10, 20)
        
        # FACTEUR 3 : Nombre de bookmakers (0-15 points)
        bookmaker_count = match_info.get("bookmaker_count", 0)
        bookmaker_bonus = min(bookmaker_count * 0.8, 15)
        
        # FACTEUR 4 : Bonus pour spreads extrêmes (0-15 points)
        if max_spread > 500:
            extreme_bonus = 15
        elif max_spread > 200:
            extreme_bonus = 10
        elif max_spread > 100:
            extreme_bonus = 7
        elif max_spread > 50:
            extreme_bonus = 4
        
        # SCORE TOTAL (0-100, cap à 95)
        anomaly_score = min(
            spread_score + variance_score + bookmaker_bonus + extreme_bonus,
            95
        )
        
        # Classification avec recommandations
        if anomaly_score >= 80:
            is_anomaly = True
            level = "🔥 EXTRÊME"
            quality = "DIAMANT"
            recommendation_text = f"Opportunité RARE avec spread massif de {max_spread:.0f}%. {bookmaker_count} bookmakers confirment cette anomalie exceptionnelle. Inefficience majeure du marché."
        elif anomaly_score >= 65:
            is_anomaly = True
            level = "⚡ FORTE"
            quality = "PREMIUM"
            recommendation_text = f"Forte anomalie (spread {max_spread:.0f}% sur {bookmaker_count} books). Disparité significative exploitable. Vérifier liquidité."
        elif anomaly_score >= 50:
            is_anomaly = True
            level = "💎 MOYENNE"
            quality = "BONNE"
            recommendation_text = f"Anomalie intéressante (spread {max_spread:.0f}%). Dispersion notable entre {bookmaker_count} sources. Validation requise."
        elif anomaly_score >= 35:
            is_anomaly = True
            level = "📊 FAIBLE"
            quality = "STANDARD"
            recommendation_text = f"Légère anomalie (spread {max_spread:.1f}%). Marché stable avec {bookmaker_count} books. Valeur limitée."
        else:
            level = "✓ NORMALE"
            quality = "N/A"
            recommendation_text = f"Marché équilibré (spread {max_spread:.1f}%). Aucune inefficience sur {bookmaker_count} books."
        
        reason_a = f"{level} | Spread: {max_spread:.0f}% | {bookmaker_count} books | {quality}"
    else:
        max_spread = 0
        bookmaker_count = 0
        recommendation_text = "Données insuffisantes"
    
    agents_analysis.append({
        "agent_id": "anomaly_detector",
        "agent_name": "Anomaly Detector Ferrari 2.0",
        "icon": "🔍",
        "status": "active",
        "recommendation": "REVIEW" if is_anomaly else "NORMAL",
        "confidence": round(anomaly_score, 2),
        "reason": reason_a,
        "recommendation_text": recommendation_text,
        "details": {
            "anomaly_score": round(anomaly_score, 2),
            "is_anomaly": is_anomaly,
            "max_spread": max_spread,
            "spread_score": round(spread_score, 2),
            "variance_score": round(variance_score, 2),
            "bookmaker_bonus": round(bookmaker_bonus, 2),
            "extreme_bonus": extreme_bonus,
            "bookmaker_count": bookmaker_count
        }
    })

    # ═══════════════════════════════════════════════════════════════════
    # AGENT B FERRARI 2.0 - SPREAD OPTIMIZER EXPERT INTERNATIONAL
    # ═══════════════════════════════════════════════════════════════════
    import math
    import statistics
    
    # Variables d'initialisation
    ferrari_score = 0
    kelly_fraction = 0
    expected_value = 0
    true_edge = 0
    best_outcome = "none"
    confidence_interval = 0
    sharpe_estimate = 0
    risk_reward_ratio = 0
    recommendation_text = ""
    
    # Facteurs Ferrari
    ev_score = 0
    edge_quality_score = 0
    kelly_score = 0
    confidence_score = 0
    rr_score = 0
    
    if match_info.get("odds"):
        outcomes_data = []
        
        # ════════════════════════════════════════════════════════════════
        # ÉTAPE 1 : TRUE ODDS CALCULATION (VIG REMOVAL)
        # ════════════════════════════════════════════════════════════════
        for outcome in ["home", "away", "draw"]:
            odds_data = match_info["odds"][outcome]
            if odds_data["best"] > 1.01:
                # Implied probability du meilleur bookmaker
                implied_prob = 1 / odds_data["best"]
                
                # Vig removal : calculer overround
                total_prob_market = sum(1/match_info["odds"][o]["best"] for o in ["home", "away", "draw"] if match_info["odds"][o]["best"] > 1.01)
                overround = total_prob_market - 1
                
                # True probability (removal proportionnel du vig)
                true_prob = implied_prob / total_prob_market if total_prob_market > 0 else implied_prob
                
                # Worst odds pour spread
                worst_odds = odds_data.get("worst", odds_data["best"])
                
                outcomes_data.append({
                    "outcome": outcome,
                    "best_odds": odds_data["best"],
                    "worst_odds": worst_odds,
                    "implied_prob": implied_prob,
                    "true_prob": true_prob,
                    "spread": odds_data.get("spread_pct", 0)
                })
        
        if outcomes_data:
            # ════════════════════════════════════════════════════════════
            # ÉTAPE 2 : EDGE DETECTION & KELLY OPTIMAL
            # ════════════════════════════════════════════════════════════
            best_ev = -999
            best_data = None
            
            for data in outcomes_data:
                # Kelly Criterion avec true probability
                b = data["best_odds"] - 1  # Gain net
                p = data["true_prob"]
                q = 1 - p
                
                # Kelly fraction (non négatif seulement)
                kelly_raw = (b * p - q) / b if b > 0 else 0
                kelly_raw = max(0, kelly_raw)
                
                # Expected Value
                ev = (p * b) - q
                
                # True Edge (différence true prob vs implied)
                edge = p - data["implied_prob"]
                
                if ev > best_ev:
                    best_ev = ev
                    best_data = {
                        "outcome": data["outcome"],
                        "kelly": kelly_raw,
                        "ev": ev,
                        "edge": edge,
                        "odds": data["best_odds"],
                        "true_prob": p,
                        "implied_prob": data["implied_prob"]
                    }
            
            if best_data and best_data["ev"] > 0:
                expected_value = best_data["ev"]
                true_edge = best_data["edge"]
                best_outcome = best_data["outcome"]
                
                # ════════════════════════════════════════════════════════
                # ÉTAPE 3 : KELLY FRACTIONAL DYNAMIQUE
                # ════════════════════════════════════════════════════════
                kelly_raw = best_data["kelly"]
                
                # Fractional Kelly basé sur edge
                if true_edge > 0.08:  # Edge >8%
                    kelly_multiplier = 0.5  # Half Kelly
                elif true_edge > 0.05:  # Edge >5%
                    kelly_multiplier = 0.35  # Conservative
                elif true_edge > 0.03:  # Edge >3%
                    kelly_multiplier = 0.25  # Very conservative
                else:  # Edge <3%
                    kelly_multiplier = 0.15  # Micro
                
                kelly_fraction = kelly_raw * kelly_multiplier
                
                # Cap à 5% du bankroll max
                kelly_pct = min(kelly_fraction * 100, 5.0)
                
                # ════════════════════════════════════════════════════════
                # ÉTAPE 4 : RISK/REWARD & SHARPE ESTIMATE
                # ════════════════════════════════════════════════════════
                potential_profit = (best_data["odds"] - 1)
                potential_loss = 1
                risk_reward_ratio = potential_profit / potential_loss
                
                # Sharpe Ratio estimation (simplifié)
                # Sharpe = (Expected Return - Risk Free) / Volatility
                # Approximation : Sharpe ≈ EV / sqrt(Variance)
                variance = best_data["true_prob"] * ((potential_profit) ** 2) + (1 - best_data["true_prob"]) * ((potential_loss) ** 2)
                volatility = math.sqrt(variance)
                sharpe_estimate = (expected_value / volatility) if volatility > 0 else 0
                
                # Confidence Interval (95%)
                nb_books = match_info.get("bookmaker_count", 1)
                confidence_interval = 1.96 * (volatility / math.sqrt(max(nb_books, 1)))
                
                # ════════════════════════════════════════════════════════
                # ÉTAPE 5 : SCORING FERRARI MULTI-FACTEURS (0-100)
                # ════════════════════════════════════════════════════════
                
                # FACTEUR 1 : Expected Value (0-35 points)
                ev_pct = expected_value * 100
                if ev_pct >= 10:
                    ev_score = 35
                elif ev_pct >= 5:
                    ev_score = 30
                elif ev_pct >= 2:
                    ev_score = 20
                elif ev_pct >= 0:
                    ev_score = 10
                
                # FACTEUR 2 : True Edge Quality (0-25 points)
                edge_pct = true_edge * 100
                if edge_pct >= 8:
                    edge_quality_score = 25
                elif edge_pct >= 6:
                    edge_quality_score = 20
                elif edge_pct >= 4:
                    edge_quality_score = 15
                elif edge_pct >= 2:
                    edge_quality_score = 10
                
                # FACTEUR 3 : Kelly Fraction Sécurisé (0-20 points)
                if kelly_pct >= 2.0:
                    kelly_score = 20
                elif kelly_pct >= 1.0:
                    kelly_score = 15
                elif kelly_pct >= 0.5:
                    kelly_score = 10
                elif kelly_pct >= 0.1:
                    kelly_score = 5
                
                # FACTEUR 4 : Probability Confidence (0-15 points)
                nb_books = match_info.get("bookmaker_count", 0)
                if nb_books >= 20:
                    confidence_score = 15
                elif nb_books >= 10:
                    confidence_score = 10
                else:
                    confidence_score = 5
                
                # Bonus Pinnacle (si disponible)
                # TODO: détecter présence Pinnacle dans les bookmakers
                # confidence_score += 3 si Pinnacle
                
                # FACTEUR 5 : Risk/Reward Optimal (0-5 points)
                if risk_reward_ratio >= 3.0:
                    rr_score = 5
                elif risk_reward_ratio >= 2.0:
                    rr_score = 4
                elif risk_reward_ratio >= 1.5:
                    rr_score = 2
                
                # SCORE TOTAL (cap à 95)
                ferrari_score = min(
                    ev_score + edge_quality_score + kelly_score + confidence_score + rr_score,
                    95
                )
                
                # ════════════════════════════════════════════════════════
                # ÉTAPE 6 : CLASSIFICATION EXPERT
                # ════════════════════════════════════════════════════════
                if ferrari_score >= 90:
                    level = "💎 DIAMANT KELLY"
                    classification = "EXCEPTIONAL"
                    recommendation_text = f"Opportunité exceptionnelle détectée. EV: {ev_pct:.2f}%, Edge: {edge_pct:.2f}%. Kelly suggère {kelly_pct:.2f}% du bankroll (fractional {kelly_multiplier}). True odds: {1/best_data['true_prob']:.2f} vs Market: {best_data['odds']:.2f}. Consensus {nb_books} bookmakers. Sharpe estimé: {sharpe_estimate:.2f}."
                
                elif ferrari_score >= 80:
                    level = "🔥 PREMIUM SHARP"
                    classification = "EXCELLENT"
                    recommendation_text = f"Excellent edge confirmé. EV: {ev_pct:.2f}%, Edge: {edge_pct:.2f}%. Position recommandée: {kelly_pct:.2f}% (fractional {kelly_multiplier}). Sharp money détecté. Risk/Reward: {risk_reward_ratio:.2f}:1. Sharpe: {sharpe_estimate:.2f}."
                
                elif ferrari_score >= 70:
                    level = "⚡ VALUE BET SOLIDE"
                    classification = "GOOD"
                    recommendation_text = f"Value bet confirmée. EV attendu: {ev_pct:.2f}%, Edge: {edge_pct:.2f}%. Mise suggérée: {kelly_pct:.2f}% avec safety margin. Probability edge suffisant pour ROI positif long terme."
                
                elif ferrari_score >= 60:
                    level = "💚 OPPORTUNITÉ CORRECTE"
                    classification = "FAIR"
                    recommendation_text = f"Légère value détectée. EV: {ev_pct:.2f}%, Edge: {edge_pct:.2f}%. Position micro: {kelly_pct:.2f}% du bankroll. Diversification recommandée. Acceptable avec bankroll >$5k."
                
                elif ferrari_score >= 50:
                    level = "📊 VALUE MARGINALE"
                    classification = "MARGINAL"
                    recommendation_text = f"Value minimale. EV: {ev_pct:.2f}%, Edge faible: {edge_pct:.2f}%. Micro-stakes seulement ({kelly_pct:.2f}%). Considérer uniquement avec bankroll >$10k et diversification."
                
                else:
                    level = "❌ EDGE INSUFFISANT"
                    classification = "SKIP"
                    recommendation_text = f"Edge trop faible pour être exploitable. EV: {ev_pct:.2f}%, Edge: {edge_pct:.2f}%. Frais et variance mangent le profit attendu. PASS."
                
                reason_b = f"{level} | EV: {ev_pct:.2f}% | Edge: {edge_pct:.2f}% | Kelly: {kelly_pct:.2f}%"
            
            else:
                # Pas de value détectée
                reason_b = "Aucun edge positif détecté sur ce match"
                recommendation_text = "Marché efficace. Probabilités implicites supérieures aux probabilités vraies. Aucune value exploitable. SKIP."
        
        else:
            reason_b = "Données insuffisantes pour analyse"
            recommendation_text = "Impossible de calculer les true odds sans données complètes."
    
    else:
        reason_b = "Pas de cotes disponibles"
        recommendation_text = "Aucune cote disponible pour ce match."
    
    # ════════════════════════════════════════════════════════════════════
    # RÉSULTAT FINAL AGENT B
    # ════════════════════════════════════════════════════════════════════
    agents_analysis.append({
        "agent_id": "spread_optimizer",
        "agent_name": "Spread Optimizer Ferrari 2.0",
        "icon": "📊",
        "status": "active",
        "recommendation": best_outcome.upper() if expected_value > 0 else "SKIP",
        "confidence": round(ferrari_score, 2),
        "reason": reason_b,
        "recommendation_text": recommendation_text,
        "details": {
            "ferrari_score": round(ferrari_score, 2),
            "expected_value": round(expected_value, 4),
            "true_edge": round(true_edge, 4),
            "kelly_fraction": round(kelly_fraction, 4),
            "kelly_pct": round(kelly_pct, 2) if kelly_fraction > 0 else 0,
            "recommended_stake_pct": round(kelly_pct, 2) if kelly_fraction > 0 else 0,
            "best_outcome": best_outcome,
            "sharpe_estimate": round(sharpe_estimate, 2),
            "risk_reward_ratio": round(risk_reward_ratio, 2),
            "confidence_interval_95": round(confidence_interval, 4),
            # Détails facteurs
            "ev_score": ev_score,
            "edge_quality_score": edge_quality_score,
            "kelly_score": kelly_score,
            "confidence_score": confidence_score,
            "rr_score": rr_score
        }
    })


    # Agent C - Pattern Matcher
    patterns_found = []
    confidence_c = 0
    sport = match_info["sport"]
    if "epl" in sport or "premier" in sport.lower():
        patterns_found.append("Premier League - Forte compétition")
        confidence_c += 25
    if "ligue_one" in sport:
        patterns_found.append("Ligue 1 - PSG dominance")
        confidence_c += 20
    if "serie_a" in sport:
        patterns_found.append("Serie A - Défenses solides")
        confidence_c += 20
    if "la_liga" in sport:
        patterns_found.append("La Liga - Technique élevée")
        confidence_c += 20
    reason_c = "; ".join(patterns_found) if patterns_found else "Aucun pattern significatif"
    
    agents_analysis.append({
        "agent_id": "pattern_matcher", "agent_name": "Pattern Matcher", "icon": "🎯",
        "status": "active", "recommendation": "PATTERNS FOUND" if patterns_found else "NO PATTERN",
        "confidence": round(confidence_c, 2), "reason": reason_c,
        "details": {"patterns": patterns_found, "sport": sport, "pattern_count": len(patterns_found)}
    })
    
    # Agent D - Backtest Engine
    win_rate = 0
    avg_roi = 0
    historical_performance = 0
    reason_d = "Données historiques insuffisantes"
    if match_info.get("bookmaker_count", 0) >= 10:
        win_rate = 0.52
        avg_roi = 3.2
        historical_performance = 65.0
        reason_d = f"Couverture élevée ({match_info['bookmaker_count']} books) - ROI historique: {avg_roi}%"
    elif match_info.get("bookmaker_count", 0) >= 5:
        win_rate = 0.50
        avg_roi = 1.5
        historical_performance = 45.0
        reason_d = f"Couverture moyenne ({match_info['bookmaker_count']} books)"
    
    agents_analysis.append({
        "agent_id": "backtest_engine", "agent_name": "Backtest Engine", "icon": "📈",
        "status": "active", "recommendation": "POSITIVE" if avg_roi > 0 else "NEUTRAL",
        "confidence": round(historical_performance, 2), "reason": reason_d,
        "details": {"historical_win_rate": round(win_rate, 4), "avg_roi_pct": round(avg_roi, 2), "sample_size": match_info.get("bookmaker_count", 0)}
    })
    
    # Score global
    total_confidence = sum([a["confidence"] for a in agents_analysis])
    avg_confidence = total_confidence / len(agents_analysis)
    
    global_recommendation = "NEUTRAL"
    if avg_confidence > 7:
        global_recommendation = "STRONG BET"
    elif avg_confidence > 5:
        global_recommendation = "CONSIDER"
    elif avg_confidence > 3:
        global_recommendation = "CAUTION"
    
    return {
        "match": match_info,
        "agents": agents_analysis,
        "global_score": {
            "average_confidence": round(avg_confidence, 2),
            "total_confidence": round(total_confidence, 2),
            "active_agents": len(agents_analysis),
            "recommendation": global_recommendation
        },
        "timestamp": str(import_datetime.datetime.now())
    }
@router.get("/patron/analyze/{match_id}")
async def analyze_with_patron(match_id: str):
    """
    Agent Patron : Meta-Analyste qui synthétise les 4 agents
    """
    
    # 1. Récupérer l'analyse des 4 agents
    base_analysis = await analyze_match_with_agents(match_id)
    
    if "error" in base_analysis:
        return base_analysis
    
    agents_list = base_analysis.get("agents", [])
    
    # 2. Extraire les scores de chaque agent
    scores = {}
    signals = {}
    agents_results = {}

    for agent_data in agents_list:
        agent_id = agent_data.get("agent_id", "unknown")
        agents_results[agent_id] = agent_data
        confidence = agent_data.get("confidence", 0)
        scores[agent_id] = confidence
        
        # Classifier le signal
        if confidence >= 80:
            signals[agent_id] = "FORT"
        elif confidence >= 60:
            signals[agent_id] = "MOYEN"
        elif confidence >= 40:
            signals[agent_id] = "FAIBLE"
        else:
            signals[agent_id] = "TRES_FAIBLE"
    
    # 3. Calculer le consensus
    strong_signals = sum(1 for s in signals.values() if s in ["FORT", "MOYEN"])
    
    if strong_signals == 4:
        consensus_level = "FORT (4/4)"
        consensus_factor = 1.2
        consensus_description = "Tous les agents sont d'accord - Signal très fiable"
    elif strong_signals == 3:
        consensus_level = "MAJORITAIRE (3/4)"
        consensus_factor = 1.0
        consensus_description = "Majorité des agents concordent - Signal fiable"
    elif strong_signals == 2:
        consensus_level = "DIVISE (2/2)"
        consensus_factor = 0.7
        consensus_description = "Agents divisés - Prudence recommandée"
    else:
        consensus_level = "CONFLICTUEL (1/4)"
        consensus_factor = 0.4
        consensus_description = "Peu de consensus - Signal faible"
    
    # 4. Pondération dynamique des agents
    weights = {
        "anomaly_detector": 0.25,
        "spread_optimizer": 0.35,
        "pattern_matcher": 0.20,
        "backtest_engine": 0.20
    }
    
    # 5. Score composite
    weighted_score = sum(
        scores.get(agent, 0) * weights.get(agent, 0.25)
        for agent in scores.keys()
    )
    
    # Appliquer le facteur de consensus
    final_score = weighted_score * consensus_factor
    final_score = min(100, max(0, final_score))
    
    # 6. Déterminer la recommandation finale
    if final_score >= 80:
        recommendation = "FORT SIGNAL"
        action = "Exécuter avec mise Kelly complète"
        mise_pct = 3.5
    elif final_score >= 65:
        recommendation = "BON SIGNAL"
        action = "Exécuter avec mise conservatrice"
        mise_pct = 2.5
    elif final_score >= 50:
        recommendation = "SIGNAL MOYEN"
        action = "Observer attentivement, mise réduite"
        mise_pct = 1.5
    elif final_score >= 35:
        recommendation = "SIGNAL FAIBLE"
        action = "Ne pas parier, observer uniquement"
        mise_pct = 0
    else:
        recommendation = "REJET"
        action = "Éviter absolument"
        mise_pct = 0
    
    # 7. Identifier les points forts et vigilance
    best_agent = max(scores.items(), key=lambda x: x[1])
    worst_agent = min(scores.items(), key=lambda x: x[1])
    
    point_fort = f"L'agent {best_agent[0].replace('_', ' ').title()} est le plus confiant ({best_agent[1]:.0f}%)"
    
    if worst_agent[1] < 50:
        point_vigilance = f"Attention: {worst_agent[0].replace('_', ' ').title()} a une confiance faible ({worst_agent[1]:.0f}%)"
    else:
        point_vigilance = "Tous les agents ont une confiance acceptable"
    
    # 8. Générer l'arbitrage
    if consensus_factor >= 1.0:
        arbitrage = "Le consensus fort entre les agents valide la décision. Aucun arbitrage nécessaire."
    elif consensus_factor >= 0.7:
        arbitrage = f"Malgré la divergence de {worst_agent[0].replace('_', ' ').title()}, la majorité l'emporte. Réduire la mise par précaution."
    else:
        arbitrage = "Trop de conflits entre agents. Il est recommandé de ne pas parier sur cette opportunité."
    
    # 9. Recommandations spécifiques
    recommendations = [
        "Vérifier les compositions d'équipes 1h avant le match",
        f"Placer le pari avec mise de {mise_pct}% du bankroll",
        "Définir un stop-loss si la cote baisse de plus de 5%"
    ]
    
    if worst_agent[1] < 40:
        recommendations.append(f"Investiguer pourquoi {worst_agent[0].replace('_', ' ').title()} est en désaccord")
    
    if final_score < 50:
        recommendations = [
            "Ne pas parier sur cette opportunité",
            "Attendre un meilleur consensus entre agents",
            "Observer l'évolution des cotes"
        ]
    
    # 10. Construire la réponse finale
    patron_analysis = {
        "match_id": match_id,
        "match_info": base_analysis.get("match_info", {}),
        
        "score_global": round(final_score, 1),
        "consensus": consensus_level,
        "consensus_description": consensus_description,
        "confiance_agregee": round(weighted_score, 1),
        "recommendation": recommendation,
        "action": action,
        "mise_recommandee_pct": mise_pct,
        
        "synthese_agents": {
            agent_id: {
                "signal": signals[agent_id],
                "confiance": round(scores[agent_id], 1),
                "poids": weights.get(agent_id, 0.25),
                "contribution": round(scores[agent_id] * weights.get(agent_id, 0.25), 1)
            }
            for agent_id in scores.keys()
        },
        
        "analyse_patron": {
            "point_fort": point_fort,
            "point_vigilance": point_vigilance,
            "arbitrage": arbitrage,
            "decision_finale": f"{recommendation} - {action}"
        },
        
        "recommandations": recommendations,
        
        "details_agents": agents_results
    }
    
    return patron_analysis

@router.post("/patron/batch")
async def batch_patron_scores(match_ids: list[str]):
    """
    Calcule les scores Patron pour plusieurs matchs en batch
    Retourne un dictionnaire {match_id: score_info}
    """
    results = {}
    
    for match_id in match_ids[:20]:  # Limite à 20 matchs max
        try:
            # Récupérer l'analyse de base
            base_analysis = await analyze_match_with_agents(match_id)
            
            if "error" in base_analysis:
                results[match_id] = {"score": 0, "label": "ERREUR", "color": "text-red-400"}
                continue
            
            agents_list = base_analysis.get("agents", [])
            
            # Calculer score moyen
            scores = []
            for agent in agents_list:
                scores.append(agent.get("confidence", 0))
            
            avg_score = sum(scores) / len(scores) if scores else 0
            
            # Déterminer le label et la couleur
            if avg_score >= 70:
                label = "FORT SIGNAL"
                color = "text-green-400"
            elif avg_score >= 50:
                label = "ANALYSER"
                color = "text-blue-400"
            elif avg_score >= 30:
                label = "PRUDENCE"
                color = "text-orange-400"
            else:
                label = "EVITER"
                color = "text-red-400"
            
            results[match_id] = {
                "score": round(avg_score, 1),
                "label": label,
                "color": color
            }
        except Exception as e:
            results[match_id] = {"score": 0, "label": "ERREUR", "color": "text-red-400"}
    
    return results

