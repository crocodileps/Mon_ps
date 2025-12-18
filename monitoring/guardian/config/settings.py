#!/usr/bin/env python3
"""
Mon_PS Institutional Guardian - Configuration Settings
Hedge Fund Grade Monitoring System
"""

import os
from pathlib import Path
from datetime import timedelta

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
        "script_path": SCRIPTS_DIR / "scrape_fbref_complete_2025_26.py",
        "critical": True
    },
    "fbref_pipeline": {
        "name": "FBRef JSON to DB Pipeline",
        "schedule": "15 6 * * *",
        "log_file": LOGS_DIR / "fbref_db.log",
        "max_age_hours": 48,
        "script_path": BASE_DIR / "backend/scripts/data_enrichment/fbref_json_to_db.py",
        "critical": True
    },
    "understat_main": {
        "name": "Understat Main Scraper",
        "schedule": "0 6,18 * * *",
        "log_file": LOGS_DIR / "understat_main.log",
        "max_age_hours": 24,
        "script_path": BASE_DIR / "backend/scripts/data_enrichment/understat_all_leagues_scraper.py",
        "critical": False
    },
    "football_data": {
        "name": "Football-Data Results",
        "schedule": "0 3,9,15,21 * * *",
        "log_file": LOGS_DIR / "football_data.log",
        "max_age_hours": 12,
        "script_path": BASE_DIR / "backend/scripts/data_enrichment/fetch_results_football_data_v2.py",
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
