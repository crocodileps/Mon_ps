#!/usr/bin/env python3
"""
═══════════════════════════════════════════════════════════════════════════════
GOALS INGESTION SERVICE - Hedge Fund Grade
═══════════════════════════════════════════════════════════════════════════════

Service principal d'ingestion des buts depuis Understat vers PostgreSQL.

HISTORIQUE DU BUG CORRIGÉ:
- Fichier: understat_master_v2.py
- Bug: match.get('h', {}).get('goals', 0) 
- Fix: match.get('goals', {}).get('h', 0)
- Les scores sont dans match['goals']['h'], PAS match['h']['goals']

Auteur: Mon_PS Team
Date: 2025-12-23
Branche: feature/goals-unified-ssot

═══════════════════════════════════════════════════════════════════════════════
"""

import json
import logging
import argparse
import psycopg2
from psycopg2.extras import execute_values
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional, Tuple

from .config import (
    DB_CONFIG, 
    UNDERSTAT_RAW_FILE, 
    MIN_GOALS_REQUIRED,
    SUPPORTED_LEAGUES,
    LEAGUE_NAMES,
    LOG_FILE,
    LOG_FORMAT,
    LOG_DATE_FORMAT
)
from .validator import GoalsValidator

# ═══════════════════════════════════════════════════════════════════════════════
# LOGGING SETUP
# ═══════════════════════════════════════════════════════════════════════════════

