"""
CARD ENGINE V1.0 - Analyse des cartons

Utilise card_dna + referee_intelligence
"""

from typing import Dict, Any, Optional


class CardEngine:
    """Analyse les marchés cartons"""
    
    def analyze(
        self, 
        home_data: Dict, 
        away_data: Dict,
        referee_data: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Analyse les probabilités cartons pour un match"""
        
        home_dna = home_data.get("dna", {}).get("card", {})
        away_dna = away_data.get("dna", {}).get("card", {})
        
        # Cartons moyens par équipe
        home_yellows = home_dna.get("yellows_for_avg", 1.5)
        home_yellows_against = home_dna.get("yellows_against_avg", 1.5)
        away_yellows = away_dna.get("yellows_for_avg", 1.5)
        away_yellows_against = away_dna.get("yellows_against_avg", 1.5)
        
        # Estimation cartons du match (sans arbitre)
        expected_home_cards = (home_yellows + away_yellows_against) / 2
        expected_away_cards = (away_yellows + home_yellows_against) / 2
        expected_total = expected_home_cards + expected_away_cards
        
        # Ajustement arbitre si connu
        referee_boost = 0
        if referee_data:
            ref_avg = referee_data.get("avg_yellow_cards_per_game")
            if ref_avg:
                # Ajuster selon si l'arbitre est plus ou moins sévère
                league_avg = 3.5  # Moyenne PL
                referee_boost = (float(ref_avg) - league_avg) * 0.3
        
        expected_total += referee_boost
        
        # Probabilités Over par seuil
        over_3_5 = self._calc_over_prob(expected_total, 3.5, home_dna, away_dna, "over_3_5_cards_pct")
        over_4_5 = self._calc_over_prob(expected_total, 4.5, home_dna, away_dna, "over_4_5_cards_pct")
        over_5_5 = self._calc_over_prob(expected_total, 5.5, home_dna, away_dna, None)
        
        # Red card probability (rare, ~5% par match en PL)
        home_reds = home_dna.get("reds_per_game", 0.05)
        away_reds = away_dna.get("reds_per_game", 0.05)
        red_prob = min(0.15, home_reds + away_reds + 0.02)
        
        return {
            "expected_home_cards": round(expected_home_cards, 1),
            "expected_away_cards": round(expected_away_cards, 1),
            "expected_total_cards": round(expected_total, 1),
            "over_3_5_prob": over_3_5,
            "over_4_5_prob": over_4_5,
            "over_5_5_prob": over_5_5,
            "red_card_prob": red_prob,
            "referee_boost": round(referee_boost, 2),
            "home_discipline": home_dna.get("discipline_score", 50),
            "away_discipline": away_dna.get("discipline_score", 50),
        }
    
    def _calc_over_prob(
        self,
        expected: float,
        threshold: float,
        home_dna: Dict,
        away_dna: Dict,
        dna_key: Optional[str]
    ) -> float:
        """Calcule P(Over threshold) basé sur expected et DNA historique"""
        
        # Base: fonction sigmoïde
        diff = expected - threshold
        base_prob = 0.50 + diff * 0.12
        
        # Ajuster avec DNA si disponible
        if dna_key:
            home_hist = home_dna.get(dna_key, 50) / 100
            away_hist = away_dna.get(dna_key, 50) / 100
            hist_avg = (home_hist + away_hist) / 2
            final_prob = base_prob * 0.55 + hist_avg * 0.45
        else:
            final_prob = base_prob
        
        return max(0.10, min(0.85, final_prob))
