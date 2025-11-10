"""
Service de logging structuré pour Mon_PS
Logs JSON en production, colorés en dev
"""
import structlog
import logging
import sys
from api.config import settings

def configure_logging():
    """Configure le système de logging structuré"""
    
    # Choisir le renderer selon l'environnement
    if settings.ENV == "production":
        # Production: JSON structuré
        renderer = structlog.processors.JSONRenderer()
    else:
        # Dev: Console colorée
        renderer = structlog.dev.ConsoleRenderer()
    
    # Configuration de structlog
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            renderer,
        ],
        wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )
    
    # Configuration du logging standard Python
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=logging.INFO,
    )

# Logger global
logger = structlog.get_logger()
