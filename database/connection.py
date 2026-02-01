"""
Database Connection Module for Uptime Bot

Manages database connections, session factories, and connection pooling
using SQLAlchemy's async engine and session maker.
"""

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from typing import Any, AsyncGenerator, Dict, Optional, Type
import logging

from sqlalchemy import event, text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine
)
from sqlalchemy.pool import NullPool, QueuePool
from sqlalchemy.exc import SQLAlchemyError

from config import settings, DatabaseSettings
from exceptions import (
    DatabaseConnectionError,
    DatabaseQueryError,
    DatabasePoolExhaustedError,
    InitializationError
)


logger = logging.getLogger(__name__)


class DatabaseManager:
    """
    Database Manager Class
    
    Manages database connections, engines, and session factories.
    Implements singleton pattern for global access.
    
    Attributes:
        engine: SQLAlchemy async engine
        session_factory: Async session maker
        is_connected: Connection status flag
    """
    
    _instance: Optional["DatabaseManager"] = None
    _lock: asyncio.Lock = asyncio.Lock()
    
    def __new__(cls) -> "DatabaseManager":
        """Implement singleton pattern."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self) -> None:
        """Initialize database manager."""
        if self._initialized:
            return
        
        self.engine: Optional[AsyncEngine] = None
        self.session_factory: Optional[async_sessionmaker[AsyncSession]] = None
        self.is_connected: bool = False
        self._settings: DatabaseSettings = settings.database
        self._initialized = True
    
    async def connect(self) -> None:
        """
        Establish database connection.
        
        Creates the async engine and session factory.
        
        Raises:
            DatabaseConnectionError: If connection fails
            InitializationError: If already connected
        """
        async with self._lock:
            if self.is_connected:
                logger.warning("Database already connected")
                return
            
            try:
                logger.info("Connecting to database...")
                
                # Create engine with appropriate settings
                engine_kwargs = self._get_engine_kwargs()
                
                self.engine = create_async_engine(
                    self._settings.url,
                    **engine_kwargs
                )
                
                # Create session factory
                self.session_factory = async_sessionmaker(
                    bind=self.engine,
                    class_=AsyncSession,
                    expire_on_commit=False,
                    autocommit=False,
                    autoflush=False
                )
                
                # Test connection
                await self._test_connection()
                
                # Set up event listeners
                self._setup_event_listeners()
                
                self.is_connected = True
                logger.info("Database connection established successfully")
                
            except SQLAlchemyError as e:
                error_msg = f"Failed to connect to database: {str(e)}"
                logger.error(error_msg)
                raise DatabaseConnectionError(
                    message=error_msg,
                    host=self._settings.host,
                    port=self._settings.port,
                    database=self._settings.name,
                    cause=e
                )
    
    def _get_engine_kwargs(self) -> Dict[str, Any]:
        """
        Get engine configuration kwargs based on settings.
        
        Returns:
            Dictionary of engine configuration options
        """
        kwargs: Dict[str, Any] = {
            "echo": self._settings.echo,
            "echo_pool": self._settings.echo_pool,
        }
        
        # Use NullPool for SQLite, QueuePool for others
        if "sqlite" in self._settings.url:
            kwargs["poolclass"] = NullPool
        else:
            kwargs["poolclass"] = QueuePool
            kwargs["pool_size"] = self._settings.pool_size
            kwargs["max_overflow"] = self._settings.max_overflow
            kwargs["pool_timeout"] = self._settings.pool_timeout
            kwargs["pool_recycle"] = self._settings.pool_recycle
            kwargs["pool_pre_ping"] = self._settings.pool_pre_ping
        
        return kwargs
    
    async def _test_connection(self) -> None:
        """
        Test database connection.
        
        Raises:
            DatabaseConnectionError: If connection test fails
        """
        try:
            async with self.engine.connect() as conn:
                await conn.execute(text("SELECT 1"))
                await conn.commit()
                
        except SQLAlchemyError as e:
            raise DatabaseConnectionError(
                message=f"Connection test failed: {str(e)}",
                cause=e
            )
    
    def _setup_event_listeners(self) -> None:
        """Set up SQLAlchemy event listeners for monitoring."""
        
        @event.listens_for(self.engine.sync_engine, "connect")
        def on_connect(dbapi_connection, connection_record):
            logger.debug("New database connection established")
        
        @event.listens_for(self.engine.sync_engine, "checkout")
        def on_checkout(dbapi_connection, connection_record, connection_proxy):
            logger.debug("Connection checked out from pool")
        
        @event.listens_for(self.engine.sync_engine, "checkin")
        def on_checkin(dbapi_connection, connection_record):
            logger.debug("Connection returned to pool")
    
    async def disconnect(self) -> None:
        """
        Close database connection.
        
        Disposes of the engine and cleans up resources.
        """
        async with self._lock:
            if not self.is_connected:
                logger.warning("Database not connected")
                return
            
            try:
                logger.info("Disconnecting from database...")
                
                if self.engine:
                    await self.engine.dispose()
                    self.engine = None
                
                self.session_factory = None
                self.is_connected = False
                
                logger.info("Database disconnected successfully")
                
            except Exception as e:
                logger.error(f"Error during database disconnect: {e}")
                raise
    
    @asynccontextmanager
    async def session(self) -> AsyncGenerator[AsyncSession, None]:
        """
        Context manager for database sessions.
        
        Provides a session that is automatically committed on success
        or rolled back on failure.
        
        Yields:
            AsyncSession: Database session
            
        Raises:
            DatabaseConnectionError: If not connected
            DatabaseQueryError: If query fails
        """
        if not self.is_connected or not self.session_factory:
            raise DatabaseConnectionError("Database not connected")
        
        session = self.session_factory()
        
        try:
            yield session
            await session.commit()
            
        except SQLAlchemyError as e:
            await session.rollback()
            logger.error(f"Database session error: {e}")
            raise DatabaseQueryError(
                message=str(e),
                cause=e
            )
            
        finally:
            await session.close()
    
    @asynccontextmanager
    async def transaction(self) -> AsyncGenerator[AsyncSession, None]:
        """
        Context manager for explicit transactions.
        
        Use when you need explicit control over commit/rollback.
        
        Yields:
            AsyncSession: Database session with active transaction
        """
        if not self.is_connected or not self.session_factory:
            raise DatabaseConnectionError("Database not connected")
        
        session = self.session_factory()
        
        try:
            async with session.begin():
                yield session
                
        except SQLAlchemyError as e:
            logger.error(f"Transaction error: {e}")
            raise DatabaseQueryError(
                message=str(e),
                cause=e
            )
            
        finally:
            await session.close()
    
    async def execute(self, statement: Any) -> Any:
        """
        Execute a SQL statement directly.
        
        Args:
            statement: SQL statement to execute
            
        Returns:
            Query result
        """
        async with self.session() as session:
            result = await session.execute(statement)
            return result
    
    
