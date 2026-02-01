"""
Database Exception Classes for Uptime Bot

Provides specialized exceptions for database-related errors
including connection issues, query errors, and data integrity problems.
"""

from __future__ import annotations

from typing import Any, Optional, Type
from exceptions.base import UptimeBotException


class DatabaseException(UptimeBotException):
    """
    Base Database Exception
    
    Parent class for all database-related exceptions.
    """
    
    default_error_code = 2000
    default_recoverable = False
    default_notify_admin = True
    
    def __init__(
        self,
        message: str,
        query: Optional[str] = None,
        table: Optional[str] = None,
        **kwargs: Any
    ) -> None:
        """
        Initialize database exception.
        
        Args:
            message: Error message
            query: The SQL query that caused the error (sanitized)
            table: The database table involved
            **kwargs: Additional arguments
        """
        super().__init__(message, **kwargs)
        
        if query:
            # Sanitize query by removing values
            self.details["query"] = self._sanitize_query(query)
        
        if table:
            self.details["table"] = table
    
    @staticmethod
    def _sanitize_query(query: str) -> str:
        """
        Sanitize SQL query by removing sensitive values.
        
        Args:
            query: The original SQL query
            
        Returns:
            Sanitized query string
        """
        # Basic sanitization - in production, use proper query logging
        import re
        
        # Remove string values
        query = re.sub(r"'[^']*'", "'***'", query)
        
        # Remove numeric values in comparisons
        query = re.sub(r"= \d+", "= ***", query)
        
        # Truncate if too long
        if len(query) > 500:
            query = query[:500] + "..."
        
        return query


class DatabaseConnectionError(DatabaseException):
    """
    Database Connection Error
    
    Raised when unable to establish or maintain database connection.
    """
    
    default_error_code = 2001
    
    def __init__(
        self,
        message: str = "Unable to connect to database",
        host: Optional[str] = None,
        port: Optional[int] = None,
        database: Optional[str] = None,
        **kwargs: Any
    ) -> None:
        """
        Initialize connection error.
        
        Args:
            message: Error message
            host: Database host
            port: Database port
            database: Database name
            **kwargs: Additional arguments
        """
        super().__init__(message, **kwargs)
        
        if host:
            self.details["host"] = host
        
        if port:
            self.details["port"] = port
        
        if database:
            self.details["database"] = database
    
    def user_message(self) -> str:
        """Get user-friendly error message."""
        return "Unable to access the database. Please try again later."


class DatabaseQueryError(DatabaseException):
    """
    Database Query Error
    
    Raised when a database query fails to execute.
    """
    
    default_error_code = 2002
    
    def __init__(
        self,
        message: str = "Database query failed",
        operation: Optional[str] = None,
        **kwargs: Any
    ) -> None:
        """
        Initialize query error.
        
        Args:
            message: Error message
            operation: The type of operation (SELECT, INSERT, etc.)
            **kwargs: Additional arguments
        """
        super().__init__(message, **kwargs)
        
        if operation:
            self.details["operation"] = operation
    
    def user_message(self) -> str:
        """Get user-friendly error message."""
        return "An error occurred while processing your request."


class DatabaseNotFoundError(DatabaseException):
    """
    Database Not Found Error
    
    Raised when a requested record is not found in the database.
    """
    
    default_error_code = 2003
    default_recoverable = True
    default_notify_admin = False
    
    def __init__(
        self,
        message: str = "Record not found",
        entity_type: Optional[str] = None,
        entity_id: Optional[Any] = None,
        **kwargs: Any
    ) -> None:
        """
        Initialize not found error.
        
        Args:
            message: Error message
            entity_type: Type of entity not found (User, Link, etc.)
            entity_id: ID of the entity
            **kwargs: Additional arguments
        """
        super().__init__(message, **kwargs)
        
        if entity_type:
            self.details["entity_type"] = entity_type
        
        if entity_id is not None:
            self.details["entity_id"] = str(entity_id)
    
    def user_message(self) -> str:
        """Get user-friendly error message."""
        entity = self.details.get("entity_type", "Record")
        return f"{entity} not found."


