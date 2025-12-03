"""
🔗 COMBOS 2.0 AUTOMATISÉ
- Auto-save des suggestions
- Résolution automatique
- Analyse IA (GPT-4o)
- Kelly Combo optimal
"""
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime, timedelta
import os
import json
import hashlib
import httpx
import math

# Reality Check Integration
try:
    from agents.reality_check import RealityChecker
    _reality_checker = RealityChecker()
    REALITY_CHECK_ENABLED = True
except ImportError:
    _reality_checker = None
    REALITY_CHECK_ENABLED = False
# Reality Check Helper
from api.services.reality_check_helper import get_match_warnings, adjust_prediction, get_team_tier, enrich_match_list, enrich_api_response




# ═══════════════════════════════════════════════════════════════════════════════
# REALITY CHECK INTEGRATION FOR COMBOS
# ═══════════════════════════════════════════════════════════════════════════════

def _check_combo_reality(matches: list) -> dict:
    """
    Vérifie la convergence Reality Check pour un combiné.
    Retourne un score global et des warnings agrégés.
    """
    try:
        from api.services.reality_check_helper import analyze_match, get_match_warnings
        
        total_score = 0
        all_warnings = []
        divergences = 0
        match_details = []
        
        for match in matches:
            home = match.get('home_team', match.get('home', ''))
            away = match.get('away_team', match.get('away', ''))
            
            if home and away:
                reality = analyze_match(home, away)
                if reality:
                    total_score += reality.get('reality_score', 50)
                    warnings = reality.get('warnings', [])
                    all_warnings.extend(warnings)
                    
                    if reality.get('convergence') in ['divergence', 'strong_divergence']:
                        divergences += 1
                    
                    match_details.append({
                        'match': f"{home} vs {away}",
                        'reality_score': reality.get('reality_score', 50),
                        'convergence': reality.get('convergence', 'unknown'),
                        'warnings_count': len(warnings)
                    })
                else:
                    total_score += 50  # Score neutre
                    match_details.append({
                        'match': f"{home} vs {away}",
                        'reality_score': 50,
                        'convergence': 'unknown',
                        'warnings_count': 0
                    })
        
        num_matches = len(matches) if matches else 1
        avg_score = total_score / num_matches
        
        # Recommandation combiné
        if divergences >= 2:
            combo_recommendation = "🚨 ÉVITER - Plusieurs divergences détectées"
        elif divergences == 1:
            combo_recommendation = "⚠️ PRUDENCE - Une divergence dans le combiné"
        elif avg_score >= 60:
            combo_recommendation = "✅ COHÉRENT - Reality Check favorable"
        else:
            combo_recommendation = "⚠️ NEUTRE - Vérifier les warnings"
        
        return {
            'enabled': True,
            'combo_reality_score': round(avg_score, 1),
            'divergences_count': divergences,
            'total_warnings': len(all_warnings),
            'recommendation': combo_recommendation,
            'match_details': match_details,
            'top_warnings': all_warnings[:5]  # Top 5 warnings
        }
        
    except Exception as e:
        return {'enabled': False, 'error': str(e)}


router = APIRouter(prefix="/api/combos", tags=["Combinés Intelligents V2"])

DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'monps_postgres'),
    'port': 5432,
    'database': 'monps_db',
    'user': 'monps_user',
    'password': os.getenv('DB_PASSWORD', 'monps_secure_password_2024')
}

OPENAI_API_KEY = os.getenv('OPENAI_API_KEY', '')

# ============================================================
# HELPERS
# ============================================================

def get_db_connection():
    return psycopg2.connect(**DB_CONFIG)


def generate_combo_hash(selections: list) -> str:
    """Génère un hash unique pour éviter les doublons"""
    sorted_sels = sorted([f"{s.get('match', '')}-{s.get('market', '')}" for s in selections])
    return hashlib.md5(json.dumps(sorted_sels).encode()).hexdigest()[:16]


def calculate_kelly(probability: float, odds: float, fraction: float = 0.25) -> float:
    """
    Calcule le Kelly Criterion pour un combo
    fraction = Kelly fractionné (0.25 = quart Kelly recommandé)
    """
    if odds <= 1 or probability <= 0:
        return 0
    
    q = 1 - probability
    b = odds - 1
    
    kelly = (probability * b - q) / b
    kelly = max(0, kelly) * fraction * 100  # En pourcentage
    
    return min(kelly, 10)  # Cap à 10% max


