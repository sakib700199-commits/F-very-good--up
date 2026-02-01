"""
Validation Exception Classes for Uptime Bot

Provides specialized exceptions for data validation errors
including URL validation, user input validation, and format errors.
"""

from __future__ import annotations

from typing import Any, List, Optional, Type, Union
from exceptions.base import UptimeBotException


class ValidationException(UptimeBotException):
    """
    Base Validation Exception
    
    Parent class for all validation-related exceptions.
    """
    
    default_error_code = 3000
    default_recoverable = True
    default_notify_admin = False
    
    def __init__(
        self,
        message: str,
        field: Optional[str] = None,
        value: Optional[Any] = None,
        **kwargs: Any
    ) -> None:
        """
        Initialize validation exception.
        
        Args:
            message: Error message
            field: The field that failed validation
            value: The invalid value (sanitized)
            **kwargs: Additional arguments
        """
        super().__init__(message, **kwargs)
        
        if field:
            self.details["field"] = field
        
        if value is not None:
            self.details["value"] = self._sanitize_value(value)
    
    @staticmethod
    def _sanitize_value(value: Any) -> str:
        """
        Sanitize value for logging.
        
        Args:
            value: The value to sanitize
            
        Returns:
            Sanitized string representation
        """
        str_value = str(value)
        
        # Truncate long values
        if len(str_value) > 100:
            str_value = str_value[:100] + "..."
        
        return str_value


class InvalidURLError(ValidationException):
    """
    Invalid URL Error
    
    Raised when a provided URL is invalid or malformed.
    """
    
    default_error_code = 3001
    
    def __init__(
        self,
        message: str = "Invalid URL format",
        url: Optional[str] = None,
        reason: Optional[str] = None,
        **kwargs: Any
    ) -> None:
        """
        Initialize invalid URL error.
        
        Args:
            message: Error message
            url: The invalid URL
            reason: Specific reason for invalidity
            **kwargs: Additional arguments
        """
        super().__init__(message, field="url", value=url, **kwargs)
        
        if reason:
            self.details["reason"] = reason
    
    def user_message(self) -> str:
        """Get user-friendly error message."""
        reasons = {
            "no_scheme": "URL must start with http:// or https://",
            "invalid_domain": "The domain name is invalid",
            "private_ip": "Private IP addresses are not allowed",
            "localhost": "Localhost URLs are not allowed",
            "too_long": "URL is too long (max 2048 characters)",
            "blocked_domain": "This domain is not allowed"
        }
        
        reason = self.details.get("reason", "")
        return reasons.get(reason, "Please provide a valid URL (e.g., https://example.com)")


class InvalidIntervalError(ValidationException):
    """
    Invalid Interval Error
    
    Raised when a provided time interval is invalid.
    """
    
    default_error_code = 3002
    
    def __init__(
        self,
        message: str = "Invalid interval",
        interval: Optional[int] = None,
        min_interval: Optional[int] = None,
        max_interval: Optional[int] = None,
        **kwargs: Any
    ) -> None:
        """
        Initialize invalid interval error.
        
        Args:
            message: Error message
            interval: The invalid interval value
            min_interval: Minimum allowed interval
            max_interval: Maximum allowed interval
            **kwargs: Additional arguments
        """
        super().__init__(message, field="interval", value=interval, **kwargs)
        
        if min_interval is not None:
            self.details["min_interval"] = min_interval
        
        if max_interval is not None:
            self.details["max_interval"] = max_interval
    
    def user_message(self) -> str:
        """Get user-friendly error message."""
        min_val = self.details.get("min_interval")
        max_val = self.details.get("max_interval")
        
        if min_val and max_val:
            return f"Interval must be between {min_val} and {max_val} seconds."
        
        return "Please provide a valid interval."


class InvalidUserDataError(ValidationException):
    """
    Invalid User Data Error
    
    Raised when user-provided data is invalid.
    """
    
    default_error_code = 3003
    
    def __init__(
        self,
        message: str = "Invalid user data",
        errors: Optional[List[str]] = None,
        **kwargs: Any
    ) -> None:
        """
        Initialize invalid user data error.
        
        Args:
            message: Error message
            errors: List of validation errors
            **kwargs: Additional arguments
        """
        super().__init__(message, **kwargs)
        
        if errors:
            self.details["errors"] = errors
    
    def user_message(self) -> str:
        """Get user-friendly error message."""
        errors = self.details.get("errors", [])
        
        if errors:
            return "Invalid data:\n" + "\n".join(f"• {e}" for e in errors[:5])
        
        return "The provided data is invalid."


