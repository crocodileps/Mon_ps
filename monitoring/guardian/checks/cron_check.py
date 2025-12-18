#!/usr/bin/env python3
"""
Mon_PS Institutional Guardian - Cron Jobs Health Check
Verifies that scheduled jobs are running correctly
"""

import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple

sys.path.insert(0, str(Path(__file__).parent.parent))

from config.settings import CRON_JOBS, LOGS_DIR


class CronChecker:
    """Check health of scheduled cron jobs."""

    def __init__(self):
        self.cron_jobs = CRON_JOBS
        self.results: Dict = {}

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

    def check_log_for_errors(self, log_file: Path, lines_to_check: int = 50) -> Tuple[bool, List[str]]:
        """
        Check recent log lines for error patterns.

        Returns:
            Tuple of (has_no_errors, list_of_errors_found)
        """
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