def calculate_ev(probability: float, odds: float) -> float:
    """Expected Value"""
    return probability * odds


# ============================================================
# STATS DYNAMIQUES
# ============================================================

@router.get("/stats-dynamic")
async def get_dynamic_market_stats():
    """Stats des marchés calculées dynamiquement depuis la DB"""
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    cur.execute("""
        SELECT 
            market_type,
            COUNT(*) as total_picks,
            COUNT(*) FILTER (WHERE is_winner = true) as wins,
            COUNT(*) FILTER (WHERE is_winner = false) as losses,
            ROUND(COUNT(*) FILTER (WHERE is_winner)::numeric / NULLIF(COUNT(*), 0) * 100, 1) as win_rate,
            ROUND(AVG(odds_taken)::numeric, 2) as avg_odds,
            ROUND(SUM(profit_loss)::numeric, 2) as total_profit,
            ROUND(AVG(clv_percentage)::numeric, 2) as avg_clv
        FROM tracking_clv_picks
        WHERE is_resolved = true AND market_type IS NOT NULL
        GROUP BY market_type
        HAVING COUNT(*) >= 5
        ORDER BY total_profit DESC
    """)
    
    markets = cur.fetchall()
    
    for m in markets:
        profit = float(m['total_profit'] or 0)
        wr = float(m['win_rate'] or 0)
        
        if profit > 10 and wr > 70:
            m['tier'] = 'S'
            m['status'] = '🏆 ELITE'
        elif profit > 5:
            m['tier'] = 'S'
            m['status'] = '🥇 TOP'
        elif profit > 0:
            m['tier'] = 'A'
            m['status'] = '✅ RENTABLE'
        elif profit > -5:
            m['tier'] = 'B'
            m['status'] = '⚠️ NEUTRE'
        else:
            m['tier'] = 'C'
            m['status'] = '❌ À ÉVITER'
    
    cur.close()
    conn.close()
    
    return {
        'count': len(markets),
        'markets': markets,
        'source': 'DYNAMIC',
        'updated_at': datetime.now().isoformat()
    }


# ============================================================
# SUGGESTIONS AVEC AUTO-SAVE
# ============================================================

