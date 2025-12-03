#!/usr/bin/env python3
"""
═══════════════════════════════════════════════════════════════════════════════
SMART SCORER UPDATER - Enrichissement par déduction logique
═══════════════════════════════════════════════════════════════════════════════

Utilise les données existantes pour déduire:
- is_hot_streak: Si équipe momentum_score >= 70 ET joueur top scorer
- is_key_player: Top scorer de chaque équipe (>= 3 buts)
- form_score: Basé sur momentum équipe + goals_per_90 joueur

Sources:
- team_momentum (goals_scored_last_5, momentum_score)
- team_intelligence (home_strength, goals_tendency)
- scorer_intelligence (season_goals, goals_per_90)
"""

import psycopg2
import psycopg2.extras

def main():
    conn = psycopg2.connect(
        host='localhost', port=5432, dbname='monps_db',
        user='monps_user', password='monps_secure_password_2024'
    )
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    
    print("═══════════════════════════════════════════════════════════════════")
    print("SMART SCORER UPDATER - Enrichissement")
    print("═══════════════════════════════════════════════════════════════════")
    
    # 1. DÉDUIRE IS_KEY_PLAYER
    # Le top scorer de chaque équipe avec >= 3 buts est key_player
    print("\n1. Mise à jour is_key_player...")
    cur.execute("""
        WITH TeamTopScorer AS (
            SELECT current_team, MAX(season_goals) as max_goals
            FROM scorer_intelligence
            WHERE season_goals >= 3
            GROUP BY current_team
        )
        UPDATE scorer_intelligence si
        SET is_key_player = true
        FROM TeamTopScorer tts
        WHERE si.current_team = tts.current_team 
        AND si.season_goals = tts.max_goals
    """)
    key_players_updated = cur.rowcount
    print(f"   ✅ {key_players_updated} key players identifiés")
    
    # 2. DÉDUIRE IS_HOT_STREAK
    # Si l'équipe a momentum_score >= 70 ET joueur a >= 0.4 goals/90
    print("\n2. Mise à jour is_hot_streak...")
    cur.execute("""
        UPDATE scorer_intelligence si
        SET is_hot_streak = true
        FROM team_momentum tm
        WHERE (
            LOWER(si.current_team) LIKE '%' || LOWER(REPLACE(tm.team_name, ' FC', '')) || '%'
            OR LOWER(tm.team_name) LIKE '%' || LOWER(REPLACE(si.current_team, ' FC', '')) || '%'
        )
        AND tm.momentum_score >= 70
        AND si.goals_per_90 >= 0.35
    """)
    hot_updated = cur.rowcount
    print(f"   ✅ {hot_updated} joueurs en hot streak")
    
    # 3. CALCULER FORM_SCORE (0-100)
    # form_score = (goals_per_90 * 50) + (team_momentum_score * 0.5)
    print("\n3. Mise à jour form_score...")
    cur.execute("""
        UPDATE scorer_intelligence si
        SET form_score = LEAST(100, GREATEST(0,
            (COALESCE(si.goals_per_90, 0) * 50) + 
            COALESCE((
                SELECT tm.momentum_score * 0.5 
                FROM team_momentum tm 
                WHERE LOWER(si.current_team) LIKE '%' || LOWER(REPLACE(tm.team_name, ' FC', '')) || '%'
                   OR LOWER(tm.team_name) LIKE '%' || LOWER(REPLACE(si.current_team, ' FC', '')) || '%'
                LIMIT 1
            ), 25)
        ))
        WHERE si.season_goals > 0
    """)
    form_updated = cur.rowcount
    print(f"   ✅ {form_updated} form_scores calculés")
    
    # 4. DÉDUIRE IS_PENALTY_TAKER
    # Si le joueur a des buts et est le top scorer ou 2ème de l'équipe
    print("\n4. Mise à jour is_penalty_taker (top 2 scorers)...")
    cur.execute("""
        WITH RankedScorers AS (
            SELECT id, current_team, season_goals,
                   ROW_NUMBER() OVER (PARTITION BY current_team ORDER BY season_goals DESC) as rank
            FROM scorer_intelligence
            WHERE season_goals >= 3
        )
        UPDATE scorer_intelligence si
        SET is_penalty_taker = true
        FROM RankedScorers rs
        WHERE si.id = rs.id AND rs.rank <= 2
    """)
    penalty_updated = cur.rowcount
    print(f"   ✅ {penalty_updated} penalty takers identifiés")
    
    conn.commit()
    
    # 5. VÉRIFICATION
    print("\n" + "═"*67)
    print("VÉRIFICATION POST-UPDATE")
    print("═"*67)
    
    cur.execute("""
        SELECT 
            COUNT(*) as total,
            COUNT(CASE WHEN is_key_player = true THEN 1 END) as key_players,
            COUNT(CASE WHEN is_hot_streak = true THEN 1 END) as hot_streaks,
            COUNT(CASE WHEN is_penalty_taker = true THEN 1 END) as penalty_takers,
            COUNT(CASE WHEN form_score > 50 THEN 1 END) as good_form
        FROM scorer_intelligence
    """)
    row = cur.fetchone()
    print(f"   Total joueurs: {row['total']}")
    print(f"   Key players: {row['key_players']}")
    print(f"   Hot streaks: {row['hot_streaks']}")
    print(f"   Penalty takers: {row['penalty_takers']}")
    print(f"   Good form (>50): {row['good_form']}")
    
    # Exemple Liverpool
    print("\n   Exemple Liverpool après enrichissement:")
    cur.execute("""
        SELECT player_name, season_goals, goals_per_90, 
               is_key_player, is_hot_streak, is_penalty_taker, form_score
        FROM scorer_intelligence 
        WHERE LOWER(current_team) LIKE '%liverpool%'
        AND season_goals > 0
        ORDER BY season_goals DESC
        LIMIT 5
    """)
    for row in cur.fetchall():
        key = "⭐" if row['is_key_player'] else ""
        hot = "🔥" if row['is_hot_streak'] else ""
        pen = "⚽" if row['is_penalty_taker'] else ""
        print(f"      {row['player_name']}: {row['season_goals']}G, form={row['form_score']} {key}{hot}{pen}")
    
    conn.close()
    print("\n✅ ENRICHISSEMENT TERMINÉ!")

if __name__ == "__main__":
    main()
