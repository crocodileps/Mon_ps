#!/usr/bin/env python3
"""
Mon_PS Institutional Guardian - Self-Healing Actions
Automatic remediation for common issues
"""

import subprocess
import time
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, Tuple, List

sys.path.insert(0, str(Path(__file__).parent.parent))

from config.settings import (
    SELF_HEALING,
    CRON_JOBS,
    DOCKER_CONTAINERS,
    LOGS_DIR,
    BASE_DIR
)


class SelfHealer:
    """Automatic remediation for detected issues."""

    def __init__(self):
        self.config = SELF_HEALING
        self.actions_log: List[Dict] = []

    def _log_action(self, action: str, target: str, success: bool, message: str):
        """Log a self-healing action."""
        self.actions_log.append({
            "timestamp": datetime.now().isoformat(),
            "action": action,
            "target": target,
            "success": success,
            "message": message
        })

    def _run_command(self, cmd: str, timeout: int = 60) -> Tuple[bool, str]:
        """Run a shell command."""
        try:
            result = subprocess.run(
                cmd,
                shell=True,
                capture_output=True,
                text=True,
                timeout=timeout
            )
            return result.returncode == 0, result.stdout + result.stderr
        except subprocess.TimeoutExpired:
            return False, f"Timeout after {timeout}s"
        except Exception as e:
            return False, str(e)

    def restart_container(self, container_name: str) -> Tuple[bool, str]:
        """
        Restart a Docker container.

        Returns:
            Tuple of (success, message)
        """
        if not self.config["actions_enabled"].get("restart_container", False):
            return False, "Container restart disabled in config"

        if container_name not in DOCKER_CONTAINERS:
            return False, f"Unknown container: {container_name}"

        if not DOCKER_CONTAINERS[container_name].get("auto_restart", False):
            return False, f"Auto-restart disabled for {container_name}"

        # Try to restart
        success, output = self._run_command(f"docker restart {container_name}")

        if success:
            # Wait a bit and verify
            time.sleep(5)
            verify_success, verify_output = self._run_command(
                f"docker inspect -f '{{{{.State.Running}}}}' {container_name}"
            )

            if verify_success and "true" in verify_output.lower():
                message = f"Container {container_name} restarted successfully"
                self._log_action("restart_container", container_name, True, message)
                return True, message

        message = f"Failed to restart {container_name}: {output}"
        self._log_action("restart_container", container_name, False, message)
        return False, message

    def rerun_cron_job(self, job_id: str) -> Tuple[bool, str]:
        """
        Manually run a cron job that failed.

        Returns:
            Tuple of (success, message)
        """
        if not self.config["actions_enabled"].get("rerun_cron", False):
            return False, "Cron rerun disabled in config"

        if job_id not in CRON_JOBS:
            return False, f"Unknown cron job: {job_id}"

        job = CRON_JOBS[job_id]
        script_path = job.get("script_path")

        if not script_path or not Path(script_path).exists():
            return False, f"Script not found: {script_path}"

        max_retries = self.config.get("max_retry_attempts", 2)
        retry_delay = self.config.get("retry_delay_seconds", 60)

        for attempt in range(1, max_retries + 1):
            success, output = self._run_command(
                f"cd {BASE_DIR} && python3 {script_path}",
                timeout=300
            )

            if success:
                message = f"Cron job {job_id} completed successfully (attempt {attempt})"
                self._log_action("rerun_cron", job_id, True, message)
                return True, message

            if attempt < max_retries:
                time.sleep(retry_delay)

        message = f"Cron job {job_id} failed after {max_retries} attempts: {output[:200]}"
        self._log_action("rerun_cron", job_id, False, message)
        return False, message

    def cleanup_disk(self) -> Tuple[bool, str]:
        """
        Clean up disk space by compressing/removing old logs.

        Returns:
            Tuple of (success, message)
        """
        if not self.config["actions_enabled"].get("cleanup_disk", False):
            return False, "Disk cleanup disabled in config"

        cleanup_config = self.config.get("cleanup_config", {})
        compress_days = cleanup_config.get("compress_older_than_days", 3)
        delete_days = cleanup_config.get("logs_older_than_days", 7)

        actions_taken = []

        # Compress old logs
        compress_cmd = (
            f"find {LOGS_DIR} -name '*.log' -mtime +{compress_days} "
            f"-exec gzip -v {{}} \\; 2>&1"
        )
        success, output = self._run_command(compress_cmd)
        if "compressed" in output.lower():
            actions_taken.append(f"Compressed logs older than {compress_days} days")

        # Delete very old compressed logs
        delete_cmd = (
            f"find {LOGS_DIR} -name '*.gz' -mtime +{delete_days} "
            f"-delete -print 2>&1"
        )
        success, output = self._run_command(delete_cmd)
        if output.strip():
            actions_taken.append(f"Deleted archives older than {delete_days} days")

        if actions_taken:
            message = "Cleanup completed: " + "; ".join(actions_taken)
            self._log_action("cleanup_disk", "logs", True, message)
            return True, message
        else:
            message = "No cleanup needed"
            self._log_action("cleanup_disk", "logs", True, message)
            return True, message

    def heal_issue(self, issue_type: str, target: str) -> Tuple[bool, str]:
        """
        Attempt to heal a detected issue.

        Args:
            issue_type: Type of issue (container_down, cron_failed, disk_full)
            target: Specific target (container name, job id, etc.)

        Returns:
            Tuple of (success, message)
        """
        if issue_type == "container_down":
            return self.restart_container(target)
        elif issue_type == "cron_failed":
            return self.rerun_cron_job(target)
        elif issue_type == "disk_full":
            return self.cleanup_disk()
        else:
            return False, f"Unknown issue type: {issue_type}"

    def get_actions_log(self) -> List[Dict]:
        """Get log of all actions taken."""
        return self.actions_log


# Standalone test
if __name__ == "__main__":
    healer = SelfHealer()

    # Test disk cleanup
    success, message = healer.cleanup_disk()
    print(f"Disk cleanup: {message}")

    print("\nActions log:")
    import json
    print(json.dumps(healer.get_actions_log(), indent=2))
