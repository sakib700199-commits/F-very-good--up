"""
Exceptions Package for Uptime Bot

Provides a comprehensive exception hierarchy for error handling
throughout the application.
"""

from exceptions.base import (
    UptimeBotException,
    UptimeBotError,
    ConfigurationError,
    InitializationError,
    ShutdownError
)

from exceptions.database import (
    DatabaseException,
    DatabaseConnectionError,
    DatabaseQueryError,
    DatabaseNotFoundError,
    DatabaseDuplicateError,
    DatabaseIntegrityError,
    DatabaseTimeoutError,
    DatabaseMigrationError
)

from exceptions.validation import (
    ValidationException,
    InvalidURLError,
    InvalidIntervalError,
    InvalidUserDataError,
    MissingFieldError,
    FieldTooLongError,
    InvalidFormatError
)

from exceptions.monitoring import (
    MonitoringException,
    PingException,
    PingTimeoutError,
    PingConnectionError,
    SSLCertificateError,
    DNSResolutionError,
    HTTPError,
    RateLimitExceededError,
    ServiceUnavailableError
)

__all__ = [
    # Base exceptions
    "UptimeBotException",
    "UptimeBotError",
    "ConfigurationError",
    "InitializationError",
    "ShutdownError",
    
    # Database exceptions
    "DatabaseException",
    "DatabaseConnectionError",
    "DatabaseQueryError",
    "DatabaseNotFoundError",
    "DatabaseDuplicateError",
    "DatabaseIntegrityError",
    "DatabaseTimeoutError",
    "DatabaseMigrationError",
    
    # Validation exceptions
    "ValidationException",
    "InvalidURLError",
    "InvalidIntervalError",
    "InvalidUserDataError",
    "MissingFieldError",
    "FieldTooLongError",
    "InvalidFormatError",
    
    # Monitoring exceptions
    "MonitoringException",
    "PingException",
    "PingTimeoutError",
    "PingConnectionError",
    "SSLCertificateError",
    "DNSResolutionError",
    "HTTPError",
    "RateLimitExceededError",
    "ServiceUnavailableError"
]
