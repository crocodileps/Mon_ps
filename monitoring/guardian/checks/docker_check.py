#!/usr/bin/env python3
"""
Mon_PS Institutional Guardian - Docker Containers Health Check
Verifies that required Docker containers are running
"""

import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, Tuple, List

sys.path.insert(0, str(Path(__file__).parent.parent))

from config.settings import DOCKER_CONTAINERS


class DockerChecker:
    """Check health of Docker containers."""

    def __init__(self):
        self.containers = DOCKER_CONTAINERS

    def _run_command(self, cmd: str) -> Tuple[bool, str]:
        """Run a shell command and return result."""
        try:
            result = subprocess.run(
                cmd,
                shell=True,
                capture_output=True,
                text=True,
                timeout=30
            )
            return result.returncode == 0, result.stdout.strip()
        except subprocess.TimeoutExpired:
            return False, "Command timeout"
        except Exception as e:
            return False, str(e)

    def get_container_status(self, container_name: str) -> Dict:
        """
        Get detailed status of a container.

        Returns:
            Dictionary with container status info
        """
        result = {
            "name": container_name,
            "running": False,
            "status": "unknown",
            "health": "unknown",
            "uptime": None
        }

        # Check if running
        success, output = self._run_command(
            f"docker inspect -f '{{{{.State.Running}}}}' {container_name} 2>/dev/null"
        )

        if success and output.lower() == "true":
            result["running"] = True
            result["status"] = "running"

            # Get uptime
            success, output = self._run_command(
                f"docker inspect -f '{{{{.State.StartedAt}}}}' {container_name}"
            )
            if success:
                result["uptime"] = output

            # Get health if available
            success, output = self._run_command(
                f"docker inspect -f '{{{{.State.Health.Status}}}}' {container_name} 2>/dev/null"
            )
            if success and output and output != "<no value>":
                result["health"] = output
        else:
            # Check if container exists but stopped
            success, output = self._run_command(
                f"docker inspect -f '{{{{.State.Status}}}}' {container_name} 2>/dev/null"
            )
            if success:
                result["status"] = output
            else:
                result["status"] = "not found"

        return result

    def check_all_containers(self) -> Dict:
        """
        Check all configured containers.

        Returns:
            Dictionary with results for all containers
        """
        results = {
            "timestamp": datetime.now().isoformat(),
            "all_healthy": True,
            "critical_down": [],
            "non_critical_down": [],
            "containers": {}
        }

        for container_name, config in self.containers.items():
            status = self.get_container_status(container_name)
            status["critical"] = config.get("critical", False)
            status["auto_restart"] = config.get("auto_restart", False)

            results["containers"][container_name] = status

            if not status["running"]:
                if config.get("critical", False):
                    results["critical_down"].append(container_name)
                    results["all_healthy"] = False
                else:
                    results["non_critical_down"].append(container_name)

        return results

    def restart_container(self, container_name: str) -> Tuple[bool, str]:
        """
        Restart a container.

        Returns:
            Tuple of (success, message)
        """
        # First try to start if stopped
        success, output = self._run_command(f"docker start {container_name}")
        if success:
            return True, f"Container {container_name} started"

        # Try restart
        success, output = self._run_command(f"docker restart {container_name}")
        if success:
            return True, f"Container {container_name} restarted"

        return False, f"Failed to restart {container_name}: {output}"

    def get_down_containers(self) -> List[str]:
        """Get list of containers that are not running."""
        results = self.check_all_containers()
        return results["critical_down"] + results["non_critical_down"]


# Standalone test
if __name__ == "__main__":
    checker = DockerChecker()
    results = checker.check_all_containers()

    import json
    print(json.dumps(results, indent=2, default=str))
