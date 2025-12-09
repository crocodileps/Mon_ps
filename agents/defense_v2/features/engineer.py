"""
═══════════════════════════════════════════════════════════════════════════════
🏦 AGENT DÉFENSE 2.0 - FEATURE ENGINEER
   Extraction complète des features pour tous les marchés
   
   SOURCES:
   - Defensive Lines V8.3 (foundation, resistance, timing, edge)
   - Defender DNA V9 (aggregated by team)
   - Goalkeeper DNA V3.1 (by_difficulty, by_situation, by_timing)
   - Team Defense 2025 (92 features)
   - Football-Data UK (corners, shots, fouls, cards)
   - Referee DNA V4
   - Zone Analysis, Gamestate Insights
   
   OUTPUT: ~200-250 features sélectionnées après élimination corrélations
═══════════════════════════════════════════════════════════════════════════════
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path
import sys

sys.path.append(str(Path(__file__).parent.parent))
from config import THRESHOLDS, LEAGUES


class FeatureEngineer:
    """
    Extrait et construit les features pour l'Agent Défense 2.0.
    
    Architecture:
        1. Team Features (home/away): ~80 features × 2 = 160
        2. Goalkeeper Features: ~20 features × 2 = 40
        3. Defender Features (aggregated): ~15 features × 2 = 30
        4. Combined Features (matchup): ~50 features
        5. Referee Features: ~10 features
        
    Total brut: ~290 features
    Après sélection: ~150-200 features
    """
    
    def __init__(self, data_loader):
        """
        Args:
            data_loader: Instance de DefenseDataLoader avec données chargées
        """
        self.loader = data_loader
        self.feature_names = []
    
    def extract_match_features(self, home_team: str, away_team: str, 
                                referee: str = None, league: str = None) -> Dict[str, float]:
        """
        Extrait toutes les features pour un match.
        
        Args:
            home_team: Nom équipe domicile
            away_team: Nom équipe extérieur
            referee: Nom arbitre (optionnel)
            league: Ligue (optionnel, pour priors)
        
        Returns:
            Dict avec toutes les features
        """
        features = {}
        
        # Récupérer les données
        home_data = self.loader.get_team_data(home_team)
        away_data = self.loader.get_team_data(away_team)
        ref_data = self.loader.get_referee_data(referee) if referee else None
        
        # 1. Team Features (home)
        home_features = self._extract_team_features(home_data, prefix='h_')
        features.update(home_features)
        
        # 2. Team Features (away)
        away_features = self._extract_team_features(away_data, prefix='a_')
        features.update(away_features)
        
        # 3. Combined Features
        combined = self._extract_combined_features(home_data, away_data)
        features.update(combined)
        
        # 4. Referee Features
        if ref_data:
            ref_features = self._extract_referee_features(ref_data)
            features.update(ref_features)
        else:
            # Default values si pas de referee
            features.update(self._get_default_referee_features())
        
        # 5. Context Features
        if league:
            features['league_encoded'] = LEAGUES.index(league) if league in LEAGUES else -1
        
        return features
    
    def _extract_team_features(self, team_data: Dict, prefix: str = '') -> Dict[str, float]:
        """
        Extrait les features pour une équipe.
        
        Sources utilisées:
        - defensive_lines (foundation, resistance, timing, edge)
        - team_defense (92 colonnes)
        - defenders (aggregated)
        - goalkeeper
        - corners_dna, shots_dna, fouls_dna, cards_team_dna
        - zones, gamestate
        """
        features = {}
        
        # ═══════════════════════════════════════════════════════════════════════
        # DEFENSIVE LINES V8.3
        # ═══════════════════════════════════════════════════════════════════════
        dl = team_data.get('defensive_lines', {}) or {}
        
        # Foundation
        foundation = dl.get('foundation', {}) or {}
        features[f'{prefix}xga_90'] = foundation.get('xga_90', 1.5)
        features[f'{prefix}ga_90'] = foundation.get('ga_90', 1.5)
        features[f'{prefix}cs_pct'] = foundation.get('cs_pct', 30)
        features[f'{prefix}overperform'] = foundation.get('overperform', 0)
        
        # Resistance
        resistance = dl.get('resistance', {}) or {}
        features[f'{prefix}resist_global'] = resistance.get('resist_global', 50)
        features[f'{prefix}resist_set_piece'] = resistance.get('resist_set_piece', 50)
        features[f'{prefix}resist_transition'] = resistance.get('resist_transition', 50)
        
        # Timing DNA
        timing = dl.get('timing_dna', {}) or {}
        features[f'{prefix}early_pct'] = timing.get('early_pct', 33)
        features[f'{prefix}mid_pct'] = timing.get('mid_pct', 33)
        features[f'{prefix}late_pct'] = timing.get('late_pct', 33)
        
        # Edge
        edge = dl.get('edge', {}) or {}
        features[f'{prefix}total_edge'] = edge.get('total_edge', 0)
        features[f'{prefix}kelly_stake'] = edge.get('kelly_stake', 0)
        
        edge_components = edge.get('components', {}) or {}
        features[f'{prefix}resistance_edge'] = edge_components.get('resistance_edge', 0)
        features[f'{prefix}temporal_edge'] = edge_components.get('temporal_edge', 0)
        features[f'{prefix}closing_edge'] = edge_components.get('closing_edge', 0)
        
        # ═══════════════════════════════════════════════════════════════════════
        # TEAM DEFENSE 2025 (92 colonnes)
        # ═══════════════════════════════════════════════════════════════════════
        td = team_data.get('team_defense', {}) or {}
        
        # xGA splits
        features[f'{prefix}xga_home'] = td.get('xga_home', 1.2) if prefix == 'h_' else td.get('xga_away', 1.8)
        features[f'{prefix}xga_total'] = td.get('xga_total', 25)
        
        # Timing xGA
        features[f'{prefix}xga_0_15'] = td.get('xga_0_15', 4)
        features[f'{prefix}xga_16_30'] = td.get('xga_16_30', 4)
        features[f'{prefix}xga_31_45'] = td.get('xga_31_45', 4)
        features[f'{prefix}xga_46_60'] = td.get('xga_46_60', 4)
        features[f'{prefix}xga_61_75'] = td.get('xga_61_75', 4)
        features[f'{prefix}xga_76_90'] = td.get('xga_76_90', 4)
        
        # Half splits
        features[f'{prefix}xga_1h_pct'] = td.get('xga_1h_pct', 50)
        features[f'{prefix}xga_2h_pct'] = td.get('xga_2h_pct', 50)
        
        # Set pieces
        features[f'{prefix}xga_corner'] = td.get('xga_corner', 2)
        features[f'{prefix}xga_free_kick'] = td.get('xga_free_kick', 1)
        features[f'{prefix}set_piece_vuln_pct'] = td.get('set_piece_vuln_pct', 25)
        
        # Gamestate
        features[f'{prefix}xga_level'] = td.get('xga_level', 10)
        features[f'{prefix}xga_leading'] = td.get('xga_leading_1', 5)
        features[f'{prefix}xga_losing'] = td.get('xga_losing_1', 8)
        
        # ═══════════════════════════════════════════════════════════════════════
        # GOALKEEPER DNA V4.4 - TEAM-CENTRIC
        # Le GK fait partie de l'ADN défensif de l'équipe
        # ═══════════════════════════════════════════════════════════════════════
        gk = team_data.get('goalkeeper', {}) or {}

        # Core metrics (compatibilité V3.1 + V4.4)
        features[f'{prefix}gk_save_rate'] = gk.get('save_rate', 70)
        features[f'{prefix}gk_percentile'] = gk.get('gk_percentile', 50)
        features[f'{prefix}gk_performance'] = gk.get('gk_performance', 0)

        # ═══════════════════════════════════════════════════════════════════════
        # DIFFICULTY ANALYSIS V4.4
        # ═══════════════════════════════════════════════════════════════════════
        diff_analysis = gk.get('difficulty_analysis', {}) or {}
        if not diff_analysis:
            diff_analysis = gk.get('by_difficulty', {}) or {}
        
        easy = diff_analysis.get('easy', {}) or {}
        medium = diff_analysis.get('medium', {}) or {}
        hard = diff_analysis.get('hard', {}) or {}
        very_hard = diff_analysis.get('very_hard', {}) or {}
        
        features[f'{prefix}gk_easy_sr'] = easy.get('sr', easy.get('save_rate', 85))
        features[f'{prefix}gk_medium_sr'] = medium.get('sr', medium.get('save_rate', 70))
        features[f'{prefix}gk_hard_sr'] = hard.get('sr', hard.get('save_rate', 45))
        features[f'{prefix}gk_vhard_sr'] = very_hard.get('sr', very_hard.get('save_rate', 25))
        
        features[f'{prefix}gk_easy_vs_bench'] = easy.get('vs_expected', 0)
        features[f'{prefix}gk_hard_vs_bench'] = hard.get('vs_expected', 0)
        
        big_save = diff_analysis.get('big_save_ability', 'AVERAGE')
        features[f'{prefix}gk_big_save'] = {'STRONG': 1, 'AVERAGE': 0, 'WEAK': -1, 'NO_DATA': 0}.get(big_save, 0)
        
        routine = diff_analysis.get('routine_reliability', 'AVERAGE')
        features[f'{prefix}gk_routine'] = {'ROCK_SOLID': 2, 'RELIABLE': 1, 'AVERAGE': 0, 'ERROR_PRONE': -1}.get(routine, 0)

        # ═══════════════════════════════════════════════════════════════════════
        # SITUATION ANALYSIS V4.4
        # ═══════════════════════════════════════════════════════════════════════
        sit_analysis = gk.get('situation_analysis', {}) or {}
        if not sit_analysis:
            sit_analysis = gk.get('by_situation', {}) or {}
        
        open_play = sit_analysis.get('open_play', sit_analysis.get('OpenPlay', {})) or {}
        corners = sit_analysis.get('corners', sit_analysis.get('FromCorner', {})) or {}
        set_pieces = sit_analysis.get('set_pieces', sit_analysis.get('SetPiece', {})) or {}
        penalties = sit_analysis.get('penalties', {}) or {}
        
        features[f'{prefix}gk_openplay_sr'] = open_play.get('sr', open_play.get('save_rate', 75))
        features[f'{prefix}gk_corner_sr'] = corners.get('sr', corners.get('save_rate', 65))
        features[f'{prefix}gk_setpiece_sr'] = set_pieces.get('sr', set_pieces.get('save_rate', 65))
        features[f'{prefix}gk_penalty_sr'] = penalties.get('sr', penalties.get('save_rate', 25))

        # ═══════════════════════════════════════════════════════════════════════
        # TIMING ANALYSIS V4.4 - Crucial pour betting
        # ═══════════════════════════════════════════════════════════════════════
        timing = gk.get('timing_analysis', {}) or {}
        if not timing:
            timing = gk.get('by_timing', {}) or {}
        
        periods = timing.get('periods', {}) or {}
        period_0_15 = periods.get('0-15', {}) or {}
        period_76_90 = periods.get('76-90', {}) or {}
        
        features[f'{prefix}gk_early_sr'] = period_0_15.get('sr', period_0_15.get('save_rate', 75))
        features[f'{prefix}gk_late_sr'] = period_76_90.get('sr', period_76_90.get('save_rate', 70))
        
        features[f'{prefix}gk_h1_sr'] = timing.get('first_half_sr', 70)
        features[f'{prefix}gk_h2_sr'] = timing.get('second_half_sr', 70)
        features[f'{prefix}gk_clutch'] = timing.get('clutch_factor', 0)
        
        pattern = timing.get('pattern', 'CONSISTENT')
        pattern_map = {'CONSISTENT': 0, 'CLUTCH_PERFORMER': 1, 'SLOW_STARTER': -1, 'FADES_LATE': -1, 'LATE_COLLAPSE': -2}
        features[f'{prefix}gk_pattern'] = pattern_map.get(pattern, 0)

        # ═══════════════════════════════════════════════════════════════════════
        # EXPLOITS V4.4 - Signal betting direct
        # ═══════════════════════════════════════════════════════════════════════
        exploits = gk.get('exploits', []) or []
        features[f'{prefix}gk_num_exploits'] = len(exploits)
        
        exploit_markets = [e.get('market', '') for e in exploits]
        features[f'{prefix}gk_exploit_goals_over'] = 1 if 'Goals Over' in exploit_markets else 0
        features[f'{prefix}gk_exploit_header'] = 1 if 'Header Goal' in exploit_markets else 0
        features[f'{prefix}gk_exploit_corner'] = 1 if 'Corner Goal' in exploit_markets else 0
        features[f'{prefix}gk_exploit_early'] = 1 if 'First Goal 0-15 min' in exploit_markets else 0
        features[f'{prefix}gk_exploit_late'] = 1 if 'Goal 76-90 min' in exploit_markets else 0

        # ═══════════════════════════════════════════════════════════════════════
        # DEFENDER DNA V9 (Aggregated)
        # ═══════════════════════════════════════════════════════════════════════
        defenders = team_data.get('defenders', {}) or {}
        
        features[f'{prefix}def_num'] = defenders.get('num_defenders', 4)
        features[f'{prefix}def_cards_90'] = defenders.get('avg_cards_90', 0.2)
        features[f'{prefix}def_shield'] = defenders.get('avg_shield', 50)
        features[f'{prefix}def_fortress'] = defenders.get('avg_fortress', 50)
        features[f'{prefix}def_discipline'] = defenders.get('avg_discipline', 50)
        features[f'{prefix}def_alpha'] = defenders.get('avg_alpha', 0)
        features[f'{prefix}def_sharpe'] = defenders.get('avg_sharpe', 0)
        features[f'{prefix}def_transition_vuln'] = defenders.get('max_transition_vuln', 0)
        features[f'{prefix}def_disciplinary_risk'] = defenders.get('disciplinary_risk', 0)
        
        # ═══════════════════════════════════════════════════════════════════════
        # FOOTBALL-DATA DNA (2025-26)
        # ═══════════════════════════════════════════════════════════════════════
        
        # Corners
        corners = team_data.get('corners_dna', {}) or {}
        features[f'{prefix}corners_for'] = corners.get('corners_for_avg', 5)
        features[f'{prefix}corners_against'] = corners.get('corners_against_avg', 5)
        features[f'{prefix}corners_total'] = corners.get('corners_total_avg', 10)
        features[f'{prefix}corners_over_95_rate'] = corners.get('over_95_rate', 50)
        features[f'{prefix}corners_over_105_rate'] = corners.get('over_105_rate', 40)
        
        # Shots
        shots = team_data.get('shots_dna', {}) or {}
        features[f'{prefix}shots_for'] = shots.get('shots_for_avg', 12)
        features[f'{prefix}shots_against'] = shots.get('shots_against_avg', 12)
        features[f'{prefix}sot_for'] = shots.get('sot_for_avg', 4)
        features[f'{prefix}sot_against'] = shots.get('sot_against_avg', 4)
        features[f'{prefix}shot_accuracy'] = shots.get('shot_accuracy', 33)
        
        # Fouls
        fouls = team_data.get('fouls_dna', {}) or {}
        features[f'{prefix}fouls_committed'] = fouls.get('fouls_committed_avg', 12)
        features[f'{prefix}fouls_suffered'] = fouls.get('fouls_suffered_avg', 12)
        features[f'{prefix}fouls_to_yellow'] = fouls.get('fouls_to_yellow_rate', 15)
        
        # Cards
        cards = team_data.get('cards_team_dna', {}) or {}
        features[f'{prefix}yellow_cards'] = cards.get('yellow_cards_avg', 2)
        features[f'{prefix}red_cards'] = cards.get('red_cards_avg', 0.05)
        features[f'{prefix}total_cards_match'] = cards.get('total_cards_match_avg', 4)
        
        # Goals Enhanced
        goals = team_data.get('goals_enhanced', {}) or {}
        features[f'{prefix}goals_for'] = goals.get('goals_for_avg', 1.3)
        features[f'{prefix}goals_against'] = goals.get('goals_against_avg', 1.3)
        features[f'{prefix}goals_1h_for'] = goals.get('goals_1h_for_avg', 0.6)
        features[f'{prefix}over_25_rate'] = goals.get('over_25_rate', 55)
        features[f'{prefix}btts_rate'] = goals.get('btts_rate', 55)
        features[f'{prefix}cs_rate'] = goals.get('cs_rate', 30)
        
        # ═══════════════════════════════════════════════════════════════════════
        # ZONE ANALYSIS
        # ═══════════════════════════════════════════════════════════════════════
        zones = team_data.get('zones', {}) or {}
        
        # Extraire les zones vulnérables
        if zones:
            zone_data = zones.get('zones', {}) or {}
            center = zone_data.get('penalty_area_center', {}) or {}
            features[f'{prefix}zone_center_conversion'] = center.get('conversion_rate', 30) if center else 30
            features[f'{prefix}zone_center_xg'] = center.get('xG', 5) if center else 5
        else:
            features[f'{prefix}zone_center_conversion'] = 30
            features[f'{prefix}zone_center_xg'] = 5
        
        # ═══════════════════════════════════════════════════════════════════════
        # GAMESTATE INSIGHTS
        # ═══════════════════════════════════════════════════════════════════════
        gamestate = team_data.get('gamestate', {}) or {}
        
        if gamestate:
            states = gamestate.get('states', {}) or {}
            level = states.get('Goal diff 0', {}) or {}
            features[f'{prefix}gs_level_xga'] = level.get('xG_against_90', 1.5) if level else 1.5
            features[f'{prefix}gs_level_shots'] = level.get('shots_against', 10) if level else 10
        else:
            features[f'{prefix}gs_level_xga'] = 1.5
            features[f'{prefix}gs_level_shots'] = 10
        
        return features
    
    def _extract_combined_features(self, home_data: Dict, away_data: Dict) -> Dict[str, float]:
        """
        Extrait les features combinées (différences, ratios, interactions).
        """
        features = {}
        
        # Helper pour récupérer les valeurs en sécurité
        def safe_get(data, *keys, default=0):
            result = data
            for key in keys:
                if result is None:
                    return default
                if isinstance(result, dict):
                    result = result.get(key, default)
                else:
                    return default
            return result if result is not None else default
        
        # ═══════════════════════════════════════════════════════════════════════
        # DIFFÉRENCES (home - away)
        # ═══════════════════════════════════════════════════════════════════════
        
        # xGA difference
        h_xga = safe_get(home_data, 'defensive_lines', 'foundation', 'xga_90', default=1.5)
        a_xga = safe_get(away_data, 'defensive_lines', 'foundation', 'xga_90', default=1.5)
        features['diff_xga'] = h_xga - a_xga
        
        # Resistance difference
        h_resist = safe_get(home_data, 'defensive_lines', 'resistance', 'resist_global', default=50)
        a_resist = safe_get(away_data, 'defensive_lines', 'resistance', 'resist_global', default=50)
        features['diff_resist'] = h_resist - a_resist
        
        # GK percentile difference
        h_gk = safe_get(home_data, 'goalkeeper', 'gk_percentile', default=50)
        a_gk = safe_get(away_data, 'goalkeeper', 'gk_percentile', default=50)
        features['diff_gk_percentile'] = h_gk - a_gk
        
        # Corners difference
        h_corners = safe_get(home_data, 'corners_dna', 'corners_for_avg', default=5)
        a_corners = safe_get(away_data, 'corners_dna', 'corners_for_avg', default=5)
        features['diff_corners'] = h_corners - a_corners
        
        # Goals difference
        h_goals = safe_get(home_data, 'goals_enhanced', 'goals_for_avg', default=1.3)
        a_goals = safe_get(away_data, 'goals_enhanced', 'goals_for_avg', default=1.3)
        features['diff_goals_for'] = h_goals - a_goals
        
        # ═══════════════════════════════════════════════════════════════════════
        # SOMMES (attaque home vs défense away et vice versa)
        # ═══════════════════════════════════════════════════════════════════════
        
        # Expected goals home team (offense vs defense)
        h_attack = safe_get(home_data, 'goals_enhanced', 'goals_for_avg', default=1.3)
        a_defense = safe_get(away_data, 'defensive_lines', 'foundation', 'xga_90', default=1.5)
        features['expected_home_goals'] = (h_attack + a_defense) / 2
        
        # Expected goals away team
        a_attack = safe_get(away_data, 'goals_enhanced', 'goals_for_avg', default=1.3)
        h_defense = safe_get(home_data, 'defensive_lines', 'foundation', 'xga_90', default=1.5)
        features['expected_away_goals'] = (a_attack + h_defense) / 2
        
        # Total expected goals
        features['expected_total_goals'] = features['expected_home_goals'] + features['expected_away_goals']
        
        # Total corners expected
        h_c_for = safe_get(home_data, 'corners_dna', 'corners_for_avg', default=5)
        h_c_against = safe_get(home_data, 'corners_dna', 'corners_against_avg', default=5)
        a_c_for = safe_get(away_data, 'corners_dna', 'corners_for_avg', default=5)
        a_c_against = safe_get(away_data, 'corners_dna', 'corners_against_avg', default=5)
        features['expected_total_corners'] = (h_c_for + a_c_against + a_c_for + h_c_against) / 2
        
        # Total cards expected
        h_cards = safe_get(home_data, 'cards_team_dna', 'yellow_cards_avg', default=2)
        a_cards = safe_get(away_data, 'cards_team_dna', 'yellow_cards_avg', default=2)
        features['expected_total_cards'] = h_cards + a_cards
        
        # ═══════════════════════════════════════════════════════════════════════
        # RATIOS
        # ═══════════════════════════════════════════════════════════════════════
        
        # Resistance ratio
        features['ratio_resist'] = h_resist / max(a_resist, 1)
        
        # GK quality ratio
        features['ratio_gk'] = h_gk / max(a_gk, 1)
        
        # Goals ratio
        features['ratio_goals'] = h_goals / max(a_goals, 0.1)
        
        # ═══════════════════════════════════════════════════════════════════════
        # TIMING INTERACTION (late game vulnerability)
        # ═══════════════════════════════════════════════════════════════════════
        
        h_late = safe_get(home_data, 'defensive_lines', 'timing_dna', 'late_pct', default=33)
        a_late = safe_get(away_data, 'defensive_lines', 'timing_dna', 'late_pct', default=33)
        features['combined_late_vuln'] = (h_late + a_late) / 2
        
        h_gk_late = safe_get(home_data, 'goalkeeper', 'by_timing', default={})
        a_gk_late = safe_get(away_data, 'goalkeeper', 'by_timing', default={})
        
        h_gk_late_sr = 70
        a_gk_late_sr = 70
        if isinstance(h_gk_late, dict):
            t76_90 = h_gk_late.get('76-90', {})
            if isinstance(t76_90, dict):
                h_gk_late_sr = t76_90.get('save_rate', 70)
        if isinstance(a_gk_late, dict):
            t76_90 = a_gk_late.get('76-90', {})
            if isinstance(t76_90, dict):
                a_gk_late_sr = t76_90.get('save_rate', 70)
        
        features['gk_late_vulnerability'] = (100 - h_gk_late_sr + 100 - a_gk_late_sr) / 2
        
        # ═══════════════════════════════════════════════════════════════════════
        # SET PIECE INTERACTION
        # ═══════════════════════════════════════════════════════════════════════
        
        h_sp_vuln = safe_get(home_data, 'team_defense', 'set_piece_vuln_pct', default=25)
        a_sp_vuln = safe_get(away_data, 'team_defense', 'set_piece_vuln_pct', default=25)
        features['combined_sp_vuln'] = (h_sp_vuln + a_sp_vuln) / 2
        
        # Corner goal probability (GK corner save rate × opponent corners)
        h_gk_corner = safe_get(home_data, 'goalkeeper', 'by_situation', default={})
        if isinstance(h_gk_corner, dict):
            corner_data = h_gk_corner.get('FromCorner', {})
            h_gk_corner_sr = corner_data.get('save_rate', 65) if isinstance(corner_data, dict) else 65
        else:
            h_gk_corner_sr = 65
        
        features['corner_goal_prob'] = (100 - h_gk_corner_sr) * a_c_for / 500  # Normalized
        
        # ═══════════════════════════════════════════════════════════════════════
        # BTTS INDICATORS
        # ═══════════════════════════════════════════════════════════════════════
        
        h_btts = safe_get(home_data, 'goals_enhanced', 'btts_rate', default=55)
        a_btts = safe_get(away_data, 'goals_enhanced', 'btts_rate', default=55)
        features['combined_btts_rate'] = (h_btts + a_btts) / 2
        
        h_cs = safe_get(home_data, 'goals_enhanced', 'cs_rate', default=30)
        a_cs = safe_get(away_data, 'goals_enhanced', 'cs_rate', default=30)
        features['combined_cs_rate'] = (h_cs + a_cs) / 2
        
        # ═══════════════════════════════════════════════════════════════════════
        # DISCIPLINARY INTERACTION
        # ═══════════════════════════════════════════════════════════════════════
        
        h_fouls = safe_get(home_data, 'fouls_dna', 'fouls_committed_avg', default=12)
        a_fouls = safe_get(away_data, 'fouls_dna', 'fouls_committed_avg', default=12)
        features['combined_fouls'] = h_fouls + a_fouls
        
        h_fouls_yellow = safe_get(home_data, 'fouls_dna', 'fouls_to_yellow_rate', default=15)
        a_fouls_yellow = safe_get(away_data, 'fouls_dna', 'fouls_to_yellow_rate', default=15)
        features['combined_fouls_to_yellow'] = (h_fouls_yellow + a_fouls_yellow) / 2
        
        return features
    
    def _extract_referee_features(self, ref_data: Dict) -> Dict[str, float]:
        """Extrait les features arbitre."""
        features = {}
        
        features['ref_card_impact'] = ref_data.get('card_impact', 1.0)
        features['ref_trigger_rate'] = ref_data.get('card_trigger_rate', 0.15)
        features['ref_avg_cards'] = ref_data.get('avg_cards', 4.0)
        features['ref_avg_yellows'] = ref_data.get('avg_yellows', 3.5)
        features['ref_over_35_pct'] = ref_data.get('over_35_pct', 40)
        features['ref_over_45_pct'] = ref_data.get('over_45_pct', 20)
        features['ref_avg_goals'] = ref_data.get('avg_goals', 2.7)
        features['ref_strictness'] = 1 if ref_data.get('strictness') == 'STRICT' else 0
        features['ref_home_bias'] = ref_data.get('home_bias', 0)
        
        return features
    
    def _get_default_referee_features(self) -> Dict[str, float]:
        """Valeurs par défaut si pas de referee."""
        return {
            'ref_card_impact': 1.0,
            'ref_trigger_rate': 0.15,
            'ref_avg_cards': 4.0,
            'ref_avg_yellows': 3.5,
            'ref_over_35_pct': 40,
            'ref_over_45_pct': 20,
            'ref_avg_goals': 2.7,
            'ref_strictness': 0,
            'ref_home_bias': 0,
        }
    
    def get_feature_names(self) -> List[str]:
        """Retourne la liste des noms de features."""
        # Générer un exemple pour obtenir les noms
        dummy_features = self.extract_match_features('Arsenal', 'Chelsea')
        return list(dummy_features.keys())
    
    def build_dataset(self, matches_df: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """
        Construit un dataset complet à partir des matchs historiques.
        
        Args:
            matches_df: DataFrame avec colonnes HomeTeam, AwayTeam, Referee, etc.
        
        Returns:
            X (features), y (targets)
        """
        features_list = []
        targets_list = []
        
        for idx, row in matches_df.iterrows():
            try:
                # Extraire features
                features = self.extract_match_features(
                    home_team=row['HomeTeam'],
                    away_team=row['AwayTeam'],
                    referee=row.get('Referee'),
                    league=row.get('league')
                )
                
                # Extraire targets
                targets = {
                    'total_goals': (row.get('FTHG', 0) or 0) + (row.get('FTAG', 0) or 0),
                    'over_15': int(((row.get('FTHG', 0) or 0) + (row.get('FTAG', 0) or 0)) > 1.5),
                    'over_25': int(((row.get('FTHG', 0) or 0) + (row.get('FTAG', 0) or 0)) > 2.5),
                    'over_35': int(((row.get('FTHG', 0) or 0) + (row.get('FTAG', 0) or 0)) > 3.5),
                    'btts': int((row.get('FTHG', 0) or 0) > 0 and (row.get('FTAG', 0) or 0) > 0),
                    'cs_home': int((row.get('FTAG', 0) or 0) == 0),
                    'cs_away': int((row.get('FTHG', 0) or 0) == 0),
                    'total_corners': (row.get('HC', 0) or 0) + (row.get('AC', 0) or 0),
                    'corners_over_95': int(((row.get('HC', 0) or 0) + (row.get('AC', 0) or 0)) > 9.5),
                    'corners_over_105': int(((row.get('HC', 0) or 0) + (row.get('AC', 0) or 0)) > 10.5),
                    'total_cards': (row.get('HY', 0) or 0) + (row.get('AY', 0) or 0),
                    'cards_over_35': int(((row.get('HY', 0) or 0) + (row.get('AY', 0) or 0)) > 3.5),
                    'cards_over_45': int(((row.get('HY', 0) or 0) + (row.get('AY', 0) or 0)) > 4.5),
                    '1h_total_goals': (row.get('HTHG', 0) or 0) + (row.get('HTAG', 0) or 0),  # Régression
                    '1h_over_05': int(((row.get('HTHG', 0) or 0) + (row.get('HTAG', 0) or 0)) > 0.5),
                }
                
                features_list.append(features)
                targets_list.append(targets)
                
            except Exception as e:
                # Skip matchs avec erreurs
                continue
        
        X = pd.DataFrame(features_list)
        y = pd.DataFrame(targets_list)
        
        return X, y


# ═══════════════════════════════════════════════════════════════════════════════
# TEST
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == '__main__':
    import sys
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from data.loader import DefenseDataLoader
    
    # Charger les données
    loader = DefenseDataLoader()
    loader.load_all()
    
    # Créer le feature engineer
    engineer = FeatureEngineer(loader)
    
    # Test: extraire features pour un match
    print("\n" + "=" * 80)
    print("🧪 TEST: Features Arsenal vs Chelsea")
    print("=" * 80)
    
    features = engineer.extract_match_features('Arsenal', 'Chelsea', referee='Michael Oliver')
    
    print(f"\n📊 Nombre de features: {len(features)}")
    print(f"\n📋 Catégories:")
    
    # Compter par préfixe
    prefixes = {}
    for key in features.keys():
        if key.startswith('h_'):
            prefixes['Home Team'] = prefixes.get('Home Team', 0) + 1
        elif key.startswith('a_'):
            prefixes['Away Team'] = prefixes.get('Away Team', 0) + 1
        elif key.startswith('ref_'):
            prefixes['Referee'] = prefixes.get('Referee', 0) + 1
        elif key.startswith('diff_') or key.startswith('ratio_') or key.startswith('expected_') or key.startswith('combined_'):
            prefixes['Combined'] = prefixes.get('Combined', 0) + 1
        else:
            prefixes['Other'] = prefixes.get('Other', 0) + 1
    
    for cat, count in prefixes.items():
        print(f"   • {cat}: {count} features")
    
    # Afficher quelques features
    print(f"\n📋 Exemples de features:")
    for key, value in list(features.items())[:20]:
        print(f"   • {key}: {value:.3f}" if isinstance(value, float) else f"   • {key}: {value}")
    
    # Test: construire dataset
    print("\n" + "=" * 80)
    print("🧪 TEST: Construction dataset (100 matchs)")
    print("=" * 80)
    
    matches = loader.get_matches().head(100)
    X, y = engineer.build_dataset(matches)
    
    print(f"\n📊 Dataset construit:")
    print(f"   • X: {X.shape[0]} matchs × {X.shape[1]} features")
    print(f"   • y: {y.shape[0]} matchs × {y.shape[1]} targets")
    print(f"\n📋 Targets disponibles: {list(y.columns)}")
    print(f"\n📋 Distribution Over 2.5:")
    print(f"   • Yes: {y['over_25'].sum()} ({y['over_25'].mean()*100:.1f}%)")
    print(f"   • No: {len(y) - y['over_25'].sum()} ({(1-y['over_25'].mean())*100:.1f}%)")
