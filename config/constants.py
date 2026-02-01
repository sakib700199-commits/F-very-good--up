"""
Constants Module for Uptime Bot

Contains all constant values, enumerations, templates, and
static configuration used throughout the application.
"""

from __future__ import annotations

from enum import Enum, IntEnum, auto
from typing import Dict, List, Set, Tuple, Final
from dataclasses import dataclass


class BotCommands(str, Enum):
    """
    Bot Commands Enumeration
    
    Defines all available bot commands with their descriptions.
    """
    
    # User commands
    START = "start"
    HELP = "help"
    ADD = "add"
    REMOVE = "remove"
    DELETE = "delete"
    LIST = "list"
    STATUS = "status"
    STATS = "stats"
    SETTINGS = "settings"
    LOGS = "logs"
    PING = "ping"
    INFO = "info"
    EXPORT = "export"
    IMPORT_CMD = "import"
    CANCEL = "cancel"
    
    # Admin commands
    ADMIN = "admin"
    BROADCAST = "broadcast"
    USERS = "users"
    ALLLINKS = "alllinks"
    BAN = "ban"
    UNBAN = "unban"
    PROMOTE = "promote"
    DEMOTE = "demote"
    MAINTENANCE = "maintenance"
    BACKUP = "backup"
    RESTORE = "restore"
    CLEANLOGS = "cleanlogs"
    SHELL = "shell"
    RESTART = "restart"
    
    @classmethod
    def user_commands(cls) -> List["BotCommands"]:
        """Get list of user-accessible commands."""
        return [
            cls.START, cls.HELP, cls.ADD, cls.REMOVE, cls.LIST,
            cls.STATUS, cls.STATS, cls.SETTINGS, cls.LOGS,
            cls.PING, cls.INFO, cls.EXPORT, cls.CANCEL
        ]
    
    @classmethod
    def admin_commands(cls) -> List["BotCommands"]:
        """Get list of admin-only commands."""
        return [
            cls.ADMIN, cls.BROADCAST, cls.USERS, cls.ALLLINKS,
            cls.BAN, cls.UNBAN, cls.PROMOTE, cls.DEMOTE,
            cls.MAINTENANCE, cls.BACKUP, cls.RESTORE,
            cls.CLEANLOGS, cls.SHELL, cls.RESTART
        ]
    
    @classmethod
    def get_description(cls, command: "BotCommands") -> str:
        """Get command description."""
        descriptions = {
            cls.START: "Start the bot and see welcome message",
            cls.HELP: "Show help message and available commands",
            cls.ADD: "Add a new URL for monitoring",
            cls.REMOVE: "Remove a URL from monitoring",
            cls.DELETE: "Delete a URL from monitoring (alias for remove)",
            cls.LIST: "List all your monitored URLs",
            cls.STATUS: "Check current status of all your URLs",
            cls.STATS: "View detailed statistics",
            cls.SETTINGS: "Manage your settings",
            cls.LOGS: "View ping logs for your URLs",
            cls.PING: "Manually ping a URL",
            cls.INFO: "View detailed info about a URL",
            cls.EXPORT: "Export your URLs to JSON/CSV",
            cls.IMPORT_CMD: "Import URLs from JSON/CSV",
            cls.CANCEL: "Cancel current operation",
            cls.ADMIN: "Open admin dashboard",
            cls.BROADCAST: "Send broadcast message to all users",
            cls.USERS: "Manage users",
            cls.ALLLINKS: "View all monitored links",
            cls.BAN: "Ban a user",
            cls.UNBAN: "Unban a user",
            cls.PROMOTE: "Promote user to admin",
            cls.DEMOTE: "Demote admin to user",
            cls.MAINTENANCE: "Toggle maintenance mode",
            cls.BACKUP: "Create database backup",
            cls.RESTORE: "Restore from backup",
            cls.CLEANLOGS: "Clean old ping logs",
            cls.SHELL: "Execute shell command (owner only)",
            cls.RESTART: "Restart the bot"
        }
        return descriptions.get(command, "No description available")


