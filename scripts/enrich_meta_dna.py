#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                    ENRICH META-DNA - META-LABELING                           ║
║                                                                              ║
║  Calcule la fiabilité des signaux par équipe et par marché                   ║
║  à partir des données historiques de tracking_clv_picks                      ║
║                                                                              ║
║  Meta-Labeling = "Est-ce que notre signal est fiable dans CE contexte?"      ║
║                                                                              ║
║  Données calculées:                                                          ║
║  - reliability_by_market: {over_25: {win_rate, n_bets, z_score}, ...}       ║
║  - best_markets: marchés avec win_rate > 55% et n >= 5                      ║
║  - avoid_markets: marchés avec win_rate < 40%                               ║
║  - global_reliability: score global de fiabilité                            ║
║                                                                              ║
║  Usage: python3 enrich_meta_dna.py                                           ║
║  Cron:  0 7 * * 1 python3 /home/Mon_ps/scripts/enrich_meta_dna.py           ║
║                                                                              ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import psycopg2
from psycopg2.extras import Json, RealDictCursor
from datetime import datetime
from collections import defaultdict
import math
import sys

# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════════

DB_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "database": "monps_db",
    "user": "monps_user",
    "password": "monps_secure_password_2024"
}

# Seuils de fiabilité
MIN_BETS_FOR_RELIABILITY = 3   # Minimum de paris pour calculer
MIN_BETS_FOR_CONFIDENCE = 5    # Minimum pour haute confiance
WIN_RATE_BEST = 0.55           # Seuil pour "best market"
WIN_RATE_AVOID = 0.40          # Seuil pour "avoid market"

# Markets à analyser
MARKET_FAMILIES = {
    'goals': ['over_25', 'under_25', 'over_15', 'under_15', 'over_35', 'under_35'],
    'btts': ['btts_yes', 'btts_no'],
    'result': ['home', 'away', 'draw'],
    'double_chance': ['dc_1x', 'dc_x2', 'dc_12'],
}


# ═══════════════════════════════════════════════════════════════════════════════
# STATISTICS
# ═══════════════════════════════════════════════════════════════════════════════

def calculate_z_score(win_rate: float, n_bets: int, expected_rate: float = 0.50) -> float:
    """
    Calcule le Z-Score de la performance
    Z > 2.0 = statistiquement significatif (95% confiance)
    Z > 2.58 = très significatif (99% confiance)
    """
    if n_bets < 2:
        return 0.0
    
    # Standard error pour proportion binomiale
    se = math.sqrt(expected_rate * (1 - expected_rate) / n_bets)
    
    if se == 0:
        return 0.0
    
    z = (win_rate - expected_rate) / se
    return round(z, 2)


def calculate_confidence_level(z_score: float) -> str:
    """Détermine le niveau de confiance statistique"""
    abs_z = abs(z_score)
    if abs_z >= 2.58:
        return "VERY_HIGH"  # 99%
    elif abs_z >= 1.96:
        return "HIGH"       # 95%
    elif abs_z >= 1.65:
        return "MEDIUM"     # 90%
    else:
        return "LOW"


def calculate_expected_rate(market_type: str) -> float:
    """Taux de réussite attendu par type de marché (pour calcul Z-Score)"""
    expected_rates = {
        # Goals markets - ajustés selon implied probability moyenne
        'over_25': 0.52,
        'under_25': 0.48,
        'over_15': 0.72,
        'under_15': 0.28,
        'over_35': 0.32,
        'under_35': 0.68,
        # BTTS
        'btts_yes': 0.52,
        'btts_no': 0.48,
        # Result - home avantage
        'home': 0.45,
        'away': 0.30,
        'draw': 0.25,
        # Double chance
        'dc_1x': 0.70,
        'dc_x2': 0.55,
        'dc_12': 0.75,
    }
    return expected_rates.get(market_type, 0.50)


# ═══════════════════════════════════════════════════════════════════════════════
# DATA EXTRACTION
# ═══════════════════════════════════════════════════════════════════════════════

