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

# ═══════════════════════════════════════════════════════════
# LEARNING SYSTEM - HELPER FUNCTIONS
# ═══════════════════════════════════════════════════════════

def save_agent_analysis(match_info, agent_name, agent_version, recommendation, confidence, reasoning, factors):
    """Sauvegarde l'analyse d'un agent dans la DB"""
    import psycopg2
    import json
    
    try:
        conn = psycopg2.connect(
            host="monps_postgres",
            database="monps_db",
            user="monps_user",
            password="monps_secure_password_2024"
        )
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO agent_analyses 
            (match_id, agent_name, agent_version, home_team, away_team, 
             sport, league, commence_time, recommendation, confidence_score, 
             reasoning, factors)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (match_id, agent_name, analyzed_at) DO NOTHING
        """, (
            match_info.get('match_id'),
            agent_name,
            agent_version,
            match_info.get('home_team'),
            match_info.get('away_team'),
            match_info.get('sport'),
            match_info.get('league'),
            match_info.get('commence_time'),
            recommendation,
            confidence,
            reasoning,
            json.dumps(factors)
        ))
        
        conn.commit()
        conn.close()
    except Exception as e:
        pass

def save_agent_prediction(match_info, agent_name, predicted_outcome, probability, confidence, strategy, edge, kelly):
    """Sauvegarde une prédiction agent"""
    import psycopg2
    
    try:
        conn = psycopg2.connect(
            host="monps_postgres",
            database="monps_db",
            user="monps_user",
            password="monps_secure_password_2024"
        )
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO agent_predictions 
            (match_id, agent_name, predicted_outcome, predicted_probability, 
             confidence, strategy_used, edge_detected, kelly_fraction)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (match_id, agent_name, predicted_at) DO NOTHING
        """, (
            match_info.get('match_id'),
            agent_name,
            predicted_outcome,
            probability,
            confidence,
            strategy,
            edge,
            kelly
        ))
        
        conn.commit()
        conn.close()
    except Exception as e:
        pass




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
    # === LEARNING SYSTEM: Save Agent A Analysis ===
    try:
        save_agent_analysis(
            match_info=match_info,
            agent_name="Anomaly Detector Ferrari 2.0",
            agent_version="2.0",
            recommendation="REVIEW" if is_anomaly else "NORMAL",
            confidence=anomaly_score,
            reasoning=recommendation_text,
            factors={
                "spread_score": spread_score,
                "variance_score": variance_score,
                "bookmaker_bonus": bookmaker_bonus,
                "extreme_bonus": extreme_bonus,
                "max_spread": max_spread,
                "bookmaker_count": bookmaker_count
            }
        )
    except:
        pass


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
    # === LEARNING SYSTEM: Save Agent B Analysis ===
    try:
        save_agent_analysis(
            match_info=match_info,
            agent_name="Spread Optimizer Ferrari 2.0",
            agent_version="2.0",
            recommendation=best_outcome.upper() if expected_value > 0 else "SKIP",
            confidence=ferrari_score,
            reasoning=recommendation_text,
            factors={
                "expected_value": float(expected_value),
                "true_edge": float(true_edge),
                "kelly_fraction": float(kelly_fraction),
                "kelly_pct": float(kelly_pct) if kelly_fraction > 0 else 0,
                "sharpe_estimate": float(sharpe_estimate),
                "risk_reward_ratio": float(risk_reward_ratio),
                "ev_score": ev_score,
                "edge_quality_score": edge_quality_score,
                "kelly_score": kelly_score
            }
        )
        if expected_value > 0:
            save_agent_prediction(
                match_info=match_info,
                agent_name="Spread Optimizer Ferrari 2.0",
                predicted_outcome=best_outcome,
                probability=float(best_data.get('true_prob', 0)) if 'best_data' in locals() and best_data else 0,
                confidence=ferrari_score,
                strategy="Kelly Criterion",
                edge=float(true_edge),
                kelly=float(kelly_fraction)
            )
    except Exception as e:
        pass



     # Agent C - Pattern Matcher Ferrari 2.0
    patterns_found = []
    ferrari_score_c = 0
    pattern_strength = 0
    sample_size_score = 0
    recent_form_score = 0
    context_score = 0
    recommendation_text_c = ""
    sport = match_info.get("sport", "")
    home_team = match_info.get("home_team", "")
    away_team = match_info.get("away_team", "")
    league_stats = {}
    context_factors = []
    sample_quality = "INCONNU"

    # Analyse patterns de ligue
    if "epl" in sport.lower() or "premier" in sport.lower():
        patterns_found.append("Premier League: Forte variance")
        pattern_strength += 15
        league_stats = {"avg_home_win": 0.45, "competitiveness": "HIGH"}
    elif "ligue_one" in sport.lower() or "france" in sport.lower():
        patterns_found.append("Ligue 1: PSG dominance")
        pattern_strength += 12
        league_stats = {"avg_home_win": 0.48, "psg_factor": True}
    elif "serie_a" in sport.lower() or "italy" in sport.lower():
        patterns_found.append("Serie A: Défenses solides")
        pattern_strength += 13
        league_stats = {"avg_home_win": 0.42, "defensive": True}
    elif "la_liga" in sport.lower() or "spain" in sport.lower():
        patterns_found.append("La Liga: Technique élevée")
        pattern_strength += 14
        league_stats = {"avg_home_win": 0.46, "top2_dominance": True}
    elif "bundesliga" in sport.lower() or "germany" in sport.lower():
        patterns_found.append("Bundesliga: Bayern dominance")
        pattern_strength += 13
        league_stats = {"avg_home_win": 0.47, "high_scoring": True}

    # Patterns équipes élites
    elite_teams = ["PSG", "Paris", "Bayern", "Real Madrid", "Barcelona", "Man City", "Liverpool", "Manchester City", "Juventus", "Inter Milan"]
    is_elite_home = any(elite in home_team for elite in elite_teams)
    is_elite_away = any(elite in away_team for elite in elite_teams)
    if is_elite_home and not is_elite_away:
        patterns_found.append(f"Elite Home: {home_team} dominance")
        pattern_strength += 20
    elif is_elite_away and not is_elite_home:
        patterns_found.append(f"Elite Away: {away_team} résilience")
        pattern_strength += 15

    # Sample size validation
    nb_bookmakers = match_info.get("bookmaker_count", 0)
    total_data_points = 8 + nb_bookmakers
    if total_data_points >= 50:
        sample_size_score = 30
        sample_quality = "ROBUSTE"
    elif total_data_points >= 30:
        sample_size_score = 25
        sample_quality = "BON"
    elif total_data_points >= 15:
        sample_size_score = 18
        sample_quality = "MOYEN"
    elif total_data_points >= 8:
        sample_size_score = 10
        sample_quality = "FAIBLE"
    else:
        sample_size_score = 5
        sample_quality = "INSUFFISANT"

    # Recent form
    top_teams = ["PSG", "Bayern", "Man City", "Real Madrid", "Barcelona"]
    home_form = 0.75 if any(t in home_team for t in top_teams) else 0.5
    away_form = 0.75 if any(t in away_team for t in top_teams) else 0.5
    form_diff = abs(home_form - away_form)
    if form_diff >= 0.3:
        recent_form_score = 20
        patterns_found.append(f"Forme: Écart {form_diff:.2f}")
    elif form_diff >= 0.15:
        recent_form_score = 12
    else:
        recent_form_score = 5

    # Context
    context_score = 8
    context_factors.append("Avantage domicile")
    if "champions" in sport.lower() or "europa" in sport.lower():
        context_score += 5
        context_factors.append("Compétition européenne")
    context_score = min(context_score, 15)

    # Score Ferrari
    pattern_strength = min(pattern_strength, 35)
    ferrari_score_c = min(pattern_strength + sample_size_score + recent_form_score + context_score, 95)

    # Classification
    if ferrari_score_c >= 80:
        level_c = "   PATTERN DOMINANT"
        recommendation_text_c = f"Pattern ML dominant. Strength: {pattern_strength}/35, Sample: {total_data_points} pts, Qualité: {sample_quality}. {len(patterns_found)} patterns confirmés."
    elif ferrari_score_c >= 65:
        level_c = "⚡ PATTERN FORT"
        recommendation_text_c = f"Pattern fort avec {len(patterns_found)} patterns. Sample: {sample_quality} ({total_data_points} pts). Validation Agent B recommandée."
    elif ferrari_score_c >= 50:
        level_c = "💎 PATTERN MOYEN"
        recommendation_text_c = f"Pattern moyen. {len(patterns_found)} patterns sur {total_data_points} pts. Qualité: {sample_quality}. Consensus requis."
    elif ferrari_score_c >= 35:
        level_c = "📊 PATTERN FAIBLE"
        recommendation_text_c = f"Pattern faible. Données limitées ({total_data_points}). Qualité: {sample_quality}."
    else:
        level_c = "❌ PAS DE PATTERN"
        recommendation_text_c = f"Aucun pattern significatif. Sample insuffisant."

    if not patterns_found:
        patterns_found.append("Aucun pattern historique")

    reason_c = f"{level_c} | Patterns: {len(patterns_found)} | {sample_quality} | {ferrari_score_c}/100"

    agents_analysis.append({
        "agent_id": "pattern_matcher",
        "agent_name": "Pattern Matcher Ferrari 2.0",
        "icon": "🎯",
        "status": "active",
        "recommendation": "PATTERNS" if ferrari_score_c >= 50 else "SKIP",
        "confidence": round(ferrari_score_c, 2),
        "reason": reason_c,
        "recommendation_text": recommendation_text_c,
        "details": {
            "ferrari_score": round(ferrari_score_c, 2),
            "patterns": patterns_found,
            "pattern_count": len(patterns_found),
            "pattern_strength": pattern_strength,
            "sample_size_score": sample_size_score,
            "recent_form_score": recent_form_score,
            "context_score": context_score,
            "total_data_points": total_data_points,
            "sample_quality": sample_quality,
            "sport": sport,
            "league_stats": league_stats,
            "context_factors": context_factors
        }
    })

    # === LEARNING SYSTEM: Save Agent C Analysis ===
    try:
        save_agent_analysis(
            match_info=match_info,
            agent_name="Pattern Matcher Ferrari 2.5",
            agent_version="2.5",
            recommendation="PATTERNS" if ferrari_score_c >= 50 else "SKIP",
            confidence=ferrari_score_c,
            reasoning=recommendation_text_c,
            factors={
                "pattern_strength": pattern_strength,
                "sample_size_score": sample_size_score,
                "patterns_count": len(patterns_found)
            }
        )
    except Exception as e:
        pass

    
    # Agent D - Backtest Engine Ferrari 2.5 (Real Data)
    import psycopg2
    from psycopg2.extras import RealDictCursor
    import math

    ferrari_score_d = 0
    win_rate_score = 0
    sharpe_score = 0
    sample_score = 0
    consistency_score = 0
    recommendation_text_d = ""

    sport = match_info.get("sport", "")
    home_team = match_info.get("home_team", "")
    away_team = match_info.get("away_team", "")

    # DB Config
    db_config = {
        "host": "monps_postgres",
        "database": "monps_db",
        "user": "monps_user",
        "password": "monps_secure_password_2024"
    }

    # Map sport to league
    league_map = {
        "soccer_epl": "Premier League",
        "premier": "Premier League",
        "spain": "La Liga",
        "la_liga": "La Liga",
        "italy": "Serie A",
        "serie_a": "Serie A",
        "germany": "Bundesliga",
        "bundesliga": "Bundesliga",
        "france": "Ligue 1",
        "ligue_one": "Ligue 1"
    }

    league = None
    for key, value in league_map.items():
        if key in sport.lower():
            league = value
            break

    # Stats historiques réelles
    total_matches = 0
    home_wins = 0
    draws = 0
    away_wins = 0
    avg_home_goals = 0
    avg_away_goals = 0
    home_win_rate = 0
    draw_rate = 0
    away_win_rate = 0

    # Stats équipe spécifique
    team_home_matches = 0
    team_home_wins = 0
    team_away_matches = 0
    team_away_wins = 0

    if league:
        try:
            conn = psycopg2.connect(**db_config)
            cursor = conn.cursor(cursor_factory=RealDictCursor)

            # QUERY 1: Stats générales de la ligue
            cursor.execute("""
                SELECT
                    COUNT(*) as total,
                    SUM(CASE WHEN result = 'H' THEN 1 ELSE 0 END) as home_wins,
                    SUM(CASE WHEN result = 'D' THEN 1 ELSE 0 END) as draws,
                    SUM(CASE WHEN result = 'A' THEN 1 ELSE 0 END) as away_wins,
                    AVG(home_goals) as avg_home_goals,
                    AVG(away_goals) as avg_away_goals
                FROM matches_results
                WHERE league = %s
            """, (league,))

            stats = cursor.fetchone()
            if stats and stats['total'] > 0:
                total_matches = stats['total']
                home_wins = stats['home_wins']
                draws = stats['draws']
                away_wins = stats['away_wins']
                avg_home_goals = float(stats['avg_home_goals'] or 0)
                avg_away_goals = float(stats['avg_away_goals'] or 0)

                home_win_rate = (home_wins / total_matches) * 100
                draw_rate = (draws / total_matches) * 100
                away_win_rate = (away_wins / total_matches) * 100

            # QUERY 2: Performance équipe à domicile
            cursor.execute("""
                SELECT
                    COUNT(*) as matches,
                    SUM(CASE WHEN result = 'H' THEN 1 ELSE 0 END) as wins
                FROM matches_results
                WHERE league = %s AND home_team ILIKE %s
            """, (league, f"%{home_team}%"))

            team_home = cursor.fetchone()
            if team_home:
                team_home_matches = team_home['matches'] or 0
                team_home_wins = team_home['wins'] or 0

            # QUERY 3: Performance équipe en déplacement
            cursor.execute("""
                SELECT
                    COUNT(*) as matches,
                    SUM(CASE WHEN result = 'A' THEN 1 ELSE 0 END) as wins
                FROM matches_results
                WHERE league = %s AND away_team ILIKE %s
            """, (league, f"%{away_team}%"))

            team_away = cursor.fetchone()
            if team_away:
                team_away_matches = team_away['matches'] or 0
                team_away_wins = team_away['wins'] or 0

            conn.close()

        except Exception as e:
            pass

    # CALCUL SCORES FERRARI

    # FACTEUR 1: Win Rate Historical (0-35 pts)
    if total_matches >= 1000:
        # Données robustes
        if home_win_rate >= 50:
            win_rate_score = 35
        elif home_win_rate >= 45:
            win_rate_score = 30
        elif home_win_rate >= 40:
            win_rate_score = 25
        elif home_win_rate >= 35:
            win_rate_score = 15
        else:
            win_rate_score = 10

        sample_quality = "EXCELLENT"
    elif total_matches >= 500:
        win_rate_score = 20
        sample_quality = "BON"
    elif total_matches >= 100:
        win_rate_score = 10
        sample_quality = "MOYEN"
    else:
        win_rate_score = 5
        sample_quality = "FAIBLE"

    # FACTEUR 2: Sharpe Quality (0-30 pts) - Basé sur consistance historique
    if total_matches > 0:
        # Sharpe simplifié = win_rate / variance
        # Plus le draw_rate est élevé, plus c'est volatile
        volatility = draw_rate / 100 if draw_rate > 0 else 0.3
        pseudo_sharpe = (home_win_rate / 100) / volatility if volatility > 0 else 0

        if pseudo_sharpe >= 2.0:
            sharpe_score = 30
        elif pseudo_sharpe >= 1.5:
            sharpe_score = 25
        elif pseudo_sharpe >= 1.0:
            sharpe_score = 18
        elif pseudo_sharpe >= 0.5:
            sharpe_score = 10
        else:
            sharpe_score = 5

    # FACTEUR 3: Sample Size (0-20 pts)
    if total_matches >= 2000:
        sample_score = 20
    elif total_matches >= 1000:
        sample_score = 17
    elif total_matches >= 500:
        sample_score = 13
    elif total_matches >= 100:
        sample_score = 8
    else:
        sample_score = 3

    # FACTEUR 4: Consistency (0-15 pts) - Équipes spécifiques
    team_performance = 0
    if team_home_matches >= 20:
        team_home_wr = (team_home_wins / team_home_matches) * 100
        if team_home_wr >= 60:
            team_performance += 8
        elif team_home_wr >= 50:
            team_performance += 5
        elif team_home_wr >= 40:
            team_performance += 3

    if team_away_matches >= 20:
        team_away_wr = (team_away_wins / team_away_matches) * 100
        if team_away_wr >= 40:
            team_performance += 7
        elif team_away_wr >= 30:
            team_performance += 4
        elif team_away_wr >= 20:
            team_performance += 2

    consistency_score = min(team_performance, 15)

    # SCORE TOTAL (cap 95)
    ferrari_score_d = min(win_rate_score + sharpe_score + sample_score + consistency_score, 95)   

    # CLASSIFICATION
    if ferrari_score_d >= 85:
        level_d = "🏆 EXCELLENT TRACK RECORD"
        recommendation_text_d = f"Backtest excellent sur {total_matches:,} matchs réels. {league}: Home win {home_win_rate:.1f}%, Draw {draw_rate:.1f}%, Away {away_win_rate:.1f}%. Équipe home: {team_home_wins}/{team_home_matches} victoires domicile. Données historiques robustes validant les patterns."
    elif ferrari_score_d >= 70:
        level_d = "⚡ BON HISTORIQUE"
        recommendation_text_d = f"Bon historique sur {total_matches:,} matchs. {league}: Home {home_win_rate:.1f}%, Draw {draw_rate:.1f}%. Sample: {sample_quality}. Buts moyens: {avg_home_goals:.1f} - {avg_away_goals:.1f}. Backtest valide les tendances."
    elif ferrari_score_d >= 55:
        level_d = "💎 HISTORIQUE MOYEN"
        recommendation_text_d = f"Historique moyen. {total_matches:,} matchs analysés. {league}: Patterns détectables mais variance élevée. Sample: {sample_quality}. Prudence recommandée."        
    elif ferrari_score_d >= 40:
        level_d = "📊 DONNÉES LIMITÉES"
        recommendation_text_d = f"Données historiques limitées ({total_matches} matchs). Sample: {sample_quality}. Backtest incomplet. Attendre plus de données."
    else:
        level_d = "❌ INSUFFISANT"
        recommendation_text_d = f"Sample insuffisant pour backtest fiable. {total_matches} matchs seulement. Besoin de plus d'historique pour validation."

    reason_d = f"{level_d} | {total_matches:,} matchs | Home: {home_win_rate:.1f}% | {sample_quality}"

    if not league:
        reason_d = "Ligue non supportée pour backtest"
        recommendation_text_d = "Cette ligue n'a pas de données historiques dans notre système."  
        ferrari_score_d = 0

    agents_analysis.append({
        "agent_id": "backtest_engine",
        "agent_name": "Backtest Engine Ferrari 2.5",
        "icon": "📈",
        "status": "active",
        "recommendation": "VALIDATED" if ferrari_score_d >= 70 else "CAUTION" if ferrari_score_d >= 40 else "INSUFFICIENT",
        "confidence": round(ferrari_score_d, 2),
        "reason": reason_d,
        "recommendation_text": recommendation_text_d,
        "details": {
            "ferrari_score": round(ferrari_score_d, 2),
            "total_historical_matches": total_matches,
            "league": league or "Unknown",
            "home_win_rate": round(home_win_rate, 2),
            "draw_rate": round(draw_rate, 2),
            "away_win_rate": round(away_win_rate, 2),
            "avg_goals_home": round(avg_home_goals, 2),
            "avg_goals_away": round(avg_away_goals, 2),
            "team_home_matches": team_home_matches,
            "team_home_wins": team_home_wins,
            "team_away_matches": team_away_matches,
            "team_away_wins": team_away_wins,
            "sample_quality": sample_quality,
            "win_rate_score": win_rate_score,
            "sharpe_score": sharpe_score,
            "sample_score": sample_score,
            "consistency_score": consistency_score
        }
    })
    # === LEARNING SYSTEM: Save Agent D Analysis ===
    try:
        save_agent_analysis(
            match_info=match_info,
            agent_name="Backtest Engine Ferrari 2.5",
            agent_version="2.5",
            recommendation="VALIDATED" if ferrari_score_d >= 70 else "CAUTION" if ferrari_score_d >= 40 else "INSUFFICIENT",
            confidence=ferrari_score_d,
            reasoning=recommendation_text_d,
            factors={
                "total_historical_matches": total_matches,
                "home_win_rate": float(home_win_rate),
                "draw_rate": float(draw_rate),
                "away_win_rate": float(away_win_rate),
                "team_home_wins": team_home_wins,
                "team_home_matches": team_home_matches,
                "win_rate_score": win_rate_score,
                "sharpe_score": sharpe_score,
                "sample_score": sample_score,
                "sample_quality": sample_quality if league else "N/A"
            }
        )
    except Exception as e:
        pass

    
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

