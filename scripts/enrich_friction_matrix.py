#!/usr/bin/env python3
"""
🔬 ENRICHISSEMENT FRICTION MATRIX - Approche Scientifique

Utilise les 11 vecteurs DNA pour calculer:
1. style_clash_score: COUNTER vs POSSESSION = high clash
2. tempo_clash_score: |diesel_A - diesel_B| normalisé
3. mental_clash_score: PREDATOR vs FRAGILE = high clash
4. predicted_goals: (xG_A_for + xG_B_for) / 2 + friction_bonus
5. predicted_btts_prob: Poisson P(A>0) * P(B>0)
6. predicted_over25_prob: Poisson 1 - P(0) - P(1) - P(2)
7. predicted_winner: basé sur Z-scores V2.4
"""

import math
import psycopg2
from psycopg2.extras import RealDictCursor
import sys
sys.path.append('/home/Mon_ps/app/services')

DB_CONFIG = {
    "host": "localhost", "port": 5432, "database": "monps_db",
    "user": "monps_user", "password": "monps_secure_password_2024"
}

# === STYLE CLASH MATRIX ===
# Plus le style est opposé, plus le clash est élevé
STYLE_CLASH = {
    ("COUNTER_ATTACK", "POSSESSION"): 90,
    ("POSSESSION", "COUNTER_ATTACK"): 90,
    ("COUNTER_ATTACK", "DIRECT"): 70,
    ("DIRECT", "COUNTER_ATTACK"): 70,
    ("POSSESSION", "DIRECT"): 80,
    ("DIRECT", "POSSESSION"): 80,
    ("HYBRID", "COUNTER_ATTACK"): 50,
    ("HYBRID", "POSSESSION"): 50,
    ("HYBRID", "DIRECT"): 50,
    ("HYBRID", "HYBRID"): 40,
    ("COUNTER_ATTACK", "COUNTER_ATTACK"): 30,
    ("POSSESSION", "POSSESSION"): 30,
    ("DIRECT", "DIRECT"): 60,
}

# === MENTAL CLASH MATRIX ===
MENTAL_CLASH = {
    ("PREDATOR", "FRAGILE"): 90,
    ("FRAGILE", "PREDATOR"): 90,
    ("PREDATOR", "CONSERVATIVE"): 75,
    ("CONSERVATIVE", "PREDATOR"): 75,
    ("VOLATILE", "VOLATILE"): 85,
    ("PREDATOR", "PREDATOR"): 80,
    ("VOLATILE", "FRAGILE"): 70,
    ("FRAGILE", "VOLATILE"): 70,
    ("BALANCED", "BALANCED"): 40,
    ("CONSERVATIVE", "CONSERVATIVE"): 30,
    ("BALANCED", "VOLATILE"): 55,
    ("BALANCED", "PREDATOR"): 50,
    ("BALANCED", "FRAGILE"): 45,
    ("BALANCED", "CONSERVATIVE"): 35,
}

def get_style_clash(style_a, style_b):
    """Calcule le clash de style"""
    key = (style_a or "HYBRID", style_b or "HYBRID")
    return STYLE_CLASH.get(key, STYLE_CLASH.get((key[1], key[0]), 50))

def get_mental_clash(mental_a, mental_b):
    """Calcule le clash mental"""
    key = (mental_a or "BALANCED", mental_b or "BALANCED")
    return MENTAL_CLASH.get(key, MENTAL_CLASH.get((key[1], key[0]), 50))

def get_tempo_clash(diesel_a, diesel_b):
    """
    Calcule le clash de tempo
    Deux équipes avec diesel très différent = match chaotique
    """
    diff = abs(diesel_a - diesel_b)
    # diff range: 0 to ~0.5, normalize to 0-100
    return min(100, diff * 200)

def calculate_predicted_goals(xg_a_for, xg_a_ag, xg_b_for, xg_b_ag, friction_score):
    """
    Prédit le nombre de buts total
    Base: (xG_A_for + xG_B_for) ajusté par friction
    """
    base_goals = (xg_a_for + xg_b_for)
    
    # Friction bonus: high friction = more open game
    friction_multiplier = 1 + (friction_score - 50) / 200
    
    return round(base_goals * friction_multiplier, 2)

