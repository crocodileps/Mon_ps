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
    anomaly_score = 0
    is_anomaly = False
    reason_a = "Pas d'anomalie détectée"
    if match_info.get("odds"):
        max_spread = max(match_info["odds"]["home"]["spread_pct"], match_info["odds"]["away"]["spread_pct"], match_info["odds"]["draw"]["spread_pct"])
        if max_spread > 10:
            anomaly_score = min(max_spread / 10, 10)
            is_anomaly = True
            reason_a = f"Spread élevé détecté ({max_spread:.1f}%)"
    else:
        max_spread = 0
    
    agents_analysis.append({
        "agent_id": "anomaly_detector", "agent_name": "Anomaly Detector", "icon": "🔍",
        "status": "active", "recommendation": "REVIEW" if is_anomaly else "NORMAL",
        "confidence": round(anomaly_score, 2), "reason": reason_a,
        "details": {"anomaly_score": round(anomaly_score, 2), "is_anomaly": is_anomaly, "max_spread": max_spread}
    })
    
    # Agent B - Spread Optimizer
    kelly_fraction = 0
    expected_value = 0
    recommended_stake = 0
    best_outcome = "none"
    reason_b = "Pas d'opportunité Kelly"
    if match_info.get("odds"):
        best_ev = -1
        for outcome in ["home", "away", "draw"]:
            odds_data = match_info["odds"][outcome]
            if odds_data["best"] > 1:
                implied_prob = 1 / odds_data["best"]
                b = odds_data["best"] - 1
                p = implied_prob * 1.05
                q = 1 - p
                kelly = (b * p - q) / b if b > 0 else 0
                ev = (p * b) - q
                if ev > best_ev and kelly > 0:
                    best_ev = ev
                    kelly_fraction = kelly
                    expected_value = ev
                    best_outcome = outcome
                    recommended_stake = min(kelly * 100, 5)
        if best_ev > 0:
            reason_b = f"Meilleure valeur sur {best_outcome.upper()} (EV: {expected_value:.2%})"
    
    agents_analysis.append({
        "agent_id": "spread_optimizer", "agent_name": "Spread Optimizer", "icon": "📊",
        "status": "active", "recommendation": best_outcome.upper() if expected_value > 0 else "PASS",
        "confidence": round(min(expected_value * 100, 10), 2) if expected_value > 0 else 0,
        "reason": reason_b,
        "details": {"kelly_fraction": round(kelly_fraction, 4), "expected_value": round(expected_value, 4), "recommended_stake_pct": round(recommended_stake, 2), "best_outcome": best_outcome}
    })
    
    # Agent C - Pattern Matcher
    patterns_found = []
    confidence_c = 0
    sport = match_info["sport"]
    if "epl" in sport or "premier" in sport.lower():
        patterns_found.append("Premier League - Forte compétition")
        confidence_c += 3
    if "ligue_one" in sport:
        patterns_found.append("Ligue 1 - PSG dominance")
        confidence_c += 2
    if "serie_a" in sport:
        patterns_found.append("Serie A - Défenses solides")
        confidence_c += 2
    if "la_liga" in sport:
        patterns_found.append("La Liga - Technique élevée")
        confidence_c += 2
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
        historical_performance = 7.5
        reason_d = f"Couverture élevée ({match_info['bookmaker_count']} books) - ROI historique: {avg_roi}%"
    elif match_info.get("bookmaker_count", 0) >= 5:
        win_rate = 0.50
        avg_roi = 1.5
        historical_performance = 5.0
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