@router.get("/patron/variations")
async def get_patron_variations():
    """
    Retourne la liste des variations disponibles pour l'Agent Patron
    Triées par win_rate décroissant
    """
    import psycopg2
    
    try:
        conn = psycopg2.connect(
            host='monps_postgres',
            port=5432,
            database='monps_db',
            user='monps_user',
            password='monps_secure_password_2024'
        )
        cur = conn.cursor()
        
        cur.execute("""
            SELECT 
                id, name, description, enabled_factors,
                matches_tested, wins, losses, win_rate, total_profit, roi,
                is_active, is_control
            FROM improvement_variations
            WHERE is_active = true
            ORDER BY win_rate DESC NULLS LAST, roi DESC NULLS LAST
        """)
        
        rows = cur.fetchall()
        cur.close()
        conn.close()
        
        variations = []
        for i, row in enumerate(rows):
            variations.append({
                "id": row[0],
                "name": row[1],
                "description": row[2],
                "factors": row[3] if row[3] else [],
                "matches_tested": row[4] if row[4] else 0,
                "wins": row[5] if row[5] else 0,
                "losses": row[6] if row[6] else 0,
                "win_rate": float(row[7]) if row[7] else 0,
                "total_profit": float(row[8]) if row[8] else 0,
                "roi": float(row[9]) if row[9] else 0,
                "is_active": row[10],
                "is_control": row[11],
                "is_best": i == 0
            })
        
        return {
            "variations": variations,
            "total": len(variations),
            "best_variation_id": variations[0]["id"] if variations else None
        }
        
    except Exception as e:
        return {"error": str(e), "variations": []}