@router.get("/suggestions")
async def get_combo_suggestions(
    limit: int = 20,
    auto_save: bool = True,
    min_ev: float = 1.0
):
    """
    Génère des suggestions de combinés ET les sauvegarde automatiquement
    """
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    # 1. Récupérer les stats dynamiques des marchés
    cur.execute("""
        SELECT market_type,
               ROUND(COUNT(*) FILTER (WHERE is_winner)::numeric / NULLIF(COUNT(*), 0) * 100, 1) as win_rate
        FROM tracking_clv_picks
        WHERE is_resolved = true AND market_type IS NOT NULL
        GROUP BY market_type
        HAVING COUNT(*) >= 10
    """)
    market_stats = {row['market_type']: float(row['win_rate'] or 50) for row in cur.fetchall()}
    
    # 2. Récupérer les picks non résolus
    cur.execute("""
        SELECT 
            home_team, away_team, commence_time, market_type,
            odds_taken, diamond_score, clv_percentage, kelly_pct,
            league
        FROM tracking_clv_picks
        WHERE is_resolved = false
        AND commence_time > NOW()
        AND commence_time < NOW() + INTERVAL '7 days'
        AND market_type IN ('dc_1x', 'over_25', 'btts_no', 'under_35', 'over_15', 'draw', 'dc_12', 'home')
        AND odds_taken > 1.1
        ORDER BY commence_time, home_team
    """)
    
    picks = cur.fetchall()
    
    # 3. Grouper par match
    matches = {}
    for pick in picks:
        key = f"{pick['home_team']} vs {pick['away_team']}"
        if key not in matches:
            matches[key] = {
                'home_team': pick['home_team'],
                'away_team': pick['away_team'],
                'commence_time': str(pick['commence_time']),
                'league': pick['league'] or 'Unknown',
                'picks': []
            }
        matches[key]['picks'].append({
            'market': pick['market_type'],
            'odds': float(pick['odds_taken']) if pick['odds_taken'] else 1.5,
            'score': pick['diamond_score'] or 50,
            'clv': float(pick['clv_percentage']) if pick['clv_percentage'] else 0,
            'win_rate': market_stats.get(pick['market_type'], 50)
        })
    
    # 4. Générer les combinés
    suggestions = []
    
    for match_name, match_data in matches.items():
        if len(match_data['picks']) >= 2:
            # Trouver les meilleures combinaisons (2 picks)
            picks_list = match_data['picks']
            
            for i in range(len(picks_list)):
                for j in range(i + 1, len(picks_list)):
                    p1, p2 = picks_list[i], picks_list[j]
                    
                    # Calculer les métriques
                    combined_odds = p1['odds'] * p2['odds']
                    
                    # Probabilité combinée (produit des win rates)
                    prob1 = p1['win_rate'] / 100
                    prob2 = p2['win_rate'] / 100
                    combined_prob = prob1 * prob2
                    
                    # EV et Kelly
                    ev = calculate_ev(combined_prob, combined_odds)
                    kelly = calculate_kelly(combined_prob, combined_odds)
                    
                    # Skip si EV trop faible
                    if ev < min_ev:
                        continue
                    
                    # Corrélation estimée (simplifiée)
                    correlation = estimate_correlation(p1['market'], p2['market'])
                    
                    # Risk level
                    if ev > 1.2 and correlation < 0.4:
                        risk = 'LOW'
                        recommendation = '🔥 EXCELLENT - Forte value, faible corrélation'
                    elif ev > 1.0 and correlation < 0.5:
                        risk = 'MEDIUM'
                        recommendation = '✅ BON - Value positive'
                    else:
                        risk = 'HIGH'
                        recommendation = '⚠️ RISQUÉ - À surveiller'
                    
                    suggestion = {
                        'match_name': match_name,
                        'home_team': match_data['home_team'],
                        'away_team': match_data['away_team'],
                        'league': match_data['league'],
                        'commence_time': match_data['commence_time'],
                        'picks': [
                            {'market': p1['market'], 'odds': p1['odds'], 'score': p1['score'], 'clv': p1['clv'], 'win_rate': p1['win_rate']},
                            {'market': p2['market'], 'odds': p2['odds'], 'score': p2['score'], 'clv': p2['clv'], 'win_rate': p2['win_rate']}
                        ],
                        'combined_odds': round(combined_odds, 2),
                        'combined_probability': round(combined_prob * 100, 1),
                        'expected_value': round(ev, 2),
                        'kelly_pct': round(kelly, 2),
                        'correlation_score': round(correlation, 2),
                        'recommendation': recommendation,
                        'risk_level': risk
                    }
                    
                    suggestions.append(suggestion)
    
    # 5. Trier par EV
    suggestions.sort(key=lambda x: x['expected_value'], reverse=True)
    suggestions = suggestions[:limit]
    
    # 6. AUTO-SAVE si activé
    saved_count = 0
    if auto_save and suggestions:
        for suggestion in suggestions:
            saved = await save_combo_internal(cur, conn, suggestion)
            if saved:
                saved_count += 1
        conn.commit()
    
    cur.close()
    conn.close()
    
    return {
        'count': len(suggestions),
        'saved_count': saved_count,
        'auto_save': auto_save,
        'suggestions': suggestions,
        'generated_at': datetime.now().isoformat()
    }


def estimate_correlation(market1: str, market2: str) -> float:
    """Estime la corrélation entre 2 marchés"""
    # Corrélations connues (à améliorer avec données réelles)
    correlations = {
        ('dc_1x', 'btts_no'): 0.35,
        ('over_25', 'btts_yes'): 0.72,
        ('dc_1x', 'under_35'): 0.28,
        ('over_25', 'over_15'): 0.85,
        ('home', 'dc_1x'): 0.65,
        ('draw', 'btts_no'): 0.42,
        ('dc_12', 'over_25'): 0.30,
        ('dc_12', 'home'): 0.55,
        ('over_15', 'btts_yes'): 0.60,
        ('under_35', 'btts_no'): 0.45,
    }
    
    key = tuple(sorted([market1, market2]))
    return correlations.get(key, correlations.get((market2, market1), 0.5))