class DatabaseDuplicateError(DatabaseException):
    """
    Database Duplicate Error
    
    Raised when attempting to insert a duplicate record.
    """
    
    default_error_code = 2004
    default_recoverable = True
    default_notify_admin = False
    
    def __init__(
        self,
        message: str = "Record already exists",
        entity_type: Optional[str] = None,
        field: Optional[str] = None,
        value: Optional[str] = None,
        **kwargs: Any
    ) -> None:
        """
        Initialize duplicate error.
        
        Args:
            message: Error message
            entity_type: Type of entity
            field: Field that caused the duplicate
            value: The duplicate value (sanitized)
            **kwargs: Additional arguments
        """
        super().__init__(message, **kwargs)
        
        if entity_type:
            self.details["entity_type"] = entity_type
        
        if field:
            self.details["field"] = field
        
        if value:
            self.details["value"] = value[:50] if len(value) > 50 else value
    
    def user_message(self) -> str:
        """Get user-friendly error message."""
        entity = self.details.get("entity_type", "Record")
        return f"This {entity.lower()} already exists."


class DatabaseIntegrityError(DatabaseException):
    """
    Database Integrity Error
    
    Raised when a database integrity constraint is violated.
    """
    
    default_error_code = 2005
    
    def __init__(
        self,
        message: str = "Data integrity violation",
        constraint: Optional[str] = None,
        **kwargs: Any
    ) -> None:
        """
        Initialize integrity error.
        
        Args:
            message: Error message
            constraint: The constraint that was violated
            **kwargs: Additional arguments
        """
        super().__init__(message, **kwargs)
        
        if constraint:
            self.details["constraint"] = constraint


class DatabaseTimeoutError(DatabaseException):
    """
    Database Timeout Error
    
    Raised when a database operation times out.
    """
    
    default_error_code = 2006
    
    def __init__(
        self,
        message: str = "Database operation timed out",
        timeout: Optional[float] = None,
        **kwargs: Any
    ) -> None:
        """
        Initialize timeout error.
        
        Args:
            message: Error message
            timeout: The timeout value in seconds
            **kwargs: Additional arguments
        """
        super().__init__(message, **kwargs)
        
        if timeout:
            self.details["timeout"] = timeout
    
    def user_message(self) -> str:
        """Get user-friendly error message."""
        return "The operation took too long. Please try again."


class DatabaseMigrationError(DatabaseException):
    """
    Database Migration Error
    
    Raised when database migration fails.
    """
    
    default_error_code = 2007
    
    def __init__(
        self,
        message: str = "Database migration failed",
        migration_id: Optional[str] = None,
        direction: Optional[str] = None,
        **kwargs: Any
    ) -> None:
        """
        Initialize migration error.
        
        Args:
            message: Error message
            migration_id: ID of the migration that failed
            direction: Migration direction (upgrade/downgrade)
            **kwargs: Additional arguments
        """
        super().__init__(message, **kwargs)
        
        if migration_id:
            self.details["migration_id"] = migration_id
        
        if direction:
            self.details["direction"] = direction


class DatabasePoolExhaustedError(DatabaseException):
    """
    Database Pool Exhausted Error
    
    Raised when no connections are available in the pool.
    """
    
    default_error_code = 2008
    
    def __init__(
        self,
        message: str = "Database connection pool exhausted",
        pool_size: Optional[int] = None,
        active_connections: Optional[int] = None,
        **kwargs: Any
    ) -> None:
        """
        Initialize pool exhausted error.
        
        Args:
            message: Error message
            pool_size: Maximum pool size
            active_connections: Current active connections
            **kwargs: Additional arguments
        """
        super().__init__(message, **kwargs)
        
        if pool_size:
            self.details["pool_size"] = pool_size
        
        if active_connections:
            self.details["active_connections"] = active_connections
    
    def user_message(self) -> str:
        """Get user-friendly error message."""
        return "The service is experiencing high load. Please try again in a moment."


class DatabaseTransactionError(DatabaseException):
    """
    Database Transaction Error
    
    Raised when a database transaction fails.
    """
    
    default_error_code = 2009
    
    def __init__(
        self,
        message: str = "Database transaction failed",
        transaction_id: Optional[str] = None,
        rollback_successful: Optional[bool] = None,
        **kwargs: Any
    ) -> None:
        """
        Initialize transaction error.
        
        Args:
            message: Error message
            transaction_id: Transaction identifier
            rollback_successful: Whether rollback was successful
            **kwargs: Additional arguments
        """
        super().__init__(message, **kwargs)
        
        if transaction_id:
            self.details["transaction_id"] = transaction_id
        
        if rollback_successful is not None:
            self.details["rollback_successful"] = rollback_successful
