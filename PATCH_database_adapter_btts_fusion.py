"""
╔═══════════════════════════════════════════════════════════════════════════════════════╗
║  PATCH POUR database_adapter.py - FUSION BTTS 3 SOURCES                               ║
╠═══════════════════════════════════════════════════════════════════════════════════════╣
║                                                                                       ║
║  AJOUTE la méthode calculate_btts_probability() qui fusionne:                         ║
║  1. tactical_matrix.btts_probability (40%)                                            ║
║  2. team_xg_tendencies.btts_xg_rate (35%)                                             ║
║  3. match_xg_stats H2H (25%)                                                          ║
║                                                                                       ║
║  INSTRUCTIONS:                                                                        ║
║  1. Ouvrir database_adapter.py                                                        ║
║  2. Ajouter les 4 méthodes ci-dessous à la classe DatabaseAdapter                     ║
║  3. Utiliser calculate_btts_probability() dans main.py                                ║
║                                                                                       ║
╚═══════════════════════════════════════════════════════════════════════════════════════╝
"""

from typing import Dict, Optional
import logging

logger = logging.getLogger('DatabaseAdapter')

# ═══════════════════════════════════════════════════════════════════════════════════════
# POIDS DES SOURCES (Total = 1.0)
# Validé: tactical(40%) + team_xg(35%) + h2h(25%) = 100%
# ═══════════════════════════════════════════════════════════════════════════════════════

BTTS_SOURCE_WEIGHTS = {
    'tactical_matrix': 0.40,
    'team_xg_tendencies': 0.35,
    'match_xg_stats': 0.25,
}


# ═══════════════════════════════════════════════════════════════════════════════════════
# MÉTHODE 1: get_tactical_btts
# ═══════════════════════════════════════════════════════════════════════════════════════

async def get_tactical_btts(self, home_style: str, away_style: str) -> Optional[Dict]:
    """
    Récupère les probabilités BTTS depuis tactical_matrix
    
    Args:
        home_style: Style de l'équipe à domicile (attacking, defensive, balanced, etc.)
        away_style: Style de l'équipe à l'extérieur
        
    Returns:
        Dict avec btts_probability et over25_probability (0-1)
    """
    query = """
    SELECT 
        btts_probability,
        over25_probability,
        avg_total_goals,
        clean_sheet_probability
    FROM tactical_matrix
    WHERE LOWER(style_home) = LOWER($1) 
      AND LOWER(style_away) = LOWER($2)
    LIMIT 1
    """
    
    try:
        row = await self.pool.fetchrow(query, home_style, away_style)
        
        if row:
            return {
                'btts_probability': float(row.get('btts_probability', 50) or 50) / 100,
                'over25_probability': float(row.get('over25_probability', 50) or 50) / 100,
                'avg_total_goals': float(row.get('avg_total_goals', 2.5) or 2.5),
                'source': 'tactical_matrix'
            }
        return None
        
    except Exception as e:
        logger.error(f"❌ Erreur get_tactical_btts: {e}")
        return None


# ═══════════════════════════════════════════════════════════════════════════════════════
# MÉTHODE 2: get_team_xg_btts
# ═══════════════════════════════════════════════════════════════════════════════════════

async def get_team_xg_btts(self, team_name: str) -> Optional[Dict]:
    """
    Récupère les tendances BTTS depuis team_xg_tendencies (Understat)
    
    Args:
        team_name: Nom de l'équipe
        
    Returns:
        Dict avec btts_xg_rate (0-1)
    """
    query = """
    SELECT 
        btts_xg_rate,
        over25_xg_rate,
        xg_for_avg,
        xg_against_avg
    FROM team_xg_tendencies
    WHERE LOWER(team_name) = LOWER($1)
    LIMIT 1
    """
    
    try:
        row = await self.pool.fetchrow(query, team_name)
        
        if row:
            return {
                'btts_xg_rate': float(row.get('btts_xg_rate', 0.5) or 0.5),
                'over25_xg_rate': float(row.get('over25_xg_rate', 0.5) or 0.5),
                'xg_for_avg': float(row.get('xg_for_avg', 1.5) or 1.5),
                'xg_against_avg': float(row.get('xg_against_avg', 1.5) or 1.5),
                'source': 'team_xg_tendencies'
            }
        return None
        
    except Exception as e:
        logger.error(f"❌ Erreur get_team_xg_btts({team_name}): {e}")
        return None


# ═══════════════════════════════════════════════════════════════════════════════════════
# MÉTHODE 3: get_h2h_btts
# ═══════════════════════════════════════════════════════════════════════════════════════

