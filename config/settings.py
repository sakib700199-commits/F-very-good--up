"""
Settings Module for Uptime Bot

Comprehensive configuration management using Pydantic Settings.
Supports environment variables, .env files, and runtime configuration.
Includes validation, type checking, and sensible defaults.
"""

from __future__ import annotations

import os
import secrets
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Union
from enum import Enum

from pydantic import (
    Field,
    SecretStr,
    field_validator,
    model_validator,
    AnyHttpUrl,
    PostgresDsn,
    RedisDsn,
    EmailStr
)
from pydantic_settings import BaseSettings, SettingsConfigDict


class Environment(str, Enum):
    """Application environment enumeration."""
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"
    TESTING = "testing"


class LogLevel(str, Enum):
    """Logging level enumeration."""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class DatabaseType(str, Enum):
    """Supported database types."""
    POSTGRESQL = "postgresql"
    SQLITE = "sqlite"
    MYSQL = "mysql"


class BaseSettingsConfig(BaseSettings):
    """Base configuration class with common settings."""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
        validate_default=True
    )


class DatabaseSettings(BaseSettingsConfig):
    """
    Database Configuration Settings
    
    Supports PostgreSQL (production), SQLite (development), and MySQL.
    Includes connection pooling, timeout, and SSL configuration.
    """
    
    model_config = SettingsConfigDict(
        env_prefix="DB_",
        env_file=".env"
    )
    
    # Database type and connection
    type: DatabaseType = Field(
        default=DatabaseType.SQLITE,
        description="Database type: postgresql, sqlite, or mysql"
    )
    
    # PostgreSQL / MySQL settings
    host: str = Field(
        default="localhost",
        description="Database host address"
    )
    port: int = Field(
        default=5432,
        ge=1,
        le=65535,
        description="Database port number"
    )
    name: str = Field(
        default="uptime_bot",
        min_length=1,
        max_length=64,
        description="Database name"
    )
    user: str = Field(
        default="postgres",
        min_length=1,
        max_length=64,
        description="Database username"
    )
    password: SecretStr = Field(
        default=SecretStr(""),
        description="Database password"
    )
    
    # SQLite settings
    sqlite_path: Path = Field(
        default=Path("data/uptime_bot.db"),
        description="Path to SQLite database file"
    )
    
    # Connection pool settings
    pool_size: int = Field(
        default=10,
        ge=1,
        le=100,
        description="Connection pool size"
    )
    max_overflow: int = Field(
        default=20,
        ge=0,
        le=100,
        description="Maximum overflow connections"
    )
    pool_timeout: int = Field(
        default=30,
        ge=1,
        le=300,
        description="Pool connection timeout in seconds"
    )
    pool_recycle: int = Field(
        default=1800,
        ge=60,
        le=7200,
        description="Connection recycle time in seconds"
    )
    pool_pre_ping: bool = Field(
        default=True,
        description="Enable connection health check before use"
    )
    
    # Query settings
    echo: bool = Field(
        default=False,
        description="Echo SQL queries (debug mode)"
    )
    echo_pool: bool = Field(
        default=False,
        description="Echo connection pool events"
    )
    
    # SSL settings
    ssl_enabled: bool = Field(
        default=False,
        description="Enable SSL for database connection"
    )
    ssl_ca_path: Optional[Path] = Field(
        default=None,
        description="Path to SSL CA certificate"
    )
    ssl_cert_path: Optional[Path] = Field(
        default=None,
        description="Path to SSL client certificate"
    )
    ssl_key_path: Optional[Path] = Field(
        default=None,
        description="Path to SSL client key"
    )
    
    # Migration settings
    auto_migrate: bool = Field(
        default=True,
        description="Automatically run migrations on startup"
    )
    migration_directory: Path = Field(
        default=Path("migrations"),
        description="Directory for database migrations"
    )
    
    @property
    def url(self) -> str:
        """Generate database URL based on configuration."""
        if self.type == DatabaseType.SQLITE:
            # Ensure directory exists
            self.sqlite_path.parent.mkdir(parents=True, exist_ok=True)
            return f"sqlite+aiosqlite:///{self.sqlite_path}"
        
        elif self.type == DatabaseType.POSTGRESQL:
            password = self.password.get_secret_value()
            return (
                f"postgresql+asyncpg://{self.user}:{password}"
                f"@{self.host}:{self.port}/{self.name}"
            )
        
        elif self.type == DatabaseType.MYSQL:
            password = self.password.get_secret_value()
            return (
                f"mysql+aiomysql://{self.user}:{password}"
                f"@{self.host}:{self.port}/{self.name}"
            )
        
        raise ValueError(f"Unsupported database type: {self.type}")
    
    @property
    def sync_url(self) -> str:
        """Generate synchronous database URL for migrations."""
        if self.type == DatabaseType.SQLITE:
            return f"sqlite:///{self.sqlite_path}"
        
        elif self.type == DatabaseType.POSTGRESQL:
            password = self.password.get_secret_value()
            return (
                f"postgresql://{self.user}:{password}"
                f"@{self.host}:{self.port}/{self.name}"
            )
        
        elif self.type == DatabaseType.MYSQL:
            password = self.password.get_secret_value()
            return (
                f"mysql://{self.user}:{password}"
                f"@{self.host}:{self.port}/{self.name}"
            )
        
        raise ValueError(f"Unsupported database type: {self.type}")
    
    @field_validator("sqlite_path")
    @classmethod
    def validate_sqlite_path(cls, v: Path) -> Path:
        """Validate and normalize SQLite path."""
        if not v.suffix:
            v = v.with_suffix(".db")
        return v
    
    @model_validator(mode="after")
    def validate_ssl_settings(self) -> "DatabaseSettings":
        """Validate SSL settings consistency."""
        if self.ssl_enabled:
            if self.type == DatabaseType.SQLITE:
                raise ValueError("SSL is not supported for SQLite databases")
            
            if self.ssl_ca_path and not self.ssl_ca_path.exists():
                raise ValueError(f"SSL CA file not found: {self.ssl_ca_path}")
        
        return self


