"""
╔═══════════════════════════════════════════════════════════════════════════════════════╗
║  TEAM RESOLVER - Résolution centralisée des noms d'équipes                            ║
║  Source unique de vérité pour tous les mappings                                       ║
╚═══════════════════════════════════════════════════════════════════════════════════════╝

USAGE:
    from quantum.utils.team_resolver import TeamResolver

    resolver = TeamResolver()

    # Mon_PS canonical -> Source-specific name
    be_name = resolver.to_source("Manchester United", source="betexplorer")
    # Returns: "Manchester Utd"

    # Source-specific name -> Mon_PS canonical
    canonical = resolver.to_canonical("Manchester Utd", source="betexplorer")
    # Returns: "Manchester United"

    # Similarity check
    sim = resolver.similarity("Man United", "Manchester Utd")
    # Returns: 0.95+ (after normalization)

Version: 1.0
Date: 19 Décembre 2025
"""

import os
import psycopg2
from psycopg2.extras import RealDictCursor
from typing import Optional, Dict, List, Tuple
from difflib import SequenceMatcher
from functools import lru_cache
import logging
import re

logger = logging.getLogger(__name__)

# Database connection
# NOTE: All team name mappings are now stored in the database (team_aliases table)
# This eliminates hardcoded mappings and centralizes team resolution
DB_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "port": os.getenv("DB_PORT", "5432"),
    "database": os.getenv("DB_NAME", "monps_db"),
    "user": os.getenv("DB_USER", "monps_user"),
    "password": os.getenv("DB_PASSWORD", "monps_secure_password_2024"),
}