class UserRoles(IntEnum):
    """
    User Role Enumeration
    
    Defines user permission levels with integer values
    for easy comparison (higher = more permissions).
    """
    
    BANNED = 0
    GUEST = 1
    USER = 2
    PREMIUM = 3
    VIP = 4
    MODERATOR = 5
    ADMIN = 6
    SUPER_ADMIN = 7
    OWNER = 8
    
    @classmethod
    def get_display_name(cls, role: "UserRoles") -> str:
        """Get human-readable role name."""
        names = {
            cls.BANNED: "🚫 Banned",
            cls.GUEST: "👤 Guest",
            cls.USER: "👤 User",
            cls.PREMIUM: "⭐ Premium",
            cls.VIP: "💎 VIP",
            cls.MODERATOR: "🛡️ Moderator",
            cls.ADMIN: "👑 Admin",
            cls.SUPER_ADMIN: "🔱 Super Admin",
            cls.OWNER: "👸 Owner"
        }
        return names.get(role, "Unknown")
    
    @classmethod
    def get_permissions(cls, role: "UserRoles") -> Set[str]:
        """Get permissions for a role."""
        base_permissions = {"view_own_links", "add_links", "remove_links"}
        
        permissions_map = {
            cls.BANNED: set(),
            cls.GUEST: {"view_own_links"},
            cls.USER: base_permissions,
            cls.PREMIUM: base_permissions | {"custom_interval", "export_data", "advanced_stats"},
            cls.VIP: base_permissions | {"custom_interval", "export_data", "advanced_stats", "priority_ping"},
            cls.MODERATOR: base_permissions | {"view_all_links", "view_users", "send_warnings"},
            cls.ADMIN: base_permissions | {"view_all_links", "view_users", "manage_users", "broadcast", "view_logs"},
            cls.SUPER_ADMIN: base_permissions | {"view_all_links", "view_users", "manage_users", "broadcast", "view_logs", "system_settings"},
            cls.OWNER: {"all"}  # Full permissions
        }
        
        return permissions_map.get(role, set())
    
    def has_permission(self, permission: str) -> bool:
        """Check if role has specific permission."""
        perms = self.get_permissions(self)
        return "all" in perms or permission in perms


class LinkStatus(str, Enum):
    """
    Link Status Enumeration
    
    Represents the current state of a monitored link.
    """
    
    ACTIVE = "active"
    PAUSED = "paused"
    DISABLED = "disabled"
    PENDING = "pending"
    ERROR = "error"
    DELETED = "deleted"
    
    @classmethod
    def get_emoji(cls, status: "LinkStatus") -> str:
        """Get emoji for status."""
        emojis = {
            cls.ACTIVE: "✅",
            cls.PAUSED: "⏸️",
            cls.DISABLED: "🔴",
            cls.PENDING: "⏳",
            cls.ERROR: "⚠️",
            cls.DELETED: "🗑️"
        }
        return emojis.get(status, "❓")
    
    @classmethod
    def is_monitorable(cls, status: "LinkStatus") -> bool:
        """Check if status allows monitoring."""
        return status == cls.ACTIVE


class PingStatus(str, Enum):
    """
    Ping Result Status Enumeration
    
    Represents the outcome of a ping operation.
    """
    
    UP = "up"
    DOWN = "down"
    TIMEOUT = "timeout"
    ERROR = "error"
    SSL_ERROR = "ssl_error"
    DNS_ERROR = "dns_error"
    CONNECTION_ERROR = "connection_error"
    UNKNOWN = "unknown"
    SKIPPED = "skipped"
    
    @classmethod
    def get_emoji(cls, status: "PingStatus") -> str:
        """Get emoji for ping status."""
        emojis = {
            cls.UP: "🟢",
            cls.DOWN: "🔴",
            cls.TIMEOUT: "🟡",
            cls.ERROR: "🟠",
            cls.SSL_ERROR: "🔒❌",
            cls.DNS_ERROR: "🌐❌",
            cls.CONNECTION_ERROR: "📡❌",
            cls.UNKNOWN: "⚪",
            cls.SKIPPED: "⏭️"
        }
        return emojis.get(status, "❓")
    
    @classmethod
    def is_successful(cls, status: "PingStatus") -> bool:
        """Check if ping was successful."""
        return status == cls.UP
    
    @classmethod
    def is_failure(cls, status: "PingStatus") -> bool:
        """Check if ping failed."""
        return status in {
            cls.DOWN, cls.TIMEOUT, cls.ERROR,
            cls.SSL_ERROR, cls.DNS_ERROR, cls.CONNECTION_ERROR
        }