def get_team_market_stats(conn) -> dict:
    """
    Extrait les statistiques par équipe et par marché depuis tracking_clv_picks
    Combine home_team et away_team pour avoir une vue complète
    """
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    # Requête combinée home + away
    cur.execute("""
        WITH combined AS (
            -- Paris où l'équipe joue à domicile
            SELECT 
                home_team as team,
                market_type,
                is_winner,
                profit_loss,
                odds_taken,
                clv_percentage
            FROM tracking_clv_picks 
            WHERE is_resolved = true AND home_team IS NOT NULL
            
            UNION ALL
            
            -- Paris où l'équipe joue à l'extérieur
            SELECT 
                away_team as team,
                market_type,
                is_winner,
                profit_loss,
                odds_taken,
                clv_percentage
            FROM tracking_clv_picks 
            WHERE is_resolved = true AND away_team IS NOT NULL
        )
        SELECT 
            team,
            market_type,
            COUNT(*) as n_bets,
            SUM(CASE WHEN is_winner THEN 1 ELSE 0 END) as wins,
            AVG(CASE WHEN is_winner THEN 1 ELSE 0 END) as win_rate,
            SUM(profit_loss) as total_pnl,
            AVG(profit_loss) as avg_pnl,
            AVG(odds_taken) as avg_odds,
            AVG(clv_percentage) as avg_clv
        FROM combined
        WHERE team IS NOT NULL AND market_type IS NOT NULL
        GROUP BY team, market_type
        HAVING COUNT(*) >= %s
        ORDER BY team, n_bets DESC
    """, (MIN_BETS_FOR_RELIABILITY,))
    
    results = cur.fetchall()
    
    # Organiser par équipe
    team_stats = defaultdict(lambda: {'markets': {}, 'total_bets': 0, 'total_wins': 0})
    
    for row in results:
        team = row['team']
        market = row['market_type']
        
        team_stats[team]['markets'][market] = {
            'n_bets': row['n_bets'],
            'wins': row['wins'],
            'win_rate': float(row['win_rate']) if row['win_rate'] else 0,
            'total_pnl': float(row['total_pnl']) if row['total_pnl'] else 0,
            'avg_pnl': float(row['avg_pnl']) if row['avg_pnl'] else 0,
            'avg_odds': float(row['avg_odds']) if row['avg_odds'] else 0,
            'avg_clv': float(row['avg_clv']) if row['avg_clv'] else 0,
        }
        team_stats[team]['total_bets'] += row['n_bets']
        team_stats[team]['total_wins'] += row['wins']
    
    return dict(team_stats)


# ═══════════════════════════════════════════════════════════════════════════════
# META-DNA CALCULATION
# ═══════════════════════════════════════════════════════════════════════════════

def calculate_meta_dna(team_name: str, stats: dict) -> dict:
    """
    Calcule le meta_dna complet pour une équipe
    """
    markets = stats.get('markets', {})
    
    if not markets:
        return None
    
    # 1. Reliability by market avec Z-Score
    reliability_by_market = {}
    for market, data in markets.items():
        expected = calculate_expected_rate(market)
        z_score = calculate_z_score(data['win_rate'], data['n_bets'], expected)
        confidence = calculate_confidence_level(z_score)
        
        reliability_by_market[market] = {
            'win_rate': round(data['win_rate'], 3),
            'n_bets': data['n_bets'],
            'z_score': z_score,
            'confidence': confidence,
            'pnl': round(data['total_pnl'], 2),
            'avg_odds': round(data['avg_odds'], 2),
            'avg_clv': round(data['avg_clv'], 2) if data['avg_clv'] else None,
        }
    
    # 2. Best markets (haute fiabilité)
    best_markets = [
        market for market, data in reliability_by_market.items()
        if data['win_rate'] >= WIN_RATE_BEST 
        and data['n_bets'] >= MIN_BETS_FOR_CONFIDENCE
    ]
    # Trier par Z-Score
    best_markets = sorted(best_markets, 
                         key=lambda m: reliability_by_market[m]['z_score'], 
                         reverse=True)[:5]
    
    # 3. Avoid markets (faible fiabilité)
    avoid_markets = [
        market for market, data in reliability_by_market.items()
        if data['win_rate'] < WIN_RATE_AVOID 
        and data['n_bets'] >= MIN_BETS_FOR_CONFIDENCE
    ]
    
    # 4. Profitable markets (PnL positif)
    profitable_markets = [
        market for market, data in reliability_by_market.items()
        if data['pnl'] > 0 and data['n_bets'] >= MIN_BETS_FOR_CONFIDENCE
    ]
    profitable_markets = sorted(profitable_markets,
                               key=lambda m: reliability_by_market[m]['pnl'],
                               reverse=True)[:5]
    
    # 5. Global reliability score (0-100)
    total_bets = stats['total_bets']
    total_wins = stats['total_wins']
    global_win_rate = total_wins / total_bets if total_bets > 0 else 0
    
    # Score pondéré: win_rate + bonus pour volume + bonus pour Z-Score positifs
    high_z_count = sum(1 for m in reliability_by_market.values() if m['z_score'] > 1.5)
    volume_bonus = min(10, total_bets / 10)  # Max 10 points pour volume
    z_bonus = min(10, high_z_count * 3)       # Max 10 points pour Z-Scores
    
    global_reliability = round(global_win_rate * 80 + volume_bonus + z_bonus, 1)
    global_reliability = min(100, max(0, global_reliability))
    
    # 6. Confidence tier
    if global_reliability >= 70 and total_bets >= 20:
        confidence_tier = "ELITE"
    elif global_reliability >= 55 and total_bets >= 10:
        confidence_tier = "TRUSTED"
    elif total_bets >= 5:
        confidence_tier = "DEVELOPING"
    else:
        confidence_tier = "INSUFFICIENT_DATA"
    
    return {
        'reliability_by_market': reliability_by_market,
        'best_markets': best_markets,
        'avoid_markets': avoid_markets,
        'profitable_markets': profitable_markets,
        'global_reliability': global_reliability,
        'confidence_tier': confidence_tier,
        'total_bets_analyzed': total_bets,
        'total_wins': total_wins,
        'global_win_rate': round(global_win_rate, 3),
        'markets_count': len(markets),
        'updated_at': datetime.now().isoformat()
    }


