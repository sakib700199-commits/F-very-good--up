"""
============================================================================
TELEGRAM UPTIME BOT - HELPERS UTILITY
============================================================================
Collection of helper functions and utilities.

Author: Professional Development Team
Version: 1.0.0
License: MIT
============================================================================
"""

import asyncio
import time
from datetime import datetime, timedelta
from typing import Optional, Any, Dict, List, Callable
import hashlib
import secrets
import string
from functools import wraps

from utils.logger import get_logger


logger = get_logger(__name__)


# ============================================================================
# TIME UTILITIES
# ============================================================================

class TimeHelper:
    """
    Time and date manipulation utilities.
    """

    @staticmethod
    def get_utc_now() -> datetime:
        """Get current UTC datetime."""
        return datetime.utcnow()

    @staticmethod
    def format_datetime(dt: datetime, fmt: str = "%Y-%m-%d %H:%M:%S") -> str:
        """
        Format datetime to string.

        Args:
            dt: Datetime to format
            fmt: Format string

        Returns:
            Formatted string
        """
        return dt.strftime(fmt)

    @staticmethod
    def parse_datetime(dt_str: str, fmt: str = "%Y-%m-%d %H:%M:%S") -> Optional[datetime]:
        """
        Parse string to datetime.

        Args:
            dt_str: String to parse
            fmt: Format string

        Returns:
            Datetime or None if parsing fails
        """
        try:
            return datetime.strptime(dt_str, fmt)
        except ValueError:
            return None

    @staticmethod
    def seconds_to_human_readable(seconds: int) -> str:
        """
        Convert seconds to human-readable format.

        Args:
            seconds: Number of seconds

        Returns:
            Human-readable string (e.g., "2h 30m 15s")
        """
        if seconds < 0:
            return "0s"

        days, remainder = divmod(seconds, 86400)
        hours, remainder = divmod(remainder, 3600)
        minutes, secs = divmod(remainder, 60)

        parts = []
        if days > 0:
            parts.append(f"{days}d")
        if hours > 0:
            parts.append(f"{hours}h")
        if minutes > 0:
            parts.append(f"{minutes}m")
        if secs > 0 or not parts:
            parts.append(f"{secs}s")

        return " ".join(parts)

    @staticmethod
    def human_readable_to_seconds(time_str: str) -> Optional[int]:
        """
        Convert human-readable time to seconds.

        Args:
            time_str: Time string (e.g., "2h 30m", "5m", "1d")

        Returns:
            Number of seconds or None if parsing fails
        """
        import re

        time_str = time_str.lower().strip()
        total_seconds = 0

        # Pattern: number followed by unit (d/h/m/s)
        pattern = r'(\d+)\s*([dhms])'
        matches = re.findall(pattern, time_str)

        if not matches:
            return None

        units = {
            'd': 86400,
            'h': 3600,
            'm': 60,
            's': 1
        }

        for value, unit in matches:
            total_seconds += int(value) * units.get(unit, 0)

        return total_seconds if total_seconds > 0 else None

    @staticmethod
    def calculate_uptime_percentage(total_time: int, downtime: int) -> float:
        """
        Calculate uptime percentage.

        Args:
            total_time: Total monitoring time in seconds
            downtime: Downtime in seconds

        Returns:
            Uptime percentage (0-100)
        """
        if total_time <= 0:
            return 100.0

        uptime = total_time - downtime
        percentage = (uptime / total_time) * 100
        return max(0.0, min(100.0, percentage))

    @staticmethod
    def get_time_ago(dt: datetime) -> str:
        """
        Get human-readable time ago string.

        Args:
            dt: Past datetime

        Returns:
            String like "5 minutes ago", "2 hours ago", etc.
        """
        now = datetime.utcnow()
        diff = now - dt

        seconds = diff.total_seconds()

        if seconds < 60:
            return f"{int(seconds)} seconds ago"
        elif seconds < 3600:
            minutes = int(seconds / 60)
            return f"{minutes} minute{'s' if minutes != 1 else ''} ago"
        elif seconds < 86400:
            hours = int(seconds / 3600)
            return f"{hours} hour{'s' if hours != 1 else ''} ago"
        else:
            days = int(seconds / 86400)
            return f"{days} day{'s' if days != 1 else ''} ago"


# ============================================================================
# STRING UTILITIES
# ============================================================================

