#!/usr/bin/env python3
"""
Mon_PS Institutional Guardian - Database Health Check
Verifies database connectivity, data freshness, and integrity
"""

import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, Tuple, Optional

sys.path.insert(0, str(Path(__file__).parent.parent))

from config.settings import DB_DOCKER_CMD, DATA_FRESHNESS


class DatabaseChecker:
    """Check health of PostgreSQL database."""

    def __init__(self):
        self.docker_cmd = DB_DOCKER_CMD
        self.data_freshness = DATA_FRESHNESS

    def _run_query(self, query: str) -> Tuple[bool, str]:
        """
        Run a SQL query via docker exec.

        Returns:
            Tuple of (success, output)
        """
        try:
            cmd = f'{self.docker_cmd} -t -c "{query}"'
            result = subprocess.run(
                cmd,
                shell=True,
                capture_output=True,
                text=True,
                timeout=30
            )

            if result.returncode == 0:
                return True, result.stdout.strip()
            else:
                return False, result.stderr.strip()

        except subprocess.TimeoutExpired:
            return False, "Query timeout (30s)"
        except Exception as e:
            return False, str(e)

    def check_connection(self) -> Tuple[bool, str]:
        """Check if database is accessible."""
        success, output = self._run_query("SELECT 1 as ping;")

        if success and "1" in output:
            return True, "Database connection OK"
        else:
            return False, f"Database connection FAILED: {output}"

    def check_data_freshness(self, table_config: Dict) -> Dict:
        """
        Check if data in a table is fresh enough.

        Args:
            table_config: Configuration dict for the table

        Returns:
            Dictionary with check results
        """
        table = table_config["table"]
        ts_column = table_config["timestamp_column"]
        max_age = table_config["max_age_hours"]

        result = {
            "table": table,
            "passed": False,
            "checks": {}
        }

        # Check 1: Get row count
        success, output = self._run_query(f"SELECT COUNT(*) FROM {table};")
        if success:
            try:
                # Parse output - handle different formats
                lines = [l.strip() for l in output.split("\n") if l.strip() and not l.strip().startswith("-")]
                if len(lines) >= 2:
                    count = int(lines[1].strip())
                else:
                    count = int(lines[0].strip())
                result["checks"]["row_count"] = {
                    "value": count,
                    "passed": table_config.get("min_rows", 0) <= count <= table_config.get("max_rows", float('inf')),
                    "message": f"{count} rows"
                }
            except Exception as e:
                result["checks"]["row_count"] = {"passed": False, "message": f"Could not parse count: {output} - {e}"}
        else:
            result["checks"]["row_count"] = {"passed": False, "message": output}

        # Check 2: Get last update time
        success, output = self._run_query(
            f"SELECT MAX({ts_column}), NOW(), "
            f"EXTRACT(EPOCH FROM (NOW() - MAX({ts_column})))/3600 as age_hours "
            f"FROM {table};"
        )

        if success:
            try:
                lines = [l.strip() for l in output.split("\n") if l.strip() and not l.startswith("-") and not l.startswith("max")]
                # Find the data line (contains pipe separators)
                for line in lines:
                    if "|" in line:
                        parts = [p.strip() for p in line.split("|")]
                        if len(parts) >= 3:
                            age_hours = float(parts[2])
                            result["checks"]["freshness"] = {
                                "value": age_hours,
                                "max_allowed": max_age,
                                "passed": age_hours <= max_age,
                                "message": f"Data age: {age_hours:.1f}h (max: {max_age}h)"
                            }
                            break
                if "freshness" not in result["checks"]:
                    result["checks"]["freshness"] = {"passed": False, "message": f"Parse error: {output}"}
            except Exception as e:
                result["checks"]["freshness"] = {"passed": False, "message": str(e)}
        else:
            result["checks"]["freshness"] = {"passed": False, "message": output}

        # Overall result
        result["passed"] = all(
            check.get("passed", False)
            for check in result["checks"].values()
        )

        return result

    def check_all(self) -> Dict:
        """
        Run all database health checks.

        Returns:
            Dictionary with all check results
        """
        results = {
            "timestamp": datetime.now().isoformat(),
            "all_healthy": True,
            "checks": {}
        }

        # Check connection
        conn_ok, conn_msg = self.check_connection()
        results["checks"]["connection"] = {
            "passed": conn_ok,
            "message": conn_msg
        }

        if not conn_ok:
            results["all_healthy"] = False
            return results

        # Check each configured table
        for table_id, table_config in self.data_freshness.items():
            table_result = self.check_data_freshness(table_config)
            results["checks"][table_id] = table_result

            if not table_result["passed"]:
                results["all_healthy"] = False

        return results

    def get_row_count(self, table: str) -> Optional[int]:
        """Get current row count for a table."""
        success, output = self._run_query(f"SELECT COUNT(*) FROM {table};")
        if success:
            try:
                lines = [l.strip() for l in output.split("\n") if l.strip() and not l.strip().startswith("-")]
                if len(lines) >= 2:
                    return int(lines[1].strip())
                return int(lines[0].strip())
            except:
                pass
        return None

    def get_data_age_hours(self, table: str, ts_column: str = "updated_at") -> Optional[float]:
        """Get age of most recent data in hours."""
        success, output = self._run_query(
            f"SELECT EXTRACT(EPOCH FROM (NOW() - MAX({ts_column})))/3600 FROM {table};"
        )
        if success:
            try:
                lines = [l.strip() for l in output.split("\n") if l.strip() and not l.strip().startswith("-")]
                if len(lines) >= 2:
                    return float(lines[1].strip())
                return float(lines[0].strip())
            except:
                pass
        return None


# Standalone test
if __name__ == "__main__":
    checker = DatabaseChecker()
    results = checker.check_all()

    import json
    print(json.dumps(results, indent=2, default=str))
