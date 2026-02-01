"""
============================================================================
TELEGRAM UPTIME BOT - SETTINGS CONFIGURATION
============================================================================
Comprehensive settings management using Pydantic for validation.

Author: Professional Development Team
Version: 1.0.0
License: MIT
============================================================================
"""

import os
from typing import List, Optional, Dict, Any
from pathlib import Path
from functools import lru_cache

from pydantic import Field, field_validator, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict


# ============================================================================
# BASE SETTINGS CLASS
# ============================================================================

class Settings(BaseSettings):
    """
    Application settings with comprehensive configuration options.
    All settings can be overridden via environment variables.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )

    # ========================================================================
    # TELEGRAM BOT CONFIGURATION
    # ========================================================================
    
    BOT_TOKEN: str = Field(..., description="Telegram bot token from BotFather")
    BOT_USERNAME: Optional[str] = Field(None, description="Bot username")
    BOT_NAME: str = Field(default="UptimeBot", description="Bot display name")
    BOT_VERSION: str = Field(default="1.0.0", description="Bot version")
    BOT_DESCRIPTION: str = Field(
        default="Professional Uptime Monitoring Bot",
        description="Bot description"
    )
    
    # Admin Configuration
    OWNER_ID: int = Field(..., description="Bot owner Telegram user ID")
    ADMIN_IDS: str = Field(default="", description="Comma-separated admin user IDs")
    
    # Bot Behavior
    MAX_CONNECTIONS: int = Field(default=100, description="Maximum concurrent connections")
    WEBHOOK_MODE: bool = Field(default=False, description="Enable webhook mode")
    
    @computed_field
    @property
    def admin_list(self) -> List[int]:
        """Parse admin IDs from comma-separated string."""
        if not self.ADMIN_IDS:
            return [self.OWNER_ID]
        
        admin_ids = [self.OWNER_ID]
        for admin_id in self.ADMIN_IDS.split(","):
            try:
                admin_ids.append(int(admin_id.strip()))
            except ValueError:
                continue
        return list(set(admin_ids))

    # ========================================================================
    # DATABASE CONFIGURATION
    # ========================================================================
    
    # PostgreSQL Settings
    DB_TYPE: str = Field(default="postgresql", description="Database type")
    DB_HOST: str = Field(default="localhost", description="Database host")
    DB_PORT: int = Field(default=5432, description="Database port")
    DB_NAME: str = Field(default="uptime_bot", description="Database name")
    DB_USER: str = Field(default="postgres", description="Database user")
    DB_PASSWORD: str = Field(default="", description="Database password")
    
    # Connection Pool Settings
    DB_POOL_SIZE: int = Field(default=20, description="Database connection pool size")
    DB_MAX_OVERFLOW: int = Field(default=10, description="Maximum pool overflow")
    DB_POOL_TIMEOUT: int = Field(default=30, description="Pool timeout in seconds")
    DB_POOL_RECYCLE: int = Field(default=3600, description="Connection recycle time")
    DB_ECHO: bool = Field(default=False, description="Echo SQL queries")
    
    # MongoDB Settings (Alternative)
    MONGO_URI: Optional[str] = Field(None, description="MongoDB connection URI")
    MONGO_DB_NAME: str = Field(default="uptime_bot", description="MongoDB database name")
    MONGO_COLLECTION_LINKS: str = Field(default="links", description="Links collection")
    MONGO_COLLECTION_USERS: str = Field(default="users", description="Users collection")
    MONGO_COLLECTION_LOGS: str = Field(default="logs", description="Logs collection")
    
    # Redis Settings
    REDIS_HOST: str = Field(default="localhost", description="Redis host")
    REDIS_PORT: int = Field(default=6379, description="Redis port")
    REDIS_DB: int = Field(default=0, description="Redis database number")
    REDIS_PASSWORD: Optional[str] = Field(None, description="Redis password")
    REDIS_SSL: bool = Field(default=False, description="Use SSL for Redis")
    REDIS_CACHE_TTL: int = Field(default=3600, description="Cache TTL in seconds")

    # ========================================================================
    # MONITORING CONFIGURATION
    # ========================================================================
    
    # Ping Settings
    DEFAULT_PING_INTERVAL: int = Field(default=300, description="Default ping interval (seconds)")
    MIN_PING_INTERVAL: int = Field(default=60, description="Minimum ping interval (seconds)")
    MAX_PING_INTERVAL: int = Field(default=86400, description="Maximum ping interval (seconds)")
    REQUEST_TIMEOUT: int = Field(default=30, description="HTTP request timeout (seconds)")
    MAX_RETRIES: int = Field(default=3, description="Maximum retry attempts")
    RETRY_DELAY: int = Field(default=5, description="Delay between retries (seconds)")
    
    # Concurrent Monitoring
    MAX_CONCURRENT_PINGS: int = Field(default=50, description="Maximum concurrent pings")
    MONITOR_BATCH_SIZE: int = Field(default=100, description="Monitoring batch size")
    MONITOR_WORKER_COUNT: int = Field(default=5, description="Number of monitor workers")
    
    # Health Check
    HEALTH_CHECK_ENABLED: bool = Field(default=True, description="Enable health checks")
    HEALTH_CHECK_INTERVAL: int = Field(default=60, description="Health check interval")
    HEALTH_CHECK_TIMEOUT: int = Field(default=10, description="Health check timeout")

    @field_validator("DEFAULT_PING_INTERVAL", "MIN_PING_INTERVAL", "MAX_PING_INTERVAL")
    @classmethod
    def validate_intervals(cls, v: int) -> int:
        """Validate ping intervals are positive."""
        if v <= 0:
            raise ValueError("Interval must be positive")
        return v

    # ========================================================================
    # SELF-PING CONFIGURATION (RENDER)
    # ========================================================================
    
    SELF_PING_ENABLED: bool = Field(default=True, description="Enable self-ping")
    SELF_PING_URL: Optional[str] = Field(None, description="Self-ping URL")
    SELF_PING_INTERVAL: int = Field(default=300, description="Self-ping interval (seconds)")
    SELF_PING_METHOD: str = Field(default="GET", description="Self-ping HTTP method")
    SELF_PING_TIMEOUT: int = Field(default=15, description="Self-ping timeout")
    SELF_PING_RETRY_COUNT: int = Field(default=3, description="Self-ping retry count")

    # ========================================================================
    # NOTIFICATION SETTINGS
    # ========================================================================
    
    # Alert Configuration
    ENABLE_DOWNTIME_ALERTS: bool = Field(default=True, description="Enable downtime alerts")
    ENABLE_RECOVERY_ALERTS: bool = Field(default=True, description="Enable recovery alerts")
    ALERT_COOLDOWN: int = Field(default=900, description="Alert cooldown period (seconds)")
    MAX_ALERTS_PER_HOUR: int = Field(default=10, description="Maximum alerts per hour")
    ALERT_RETRY_COUNT: int = Field(default=3, description="Alert retry count")
    
    # Notification Channels
    ALERT_CHANNEL_ID: Optional[int] = Field(None, description="Alert channel ID")
    BROADCAST_CHANNEL_ID: Optional[int] = Field(None, description="Broadcast channel ID")
    LOG_CHANNEL_ID: Optional[int] = Field(None, description="Log channel ID")

    # ========================================================================
    # LOGGING CONFIGURATION
    # ========================================================================
    
    LOG_LEVEL: str = Field(default="INFO", description="Logging level")
    LOG_FORMAT: str = Field(default="json", description="Log format (json/text)")
    LOG_TO_FILE: bool = Field(default=True, description="Enable file logging")
    LOG_FILE_PATH: str = Field(default="logs/uptime_bot.log", description="Log file path")
    LOG_FILE_MAX_SIZE: int = Field(default=10485760, description="Max log file size (bytes)")
    LOG_FILE_BACKUP_COUNT: int = Field(default=5, description="Number of backup logs")
    LOG_TO_CONSOLE: bool = Field(default=True, description="Enable console logging")
    LOG_COLORIZE: bool = Field(default=True, description="Colorize console logs")
    
    # Database Logging
    DB_LOG_ENABLED: bool = Field(default=True, description="Enable database logging")
    DB_LOG_RETENTION_DAYS: int = Field(default=30, description="Log retention days")
    DB_LOG_BATCH_SIZE: int = Field(default=100, description="Log batch size")

    @field_validator("LOG_LEVEL")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        """Validate log level."""
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        v = v.upper()
        if v not in valid_levels:
            raise ValueError(f"Invalid log level. Must be one of: {valid_levels}")
        return v

    # ========================================================================
    # SECURITY & RATE LIMITING
    # ========================================================================
    
    # Rate Limiting
    RATE_LIMIT_ENABLED: bool = Field(default=True, description="Enable rate limiting")
    RATE_LIMIT_PER_USER: int = Field(default=30, description="Rate limit per user")
    RATE_LIMIT_WINDOW: int = Field(default=60, description="Rate limit window (seconds)")
    RATE_LIMIT_STORAGE: str = Field(default="redis", description="Rate limit storage")
    
    # Security
    SECRET_KEY: str = Field(
        default="change_this_secret_key_in_production",
        description="Secret key for encryption"
    )
    ENCRYPTION_KEY: str = Field(
        default="change_this_encryption_key",
        description="Encryption key"
    )
    JWT_SECRET: str = Field(default="jwt_secret_key", description="JWT secret")
    JWT_EXPIRATION: int = Field(default=86400, description="JWT expiration (seconds)")
    
    # API Keys
    API_KEY_HEADER: str = Field(default="X-API-Key", description="API key header name")
    API_KEYS: str = Field(default="", description="Comma-separated API keys")

    @computed_field
    @property
    def api_keys_list(self) -> List[str]:
        """Parse API keys from comma-separated string."""
        if not self.API_KEYS:
            return []
        return [key.strip() for key in self.API_KEYS.split(",") if key.strip()]

    # ========================================================================
    # USER LIMITS & QUOTAS
    # ========================================================================
    
    # Free Tier
    FREE_USER_MAX_LINKS: int = Field(default=10, description="Free user max links")
    FREE_USER_MIN_INTERVAL: int = Field(default=300, description="Free user min interval")
    
    # Premium Tier
    PREMIUM_USER_MAX_LINKS: int = Field(default=100, description="Premium user max links")
    PREMIUM_USER_MIN_INTERVAL: int = Field(default=60, description="Premium user min interval")
    
    # Admin Limits
    ADMIN_MAX_LINKS: int = Field(default=1000, description="Admin max links")
    ADMIN_MIN_INTERVAL: int = Field(default=30, description="Admin min interval")

    # ========================================================================
    # WEBHOOK CONFIGURATION
    # ========================================================================
    
    WEBHOOK_HOST: Optional[str] = Field(None, description="Webhook host URL")
    WEBHOOK_PATH: str = Field(default="/webhook/{token}", description="Webhook path")
    WEBHOOK_PORT: int = Field(default=8443, description="Webhook port")
    WEBHOOK_LISTEN: str = Field(default="0.0.0.0", description="Webhook listen address")
    
    # SSL/TLS
    WEBHOOK_SSL_CERT: Optional[str] = Field(None, description="SSL certificate path")
    WEBHOOK_SSL_PRIV: Optional[str] = Field(None, description="SSL private key path")

    @computed_field
    @property
    def webhook_url(self) -> Optional[str]:
        """Generate full webhook URL."""
        if self.WEBHOOK_HOST and self.BOT_TOKEN:
            path = self.WEBHOOK_PATH.format(token=self.BOT_TOKEN)
            return f"{self.WEBHOOK_HOST}{path}"
        return None

    # ========================================================================
    # API SERVER CONFIGURATION
    # ========================================================================
    
    API_ENABLED: bool = Field(default=True, description="Enable API server")
    API_HOST: str = Field(default="0.0.0.0", description="API host")
    API_PORT: int = Field(default=8000, description="API port")
    API_WORKERS: int = Field(default=4, description="API worker count")
    API_RELOAD: bool = Field(default=False, description="Enable API auto-reload")
    API_DEBUG: bool = Field(default=False, description="Enable API debug mode")
    
    # CORS
    CORS_ENABLED: bool = Field(default=True, description="Enable CORS")
    CORS_ORIGINS: str = Field(default="*", description="CORS allowed origins")
    CORS_METHODS: str = Field(default="GET,POST,PUT,DELETE", description="CORS methods")
    CORS_HEADERS: str = Field(default="*", description="CORS headers")

    @computed_field
    @property
    def cors_origins_list(self) -> List[str]:
        """Parse CORS origins."""
        if self.CORS_ORIGINS == "*":
            return ["*"]
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",")]

    # ========================================================================
    # BACKUP & MAINTENANCE
    # ========================================================================
    
    AUTO_BACKUP_ENABLED: bool = Field(default=True, description="Enable auto backup")
    BACKUP_INTERVAL: int = Field(default=86400, description="Backup interval (seconds)")
    BACKUP_PATH: str = Field(default="backups/", description="Backup directory")
    BACKUP_RETENTION_DAYS: int = Field(default=7, description="Backup retention days")
    BACKUP_COMPRESS: bool = Field(default=True, description="Compress backups")
    
    # Maintenance
    MAINTENANCE_MODE: bool = Field(default=False, description="Maintenance mode")
    MAINTENANCE_MESSAGE: str = Field(
        default="Bot is under maintenance. Please try again later.",
        description="Maintenance message"
    )

    # ========================================================================
    # METRICS & ANALYTICS
    # ========================================================================
    
    # Prometheus
    METRICS_ENABLED: bool = Field(default=True, description="Enable metrics")
    METRICS_PORT: int = Field(default=9090, description="Metrics port")
    METRICS_PATH: str = Field(default="/metrics", description="Metrics endpoint")
    
    # Statistics
    STATS_ENABLED: bool = Field(default=True, description="Enable statistics")
    STATS_CACHE_TTL: int = Field(default=300, description="Stats cache TTL")
    STATS_HISTORY_RETENTION_DAYS: int = Field(default=90, description="Stats retention")

    # ========================================================================
    # PERFORMANCE TUNING
    # ========================================================================
    
    # Threading & Async
    THREAD_POOL_SIZE: int = Field(default=10, description="Thread pool size")
    PROCESS_POOL_SIZE: int = Field(default=4, description="Process pool size")
    ASYNC_TIMEOUT: int = Field(default=60, description="Async operation timeout")
    
    # Memory Management
    MAX_MEMORY_MB: int = Field(default=512, description="Maximum memory (MB)")
    GARBAGE_COLLECTION_ENABLED: bool = Field(default=True, description="Enable GC")
    GC_THRESHOLD: str = Field(default="700,10,10", description="GC threshold")

    # ========================================================================
    # EXTERNAL SERVICES
    # ========================================================================
    
    # Email
    EMAIL_ENABLED: bool = Field(default=False, description="Enable email")
    SMTP_HOST: str = Field(default="smtp.gmail.com", description="SMTP host")
    SMTP_PORT: int = Field(default=587, description="SMTP port")
    SMTP_USER: Optional[str] = Field(None, description="SMTP user")
    SMTP_PASSWORD: Optional[str] = Field(None, description="SMTP password")
    SMTP_FROM: Optional[str] = Field(None, description="Email from address")
    
    # Sentry
    SENTRY_ENABLED: bool = Field(default=False, description="Enable Sentry")
    SENTRY_DSN: Optional[str] = Field(None, description="Sentry DSN")
    
    # Analytics
    ANALYTICS_ENABLED: bool = Field(default=False, description="Enable analytics")
    ANALYTICS_ID: Optional[str] = Field(None, description="Analytics ID")

    # ========================================================================
    # DEVELOPMENT & DEBUG
    # ========================================================================
    
    DEBUG: bool = Field(default=False, description="Debug mode")
    DEV_MODE: bool = Field(default=False, description="Development mode")
    TESTING: bool = Field(default=False, description="Testing mode")
    
    # Profiling
    PROFILING_ENABLED: bool = Field(default=False, description="Enable profiling")
    PROFILING_OUTPUT_PATH: str = Field(default="profiles/", description="Profile output")

    # ========================================================================
    # TIMEZONE & LOCALIZATION
    # ========================================================================
    
    TIMEZONE: str = Field(default="UTC", description="Application timezone")
    DATE_FORMAT: str = Field(default="%Y-%m-%d %H:%M:%S", description="Date format")
    DEFAULT_LANGUAGE: str = Field(default="en", description="Default language")
    SUPPORTED_LANGUAGES: str = Field(default="en,ru,es,fr,de", description="Supported languages")

    @computed_field
    @property
    def supported_languages_list(self) -> List[str]:
        """Parse supported languages."""
        return [lang.strip() for lang in self.SUPPORTED_LANGUAGES.split(",")]

    # ========================================================================
    # RENDER SPECIFIC SETTINGS
    # ========================================================================
    
    RENDER_ENABLED: bool = Field(default=True, description="Running on Render")
    RENDER_INSTANCE_ID: Optional[str] = Field(None, description="Render instance ID")
    RENDER_SERVICE_NAME: str = Field(default="uptime-bot", description="Render service")
    RENDER_REGION: Optional[str] = Field(None, description="Render region")
    PORT: int = Field(default=10000, description="Application port")

    # ========================================================================
    # FEATURE FLAGS
    # ========================================================================
    
    ENABLE_PREMIUM_FEATURES: bool = Field(default=True, description="Premium features")
    ENABLE_ADMIN_PANEL: bool = Field(default=True, description="Admin panel")
    ENABLE_USER_DASHBOARD: bool = Field(default=True, description="User dashboard")
    ENABLE_EXPORT_DATA: bool = Field(default=True, description="Data export")
    ENABLE_IMPORT_DATA: bool = Field(default=True, description="Data import")
    ENABLE_BATCH_OPERATIONS: bool = Field(default=True, description="Batch operations")
    ENABLE_SCHEDULED_REPORTS: bool = Field(default=True, description="Scheduled reports")
    ENABLE_CUSTOM_DOMAINS: bool = Field(default=True, description="Custom domains")
    ENABLE_SSL_MONITORING: bool = Field(default=True, description="SSL monitoring")
    ENABLE_DNS_MONITORING: bool = Field(default=True, description="DNS monitoring")
    ENABLE_API_MONITORING: bool = Field(default=True, description="API monitoring")
    
    # Experimental
    EXPERIMENTAL_FEATURES: bool = Field(default=False, description="Experimental features")
    BETA_FEATURES: bool = Field(default=False, description="Beta features")

    # ========================================================================
    # COMPUTED PROPERTIES
    # ========================================================================

    @computed_field
    @property
    def is_production(self) -> bool:
        """Check if running in production mode."""
        return not (self.DEBUG or self.DEV_MODE or self.TESTING)

    @computed_field
    @property
    def base_dir(self) -> Path:
        """Get base directory path."""
        return Path(__file__).parent.parent

    @computed_field
    @property
    def logs_dir(self) -> Path:
        """Get logs directory path."""
        logs_path = self.base_dir / "logs"
        logs_path.mkdir(exist_ok=True)
        return logs_path

    @computed_field
    @property
    def backups_dir(self) -> Path:
        """Get backups directory path."""
        backup_path = self.base_dir / self.BACKUP_PATH
        backup_path.mkdir(exist_ok=True)
        return backup_path


# ============================================================================
# SETTINGS SINGLETON
# ============================================================================

@lru_cache()
def get_settings() -> Settings:
    """
    Get cached settings instance.
    
    Returns:
        Settings instance
    """
    return Settings()


# ============================================================================
# END OF SETTINGS MODULE
# ============================================================================
