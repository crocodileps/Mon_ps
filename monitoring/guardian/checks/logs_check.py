#!/usr/bin/env python3
"""
Mon_PS Institutional Guardian - Logs Health Check
Monitors log files for errors and anomalies
HEDGE FUND GRADE - Tolérance Sélective + Métriques
"""

import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List

sys.path.insert(0, str(Path(__file__).parent.parent))

from config.settings import (
    LOGS_DIR,
    IGNORE_WARNING_PATTERNS,
    IGNORE_ERROR_PATTERNS,
    CRITICAL_IN_WARNINGS,
    ZERO_RESULTS_PATTERNS,
    LOG_SCAN_CONFIG,
)


class LogsChecker:
    """Check log files for errors and issues - HEDGE FUND GRADE."""

    def __init__(self):
        self.logs_dir = LOGS_DIR
        self.lines_to_scan = LOG_SCAN_CONFIG.get("lines_to_scan", 150)

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

        # Métriques de filtrage - Point 5
        self.metrics = {
            "filtered_warnings": 0,
            "filtered_errors": 0,
            "promoted_to_error": 0,
            "zero_results_detected": 0,
        }

    def reset_metrics(self):
        """Reset metrics for new scan."""
        for key in self.metrics:
            self.metrics[key] = 0

    def get_metrics(self) -> Dict:
        """Return current filtering metrics."""
        return self.metrics.copy()

    def scan_log_for_issues(
        self,
        log_file: Path,
        lines_to_scan: int = None
    ) -> Dict:
        """
        Scan a log file for error patterns.
        HEDGE FUND GRADE: Tolérance sélective + métriques de filtrage.

        Returns:
            Dictionary with scan results including filtering metrics
        """
        if lines_to_scan is None:
            lines_to_scan = self.lines_to_scan

        result = {
            "file": str(log_file),
            "exists": log_file.exists(),
            "errors": [],
            "warnings": [],
            "scanned_lines": 0,
            "status": "unknown",
            "metrics": {
                "filtered_warnings": 0,
                "filtered_errors": 0,
                "promoted_to_error": 0,
                "zero_results_detected": 0,
            }
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

                    # Check for ZERO RESULTS first (silent failures) - Point 1
                    # Use word boundary matching to avoid "380 matchs" matching "0 matchs"
                    for pattern in ZERO_RESULTS_PATTERNS:
                        # Create regex with word boundary for patterns starting with "0"
                        if pattern.startswith("0 "):
                            # Use word boundary: \b0 matchs\b
                            regex_pattern = r'\b' + re.escape(pattern) + r'\b'
                            if re.search(regex_pattern, line_lower):
                                result["errors"].append({
                                    "pattern": f"ZERO_RESULTS:{pattern}",
                                    "line": line.strip()[:150]
                                })
                                result["metrics"]["zero_results_detected"] += 1
                                self.metrics["zero_results_detected"] += 1
                                break
                        elif pattern.lower() in line_lower:
                            # For non-numeric patterns, simple substring match
                            result["errors"].append({
                                "pattern": f"ZERO_RESULTS:{pattern}",
                                "line": line.strip()[:150]
                            })
                            result["metrics"]["zero_results_detected"] += 1
                            self.metrics["zero_results_detected"] += 1
                            break

                    # Check for errors - with selective tolerance
                    for pattern in self.error_patterns:
                        if pattern.lower() in line_lower:
                            # Check if this is a known false positive
                            is_ignorable = any(
                                ignore_pat.lower() in line_lower
                                for ignore_pat in IGNORE_ERROR_PATTERNS
                            )

                            if is_ignorable:
                                result["metrics"]["filtered_errors"] += 1
                                self.metrics["filtered_errors"] += 1
                            else:
                                result["errors"].append({
                                    "pattern": pattern,
                                    "line": line.strip()[:150]
                                })
                            break

                    # Check for warnings - with selective tolerance
                    for pattern in self.warning_patterns:
                        if pattern.lower() in line_lower:
                            # Check if this is a known false positive
                            is_ignorable = any(
                                ignore_pat.lower() in line_lower
                                for ignore_pat in IGNORE_WARNING_PATTERNS
                            )

                            # Check if this contains critical patterns
                            is_critical = any(
                                crit_pat.lower() in line_lower
                                for crit_pat in CRITICAL_IN_WARNINGS
                            )

                            if is_critical:
                                # Promote to error!
                                result["errors"].append({
                                    "pattern": f"CRITICAL_WARNING:{pattern}",
                                    "line": line.strip()[:150]
                                })
                                result["metrics"]["promoted_to_error"] += 1
                                self.metrics["promoted_to_error"] += 1
                            elif is_ignorable:
                                result["metrics"]["filtered_warnings"] += 1
                                self.metrics["filtered_warnings"] += 1
                            else:
                                # Normal warning, keep it
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
        HEDGE FUND GRADE: Includes filtering metrics.

        Returns:
            Dictionary with results for all logs including global metrics
        """
        # Reset metrics for this scan
        self.reset_metrics()

        results = {
            "timestamp": datetime.now().isoformat(),
            "all_clean": True,
            "logs_with_errors": [],
            "logs_with_warnings": [],
            "logs": {},
            "filtering_metrics": {}
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
            elif scan_result["status"] == "alerts_present":
                results["logs_with_warnings"].append(log_name)
                results["all_clean"] = False
            elif scan_result["status"] == "warnings_found":
                # Warnings don't fail the check, just track them
                results["logs_with_warnings"].append(log_name)

        # Add global filtering metrics - Point 5
        results["filtering_metrics"] = self.get_metrics()

        return results


# Standalone test
if __name__ == "__main__":
    checker = LogsChecker()
    results = checker.check_all_logs()

    import json
    print(json.dumps(results, indent=2, default=str))