class BotSettings(BaseSettingsConfig):
    """
    Telegram Bot Configuration Settings
    
    Contains all bot-related settings including token, admin IDs,
    rate limiting, and feature toggles.
    """
    
    model_config = SettingsConfigDict(
        env_prefix="BOT_",
        env_file=".env"
    )
    
    # Core bot settings
    token: SecretStr = Field(
        ...,  # Required
        description="Telegram Bot API token from @BotFather"
    )
    
    # Admin configuration
    owner_id: int = Field(
        ...,  # Required
        description="Telegram user ID of the bot owner"
    )
    admin_ids: Set[int] = Field(
        default_factory=set,
        description="Set of admin user IDs"
    )
    
    # Bot information
    name: str = Field(
        default="Uptime Bot",
        min_length=1,
        max_length=64,
        description="Bot display name"
    )
    username: Optional[str] = Field(
        default=None,
        description="Bot username (without @)"
    )
    version: str = Field(
        default="1.0.0",
        description="Bot version string"
    )
    
    # Rate limiting
    rate_limit_enabled: bool = Field(
        default=True,
        description="Enable rate limiting for commands"
    )
    rate_limit_window: int = Field(
        default=60,
        ge=1,
        le=3600,
        description="Rate limit window in seconds"
    )
    rate_limit_max_requests: int = Field(
        default=30,
        ge=1,
        le=1000,
        description="Maximum requests per window"
    )
    
    # Message settings
    parse_mode: str = Field(
        default="HTML",
        description="Default message parse mode (HTML, Markdown, MarkdownV2)"
    )
    disable_web_page_preview: bool = Field(
        default=True,
        description="Disable link previews in messages"
    )
    
    # Webhook settings (for production)
    use_webhook: bool = Field(
        default=False,
        description="Use webhook instead of polling"
    )
    webhook_host: Optional[str] = Field(
        default=None,
        description="Webhook host URL"
    )
    webhook_path: str = Field(
        default="/webhook",
        description="Webhook URL path"
    )
    webhook_port: int = Field(
        default=8443,
        ge=1,
        le=65535,
        description="Webhook server port"
    )
    webhook_secret: Optional[SecretStr] = Field(
        default=None,
        description="Webhook secret token for verification"
    )
    
    # Polling settings (for development)
    polling_timeout: int = Field(
        default=30,
        ge=1,
        le=60,
        description="Long polling timeout in seconds"
    )
    polling_allowed_updates: List[str] = Field(
        default_factory=lambda: [
            "message",
            "callback_query",
            "inline_query",
            "chat_member"
        ],
        description="Allowed update types for polling"
    )
    
    # Feature toggles
    enable_inline_mode: bool = Field(
        default=False,
        description="Enable inline query mode"
    )
    enable_group_mode: bool = Field(
        default=True,
        description="Allow bot usage in groups"
    )
    enable_channel_mode: bool = Field(
        default=False,
        description="Allow bot usage in channels"
    )
    maintenance_mode: bool = Field(
        default=False,
        description="Enable maintenance mode (blocks non-admin users)"
    )
    
    # Limits
    max_links_per_user: int = Field(
        default=0,  # 0 = unlimited
        ge=0,
        description="Maximum links per user (0 = unlimited)"
    )
    max_links_premium: int = Field(
        default=0,  # 0 = unlimited
        ge=0,
        description="Maximum links for premium users (0 = unlimited)"
    )
    
    @field_validator("token")
    @classmethod
    def validate_token(cls, v: SecretStr) -> SecretStr:
        """Validate Telegram bot token format."""
        token = v.get_secret_value()
        
        if not token:
            raise ValueError("Bot token cannot be empty")
        
        parts = token.split(":")
        if len(parts) != 2:
            raise ValueError("Invalid bot token format")
        
        try:
            int(parts[0])
        except ValueError:
            raise ValueError("Invalid bot token format: ID must be numeric")
        
        if len(parts[1]) < 30:
            raise ValueError("Invalid bot token format: Token too short")
        
        return v
    
    @field_validator("admin_ids", mode="before")
    @classmethod
    def parse_admin_ids(cls, v: Any) -> Set[int]:
        """Parse admin IDs from string or list."""
        if isinstance(v, str):
            if not v.strip():
                return set()
            return {int(x.strip()) for x in v.split(",") if x.strip()}
        
        if isinstance(v, (list, set, tuple)):
            return {int(x) for x in v}
        
        return set()
    
    @property
    def all_admin_ids(self) -> Set[int]:
        """Get all admin IDs including owner."""
        return self.admin_ids | {self.owner_id}
    
    @property
    def webhook_url(self) -> Optional[str]:
        """Generate full webhook URL."""
        if not self.use_webhook or not self.webhook_host:
            return None
        
        return f"{self.webhook_host.rstrip('/')}{self.webhook_path}"
    
    def is_admin(self, user_id: int) -> bool:
        """Check if user is an admin."""
        return user_id in self.all_admin_ids
    
    def is_owner(self, user_id: int) -> bool:
        """Check if user is the owner."""
        return user_id == self.owner_id