def calculate_btts_prob(xg_a, xg_b):
    """
    Probabilité BTTS (Both Teams To Score)
    P(BTTS) = P(A scores at least 1) * P(B scores at least 1)
    P(score >= 1) = 1 - P(0) = 1 - e^(-xg)
    """
    p_a_scores = 1 - math.exp(-xg_a)
    p_b_scores = 1 - math.exp(-xg_b)
    return round(p_a_scores * p_b_scores, 3)

def calculate_over25_prob(total_xg):
    """
    Probabilité Over 2.5
    P(over 2.5) = 1 - P(0) - P(1) - P(2)
    Poisson: P(k) = (λ^k * e^(-λ)) / k!
    """
    lam = total_xg
    p_0 = math.exp(-lam)
    p_1 = lam * math.exp(-lam)
    p_2 = (lam ** 2 / 2) * math.exp(-lam)
    
    return round(1 - p_0 - p_1 - p_2, 3)

def predict_winner(z_a, z_b, xg_a, xg_b):
    """
    Prédit le gagnant basé sur Z-scores et xG
    Returns: 'team_a', 'team_b', ou 'draw'
    """
    # Combiner Z-score (60%) et xG (40%)
    score_a = z_a * 0.6 + (xg_a - xg_b) * 0.4
    score_b = z_b * 0.6 + (xg_b - xg_a) * 0.4
    
    diff = score_a - score_b
    
    if diff > 0.5:
        return 'team_a'
    elif diff < -0.5:
        return 'team_b'
    else:
        return 'draw'

