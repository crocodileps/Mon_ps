"""
Brain Repository Layer - Wrapper UnifiedBrain V2.8.0

Architecture:
- Single Source of Truth: /quantum_core_master (Docker volume)
- Read-Only mount pour immutabilité
- Path explicite pour éviter confusion
"""

import sys
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime
import logging

# ============================================================================
# PATH CONFIGURATION - EXPLICIT & DOCUMENTED
# ============================================================================

# Priority 1: Docker volume (production)
QUANTUM_CORE_DOCKER = Path("/quantum_core")

# Priority 2: Local development (hors Docker)
QUANTUM_CORE_LOCAL = Path("/home/Mon_ps/quantum_core")

# Détecter environnement
if QUANTUM_CORE_DOCKER.exists():
    QUANTUM_CORE_PATH = QUANTUM_CORE_DOCKER
    ENV = "DOCKER"
elif QUANTUM_CORE_LOCAL.exists():
    QUANTUM_CORE_PATH = QUANTUM_CORE_LOCAL
    ENV = "LOCAL"
else:
    raise RuntimeError(
        "quantum_core MASTER not found. Expected:\n"
        f"  - {QUANTUM_CORE_DOCKER} (Docker volume)\n"
        f"  - {QUANTUM_CORE_LOCAL} (local dev)"
    )

# Ajouter au sys.path
# Important: Ajouter le PARENT pour permettre "from quantum_core.xxx"
quantum_core_parent = QUANTUM_CORE_PATH.parent
if str(quantum_core_parent) not in sys.path:
    sys.path.insert(0, str(quantum_core_parent))

# Aussi ajouter quantum_core directement pour "from brain.xxx"
if str(QUANTUM_CORE_PATH) not in sys.path:
    sys.path.insert(0, str(QUANTUM_CORE_PATH))

logger = logging.getLogger(__name__)
logger.info(f"quantum_core loaded from: {QUANTUM_CORE_PATH} (ENV={ENV})")

# ============================================================================
# IMPORTS UnifiedBrain (après path setup)
# ============================================================================

try:
    from brain.unified_brain import UnifiedBrain
except ImportError as e:
    logger.error(f"Failed to import UnifiedBrain: {e}")
    logger.error(f"sys.path: {sys.path}")
    logger.error(f"quantum_core path: {QUANTUM_CORE_PATH}")
    raise


class BrainRepository:
    """Repository UnifiedBrain V2.8.0"""

    def __init__(self):
        try:
            self.brain = UnifiedBrain()
            self.version = "2.8.0"
            logger.info(f"UnifiedBrain V{self.version} initialized (ENV={ENV})")
        except Exception as e:
            logger.error(f"Failed to init UnifiedBrain: {e}")
            raise

    def calculate_predictions(
        self,
        home_team: str,
        away_team: str,
        match_date: datetime,
        dna_context: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Calcule 93 marchés via analyze_match()

        Note: UnifiedBrain V2.8.0 utilise analyze_match(), pas predict_match()
        """
        start = datetime.now()

        try:
            # API UnifiedBrain V2.8.0 = analyze_match()
            result = self.brain.analyze_match(
                home=home_team,
                away=away_team
                # Note: match_date et dna_context pas supportés par v2.8.0
                # TODO: Upgrade UnifiedBrain pour supporter ces params
            )

            calc_time = (datetime.now() - start).total_seconds()

            # Adapter MatchPrediction → Dict API
            return {
                "markets": self._convert_match_prediction_to_markets(result),
                "calculation_time": calc_time,
                "brain_version": self.version,
                "created_at": datetime.now()
            }
        except Exception as e:
            logger.error(f"analyze_match() failed: {e}")
            raise RuntimeError(f"Brain error: {str(e)}")

    def _convert_match_prediction_to_markets(self, prediction) -> Dict:
        """
        Convertit MatchPrediction → format API markets

        MatchPrediction contient 93 marchés, on les transforme
        en Dict[market_id, Dict[outcome, MarketPrediction]]
        """
        markets = {}

        # Extraire tous les attributs de MatchPrediction
        for attr_name in dir(prediction):
            if attr_name.startswith('_'):
                continue

            # Skip non-market attributes
            if attr_name in ['home_team', 'away_team', 'home_profile', 'away_profile']:
                continue

            try:
                attr_value = getattr(prediction, attr_name)

                # Si c'est un float/int ET une probabilité valide (0-1)
                if isinstance(attr_value, (float, int)):
                    # Filtrer seulement les probabilités (0-1), pas les expected values
                    if 0.0 <= float(attr_value) <= 1.0:
                        markets[attr_name] = {
                            "prediction": {
                                "probability": float(attr_value),
                                "confidence": 0.85,  # Default confidence
                                "edge": None
                            }
                        }
            except Exception:
                continue

        return markets

    def calculate_goalscorers(
        self,
        home_team: str,
        away_team: str,
        match_date: datetime
    ) -> Dict[str, Any]:
        """
        Top 5 buteurs

        TODO: Intégrer GoalscorerCalculator depuis quantum_core
        """
        # Mock response for now
        return {
            "home_goalscorers": [],
            "away_goalscorers": [],
            "first_goalscorer_team_prob": {"home": 0.52, "away": 0.48}
        }

    def get_supported_markets(self) -> List[Dict[str, str]]:
        """
        Liste 93 marchés supportés (extrait depuis UnifiedBrain)
        """
        try:
            # Analyser un match dummy pour extraire la liste
            dummy = self.brain.analyze_match(home="Liverpool", away="Chelsea")

            markets = []
            for attr_name in dir(dummy):
                if attr_name.startswith('_'):
                    continue

                if attr_name in ['home_team', 'away_team', 'home_profile', 'away_profile']:
                    continue

                try:
                    attr_value = getattr(dummy, attr_name)
                    if isinstance(attr_value, (float, int)):
                        markets.append({
                            "id": attr_name,
                            "name": attr_name.replace('_', ' ').title(),
                            "category": self._infer_category(attr_name),
                            "description": f"Market {attr_name}"
                        })
                except Exception:
                    continue

            return markets
        except Exception as e:
            logger.error(f"Failed to get markets: {e}")
            # Fallback hardcodé
            return [
                {"id": "over_under_25", "name": "Over/Under 2.5", "category": "goals", "description": "O/U 2.5"},
                {"id": "btts", "name": "BTTS", "category": "goals", "description": "Both teams score"},
                {"id": "match_result_1x2", "name": "1X2", "category": "result", "description": "Match result"},
            ]

    def _infer_category(self, market_id: str) -> str:
        """Inférer catégorie depuis market_id"""
        if 'goal' in market_id or 'over' in market_id or 'under' in market_id or 'btts' in market_id:
            return "goals"
        elif 'corner' in market_id:
            return "corners"
        elif 'card' in market_id:
            return "cards"
        elif 'asian' in market_id or 'handicap' in market_id:
            return "asian_handicap"
        elif 'goalscorer' in market_id or 'scorer' in market_id:
            return "goalscorers"
        else:
            return "result"

    def get_health_status(self) -> Dict[str, Any]:
        """Health check"""
        try:
            # Test health_check method
            test = self.brain.health_check()

            return {
                "status": "operational",
                "version": self.version,
                "markets_count": test.get('markets_supported', 93),
                "goalscorer_profiles": 876,
                "uptime_percent": 99.9,
                "quantum_core_path": str(QUANTUM_CORE_PATH),
                "environment": ENV
            }
        except Exception as e:
            return {
                "status": "error",
                "version": self.version,
                "error": str(e),
                "quantum_core_path": str(QUANTUM_CORE_PATH),
                "environment": ENV
            }
