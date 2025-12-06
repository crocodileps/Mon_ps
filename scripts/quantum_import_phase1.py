#!/usr/bin/env python3
"""
╔═══════════════════════════════════════════════════════════════════════════════════════════════════════════════╗
║     🔬 QUANTUM ADN - PHASE 1 - SCRIPT D'IMPORT                                                                ║
║                                                                                                               ║
║  ✅ Importe audit_complet_99_equipes.json → quantum.team_profiles                                            ║
║  ✅ Importe toutes les stratégies → quantum.team_strategies                                                   ║
║  ✅ Enrichit depuis team_intelligence (styles tactiques)                                                      ║
║  ✅ Enrichit depuis tracking_clv_picks (performance marché)                                                   ║
║  ✅ Crée un snapshot d'audit                                                                                  ║
╚═══════════════════════════════════════════════════════════════════════════════════════════════════════════════╝
"""

import json
import psycopg2
from psycopg2.extras import RealDictCursor, execute_values
from datetime import datetime
from typing import Dict, List, Optional
import hashlib

# Configuration DB
DB_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "database": "monps_db",
    "user": "monps_user",
    "password": "monps_secure_password_2024"
}

# Fichiers sources
AUDIT_JSON_PATH = "/home/Mon_ps/benchmarks/audit_complet_99_equipes.json"

# Mapping des tiers basé sur le rang
def get_tier(rank: int, pnl: float) -> str:
    """Détermine le tier basé sur le rang et P&L"""
    if rank <= 10 and pnl >= 15:
        return "ELITE"
    elif rank <= 25 and pnl >= 10:
        return "GOLD"
    elif rank <= 50 and pnl >= 5:
        return "SILVER"
    elif rank <= 75 and pnl >= 0:
        return "BRONZE"
    else:
        return "EXPERIMENTAL"

# Mapping des familles de stratégies
STRATEGY_FAMILIES = {
    "CONVERGENCE": ["CONVERGENCE_OVER_PURE", "CONVERGENCE_OVER_MC", "CONVERGENCE_UNDER_PURE", "CONVERGENCE_UNDER_MC"],
    "MONTE_CARLO": ["MC_PURE", "MC_V2", "MC_NO_CLASH", "MONTE_CARLO"],
    "QUANT": ["QUANT_BEST_MARKET", "QUANT_ROI"],
    "SCORE": ["SCORE_SNIPER", "SCORE_HIGH", "SCORE_GOOD", "SCORE_MEDIUM"],
    "TACTICAL": ["TACTICAL_", "STYLE_"],
    "LEAGUE": ["LEAGUE_"],
    "COMBO": ["COMBO_", "TRIPLE_", "ULTIMATE_"],
    "TIER": ["TIER_"],
    "SPECIAL": ["BTTS_NO", "UNDER_35", "OVER_15", "ADAPTIVE", "TOTAL_CHAOS"]
}

def get_strategy_family(strategy_name: str) -> str:
    """Détermine la famille d'une stratégie"""
    strategy_upper = strategy_name.upper()
    for family, patterns in STRATEGY_FAMILIES.items():
        for pattern in patterns:
            if pattern in strategy_upper:
                return family
    return "OTHER"

def compute_parameters_hash(params: dict) -> str:
    """Calcule un hash des paramètres pour déduplication"""
    return hashlib.md5(json.dumps(params, sort_keys=True).encode()).hexdigest()[:16]


