"""
🧠 REALITY CHECK HELPER V1.0
============================

Fonctions utilitaires pour intégrer Reality Check dans tous les services.
Ce helper centralise la logique d'ajustement des scores et probabilités.

Usage:
    from api.services.reality_check_helper import adjust_prediction, get_match_warnings
    
    # Ajuster un score de confiance
    adjusted = adjust_prediction(home_team, away_team, original_score, market='h2h', direction='home')
    
    # Obtenir les warnings pour affichage
    warnings = get_match_warnings(home_team, away_team)
"""

import sys
sys.path.insert(0, '/app')

from typing import Dict, List, Optional, Tuple
import logging

logger = logging.getLogger('RealityCheckHelper')

# Import Reality Check
try:
    from agents.reality_check import RealityChecker
    from agents.reality_check.data_service import RealityDataService
    _checker = RealityChecker()
    _data_service = RealityDataService()
    REALITY_CHECK_ENABLED = True
    logger.info("✅ Reality Check Helper initialized")
except ImportError as e:
    _checker = None
    _data_service = None
    REALITY_CHECK_ENABLED = False
    logger.warning(f"⚠️ Reality Check not available: {e}")


# ═══════════════════════════════════════════════════════════════════════════════
# FONCTIONS PRINCIPALES
# ═══════════════════════════════════════════════════════════════════════════════

def is_enabled() -> bool:
    """Vérifie si Reality Check est disponible"""
    return REALITY_CHECK_ENABLED


def analyze_match(home_team: str, away_team: str, referee: str = None) -> Optional[Dict]:
    """
    Analyse complète d'un match.
    
    Returns:
        Dict avec reality_score, convergence, warnings, adjustments, etc.
        None si Reality Check non disponible
    """
    if not REALITY_CHECK_ENABLED or not _checker:
        return None
    
    try:
        result = _checker.analyze_match(home_team, away_team, referee=referee)
        return result.to_dict()
    except Exception as e:
        logger.error(f"Reality Check error for {home_team} vs {away_team}: {e}")
        return None


def adjust_prediction(
    home_team: str, 
    away_team: str, 
    original_score: float,
    market: str = 'h2h',
    direction: str = 'home'
) -> Dict:
    """
    Ajuste un score/probabilité en fonction du Reality Check.
    
    Args:
        home_team: Équipe domicile
        away_team: Équipe extérieur
        original_score: Score original (0-100 ou probabilité 0-1)
        market: Type de marché (h2h, totals, btts, etc.)
        direction: Direction du pari (home, away, draw, over, under, btts_yes, btts_no)
    
    Returns:
        Dict avec:
        - adjusted_score: Score ajusté
        - adjustment_factor: Facteur multiplicateur appliqué
        - reality_score: Score Reality Check (0-100)
        - convergence: Niveau de convergence
        - warnings: Liste des warnings
        - applied: Boolean indiquant si ajustement appliqué
    """
    result = {
        'original_score': original_score,
        'adjusted_score': original_score,
        'adjustment_factor': 1.0,
        'reality_score': 50,
        'convergence': 'unknown',
        'warnings': [],
        'applied': False
    }
    
    if not REALITY_CHECK_ENABLED or not _checker:
        return result
    
    try:
        reality = _checker.analyze_match(home_team, away_team)
        
        # Mapping direction -> adjustment key
        mult_map = {
            'home': 'home_win_mult',
            'away': 'away_win_mult',
            'draw': 'draw_mult',
            'over': 'over_mult',
            'under': 'under_mult',
            'btts_yes': 'btts_mult',
            'btts_no': 'btts_mult'
        }
        
        mult_key = mult_map.get(direction, 'confidence_correction')
        adjustment_factor = reality.adjustments.get(mult_key, 1.0)
        
        # Ajustement basé sur la convergence
        convergence_factor = 1.0
        if reality.convergence == 'full_convergence':
            convergence_factor = 1.05  # Boost +5%
        elif reality.convergence == 'divergence':
            convergence_factor = 0.90  # Pénalité -10%
        elif reality.convergence == 'strong_divergence':
            convergence_factor = 0.80  # Pénalité -20%
        
        # Appliquer les ajustements
        adjusted_score = original_score * adjustment_factor * convergence_factor
        
        # Borner le score
        if original_score <= 1:  # Probabilité (0-1)
            adjusted_score = max(0.01, min(0.99, adjusted_score))
        else:  # Score (0-100)
            adjusted_score = max(0, min(100, int(adjusted_score)))
        
        result.update({
            'adjusted_score': adjusted_score,
            'adjustment_factor': round(adjustment_factor * convergence_factor, 3),
            'reality_score': reality.reality_score,
            'convergence': reality.convergence,
            'warnings': reality.warnings,
            'tier_gap': reality.tier_gap,
            'home_tier': reality.home_tier,
            'away_tier': reality.away_tier,
            'applied': True
        })
        
    except Exception as e:
        logger.error(f"adjust_prediction error: {e}")
    
    return result


