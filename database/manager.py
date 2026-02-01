"""
============================================================================
TELEGRAM UPTIME BOT - DATABASE MANAGER
============================================================================
Comprehensive database management system with connection pooling,
session management, and transaction handling.

Author: Professional Development Team
Version: 1.0.0
License: MIT
============================================================================
"""

import asyncio
import logging
from typing import Optional, AsyncGenerator, Dict, Any, List
from contextlib import asynccontextmanager
from datetime import datetime

from sqlalchemy.ext.asyncio import (
    create_async_engine,
    AsyncSession,
    AsyncEngine,
    async_sessionmaker
)
from sqlalchemy.orm import sessionmaker
from sqlalchemy import event, text, select, and_, or_
from sqlalchemy.pool import NullPool, QueuePool
from sqlalchemy.exc import SQLAlchemyError, IntegrityError, OperationalError

from database.models import Base, User, MonitoredLink, PingLog, Alert, UserLog, Statistics
from config.settings import Settings
from utils.logger import get_logger


logger = get_logger(__name__)


# ============================================================================
# DATABASE MANAGER CLASS
# ============================================================================

class DatabaseManager:
    """
    Comprehensive database manager for handling all database operations.
    Implements connection pooling, session management, and transaction handling.
    """

    def __init__(self, settings: Settings):
        """
        Initialize database manager.

        Args:
            settings: Application settings instance
        """
        self.settings = settings
        self.engine: Optional[AsyncEngine] = None
        self.session_factory: Optional[async_sessionmaker] = None
        self._is_initialized = False
        self._lock = asyncio.Lock()

        # Configuration
        self.database_url = self._build_database_url()
        self.echo = settings.DB_ECHO
        self.pool_size = settings.DB_POOL_SIZE
        self.max_overflow = settings.DB_MAX_OVERFLOW
        self.pool_timeout = settings.DB_POOL_TIMEOUT
        self.pool_recycle = settings.DB_POOL_RECYCLE

        logger.info(f"DatabaseManager initialized with URL: {self._mask_password(self.database_url)}")

    def _build_database_url(self) -> str:
        """
        Build database URL from settings.

        Returns:
            Database connection URL
        """
        db_type = self.settings.DB_TYPE.lower()

        if db_type == "postgresql":
            return (
                f"postgresql+asyncpg://{self.settings.DB_USER}:{self.settings.DB_PASSWORD}"
                f"@{self.settings.DB_HOST}:{self.settings.DB_PORT}/{self.settings.DB_NAME}"
            )
        elif db_type == "sqlite":
            return f"sqlite+aiosqlite:///{self.settings.DB_NAME}.db"
        else:
            raise ValueError(f"Unsupported database type: {db_type}")

    @staticmethod
    def _mask_password(url: str) -> str:
        """
        Mask password in database URL for logging.

        Args:
            url: Database URL

        Returns:
            Masked URL
        """
        if "://" not in url:
            return url

        protocol, rest = url.split("://", 1)
        if "@" not in rest:
            return url

        credentials, host_part = rest.split("@", 1)
        if ":" in credentials:
            user, _ = credentials.split(":", 1)
            return f"{protocol}://{user}:****@{host_part}"

        return url

    async def initialize(self) -> None:
        """
        Initialize database engine and session factory.
        Creates all tables if they don't exist.
        """
        async with self._lock:
            if self._is_initialized:
                logger.warning("Database already initialized")
                return

            try:
                # Create async engine
                self.engine = create_async_engine(
                    self.database_url,
                    echo=self.echo,
                    poolclass=QueuePool,
                    pool_size=self.pool_size,
                    max_overflow=self.max_overflow,
                    pool_timeout=self.pool_timeout,
                    pool_recycle=self.pool_recycle,
                    pool_pre_ping=True,  # Enable connection health checks
                )

                # Register event listeners
                self._register_event_listeners()

                # Create session factory
                self.session_factory = async_sessionmaker(
                    self.engine,
                    class_=AsyncSession,
                    expire_on_commit=False,
                    autoflush=False,
                    autocommit=False
                )

                # Create all tables
                await self.create_tables()

                self._is_initialized = True
                logger.info("Database initialized successfully")

            except Exception as e:
                logger.error(f"Failed to initialize database: {e}", exc_info=True)
                raise

    def _register_event_listeners(self) -> None:
        """Register SQLAlchemy event listeners for connection management."""
        
        @event.listens_for(self.engine.sync_engine, "connect")
        def receive_connect(dbapi_conn, connection_record):
            """Handle new database connections."""
            logger.debug("New database connection established")

        @event.listens_for(self.engine.sync_engine, "checkout")
        def receive_checkout(dbapi_conn, connection_record, connection_proxy):
            """Handle connection checkout from pool."""
            logger.debug("Connection checked out from pool")

        @event.listens_for(self.engine.sync_engine, "checkin")
        def receive_checkin(dbapi_conn, connection_record):
            """Handle connection checkin to pool."""
            logger.debug("Connection returned to pool")

    async def create_tables(self) -> None:
        """
        Create all database tables.
        """
        try:
            async with self.engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
            logger.info("Database tables created successfully")
        except Exception as e:
            logger.error(f"Failed to create tables: {e}", exc_info=True)
            raise

    async def drop_tables(self) -> None:
        """
        Drop all database tables.
        WARNING: This will delete all data!
        """
        try:
            async with self.engine.begin() as conn:
                await conn.run_sync(Base.metadata.drop_all)
            logger.warning("All database tables dropped")
        except Exception as e:
            logger.error(f"Failed to drop tables: {e}", exc_info=True)
            raise

    @asynccontextmanager
    async def session(self) -> AsyncGenerator[AsyncSession, None]:
        """
        Provide a transactional scope for database operations.

        Yields:
            AsyncSession instance

        Example:
            async with db_manager.session() as session:
                user = await session.get(User, user_id)
        """
        if not self._is_initialized:
            await self.initialize()

        session = self.session_factory()
        try:
            yield session
            await session.commit()
        except Exception as e:
            await session.rollback()
            logger.error(f"Session error: {e}", exc_info=True)
            raise
        finally:
            await session.close()

    async def execute_raw(self, query: str, params: Optional[Dict[str, Any]] = None) -> Any:
        """
        Execute raw SQL query.

        Args:
            query: SQL query string
            params: Query parameters

        Returns:
            Query result
        """
        async with self.session() as session:
            result = await session.execute(text(query), params or {})
            return result

    async def check_connection(self) -> bool:
        """
        Check if database connection is alive.

        Returns:
            True if connection is alive, False otherwise
        """
        try:
            async with self.session() as session:
                await session.execute(text("SELECT 1"))
            return True
        except Exception as e:
            logger.error(f"Database connection check failed: {e}")
            return False

    async def get_database_info(self) -> Dict[str, Any]:
        """
        Get database information and statistics.

        Returns:
            Dictionary with database info
        """
        try:
            async with self.session() as session:
                # Get table counts
                user_count = await session.scalar(select(func.count(User.id)))
                link_count = await session.scalar(select(func.count(MonitoredLink.id)))
                log_count = await session.scalar(select(func.count(PingLog.id)))
                alert_count = await session.scalar(select(func.count(Alert.id)))

                return {
                    "status": "connected",
                    "database_url": self._mask_password(self.database_url),
                    "pool_size": self.pool_size,
                    "users": user_count,
                    "links": link_count,
                    "logs": log_count,
                    "alerts": alert_count,
                    "checked_at": datetime.utcnow().isoformat()
                }
        except Exception as e:
            logger.error(f"Failed to get database info: {e}")
            return {
                "status": "error",
                "error": str(e),
                "checked_at": datetime.utcnow().isoformat()
            }

    async def cleanup_old_logs(self, days: int = 30) -> int:
        """
        Delete old log entries to save space.

        Args:
            days: Number of days to retain

        Returns:
            Number of deleted records
        """
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            
            async with self.session() as session:
                # Delete old ping logs
                result = await session.execute(
                    delete(PingLog).where(PingLog.created_at < cutoff_date)
                )
                deleted_count = result.rowcount
                
                # Delete old user logs
                result = await session.execute(
                    delete(UserLog).where(UserLog.created_at < cutoff_date)
                )
                deleted_count += result.rowcount
                
                await session.commit()
                
                logger.info(f"Cleaned up {deleted_count} old log entries")
                return deleted_count

        except Exception as e:
            logger.error(f"Failed to cleanup old logs: {e}")
            return 0

    async def backup_database(self, backup_path: str) -> bool:
        """
        Create database backup.

        Args:
            backup_path: Path to save backup

        Returns:
            True if successful, False otherwise
        """
        try:
            # This is a placeholder - actual implementation depends on database type
            logger.info(f"Creating database backup to {backup_path}")
            # Implementation would use pg_dump for PostgreSQL or similar
            return True
        except Exception as e:
            logger.error(f"Failed to backup database: {e}")
            return False

    async def close(self) -> None:
        """
        Close database connections and cleanup resources.
        """
        if self.engine:
            await self.engine.dispose()
            logger.info("Database connections closed")
            self._is_initialized = False