class MonitoringSettings(BaseSettingsConfig):
    """
    Monitoring Engine Configuration Settings
    
    Controls ping intervals, timeout settings, retry logic,
    and alert thresholds for the monitoring engine.
    """
    
    model_config = SettingsConfigDict(
        env_prefix="MONITOR_",
        env_file=".env"
    )
    
    # Ping intervals
    default_interval: int = Field(
        default=300,  # 5 minutes
        ge=30,
        le=86400,
        description="Default ping interval in seconds"
    )
    min_interval: int = Field(
        default=60,  # 1 minute
        ge=30,
        le=300,
        description="Minimum allowed ping interval"
    )
    max_interval: int = Field(
        default=86400,  # 24 hours
        ge=300,
        le=604800,
        description="Maximum allowed ping interval"
    )
    
    # Self-ping settings (for Render/Heroku)
    self_ping_enabled: bool = Field(
        default=True,
        description="Enable self-pinging to prevent sleep"
    )
    self_ping_url: Optional[str] = Field(
        default=None,
        description="URL for self-ping (auto-detected if not set)"
    )
    self_ping_interval: int = Field(
        default=300,  # 5 minutes
        ge=60,
        le=900,
        description="Self-ping interval in seconds"
    )
    
    # HTTP client settings
    request_timeout: int = Field(
        default=30,
        ge=5,
        le=120,
        description="HTTP request timeout in seconds"
    )
    connect_timeout: int = Field(
        default=10,
        ge=3,
        le=60,
        description="Connection timeout in seconds"
    )
    read_timeout: int = Field(
        default=20,
        ge=5,
        le=120,
        description="Read timeout in seconds"
    )
    
    # Retry settings
    retry_enabled: bool = Field(
        default=True,
        description="Enable automatic retries on failure"
    )
    retry_count: int = Field(
        default=3,
        ge=1,
        le=10,
        description="Number of retry attempts"
    )
    retry_delay: int = Field(
        default=5,
        ge=1,
        le=60,
        description="Delay between retries in seconds"
    )
    retry_backoff_factor: float = Field(
        default=2.0,
        ge=1.0,
        le=5.0,
        description="Exponential backoff multiplier"
    )
    
    # Alert settings
    alert_on_first_failure: bool = Field(
        default=False,
        description="Send alert on first failure (vs consecutive)"
    )
    consecutive_failures_threshold: int = Field(
        default=3,
        ge=1,
        le=10,
        description="Number of consecutive failures before alert"
    )
    alert_cooldown: int = Field(
        default=300,  # 5 minutes
        ge=60,
        le=3600,
        description="Minimum time between duplicate alerts"
    )
    recovery_alert: bool = Field(
        default=True,
        description="Send alert when service recovers"
    )
    
    # Concurrency settings
    max_concurrent_pings: int = Field(
        default=50,
        ge=1,
        le=500,
        description="Maximum concurrent ping operations"
    )
    batch_size: int = Field(
        default=100,
        ge=10,
        le=1000,
        description="Batch size for ping operations"
    )
    
    # User agent settings
    user_agent: str = Field(
        default="UptimeBot/1.0 (Compatible; Monitoring Service)",
        description="User agent string for HTTP requests"
    )
    random_user_agent: bool = Field(
        default=False,
        description="Use random user agents for requests"
    )
    
    # SSL settings
    verify_ssl: bool = Field(
        default=True,
        description="Verify SSL certificates"
    )
    ssl_error_as_down: bool = Field(
        default=True,
        description="Treat SSL errors as service down"
    )
    
    # Status code settings
    expected_status_codes: Set[int] = Field(
        default_factory=lambda: {200, 201, 202, 204, 301, 302, 307, 308},
        description="HTTP status codes considered as 'up'"
    )
    
    # Content validation
    content_validation_enabled: bool = Field(
        default=False,
        description="Enable response content validation"
    )
    
    # Metrics and statistics
    keep_ping_history_days: int = Field(
        default=30,
        ge=1,
        le=365,
        description="Days to keep ping history"
    )
    statistics_aggregation_interval: int = Field(
        default=3600,  # 1 hour
        ge=300,
        le=86400,
        description="Interval for statistics aggregation"
    )
    
    @field_validator("expected_status_codes", mode="before")
    @classmethod
    def parse_status_codes(cls, v: Any) -> Set[int]:
        """Parse expected status codes from string or list."""
        if isinstance(v, str):
            return {int(x.strip()) for x in v.split(",") if x.strip()}
        
        if isinstance(v, (list, set, tuple)):
            return {int(x) for x in v}
        
        return v
    
    @model_validator(mode="after")
    def validate_intervals(self) -> "MonitoringSettings":
        """Validate interval relationships."""
        if self.min_interval > self.max_interval:
            raise ValueError("min_interval cannot be greater than max_interval")
        
        if not (self.min_interval <= self.default_interval <= self.max_interval):
            raise ValueError("default_interval must be between min and max")
        
        return self
    
    def validate_interval(self, interval: int) -> int:
        """Validate and clamp interval to allowed range."""
        return max(self.min_interval, min(interval, self.max_interval))