class MissingFieldError(ValidationException):
    """
    Missing Field Error
    
    Raised when a required field is missing.
    """
    
    default_error_code = 3004
    
    def __init__(
        self,
        message: str = "Required field is missing",
        field: str = "unknown",
        **kwargs: Any
    ) -> None:
        """
        Initialize missing field error.
        
        Args:
            message: Error message
            field: The missing field name
            **kwargs: Additional arguments
        """
        super().__init__(message, field=field, **kwargs)
    
    def user_message(self) -> str:
        """Get user-friendly error message."""
        field = self.details.get("field", "field")
        return f"The {field} is required."


class FieldTooLongError(ValidationException):
    """
    Field Too Long Error
    
    Raised when a field exceeds maximum length.
    """
    
    default_error_code = 3005
    
    def __init__(
        self,
        message: str = "Field exceeds maximum length",
        field: Optional[str] = None,
        max_length: Optional[int] = None,
        actual_length: Optional[int] = None,
        **kwargs: Any
    ) -> None:
        """
        Initialize field too long error.
        
        Args:
            message: Error message
            field: The field name
            max_length: Maximum allowed length
            actual_length: Actual length of the value
            **kwargs: Additional arguments
        """
        super().__init__(message, field=field, **kwargs)
        
        if max_length is not None:
            self.details["max_length"] = max_length
        
        if actual_length is not None:
            self.details["actual_length"] = actual_length
    
    def user_message(self) -> str:
        """Get user-friendly error message."""
        field = self.details.get("field", "Field")
        max_len = self.details.get("max_length", "unknown")
        return f"{field.capitalize()} must be {max_len} characters or less."


class InvalidFormatError(ValidationException):
    """
    Invalid Format Error
    
    Raised when data doesn't match expected format.
    """
    
    default_error_code = 3006
    
    def __init__(
        self,
        message: str = "Invalid format",
        field: Optional[str] = None,
        expected_format: Optional[str] = None,
        example: Optional[str] = None,
        **kwargs: Any
    ) -> None:
        """
        Initialize invalid format error.
        
        Args:
            message: Error message
            field: The field name
            expected_format: Description of expected format
            example: Example of valid format
            **kwargs: Additional arguments
        """
        super().__init__(message, field=field, **kwargs)
        
        if expected_format:
            self.details["expected_format"] = expected_format
        
        if example:
            self.details["example"] = example
    
    def user_message(self) -> str:
        """Get user-friendly error message."""
        field = self.details.get("field", "Value")
        expected = self.details.get("expected_format", "correct format")
        example = self.details.get("example")
        
        msg = f"{field.capitalize()} must be in {expected}."
        
        if example:
            msg += f"\nExample: {example}"
        
        return msg


class MultipleValidationErrors(ValidationException):
    """
    Multiple Validation Errors
    
    Container for multiple validation errors.
    """
    
    default_error_code = 3100
    
    def __init__(
        self,
        message: str = "Multiple validation errors occurred",
        errors: Optional[List[ValidationException]] = None,
        **kwargs: Any
    ) -> None:
        """
        Initialize multiple validation errors.
        
        Args:
            message: Error message
            errors: List of validation exceptions
            **kwargs: Additional arguments
        """
        super().__init__(message, **kwargs)
        
        self.errors = errors or []
        
        if errors:
            self.details["error_count"] = len(errors)
            self.details["fields"] = [
                e.details.get("field", "unknown") 
                for e in errors 
                if hasattr(e, "details")
            ]
    
    def add_error(self, error: ValidationException) -> None:
        """Add an error to the collection."""
        self.errors.append(error)
        self.details["error_count"] = len(self.errors)
    
    def user_message(self) -> str:
        """Get user-friendly error message."""
        if not self.errors:
            return "Validation failed."
        
        messages = [e.user_message() for e in self.errors[:5]]
        
        result = "Please fix the following errors:\n"
        result += "\n".join(f"• {m}" for m in messages)
        
        if len(self.errors) > 5:
            result += f"\n... and {len(self.errors) - 5} more errors."
        
        return result
    
    def __len__(self) -> int:
        """Return number of errors."""
        return len(self.errors)
    
    def __bool__(self) -> bool:
        """Return True if there are errors."""
        return len(self.errors) > 0
