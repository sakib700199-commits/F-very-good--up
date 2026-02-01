"""
============================================================================
TELEGRAM UPTIME BOT - VALIDATORS UTILITY
============================================================================
Comprehensive validation functions for URLs, data, and user input.

Author: Professional Development Team
Version: 1.0.0
License: MIT
============================================================================
"""

import re
from typing import Optional, Dict, Any, List
from urllib.parse import urlparse
import validators as external_validators
import ipaddress

from utils.logger import get_logger


logger = get_logger(__name__)


# ============================================================================
# URL VALIDATORS
# ============================================================================

class URLValidator:
    """
    Comprehensive URL validation and parsing.
    """

    # URL regex pattern
    URL_PATTERN = re.compile(
        r'^https?://'  # http:// or https://
        r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'  # domain
        r'localhost|'  # localhost
        r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # or IP
        r'(?::\d+)?'  # optional port
        r'(?:/?|[/?]\S+)$', re.IGNORECASE
    )

    @staticmethod
    def is_valid_url(url: str) -> bool:
        """
        Check if URL is valid.

        Args:
            url: URL to validate

        Returns:
            True if valid, False otherwise
        """
        try:
            # Basic format check
            if not URLValidator.URL_PATTERN.match(url):
                return False

            # Use external validator
            result = external_validators.url(url)
            return result is True

        except Exception as e:
            logger.debug(f"URL validation error: {e}")
            return False

    @staticmethod
    def is_valid_domain(domain: str) -> bool:
        """
        Check if domain is valid.

        Args:
            domain: Domain to validate

        Returns:
            True if valid, False otherwise
        """
        try:
            result = external_validators.domain(domain)
            return result is True
        except:
            return False

    @staticmethod
    def is_valid_ip(ip: str) -> bool:
        """
        Check if IP address is valid.

        Args:
            ip: IP address to validate

        Returns:
            True if valid, False otherwise
        """
        try:
            ipaddress.ip_address(ip)
            return True
        except ValueError:
            return False

    @staticmethod
    def parse_url(url: str) -> Optional[Dict[str, Any]]:
        """
        Parse URL into components.

        Args:
            url: URL to parse

        Returns:
            Dictionary with URL components or None if invalid
        """
        try:
            if not URLValidator.is_valid_url(url):
                return None

            parsed = urlparse(url)
            return {
                "scheme": parsed.scheme,
                "netloc": parsed.netloc,
                "hostname": parsed.hostname,
                "port": parsed.port,
                "path": parsed.path,
                "params": parsed.params,
                "query": parsed.query,
                "fragment": parsed.fragment,
                "full_url": url
            }
        except Exception as e:
            logger.error(f"URL parsing error: {e}")
            return None

    @staticmethod
    def normalize_url(url: str) -> Optional[str]:
        """
        Normalize URL (add scheme if missing, remove trailing slash, etc.).

        Args:
            url: URL to normalize

        Returns:
            Normalized URL or None if invalid
        """
        try:
            # Add scheme if missing
            if not url.startswith(('http://', 'https://')):
                url = 'https://' + url

            parsed = urlparse(url)

            # Rebuild URL
            normalized = f"{parsed.scheme}://{parsed.netloc}"

            # Add path if exists
            if parsed.path and parsed.path != '/':
                normalized += parsed.path.rstrip('/')

            # Add query if exists
            if parsed.query:
                normalized += f"?{parsed.query}"

            # Validate normalized URL
            if URLValidator.is_valid_url(normalized):
                return normalized

            return None

        except Exception as e:
            logger.error(f"URL normalization error: {e}")
            return None

    @staticmethod
    def extract_domain(url: str) -> Optional[str]:
        """
        Extract domain from URL.

        Args:
            url: URL to extract domain from

        Returns:
            Domain or None if invalid
        """
        try:
            parsed = urlparse(url)
            return parsed.netloc or None
        except:
            return None


# ============================================================================
# DATA VALIDATORS
# ============================================================================