class LoggingSettings(BaseSettingsConfig):
    """
    Logging Configuration Settings
    
    Comprehensive logging configuration with support for
    file logging, rotation, and structured output.
    """
    
    model_config = SettingsConfigDict(
        env_prefix="LOG_",
        env_file=".env"
    )
    
    # General settings
    level: LogLevel = Field(
        default=LogLevel.INFO,
        description="Minimum logging level"
    )
    format: str = Field(
        default="%(asctime)s | %(levelname)-8s | %(name)s:%(funcName)s:%(lineno)d - %(message)s",
        description="Log message format"
    )
    date_format: str = Field(
        default="%Y-%m-%d %H:%M:%S",
        description="Date format in log messages"
    )
    
    # Console logging
    console_enabled: bool = Field(
        default=True,
        description="Enable console logging"
    )
    console_colored: bool = Field(
        default=True,
        description="Enable colored console output"
    )
    console_rich: bool = Field(
        default=True,
        description="Use rich library for console output"
    )
    
    # File logging
    file_enabled: bool = Field(
        default=True,
        description="Enable file logging"
    )
    file_path: Path = Field(
        default=Path("logs/uptime_bot.log"),
        description="Log file path"
    )
    file_rotation: str = Field(
        default="10 MB",
        description="Log rotation size (e.g., '10 MB', '1 day')"
    )
    file_retention: str = Field(
        default="30 days",
        description="Log retention period"
    )
    file_compression: str = Field(
        default="gz",
        description="Compression format for rotated logs"
    )
    
    # Error logging (separate file for errors)
    error_file_enabled: bool = Field(
        default=True,
        description="Enable separate error log file"
    )
    error_file_path: Path = Field(
        default=Path("logs/errors.log"),
        description="Error log file path"
    )
    
    # Ping logging (detailed ping history)
    ping_log_enabled: bool = Field(
        default=True,
        description="Enable detailed ping logging"
    )
    ping_log_path: Path = Field(
        default=Path("logs/pings.log"),
        description="Ping log file path"
    )
    
    # JSON logging
    json_enabled: bool = Field(
        default=False,
        description="Enable JSON formatted logging"
    )
    json_file_path: Path = Field(
        default=Path("logs/uptime_bot.json"),
        description="JSON log file path"
    )
    
    # Performance logging
    slow_request_threshold: float = Field(
        default=5.0,
        ge=0.1,
        le=60.0,
        description="Threshold for slow request logging (seconds)"
    )
    log_request_body: bool = Field(
        default=False,
        description="Log request bodies (may contain sensitive data)"
    )
    log_response_body: bool = Field(
        default=False,
        description="Log response bodies"
    )
    
    # Debug options
    log_sql_queries: bool = Field(
        default=False,
        description="Log SQL queries (debug mode)"
    )
    log_api_calls: bool = Field(
        default=False,
        description="Log Telegram API calls"
    )
    
    @field_validator("file_path", "error_file_path", "ping_log_path", "json_file_path")
    @classmethod
    def ensure_log_directory(cls, v: Path) -> Path:
        """Ensure log directory exists."""
        v.parent.mkdir(parents=True, exist_ok=True)
        return v


