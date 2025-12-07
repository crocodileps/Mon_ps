"""
╔═══════════════════════════════════════════════════════════════════════════════════════╗
║                    QUANTUM FEATURE CALCULATOR 2.0                                     ║
║                                                                                       ║
║  Calcule les 150+ features à partir des DNA des équipes.                             ║
║  Ces features sont l'avantage concurrentiel du système.                              ║
║                                                                                       ║
║  "On n'entraîne pas sur 'nombre de buts' mais sur des métriques avancées."          ║
║                                                                                       ║
╚═══════════════════════════════════════════════════════════════════════════════════════╝
"""

from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime
import math


@dataclass
class MatchFeatures:
    """Container pour toutes les features d'un match"""
    
    # Identifiants
    home_team: str
    away_team: str
    
    # Features calculées (dictionnaire plat pour ML)
    features: Dict[str, float] = field(default_factory=dict)
    
    # Métadonnées
    calculated_at: datetime = field(default_factory=datetime.now)
    feature_count: int = 0
    warnings: List[str] = field(default_factory=list)
    
    def get(self, key: str, default: float = 0.0) -> float:
        return self.features.get(key, default)
    
    def to_vector(self) -> List[float]:
        """Convertit en vecteur pour ML"""
        return list(self.features.values())
    
    def to_dict(self) -> Dict[str, float]:
        return self.features.copy()


