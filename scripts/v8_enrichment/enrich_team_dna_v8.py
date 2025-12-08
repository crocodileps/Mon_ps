#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════════════════╗
║  🧬 V8 ADN ENRICHMENT - Calcul depuis données réelles                        ║
║                                                                              ║
║  Nouvelles métriques calculées depuis match_xg_stats enrichi:               ║
║  • diesel_factor_v8: % buts 2ème MT (depuis scores réels)                   ║
║  • fast_starter_v8: % buts 1ère MT                                          ║
║  • clutch_rating: capacité à marquer quand mené à la MT                     ║
║  • collapse_rate: % matchs perdus après avoir mené à la MT                  ║
║  • ht_dominance: % matchs en tête à la MT                                   ║
║  • comeback_rate: % remontées après avoir été mené                          ║
║  • xg_momentum: ratio xG 2H / xG 1H                                         ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import psycopg2
from psycopg2.extras import RealDictCursor
import json
from datetime import datetime

DB_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "database": "monps_db",
    "user": "monps_user",
    "password": "monps_secure_password_2024"
}

def get_connection():
    return psycopg2.connect(**DB_CONFIG)

def calculate_team_stats(team_name: str) -> dict:
    """Calcule toutes les stats V8 pour une équipe"""
    conn = get_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    # Récupérer tous les matchs de l'équipe (home et away)
    cur.execute("""
        SELECT 
            home_team, away_team,
            home_goals, away_goals,
            ht_home_score, ht_away_score,
            COALESCE(xg_1h_home, 0) as xg_1h_home,
            COALESCE(xg_1h_away, 0) as xg_1h_away,
            COALESCE(xg_2h_home, 0) as xg_2h_home,
            COALESCE(xg_2h_away, 0) as xg_2h_away,
            shots_home, shots_away,
            sot_home, sot_away
        FROM match_xg_stats 
        WHERE season = '2025-2026'
        AND ht_home_score IS NOT NULL
        AND (home_team = %s OR away_team = %s)
    """, (team_name, team_name))
    
    matches = cur.fetchall()
    cur.close()
    conn.close()
    
    if not matches:
        return None
    
    # Initialiser compteurs
    stats = {
        'matches': len(matches),
        'goals_1h': 0,
        'goals_2h': 0,
        'goals_total': 0,
        'goals_conceded_1h': 0,
        'goals_conceded_2h': 0,
        'xg_1h': 0.0,
        'xg_2h': 0.0,
        'xg_total': 0.0,
        'shots': 0,
        'sot': 0,
        # Situations à la MT
        'leading_at_ht': 0,
        'trailing_at_ht': 0,
        'drawing_at_ht': 0,
        # Résultats finaux selon situation MT
        'win_when_leading_ht': 0,
        'loss_when_leading_ht': 0,  # Collapse
        'win_when_trailing_ht': 0,  # Comeback
        'loss_when_trailing_ht': 0,
        'win_when_drawing_ht': 0,
        # Home/Away splits
        'home_matches': 0,
        'away_matches': 0,
        'home_goals_1h': 0,
        'home_goals_2h': 0,
        'away_goals_1h': 0,
        'away_goals_2h': 0,
    }
    
    for m in matches:
        is_home = m['home_team'] == team_name
        
        if is_home:
            team_ht = m['ht_home_score']
            opp_ht = m['ht_away_score']
            team_ft = m['home_goals']
            opp_ft = m['away_goals']
            team_xg_1h = float(m['xg_1h_home'] or 0)
            team_xg_2h = float(m['xg_2h_home'] or 0)
            team_shots = m['shots_home'] or 0
            team_sot = m['sot_home'] or 0
            stats['home_matches'] += 1
        else:
            team_ht = m['ht_away_score']
            opp_ht = m['ht_home_score']
            team_ft = m['away_goals']
            opp_ft = m['home_goals']
            team_xg_1h = float(m['xg_1h_away'] or 0)
            team_xg_2h = float(m['xg_2h_away'] or 0)
            team_shots = m['shots_away'] or 0
            team_sot = m['sot_away'] or 0
            stats['away_matches'] += 1
        
        # Buts par mi-temps
        goals_1h = team_ht
        goals_2h = team_ft - team_ht
        goals_conceded_1h = opp_ht
        goals_conceded_2h = opp_ft - opp_ht
        
        stats['goals_1h'] += goals_1h
        stats['goals_2h'] += goals_2h
        stats['goals_total'] += team_ft
        stats['goals_conceded_1h'] += goals_conceded_1h
        stats['goals_conceded_2h'] += goals_conceded_2h
        
        # xG
        stats['xg_1h'] += team_xg_1h
        stats['xg_2h'] += team_xg_2h
        stats['xg_total'] += team_xg_1h + team_xg_2h
        
        # Tirs
        stats['shots'] += team_shots
        stats['sot'] += team_sot
        
        # Home/Away goals split
        if is_home:
            stats['home_goals_1h'] += goals_1h
            stats['home_goals_2h'] += goals_2h
        else:
            stats['away_goals_1h'] += goals_1h
            stats['away_goals_2h'] += goals_2h
        
        # Situation à la MT
        if team_ht > opp_ht:
            stats['leading_at_ht'] += 1
            # Résultat final
            if team_ft > opp_ft:
                stats['win_when_leading_ht'] += 1
            elif team_ft < opp_ft:
                stats['loss_when_leading_ht'] += 1  # Collapse!
        elif team_ht < opp_ht:
            stats['trailing_at_ht'] += 1
            if team_ft > opp_ft:
                stats['win_when_trailing_ht'] += 1  # Comeback!
            elif team_ft < opp_ft:
                stats['loss_when_trailing_ht'] += 1
        else:
            stats['drawing_at_ht'] += 1
            if team_ft > opp_ft:
                stats['win_when_drawing_ht'] += 1
    
    return stats