async def save_combo_internal(cur, conn, suggestion: dict) -> bool:
    """Sauvegarde interne d'un combo (évite doublons)"""
    try:
        selections = suggestion['picks']
        combo_hash = generate_combo_hash([
            {'match': suggestion['match_name'], 'market': p['market']} 
            for p in selections
        ])
        
        # Vérifier si existe déjà
        cur.execute("""
            SELECT id FROM fg_combo_tracking 
            WHERE selections::text LIKE %s
            AND created_at > NOW() - INTERVAL '24 hours'
        """, (f'%{suggestion["match_name"]}%',))
        
        if cur.fetchone():
            return False  # Déjà existe
        
        # Calculer stake optimal (Kelly)
        kelly_stake = max(1, min(suggestion['kelly_pct'], 10))  # 1€ à 10€
        
        cur.execute("""
            INSERT INTO fg_combo_tracking 
            (selections, total_odds, num_selections, combined_probability, 
             kelly_combo, expected_value, stake, status)
            VALUES (%s, %s, %s, %s, %s, %s, %s, 'pending')
            ON CONFLICT DO NOTHING
            RETURNING id
        """, (
            json.dumps({
                'match': suggestion['match_name'],
                'home_team': suggestion['home_team'],
                'away_team': suggestion['away_team'],
                'league': suggestion.get('league', ''),
                'commence_time': suggestion['commence_time'],
                'picks': selections,
                'risk_level': suggestion['risk_level'],
                'recommendation': suggestion['recommendation']
            }),
            suggestion['combined_odds'],
            len(selections),
            suggestion['combined_probability'],
            suggestion['kelly_pct'],
            suggestion['expected_value'],
            kelly_stake
        ))
        
        return cur.fetchone() is not None
        
    except Exception as e:
        print(f"Erreur save combo: {e}")
        return False


# ============================================================
# ANALYSE IA (GPT-4o)
# ============================================================

@router.post("/analyze-ai/{combo_id}")
async def analyze_combo_with_ai(combo_id: int):
    """
    Analyse un combo avec GPT-4o
    """
    if not OPENAI_API_KEY:
        return {"error": "OpenAI API key not configured", "analysis": None}
    
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    cur.execute("SELECT * FROM fg_combo_tracking WHERE id = %s", (combo_id,))
    combo = cur.fetchone()
    
    if not combo:
        return {"error": "Combo not found"}
    
    selections = combo['selections'] if isinstance(combo['selections'], dict) else json.loads(combo['selections'])
    
    # Construire le prompt
    prompt = f"""Tu es un expert en paris sportifs et analyse de combinés.

Analyse ce combo et donne ton verdict:

**Match:** {selections.get('match', 'N/A')}
**Ligue:** {selections.get('league', 'N/A')}
**Date:** {selections.get('commence_time', 'N/A')}

**Sélections:**
{json.dumps(selections.get('picks', []), indent=2)}

**Métriques:**
- Cote combinée: {combo['total_odds']}
- Probabilité estimée: {combo['combined_probability']}%
- Expected Value: {combo['expected_value']}
- Kelly suggéré: {combo['kelly_combo']}%
- Risque: {selections.get('risk_level', 'N/A')}

**Analyse demandée:**
1. Ces 2 marchés sont-ils compatibles ?
2. Y a-t-il des corrélations cachées à surveiller ?
3. Quel est le scénario de match le plus probable ?
4. Verdict final: VALIDER / ÉVITER / À SURVEILLER
5. Mise recommandée (en % du bankroll)

Réponds de manière concise et actionnable."""

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(
                "https://api.openai.com/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {OPENAI_API_KEY}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": "gpt-4o",
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": 800,
                    "temperature": 0.7
                }
            )
            
            data = response.json()
            analysis = data['choices'][0]['message']['content']
            
            # Sauvegarder l'analyse dans le combo
            cur.execute("""
                UPDATE fg_combo_tracking 
                SET selections = selections || %s::jsonb
                WHERE id = %s
            """, (json.dumps({'ai_analysis': analysis}), combo_id))
            conn.commit()
            
            return {
                "combo_id": combo_id,
                "analysis": analysis,
                "analyzed_at": datetime.now().isoformat()
            }
            
    except Exception as e:
        return {"error": str(e), "analysis": None}
    finally:
        cur.close()
        conn.close()


