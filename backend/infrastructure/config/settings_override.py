"""Settings override pattern for testing.

Pattern: Support programmatic settings override while maintaining
singleton pattern for production use.
"""

from typing import Optional
from quantum_core.config.settings import Settings, get_settings as _get_settings

_settings_override: Optional[Settings] = None


def set_settings_override(settings: Optional[Settings]) -> None:
    """Override settings for testing.

    Usage:
        set_settings_override(Settings(environment="test"))
        # ... run tests ...
        set_settings_override(None)  # Cleanup
    """
    global _settings_override
    _settings_override = settings
    _get_settings.cache_clear()


def get_settings() -> Settings:
    """Get settings with test override support."""
    if _settings_override is not None:
        return _settings_override
    return _get_settings()