class QuantumImporter:
    def __init__(self):
        self.conn = None
        self.audit_data = None
        self.team_intelligence = {}
        self.imported_profiles = 0
        self.imported_strategies = 0
        
    def connect(self):
        """Connexion à la base de données"""
        self.conn = psycopg2.connect(**DB_CONFIG)
        print("✅ Connexion DB établie")
        
    def close(self):
        """Fermeture connexion"""
        if self.conn:
            self.conn.close()
            
    def load_audit_json(self):
        """Charge le fichier JSON d'audit"""
        with open(AUDIT_JSON_PATH, 'r', encoding='utf-8') as f:
            self.audit_data = json.load(f)
        print(f"✅ JSON chargé: {self.audit_data['summary']['total_teams']} équipes, +{self.audit_data['summary']['total_pnl']}u")
        
    def load_team_intelligence(self):
        """Charge les données de team_intelligence pour enrichissement"""
        with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT id, team_name, team_name_normalized, current_style, 
                       current_style_score, home_strength, away_strength,
                       goals_tendency, btts_tendency, draw_tendency,
                       home_over25_rate, away_over25_rate, home_btts_rate, away_btts_rate
                FROM team_intelligence
            """)
            for row in cur.fetchall():
                # Index par nom normalisé ET nom original pour matching flexible
                self.team_intelligence[row['team_name'].lower()] = dict(row)
                if row['team_name_normalized']:
                    self.team_intelligence[row['team_name_normalized'].lower()] = dict(row)
        print(f"✅ {len(self.team_intelligence)} profils team_intelligence chargés")
        
    def find_team_intelligence(self, team_name: str) -> Optional[Dict]:
        """Trouve le profil team_intelligence pour une équipe"""
        # Essai direct
        key = team_name.lower()
        if key in self.team_intelligence:
            return self.team_intelligence[key]
        
        # Essai avec variations courantes
        variations = [
            key.replace(" fc", ""),
            key.replace("fc ", ""),
            key + " fc",
            key.replace(" cf", ""),
            key.replace("cf ", ""),
        ]
        for var in variations:
            if var in self.team_intelligence:
                return self.team_intelligence[var]
                
        return None
        
    def import_team_profiles(self):
        """Importe les équipes dans quantum.team_profiles"""
        print("\n📥 Import des team_profiles...")
        
        with self.conn.cursor() as cur:
            for team in self.audit_data['teams']:
                # Chercher enrichissement team_intelligence
                ti = self.find_team_intelligence(team['name'])
                
                # Construire quantum_dna initial
                quantum_dna = {
                    "context_dna": {
                        "style": ti['current_style'] if ti else None,
                        "style_score": ti['current_style_score'] if ti else None,
                        "home_strength": ti['home_strength'] if ti else None,
                        "away_strength": ti['away_strength'] if ti else None,
                    },
                    "market_dna": {
                        "best_strategy": team['best_strategy'],
                        "total_strategies_tested": len(team.get('all_strategies', {})),
                        "profitable_strategies": sum(1 for s in team.get('all_strategies', {}).values() if s.get('profit', 0) > 0)
                    },
                    "temporal_dna": {},  # À enrichir plus tard
                    "nemesis_dna": {},   # À enrichir plus tard
                    "sentiment_dna": {}, # À enrichir plus tard
                    "psyche_dna": {
                        "unlucky_ratio": team.get('unlucky_pct', 0),
                        "bad_analysis_ratio": team.get('bad_analysis_pct', 0)
                    },
                    "meta_dna": {
                        "source_audit": "audit_complet_99_equipes",
                        "audit_date": self.audit_data.get('timestamp'),
                        "rank": team['rank']
                    },
                    "friction_signatures": []
                }
                
                # Calculer tier
                tier = get_tier(team['rank'], team.get('pnl', 0))
                
                # Calculer losses depuis bets et wins
                losses = team['bets'] - team['wins'] if team['bets'] > team['wins'] else 0
                
                # Calculer unlucky/bad losses
                total_losses = losses
                unlucky_losses = int(total_losses * team.get('unlucky_pct', 0) / 100) if total_losses > 0 else 0
                bad_analysis_losses = total_losses - unlucky_losses
                
                # INSERT avec ON CONFLICT UPDATE
                cur.execute("""
                    INSERT INTO quantum.team_profiles (
                        team_name, team_name_normalized, team_intelligence_id,
                        tier, tier_rank, current_style, style_confidence,
                        total_matches, total_bets, total_wins, total_losses,
                        win_rate, total_pnl, roi,
                        unlucky_losses, bad_analysis_losses, unlucky_pct,
                        quantum_dna, last_audit_at
                    ) VALUES (
                        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW()
                    )
                    ON CONFLICT (team_name) DO UPDATE SET
                        tier = EXCLUDED.tier,
                        tier_rank = EXCLUDED.tier_rank,
                        current_style = COALESCE(EXCLUDED.current_style, quantum.team_profiles.current_style),
                        total_matches = EXCLUDED.total_matches,
                        total_bets = EXCLUDED.total_bets,
                        total_wins = EXCLUDED.total_wins,
                        total_losses = EXCLUDED.total_losses,
                        win_rate = EXCLUDED.win_rate,
                        total_pnl = EXCLUDED.total_pnl,
                        roi = EXCLUDED.roi,
                        unlucky_losses = EXCLUDED.unlucky_losses,
                        bad_analysis_losses = EXCLUDED.bad_analysis_losses,
                        unlucky_pct = EXCLUDED.unlucky_pct,
                        quantum_dna = EXCLUDED.quantum_dna,
                        last_audit_at = NOW(),
                        updated_at = NOW()
                    RETURNING id
                """, (
                    team['name'],
                    ti['team_name_normalized'] if ti else team['name'].lower().replace(' ', '_'),
                    ti['id'] if ti else None,
                    tier,
                    team['rank'],
                    ti['current_style'] if ti else None,
                    ti['current_style_score'] if ti else 50,
                    team['matches'],
                    team['bets'],
                    team['wins'],
                    losses,
                    team.get('wr', 0),
                    team.get('pnl', 0),
                    team.get('roi', round(team.get('pnl', 0) / team['bets'] * 100, 1) if team['bets'] > 0 else 0),
                    unlucky_losses,
                    bad_analysis_losses,
                    team.get('unlucky_pct', 0),
                    json.dumps(quantum_dna)
                ))
                
                self.imported_profiles += 1
                
            self.conn.commit()
            print(f"✅ {self.imported_profiles} team_profiles importés/mis à jour")
            
    def import_team_strategies(self):
        """Importe toutes les stratégies par équipe"""
        print("\n📥 Import des team_strategies...")
        
        with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
            for team in self.audit_data['teams']:
                # Récupérer l'ID du profil
                cur.execute("SELECT id FROM quantum.team_profiles WHERE team_name = %s", (team['name'],))
                result = cur.fetchone()
                profile_id = result['id'] if result else None
                
                strategies = team.get('all_strategies', {})
                best_strategy = team.get('best_strategy')
                
                # Trier par profit pour calculer le rang
                sorted_strategies = sorted(
                    strategies.items(), 
                    key=lambda x: x[1].get('profit', 0), 
                    reverse=True
                )
                
                for rank, (strategy_name, stats) in enumerate(sorted_strategies, 1):
                    is_best = (strategy_name == best_strategy)
                    family = get_strategy_family(strategy_name)
                    
                    # Calculer win_rate
                    bets = stats.get('bets', 0)
                    wins = stats.get('wins', 0)
                    wr = round(wins / bets * 100, 1) if bets > 0 else 0
                    roi = round(stats.get('profit', 0) / bets * 100, 1) if bets > 0 else 0
                    
                    cur.execute("""
                        INSERT INTO quantum.team_strategies (
                            team_profile_id, team_name, strategy_name, strategy_version,
                            is_best_strategy, strategy_rank,
                            bets, wins, losses, win_rate, profit, roi,
                            unlucky_count, bad_analysis_count,
                            source, parameters
                        ) VALUES (
                            %s, %s, %s, '1.0', %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                        )
                        ON CONFLICT (team_name, strategy_name, strategy_version) DO UPDATE SET
                            is_best_strategy = EXCLUDED.is_best_strategy,
                            strategy_rank = EXCLUDED.strategy_rank,
                            bets = EXCLUDED.bets,
                            wins = EXCLUDED.wins,
                            losses = EXCLUDED.losses,
                            win_rate = EXCLUDED.win_rate,
                            profit = EXCLUDED.profit,
                            roi = EXCLUDED.roi,
                            unlucky_count = EXCLUDED.unlucky_count,
                            bad_analysis_count = EXCLUDED.bad_analysis_count,
                            updated_at = NOW()
                    """, (
                        profile_id,
                        team['name'],
                        strategy_name,
                        is_best,
                        rank,
                        bets,
                        wins,
                        bets - wins,  # losses
                        wr,
                        stats.get('profit', 0),
                        roi,
                        stats.get('unlucky', 0),
                        stats.get('bad', 0),
                        'audit_99_equipes',
                        json.dumps({"family": family})
                    ))
                    
                    self.imported_strategies += 1
                    
            self.conn.commit()
            print(f"✅ {self.imported_strategies} team_strategies importées")
            
    def populate_strategy_catalog(self):
        """Agrège les stats dans strategy_catalog"""
        print("\n📥 Peuplement du strategy_catalog...")
        
        with self.conn.cursor() as cur:
            cur.execute("""
                INSERT INTO quantum.strategy_catalog (
                    strategy_code, strategy_name, strategy_family,
                    total_teams_applied, total_bets, total_wins,
                    global_win_rate, global_pnl, global_roi,
                    verdict, source_audit
                )
                SELECT 
                    strategy_name,
                    strategy_name,
                    (parameters->>'family')::VARCHAR,
                    COUNT(DISTINCT team_name),
                    SUM(bets),
                    SUM(wins),
                    ROUND(SUM(wins)::NUMERIC / NULLIF(SUM(bets), 0) * 100, 1),
                    SUM(profit),
                    ROUND(SUM(profit)::NUMERIC / NULLIF(SUM(bets), 0) * 100, 1),
                    CASE 
                        WHEN SUM(profit) >= 100 THEN 'CHAMPION'
                        WHEN SUM(profit) >= 50 THEN 'EXCELLENT'
                        WHEN SUM(profit) >= 20 THEN 'TRÈS BON'
                        WHEN SUM(profit) >= 0 THEN 'POSITIF'
                        ELSE 'À ÉVITER'
                    END,
                    'audit_99_equipes'
                FROM quantum.team_strategies
                GROUP BY strategy_name, parameters->>'family'
                ON CONFLICT (strategy_code) DO UPDATE SET
                    total_teams_applied = EXCLUDED.total_teams_applied,
                    total_bets = EXCLUDED.total_bets,
                    total_wins = EXCLUDED.total_wins,
                    global_win_rate = EXCLUDED.global_win_rate,
                    global_pnl = EXCLUDED.global_pnl,
                    global_roi = EXCLUDED.global_roi,
                    verdict = EXCLUDED.verdict,
                    updated_at = NOW()
            """)
            
            count = cur.rowcount
            self.conn.commit()
            print(f"✅ {count} stratégies agrégées dans le catalog")
            
    def create_audit_snapshot(self):
        """Crée un snapshot de l'audit"""
        print("\n📥 Création du snapshot d'audit...")
        
        summary = self.audit_data['summary']
        
        with self.conn.cursor() as cur:
            cur.execute("""
                INSERT INTO quantum.audit_snapshots (
                    audit_name, audit_version, audit_date,
                    total_teams, total_bets, total_wins,
                    global_win_rate, global_pnl,
                    unlucky_pct, bad_analysis_pct,
                    source_file, raw_summary
                ) VALUES (
                    'audit_complet_99_equipes', '1.0', %s,
                    %s, %s, %s, %s, %s, %s, %s, %s, %s
                )
            """, (
                self.audit_data.get('timestamp', datetime.now().isoformat()),
                summary['total_teams'],
                summary['total_bets'],
                summary['total_wins'],
                summary['overall_wr'],
                summary['total_pnl'],
                summary['unlucky_pct'],
                summary['bad_analysis_pct'],
                AUDIT_JSON_PATH,
                json.dumps(summary)
            ))
            
            self.conn.commit()
            print("✅ Snapshot d'audit créé")
            
    def enrich_from_tracking_clv(self):
        """Enrichit market_performance depuis tracking_clv_picks"""
        print("\n📥 Enrichissement depuis tracking_clv_picks...")
        
        with self.conn.cursor() as cur:
            # Agrège les stats par équipe et marché
            cur.execute("""
                INSERT INTO quantum.market_performance (
                    team_name, market_type, market_family,
                    total_picks, wins, losses, pending, win_rate,
                    total_pnl, avg_odds, avg_clv, avg_edge, avg_diamond_score
                )
                WITH team_market_stats AS (
                    SELECT 
                        team,
                        market_type,
                        COUNT(*) as total_picks,
                        SUM(CASE WHEN is_winner = true THEN 1 ELSE 0 END) as wins,
                        SUM(CASE WHEN is_winner = false THEN 1 ELSE 0 END) as losses,
                        SUM(CASE WHEN is_resolved = false THEN 1 ELSE 0 END) as pending,
                        ROUND(AVG(CASE WHEN is_winner THEN 100.0 ELSE 0 END), 1) as win_rate,
                        ROUND(SUM(COALESCE(profit_loss, 0))::NUMERIC, 2) as total_pnl,
                        ROUND(AVG(odds_taken)::NUMERIC, 3) as avg_odds,
                        ROUND(AVG(clv_percentage)::NUMERIC, 3) as avg_clv,
                        ROUND(AVG(edge_pct)::NUMERIC, 3) as avg_edge,
                        ROUND(AVG(diamond_score)::NUMERIC, 1) as avg_diamond
                    FROM (
                        SELECT home_team as team, market_type, is_winner, is_resolved, 
                               profit_loss, odds_taken, clv_percentage, edge_pct, diamond_score
                        FROM tracking_clv_picks WHERE home_team IS NOT NULL
                        UNION ALL
                        SELECT away_team as team, market_type, is_winner, is_resolved,
                               profit_loss, odds_taken, clv_percentage, edge_pct, diamond_score
                        FROM tracking_clv_picks WHERE away_team IS NOT NULL
                    ) combined
                    WHERE team IN (SELECT team_name FROM quantum.team_profiles)
                    GROUP BY team, market_type
                    HAVING COUNT(*) >= 3
                )
                SELECT 
                    team,
                    market_type,
                    CASE 
                        WHEN market_type LIKE 'over_%' OR market_type LIKE 'under_%' THEN 'GOALS'
                        WHEN market_type LIKE 'btts_%' THEN 'BTTS'
                        WHEN market_type IN ('home', 'away', 'draw') THEN '1X2'
                        WHEN market_type LIKE 'dc_%' THEN 'DOUBLE_CHANCE'
                        WHEN market_type LIKE 'dnb_%' THEN 'DNB'
                        ELSE 'OTHER'
                    END as market_family,
                    total_picks, wins, losses, pending, win_rate,
                    total_pnl, avg_odds, avg_clv, avg_edge, avg_diamond
                FROM team_market_stats
                ON CONFLICT (team_name, market_type) DO UPDATE SET
                    total_picks = EXCLUDED.total_picks,
                    wins = EXCLUDED.wins,
                    losses = EXCLUDED.losses,
                    pending = EXCLUDED.pending,
                    win_rate = EXCLUDED.win_rate,
                    total_pnl = EXCLUDED.total_pnl,
                    avg_odds = EXCLUDED.avg_odds,
                    avg_clv = EXCLUDED.avg_clv,
                    avg_edge = EXCLUDED.avg_edge,
                    avg_diamond_score = EXCLUDED.avg_diamond_score,
                    updated_at = NOW()
            """)
            
            count = cur.rowcount
            self.conn.commit()
            print(f"✅ {count} entrées market_performance créées/mises à jour")
            
    def link_team_profiles_to_market_performance(self):
        """Lie les market_performance aux team_profiles"""
        print("\n📥 Liaison market_performance → team_profiles...")
        
        with self.conn.cursor() as cur:
            cur.execute("""
                UPDATE quantum.market_performance mp
                SET team_profile_id = tp.id
                FROM quantum.team_profiles tp
                WHERE mp.team_name = tp.team_name
                AND mp.team_profile_id IS NULL
            """)
            
            count = cur.rowcount
            self.conn.commit()
            print(f"✅ {count} liaisons créées")
            
    def print_summary(self):
        """Affiche un résumé de l'import"""
        print("\n" + "="*80)
        print("📊 RÉSUMÉ DE L'IMPORT QUANTUM PHASE 1")
        print("="*80)
        
        with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
            # Team profiles
            cur.execute("SELECT COUNT(*), SUM(total_pnl) FROM quantum.team_profiles")
            r = cur.fetchone()
            print(f"   Team Profiles: {r['count']} équipes, P&L total: {r['sum']}u")
            
            # Par tier
            cur.execute("""
                SELECT tier, COUNT(*), ROUND(SUM(total_pnl)::NUMERIC, 1) as pnl
                FROM quantum.team_profiles
                GROUP BY tier ORDER BY 
                    CASE tier WHEN 'ELITE' THEN 1 WHEN 'GOLD' THEN 2 
                              WHEN 'SILVER' THEN 3 WHEN 'BRONZE' THEN 4 ELSE 5 END
            """)
            print("\n   Par Tier:")
            for row in cur.fetchall():
                print(f"      {row['tier']}: {row['count']} équipes, {row['pnl']}u")
            
            # Team strategies
            cur.execute("SELECT COUNT(*), COUNT(DISTINCT team_name), COUNT(DISTINCT strategy_name) FROM quantum.team_strategies")
            r = cur.fetchone()
            print(f"\n   Team Strategies: {r['count']} entrées ({r['count_1']} équipes × ~{r['count']//max(r['count_1'],1)} strats)")
            
            # Best strategies
            cur.execute("""
                SELECT strategy_name, COUNT(*) as teams, SUM(profit) as total_profit
                FROM quantum.team_strategies WHERE is_best_strategy = true
                GROUP BY strategy_name ORDER BY teams DESC LIMIT 5
            """)
            print("\n   Top 5 Best Strategies:")
            for row in cur.fetchall():
                print(f"      {row['strategy_name']}: {row['teams']} équipes, +{row['total_profit']}u")
            
            # Strategy catalog
            cur.execute("""
                SELECT verdict, COUNT(*), ROUND(SUM(global_pnl)::NUMERIC, 1) as pnl
                FROM quantum.strategy_catalog GROUP BY verdict
                ORDER BY CASE verdict 
                    WHEN 'CHAMPION' THEN 1 WHEN 'EXCELLENT' THEN 2 
                    WHEN 'TRÈS BON' THEN 3 WHEN 'POSITIF' THEN 4 ELSE 5 END
            """)
            print("\n   Strategy Catalog par verdict:")
            for row in cur.fetchall():
                print(f"      {row['verdict']}: {row['count']} stratégies, {row['pnl']}u")
            
            # Market performance
            cur.execute("SELECT COUNT(*), COUNT(DISTINCT team_name) FROM quantum.market_performance")
            r = cur.fetchone()
            print(f"\n   Market Performance: {r['count']} entrées pour {r['count_1']} équipes")
            
        print("\n" + "="*80)
        print("✅ IMPORT QUANTUM PHASE 1 TERMINÉ !")
        print("="*80)


def main():
    print("""
╔═══════════════════════════════════════════════════════════════════════════════════════════════════════════════╗
║     🔬 QUANTUM ADN - PHASE 1 - IMPORT                                                                         ║
╚═══════════════════════════════════════════════════════════════════════════════════════════════════════════════╝
    """)
    
    importer = QuantumImporter()
    
    try:
        # 1. Connexion
        importer.connect()
        
        # 2. Charger les sources
        importer.load_audit_json()
        importer.load_team_intelligence()
        
        # 3. Import principal
        importer.import_team_profiles()
        importer.import_team_strategies()
        
        # 4. Agrégation
        importer.populate_strategy_catalog()
        
        # 5. Enrichissement depuis tracking_clv
        importer.enrich_from_tracking_clv()
        importer.link_team_profiles_to_market_performance()
        
        # 6. Snapshot
        importer.create_audit_snapshot()
        
        # 7. Résumé
        importer.print_summary()
        
    except Exception as e:
        print(f"\n❌ ERREUR: {e}")
        import traceback
        traceback.print_exc()
        
    finally:
        importer.close()


if __name__ == "__main__":
    main()
