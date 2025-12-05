#!/usr/bin/env python3
"""
╔═══════════════════════════════════════════════════════════════════════════════╗
║     🧠 ADVANCED DYNAMIC CLASH MODEL (ADCM) 2.0 - INSTITUTIONAL QUANT          ║
║                                                                               ║
║  Analyse BIVARIÉE des confrontations:                                        ║
║  • Pace Index: Volume offensif (xG + Big Chances)                            ║
║  • Control Index: Domination territoriale                                    ║
║  • Lethality Index: Efficacité de conversion                                 ║
║  • GameState Profile: Comportement selon le score                            ║
║                                                                               ║
║  5 SCÉNARIOS STRATÉGIQUES:                                                   ║
║  🌪️ TOTAL_CHAOS: Deux équipes offensives, défenses faibles                   ║
║  �� SIEGE: Domination territoriale, bloc bas adverse                         ║
║  🔫 SNIPER_DUEL: Haute efficacité des deux côtés                            ║
║  💤 ATTRITION: Faible intensité, guerre d'usure                             ║
║  🃏 GLASS_CANNON: Attaque forte mais défense vulnérable                      ║
╚═══════════════════════════════════════════════════════════════════════════════╝
"""

import psycopg2
from psycopg2.extras import RealDictCursor
import math
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import json

DB_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "database": "monps_db",
    "user": "monps_user",
    "password": "monps_secure_password_2024"
}


class Scenario(Enum):
    TOTAL_CHAOS = "🌪️ TOTAL_CHAOS"
    SIEGE = "🏰 SIEGE"
    SNIPER_DUEL = "🔫 SNIPER_DUEL"
    ATTRITION = "💤 ATTRITION"
    GLASS_CANNON = "�� GLASS_CANNON"
    CONVERGENCE_OVER = "⚡ CONVERGENCE_OVER"
    CONVERGENCE_UNDER = "🛡️ CONVERGENCE_UNDER"
    UNCERTAIN = "❓ UNCERTAIN"


class Action(Enum):
    SNIPER = "SNIPER"
    NORMAL = "NORMAL"
    SPECULATIVE = "SPECULATIVE"
    SKIP = "SKIP"


@dataclass
class TeamMetrics:
    """Métriques calculées pour une équipe"""
    team_name: str
    league: str
    
    # Pace (Volume/Intensity) - Scale 0-100
    pace_index: float
    xg_for: float
    bc_created: float
    
    # Control - Scale 0-100
    control_index: float
    
    # Lethality (Efficiency) - Scale 0-100
    lethality_index: float
    bc_conversion: float
    shot_quality: float
    
    # Defensive - Scale 0-100
    defensive_solidity: float
    xg_against: float
    
    # GameState
    gamestate_profile: str  # AGGRESSIVE / PASSIVE / BALANCED
    when_drawing_xg: float
    when_trailing_xg: float
    
    # Best Market
    best_market: str
    best_market_roi: float


@dataclass
class ClashResult:
    """Résultat de l'analyse ADCM"""
    home: TeamMetrics
    away: TeamMetrics
    
    # Clash Analysis
    scenario: Scenario
    scenario_confidence: float
    
    # Expected Metrics
    expected_total_goals: float
    expected_volatility: float
    style_convergence: float  # -1 (clash) to +1 (convergence)
    
    # Recommendations
    primary_market: str
    primary_edge: float
    secondary_market: str
    secondary_edge: float
    
    # Decision
    action: Action
    stake: float
    reasoning: str


