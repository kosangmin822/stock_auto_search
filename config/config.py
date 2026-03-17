"""Application configuration."""

import os

from dotenv import load_dotenv

load_dotenv()


def _as_bool(value, default=False):
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _resolve_path(path):
    if not path:
        return path
    if os.path.isabs(path):
        return path
    project_root = os.path.dirname(os.path.dirname(__file__))
    return os.path.join(project_root, path)


class Config:
    """Environment-backed runtime configuration."""

    DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")

    # Trading-only settings.
    KIS_API_KEY = os.getenv("KIS_API_KEY")
    KIS_SECRET_KEY = os.getenv("KIS_SECRET_KEY")
    KIS_ACCOUNT_NUMBER = os.getenv("KIS_ACCOUNT_NUMBER")
    KIS_ACCOUNT_TYPE = os.getenv("KIS_ACCOUNT_TYPE")
    KIS_BASE_URL = os.getenv(
        "KIS_BASE_URL",
        "https://openapivts.koreainvestment.com:29443",
    )

    # Search/report defaults.
    DEFAULT_MARKET = os.getenv("DEFAULT_MARKET", "ALL")
    DEFAULT_LOOKBACK_DAYS = int(os.getenv("DEFAULT_LOOKBACK_DAYS", "365"))
    DEFAULT_REPORT_LIMIT = int(os.getenv("DEFAULT_REPORT_LIMIT", "5"))

    # Notification settings.
    ALERT_WEBHOOK_URL = os.getenv("ALERT_WEBHOOK_URL")
    ALERT_OUTPUT_FILE = _resolve_path(
        os.getenv(
            "ALERT_OUTPUT_FILE",
            os.path.join(DATA_DIR, "alerts", "notifications.log"),
        )
    )
    ALERT_CONSOLE_ENABLED = _as_bool(
        os.getenv("ALERT_CONSOLE_ENABLED"),
        default=True,
    )

    # Logging.
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

    @classmethod
    def ensure_runtime_dirs(cls):
        """Create runtime directories used by the app."""
        os.makedirs(cls.DATA_DIR, exist_ok=True)
        os.makedirs(os.path.join(cls.DATA_DIR, "logs"), exist_ok=True)
        os.makedirs(os.path.join(cls.DATA_DIR, "reports"), exist_ok=True)
        alert_dir = os.path.dirname(cls.ALERT_OUTPUT_FILE)
        if alert_dir:
            os.makedirs(alert_dir, exist_ok=True)

    @classmethod
    def validate_kis(cls):
        """Validate required KIS configuration for trading/account features."""
        required_fields = [
            "KIS_API_KEY",
            "KIS_SECRET_KEY",
            "KIS_ACCOUNT_NUMBER",
            "KIS_ACCOUNT_TYPE",
        ]
        missing_fields = [
            field for field in required_fields if not getattr(cls, field, None)
        ]
        if missing_fields:
            raise ValueError(
                f"Missing required KIS config fields: {', '.join(missing_fields)}"
            )
        return True

    @classmethod
    def validate_non_trading(cls):
        """Validate required configuration for search/report/alert features."""
        cls.ensure_runtime_dirs()
        return True

    @classmethod
    def validate(cls):
        """Backward-compatible alias for KIS validation."""
        return cls.validate_kis()