async def get_h2h_btts(self, home_team: str, away_team: str) -> Optional[Dict]:
    """
    Récupère les stats BTTS historiques H2H depuis match_xg_stats
    
    Args:
        home_team: Équipe à domicile
        away_team: Équipe à l'extérieur
        
    Returns:
        Dict avec btts_avg historique (0-1)
    """
    query = """
    SELECT 
        AVG(btts_expected) as btts_avg,
        AVG(total_xg) as total_xg_avg,
        COUNT(*) as matches
    FROM match_xg_stats
    WHERE (LOWER(home_team) = LOWER($1) AND LOWER(away_team) = LOWER($2))
       OR (LOWER(home_team) = LOWER($3) AND LOWER(away_team) = LOWER($4))
    """
    
    try:
        row = await self.pool.fetchrow(query, home_team, away_team, away_team, home_team)
        
        if row and row['matches'] and int(row['matches']) > 0:
            return {
                'btts_avg': float(row.get('btts_avg', 0.5) or 0.5),
                'total_xg_avg': float(row.get('total_xg_avg', 2.5) or 2.5),
                'matches': int(row['matches']),
                'source': 'match_xg_stats'
            }
        return None
        
    except Exception as e:
        logger.error(f"❌ Erreur get_h2h_btts: {e}")
        return None


# ═══════════════════════════════════════════════════════════════════════════════════════
# MÉTHODE 4: calculate_btts_probability (MÉTHODE PRINCIPALE)
# ═══════════════════════════════════════════════════════════════════════════════════════

async def calculate_btts_probability(
    self, 
    home_team: str, 
    away_team: str, 
    home_style: str = None, 
    away_style: str = None
) -> Dict:
    """
    🎯 MÉTHODE CLÉ: Fusionne toutes les sources de probabilité BTTS
    
    Combine:
    1. tactical_matrix.btts_probability (40%) - style matchup
    2. team_xg_tendencies.btts_xg_rate (35%) - tendance Understat
    3. match_xg_stats H2H (25%) - historique confrontations
    
    Args:
        home_team: Équipe à domicile
        away_team: Équipe à l'extérieur
        home_style: Style tactique home (optionnel, pour tactical_matrix)
        away_style: Style tactique away (optionnel)
        
    Returns:
        Dict avec:
        - btts_probability: float (0-1)
        - over25_probability: float (0-1)
        - confidence: str (HIGH/MEDIUM/LOW)
        - sources_used: List[str]
    """
    weights = BTTS_SOURCE_WEIGHTS
    btts_probs = []
    over25_probs = []
    sources_used = []
    total_weight = 0
    
    # ═══════════════════════════════════════════════════════════════════════════════
    # Source 1: Tactical Matrix (40%) - si styles fournis
    # ═══════════════════════════════════════════════════════════════════════════════
    if home_style and away_style:
        tactical = await self.get_tactical_btts(home_style, away_style)
        if tactical:
            btts_probs.append((tactical['btts_probability'], weights['tactical_matrix']))
            over25_probs.append((tactical['over25_probability'], weights['tactical_matrix']))
            sources_used.append('tactical_matrix')
            total_weight += weights['tactical_matrix']
            logger.debug(f"   📊 Tactical BTTS: {tactical['btts_probability']*100:.0f}%")
    
    # ═══════════════════════════════════════════════════════════════════════════════
    # Source 2: Team xG Tendencies (35%) - moyenne des deux équipes
    # ═══════════════════════════════════════════════════════════════════════════════
    home_xg = await self.get_team_xg_btts(home_team)
    away_xg = await self.get_team_xg_btts(away_team)
    
    if home_xg and away_xg:
        combined_btts = (home_xg['btts_xg_rate'] + away_xg['btts_xg_rate']) / 2
        combined_over25 = (home_xg['over25_xg_rate'] + away_xg['over25_xg_rate']) / 2
        btts_probs.append((combined_btts, weights['team_xg_tendencies']))
        over25_probs.append((combined_over25, weights['team_xg_tendencies']))
        sources_used.append('team_xg_tendencies')
        total_weight += weights['team_xg_tendencies']
        logger.debug(f"   📊 Team xG BTTS: {combined_btts*100:.0f}%")
    elif home_xg or away_xg:
        # Une seule équipe trouvée - poids réduit de moitié
        xg_data = home_xg or away_xg
        btts_probs.append((xg_data['btts_xg_rate'], weights['team_xg_tendencies'] * 0.5))
        over25_probs.append((xg_data['over25_xg_rate'], weights['team_xg_tendencies'] * 0.5))
        sources_used.append('team_xg_tendencies_partial')
        total_weight += weights['team_xg_tendencies'] * 0.5
    
    # ═══════════════════════════════════════════════════════════════════════════════
    # Source 3: H2H Historical (25%) - si au moins 2 matchs
    # ═══════════════════════════════════════════════════════════════════════════════
    h2h = await self.get_h2h_btts(home_team, away_team)
    if h2h and h2h['matches'] >= 2:
        btts_probs.append((h2h['btts_avg'], weights['match_xg_stats']))
        # Approximation over25 depuis total_xg
        over25_from_xg = min(0.9, h2h['total_xg_avg'] / 4.0)  # 4 xG ≈ 90% over25
        over25_probs.append((over25_from_xg, weights['match_xg_stats']))
        sources_used.append('match_xg_stats')
        total_weight += weights['match_xg_stats']
        logger.debug(f"   📊 H2H BTTS: {h2h['btts_avg']*100:.0f}% ({h2h['matches']} matchs)")
    
    # ═══════════════════════════════════════════════════════════════════════════════
    # Fusion pondérée
    # ═══════════════════════════════════════════════════════════════════════════════
    if btts_probs and total_weight > 0:
        btts_final = sum(p * w for p, w in btts_probs) / total_weight
        over25_final = sum(p * w for p, w in over25_probs) / total_weight
    else:
        # Fallback: moyenne historique générique
        btts_final = 0.50
        over25_final = 0.55
        sources_used.append('fallback')
    
    # ═══════════════════════════════════════════════════════════════════════════════
    # Niveau de confiance
    # ═══════════════════════════════════════════════════════════════════════════════
    if len(sources_used) >= 3:
        confidence = 'HIGH'
    elif len(sources_used) >= 2:
        confidence = 'MEDIUM'
    else:
        confidence = 'LOW'
    
    result = {
        'btts_probability': round(btts_final, 3),
        'over25_probability': round(over25_final, 3),
        'confidence': confidence,
        'sources_used': sources_used,
        'total_weight': round(total_weight, 2)
    }
    
    logger.info(f"   🎯 BTTS Fusion: {btts_final*100:.0f}% | Over25: {over25_final*100:.0f}% | Confidence: {confidence}")
    
    return result


