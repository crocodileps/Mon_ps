"""
BAYESIAN FUSION V3.0 - Basé sur Données Réelles

Utilise market_profiles de la DB comme BASE, puis ajuste avec les engines.
Supporte 22 marchés.
"""

from typing import Dict, Any, Optional
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))


class BayesianFusion:
    """
    Fusionne les probabilités en utilisant:
    1. Données historiques réelles (market_profiles) comme BASE
    2. Ajustements des engines comme MODIFICATEURS
    """
    
    # Poids des ajustements engines (max ±15% de modification)
    ENGINE_WEIGHTS = {
        "matchup": 0.25,
        "chain": 0.20,
        "coach": 0.15,
        "pattern": 0.15,
        "variance": 0.15,
        "referee": 0.10,
    }
    
    # Marchés supportés
    SUPPORTED_MARKETS = [
        "1X2", "over_25", "under_25", "over_15", "under_15", "over_35", "under_35",
        "btts", "dc_1x", "dc_x2", "dc_12", "dnb_home", "dnb_away",
    ]
    
    def __init__(self, data_hub=None):
        self.data_hub = data_hub
    
    def fuse(
        self,
        home_team: str,
        away_team: str,
        engine_outputs: Dict[str, Any],
        odds: Dict[str, Dict[str, float]],
        data_hub=None
    ) -> Dict[str, Dict[str, float]]:
        """
        Fusionne les probabilités pour tous les marchés demandés.
        
        Méthode:
        1. Récupérer les taux historiques réels des deux équipes
        2. Combiner selon la formule du marché
        3. Appliquer les ajustements des engines (±15% max)
        """
        hub = data_hub or self.data_hub
        probabilities = {}
        
        # Récupérer les profils marchés
        home_profile = hub.get_market_profile(home_team, "home") if hub else self._default_profile()
        away_profile = hub.get_market_profile(away_team, "away") if hub else self._default_profile()
        
        # Calculer les ajustements engines
        adjustments = self._calculate_adjustments(engine_outputs)
        
        # 1X2
        if "1X2" in odds:
            probabilities["1X2"] = self._fuse_1x2(
                home_team, away_team, engine_outputs, odds["1X2"], hub
            )
        
        # Over/Under 2.5
        if "over_25" in odds:
            probabilities["over_25"] = self._fuse_over_under(
                home_profile, away_profile, adjustments, odds["over_25"], threshold=2.5
            )
        
        # Over/Under 1.5
        if "over_15" in odds:
            probabilities["over_15"] = self._fuse_over_under(
                home_profile, away_profile, adjustments, odds["over_15"], threshold=1.5
            )
        
        # Over/Under 3.5
        if "over_35" in odds:
            probabilities["over_35"] = self._fuse_over_under(
                home_profile, away_profile, adjustments, odds["over_35"], threshold=3.5
            )
        
        # BTTS
        if "btts" in odds:
            probabilities["btts"] = self._fuse_btts(
                home_profile, away_profile, adjustments, odds["btts"], hub, home_team, away_team
            )
        
        # Double Chance
        if "dc_1x" in odds:
            probabilities["dc_1x"] = self._fuse_double_chance(
                probabilities.get("1X2", {}), "1x", odds["dc_1x"]
            )
        if "dc_x2" in odds:
            probabilities["dc_x2"] = self._fuse_double_chance(
                probabilities.get("1X2", {}), "x2", odds["dc_x2"]
            )
        if "dc_12" in odds:
            probabilities["dc_12"] = self._fuse_double_chance(
                probabilities.get("1X2", {}), "12", odds["dc_12"]
            )
        
        # Draw No Bet
        if "dnb_home" in odds:
            probabilities["dnb_home"] = self._fuse_dnb(
                probabilities.get("1X2", {}), "home", odds["dnb_home"]
            )
        if "dnb_away" in odds:
            probabilities["dnb_away"] = self._fuse_dnb(
                probabilities.get("1X2", {}), "away", odds["dnb_away"]
            )
        
        return probabilities
    
    def _default_profile(self) -> Dict[str, float]:
        """Profil par défaut (moyenne Premier League)"""
        return {
            "over25": 53.0,
            "btts": 52.0,
            "under25": 47.0,
            "clean_sheet": 25.0,
            "fail_to_score": 25.0,
        }
    
    def _calculate_adjustments(self, outputs: Dict) -> Dict[str, float]:
        """Calcule les ajustements depuis les engines"""
        matchup = outputs.get("matchup", {})
        chain = outputs.get("chain", {})
        coach = outputs.get("coach", {})
        pattern = outputs.get("pattern", {})
        variance = outputs.get("variance", {})
        
        # Edge offensif total (influence Over/BTTS)
        offensive_edge = (
            matchup.get("home_attack_edge", 0) + matchup.get("away_attack_edge", 0)
        ) / 2
        
        flow = chain.get("flow_differential", 0)
        coach_over = coach.get("market_impacts", {}).get("over25_combined", 0)
        coach_btts = coach.get("market_impacts", {}).get("btts_combined", 0)
        
        return {
            "offensive": offensive_edge * 0.5 + flow * 0.3,
            "coach_over": coach_over,
            "coach_btts": coach_btts,
            "momentum": pattern.get("total_pattern_edge", 0),
            "variance": variance.get("regression_edge", 0),
        }
    
    def _fuse_1x2(
        self,
        home_team: str,
        away_team: str,
        outputs: Dict,
        market_odds: Dict,
        hub
    ) -> Dict[str, float]:
        """
        1X2: Partir des implied odds (marché efficient) puis ajuster
        """
        # Implied probabilities (référence marché)
        implied_home = 1 / market_odds.get("home", 2.0)
        implied_draw = 1 / market_odds.get("draw", 3.5)
        implied_away = 1 / market_odds.get("away", 4.0)
        total = implied_home + implied_draw + implied_away
        
        market_home = implied_home / total
        market_draw = implied_draw / total
        market_away = implied_away / total
        
        # Ajustements engines
        matchup = outputs.get("matchup", {})
        chain = outputs.get("chain", {})
        coach = outputs.get("coach", {})
        variance = outputs.get("variance", {})
        
        home_edge = matchup.get("home_attack_edge", 0) - matchup.get("away_attack_edge", 0)
        flow = chain.get("flow_differential", 0)
        coach_edge = coach.get("tactical_edge", 0)
        var_edge = variance.get("regression_edge", 0)
        
        total_edge = home_edge * 0.4 + flow * 0.25 + coach_edge * 0.2 + var_edge * 0.15
        
        # Limiter à ±12%
        adjustment = max(-0.12, min(0.12, total_edge))
        
        home_prob = market_home + adjustment
        away_prob = market_away - adjustment * 0.7
        draw_prob = 1 - home_prob - away_prob
        
        # Contraintes
        home_prob = max(0.08, min(0.88, home_prob))
        away_prob = max(0.05, min(0.85, away_prob))
        draw_prob = max(0.12, min(0.38, draw_prob))
        
        total = home_prob + draw_prob + away_prob
        return {
            "home": home_prob / total,
            "draw": draw_prob / total,
            "away": away_prob / total,
        }
    
    def _fuse_over_under(
        self,
        home_profile: Dict,
        away_profile: Dict,
        adjustments: Dict,
        market_odds: Dict,
        threshold: float = 2.5
    ) -> Dict[str, float]:
        """
        Over/Under: Combiner les taux historiques des deux équipes
        
        Formule: P(Over) = (home_over_rate + away_over_rate) / 2
        Puis ajuster avec engines
        """
        # Sélectionner le bon taux selon le seuil
        if threshold == 2.5:
            base_home = home_profile.get("over25", 53)
            base_away = away_profile.get("over25", 53)
        elif threshold == 1.5:
            # Over 1.5 généralement plus haut
            base_home = min(95, home_profile.get("over25", 53) + 25)
            base_away = min(95, away_profile.get("over25", 53) + 25)
        elif threshold == 3.5:
            # Over 3.5 généralement plus bas
            base_home = max(15, home_profile.get("over25", 53) - 20)
            base_away = max(15, away_profile.get("over25", 53) - 20)
        else:
            base_home = home_profile.get("over25", 53)
            base_away = away_profile.get("over25", 53)
        
        # Moyenne pondérée (home légèrement favorisé)
        base_over = (base_home * 0.55 + base_away * 0.45) / 100
        
        # Ajustements engines (max ±10%)
        offensive_adj = adjustments.get("offensive", 0) * 0.15
        coach_adj = adjustments.get("coach_over", 0) * 0.08
        
        over_prob = base_over + offensive_adj + coach_adj
        over_prob = max(0.20, min(0.85, over_prob))
        
        return {
            "over": over_prob,
            "under": 1 - over_prob,
        }
    
    def _fuse_btts(
        self,
        home_profile: Dict,
        away_profile: Dict,
        adjustments: Dict,
        market_odds: Dict,
        hub,
        home_team: str,
        away_team: str
    ) -> Dict[str, float]:
        """
        BTTS: P(BTTS) basé sur les taux historiques
        
        Formule simplifiée: moyenne des deux taux BTTS
        (car BTTS = les deux marquent, donc dépend des deux équipes)
        """
        base_home_btts = home_profile.get("btts", 52)  # Liverpool home BTTS
        base_away_btts = away_profile.get("btts", 52)  # Bournemouth away BTTS
        
        # Moyenne pondérée
        base_btts = (base_home_btts + base_away_btts) / 2 / 100
        
        # Vérifier si spécialistes
        if hub:
            home_spec = hub.is_specialist(home_team, "btts_yes", "home")
            away_spec = hub.is_specialist(away_team, "btts_yes", "away")
            
            if home_spec or away_spec:
                base_btts = min(0.80, base_btts + 0.08)
            
            home_spec_no = hub.is_specialist(home_team, "btts_no", "home")
            away_spec_no = hub.is_specialist(away_team, "btts_no", "away")
            
            if home_spec_no or away_spec_no:
                base_btts = max(0.25, base_btts - 0.10)
        
        # Ajustements
        coach_adj = adjustments.get("coach_btts", 0) * 0.05
        offensive_adj = adjustments.get("offensive", 0) * 0.08
        
        btts_prob = base_btts + coach_adj + offensive_adj
        btts_prob = max(0.25, min(0.80, btts_prob))
        
        return {
            "yes": btts_prob,
            "no": 1 - btts_prob,
        }
    
    def _fuse_double_chance(
        self,
        probs_1x2: Dict,
        dc_type: str,
        market_odds: Dict
    ) -> Dict[str, float]:
        """Double Chance: Somme des probabilités 1X2"""
        if not probs_1x2:
            return {"yes": 0.5, "no": 0.5}
        
        if dc_type == "1x":
            prob = probs_1x2.get("home", 0.4) + probs_1x2.get("draw", 0.25)
        elif dc_type == "x2":
            prob = probs_1x2.get("draw", 0.25) + probs_1x2.get("away", 0.35)
        elif dc_type == "12":
            prob = probs_1x2.get("home", 0.4) + probs_1x2.get("away", 0.35)
        else:
            prob = 0.65
        
        return {"yes": prob, "no": 1 - prob}
    
    def _fuse_dnb(
        self,
        probs_1x2: Dict,
        selection: str,
        market_odds: Dict
    ) -> Dict[str, float]:
        """Draw No Bet: Probabilité conditionnelle sans le nul"""
        if not probs_1x2:
            return {"yes": 0.5, "no": 0.5}
        
        home = probs_1x2.get("home", 0.4)
        away = probs_1x2.get("away", 0.35)
        
        # P(Home|pas nul) = P(Home) / (P(Home) + P(Away))
        total = home + away
        if total == 0:
            return {"yes": 0.5, "no": 0.5}
        
        if selection == "home":
            prob = home / total
        else:
            prob = away / total
        
        return {"yes": prob, "no": 1 - prob}
