
"""
Database Package for Uptime Bot

Provides database connectivity, models, and repository patterns
for data persistence using SQLAlchemy with async support.
"""

from database.connection import (
    DatabaseManager,
    get_db_manager,
    get_async_session,
    get_session_factory,
    init_database,
    close_database
)

from database.models import (
    Base,
    User,
    Link,
    PingLog,
    UserSettings,
    Notification,
    SystemSettings,
    AuditLog
)

from database.repositories import (
    BaseRepository,
    UserRepository,
    LinkRepository,
    PingLogRepository,
    SettingsRepository
)

__all__ = [
    # Connection
    "DatabaseManager",
    "get_db_manager",
    "get_async_session",
    "get_session_factory",
    "init_database",
    "close_database",
    
    # Models
    "Base",
    "User",
    "Link",
    "PingLog",
    "UserSettings",
    "Notification",
    "SystemSettings",
    "AuditLog",
    
    # Repositories
    "BaseRepository",
    "UserRepository",
    "LinkRepository",
    "PingLogRepository",
    "SettingsRepository"
]
