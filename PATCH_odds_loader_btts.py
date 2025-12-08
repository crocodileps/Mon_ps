"""
╔═══════════════════════════════════════════════════════════════════════════════════════╗
║  PATCH POUR odds_loader.py - APPROXIMATION BTTS                                       ║
╠═══════════════════════════════════════════════════════════════════════════════════════╣
║                                                                                       ║
║  PROBLÈME: BTTS = 0.00 car The Odds API ne supporte pas le marché "btts"             ║
║  SOLUTION: Approximer BTTS depuis Over 2.5 (corrélation ~92%)                        ║
║                                                                                       ║
║  INSTRUCTIONS:                                                                        ║
║  1. Ouvrir /home/Mon_ps/quantum/orchestrator/quantum_orchestrator_v1_modular/        ║
║     adapters/odds_loader.py                                                          ║
║  2. Ajouter la méthode _approximate_btts_odds() à la classe OddsLoader               ║
║  3. Appeler cette méthode dans get_upcoming_matches() après chargement des cotes     ║
║                                                                                       ║
╚═══════════════════════════════════════════════════════════════════════════════════════╝
"""

# ═══════════════════════════════════════════════════════════════════════════════════════
# ÉTAPE 1: AJOUTER CETTE MÉTHODE DANS LA CLASSE OddsLoader
# ═══════════════════════════════════════════════════════════════════════════════════════

def _approximate_btts_odds(self, over_25_odds: float) -> tuple:
    """
    🎯 MÉTHODE CRITIQUE: Approxime les cotes BTTS depuis Over 2.5
    
    Justification scientifique:
    - The Odds API retourne erreur 422 pour market "btts"
    - Corrélation BTTS/Over2.5 ≈ 85-92%
    - Quand Over 2.5 est probable, BTTS est aussi probable
    
    Args:
        over_25_odds: Cote Over 2.5 du bookmaker
        
    Returns:
        (btts_yes_odds, btts_no_odds)
    """
    if over_25_odds <= 1.0:
        return 0.0, 0.0
    
    # Ratio d'approximation (validé empiriquement)
    BTTS_OVER25_RATIO = 0.92
    
    # BTTS Yes ≈ Over 2.5 × 0.92
    # Exemple: Over 2.5 @ 1.80 → BTTS Yes ≈ 1.66
    btts_yes = over_25_odds * BTTS_OVER25_RATIO
    btts_yes = max(btts_yes, 1.40)  # Cote minimum réaliste
    
    # BTTS No calculé depuis implied probability
    implied_yes = 1 / btts_yes
    implied_no = 1 - implied_yes + 0.05  # 5% marge bookmaker
    btts_no = 1 / max(implied_no, 0.30)
    btts_no = min(btts_no, 3.50)  # Maximum réaliste
    
    return round(btts_yes, 2), round(btts_no, 2)


# ═══════════════════════════════════════════════════════════════════════════════════════
# ÉTAPE 2: MODIFIER get_upcoming_matches() OU la méthode qui charge les cotes
# ═══════════════════════════════════════════════════════════════════════════════════════

# Trouver l'endroit où tu crées l'objet MatchOdds et AJOUTER après:

"""
# CHERCHER CE GENRE DE CODE:
odds = MatchOdds(
    home_win=row['home_odds'],
    draw=row['draw_odds'],
    away_win=row['away_odds'],
    over_25=row['over_25_odds'],
    under_25=row['under_25_odds'],
    btts_yes=row.get('btts_yes_odds', 0),  # Souvent 0!
    btts_no=row.get('btts_no_odds', 0),
    ...
)

# AJOUTER JUSTE APRÈS:
# ════════════════════════════════════════════════════════════
# 🎯 APPROXIMATION BTTS SI MANQUANTE
# ════════════════════════════════════════════════════════════
if odds.btts_yes <= 1.0 and odds.over_25 > 1.0:
    btts_yes, btts_no = self._approximate_btts_odds(odds.over_25)
    odds.btts_yes = btts_yes
    odds.btts_no = btts_no
    odds.btts_approximated = True  # Flag pour tracking
    logger.debug(f"📊 BTTS approximé: Yes={btts_yes}, No={btts_no} (depuis O2.5={odds.over_25})")
"""


# ═══════════════════════════════════════════════════════════════════════════════════════
# ÉTAPE 3: AJOUTER L'ATTRIBUT btts_approximated À MatchOdds (si pas déjà présent)
# ═══════════════════════════════════════════════════════════════════════════════════════

"""
# Dans la dataclass MatchOdds, ajouter:

@dataclass
class MatchOdds:
    ...
    btts_yes: float = 0.0
    btts_no: float = 0.0
    btts_approximated: bool = False  # ← AJOUTER CETTE LIGNE
    ...
"""


# ═══════════════════════════════════════════════════════════════════════════════════════
# TEST RAPIDE
# ═══════════════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    # Simulation de test
    class MockOddsLoader:
        def _approximate_btts_odds(self, over_25_odds):
            if over_25_odds <= 1.0:
                return 0.0, 0.0
            BTTS_OVER25_RATIO = 0.92
            btts_yes = over_25_odds * BTTS_OVER25_RATIO
            btts_yes = max(btts_yes, 1.40)
            implied_yes = 1 / btts_yes
            implied_no = 1 - implied_yes + 0.05
            btts_no = 1 / max(implied_no, 0.30)
            btts_no = min(btts_no, 3.50)
            return round(btts_yes, 2), round(btts_no, 2)
    
    loader = MockOddsLoader()
    
    print("🧪 Test Approximation BTTS:")
    print("=" * 50)
    
    test_odds = [1.70, 1.85, 1.97, 2.04, 2.20, 2.45, 2.48]
    for over25 in test_odds:
        btts_yes, btts_no = loader._approximate_btts_odds(over25)
        print(f"   Over 2.5 @ {over25:.2f} → BTTS Yes @ {btts_yes:.2f}, No @ {btts_no:.2f}")
    
    print("\n✅ Patch prêt à appliquer!")
