"""
Configuration Package for Uptime Bot

This package contains all configuration-related modules including:
- Settings management with environment variable support
- Constants and enums used throughout the application
- Feature flags and runtime configuration
"""

from config.settings import (
    Settings,
    DatabaseSettings,
    BotSettings,
    MonitoringSettings,
    LoggingSettings,
    CacheSettings,
    SecuritySettings,
    get_settings,
    settings
)

from config.constants import (
    BotCommands,
    UserRoles,
    LinkStatus,
    PingStatus,
    NotificationType,
    TimeIntervals,
    HTTPMethods,
    StatusCodes,
    MessageTemplates,
    Limits,
    Defaults,
    CacheKeys,
    CallbackPrefixes
)

__all__ = [
    # Settings
    "Settings",
    "DatabaseSettings",
    "BotSettings",
    "MonitoringSettings",
    "LoggingSettings",
    "CacheSettings",
    "SecuritySettings",
    "get_settings",
    "settings",
    
    # Constants
    "BotCommands",
    "UserRoles",
    "LinkStatus",
    "PingStatus",
    "NotificationType",
    "TimeIntervals",
    "HTTPMethods",
    "StatusCodes",
    "MessageTemplates",
    "Limits",
    "Defaults",
    "CacheKeys",
    "CallbackPrefixes"
]
