#!/usr/bin/env python3
"""
╔═══════════════════════════════════════════════════════════════════════════════╗
║           TEAM-CENTRIC NARRATIVE PROFILE GENERATOR V1.1                       ║
║                                                                               ║
║  Philosophie Mon_PS:                                                          ║
║  • ÉQUIPE au centre (comme un trou noir)                                      ║
║  • Chaque équipe = 1 ADN = 1 empreinte digitale unique                       ║
║  • Les marchés sont des CONSÉQUENCES de l'ADN, pas l'inverse                 ║
╚═══════════════════════════════════════════════════════════════════════════════╝
"""

import psycopg2
from psycopg2.extras import RealDictCursor, Json
import json
from datetime import datetime
from typing import Dict, List, Any

DB_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "database": "monps_db",
    "user": "monps_user",
    "password": "monps_secure_password_2024"
}

def safe_get(d: dict, *keys, default=0):
    """Récupère une valeur imbriquée de façon sécurisée"""
    result = d
    for key in keys:
        if isinstance(result, dict):
            result = result.get(key, default)
        else:
            return default
    return result if result is not None else default

# ═══════════════════════════════════════════════════════════════════════════════
# ARCHETYPES D'ÉQUIPES
# ═══════════════════════════════════════════════════════════════════════════════

TEAM_ARCHETYPES = {
    "FORTRESS": {
        "description": "Forteresse défensive - Clean sheets machine",
        "primary_exploit": ["btts_no", "under_25", "home_clean_sheet"],
        "avoid": ["over_35", "btts_yes"]
    },
    "GOAL_MACHINE": {
        "description": "Machine à buts - Over specialist",
        "primary_exploit": ["over_25", "over_35", "team_over_15"],
        "avoid": ["under_25", "btts_no"]
    },
    "GLASS_CANNON": {
        "description": "Canon de verre - Attaque forte, défense faible",
        "primary_exploit": ["btts_yes", "over_25", "over_35"],
        "avoid": ["clean_sheet", "under_25"]
    },
    "DIESEL_ENGINE": {
        "description": "Moteur diesel - Monte en puissance en 2ème MT",
        "primary_exploit": ["second_half_over", "goal_75_90"],
        "avoid": ["first_half_over_15"]
    },
    "SPRINTER": {
        "description": "Sprinter - Démarre fort, s'essouffle",
        "primary_exploit": ["first_half_over_15", "goal_before_30"],
        "avoid": ["second_half_bets"]
    },
    "MENTAL_GIANT": {
        "description": "Géant mental - Killer instinct",
        "primary_exploit": ["home_win", "team_win", "handicap_cover"],
        "avoid": ["draw", "opponent_dnb"]
    },
    "MENTAL_FRAGILE": {
        "description": "Mental fragile - Craque sous pression",
        "primary_exploit": ["btts_yes", "draw", "opponent_dnb"],
        "avoid": ["team_handicap"]
    },
    "HOME_BEAST": {
        "description": "Bête à domicile - Imbattable chez soi",
        "primary_exploit": ["home_win", "home_over_15"],
        "avoid": ["away_bets"]
    },
    "ROAD_WARRIOR": {
        "description": "Guerrier des routes - Performant à l'extérieur",
        "primary_exploit": ["away_win", "away_dnb"],
        "avoid": []
    },
    "SET_PIECE_SPECIALIST": {
        "description": "Spécialiste coups de pied arrêtés",
        "primary_exploit": ["corners_over", "team_corners"],
        "avoid": []
    },
    "COUNTER_ATTACK_KING": {
        "description": "Roi du contre - Létal en transition",
        "primary_exploit": ["away_goals", "btts_yes"],
        "avoid": []
    },
    "BALANCED_WARRIOR": {
        "description": "Guerrier équilibré - Polyvalent",
        "primary_exploit": ["context_dependent"],
        "avoid": []
    },
    "LUCKY_CHARM": {
        "description": "Porte-bonheur - Surperforme les xG",
        "primary_exploit": ["team_win", "team_goals"],
        "avoid": []
    },
    "UNLUCKY_SOLDIER": {
        "description": "Soldat malchanceux - Sous-performe les xG",
        "primary_exploit": ["value_on_team"],
        "avoid": ["against_form"]
    }
}