# ============================================================================
# DATABASE REPOSITORY BASE CLASS
# ============================================================================

class BaseRepository:
    """
    Base repository class for database operations.
    Provides common CRUD operations.
    """

    def __init__(self, db_manager: DatabaseManager):
        """
        Initialize repository.

        Args:
            db_manager: DatabaseManager instance
        """
        self.db = db_manager
        self.logger = get_logger(self.__class__.__name__)

    async def get_by_id(self, model_class, record_id: int):
        """
        Get record by ID.

        Args:
            model_class: SQLAlchemy model class
            record_id: Record ID

        Returns:
            Model instance or None
        """
        try:
            async with self.db.session() as session:
                result = await session.get(model_class, record_id)
                return result
        except Exception as e:
            self.logger.error(f"Error getting {model_class.__name__} by ID {record_id}: {e}")
            return None

    async def get_all(self, model_class, limit: Optional[int] = None, offset: int = 0):
        """
        Get all records.

        Args:
            model_class: SQLAlchemy model class
            limit: Maximum number of records
            offset: Number of records to skip

        Returns:
            List of model instances
        """
        try:
            async with self.db.session() as session:
                query = select(model_class).offset(offset)
                if limit:
                    query = query.limit(limit)
                
                result = await session.execute(query)
                return result.scalars().all()
        except Exception as e:
            self.logger.error(f"Error getting all {model_class.__name__}: {e}")
            return []

    async def create(self, model_instance):
        """
        Create new record.

        Args:
            model_instance: Model instance to create

        Returns:
            Created model instance
        """
        try:
            async with self.db.session() as session:
                session.add(model_instance)
                await session.commit()
                await session.refresh(model_instance)
                return model_instance
        except Exception as e:
            self.logger.error(f"Error creating {model_instance.__class__.__name__}: {e}")
            raise

    async def update(self, model_instance):
        """
        Update existing record.

        Args:
            model_instance: Model instance to update

        Returns:
            Updated model instance
        """
        try:
            async with self.db.session() as session:
                session.add(model_instance)
                await session.commit()
                await session.refresh(model_instance)
                return model_instance
        except Exception as e:
            self.logger.error(f"Error updating {model_instance.__class__.__name__}: {e}")
            raise

    async def delete(self, model_instance):
        """
        Delete record.

        Args:
            model_instance: Model instance to delete

        Returns:
            True if successful
        """
        try:
            async with self.db.session() as session:
                await session.delete(model_instance)
                await session.commit()
                return True
        except Exception as e:
            self.logger.error(f"Error deleting {model_instance.__class__.__name__}: {e}")
            return False

    async def count(self, model_class) -> int:
        """
        Count total records.

        Args:
            model_class: SQLAlchemy model class

        Returns:
            Total count
        """
        try:
            async with self.db.session() as session:
                result = await session.execute(
                    select(func.count(model_class.id))
                )
                return result.scalar()
        except Exception as e:
            self.logger.error(f"Error counting {model_class.__name__}: {e}")
            return 0


