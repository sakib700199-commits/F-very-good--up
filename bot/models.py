"""
============================================================================
TELEGRAM UPTIME BOT - DATABASE MODELS
============================================================================
Comprehensive SQLAlchemy ORM models for the uptime monitoring system.

Author: Professional Development Team
Version: 1.0.0
License: MIT
============================================================================
"""

import enum
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from decimal import Decimal

from sqlalchemy import (
    Column, Integer, BigInteger, String, Boolean, DateTime, Text,
    Float, JSON, Enum, ForeignKey, Index, UniqueConstraint,
    CheckConstraint, Table, func, and_, or_
)
from sqlalchemy.orm import relationship, declarative_base, declared_attr
from sqlalchemy.ext.hybrid import hybrid_property, hybrid_method
from sqlalchemy.dialects.postgresql import UUID, JSON, ARRAY
import uuid


# ============================================================================
# BASE MODEL CONFIGURATION
# ============================================================================

Base = declarative_base()


class TimestampMixin:
    """
    Mixin to add created_at and updated_at timestamps to models.
    Automatically manages these fields.
    """
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow,
        server_default=func.now(),
        index=True
    )
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        server_default=func.now(),
        server_onupdate=func.now()
    )


class SoftDeleteMixin:
    """
    Mixin to add soft delete functionality.
    Records are marked as deleted instead of being removed.
    """
    deleted_at = Column(DateTime(timezone=True), nullable=True, index=True)
    is_deleted = Column(Boolean, default=False, nullable=False, index=True)

    def soft_delete(self):
        """Mark record as deleted"""
        self.is_deleted = True
        self.deleted_at = datetime.utcnow()

    def restore(self):
        """Restore a soft-deleted record"""
        self.is_deleted = False
        self.deleted_at = None


class UUIDMixin:
    """
    Mixin to add UUID primary key to models.
    """
    @declared_attr
    def uuid(cls):
        return Column(
            UUID(as_uuid=True),
            primary_key=True,
            default=uuid.uuid4,
            unique=True,
            nullable=False
        )


# ============================================================================
# ENUMERATIONS
# ============================================================================

class UserRole(str, enum.Enum):
    """User role enumeration"""
    OWNER = "owner"
    ADMIN = "admin"
    MODERATOR = "moderator"
    PREMIUM = "premium"
    USER = "user"
    BANNED = "banned"