class NotificationType(str, Enum):
    """
    Notification Type Enumeration
    
    Types of notifications that can be sent to users.
    """
    
    # Status notifications
    LINK_DOWN = "link_down"
    LINK_UP = "link_up"
    LINK_RECOVERED = "link_recovered"
    LINK_TIMEOUT = "link_timeout"
    LINK_SSL_ERROR = "link_ssl_error"
    
    # System notifications
    SYSTEM_ALERT = "system_alert"
    MAINTENANCE = "maintenance"
    UPDATE = "update"
    
    # User notifications
    WELCOME = "welcome"
    ACCOUNT_UPDATED = "account_updated"
    LIMIT_WARNING = "limit_warning"
    LIMIT_REACHED = "limit_reached"
    
    # Admin notifications
    NEW_USER = "new_user"
    USER_BANNED = "user_banned"
    BROADCAST = "broadcast"
    
    @classmethod
    def get_priority(cls, notification_type: "NotificationType") -> int:
        """Get notification priority (1 = highest)."""
        priorities = {
            cls.LINK_DOWN: 1,
            cls.LINK_SSL_ERROR: 2,
            cls.LINK_TIMEOUT: 3,
            cls.SYSTEM_ALERT: 1,
            cls.LINK_RECOVERED: 4,
            cls.LINK_UP: 5,
            cls.MAINTENANCE: 2,
            cls.UPDATE: 6,
            cls.WELCOME: 7,
            cls.ACCOUNT_UPDATED: 8,
            cls.LIMIT_WARNING: 3,
            cls.LIMIT_REACHED: 2,
            cls.NEW_USER: 5,
            cls.USER_BANNED: 4,
            cls.BROADCAST: 3
        }
        return priorities.get(notification_type, 10)


class TimeIntervals(IntEnum):
    """
    Time Interval Constants
    
    Common time intervals in seconds.
    """
    
    SECONDS_1 = 1
    SECONDS_5 = 5
    SECONDS_10 = 10
    SECONDS_30 = 30
    MINUTE_1 = 60
    MINUTES_2 = 120
    MINUTES_5 = 300
    MINUTES_10 = 600
    MINUTES_15 = 900
    MINUTES_30 = 1800
    HOUR_1 = 3600
    HOURS_2 = 7200
    HOURS_6 = 21600
    HOURS_12 = 43200
    DAY_1 = 86400
    WEEK_1 = 604800
    MONTH_1 = 2592000
    
    @classmethod
    def get_display_name(cls, interval: "TimeIntervals") -> str:
        """Get human-readable interval name."""
        names = {
            cls.SECONDS_1: "1 second",
            cls.SECONDS_5: "5 seconds",
            cls.SECONDS_10: "10 seconds",
            cls.SECONDS_30: "30 seconds",
            cls.MINUTE_1: "1 minute",
            cls.MINUTES_2: "2 minutes",
            cls.MINUTES_5: "5 minutes",
            cls.MINUTES_10: "10 minutes",
            cls.MINUTES_15: "15 minutes",
            cls.MINUTES_30: "30 minutes",
            cls.HOUR_1: "1 hour",
            cls.HOURS_2: "2 hours",
            cls.HOURS_6: "6 hours",
            cls.HOURS_12: "12 hours",
            cls.DAY_1: "1 day",
            cls.WEEK_1: "1 week",
            cls.MONTH_1: "1 month"
        }
        return names.get(interval, f"{interval} seconds")
    
    @classmethod
    def get_available_intervals(cls) -> List[Tuple[int, str]]:
        """Get list of available ping intervals with display names."""
        return [
            (cls.MINUTE_1, "1 minute"),
            (cls.MINUTES_2, "2 minutes"),
            (cls.MINUTES_5, "5 minutes"),
            (cls.MINUTES_10, "10 minutes"),
            (cls.MINUTES_15, "15 minutes"),
            (cls.MINUTES_30, "30 minutes"),
            (cls.HOUR_1, "1 hour"),
            (cls.HOURS_2, "2 hours"),
            (cls.HOURS_6, "6 hours"),
            (cls.HOURS_12, "12 hours"),
            (cls.DAY_1, "24 hours")
        ]


