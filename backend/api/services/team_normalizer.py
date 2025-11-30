"""
�� TEAM NAME NORMALIZER SERVICE
═══════════════════════════════════════════════════════════════════════════════

Service pour normaliser les noms d'équipes et éviter les jointures ILIKE fragiles.
Utilise les tables team_mapping, team_aliases, team_name_mapping.

VERSION: 1.0.0
"""

import psycopg2
from psycopg2.extras import RealDictCursor
from typing import Optional, Dict, List
from functools import lru_cache
import structlog

logger = structlog.get_logger(__name__)

DB_CONFIG = {
    "host": "monps_postgres",
    "port": 5432,
    "dbname": "monps_db",
    "user": "monps_user",
    "password": "monps_secure_password_2024"
}


class TeamNormalizer:
    """Service de normalisation des noms d'équipes"""
    
    def __init__(self):
        self._cache: Dict[str, str] = {}
        self._reverse_cache: Dict[str, List[str]] = {}
        self._load_mappings()
    
    def _get_connection(self):
        return psycopg2.connect(**DB_CONFIG)
    
    def _load_mappings(self):
        """Charge tous les mappings en mémoire"""
        try:
            with self._get_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                    # 1. Charger team_mapping + aliases
                    cursor.execute("""
                        SELECT 
                            tm.team_name as canonical,
                            tm.team_name_normalized,
                            ta.alias
                        FROM team_mapping tm
                        LEFT JOIN team_aliases ta ON tm.id = ta.team_mapping_id
                    """)
                    for row in cursor.fetchall():
                        canonical = row['canonical']
                        normalized = row['team_name_normalized']
                        alias = row['alias']
                        
                        # Mapper le nom normalisé vers canonical
                        if normalized:
                            self._cache[normalized.lower()] = canonical
                        
                        # Mapper l'alias vers canonical
                        if alias:
                            self._cache[alias.lower()] = canonical
                        
                        # Reverse cache
                        if canonical not in self._reverse_cache:
                            self._reverse_cache[canonical] = []
                        if alias:
                            self._reverse_cache[canonical].append(alias)
                    
                    # 2. Charger team_name_mapping
                    cursor.execute("""
                        SELECT source_name, canonical_name, normalized_name
                        FROM team_name_mapping
                    """)
                    for row in cursor.fetchall():
                        source = row['source_name']
                        canonical = row['canonical_name']
                        normalized = row['normalized_name']
                        
                        if source:
                            self._cache[source.lower()] = canonical
                        if normalized:
                            self._cache[normalized.lower()] = canonical
                    
            logger.info(f"TeamNormalizer chargé: {len(self._cache)} mappings")
            
        except Exception as e:
            logger.error(f"Erreur chargement mappings: {e}")
    
    def normalize(self, team_name: str) -> str:
        """
        Normalise un nom d'équipe vers son nom canonique.
        
        Args:
            team_name: Nom d'équipe (peut être un alias, abréviation, etc.)
            
        Returns:
            Nom canonique ou le nom original si pas trouvé
        """
        if not team_name:
            return team_name
            
        # Essayer le cache direct
        key = team_name.lower().strip()
        if key in self._cache:
            return self._cache[key]
        
        # Essayer sans accents et caractères spéciaux
        import unicodedata
        normalized = unicodedata.normalize('NFKD', key).encode('ASCII', 'ignore').decode('ASCII')
        if normalized in self._cache:
            return self._cache[normalized]
        
        # Essayer des variations communes
        variations = [
            key.replace('fc ', '').replace(' fc', ''),
            key.replace('sc ', '').replace(' sc', ''),
            key.replace('cf ', '').replace(' cf', ''),
            key.replace('afc ', '').replace(' afc', ''),
        ]
        
        for var in variations:
            if var in self._cache:
                return self._cache[var]
        
        # Pas trouvé, retourner l'original
        return team_name
    
    def get_all_aliases(self, canonical_name: str) -> List[str]:
        """Retourne tous les alias d'une équipe"""
        return self._reverse_cache.get(canonical_name, [])
    
    def get_sql_pattern(self, team_name: str) -> str:
        """
        Génère un pattern SQL pour matcher une équipe.
        Utile pour les requêtes avec ILIKE.
        """
        canonical = self.normalize(team_name)
        aliases = self.get_all_aliases(canonical)
        
        # Créer un pattern avec toutes les variantes
        all_names = [canonical] + aliases
        return '|'.join(all_names)
    
    def reload(self):
        """Recharge les mappings depuis la DB"""
        self._cache.clear()
        self._reverse_cache.clear()
        self._load_mappings()


# Instance singleton
team_normalizer = TeamNormalizer()