class StringHelper:
    """
    String manipulation utilities.
    """

    @staticmethod
    def truncate(text: str, max_length: int = 100, suffix: str = "...") -> str:
        """
        Truncate string to maximum length.

        Args:
            text: Text to truncate
            max_length: Maximum length
            suffix: Suffix to add if truncated

        Returns:
            Truncated string
        """
        if len(text) <= max_length:
            return text

        return text[:max_length - len(suffix)] + suffix

    @staticmethod
    def escape_markdown(text: str) -> str:
        """
        Escape special characters for Telegram MarkdownV2.

        Args:
            text: Text to escape

        Returns:
            Escaped text
        """
        escape_chars = r'_*[]()~`>#+-=|{}.!'
        return ''.join(f'\\{char}' if char in escape_chars else char for char in text)

    @staticmethod
    def escape_html(text: str) -> str:
        """
        Escape HTML special characters.

        Args:
            text: Text to escape

        Returns:
            Escaped text
        """
        import html
        return html.escape(text)

    @staticmethod
    def generate_random_string(length: int = 32) -> str:
        """
        Generate random string.

        Args:
            length: Length of string

        Returns:
            Random string
        """
        alphabet = string.ascii_letters + string.digits
        return ''.join(secrets.choice(alphabet) for _ in range(length))

    @staticmethod
    def generate_hash(text: str, algorithm: str = "sha256") -> str:
        """
        Generate hash of text.

        Args:
            text: Text to hash
            algorithm: Hash algorithm (md5, sha1, sha256, sha512)

        Returns:
            Hash string
        """
        hash_func = getattr(hashlib, algorithm)
        return hash_func(text.encode()).hexdigest()

    @staticmethod
    def format_bytes(bytes_value: int) -> str:
        """
        Format bytes to human-readable size.

        Args:
            bytes_value: Number of bytes

        Returns:
            Formatted string (e.g., "1.5 MB")
        """
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if bytes_value < 1024.0:
                return f"{bytes_value:.2f} {unit}"
            bytes_value /= 1024.0
        return f"{bytes_value:.2f} PB"


# ============================================================================
# PERFORMANCE UTILITIES
# ============================================================================

class PerformanceHelper:
    """
    Performance monitoring and optimization utilities.
    """

    @staticmethod
    async def measure_async_execution_time(func: Callable, *args, **kwargs) -> tuple:
        """
        Measure async function execution time.

        Args:
            func: Async function to measure
            *args: Function arguments
            **kwargs: Function keyword arguments

        Returns:
            Tuple of (result, execution_time_seconds)
        """
        start_time = time.time()
        result = await func(*args, **kwargs)
        execution_time = time.time() - start_time
        return result, execution_time

    @staticmethod
    def measure_sync_execution_time(func: Callable, *args, **kwargs) -> tuple:
        """
        Measure sync function execution time.

        Args:
            func: Function to measure
            *args: Function arguments
            **kwargs: Function keyword arguments

        Returns:
            Tuple of (result, execution_time_seconds)
        """
        start_time = time.time()
        result = func(*args, **kwargs)
        execution_time = time.time() - start_time
        return result, execution_time

    @staticmethod
    def get_memory_usage() -> float:
        """
        Get current memory usage in MB.

        Returns:
            Memory usage in MB
        """
        import psutil
        import os

        process = psutil.Process(os.getpid())
        return process.memory_info().rss / 1024 / 1024

    @staticmethod
    def get_cpu_usage() -> float:
        """
        Get current CPU usage percentage.

        Returns:
            CPU usage percentage
        """
        import psutil
        return psutil.cpu_percent(interval=1)


# ============================================================================
# RETRY DECORATOR
# ============================================================================