# ═══════════════════════════════════════════════════════════════════════════════
# DATABASE UPDATE
# ═══════════════════════════════════════════════════════════════════════════════

def update_meta_dna(conn, team_name: str, meta_dna_data: dict) -> bool:
    """Met à jour meta_dna dans quantum_dna"""
    cur = conn.cursor()
    try:
        # Récupérer le quantum_dna actuel
        cur.execute("""
            SELECT quantum_dna FROM quantum.team_profiles 
            WHERE team_name = %s
        """, (team_name,))
        
        row = cur.fetchone()
        if not row:
            # Essayer avec ILIKE pour les variations de nom
            cur.execute("""
                SELECT team_name, quantum_dna FROM quantum.team_profiles 
                WHERE team_name ILIKE %s
                LIMIT 1
            """, (f"%{team_name}%",))
            row = cur.fetchone()
            if row:
                team_name = row[0]
                quantum_dna = row[1] or {}
            else:
                return False
        else:
            quantum_dna = row[0] or {}
        
        # Mettre à jour meta_dna
        quantum_dna['meta_dna'] = meta_dna_data
        
        # Sauvegarder
        cur.execute("""
            UPDATE quantum.team_profiles 
            SET quantum_dna = %s, updated_at = NOW()
            WHERE team_name = %s
        """, (Json(quantum_dna), team_name))
        
        conn.commit()
        return True
        
    except Exception as e:
        conn.rollback()
        print(f"   ❌ Erreur update {team_name}: {e}")
        return False


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    print("╔══════════════════════════════════════════════════════════════════╗")
    print("║          META-LABELING - RELIABILITY ENRICHMENT                 ║")
    print("╚══════════════════════════════════════════════════════════════════╝")
    print(f"⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    conn = psycopg2.connect(**DB_CONFIG)
    
    # 1. Extraire les stats depuis tracking_clv_picks
    print("📊 Extraction des données CLV tracking...")
    team_stats = get_team_market_stats(conn)
    print(f"   ✓ {len(team_stats)} équipes avec données suffisantes")
    print()
    
    # 2. Calculer et enrichir meta_dna pour chaque équipe
    print("🔬 Calcul du Meta-DNA...")
    
    total_updated = 0
    total_errors = 0
    elite_teams = []
    
    for team_name, stats in sorted(team_stats.items()):
        meta_dna = calculate_meta_dna(team_name, stats)
        
        if not meta_dna:
            continue
        
        success = update_meta_dna(conn, team_name, meta_dna)
        
        if success:
            total_updated += 1
            
            # Tracker les équipes ELITE
            if meta_dna['confidence_tier'] == 'ELITE':
                elite_teams.append({
                    'team': team_name,
                    'reliability': meta_dna['global_reliability'],
                    'best_markets': meta_dna['best_markets'][:3],
                    'win_rate': meta_dna['global_win_rate']
                })
            
            # Afficher progress pour les équipes avec beaucoup de données
            if stats['total_bets'] >= 10:
                tier_emoji = {
                    'ELITE': '🏆',
                    'TRUSTED': '✅',
                    'DEVELOPING': '📈',
                    'INSUFFICIENT_DATA': '⏳'
                }.get(meta_dna['confidence_tier'], '❓')
                
                print(f"   {tier_emoji} {team_name[:25]:25} | "
                      f"Bets: {stats['total_bets']:3} | "
                      f"WR: {meta_dna['global_win_rate']*100:5.1f}% | "
                      f"Tier: {meta_dna['confidence_tier']}")
        else:
            total_errors += 1
    
    conn.close()
    
    # 3. Résumé
    print("\n" + "═" * 60)
    print(f"✅ {total_updated} équipes enrichies avec Meta-DNA")
    print(f"❌ {total_errors} erreurs")
    
    if elite_teams:
        print(f"\n🏆 ÉQUIPES ELITE ({len(elite_teams)}):")
        for t in sorted(elite_teams, key=lambda x: x['reliability'], reverse=True)[:10]:
            print(f"   • {t['team'][:20]:20} | Reliability: {t['reliability']:5.1f} | "
                  f"WR: {t['win_rate']*100:.1f}% | Best: {', '.join(t['best_markets'][:2])}")
    
    print("═" * 60)
    
    return 0 if total_errors == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