class DataValidator:
    """
    General data validation utilities.
    """

    @staticmethod
    def is_valid_telegram_id(user_id: Any) -> bool:
        """
        Check if Telegram user ID is valid.

        Args:
            user_id: User ID to validate

        Returns:
            True if valid, False otherwise
        """
        try:
            uid = int(user_id)
            # Telegram IDs are positive integers
            return uid > 0
        except (ValueError, TypeError):
            return False

    @staticmethod
    def is_valid_interval(interval: Any, min_val: int = 60, max_val: int = 86400) -> bool:
        """
        Check if ping interval is valid.

        Args:
            interval: Interval to validate
            min_val: Minimum allowed value
            max_val: Maximum allowed value

        Returns:
            True if valid, False otherwise
        """
        try:
            interval = int(interval)
            return min_val <= interval <= max_val
        except (ValueError, TypeError):
            return False

    @staticmethod
    def is_valid_timeout(timeout: Any, min_val: int = 5, max_val: int = 300) -> bool:
        """
        Check if timeout is valid.

        Args:
            timeout: Timeout to validate
            min_val: Minimum allowed value
            max_val: Maximum allowed value

        Returns:
            True if valid, False otherwise
        """
        try:
            timeout = int(timeout)
            return min_val <= timeout <= max_val
        except (ValueError, TypeError):
            return False

    @staticmethod
    def is_valid_email(email: str) -> bool:
        """
        Check if email is valid.

        Args:
            email: Email to validate

        Returns:
            True if valid, False otherwise
        """
        try:
            result = external_validators.email(email)
            return result is True
        except:
            return False

    @staticmethod
    def is_valid_port(port: Any) -> bool:
        """
        Check if port number is valid.

        Args:
            port: Port to validate

        Returns:
            True if valid, False otherwise
        """
        try:
            port = int(port)
            return 1 <= port <= 65535
        except (ValueError, TypeError):
            return False

    @staticmethod
    def sanitize_string(text: str, max_length: Optional[int] = None) -> str:
        """
        Sanitize string by removing dangerous characters.

        Args:
            text: Text to sanitize
            max_length: Maximum length

        Returns:
            Sanitized string
        """
        # Remove control characters
        sanitized = re.sub(r'[\x00-\x1F\x7F-\x9F]', '', text)

        # Strip whitespace
        sanitized = sanitized.strip()

        # Limit length
        if max_length and len(sanitized) > max_length:
            sanitized = sanitized[:max_length]

        return sanitized

    @staticmethod
    def validate_json(data: str) -> bool:
        """
        Check if string is valid JSON.

        Args:
            data: JSON string to validate

        Returns:
            True if valid, False otherwise
        """
        import json
        try:
            json.loads(data)
            return True
        except (ValueError, TypeError):
            return False


# ============================================================================
# LINK NAME VALIDATOR
# ============================================================================

class LinkNameValidator:
    """
    Validator for link names and descriptions.
    """

    MIN_LENGTH = 1
    MAX_LENGTH = 500
    
    # Forbidden patterns
    FORBIDDEN_PATTERNS = [
        r'<script',
        r'javascript:',
        r'onclick',
        r'onerror',
    ]

    @staticmethod
    def is_valid_name(name: str) -> bool:
        """
        Check if link name is valid.

        Args:
            name: Name to validate

        Returns:
            True if valid, False otherwise
        """
        if not name or not isinstance(name, str):
            return False

        # Check length
        if not (LinkNameValidator.MIN_LENGTH <= len(name) <= LinkNameValidator.MAX_LENGTH):
            return False

        # Check for forbidden patterns
        for pattern in LinkNameValidator.FORBIDDEN_PATTERNS:
            if re.search(pattern, name, re.IGNORECASE):
                return False

        return True

    @staticmethod
    def sanitize_name(name: str) -> str:
        """
        Sanitize link name.

        Args:
            name: Name to sanitize

        Returns:
            Sanitized name
        """
        # Remove HTML tags
        sanitized = re.sub(r'<[^>]+>', '', name)

        # Remove excessive whitespace
        sanitized = re.sub(r'\s+', ' ', sanitized)

        # Trim
        sanitized = sanitized.strip()

        # Limit length
        if len(sanitized) > LinkNameValidator.MAX_LENGTH:
            sanitized = sanitized[:LinkNameValidator.MAX_LENGTH]

        return sanitized


