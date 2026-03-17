"""Notification helpers for report delivery."""

from __future__ import annotations

from datetime import datetime
from typing import Dict, List, Optional

import requests

from config.config import Config
from utils.logger import setup_logger

logger = setup_logger(__name__)


class ConsoleNotifier:
    """Emit alert messages to the application logger."""

    channel = "console"

    def send(self, title: str, message: str) -> Dict[str, object]:
        logger.info("%s\n%s", title, message)
        return {"channel": self.channel, "success": True}


class FileNotifier:
    """Append alert messages to a local text file."""

    channel = "file"

    def __init__(self, output_file: str):
        self.output_file = output_file

    def send(self, title: str, message: str) -> Dict[str, object]:
        timestamp = datetime.now().isoformat(timespec="seconds")
        with open(self.output_file, "a", encoding="utf-8") as handle:
            handle.write(f"[{timestamp}] {title}\n{message}\n\n")
        return {
            "channel": self.channel,
            "success": True,
            "target": self.output_file,
        }


class WebhookNotifier:
    """Send alert messages to a generic webhook endpoint."""

    channel = "webhook"

    def __init__(self, webhook_url: str):
        self.webhook_url = webhook_url

    def send(self, title: str, message: str) -> Dict[str, object]:
        payload = {"text": f"{title}\n{message}"}
        response = requests.post(self.webhook_url, json=payload, timeout=10)
        success = 200 <= response.status_code < 300
        if not success:
            logger.warning(
                "Webhook delivery failed with status %s",
                response.status_code,
            )
        return {
            "channel": self.channel,
            "success": success,
            "status_code": response.status_code,
        }


class NotificationManager:
    """Fan out a message to the enabled notification channels."""

    def __init__(
        self,
        webhook_url: Optional[str] = None,
        output_file: Optional[str] = None,
        console_enabled: Optional[bool] = None,
    ):
        Config.ensure_runtime_dirs()

        webhook_url = webhook_url if webhook_url is not None else Config.ALERT_WEBHOOK_URL
        output_file = output_file or Config.ALERT_OUTPUT_FILE
        console_enabled = (
            Config.ALERT_CONSOLE_ENABLED
            if console_enabled is None
            else console_enabled
        )

        self.channels: List[object] = []
        if console_enabled:
            self.channels.append(ConsoleNotifier())
        if output_file:
            self.channels.append(FileNotifier(output_file))
        if webhook_url:
            self.channels.append(WebhookNotifier(webhook_url))

    def send(self, title: str, message: str) -> List[Dict[str, object]]:
        """Send a message via all configured channels."""
        results = []
        for notifier in self.channels:
            try:
                results.append(notifier.send(title, message))
            except Exception as exc:
                logger.error(
                    "Notification failed on %s: %s",
                    getattr(notifier, "channel", type(notifier).__name__),
                    exc,
                )
                results.append(
                    {
                        "channel": getattr(
                            notifier,
                            "channel",
                            type(notifier).__name__,
                        ),
                        "success": False,
                        "error": str(exc),
                    }
                )
        return results