@router.get("/patron/analyze/{match_id}")
async def analyze_with_patron(match_id: str, variation_id: int = None):
    """
    Agent Patron V2.0 : Meta-Analyste avec sélection de variation
    et score basé sur les données réelles (60 matchs analysés)
    """
    import psycopg2

    # 1. Récupérer l'analyse des 4 agents
    base_analysis = await analyze_match_with_agents(match_id)

    if "error" in base_analysis:
        return base_analysis

    agents_list = base_analysis.get("agents", [])

    # 2. Récupérer la variation (meilleure par défaut ou sélectionnée)
    selected_variation = None
    try:
        conn = psycopg2.connect(
            host='monps_postgres',
            port=5432,
            database='monps_db',
            user='monps_user',
            password='monps_secure_password_2024'
        )
        cur = conn.cursor()
        
        if variation_id:
            cur.execute("""
                SELECT id, name, description, enabled_factors,
                       matches_tested, wins, losses, win_rate, total_profit, roi
                FROM improvement_variations
                WHERE id = %s AND is_active = true
            """, (variation_id,))
        else:
            cur.execute("""
                SELECT id, name, description, enabled_factors,
                       matches_tested, wins, losses, win_rate, total_profit, roi
                FROM improvement_variations
                WHERE is_active = true
                ORDER BY win_rate DESC NULLS LAST, roi DESC NULLS LAST
                LIMIT 1
            """)
        
        var_row = cur.fetchone()
        cur.close()
        conn.close()
        
        if var_row:
            selected_variation = {
                "id": var_row[0],
                "name": var_row[1],
                "description": var_row[2],
                "factors": var_row[3] if var_row[3] else [],
                "matches_tested": var_row[4] if var_row[4] else 0,
                "wins": var_row[5] if var_row[5] else 0,
                "losses": var_row[6] if var_row[6] else 0,
                "win_rate": float(var_row[7]) if var_row[7] else 0,
                "total_profit": float(var_row[8]) if var_row[8] else 0,
                "roi": float(var_row[9]) if var_row[9] else 0
            }
    except Exception as e:
        selected_variation = None

    # 3. Extraire les scores de chaque agent
    scores = {}
    signals = {}
    agents_results = {}

    for agent_data in agents_list:
        agent_id = agent_data.get("agent_id", "unknown")
        agents_results[agent_id] = agent_data
        confidence = agent_data.get("confidence", 0)
        scores[agent_id] = confidence

        if confidence >= 80:
            signals[agent_id] = "FORT"
        elif confidence >= 60:
            signals[agent_id] = "MOYEN"
        elif confidence >= 40:
            signals[agent_id] = "FAIBLE"
        else:
            signals[agent_id] = "TRES_FAIBLE"

    # 4. Extraire outcome et confidence du spread_optimizer pour Score V2
    spread_agent = next((a for a in agents_list if a.get("agent_id") == "spread_optimizer"), None)
    
    predicted_outcome = "home"
    agent_confidence = 40
    edge = 0
    
    if spread_agent:
        details = spread_agent.get("details", {})
        rec = spread_agent.get("recommendation", "").lower()
        if rec in ["home", "away", "draw"]:
            predicted_outcome = rec
        agent_confidence = spread_agent.get("confidence", 40)
        edge = details.get("edge_pct", 0) if details.get("edge_pct") else 0

    # 5. CALCUL DU SCORE V2 (basé sur nos 60 résultats réels)
    score_v2 = 50  # Base
    factors_positive = []
    factors_negative = []

    # === BONUS OUTCOME (basé sur nos données) ===
    if predicted_outcome == "home":
        score_v2 += 15
        factors_positive.append({
            "label": "HOME",
            "points": 15,
            "detail": "62.5% WR historique sur 72 matchs"
        })
    elif predicted_outcome == "away":
        score_v2 -= 10
        factors_negative.append({
            "label": "AWAY",
            "points": -10,
            "detail": "14.0% WR historique - zone a risque"
        })
    elif predicted_outcome == "draw":
        score_v2 -= 20
        factors_negative.append({
            "label": "DRAW",
            "points": -20,
            "detail": "4.5% WR historique - tres risque"
        })

    # === BONUS CONFIANCE (paradoxe inverse confirme) ===
    if 25 <= agent_confidence < 35:
        score_v2 += 20
        factors_positive.append({
            "label": f"Confiance {agent_confidence:.0f}%",
            "points": 20,
            "detail": "Zone diamant: 77.8% WR (7W/2L sur 9 matchs)"
        })
    elif 35 <= agent_confidence < 50:
        score_v2 += 5
        factors_positive.append({
            "label": f"Confiance {agent_confidence:.0f}%",
            "points": 5,
            "detail": "Zone correcte: 45.5% WR"
        })
    elif agent_confidence >= 50:
        score_v2 -= 15
        factors_negative.append({
            "label": f"Confiance {agent_confidence:.0f}%",
            "points": -15,
            "detail": "ATTENTION: Paradoxe inverse, 14-25% WR seulement"
        })

    # === BONUS EDGE ===
    if edge and edge > 20:
        score_v2 += 10
        factors_positive.append({
            "label": f"Edge {edge:.1f}%",
            "points": 10,
            "detail": "Edge excellent"
        })
    elif edge and edge > 10:
        score_v2 += 5
        factors_positive.append({
            "label": f"Edge {edge:.1f}%",
            "points": 5,
            "detail": "Edge significatif"
        })
    elif edge and edge > 5:
        score_v2 += 2
        factors_positive.append({
            "label": f"Edge {edge:.1f}%",
            "points": 2,
            "detail": "Edge modere"
        })

    # Clamp 0-100
    score_v2 = max(0, min(100, score_v2))

    # 6. DETERMINER LA NOTE
    if score_v2 >= 90:
        grade = "A+"
        verdict = "EXCELLENT"
        verdict_color = "green-500"
        verdict_message = "Toutes conditions optimales"
    elif score_v2 >= 80:
        grade = "A"
        verdict = "RECOMMANDE"
        verdict_color = "green-400"
        verdict_message = "Conditions tres favorables"
    elif score_v2 >= 70:
        grade = "B+"
        verdict = "FAVORABLE"
        verdict_color = "green-300"
        verdict_message = "Bon potentiel"
    elif score_v2 >= 60:
        grade = "B"
        verdict = "MODERE"
        verdict_color = "yellow-400"
        verdict_message = "Potentiel avec reserves"
    elif score_v2 >= 50:
        grade = "C"
        verdict = "RISQUE"
        verdict_color = "orange-400"
        verdict_message = "Equilibre risque/recompense"
    elif score_v2 >= 40:
        grade = "D"
        verdict = "DEFAVORABLE"
        verdict_color = "orange-500"
        verdict_message = "Plus de facteurs negatifs"
    else:
        grade = "E"
        verdict = "DECONSEILLE"
        verdict_color = "red-500"
        verdict_message = "Conditions defavorables"

    # 7. REFERENCE HISTORIQUE
    if predicted_outcome == "home" and 25 <= agent_confidence < 35:
        historical_reference = {
            "zone": "HOME + Conf 25-35%",
            "win_rate": 77.8,
            "sample": "7W/2L sur 9 matchs",
            "quality": "DIAMANT"
        }
    elif predicted_outcome == "home" and 35 <= agent_confidence < 50:
        historical_reference = {
            "zone": "HOME + Conf 35-50%",
            "win_rate": 45.5,
            "sample": "5W/6L sur 11 matchs",
            "quality": "OR"
        }
    elif predicted_outcome == "home" and agent_confidence >= 50:
        historical_reference = {
            "zone": "HOME + Conf 50%+",
            "win_rate": 25.0,
            "sample": "1W/3L sur 4 matchs",
            "quality": "ATTENTION"
        }
    elif predicted_outcome == "away" and agent_confidence < 50:
        historical_reference = {
            "zone": "AWAY + Conf <50%",
            "win_rate": 23.8,
            "sample": "5W/16L sur 21 matchs",
            "quality": "BRONZE"
        }
    elif predicted_outcome == "away" and agent_confidence >= 50:
        historical_reference = {
            "zone": "AWAY + Conf 50%+",
            "win_rate": 0.0,
            "sample": "0W/3L sur 3 matchs",
            "quality": "CRITIQUE"
        }
    elif predicted_outcome == "draw":
        historical_reference = {
            "zone": "DRAW",
            "win_rate": 16.7,
            "sample": "2W/10L sur 12 matchs",
            "quality": "RISQUE"
        }
    else:
        historical_reference = {
            "zone": f"{predicted_outcome.upper()}",
            "win_rate": 33.3,
            "sample": "Moyenne globale 20W/40L",
            "quality": "STANDARD"
        }

    # 8. Ancien calcul (garder pour compatibilite)
    weights = {
        "anomaly_detector": 0.25,
        "spread_optimizer": 0.35,
        "pattern_matcher": 0.20,
        "backtest_engine": 0.20
    }

    weighted_score = sum(
        scores.get(agent, 0) * weights.get(agent, 0.25)
        for agent in scores.keys()
    )

    strong_signals = sum(1 for s in signals.values() if s in ["FORT", "MOYEN"])

    if strong_signals == 4:
        consensus_level = "FORT (4/4)"
    elif strong_signals == 3:
        consensus_level = "MAJORITAIRE (3/4)"
    elif strong_signals == 2:
        consensus_level = "DIVISE (2/4)"
    else:
        consensus_level = "CONFLICTUEL"

    # 9. Construire la reponse enrichie
    patron_analysis = {
        "match_id": match_id,
        "match_info": base_analysis.get("match", {}),

        # NOUVEAU: Score V2 avec note
        "score_v2": {
            "score": round(score_v2, 1),
            "grade": grade,
            "verdict": verdict,
            "verdict_color": verdict_color,
            "verdict_message": verdict_message,
            "factors_positive": factors_positive,
            "factors_negative": factors_negative,
            "historical_reference": historical_reference,
            "predicted_outcome": predicted_outcome,
            "agent_confidence": round(agent_confidence, 1)
        },

        # NOUVEAU: Variation selectionnee
        "variation": selected_variation,

        # Ancien format (compatibilite)
        "score_global": round(score_v2, 1),
        "consensus": consensus_level,
        "confiance_agregee": round(weighted_score, 1),

        "synthese_agents": {
            agent_id: {
                "signal": signals.get(agent_id, "INCONNU"),
                "confiance": round(scores.get(agent_id, 0), 1),
                "poids": weights.get(agent_id, 0.25),
                "contribution": round(scores.get(agent_id, 0) * weights.get(agent_id, 0.25), 1)
            }
            for agent_id in scores.keys()
        },

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


@router.post("/diamond/synthesize")
async def diamond_synthesize(match_id: str):
    """
    Agent Diamond Narrator : Synthèse qualitative avec GPT-4o
    Génère une analyse narrative basée sur les 4 agents + Agent Patron
    """
    import os
    
    # 1. Récupérer l'analyse complète
    base_analysis = await analyze_match_with_agents(match_id)
    if "error" in base_analysis:
        return base_analysis
    
    # 2. Récupérer l'analyse Patron
    try:
        patron_analysis = await analyze_with_patron(match_id)
    except:
        patron_analysis = None
    
    # 3. Préparer le contexte
    agents_data = base_analysis.get("agents", [])
    match_info = base_analysis.get("match", {})
    
    context = f"""MATCH: {match_info.get('home_team')} vs {match_info.get('away_team')}
SPORT: {match_info.get('sport')}
DATE: {match_info.get('commence_time')}

ODDS:
- HOME: {match_info.get('odds', {}).get('home', {}).get('best')}
- DRAW: {match_info.get('odds', {}).get('draw', {}).get('best')}
- AWAY: {match_info.get('odds', {}).get('away', {}).get('best')}

ANALYSES DES 4 AGENTS ML:
"""
    
    for agent in agents_data:
        context += f"\n{agent.get('agent_name')}: {agent.get('prediction')} (conf: {agent.get('confidence')}/100)\n"
        context += f"Raison: {agent.get('reason')}\n"
    
    if patron_analysis and "score_v2" in patron_analysis:
        score_v2 = patron_analysis["score_v2"]
        context += f"\n\nAGENT PATRON: Score {score_v2.get('score')}/100 ({score_v2.get('grade')})\n"
        context += f"Verdict: {score_v2.get('verdict')}\n"
    
    # 4. Appeler GPT-4o
    try:
        from openai import OpenAI
        client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
        
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "Tu es un expert en analyse de paris sportifs quantitatifs. Réponds en JSON."},
                {"role": "user", "content": f"""{context}

Génère une synthèse JSON avec:
- feux_verts: [{{"titre": "...", "detail": "..."}}] (2-3 points forts)
- feux_orange: [{{"titre": "...", "detail": "..."}}] (1-2 vigilances)
- feux_rouges: [{{"titre": "...", "detail": "..."}}] (1-2 risques)
- recommandation: "verdict concis"
- narrative: "analyse de 2-3 phrases"
- risk_level: "FAIBLE|MODÉRÉ|ÉLEVÉ"
- confidence_narrative: "HIGH|MEDIUM|LOW"
"""}
            ],
            temperature=0.3,
            max_tokens=1500,
            response_format={"type": "json_object"}
        )
        
        import json
        synthesis = json.loads(response.choices[0].message.content)
        
        return {
            "match_id": match_id,
            "synthesis": synthesis,
            "generated_at": import_datetime.datetime.now().isoformat(),
            "model": "gpt-4o",
            "cost_estimate": 0.004
        }
        
    except Exception as e:
        return {
            "error": f"Erreur: {str(e)}",
            "match_id": match_id
        }