# ============================================================================
# BATCH VALIDATOR
# ============================================================================

class BatchValidator:
    """
    Validator for batch operations.
    """

    @staticmethod
    def validate_url_list(urls: List[str]) -> Dict[str, List[str]]:
        """
        Validate a list of URLs.

        Args:
            urls: List of URLs to validate

        Returns:
            Dictionary with 'valid' and 'invalid' URLs
        """
        valid = []
        invalid = []

        for url in urls:
            if URLValidator.is_valid_url(url):
                normalized = URLValidator.normalize_url(url)
                if normalized:
                    valid.append(normalized)
                else:
                    invalid.append(url)
            else:
                invalid.append(url)

        return {
            "valid": valid,
            "invalid": invalid
        }

    @staticmethod
    def deduplicate_urls(urls: List[str]) -> List[str]:
        """
        Remove duplicate URLs from list.

        Args:
            urls: List of URLs

        Returns:
            List without duplicates
        """
        seen = set()
        unique = []

        for url in urls:
            normalized = URLValidator.normalize_url(url)
            if normalized and normalized not in seen:
                seen.add(normalized)
                unique.append(normalized)

        return unique


# ============================================================================
# VALIDATION RESULT CLASS
# ============================================================================

class ValidationResult:
    """
    Class to hold validation results with detailed information.
    """

    def __init__(self, is_valid: bool, message: str = "", errors: Optional[List[str]] = None):
        """
        Initialize validation result.

        Args:
            is_valid: Whether validation passed
            message: Validation message
            errors: List of error messages
        """
        self.is_valid = is_valid
        self.message = message
        self.errors = errors or []

    def __bool__(self):
        """Allow using result as boolean."""
        return self.is_valid

    def __str__(self):
        """String representation."""
        if self.is_valid:
            return f"Valid: {self.message}"
        else:
            errors_str = ", ".join(self.errors) if self.errors else "Unknown error"
            return f"Invalid: {self.message} - {errors_str}"

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "is_valid": self.is_valid,
            "message": self.message,
            "errors": self.errors
        }


# ============================================================================
# COMPREHENSIVE VALIDATOR
# ============================================================================

class LinkValidator:
    """
    Comprehensive link validation.
    """

    @staticmethod
    def validate_new_link(
        url: str,
        name: Optional[str] = None,
        ping_interval: Optional[int] = None,
        timeout: Optional[int] = None,
        user_max_links: int = 100,
        user_current_links: int = 0,
        user_min_interval: int = 60
    ) -> ValidationResult:
        """
        Validate all aspects of a new link.

        Args:
            url: URL to monitor
            name: Optional link name
            ping_interval: Ping interval in seconds
            timeout: Request timeout in seconds
            user_max_links: Maximum links allowed for user
            user_current_links: Current number of links for user
            user_min_interval: Minimum interval allowed for user

        Returns:
            ValidationResult instance
        """
        errors = []

        # Validate URL
        if not URLValidator.is_valid_url(url):
            errors.append("Invalid URL format")

        # Validate name if provided
        if name and not LinkNameValidator.is_valid_name(name):
            errors.append("Invalid link name")

        # Validate interval if provided
        if ping_interval is not None:
            if not DataValidator.is_valid_interval(ping_interval, user_min_interval):
                errors.append(f"Ping interval must be between {user_min_interval} and 86400 seconds")

        # Validate timeout if provided
        if timeout is not None:
            if not DataValidator.is_valid_timeout(timeout):
                errors.append("Timeout must be between 5 and 300 seconds")

        # Check user limits
        if user_current_links >= user_max_links:
            errors.append(f"Maximum number of links reached ({user_max_links})")

        if errors:
            return ValidationResult(
                is_valid=False,
                message="Link validation failed",
                errors=errors
            )

        return ValidationResult(
            is_valid=True,
            message="Link is valid"
        )


# ============================================================================
# END OF VALIDATORS MODULE
# ============================================================================