def retry(
    max_attempts: int = 3,
    delay: float = 1.0,
    backoff: float = 2.0,
    exceptions: tuple = (Exception,)
):
    """
    Retry decorator for async functions.

    Args:
        max_attempts: Maximum number of attempts
        delay: Initial delay between retries (seconds)
        backoff: Multiplier for delay after each retry
        exceptions: Tuple of exceptions to catch

    Returns:
        Decorator function
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            current_delay = delay
            last_exception = None

            for attempt in range(1, max_attempts + 1):
                try:
                    return await func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt < max_attempts:
                        logger.warning(
                            f"Attempt {attempt}/{max_attempts} failed for {func.__name__}: {e}. "
                            f"Retrying in {current_delay}s..."
                        )
                        await asyncio.sleep(current_delay)
                        current_delay *= backoff
                    else:
                        logger.error(
                            f"All {max_attempts} attempts failed for {func.__name__}: {e}"
                        )

            raise last_exception

        return wrapper
    return decorator


# ============================================================================
# CACHE DECORATOR
# ============================================================================

class AsyncCache:
    """
    Simple async cache decorator.
    """

    def __init__(self, ttl: int = 300):
        """
        Initialize cache.

        Args:
            ttl: Time to live in seconds
        """
        self.ttl = ttl
        self.cache: Dict[str, tuple] = {}

    def __call__(self, func):
        """Make cache instance callable as decorator."""
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Create cache key from function name and arguments
            key = f"{func.__name__}:{str(args)}:{str(kwargs)}"

            # Check cache
            if key in self.cache:
                value, timestamp = self.cache[key]
                if time.time() - timestamp < self.ttl:
                    logger.debug(f"Cache hit for {func.__name__}")
                    return value

            # Call function
            logger.debug(f"Cache miss for {func.__name__}")
            result = await func(*args, **kwargs)

            # Store in cache
            self.cache[key] = (result, time.time())

            return result

        return wrapper


# ============================================================================
# BATCH PROCESSOR
# ============================================================================

class BatchProcessor:
    """
    Process items in batches.
    """

    @staticmethod
    async def process_in_batches(
        items: List[Any],
        batch_size: int,
        process_func: Callable,
        delay_between_batches: float = 0.0
    ) -> List[Any]:
        """
        Process items in batches.

        Args:
            items: List of items to process
            batch_size: Number of items per batch
            process_func: Async function to process each batch
            delay_between_batches: Delay between batches in seconds

        Returns:
            List of results
        """
        results = []

        for i in range(0, len(items), batch_size):
            batch = items[i:i + batch_size]
            logger.debug(f"Processing batch {i//batch_size + 1}")

            batch_results = await process_func(batch)
            results.extend(batch_results)

            if delay_between_batches > 0 and i + batch_size < len(items):
                await asyncio.sleep(delay_between_batches)

        return results


# ============================================================================
# RATE LIMITER
# ============================================================================

class RateLimiter:
    """
    Simple rate limiter.
    """

    def __init__(self, max_calls: int, time_window: int):
        """
        Initialize rate limiter.

        Args:
            max_calls: Maximum number of calls
            time_window: Time window in seconds
        """
        self.max_calls = max_calls
        self.time_window = time_window
        self.calls: Dict[str, List[float]] = {}

    def is_allowed(self, identifier: str) -> bool:
        """
        Check if call is allowed.

        Args:
            identifier: Unique identifier (e.g., user_id)

        Returns:
            True if allowed, False otherwise
        """
        now = time.time()

        # Get call history for identifier
        if identifier not in self.calls:
            self.calls[identifier] = []

        # Remove old calls outside time window
        self.calls[identifier] = [
            call_time for call_time in self.calls[identifier]
            if now - call_time < self.time_window
        ]

        # Check if under limit
        if len(self.calls[identifier]) < self.max_calls:
            self.calls[identifier].append(now)
            return True

        return False

    def reset(self, identifier: str):
        """Reset rate limit for identifier."""
        if identifier in self.calls:
            del self.calls[identifier]


# ============================================================================
# DATA STRUCTURE HELPERS
# ============================================================================

class DataHelper:
    """
    Data structure manipulation helpers.
    """

    @staticmethod
    def chunk_list(lst: List[Any], chunk_size: int) -> List[List[Any]]:
        """
        Split list into chunks.

        Args:
            lst: List to split
            chunk_size: Size of each chunk

        Returns:
            List of chunks
        """
        return [lst[i:i + chunk_size] for i in range(0, len(lst), chunk_size)]

    @staticmethod
    def flatten_list(nested_list: List[List[Any]]) -> List[Any]:
        """
        Flatten nested list.

        Args:
            nested_list: Nested list

        Returns:
            Flattened list
        """
        return [item for sublist in nested_list for item in sublist]

    @staticmethod
    def merge_dicts(*dicts: Dict) -> Dict:
        """
        Merge multiple dictionaries.

        Args:
            *dicts: Dictionaries to merge

        Returns:
            Merged dictionary
        """
        result = {}
        for d in dicts:
            result.update(d)
        return result

    @staticmethod
    def filter_dict(d: Dict, keys: List[str]) -> Dict:
        """
        Filter dictionary by keys.

        Args:
            d: Dictionary to filter
            keys: Keys to keep

        Returns:
            Filtered dictionary
        """
        return {k: v for k, v in d.items() if k in keys}


# ============================================================================
# TELEGRAM HELPERS
# ============================================================================

class TelegramHelper:
    """
    Telegram-specific helper functions.
    """

    @staticmethod
    def format_user_mention(user_id: int, name: str) -> str:
        """
        Format user mention for Telegram.

        Args:
            user_id: User ID
            name: Display name

        Returns:
            Mention string
        """
        return f'<a href="tg://user?id={user_id}">{name}</a>'

    @staticmethod
    def create_progress_bar(current: int, total: int, length: int = 10) -> str:
        """
        Create text-based progress bar.

        Args:
            current: Current value
            total: Total value
            length: Bar length

        Returns:
            Progress bar string
        """
        if total == 0:
            percentage = 0
        else:
            percentage = (current / total) * 100

        filled = int((current / total) * length) if total > 0 else 0
        bar = "█" * filled + "░" * (length - filled)

        return f"[{bar}] {percentage:.1f}%"

    @staticmethod
    def format_uptime_status(is_up: bool) -> str:
        """
        Format uptime status with emoji.

        Args:
            is_up: Whether service is up

        Returns:
            Formatted status string
        """
        if is_up:
            return "🟢 UP"
        else:
            return "🔴 DOWN"


# ============================================================================
# END OF HELPERS MODULE
# ============================================================================