class UserStatus(str, enum.Enum):
    """User status enumeration"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"
    BANNED = "banned"
    PENDING = "pending"


class LinkStatus(str, enum.Enum):
    """Link monitoring status enumeration"""
    ACTIVE = "active"
    PAUSED = "paused"
    INACTIVE = "inactive"
    ERROR = "error"
    MAINTENANCE = "maintenance"


class MonitorType(str, enum.Enum):
    """Type of monitoring"""
    HTTP = "http"
    HTTPS = "https"
    PING = "ping"
    TCP = "tcp"
    DNS = "dns"
    SSL = "ssl"
    API = "api"
    WEBHOOK = "webhook"


class HTTPMethod(str, enum.Enum):
    """HTTP methods for monitoring"""
    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    DELETE = "DELETE"
    HEAD = "HEAD"
    OPTIONS = "OPTIONS"
    PATCH = "PATCH"


class AlertType(str, enum.Enum):
    """Alert type enumeration"""
    DOWN = "down"
    UP = "up"
    SLOW = "slow"
    SSL_EXPIRY = "ssl_expiry"
    MAINTENANCE = "maintenance"
    ERROR = "error"
    WARNING = "warning"


class LogLevel(str, enum.Enum):
    """Log level enumeration"""
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class NotificationChannel(str, enum.Enum):
    """Notification channel enumeration"""
    TELEGRAM = "telegram"
    EMAIL = "email"
    WEBHOOK = "webhook"
    SMS = "sms"


# ============================================================================
# USER MODEL
# ============================================================================

class User(Base, TimestampMixin, SoftDeleteMixin):
    """
    User model representing bot users with comprehensive features.
    """
    __tablename__ = "users"

    # Primary Key
    id = Column(BigInteger, primary_key=True, index=True)
    
    # User Information
    user_id = Column(BigInteger, unique=True, nullable=False, index=True)
    username = Column(String(255), nullable=True, index=True)
    first_name = Column(String(255), nullable=True)
    last_name = Column(String(255), nullable=True)
    language_code = Column(String(10), nullable=True, default="en")
    
    # Role & Status
    role = Column(
        Enum(UserRole),
        nullable=False,
        default=UserRole.USER,
        index=True
    )
    status = Column(
        Enum(UserStatus),
        nullable=False,
        default=UserStatus.ACTIVE,
        index=True
    )
    
    # Premium Features
    is_premium = Column(Boolean, default=False, nullable=False, index=True)
    premium_until = Column(DateTime(timezone=True), nullable=True)
    
    # Quotas & Limits
    max_links = Column(Integer, default=10, nullable=False)
    current_link_count = Column(Integer, default=0, nullable=False)
    min_ping_interval = Column(Integer, default=300, nullable=False)
    
    # User Settings (JSON)
    settings = Column(JSON, default=dict, nullable=False)
    preferences = Column(JSON, default=dict, nullable=False)
    
    # Notification Settings
    notifications_enabled = Column(Boolean, default=True, nullable=False)
    email_notifications = Column(Boolean, default=False, nullable=False)
    telegram_notifications = Column(Boolean, default=True, nullable=False)
    
    # Activity Tracking
    last_activity = Column(DateTime(timezone=True), nullable=True)
    last_command = Column(String(100), nullable=True)
    total_commands = Column(Integer, default=0, nullable=False)
    
    # Statistics
    total_links_created = Column(Integer, default=0, nullable=False)
    total_alerts_received = Column(Integer, default=0, nullable=False)
    
    # API Access
    api_key = Column(String(255), unique=True, nullable=True, index=True)
    api_enabled = Column(Boolean, default=False, nullable=False)
    api_rate_limit = Column(Integer, default=100, nullable=False)
    
    # Relationships
    links = relationship(
        "MonitoredLink",
        back_populates="user",
        lazy="dynamic",
        cascade="all, delete-orphan"
    )
    alerts = relationship(
        "Alert",
        back_populates="user",
        lazy="dynamic",
        cascade="all, delete-orphan"
    )
    logs = relationship(
        "UserLog",
        back_populates="user",
        lazy="dynamic",
        cascade="all, delete-orphan"
    )
    
    # Indexes
    __table_args__ = (
        Index('idx_user_role_status', 'role', 'status'),
        Index('idx_user_premium', 'is_premium', 'premium_until'),
        Index('idx_user_activity', 'last_activity'),
    )

    @hybrid_property
    def full_name(self) -> str:
        """Get user's full name"""
        if self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name}"
        return self.first_name or self.username or f"User{self.user_id}"

    @hybrid_property
    def is_admin(self) -> bool:
        """Check if user is admin or owner"""
        return self.role in [UserRole.OWNER, UserRole.ADMIN]

    @hybrid_property
    def is_active_premium(self) -> bool:
        """Check if user has active premium subscription"""
        if not self.is_premium:
            return False
        if self.premium_until is None:
            return True
        return self.premium_until > datetime.utcnow()

    @hybrid_property
    def can_add_link(self) -> bool:
        """Check if user can add more links"""
        return self.current_link_count < self.max_links

    @hybrid_property
    def remaining_links(self) -> int:
        """Get remaining link slots"""
        return max(0, self.max_links - self.current_link_count)

    def increment_link_count(self):
        """Increment user's link count"""
        self.current_link_count += 1
        self.total_links_created += 1

    def decrement_link_count(self):
        """Decrement user's link count"""
        if self.current_link_count > 0:
            self.current_link_count -= 1

    def update_activity(self, command: Optional[str] = None):
        """Update user's last activity"""
        self.last_activity = datetime.utcnow()
        if command:
            self.last_command = command
        self.total_commands += 1

    def to_dict(self) -> Dict[str, Any]:
        """Convert user to dictionary"""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "username": self.username,
            "full_name": self.full_name,
            "role": self.role.value,
            "status": self.status.value,
            "is_premium": self.is_premium,
            "premium_until": self.premium_until.isoformat() if self.premium_until else None,
            "max_links": self.max_links,
            "current_link_count": self.current_link_count,
            "remaining_links": self.remaining_links,
            "created_at": self.created_at.isoformat(),
            "last_activity": self.last_activity.isoformat() if self.last_activity else None
        }