@router.post("/analyze-all-pending")
async def analyze_all_pending_combos():
    """Analyse tous les combos pending avec l'IA"""
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    cur.execute("""
        SELECT id FROM fg_combo_tracking 
        WHERE status = 'pending'
        AND NOT (selections::text LIKE '%ai_analysis%')
        ORDER BY created_at DESC
        LIMIT 10
    """)
    
    combos = cur.fetchall()
    cur.close()
    conn.close()
    
    results = []
    for combo in combos:
        result = await analyze_combo_with_ai(combo['id'])
        results.append(result)
    
    return {
        "analyzed_count": len(results),
        "results": results
    }


# ============================================================
# AUTO-RÉSOLUTION
# ============================================================

@router.post("/auto-resolve")
async def auto_resolve_combos():
    """
    Résout automatiquement les combos dont les matchs sont terminés
    """
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    # 1. Récupérer les combos pending dont le match est passé
    cur.execute("""
        SELECT id, combo_id, selections, total_odds, stake
        FROM fg_combo_tracking
        WHERE status = 'pending'
    """)
    
    pending_combos = cur.fetchall()
    resolved_count = 0
    results = []
    
    for combo in pending_combos:
        selections = combo['selections'] if isinstance(combo['selections'], dict) else json.loads(combo['selections'])
        
        # Extraire infos du match
        home_team = selections.get('home_team', '')
        away_team = selections.get('away_team', '')
        commence_time = selections.get('commence_time', '')
        
        if not home_team or not away_team:
            continue
        
        # Vérifier si le match est terminé
        cur.execute("""
            SELECT home_team, away_team, home_score, away_score, is_resolved
            FROM tracking_clv_picks
            WHERE home_team = %s AND away_team = %s
            AND is_resolved = true
            LIMIT 1
        """, (home_team, away_team))
        
        match_result = cur.fetchone()
        
        if not match_result:
            # Match pas encore terminé
            continue
        
        home_score = match_result['home_score'] or 0
        away_score = match_result['away_score'] or 0
        total_goals = home_score + away_score
        
        # Vérifier chaque sélection du combo
        all_won = True
        winning_count = 0
        picks_results = []
        
        for pick in selections.get('picks', []):
            market = pick.get('market', '')
            won = check_market_result(market, home_score, away_score)
            
            picks_results.append({
                'market': market,
                'won': won
            })
            
            if won:
                winning_count += 1
            else:
                all_won = False
        
        # Déterminer le status
        if all_won:
            status = 'won'
            profit_loss = float(combo['stake']) * float(combo['total_odds']) - float(combo['stake'])
        elif winning_count > 0:
            status = 'partial'
            profit_loss = -float(combo['stake']) * 0.5  # Perte partielle
        else:
            status = 'lost'
            profit_loss = -float(combo['stake'])
        
        # Mettre à jour
        cur.execute("""
            UPDATE fg_combo_tracking
            SET status = %s,
                outcome = %s,
                winning_selections = %s,
                profit_loss = %s,
                resolved_at = NOW(),
                selections = selections || %s::jsonb
            WHERE id = %s
        """, (
            status,
            status,
            winning_count,
            round(profit_loss, 2),
            json.dumps({'match_result': {'home': home_score, 'away': away_score}, 'picks_results': picks_results}),
            combo['id']
        ))
        
        resolved_count += 1
        results.append({
            'combo_id': str(combo['combo_id']),
            'match': f"{home_team} vs {away_team}",
            'score': f"{home_score}-{away_score}",
            'status': status,
            'profit_loss': round(profit_loss, 2),
            'winning_picks': f"{winning_count}/{len(selections.get('picks', []))}"
        })
    
    conn.commit()
    cur.close()
    conn.close()
    
    return {
        "resolved_count": resolved_count,
        "results": results,
        "resolved_at": datetime.now().isoformat()
    }


def check_market_result(market: str, home_score: int, away_score: int) -> bool:
    """Vérifie si un marché est gagnant"""
    total = home_score + away_score
    
    market_checks = {
        'home': home_score > away_score,
        'away': away_score > home_score,
        'draw': home_score == away_score,
        'dc_1x': home_score >= away_score,  # Dom ou Nul
        'dc_x2': away_score >= home_score,  # Nul ou Ext
        'dc_12': home_score != away_score,  # Dom ou Ext (pas nul)
        'over_15': total > 1.5,
        'over_25': total > 2.5,
        'over_35': total > 3.5,
        'under_15': total < 1.5,
        'under_25': total < 2.5,
        'under_35': total < 3.5,
        'under35': total < 3.5,
        'btts_yes': home_score > 0 and away_score > 0,
        'btts_no': home_score == 0 or away_score == 0,
        'dnb_home': home_score > away_score,
        'dnb_away': away_score > home_score,
    }
    
    return market_checks.get(market, False)