class HTTPMethods(str, Enum):
    """HTTP Methods for ping requests."""
    
    GET = "GET"
    HEAD = "HEAD"
    POST = "POST"
    PUT = "PUT"
    DELETE = "DELETE"
    OPTIONS = "OPTIONS"
    PATCH = "PATCH"


class StatusCodes:
    """
    HTTP Status Code Categories
    
    Provides categorization and utilities for HTTP status codes.
    """
    
    # Successful responses
    SUCCESS: Final[Set[int]] = {200, 201, 202, 203, 204, 205, 206, 207, 208, 226}
    
    # Redirect responses
    REDIRECT: Final[Set[int]] = {300, 301, 302, 303, 304, 305, 307, 308}
    
    # Client errors
    CLIENT_ERROR: Final[Set[int]] = set(range(400, 500))
    
    # Server errors
    SERVER_ERROR: Final[Set[int]] = set(range(500, 600))
    
    # Commonly accepted as "up"
    ACCEPTABLE: Final[Set[int]] = SUCCESS | {301, 302, 307, 308}
    
    @classmethod
    def is_success(cls, code: int) -> bool:
        """Check if status code indicates success."""
        return 200 <= code < 300
    
    @classmethod
    def is_redirect(cls, code: int) -> bool:
        """Check if status code indicates redirect."""
        return 300 <= code < 400
    
    @classmethod
    def is_client_error(cls, code: int) -> bool:
        """Check if status code indicates client error."""
        return 400 <= code < 500
    
    @classmethod
    def is_server_error(cls, code: int) -> bool:
        """Check if status code indicates server error."""
        return 500 <= code < 600
    
    @classmethod
    def get_category(cls, code: int) -> str:
        """Get category name for status code."""
        if cls.is_success(code):
            return "Success"
        elif cls.is_redirect(code):
            return "Redirect"
        elif cls.is_client_error(code):
            return "Client Error"
        elif cls.is_server_error(code):
            return "Server Error"
        return "Unknown"
    
    @classmethod
    def get_description(cls, code: int) -> str:
        """Get description for common status codes."""
        descriptions = {
            200: "OK",
            201: "Created",
            204: "No Content",
            301: "Moved Permanently",
            302: "Found (Redirect)",
            304: "Not Modified",
            400: "Bad Request",
            401: "Unauthorized",
            403: "Forbidden",
            404: "Not Found",
            405: "Method Not Allowed",
            408: "Request Timeout",
            429: "Too Many Requests",
            500: "Internal Server Error",
            502: "Bad Gateway",
            503: "Service Unavailable",
            504: "Gateway Timeout"
        }
        return descriptions.get(code, f"HTTP {code}")