# ============================================================================
# MONITORED LINK MODEL
# ============================================================================

class MonitoredLink(Base, TimestampMixin, SoftDeleteMixin):
    """
    Model representing a monitored URL/link with comprehensive monitoring features.
    """
    __tablename__ = "monitored_links"

    # Primary Key
    id = Column(BigInteger, primary_key=True, index=True)
    uuid = Column(UUID(as_uuid=True), default=uuid.uuid4, unique=True, nullable=False)
    
    # Foreign Key
    user_id = Column(
        BigInteger,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    
    # Link Information
    url = Column(Text, nullable=False)
    name = Column(String(500), nullable=True)
    description = Column(Text, nullable=True)
    
    # Monitoring Configuration
    monitor_type = Column(
        Enum(MonitorType),
        nullable=False,
        default=MonitorType.HTTPS,
        index=True
    )
    http_method = Column(
        Enum(HTTPMethod),
        nullable=False,
        default=HTTPMethod.GET
    )
    ping_interval = Column(Integer, default=300, nullable=False)
    timeout = Column(Integer, default=30, nullable=False)
    
    # Status
    status = Column(
        Enum(LinkStatus),
        nullable=False,
        default=LinkStatus.ACTIVE,
        index=True
    )
    is_active = Column(Boolean, default=True, nullable=False, index=True)
    
    # Monitoring State
    last_checked = Column(DateTime(timezone=True), nullable=True)
    next_check = Column(DateTime(timezone=True), nullable=True, index=True)
    last_status_code = Column(Integer, nullable=True)
    last_response_time = Column(Float, nullable=True)
    
    # Uptime Tracking
    is_up = Column(Boolean, default=True, nullable=False, index=True)
    uptime_percentage = Column(Float, default=100.0, nullable=False)
    total_checks = Column(Integer, default=0, nullable=False)
    successful_checks = Column(Integer, default=0, nullable=False)
    failed_checks = Column(Integer, default=0, nullable=False)
    
    # Downtime Tracking
    last_downtime = Column(DateTime(timezone=True), nullable=True)
    total_downtime_seconds = Column(BigInteger, default=0, nullable=False)
    downtime_events = Column(Integer, default=0, nullable=False)
    current_downtime_start = Column(DateTime(timezone=True), nullable=True)
    
    # Performance Metrics
    avg_response_time = Column(Float, nullable=True)
    min_response_time = Column(Float, nullable=True)
    max_response_time = Column(Float, nullable=True)
    
    # SSL/TLS Monitoring
    ssl_enabled = Column(Boolean, default=False, nullable=False)
    ssl_expiry_date = Column(DateTime(timezone=True), nullable=True)
    ssl_issuer = Column(String(500), nullable=True)
    ssl_days_remaining = Column(Integer, nullable=True)
    
    # Alert Configuration
    alert_on_down = Column(Boolean, default=True, nullable=False)
    alert_on_recovery = Column(Boolean, default=True, nullable=False)
    alert_on_slow = Column(Boolean, default=False, nullable=False)
    slow_threshold = Column(Float, default=5.0, nullable=False)
    
    # Custom Headers & Body
    custom_headers = Column(JSON, default=dict, nullable=False)
    request_body = Column(Text, nullable=True)
    
    # Expected Response
    expected_status_codes = Column(ARRAY(Integer), default=[200], nullable=False)
    expected_content = Column(Text, nullable=True)
    
    # Retry Configuration
    max_retries = Column(Integer, default=3, nullable=False)
    retry_delay = Column(Integer, default=5, nullable=False)
    
    # Statistics
    total_uptime_seconds = Column(BigInteger, default=0, nullable=False)
    first_check_at = Column(DateTime(timezone=True), nullable=True)
    
    # Metadata
    extra_info = Column(JSON, default=dict, nullable=False)
    tags = Column(ARRAY(String), default=list, nullable=False)
    
    # Relationships
    user = relationship("User", back_populates="links")
    ping_logs = relationship(
        "PingLog",
        back_populates="link",
        lazy="dynamic",
        cascade="all, delete-orphan"
    )
    alerts = relationship(
        "Alert",
        back_populates="link",
        lazy="dynamic",
        cascade="all, delete-orphan"
    )
    
    # Indexes
    __table_args__ = (
        Index('idx_link_user_status', 'user_id', 'status'),
        Index('idx_link_next_check', 'next_check', 'is_active'),
        Index('idx_link_is_up', 'is_up', 'is_active'),
        Index('idx_link_monitor_type', 'monitor_type', 'status'),
    )

    @hybrid_property
    def display_name(self) -> str:
        """Get display name for the link"""
        return self.name or self.url[:50]

    @hybrid_property
    def is_down(self) -> bool:
        """Check if link is currently down"""
        return not self.is_up

    @hybrid_property
    def downtime_duration(self) -> Optional[int]:
        """Get current downtime duration in seconds"""
        if self.current_downtime_start:
            return int((datetime.utcnow() - self.current_downtime_start).total_seconds())
        return None

    @hybrid_property
    def ssl_is_expiring_soon(self) -> bool:
        """Check if SSL certificate is expiring within 30 days"""
        if not self.ssl_expiry_date:
            return False
        days_remaining = (self.ssl_expiry_date - datetime.utcnow()).days
        return days_remaining <= 30

    def calculate_uptime_percentage(self) -> float:
        """Calculate and update uptime percentage"""
        if self.total_checks == 0:
            return 100.0
        self.uptime_percentage = (self.successful_checks / self.total_checks) * 100
        return self.uptime_percentage

    def record_check(self, success: bool, status_code: Optional[int] = None, 
                    response_time: Optional[float] = None):
        """Record a monitoring check"""
        self.total_checks += 1
        self.last_checked = datetime.utcnow()
        
        if success:
            self.successful_checks += 1
            if not self.is_up:
                # Recovery from downtime
                self.is_up = True
                if self.current_downtime_start:
                    downtime_duration = (datetime.utcnow() - self.current_downtime_start).total_seconds()
                    self.total_downtime_seconds += int(downtime_duration)
                    self.current_downtime_start = None
        else:
            self.failed_checks += 1
            if self.is_up:
                # Start of downtime
                self.is_up = False
                self.last_downtime = datetime.utcnow()
                self.current_downtime_start = datetime.utcnow()
                self.downtime_events += 1
        
        if status_code:
            self.last_status_code = status_code
        
        if response_time:
            self.last_response_time = response_time
            self._update_response_time_stats(response_time)
        
        self.calculate_uptime_percentage()
        self.calculate_next_check()

    def _update_response_time_stats(self, response_time: float):
        """Update response time statistics"""
        if self.avg_response_time is None:
            self.avg_response_time = response_time
        else:
            # Moving average
            self.avg_response_time = (self.avg_response_time * (self.total_checks - 1) + response_time) / self.total_checks
        
        if self.min_response_time is None or response_time < self.min_response_time:
            self.min_response_time = response_time
        
        if self.max_response_time is None or response_time > self.max_response_time:
            self.max_response_time = response_time

    def calculate_next_check(self):
        """Calculate next check time"""
        self.next_check = datetime.utcnow() + timedelta(seconds=self.ping_interval)

    def to_dict(self) -> Dict[str, Any]:
        """Convert link to dictionary"""
        return {
            "id": self.id,
            "uuid": str(self.uuid),
            "url": self.url,
            "name": self.display_name,
            "status": self.status.value,
            "is_up": self.is_up,
            "uptime_percentage": round(self.uptime_percentage, 2),
            "total_checks": self.total_checks,
            "successful_checks": self.successful_checks,
            "failed_checks": self.failed_checks,
            "last_checked": self.last_checked.isoformat() if self.last_checked else None,
            "last_status_code": self.last_status_code,
            "last_response_time": round(self.last_response_time, 3) if self.last_response_time else None,
            "avg_response_time": round(self.avg_response_time, 3) if self.avg_response_time else None,
            "ping_interval": self.ping_interval,
            "created_at": self.created_at.isoformat()
        }


# ============================================================================
# PING LOG MODEL
# ============================================================================

class PingLog(Base, TimestampMixin):
    """
    Model for storing detailed ping/check logs.
    """
    __tablename__ = "ping_logs"

    # Primary Key
    id = Column(BigInteger, primary_key=True, index=True)
    uuid = Column(UUID(as_uuid=True), default=uuid.uuid4, unique=True, nullable=False)
    
    # Foreign Keys
    link_id = Column(
        BigInteger,
        ForeignKey("monitored_links.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    
    # Check Details
    check_time = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow, index=True)
    success = Column(Boolean, nullable=False, index=True)
    
    # Response Details
    status_code = Column(Integer, nullable=True)
    response_time = Column(Float, nullable=True)
    response_size = Column(BigInteger, nullable=True)
    
    # Error Information
    error_message = Column(Text, nullable=True)
    error_type = Column(String(255), nullable=True)
    
    # Request Details
    request_method = Column(String(10), nullable=True)
    request_headers = Column(JSON, default=dict, nullable=False)
    
    # Response Details
    response_headers = Column(JSON, default=dict, nullable=False)
    response_body = Column(Text, nullable=True)
    
    # Network Details
    ip_address = Column(String(45), nullable=True)
    dns_resolution_time = Column(Float, nullable=True)
    connection_time = Column(Float, nullable=True)
    
    # SSL Details
    ssl_verified = Column(Boolean, nullable=True)
    ssl_error = Column(Text, nullable=True)
    
    # Retry Information
    retry_count = Column(Integer, default=0, nullable=False)
    
    # Metadata
    extra_info = Column(JSON, default=dict, nullable=False)
    
    # Relationships
    link = relationship("MonitoredLink", back_populates="ping_logs")
    
    # Indexes
    __table_args__ = (
        Index('idx_ping_log_link_time', 'link_id', 'check_time'),
        Index('idx_ping_log_success', 'success', 'check_time'),
    )

    def to_dict(self) -> Dict[str, Any]:
        """Convert ping log to dictionary"""
        return {
            "id": self.id,
            "link_id": self.link_id,
            "check_time": self.check_time.isoformat(),
            "success": self.success,
            "status_code": self.status_code,
            "response_time": round(self.response_time, 3) if self.response_time else None,
            "error_message": self.error_message,
            "created_at": self.created_at.isoformat()
        }


# ============================================================================
# ALERT MODEL
# ============================================================================

class Alert(Base, TimestampMixin):
    """
    Model for storing alerts and notifications.
    """
    __tablename__ = "alerts"

    # Primary Key
    id = Column(BigInteger, primary_key=True, index=True)
    uuid = Column(UUID(as_uuid=True), default=uuid.uuid4, unique=True, nullable=False)
    
    # Foreign Keys
    user_id = Column(
        BigInteger,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    link_id = Column(
        BigInteger,
        ForeignKey("monitored_links.id", ondelete="CASCADE"),
        nullable=True,
        index=True
    )
    
    # Alert Information
    alert_type = Column(
        Enum(AlertType),
        nullable=False,
        index=True
    )
    title = Column(String(500), nullable=False)
    message = Column(Text, nullable=False)
    
    # Notification Status
    sent = Column(Boolean, default=False, nullable=False, index=True)
    sent_at = Column(DateTime(timezone=True), nullable=True)
    read = Column(Boolean, default=False, nullable=False)
    read_at = Column(DateTime(timezone=True), nullable=True)
    
    # Notification Channels
    channels = Column(ARRAY(String), default=["telegram"], nullable=False)
    
    # Priority
    priority = Column(Integer, default=1, nullable=False)
    
    # Retry Information
    retry_count = Column(Integer, default=0, nullable=False)
    max_retries = Column(Integer, default=3, nullable=False)
    
    # Metadata
    extra_info = Column(JSON, default=dict, nullable=False)
    
    # Relationships
    user = relationship("User", back_populates="alerts")
    link = relationship("MonitoredLink", back_populates="alerts")
    
    # Indexes
    __table_args__ = (
        Index('idx_alert_user_sent', 'user_id', 'sent'),
        Index('idx_alert_type_created', 'alert_type', 'created_at'),
    )

    def mark_as_sent(self):
        """Mark alert as sent"""
        self.sent = True
        self.sent_at = datetime.utcnow()

    def mark_as_read(self):
        """Mark alert as read"""
        self.read = True
        self.read_at = datetime.utcnow()

    def to_dict(self) -> Dict[str, Any]:
        """Convert alert to dictionary"""
        return {
            "id": self.id,
            "type": self.alert_type.value,
            "title": self.title,
            "message": self.message,
            "sent": self.sent,
            "read": self.read,
            "created_at": self.created_at.isoformat()
        }


# ============================================================================
# USER LOG MODEL
# ============================================================================

class UserLog(Base, TimestampMixin):
    """
    Model for storing user activity logs.
    """
    __tablename__ = "user_logs"

    # Primary Key
    id = Column(BigInteger, primary_key=True, index=True)
    
    # Foreign Key
    user_id = Column(
        BigInteger,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    
    # Log Information
    action = Column(String(255), nullable=False, index=True)
    description = Column(Text, nullable=True)
    
    # Log Level
    level = Column(
        Enum(LogLevel),
        nullable=False,
        default=LogLevel.INFO,
        index=True
    )
    
    # Request Information
    command = Column(String(100), nullable=True)
    parameters = Column(JSON, default=dict, nullable=False)
    
    # Result
    success = Column(Boolean, default=True, nullable=False)
    error_message = Column(Text, nullable=True)
    
    # Metadata
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(Text, nullable=True)
    extra_info = Column(JSON, default=dict, nullable=False)
    
    # Relationships
    user = relationship("User", back_populates="logs")
    
    # Indexes
    __table_args__ = (
        Index('idx_user_log_user_action', 'user_id', 'action'),
        Index('idx_user_log_level_created', 'level', 'created_at'),
    )

    def to_dict(self) -> Dict[str, Any]:
        """Convert user log to dictionary"""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "action": self.action,
            "level": self.level.value,
            "success": self.success,
            "created_at": self.created_at.isoformat()
        }


# ============================================================================
# STATISTICS MODEL
# ============================================================================

class Statistics(Base, TimestampMixin):
    """
    Model for storing global statistics and metrics.
    """
    __tablename__ = "statistics"

    # Primary Key
    id = Column(BigInteger, primary_key=True, index=True)
    date = Column(DateTime(timezone=True), nullable=False, unique=True, index=True)
    
    # User Statistics
    total_users = Column(Integer, default=0, nullable=False)
    active_users = Column(Integer, default=0, nullable=False)
    premium_users = Column(Integer, default=0, nullable=False)
    new_users = Column(Integer, default=0, nullable=False)
    
    # Link Statistics
    total_links = Column(Integer, default=0, nullable=False)
    active_links = Column(Integer, default=0, nullable=False)
    up_links = Column(Integer, default=0, nullable=False)
    down_links = Column(Integer, default=0, nullable=False)
    
    # Check Statistics
    total_checks = Column(BigInteger, default=0, nullable=False)
    successful_checks = Column(BigInteger, default=0, nullable=False)
    failed_checks = Column(BigInteger, default=0, nullable=False)
    
    # Alert Statistics
    total_alerts = Column(Integer, default=0, nullable=False)
    alerts_sent = Column(Integer, default=0, nullable=False)
    
    # Performance Metrics
    avg_response_time = Column(Float, nullable=True)
    total_downtime_seconds = Column(BigInteger, default=0, nullable=False)
    
    # System Metrics
    cpu_usage = Column(Float, nullable=True)
    memory_usage = Column(Float, nullable=True)
    disk_usage = Column(Float, nullable=True)
    
    # Metadata
    extra_info = Column(JSON, default=dict, nullable=False)

    def to_dict(self) -> Dict[str, Any]:
        """Convert statistics to dictionary"""
        return {
            "date": self.date.isoformat(),
            "total_users": self.total_users,
            "active_users": self.active_users,
            "total_links": self.total_links,
            "up_links": self.up_links,
            "down_links": self.down_links,
            "total_checks": self.total_checks,
            "successful_checks": self.successful_checks,
            "failed_checks": self.failed_checks
        }


# ============================================================================
# END OF MODELS MODULE
# ============================================================================
