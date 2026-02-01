"""
Base Exception Classes for Uptime Bot

Provides the foundation exception hierarchy from which all
other exceptions inherit.
"""

from __future__ import annotations

from typing import Any, Dict, Optional, Type
from datetime import datetime
import traceback
import sys


class UptimeBotException(Exception):
    """
    Base Exception Class
    
    All custom exceptions in the Uptime Bot application inherit
    from this class. Provides common functionality for error
    handling, logging, and serialization.
    
    Attributes:
        message: Human-readable error message
        error_code: Numeric error code for categorization
        details: Additional error details as dictionary
        timestamp: When the exception occurred
        traceback_str: String representation of the traceback
        recoverable: Whether the error is recoverable
        notify_admin: Whether admin should be notified
    """
    
    # Default error code
    default_error_code: int = 1000
    
    # Default recoverability
    default_recoverable: bool = True
    
    # Default admin notification
    default_notify_admin: bool = False
    
    def __init__(
        self,
        message: str = "An error occurred",
        error_code: Optional[int] = None,
        details: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None,
        recoverable: Optional[bool] = None,
        notify_admin: Optional[bool] = None
    ) -> None:
        """
        Initialize the exception.
        
        Args:
            message: Human-readable error message
            error_code: Numeric error code
            details: Additional error details
            cause: The underlying exception that caused this one
            recoverable: Whether the error is recoverable
            notify_admin: Whether admin should be notified
        """
        super().__init__(message)
        
        self.message = message
        self.error_code = error_code or self.default_error_code
        self.details = details or {}
        self.cause = cause
        self.recoverable = recoverable if recoverable is not None else self.default_recoverable
        self.notify_admin = notify_admin if notify_admin is not None else self.default_notify_admin
        self.timestamp = datetime.utcnow()
        
        # Capture traceback
        self.traceback_str = self._capture_traceback()
        
        # Store the original exception info
        self._exc_info = sys.exc_info()
    
    def _capture_traceback(self) -> str:
        """Capture the current traceback as a string."""
        return "".join(traceback.format_exception(*sys.exc_info()))
    
    @property
    def full_message(self) -> str:
        """Get full error message with code."""
        return f"[{self.error_code}] {self.message}"
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert exception to dictionary for logging/serialization.
        
        Returns:
            Dictionary representation of the exception
        """
        return {
            "type": self.__class__.__name__,
            "message": self.message,
            "error_code": self.error_code,
            "details": self.details,
            "timestamp": self.timestamp.isoformat(),
            "recoverable": self.recoverable,
            "notify_admin": self.notify_admin,
            "cause": str(self.cause) if self.cause else None,
            "traceback": self.traceback_str if not self.recoverable else None
        }
    
    def log_format(self) -> str:
        """
        Format exception for logging.
        
        Returns:
            Formatted string for logging
        """
        parts = [
            f"Exception: {self.__class__.__name__}",
            f"Code: {self.error_code}",
            f"Message: {self.message}"
        ]
        
        if self.details:
            parts.append(f"Details: {self.details}")
        
        if self.cause:
            parts.append(f"Cause: {self.cause}")
        
        return " | ".join(parts)
    
    def user_message(self) -> str:
        """
        Get user-friendly error message.
        
        Returns:
            Message suitable for displaying to users
        """
        return self.message
    
    def with_details(self, **kwargs: Any) -> "UptimeBotException":
        """
        Add additional details to the exception.
        
        Args:
            **kwargs: Key-value pairs to add to details
            
        Returns:
            Self for chaining
        """
        self.details.update(kwargs)
        return self
    
    @classmethod
    def from_exception(
        cls,
        exception: Exception,
        message: Optional[str] = None,
        **kwargs: Any
    ) -> "UptimeBotException":
        """
        Create from another exception.
        
        Args:
            exception: The original exception
            message: Override message (uses original if not provided)
            **kwargs: Additional arguments for the exception
            
        Returns:
            New exception instance
        """
        return cls(
            message=message or str(exception),
            cause=exception,
            **kwargs
        )
    
    def __str__(self) -> str:
        """String representation."""
        return self.full_message
    
    def __repr__(self) -> str:
        """Detailed string representation."""
        return (
            f"{self.__class__.__name__}("
            f"message={self.message!r}, "
            f"error_code={self.error_code}, "
            f"details={self.details})"
        )


class UptimeBotError(UptimeBotException):
    """
    General Error Class
    
    Used for general application errors that don't fit
    into more specific categories.
    """
    
    default_error_code = 1001


class ConfigurationError(UptimeBotException):
    """
    Configuration Error
    
    Raised when there are issues with application configuration,
    environment variables, or settings files.
    """
    
    default_error_code = 1100
    default_recoverable = False
    default_notify_admin = True
    
    def __init__(
        self,
        message: str,
        config_key: Optional[str] = None,
        expected_type: Optional[Type] = None,
        **kwargs: Any
    ) -> None:
        """
        Initialize configuration error.
        
        Args:
            message: Error message
            config_key: The configuration key that caused the error
            expected_type: The expected type for the configuration value
            **kwargs: Additional arguments
        """
        super().__init__(message, **kwargs)
        
        if config_key:
            self.details["config_key"] = config_key
        
        if expected_type:
            self.details["expected_type"] = expected_type.__name__


class InitializationError(UptimeBotException):
    """
    Initialization Error
    
    Raised when the application fails to initialize properly.
    This includes database connections, bot setup, etc.
    """
    
    default_error_code = 1200
    default_recoverable = False
    default_notify_admin = True
    
    def __init__(
        self,
        message: str,
        component: Optional[str] = None,
        **kwargs: Any
    ) -> None:
        """
        Initialize initialization error.
        
        Args:
            message: Error message
            component: The component that failed to initialize
            **kwargs: Additional arguments
        """
        super().__init__(message, **kwargs)
        
        if component:
            self.details["component"] = component


class ShutdownError(UptimeBotException):
    """
    Shutdown Error
    
    Raised when the application fails to shut down gracefully.
    """
    
    default_error_code = 1300
    default_recoverable = False
    
    def __init__(
        self,
        message: str,
        component: Optional[str] = None,
        **kwargs: Any
    ) -> None:
        """
        Initialize shutdown error.
        
        Args:
            message: Error message
            component: The component that failed to shutdown
            **kwargs: Additional arguments
        """
        super().__init__(message, **kwargs)
        
        if component:
            self.details["component"] = component


class PermissionError(UptimeBotException):
    """
    Permission Error
    
    Raised when a user attempts an action they don't have
    permission to perform.
    """
    
    default_error_code = 1400
    default_recoverable = True
    
    def __init__(
        self,
        message: str = "Permission denied",
        required_role: Optional[str] = None,
        user_role: Optional[str] = None,
        action: Optional[str] = None,
        **kwargs: Any
    ) -> None:
        """
        Initialize permission error.
        
        Args:
            message: Error message
            required_role: The role required for the action
            user_role: The user's current role
            action: The action that was denied
            **kwargs: Additional arguments
        """
        super().__init__(message, **kwargs)
        
        if required_role:
            self.details["required_role"] = required_role
        
        if user_role:
            self.details["user_role"] = user_role
        
        if action:
            self.details["action"] = action
    
    def user_message(self) -> str:
        """Get user-friendly error message."""
        if "required_role" in self.details:
            return f"This action requires {self.details['required_role']} role."
        return "You don't have permission to perform this action."


class RateLimitError(UptimeBotException):
    """
    Rate Limit Error
    
    Raised when a user exceeds rate limits.
    """
    
    default_error_code = 1500
    default_recoverable = True
    
    def __init__(
        self,
        message: str = "Rate limit exceeded",
        retry_after: Optional[int] = None,
        limit: Optional[int] = None,
        window: Optional[int] = None,
        **kwargs: Any
    ) -> None:
        """
        Initialize rate limit error.
        
        Args:
            message: Error message
            retry_after: Seconds until the rate limit resets
            limit: The rate limit that was exceeded
            window: The time window for the rate limit
            **kwargs: Additional arguments
        """
        super().__init__(message, **kwargs)
        
        self.retry_after = retry_after
        
        if retry_after:
            self.details["retry_after"] = retry_after
        
        if limit:
            self.details["limit"] = limit
        
        if window:
            self.details["window"] = window
    
    def user_message(self) -> str:
        """Get user-friendly error message."""
        if self.retry_after:
            return f"Please wait {self.retry_after} seconds before trying again."
        return "You're doing that too fast. Please slow down."


class MaintenanceError(UptimeBotException):
    """
    Maintenance Error
    
    Raised when the bot is in maintenance mode.
    """
    
    default_error_code = 1600
    default_recoverable = True
    
    def __init__(
        self,
        message: str = "Bot is under maintenance",
        estimated_end: Optional[datetime] = None,
        **kwargs: Any
    ) -> None:
        """
        Initialize maintenance error.
        
        Args:
            message: Error message
            estimated_end: Estimated end time of maintenance
            **kwargs: Additional arguments
        """
        super().__init__(message, **kwargs)
        
        if estimated_end:
            self.details["estimated_end"] = estimated_end.isoformat()
    
    def user_message(self) -> str:
        """Get user-friendly error message."""
        if "estimated_end" in self.details:
            return f"Bot is under maintenance. Expected back: {self.details['estimated_end']}"
        return "Bot is currently under maintenance. Please try again later."