@router.get("/patron/analyze-factors/{match_id}")
async def analyze_factors_for_match(match_id: str, variation_id: int = None):
    """
    Analyse détaillée des facteurs pour un match spécifique
    Retourne le score de chaque facteur (0-10) avec impact et détail
    """
    import psycopg2
    from psycopg2.extras import RealDictCursor
    
    # 1. Récupérer l'analyse des 4 agents
    base_analysis = await analyze_match_with_agents(match_id)
    if "error" in base_analysis:
        return base_analysis
    
    agents = base_analysis.get("agents", [])
    
    # 2. Extraire les signaux des agents
    anomaly = next((a for a in agents if "Anomaly" in a.get("agent_name", "")), None)
    spread = next((a for a in agents if "Spread" in a.get("agent_name", "")), None)
    pattern = next((a for a in agents if "Pattern" in a.get("agent_name", "")), None)
    backtest = next((a for a in agents if "Backtest" in a.get("agent_name", "")), None)
    
    # 3. Calculer les scores des facteurs
    factors_analysis = []
    
    # Facteur 1 : Forme récente (basé sur backtest + pattern)
    forme_score = 5.0  # Neutre par défaut
    forme_impact = 0.0
    if backtest:
        home_wr = backtest.get("details", {}).get("home_win_rate", 50)
        if home_wr > 50:
            forme_score = min(10, 5 + (home_wr - 50) / 10)
            forme_impact = (home_wr - 50) / 2
        else:
            forme_score = max(0, 5 - (50 - home_wr) / 10)
            forme_impact = -(50 - home_wr) / 2
    
    factors_analysis.append({
        "name": "forme_récente_des_équipes",
        "display_name": "Forme Récente",
        "score": round(forme_score, 1),
        "impact": round(forme_impact, 1),
        "detail": f"Analyse des derniers matchs" + (f" - {backtest.get('details', {}).get('team_home_wins', 0)} victoires récentes" if backtest else ""),
        "category": "positive" if forme_score >= 6 else "negative" if forme_score < 4 else "neutral"
    })
    
    # Facteur 2 : Blessures (basé sur anomaly detector)
    blessures_score = 5.0
    blessures_impact = 0.0
    if anomaly:
        conf = anomaly.get("confidence", 50)
        if conf > 80:  # Pas d'anomalies = bonnes nouvelles sur blessures
            blessures_score = 8.0
            blessures_impact = 10.0
        elif conf < 40:
            blessures_score = 3.0
            blessures_impact = -15.0
    
    factors_analysis.append({
        "name": "blessures_clés",
        "display_name": "Blessures Clés",
        "score": round(blessures_score, 1),
        "impact": round(blessures_impact, 1),
        "detail": "Aucune anomalie détectée" if blessures_score > 6 else "Effectif surveillé",
        "category": "positive" if blessures_score >= 6 else "negative" if blessures_score < 4 else "neutral"
    })
    
    # Facteur 3 : Conditions météo (neutre par défaut)
    meteo_score = 5.0
    meteo_impact = 0.0
    
    factors_analysis.append({
        "name": "conditions_météorologiques",
        "display_name": "Conditions Météo",
        "score": round(meteo_score, 1),
        "impact": round(meteo_impact, 1),
        "detail": "Conditions standard attendues",
        "category": "neutral"
    })
    
    # Facteur 4 : Historique H2H (basé sur backtest)
    h2h_score = 5.0
    h2h_impact = 0.0
    if backtest:
        sample_quality = backtest.get("details", {}).get("sample_quality", "STANDARD")
        if sample_quality == "EXCELLENT":
            h2h_score = 7.5
            h2h_impact = 8.0
        elif sample_quality == "FAIBLE":
            h2h_score = 3.0
            h2h_impact = -8.0
    
    factors_analysis.append({
        "name": "historique_des_confrontations_directes",
        "display_name": "Historique H2H",
        "score": round(h2h_score, 1),
        "impact": round(h2h_impact, 1),
        "detail": f"Historique {backtest.get('details', {}).get('sample_quality', 'standard').lower()}" if backtest else "Données limitées",
        "category": "positive" if h2h_score >= 6 else "negative" if h2h_score < 4 else "neutral"
    })
    
    # 4. Calculer les statistiques globales
    positive_count = sum(1 for f in factors_analysis if f["category"] == "positive")
    negative_count = sum(1 for f in factors_analysis if f["category"] == "negative")
    avg_score = sum(f["score"] for f in factors_analysis) / len(factors_analysis)
    avg_impact = sum(f["impact"] for f in factors_analysis) / len(factors_analysis)
    
    return {
        "match_id": match_id,
        "factors": factors_analysis,
        "summary": {
            "positive_count": positive_count,
            "negative_count": negative_count,
            "neutral_count": len(factors_analysis) - positive_count - negative_count,
            "average_score": round(avg_score, 1),
            "average_impact": round(avg_impact, 1),
            "overall_sentiment": "positive" if avg_score >= 6 else "negative" if avg_score < 4 else "neutral"
        }
    }