class TeamResolver:
    """
    Résolution centralisée des noms d'équipes.

    Utilise les tables:
    - team_mapping: noms canoniques Mon_PS
    - team_aliases: aliases par source (betexplorer, transfermarkt, etc.)
    """

    def __init__(self, db_config: Optional[Dict] = None):
        self.db_config = db_config or DB_CONFIG
        self._cache_canonical_to_source: Dict[str, Dict[str, str]] = {}
        self._cache_source_to_canonical: Dict[str, Dict[str, str]] = {}
        self._canonical_names: List[str] = []
        self._loaded = False

    def _get_connection(self):
        """Get database connection."""
        return psycopg2.connect(**self.db_config)

    def _load_mappings(self):
        """Load all mappings from database."""
        if self._loaded:
            return

        try:
            with self._get_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    # Load canonical names
                    cur.execute("""
                        SELECT id, team_name, team_name_normalized, league_name
                        FROM team_mapping
                    """)
                    for row in cur.fetchall():
                        canonical = row['team_name']
                        self._canonical_names.append(canonical)

                        # Self-mapping (canonical -> canonical for any source)
                        normalized = row['team_name_normalized']
                        if canonical not in self._cache_source_to_canonical:
                            self._cache_source_to_canonical[canonical.lower()] = {}
                        self._cache_source_to_canonical[canonical.lower()]['_canonical'] = canonical
                        self._cache_source_to_canonical[normalized] = {'_canonical': canonical}

                    # Load aliases
                    cur.execute("""
                        SELECT ta.alias, ta.alias_normalized, ta.source, tm.team_name as canonical
                        FROM team_aliases ta
                        JOIN team_mapping tm ON ta.team_mapping_id = tm.id
                    """)
                    for row in cur.fetchall():
                        alias = row['alias']
                        alias_norm = row['alias_normalized']
                        source = row['source']
                        canonical = row['canonical']

                        # source -> canonical mapping
                        if alias_norm not in self._cache_source_to_canonical:
                            self._cache_source_to_canonical[alias_norm] = {}
                        self._cache_source_to_canonical[alias_norm][source] = canonical
                        self._cache_source_to_canonical[alias.lower()][source] = canonical

                        # canonical -> source mapping
                        canonical_key = canonical.lower()
                        if canonical_key not in self._cache_canonical_to_source:
                            self._cache_canonical_to_source[canonical_key] = {}
                        self._cache_canonical_to_source[canonical_key][source] = alias

            self._loaded = True
            logger.info(f"TeamResolver: Loaded {len(self._canonical_names)} teams, "
                       f"{len(self._cache_source_to_canonical)} aliases")

        except Exception as e:
            logger.error(f"Failed to load team mappings: {e}")
            raise

    def to_canonical(self, name: str, source: str = "betexplorer") -> str:
        """
        Convert source-specific name to Mon_PS canonical name.

        Args:
            name: Team name from source (e.g., "Manchester Utd")
            source: Source identifier (e.g., "betexplorer")

        Returns:
            Canonical Mon_PS name (e.g., "Manchester United")
        """
        self._load_mappings()

        name_lower = name.lower().strip()

        # Check alias cache
        if name_lower in self._cache_source_to_canonical:
            aliases = self._cache_source_to_canonical[name_lower]
            if source in aliases:
                return aliases[source]
            if '_canonical' in aliases:
                return aliases['_canonical']

        # Fuzzy match on canonical names
        best_match = self._fuzzy_match(name, self._canonical_names)
        if best_match:
            return best_match

        # Return original if no match
        return name

    def to_source(self, canonical_name: str, source: str = "betexplorer") -> str:
        """
        Convert Mon_PS canonical name to source-specific name.

        Args:
            canonical_name: Mon_PS canonical name (e.g., "Manchester United")
            source: Target source (e.g., "betexplorer")

        Returns:
            Source-specific name (e.g., "Manchester Utd")
        """
        # Load mappings from database
        self._load_mappings()

        canonical_lower = canonical_name.lower().strip()
        canonical_normalized = canonical_lower.replace('-', ' ').replace('  ', ' ')

        # 1. Direct match in cache
        for variant in [canonical_lower, canonical_normalized]:
            if variant in self._cache_canonical_to_source:
                sources = self._cache_canonical_to_source[variant]
                if source in sources:
                    return sources[source]

        # 2. Fuzzy match on canonical names
        best_match = self._fuzzy_match(canonical_name, self._canonical_names, threshold=0.85)
        if best_match:
            best_lower = best_match.lower()
            if best_lower in self._cache_canonical_to_source:
                sources = self._cache_canonical_to_source[best_lower]
                if source in sources:
                    return sources[source]

        # No mapping = return original
        return canonical_name

    @staticmethod
    def normalize(name: str) -> str:
        """
        Normalize team name for comparison.

        - Lowercase
        - Remove common suffixes (FC, SC, etc.)
        - Expand abbreviations
        - Remove special characters
        """
        name = name.lower().strip()

        # Expand abbreviations
        expansions = {
            'man city': 'manchester city',
            'man utd': 'manchester united',
            'man united': 'manchester united',
            'spurs': 'tottenham',
            'wolves': 'wolverhampton',
        }
        for abbr, full in expansions.items():
            if name == abbr:
                name = full
                break

        # Remove suffixes
        suffixes = [' fc', ' sc', ' cf', ' afc', ' ac', ' as', ' fk', ' sk']
        for suffix in suffixes:
            if name.endswith(suffix):
                name = name[:-len(suffix)]

        # Remove prefixes
        prefixes = ['fc ', 'sc ', 'cf ', 'afc ', 'ac ', 'as ']
        for prefix in prefixes:
            if name.startswith(prefix):
                name = name[len(prefix):]

        # Remove special characters
        name = re.sub(r'[^a-z0-9\s]', '', name)
        name = ' '.join(name.split())

        return name

    def similarity(self, name1: str, name2: str) -> float:
        """
        Calculate similarity between two team names after normalization.

        Returns:
            Float between 0 and 1
        """
        norm1 = self.normalize(name1)
        norm2 = self.normalize(name2)
        return SequenceMatcher(None, norm1, norm2).ratio()

    def _fuzzy_match(self, name: str, candidates: List[str], threshold: float = 0.8) -> Optional[str]:
        """Find best fuzzy match above threshold."""
        name_norm = self.normalize(name)
        best_match = None
        best_score = 0

        for candidate in candidates:
            cand_norm = self.normalize(candidate)
            score = SequenceMatcher(None, name_norm, cand_norm).ratio()
            if score > best_score and score >= threshold:
                best_score = score
                best_match = candidate

        return best_match

    def validate_match(
        self,
        our_home: str,
        our_away: str,
        be_home: str,
        be_away: str,
        threshold: float = 0.8
    ) -> Tuple[bool, Dict]:
        """
        Validate that Betexplorer teams match our teams.

        Returns:
            (is_valid, details_dict)
        """
        # Convert our names to BE format
        our_home_be = self.to_source(our_home, "betexplorer")
        our_away_be = self.to_source(our_away, "betexplorer")

        # Calculate similarities
        sim_home = self.similarity(our_home_be, be_home)
        sim_away = self.similarity(our_away_be, be_away)

        details = {
            'our_home': our_home,
            'our_away': our_away,
            'our_home_be': our_home_be,
            'our_away_be': our_away_be,
            'be_home': be_home,
            'be_away': be_away,
            'sim_home': round(sim_home, 3),
            'sim_away': round(sim_away, 3),
            'threshold': threshold,
        }

        is_valid = sim_home >= threshold and sim_away >= threshold
        details['is_valid'] = is_valid

        return is_valid, details


