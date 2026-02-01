"""
============================================================================
TELEGRAM UPTIME BOT - LOGGING UTILITY
============================================================================
Comprehensive logging system with multiple handlers, formatters, and levels.

Author: Professional Development Team
Version: 1.0.0
License: MIT
============================================================================
"""

import sys
import logging
from pathlib import Path
from typing import Optional
from datetime import datetime
import json

from loguru import logger
from logging.handlers import RotatingFileHandler, TimedRotatingFileHandler

from config.settings import get_settings


settings = get_settings()


# ============================================================================
# CUSTOM LOG FORMATTER
# ============================================================================

class JSONFormatter(logging.Formatter):
    """
    Custom JSON formatter for structured logging.
    """

    def format(self, record: logging.LogRecord) -> str:
        """
        Format log record as JSON.

        Args:
            record: Log record

        Returns:
            Formatted JSON string
        """
        log_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        if hasattr(record, "user_id"):
            log_data["user_id"] = record.user_id

        if hasattr(record, "link_id"):
            log_data["link_id"] = record.link_id

        return json.dumps(log_data)


class ColoredFormatter(logging.Formatter):
    """
    Custom colored formatter for console logging.
    """

    COLORS = {
        "DEBUG": "\033[36m",  # Cyan
        "INFO": "\033[32m",  # Green
        "WARNING": "\033[33m",  # Yellow
        "ERROR": "\033[31m",  # Red
        "CRITICAL": "\033[35m",  # Magenta
        "RESET": "\033[0m",
    }

    def format(self, record: logging.LogRecord) -> str:
        """
        Format log record with colors.

        Args:
            record: Log record

        Returns:
            Formatted colored string
        """
        if settings.LOG_COLORIZE:
            color = self.COLORS.get(record.levelname, self.COLORS["RESET"])
            record.levelname = f"{color}{record.levelname}{self.COLORS['RESET']}"
            record.name = f"\033[34m{record.name}{self.COLORS['RESET']}"

        return super().format(record)


# ============================================================================
# LOGGER CONFIGURATION
# ============================================================================

def setup_logging() -> None:
    """
    Configure logging system with multiple handlers.
    Sets up both file and console logging.
    """
    # Remove default loguru handler
    logger.remove()

    # Configure log level
    log_level = settings.LOG_LEVEL.upper()

    # Console Handler
    if settings.LOG_TO_CONSOLE:
        logger.add(
            sys.stdout,
            format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
            level=log_level,
            colorize=settings.LOG_COLORIZE,
            backtrace=True,
            diagnose=True,
        )

    # File Handler
    if settings.LOG_TO_FILE:
        log_file_path = settings.logs_dir / Path(settings.LOG_FILE_PATH).name

        if settings.LOG_FORMAT == "json":
            # JSON format for structured logging
            logger.add(
                log_file_path,
                format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {name}:{function}:{line} | {message}",
                level=log_level,
                rotation=settings.LOG_FILE_MAX_SIZE,
                retention=settings.LOG_FILE_BACKUP_COUNT,
                compression="zip",
                serialize=True,  # JSON serialization
                backtrace=True,
                diagnose=True,
            )
        else:
            # Text format
            logger.add(
                log_file_path,
                format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
                level=log_level,
                rotation=settings.LOG_FILE_MAX_SIZE,
                retention=settings.LOG_FILE_BACKUP_COUNT,
                compression="zip",
                backtrace=True,
                diagnose=True,
            )

    # Error log file (separate file for errors)
    error_log_path = settings.logs_dir / "errors.log"
    logger.add(
        error_log_path,
        format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {name}:{function}:{line} | {message}",
        level="ERROR",
        rotation="1 day",
        retention="7 days",
        compression="zip",
        backtrace=True,
        diagnose=True,
    )

    logger.info("Logging system initialized")
    logger.info(f"Log level: {log_level}")
    logger.info(f"Console logging: {settings.LOG_TO_CONSOLE}")
    logger.info(f"File logging: {settings.LOG_TO_FILE}")


def get_logger(name: Optional[str] = None):
    """
    Get logger instance with optional name.

    Args:
        name: Logger name (usually __name__)

    Returns:
        Logger instance
    """
    if name:
        return logger.bind(name=name)
    return logger


# ============================================================================
# LOG DECORATORS
# ============================================================================

