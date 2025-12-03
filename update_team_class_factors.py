#!/usr/bin/env python3
"""
Mettre à jour les facteurs team_class pour les équipes anglaises
Basé sur des données réalistes de performance
"""

import psycopg2

conn = psycopg2.connect(host='localhost', port=5432, dbname='monps_db', 
                        user='monps_user', password='monps_secure_password_2024')
cur = conn.cursor()

print("="*70)
print("MISE À JOUR TEAM_CLASS FACTORS")
print("="*70)

# Facteurs réalistes basés sur les performances historiques
team_factors = {
    # Tier S - Clubs d'élite mondiale
    'Real Madrid': {'home_fortress': 1.20, 'away_weakness': 0.90, 'psych_edge': 1.15},
    'Manchester City': {'home_fortress': 1.25, 'away_weakness': 0.85, 'psych_edge': 1.12},
    'Bayern Munich': {'home_fortress': 1.22, 'away_weakness': 0.88, 'psych_edge': 1.10},
    'PSG': {'home_fortress': 1.18, 'away_weakness': 0.92, 'psych_edge': 1.05},
    
    # Tier A - Top clubs européens
    'Liverpool': {'home_fortress': 1.18, 'away_weakness': 0.92, 'psych_edge': 1.10},
    'Arsenal': {'home_fortress': 1.15, 'away_weakness': 0.95, 'psych_edge': 1.05},
    'Barcelona': {'home_fortress': 1.15, 'away_weakness': 0.95, 'psych_edge': 1.08},
    'Chelsea': {'home_fortress': 1.10, 'away_weakness': 1.00, 'psych_edge': 1.02},
    'Atletico Madrid': {'home_fortress': 1.20, 'away_weakness': 0.95, 'psych_edge': 1.05},
    'Inter': {'home_fortress': 1.15, 'away_weakness': 0.95, 'psych_edge': 1.03},
    'Juventus': {'home_fortress': 1.12, 'away_weakness': 0.98, 'psych_edge': 1.02},
    'Borussia Dortmund': {'home_fortress': 1.18, 'away_weakness': 0.95, 'psych_edge': 1.00},
    
    # Tier B - Bons clubs
    'Tottenham': {'home_fortress': 1.08, 'away_weakness': 1.02, 'psych_edge': 0.98},
    'Manchester United': {'home_fortress': 1.10, 'away_weakness': 1.05, 'psych_edge': 1.00},
    'Aston Villa': {'home_fortress': 1.10, 'away_weakness': 1.00, 'psych_edge': 0.98},
    'Newcastle': {'home_fortress': 1.12, 'away_weakness': 1.02, 'psych_edge': 0.95},
    
    # Tier C - Championship / Bas de tableau PL
    'Leeds': {'home_fortress': 1.05, 'away_weakness': 1.05, 'psych_edge': 0.92},
    'Burnley': {'home_fortress': 1.08, 'away_weakness': 1.08, 'psych_edge': 0.90},
    'Sunderland': {'home_fortress': 1.05, 'away_weakness': 1.12, 'psych_edge': 0.88},
    'Sheffield United': {'home_fortress': 1.02, 'away_weakness': 1.10, 'psych_edge': 0.90},
    
    # Tier D - Bas Championship
    'Plymouth': {'home_fortress': 1.00, 'away_weakness': 1.15, 'psych_edge': 0.85},
    'Hull': {'home_fortress': 1.00, 'away_weakness': 1.12, 'psych_edge': 0.85},
}

updated = 0
for team, factors in team_factors.items():
    cur.execute("""
        UPDATE team_class SET 
            home_fortress_factor = %s,
            away_weakness_factor = %s,
            psychological_edge = %s,
            updated_at = NOW()
        WHERE LOWER(team_name) LIKE %s
    """, (factors['home_fortress'], factors['away_weakness'], 
          factors['psych_edge'], f"%{team.lower()}%"))
    
    if cur.rowcount > 0:
        print(f"   ✅ {team}: HomeFort={factors['home_fortress']}, AwayWeak={factors['away_weakness']}, Psych={factors['psych_edge']}")
        updated += cur.rowcount

conn.commit()
print(f"\n   Total: {updated} équipes mises à jour")

# Vérifier Liverpool et Sunderland
print("\n" + "="*70)
print("VÉRIFICATION:")
print("="*70)

cur.execute("""
    SELECT team_name, tier, home_fortress_factor, away_weakness_factor, psychological_edge
    FROM team_class 
    WHERE LOWER(team_name) LIKE '%liverpool%' OR LOWER(team_name) LIKE '%sunderland%'
""")
for r in cur.fetchall():
    print(f"   {r[0]}: Tier={r[1]}, HomeFort={r[2]}, AwayWeak={r[3]}, Psych={r[4]}")

cur.close()
conn.close()
