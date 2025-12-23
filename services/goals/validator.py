#!/usr/bin/env python3
"""
═══════════════════════════════════════════════════════════════════════════════
GOALS VALIDATOR - Protection anti-données corrompues
═══════════════════════════════════════════════════════════════════════════════
"""

import logging
from typing import List, Dict, Tuple

from .config import MIN_GOALS_REQUIRED, SUPPORTED_LEAGUES

logger = logging.getLogger(__name__)


class GoalsValidator:
    """Valide les données de buts avant insertion."""
    
    def __init__(self, min_goals: int = MIN_GOALS_REQUIRED):
        self.min_goals = min_goals
        self.errors = []
        self.warnings = []
    
    def validate(self, goals: List[Dict]) -> Tuple[bool, str]:
        """
        Valide une liste de buts.
        
        Returns:
            Tuple[bool, str]: (is_valid, message)
        """
        self.errors = []
        self.warnings = []
        
        # Check 1: Liste non vide
        if not goals:
            self.errors.append("Liste de buts vide")
            return False, "ERREUR: Liste de buts vide"
        
        # Check 2: Minimum requis
        if len(goals) < self.min_goals:
            self.errors.append(f"Seulement {len(goals)} buts (minimum: {self.min_goals})")
            return False, f"ERREUR: {len(goals)} buts < {self.min_goals} minimum"
        
        # Check 3: Champs obligatoires
        required_fields = ["match_id", "team_name", "minute", "league"]
        missing_fields = 0
        
        for i, goal in enumerate(goals[:100]):  # Check first 100
            for field in required_fields:
                if not goal.get(field):
                    missing_fields += 1
                    if missing_fields <= 5:
                        self.warnings.append(f"But #{i}: champ '{field}' manquant")
        
        if missing_fields > len(goals) * 0.1:  # Plus de 10% manquants
            self.errors.append(f"{missing_fields} champs obligatoires manquants")
            return False, f"ERREUR: Trop de champs manquants ({missing_fields})"
        
        # Check 4: Ligues valides
        leagues_found = set(g.get("league") for g in goals if g.get("league"))
        invalid_leagues = leagues_found - set(SUPPORTED_LEAGUES)
        if invalid_leagues:
            self.warnings.append(f"Ligues inconnues: {invalid_leagues}")
        
        # Check 5: Minutes valides (0-120)
        invalid_minutes = sum(1 for g in goals if not 0 <= g.get("minute", -1) <= 120)
        if invalid_minutes > 0:
            self.warnings.append(f"{invalid_minutes} buts avec minute invalide")
        
        # Success
        msg = f"OK: {len(goals)} buts valides"
        if self.warnings:
            msg += f" ({len(self.warnings)} warnings)"
        
        logger.info(msg)
        return True, msg
    
    def get_report(self) -> str:
        """Retourne un rapport de validation."""
        lines = ["=== RAPPORT VALIDATION ==="]
        
        if self.errors:
            lines.append(f"ERREURS ({len(self.errors)}):")
            for e in self.errors:
                lines.append(f"  - {e}")
        
        if self.warnings:
            lines.append(f"WARNINGS ({len(self.warnings)}):")
            for w in self.warnings[:10]:  # Max 10
                lines.append(f"  - {w}")
            if len(self.warnings) > 10:
                lines.append(f"  ... et {len(self.warnings) - 10} autres")
        
        if not self.errors and not self.warnings:
            lines.append("Aucun problème détecté")
        
        return "\n".join(lines)
