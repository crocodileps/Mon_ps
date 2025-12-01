#!/usr/bin/env python3
"""
Coach Impact Calculator V1.1
Calcule les ajustements xG basés sur les styles tactiques RÉELS des coaches
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
    'man city': 'Manchester City',
    'man united': 'Manchester United',
}


def clean_team_name(name: str) -> str:
    """Nettoie les prefixes et suffixes courants"""
    prefixes = ["SSC ", "AC ", "FC ", "AS ", "US ", "RC "]
    for prefix in prefixes:
        if name.startswith(prefix):
            name = name[len(prefix):].strip()
            break
    """Nettoie les suffixes courants des noms d'équipes"""
    suffixes = [" FC", " AFC", " CF", " SC", " SSC", " AC", " BC"]
    for suffix in suffixes:
        if name.endswith(suffix):
            return name[:-len(suffix)].strip()
    return name


class CoachImpactCalculator:
    LEAGUE_AVG_GF = 1.31
    LEAGUE_AVG_GA = 1.43
    
    def __init__(self, conn=None):
        self.conn = conn
        self.cache = {}
        self._load_averages()
    
    def _get_conn(self):
        if self.conn:
            return self.conn
        return psycopg2.connect(**DB_CONFIG)
    
    def _load_averages(self):
        try:
            conn = self._get_conn()
            cur = conn.cursor()
            cur.execute("""
                SELECT AVG(avg_goals_per_match), AVG(avg_goals_conceded_per_match)
                FROM coach_intelligence WHERE career_matches >= 5
            """)
            row = cur.fetchone()
            if row and row[0]:
                self.LEAGUE_AVG_GF = float(row[0])
                self.LEAGUE_AVG_GA = float(row[1])
            cur.close()
            if not self.conn:
                conn.close()
        except Exception as e:
            logger.warning(f"Could not load averages: {e}")
    
    def get_coach_factors(self, team_name: str) -> dict:
        if team_name in self.cache:
            return self.cache[team_name]
        
        factors = {'att': 1.0, 'def': 1.0, 'style': 'unknown', 'coach': None, 'reliable': False}
        
        try:
            conn = self._get_conn()
            cur = conn.cursor(cursor_factory=RealDictCursor)
            
            # Résoudre alias puis nettoyer suffixes
            search_term = DIRECT_MAPPING.get(team_name.lower().strip(), team_name)
            search_term = clean_team_name(search_term)
            
            cur.execute("""
                SELECT coach_name, current_team, tactical_style,
                       avg_goals_per_match, avg_goals_conceded_per_match,
                       career_matches, is_reliable
                FROM coach_intelligence
                WHERE unaccent(current_team) ILIKE unaccent(%s)
                LIMIT 1
            """, (f'%{search_term}%',))
            
            row = cur.fetchone()
            if row:
                gf = float(row['avg_goals_per_match'] or self.LEAGUE_AVG_GF)
                ga = float(row['avg_goals_conceded_per_match'] or self.LEAGUE_AVG_GA)
                
                factors['att'] = max(0.6, min(2.0, gf / self.LEAGUE_AVG_GF))
                factors['def'] = max(0.4, min(1.8, ga / self.LEAGUE_AVG_GA))
                factors['style'] = row['tactical_style']
                factors['coach'] = row['coach_name']
                factors['reliable'] = row['is_reliable']
            
            cur.close()
            if not self.conn:
                conn.close()
                
        except Exception as e:
            logger.warning(f"Coach fetch error for {team_name}: {e}")
        
        self.cache[team_name] = factors
        return factors
    
    def calculate_adjusted_xg(self, home_team: str, away_team: str,
                               base_home_xg: float, base_away_xg: float,
                               home_advantage: float = 1.08) -> dict:
        home_coach = self.get_coach_factors(home_team)
        away_coach = self.get_coach_factors(away_team)
        
        home_xg = base_home_xg * home_advantage * home_coach['att'] * away_coach['def']
        away_xg = base_away_xg * (1/home_advantage) * away_coach['att'] * home_coach['def']
        
        max_home = 4.0 if 'offensive' in (home_coach['style'] or '') else 3.2
        max_away = 3.5 if 'offensive' in (away_coach['style'] or '') else 2.8
        
        home_xg = max(0.3, min(max_home, home_xg))
        away_xg = max(0.2, min(max_away, away_xg))
        
        return {
            'home_xg': round(home_xg, 2),
            'away_xg': round(away_xg, 2),
            'total_xg': round(home_xg + away_xg, 2),
            'home_coach': home_coach,
            'away_coach': away_coach,
        }


if __name__ == "__main__":
    calc = CoachImpactCalculator()
    print(f"📊 Averages: GF={calc.LEAGUE_AVG_GF:.2f} GA={calc.LEAGUE_AVG_GA:.2f}")
    
    tests = [
        ("Arsenal FC", "Chelsea FC", 1.5, 1.3),
        ("FC Bayern München", "Borussia Dortmund", 2.0, 1.4),
        ("SSC Napoli", "FC Internazionale Milano", 1.2, 1.5),
    ]
    
    for h, a, bh, ba in tests:
        r = calc.calculate_adjusted_xg(h, a, bh, ba)
        hc, ac = r['home_coach'], r['away_coach']
        print(f"\n⚽ {h} vs {a}")
        print(f"   🏠 {hc['coach'] or '?'} ({hc['style']}) ATT:{hc['att']:.2f}")
        print(f"   ✈️ {ac['coach'] or '?'} ({ac['style']}) ATT:{ac['att']:.2f}")
        print(f"   📈 {bh:.1f}->{r['home_xg']:.2f} | {ba:.1f}->{r['away_xg']:.2f}")