@dataclass(frozen=True)
class MessageTemplates:
    """
    Message Templates for Bot Responses
    
    Contains all message templates used by the bot.
    HTML formatting is used by default.
    """
    
    # Welcome messages
    WELCOME: Final[str] = """
🤖 <b>Welcome to Uptime Bot!</b>

I'm your personal uptime monitoring assistant. I'll keep your websites and services alive by pinging them at regular intervals.

<b>🎯 Quick Start:</b>
• Add URL: <code>/add https://your-site.com</code>
• View links: <code>/list</code>
• Check status: <code>/status</code>

<b>📊 Features:</b>
✅ Unlimited URL monitoring
✅ Custom ping intervals
✅ Real-time alerts
✅ Detailed statistics
✅ Self-ping for hosting platforms

Type /help for all commands.
"""
    
    HELP: Final[str] = """
📚 <b>Uptime Bot Commands</b>

<b>🔗 Link Management:</b>
/add <code>[url]</code> - Add a new URL to monitor
/remove <code>[url or id]</code> - Remove a URL
/list - List all your monitored URLs
/status - Check current status of all URLs
/info <code>[url or id]</code> - Detailed info about a URL

<b>📊 Statistics:</b>
/stats - View your monitoring statistics
/logs <code>[url or id]</code> - View ping logs

<b>⚙️ Settings:</b>
/settings - Manage your preferences

<b>🔧 Utilities:</b>
/ping <code>[url]</code> - Manually ping a URL
/export - Export your data
/cancel - Cancel current operation

<b>Need help?</b>
Contact: @YourSupportBot
"""
    
    # Link operations
    LINK_ADDED: Final[str] = """
✅ <b>URL Added Successfully!</b>

🔗 <b>URL:</b> <code>{url}</code>
📛 <b>Name:</b> {name}
⏱️ <b>Interval:</b> {interval}
📊 <b>Status:</b> {status}

The URL will be monitored automatically.
Use /list to see all your URLs.
"""
    
    LINK_REMOVED: Final[str] = """
🗑️ <b>URL Removed</b>

🔗 <b>URL:</b> <code>{url}</code>

The URL has been removed from monitoring.
"""
    
    LINK_NOT_FOUND: Final[str] = """
❌ <b>URL Not Found</b>

The specified URL was not found in your monitoring list.
Use /list to see your URLs.
"""
    
    LINK_ALREADY_EXISTS: Final[str] = """
⚠️ <b>URL Already Exists</b>

This URL is already being monitored:
🔗 <code>{url}</code>

Use /info to view its current status.
"""
    
    # Status messages
    LINK_STATUS: Final[str] = """
{emoji} <b>{name}</b>
└─ 🔗 <code>{url}</code>
└─ 📊 Status: {status}
└─ ⏱️ Response: {response_time}ms
└─ 📅 Last check: {last_check}
"""
    
    ALL_LINKS_STATUS: Final[str] = """
📊 <b>Your Monitored URLs</b>

{links}

<b>📈 Summary:</b>
• Total: {total}
• Online: {online} 🟢
• Offline: {offline} 🔴
• Paused: {paused} ⏸️
"""
    
    # Alert messages
    ALERT_DOWN: Final[str] = """
🔴 <b>SERVICE DOWN!</b>

🔗 <b>URL:</b> <code>{url}</code>
📛 <b>Name:</b> {name}
📊 <b>Status:</b> {status_code}
⏱️ <b>Down since:</b> {down_since}
📅 <b>Last up:</b> {last_up}

❗ Error: {error_message}
"""
    
    ALERT_UP: Final[str] = """
🟢 <b>SERVICE RECOVERED!</b>

🔗 <b>URL:</b> <code>{url}</code>
📛 <b>Name:</b> {name}
⏱️ <b>Downtime:</b> {downtime}
📊 <b>Response:</b> {response_time}ms

Service is back online! ✅
"""
    
    # Statistics
    STATS_OVERVIEW: Final[str] = """
📊 <b>Your Statistics</b>

<b>📈 Overview:</b>
• Total URLs: {total_links}
• Active: {active_links}
• Paused: {paused_links}

<b>⏱️ Uptime (30 days):</b>
• Average: {avg_uptime}%
• Best: {best_uptime}%
• Worst: {worst_uptime}%

<b>🏓 Ping Stats:</b>
• Total pings: {total_pings}
• Successful: {successful_pings}
• Failed: {failed_pings}

<b>📅 Last 24 hours:</b>
• Checks: {checks_24h}
• Incidents: {incidents_24h}
"""
    
    # Errors
    ERROR_GENERIC: Final[str] = """
❌ <b>An Error Occurred</b>

{error_message}

Please try again or contact support if the issue persists.
"""
    
    ERROR_INVALID_URL: Final[str] = """
❌ <b>Invalid URL</b>

The provided URL is not valid. Please ensure:
• URL starts with http:// or https://
• URL format is correct

Example: <code>/add https://example.com</code>
"""
    
    ERROR_LIMIT_REACHED: Final[str] = """
⚠️ <b>Limit Reached</b>

You've reached the maximum number of monitored URLs ({limit}).

Options:
• Remove unused URLs with /remove
• Upgrade to premium for unlimited URLs

Contact @Admin for assistance.
"""
    
    ERROR_PERMISSION_DENIED: Final[str] = """
🚫 <b>Permission Denied</b>

You don't have permission to perform this action.

Required role: {required_role}
Your role: {user_role}
"""
    
    ERROR_MAINTENANCE: Final[str] = """
🔧 <b>Maintenance Mode</b>

The bot is currently under maintenance.
Please try again later.

Estimated completion: {estimated_time}
"""
    
    # Admin messages
    ADMIN_DASHBOARD: Final[str] = """
👑 <b>Admin Dashboard</b>

<b>📊 System Stats:</b>
• Total users: {total_users}
• Active users: {active_users}
• Total links: {total_links}
• Active pings: {active_pings}

<b>⚙️ System Status:</b>
• Uptime: {bot_uptime}
• Memory: {memory_usage}
• CPU: {cpu_usage}
• Queue: {queue_size}

<b>📅 Today:</b>
• New users: {new_users_today}
• New links: {new_links_today}
• Total pings: {pings_today}

Use the buttons below to manage.
"""
    
    BROADCAST_CONFIRM: Final[str] = """
📢 <b>Broadcast Preview</b>

<b>Message:</b>
{message}

<b>Recipients:</b> {recipient_count} users

⚠️ This will send to ALL users.
Are you sure?
"""
    
    BROADCAST_COMPLETE: Final[str] = """
✅ <b>Broadcast Complete</b>

📤 Sent: {sent}
❌ Failed: {failed}
⏱️ Duration: {duration}
"""
    
    # Pagination
    PAGE_INDICATOR: Final[str] = "Page {current}/{total}"
    
    # Confirmations
    CONFIRM_DELETE: Final[str] = """
⚠️ <b>Confirm Deletion</b>

Are you sure you want to delete:
🔗 <code>{url}</code>

This action cannot be undone.
"""
    
    # Empty states
    NO_LINKS: Final[str] = """
📭 <b>No URLs Found</b>

You haven't added any URLs for monitoring yet.

Add your first URL:
<code>/add https://your-site.com</code>
"""
    
    NO_LOGS: Final[str] = """
📭 <b>No Logs Found</b>

No ping logs available for this URL yet.
Logs will appear after the first ping.
"""