def compute_dna_v8(stats: dict) -> dict:
    """Calcule les vecteurs ADN V8 depuis les stats"""
    if not stats or stats['matches'] == 0:
        return {}
    
    total_goals = max(stats['goals_total'], 1)
    
    dna = {
        # TEMPORAL DNA V8
        'diesel_factor_v8': round(stats['goals_2h'] / total_goals, 3) if total_goals > 0 else 0.5,
        'fast_starter_v8': round(stats['goals_1h'] / total_goals, 3) if total_goals > 0 else 0.5,
        'goals_1h_avg': round(stats['goals_1h'] / stats['matches'], 2),
        'goals_2h_avg': round(stats['goals_2h'] / stats['matches'], 2),
        
        # XG MOMENTUM
        'xg_1h_avg': round(stats['xg_1h'] / stats['matches'], 2),
        'xg_2h_avg': round(stats['xg_2h'] / stats['matches'], 2),
        'xg_momentum': round(stats['xg_2h'] / max(stats['xg_1h'], 0.1), 2),  # >1 = monte en puissance
        
        # SHOOTING DNA
        'shots_per_game': round(stats['shots'] / stats['matches'], 1),
        'sot_per_game': round(stats['sot'] / stats['matches'], 1),
        'shot_accuracy': round(100 * stats['sot'] / max(stats['shots'], 1), 1),
        
        # PSYCHE DNA V8 (basé sur situations réelles)
        'ht_dominance': round(100 * stats['leading_at_ht'] / stats['matches'], 1),
        'ht_deficit_rate': round(100 * stats['trailing_at_ht'] / stats['matches'], 1),
        
        # CLUTCH DNA
        'collapse_rate': round(100 * stats['loss_when_leading_ht'] / max(stats['leading_at_ht'], 1), 1),
        'lead_protection_v8': round(100 * stats['win_when_leading_ht'] / max(stats['leading_at_ht'], 1), 1),
        'comeback_rate': round(100 * stats['win_when_trailing_ht'] / max(stats['trailing_at_ht'], 1), 1),
        'surrender_rate': round(100 * stats['loss_when_trailing_ht'] / max(stats['trailing_at_ht'], 1), 1),
        
        # HOME/AWAY TEMPORAL
        'home_diesel': round(stats['home_goals_2h'] / max(stats['home_goals_1h'] + stats['home_goals_2h'], 1), 2),
        'away_diesel': round(stats['away_goals_2h'] / max(stats['away_goals_1h'] + stats['away_goals_2h'], 1), 2),
        
        # DEFENSIVE TEMPORAL
        'goals_conceded_1h_avg': round(stats['goals_conceded_1h'] / stats['matches'], 2),
        'goals_conceded_2h_avg': round(stats['goals_conceded_2h'] / stats['matches'], 2),
        'defensive_diesel': round(stats['goals_conceded_2h'] / max(stats['goals_conceded_1h'] + stats['goals_conceded_2h'], 1), 2),
        
        # META
        'matches_analyzed_v8': stats['matches'],
        'computed_at': datetime.now().isoformat(),
    }
    
    # Profils dérivés
    if dna['diesel_factor_v8'] > 0.6:
        dna['temporal_profile'] = 'DIESEL'
    elif dna['fast_starter_v8'] > 0.6:
        dna['temporal_profile'] = 'FAST_STARTER'
    else:
        dna['temporal_profile'] = 'BALANCED'
    
    if dna['collapse_rate'] > 20:
        dna['mental_profile'] = 'FRAGILE'
    elif dna['comeback_rate'] > 30:
        dna['mental_profile'] = 'RESILIENT'
    else:
        dna['mental_profile'] = 'STABLE'
    
    return dna