class QuantumFeatureCalculator:
    """
    Calculateur de features Quantum.
    
    150+ features organisées en catégories:
    - Indices Composites (15)
    - Friction Features (20)
    - Temporal Features (30)
    - Physical Features (20)
    - Roster Features (20)
    - Psyche Features (20)
    - Tactical Features (15)
    - Context Features (25)
    - Interaction Features (10)
    """
    
    def __init__(self):
        self.feature_importance: Dict[str, float] = {}
        self._feature_registry: List[str] = []
    
    def calculate_all_features(
        self,
        home_dna: Dict[str, Any],
        away_dna: Dict[str, Any],
        friction: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> MatchFeatures:
        """
        Calcule TOUTES les features pour un match.
        
        Args:
            home_dna: DNA de l'équipe à domicile
            away_dna: DNA de l'équipe à l'extérieur
            friction: Données de friction pré-calculées
            context: Contexte du match (optionnel)
        
        Returns:
            MatchFeatures avec 150+ features
        """
        features = {}
        warnings = []
        
        # 1. INDICES COMPOSITES (15 features)
        composite = self._calc_composite_indices(home_dna, away_dna)
        features.update(composite)
        
        # 2. FRICTION FEATURES (20 features)
        friction_feats = self._calc_friction_features(friction, home_dna, away_dna)
        features.update(friction_feats)
        
        # 3. TEMPORAL FEATURES (30 features)
        temporal = self._calc_temporal_features(home_dna, away_dna)
        features.update(temporal)
        
        # 4. PHYSICAL FEATURES (20 features)
        physical = self._calc_physical_features(home_dna, away_dna, context)
        features.update(physical)
        
        # 5. ROSTER FEATURES (20 features)
        roster = self._calc_roster_features(home_dna, away_dna)
        features.update(roster)
        
        # 6. PSYCHE FEATURES (20 features)
        psyche = self._calc_psyche_features(home_dna, away_dna)
        features.update(psyche)
        
        # 7. TACTICAL FEATURES (15 features)
        tactical = self._calc_tactical_features(home_dna, away_dna)
        features.update(tactical)
        
        # 8. CONTEXT FEATURES (25 features)
        context_feats = self._calc_context_features(home_dna, away_dna, context)
        features.update(context_feats)
        
        # 9. INTERACTION FEATURES (10 features) - Combinaisons clés
        interactions = self._calc_interaction_features(features, home_dna, away_dna)
        features.update(interactions)
        
        # 10. LUCK & REGRESSION FEATURES (10 features)
        luck = self._calc_luck_features(home_dna, away_dna)
        features.update(luck)
        
        # 11. CHAMELEON FEATURES (10 features)
        chameleon = self._calc_chameleon_features(home_dna, away_dna)
        features.update(chameleon)
        
        return MatchFeatures(
            home_team=home_dna.get('team_name', 'Home'),
            away_team=away_dna.get('team_name', 'Away'),
            features=features,
            feature_count=len(features),
            warnings=warnings
        )
    
    # ═══════════════════════════════════════════════════════════════════════════════════
    # 1. INDICES COMPOSITES (15 features)
    # ═══════════════════════════════════════════════════════════════════════════════════
    
    def _calc_composite_indices(self, home: Dict, away: Dict) -> Dict[str, float]:
        """Calcule les indices composites ADCM"""
        
        # Extraire les données contextuelles
        home_ctx = home.get('context_dna', {})
        away_ctx = away.get('context_dna', {})
        home_curr = home.get('current_season', {})
        away_curr = away.get('current_season', {})
        
        # PACE FACTOR = Shots × 2 + Dangerous Attacks × 0.5 + Corners × 3
        home_shots = home_ctx.get('shots_per_match', 12)
        away_shots = away_ctx.get('shots_per_match', 12)
        
        pace_home = home_shots * 2 + home_ctx.get('dangerous_attacks', 40) * 0.5
        pace_away = away_shots * 2 + away_ctx.get('dangerous_attacks', 40) * 0.5
        
        # CONTROL INDEX = Possession × 0.6 + Pass Accuracy × 0.4
        control_home = home_ctx.get('possession', 50) * 0.6 + home_ctx.get('pass_accuracy', 80) * 0.4
        control_away = away_ctx.get('possession', 50) * 0.6 + away_ctx.get('pass_accuracy', 80) * 0.4
        
        # SNIPER INDEX = Shot Accuracy × 50 + Conversion × 50
        xg_home = home_curr.get('xg_for', home_ctx.get('xg_for', 1.3))
        xg_away = away_curr.get('xg_for', away_ctx.get('xg_for', 1.3))
        
        # Conversion approximée = xG / shots
        conv_home = (xg_home / max(home_shots / 10, 0.1)) * 100
        conv_away = (xg_away / max(away_shots / 10, 0.1)) * 100
        
        sniper_home = min(100, conv_home)
        sniper_away = min(100, conv_away)
        
        return {
            # Indices individuels
            "pace_factor_home": pace_home,
            "pace_factor_away": pace_away,
            "pace_factor_combined": pace_home + pace_away,
            "pace_factor_diff": pace_home - pace_away,
            
            "control_index_home": control_home,
            "control_index_away": control_away,
            "control_combined": control_home + control_away,
            "control_diff": control_home - control_away,
            
            "sniper_index_home": sniper_home,
            "sniper_index_away": sniper_away,
            "sniper_combined": sniper_home + sniper_away,
            "sniper_diff": sniper_home - sniper_away,
            
            # xG combiné
            "xg_combined": xg_home + xg_away,
            "xg_diff": xg_home - xg_away,
            "xg_home": xg_home,
        }
    
    # ═══════════════════════════════════════════════════════════════════════════════════
    # 2. FRICTION FEATURES (20 features)
    # ═══════════════════════════════════════════════════════════════════════════════════
    
    def _calc_friction_features(self, friction: Dict, home: Dict, away: Dict) -> Dict[str, float]:
        """Features de friction tactique"""
        
        kinetic_home = friction.get('kinetic_friction_home', 50)
        kinetic_away = friction.get('kinetic_friction_away', 50)
        
        return {
            # Friction kinétique
            "kinetic_friction_home": kinetic_home,
            "kinetic_friction_away": kinetic_away,
            "kinetic_friction_total": kinetic_home + kinetic_away,
            "kinetic_friction_diff": kinetic_home - kinetic_away,
            
            # Scores de friction
            "friction_score": friction.get('friction_score', 50),
            "chaos_potential": friction.get('chaos_potential', 50),
            
            # Clash metrics
            "style_clash": friction.get('style_clash', 50),
            "tempo_clash": friction.get('tempo_clash', 20),
            "mental_clash": friction.get('mental_clash', 50),
            
            # Prédictions
            "predicted_goals": friction.get('predicted_goals', 2.5),
            
            # Dominance
            "home_dominance_friction": 1 if kinetic_home > kinetic_away + 10 else 0,
            "away_dominance_friction": 1 if kinetic_away > kinetic_home + 10 else 0,
            "balanced_friction": 1 if abs(kinetic_home - kinetic_away) <= 10 else 0,
            
            # Chaos flags
            "is_chaotic_match": 1 if friction.get('chaos_potential', 50) > 70 else 0,
            "is_high_friction": 1 if friction.get('friction_score', 50) > 65 else 0,
            "is_low_friction": 1 if friction.get('friction_score', 50) < 35 else 0,
            
            # Interaction avec les styles
            "friction_x_pace": friction.get('friction_score', 50) * (kinetic_home + kinetic_away) / 100,
            "chaos_x_goals": friction.get('chaos_potential', 50) * friction.get('predicted_goals', 2.5) / 100,
            
            # Defensive solidity (inverse de friction reçue)
            "defensive_solidity_home": max(0, 100 - kinetic_away),
            "defensive_solidity_away": max(0, 100 - kinetic_home),
        }
    
    # ═══════════════════════════════════════════════════════════════════════════════════
    # 3. TEMPORAL FEATURES (30 features)
    # ═══════════════════════════════════════════════════════════════════════════════════
    
    def _calc_temporal_features(self, home: Dict, away: Dict) -> Dict[str, float]:
        """Features temporelles (quand les buts tombent)"""
        
        home_temp = home.get('temporal_dna', {})
        away_temp = away.get('temporal_dna', {})
        
        diesel_home = home_temp.get('diesel_factor', 0.5)
        diesel_away = away_temp.get('diesel_factor', 0.5)
        clutch_home = home_temp.get('clutch_factor', 0.5)
        clutch_away = away_temp.get('clutch_factor', 0.5)
        sprinter_home = home_temp.get('sprinter_factor', 0.5)
        sprinter_away = away_temp.get('sprinter_factor', 0.5)
        
        return {
            # Diesel (finit fort)
            "diesel_factor_home": diesel_home,
            "diesel_factor_away": diesel_away,
            "diesel_factor_combined": diesel_home + diesel_away,
            "diesel_factor_diff": diesel_home - diesel_away,
            
            # Clutch (moments critiques)
            "clutch_factor_home": clutch_home,
            "clutch_factor_away": clutch_away,
            "clutch_factor_combined": clutch_home + clutch_away,
            "clutch_factor_diff": clutch_home - clutch_away,
            
            # Sprinter (démarre fort)
            "sprinter_factor_home": sprinter_home,
            "sprinter_factor_away": sprinter_away,
            "sprinter_factor_combined": sprinter_home + sprinter_away,
            "sprinter_factor_diff": sprinter_home - sprinter_away,
            
            # Half-time xG
            "first_half_xg_home": home_temp.get('first_half_xg', 0.7),
            "first_half_xg_away": away_temp.get('first_half_xg', 0.7),
            "second_half_xg_home": home_temp.get('second_half_xg', 0.8),
            "second_half_xg_away": away_temp.get('second_half_xg', 0.8),
            
            "xg_1h_combined": home_temp.get('first_half_xg', 0.7) + away_temp.get('first_half_xg', 0.7),
            "xg_2h_combined": home_temp.get('second_half_xg', 0.8) + away_temp.get('second_half_xg', 0.8),
            
            # Flags
            "both_diesel": 1 if diesel_home > 0.6 and diesel_away > 0.6 else 0,
            "both_sprinter": 1 if sprinter_home > 0.6 and sprinter_away > 0.6 else 0,
            "diesel_vs_sprinter": 1 if (diesel_home > 0.65 and sprinter_away > 0.65) or (diesel_away > 0.65 and sprinter_home > 0.65) else 0,
            
            "home_late_game_killer": 1 if diesel_home > 0.7 and clutch_home > 0.7 else 0,
            "away_late_game_killer": 1 if diesel_away > 0.7 and clutch_away > 0.7 else 0,
            
            "second_half_expected_higher": 1 if (home_temp.get('second_half_xg', 0.8) + away_temp.get('second_half_xg', 0.8)) > (home_temp.get('first_half_xg', 0.7) + away_temp.get('first_half_xg', 0.7)) else 0,
            
            # Late punishment potential
            "late_punishment_home": diesel_home * clutch_home,
            "late_punishment_away": diesel_away * clutch_away,
            
            # Early explosion potential
            "early_explosion": sprinter_home * sprinter_away,
        }
    
    # ═══════════════════════════════════════════════════════════════════════════════════
    # 4. PHYSICAL FEATURES (20 features)
    # ═══════════════════════════════════════════════════════════════════════════════════
    
    def _calc_physical_features(self, home: Dict, away: Dict, context: Optional[Dict]) -> Dict[str, float]:
        """Features physiques (fatigue, pressing)"""
        
        home_phys = home.get('physical_dna', {})
        away_phys = away.get('physical_dna', {})
        
        # Rest days from context
        rest_home = context.get('rest_days_home', 7) if context else 7
        rest_away = context.get('rest_days_away', 7) if context else 7
        european_home = context.get('european_week_home', False) if context else False
        european_away = context.get('european_week_away', False) if context else False
        
        pressing_decay_home = home_phys.get('pressing_decay', 0.2)
        pressing_decay_away = away_phys.get('pressing_decay', 0.2)
        
        # Calcul fatigue
        fatigue_home = max(0, (7 - rest_home) * 0.1) + (0.15 if european_home else 0)
        fatigue_away = max(0, (7 - rest_away) * 0.1) + (0.15 if european_away else 0)
        
        return {
            # Pressing decay
            "pressing_decay_home": pressing_decay_home,
            "pressing_decay_away": pressing_decay_away,
            "pressing_decay_diff": pressing_decay_home - pressing_decay_away,
            "pressing_decay_combined": pressing_decay_home + pressing_decay_away,
            
            # Stamina
            "stamina_home": home_phys.get('stamina', 70),
            "stamina_away": away_phys.get('stamina', 70),
            "stamina_diff": home_phys.get('stamina', 70) - away_phys.get('stamina', 70),
            
            # Fatigue
            "fatigue_home": fatigue_home,
            "fatigue_away": fatigue_away,
            "fatigue_diff": fatigue_home - fatigue_away,
            "fatigue_gap": fatigue_away - fatigue_home,  # Positif = Home plus frais
            
            # Rest days
            "rest_days_home": rest_home,
            "rest_days_away": rest_away,
            "rest_days_gap": rest_home - rest_away,
            
            # European week
            "european_week_home": 1 if european_home else 0,
            "european_week_away": 1 if european_away else 0,
            
            # Collapse potential
            "collapse_potential_away": pressing_decay_away * fatigue_away * 100,
            "collapse_potential_home": pressing_decay_home * fatigue_home * 100,
            
            # Late game physical advantage
            "late_game_physical_adv_home": (1 - pressing_decay_home) * (1 - fatigue_home),
            "late_game_physical_adv_away": (1 - pressing_decay_away) * (1 - fatigue_away),
        }
    
    # ═══════════════════════════════════════════════════════════════════════════════════
    # 5. ROSTER FEATURES (20 features)
    # ═══════════════════════════════════════════════════════════════════════════════════
    
    def _calc_roster_features(self, home: Dict, away: Dict) -> Dict[str, float]:
        """Features de composition d'équipe"""
        
        home_roster = home.get('roster_dna', {})
        away_roster = away.get('roster_dna', {})
        
        mvp_dep_home = home_roster.get('mvp_dependency', 0.3)
        mvp_dep_away = away_roster.get('mvp_dependency', 0.3)
        bench_home = home_roster.get('bench_impact', 5)
        bench_away = away_roster.get('bench_impact', 5)
        
        return {
            # MVP Dependency
            "mvp_dependency_home": mvp_dep_home,
            "mvp_dependency_away": mvp_dep_away,
            "mvp_dependency_diff": mvp_dep_home - mvp_dep_away,
            
            # Bench Impact
            "bench_impact_home": bench_home,
            "bench_impact_away": bench_away,
            "bench_impact_gap": bench_home - bench_away,
            "bench_impact_combined": bench_home + bench_away,
            
            # Clinical
            "clinical_home": self._encode_clinical(home_roster.get('clinical_finisher', 'AVERAGE')),
            "clinical_away": self._encode_clinical(away_roster.get('clinical_finisher', 'AVERAGE')),
            
            # Flags
            "high_mvp_dep_home": 1 if mvp_dep_home > 0.5 else 0,
            "high_mvp_dep_away": 1 if mvp_dep_away > 0.5 else 0,
            "strong_bench_home": 1 if bench_home > 7 else 0,
            "strong_bench_away": 1 if bench_away > 7 else 0,
            "weak_bench_home": 1 if bench_home < 4 else 0,
            "weak_bench_away": 1 if bench_away < 4 else 0,
            
            # Bench warfare potential
            "bench_warfare_advantage_home": max(0, bench_home - bench_away - 2),
            "bench_warfare_advantage_away": max(0, bench_away - bench_home - 2),
            
            # Depth
            "squad_depth_home": home_roster.get('squad_depth', 50),
            "squad_depth_away": away_roster.get('squad_depth', 50),
        }
    
    def _encode_clinical(self, clinical: str) -> float:
        """Encode le niveau clinical en nombre"""
        mapping = {"POOR": 0.3, "AVERAGE": 0.5, "GOOD": 0.7, "CLINICAL": 0.9}
        return mapping.get(clinical, 0.5)
    
    # ═══════════════════════════════════════════════════════════════════════════════════
    # 6. PSYCHE FEATURES (20 features)
    # ═══════════════════════════════════════════════════════════════════════════════════
    
    def _calc_psyche_features(self, home: Dict, away: Dict) -> Dict[str, float]:
        """Features psychologiques"""
        
        home_psyche = home.get('psyche_dna', {})
        away_psyche = away.get('psyche_dna', {})
        
        killer_home = home_psyche.get('killer_instinct', 1.0)
        killer_away = away_psyche.get('killer_instinct', 1.0)
        collapse_home = home_psyche.get('collapse_rate', 0.2)
        collapse_away = away_psyche.get('collapse_rate', 0.2)
        resilience_home = home_psyche.get('resilience_index', 50)
        resilience_away = away_psyche.get('resilience_index', 50)
        
        return {
            # Killer Instinct
            "killer_instinct_home": killer_home,
            "killer_instinct_away": killer_away,
            "killer_instinct_diff": killer_home - killer_away,
            
            # Collapse rate
            "collapse_rate_home": collapse_home,
            "collapse_rate_away": collapse_away,
            "collapse_rate_diff": collapse_home - collapse_away,
            
            # Resilience
            "resilience_index_home": resilience_home,
            "resilience_index_away": resilience_away,
            "resilience_gap": resilience_home - resilience_away,
            
            # Mentality encoded
            "mentality_conservative_home": 1 if home_psyche.get('mentality') == 'CONSERVATIVE' else 0,
            "mentality_conservative_away": 1 if away_psyche.get('mentality') == 'CONSERVATIVE' else 0,
            "mentality_aggressive_home": 1 if home_psyche.get('mentality') == 'AGGRESSIVE' else 0,
            "mentality_aggressive_away": 1 if away_psyche.get('mentality') == 'AGGRESSIVE' else 0,
            
            # Panic factor
            "panic_factor_home": home_psyche.get('panic_factor', 0.5),
            "panic_factor_away": away_psyche.get('panic_factor', 0.5),
            
            # Flags
            "killer_vs_collapse": 1 if killer_home > 1.3 and collapse_away > 0.25 else 0,
            "collapse_alert_home": 1 if collapse_home > 0.3 else 0,
            "collapse_alert_away": 1 if collapse_away > 0.3 else 0,
            
            # Psychological dominance
            "psyche_dominance_home": (killer_home * resilience_home / 100) - (collapse_home * 2),
            "psyche_dominance_away": (killer_away * resilience_away / 100) - (collapse_away * 2),
        }
    
    # ═══════════════════════════════════════════════════════════════════════════════════
    # 7. TACTICAL FEATURES (15 features)
    # ═══════════════════════════════════════════════════════════════════════════════════
    
    def _calc_tactical_features(self, home: Dict, away: Dict) -> Dict[str, float]:
        """Features tactiques"""
        
        home_tac = home.get('tactical_dna', {})
        away_tac = away.get('tactical_dna', {})
        home_nem = home.get('nemesis_dna', {})
        away_nem = away.get('nemesis_dna', {})
        
        return {
            # Formation encoded
            "formation_433_home": 1 if home_tac.get('formation') == '4-3-3' else 0,
            "formation_433_away": 1 if away_tac.get('formation') == '4-3-3' else 0,
            "formation_442_home": 1 if home_tac.get('formation') == '4-4-2' else 0,
            "formation_442_away": 1 if away_tac.get('formation') == '4-4-2' else 0,
            
            # Set piece threat
            "set_piece_threat_home": home_tac.get('set_piece_threat', 0.5),
            "set_piece_threat_away": away_tac.get('set_piece_threat', 0.5),
            "set_piece_diff": home_tac.get('set_piece_threat', 0.5) - away_tac.get('set_piece_threat', 0.5),
            
            # Verticality
            "verticality_home": home_nem.get('verticality', 50),
            "verticality_away": away_nem.get('verticality', 50),
            "verticality_diff": home_nem.get('verticality', 50) - away_nem.get('verticality', 50),
            
            # Pressing intensity (PPDA)
            "ppda_home": home_nem.get('pressing_intensity', 10),
            "ppda_away": away_nem.get('pressing_intensity', 10),
            "ppda_diff": away_nem.get('pressing_intensity', 10) - home_nem.get('pressing_intensity', 10),  # Lower = more intense
            
            # Aerial threat
            "aerial_threat_combined": (home_tac.get('set_piece_threat', 0.5) + away_tac.get('set_piece_threat', 0.5)) * 50,
        }
    
    # ═══════════════════════════════════════════════════════════════════════════════════
    # 8. CONTEXT FEATURES (25 features)
    # ═══════════════════════════════════════════════════════════════════════════════════
    
    def _calc_context_features(self, home: Dict, away: Dict, context: Optional[Dict]) -> Dict[str, float]:
        """Features de contexte"""
        
        home_curr = home.get('current_season', {})
        away_curr = away.get('current_season', {})
        
        pos_home = home_curr.get('position', 10)
        pos_away = away_curr.get('position', 10)
        
        return {
            # Position
            "position_home": pos_home,
            "position_away": pos_away,
            "position_gap": pos_away - pos_home,  # Positif = Home mieux classé
            
            # Points
            "points_home": home_curr.get('points', 0),
            "points_away": away_curr.get('points', 0),
            "ppg_home": home_curr.get('ppg', 1.5),
            "ppg_away": away_curr.get('ppg', 1.5),
            "ppg_diff": home_curr.get('ppg', 1.5) - away_curr.get('ppg', 1.5),
            
            # Zones
            "title_race_home": 1 if pos_home <= 3 else 0,
            "title_race_away": 1 if pos_away <= 3 else 0,
            "europe_race_home": 1 if pos_home <= 7 else 0,
            "europe_race_away": 1 if pos_away <= 7 else 0,
            "relegation_home": 1 if pos_home >= 17 else 0,
            "relegation_away": 1 if pos_away >= 17 else 0,
            
            # Motivation
            "motivation_gap": self._calc_motivation(pos_home) - self._calc_motivation(pos_away),
            "nothing_to_lose_away": 1 if pos_away >= 17 else 0,
            
            # Form (if available)
            "form_momentum_home": self._encode_form(home_curr.get('form', 'NEUTRAL')),
            "form_momentum_away": self._encode_form(away_curr.get('form', 'NEUTRAL')),
            
            # Quality gap
            "quality_gap": (away_curr.get('xg_for', 1.3) - away_curr.get('xg_against', 1.3)) - \
                          (home_curr.get('xg_for', 1.3) - home_curr.get('xg_against', 1.3)),
            
            # Home advantage baseline
            "home_advantage_factor": 1.15,  # Base home advantage
            
            # Big team flags
            "top6_home": 1 if pos_home <= 6 else 0,
            "top6_away": 1 if pos_away <= 6 else 0,
            "bottom6_home": 1 if pos_home >= 15 else 0,
            "bottom6_away": 1 if pos_away >= 15 else 0,
        }
    
    def _calc_motivation(self, position: int) -> float:
        """Calcule le niveau de motivation basé sur la position"""
        if position <= 3:
            return 90  # Title race
        elif position <= 7:
            return 75  # Europe race
        elif position >= 17:
            return 85  # Relegation fight
        return 60  # Mid-table
    
    def _encode_form(self, form: str) -> float:
        """Encode la forme en nombre"""
        mapping = {
            "BLAZING": 1.0, "HOT": 0.8, "WARMING": 0.6,
            "NEUTRAL": 0.5, "COOLING": 0.4, "COLD": 0.2
        }
        return mapping.get(form, 0.5)
    
    # ═══════════════════════════════════════════════════════════════════════════════════
    # 9. INTERACTION FEATURES (10 features)
    # ═══════════════════════════════════════════════════════════════════════════════════
    
    def _calc_interaction_features(self, features: Dict, home: Dict, away: Dict) -> Dict[str, float]:
        """Features d'interaction (combinaisons clés)"""
        
        return {
            # Fatigue × Bench = Late punishment
            "late_punishment_potential_home": features.get('fatigue_away', 0) * features.get('bench_impact_home', 5) * features.get('diesel_factor_home', 0.5),
            "late_punishment_potential_away": features.get('fatigue_home', 0) * features.get('bench_impact_away', 5) * features.get('diesel_factor_away', 0.5),
            
            # Pressing × Build-up weakness = Early goals
            "pressing_death_potential": (10 - features.get('ppda_home', 10)) * features.get('pressing_decay_away', 0.2) * 10,
            
            # High line × Transition speed = Counter goals
            "counter_threat": features.get('verticality_home', 50) * features.get('pace_factor_home', 50) / 100,
            
            # Diesel × Pressing decay = 2H dominance
            "second_half_dominance_home": features.get('diesel_factor_home', 0.5) * (1 + features.get('pressing_decay_away', 0.2)),
            "second_half_dominance_away": features.get('diesel_factor_away', 0.5) * (1 + features.get('pressing_decay_home', 0.2)),
            
            # Chaos × Sniper = Goals expected
            "goals_catalyst": features.get('chaos_potential', 50) * features.get('sniper_combined', 100) / 100,
            
            # Killer × Collapse = Execution
            "execution_potential": features.get('killer_instinct_home', 1) * features.get('collapse_rate_away', 0.2) * 10,
            
            # Conservative × Low block = Under potential
            "under_potential": features.get('mentality_conservative_home', 0) * (100 - features.get('pace_factor_combined', 100)) / 100,
            
            # Total drama potential
            "drama_potential": features.get('diesel_factor_combined', 1) * features.get('clutch_factor_combined', 1) * features.get('chaos_potential', 50) / 50,
        }
    
    # ═══════════════════════════════════════════════════════════════════════════════════
    # 10. LUCK FEATURES (10 features)
    # ═══════════════════════════════════════════════════════════════════════════════════
    
    def _calc_luck_features(self, home: Dict, away: Dict) -> Dict[str, float]:
        """Features de chance/régression"""
        
        home_luck = home.get('luck_dna', {})
        away_luck = away.get('luck_dna', {})
        
        xp_delta_home = home_luck.get('xpoints_delta', 0)
        xp_delta_away = away_luck.get('xpoints_delta', 0)
        
        return {
            # xPoints delta
            "xpoints_delta_home": xp_delta_home,
            "xpoints_delta_away": xp_delta_away,
            "xpoints_delta_diff": xp_delta_home - xp_delta_away,
            
            # Regression direction encoded
            "regression_up_home": 1 if home_luck.get('regression_direction') == 'UP' else 0,
            "regression_up_away": 1 if away_luck.get('regression_direction') == 'UP' else 0,
            "regression_down_home": 1 if home_luck.get('regression_direction') == 'DOWN' else 0,
            "regression_down_away": 1 if away_luck.get('regression_direction') == 'DOWN' else 0,
            
            # Luck profile
            "unlucky_home": 1 if home_luck.get('luck_profile') in ['UNLUCKY', 'VERY_UNLUCKY'] else 0,
            "unlucky_away": 1 if away_luck.get('luck_profile') in ['UNLUCKY', 'VERY_UNLUCKY'] else 0,
            
            # Value potential (unlucky = value)
            "value_regression_home": max(0, xp_delta_home),
            "value_regression_away": max(0, xp_delta_away),
        }
    
    # ═══════════════════════════════════════════════════════════════════════════════════
    # 11. CHAMELEON FEATURES (10 features)
    # ═══════════════════════════════════════════════════════════════════════════════════
    
    def _calc_chameleon_features(self, home: Dict, away: Dict) -> Dict[str, float]:
        """Features d'adaptabilité"""
        
        home_cham = home.get('chameleon_dna', {})
        away_cham = away.get('chameleon_dna', {})
        
        comeback_home = home_cham.get('comeback_ability', 50)
        comeback_away = away_cham.get('comeback_ability', 50)
        adapt_home = home_cham.get('adaptability', 50)
        adapt_away = away_cham.get('adaptability', 50)
        
        return {
            # Comeback ability
            "comeback_ability_home": comeback_home,
            "comeback_ability_away": comeback_away,
            "comeback_diff": comeback_home - comeback_away,
            
            # Adaptability
            "adaptability_home": adapt_home,
            "adaptability_away": adapt_away,
            "adaptability_diff": adapt_home - adapt_away,
            
            # Tactical flexibility
            "flexibility_home": home_cham.get('tactical_flexibility', 50),
            "flexibility_away": away_cham.get('tactical_flexibility', 50),
            
            # Chameleon flags
            "true_chameleon_home": 1 if adapt_home > 70 else 0,
            "true_chameleon_away": 1 if adapt_away > 70 else 0,
            
            # Upset potential
            "upset_potential": (comeback_away * adapt_away) / 100 if comeback_away > 60 else 0,
        }
    
    # ═══════════════════════════════════════════════════════════════════════════════════
    # UTILITY METHODS
    # ═══════════════════════════════════════════════════════════════════════════════════
    
    def get_feature_names(self) -> List[str]:
        """Retourne la liste de toutes les features"""
        # Créer un exemple pour récupérer les noms
        dummy_features = self.calculate_all_features(
            {"team_name": "A"}, {"team_name": "B"}, {}, {}
        )
        return list(dummy_features.features.keys())
    
    def get_feature_count(self) -> int:
        """Retourne le nombre total de features"""
        return len(self.get_feature_names())
