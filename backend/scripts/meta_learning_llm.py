#!/usr/bin/env python3
"""
META-LEARNING avec Claude API
Analyse les échecs des agents et suggère améliorations
"""
import os
import requests
import psycopg2
from psycopg2.extras import RealDictCursor
import json
import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Configuration
ANTHROPIC_API_KEY = os.getenv('ANTHROPIC_API_KEY', '')  # À configurer
DB_CONFIG = {
    "host": "monps_postgres",
    "database": "monps_db",
    "user": "monps_user",
    "password": "monps_secure_password_2024"
}

def get_strategies_needing_improvement():
    """Récupère stratégies avec performance < 45% win rate"""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        cursor.execute("""
            SELECT 
                s.id as strategy_id,
                s.agent_name,
                s.strategy_name,
                s.win_rate,
                s.roi,
                s.total_predictions,
                s.tier
            FROM strategies s
            WHERE s.tier IN ('C', 'D')  -- Seulement les stratégies à améliorer
            AND s.total_predictions >= 10  -- Minimum 10 prédictions
            AND s.is_active = TRUE
            AND NOT EXISTS (
                SELECT 1 FROM strategy_improvements si
                WHERE si.strategy_id = s.id
                AND si.ab_test_active = TRUE  -- Pas déjà en test
            )
            ORDER BY s.win_rate ASC NULLS LAST
            LIMIT 5
        """)
        
        strategies = cursor.fetchall()
        conn.close()
        
        logger.info(f"📊 {len(strategies)} stratégies à améliorer")
        return strategies
        
    except Exception as e:
        logger.error(f"❌ Erreur: {e}")
        return []

def get_recent_failures(agent_name, limit=15):
    """Récupère échecs récents d'un agent pour analyse"""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        cursor.execute("""
            SELECT 
                ap.match_id,
                aa.home_team,
                aa.away_team,
                aa.sport,
                aa.league,
                ap.predicted_outcome,
                mr.outcome as actual_outcome,
                ap.confidence,
                aa.factors,
                aa.reasoning,
                mr.score_home,
                mr.score_away
            FROM agent_predictions ap
            JOIN agent_analyses aa ON ap.match_id = aa.match_id 
                AND ap.agent_name = aa.agent_name
            JOIN match_results mr ON ap.match_id = mr.match_id
            WHERE ap.agent_name = %s
            AND ap.was_correct = FALSE
            AND mr.is_finished = TRUE
            ORDER BY ap.created_at DESC
            LIMIT %s
        """, (agent_name, limit))
        
        failures = cursor.fetchall()
        conn.close()
        
        logger.info(f"📊 {len(failures)} échecs récents pour {agent_name}")
        return failures
        
    except Exception as e:
        logger.error(f"❌ Erreur: {e}")
        return []

def analyze_with_claude(strategy, failures):
    """Envoie analyse à Claude API"""
    
    if not ANTHROPIC_API_KEY:
        logger.warning("⚠️ ANTHROPIC_API_KEY non configurée")
        return None
    
    # Préparer données pour LLM
    failures_summary = []
    for f in failures[:10]:  # Max 10 pour ne pas dépasser token limit
        failures_summary.append({
            "match": f"{f['home_team']} vs {f['away_team']}",
            "league": f['league'],
            "predicted": f['predicted_outcome'],
            "actual": f['actual_outcome'],
            "score": f"{f['score_home']}-{f['score_away']}",
            "confidence": f['confidence'],
            "factors": f['factors']
        })
    
    prompt = f"""Tu es un expert en analyse quantitative des paris sportifs.

STRATÉGIE À ANALYSER:
- Agent: {strategy['agent_name']}
- Stratégie: {strategy['strategy_name']}
- Win rate actuel: {strategy['win_rate']}%
- Total prédictions: {strategy['total_predictions']}
- Tier: {strategy['tier']}

ÉCHECS RÉCENTS (10 derniers):
{json.dumps(failures_summary, indent=2)}

MISSION:
1. Identifie le PATTERN COMMUN des échecs
2. Quels FACTEURS ont été IGNORÉS ou SOUS-ESTIMÉS ?
3. Quelles AMÉLIORATIONS concrètes suggères-tu ?
4. Quel NOUVEAU SEUIL de confiance recommandes-tu ?

Réponds UNIQUEMENT en JSON valide:
{{
  "failure_pattern": "Description du pattern identifié",
  "missing_factors": ["facteur1", "facteur2", "facteur3"],
  "recommended_adjustments": [
    "Ajustement concret 1",
    "Ajustement concret 2"
  ],
  "new_confidence_threshold": 55.0,
  "expected_improvement": 8.5,
  "reasoning": "Explication détaillée de l'analyse"
}}

IMPORTANT: Réponds SEULEMENT avec le JSON, rien d'autre."""

    try:
        response = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": ANTHROPIC_API_KEY,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json"
            },
            json={
                "model": "claude-sonnet-4-20250514",
                "max_tokens": 2000,
                "messages": [
                    {"role": "user", "content": prompt}
                ]
            },
            timeout=60
        )
        
        if response.status_code == 200:
            data = response.json()
            content = data['content'][0]['text']
            
            # Parser JSON
            analysis = json.loads(content)
            logger.info(f"✅ Analyse Claude complète")
            return analysis
        else:
            logger.error(f"❌ Erreur API: {response.status_code}")
            return None
            
    except Exception as e:
        logger.error(f"❌ Erreur Claude: {e}")
        return None