# ============================================================
# HISTORIQUE
# ============================================================

@router.get("/history")
async def get_combo_history(
    status: str = "all",
    limit: int = 50
):
    """Récupère l'historique des combos avec stats"""
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    query = """
        SELECT 
            id, combo_id, selections, total_odds, num_selections,
            combined_probability, kelly_combo, expected_value,
            status, outcome, winning_selections, stake, profit_loss,
            created_at, resolved_at
        FROM fg_combo_tracking
    """
    
    params = []
    if status != "all":
        query += " WHERE status = %s"
        params.append(status)
    
    query += " ORDER BY created_at DESC LIMIT %s"
    params.append(limit)
    
    cur.execute(query, params)
    combos = cur.fetchall()
    
    # Stats globales
    cur.execute("""
        SELECT 
            COUNT(*) as total_combos,
            COUNT(*) FILTER (WHERE status = 'won') as won,
            COUNT(*) FILTER (WHERE status = 'lost') as lost,
            COUNT(*) FILTER (WHERE status = 'partial') as partial,
            COUNT(*) FILTER (WHERE status = 'pending') as pending,
            ROUND(COALESCE(SUM(profit_loss), 0)::numeric, 2) as total_profit,
            ROUND(AVG(total_odds)::numeric, 2) as avg_odds,
            ROUND(AVG(num_selections)::numeric, 1) as avg_selections,
            ROUND(AVG(expected_value)::numeric, 2) as avg_ev
        FROM fg_combo_tracking
    """)
    stats = cur.fetchone()
    
    # Win rate (exclut pending)
    resolved = (stats['won'] or 0) + (stats['lost'] or 0) + (stats['partial'] or 0)
    win_rate = round((stats['won'] or 0) / max(1, resolved) * 100, 1) if resolved > 0 else 0
    
    cur.close()
    conn.close()
    
    # Formater
    for combo in combos:
        combo['created_at'] = str(combo['created_at']) if combo['created_at'] else None
        combo['resolved_at'] = str(combo['resolved_at']) if combo['resolved_at'] else None
        combo['combo_id'] = str(combo['combo_id']) if combo['combo_id'] else None
    
    return {
        "count": len(combos),
        "combos": combos,
        "stats": {
            "total": stats['total_combos'] or 0,
            "won": stats['won'] or 0,
            "lost": stats['lost'] or 0,
            "partial": stats['partial'] or 0,
            "pending": stats['pending'] or 0,
            "win_rate": win_rate,
            "total_profit": float(stats['total_profit'] or 0),
            "avg_odds": float(stats['avg_odds'] or 0),
            "avg_selections": float(stats['avg_selections'] or 0),
            "avg_ev": float(stats['avg_ev'] or 0)
        }
    }


# ============================================================
# CORRÉLATIONS DYNAMIQUES
# ============================================================

