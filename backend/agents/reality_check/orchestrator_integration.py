#!/usr/bin/env python3
"""
🔗 REALITY CHECK - ORCHESTRATOR V7 INTEGRATION
===============================================

Ce fichier contient le code à ajouter dans orchestrator_v7_smart.py
pour intégrer le Reality Check.

Instructions:
1. Ajouter l'import en haut du fichier
2. Initialiser le RealityChecker dans __init__
3. Appeler apply_reality_check() avant de sauvegarder les picks
"""

# ============================================================
# ÉTAPE 1 : IMPORTS À AJOUTER (en haut de orchestrator_v7_smart.py)
# ============================================================

IMPORTS_TO_ADD = '''
# Reality Check Integration (AJOUT)
try:
    from agents.reality_check import RealityChecker
    REALITY_CHECK_ENABLED = True
    print("✅ Reality Check Module loaded")
except ImportError as e:
    REALITY_CHECK_ENABLED = False
    print(f"⚠️ Reality Check not available: {e}")
'''

# ============================================================
# ÉTAPE 2 : INIT À AJOUTER (dans __init__ de CLVOrchestratorV7)
# ============================================================

INIT_TO_ADD = '''
        # Reality Check Engine
        self.reality_checker = None
        if REALITY_CHECK_ENABLED:
            try:
                self.reality_checker = RealityChecker(DB_CONFIG)
                logger.info("🧠 Reality Check Engine initialized")
            except Exception as e:
                logger.warning(f"Reality Check init failed: {e}")
'''

# ============================================================
# ÉTAPE 3 : MÉTHODE À AJOUTER (nouvelle méthode dans la classe)
# ============================================================

METHOD_TO_ADD = '''
    def apply_reality_check(self, home_team: str, away_team: str, 
                            raw_score: int, market: str, direction: str) -> dict:
        """
        Applique le filtre Reality Check sur un pick.
        
        Args:
            home_team: Équipe domicile
            away_team: Équipe extérieur
            raw_score: Score V7 original (0-100)
            market: Type de marché (h2h, totals, etc.)
            direction: Direction du pari (home, away, over, under, etc.)
        
        Returns:
            Dict avec score ajusté, warnings et multiplicateur
        """
        if not self.reality_checker:
            return {
                'adjusted_score': raw_score,
                'warnings': [],
                'confidence_mult': 1.0,
                'reality_score': 50,
                'convergence': 'unknown'
            }
        
        try:
            # Analyse Reality Check
            reality = self.reality_checker.analyze_match(home_team, away_team)
            
            # Récupérer le multiplicateur approprié selon la direction
            mult_key = f'{direction}_mult' if f'{direction}_mult' in reality.adjustments else 'confidence_correction'
            confidence_mult = reality.adjustments.get(mult_key, 1.0)
            
            # Ajuster le score
            adjusted_score = raw_score
            
            # Bonus/Malus selon convergence
            if reality.convergence == 'full_convergence':
                adjusted_score = min(100, int(raw_score * 1.05))  # +5%
            elif reality.convergence == 'divergence':
                adjusted_score = int(raw_score * 0.90)  # -10%
            elif reality.convergence == 'strong_divergence':
                adjusted_score = int(raw_score * 0.80)  # -20%
                logger.warning(f"⚠️ STRONG DIVERGENCE: {home_team} vs {away_team}")
            
            # Appliquer le multiplicateur de confiance
            adjusted_score = int(adjusted_score * confidence_mult)
            adjusted_score = max(0, min(100, adjusted_score))
            
            return {
                'adjusted_score': adjusted_score,
                'warnings': reality.warnings,
                'confidence_mult': confidence_mult,
                'reality_score': reality.reality_score,
                'convergence': reality.convergence,
                'tier_gap': reality.tier_gap,
                'home_tier': reality.home_tier,
                'away_tier': reality.away_tier
            }
            
        except Exception as e:
            logger.error(f"Reality Check error for {home_team} vs {away_team}: {e}")
            return {
                'adjusted_score': raw_score,
                'warnings': [f"Reality Check failed: {e}"],
                'confidence_mult': 1.0,
                'reality_score': 50,
                'convergence': 'error'
            }
'''

# ============================================================
# ÉTAPE 4 : MODIFICATION DE _save_picks (dans la boucle)
# ============================================================

SAVE_PICKS_MODIFICATION = '''
# Dans la boucle de _save_picks, AVANT l'INSERT, ajouter:

# Apply Reality Check
reality_result = self.apply_reality_check(
    home_team=pick['home_team'],
    away_team=pick['away_team'],
    raw_score=pick['sweet_score'],
    market=pick['market'],
    direction=pick['direction']
)

# Mettre à jour le pick avec les données Reality Check
pick['sweet_score'] = reality_result['adjusted_score']
pick['reality_warnings'] = reality_result['warnings']
pick['reality_score'] = reality_result['reality_score']
pick['convergence'] = reality_result['convergence']

# Log si divergence
if reality_result['convergence'] in ['divergence', 'strong_divergence']:
    logger.warning(f"⚠️ {pick['home_team']} vs {pick['away_team']}: {reality_result['convergence']}")
'''

print("Ce fichier contient les instructions d'intégration.")
print("Voir les constantes IMPORTS_TO_ADD, INIT_TO_ADD, METHOD_TO_ADD")