class TeamNarrativeGenerator:
    def __init__(self):
        self.conn = None
        self.scenarios = []
        self.strategies = []
        
    def connect(self):
        self.conn = psycopg2.connect(**DB_CONFIG)
        print("✅ Connexion DB établie")
        
    def load_scenarios_and_strategies(self):
        with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT * FROM quantum.scenario_catalog WHERE is_active = true")
            self.scenarios = cur.fetchall()
            cur.execute("SELECT * FROM quantum.strategy_catalog")
            self.strategies = cur.fetchall()
        print(f"📋 Chargé: {len(self.scenarios)} scénarios, {len(self.strategies)} stratégies")
    
    def determine_archetype(self, dna: dict) -> str:
        """Détermine l'archétype basé sur l'ADN"""
        scores = {}
        
        # Clutch/Mental DNA
        clutch = dna.get('clutch_dna', {}) or {}
        mental_profile = clutch.get('mental_profile', 'STABLE')
        killer_instinct = safe_get(clutch, 'killer_instinct', default=50)
        panic_factor = safe_get(clutch, 'panic_factor', default=50)
        
        if mental_profile == 'KILLER' or killer_instinct > 75:
            scores['MENTAL_GIANT'] = scores.get('MENTAL_GIANT', 0) + 30
        if panic_factor > 50 or mental_profile == 'FRAGILE':
            scores['MENTAL_FRAGILE'] = scores.get('MENTAL_FRAGILE', 0) + 30
            
        # Temporal DNA
        temporal = dna.get('temporal_dna', {}) or {}
        diesel_factor = safe_get(temporal, 'diesel_factor', default=0.5)
        first_half_pct = safe_get(temporal, 'first_half_goals_pct', default=50)
        
        if diesel_factor > 0.6:
            scores['DIESEL_ENGINE'] = scores.get('DIESEL_ENGINE', 0) + 25
        if first_half_pct > 55:
            scores['SPRINTER'] = scores.get('SPRINTER', 0) + 25
            
        # Luck DNA
        luck = dna.get('luck_dna', {}) or {}
        luck_profile = luck.get('luck_profile', 'NEUTRAL')
        total_luck = safe_get(luck, 'total_luck', default=0)
        
        if luck_profile == 'LUCKY' or total_luck > 5:
            scores['LUCKY_CHARM'] = scores.get('LUCKY_CHARM', 0) + 20
        if luck_profile == 'UNLUCKY' or total_luck < -5:
            scores['UNLUCKY_SOLDIER'] = scores.get('UNLUCKY_SOLDIER', 0) + 20
            
        # Context DNA
        context = dna.get('context_dna', {}) or {}
        home_strength = safe_get(context, 'home_strength', default=50)
        away_strength = safe_get(context, 'away_strength', default=50)
        
        if home_strength > 70:
            scores['HOME_BEAST'] = scores.get('HOME_BEAST', 0) + 25
        if away_strength > 50:
            scores['ROAD_WARRIOR'] = scores.get('ROAD_WARRIOR', 0) + 20
            
        # Psyche DNA
        psyche = dna.get('psyche_dna', {}) or {}
        attack_index = safe_get(psyche, 'attacking_tendency', default=50)
        defense_index = safe_get(psyche, 'defensive_tendency', default=50)
        
        if attack_index > 70 and defense_index < 40:
            scores['GLASS_CANNON'] = scores.get('GLASS_CANNON', 0) + 30
        if attack_index > 70:
            scores['GOAL_MACHINE'] = scores.get('GOAL_MACHINE', 0) + 25
        if defense_index > 70:
            scores['FORTRESS'] = scores.get('FORTRESS', 0) + 25
            
        # Corner DNA
        corner = dna.get('corner_dna', {}) or {}
        corner_profile = corner.get('profile', 'NEUTRAL')
        corner_dominance = safe_get(corner, 'corner_dominance', default=0)
        
        if corner_profile == 'CORNER_DOMINANT' or corner_dominance > 0.5:
            scores['SET_PIECE_SPECIALIST'] = scores.get('SET_PIECE_SPECIALIST', 0) + 20
            
        # Tactical DNA
        tactical = dna.get('tactical_dna', {}) or {}
        counter_efficiency = safe_get(tactical, 'counter_attack_efficiency', default=50)
        
        if counter_efficiency > 65:
            scores['COUNTER_ATTACK_KING'] = scores.get('COUNTER_ATTACK_KING', 0) + 25
            
        # Default
        if not scores:
            scores['BALANCED_WARRIOR'] = 50
            
        return max(scores.items(), key=lambda x: x[1])[0]
    
    def generate_exploit_markets(self, dna: dict, archetype: str, market_perf: list) -> list:
        """Génère les marchés exploitables"""
        exploit_markets = []
        
        # Marchés de l'archétype
        archetype_data = TEAM_ARCHETYPES.get(archetype, {})
        for m in archetype_data.get('primary_exploit', []):
            exploit_markets.append({"market": m, "source": "archetype", "confidence": "HIGH"})
        
        # Marchés historiquement profitables
        for mp in (market_perf or []):
            pnl = float(mp.get('total_pnl', 0) or 0)
            wr = float(mp.get('win_rate', 0) or 0)
            picks = int(mp.get('total_picks', 0) or 0)
            
            if pnl > 0 and wr > 55 and picks >= 3:
                exploit_markets.append({
                    "market": mp['market_type'],
                    "historical_wr": wr,
                    "historical_pnl": pnl,
                    "picks": picks,
                    "source": "historical",
                    "confidence": "VERY_HIGH" if wr > 70 else "HIGH"
                })
        
        return exploit_markets[:8]
    
    def generate_avoid_markets(self, dna: dict, archetype: str, market_perf: list) -> list:
        """Génère les marchés à éviter"""
        avoid_markets = []
        
        archetype_data = TEAM_ARCHETYPES.get(archetype, {})
        for m in archetype_data.get('avoid', []):
            avoid_markets.append({"market": m, "reason": "archetype_mismatch"})
        
        for mp in (market_perf or []):
            pnl = float(mp.get('total_pnl', 0) or 0)
            picks = int(mp.get('total_picks', 0) or 0)
            
            if pnl < -5 and picks > 3:
                avoid_markets.append({
                    "market": mp['market_type'],
                    "historical_pnl": pnl,
                    "reason": "historically_unprofitable"
                })
        
        return avoid_markets[:5]
    
    def match_optimal_scenarios(self, dna: dict, archetype: str) -> list:
        """Identifie les scénarios optimaux"""
        optimal = []
        
        scenario_archetype_map = {
            'GOAL_MACHINE': ['TOTAL_CHAOS', 'SNIPER_DUEL', 'GLASS_CANNON'],
            'FORTRESS': ['ATTRITION_WAR', 'THE_SIEGE', 'CONSERVATIVE_WALL'],
            'DIESEL_ENGINE': ['DIESEL_DUEL', 'LATE_PUNISHMENT', 'CLUTCH_KILLER'],
            'SPRINTER': ['EXPLOSIVE_START'],
            'MENTAL_GIANT': ['KILLER_INSTINCT', 'PREY_HUNT'],
            'MENTAL_FRAGILE': ['COLLAPSE_ALERT', 'NOTHING_TO_LOSE'],
            'HOME_BEAST': ['PRESSING_DEATH'],
            'GLASS_CANNON': ['TOTAL_CHAOS', 'GLASS_CANNON', 'SNIPER_DUEL'],
        }
        
        matched_codes = scenario_archetype_map.get(archetype, [])
        
        for scenario in self.scenarios:
            code = scenario['scenario_code']
            if code in matched_codes:
                optimal.append({
                    "scenario_code": code,
                    "match_score": 80,
                    "expected_roi": float(scenario.get('historical_roi', 0) or 0)
                })
        
        optimal.sort(key=lambda x: x['expected_roi'], reverse=True)
        return optimal[:5]
    
    def match_optimal_strategies(self, dna: dict, archetype: str, tier: str) -> list:
        """Identifie les stratégies optimales"""
        optimal = []
        
        strategy_archetype_map = {
            'GOAL_MACHINE': ['CONVERGENCE_OVER_MC_55', 'CONVERGENCE_OVER_MC_60', 'MC_PURE_60'],
            'FORTRESS': ['CONVERGENCE_UNDER_PURE', 'UNDER_35_PURE', 'BTTS_NO_PURE'],
            'MENTAL_GIANT': ['TIER_1_SNIPER', 'ULTIMATE_SNIPER', 'SCORE_SNIPER_34'],
            'DIESEL_ENGINE': ['TEAM_GOALS_2H', 'GOAL_75_90'],
        }
        
        matched_codes = strategy_archetype_map.get(archetype, ['QUANT_BEST_MARKET'])
        
        for strategy in self.strategies:
            code = strategy['strategy_code']
            if code in matched_codes or code == 'QUANT_BEST_MARKET':
                optimal.append({
                    "strategy_code": code,
                    "match_score": 80 if code in matched_codes else 50,
                    "min_edge": float(strategy.get('min_edge', 0) or 0)
                })
        
        optimal.sort(key=lambda x: x['match_score'], reverse=True)
        return optimal[:5]
    
    def generate_fingerprint(self, team_name: str, dna: dict, archetype: str) -> str:
        """Génère l'empreinte digitale unique"""
        abbrev = {
            'FORTRESS': 'FRT', 'GOAL_MACHINE': 'GOL', 'GLASS_CANNON': 'GLS',
            'DIESEL_ENGINE': 'DSL', 'SPRINTER': 'SPR', 'MENTAL_GIANT': 'MGT',
            'MENTAL_FRAGILE': 'MFR', 'HOME_BEAST': 'HMB', 'ROAD_WARRIOR': 'RDW',
            'SET_PIECE_SPECIALIST': 'SPS', 'COUNTER_ATTACK_KING': 'CTK',
            'BALANCED_WARRIOR': 'BAL', 'LUCKY_CHARM': 'LCK', 'UNLUCKY_SOLDIER': 'UNL'
        }
        
        parts = [abbrev.get(archetype, 'UNK')]
        
        clutch = dna.get('clutch_dna', {}) or {}
        parts.append(str(clutch.get('mental_profile', 'S'))[:1])
        
        luck = dna.get('luck_dna', {}) or {}
        parts.append(str(luck.get('luck_profile', 'N'))[:1])
        
        temporal = dna.get('temporal_dna', {}) or {}
        diesel = safe_get(temporal, 'diesel_factor', default=0.5)
        parts.append('D' if diesel > 0.6 else 'S' if diesel < 0.4 else 'B')
        
        name_hash = ''.join([c for c in team_name[:3].upper() if c.isalpha()])
        parts.append(name_hash)
        
        return '-'.join(parts)
    
    def generate_narrative(self, team_name: str, tier: str, dna: dict, archetype: str,
                          exploit_markets: list, optimal_scenarios: list) -> str:
        """Génère le profil narratif"""
        archetype_data = TEAM_ARCHETYPES.get(archetype, {})
        archetype_desc = archetype_data.get('description', 'Profil unique')
        
        parts = [f"🎯 {team_name} [{tier}] - {archetype_desc}"]
        
        # Mental
        clutch = dna.get('clutch_dna', {}) or {}
        mental = clutch.get('mental_profile', 'STABLE')
        killer = safe_get(clutch, 'killer_instinct', default=50)
        panic = safe_get(clutch, 'panic_factor', default=50)
        
        if mental == 'KILLER':
            parts.append(f"💪 Mental: TUEUR ({killer}%) - Finit le travail")
        elif mental == 'FRAGILE':
            parts.append(f"😰 Mental: FRAGILE ({panic}%) - Craque sous pression")
        else:
            parts.append(f"🧠 Mental: STABLE - Régulier")
            
        # Temporal
        temporal = dna.get('temporal_dna', {}) or {}
        diesel = safe_get(temporal, 'diesel_factor', default=0.5)
        if diesel > 0.6:
            parts.append(f"🐢 Tempo: DIESEL ({diesel*100:.0f}%) - Fort en 2ème MT")
        elif diesel < 0.4:
            parts.append(f"🚀 Tempo: SPRINTER - Fort en 1ère MT")
        else:
            parts.append(f"⚖️ Tempo: ÉQUILIBRÉ")
            
        # Luck
        luck = dna.get('luck_dna', {}) or {}
        luck_profile = luck.get('luck_profile', 'NEUTRAL')
        luck_score = safe_get(luck, 'total_luck', default=0)
        if luck_profile == 'LUCKY':
            parts.append(f"🍀 Chance: CHANCEUX (+{luck_score:.1f})")
        elif luck_profile == 'UNLUCKY':
            parts.append(f"😢 Chance: MALCHANCEUX ({luck_score:.1f})")
            
        # Exploits
        if exploit_markets:
            markets_str = ', '.join([m.get('market', str(m)) if isinstance(m, dict) else str(m) for m in exploit_markets[:3]])
            parts.append(f"💰 EXPLOIT: {markets_str}")
            
        # Scénarios
        if optimal_scenarios:
            scenarios_str = ', '.join([s['scenario_code'] for s in optimal_scenarios[:2]])
            parts.append(f"🎭 SCÉNARIOS: {scenarios_str}")
        
        return '\n'.join(parts)
    
    def process_all_teams(self):
        """Traite toutes les équipes"""
        print("\n" + "="*70)
        print("🧬 GÉNÉRATION DES PROFILS NARRATIFS TEAM-CENTRIC")
        print("="*70)
        
        with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT tp.id, tp.team_name, tp.tier, tp.quantum_dna,
                       (SELECT json_agg(mp.*) FROM quantum.market_performance mp 
                        WHERE mp.team_name = tp.team_name) as market_perf
                FROM quantum.team_profiles tp
                WHERE tp.quantum_dna IS NOT NULL
                ORDER BY tp.tier, tp.team_name
            """)
            teams = cur.fetchall()
            
        print(f"\n📊 {len(teams)} équipes à traiter")
        
        updated = 0
        archetypes_count = {}
        
        for team in teams:
            team_name = team['team_name']
            tier = team['tier'] or 'STANDARD'
            dna = team['quantum_dna'] or {}
            market_perf = team['market_perf'] or []
            
            # 1. Archétype
            archetype = self.determine_archetype(dna)
            archetypes_count[archetype] = archetypes_count.get(archetype, 0) + 1
            
            # 2. Marchés exploitables
            exploit_markets = self.generate_exploit_markets(dna, archetype, market_perf)
            
            # 3. Marchés à éviter
            avoid_markets = self.generate_avoid_markets(dna, archetype, market_perf)
            
            # 4. Scénarios optimaux
            optimal_scenarios = self.match_optimal_scenarios(dna, archetype)
            
            # 5. Stratégies optimales
            optimal_strategies = self.match_optimal_strategies(dna, archetype, tier)
            
            # 6. Fingerprint
            fingerprint = self.generate_fingerprint(team_name, dna, archetype)
            
            # 7. Narratif
            narrative = self.generate_narrative(team_name, tier, dna, archetype, exploit_markets, optimal_scenarios)
            
            # 8. Betting identity
            betting_identity = {
                "philosophy": "TEAM_CENTRIC",
                "archetype": archetype,
                "mental": (dna.get('clutch_dna', {}) or {}).get('mental_profile', 'STABLE'),
                "luck": (dna.get('luck_dna', {}) or {}).get('luck_profile', 'NEUTRAL'),
                "temporal": "DIESEL" if safe_get(dna, 'temporal_dna', 'diesel_factor', default=0.5) > 0.6 else "BALANCED",
                "updated": datetime.now().isoformat()
            }
            
            # 9. Update
            with self.conn.cursor() as cur:
                cur.execute("""
                    UPDATE quantum.team_profiles
                    SET team_archetype = %s,
                        dna_fingerprint = %s,
                        narrative_profile = %s,
                        exploit_markets = %s,
                        avoid_markets = %s,
                        optimal_scenarios = %s,
                        optimal_strategies = %s,
                        betting_identity = %s,
                        updated_at = NOW()
                    WHERE team_name = %s
                """, (
                    archetype, fingerprint, narrative,
                    Json(exploit_markets), Json(avoid_markets),
                    Json(optimal_scenarios), Json(optimal_strategies),
                    Json(betting_identity), team_name
                ))
                
            updated += 1
            if updated % 25 == 0:
                print(f"   ✅ {updated}/{len(teams)} équipes...")
                
        self.conn.commit()
        
        print(f"\n✅ {updated} équipes mises à jour")
        print("\n��️ Distribution des archétypes:")
        for arch, count in sorted(archetypes_count.items(), key=lambda x: -x[1]):
            print(f"   {arch}: {count}")
            
    def show_examples(self, n: int = 5):
        """Affiche des exemples"""
        print("\n" + "="*70)
        print("🎯 EXEMPLES DE PROFILS NARRATIFS")
        print("="*70)
        
        with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT team_name, tier, team_archetype, dna_fingerprint, 
                       narrative_profile, exploit_markets
                FROM quantum.team_profiles
                WHERE narrative_profile IS NOT NULL
                ORDER BY total_pnl DESC NULLS LAST
                LIMIT %s
            """, (n,))
            
            for team in cur.fetchall():
                print(f"\n{'─'*70}")
                print(f"📋 {team['team_name']} | {team['dna_fingerprint']}")
                print(f"{'─'*70}")
                print(team['narrative_profile'])


def main():
    print("""
╔═══════════════════════════════════════════════════════════════════════════════╗
║           TEAM-CENTRIC NARRATIVE PROFILE GENERATOR V1.1                       ║
║                                                                               ║
║  "Chaque équipe = 1 ADN = 1 empreinte digitale unique"                       ║
╚═══════════════════════════════════════════════════════════════════════════════╝
    """)
    
    gen = TeamNarrativeGenerator()
    gen.connect()
    gen.load_scenarios_and_strategies()
    gen.process_all_teams()
    gen.show_examples(5)
    print("\n✅ Terminé!")


if __name__ == "__main__":
    main()
