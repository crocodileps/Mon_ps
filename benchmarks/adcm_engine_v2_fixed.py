#!/usr/bin/env python3
"""
╔═══════════════════════════════════════════════════════════════════════════════╗
║     🧠 ADVANCED DYNAMIC CLASH MODEL (ADCM) 2.1 - FIXED & CALIBRATED           ║
║                                                                               ║
║  CORRECTIONS APPLIQUÉES:                                                      ║
║  • Priorité CONVERGENCE > autres scénarios                                    ║
║  • Recalibrage du Lethality Index (échelle 0-100 réelle)                     ║
║  • TOTAL_CHAOS détecté si Pace > 150 + xG > 3.5                              ║
║  • Recommandations COHÉRENTES avec best_markets                              ║
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
    GLASS_CANNON = "🃏 GLASS_CANNON"
    CONVERGENCE_OVER = "⚡ CONVERGENCE_OVER"
    CONVERGENCE_UNDER = "🛡️ CONVERGENCE_UNDER"
    STYLE_CLASH = "⚔️ STYLE_CLASH"
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
    
    # Lethality (Efficiency) - Scale 0-100 CALIBRÉ
    lethality_index: float
    bc_conversion: float
    shot_quality: float
    
    # Defensive - Scale 0-100
    defensive_solidity: float
    xg_against: float
    
    # GameState
    gamestate_profile: str
    when_drawing_xg: float
    when_trailing_xg: float
    
    # Best Market
    best_market: str
    best_market_roi: float
    
    # Market Category (calculé)
    market_tendency: str  # "OVER" or "UNDER"


@dataclass
class ClashResult:
    """Résultat de l'analyse ADCM"""
    home: TeamMetrics
    away: TeamMetrics
    
    scenario: Scenario
    scenario_confidence: float
    
    expected_total_goals: float
    expected_volatility: float
    style_convergence: float
    
    primary_market: str
    primary_edge: float
    secondary_market: str
    secondary_edge: float
    
    action: Action
    stake: float
    reasoning: str