def adjust_probabilities(
    home_team: str,
    away_team: str,
    probabilities: Dict[str, float]
) -> Dict[str, float]:
    """
    Ajuste un dictionnaire de probabilités.
    
    Args:
        home_team: Équipe domicile
        away_team: Équipe extérieur  
        probabilities: Dict comme {"home": 0.45, "draw": 0.25, "away": 0.30}
    
    Returns:
        Dict de probabilités ajustées (normalisées à 1)
    """
    if not REALITY_CHECK_ENABLED or not _checker:
        return probabilities
    
    try:
        reality = _checker.analyze_match(home_team, away_team)
        
        adjusted = {}
        for key, prob in probabilities.items():
            mult_map = {
                'home': 'home_win_mult',
                'home_win': 'home_win_mult',
                'draw': 'draw_mult',
                'away': 'away_win_mult',
                'away_win': 'away_win_mult',
                'over': 'over_mult',
                'over_25': 'over_mult',
                'under': 'under_mult',
                'under_25': 'under_mult',
                'btts': 'btts_mult',
                'btts_yes': 'btts_mult',
                'btts_no': 'btts_mult'
            }
            
            mult_key = mult_map.get(key.lower(), 'confidence_correction')
            mult = reality.adjustments.get(mult_key, 1.0)
            adjusted[key] = prob * mult
        
        # Normaliser si c'est un marché 3-way (home/draw/away)
        if all(k in adjusted for k in ['home', 'draw', 'away']):
            total = adjusted['home'] + adjusted['draw'] + adjusted['away']
            if total > 0:
                adjusted['home'] /= total
                adjusted['draw'] /= total
                adjusted['away'] /= total
        
        return adjusted
        
    except Exception as e:
        logger.error(f"adjust_probabilities error: {e}")
        return probabilities


def get_match_warnings(home_team: str, away_team: str) -> List[str]:
    """
    Récupère uniquement les warnings pour un match.
    
    Returns:
        Liste de warnings (strings)
    """
    if not REALITY_CHECK_ENABLED or not _checker:
        return []
    
    try:
        reality = _checker.analyze_match(home_team, away_team)
        return reality.warnings
    except Exception as e:
        logger.error(f"get_match_warnings error: {e}")
        return []


def get_team_tier(team_name: str) -> str:
    """
    Récupère le Tier d'une équipe.
    
    Returns:
        Tier (S/A/B/C/D) ou 'C' par défaut
    """
    if not REALITY_CHECK_ENABLED or not _data_service:
        return 'C'
    
    try:
        team_class = _data_service.get_team_class(team_name)
        return team_class.get('tier', 'C') if team_class else 'C'
    except:
        return 'C'


def get_tactical_insight(style_a: str, style_b: str) -> Optional[Dict]:
    """
    Récupère les insights d'un matchup tactique.
    
    Returns:
        Dict avec upset_probability, btts_probability, etc. ou None
    """
    if not REALITY_CHECK_ENABLED or not _data_service:
        return None
    
    try:
        return _data_service.get_tactical_matchup(style_a, style_b)
    except:
        return None


def enrich_prediction(
    home_team: str,
    away_team: str,
    prediction: Dict
) -> Dict:
    """
    Enrichit une prédiction existante avec les données Reality Check.
    
    Args:
        home_team: Équipe domicile
        away_team: Équipe extérieur
        prediction: Dict de prédiction existant
    
    Returns:
        Prédiction enrichie avec clé 'reality_check'
    """
    if not REALITY_CHECK_ENABLED or not _checker:
        prediction['reality_check'] = {'enabled': False}
        return prediction
    
    try:
        reality = _checker.analyze_match(home_team, away_team)
        
        prediction['reality_check'] = {
            'enabled': True,
            'reality_score': reality.reality_score,
            'convergence': reality.convergence,
            'home_tier': reality.home_tier,
            'away_tier': reality.away_tier,
            'tier_gap': reality.tier_gap,
            'warnings': reality.warnings,
            'warnings_count': len(reality.warnings),
            'recommendation': reality.recommendation,
            'adjustments': reality.adjustments
        }
        
    except Exception as e:
        logger.error(f"enrich_prediction error: {e}")
        prediction['reality_check'] = {'enabled': False, 'error': str(e)}
    
    return prediction


# ═══════════════════════════════════════════════════════════════════════════════
# FONCTION RAPIDE POUR SCORE AJUSTÉ
# ═══════════════════════════════════════════════════════════════════════════════

def quick_adjust(home_team: str, away_team: str, score: float, direction: str = 'home') -> float:
    """
    Ajustement rapide d'un score. Retourne directement le score ajusté.
    
    Usage simple:
        adjusted_score = quick_adjust("Man City", "Southampton", 75, "home")
    """
    result = adjust_prediction(home_team, away_team, score, direction=direction)
    return result['adjusted_score']