def log_execution_time(func):
    """
    Decorator to log function execution time.

    Args:
        func: Function to decorate

    Returns:
        Decorated function
    """
    import time
    from functools import wraps

    @wraps(func)
    async def async_wrapper(*args, **kwargs):
        start_time = time.time()
        try:
            result = await func(*args, **kwargs)
            execution_time = time.time() - start_time
            logger.debug(
                f"Function {func.__name__} executed in {execution_time:.4f} seconds"
            )
            return result
        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(
                f"Function {func.__name__} failed after {execution_time:.4f} seconds: {e}"
            )
            raise

    @wraps(func)
    def sync_wrapper(*args, **kwargs):
        start_time = time.time()
        try:
            result = func(*args, **kwargs)
            execution_time = time.time() - start_time
            logger.debug(
                f"Function {func.__name__} executed in {execution_time:.4f} seconds"
            )
            return result
        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(
                f"Function {func.__name__} failed after {execution_time:.4f} seconds: {e}"
            )
            raise

    if asyncio.iscoroutinefunction(func):
        return async_wrapper
    return sync_wrapper


def log_errors(func):
    """
    Decorator to log errors with full traceback.

    Args:
        func: Function to decorate

    Returns:
        Decorated function
    """
    from functools import wraps
    import traceback

    @wraps(func)
    async def async_wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except Exception as e:
            logger.error(f"Error in {func.__name__}: {e}")
            logger.error(traceback.format_exc())
            raise

    @wraps(func)
    def sync_wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            logger.error(f"Error in {func.__name__}: {e}")
            logger.error(traceback.format_exc())
            raise

    if asyncio.iscoroutinefunction(func):
        return async_wrapper
    return sync_wrapper


# ============================================================================
# CONTEXT MANAGERS FOR LOGGING
# ============================================================================

class LogContext:
    """
    Context manager for adding context to logs.
    """

    def __init__(self, **context):
        """
        Initialize log context.

        Args:
            **context: Context key-value pairs
        """
        self.context = context
        self.token = None

    def __enter__(self):
        """Enter context."""
        self.token = logger.contextualize(**self.context)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit context."""
        if self.token:
            logger.remove(self.token)


# ============================================================================
# SPECIALIZED LOGGERS
# ============================================================================

class MonitorLogger:
    """
    Specialized logger for monitoring operations.
    """

    def __init__(self):
        """Initialize monitor logger."""
        self.logger = get_logger("Monitor")

    def log_check(self, link_id: int, url: str, success: bool, response_time: Optional[float] = None):
        """Log a monitoring check."""
        if success:
            self.logger.info(
                f"Check successful for link {link_id} ({url}) - Response time: {response_time:.3f}s"
            )
        else:
            self.logger.warning(f"Check failed for link {link_id} ({url})")

    def log_downtime(self, link_id: int, url: str, error: Optional[str] = None):
        """Log downtime event."""
        self.logger.error(f"Downtime detected for link {link_id} ({url}): {error}")

    def log_recovery(self, link_id: int, url: str, downtime_duration: int):
        """Log recovery event."""
        self.logger.info(
            f"Recovery detected for link {link_id} ({url}) - Downtime: {downtime_duration}s"
        )


class DatabaseLogger:
    """
    Specialized logger for database operations.
    """

    def __init__(self):
        """Initialize database logger."""
        self.logger = get_logger("Database")

    def log_query(self, query: str, params: Optional[dict] = None):
        """Log database query."""
        self.logger.debug(f"Query: {query} | Params: {params}")

    def log_transaction(self, operation: str, success: bool):
        """Log database transaction."""
        if success:
            self.logger.debug(f"Transaction successful: {operation}")
        else:
            self.logger.error(f"Transaction failed: {operation}")


class BotLogger:
    """
    Specialized logger for bot operations.
    """

    def __init__(self):
        """Initialize bot logger."""
        self.logger = get_logger("Bot")

    def log_command(self, user_id: int, command: str, success: bool):
        """Log bot command."""
        if success:
            self.logger.info(f"Command /{command} executed by user {user_id}")
        else:
            self.logger.warning(f"Command /{command} failed for user {user_id}")

    def log_error(self, user_id: int, error: str):
        """Log bot error."""
        self.logger.error(f"Error for user {user_id}: {error}")


# ============================================================================
# PERFORMANCE MONITORING
# ============================================================================

class PerformanceLogger:
    """
    Logger for performance metrics.
    """

    def __init__(self):
        """Initialize performance logger."""
        self.logger = get_logger("Performance")

    def log_metric(self, metric_name: str, value: float, unit: str = ""):
        """Log performance metric."""
        self.logger.info(f"Metric: {metric_name} = {value}{unit}")

    def log_memory_usage(self, usage_mb: float):
        """Log memory usage."""
        self.logger.info(f"Memory usage: {usage_mb:.2f} MB")

    def log_cpu_usage(self, usage_percent: float):
        """Log CPU usage."""
        self.logger.info(f"CPU usage: {usage_percent:.2f}%")


# ============================================================================
# INITIALIZE LOGGING ON MODULE IMPORT
# ============================================================================

import asyncio

# Setup logging when module is imported
setup_logging()


# ============================================================================
# END OF LOGGER MODULE
# ============================================================================
