#!/usr/bin/env python3
"""
Mon_PS Institutional Guardian v1.0
Hedge Fund Grade Health Check & Self-Healing System

Author: Mon_PS Team
Version: 1.0.0
"""

import os
import sys
import json
import argparse
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import Dict, List

# Load environment variables from .env
env_file = Path(__file__).parent / ".env"
if env_file.exists():
    with open(env_file) as f:
        for line in f:
            if "=" in line and not line.strip().startswith("#"):
                key, value = line.strip().split("=", 1)
                os.environ[key] = value

# Add guardian directory to path
sys.path.insert(0, str(Path(__file__).parent))

from config.settings import (
    GUARDIAN_LOG_FILE,
    HEALTHCHECK_PING_URL,
    LOGS_DIR
)
from checks.cron_check import CronChecker
from checks.database_check import DatabaseChecker
from checks.docker_check import DockerChecker
from checks.disk_check import DiskChecker
from checks.logs_check import LogsChecker
from actions.self_healing import SelfHealer
from notifications.telegram import TelegramNotifier


class InstitutionalGuardian:
    """
    Main orchestrator for the health check system.

    Coordinates all checks, self-healing actions, and notifications.
    """

    VERSION = "1.0.0"

    def __init__(self, dry_run: bool = False, verbose: bool = False):
        self.dry_run = dry_run
        self.verbose = verbose
        self.start_time = datetime.now()

        # Initialize components
        self.cron_checker = CronChecker()
        self.db_checker = DatabaseChecker()
        self.docker_checker = DockerChecker()
        self.disk_checker = DiskChecker()
        self.logs_checker = LogsChecker()
        self.healer = SelfHealer()
        self.notifier = TelegramNotifier()

        # Results storage
        self.results: Dict = {
            "version": self.VERSION,
            "timestamp": self.start_time.isoformat(),
            "dry_run": dry_run,
            "checks": {},
            "healing_actions": [],
            "overall_status": "unknown"
        }

    def log(self, message: str, level: str = "INFO"):
        """Log a message."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_line = f"[{timestamp}] [{level}] {message}"

        if self.verbose:
            print(log_line)

        try:
            LOGS_DIR.mkdir(parents=True, exist_ok=True)
            with open(GUARDIAN_LOG_FILE, "a") as f:
                f.write(log_line + "\n")
        except Exception:
            pass

    def run_all_checks(self) -> Dict:
        """Run all health checks."""
        self.log("Starting health checks...")

        # Check 1: Docker containers (check first - DB depends on it)
        self.log("Checking Docker containers...")
        docker_results = self.docker_checker.check_all_containers()
        self.results["checks"]["docker"] = {
            "passed": docker_results["all_healthy"],
            "details": docker_results
        }

        # Check 2: Database
        self.log("Checking database...")
        db_results = self.db_checker.check_all()
        self.results["checks"]["database"] = {
            "passed": db_results["all_healthy"],
            "details": db_results
        }

        # Check 3: Cron jobs
        self.log("Checking cron jobs...")
        cron_results = self.cron_checker.check_all_crons()
        self.results["checks"]["cron"] = {
            "passed": cron_results["all_healthy"],
            "details": cron_results
        }

        # Check 4: Disk space
        self.log("Checking disk space...")
        disk_results = self.disk_checker.check_all_paths()
        self.results["checks"]["disk"] = {
            "passed": disk_results["all_healthy"],
            "details": disk_results
        }

        # Check 5: Logs
        self.log("Checking log files...")
        logs_results = self.logs_checker.check_all_logs()
        self.results["checks"]["logs"] = {
            "passed": logs_results["all_clean"],
            "details": logs_results
        }

        return self.results["checks"]

    def attempt_self_healing(self) -> List:
        """Attempt to fix detected issues."""
        actions = []

        if self.dry_run:
            self.log("Dry run mode - skipping self-healing")
            return actions

        # Heal Docker containers
        docker_check = self.results["checks"].get("docker", {})
        if not docker_check.get("passed"):
            details = docker_check.get("details", {})
            for container in details.get("critical_down", []):
                self.log(f"Attempting to restart container: {container}")
                success, message = self.healer.restart_container(container)
                actions.append({
                    "type": "container_restart",
                    "target": container,
                    "success": success,
                    "message": message
                })

        # Clean up disk if needed
        disk_check = self.results["checks"].get("disk", {})
        if not disk_check.get("passed"):
            details = disk_check.get("details", {})
            if details.get("critical_paths"):
                self.log("Attempting disk cleanup...")
                success, message = self.healer.cleanup_disk()
                actions.append({
                    "type": "disk_cleanup",
                    "target": "logs",
                    "success": success,
                    "message": message
                })

        self.results["healing_actions"] = actions
        return actions

    def determine_overall_status(self) -> str:
        """Determine the overall system health status."""
        all_passed = all(
            check.get("passed", False)
            for check in self.results["checks"].values()
        )

        # Check if healing was successful
        healing_success = all(
            action.get("success", False)
            for action in self.results.get("healing_actions", [])
        )

        if all_passed:
            status = "HEALTHY"
        elif healing_success and self.results.get("healing_actions"):
            status = "RECOVERED"
        else:
            # Check if any critical checks failed
            critical_checks = ["database", "docker"]
            critical_failed = any(
                not self.results["checks"].get(c, {}).get("passed", True)
                for c in critical_checks
            )
            status = "CRITICAL" if critical_failed else "DEGRADED"

        self.results["overall_status"] = status
        return status

    def send_notifications(self):
        """Send appropriate notifications based on results."""
        status = self.results["overall_status"]

        if status == "HEALTHY":
            # Only send daily summary in verbose mode
            if self.verbose:
                self.notifier.send_success("Daily health check passed. All systems operational.")

        elif status == "RECOVERED":
            # Send recovery notification
            actions_summary = "\n".join([
                f"* {a['type']}: {a['target']} - {'OK' if a['success'] else 'FAILED'}"
                for a in self.results["healing_actions"]
            ])
            self.notifier.send_recovery(
                f"System auto-recovered!\n\n*Actions taken:*\n{actions_summary}"
            )

        else:  # CRITICAL or DEGRADED
            # Send alert with details
            failed_checks = [
                name for name, result in self.results["checks"].items()
                if not result.get("passed")
            ]

            message = f"*Failed checks:* {', '.join(failed_checks)}\n\n"

            # Add details for each failed check
            for check_name in failed_checks[:3]:
                check = self.results["checks"][check_name]
                details = check.get("details", {})

                if check_name == "cron":
                    failures = details.get('critical_failures', [])
                    message += f"*Cron:* {failures}\n"
                elif check_name == "docker":
                    down = details.get('critical_down', [])
                    message += f"*Docker:* {down}\n"
                elif check_name == "database":
                    message += "*Database:* Connection or freshness issue\n"
                elif check_name == "disk":
                    paths = details.get('critical_paths', [])
                    message += f"*Disk:* {paths}\n"

            if status == "CRITICAL":
                self.notifier.send_critical(message)
            else:
                self.notifier.send_warning(message)

    def ping_healthcheck(self):
        """Send heartbeat to external monitoring service."""
        if not HEALTHCHECK_PING_URL:
            self.log("Healthcheck URL not configured, skipping ping")
            return

        try:
            # Append status to URL
            status = self.results["overall_status"]
            url = HEALTHCHECK_PING_URL

            if status not in ["HEALTHY", "RECOVERED"]:
                url += "/fail"

            urllib.request.urlopen(url, timeout=10)
            self.log(f"Healthcheck ping sent: {status}")
        except Exception as e:
            self.log(f"Failed to send healthcheck ping: {e}", "WARNING")

    def save_report(self) -> Path:
        """Save detailed report to file."""
        report_dir = LOGS_DIR / "guardian_reports"
        report_dir.mkdir(parents=True, exist_ok=True)

        timestamp = self.start_time.strftime("%Y%m%d_%H%M%S")
        report_file = report_dir / f"health_report_{timestamp}.json"

        # Add timing info
        self.results["duration_seconds"] = (
            datetime.now() - self.start_time
        ).total_seconds()

        with open(report_file, "w") as f:
            json.dump(self.results, f, indent=2, default=str)

        self.log(f"Report saved: {report_file}")
        return report_file

    def run(self) -> Dict:
        """
        Run the complete health check cycle.

        Returns:
            Dictionary with all results
        """
        self.log("=" * 60)
        self.log(f"INSTITUTIONAL GUARDIAN v{self.VERSION} - Starting")
        self.log("=" * 60)

        status = "ERROR"

        try:
            # Step 1: Run all checks
            self.run_all_checks()

            # Step 2: Attempt self-healing for failures
            if not self.dry_run:
                self.attempt_self_healing()

            # Step 3: Determine overall status
            status = self.determine_overall_status()
            self.log(f"Overall status: {status}")

            # Step 4: Send notifications
            if not self.dry_run:
                self.send_notifications()

            # Step 5: Ping external healthcheck
            if not self.dry_run:
                self.ping_healthcheck()

            # Step 6: Save report
            self.save_report()

        except Exception as e:
            self.log(f"Guardian error: {e}", "ERROR")
            self.results["error"] = str(e)
            self.results["overall_status"] = "ERROR"

            if not self.dry_run:
                self.notifier.send_critical(f"Guardian crashed: {e}")

        self.log("=" * 60)
        self.log(f"INSTITUTIONAL GUARDIAN - Complete ({status})")
        self.log("=" * 60)

        return self.results


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Mon_PS Institutional Guardian - Health Check System"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Run checks without taking actions or sending alerts"
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Print detailed output"
    )
    parser.add_argument(
        "--test-telegram",
        action="store_true",
        help="Send a test message to Telegram"
    )

    args = parser.parse_args()

    if args.test_telegram:
        notifier = TelegramNotifier()
        if notifier.is_configured():
            success = notifier.test_connection()
            print(f"Telegram test: {'SUCCESS' if success else 'FAILED'}")
        else:
            print("Telegram not configured. Set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID in .env")
        return

    guardian = InstitutionalGuardian(
        dry_run=args.dry_run,
        verbose=args.verbose
    )

    results = guardian.run()

    if args.verbose:
        print("\n" + "=" * 60)
        print("RESULTS SUMMARY")
        print("=" * 60)
        print(json.dumps(results, indent=2, default=str))

    # Exit code based on status
    status = results.get("overall_status", "ERROR")
    exit_codes = {
        "HEALTHY": 0,
        "RECOVERED": 0,
        "DEGRADED": 1,
        "CRITICAL": 2,
        "ERROR": 3
    }
    sys.exit(exit_codes.get(status, 3))


if __name__ == "__main__":
    main()
