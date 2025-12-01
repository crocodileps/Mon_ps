#!/usr/bin/env python3
"""
Coach Impact Calculator V3
Calcule les ajustements xG basés sur les styles tactiques RÉELS des coaches
MISE À JOUR: Nouveaux styles (struggling, attacking_vulnerable, defensive_weak)
"""
import psycopg2
from psycopg2.extras import RealDictCursor
import logging

logger = logging.getLogger('CoachImpact')

DB_CONFIG = {
    'host': 'postgres',
    'port': 5432,
    'database': 'monps_db',
    'user': 'monps_user',
    'password': 'monps_secure_password_2024'
}

# STYLE_MULTIPLIERS V3 - Avec nouveaux styles
STYLE_MULTIPLIERS = {
    'dominant_offensive':   {'att': 1.25, 'def': 0.85},  # Bayern, City, Arsenal
    'offensive':            {'att': 1.15, 'def': 1.00},  # Classique offensif
    'attacking_vulnerable': {'att': 1.20, 'def': 1.30},  # BTTS kings (Spurs, Hoffenheim)
    'balanced':             {'att': 1.00, 'def': 1.00},  # Neutre
    'defensive':            {'att': 0.90, 'def': 0.85},  # Solides derrière
    'defensive_weak':       {'att': 0.75, 'def': 1.00},  # Marque peu mais tient (Getafe)
    'ultra_defensive':      {'att': 0.80, 'def': 0.70},  # Clean sheet kings (Conte)
    'struggling':           {'att': 0.65, 'def': 1.40},  # En difficulté (Valencia, Wolves)
    # Legacy
    'high_risk_offensive':  {'att': 1.20, 'def': 1.35},
    'unknown':              {'att': 1.00, 'def': 1.00},
}

DIRECT_MAPPING = {
    'psg': 'Paris Saint-Germain',
    'om': 'Marseille',
    'ol': 'Lyon',
    'real': 'Real Madrid',
    'barca': 'Barcelona',
    'atletico': 'Atlético de Madrid',
    'inter': 'Internazionale',
    'milan': 'AC Milan',
    'juve': 'Juventus',
    'bayern': 'Bayern',
    'dortmund': 'Dortmund',
    'liverpool': 'Liverpool',
    'chelsea': 'Chelsea',
    'arsenal': 'Arsenal',
    'city': 'Manchester City',
    'united': 'Manchester United',
    'tottenham': 'Tottenham',
    'spurs': 'Tottenham',
}


def normalize_team_name(name: str) -> str:
    """Normalise le nom d'équipe pour la recherche DB"""
    if not name:
        return ""
    
    lower = name.lower().strip()
    
    # Check direct mapping
    if lower in DIRECT_MAPPING:
        return DIRECT_MAPPING[lower]
    
    # Remove common suffixes
    for suffix in [' fc', ' cf', ' sc', ' ac', ' bc', ' afc']:
        if lower.endswith(suffix):
            lower = lower[:-len(suffix)]
    
    return lower.strip().title()


def get_coach_style(team_name: str) -> dict:
    """
    Récupère le style tactique du coach pour une équipe
    
    Returns:
        dict: {'style': str, 'coach': str, 'att': float, 'def': float, 'reliable': bool}
    """
    if not team_name:
        return {'style': 'unknown', 'coach': None, 'att': 1.0, 'def': 1.0, 'reliable': False}
    
    normalized = normalize_team_name(team_name)
    
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        cur.execute("""
            SELECT coach_name, tactical_style, is_reliable,
                   avg_goals_per_match, avg_goals_conceded_per_match
            FROM coach_intelligence
            WHERE current_team ILIKE %s
            LIMIT 1
        """, (f"%{normalized}%",))
        
        row = cur.fetchone()
        cur.close()
        conn.close()
        
        if row:
            style = row['tactical_style'] or 'balanced'
            multipliers = STYLE_MULTIPLIERS.get(style, STYLE_MULTIPLIERS['balanced'])
            
            return {
                'style': style,
                'coach': row['coach_name'],
                'att': multipliers['att'],
                'def': multipliers['def'],
                'reliable': row['is_reliable'] or False,
                'avg_gf': float(row['avg_goals_per_match'] or 1.0),
                'avg_ga': float(row['avg_goals_conceded_per_match'] or 1.0)
            }
        
    except Exception as e:
        logger.error(f"Erreur get_coach_style: {e}")
    
    return {'style': 'unknown', 'coach': None, 'att': 1.0, 'def': 1.0, 'reliable': False}


def calculate_adjusted_xg(home_team: str, away_team: str, 
                          base_home_xg: float = 1.5, base_away_xg: float = 1.2) -> dict:
    """
    Calcule les xG ajustés selon les styles des coaches
    
    Args:
        home_team: Équipe domicile
        away_team: Équipe extérieur
        base_home_xg: xG de base domicile (défaut 1.5)
        base_away_xg: xG de base extérieur (défaut 1.2)
    
    Returns:
        dict avec home_xg, away_xg, total_xg et détails coaches
    """
    home_coach = get_coach_style(home_team)
    away_coach = get_coach_style(away_team)
    
    # Home advantage factor
    home_advantage = 1.08
    
    # Calculate adjusted xG
    # home_xg = base * home_advantage * home_attack * away_defense_vulnerability
    # away_xg = base * (1/home_advantage) * away_attack * home_defense_vulnerability
    
    home_xg = round(base_home_xg * home_advantage * home_coach['att'] * away_coach['def'], 2)
    away_xg = round(base_away_xg * (1/home_advantage) * away_coach['att'] * home_coach['def'], 2)
    
    # Clamp to reasonable values
    home_xg = max(0.3, min(5.0, home_xg))
    away_xg = max(0.2, min(4.5, away_xg))
    
    return {
        'home_xg': home_xg,
        'away_xg': away_xg,
        'total_xg': round(home_xg + away_xg, 2),
        'home_coach': home_coach,
        'away_coach': away_coach
    }


# Test
if __name__ == "__main__":
    tests = [
        ("Bayern", "Dortmund"),
        ("Valencia", "Rayo Vallecano"),
        ("Tottenham", "Liverpool"),
        ("Arsenal", "Chelsea"),
    ]
    
    print("🧠 COACH IMPACT V3 TEST")
    print("=" * 60)
    
    for home, away in tests:
        result = calculate_adjusted_xg(home, away)
        hc = result['home_coach']
        ac = result['away_coach']
        
        print(f"\n⚽ {home} vs {away}")
        print(f"   🏠 {hc.get('coach', 'Unknown')} ({hc['style']}) ATT:{hc['att']} DEF:{hc['def']}")
        print(f"   ✈️  {ac.get('coach', 'Unknown')} ({ac['style']}) ATT:{ac['att']} DEF:{ac['def']}")
        print(f"   📊 xG: {result['home_xg']} - {result['away_xg']} (Total: {result['total_xg']})")


# Alias pour compatibilité
class CoachImpactCalculator:
    """Wrapper de compatibilité pour les anciens imports"""
    
    def __init__(self, conn=None):
        self.conn = conn
    
    def get_coach_factors(self, team_name: str) -> dict:
        return get_coach_style(team_name)
    
    def calculate_adjusted_xg(self, home_team: str, away_team: str, 
                              base_home_xg: float = 1.5, base_away_xg: float = 1.2) -> dict:
        return calculate_adjusted_xg(home_team, away_team, base_home_xg, base_away_xg)
