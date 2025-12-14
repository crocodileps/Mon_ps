"""Logging configuration - Structured logging with Loguru.

ADR #006: Observability Framework.
"""

import logging
import sys


def setup_logging(log_level: str = "INFO", log_format: str = "text"):
    """Setup structured logging.

    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR)
        log_format: Format (json, text)

    Note:
        Currently uses Python logging.
        TODO: Migrate to Loguru for better structured logging.
    """
    level = getattr(logging, log_level.upper(), logging.INFO)

    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
    )

    logger = logging.getLogger(__name__)
    logger.info(f"Logging configured - Level: {log_level}, Format: {log_format}")
