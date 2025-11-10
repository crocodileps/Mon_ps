"""
Service de logging structuré pour Mon_PS
Logs JSON en production, colorés en dev
"""
import logging

import structlog

from api.config import settings


def configure_logging():
    """Configure le système de logging structuré"""

    if settings.ENV == "production":
        log_level = logging.INFO
        renderer = structlog.processors.JSONRenderer()
    elif settings.ENV == "development":
        log_level = logging.DEBUG
        renderer = structlog.dev.ConsoleRenderer()
    else:
        log_level = logging.WARNING
        renderer = structlog.processors.JSONRenderer()

    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            renderer,
        ],
        wrapper_class=structlog.make_filtering_bound_logger(log_level),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )


logger = structlog.get_logger()