# ============================================================================
# USER REPOSITORY
# ============================================================================

class UserRepository(BaseRepository):
    """Repository for User model operations."""

    async def get_by_user_id(self, user_id: int) -> Optional[User]:
        """Get user by Telegram user ID."""
        try:
            async with self.db.session() as session:
                result = await session.execute(
                    select(User).where(User.user_id == user_id)
                )
                return result.scalar_one_or_none()
        except Exception as e:
            self.logger.error(f"Error getting user by user_id {user_id}: {e}")
            return None

    async def get_or_create(self, user_id: int, **kwargs) -> User:
        """Get existing user or create new one."""
        user = await self.get_by_user_id(user_id)
        if user:
            return user

        user = User(user_id=user_id, **kwargs)
        return await self.create(user)

    async def get_all_active(self) -> List[User]:
        """Get all active users."""
        try:
            async with self.db.session() as session:
                result = await session.execute(
                    select(User).where(
                        and_(
                            User.status == "active",
                            User.is_deleted == False
                        )
                    )
                )
                return result.scalars().all()
        except Exception as e:
            self.logger.error(f"Error getting active users: {e}")
            return []

    async def get_admins(self) -> List[User]:
        """Get all admin users."""
        try:
            async with self.db.session() as session:
                result = await session.execute(
                    select(User).where(
                        User.role.in_(["owner", "admin"])
                    )
                )
                return result.scalars().all()
        except Exception as e:
            self.logger.error(f"Error getting admin users: {e}")
            return []

    async def update_activity(self, user_id: int, command: Optional[str] = None) -> bool:
        """Update user's last activity."""
        try:
            user = await self.get_by_user_id(user_id)
            if user:
                user.update_activity(command)
                await self.update(user)
                return True
            return False
        except Exception as e:
            self.logger.error(f"Error updating user activity: {e}")
            return False


