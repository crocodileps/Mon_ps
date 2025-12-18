#!/usr/bin/env python3
"""
Mon_PS Institutional Guardian - Telegram Notifications
Hedge Fund Grade Alerting System
"""

import os
import sys
import json
import urllib.request
import urllib.error
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from config.settings import (
    TELEGRAM_BOT_TOKEN,
    TELEGRAM_CHAT_ID,
    ALERT_CONFIG,
    GUARDIAN_ALERTS_FILE
)


class TelegramNotifier:
    """Send alerts via Telegram Bot API."""

    def __init__(self):
        self.bot_token = TELEGRAM_BOT_TOKEN
        self.chat_id = TELEGRAM_CHAT_ID
        self.api_url = f"https://api.telegram.org/bot{self.bot_token}"
        self.alerts_file = GUARDIAN_ALERTS_FILE
        self._last_alerts: Dict[str, datetime] = {}

    def is_configured(self) -> bool:
        """Check if Telegram is properly configured."""
        return bool(self.bot_token and self.chat_id)

    def _should_send(self, alert_key: str) -> bool:
        """Check cooldown to avoid alert spam."""
        if alert_key not in self._last_alerts:
            return True

        last_time = self._last_alerts[alert_key]
        cooldown = ALERT_CONFIG.get("cooldown_minutes", 30) * 60

        return (datetime.now() - last_time).total_seconds() > cooldown

    def _log_alert(self, level: str, message: str, sent: bool):
        """Log alert to file."""
        try:
            self.alerts_file.parent.mkdir(parents=True, exist_ok=True)

            log_entry = {
                "timestamp": datetime.now().isoformat(),
                "level": level,
                "message": message[:200],
                "sent_telegram": sent
            }

            with open(self.alerts_file, "a") as f:
                f.write(json.dumps(log_entry) + "\n")
        except Exception as e:
            print(f"Failed to log alert: {e}")

    def send_message(self, message: str, level: str = "INFO") -> bool:
        """
        Send a message to Telegram.

        Args:
            message: The message to send
            level: Alert level (INFO, WARNING, CRITICAL)

        Returns:
            True if sent successfully, False otherwise
        """
        if not self.is_configured():
            print("Telegram not configured. Message not sent.")
            self._log_alert(level, message, False)
            return False

        # Add emoji based on level
        emoji_map = {
            "INFO": "ℹ️",
            "SUCCESS": "✅",
            "WARNING": "⚠️",
            "CRITICAL": "🔴",
            "RECOVERY": "🟢"
        }
        emoji = emoji_map.get(level, "📢")

        # Format message
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        hostname = os.uname().nodename

        formatted_message = f"{emoji} *MON_PS GUARDIAN*\n"
        formatted_message += f"━━━━━━━━━━━━━━━━━━━━\n"
        formatted_message += f"*Level:* {level}\n"
        formatted_message += f"*Time:* {timestamp}\n"
        formatted_message += f"*Host:* {hostname}\n"
        formatted_message += f"━━━━━━━━━━━━━━━━━━━━\n"
        formatted_message += f"{message}"

        # Prepare request
        data = {
            "chat_id": self.chat_id,
            "text": formatted_message,
            "parse_mode": "Markdown"
        }

        try:
            req = urllib.request.Request(
                f"{self.api_url}/sendMessage",
                data=json.dumps(data).encode("utf-8"),
                headers={"Content-Type": "application/json"}
            )

            with urllib.request.urlopen(req, timeout=10) as response:
                result = json.loads(response.read().decode())

                if result.get("ok"):
                    self._log_alert(level, message, True)
                    return True
                else:
                    print(f"Telegram API error: {result}")
                    self._log_alert(level, message, False)
                    return False

        except urllib.error.URLError as e:
            print(f"Network error sending Telegram: {e}")
            self._log_alert(level, message, False)
            return False
        except Exception as e:
            print(f"Error sending Telegram: {e}")
            self._log_alert(level, message, False)
            return False

    def send_critical(self, message: str) -> bool:
        """Send a critical alert."""
        return self.send_message(message, "CRITICAL")

    def send_warning(self, message: str) -> bool:
        """Send a warning alert."""
        return self.send_message(message, "WARNING")

    def send_info(self, message: str) -> bool:
        """Send an info message."""
        return self.send_message(message, "INFO")

    def send_success(self, message: str) -> bool:
        """Send a success message."""
        return self.send_message(message, "SUCCESS")

    def send_recovery(self, message: str) -> bool:
        """Send a recovery notification."""
        return self.send_message(message, "RECOVERY")

    def send_health_report(self, report: dict) -> bool:
        """
        Send a formatted health report.

        Args:
            report: Dictionary with health check results
        """
        status_emoji = "✅" if report.get("healthy", False) else "🔴"

        message = f"{status_emoji} *Daily Health Report*\n\n"

        # Add check results
        for check_name, result in report.get("checks", {}).items():
            check_emoji = "✅" if result.get("passed", False) else "❌"
            message += f"{check_emoji} {check_name}\n"
            if not result.get("passed"):
                msg = result.get('message', 'Unknown error')
                message += f"   └─ {msg}\n"

        # Add summary
        message += f"\n*Summary:*\n"
        message += f"• Checks passed: {report.get('passed_count', 0)}/{report.get('total_count', 0)}\n"
        message += f"• Auto-healed: {report.get('healed_count', 0)}\n"

        if report.get("actions_taken"):
            message += f"\n*Actions taken:*\n"
            for action in report["actions_taken"]:
                message += f"• {action}\n"

        level = "SUCCESS" if report.get("healthy") else "CRITICAL"
        return self.send_message(message, level)

    def test_connection(self) -> bool:
        """Test Telegram connection with a simple message."""
        return self.send_message("🧪 Test connection from Institutional Guardian v1.0", "INFO")


# Standalone test
if __name__ == "__main__":
    # Load .env manually for testing
    env_file = Path(__file__).parent.parent / ".env"
    if env_file.exists():
        with open(env_file) as f:
            for line in f:
                if "=" in line and not line.strip().startswith("#"):
                    key, value = line.strip().split("=", 1)
                    os.environ[key] = value

    notifier = TelegramNotifier()

    if notifier.is_configured():
        print("Testing Telegram connection...")
        success = notifier.test_connection()
        print(f"Test result: {'SUCCESS' if success else 'FAILED'}")
    else:
        print("Telegram not configured. Set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID in .env")