def update_team_dna(team_name: str, dna_v8: dict):
    """Met à jour quantum_dna avec les nouvelles données V8"""
    conn = get_connection()
    cur = conn.cursor()
    
    # Récupérer l'ADN existant
    cur.execute("""
        SELECT quantum_dna FROM quantum.team_profiles 
        WHERE team_name = %s
    """, (team_name,))
    
    row = cur.fetchone()
    if row and row[0]:
        existing_dna = row[0]
    else:
        existing_dna = {}
    
    # Fusionner avec les nouvelles données V8
    if 'temporal_dna' not in existing_dna:
        existing_dna['temporal_dna'] = {}
    
    # Ajouter/remplacer les métriques V8
    existing_dna['temporal_dna']['v8_enriched'] = dna_v8
    existing_dna['temporal_dna']['diesel_factor_v8'] = dna_v8['diesel_factor_v8']
    existing_dna['temporal_dna']['fast_starter_v8'] = dna_v8['fast_starter_v8']
    existing_dna['temporal_dna']['xg_momentum'] = dna_v8['xg_momentum']
    existing_dna['temporal_dna']['temporal_profile_v8'] = dna_v8['temporal_profile']
    
    # Ajouter clutch_dna
    existing_dna['clutch_dna'] = {
        'collapse_rate': dna_v8['collapse_rate'],
        'comeback_rate': dna_v8['comeback_rate'],
        'lead_protection_v8': dna_v8['lead_protection_v8'],
        'surrender_rate': dna_v8['surrender_rate'],
        'ht_dominance': dna_v8['ht_dominance'],
        'mental_profile': dna_v8['mental_profile'],
    }
    
    # Ajouter shooting_dna
    existing_dna['shooting_dna'] = {
        'shots_per_game': dna_v8['shots_per_game'],
        'sot_per_game': dna_v8['sot_per_game'],
        'shot_accuracy': dna_v8['shot_accuracy'],
    }
    
    # Update
    cur.execute("""
        UPDATE quantum.team_profiles 
        SET quantum_dna = %s, updated_at = NOW()
        WHERE team_name = %s
    """, (json.dumps(existing_dna), team_name))
    
    conn.commit()
    cur.close()
    conn.close()
    
    return cur.rowcount > 0

def main():
    print("""
╔══════════════════════════════════════════════════════════════════════════════╗
║  🧬 V8 ADN ENRICHMENT - Calcul depuis données réelles                        ║
╚══════════════════════════════════════════════════════════════════════════════╝
    """)
    
    conn = get_connection()
    cur = conn.cursor()
    
    # Récupérer toutes les équipes avec profils
    cur.execute("SELECT DISTINCT team_name FROM quantum.team_profiles ORDER BY team_name")
    teams = [r[0] for r in cur.fetchall()]
    cur.close()
    conn.close()
    
    print(f"📊 {len(teams)} équipes à enrichir\n")
    
    enriched = 0
    examples = []
    
    for team in teams:
        stats = calculate_team_stats(team)
        
        if stats:
            dna_v8 = compute_dna_v8(stats)
            if update_team_dna(team, dna_v8):
                enriched += 1
                
                # Garder quelques exemples intéressants
                if dna_v8['diesel_factor_v8'] > 0.65 or dna_v8['collapse_rate'] > 15:
                    examples.append({
                        'team': team,
                        'diesel': dna_v8['diesel_factor_v8'],
                        'collapse': dna_v8['collapse_rate'],
                        'comeback': dna_v8['comeback_rate'],
                        'profile': dna_v8['temporal_profile'],
                        'mental': dna_v8['mental_profile'],
                    })
                
                print(f"✅ {team}: diesel={dna_v8['diesel_factor_v8']:.2f}, collapse={dna_v8['collapse_rate']:.1f}%")
        else:
            print(f"⚠️ {team}: Pas de données matchs")
    
    # Résumé
    print(f"""
╔══════════════════════════════════════════════════════════════════════════════╗
║  📊 RÉSUMÉ ENRICHISSEMENT V8                                                 ║
╠══════════════════════════════════════════════════════════════════════════════╣
║  Équipes enrichies: {enriched}/{len(teams)}                                              
╚══════════════════════════════════════════════════════════════════════════════╝
    """)
    
    if examples:
        print("\n🔥 ÉQUIPES INTÉRESSANTES (DIESEL ou FRAGILE):\n")
        for e in sorted(examples, key=lambda x: -x['diesel'])[:10]:
            print(f"   {e['team']}: {e['profile']} | diesel={e['diesel']:.2f} | collapse={e['collapse']:.0f}% | comeback={e['comeback']:.0f}%")

if __name__ == "__main__":
    main()