class CacheSettings(BaseSettingsConfig):
    """
    Caching Configuration Settings
    
    Supports Redis and in-memory caching with configurable
    TTL and eviction policies.
    """
    
    model_config = SettingsConfigDict(
        env_prefix="CACHE_",
        env_file=".env"
    )
    
    # Cache backend
    enabled: bool = Field(
        default=True,
        description="Enable caching"
    )
    backend: str = Field(
        default="memory",
        description="Cache backend: 'memory' or 'redis'"
    )
    
    # Redis settings
    redis_url: Optional[str] = Field(
        default=None,
        description="Redis connection URL"
    )
    redis_host: str = Field(
        default="localhost",
        description="Redis host"
    )
    redis_port: int = Field(
        default=6379,
        ge=1,
        le=65535,
        description="Redis port"
    )
    redis_password: Optional[SecretStr] = Field(
        default=None,
        description="Redis password"
    )
    redis_db: int = Field(
        default=0,
        ge=0,
        le=15,
        description="Redis database number"
    )
    redis_ssl: bool = Field(
        default=False,
        description="Use SSL for Redis connection"
    )
    
    # TTL settings
    default_ttl: int = Field(
        default=300,  # 5 minutes
        ge=1,
        le=86400,
        description="Default cache TTL in seconds"
    )
    user_ttl: int = Field(
        default=600,  # 10 minutes
        ge=1,
        le=86400,
        description="User data cache TTL"
    )
    link_ttl: int = Field(
        default=300,  # 5 minutes
        ge=1,
        le=86400,
        description="Link data cache TTL"
    )
    stats_ttl: int = Field(
        default=60,  # 1 minute
        ge=1,
        le=3600,
        description="Statistics cache TTL"
    )
    
    # Memory cache settings
    memory_max_size: int = Field(
        default=10000,
        ge=100,
        le=1000000,
        description="Maximum items in memory cache"
    )
    memory_eviction_policy: str = Field(
        default="lru",
        description="Eviction policy: 'lru', 'lfu', 'fifo'"
    )
    
    # Key prefix
    key_prefix: str = Field(
        default="uptimebot:",
        description="Prefix for all cache keys"
    )
    
    @property
    def redis_connection_url(self) -> str:
        """Generate Redis connection URL."""
        if self.redis_url:
            return self.redis_url
        
        password_part = ""
        if self.redis_password:
            password_part = f":{self.redis_password.get_secret_value()}@"
        
        protocol = "rediss" if self.redis_ssl else "redis"
        
        return f"{protocol}://{password_part}{self.redis_host}:{self.redis_port}/{self.redis_db}"