class ADCMEngineV2:
    """Advanced Dynamic Clash Model Engine - Version 2.1 Calibrated"""
    
    # Markets classification
    OVER_MARKETS = ['over_25', 'over_35', 'over_15', 'btts_yes', 'team_over_15', 'team_over_25']
    UNDER_MARKETS = ['under_25', 'under_35', 'under_15', 'btts_no', 'clean_sheet', 'fail_to_score']
    
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
            cur.execute("SELECT * FROM team_xg_tendencies")
            xg_data = {row['team_name']: row for row in cur.fetchall()}
            
            cur.execute("SELECT * FROM team_big_chances_tendencies")
            bc_data = {row['team_name']: row for row in cur.fetchall()}
            
            cur.execute("SELECT * FROM team_gamestate_stats")
            gs_data = {row['team_name']: row for row in cur.fetchall()}
            
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
                
        all_teams = set(xg_data.keys()) | set(bc_data.keys())
        
        for team in all_teams:
            xg = xg_data.get(team, {})
            bc = bc_data.get(team, {})
            gs = gs_data.get(team, {})
            mkt = market_data.get(team, {'best_market': 'over_25', 'roi': 0, 'wr': 50})
            
            self.team_data[team] = {'xg': xg, 'bc': bc, 'gs': gs, 'market': mkt}
            
        print(f"✅ {len(self.team_data)} équipes chargées")
        
    def get_market_tendency(self, market: str) -> str:
        """Détermine si un marché est OVER ou UNDER"""
        if market in self.OVER_MARKETS:
            return "OVER"
        elif market in self.UNDER_MARKETS:
            return "UNDER"
        return "NEUTRAL"
        
    def calculate_team_metrics(self, team_name: str) -> Optional[TeamMetrics]:
        """Calcule les métriques ADCM pour une équipe - VERSION CALIBRÉE"""
        data = self.team_data.get(team_name)
        if not data:
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
        # PACE INDEX (0-100) - CALIBRÉ
        # Moyenne ligue xG ≈ 1.3, BC ≈ 1.5
        # Formule: ((xG_for / 1.3) * 25) + ((BC_created / 1.5) * 25) + 25
        # ═══════════════════════════════════════════════════════════════════════
        xg_for = float(xg.get('avg_xg_for') or 1.3)
        bc_created = float(bc.get('avg_bc_created') or 1.5)
        
        pace_raw = ((xg_for / 1.3) * 30) + ((bc_created / 1.5) * 20)
        pace_index = min(100, max(0, pace_raw))
        
        # ═══════════════════════════════════════════════════════════════════════
        # CONTROL INDEX (0-100) - Basé sur open_play vs defensive
        # ═══════════════════════════════════════════════════════════════════════
        open_rate = float(xg.get('open_rate') or 50)
        defensive_rate = float(xg.get('defensive_rate') or 50)
        
        control_index = (open_rate * 0.7) + ((100 - defensive_rate) * 0.3)
        
        # ═══════════════════════════════════════════════════════════════════════
        # LETHALITY INDEX (0-100) - RECALIBRÉ
        # BC conversion moyenne ≈ 45%, shot_quality moyenne ≈ 0.12
        # Formule: (bc_conversion / 60) * 50 + (shot_quality / 0.15) * 50
        # ═══════════════════════════════════════════════════════════════════════
        bc_conversion = float(bc.get('bc_conversion_rate') or 45)
        shot_quality = float(bc.get('avg_shot_quality') or 0.12)
        
        # Normalisation pour avoir une échelle 0-100 réaliste
        lethality_raw = (bc_conversion / 70) * 50 + (shot_quality / 0.20) * 50
        lethality_index = min(100, max(0, lethality_raw))
        
        # ═══════════════════════════════════════════════════════════════════════
        # DEFENSIVE SOLIDITY (0-100)
        # xG_against moyen ≈ 1.3, BC concédées moyen ≈ 1.5
        # ═══════════════════════════════════════════════════════════════════════
        xg_against = float(xg.get('avg_xg_against') or 1.3)
        bc_conceded = float(bc.get('avg_bc_conceded') or 1.5)
        
        # Inverse: moins on concède, plus on est solide
        defensive_raw = 100 - ((xg_against / 1.3) * 25) - ((bc_conceded / 1.5) * 25)
        defensive_solidity = min(100, max(0, defensive_raw))
        
        # ═══════════════════════════════════════════════════════════════════════
        # GAMESTATE PROFILE
        # ═══════════════════════════════════════════════════════════════════════
        drawing_time = max(1, int(gs.get('gs_drawing_time') or 1))
        trailing_time = max(1, int(gs.get('gs_trailing_time') or 1))
        leading_time = max(1, int(gs.get('gs_leading_time') or 1))
        
        drawing_xg = float(gs.get('gs_drawing_xg') or 0) / drawing_time * 90
        trailing_xg = float(gs.get('gs_trailing_xg') or 0) / trailing_time * 90
        leading_xg = float(gs.get('gs_leading_xg') or 0) / leading_time * 90
        
        if trailing_xg > drawing_xg * 1.3:
            gs_profile = "AGGRESSIVE"
        elif leading_xg < drawing_xg * 0.6:
            gs_profile = "PASSIVE"
        else:
            gs_profile = "BALANCED"
            
        # Market tendency
        best_market = mkt['best_market']
        market_tendency = self.get_market_tendency(best_market)
            
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
            best_market=best_market,
            best_market_roi=mkt['roi'],
            market_tendency=market_tendency
        )
        
    def calculate_expected_goals(self, home: TeamMetrics, away: TeamMetrics) -> Tuple[float, float]:
        """Calcule les lambdas avec Dixon-Coles simplifié"""
        HOME_ADVANTAGE = 1.12
        
        lambda_home = math.sqrt(home.xg_for * away.xg_against) * HOME_ADVANTAGE
        lambda_away = math.sqrt(away.xg_for * home.xg_against)
        
        return round(lambda_home, 2), round(lambda_away, 2)
        
    def calculate_style_convergence(self, home: TeamMetrics, away: TeamMetrics) -> Tuple[float, str]:
        """
        Calcule la convergence de style
        Returns: (score, type)
        - score: -1 (clash) to +1 (convergence)
        - type: "OVER", "UNDER", "CLASH"
        """
        home_over = home.market_tendency == "OVER"
        away_over = away.market_tendency == "OVER"
        home_under = home.market_tendency == "UNDER"
        away_under = away.market_tendency == "UNDER"
        
        if home_over and away_over:
            return 1.0, "OVER"
        elif home_under and away_under:
            return 1.0, "UNDER"
        elif (home_over and away_under) or (home_under and away_over):
            return -0.5, "CLASH"
        else:
            return 0.0, "NEUTRAL"
            
    def classify_scenario(self, home: TeamMetrics, away: TeamMetrics,
                          lambda_home: float, lambda_away: float,
                          convergence: float, conv_type: str) -> Tuple[Scenario, float]:
        """
        Classifie le match - PRIORITÉ CONVERGENCE
        """
        total_pace = home.pace_index + away.pace_index
        control_diff = abs(home.control_index - away.control_index)
        avg_lethality = (home.lethality_index + away.lethality_index) / 2
        expected_total = lambda_home + lambda_away
        avg_defensive = (home.defensive_solidity + away.defensive_solidity) / 2
        
        # ═══════════════════════════════════════════════════════════════════════
        # PRIORITÉ 1: CONVERGENCE (quand les deux équipes veulent la même chose)
        # C'est le signal LE PLUS FORT
        # ═══════════════════════════════════════════════════════════════════════
        
        if convergence > 0.5:
            if conv_type == "OVER":
                # Les deux équipes favorisent Over
                if expected_total >= 2.6:
                    confidence = min(95, 70 + (expected_total - 2.5) * 15)
                    return Scenario.CONVERGENCE_OVER, confidence
                else:
                    # Stats ne supportent pas assez
                    confidence = 55
                    return Scenario.CONVERGENCE_OVER, confidence
                    
            elif conv_type == "UNDER":
                # Les deux équipes favorisent Under
                if expected_total <= 2.6:
                    confidence = min(95, 70 + (2.7 - expected_total) * 20)
                    return Scenario.CONVERGENCE_UNDER, confidence
                else:
                    # Stats élevées mais profils Under - prudence
                    confidence = 50
                    return Scenario.CONVERGENCE_UNDER, confidence
                    
        # ═══════════════════════════════════════════════════════════════════════
        # PRIORITÉ 2: TOTAL CHAOS (haut volume + défenses faibles)
        # ═══════════════════════════════════════════════════════════════════════
        
        if total_pace > 100 and avg_defensive < 50 and expected_total > 3.2:
            confidence = min(95, 65 + (expected_total - 3.0) * 10)
            return Scenario.TOTAL_CHAOS, confidence
            
        # ═══════════════════════════════════════════════════════════════════════
        # PRIORITÉ 3: STYLE CLASH (conflit Over vs Under)
        # ═══════════════════════════════════════════════════════════════════════
        
        if convergence < 0:
            # Qui domine? Le plus fort (pace + ROI)
            home_strength = home.pace_index * 0.5 + home.best_market_roi * 0.5
            away_strength = away.pace_index * 0.5 + away.best_market_roi * 0.5
            
            if abs(home_strength - away_strength) < 15:
                # Forces égales = incertain
                return Scenario.STYLE_CLASH, 45
            else:
                # Un camp domine
                return Scenario.STYLE_CLASH, 55
                
        # ═══════════════════════════════════════════════════════════════════════
        # PRIORITÉ 4: SIEGE (domination territoriale)
        # ═══════════════════════════════════════════════════════════════════════
        
        if control_diff > 20:
            dominant = home if home.control_index > away.control_index else away
            confidence = min(85, 55 + control_diff * 0.8)
            return Scenario.SIEGE, confidence
            
        # ═══════════════════════════════════════════════════════════════════════
        # PRIORITÉ 5: SNIPER DUEL (haute efficacité des deux)
        # Seuil relevé: lethality > 55 (pas 50)
        # ═══════════════════════════════════════════════════════════════════════
        
        if home.lethality_index > 55 and away.lethality_index > 55:
            confidence = min(85, 55 + (avg_lethality - 55))
            return Scenario.SNIPER_DUEL, confidence
            
        # ═══════════════════════════════════════════════════════════════════════
        # PRIORITÉ 6: ATTRITION (faible intensité)
        # ═══════════════════════════════════════════════════════════════════════
        
        if total_pace < 70 and expected_total < 2.3:
            confidence = min(80, 50 + (80 - total_pace) / 2)
            return Scenario.ATTRITION, confidence
            
        # ═══════════════════════════════════════════════════════════════════════
        # PRIORITÉ 7: GLASS CANNON
        # ═══════════════════════════════════════════════════════════════════════
        
        home_glass = home.pace_index > 50 and home.defensive_solidity < 35
        away_glass = away.pace_index > 50 and away.defensive_solidity < 35
        
        if home_glass or away_glass:
            return Scenario.GLASS_CANNON, 55
            
        # Default
        return Scenario.UNCERTAIN, 40
        
    def get_recommendations(self, scenario: Scenario, home: TeamMetrics, away: TeamMetrics,
                           expected_total: float, convergence: float, conv_type: str) -> Tuple[str, float, str, float]:
        """
        Génère les recommandations COHÉRENTES avec les best_markets
        """
        primary = None
        primary_edge = 0
        secondary = None
        secondary_edge = 0
        
        if scenario == Scenario.CONVERGENCE_OVER:
            # Les deux équipes veulent Over → suivre!
            primary = 'over_25'
            primary_edge = min(30, 15 + (expected_total - 2.5) * 10)
            secondary = 'over_35' if expected_total > 3.0 else 'btts_yes'
            secondary_edge = primary_edge * 0.7
            
        elif scenario == Scenario.CONVERGENCE_UNDER:
            # Les deux équipes veulent Under → suivre!
            primary = 'under_25'
            primary_edge = min(30, 15 + (2.7 - expected_total) * 12)
            secondary = 'btts_no'
            secondary_edge = primary_edge * 0.7
            
        elif scenario == Scenario.TOTAL_CHAOS:
            primary = 'over_35' if expected_total > 3.5 else 'over_25'
            primary_edge = min(25, (expected_total - 2.5) * 12)
            secondary = 'btts_yes'
            secondary_edge = 18
            
        elif scenario == Scenario.STYLE_CLASH:
            # Suivre l'équipe dominante (meilleur ROI)
            leader = home if home.best_market_roi > away.best_market_roi else away
            primary = leader.best_market
            primary_edge = 8  # Réduit car incertain
            secondary = None
            secondary_edge = 0
            
        elif scenario == Scenario.SIEGE:
            dominant = home if home.control_index > away.control_index else away
            if dominant.market_tendency == "OVER":
                primary = 'over_25'
                primary_edge = 12
            else:
                primary = 'under_25'
                primary_edge = 12
            secondary = dominant.best_market
            secondary_edge = 8
            
        elif scenario == Scenario.SNIPER_DUEL:
            primary = 'btts_yes'
            primary_edge = 18
            secondary = 'over_25'
            secondary_edge = 12
            
        elif scenario == Scenario.ATTRITION:
            primary = 'under_25'
            primary_edge = 15
            secondary = 'btts_no'
            secondary_edge = 10
            
        elif scenario == Scenario.GLASS_CANNON:
            primary = 'btts_yes'
            primary_edge = 12
            secondary = 'over_25'
            secondary_edge = 8
            
        else:  # UNCERTAIN
            leader = home if home.best_market_roi > away.best_market_roi else away
            primary = leader.best_market
            primary_edge = 5
            
        return primary, primary_edge, secondary, secondary_edge
        
    def determine_action(self, scenario: Scenario, confidence: float, 
                        primary_edge: float, convergence: float) -> Tuple[Action, float]:
        """Détermine l'action et le stake"""
        
        # SNIPER: Convergence parfaite + haute confiance
        if scenario in [Scenario.CONVERGENCE_OVER, Scenario.CONVERGENCE_UNDER]:
            if confidence >= 70 and primary_edge >= 18:
                return Action.SNIPER, 3.0
            elif confidence >= 60:
                return Action.NORMAL, 2.0
                
        if scenario == Scenario.TOTAL_CHAOS and confidence >= 65:
            return Action.SNIPER, 2.5
            
        # SPECULATIVE: Clash de styles
        if scenario == Scenario.STYLE_CLASH:
            return Action.SPECULATIVE, 1.0
            
        # NORMAL
        if confidence >= 60 and primary_edge >= 12:
            return Action.NORMAL, 2.0
            
        # SKIP si trop incertain
        if confidence < 50 or primary_edge < 8:
            return Action.SKIP, 0
            
        return Action.NORMAL, 1.5
        
    def analyze_match(self, home_team: str, away_team: str) -> Optional[ClashResult]:
        """Analyse complète d'un match"""
        home = self.calculate_team_metrics(home_team)
        away = self.calculate_team_metrics(away_team)
        
        if not home or not away:
            return None
            
        lambda_home, lambda_away = self.calculate_expected_goals(home, away)
        expected_total = lambda_home + lambda_away
        convergence, conv_type = self.calculate_style_convergence(home, away)
        
        scenario, confidence = self.classify_scenario(
            home, away, lambda_home, lambda_away, convergence, conv_type
        )
        
        primary, primary_edge, secondary, secondary_edge = self.get_recommendations(
            scenario, home, away, expected_total, convergence, conv_type
        )
        
        action, stake = self.determine_action(scenario, confidence, primary_edge, convergence)
        
        volatility = math.sqrt(lambda_home + lambda_away)
        
        # Reasoning AMÉLIORÉ
        reasoning_parts = {
            Scenario.CONVERGENCE_OVER: f"CONVERGENCE OVER: {home.team_name} ({home.best_market}) + {away.team_name} ({away.best_market}) → Both want goals. xG: {expected_total:.1f}",
            Scenario.CONVERGENCE_UNDER: f"CONVERGENCE UNDER: {home.team_name} ({home.best_market}) + {away.team_name} ({away.best_market}) → Both want low scoring. xG: {expected_total:.1f}",
            Scenario.TOTAL_CHAOS: f"TOTAL CHAOS: Pace {home.pace_index:.0f}+{away.pace_index:.0f}={home.pace_index+away.pace_index:.0f}, weak defenses ({home.defensive_solidity:.0f}/{away.defensive_solidity:.0f}). Goal fest!",
            Scenario.STYLE_CLASH: f"STYLE CLASH: {home.team_name} ({home.market_tendency}) vs {away.team_name} ({away.market_tendency}). Following ROI leader.",
            Scenario.SIEGE: f"SIEGE: Control diff {abs(home.control_index - away.control_index):.0f}pts. Territorial domination expected.",
            Scenario.SNIPER_DUEL: f"SNIPER DUEL: High lethality ({home.lethality_index:.0f} vs {away.lethality_index:.0f}). Clinical finishing expected.",
            Scenario.ATTRITION: f"ATTRITION: Low pace ({home.pace_index + away.pace_index:.0f}). Tactical battle.",
            Scenario.GLASS_CANNON: f"GLASS CANNON: Attack > Defense imbalance. Open game.",
            Scenario.UNCERTAIN: f"UNCERTAIN: Mixed signals. Proceed with caution."
        }
        reasoning = reasoning_parts.get(scenario, "Analysis complete.")
            
        return ClashResult(
            home=home, away=away,
            scenario=scenario, scenario_confidence=confidence,
            expected_total_goals=expected_total, expected_volatility=round(volatility, 2),
            style_convergence=convergence,
            primary_market=primary, primary_edge=primary_edge,
            secondary_market=secondary, secondary_edge=secondary_edge,
            action=action, stake=stake, reasoning=reasoning
        )
        
    def print_analysis(self, result: ClashResult):
        """Affiche l'analyse formatée"""
        print("\n" + "═"*90)
        print(f"🧠 ADCM 2.1: {result.home.team_name} vs {result.away.team_name}")
        print("═"*90)
        
        print(f"\n📊 TEAM METRICS (Calibrated 0-100):")
        print(f"{'Metric':<22} {result.home.team_name:<22} {result.away.team_name:<22}")
        print("-"*70)
        print(f"{'Pace Index':<22} {result.home.pace_index:<22.1f} {result.away.pace_index:<22.1f}")
        print(f"{'Control Index':<22} {result.home.control_index:<22.1f} {result.away.control_index:<22.1f}")
        print(f"{'Lethality Index':<22} {result.home.lethality_index:<22.1f} {result.away.lethality_index:<22.1f}")
        print(f"{'Defensive Solidity':<22} {result.home.defensive_solidity:<22.1f} {result.away.defensive_solidity:<22.1f}")
        print(f"{'Best Market':<22} {result.home.best_market:<22} {result.away.best_market:<22}")
        print(f"{'Market Tendency':<22} {result.home.market_tendency:<22} {result.away.market_tendency:<22}")
        
        print(f"\n🎯 CLASH ANALYSIS:")
        print(f"   Expected Goals: {result.expected_total_goals:.2f}")
        print(f"   Style Convergence: {result.style_convergence:+.1f} ({'ALIGNED' if result.style_convergence > 0 else 'CLASH' if result.style_convergence < 0 else 'NEUTRAL'})")
        
        print(f"\n🏷️ SCENARIO: {result.scenario.value}")
        print(f"   Confidence: {result.scenario_confidence:.0f}%")
        
        print(f"\n💰 RECOMMENDATIONS:")
        print(f"   Primary: {result.primary_market} (Edge: {result.primary_edge:+.1f}%)")
        if result.secondary_market:
            print(f"   Secondary: {result.secondary_market} (Edge: {result.secondary_edge:+.1f}%)")
            
        action_emoji = {"SNIPER": "🎯", "NORMAL": "✅", "SPECULATIVE": "⚠️", "SKIP": "❌"}
        print(f"\n🎲 DECISION: {action_emoji.get(result.action.value, '')} {result.action.value} | Stake: {result.stake}u")
        print(f"   📝 {result.reasoning}")