def save_improvement_suggestion(strategy_id, agent_name, strategy_name, analysis, baseline_data):
    """Sauvegarde suggestion d'amélioration en DB"""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO strategy_improvements
            (strategy_id, agent_name, strategy_name, baseline_win_rate, 
             baseline_roi, baseline_samples, failure_pattern, missing_factors,
             recommended_adjustments, llm_reasoning, new_threshold)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        """, (
            strategy_id,
            agent_name,
            strategy_name,
            baseline_data['win_rate'],
            baseline_data['roi'],
            baseline_data['total_predictions'],
            analysis['failure_pattern'],
            analysis['missing_factors'],
            json.dumps(analysis['recommended_adjustments']),
            analysis['reasoning'],
            analysis['new_confidence_threshold']
        ))
        
        improvement_id = cursor.fetchone()[0]
        conn.commit()
        conn.close()
        
        logger.info(f"✅ Amélioration #{improvement_id} créée")
        return improvement_id
        
    except Exception as e:
        logger.error(f"❌ Erreur save: {e}")
        return None

def main():
    """Fonction principale"""
    logger.info("="*80)
    logger.info("🧠 META-LEARNING: Analyse LLM des stratégies")
    logger.info("="*80)
    
    # 1. Récupérer stratégies à améliorer
    strategies = get_strategies_needing_improvement()
    
    if not strategies:
        logger.info("✅ Aucune stratégie à améliorer")
        return
    
    improvements_created = 0
    
    # 2. Pour chaque stratégie
    for strategy in strategies:
        logger.info(f"\n{'='*80}")
        logger.info(f"🔍 Analyse: {strategy['agent_name']}")
        logger.info(f"   Win rate: {strategy['win_rate']}% | Tier: {strategy['tier']}")
        logger.info(f"{'='*80}")
        
        # Récupérer échecs
        failures = get_recent_failures(strategy['agent_name'])
        
        if len(failures) < 5:
            logger.warning(f"⚠️ Pas assez d'échecs pour analyse ({len(failures)})")
            continue
        
        # Analyser avec Claude
        analysis = analyze_with_claude(strategy, failures)
        
        if not analysis:
            logger.warning("⚠️ Analyse LLM échouée")
            continue
        
        # Afficher résultats
        logger.info(f"\n📊 RÉSULTATS ANALYSE:")
        logger.info(f"   Pattern: {analysis['failure_pattern']}")
        logger.info(f"   Facteurs manquants: {', '.join(analysis['missing_factors'])}")
        logger.info(f"   Amélioration attendue: +{analysis['expected_improvement']}%")
        
        # Sauvegarder
        improvement_id = save_improvement_suggestion(
            strategy['strategy_id'],
            strategy['agent_name'],
            strategy['strategy_name'],
            analysis,
            strategy
        )
        
        if improvement_id:
            improvements_created += 1
    
    logger.info(f"\n{'='*80}")
    logger.info(f"✅ {improvements_created} améliorations créées")
    logger.info("="*80)

if __name__ == "__main__":
    main()
