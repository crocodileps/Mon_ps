"""
CORNER ENGINE V1.0 - Analyse des corners

Utilise corner_dna de quantum.team_stats_extended
"""

from typing import Dict, Any


class CornerEngine:
    """Analyse les marchés corners"""
    
    # Seuils Over/Under populaires
    THRESHOLDS = [8.5, 9.5, 10.5, 11.5]
    
    def analyze(self, home_data: Dict, away_data: Dict) -> Dict[str, Any]:
        """Analyse les probabilités corners pour un match"""
        
        home_dna = home_data.get("dna", {}).get("corner", {})
        away_dna = away_data.get("dna", {}).get("corner", {})
        
        # Corners moyens
        home_for = home_dna.get("corners_for_avg", 5.0)
        home_against = home_dna.get("corners_against_avg", 5.0)
        away_for = away_dna.get("corners_for_avg", 5.0)
        away_against = away_dna.get("corners_against_avg", 5.0)
        
        # Estimation corners du match
        # Home corners = home_for + boost domicile
        expected_home = (home_for * 1.1 + away_against * 0.9) / 2
        # Away corners = away_for - malus extérieur
        expected_away = (away_for * 0.9 + home_against * 1.1) / 2
        expected_total = expected_home + expected_away
        
        # Probabilités Over par seuil
        over_probs = {}
        
        # Over 8.5 - facile si total > 9
        over_probs["over_8_5"] = self._calc_over_prob(expected_total, 8.5, home_dna, away_dna, "over_9_5_pct")
        
        # Over 9.5
        over_probs["over_9_5"] = self._calc_over_prob(expected_total, 9.5, home_dna, away_dna, "over_9_5_pct")
        
        # Over 10.5
        over_probs["over_10_5"] = self._calc_over_prob(expected_total, 10.5, home_dna, away_dna, "over_10_5_pct")
        
        # Over 11.5
        over_probs["over_11_5"] = self._calc_over_prob(expected_total, 11.5, home_dna, away_dna, "over_11_5_pct")
        
        # First corner (home favori ~55%)
        home_first_pct = 55 + (expected_home - expected_away) * 3
        home_first_pct = max(35, min(70, home_first_pct))
        
        return {
            "expected_home_corners": round(expected_home, 1),
            "expected_away_corners": round(expected_away, 1),
            "expected_total_corners": round(expected_total, 1),
            "over_8_5_prob": over_probs["over_8_5"],
            "over_9_5_prob": over_probs["over_9_5"],
            "over_10_5_prob": over_probs["over_10_5"],
            "over_11_5_prob": over_probs["over_11_5"],
            "first_corner_home_prob": home_first_pct / 100,
            "first_corner_away_prob": 1 - home_first_pct / 100,
            "home_dna": home_dna.get("profile", "UNKNOWN"),
            "away_dna": away_dna.get("profile", "UNKNOWN"),
        }
    
    def _calc_over_prob(
        self, 
        expected: float, 
        threshold: float,
        home_dna: Dict,
        away_dna: Dict,
        dna_key: str
    ) -> float:
        """Calcule P(Over threshold) basé sur expected et DNA historique"""
        
        # Base: fonction sigmoïde centrée sur le seuil
        diff = expected - threshold
        base_prob = 0.50 + diff * 0.10  # ±10% par corner d'écart
        
        # Ajuster avec DNA historique si disponible
        home_hist = home_dna.get(dna_key, 50) / 100
        away_hist = away_dna.get(dna_key, 50) / 100
        hist_avg = (home_hist + away_hist) / 2
        
        # Blend: 60% modèle, 40% historique
        final_prob = base_prob * 0.60 + hist_avg * 0.40
        
        return max(0.15, min(0.85, final_prob))