class ADCMEngine:
    """Advanced Dynamic Clash Model Engine"""
    
    # Thresholds for scenario classification
    PACE_HIGH = 70
    PACE_LOW = 40
    LETHALITY_HIGH = 55
    CONTROL_DIFF_HIGH = 20
    XG_TOTAL_HIGH = 3.0
    XG_TOTAL_LOW = 2.2
    
    # Market odds
    MARKET_ODDS = {
        'over_25': 1.85, 'over_35': 2.40, 'over_15': 1.30,
        'under_25': 2.00, 'under_35': 1.55,
        'btts_yes': 1.80, 'btts_no': 2.00,
    }
    
    def __init__(self):
        self.conn = None
        self.team_data = {}
        
    def connect(self):
        self.conn = psycopg2.connect(**DB_CONFIG)
        print("✅ Connexion DB établie")
        
    def load_team_data(self):
        """Charge toutes les données nécessaires pour les équipes"""
        with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
            # XG Tendencies
            cur.execute("SELECT * FROM team_xg_tendencies")
            xg_data = {row['team_name']: row for row in cur.fetchall()}
            
            # Big Chances
            cur.execute("SELECT * FROM team_big_chances_tendencies")
            bc_data = {row['team_name']: row for row in cur.fetchall()}
            
            # GameState
            cur.execute("SELECT * FROM team_gamestate_stats")
            gs_data = {row['team_name']: row for row in cur.fetchall()}
            
            # Team Market Profiles
            cur.execute("""
                SELECT team_name, market_type, roi, win_rate, is_best_market
                FROM team_market_profiles
                WHERE is_best_market = true AND sample_size >= 8
            """)
            market_data = {}
            for row in cur.fetchall():
                market_data[row['team_name']] = {
                    'best_market': row['market_type'],
                    'roi': float(row['roi'] or 0),
                    'wr': float(row['win_rate'] or 0)
                }
                
        # Merge data
        all_teams = set(xg_data.keys()) | set(bc_data.keys())
        
        for team in all_teams:
            xg = xg_data.get(team, {})
            bc = bc_data.get(team, {})
            gs = gs_data.get(team, {})
            mkt = market_data.get(team, {'best_market': 'over_25', 'roi': 0, 'wr': 50})
            
            self.team_data[team] = {
                'xg': xg,
                'bc': bc,
                'gs': gs,
                'market': mkt
            }
            
        print(f"✅ {len(self.team_data)} équipes chargées avec données complètes")
        
    def calculate_team_metrics(self, team_name: str) -> Optional[TeamMetrics]:
        """Calcule les métriques ADCM pour une équipe"""
        data = self.team_data.get(team_name)
        if not data:
            # Try partial match
            for t in self.team_data:
                if t.lower() in team_name.lower() or team_name.lower() in t.lower():
                    data = self.team_data[t]
                    team_name = t
                    break
                    
        if not data:
            return None
            
        xg = data['xg']
        bc = data['bc']
        gs = data['gs']
        mkt = data['market']
        
        # ═══════════════════════════════════════════════════════════════════════
        # PACE INDEX (0-100): Volume offensif
        # Formule: (xG_for * 20) + (BC_created * 15) + base
        # ═══════════════════════════════════════════════════════════════════════
        xg_for = float(xg.get('avg_xg_for') or 1.2)
        bc_created = float(bc.get('avg_bc_created') or 1.5)
        
        pace_index = min(100, (xg_for * 20) + (bc_created * 15) + 20)
        
        # ═══════════════════════════════════════════════════════════════════════
        # CONTROL INDEX (0-100): Domination du jeu
        # Basé sur: open_play_rate + (100 - defensive_rate)
        # ═══════════════════════════════════════════════════════════════════════
        open_rate = float(xg.get('open_rate') or 50)
        defensive_rate = float(xg.get('defensive_rate') or 50)
        
        control_index = (open_rate * 0.6) + ((100 - defensive_rate) * 0.4)
        
        # ═══════════════════════════════════════════════════════════════════════
        # LETHALITY INDEX (0-100): Efficacité de conversion
        # Formule: bc_conversion_rate * 1.2 + shot_quality * 200
        # ═══════════════════════════════════════════════════════════════════════
        bc_conversion = float(bc.get('bc_conversion_rate') or 45)
        shot_quality = float(bc.get('avg_shot_quality') or 0.10)
        
        lethality_index = min(100, (bc_conversion * 0.8) + (shot_quality * 300))
        
        # ═══════════════════════════════════════════════════════════════════════
        # DEFENSIVE SOLIDITY (0-100): Solidité défensive
        # Formule: 100 - (xG_against * 25) - (BC_conceded * 10)
        # ═══════════════════════════════════════════════════════════════════════
        xg_against = float(xg.get('avg_xg_against') or 1.3)
        bc_conceded = float(bc.get('avg_bc_conceded') or 1.5)
        
        defensive_solidity = max(0, 100 - (xg_against * 25) - (bc_conceded * 10))
        
        # ═══════════════════════════════════════════════════════════════════════
        # GAMESTATE PROFILE: Comportement selon le score
        # ═══════════════════════════════════════════════════════════════════════
        drawing_xg = float(gs.get('gs_drawing_xg') or 0) / max(1, int(gs.get('gs_drawing_time') or 1)) * 90
        trailing_xg = float(gs.get('gs_trailing_xg') or 0) / max(1, int(gs.get('gs_trailing_time') or 1)) * 90
        leading_xg = float(gs.get('gs_leading_xg') or 0) / max(1, int(gs.get('gs_leading_time') or 1)) * 90
        
        if trailing_xg > drawing_xg * 1.3:
            gs_profile = "AGGRESSIVE"
        elif leading_xg < drawing_xg * 0.7:
            gs_profile = "PASSIVE"
        else:
            gs_profile = "BALANCED"
            
        return TeamMetrics(
            team_name=team_name,
            league=xg.get('league', 'Unknown'),
            pace_index=round(pace_index, 1),
            xg_for=xg_for,
            bc_created=bc_created,
            control_index=round(control_index, 1),
            lethality_index=round(lethality_index, 1),
            bc_conversion=bc_conversion,
            shot_quality=shot_quality,
            defensive_solidity=round(defensive_solidity, 1),
            xg_against=xg_against,
            gamestate_profile=gs_profile,
            when_drawing_xg=round(drawing_xg, 2),
            when_trailing_xg=round(trailing_xg, 2),
            best_market=mkt['best_market'],
            best_market_roi=mkt['roi']
        )
        
    def calculate_expected_goals(self, home: TeamMetrics, away: TeamMetrics) -> Tuple[float, float]:
        """
        Calcule les lambdas (buts attendus) avec formule Dixon-Coles simplifiée
        λ_home = (xG_home_for * xG_away_against) ^ 0.5 * home_advantage
        """
        HOME_ADVANTAGE = 1.15
        
        lambda_home = math.sqrt(home.xg_for * away.xg_against) * HOME_ADVANTAGE
        lambda_away = math.sqrt(away.xg_for * home.xg_against)
        
        return round(lambda_home, 2), round(lambda_away, 2)
        
    def calculate_style_convergence(self, home: TeamMetrics, away: TeamMetrics) -> float:
        """
        Calcule la convergence de style (-1 = clash total, +1 = convergence parfaite)
        """
        # Vérifier si les deux équipes ont le même type de best_market
        over_markets = ['over_25', 'over_35', 'btts_yes']
        under_markets = ['under_25', 'under_35', 'btts_no']
        
        home_over = home.best_market in over_markets
        away_over = away.best_market in over_markets
        home_under = home.best_market in under_markets
        away_under = away.best_market in under_markets
        
        if (home_over and away_over) or (home_under and away_under):
            # Convergence parfaite
            return 1.0
        elif (home_over and away_under) or (home_under and away_over):
            # Clash de styles
            return -0.5
        else:
            return 0.0
            
    def classify_scenario(self, home: TeamMetrics, away: TeamMetrics,
                          lambda_home: float, lambda_away: float,
                          convergence: float) -> Tuple[Scenario, float]:
        """
        Classifie le match dans un des 5 scénarios stratégiques
        """
        total_pace = home.pace_index + away.pace_index
        pace_diff = abs(home.pace_index - away.pace_index)
        control_diff = abs(home.control_index - away.control_index)
        avg_lethality = (home.lethality_index + away.lethality_index) / 2
        expected_total = lambda_home + lambda_away
        
        both_weak_defense = home.defensive_solidity < 45 and away.defensive_solidity < 45
        one_strong_defense = home.defensive_solidity > 60 or away.defensive_solidity > 60
        
        # ═══════════════════════════════════════════════════════════════════════
        # SCENARIO 1: TOTAL CHAOS 🌪️
        # Deux équipes à haut volume + défenses faibles
        # ═══════════════════════════════════════════════════════════════════════
        if total_pace > 130 and both_weak_defense and expected_total > 2.8:
            confidence = min(95, 60 + (total_pace - 130) + (3.5 - home.defensive_solidity/10))
            return Scenario.TOTAL_CHAOS, confidence
            
        # ═══════════════════════════════════════════════════════════════════════
        # SCENARIO 2: CONVERGENCE OVER ⚡
        # Les deux équipes ont Over comme best market + stats supportent
        # ═══════════════════════════════════════════════════════════════════════
        if convergence > 0.5 and expected_total > 2.6:
            over_markets = ['over_25', 'over_35', 'btts_yes']
            if home.best_market in over_markets and away.best_market in over_markets:
                confidence = min(95, 70 + convergence * 20 + (expected_total - 2.5) * 10)
                return Scenario.CONVERGENCE_OVER, confidence
                
        # ═══════════════════════════════════════════════════════════════════════
        # SCENARIO 3: CONVERGENCE UNDER 🛡️
        # Les deux équipes ont Under/BTTS No comme best market
        # ═══════════════════════════════════════════════════════════════════════
        if convergence > 0.5 and expected_total < 2.4:
            under_markets = ['under_25', 'under_35', 'btts_no']
            if home.best_market in under_markets and away.best_market in under_markets:
                confidence = min(95, 70 + convergence * 20 + (2.5 - expected_total) * 15)
                return Scenario.CONVERGENCE_UNDER, confidence
                
        # ═══════════════════════════════════════════════════════════════════════
        # SCENARIO 4: SIEGE 🏰
        # Gros écart de contrôle (une équipe domine territorialement)
        # ═══════════════════════════════════════════════════════════════════════
        if control_diff > 20:
            dominant = home if home.control_index > away.control_index else away
            if dominant.defensive_solidity > 50:
                confidence = min(90, 55 + control_diff)
                return Scenario.SIEGE, confidence
                
        # ═══════════════════════════════════════════════════════════════════════
        # SCENARIO 5: SNIPER DUEL 🔫
        # Haute efficacité des deux côtés (lethality élevée)
        # ═══════════════════════════════════════════════════════════════════════
        if avg_lethality > self.LETHALITY_HIGH and home.lethality_index > 50 and away.lethality_index > 50:
            confidence = min(90, 55 + (avg_lethality - 50))
            return Scenario.SNIPER_DUEL, confidence
            
        # ═══════════════════════════════════════════════════════════════════════
        # SCENARIO 6: ATTRITION 💤
        # Faible intensité des deux côtés
        # ═══════════════════════════════════════════════════════════════════════
        if total_pace < 90 and expected_total < 2.3:
            confidence = min(85, 50 + (100 - total_pace) / 2)
            return Scenario.ATTRITION, confidence
            
        # ═══════════════════════════════════════════════════════════════════════
        # SCENARIO 7: GLASS CANNON 🃏
        # Une équipe attaque fort mais défend mal
        # ═══════════════════════════════════════════════════════════════════════
        home_glass = home.pace_index > 60 and home.defensive_solidity < 40
        away_glass = away.pace_index > 60 and away.defensive_solidity < 40
        
        if home_glass or away_glass:
            confidence = 60
            return Scenario.GLASS_CANNON, confidence
            
        # Default
        return Scenario.UNCERTAIN, 40
        
    def get_recommendations(self, scenario: Scenario, home: TeamMetrics, away: TeamMetrics,
                           expected_total: float, convergence: float) -> Tuple[str, float, str, float]:
        """
        Génère les recommandations de paris basées sur le scénario
        """
        primary = None
        primary_edge = 0
        secondary = None
        secondary_edge = 0
        
        if scenario == Scenario.TOTAL_CHAOS:
            primary = 'over_35' if expected_total > 3.2 else 'over_25'
            primary_edge = min(25, (expected_total - 2.5) * 15)
            secondary = 'btts_yes'
            secondary_edge = 15
            
        elif scenario == Scenario.CONVERGENCE_OVER:
            primary = 'over_25'
            primary_edge = min(30, convergence * 20 + (expected_total - 2.5) * 10)
            secondary = 'over_35' if expected_total > 3.0 else 'btts_yes'
            secondary_edge = primary_edge * 0.7
            
        elif scenario == Scenario.CONVERGENCE_UNDER:
            primary = 'under_25'
            primary_edge = min(30, convergence * 20 + (2.5 - expected_total) * 15)
            secondary = 'btts_no'
            secondary_edge = primary_edge * 0.7
            
        elif scenario == Scenario.SIEGE:
            dominant = home if home.control_index > away.control_index else away
            if dominant.lethality_index > 55:
                primary = 'over_25'
                primary_edge = 12
            else:
                primary = 'under_35'
                primary_edge = 15
            secondary = 'btts_no'
            secondary_edge = 10
            
        elif scenario == Scenario.SNIPER_DUEL:
            primary = 'btts_yes'
            primary_edge = 20
            secondary = 'over_25'
            secondary_edge = 15
            
        elif scenario == Scenario.ATTRITION:
            primary = 'under_25'
            primary_edge = 18
            secondary = 'btts_no'
            secondary_edge = 12
            
        elif scenario == Scenario.GLASS_CANNON:
            primary = 'btts_yes'
            primary_edge = 15
            secondary = 'over_25'
            secondary_edge = 10
            
        else:  # UNCERTAIN
            # Suivre le leader (meilleur ROI)
            leader = home if home.best_market_roi > away.best_market_roi else away
            primary = leader.best_market
            primary_edge = 5
            secondary = None
            secondary_edge = 0
            
        return primary, primary_edge, secondary, secondary_edge
        
    def determine_action(self, scenario: Scenario, confidence: float, 
                        primary_edge: float, convergence: float) -> Tuple[Action, float]:
        """
        Détermine l'action et le stake recommandé
        """
        # SNIPER: Haute confiance + convergence + edge élevé
        if confidence >= 75 and primary_edge >= 20 and scenario in [
            Scenario.CONVERGENCE_OVER, Scenario.CONVERGENCE_UNDER, Scenario.TOTAL_CHAOS
        ]:
            return Action.SNIPER, 3.0
            
        # NORMAL: Bonne confiance
        if confidence >= 60 and primary_edge >= 12:
            return Action.NORMAL, 2.0
            
        # SPECULATIVE: Clash de styles ou incertain
        if convergence < 0 or scenario == Scenario.UNCERTAIN:
            return Action.SPECULATIVE, 1.0
            
        # SKIP: Pas assez de signal
        if confidence < 50 or primary_edge < 8:
            return Action.SKIP, 0
            
        return Action.NORMAL, 1.5
        
    def analyze_match(self, home_team: str, away_team: str) -> Optional[ClashResult]:
        """
        Analyse complète d'un match avec le modèle ADCM
        """
        home = self.calculate_team_metrics(home_team)
        away = self.calculate_team_metrics(away_team)
        
        if not home or not away:
            return None
            
        # Calculs
        lambda_home, lambda_away = self.calculate_expected_goals(home, away)
        expected_total = lambda_home + lambda_away
        convergence = self.calculate_style_convergence(home, away)
        
        # Classification
        scenario, confidence = self.classify_scenario(
            home, away, lambda_home, lambda_away, convergence
        )
        
        # Recommendations
        primary, primary_edge, secondary, secondary_edge = self.get_recommendations(
            scenario, home, away, expected_total, convergence
        )
        
        # Action
        action, stake = self.determine_action(scenario, confidence, primary_edge, convergence)
        
        # Volatility (écart-type attendu)
        volatility = math.sqrt(lambda_home + lambda_away)
        
        # Reasoning
        reasoning = f"{scenario.value}: "
        if scenario == Scenario.CONVERGENCE_OVER:
            reasoning += f"Both teams favor Over markets. {home.team_name} ({home.best_market}) + {away.team_name} ({away.best_market}). Expected {expected_total:.1f} goals."
        elif scenario == Scenario.CONVERGENCE_UNDER:
            reasoning += f"Both teams favor Under markets. Defensive match expected. {expected_total:.1f} goals."
        elif scenario == Scenario.TOTAL_CHAOS:
            reasoning += f"High pace ({home.pace_index:.0f} + {away.pace_index:.0f}) + weak defenses. Goal fest expected."
        elif scenario == Scenario.SIEGE:
            dominant = home if home.control_index > away.control_index else away
            reasoning += f"{dominant.team_name} to dominate territorially (Control: {dominant.control_index:.0f})."
        elif scenario == Scenario.SNIPER_DUEL:
            reasoning += f"High efficiency both sides (Lethality: {home.lethality_index:.0f} vs {away.lethality_index:.0f}). Both should score."
        elif scenario == Scenario.ATTRITION:
            reasoning += f"Low intensity match. Total pace: {home.pace_index + away.pace_index:.0f}. Under likely."
        else:
            reasoning += f"Style clash. Following leader: {home.team_name if home.best_market_roi > away.best_market_roi else away.team_name}"
            
        return ClashResult(
            home=home,
            away=away,
            scenario=scenario,
            scenario_confidence=confidence,
            expected_total_goals=expected_total,
            expected_volatility=round(volatility, 2),
            style_convergence=convergence,
            primary_market=primary,
            primary_edge=primary_edge,
            secondary_market=secondary,
            secondary_edge=secondary_edge,
            action=action,
            stake=stake,
            reasoning=reasoning
        )
        
    def print_analysis(self, result: ClashResult):
        """Affiche l'analyse formatée"""
        print("\n" + "═"*80)
        print(f"🧠 ADCM ANALYSIS: {result.home.team_name} vs {result.away.team_name}")
        print("═"*80)
        
        print(f"\n📊 TEAM METRICS:")
        print(f"{'Metric':<20} {result.home.team_name:<20} {result.away.team_name:<20}")
        print("-"*60)
        print(f"{'Pace Index':<20} {result.home.pace_index:<20.1f} {result.away.pace_index:<20.1f}")
        print(f"{'Control Index':<20} {result.home.control_index:<20.1f} {result.away.control_index:<20.1f}")
        print(f"{'Lethality Index':<20} {result.home.lethality_index:<20.1f} {result.away.lethality_index:<20.1f}")
        print(f"{'Defensive Solidity':<20} {result.home.defensive_solidity:<20.1f} {result.away.defensive_solidity:<20.1f}")
        print(f"{'GameState Profile':<20} {result.home.gamestate_profile:<20} {result.away.gamestate_profile:<20}")
        print(f"{'Best Market':<20} {result.home.best_market:<20} {result.away.best_market:<20}")
        
        print(f"\n🎯 CLASH ANALYSIS:")
        print(f"   Expected Goals: {result.expected_total_goals:.2f}")
        print(f"   Volatility: {result.expected_volatility:.2f}")
        print(f"   Style Convergence: {result.style_convergence:+.1f}")
        
        print(f"\n🏷️ SCENARIO: {result.scenario.value}")
        print(f"   Confidence: {result.scenario_confidence:.0f}%")
        
        print(f"\n💰 RECOMMENDATIONS:")
        print(f"   Primary: {result.primary_market} (Edge: {result.primary_edge:+.1f}%)")
        if result.secondary_market:
            print(f"   Secondary: {result.secondary_market} (Edge: {result.secondary_edge:+.1f}%)")
            
        print(f"\n🎲 DECISION: {result.action.value} | Stake: {result.stake}u")
        print(f"   📝 {result.reasoning}")


def main():
    print("""
╔═══════════════════════════════════════════════════════════════════════════════╗
║     🧠 ADVANCED DYNAMIC CLASH MODEL (ADCM) 2.0 - INSTITUTIONAL QUANT          ║
╚═══════════════════════════════════════════════════════════════════════════════╝
    """)
    
    engine = ADCMEngine()
    engine.connect()
    engine.load_team_data()
    
    # Test matches
    test_matches = [
        ("Bayern Munich", "Lazio"),           # Clash: Over vs Under
        ("Bayern Munich", "Leeds"),           # Convergence Over
        ("Lazio", "AS Roma"),                 # Convergence Under
        ("Barcelona", "Real Madrid"),         # High intensity
        ("Getafe", "Rayo Vallecano"),        # Low scoring
    ]
    
    print("\n" + "="*80)
    print("🧪 TEST MATCHES ANALYSIS")
    print("="*80)
    
    for home, away in test_matches:
        result = engine.analyze_match(home, away)
        if result:
            engine.print_analysis(result)
        else:
            print(f"\n⚠️ Cannot analyze: {home} vs {away} (missing data)")
            

if __name__ == "__main__":
    main()