# ═══════════════════════════════════════════════════════════════════════════════════════
# COMMENT UTILISER DANS main.py
# ═══════════════════════════════════════════════════════════════════════════════════════

"""
Dans main.py, après avoir chargé les DNA des équipes:

# Charger DNA
home_dna = await self.db.get_team_dna(match.home_team)
away_dna = await self.db.get_team_dna(match.away_team)

# 🆕 AJOUTER: Calculer BTTS fusionné
btts_analysis = await self.db.calculate_btts_probability(
    home_team=match.home_team,
    away_team=match.away_team,
    home_style=home_dna.style if home_dna else 'balanced',
    away_style=away_dna.style if away_dna else 'balanced'
)

# Utiliser les résultats
logger.info(f"   🎯 BTTS Analysis (3 sources):")
logger.info(f"      BTTS Prob: {btts_analysis['btts_probability']*100:.0f}%")
logger.info(f"      Over 2.5 Prob: {btts_analysis['over25_probability']*100:.0f}%")
logger.info(f"      Confidence: {btts_analysis['confidence']}")
logger.info(f"      Sources: {', '.join(btts_analysis['sources_used'])}")
"""


# ═══════════════════════════════════════════════════════════════════════════════════════
# TEST
# ═══════════════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("╔════════════════════════════════════════════════════════════════╗")
    print("║  PATCH: BTTS FUSION 3 SOURCES                                  ║")
    print("╠════════════════════════════════════════════════════════════════╣")
    print("║                                                                ║")
    print("║  Source 1: tactical_matrix       (40%)                        ║")
    print("║  Source 2: team_xg_tendencies    (35%)                        ║")
    print("║  Source 3: match_xg_stats H2H    (25%)                        ║")
    print("║                                                                ║")
    print("║  final_btts = (src1×0.40) + (src2×0.35) + (src3×0.25)         ║")
    print("║                                                                ║")
    print("╚════════════════════════════════════════════════════════════════╝")
    print("\n✅ Ajouter ces 4 méthodes à DatabaseAdapter:")
    print("   1. get_tactical_btts()")
    print("   2. get_team_xg_btts()")
    print("   3. get_h2h_btts()")
    print("   4. calculate_btts_probability()")
