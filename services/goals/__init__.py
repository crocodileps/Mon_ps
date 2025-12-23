"""
Goals Ingestion Service - Hedge Fund Grade
Source unique de vérité pour les buts dans PostgreSQL.
"""

from .config import DB_CONFIG, MIN_GOALS_REQUIRED
from .ingestion_service import GoalsIngestionService
from .validator import GoalsValidator
from .legacy_exporter import LegacyExporter

__all__ = [
    "GoalsIngestionService",
    "GoalsValidator", 
    "LegacyExporter",
    "DB_CONFIG",
    "MIN_GOALS_REQUIRED"
]
