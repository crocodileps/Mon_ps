#!/usr/bin/env python3
"""
META-LEARNING avec GPT-4o (Meilleur modèle OpenAI actuel)
Analyse quantitative des échecs et améliorations stratégiques
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
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY', '')
DB_CONFIG = {
    "host": "monps_postgres",
    "database": "monps_db",
    "user": "monps_user",
    "password": "monps_secure_password_2024"
}

def get_strategies_needing_improvement():
    """Récupère stratégies tier C/D à améliorer"""
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
            WHERE s.tier IN ('C', 'D')
            AND s.total_predictions >= 10
            AND s.is_active = TRUE
            AND NOT EXISTS (
                SELECT 1 FROM strategy_improvements si
                WHERE si.strategy_id = s.id
                AND si.ab_test_active = TRUE
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
    """Récupère derniers échecs d'un agent"""
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
            ORDER BY ap.predicted_at DESC
            LIMIT %s
        """, (agent_name, limit))
        
        failures = cursor.fetchall()
        conn.close()
        
        logger.info(f"📊 {len(failures)} échecs récents")
        return failures
        
    except Exception as e:
        logger.error(f"❌ Erreur: {e}")
        return []

def analyze_with_gpt4o(strategy, failures):
    """
    Analyse avec GPT-4o (meilleur modèle OpenAI actuel)
    Optimisé pour analyse quantitative
    """
    
    if not OPENAI_API_KEY:
        logger.warning("⚠️ OPENAI_API_KEY non configurée")
        return None
    
    # Préparer échecs pour analyse
    failures_data = []
    for f in failures[:10]:  # Top 10 échecs
        failures_data.append({
            "match": f"{f['home_team']} vs {f['away_team']}",
            "league": f['league'],
            "predicted": f['predicted_outcome'],
            "actual": f['actual_outcome'],
            "score": f"{f['score_home']}-{f['score_away']}",
            "confidence": float(f['confidence']) if f['confidence'] else 0,
            "factors": f['factors'] or {}
        })
    
    # Prompt optimisé pour GPT-4o
    system_prompt = """Tu es un expert en analyse quantitative et machine learning appliqué aux paris sportifs.
    
Tu analyses les patterns d'échecs des agents ML pour identifier:
1. Les biais systématiques
2. Les facteurs sous-estimés
3. Les ajustements optimaux des hyperparamètres

Tu réponds UNIQUEMENT en JSON valide, sans markdown, sans texte supplémentaire."""

    user_prompt = f"""Analyse cette stratégie défaillante:

STRATÉGIE:
- Agent: {strategy['agent_name']}
- Nom: {strategy['strategy_name']}
- Win rate: {strategy['win_rate']}%
- Échantillon: {strategy['total_predictions']} prédictions
- Classification: Tier {strategy['tier']}

ÉCHECS RÉCENTS (10 derniers):
{json.dumps(failures_data, indent=2)}

ANALYSE QUANTITATIVE REQUISE:

1. PATTERN DETECTION
   Identifie le pattern statistique commun des échecs
   
2. FEATURE ENGINEERING
   Quels features/facteurs sont manquants ou sous-pondérés ?
   
3. HYPERPARAMETER TUNING
   Quels ajustements des seuils/paramètres suggères-tu ?
   
4. EXPECTED LIFT
   Quelle amélioration de win rate estimes-tu (en %) ?

SORTIE JSON (STRICTE):
{{
  "failure_pattern": "Description technique du pattern identifié",
  "missing_factors": ["facteur_technique_1", "facteur_technique_2", "facteur_technique_3"],
  "recommended_adjustments": [
    "Ajustement hyperparamètre 1 (précis et chiffré)",
    "Ajustement feature 2 (précis et chiffré)",
    "Ajustement seuil 3 (précis et chiffré)"
  ],
  "new_confidence_threshold": 52.5,
  "expected_improvement": 7.5,
  "reasoning": "Explication technique de l'analyse avec chiffres et logique quantitative"
}}"""

    try:
        response = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {OPENAI_API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "model": "gpt-4o",  # LE MEILLEUR MODÈLE ACTUEL
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                "temperature": 0.2,  # Bas pour analyse quantitative
                "max_tokens": 2500,
                "response_format": {"type": "json_object"}  # Force JSON
            },
            timeout=60
        )
        
        if response.status_code == 200:
            data = response.json()
            content = data['choices'][0]['message']['content']
            
            # Parser JSON
            analysis = json.loads(content)
            
            logger.info(f"✅ Analyse GPT-4o complète")
            logger.info(f"   Coût: ~${data['usage']['total_tokens'] * 0.00002:.4f}")
            
            return analysis
        else:
            logger.error(f"❌ Erreur API: {response.status_code}")
            logger.error(f"   Response: {response.text[:200]}")
            return None
            
    except Exception as e:
        logger.error(f"❌ Erreur GPT-4o: {e}")
        return None

def save_improvement_suggestion(strategy_id, agent_name, strategy_name, analysis, baseline_data):
    """Sauvegarde amélioration en DB"""
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
        
        logger.info(f"✅ Amélioration #{improvement_id} sauvegardée")
        return improvement_id
        
    except Exception as e:
        logger.error(f"❌ Erreur save: {e}")
        conn.rollback()
        return None

def main():
    """Fonction principale"""
    logger.info("="*80)
    logger.info("🧠 META-LEARNING: Analyse GPT-4o (Meilleur modèle OpenAI)")
    logger.info("="*80)
    
    # Récupérer stratégies
    strategies = get_strategies_needing_improvement()
    
    if not strategies:
        logger.info("✅ Aucune stratégie à améliorer")
        logger.info("   Toutes les stratégies ont win rate > 45%")
        return
    
    improvements_created = 0
    total_cost = 0
    
    # Analyser chaque stratégie
    for strategy in strategies:
        logger.info(f"\n{'='*80}")
        logger.info(f"🔍 Analyse: {strategy['agent_name']}")
        logger.info(f"   Win rate: {strategy['win_rate']}%")
        logger.info(f"   Tier: {strategy['tier']}")
        logger.info(f"   Échantillon: {strategy['total_predictions']} matchs")
        
        # Récupérer échecs
        failures = get_recent_failures(strategy['agent_name'])
        
        if len(failures) < 2:
            logger.warning(f"⚠️ Échantillon limité: {len(failures)} échecs (on teste quand même)")
            continue
        
        # Analyser avec GPT-4o
        logger.info(f"   📡 Envoi à GPT-4o...")
        analysis = analyze_with_gpt4o(strategy, failures)
        
        if not analysis:
            logger.warning("⚠️ Analyse échouée")
            continue
        
        # Afficher résultats
        logger.info(f"\n   📊 RÉSULTATS ANALYSE:")
        logger.info(f"   • Pattern: {analysis['failure_pattern'][:80]}...")
        logger.info(f"   • Facteurs manquants: {len(analysis['missing_factors'])}")
        for factor in analysis['missing_factors'][:3]:
            logger.info(f"     - {factor}")
        logger.info(f"   • Gain attendu: +{analysis['expected_improvement']}%")
        logger.info(f"   • Nouveau seuil: {analysis['new_confidence_threshold']}%")
        
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
    
    # Résumé
    logger.info(f"\n{'='*80}")
    logger.info(f"✅ SESSION TERMINÉE")
    logger.info(f"   Améliorations créées: {improvements_created}")
    logger.info(f"   Coût total estimé: ~${total_cost:.4f}")
    logger.info("="*80)

if __name__ == "__main__":
    main()