# Singleton instance for convenience
_resolver: Optional[TeamResolver] = None

def get_resolver() -> TeamResolver:
    """Get singleton TeamResolver instance."""
    global _resolver
    if _resolver is None:
        _resolver = TeamResolver()
    return _resolver


# Convenience functions
def to_canonical(name: str, source: str = "betexplorer") -> str:
    """Convert source name to Mon_PS canonical."""
    return get_resolver().to_canonical(name, source)

def to_betexplorer(canonical_name: str) -> str:
    """Convert Mon_PS canonical to Betexplorer name."""
    return get_resolver().to_source(canonical_name, "betexplorer")

def normalize_team(name: str) -> str:
    """Normalize team name."""
    return TeamResolver.normalize(name)

def team_similarity(name1: str, name2: str) -> float:
    """Calculate similarity between two team names."""
    return get_resolver().similarity(name1, name2)


if __name__ == "__main__":
    print("=== Team Resolver Test ===\n")

    resolver = TeamResolver()

    # Test to_source (Mon_PS -> BE)
    print("1. Mon_PS -> Betexplorer:")
    tests = [
        "Manchester United",
        "Nottingham Forest",
        "Wolverhampton",
        "Leeds United",
        "Liverpool",  # No change expected
    ]
    for team in tests:
        be_name = resolver.to_source(team, "betexplorer")
        print(f"   {team} -> {be_name}")

    print()

    # Test to_canonical (BE -> Mon_PS)
    print("2. Betexplorer -> Mon_PS:")
    tests = [
        "Manchester Utd",
        "Nottingham",
        "Wolves",
        "Leeds",
        "Liverpool",
    ]
    for team in tests:
        canonical = resolver.to_canonical(team, "betexplorer")
        print(f"   {team} -> {canonical}")

    print()

    # Test similarity
    print("3. Similarity tests:")
    pairs = [
        ("Manchester United", "Manchester Utd"),
        ("Nottingham Forest", "Nottingham"),
        ("Man City", "Manchester City"),
        ("Real Madrid", "Real Betis"),
    ]
    for a, b in pairs:
        sim = resolver.similarity(a, b)
        status = "✅" if sim >= 0.8 else "❌"
        print(f"   {status} {a} vs {b}: {sim:.2f}")

    print("\n=== Test Complete ===")
