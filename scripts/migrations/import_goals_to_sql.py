#!/usr/bin/env python3
"""
IMPORT GOALS TO POSTGRESQL - Migration Phase 2
Importe les buts depuis all_goals_detailed_2025.json vers quantum.goals_unified
"""

import json
import psycopg2
from psycopg2.extras import execute_values
from pathlib import Path
from datetime import datetime

DB_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "database": "monps_db",
    "user": "monps_user",
    "password": "monps_secure_password_2024"
}

SOURCE_FILE = Path("/home/Mon_ps/data/goals/all_goals_detailed_2025.json")
MIN_GOALS_REQUIRED = 100

def calculate_period(minute):
    if minute <= 15: return "0-15"
    elif minute <= 30: return "16-30"
    elif minute <= 45: return "31-45"
    elif minute <= 60: return "46-60"
    elif minute <= 75: return "61-75"
    elif minute <= 90: return "76-90"
    else: return "90+"

def transform_goal(goal):
    minute = int(goal.get("minute", 0))
    period = goal.get("period") or calculate_period(minute)
    return (
        str(goal.get("goal_id")),
        str(goal.get("match_id")),
        "2025",
        goal.get("league", "Unknown"),
        goal.get("date"),
        goal.get("home_team", ""),
        goal.get("away_team", ""),
        str(goal.get("player_id", "")),
        goal.get("player_name", "Unknown"),
        goal.get("team_name", "Unknown"),
        goal.get("opponent", ""),
        goal.get("is_home", False),
        minute,
        period,
        goal.get("xg"),
        goal.get("situation"),
        goal.get("shot_type"),
        goal.get("is_first_goal", False),
        goal.get("is_last_goal", False),
        goal.get("goal_number_in_match"),
        "understat",
        str(SOURCE_FILE)
    )

def main():
    print("=" * 70)
    print("IMPORT GOALS TO POSTGRESQL - Phase 2")
    print("=" * 70)
    
    # 1. Charger JSON
    print(f"[1/5] Chargement {SOURCE_FILE.name}...")
    with open(SOURCE_FILE) as f:
        goals = json.load(f)
    print(f"   OK: {len(goals)} buts")
    
    # 2. Validation
    print(f"[2/5] Validation...")
    if len(goals) < MIN_GOALS_REQUIRED:
        print(f"   ERREUR: {len(goals)} < {MIN_GOALS_REQUIRED}")
        return False
    print(f"   OK: {len(goals)} >= {MIN_GOALS_REQUIRED}")
    
    # 3. Transform
    print(f"[3/5] Transformation...")
    values = [transform_goal(g) for g in goals]
    print(f"   OK: {len(values)} tuples")
    
    # 4. Insert
    print(f"[4/5] Insertion SQL...")
    conn = psycopg2.connect(**DB_CONFIG)
    try:
        cursor = conn.cursor()
        sql = """
        INSERT INTO quantum.goals_unified (
            goal_id, match_id, season, league, date,
            home_team, away_team, player_id, player_name,
            team_name, opponent, is_home, minute, period,
            xg, situation, shot_type, is_first_goal, is_last_goal,
            goal_number_in_match, source, source_file
        ) VALUES %s
        ON CONFLICT (goal_id) DO UPDATE SET
            xg = EXCLUDED.xg, updated_at = NOW()
        """
        execute_values(cursor, sql, values, page_size=100)
        conn.commit()
        print(f"   OK: {len(values)} inseres")
    except Exception as e:
        conn.rollback()
        print(f"   ERREUR: {e}")
        return False
    finally:
        conn.close()
    
    # 5. Verification
    print(f"[5/5] Verification...")
    conn = psycopg2.connect(**DB_CONFIG)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM quantum.goals_unified")
    print(f"   Total en base: {cursor.fetchone()[0]}")
    cursor.execute("SELECT team_name, COUNT(*) FROM quantum.goals_unified GROUP BY team_name ORDER BY COUNT(*) DESC LIMIT 5")
    print("   Top 5 equipes:")
    for row in cursor.fetchall():
        print(f"      {row[0]}: {row[1]}")
    cursor.execute("SELECT player_name, scorer, minute, half FROM quantum.goals_unified LIMIT 2")
    print("   Verification triggers:")
    for row in cursor.fetchall():
        print(f"      {row[0]}={row[1]}, min={row[2]} -> half={row[3]}")
    conn.close()
    
    print("=" * 70)
    print("IMPORT TERMINE AVEC SUCCES")
    print("=" * 70)
    return True

if __name__ == "__main__":
    exit(0 if main() else 1)