class SecuritySettings(BaseSettingsConfig):
    """
    Security Configuration Settings
    
    Manages encryption, authentication, and security policies.
    """
    
    model_config = SettingsConfigDict(
        env_prefix="SECURITY_",
        env_file=".env"
    )
    
    # Encryption
    secret_key: SecretStr = Field(
        default_factory=lambda: SecretStr(secrets.token_hex(32)),
        description="Secret key for encryption"
    )
    encryption_algorithm: str = Field(
        default="AES-256-GCM",
        description="Encryption algorithm"
    )
    
    # Token settings
    token_expiry: int = Field(
        default=3600,  # 1 hour
        ge=60,
        le=86400,
        description="API token expiry in seconds"
    )
    refresh_token_expiry: int = Field(
        default=604800,  # 7 days
        ge=3600,
        le=2592000,
        description="Refresh token expiry in seconds"
    )
    
    # IP-based security
    ip_whitelist_enabled: bool = Field(
        default=False,
        description="Enable IP whitelist"
    )
    ip_whitelist: Set[str] = Field(
        default_factory=set,
        description="Whitelisted IP addresses"
    )
    ip_blacklist_enabled: bool = Field(
        default=False,
        description="Enable IP blacklist"
    )
    ip_blacklist: Set[str] = Field(
        default_factory=set,
        description="Blacklisted IP addresses"
    )
    
    # Anti-abuse
    max_failed_attempts: int = Field(
        default=5,
        ge=1,
        le=20,
        description="Maximum failed attempts before lockout"
    )
    lockout_duration: int = Field(
        default=900,  # 15 minutes
        ge=60,
        le=86400,
        description="Lockout duration in seconds"
    )
    
    # Content security
    allowed_url_schemes: Set[str] = Field(
        default_factory=lambda: {"http", "https"},
        description="Allowed URL schemes for monitoring"
    )
    block_private_ips: bool = Field(
        default=True,
        description="Block monitoring of private IP addresses"
    )
    block_localhost: bool = Field(
        default=True,
        description="Block monitoring of localhost"
    )
    
    # Request validation
    validate_url_dns: bool = Field(
        default=True,
        description="Validate URL DNS resolution"
    )
    max_url_length: int = Field(
        default=2048,
        ge=50,
        le=8192,
        description="Maximum URL length"
    )
    
    @field_validator("ip_whitelist", "ip_blacklist", mode="before")
    @classmethod
    def parse_ip_list(cls, v: Any) -> Set[str]:
        """Parse IP list from string or list."""
        if isinstance(v, str):
            return {x.strip() for x in v.split(",") if x.strip()}
        
        if isinstance(v, (list, set, tuple)):
            return set(v)
        
        return set()


