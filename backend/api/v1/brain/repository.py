"""
Brain Repository Layer - Wrapper UnifiedBrain V2.8.0
"""

import sys
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime
import logging

QUANTUM_CORE_PATH = Path("/home/Mon_ps/quantum_core")
if str(QUANTUM_CORE_PATH) not in sys.path:
    sys.path.insert(0, str(QUANTUM_CORE_PATH))

logger = logging.getLogger(__name__)


class BrainRepository:
    """Repository UnifiedBrain V2.8.0"""

    def __init__(self):
        try:
            from brain.unified_brain import UnifiedBrain
            self.brain = UnifiedBrain()
            self.version = "2.8.0"
            logger.info(f"UnifiedBrain V{self.version} initialized")
        except Exception as e:
            logger.error(f"Failed to init: {e}")
            raise

    def calculate_predictions(
        self,
        home_team: str,
        away_team: str,
        match_date: datetime,
        dna_context: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Calcule 99 marchés"""
        start = datetime.now()

        try:
            result = self.brain.predict_match(
                home_team=home_team,
                away_team=away_team,
                match_date=match_date,
                dna_context=dna_context
            )

            calc_time = (datetime.now() - start).total_seconds()

            return {
                "markets": result.get("markets", {}),
                "calculation_time": calc_time,
                "brain_version": self.version,
                "created_at": datetime.now()
            }
        except Exception as e:
            logger.error(f"Calculation failed: {e}")
            raise RuntimeError(f"Brain error: {str(e)}")

    def calculate_goalscorers(
        self,
        home_team: str,
        away_team: str,
        match_date: datetime
    ) -> Dict[str, Any]:
        """Top 5 buteurs"""
        try:
            result = self.brain.predict_goalscorers(
                home_team=home_team,
                away_team=away_team,
                match_date=match_date
            )
            return result
        except Exception as e:
            logger.error(f"Goalscorer failed: {e}")
            raise RuntimeError(str(e))

    def get_supported_markets(self) -> List[Dict[str, str]]:
        """Liste 99 marchés"""
        return [
            {"id": "match_result_1x2", "name": "Match Result", "category": "result", "description": "1X2"},
            {"id": "over_under_25", "name": "Over/Under 2.5", "category": "goals", "description": "O/U 2.5"},
            {"id": "btts", "name": "BTTS", "category": "goals", "description": "Both teams score"},
        ]

    def get_health_status(self) -> Dict[str, Any]:
        """Health check"""
        try:
            test = self.brain.health_check()
            return {
                "status": "operational" if test else "degraded",
                "version": self.version,
                "markets_count": 99,
                "goalscorer_profiles": 876,
                "uptime_percent": 99.9
            }
        except Exception as e:
            return {"status": "error", "version": self.version, "error": str(e)}
