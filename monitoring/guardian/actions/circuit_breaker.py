#!/usr/bin/env python3
"""
Mon_PS Institutional Guardian - Circuit Breaker
Protects database from bad data injection
"""

import json
import shutil
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, Tuple

sys.path.insert(0, str(Path(__file__).parent.parent))

from config.settings import CIRCUIT_BREAKER, DATA_DIR


class DataCircuitBreaker:
    """
    Validates data before database insertion.
    Prevents bad data from corrupting the database.
    """

    def __init__(self):
        self.config = CIRCUIT_BREAKER
        self.history_file = DATA_DIR / ".circuit_breaker_history.json"
        self.history = self._load_history()

    def _load_history(self) -> Dict:
        """Load historical stats for comparison."""
        if self.history_file.exists():
            try:
                with open(self.history_file) as f:
                    return json.load(f)
            except Exception:
                pass
        return {}

    def _save_history(self):
        """Save current stats to history."""
        try:
            self.history_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.history_file, "w") as f:
                json.dump(self.history, f, indent=2, default=str)
        except Exception as e:
            print(f"Warning: Could not save history: {e}")

    def validate_json_file(
        self,
        file_path: Path,
        config_key: str
    ) -> Tuple[bool, str, Dict]:
        """
        Validate a JSON data file before processing.

        Args:
            file_path: Path to the JSON file
            config_key: Key in CIRCUIT_BREAKER config

        Returns:
            Tuple of (is_valid, message, stats)
        """
        if config_key not in self.config:
            return True, f"No validation rules for {config_key}", {}

        rules = self.config[config_key]
        stats: Dict = {}
        issues = []

        # Check file exists
        if not file_path.exists():
            return False, f"File not found: {file_path}", stats

        # Load JSON
        try:
            with open(file_path) as f:
                data = json.load(f)
        except json.JSONDecodeError as e:
            return False, f"Invalid JSON: {e}", stats
        except Exception as e:
            return False, f"Error reading file: {e}", stats

        # Check if data is a list
        if not isinstance(data, list):
            return False, "Data must be a list", stats

        stats["row_count"] = len(data)

        # Rule 1: Check count bounds
        if len(data) < rules.get("min_count", 0):
            issues.append(f"Too few rows: {len(data)} < {rules['min_count']}")

        if len(data) > rules.get("max_count", float('inf')):
            issues.append(f"Too many rows: {len(data)} > {rules['max_count']}")

        # Rule 2: Check daily change
        history_key = f"{config_key}_count"
        if history_key in self.history:
            prev_count = self.history[history_key]
            if prev_count > 0:
                change_pct = abs(len(data) - prev_count) / prev_count * 100
                stats["change_percent"] = change_pct

                max_change = rules.get("max_daily_change_percent", 10)
                if change_pct > max_change:
                    issues.append(
                        f"Daily change too large: {change_pct:.1f}% > {max_change}%"
                    )

        # Rule 3: Check required columns
        if data and rules.get("required_columns"):
            first_row = data[0]
            missing = [
                col for col in rules["required_columns"]
                if col not in first_row
            ]
            if missing:
                issues.append(f"Missing columns: {missing}")

        # Rule 4: Check null percentage
        if data and rules.get("max_null_percent"):
            max_null = rules["max_null_percent"]
            for col in rules.get("required_columns", []):
                null_count = sum(1 for row in data if not row.get(col))
                null_pct = null_count / len(data) * 100

                if null_pct > max_null:
                    issues.append(
                        f"Column '{col}' has {null_pct:.1f}% nulls > {max_null}%"
                    )

            stats["null_analysis"] = "checked"

        # Update history if valid
        if not issues:
            self.history[history_key] = len(data)
            self.history[f"{history_key}_timestamp"] = datetime.now().isoformat()
            self._save_history()

        if issues:
            return False, "Validation failed: " + "; ".join(issues), stats

        return True, "Validation passed", stats

    def validate_fbref_data(self, file_path: Path) -> Tuple[bool, str, Dict]:
        """Convenience method for FBRef data validation."""
        return self.validate_json_file(file_path, "fbref_players")

    def quarantine_file(self, file_path: Path, reason: str) -> Path:
        """
        Move a suspicious file to quarantine.

        Returns:
            Path to quarantined file
        """
        quarantine_dir = DATA_DIR / "quarantine"
        quarantine_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        quarantine_path = quarantine_dir / f"{file_path.stem}_{timestamp}{file_path.suffix}"

        # Copy to quarantine (don't move - preserve original for analysis)
        shutil.copy2(file_path, quarantine_path)

        # Write reason
        reason_file = quarantine_path.with_suffix(".reason.txt")
        with open(reason_file, "w") as f:
            f.write(f"Quarantined: {datetime.now().isoformat()}\n")
            f.write(f"Original: {file_path}\n")
            f.write(f"Reason: {reason}\n")

        return quarantine_path


# Standalone test
if __name__ == "__main__":
    breaker = DataCircuitBreaker()

    # Test with FBRef file if exists
    test_file = Path("/home/Mon_ps/data/fbref/fbref_players_clean_2025_26.json")

    if test_file.exists():
        is_valid, message, stats = breaker.validate_fbref_data(test_file)
        print(f"Validation: {message}")
        print(f"Stats: {json.dumps(stats, indent=2)}")
    else:
        print(f"Test file not found: {test_file}")
        print("Circuit breaker ready for use.")