class Settings(BaseSettingsConfig):
    """
    Main Settings Class
    
    Aggregates all settings sections and provides the main
    configuration interface for the application.
    """
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8"
    )
    
    # Environment
    environment: Environment = Field(
        default=Environment.DEVELOPMENT,
        description="Application environment"
    )
    debug: bool = Field(
        default=False,
        description="Enable debug mode"
    )
    
    # Application info
    app_name: str = Field(
        default="Uptime Bot",
        description="Application name"
    )
    app_version: str = Field(
        default="1.0.0",
        description="Application version"
    )
    
    # Timezone
    timezone: str = Field(
        default="UTC",
        description="Application timezone"
    )
    
    # Web server (for health checks)
    web_host: str = Field(
        default="0.0.0.0",
        description="Web server host"
    )
    web_port: int = Field(
        default=8080,
        ge=1,
        le=65535,
        description="Web server port"
    )
    
    # Nested settings
    database: DatabaseSettings = Field(
        default_factory=DatabaseSettings
    )
    bot: BotSettings = Field(
        default_factory=BotSettings
    )
    monitoring: MonitoringSettings = Field(
        default_factory=MonitoringSettings
    )
    logging: LoggingSettings = Field(
        default_factory=LoggingSettings
    )
    cache: CacheSettings = Field(
        default_factory=CacheSettings
    )
    security: SecuritySettings = Field(
        default_factory=SecuritySettings
    )
    
    @property
    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.environment == Environment.PRODUCTION
    
    @property
    def is_development(self) -> bool:
        """Check if running in development environment."""
        return self.environment == Environment.DEVELOPMENT
    
    @property
    def is_testing(self) -> bool:
        """Check if running in testing environment."""
        return self.environment == Environment.TESTING
    
    @model_validator(mode="after")
    def configure_for_environment(self) -> "Settings":
        """Apply environment-specific configuration."""
        if self.is_production:
            # Force secure defaults in production
            self.debug = False
            self.database.echo = False
            self.logging.log_sql_queries = False
            self.logging.log_request_body = False
            self.logging.log_response_body = False
        
        elif self.is_development:
            # Development defaults
            if self.logging.level == LogLevel.INFO:
                self.logging.level = LogLevel.DEBUG
        
        return self
    
    def to_dict(self, *, exclude_secrets: bool = True) -> Dict[str, Any]:
        """Convert settings to dictionary."""
        data = self.model_dump()
        
        if exclude_secrets:
            # Remove sensitive values
            def remove_secrets(obj: Any) -> Any:
                if isinstance(obj, dict):
                    return {
                        k: remove_secrets(v)
                        for k, v in obj.items()
                        if "password" not in k.lower()
                        and "secret" not in k.lower()
                        and "token" not in k.lower()
                    }
                elif isinstance(obj, list):
                    return [remove_secrets(item) for item in obj]
                return obj
            
            data = remove_secrets(data)
        
        return data


@lru_cache()
def get_settings() -> Settings:
    """
    Get cached settings instance.
    
    This function is cached to ensure a single settings instance
    is used throughout the application lifecycle.
    
    Returns:
        Settings: Application settings instance
    """
    return Settings()


# Global settings instance
settings = get_settings()