logging.basicConfig(
    level=logging.INFO,
    format=LOG_FORMAT,
    datefmt=LOG_DATE_FORMAT,
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class GoalsIngestionService:
    """
    Service d'ingestion des buts - Hedge Fund Grade.
    
    Lit les données Understat et les insère dans PostgreSQL
    avec toutes les protections nécessaires.
    """
    
    def __init__(self, dry_run: bool = False):
        self.dry_run = dry_run
        self.validator = GoalsValidator(min_goals=MIN_GOALS_REQUIRED)
        self.goals_processed = 0
        self.goals_inserted = 0
        self.errors = []
    
    # ═══════════════════════════════════════════════════════════════════════════
    # MÉTHODE PRINCIPALE
    # ═══════════════════════════════════════════════════════════════════════════
    
    def run(self, source_file: Optional[Path] = None) -> bool:
        """
        Exécute l'ingestion complète.
        
        Args:
            source_file: Chemin vers le fichier JSON source (défaut: understat_raw_api.json)
            
        Returns:
            bool: True si succès, False sinon
        """
        source = source_file or UNDERSTAT_RAW_FILE
        
        logger.info("=" * 70)
        logger.info("GOALS INGESTION SERVICE - Hedge Fund Grade")
        logger.info("=" * 70)
        logger.info(f"Mode: {'DRY-RUN' if self.dry_run else 'PRODUCTION'}")
        logger.info(f"Source: {source}")
        logger.info(f"Destination: quantum.goals_unified")
        logger.info("=" * 70)
        
        try:
            # 1. Charger les données brutes
            raw_data = self._load_raw_data(source)
            if not raw_data:
                return False
            
            # 2. Extraire les buts avec le MAPPING CORRECT
            goals = self._extract_goals(raw_data)
            
            # 3. Valider
            is_valid, msg = self.validator.validate(goals)
            if not is_valid:
                logger.error(f"Validation échouée: {msg}")
                logger.error("INGESTION ANNULÉE - Données protégées")
                return False
            
            # 4. Insérer en base
            if not self.dry_run:
                success = self._insert_to_db(goals)
                if not success:
                    return False
            else:
                logger.info(f"[DRY-RUN] Aurait inséré {len(goals)} buts")
                self.goals_inserted = len(goals)
            
            # 5. Rapport final
            self._print_report()
            return True
            
        except Exception as e:
            logger.error(f"ERREUR CRITIQUE: {e}")
            self.errors.append(str(e))
            return False
    
    # ═══════════════════════════════════════════════════════════════════════════
    # CHARGEMENT DONNÉES
    # ═══════════════════════════════════════════════════════════════════════════
    
    def _load_raw_data(self, source: Path) -> Optional[Dict]:
        """Charge le fichier JSON brut."""
        logger.info(f"[1/4] Chargement {source.name}...")
        
        if not source.exists():
            logger.error(f"Fichier non trouvé: {source}")
            return None
        
        try:
            with open(source) as f:
                data = json.load(f)
            
            # Vérifier structure
            leagues_found = [k for k in data.keys() if k in SUPPORTED_LEAGUES]
            logger.info(f"   OK: {len(leagues_found)} ligues trouvées: {leagues_found}")
            
            return data
            
        except json.JSONDecodeError as e:
            logger.error(f"Erreur parsing JSON: {e}")
            return None
    
    # ═══════════════════════════════════════════════════════════════════════════
    # EXTRACTION DES BUTS - MAPPING CORRECT
    # ═══════════════════════════════════════════════════════════════════════════
    
    def _extract_goals(self, raw_data: Dict) -> List[Dict]:
        """
        Extrait les buts depuis les données brutes.
        
        ⚠️ ATTENTION - MAPPING CORRECT:
        Les scores sont dans match['goals']['h'] et match['goals']['a']
        PAS dans match['h']['goals'] (bug historique)
        """
        logger.info("[2/4] Extraction des buts...")
        
        all_goals = []
        goal_id_counter = 0
        
        for league_code in SUPPORTED_LEAGUES:
            if league_code not in raw_data:
                continue
            
            league_data = raw_data[league_code]
            matches = league_data.get("dates", [])
            league_goals = 0
            
            for match in matches:
                # Skip si match pas encore joué
                if not match.get("isResult"):
                    continue
                
                match_id = str(match.get("id", ""))
                match_date = match.get("datetime", "")
                
                # Équipes
                home_team = match.get("h", {}).get("title", "Unknown")
                away_team = match.get("a", {}).get("title", "Unknown")
                
                # ═══════════════════════════════════════════════════════════════
                # MAPPING CORRECT - NE JAMAIS CHANGER
                # ═══════════════════════════════════════════════════════════════
                goals_data = match.get("goals", {})
                home_goals = int(goals_data.get("h", 0))
                away_goals = int(goals_data.get("a", 0))
                # ═══════════════════════════════════════════════════════════════
                
                xg_data = match.get("xG", {})
                home_xg = float(xg_data.get("h", 0))
                away_xg = float(xg_data.get("a", 0))
                
                # Créer entrées pour buts domicile
                for i in range(home_goals):
                    goal_id_counter += 1
                    all_goals.append(self._create_goal_entry(
                        goal_id=f"gen_{goal_id_counter}",
                        match_id=match_id,
                        date=match_date,
                        league=LEAGUE_NAMES.get(league_code, league_code),
                        team_name=home_team,
                        opponent=away_team,
                        is_home=True,
                        home_team=home_team,
                        away_team=away_team,
                        goal_number=i + 1,
                        total_goals_team=home_goals,
                        xg_match=home_xg / home_goals if home_goals > 0 else 0
                    ))
                
                # Créer entrées pour buts extérieur
                for i in range(away_goals):
                    goal_id_counter += 1
                    all_goals.append(self._create_goal_entry(
                        goal_id=f"gen_{goal_id_counter}",
                        match_id=match_id,
                        date=match_date,
                        league=LEAGUE_NAMES.get(league_code, league_code),
                        team_name=away_team,
                        opponent=home_team,
                        is_home=False,
                        home_team=home_team,
                        away_team=away_team,
                        goal_number=i + 1,
                        total_goals_team=away_goals,
                        xg_match=away_xg / away_goals if away_goals > 0 else 0
                    ))
                
                league_goals += home_goals + away_goals
            
            logger.info(f"   {league_code}: {league_goals} buts")
        
        self.goals_processed = len(all_goals)
        logger.info(f"   TOTAL: {len(all_goals)} buts extraits")
        
        return all_goals
    
    def _create_goal_entry(self, **kwargs) -> Dict:
        """Crée une entrée de but normalisée."""
        # Estimer la minute (distribution uniforme si pas de données détaillées)
        import random
        estimated_minute = random.randint(1, 90)
        
        return {
            "goal_id": kwargs["goal_id"],
            "match_id": kwargs["match_id"],
            "date": kwargs["date"],
            "league": kwargs["league"],
            "team_name": kwargs["team_name"],
            "opponent": kwargs["opponent"],
            "is_home": kwargs["is_home"],
            "home_team": kwargs["home_team"],
            "away_team": kwargs["away_team"],
            "minute": estimated_minute,
            "period": self._calculate_period(estimated_minute),
            "xg": kwargs.get("xg_match"),
            "goal_number_in_match": kwargs["goal_number"],
            "is_first_goal": kwargs["goal_number"] == 1,
            "is_last_goal": kwargs["goal_number"] == kwargs["total_goals_team"],
            "player_name": "Unknown",  # Pas disponible dans ce format
            "player_id": None,
            "situation": None,
            "shot_type": None,
        }
    
    @staticmethod
    def _calculate_period(minute: int) -> str:
        """Calcule la période depuis la minute."""
        if minute <= 15: return "0-15"
        elif minute <= 30: return "16-30"
        elif minute <= 45: return "31-45"
        elif minute <= 60: return "46-60"
        elif minute <= 75: return "61-75"
        elif minute <= 90: return "76-90"
        else: return "90+"
    
    # ═══════════════════════════════════════════════════════════════════════════
    # INSERTION BASE DE DONNÉES
    # ═══════════════════════════════════════════════════════════════════════════
    
    def _insert_to_db(self, goals: List[Dict]) -> bool:
        """Insère les buts en base avec transaction atomique."""
        logger.info("[3/4] Insertion dans PostgreSQL...")
        
        conn = None
        try:
            conn = psycopg2.connect(**DB_CONFIG)
            cursor = conn.cursor()
            
            # Préparer les tuples
            values = [self._goal_to_tuple(g) for g in goals]
            
            # UPSERT atomique
            sql = """
            INSERT INTO quantum.goals_unified (
                goal_id, match_id, season, league, date,
                home_team, away_team, player_id, player_name,
                team_name, opponent, is_home, minute, period,
                xg, situation, shot_type, is_first_goal, is_last_goal,
                goal_number_in_match, source
            ) VALUES %s
            ON CONFLICT (goal_id) DO UPDATE SET
                xg = EXCLUDED.xg,
                updated_at = NOW()
            """
            
            execute_values(cursor, sql, values, page_size=100)
            conn.commit()
            
            self.goals_inserted = len(values)
            logger.info(f"   OK: {self.goals_inserted} buts insérés/mis à jour")
            
            return True
            
        except Exception as e:
            if conn:
                conn.rollback()
            logger.error(f"   ERREUR SQL: {e}")
            logger.error("   Transaction ROLLBACK")
            self.errors.append(str(e))
            return False
            
        finally:
            if conn:
                conn.close()
    
    def _goal_to_tuple(self, goal: Dict) -> Tuple:
        """Convertit un but en tuple pour SQL."""
        return (
            goal["goal_id"],
            goal["match_id"],
            "2025",  # season
            goal["league"],
            goal["date"],
            goal["home_team"],
            goal["away_team"],
            goal.get("player_id"),
            goal["player_name"],
            goal["team_name"],
            goal["opponent"],
            goal["is_home"],
            goal["minute"],
            goal["period"],
            goal.get("xg"),
            goal.get("situation"),
            goal.get("shot_type"),
            goal.get("is_first_goal", False),
            goal.get("is_last_goal", False),
            goal.get("goal_number_in_match"),
            "understat_raw"
        )
    
    # ═══════════════════════════════════════════════════════════════════════════
    # RAPPORT
    # ═══════════════════════════════════════════════════════════════════════════
    
    def _print_report(self):
        """Affiche le rapport final."""
        logger.info("[4/4] Rapport final")
        logger.info("=" * 70)
        logger.info(f"Buts traités: {self.goals_processed}")
        logger.info(f"Buts insérés: {self.goals_inserted}")
        if self.errors:
            logger.info(f"Erreurs: {len(self.errors)}")
            for e in self.errors[:5]:
                logger.info(f"  - {e}")
        logger.info("=" * 70)
        logger.info("INGESTION TERMINÉE AVEC SUCCÈS" if not self.errors else "INGESTION TERMINÉE AVEC ERREURS")
        logger.info("=" * 70)


# ═══════════════════════════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(
        description="Goals Ingestion Service - Hedge Fund Grade"
    )
    parser.add_argument(
        "--dry-run", 
        action="store_true", 
        help="Mode simulation (pas d insertion)"
    )
    parser.add_argument(
        "--source",
        type=str,
        default=None,
        help="Fichier JSON source (defaut: understat_raw_api.json)"
    )
    
    args = parser.parse_args()
    
    source = Path(args.source) if args.source else None
    service = GoalsIngestionService(dry_run=args.dry_run)
    success = service.run(source_file=source)
    
    exit(0 if success else 1)


if __name__ == "__main__":
    main()
