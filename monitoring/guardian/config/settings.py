#!/usr/bin/env python3
"""
Mon_PS Institutional Guardian - Configuration Settings
Hedge Fund Grade Monitoring System
"""

import os
from pathlib import Path
from datetime import timedelta
from dotenv import load_dotenv

# Load .env file from guardian directory
_env_file = Path(__file__).parent.parent / ".env"
if _env_file.exists():
    load_dotenv(_env_file)

# =============================================================================
# PATHS
# =============================================================================
BASE_DIR = Path("/home/Mon_ps")
GUARDIAN_DIR = BASE_DIR / "monitoring" / "guardian"
LOGS_DIR = BASE_DIR / "logs"
DATA_DIR = BASE_DIR / "data"
SCRIPTS_DIR = BASE_DIR / "scripts"

# =============================================================================
# DATABASE
# =============================================================================
DB_CONFIG = {
    "host": "monps_postgres",
    "port": 5432,
    "user": "monps_user",
    "password": "monps_secure_password_2024",
    "database": "monps_db"
}

# Docker command prefix for DB access
DB_DOCKER_CMD = "docker exec monps_postgres psql -U monps_user -d monps_db"

# =============================================================================
# TELEGRAM (loaded from .env)
# =============================================================================
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

# =============================================================================
# HEALTHCHECKS.IO (Dead Man's Switch)
# =============================================================================
HEALTHCHECK_PING_URL = os.getenv("HEALTHCHECK_PING_URL", "")

# =============================================================================
# MONITORED CRONS
# =============================================================================
CRON_JOBS = {
    "fbref_scraper": {
        "name": "FBRef Scraper",
        "schedule": "0 6 * * *",
        "log_file": LOGS_DIR / "fbref.log",
        "max_age_hours": 48,
        "success_max_age_hours": 26,  # 24h interval + 2h margin
        "script_path": SCRIPTS_DIR / "scrape_fbref_complete_2025_26.py",
        "critical": True
    },
    "fbref_pipeline": {
        "name": "FBRef JSON to DB Pipeline",
        "schedule": "15 6 * * *",
        "log_file": LOGS_DIR / "fbref_db.log",
        "max_age_hours": 48,
        "success_max_age_hours": 26,  # 24h interval + 2h margin
        "script_path": BASE_DIR / "backend/scripts/data_enrichment/fbref_json_to_db.py",
        "critical": True
    },
    "understat_main": {
        "name": "Understat Main Scraper",
        "schedule": "0 6,18 * * *",
        "log_file": LOGS_DIR / "understat_main.log",
        "max_age_hours": 24,
        "success_max_age_hours": 14,  # 12h interval + 2h margin
        "script_path": BASE_DIR / "backend/scripts/data_enrichment/understat_all_leagues_scraper.py",
        "critical": False
    },
    "football_data": {
        "name": "Football-Data Results",
        "schedule": "0 3,9,15,21 * * *",
        "log_file": LOGS_DIR / "football_data.log",
        "max_age_hours": 12,
        "success_max_age_hours": 8,   # 6h interval + 2h margin
        "script_path": BASE_DIR / "backend/scripts/fetch_results_football_data_v2.py",
        "critical": False
    }
}

# =============================================================================
# DOCKER CONTAINERS
# =============================================================================
DOCKER_CONTAINERS = {
    "monps_postgres": {"critical": True, "auto_restart": True},
    "monps_backend": {"critical": True, "auto_restart": True},
    "monps_redis": {"critical": True, "auto_restart": True},
    "monps_frontend": {"critical": False, "auto_restart": True},
    "monps_grafana": {"critical": False, "auto_restart": True},
    "monps_prometheus": {"critical": False, "auto_restart": True}
}

# =============================================================================
# DISK THRESHOLDS
# =============================================================================
DISK_THRESHOLDS = {
    "warning_percent": 80,
    "critical_percent": 90,
    "paths_to_check": ["/", "/home/Mon_ps"]
}