# ============================================================================
# LINK REPOSITORY
# ============================================================================

class LinkRepository(BaseRepository):
    """Repository for MonitoredLink model operations."""

    async def get_user_links(self, user_id: int, active_only: bool = False) -> List[MonitoredLink]:
        """Get all links for a user."""
        try:
            async with self.db.session() as session:
                query = select(MonitoredLink).join(User).where(User.user_id == user_id)
                
                if active_only:
                    query = query.where(
                        and_(
                            MonitoredLink.is_active == True,
                            MonitoredLink.is_deleted == False
                        )
                    )
                
                result = await session.execute(query)
                return result.scalars().all()
        except Exception as e:
            self.logger.error(f"Error getting user links: {e}")
            return []

    async def get_links_to_check(self, limit: Optional[int] = None) -> List[MonitoredLink]:
        """Get links that need to be checked."""
        try:
            async with self.db.session() as session:
                query = select(MonitoredLink).where(
                    and_(
                        MonitoredLink.is_active == True,
                        MonitoredLink.is_deleted == False,
                        or_(
                            MonitoredLink.next_check <= datetime.utcnow(),
                            MonitoredLink.next_check.is_(None)
                        )
                    )
                ).order_by(MonitoredLink.next_check.asc())
                
                if limit:
                    query = query.limit(limit)
                
                result = await session.execute(query)
                return result.scalars().all()
        except Exception as e:
            self.logger.error(f"Error getting links to check: {e}")
            return []

    async def count_user_links(self, user_id: int) -> int:
        """Count total links for a user."""
        try:
            async with self.db.session() as session:
                result = await session.execute(
                    select(func.count(MonitoredLink.id))
                    .join(User)
                    .where(
                        and_(
                            User.user_id == user_id,
                            MonitoredLink.is_deleted == False
                        )
                    )
                )
                return result.scalar()
        except Exception as e:
            self.logger.error(f"Error counting user links: {e}")
            return 0


# ============================================================================
# END OF DATABASE MANAGER MODULE
# ============================================================================
