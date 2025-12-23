#!/usr/bin/env python3
"""
═══════════════════════════════════════════════════════════════════════════════
LEGACY EXPORTER - Export PostgreSQL vers JSON
═══════════════════════════════════════════════════════════════════════════════

Exporte les buts depuis quantum.goals_unified vers all_goals_2025.json
pour compatibilité avec les 20 scripts legacy.

PROTECTION: Backup automatique avant écrasement.

Auteur: Mon_PS Team
Date: 2025-12-23
═══════════════════════════════════════════════════════════════════════════════
"""

import json
import shutil
import logging
import psycopg2
from psycopg2.extras import RealDictCursor
from pathlib import Path
from datetime import datetime

from .config import (
    DB_CONFIG,
    LEGACY_GOALS_FILE,
    LEGACY_GOALS_BACKUP,
    MIN_GOALS_REQUIRED
)

logger = logging.getLogger(__name__)


class LegacyExporter:
    """Exporte les buts PostgreSQL vers JSON legacy."""
    
    def __init__(self):
        self.goals_exported = 0
    
    def export(self, output_file: Path = None) -> bool:
        """
        Exporte les buts vers JSON.
        
        Args:
            output_file: Chemin de sortie (defaut: all_goals_2025.json)
            
        Returns:
            bool: True si succes
        """
        output = output_file or LEGACY_GOALS_FILE
        
        logger.info("=" * 70)
        logger.info("LEGACY EXPORTER - PostgreSQL vers JSON")
        logger.info("=" * 70)
        
        try:
            # 1. Charger depuis PostgreSQL
            goals = self._load_from_db()
            
            # 2. Valider (protection anti-export-vide)
            if len(goals) < MIN_GOALS_REQUIRED:
                logger.error(f"ERREUR: {len(goals)} buts < {MIN_GOALS_REQUIRED}")
                logger.error("Export ANNULE - fichier legacy protege")
                return False
            
            # 3. Backup avant ecrasement
            self._backup_existing(output)
            
            # 4. Ecrire le JSON
            self._write_json(goals, output)
            
            logger.info("=" * 70)
            logger.info(f"EXPORT TERMINE: {self.goals_exported} buts")
            logger.info(f"Fichier: {output}")
            logger.info("=" * 70)
            
            return True
            
        except Exception as e:
            logger.error(f"ERREUR: {e}")
            return False
    
    def _load_from_db(self) -> list:
        """Charge les buts depuis PostgreSQL."""
        logger.info("[1/3] Chargement depuis PostgreSQL...")
        
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        # Utiliser les champs calcules par trigger pour compatibilite
        cursor.execute("""
            SELECT 
                goal_id,
                match_id,
                scorer,
                scoring_team,
                opponent,
                league,
                date::text as date,
                minute,
                half,
                timing_period,
                period,
                xg,
                situation,
                shot_type,
                is_home,
                home_team,
                away_team,
                is_first_goal,
                is_last_goal,
                goal_number_in_match,
                player_id,
                player_name,
                team_name
            FROM quantum.goals_unified
            WHERE season = '2025'
            ORDER BY date, match_id, minute
        """)
        
        goals = [dict(row) for row in cursor.fetchall()]
        conn.close()
        
        logger.info(f"   OK: {len(goals)} buts charges")
        return goals
    
    def _backup_existing(self, output: Path):
        """Backup le fichier existant avant ecrasement."""
        logger.info("[2/3] Backup fichier existant...")
        
        if output.exists():
            backup_path = output.with_suffix('.json.bak')
            shutil.copy(output, backup_path)
            logger.info(f"   OK: Backup cree -> {backup_path.name}")
        else:
            logger.info("   OK: Pas de fichier existant")
    
    def _write_json(self, goals: list, output: Path):
        """Ecrit le fichier JSON."""
        logger.info("[3/3] Ecriture JSON...")
        
        # Assurer que le dossier existe
        output.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output, 'w') as f:
            json.dump(goals, f, indent=2, default=str)
        
        size_kb = output.stat().st_size / 1024
        self.goals_exported = len(goals)
        
        logger.info(f"   OK: {self.goals_exported} buts ({size_kb:.1f} KB)")


def main():
    """CLI pour export manuel."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Export PostgreSQL vers JSON")
    parser.add_argument("--output", type=str, help="Fichier de sortie")
    args = parser.parse_args()
    
    output = Path(args.output) if args.output else None
    exporter = LegacyExporter()
    success = exporter.export(output_file=output)
    
    exit(0 if success else 1)


if __name__ == "__main__":
    main()