# =============================================================================
# DATABASE FRESHNESS
# =============================================================================
DATA_FRESHNESS = {
    "fbref_player_stats_full": {
        "table": "fbref_player_stats_full",
        "timestamp_column": "updated_at",
        "max_age_hours": 48,
        "min_rows": 2000,
        "max_rows": 5000
    }
}

# =============================================================================
# CIRCUIT BREAKER THRESHOLDS
# =============================================================================
CIRCUIT_BREAKER = {
    "fbref_players": {
        "min_count": 2000,
        "max_count": 5000,
        "max_daily_change_percent": 15,
        "required_columns": ["player_name", "team", "league", "goals", "assists"],
        "max_null_percent": 10
    }
}

# =============================================================================
# SELF-HEALING CONFIGURATION
# =============================================================================
SELF_HEALING = {
    "max_retry_attempts": 2,
    "retry_delay_seconds": 60,
    "actions_enabled": {
        "restart_container": True,
        "rerun_cron": True,
        "cleanup_disk": True
    },
    "cleanup_config": {
        "logs_older_than_days": 7,
        "compress_older_than_days": 3
    }
}

# =============================================================================
# ALERT CONFIGURATION
# =============================================================================
ALERT_CONFIG = {
    "cooldown_minutes": 30,
    "batch_alerts": True,
    "include_timestamp": True,
    "include_hostname": True
}

# =============================================================================
# LOGGING
# =============================================================================
GUARDIAN_LOG_FILE = LOGS_DIR / "guardian.log"
GUARDIAN_ALERTS_FILE = LOGS_DIR / "guardian_alerts.log"

# =============================================================================
# TOLÉRANCE SÉLECTIVE - HEDGE FUND GRADE
# Configuration centralisée pour maintenance facilitée
# =============================================================================

# Patterns à IGNORER dans les warnings (faux positifs connus)
IGNORE_WARNING_PATTERNS = [
    "FutureWarning",
    "DeprecationWarning",
    "UserWarning",
    "ResourceWarning",
    "SyntaxWarning",
    "Status 403",
    "Status: 403",
    "PendingDeprecationWarning",
    "Overall status: WARNING",
    "Complete (WARNING)",
]

# Patterns à IGNORER dans les erreurs (faux positifs connus)
IGNORE_ERROR_PATTERNS = [
    "non-critical",
    "Overall status:",
    "Complete (",
]

# Patterns CRITIQUES même dans les warnings (vrais problèmes à promouvoir en erreur)
CRITICAL_IN_WARNINGS = [
    "Status 429",
    "Status: 429",
    "Connection refused",
    "Connection reset",
    "failed to fetch",
    "could not connect",
    "authentication failed",
    "permission denied",
    "Timeout exceeded",
    "Max retries exceeded",
]

# Patterns indiquant ZÉRO RÉSULTATS (échec silencieux) - Point 1 amélioré
# Note: Patterns spécifiques pour éviter faux positifs (ex: "Milieux: 0" = OK)
ZERO_RESULTS_PATTERNS = [
    "0 rows saved",
    "0 rows inserted",
    "0 matchs récupérés",
    "0 matchs sauvegardés",
    "0 records saved",
    "saved 0 rows",
    "inserted 0 rows",
    "scraped 0 players",
    "fetched 0 results",
    "no data found",
    "empty result set",
    "no results found",
    "failed to fetch any",
    "could not retrieve",
]

# Patterns de SUCCÈS pour validation positive - Point 1 amélioré
SUCCESS_PATTERNS = [
    "✅",
    "rows saved",
    "rows inserted",
    "matchs récupérés",
    "matchs sauvegardés",
    "records saved",
    "completed successfully",
    "SUCCESS",
    "successfully",
    "xG sauvegardés",
    "équipes trouvées",
    "SCRAPING TERMINE",
    "Total joueurs",
    "Aucun match pending",
    "matchs pending",
    "finished",
    "done",
    "completed",
]

# Configuration scan logs - Point 2
LOG_SCAN_CONFIG = {
    "lines_to_scan": 150,
    "success_max_age_minutes": 120,
}