def main():
    conn = psycopg2.connect(**DB_CONFIG)
    
    print("=" * 80)
    print("🔬 ENRICHISSEMENT FRICTION MATRIX")
    print("=" * 80)
    
    # 1. Récupérer tous les profils d'équipes
    print("\n�� Chargement des profils DNA...")
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute("""
            SELECT team_name,
                   quantum_dna->'nemesis_dna'->>'style' as style,
                   quantum_dna->'psyche_dna'->>'profile' as mentality,
                   quantum_dna->'temporal_dna'->>'diesel_factor' as diesel,
                   quantum_dna->'current_season'->>'xg_for_avg' as xg_for,
                   quantum_dna->'current_season'->>'xg_against_avg' as xg_against
            FROM quantum.team_profiles
        """)
        teams = {r['team_name']: r for r in cur.fetchall()}
    
    print(f"   ✅ {len(teams)} équipes chargées")
    
    # 2. Récupérer les Z-scores V2.4
    print("\n📊 Calcul des Z-Scores V2.4...")
    from quantum_scorer_v2_4 import QuantumScorerV24
    scorer = QuantumScorerV24()
    all_scores = scorer.get_all_sorted()
    z_scores = {s['team']: s['z_score'] for s in all_scores}
    print(f"   ✅ {len(z_scores)} Z-scores calculés")
    
    # 3. Récupérer toutes les paires de friction
    print("\n📊 Chargement des paires friction...")
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute("""
            SELECT id, team_a_name, team_b_name, friction_score, chaos_potential
            FROM quantum.matchup_friction
        """)
        pairs = cur.fetchall()
    
    print(f"   ✅ {len(pairs)} paires à enrichir")
    
    # 4. Enrichir chaque paire
    print("\n🔬 Enrichissement en cours...")
    updated = 0
    errors = 0
    
    for pair in pairs:
        team_a = pair['team_a_name']
        team_b = pair['team_b_name']
        friction = float(pair['friction_score'] or 50)
        
        # Vérifier que les deux équipes existent
        if team_a not in teams or team_b not in teams:
            errors += 1
            continue
            
        profile_a = teams[team_a]
        profile_b = teams[team_b]
        
        # Extraire les données
        style_a = profile_a['style'] or 'HYBRID'
        style_b = profile_b['style'] or 'HYBRID'
        mental_a = profile_a['mentality'] or 'BALANCED'
        mental_b = profile_b['mentality'] or 'BALANCED'
        diesel_a = float(profile_a['diesel'] or 0.5)
        diesel_b = float(profile_b['diesel'] or 0.5)
        xg_a_for = float(profile_a['xg_for'] or 1.3)
        xg_a_ag = float(profile_a['xg_against'] or 1.3)
        xg_b_for = float(profile_b['xg_for'] or 1.3)
        xg_b_ag = float(profile_b['xg_against'] or 1.3)
        z_a = z_scores.get(team_a, 0)
        z_b = z_scores.get(team_b, 0)
        
        # Calculer les clash scores
        style_clash = get_style_clash(style_a, style_b)
        mental_clash = get_mental_clash(mental_a, mental_b)
        tempo_clash = get_tempo_clash(diesel_a, diesel_b)
        
        # xG pour ce match spécifique
        # Home (A) attack vs Away (B) defense, etc.
        xg_a = (xg_a_for + xg_b_ag) / 2
        xg_b = (xg_b_for + xg_a_ag) / 2
        
        # Prédictions
        predicted_goals = calculate_predicted_goals(xg_a_for, xg_a_ag, xg_b_for, xg_b_ag, friction)
        btts_prob = calculate_btts_prob(xg_a, xg_b)
        over25_prob = calculate_over25_prob(predicted_goals)
        winner = predict_winner(z_a, z_b, xg_a, xg_b)
        
        # Mettre à jour
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE quantum.matchup_friction
                SET style_clash_score = %s,
                    tempo_clash_score = %s,
                    mental_clash_score = %s,
                    predicted_goals = %s,
                    predicted_btts_prob = %s,
                    predicted_over25_prob = %s,
                    predicted_winner = %s,
                    style_a = %s,
                    style_b = %s,
                    updated_at = NOW()
                WHERE id = %s
            """, (
                style_clash, tempo_clash, mental_clash,
                predicted_goals, btts_prob, over25_prob,
                winner, style_a, style_b,
                pair['id']
            ))
        
        updated += 1
        
        if updated % 500 == 0:
            print(f"   ... {updated} paires enrichies")
            conn.commit()
    
    conn.commit()
    
    print(f"\n✅ Enrichissement terminé:")
    print(f"   - {updated} paires mises à jour")
    print(f"   - {errors} erreurs (équipes manquantes)")
    
    # 5. Vérification
    print("\n📊 Vérification des données enrichies:")
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute("""
            SELECT team_a_name, team_b_name,
                   friction_score, chaos_potential,
                   style_clash_score, tempo_clash_score, mental_clash_score,
                   predicted_goals, predicted_btts_prob, predicted_over25_prob,
                   predicted_winner, style_a, style_b
            FROM quantum.matchup_friction
            WHERE style_clash_score IS NOT NULL
            ORDER BY friction_score DESC
            LIMIT 5
        """)
        samples = cur.fetchall()
        
    for s in samples:
        print(f"\n   {s['team_a_name']} vs {s['team_b_name']}:")
        print(f"      Friction: {s['friction_score']} | Chaos: {s['chaos_potential']}")
        print(f"      Style Clash: {s['style_clash_score']} ({s['style_a']} vs {s['style_b']})")
        print(f"      Tempo Clash: {s['tempo_clash_score']:.0f} | Mental Clash: {s['mental_clash_score']}")
        print(f"      Predicted: {s['predicted_goals']:.2f} goals | BTTS: {s['predicted_btts_prob']:.0%} | O2.5: {s['predicted_over25_prob']:.0%}")
        print(f"      Winner: {s['predicted_winner']}")
    
    # Stats
    print("\n📊 Stats après enrichissement:")
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute("""
            SELECT 
                COUNT(*) as total,
                COUNT(style_clash_score) as enriched,
                ROUND(AVG(predicted_goals)::numeric, 2) as avg_goals,
                ROUND(AVG(predicted_btts_prob)::numeric, 2) as avg_btts,
                ROUND(AVG(predicted_over25_prob)::numeric, 2) as avg_over25
            FROM quantum.matchup_friction
        """)
        stats = cur.fetchone()
        
    print(f"   Total paires: {stats['total']}")
    print(f"   Enrichies: {stats['enriched']}")
    print(f"   Avg Goals: {stats['avg_goals']}")
    print(f"   Avg BTTS: {stats['avg_btts']:.0%}")
    print(f"   Avg O2.5: {stats['avg_over25']:.0%}")
    
    conn.close()
    scorer.close()
    print("\n✅ DONE!")

if __name__ == "__main__":
    main()