class Limits:
    """
    Application Limits and Constraints
    
    Defines various limits used throughout the application.
    """
    
    # URL limits
    MAX_URL_LENGTH: Final[int] = 2048
    MIN_URL_LENGTH: Final[int] = 10
    MAX_URL_NAME_LENGTH: Final[int] = 100
    MAX_LINKS_FREE: Final[int] = 50
    MAX_LINKS_PREMIUM: Final[int] = 0  # Unlimited
    
    # Message limits
    MAX_MESSAGE_LENGTH: Final[int] = 4096
    MAX_CAPTION_LENGTH: Final[int] = 1024
    MAX_CALLBACK_DATA: Final[int] = 64
    
    # Pagination
    ITEMS_PER_PAGE: Final[int] = 10
    MAX_INLINE_BUTTONS_PER_ROW: Final[int] = 3
    MAX_INLINE_BUTTONS_TOTAL: Final[int] = 100
    
    # Rate limits
    MAX_COMMANDS_PER_MINUTE: Final[int] = 30
    MAX_LINKS_PER_MINUTE: Final[int] = 10
    COOLDOWN_SECONDS: Final[int] = 3
    
    # Timeouts
    CALLBACK_TIMEOUT: Final[int] = 300  # 5 minutes
    SESSION_TIMEOUT: Final[int] = 3600  # 1 hour
    
    # Batch operations
    MAX_BATCH_SIZE: Final[int] = 100
    MAX_IMPORT_SIZE: Final[int] = 1000
    
    # Logs
    MAX_LOGS_DISPLAY: Final[int] = 50
    MAX_LOGS_EXPORT: Final[int] = 10000