def main():
    print("""
╔═══════════════════════════════════════════════════════════════════════════════╗
║     🧠 ADVANCED DYNAMIC CLASH MODEL (ADCM) 2.1 - CALIBRATED & FIXED           ║
║                                                                               ║
║  CORRECTIONS:                                                                 ║
║  ✅ Priorité CONVERGENCE > autres scénarios                                   ║
║  ✅ Lethality Index recalibré (échelle réelle 0-100)                         ║
║  ✅ Recommandations COHÉRENTES avec market_tendency                           ║
║  ✅ Nouveau scénario STYLE_CLASH pour les conflits                           ║
╚═══════════════════════════════════════════════════════════════════════════════╝
    """)
    
    engine = ADCMEngineV2()
    engine.connect()
    engine.load_team_data()
    
    test_matches = [
        ("Bayern Munich", "Lazio"),        # Clash: Over vs Under
        ("Bayern Munich", "Leeds"),        # Convergence Over
        ("Lazio", "AS Roma"),              # Convergence Under (btts_no vs btts_no)
        ("Barcelona", "Real Madrid"),      # High intensity
        ("Getafe", "Rayo Vallecano"),      # Under vs Under
    ]
    
    print("\n" + "="*90)
    print("🧪 TEST MATCHES - VALIDATION DES CORRECTIONS")
    print("="*90)
    
    results_summary = []
    
    for home, away in test_matches:
        result = engine.analyze_match(home, away)
        if result:
            engine.print_analysis(result)
            results_summary.append({
                'match': f"{home} vs {away}",
                'scenario': result.scenario.value,
                'convergence': result.style_convergence,
                'primary': result.primary_market,
                'action': result.action.value
            })
            
    # Validation summary
    print("\n" + "="*90)
    print("📋 VALIDATION SUMMARY")
    print("="*90)
    print(f"\n{'Match':<35} {'Scenario':<25} {'Conv':<8} {'Primary':<12} {'Action':<12}")
    print("-"*90)
    for r in results_summary:
        print(f"{r['match']:<35} {r['scenario']:<25} {r['convergence']:+.1f}{'':<4} {r['primary']:<12} {r['action']:<12}")


if __name__ == "__main__":
    main()
