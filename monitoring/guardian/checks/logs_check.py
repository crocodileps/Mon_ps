#!/usr/bin/env python3
"""
Mon_PS Institutional Guardian - Logs Health Check
Monitors log files for errors and anomalies
"""

import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List

sys.path.insert(0, str(Path(__file__).parent.parent))

from config.settings import LOGS_DIR


class LogsChecker:
    """Check log files for errors and issues."""

    def __init__(self):
        self.logs_dir = LOGS_DIR
        self.error_patterns = [
            "ERROR",
            "CRITICAL",
            "FATAL",
            "Exception",
            "Traceback",
            "FAILED",
            "ECHEC",
            "denied",
            "refused"
        ]
        self.warning_patterns = [
            "WARNING",
            "WARN",
            "timeout",
            "retry"
        ]

    def scan_log_for_issues(
        self,
        log_file: Path,
        lines_to_scan: int = 100
    ) -> Dict:
        """
        Scan a log file for error patterns.

        Returns:
            Dictionary with scan results
        """
        result = {
            "file": str(log_file),
            "exists": log_file.exists(),
            "errors": [],
            "warnings": [],
            "scanned_lines": 0,
            "status": "unknown"
        }

        if not log_file.exists():
            result["status"] = "missing"
            return result

        try:
            with open(log_file, "r", errors="ignore") as f:
                lines = f.readlines()[-lines_to_scan:]
                result["scanned_lines"] = len(lines)

                for line in lines:
                    line_lower = line.lower()

                    # Check for errors
                    for pattern in self.error_patterns:
                        if pattern.lower() in line_lower:
                            result["errors"].append({
                                "pattern": pattern,
                                "line": line.strip()[:150]
                            })
                            break

                    # Check for warnings
                    for pattern in self.warning_patterns:
                        if pattern.lower() in line_lower:
                            result["warnings"].append({
                                "pattern": pattern,
                                "line": line.strip()[:150]
                            })
                            break

            # Determine status
            if result["errors"]:
                result["status"] = "errors_found"
            elif result["warnings"]:
                result["status"] = "warnings_found"
            else:
                result["status"] = "clean"

        except Exception as e:
            result["status"] = "read_error"
            result["error"] = str(e)

        return result

    def check_alerts_log(self) -> Dict:
        """
        Specifically check the alerts.log file.

        Returns:
            Dictionary with alerts status
        """
        alerts_file = self.logs_dir / "alerts.log"

        result = {
            "file": str(alerts_file),
            "exists": alerts_file.exists(),
            "has_alerts": False,
            "recent_alerts": [],
            "status": "ok"
        }

        if not alerts_file.exists():
            return result

        try:
            with open(alerts_file, "r") as f:
                content = f.read().strip()

            if content:
                result["has_alerts"] = True
                result["status"] = "alerts_present"

                # Get last 5 alerts
                lines = content.split("\n")
                result["recent_alerts"] = lines[-5:]
        except Exception as e:
            result["status"] = "read_error"
            result["error"] = str(e)

        return result

    def check_all_logs(self) -> Dict:
        """
        Check all log files in the logs directory.

        Returns:
            Dictionary with results for all logs
        """
        results = {
            "timestamp": datetime.now().isoformat(),
            "all_clean": True,
            "logs_with_errors": [],
            "logs_with_warnings": [],
            "logs": {}
        }

        # Check standard log files
        log_files = [
            "fbref.log",
            "fbref_db.log",
            "understat_main.log",
            "football_data.log",
            "alerts.log",
            "guardian.log"
        ]

        for log_name in log_files:
            log_path = self.logs_dir / log_name

            if log_name == "alerts.log":
                scan_result = self.check_alerts_log()
            else:
                scan_result = self.scan_log_for_issues(log_path)

            results["logs"][log_name] = scan_result

            if scan_result["status"] == "errors_found":
                results["logs_with_errors"].append(log_name)
                results["all_clean"] = False
            elif scan_result["status"] in ["warnings_found", "alerts_present"]:
                results["logs_with_warnings"].append(log_name)

        return results


# Standalone test
if __name__ == "__main__":
    checker = LogsChecker()
    results = checker.check_all_logs()

    import json
    print(json.dumps(results, indent=2, default=str))