class Defaults:
    """
    Default Values
    
    Provides default values for various settings.
    """
    
    # Ping defaults
    PING_INTERVAL: Final[int] = 300  # 5 minutes
    PING_TIMEOUT: Final[int] = 30
    PING_RETRIES: Final[int] = 3
    
    # Notification defaults
    NOTIFY_ON_DOWN: Final[bool] = True
    NOTIFY_ON_UP: Final[bool] = True
    NOTIFY_ON_RECOVERY: Final[bool] = True
    
    # Display defaults
    DATE_FORMAT: Final[str] = "%Y-%m-%d"
    TIME_FORMAT: Final[str] = "%H:%M:%S"
    DATETIME_FORMAT: Final[str] = "%Y-%m-%d %H:%M:%S"
    TIMEZONE: Final[str] = "UTC"
    
    # Link defaults
    LINK_NAME: Final[str] = "Unnamed URL"
    LINK_STATUS: Final[LinkStatus] = LinkStatus.ACTIVE
    
    # User defaults
    USER_ROLE: Final[UserRoles] = UserRoles.USER
    USER_LANGUAGE: Final[str] = "en"
    
    # HTTP defaults
    HTTP_METHOD: Final[HTTPMethods] = HTTPMethods.HEAD
    USER_AGENT: Final[str] = "UptimeBot/1.0 (Monitoring Service)"
    
    # Retry defaults
    RETRY_DELAY: Final[int] = 5
    RETRY_BACKOFF: Final[float] = 2.0


class CacheKeys:
    """
    Cache Key Templates
    
    Defines cache key patterns for different data types.
    """
    
    # User cache
    USER: Final[str] = "user:{user_id}"
    USER_SETTINGS: Final[str] = "user:{user_id}:settings"
    USER_LINKS: Final[str] = "user:{user_id}:links"
    USER_STATS: Final[str] = "user:{user_id}:stats"
    
    # Link cache
    LINK: Final[str] = "link:{link_id}"
    LINK_STATUS: Final[str] = "link:{link_id}:status"
    LINK_LOGS: Final[str] = "link:{link_id}:logs"
    
    # System cache
    SYSTEM_STATS: Final[str] = "system:stats"
    SYSTEM_HEALTH: Final[str] = "system:health"
    
    # Rate limiting
    RATE_LIMIT: Final[str] = "ratelimit:{user_id}:{action}"
    
    # Sessions
    SESSION: Final[str] = "session:{user_id}"
    
    @classmethod
    def user(cls, user_id: int) -> str:
        """Generate user cache key."""
        return cls.USER.format(user_id=user_id)
    
    @classmethod
    def user_settings(cls, user_id: int) -> str:
        """Generate user settings cache key."""
        return cls.USER_SETTINGS.format(user_id=user_id)
    
    @classmethod
    def link(cls, link_id: int) -> str:
        """Generate link cache key."""
        return cls.LINK.format(link_id=link_id)
    
    @classmethod
    def rate_limit(cls, user_id: int, action: str) -> str:
        """Generate rate limit cache key."""
        return cls.RATE_LIMIT.format(user_id=user_id, action=action)