@router.get("/correlations-dynamic")
async def get_dynamic_correlations():
    """Calcule les corrélations réelles entre marchés"""
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    cur.execute("""
        WITH market_results AS (
            SELECT 
                home_team, away_team, commence_time::date as match_date,
                market_type, is_winner
            FROM tracking_clv_picks
            WHERE is_resolved = true
        ),
        pair_analysis AS (
            SELECT 
                a.market_type as market_a,
                b.market_type as market_b,
                COUNT(*) as sample_size,
                COUNT(*) FILTER (WHERE a.is_winner AND b.is_winner) as both_win,
                COUNT(*) FILTER (WHERE a.is_winner) as a_wins,
                COUNT(*) FILTER (WHERE b.is_winner) as b_wins
            FROM market_results a
            JOIN market_results b ON 
                a.home_team = b.home_team 
                AND a.away_team = b.away_team 
                AND a.match_date = b.match_date
                AND a.market_type < b.market_type
            GROUP BY a.market_type, b.market_type
            HAVING COUNT(*) >= 10
        )
        SELECT 
            market_a, market_b, sample_size,
            ROUND(a_wins::numeric / sample_size * 100, 1) as wr_a,
            ROUND(b_wins::numeric / sample_size * 100, 1) as wr_b,
            ROUND(both_win::numeric / sample_size * 100, 1) as both_wr,
            ROUND((both_win::numeric / NULLIF(a_wins * b_wins / sample_size::numeric, 0)), 2) as lift
        FROM pair_analysis
        ORDER BY lift DESC
    """)
    
    correlations = cur.fetchall()
    
    best_combos = []
    avoid_combos = []
    
    for c in correlations:
        lift = float(c['lift'] or 1)
        both_wr = float(c['both_wr'] or 0)
        
        if lift > 1.2 and both_wr > 30:
            best_combos.append({
                'pair': f"{c['market_a']} + {c['market_b']}",
                'win_rate': both_wr,
                'lift': lift,
                'sample': c['sample_size']
            })
        elif lift < 0.8 or both_wr < 15:
            avoid_combos.append({
                'pair': f"{c['market_a']} + {c['market_b']}",
                'win_rate': both_wr,
                'lift': lift,
                'reason': 'Corrélation négative' if lift < 0.8 else 'Win rate trop faible'
            })
    
    cur.close()
    conn.close()
    
    return {
        'correlations': correlations,
        'best_combos': sorted(best_combos, key=lambda x: x['win_rate'], reverse=True)[:5],
        'avoid_combos': avoid_combos[:5]
    }


# ============================================================
# SAUVEGARDE MANUELLE
# ============================================================

@router.post("/save")
async def save_combo(combo_data: dict):
    """Sauvegarde manuelle d'un combo"""
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    try:
        selections_list = combo_data.get('selections', [])
        total_odds = combo_data.get('total_odds', 1.0)
        stake = combo_data.get('stake', 10.0)
        match_name = combo_data.get('match_name', '')
        
        if len(selections_list) < 2:
            return {"error": "Minimum 2 sélections"}
        
        # Calculer probabilité combinée
        combined_prob = 1.0
        for sel in selections_list:
            wr = sel.get('win_rate', sel.get('score', 50))
            if wr and wr > 1:
                combined_prob *= wr / 100
        combined_prob *= 100
        
        ev = (combined_prob / 100) * total_odds
        kelly = calculate_kelly(combined_prob / 100, total_odds)
        
        # Formater selections comme un dict (comme les suggestions auto)
        if not match_name and selections_list:
            match_name = selections_list[0].get('match', 'Unknown')
        
        formatted_selections = {
            'match': match_name,
            'picks': selections_list,
            'league': combo_data.get('league', 'Unknown'),
            'risk_level': combo_data.get('risk_level', 'MEDIUM'),
            'recommendation': combo_data.get('recommendation', '')
        }
        
        cur.execute("""
            INSERT INTO fg_combo_tracking 
            (selections, total_odds, num_selections, combined_probability, 
             kelly_combo, expected_value, stake, status)
            VALUES (%s, %s, %s, %s, %s, %s, %s, 'pending')
            RETURNING id, combo_id
        """, (
            json.dumps(formatted_selections),
            total_odds,
            len(selections_list),
            round(combined_prob, 2),
            round(kelly, 2),
            round(ev, 2),
            stake
        ))
        
        result = cur.fetchone()
        conn.commit()
        
        return {
            "success": True,
            "combo_id": str(result['combo_id']),
            "id": result['id']
        }
        
    except Exception as e:
        conn.rollback()
        return {"error": str(e)}
    finally:
        cur.close()
        conn.close()


# ============================================================
# STATS AVANCÉES
# ============================================================

