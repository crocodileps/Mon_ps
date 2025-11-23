"""
Team Resolver Service
Résout automatiquement les noms d'équipes vers API-Football IDs
"""

import logging
from typing import Dict, List, Optional, Tuple
import psycopg2
from psycopg2.extras import RealDictCursor
import re

logger = logging.getLogger(__name__)


class TeamResolver:
    """Service de résolution noms équipes → API IDs"""
    
    def __init__(self, db_config: Dict):
        self.db_config = db_config
        self.cache = {}  # Cache en mémoire
    
    
    def normalize_name(self, name: str) -> str:
        """Normalise un nom d'équipe"""
        # Lowercase, remove special chars, trim
        normalized = re.sub(r'[^a-z0-9\s]', '', name.lower().strip())
        return ' '.join(normalized.split())  # Remove extra spaces
    
    
    def resolve_team(
        self, 
        team_name: str, 
        sport: str = 'soccer',
        league_hint: Optional[str] = None
    ) -> Optional[Tuple[int, int, str]]:
        """
        Résout un nom d'équipe
        
        Returns:
            (api_football_id, league_id, official_name) ou None
        """
        # Check cache
        cache_key = f"{team_name}:{league_hint}"
        if cache_key in self.cache:
            return self.cache[cache_key]
        
        try:
            conn = psycopg2.connect(**self.db_config)
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            
            normalized = self.normalize_name(team_name)
            
            # Try exact match first
            query = """
                SELECT 
                    tm.api_football_id,
                    tm.league_id,
                    tm.team_name,
                    1.0 as confidence
                FROM team_mapping tm
                WHERE tm.team_name_normalized = %s
                LIMIT 1
            """
            
            cursor.execute(query, (normalized,))
            result = cursor.fetchone()
            
            if not result:
                # Try aliases
                query = """
                    SELECT 
                        tm.api_football_id,
                        tm.league_id,
                        tm.team_name,
                        0.9 as confidence
                    FROM team_aliases ta
                    JOIN team_mapping tm ON ta.team_mapping_id = tm.id
                    WHERE ta.alias_normalized = %s
                    LIMIT 1
                """
                
                cursor.execute(query, (normalized,))
                result = cursor.fetchone()
            
            if not result:
                # Fuzzy search
                query = """
                    SELECT 
                        tm.api_football_id,
                        tm.league_id,
                        tm.team_name,
                        CASE 
                            WHEN tm.team_name_normalized LIKE %s THEN 0.8
                            WHEN %s LIKE '%%' || tm.team_name_normalized || '%%' THEN 0.7
                            ELSE 0.5
                        END as confidence
                    FROM team_mapping tm
                    WHERE tm.team_name_normalized LIKE '%%' || %s || '%%'
                       OR %s LIKE '%%' || tm.team_name_normalized || '%%'
                    ORDER BY confidence DESC
                    LIMIT 1
                """
                
                cursor.execute(query, (f'%{normalized}%', normalized, normalized, normalized))
                result = cursor.fetchone()
            
            cursor.close()
            conn.close()
            
            if result and result['confidence'] >= 0.7:
                resolved = (
                    result['api_football_id'],
                    result['league_id'],
                    result['team_name']
                )
                
                # Cache
                self.cache[cache_key] = resolved
                
                logger.info(f"✅ Résolu: '{team_name}' → {result['team_name']} (ID: {result['api_football_id']}, conf: {result['confidence']:.0%})")
                
                return resolved
            else:
                logger.warning(f"⚠️  Équipe non trouvée: '{team_name}'")
                return None
                
        except Exception as e:
            logger.error(f"❌ Erreur résolution: {e}")
            return None
    
    
    def add_team(
        self,
        team_name: str,
        api_football_id: int,
        league_id: int,
        league_name: str = None,
        country: str = None
    ) -> bool:
        """Ajoute une nouvelle équipe au mapping"""
        try:
            conn = psycopg2.connect(**self.db_config)
            cursor = conn.cursor()
            
            normalized = self.normalize_name(team_name)
            
            query = """
                INSERT INTO team_mapping (
                    team_name, team_name_normalized, 
                    api_football_id, league_id, league_name, country
                ) VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (team_name_normalized, league_id) DO NOTHING
                RETURNING id
            """
            
            cursor.execute(query, (
                team_name, normalized,
                api_football_id, league_id, league_name, country
            ))
            
            result = cursor.fetchone()
            
            conn.commit()
            cursor.close()
            conn.close()
            
            if result:
                logger.info(f"✅ Équipe ajoutée: {team_name} → {api_football_id}")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"❌ Erreur ajout: {e}")
            return False
    
    
    def auto_detect_teams(self, limit: int = 50) -> Dict:
        """
        Auto-détecte équipes depuis current_opportunities
        et propose des mappings
        """
        try:
            conn = psycopg2.connect(**self.db_config)
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            
            # Récupérer équipes uniques non mappées
            query = """
                WITH unique_teams AS (
                    SELECT DISTINCT home_team as team_name, sport_key
                    FROM current_opportunities
                    UNION
                    SELECT DISTINCT away_team as team_name, sport_key
                    FROM current_opportunities
                )
                SELECT 
                    ut.team_name,
                    ut.sport_key,
                    COUNT(*) OVER() as total_unmapped
                FROM unique_teams ut
                WHERE NOT EXISTS (
                    SELECT 1 FROM team_mapping tm
                    WHERE tm.team_name_normalized = normalize_team_name(ut.team_name)
                )
                AND NOT EXISTS (
                    SELECT 1 FROM team_aliases ta
                    WHERE ta.alias_normalized = normalize_team_name(ut.team_name)
                )
                LIMIT %s
            """
            
            cursor.execute(query, (limit,))
            unmapped = cursor.fetchall()
            
            cursor.close()
            conn.close()
            
            return {
                'unmapped_teams': [dict(row) for row in unmapped],
                'count': len(unmapped)
            }
            
        except Exception as e:
            logger.error(f"❌ Erreur auto-detect: {e}")
            return {'unmapped_teams': [], 'count': 0}


# Singleton
_team_resolver = None

def get_team_resolver(db_config: Dict) -> TeamResolver:
    global _team_resolver
    if _team_resolver is None:
        _team_resolver = TeamResolver(db_config)
    return _team_resolver