class CallbackPrefixes:
    """
    Callback Data Prefixes
    
    Defines prefixes for inline keyboard callback data.
    """
    
    # Navigation
    NAV: Final[str] = "nav"
    PAGE: Final[str] = "page"
    BACK: Final[str] = "back"
    CLOSE: Final[str] = "close"
    REFRESH: Final[str] = "refresh"
    
    # Link operations
    LINK: Final[str] = "link"
    LINK_VIEW: Final[str] = "link_view"
    LINK_EDIT: Final[str] = "link_edit"
    LINK_DELETE: Final[str] = "link_del"
    LINK_PAUSE: Final[str] = "link_pause"
    LINK_RESUME: Final[str] = "link_resume"
    LINK_PING: Final[str] = "link_ping"
    LINK_LOGS: Final[str] = "link_logs"
    
    # Settings
    SETTINGS: Final[str] = "settings"
    SETTING_TOGGLE: Final[str] = "set_toggle"
    SETTING_VALUE: Final[str] = "set_value"
    
    # Admin
    ADMIN: Final[str] = "admin"
    ADMIN_USERS: Final[str] = "admin_users"
    ADMIN_LINKS: Final[str] = "admin_links"
    ADMIN_BROADCAST: Final[str] = "admin_bc"
    ADMIN_SETTINGS: Final[str] = "admin_set"
    
    # User management
    USER: Final[str] = "user"
    USER_BAN: Final[str] = "user_ban"
    USER_UNBAN: Final[str] = "user_unban"
    USER_PROMOTE: Final[str] = "user_promote"
    USER_DEMOTE: Final[str] = "user_demote"
    
    # Confirmations
    CONFIRM: Final[str] = "confirm"
    CANCEL: Final[str] = "cancel"
    
    # Intervals
    INTERVAL: Final[str] = "interval"
    
    @classmethod
    def make(cls, prefix: str, *args) -> str:
        """Create callback data string."""
        parts = [prefix] + [str(arg) for arg in args]
        return ":".join(parts)
    
    @classmethod
    def parse(cls, data: str) -> List[str]:
        """Parse callback data string."""
        return data.split(":")


# Error codes
class ErrorCodes:
    """Application error codes."""
    
    # General errors (1xxx)
    UNKNOWN_ERROR: Final[int] = 1000
    VALIDATION_ERROR: Final[int] = 1001
    PERMISSION_DENIED: Final[int] = 1002
    RATE_LIMITED: Final[int] = 1003
    MAINTENANCE_MODE: Final[int] = 1004
    
    # Database errors (2xxx)
    DB_CONNECTION_ERROR: Final[int] = 2000
    DB_QUERY_ERROR: Final[int] = 2001
    DB_NOT_FOUND: Final[int] = 2002
    DB_DUPLICATE: Final[int] = 2003
    
    # User errors (3xxx)
    USER_NOT_FOUND: Final[int] = 3000
    USER_BANNED: Final[int] = 3001
    USER_ALREADY_EXISTS: Final[int] = 3002
    
    # Link errors (4xxx)
    LINK_NOT_FOUND: Final[int] = 4000
    LINK_ALREADY_EXISTS: Final[int] = 4001
    LINK_INVALID_URL: Final[int] = 4002
    LINK_LIMIT_REACHED: Final[int] = 4003
    
    # Monitoring errors (5xxx)
    PING_TIMEOUT: Final[int] = 5000
    PING_ERROR: Final[int] = 5001
    SSL_ERROR: Final[int] = 5002
    DNS_ERROR: Final[int] = 5003


# Regex patterns
class Patterns:
    """Regular expression patterns."""
    
    URL: Final[str] = (
        r"https?:\/\/(www\.)?[-a-zA-Z0-9@:%._\+~#=]{1,256}\."
        r"[a-zA-Z0-9()]{1,6}\b([-a-zA-Z0-9()@:%_\+.~#?&//=]*)"
    )
    
    DOMAIN: Final[str] = (
        r"^(?:[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.)+"
        r"[a-zA-Z]{2,}$"
    )
    
    IP_ADDRESS: Final[str] = (
        r"^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}"
        r"(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$"
    )
    
    BOT_TOKEN: Final[str] = r"^\d+:[A-Za-z0-9_-]{35,}$"
