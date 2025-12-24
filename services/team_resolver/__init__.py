"""
Team Name Resolver Service
═══════════════════════════════════════════════════════════════════════════
Résolution centralisée des noms d'équipes entre différentes sources.

Usage:
    from services.team_resolver import TeamNameResolver

    resolver = TeamNameResolver()
    api_football_name = resolver.to_api_football("Manchester United")
    # Returns: "Manchester United FC"

Auteur: Mon_PS Team
Date: 2025-12-24
Version: 1.0.0
═══════════════════════════════════════════════════════════════════════════
"""
from .resolver import TeamNameResolver

__all__ = ['TeamNameResolver']
