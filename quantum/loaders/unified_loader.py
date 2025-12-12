#!/usr/bin/env python3
"""
╔═══════════════════════════════════════════════════════════════════════════════════════╗
║  UNIFIED LOADER - MON_PS QUANTUM PLATFORM                                             ║
║  "Chaque équipe = 1 ADN = 1 empreinte digitale unique"                                ║
╚═══════════════════════════════════════════════════════════════════════════════════════╝

API unifiée pour accéder aux données ADN:
- Teams (team_dna_unified_v2.json)
- Players (player_dna_unified.json)
- Referees (referee_dna_unified.json)
- Name Mapping (team_name_mapping.json)

USAGE:
    from quantum.loaders.unified_loader import UnifiedLoader

    loader = UnifiedLoader()

    # Teams
    liverpool = loader.get_team("Liverpool")
    pl_teams = loader.get_teams_by_league("Premier League")

    # Players
    salah = loader.get_player("Salah", "Liverpool")
    defenders = loader.get_players_by_position("DEF")

    # Referees
    oliver = loader.get_referee("M Oliver")
    top_refs = loader.get_referees_by_tier("hedge_fund_grade")

    # Search
    results = loader.search("Liver", entity_type="team")

    # Stats
    stats = loader.get_stats()

Version: 2.0 - Unified API
Date: 12 Décembre 2025
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Dict, List, Optional, Any, Literal
from difflib import get_close_matches, SequenceMatcher
from functools import cached_property
import logging

# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════════

DATA_ROOT = Path("/home/Mon_ps/data/quantum_v2")

FILES = {
    "teams": DATA_ROOT / "team_dna_unified_v2.json",
    "players": DATA_ROOT / "player_dna_unified.json",
    "referees": DATA_ROOT / "referee_dna_unified.json",
    "mapping": DATA_ROOT / "team_name_mapping.json",
}

# Position mapping for players
# The data uses format like "D", "D M", "D M S", "F M S", "M S", etc.
# D = Defender, M = Midfielder, F = Forward, S = Substitute, GK = Goalkeeper
POSITION_CATEGORIES = {
    "GK": ["GK", "Goalkeeper"],
    "DEF": ["D", "DF", "CB", "LB", "RB", "WB", "Defender", "Centre-Back", "Left-Back", "Right-Back"],
    "MID": ["M", "MF", "CM", "DM", "AM", "CDM", "CAM", "Midfielder", "Central Midfield", "Defensive Midfield"],
    "ATT": ["F", "FW", "ST", "CF", "LW", "RW", "Forward", "Striker", "Winger", "Centre-Forward"],
}

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════════
# UNIFIED LOADER CLASS
# ═══════════════════════════════════════════════════════════════════════════════

class UnifiedLoader:
    """
    API unifiée pour accéder aux données ADN de Mon_PS.

    Features:
    - Lazy loading (données chargées au premier accès)
    - Cache en mémoire
    - Normalisation automatique des noms
    - Recherche floue
    - Type hints complets

    Example:
        loader = UnifiedLoader()
        team = loader.get_team("Liverpool")
        player = loader.get_player("Salah")
        ref = loader.get_referee("M Oliver")
    """

    def __init__(self, data_root: Optional[Path] = None):
        """
        Initialise le loader.

        Args:
            data_root: Chemin racine des données (optionnel, utilise le défaut sinon)
        """
        self._data_root = data_root or DATA_ROOT

        # Lazy-loaded data stores
        self._teams_data: Optional[Dict] = None
        self._players_data: Optional[Dict] = None
        self._referees_data: Optional[Dict] = None
        self._mapping_data: Optional[Dict] = None

        # Indexes for fast lookup
        self._team_name_index: Dict[str, str] = {}  # normalized -> canonical
        self._player_name_index: Dict[str, List[str]] = {}  # name -> [keys]
        self._referee_name_index: Dict[str, str] = {}  # normalized -> canonical

    # ═══════════════════════════════════════════════════════════════════════════
    # PRIVATE: DATA LOADING
    # ═══════════════════════════════════════════════════════════════════════════

    def _load_json(self, filepath: Path) -> Optional[Dict]:
        """Charge un fichier JSON."""
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                return json.load(f)
        except FileNotFoundError:
            logger.warning(f"Fichier non trouvé: {filepath}")
            return None
        except json.JSONDecodeError as e:
            logger.error(f"Erreur JSON dans {filepath}: {e}")
            return None

    @staticmethod
    def _normalize_name(name: str) -> str:
        """Normalise un nom pour la recherche (lowercase, sans accents basique)."""
        if not name:
            return ""
        # Lowercase et suppression des caractères spéciaux
        normalized = name.lower().strip()
        # Remplacements basiques d'accents
        replacements = {
            'é': 'e', 'è': 'e', 'ê': 'e', 'ë': 'e',
            'à': 'a', 'â': 'a', 'ä': 'a',
            'ù': 'u', 'û': 'u', 'ü': 'u',
            'î': 'i', 'ï': 'i',
            'ô': 'o', 'ö': 'o',
            'ç': 'c', 'ñ': 'n',
            "'": "", "-": " ", "_": " "
        }
        for old, new in replacements.items():
            normalized = normalized.replace(old, new)
        return normalized

    # ═══════════════════════════════════════════════════════════════════════════
    # PRIVATE: LAZY LOADING PROPERTIES
    # ═══════════════════════════════════════════════════════════════════════════

    @property
    def _teams(self) -> Dict[str, Dict]:
        """Lazy load teams data."""
        if self._teams_data is None:
            raw = self._load_json(FILES["teams"]) or {}
            self._teams_data = raw.get("teams", raw)
            # Build index AFTER data is loaded
        if not self._team_name_index and self._teams_data:
            self._build_team_index()
        return self._teams_data

    @property
    def _players(self) -> Dict[str, Dict]:
        """Lazy load players data."""
        if self._players_data is None:
            raw = self._load_json(FILES["players"]) or {}
            self._players_data = raw.get("players", raw)
        if not self._player_name_index and self._players_data:
            self._build_player_index()
        return self._players_data

    @property
    def _referees(self) -> Dict[str, Dict]:
        """Lazy load referees data."""
        if self._referees_data is None:
            self._referees_data = self._load_json(FILES["referees"]) or {}
        if not self._referee_name_index and self._referees_data:
            self._build_referee_index()
        return self._referees_data

    @property
    def _mapping(self) -> Dict:
        """Lazy load name mapping."""
        if self._mapping_data is None:
            self._mapping_data = self._load_json(FILES["mapping"]) or {}
        return self._mapping_data

    # ═══════════════════════════════════════════════════════════════════════════
    # PRIVATE: INDEX BUILDING
    # ═══════════════════════════════════════════════════════════════════════════

    def _build_team_index(self) -> None:
        """Construit l'index des noms d'équipes."""
        self._team_name_index = {}

        # Index depuis les données
        for team_name in self._teams_data.keys():
            normalized = self._normalize_name(team_name)
            self._team_name_index[normalized] = team_name

        # Index depuis le mapping (aliases)
        alias_to_canonical = self._mapping.get("alias_to_canonical", {})
        for alias, canonical in alias_to_canonical.items():
            normalized = self._normalize_name(alias)
            if normalized not in self._team_name_index:
                self._team_name_index[normalized] = canonical

    def _build_player_index(self) -> None:
        """Construit l'index des noms de joueurs."""
        self._player_name_index = {}

        for key in self._players_data.keys():
            # Key format: "player_name_team" ou "player name_team"
            parts = key.rsplit("_", 1)
            if len(parts) >= 1:
                player_name = parts[0].replace("_", " ")
                normalized = self._normalize_name(player_name)

                if normalized not in self._player_name_index:
                    self._player_name_index[normalized] = []
                self._player_name_index[normalized].append(key)

                # Index aussi le nom de famille seul
                name_parts = player_name.split()
                if len(name_parts) > 1:
                    last_name = self._normalize_name(name_parts[-1])
                    if last_name not in self._player_name_index:
                        self._player_name_index[last_name] = []
                    if key not in self._player_name_index[last_name]:
                        self._player_name_index[last_name].append(key)

    def _build_referee_index(self) -> None:
        """Construit l'index des noms d'arbitres."""
        self._referee_name_index = {}

        for ref_name in self._referees_data.keys():
            normalized = self._normalize_name(ref_name)
            self._referee_name_index[normalized] = ref_name

            # Index aussi le nom de famille seul
            parts = ref_name.split()
            if len(parts) > 1:
                last_name = self._normalize_name(parts[-1])
                if last_name not in self._referee_name_index:
                    self._referee_name_index[last_name] = ref_name

    # ═══════════════════════════════════════════════════════════════════════════
    # PRIVATE: NAME RESOLUTION
    # ═══════════════════════════════════════════════════════════════════════════

    def _resolve_team_name(self, name: str) -> Optional[str]:
        """Résout un nom d'équipe vers son nom canonique."""
        normalized = self._normalize_name(name)

        # Exact match
        if normalized in self._team_name_index:
            return self._team_name_index[normalized]

        # Fuzzy match
        matches = get_close_matches(normalized, self._team_name_index.keys(), n=1, cutoff=0.8)
        if matches:
            return self._team_name_index[matches[0]]

        return None

    def _resolve_player_keys(self, name: str, team: Optional[str] = None) -> List[str]:
        """Résout un nom de joueur vers ses clés dans le dictionnaire."""
        normalized = self._normalize_name(name)

        # Trigger lazy load
        _ = self._players

        keys = []

        # Exact match
        if normalized in self._player_name_index:
            keys = self._player_name_index[normalized].copy()
        else:
            # Fuzzy match
            matches = get_close_matches(normalized, self._player_name_index.keys(), n=3, cutoff=0.7)
            for match in matches:
                keys.extend(self._player_name_index[match])

        # Filter by team if provided
        if team and keys:
            team_normalized = self._normalize_name(team)
            keys = [k for k in keys if team_normalized in self._normalize_name(k)]

        return list(set(keys))  # Remove duplicates

    def _resolve_referee_name(self, name: str) -> Optional[str]:
        """Résout un nom d'arbitre vers son nom canonique."""
        normalized = self._normalize_name(name)

        # Trigger lazy load
        _ = self._referees

        # Exact match
        if normalized in self._referee_name_index:
            return self._referee_name_index[normalized]

        # Fuzzy match
        matches = get_close_matches(normalized, self._referee_name_index.keys(), n=1, cutoff=0.7)
        if matches:
            return self._referee_name_index[matches[0]]

        return None

    # ═══════════════════════════════════════════════════════════════════════════
    # PUBLIC API: TEAMS
    # ═══════════════════════════════════════════════════════════════════════════

    def get_team(self, name: str) -> Optional[Dict[str, Any]]:
        """
        Récupère les données d'une équipe par son nom.

        Args:
            name: Nom de l'équipe (flexible, accepte les aliases)

        Returns:
            Dictionnaire des données de l'équipe ou None si non trouvée

        Example:
            >>> loader.get_team("Liverpool")
            >>> loader.get_team("LFC")  # Alias supporté
            >>> loader.get_team("Liverpol")  # Fuzzy match
        """
        canonical = self._resolve_team_name(name)
        if canonical and canonical in self._teams:
            data = self._teams[canonical].copy()
            data["_canonical_name"] = canonical
            return data
        return None

    def get_all_teams(self) -> Dict[str, Dict[str, Any]]:
        """
        Récupère toutes les équipes.

        Returns:
            Dictionnaire {nom: données} de toutes les équipes
        """
        return self._teams.copy()

    def get_teams_by_league(self, league: str) -> List[Dict[str, Any]]:
        """
        Récupère toutes les équipes d'une ligue.

        Args:
            league: Nom de la ligue (ex: "Premier League", "Ligue 1")

        Returns:
            Liste des équipes de cette ligue
        """
        league_lower = league.lower()
        results = []

        for name, data in self._teams.items():
            team_league = ""
            # Chercher la ligue dans différentes structures (priorité: context > meta > root)
            if "context" in data and isinstance(data["context"], dict):
                team_league = data["context"].get("league", "")
            if not team_league and "meta" in data:
                team_league = data["meta"].get("league", "")
            if not team_league and "league" in data:
                team_league = data["league"]

            if team_league and league_lower in team_league.lower():
                result = data.copy()
                result["_canonical_name"] = name
                results.append(result)

        return results

    # ═══════════════════════════════════════════════════════════════════════════
    # PUBLIC API: PLAYERS
    # ═══════════════════════════════════════════════════════════════════════════

    def get_player(self, name: str, team: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Récupère les données d'un joueur par son nom.

        Args:
            name: Nom du joueur (peut être partiel, ex: "Salah")
            team: Nom de l'équipe pour filtrer (optionnel)

        Returns:
            Dictionnaire des données du joueur ou None si non trouvé

        Example:
            >>> loader.get_player("Salah")
            >>> loader.get_player("Salah", "Liverpool")
            >>> loader.get_player("Mohamed Salah")
        """
        keys = self._resolve_player_keys(name, team)

        if keys:
            # Return first match
            key = keys[0]
            data = self._players[key].copy()
            data["_key"] = key
            return data

        return None

    def get_all_players(self) -> Dict[str, Dict[str, Any]]:
        """
        Récupère tous les joueurs.

        Returns:
            Dictionnaire {clé: données} de tous les joueurs
        """
        return self._players.copy()

    def get_players_by_team(self, team: str) -> List[Dict[str, Any]]:
        """
        Récupère tous les joueurs d'une équipe.

        Args:
            team: Nom de l'équipe

        Returns:
            Liste des joueurs de l'équipe
        """
        team_normalized = self._normalize_name(team)
        results = []

        for key, data in self._players.items():
            # Check if team name is in key
            if team_normalized in self._normalize_name(key):
                result = data.copy()
                result["_key"] = key
                results.append(result)
                continue

            # Check meta.team
            if "meta" in data:
                player_team = data["meta"].get("team", "")
                if team_normalized in self._normalize_name(player_team):
                    result = data.copy()
                    result["_key"] = key
                    results.append(result)

        return results

    def get_players_by_position(self, position: str) -> List[Dict[str, Any]]:
        """
        Récupère tous les joueurs d'une position.

        Args:
            position: Catégorie de position ("GK", "DEF", "MID", "ATT")

        Returns:
            Liste des joueurs à cette position
        """
        position = position.upper()

        # Get position keywords
        keywords = POSITION_CATEGORIES.get(position, [position])

        results = []

        for key, data in self._players.items():
            player_position = ""
            player_category = ""

            # Get position from meta
            if "meta" in data and data["meta"]:
                player_category = data["meta"].get("position_category") or ""
                player_position = data["meta"].get("position") or ""
            elif "position" in data:
                player_position = data["position"] or ""

            matched = False

            # Check by category first (exact match for GK, CB)
            if player_category:
                cat_upper = player_category.upper()
                if cat_upper == position:
                    matched = True
                elif position == "DEF" and cat_upper == "CB":
                    matched = True
                elif position == "GK" and cat_upper == "GK":
                    matched = True

            # Check position field (handles composite positions like "D M S")
            if not matched and player_position:
                pos_parts = player_position.upper().split()
                for keyword in keywords:
                    kw_upper = keyword.upper()
                    # Match "D" in "D M S" for DEF
                    if kw_upper in pos_parts:
                        matched = True
                        break
                    # Exact match
                    if kw_upper == player_position.upper():
                        matched = True
                        break

            if matched:
                result = data.copy()
                result["_key"] = key
                results.append(result)

        return results

    # ═══════════════════════════════════════════════════════════════════════════
    # PUBLIC API: REFEREES
    # ═══════════════════════════════════════════════════════════════════════════

    def get_referee(self, name: str) -> Optional[Dict[str, Any]]:
        """
        Récupère les données d'un arbitre par son nom.

        Args:
            name: Nom de l'arbitre (flexible, ex: "Oliver", "M Oliver")

        Returns:
            Dictionnaire des données de l'arbitre ou None si non trouvé

        Example:
            >>> loader.get_referee("M Oliver")
            >>> loader.get_referee("Oliver")
            >>> loader.get_referee("Michael Oliver")
        """
        canonical = self._resolve_referee_name(name)
        if canonical and canonical in self._referees:
            data = self._referees[canonical].copy()
            data["_canonical_name"] = canonical
            return data
        return None

    def get_all_referees(self) -> Dict[str, Dict[str, Any]]:
        """
        Récupère tous les arbitres.

        Returns:
            Dictionnaire {nom: données} de tous les arbitres
        """
        return self._referees.copy()

    def get_referees_by_tier(self, tier: str) -> List[Dict[str, Any]]:
        """
        Récupère tous les arbitres d'un tier de qualité.

        Args:
            tier: Tier de qualité ("hedge_fund_grade", "excellent",
                  "championship_grade", "championship_partial", "partial", "minimal")

        Returns:
            Liste des arbitres de ce tier
        """
        tier_lower = tier.lower()
        results = []

        for name, data in self._referees.items():
            ref_tier = ""
            if "meta" in data:
                ref_tier = data["meta"].get("quality_tier", "")

            if ref_tier.lower() == tier_lower:
                result = data.copy()
                result["_canonical_name"] = name
                results.append(result)

        return results

    def get_referees_by_league_tier(self, league_tier: str) -> List[Dict[str, Any]]:
        """
        Récupère tous les arbitres d'un tier de ligue.

        Args:
            league_tier: "top_flight" (Premier League) ou "second_tier" (Championship)

        Returns:
            Liste des arbitres de ce tier de ligue
        """
        tier_lower = league_tier.lower()
        results = []

        for name, data in self._referees.items():
            ref_tier = ""
            if "meta" in data:
                ref_tier = data["meta"].get("league_tier", "")

            if ref_tier.lower() == tier_lower:
                result = data.copy()
                result["_canonical_name"] = name
                results.append(result)

        return results

    # ═══════════════════════════════════════════════════════════════════════════
    # PUBLIC API: SEARCH
    # ═══════════════════════════════════════════════════════════════════════════

    def search(
        self,
        query: str,
        entity_type: Literal["all", "team", "player", "referee"] = "all",
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Recherche floue dans toutes les entités.

        Args:
            query: Terme de recherche
            entity_type: Type d'entité ("all", "team", "player", "referee")
            limit: Nombre maximum de résultats

        Returns:
            Liste de résultats avec type et données

        Example:
            >>> loader.search("Liver")  # Trouve Liverpool, Liverbird, etc.
            >>> loader.search("Salah", entity_type="player")
        """
        query_normalized = self._normalize_name(query)
        results = []

        # Helper for similarity score
        def similarity_score(a: str, b: str) -> float:
            return SequenceMatcher(None, a, b).ratio()

        # Search teams
        if entity_type in ["all", "team"]:
            _ = self._teams  # Trigger lazy load
            matches = get_close_matches(query_normalized, self._team_name_index.keys(), n=limit, cutoff=0.5)
            for match in matches:
                canonical = self._team_name_index[match]
                if canonical in self._teams:
                    results.append({
                        "type": "team",
                        "name": canonical,
                        "match_score": similarity_score(query_normalized, match),
                        "data": self._teams[canonical]
                    })

        # Search players
        if entity_type in ["all", "player"]:
            _ = self._players  # Trigger lazy load
            matches = get_close_matches(query_normalized, self._player_name_index.keys(), n=limit, cutoff=0.5)
            for match in matches:
                for key in self._player_name_index[match][:2]:  # Limit per name
                    if key in self._players:
                        results.append({
                            "type": "player",
                            "name": key,
                            "match_score": similarity_score(query_normalized, match),
                            "data": self._players[key]
                        })

        # Search referees
        if entity_type in ["all", "referee"]:
            _ = self._referees  # Trigger lazy load
            matches = get_close_matches(query_normalized, self._referee_name_index.keys(), n=limit, cutoff=0.5)
            for match in matches:
                canonical = self._referee_name_index[match]
                if canonical in self._referees:
                    results.append({
                        "type": "referee",
                        "name": canonical,
                        "match_score": similarity_score(query_normalized, match),
                        "data": self._referees[canonical]
                    })

        # Sort by match score and limit
        results.sort(key=lambda x: x["match_score"], reverse=True)
        return results[:limit]

    # ═══════════════════════════════════════════════════════════════════════════
    # PUBLIC API: STATS
    # ═══════════════════════════════════════════════════════════════════════════

    def get_stats(self) -> Dict[str, Any]:
        """
        Retourne des statistiques sur les données chargées.

        Returns:
            Dictionnaire avec le nombre d'entités, la couverture, etc.
        """
        # Trigger lazy loading
        _ = self._teams
        _ = self._players
        _ = self._referees

        # Referee tiers
        ref_tiers = {}
        ref_league_tiers = {}
        for name, data in self._referees.items():
            meta = data.get("meta", {})
            tier = meta.get("quality_tier", "unknown")
            league_tier = meta.get("league_tier", "unknown")
            ref_tiers[tier] = ref_tiers.get(tier, 0) + 1
            ref_league_tiers[league_tier] = ref_league_tiers.get(league_tier, 0) + 1

        # Team leagues
        team_leagues = {}
        for name, data in self._teams.items():
            league = ""
            if "meta" in data:
                league = data["meta"].get("league", "unknown")
            elif "context" in data:
                league = data["context"].get("league", "unknown")
            team_leagues[league] = team_leagues.get(league, 0) + 1

        # Player positions (use same logic as get_players_by_position)
        player_positions = {"GK": 0, "DEF": 0, "MID": 0, "ATT": 0, "unknown": 0}
        for key, data in self._players.items():
            pos_cat = ""
            pos_val = ""
            if "meta" in data and data["meta"]:
                pos_cat = data["meta"].get("position_category") or ""
                pos_val = data["meta"].get("position") or ""

            # Determine category
            assigned = False
            if pos_cat:
                cat_upper = pos_cat.upper()
                if cat_upper == "GK":
                    player_positions["GK"] += 1
                    assigned = True
                elif cat_upper == "CB":
                    player_positions["DEF"] += 1
                    assigned = True

            if not assigned and pos_val:
                pos_parts = pos_val.upper().split()
                if "GK" in pos_parts:
                    player_positions["GK"] += 1
                elif "D" in pos_parts:
                    player_positions["DEF"] += 1
                elif "M" in pos_parts:
                    player_positions["MID"] += 1
                elif "F" in pos_parts:
                    player_positions["ATT"] += 1
                else:
                    player_positions["unknown"] += 1
            elif not assigned:
                player_positions["unknown"] += 1

        return {
            "teams": {
                "total": len(self._teams),
                "loaded": len(self._teams),  # Alias for compatibility
                "by_league": team_leagues,
            },
            "players": {
                "total": len(self._players),
                "loaded": len(self._players),  # Alias for compatibility
                "by_position": player_positions,
            },
            "referees": {
                "total": len(self._referees),
                "loaded": len(self._referees),  # Alias for compatibility
                "by_quality_tier": ref_tiers,
                "by_league_tier": ref_league_tiers,
            },
            "mapping": {
                "aliases": len(self._mapping.get("alias_to_canonical", {})),
                "canonical": len(self._mapping.get("canonical_to_aliases", {})),
            },
            "data_files": {
                name: str(path) for name, path in FILES.items()
            }
        }

    # ═══════════════════════════════════════════════════════════════════════════
    # UTILITY METHODS
    # ═══════════════════════════════════════════════════════════════════════════

    def reload(self) -> None:
        """Force le rechargement de toutes les données."""
        self._teams_data = None
        self._players_data = None
        self._referees_data = None
        self._mapping_data = None
        self._team_name_index = {}
        self._player_name_index = {}
        self._referee_name_index = {}

    def get_canonical_team_name(self, name: str) -> Optional[str]:
        """
        Retourne le nom canonique d'une équipe.

        Args:
            name: Nom ou alias de l'équipe

        Returns:
            Nom canonique ou None si non trouvé
        """
        return self._resolve_team_name(name)

    def list_team_aliases(self, team: str) -> List[str]:
        """
        Liste tous les aliases connus pour une équipe.

        Args:
            team: Nom de l'équipe

        Returns:
            Liste des aliases
        """
        canonical = self._resolve_team_name(team)
        if not canonical:
            return []

        canonical_to_aliases = self._mapping.get("canonical_to_aliases", {})
        return canonical_to_aliases.get(canonical, [])


# ═══════════════════════════════════════════════════════════════════════════════
# SINGLETON INSTANCE
# ═══════════════════════════════════════════════════════════════════════════════

_default_loader: Optional[UnifiedLoader] = None


def get_loader() -> UnifiedLoader:
    """Retourne l'instance singleton du loader."""
    global _default_loader
    if _default_loader is None:
        _default_loader = UnifiedLoader()
    return _default_loader


# ═══════════════════════════════════════════════════════════════════════════════
# CONVENIENCE FUNCTIONS (Backward compatibility)
# ═══════════════════════════════════════════════════════════════════════════════

def load_team(name: str) -> Optional[Dict]:
    """Fonction de commodité pour charger une équipe."""
    return get_loader().get_team(name)


def load_all_teams() -> Dict[str, Dict]:
    """Fonction de commodité pour charger toutes les équipes."""
    return get_loader().get_all_teams()


def get_team(name: str) -> Optional[Dict]:
    """Alias pour load_team."""
    return load_team(name)


# ═══════════════════════════════════════════════════════════════════════════════
# CLI TEST
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("\n" + "=" * 70)
    print("   UNIFIED LOADER - MON_PS QUANTUM PLATFORM")
    print("=" * 70)

    loader = UnifiedLoader()

    # Get stats
    stats = loader.get_stats()

    print(f"\n📊 STATISTIQUES:")
    print(f"   Teams:    {stats['teams']['total']}")
    print(f"   Players:  {stats['players']['total']}")
    print(f"   Referees: {stats['referees']['total']}")

    print(f"\n📋 ARBITRES PAR TIER:")
    for tier, count in stats['referees']['by_quality_tier'].items():
        print(f"   {tier}: {count}")

    # Test team
    print(f"\n🏟️ TEST TEAM:")
    team = loader.get_team("Liverpool")
    if team:
        print(f"   Found: {team.get('_canonical_name', 'N/A')}")
        # League can be in context or meta
        league = team.get("context", {}).get("league") or team.get("meta", {}).get("league", "N/A")
        print(f"   League: {league}")

    # Test player
    print(f"\n👤 TEST PLAYER:")
    player = loader.get_player("Salah")
    if player:
        print(f"   Found: {player.get('_key', 'N/A')}")

    # Test referee
    print(f"\n👨‍⚖️ TEST REFEREE:")
    ref = loader.get_referee("Oliver")
    if ref:
        print(f"   Found: {ref.get('_canonical_name', 'N/A')}")
        if "meta" in ref:
            print(f"   Tier: {ref['meta'].get('quality_tier', 'N/A')}")

    # Test search
    print(f"\n🔍 TEST SEARCH 'liver':")
    results = loader.search("liver", limit=5)
    for r in results:
        print(f"   [{r['type']}] {r['name']}")

    # Test referees by tier
    print(f"\n🏆 HEDGE FUND GRADE REFEREES:")
    hfg_refs = loader.get_referees_by_tier("hedge_fund_grade")
    for ref in hfg_refs[:5]:
        print(f"   {ref.get('_canonical_name', 'N/A')}")
    print(f"   ... ({len(hfg_refs)} total)")

    print("\n" + "=" * 70)
    print("   ✅ ALL TESTS PASSED")
    print("=" * 70)
