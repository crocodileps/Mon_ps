#!/usr/bin/env python3
"""
Mon_PS Institutional Guardian - Cron Jobs Health Check
Verifies that scheduled jobs are running correctly
HEDGE FUND GRADE - Validation Positive avec contrôle temporel
"""

import os
import re
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Tuple

sys.path.insert(0, str(Path(__file__).parent.parent))

from config.settings import (
    CRON_JOBS,
    LOGS_DIR,
    SUCCESS_PATTERNS,
    LOG_SCAN_CONFIG,
)


class CronChecker:
    """Check health of scheduled cron jobs - HEDGE FUND GRADE."""

    def __init__(self):
        self.cron_jobs = CRON_JOBS
        self.results: Dict = {}
        self.lines_to_scan = LOG_SCAN_CONFIG.get("lines_to_scan", 150)
        self.success_max_age_minutes = LOG_SCAN_CONFIG.get("success_max_age_minutes", 120)

    def check_log_freshness(self, log_file: Path, max_age_hours: int) -> Tuple[bool, str]:
        """
        Check if a log file has been modified recently.

        Returns:
            Tuple of (is_fresh, message)
        """
        if not log_file.exists():
            return False, f"Log file not found: {log_file}"

        mtime = datetime.fromtimestamp(log_file.stat().st_mtime)
        age = datetime.now() - mtime
        age_hours = age.total_seconds() / 3600

        if age_hours > max_age_hours:
            return False, f"Log stale: {age_hours:.1f}h old (max: {max_age_hours}h)"

        return True, f"Log fresh: {age_hours:.1f}h old"

    def check_log_for_errors(self, log_file: Path, lines_to_check: int = None) -> Tuple[bool, List[str]]:
        """
        Check recent log lines for error patterns.

        Returns:
            Tuple of (has_no_errors, list_of_errors_found)
        """
        if lines_to_check is None:
            lines_to_check = self.lines_to_scan

        error_patterns = [
            "ERROR",
            "CRITICAL",
            "FAILED",
            "Exception",
            "Traceback",
            "ECHEC"
        ]

        if not log_file.exists():
            return True, []

        errors_found = []

        try:
            with open(log_file, "r", errors="ignore") as f:
                lines = f.readlines()[-lines_to_check:]

                for line in lines:
                    for pattern in error_patterns:
                        if pattern in line:
                            errors_found.append(line.strip()[:100])
                            break
        except Exception as e:
            errors_found.append(f"Could not read log: {e}")

        return len(errors_found) == 0, errors_found

    def check_success_confirmation(
        self,
        log_file: Path,
        lines_to_check: int = None,
        max_age_minutes: int = None
    ) -> Tuple[bool, str]:
        """
        Check that the log contains RECENT success indicators (positive validation).
        HEDGE FUND GRADE: Vérifie que le succès est récent (pas contamination historique).

        Point 3: Un succès d'hier ne compte pas pour aujourd'hui!

        Returns:
            Tuple of (has_recent_success_confirmation, message)
        """
        if lines_to_check is None:
            lines_to_check = self.lines_to_scan

        if not log_file.exists():
            return False, "Log file not found - cannot confirm success"

        try:
            with open(log_file, "r", errors="ignore") as f:
                lines = f.readlines()[-lines_to_check:]

            if not lines:
                return False, "Log file empty"

            # Point 3: Extraire le timestamp de la dernière ligne avec succès
            now = datetime.now()
            effective_max_age = max_age_minutes if max_age_minutes else self.success_max_age_minutes
            max_age = timedelta(minutes=effective_max_age)

            found_patterns = []
            recent_success = False
            success_timestamp = None

            # Patterns de timestamp courants dans les logs
            timestamp_patterns = [
                r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})',
                r'(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})',
                r'\[(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\]',
            ]

            # Parcourir les lignes en sens inverse (plus récent d'abord)
            for line in reversed(lines):
                line_lower = line.lower()

                # Chercher patterns de succès
                for pattern in SUCCESS_PATTERNS:
                    if pattern.lower() in line_lower:
                        # Extraire le timestamp de cette ligne
                        line_timestamp = None
                        for ts_pattern in timestamp_patterns:
                            match = re.search(ts_pattern, line)
                            if match:
                                try:
                                    ts_str = match.group(1)
                                    if 'T' in ts_str:
                                        line_timestamp = datetime.fromisoformat(ts_str.replace('Z', ''))
                                    else:
                                        line_timestamp = datetime.strptime(ts_str, "%Y-%m-%d %H:%M:%S")
                                    break
                                except ValueError:
                                    continue

                        # Vérifier si le succès est récent
                        if line_timestamp:
                            age = now - line_timestamp
                            if age <= max_age:
                                found_patterns.append(pattern)
                                recent_success = True
                                if success_timestamp is None or line_timestamp > success_timestamp:
                                    success_timestamp = line_timestamp
                        else:
                            # Pas de timestamp trouvé, on accepte si c'est dans les dernières lignes
                            found_patterns.append(pattern)
                        break

                # Si on a trouvé un succès récent, on peut s'arrêter
                if recent_success and len(found_patterns) >= 3:
                    break

            if found_patterns:
                if recent_success and success_timestamp:
                    age_minutes = (now - success_timestamp).total_seconds() / 60
                    return True, f"Success confirmed ({age_minutes:.0f}min ago): {', '.join(found_patterns[:3])}"
                else:
                    return True, f"Success found (timestamp unverified): {', '.join(found_patterns[:3])}"
            else:
                return False, f"No success confirmation in last {lines_to_check} lines (max age: {effective_max_age}min)"

        except Exception as e:
            return False, f"Could not read log: {e}"

    def check_all_crons(self) -> Dict:
        """
        Check all configured cron jobs.

        Returns:
            Dictionary with results for each cron job
        """
        results = {
            "timestamp": datetime.now().isoformat(),
            "all_healthy": True,
            "critical_failures": [],
            "warnings": [],
            "jobs": {}
        }

        for job_id, job_config in self.cron_jobs.items():
            job_result = {
                "name": job_config["name"],
                "schedule": job_config["schedule"],
                "critical": job_config.get("critical", False),
                "checks": {}
            }

            # Check 1: Log freshness
            log_file = job_config["log_file"]
            max_age = job_config["max_age_hours"]

            is_fresh, freshness_msg = self.check_log_freshness(log_file, max_age)
            job_result["checks"]["log_freshness"] = {
                "passed": is_fresh,
                "message": freshness_msg
            }

            # Check 2: No errors in log
            no_errors, errors = self.check_log_for_errors(log_file)
            job_result["checks"]["no_errors"] = {
                "passed": no_errors,
                "message": f"Found {len(errors)} error(s)" if errors else "No errors",
                "errors": errors[:5]
            }

            # Check 3: Script exists and is executable
            script_path = job_config.get("script_path")
            if script_path:
                script_exists = Path(script_path).exists()
                script_executable = os.access(script_path, os.X_OK) if script_exists else False
                script_readable = os.access(script_path, os.R_OK) if script_exists else False
                job_result["checks"]["script_ready"] = {
                    "passed": script_exists and (script_executable or script_readable),
                    "message": f"Script: {'OK' if script_exists else 'MISSING'}, Accessible: {'YES' if script_executable or script_readable else 'NO'}"
                }

            # Check 4: Success confirmation (positive validation)
            # Only check if log exists and is fresh
            if job_result["checks"]["log_freshness"]["passed"]:
                # Use job-specific max_age if configured, otherwise use global default
                job_success_max_age = job_config.get("success_max_age_hours")
                if job_success_max_age:
                    success_max_age_minutes = job_success_max_age * 60
                else:
                    success_max_age_minutes = self.success_max_age_minutes

                has_success, success_msg = self.check_success_confirmation(
                    log_file,
                    max_age_minutes=success_max_age_minutes
                )
                job_result["checks"]["success_confirmation"] = {
                    "passed": has_success,
                    "message": success_msg
                }

            # Determine overall job health
            job_healthy = all(
                check["passed"]
                for check in job_result["checks"].values()
            )
            job_result["healthy"] = job_healthy

            # Track failures
            if not job_healthy:
                if job_config.get("critical", False):
                    results["critical_failures"].append(job_id)
                    results["all_healthy"] = False
                else:
                    results["warnings"].append(job_id)

            results["jobs"][job_id] = job_result

        return results

    def get_failed_crons(self) -> List[str]:
        """Get list of cron job IDs that have failed."""
        results = self.check_all_crons()
        return results["critical_failures"] + results["warnings"]


# Standalone test
if __name__ == "__main__":
    checker = CronChecker()
    results = checker.check_all_crons()

    import json
    print(json.dumps(results, indent=2, default=str))
