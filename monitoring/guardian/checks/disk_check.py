#!/usr/bin/env python3
"""
Mon_PS Institutional Guardian - Disk Space Health Check
Monitors disk usage and alerts on low space
"""

import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List

sys.path.insert(0, str(Path(__file__).parent.parent))

from config.settings import DISK_THRESHOLDS


class DiskChecker:
    """Check disk space usage."""

    def __init__(self):
        self.thresholds = DISK_THRESHOLDS

    def get_disk_usage(self, path: str = "/") -> Dict:
        """
        Get disk usage for a path.

        Returns:
            Dictionary with disk usage info
        """
        result = {
            "path": path,
            "total_gb": 0,
            "used_gb": 0,
            "free_gb": 0,
            "percent_used": 0,
            "status": "unknown"
        }

        try:
            cmd = f"df -BG {path} | tail -1"
            output = subprocess.run(
                cmd,
                shell=True,
                capture_output=True,
                text=True,
                timeout=10
            )

            if output.returncode == 0:
                parts = output.stdout.split()
                if len(parts) >= 5:
                    result["total_gb"] = int(parts[1].replace("G", ""))
                    result["used_gb"] = int(parts[2].replace("G", ""))
                    result["free_gb"] = int(parts[3].replace("G", ""))
                    result["percent_used"] = int(parts[4].replace("%", ""))

                    # Determine status
                    if result["percent_used"] >= self.thresholds["critical_percent"]:
                        result["status"] = "critical"
                    elif result["percent_used"] >= self.thresholds["warning_percent"]:
                        result["status"] = "warning"
                    else:
                        result["status"] = "ok"

        except Exception as e:
            result["error"] = str(e)
            result["status"] = "error"

        return result

    def check_all_paths(self) -> Dict:
        """
        Check disk usage for all configured paths.

        Returns:
            Dictionary with results for all paths
        """
        results = {
            "timestamp": datetime.now().isoformat(),
            "all_healthy": True,
            "critical_paths": [],
            "warning_paths": [],
            "paths": {}
        }

        for path in self.thresholds["paths_to_check"]:
            usage = self.get_disk_usage(path)
            results["paths"][path] = usage

            if usage["status"] == "critical":
                results["critical_paths"].append(path)
                results["all_healthy"] = False
            elif usage["status"] == "warning":
                results["warning_paths"].append(path)

        return results

    def get_cleanup_candidates(self, path: str = "/home/Mon_ps/logs") -> List[Dict]:
        """
        Find large files that could be cleaned up.

        Returns:
            List of files with size info
        """
        candidates = []

        try:
            # Find files > 10MB
            cmd = f"find {path} -type f -size +10M -exec ls -lh {{}} \\; 2>/dev/null | head -20"
            result = subprocess.run(
                cmd,
                shell=True,
                capture_output=True,
                text=True,
                timeout=30
            )

            if result.returncode == 0:
                for line in result.stdout.strip().split("\n"):
                    if line:
                        parts = line.split()
                        if len(parts) >= 9:
                            candidates.append({
                                "path": parts[-1],
                                "size": parts[4],
                                "modified": f"{parts[5]} {parts[6]} {parts[7]}"
                            })
        except Exception:
            pass

        return candidates


# Standalone test
if __name__ == "__main__":
    checker = DiskChecker()
    results = checker.check_all_paths()

    import json
    print(json.dumps(results, indent=2, default=str))

    print("\nCleanup candidates:")
    candidates = checker.get_cleanup_candidates()
    for c in candidates:
        print(f"  {c['size']:>10} {c['path']}")