@router.get("/analytics")
async def get_combo_analytics():
    """Statistiques avancées pour l'amélioration"""
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    # Stats par risk level
    cur.execute("""
        SELECT 
            selections->>'risk_level' as risk_level,
            COUNT(*) as total,
            COUNT(*) FILTER (WHERE status = 'won') as won,
            ROUND(COUNT(*) FILTER (WHERE status = 'won')::numeric / 
                  NULLIF(COUNT(*) FILTER (WHERE status IN ('won', 'lost')), 0) * 100, 1) as win_rate,
            ROUND(SUM(profit_loss)::numeric, 2) as profit
        FROM fg_combo_tracking
        WHERE status != 'pending'
        GROUP BY selections->>'risk_level'
    """)
    by_risk = cur.fetchall()
    
    # Stats par nombre de sélections
    cur.execute("""
        SELECT 
            num_selections,
            COUNT(*) as total,
            COUNT(*) FILTER (WHERE status = 'won') as won,
            ROUND(COUNT(*) FILTER (WHERE status = 'won')::numeric / 
                  NULLIF(COUNT(*) FILTER (WHERE status IN ('won', 'lost')), 0) * 100, 1) as win_rate,
            ROUND(SUM(profit_loss)::numeric, 2) as profit
        FROM fg_combo_tracking
        WHERE status != 'pending'
        GROUP BY num_selections
        ORDER BY num_selections
    """)
    by_selections = cur.fetchall()
    
    # Stats par range EV
    cur.execute("""
        SELECT 
            CASE 
                WHEN expected_value >= 1.3 THEN 'EV >= 1.3'
                WHEN expected_value >= 1.1 THEN 'EV 1.1-1.3'
                ELSE 'EV < 1.1'
            END as ev_range,
            COUNT(*) as total,
            COUNT(*) FILTER (WHERE status = 'won') as won,
            ROUND(SUM(profit_loss)::numeric, 2) as profit
        FROM fg_combo_tracking
        WHERE status != 'pending'
        GROUP BY ev_range
    """)
    by_ev = cur.fetchall()
    
    cur.close()
    conn.close()
    
    return {
        "by_risk_level": by_risk,
        "by_num_selections": by_selections,
        "by_ev_range": by_ev,
        "insights": generate_insights(by_risk, by_ev)
    }


def generate_insights(by_risk: list, by_ev: list) -> list:
    """Génère des insights automatiques"""
    insights = []
    
    for r in by_risk:
        if r['risk_level'] == 'LOW' and float(r['profit'] or 0) > 0:
            insights.append(f"✅ Les combos LOW RISK sont rentables (+{r['profit']}u)")
        elif r['risk_level'] == 'HIGH' and float(r['profit'] or 0) < 0:
            insights.append(f"⚠️ Les combos HIGH RISK perdent ({r['profit']}u) - À éviter")
    
    for e in by_ev:
        if 'EV >= 1.3' in str(e.get('ev_range', '')) and float(e.get('profit', 0)) > 0:
            insights.append(f"📈 Les combos avec EV >= 1.3 sont très rentables")
    
    if not insights:
        insights.append("📊 Pas assez de données pour générer des insights (besoin de plus de combos résolus)")
    
    return insights


# ════════════════════════════════════════════════════════════
# 🏎️ FERRARI COMBO INTEGRATION
# ════════════════════════════════════════════════════════════

from api.services.ferrari_combo_integration import get_ferrari_combo_service

@router.get("/ferrari/analyze/{combo_id}")
async def analyze_combo_ferrari(combo_id: int):
    """
    🏎️ Analyse FERRARI d'un combo
    Détecte les pièges et calcule le risque
    """
    service = get_ferrari_combo_service()
    analysis = service.analyze_combo(combo_id)
    
    if not analysis:
        return {"error": f"Combo #{combo_id} non trouvé"}
    
    from dataclasses import asdict
    return asdict(analysis)


@router.get("/ferrari/analyze-all")
async def analyze_all_combos_ferrari():
    """
    🏎️ Analyse FERRARI de tous les combos pending
    """
    service = get_ferrari_combo_service()
    analyses = service.analyze_all_pending()
    
    # Résumé
    total = len(analyses)
    safe = sum(1 for a in analyses if a.get('total_traps', 0) == 0)
    risky = total - safe
    
    return {
        "total_combos": total,
        "safe_combos": safe,
        "risky_combos": risky,
        "analyses": analyses
    }


@router.get("/ferrari/safe-combos")
async def get_safe_combos():
    """
    🏎️ Retourne uniquement les combos SAFE (sans pièges)
    """
    service = get_ferrari_combo_service()
    safe = service.get_safe_combos()
    
    return {
        "count": len(safe),
        "combos": safe
    }


@router.get("/ferrari/risky-combos")
async def get_risky_combos():
    """
    🏎️ Retourne les combos avec des pièges détectés
    """
    service = get_ferrari_combo_service()
    risky = service.get_risky_combos()
    
    return {
        "count": len(risky),
        "combos": risky
    }
