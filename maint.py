# ═══════════════════════════════════════════════════════════════════════════════
# ██████╗ ██╗   ██╗██╗  ██╗██╗    ██╗  ██╗    ██╗  ██╗ ██████╗ ███████╗████████╗
# ██╔══██╗██║   ██║██║  ██║██║    ╚██╗██╔╝    ██║  ██║██╔═══██╗██╔════╝╚══██╔══╝
# ██████╔╝██║   ██║███████║██║     ╚███╔╝     ███████║██║   ██║███████╗   ██║
# ██╔══██╗██║   ██║██╔══██║██║     ██╔██╗     ██╔══██║██║   ██║╚════██║   ██║
# ██║  ██║╚██████╔╝██║  ██║██║    ██╔╝ ██╗    ██║  ██║╚██████╔╝███████║   ██║
# ╚═╝  ╚═╝ ╚═════╝ ╚═╝  ╚═╝╚═╝    ╚═╝  ╚═╝    ╚═╝  ╚═╝ ╚═════╝ ╚══════╝   ╚═╝
# ═══════════════════════════════════════════════════════════════════════════════

# ┌─────────────────────────────────────────────────────────────────────────────┐
# │                        SECTION 1: IMPORTS & SETUP                          │
# └─────────────────────────────────────────────────────────────────────────────┘

import os
import sys
import json
import time
import signal
import shutil
import sqlite3
import hashlib
import zipfile
import tarfile
import logging
import asyncio
import platform
import subprocess
import traceback
import threading
import mimetypes
import re
import uuid
import io
import stat
import tempfile
from telegram.constants import ChatAction
from enum import Enum, auto
from pathlib import Path
from datetime import datetime, timedelta
from typing import (
    Dict, List, Optional, Tuple, Any,
    Union, Callable, Set, TypeVar, Coroutine
)
from dataclasses import dataclass, field, asdict
from collections import defaultdict, deque
from functools import wraps, lru_cache
from contextlib import contextmanager, asynccontextmanager
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor

# ── Telegram Bot API ──
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
    KeyboardButton,
    BotCommand,
    InputFile,
    Message,
    CallbackQuery,
    Document,
)
from telegram.ext import (
    Application,
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ConversationHandler,
    ContextTypes,
    filters,
    Defaults,
    JobQueue,
)
from telegram.constants import ParseMode, ChatType
from telegram.error import (
    TelegramError,
    BadRequest,
    TimedOut,
    NetworkError,
    Forbidden,
    RetryAfter,
)

# ── System Monitoring ──
import psutil

# ── Logging Configuration ──
logging.basicConfig(
    format="%(asctime)s │ %(name)-18s │ %(levelname)-8s │ %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    level=logging.INFO,
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("ruhi_hosting.log", encoding="utf-8"),
    ],
)
logger = logging.getLogger("RUHI_X_HOSTING")


# ┌─────────────────────────────────────────────────────────────────────────────┐
# │                    SECTION 2: CONFIGURATION & CONSTANTS                     │
# └─────────────────────────────────────────────────────────────────────────────┘

# ═══════════════════════════════════════════
#  ★ EDIT THESE VALUES TO CUSTOMIZE YOUR BOT
# ═══════════════════════════════════════════

BOT_TOKEN = "8486988430:AAF2PDOxKUVaQAAEM1gxPm_uy0IrD3C8I3o"                # ← Your Bot Token from @BotFather
OWNER_USERNAME = "@RUHI_VIG_QNR"                      # ← Your Telegram username
OWNER_ID = 8128852482                               # ← Your Telegram numeric ID
BOT_NAME = "RUHI X HOSTING"                        # ← Bot display name
BOT_VERSION = "3.0.0"                              # ← Bot version
BOT_BUILD = "PRODUCTION"                           # ← Build type

# ── Directory Structure ──
BASE_DIR = Path(__file__).parent.resolve()
PROJECTS_DIR = BASE_DIR / "projects"
UPLOADS_DIR = BASE_DIR / "uploads"
LOGS_DIR = BASE_DIR / "logs"
BACKUPS_DIR = BASE_DIR / "backups"
TEMP_DIR = BASE_DIR / "temp"
DATABASE_PATH = BASE_DIR / "ruhi_hosting.db"

# ── Create directories ──
for _dir in [PROJECTS_DIR, UPLOADS_DIR, LOGS_DIR, BACKUPS_DIR, TEMP_DIR]:
    _dir.mkdir(parents=True, exist_ok=True)

# ── Limits & Thresholds ──
MAX_UPLOAD_SIZE_MB = 50
MAX_PROJECTS = 25
MAX_LOG_LINES = 100
MAX_FILE_LIST = 50
PROCESS_TIMEOUT = 300  # seconds
HEALTH_CHECK_INTERVAL = 30  # seconds
LOG_STREAM_INTERVAL = 2  # seconds
SESSION_TIMEOUT = 3600  # 1 hour

# ── Supported Project Types ──
SUPPORTED_MAIN_FILES = {
    "python": [
        "main.py", "app.py", "bot.py", "run.py", "server.py",
        "index.py", "manage.py", "start.py", "launch.py", "hosting.py",
    ],
    "nodejs": [
        "index.js", "app.js", "server.js", "main.js", "bot.js",
        "start.js", "run.js",
    ],
    "java": [
        "Main.java", "App.java", "Server.java", "Application.java",
    ],
}

RUNTIME_COMMANDS = {
    "python": "python3",
    "nodejs": "node",
    "java": "java",
}

SUPPORTED_ARCHIVES = {".zip", ".tar", ".tar.gz", ".tgz", ".tar.bz2"}

# ── Allowed Users (set of Telegram user IDs; empty = owner only) ──
ALLOWED_USERS: Set[int] = set()


# ┌─────────────────────────────────────────────────────────────────────────────┐
# │                SECTION 3: DECORATIVE FONTS & UI CONSTANTS                   │
# └─────────────────────────────────────────────────────────────────────────────┘

class Fonts:
    """Unicode small-caps and styled text generator."""

    SMALL_CAPS_MAP = {
        'a': 'ᴀ', 'b': 'ʙ', 'c': 'ᴄ', 'd': 'ᴅ', 'e': 'ᴇ', 'f': 'ғ',
        'g': 'ɢ', 'h': 'ʜ', 'i': 'ɪ', 'j': 'ᴊ', 'k': 'ᴋ', 'l': 'ʟ',
        'm': 'ᴍ', 'n': 'ɴ', 'o': 'ᴏ', 'p': 'ᴘ', 'q': 'ǫ', 'r': 'ʀ',
        's': 's', 't': 'ᴛ', 'u': 'ᴜ', 'v': 'ᴠ', 'w': 'ᴡ', 'x': 'x',
        'y': 'ʏ', 'z': 'ᴢ',
    }

    BOLD_MAP = {
        'A': '𝗔', 'B': '𝗕', 'C': '𝗖', 'D': '𝗗', 'E': '𝗘', 'F': '𝗙',
        'G': '𝗚', 'H': '𝗛', 'I': '𝗜', 'J': '𝗝', 'K': '𝗞', 'L': '𝗟',
        'M': '𝗠', 'N': '𝗡', 'O': '𝗢', 'P': '𝗣', 'Q': '𝗤', 'R': '𝗥',
        'S': '𝗦', 'T': '𝗧', 'U': '𝗨', 'V': '𝗩', 'W': '𝗪', 'X': '𝗫',
        'Y': '𝗬', 'Z': '𝗭',
        'a': '𝗮', 'b': '𝗯', 'c': '𝗰', 'd': '𝗱', 'e': '𝗲', 'f': '𝗳',
        'g': '𝗴', 'h': '𝗵', 'i': '𝗶', 'j': '𝗷', 'k': '𝗸', 'l': '𝗹',
        'm': '𝗺', 'n': '𝗻', 'o': '𝗼', 'p': '𝗽', 'q': '𝗾', 'r': '𝗿',
        's': '𝘀', 't': '𝘁', 'u': '𝘂', 'v': '𝘃', 'w': '𝘄', 'x': '𝘅',
        'y': '𝘆', 'z': '𝘇',
        '0': '𝟬', '1': '𝟭', '2': '𝟮', '3': '𝟯', '4': '𝟰',
        '5': '𝟱', '6': '𝟲', '7': '𝟳', '8': '𝟴', '9': '𝟵',
    }

    MONO_MAP = {
        'A': '𝙰', 'B': '𝙱', 'C': '𝙲', 'D': '𝙳', 'E': '𝙴', 'F': '𝙵',
        'G': '𝙶', 'H': '𝙷', 'I': '𝙸', 'J': '𝙹', 'K': '𝙺', 'L': '𝙻',
        'M': '𝙼', 'N': '𝙽', 'O': '𝙾', 'P': '𝙿', 'Q': '𝚀', 'R': '𝚁',
        'S': '𝚂', 'T': '𝚃', 'U': '𝚄', 'V': '𝚅', 'W': '𝚆', 'X': '𝚇',
        'Y': '𝚈', 'Z': '𝚉',
        'a': '𝚊', 'b': '𝚋', 'c': '𝚌', 'd': '𝚍', 'e': '𝚎', 'f': '𝚏',
        'g': '𝚐', 'h': '𝚑', 'i': '𝚒', 'j': '𝚓', 'k': '𝚔', 'l': '𝚕',
        'm': '𝚖', 'n': '𝚗', 'o': '𝚘', 'p': '𝚙', 'q': '𝚚', 'r': '𝚛',
        's': '𝚜', 't': '𝚝', 'u': '𝚞', 'v': '𝚟', 'w': '𝚠', 'x': '𝚡',
        'y': '𝚢', 'z': '𝚣',
    }

    @classmethod
    def small_caps(cls, text: str) -> str:
        return "".join(cls.SMALL_CAPS_MAP.get(c, c) for c in text.lower())

    @classmethod
    def bold(cls, text: str) -> str:
        return "".join(cls.BOLD_MAP.get(c, c) for c in text)

    @classmethod
    def mono(cls, text: str) -> str:
        return "".join(cls.MONO_MAP.get(c, c) for c in text)


class Emoji:
    """Centralized emoji constants for consistent UI."""

    # ── Status ──
    ONLINE = "🟢"
    OFFLINE = "🔴"
    WARNING = "🟡"
    LOADING = "⏳"
    SUCCESS = "✅"
    ERROR = "❌"
    INFO = "ℹ️"

    # ── System ──
    CPU = "🖥️"
    RAM = "🧠"
    DISK = "💾"
    NETWORK = "🌐"
    UPTIME = "⏱️"
    TEMP = "🌡️"

    # ── Actions ──
    DEPLOY = "🚀"
    STOP = "⏹️"
    RESTART = "🔄"
    DELETE = "🗑️"
    UPLOAD = "📤"
    DOWNLOAD = "📥"
    EDIT = "✏️"
    SEARCH = "🔍"
    SETTINGS = "⚙️"
    BACK = "◀️"
    FORWARD = "▶️"
    HOME = "🏠"
    REFRESH = "🔃"

    # ── Files ──
    FOLDER = "📁"
    FILE = "📄"
    CODE = "💻"
    ZIP = "🗜️"
    LOG = "📋"
    DATABASE = "🗄️"

    # ── UI ──
    STAR = "⭐"
    DIAMOND = "💎"
    FIRE = "🔥"
    BOLT = "⚡"
    SHIELD = "🛡️"
    KEY = "🔑"
    CROWN = "👑"
    ROCKET = "🚀"
    HEART = "❤️"
    GEAR = "⚙️"
    PIN = "📌"
    BELL = "🔔"
    LOCK = "🔒"
    UNLOCK = "🔓"
    CHART = "📊"
    CLOCK = "🕐"
    SPARKLE = "✨"
    LIGHTNING = "⚡"
    GLOBE = "🌍"
    SERVER = "🖧"
    TERMINAL = "🖥️"
    PACKAGE = "📦"
    WRENCH = "🔧"
    HAMMER = "🔨"
    MAGIC = "🪄"
    CHECKMARK = "☑️"
    CROSS = "☒"
    WAVE = "👋"
    USER = "👤"
    USERS = "👥"
    LINK = "🔗"
    STATS = "📈"
    BUG = "🐛"
    ROBOT = "🤖"


class UI:
    """UI decoration strings and separators."""

    DIVIDER_THIN = "•── ⋅ ⋅ ⋅ ────── ⋅ ⋅ ────── ⋅ ⋅ ⋅ ──•"
    DIVIDER_THICK = "═══════════════════════════════════"
    DIVIDER_STAR = "★ ═══════════════════════════ ★"
    DIVIDER_DIAMOND = "◇━━━━━━━━━━━━━━━━━━━━━━━━━━━◇"
    DIVIDER_DOT = "• • • • • • • • • • • • • • • • • •"
    DIVIDER_WAVE = "〰️〰️〰️〰️〰️〰️〰️〰️〰️〰️〰️〰️〰️〰️〰️"
    DIVIDER_ARROW = "▸▸▸▸▸▸▸▸▸▸▸▸▸▸▸▸▸▸▸▸▸▸▸▸▸▸▸"
    DIVIDER_BLOCK = "▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓"

    BULLET = "๏"
    ARROW_R = "➤"
    ARROW_R2 = "➜"
    DOT = "•"
    CIRCLE = "◉"
    TRIANGLE = "▸"
    SQUARE = "▪"
    CHECK = "✓"
    CROSS = "✗"

    HEADER_TOP = "╔═══════════════════════════════════╗"
    HEADER_BOT = "╚═══════════════════════════════════╝"
    HEADER_MID = "╠═══════════════════════════════════╣"
    HEADER_L = "║"
    HEADER_R = "║"

    BOX_TL = "┌"
    BOX_TR = "┐"
    BOX_BL = "└"
    BOX_BR = "┘"
    BOX_H = "─"
    BOX_V = "│"

    @staticmethod
    def box(title: str, content: str, width: int = 35) -> str:
        """Create a Unicode box around content."""
        lines = content.split("\n")
        top = f"┌{'─' * (width + 2)}┐"
        title_line = f"│ {title:^{width}} │"
        sep = f"├{'─' * (width + 2)}┤"
        body = "\n".join(f"│ {line:<{width}} │" for line in lines)
        bottom = f"└{'─' * (width + 2)}┘"
        return f"{top}\n{title_line}\n{sep}\n{body}\n{bottom}"

    @staticmethod
    def progress_bar(current: float, total: float, length: int = 20) -> str:
        """Generate a visual progress bar."""
        if total <= 0:
            percent = 0
        else:
            percent = min(current / total, 1.0)
        filled = int(length * percent)
        empty = length - filled
        bar = "█" * filled + "░" * empty
        pct = percent * 100
        return f"[{bar}] {pct:.1f}%"

    @staticmethod
    def status_dot(is_active: bool) -> str:
        return Emoji.ONLINE if is_active else Emoji.OFFLINE

    @staticmethod
    def format_bytes(bytes_val: int) -> str:
        """Format bytes to human-readable string."""
        if bytes_val < 0:
            return "0 B"
        for unit in ["B", "KB", "MB", "GB", "TB"]:
            if abs(bytes_val) < 1024.0:
                return f"{bytes_val:.2f} {unit}"
            bytes_val /= 1024.0
        return f"{bytes_val:.2f} PB"

    @staticmethod
    def format_uptime(seconds: float) -> str:
        """Format seconds to human-readable uptime."""
        days = int(seconds // 86400)
        hours = int((seconds % 86400) // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        parts = []
        if days > 0:
            parts.append(f"{days}d")
        if hours > 0:
            parts.append(f"{hours}h")
        if minutes > 0:
            parts.append(f"{minutes}m")
        parts.append(f"{secs}s")
        return " ".join(parts)

    @staticmethod
    def truncate(text: str, max_len: int = 50) -> str:
        if len(text) <= max_len:
            return text
        return text[: max_len - 3] + "..."


# ┌─────────────────────────────────────────────────────────────────────────────┐
# │                    SECTION 4: DATABASE SCHEMA & MANAGER                     │
# └─────────────────────────────────────────────────────────────────────────────┘

class DatabaseManager:
    """
    SQLite3 Database Manager for RUHI X HOSTING.
    Handles all persistent storage: users, projects, deployments, logs, settings.
    Thread-safe with connection pooling.
    """

    SCHEMA_VERSION = 3

    SCHEMA_SQL = """
    -- ═══════════════════════════════════════
    -- Table: schema_version
    -- Tracks database migration version
    -- ═══════════════════════════════════════
    CREATE TABLE IF NOT EXISTS schema_version (
        id              INTEGER PRIMARY KEY DEFAULT 1,
        version         INTEGER NOT NULL DEFAULT 1,
        updated_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        CHECK (id = 1)
    );

    -- ═══════════════════════════════════════
    -- Table: users
    -- Stores authorized users and their data
    -- ═══════════════════════════════════════
    CREATE TABLE IF NOT EXISTS users (
        user_id         INTEGER PRIMARY KEY,
        username        TEXT,
        first_name      TEXT,
        last_name       TEXT,
        is_owner        INTEGER DEFAULT 0,
        is_admin        INTEGER DEFAULT 0,
        is_banned       INTEGER DEFAULT 0,
        language        TEXT DEFAULT 'en',
        theme           TEXT DEFAULT 'default',
        notifications   INTEGER DEFAULT 1,
        max_projects    INTEGER DEFAULT 10,
        total_deploys   INTEGER DEFAULT 0,
        last_active     TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        joined_at       TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        settings_json   TEXT DEFAULT '{}'
    );

    -- ═══════════════════════════════════════
    -- Table: projects
    -- Stores project metadata
    -- ═══════════════════════════════════════
    CREATE TABLE IF NOT EXISTS projects (
        project_id      TEXT PRIMARY KEY,
        user_id         INTEGER NOT NULL,
        project_name    TEXT NOT NULL,
        project_type    TEXT NOT NULL DEFAULT 'python',
        main_file       TEXT,
        directory       TEXT NOT NULL,
        description     TEXT DEFAULT '',
        status          TEXT DEFAULT 'stopped',
        pid             INTEGER DEFAULT NULL,
        port            INTEGER DEFAULT NULL,
        auto_restart    INTEGER DEFAULT 0,
        restart_count   INTEGER DEFAULT 0,
        max_restarts    INTEGER DEFAULT 5,
        env_vars        TEXT DEFAULT '{}',
        dependencies    TEXT DEFAULT '[]',
        created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        last_deployed   TIMESTAMP DEFAULT NULL,
        last_stopped    TIMESTAMP DEFAULT NULL,
        total_runtime   REAL DEFAULT 0,
        deploy_count    INTEGER DEFAULT 0,
        error_count     INTEGER DEFAULT 0,
        config_json     TEXT DEFAULT '{}',
        FOREIGN KEY (user_id) REFERENCES users(user_id)
    );

    -- ═══════════════════════════════════════
    -- Table: deployment_logs
    -- Stores deployment history
    -- ═══════════════════════════════════════
    CREATE TABLE IF NOT EXISTS deployment_logs (
        log_id          INTEGER PRIMARY KEY AUTOINCREMENT,
        project_id      TEXT NOT NULL,
        user_id         INTEGER NOT NULL,
        action          TEXT NOT NULL,
        status          TEXT NOT NULL,
        message         TEXT DEFAULT '',
        pid             INTEGER DEFAULT NULL,
        duration        REAL DEFAULT 0,
        exit_code       INTEGER DEFAULT NULL,
        created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (project_id) REFERENCES projects(project_id),
        FOREIGN KEY (user_id) REFERENCES users(user_id)
    );

    -- ═══════════════════════════════════════
    -- Table: process_logs
    -- Stores stdout/stderr output from processes
    -- ═══════════════════════════════════════
    CREATE TABLE IF NOT EXISTS process_logs (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        project_id      TEXT NOT NULL,
        log_type        TEXT DEFAULT 'stdout',
        content         TEXT NOT NULL,
        created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (project_id) REFERENCES projects(project_id)
    );

    -- ═══════════════════════════════════════
    -- Table: file_operations
    -- Audit trail for file operations
    -- ═══════════════════════════════════════
    CREATE TABLE IF NOT EXISTS file_operations (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id         INTEGER NOT NULL,
        project_id      TEXT,
        operation       TEXT NOT NULL,
        file_path       TEXT NOT NULL,
        file_size       INTEGER DEFAULT 0,
        status          TEXT DEFAULT 'success',
        details         TEXT DEFAULT '',
        created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(user_id)
    );

    -- ═══════════════════════════════════════
    -- Table: system_stats
    -- Periodic system health snapshots
    -- ═══════════════════════════════════════
    CREATE TABLE IF NOT EXISTS system_stats (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        cpu_percent     REAL,
        ram_total       INTEGER,
        ram_used        INTEGER,
        ram_percent     REAL,
        disk_total      INTEGER,
        disk_used       INTEGER,
        disk_percent    REAL,
        net_sent        INTEGER DEFAULT 0,
        net_recv        INTEGER DEFAULT 0,
        active_procs    INTEGER DEFAULT 0,
        load_avg        TEXT DEFAULT '',
        created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    -- ═══════════════════════════════════════
    -- Table: notifications
    -- Stores user notifications
    -- ═══════════════════════════════════════
    CREATE TABLE IF NOT EXISTS notifications (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id         INTEGER NOT NULL,
        title           TEXT NOT NULL,
        message         TEXT NOT NULL,
        notif_type      TEXT DEFAULT 'info',
        is_read         INTEGER DEFAULT 0,
        created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(user_id)
    );

    -- ═══════════════════════════════════════
    -- Table: scheduled_tasks
    -- Scheduled/cron tasks for projects
    -- ═══════════════════════════════════════
    CREATE TABLE IF NOT EXISTS scheduled_tasks (
        task_id         TEXT PRIMARY KEY,
        project_id      TEXT NOT NULL,
        user_id         INTEGER NOT NULL,
        task_name       TEXT NOT NULL,
        task_type       TEXT NOT NULL DEFAULT 'restart',
        cron_expr       TEXT DEFAULT '',
        interval_sec    INTEGER DEFAULT 0,
        is_active       INTEGER DEFAULT 1,
        last_run        TIMESTAMP DEFAULT NULL,
        next_run        TIMESTAMP DEFAULT NULL,
        run_count       INTEGER DEFAULT 0,
        created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (project_id) REFERENCES projects(project_id),
        FOREIGN KEY (user_id) REFERENCES users(user_id)
    );

    -- ═══════════════════════════════════════
    -- Indexes for performance
    -- ═══════════════════════════════════════
    CREATE INDEX IF NOT EXISTS idx_projects_user ON projects(user_id);
    CREATE INDEX IF NOT EXISTS idx_projects_status ON projects(status);
    CREATE INDEX IF NOT EXISTS idx_deployment_logs_project ON deployment_logs(project_id);
    CREATE INDEX IF NOT EXISTS idx_deployment_logs_user ON deployment_logs(user_id);
    CREATE INDEX IF NOT EXISTS idx_process_logs_project ON process_logs(project_id);
    CREATE INDEX IF NOT EXISTS idx_process_logs_created ON process_logs(created_at);
    CREATE INDEX IF NOT EXISTS idx_file_operations_user ON file_operations(user_id);
    CREATE INDEX IF NOT EXISTS idx_system_stats_created ON system_stats(created_at);
    CREATE INDEX IF NOT EXISTS idx_notifications_user ON notifications(user_id);
    CREATE INDEX IF NOT EXISTS idx_notifications_read ON notifications(is_read);
    CREATE INDEX IF NOT EXISTS idx_scheduled_tasks_project ON scheduled_tasks(project_id);
    """

    def __init__(self, db_path: Path = DATABASE_PATH):
        self.db_path = db_path
        self._lock = threading.Lock()
        self._local = threading.local()
        self._initialized = False
        self.initialize()

    def _get_connection(self) -> sqlite3.Connection:
        """Get thread-local database connection."""
        if not hasattr(self._local, "connection") or self._local.connection is None:
            conn = sqlite3.connect(
                str(self.db_path),
                timeout=30,
                check_same_thread=False,
            )
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA synchronous=NORMAL")
            conn.execute("PRAGMA cache_size=10000")
            conn.execute("PRAGMA temp_store=MEMORY")
            conn.execute("PRAGMA mmap_size=268435456")
            conn.execute("PRAGMA foreign_keys=ON")
            self._local.connection = conn
        return self._local.connection

    @property
    def conn(self) -> sqlite3.Connection:
        return self._get_connection()

    def initialize(self):
        """Initialize database schema."""
        with self._lock:
            if self._initialized:
                return
            try:
                cursor = self.conn.cursor()
                # Execute schema SQL (split by semicolons for multi-statement)
                cursor.executescript(self.SCHEMA_SQL)

                # Insert or update schema version
                cursor.execute(
                    "INSERT OR REPLACE INTO schema_version (id, version, updated_at) "
                    "VALUES (1, ?, CURRENT_TIMESTAMP)",
                    (self.SCHEMA_VERSION,),
                )
                self.conn.commit()
                self._initialized = True
                logger.info(
                    f"Database initialized successfully. Schema v{self.SCHEMA_VERSION}"
                )
            except Exception as e:
                logger.error(f"Database initialization failed: {e}")
                raise

    def execute(
        self, query: str, params: tuple = (), fetch: bool = False
    ) -> Union[List[sqlite3.Row], int]:
        """Execute a query with thread safety."""
        with self._lock:
            try:
                cursor = self.conn.cursor()
                cursor.execute(query, params)
                if fetch:
                    return cursor.fetchall()
                self.conn.commit()
                return cursor.lastrowid
            except sqlite3.Error as e:
                logger.error(f"DB Execute Error: {e}\nQuery: {query}\nParams: {params}")
                self.conn.rollback()
                raise

    def execute_many(self, query: str, params_list: List[tuple]):
        """Execute multiple queries."""
        with self._lock:
            try:
                cursor = self.conn.cursor()
                cursor.executemany(query, params_list)
                self.conn.commit()
            except sqlite3.Error as e:
                logger.error(f"DB ExecuteMany Error: {e}")
                self.conn.rollback()
                raise

    def fetchone(self, query: str, params: tuple = ()) -> Optional[sqlite3.Row]:
        """Fetch a single row."""
        with self._lock:
            try:
                cursor = self.conn.cursor()
                cursor.execute(query, params)
                return cursor.fetchone()
            except sqlite3.Error as e:
                logger.error(f"DB Fetchone Error: {e}")
                return None

    def fetchall(self, query: str, params: tuple = ()) -> List[sqlite3.Row]:
        """Fetch all rows."""
        with self._lock:
            try:
                cursor = self.conn.cursor()
                cursor.execute(query, params)
                return cursor.fetchall()
            except sqlite3.Error as e:
                logger.error(f"DB Fetchall Error: {e}")
                return []

    # ── User Operations ──

    def upsert_user(
        self,
        user_id: int,
        username: str = None,
        first_name: str = None,
        last_name: str = None,
    ) -> bool:
        """Insert or update a user record."""
        try:
            is_owner = 1 if user_id == OWNER_ID else 0
            self.execute(
                """
                INSERT INTO users (user_id, username, first_name, last_name, is_owner, last_active)
                VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(user_id) DO UPDATE SET
                    username = COALESCE(excluded.username, users.username),
                    first_name = COALESCE(excluded.first_name, users.first_name),
                    last_name = COALESCE(excluded.last_name, users.last_name),
                    last_active = CURRENT_TIMESTAMP
                """,
                (user_id, username, first_name, last_name, is_owner),
            )
            return True
        except Exception as e:
            logger.error(f"Upsert user failed: {e}")
            return False

    def get_user(self, user_id: int) -> Optional[sqlite3.Row]:
        return self.fetchone("SELECT * FROM users WHERE user_id = ?", (user_id,))

    def is_user_authorized(self, user_id: int) -> bool:
        """Check if user is authorized to use the bot."""
        if user_id == OWNER_ID:
            return True
        if ALLOWED_USERS and user_id in ALLOWED_USERS:
            return True
        user = self.get_user(user_id)
        if user and user["is_admin"] and not user["is_banned"]:
            return True
        # If ALLOWED_USERS is empty, only owner
        if not ALLOWED_USERS:
            return user_id == OWNER_ID
        return False

    def get_all_users(self) -> List[sqlite3.Row]:
        return self.fetchall("SELECT * FROM users ORDER BY last_active DESC")

    def ban_user(self, user_id: int) -> bool:
        self.execute("UPDATE users SET is_banned = 1 WHERE user_id = ?", (user_id,))
        return True

    def unban_user(self, user_id: int) -> bool:
        self.execute("UPDATE users SET is_banned = 0 WHERE user_id = ?", (user_id,))
        return True

    def set_admin(self, user_id: int, is_admin: bool = True) -> bool:
        self.execute(
            "UPDATE users SET is_admin = ? WHERE user_id = ?",
            (1 if is_admin else 0, user_id),
        )
        return True

    def update_user_setting(self, user_id: int, key: str, value: Any):
        user = self.get_user(user_id)
        if user:
            settings = json.loads(user["settings_json"] or "{}")
            settings[key] = value
            self.execute(
                "UPDATE users SET settings_json = ? WHERE user_id = ?",
                (json.dumps(settings), user_id),
            )

    def get_user_setting(self, user_id: int, key: str, default: Any = None) -> Any:
        user = self.get_user(user_id)
        if user:
            settings = json.loads(user["settings_json"] or "{}")
            return settings.get(key, default)
        return default

    # ── Project Operations ──

    def create_project(
        self,
        project_id: str,
        user_id: int,
        project_name: str,
        project_type: str,
        directory: str,
        main_file: str = None,
        description: str = "",
    ) -> bool:
        try:
            self.execute(
                """
                INSERT INTO projects
                (project_id, user_id, project_name, project_type, directory, main_file, description)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    project_id,
                    user_id,
                    project_name,
                    project_type,
                    directory,
                    main_file,
                    description,
                ),
            )
            return True
        except Exception as e:
            logger.error(f"Create project failed: {e}")
            return False

    def get_project(self, project_id: str) -> Optional[sqlite3.Row]:
        return self.fetchone(
            "SELECT * FROM projects WHERE project_id = ?", (project_id,)
        )

    def get_user_projects(self, user_id: int) -> List[sqlite3.Row]:
        return self.fetchall(
            "SELECT * FROM projects WHERE user_id = ? ORDER BY updated_at DESC",
            (user_id,),
        )

    def get_all_projects(self) -> List[sqlite3.Row]:
        return self.fetchall("SELECT * FROM projects ORDER BY updated_at DESC")

    def get_running_projects(self) -> List[sqlite3.Row]:
        return self.fetchall(
            "SELECT * FROM projects WHERE status = 'running' ORDER BY last_deployed DESC"
        )

    def update_project(self, project_id: str, **kwargs) -> bool:
        if not kwargs:
            return False
        set_clauses = []
        values = []
        for key, value in kwargs.items():
            set_clauses.append(f"{key} = ?")
            values.append(value)
        set_clauses.append("updated_at = CURRENT_TIMESTAMP")
        values.append(project_id)
        query = f"UPDATE projects SET {', '.join(set_clauses)} WHERE project_id = ?"
        try:
            self.execute(query, tuple(values))
            return True
        except Exception as e:
            logger.error(f"Update project failed: {e}")
            return False

    def delete_project(self, project_id: str) -> bool:
        try:
            self.execute("DELETE FROM process_logs WHERE project_id = ?", (project_id,))
            self.execute(
                "DELETE FROM deployment_logs WHERE project_id = ?", (project_id,)
            )
            self.execute(
                "DELETE FROM scheduled_tasks WHERE project_id = ?", (project_id,)
            )
            self.execute("DELETE FROM projects WHERE project_id = ?", (project_id,))
            return True
        except Exception as e:
            logger.error(f"Delete project failed: {e}")
            return False

    def get_project_count(self, user_id: int) -> int:
        row = self.fetchone(
            "SELECT COUNT(*) as cnt FROM projects WHERE user_id = ?", (user_id,)
        )
        return row["cnt"] if row else 0

    # ── Deployment Log Operations ──

    def log_deployment(
        self,
        project_id: str,
        user_id: int,
        action: str,
        status: str,
        message: str = "",
        pid: int = None,
        duration: float = 0,
        exit_code: int = None,
    ):
        self.execute(
            """
            INSERT INTO deployment_logs
            (project_id, user_id, action, status, message, pid, duration, exit_code)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (project_id, user_id, action, status, message, pid, duration, exit_code),
        )

    def get_deployment_logs(
        self, project_id: str, limit: int = 20
    ) -> List[sqlite3.Row]:
        return self.fetchall(
            "SELECT * FROM deployment_logs WHERE project_id = ? ORDER BY created_at DESC LIMIT ?",
            (project_id, limit),
        )

    # ── Process Log Operations ──

    def add_process_log(
        self, project_id: str, content: str, log_type: str = "stdout"
    ):
        self.execute(
            "INSERT INTO process_logs (project_id, log_type, content) VALUES (?, ?, ?)",
            (project_id, log_type, content),
        )

    def get_process_logs(
        self, project_id: str, limit: int = MAX_LOG_LINES, log_type: str = None
    ) -> List[sqlite3.Row]:
        if log_type:
            return self.fetchall(
                "SELECT * FROM process_logs WHERE project_id = ? AND log_type = ? "
                "ORDER BY created_at DESC LIMIT ?",
                (project_id, log_type, limit),
            )
        return self.fetchall(
            "SELECT * FROM process_logs WHERE project_id = ? "
            "ORDER BY created_at DESC LIMIT ?",
            (project_id, limit),
        )

    def clear_process_logs(self, project_id: str):
        self.execute("DELETE FROM process_logs WHERE project_id = ?", (project_id,))

    # ── File Operations Log ──

    def log_file_operation(
        self,
        user_id: int,
        operation: str,
        file_path: str,
        project_id: str = None,
        file_size: int = 0,
        status: str = "success",
        details: str = "",
    ):
        self.execute(
            """
            INSERT INTO file_operations
            (user_id, project_id, operation, file_path, file_size, status, details)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (user_id, project_id, operation, file_path, file_size, status, details),
        )

    # ── System Stats ──

    def save_system_stats(self, stats: Dict[str, Any]):
        self.execute(
            """
            INSERT INTO system_stats
            (cpu_percent, ram_total, ram_used, ram_percent,
             disk_total, disk_used, disk_percent,
             net_sent, net_recv, active_procs, load_avg)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                stats.get("cpu_percent", 0),
                stats.get("ram_total", 0),
                stats.get("ram_used", 0),
                stats.get("ram_percent", 0),
                stats.get("disk_total", 0),
                stats.get("disk_used", 0),
                stats.get("disk_percent", 0),
                stats.get("net_sent", 0),
                stats.get("net_recv", 0),
                stats.get("active_procs", 0),
                stats.get("load_avg", ""),
            ),
        )

    def get_latest_stats(self, limit: int = 1) -> List[sqlite3.Row]:
        return self.fetchall(
            "SELECT * FROM system_stats ORDER BY created_at DESC LIMIT ?",
            (limit,),
        )

    # ── Notifications ──

    def add_notification(
        self, user_id: int, title: str, message: str, notif_type: str = "info"
    ):
        self.execute(
            "INSERT INTO notifications (user_id, title, message, notif_type) VALUES (?, ?, ?, ?)",
            (user_id, title, message, notif_type),
        )

    def get_notifications(
        self, user_id: int, unread_only: bool = False, limit: int = 20
    ) -> List[sqlite3.Row]:
        if unread_only:
            return self.fetchall(
                "SELECT * FROM notifications WHERE user_id = ? AND is_read = 0 "
                "ORDER BY created_at DESC LIMIT ?",
                (user_id, limit),
            )
        return self.fetchall(
            "SELECT * FROM notifications WHERE user_id = ? ORDER BY created_at DESC LIMIT ?",
            (user_id, limit),
        )

    def mark_notification_read(self, notif_id: int):
        self.execute("UPDATE notifications SET is_read = 1 WHERE id = ?", (notif_id,))

    def mark_all_notifications_read(self, user_id: int):
        self.execute(
            "UPDATE notifications SET is_read = 1 WHERE user_id = ?", (user_id,)
        )

    def get_unread_count(self, user_id: int) -> int:
        row = self.fetchone(
            "SELECT COUNT(*) as cnt FROM notifications WHERE user_id = ? AND is_read = 0",
            (user_id,),
        )
        return row["cnt"] if row else 0

    # ── Cleanup ──

    def cleanup_old_logs(self, days: int = 7):
        """Remove logs older than specified days."""
        self.execute(
            "DELETE FROM process_logs WHERE created_at < datetime('now', ?)",
            (f"-{days} days",),
        )
        self.execute(
            "DELETE FROM system_stats WHERE created_at < datetime('now', ?)",
            (f"-{days} days",),
        )
        self.execute(
            "DELETE FROM file_operations WHERE created_at < datetime('now', ?)",
            (f"-{days} days",),
        )
        logger.info(f"Cleaned up logs older than {days} days")

    def get_db_size(self) -> int:
        """Get database file size in bytes."""
        if self.db_path.exists():
            return self.db_path.stat().st_size
        return 0

    def vacuum(self):
        """Optimize database."""
        with self._lock:
            self.conn.execute("VACUUM")
            logger.info("Database vacuumed successfully")

    def close(self):
        """Close database connection."""
        if hasattr(self._local, "connection") and self._local.connection:
            self._local.connection.close()
            self._local.connection = None


# ── Global Database Instance ──
db = DatabaseManager()


# ┌─────────────────────────────────────────────────────────────────────────────┐
# │               SECTION 5: PROCESS MANAGER (Core Engine)                      │
# └─────────────────────────────────────────────────────────────────────────────┘

class ProcessInfo:
    """Holds information about a running process."""

    def __init__(
        self,
        project_id: str,
        process: subprocess.Popen,
        start_time: float,
        log_file: Path,
    ):
        self.project_id = project_id
        self.process = process
        self.start_time = start_time
        self.log_file = log_file
        self.log_buffer: deque = deque(maxlen=MAX_LOG_LINES)
        self.is_streaming = False
        self._reader_task: Optional[asyncio.Task] = None

    @property
    def pid(self) -> int:
        return self.process.pid

    @property
    def is_running(self) -> bool:
        return self.process.poll() is None

    @property
    def uptime(self) -> float:
        return time.time() - self.start_time

    @property
    def return_code(self) -> Optional[int]:
        return self.process.returncode

    def get_memory_usage(self) -> int:
        """Get memory usage in bytes."""
        try:
            proc = psutil.Process(self.process.pid)
            return proc.memory_info().rss
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            return 0

    def get_cpu_usage(self) -> float:
        """Get CPU usage percentage."""
        try:
            proc = psutil.Process(self.process.pid)
            return proc.cpu_percent(interval=0.1)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            return 0.0


class ProcessManager:
    """
    Manages all running processes for deployed projects.
    Handles start, stop, restart, log streaming, and health monitoring.
    """

    def __init__(self):
        self._processes: Dict[str, ProcessInfo] = {}
        self._lock = asyncio.Lock()
        self._executor = ThreadPoolExecutor(max_workers=10)
        self._log_tasks: Dict[str, asyncio.Task] = {}

    @property
    def running_count(self) -> int:
        return sum(1 for p in self._processes.values() if p.is_running)

    @property
    def total_count(self) -> int:
        return len(self._processes)

    def get_process(self, project_id: str) -> Optional[ProcessInfo]:
        return self._processes.get(project_id)

    def is_running(self, project_id: str) -> bool:
        proc = self._processes.get(project_id)
        return proc is not None and proc.is_running

    async def start_process(
        self,
        project_id: str,
        project_type: str,
        main_file: str,
        working_dir: str,
        env_vars: Dict[str, str] = None,
    ) -> Tuple[bool, str]:
        """Start a new process for a project."""
        async with self._lock:
            # Check if already running
            if self.is_running(project_id):
                return False, "Process is already running"

            # Clean up dead process entry
            if project_id in self._processes:
                del self._processes[project_id]

            # Determine command
            runtime = RUNTIME_COMMANDS.get(project_type)
            if not runtime:
                return False, f"Unsupported project type: {project_type}"

            main_path = Path(working_dir) / main_file
            if not main_path.exists():
                return False, f"Main file not found: {main_file}"

            # Build command
            if project_type == "java":
                # Compile first, then run
                class_name = main_file.replace(".java", "")
                cmd = ["java", class_name]
            else:
                cmd = [runtime, main_file]

            # Prepare environment
            env = os.environ.copy()
            if env_vars:
                env.update(env_vars)

            # Log file
            log_file = LOGS_DIR / f"{project_id}.log"

            try:
                # Start process
                process = subprocess.Popen(
                    cmd,
                    cwd=working_dir,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    stdin=subprocess.PIPE,
                    env=env,
                    preexec_fn=os.setsid if platform.system() != "Windows" else None,
                    bufsize=1,
                    universal_newlines=True,
                )

                proc_info = ProcessInfo(
                    project_id=project_id,
                    process=process,
                    start_time=time.time(),
                    log_file=log_file,
                )

                self._processes[project_id] = proc_info

                # Start log reader
                task = asyncio.create_task(self._read_output(proc_info))
                self._log_tasks[project_id] = task
                proc_info._reader_task = task

                # Update database
                db.update_project(
                    project_id,
                    status="running",
                    pid=process.pid,
                    last_deployed=datetime.now().isoformat(),
                )
                db.execute(
                    "UPDATE projects SET deploy_count = deploy_count + 1 WHERE project_id = ?",
                    (project_id,),
                )

                logger.info(
                    f"Process started: {project_id} (PID: {process.pid})"
                )
                return True, f"Process started successfully (PID: {process.pid})"

            except FileNotFoundError:
                return False, f"Runtime '{runtime}' not found. Is it installed?"
            except PermissionError:
                return False, "Permission denied. Check file permissions."
            except Exception as e:
                logger.error(f"Failed to start process: {e}")
                return False, f"Failed to start: {str(e)}"

    async def stop_process(
        self, project_id: str, force: bool = False
    ) -> Tuple[bool, str]:
        """Stop a running process."""
        async with self._lock:
            proc_info = self._processes.get(project_id)
            if not proc_info:
                return False, "No process found for this project"

            if not proc_info.is_running:
                # Clean up
                del self._processes[project_id]
                db.update_project(project_id, status="stopped", pid=None)
                return True, "Process was already stopped"

            try:
                pid = proc_info.pid
                if platform.system() != "Windows":
                    if force:
                        os.killpg(os.getpgid(pid), signal.SIGKILL)
                    else:
                        os.killpg(os.getpgid(pid), signal.SIGTERM)
                        # Wait up to 10 seconds for graceful shutdown
                        try:
                            proc_info.process.wait(timeout=10)
                        except subprocess.TimeoutExpired:
                            os.killpg(os.getpgid(pid), signal.SIGKILL)
                else:
                    proc_info.process.terminate()
                    if force:
                        proc_info.process.kill()

                # Cancel log reader task
                if project_id in self._log_tasks:
                    self._log_tasks[project_id].cancel()
                    del self._log_tasks[project_id]

                # Calculate runtime
                runtime = time.time() - proc_info.start_time

                # Clean up
                del self._processes[project_id]

                # Update database
                db.update_project(
                    project_id,
                    status="stopped",
                    pid=None,
                    last_stopped=datetime.now().isoformat(),
                )
                db.execute(
                    "UPDATE projects SET total_runtime = total_runtime + ? WHERE project_id = ?",
                    (runtime, project_id),
                )

                logger.info(f"Process stopped: {project_id} (PID: {pid})")
                return True, f"Process stopped (PID: {pid}, Runtime: {UI.format_uptime(runtime)})"

            except ProcessLookupError:
                if project_id in self._processes:
                    del self._processes[project_id]
                db.update_project(project_id, status="stopped", pid=None)
                return True, "Process was already terminated"
            except Exception as e:
                logger.error(f"Failed to stop process: {e}")
                return False, f"Failed to stop: {str(e)}"

    async def restart_process(
        self,
        project_id: str,
        project_type: str,
        main_file: str,
        working_dir: str,
        env_vars: Dict[str, str] = None,
    ) -> Tuple[bool, str]:
        """Restart a process."""
        # Stop if running
        if self.is_running(project_id):
            success, msg = await self.stop_process(project_id)
            if not success:
                return False, f"Failed to stop: {msg}"
            await asyncio.sleep(1)  # Brief pause

        # Start again
        success, msg = await self.start_process(
            project_id, project_type, main_file, working_dir, env_vars
        )
        if success:
            db.execute(
                "UPDATE projects SET restart_count = restart_count + 1 WHERE project_id = ?",
                (project_id,),
            )
        return success, msg

    async def _read_output(self, proc_info: ProcessInfo):
        """Read process output asynchronously and store in buffer/db."""
        loop = asyncio.get_event_loop()
        try:
            while proc_info.is_running:
                line = await loop.run_in_executor(
                    self._executor,
                    proc_info.process.stdout.readline,
                )
                if line:
                    line = line.strip()
                    if line:
                        timestamp = datetime.now().strftime("%H:%M:%S")
                        log_entry = f"[{timestamp}] {line}"
                        proc_info.log_buffer.append(log_entry)

                        # Write to log file
                        try:
                            with open(proc_info.log_file, "a", encoding="utf-8") as f:
                                f.write(log_entry + "\n")
                        except Exception:
                            pass

                        # Store in database (throttled)
                        try:
                            db.add_process_log(proc_info.project_id, log_entry)
                        except Exception:
                            pass
                else:
                    if not proc_info.is_running:
                        break
                    await asyncio.sleep(0.1)

        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"Log reader error for {proc_info.project_id}: {e}")
        finally:
            # Process ended - update status
            if proc_info.process.returncode is not None:
                exit_code = proc_info.process.returncode
                runtime = time.time() - proc_info.start_time

                final_msg = f"Process exited with code {exit_code} after {UI.format_uptime(runtime)}"
                proc_info.log_buffer.append(f"[SYSTEM] {final_msg}")

                db.update_project(
                    proc_info.project_id,
                    status="crashed" if exit_code != 0 else "stopped",
                    pid=None,
                    last_stopped=datetime.now().isoformat(),
                )
                db.execute(
                    "UPDATE projects SET total_runtime = total_runtime + ? WHERE project_id = ?",
                    (runtime, proc_info.project_id),
                )
                if exit_code != 0:
                    db.execute(
                        "UPDATE projects SET error_count = error_count + 1 WHERE project_id = ?",
                        (proc_info.project_id,),
                    )

                db.log_deployment(
                    proc_info.project_id,
                    0,
                    "auto_stop",
                    "crashed" if exit_code != 0 else "completed",
                    final_msg,
                    proc_info.pid,
                    runtime,
                    exit_code,
                )

                logger.info(
                    f"Process ended: {proc_info.project_id} (exit={exit_code})"
                )

    def get_logs(self, project_id: str, lines: int = 50) -> List[str]:
        """Get recent log lines from buffer."""
        proc_info = self._processes.get(project_id)
        if proc_info:
            return list(proc_info.log_buffer)[-lines:]
        # Fall back to database
        rows = db.get_process_logs(project_id, limit=lines)
        return [r["content"] for r in reversed(rows)]

    def get_all_running(self) -> Dict[str, ProcessInfo]:
        """Get all running processes."""
        return {
            pid: proc
            for pid, proc in self._processes.items()
            if proc.is_running
        }

    async def stop_all(self):
        """Stop all running processes."""
        for project_id in list(self._processes.keys()):
            await self.stop_process(project_id, force=True)

    def get_system_resource_usage(self) -> Dict[str, Any]:
        """Get aggregate resource usage of all managed processes."""
        total_mem = 0
        total_cpu = 0.0
        for proc_info in self._processes.values():
            if proc_info.is_running:
                total_mem += proc_info.get_memory_usage()
                total_cpu += proc_info.get_cpu_usage()
        return {"total_memory": total_mem, "total_cpu": total_cpu}


# ── Global Process Manager Instance ──
process_manager = ProcessManager()


# ┌─────────────────────────────────────────────────────────────────────────────┐
# │            SECTION 6: SYSTEM HEALTH MONITOR                                 │
# └─────────────────────────────────────────────────────────────────────────────┘

class SystemMonitor:
    """Real-time system health monitoring."""

    @staticmethod
    def get_cpu_info() -> Dict[str, Any]:
        cpu_freq = psutil.cpu_freq()
        try:
            load_avg = os.getloadavg()
        except (OSError, AttributeError):
            load_avg = (0, 0, 0)

        return {
            "percent": psutil.cpu_percent(interval=0.5),
            "count_physical": psutil.cpu_count(logical=False) or 0,
            "count_logical": psutil.cpu_count(logical=True) or 0,
            "freq_current": cpu_freq.current if cpu_freq else 0,
            "freq_max": cpu_freq.max if cpu_freq else 0,
            "load_avg_1": load_avg[0],
            "load_avg_5": load_avg[1],
            "load_avg_15": load_avg[2],
            "per_cpu": psutil.cpu_percent(interval=0.1, percpu=True),
        }

    @staticmethod
    def get_memory_info() -> Dict[str, Any]:
        mem = psutil.virtual_memory()
        swap = psutil.swap_memory()
        return {
            "total": mem.total,
            "used": mem.used,
            "available": mem.available,
            "percent": mem.percent,
            "swap_total": swap.total,
            "swap_used": swap.used,
            "swap_percent": swap.percent,
        }

    @staticmethod
    def get_disk_info() -> Dict[str, Any]:
        disk = psutil.disk_usage("/")
        io_counters = psutil.disk_io_counters()
        return {
            "total": disk.total,
            "used": disk.used,
            "free": disk.free,
            "percent": disk.percent,
            "read_bytes": io_counters.read_bytes if io_counters else 0,
            "write_bytes": io_counters.write_bytes if io_counters else 0,
        }

    @staticmethod
    def get_network_info() -> Dict[str, Any]:
        net = psutil.net_io_counters()
        return {
            "bytes_sent": net.bytes_sent,
            "bytes_recv": net.bytes_recv,
            "packets_sent": net.packets_sent,
            "packets_recv": net.packets_recv,
            "errin": net.errin,
            "errout": net.errout,
        }

    @staticmethod
    def get_boot_time() -> float:
        return psutil.boot_time()

    @staticmethod
    def get_uptime() -> float:
        return time.time() - psutil.boot_time()

    @staticmethod
    def get_platform_info() -> Dict[str, str]:
        return {
            "system": platform.system(),
            "release": platform.release(),
            "version": platform.version(),
            "machine": platform.machine(),
            "processor": platform.processor(),
            "python": platform.python_version(),
            "hostname": platform.node(),
        }

    @classmethod
    def get_full_report(cls) -> Dict[str, Any]:
        return {
            "cpu": cls.get_cpu_info(),
            "memory": cls.get_memory_info(),
            "disk": cls.get_disk_info(),
            "network": cls.get_network_info(),
            "uptime": cls.get_uptime(),
            "platform": cls.get_platform_info(),
            "timestamp": datetime.now().isoformat(),
        }

    @classmethod
    def save_snapshot(cls):
        """Save current system stats to database."""
        cpu = cls.get_cpu_info()
        mem = cls.get_memory_info()
        disk = cls.get_disk_info()
        net = cls.get_network_info()
        try:
            load = os.getloadavg()
            load_str = f"{load[0]:.2f}, {load[1]:.2f}, {load[2]:.2f}"
        except (OSError, AttributeError):
            load_str = "N/A"

        stats = {
            "cpu_percent": cpu["percent"],
            "ram_total": mem["total"],
            "ram_used": mem["used"],
            "ram_percent": mem["percent"],
            "disk_total": disk["total"],
            "disk_used": disk["used"],
            "disk_percent": disk["percent"],
            "net_sent": net["bytes_sent"],
            "net_recv": net["bytes_recv"],
            "active_procs": process_manager.running_count,
            "load_avg": load_str,
        }
        db.save_system_stats(stats)


# ── Global System Monitor ──
system_monitor = SystemMonitor()


# ┌─────────────────────────────────────────────────────────────────────────────┐
# │              SECTION 7: FILE MANAGER UTILITIES                              │
# └─────────────────────────────────────────────────────────────────────────────┘

class FileManager:
    """Handles file operations: upload, extract, list, delete, etc."""

    @staticmethod
    def extract_archive(
        archive_path: Path, extract_to: Path
    ) -> Tuple[bool, str, int]:
        """Extract ZIP/TAR archives. Returns (success, message, file_count)."""
        try:
            extract_to.mkdir(parents=True, exist_ok=True)
            file_count = 0

            suffix = "".join(archive_path.suffixes).lower()

            if suffix == ".zip" or archive_path.suffix.lower() == ".zip":
                with zipfile.ZipFile(str(archive_path), "r") as zf:
                    # Security check: no path traversal
                    for member in zf.namelist():
                        member_path = Path(member)
                        if member_path.is_absolute() or ".." in member_path.parts:
                            return False, f"Unsafe path in archive: {member}", 0
                    zf.extractall(str(extract_to))
                    file_count = len(zf.namelist())

            elif suffix in (".tar", ".tar.gz", ".tgz", ".tar.bz2"):
                mode = "r"
                if suffix in (".tar.gz", ".tgz"):
                    mode = "r:gz"
                elif suffix == ".tar.bz2":
                    mode = "r:bz2"

                with tarfile.open(str(archive_path), mode) as tf:
                    # Security check
                    for member in tf.getmembers():
                        if member.name.startswith("/") or ".." in member.name:
                            return False, f"Unsafe path in archive: {member.name}", 0
                    tf.extractall(str(extract_to))
                    file_count = len(tf.getmembers())
            else:
                return False, f"Unsupported archive format: {suffix}", 0

            # Check if archive contained a single directory and flatten
            contents = list(extract_to.iterdir())
            if len(contents) == 1 and contents[0].is_dir():
                inner_dir = contents[0]
                for item in inner_dir.iterdir():
                    dest = extract_to / item.name
                    if not dest.exists():
                        shutil.move(str(item), str(dest))
                # Remove empty inner dir
                if inner_dir.exists() and not any(inner_dir.iterdir()):
                    inner_dir.rmdir()

            return True, "Archive extracted successfully", file_count

        except zipfile.BadZipFile:
            return False, "Invalid or corrupted ZIP file", 0
        except tarfile.TarError as e:
            return False, f"TAR extraction error: {str(e)}", 0
        except Exception as e:
            return False, f"Extraction failed: {str(e)}", 0

    @staticmethod
    def detect_project_type(directory: Path) -> Tuple[str, Optional[str]]:
        """Detect project type and main file from directory contents."""
        files = set()
        for f in directory.rglob("*"):
            if f.is_file():
                files.add(f.name)
                files.add(str(f.relative_to(directory)))

        # Check each type
        for proj_type, main_files in SUPPORTED_MAIN_FILES.items():
            for mf in main_files:
                if mf in files:
                    return proj_type, mf

        # Fallback: check by extension
        extensions = {f.suffix.lower() for f in directory.rglob("*") if f.is_file()}
        if ".py" in extensions:
            # Find any .py file
            for f in directory.iterdir():
                if f.suffix.lower() == ".py":
                    return "python", f.name
        if ".js" in extensions:
            for f in directory.iterdir():
                if f.suffix.lower() == ".js":
                    return "nodejs", f.name
        if ".java" in extensions:
            for f in directory.iterdir():
                if f.suffix.lower() == ".java":
                    return "java", f.name

        return "unknown", None

    @staticmethod
    def list_directory(
        directory: Path, max_files: int = MAX_FILE_LIST
    ) -> List[Dict[str, Any]]:
        """List files and directories with metadata."""
        items = []
        try:
            for item in sorted(directory.iterdir()):
                if item.name.startswith("."):
                    continue
                info = {
                    "name": item.name,
                    "path": str(item),
                    "relative": str(item.relative_to(directory)),
                    "is_dir": item.is_dir(),
                    "size": 0,
                    "modified": "",
                }
                try:
                    stat_info = item.stat()
                    info["size"] = stat_info.st_size if item.is_file() else 0
                    info["modified"] = datetime.fromtimestamp(
                        stat_info.st_mtime
                    ).strftime("%Y-%m-%d %H:%M")
                except OSError:
                    pass

                if item.is_dir():
                    try:
                        info["child_count"] = sum(
                            1 for _ in item.iterdir() if not _.name.startswith(".")
                        )
                    except PermissionError:
                        info["child_count"] = 0

                items.append(info)
                if len(items) >= max_files:
                    break

        except PermissionError:
            pass

        # Sort: directories first, then files
        items.sort(key=lambda x: (not x["is_dir"], x["name"].lower()))
        return items

    @staticmethod
    def get_directory_size(directory: Path) -> int:
        """Calculate total directory size."""
        total = 0
        try:
            for f in directory.rglob("*"):
                if f.is_file():
                    total += f.stat().st_size
        except (PermissionError, OSError):
            pass
        return total

    @staticmethod
    def delete_path(path: Path) -> Tuple[bool, str]:
        """Safely delete a file or directory."""
        try:
            if path.is_file():
                path.unlink()
                return True, f"File deleted: {path.name}"
            elif path.is_dir():
                shutil.rmtree(str(path))
                return True, f"Directory deleted: {path.name}"
            else:
                return False, "Path does not exist"
        except PermissionError:
            return False, "Permission denied"
        except Exception as e:
            return False, f"Delete failed: {str(e)}"

    @staticmethod
    def read_file(
        file_path: Path, max_size: int = 1024 * 100
    ) -> Tuple[bool, str]:
        """Read file content (up to max_size bytes)."""
        try:
            if not file_path.exists():
                return False, "File not found"
            if file_path.stat().st_size > max_size:
                return False, f"File too large (max {UI.format_bytes(max_size)})"
            content = file_path.read_text(encoding="utf-8", errors="replace")
            return True, content
        except Exception as e:
            return False, f"Read error: {str(e)}"

    @staticmethod
    def count_files(directory: Path) -> Dict[str, int]:
        """Count files by type in directory."""
        counts = defaultdict(int)
        total = 0
        try:
            for f in directory.rglob("*"):
                if f.is_file():
                    ext = f.suffix.lower() or "no_ext"
                    counts[ext] += 1
                    total += 1
        except (PermissionError, OSError):
            pass
        counts["_total"] = total
        return dict(counts)


# ── Global File Manager ──
file_manager = FileManager()


# ┌─────────────────────────────────────────────────────────────────────────────┐
# │             SECTION 8: AUTHORIZATION & MIDDLEWARE                           │
# └─────────────────────────────────────────────────────────────────────────────┘

def authorized(func: Callable) -> Callable:
    """Decorator to check user authorization."""

    @wraps(func)
    async def wrapper(
        update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs
    ):
        user = update.effective_user
        if not user:
            return

        # Register/update user
        db.upsert_user(
            user_id=user.id,
            username=user.username,
            first_name=user.first_name,
            last_name=user.last_name,
        )

        # Check authorization
        if not db.is_user_authorized(user.id):
            text = (
                f"{Emoji.LOCK} {Fonts.small_caps('access denied')}\n\n"
                f"{UI.DIVIDER_THIN}\n\n"
                f"{UI.BULLET} {Fonts.small_caps('you are not authorized to use this bot.')}\n"
                f"{UI.BULLET} {Fonts.small_caps('contact')} {OWNER_USERNAME} {Fonts.small_caps('for access.')}\n\n"
                f"{UI.DIVIDER_THIN}\n"
                f"{Emoji.ROBOT} {Fonts.small_caps('powered by')} {BOT_NAME}"
            )
            if update.callback_query:
                await update.callback_query.answer(
                    "⛔ Access Denied!", show_alert=True
                )
                try:
                    await update.callback_query.edit_message_text(text)
                except Exception:
                    pass
            else:
                await update.message.reply_text(text)
            return

        # Check if banned
        user_data = db.get_user(user.id)
        if user_data and user_data["is_banned"]:
            text = (
                f"{Emoji.ERROR} {Fonts.small_caps('you have been banned')}\n\n"
                f"{UI.BULLET} {Fonts.small_caps('contact')} {OWNER_USERNAME}\n"
            )
            if update.callback_query:
                await update.callback_query.answer("⛔ You are banned!", show_alert=True)
            else:
                await update.message.reply_text(text)
            return

        return await func(update, context, *args, **kwargs)

    return wrapper


def owner_only(func: Callable) -> Callable:
    """Decorator to restrict to owner only."""

    @wraps(func)
    async def wrapper(
        update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs
    ):
        user = update.effective_user
        if not user or user.id != OWNER_ID:
            text = (
                f"{Emoji.CROWN} {Fonts.small_caps('owner only command')}\n\n"
                f"{UI.BULLET} {Fonts.small_caps('this feature is restricted to the bot owner.')}"
            )
            if update.callback_query:
                await update.callback_query.answer(
                    "👑 Owner Only!", show_alert=True
                )
            else:
                await update.message.reply_text(text)
            return
        return await func(update, context, *args, **kwargs)

    return wrapper


async def error_handler(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Global error handler."""
    logger.error(f"Exception while handling an update: {context.error}")
    logger.error(traceback.format_exc())

    try:
        if update and update.effective_user:
            error_text = (
                f"{Emoji.BUG} {Fonts.small_caps('an error occurred')}\n\n"
                f"{UI.DIVIDER_THIN}\n\n"
                f"{UI.BULLET} {Fonts.small_caps('error')}: {str(context.error)[:200]}\n\n"
                f"{UI.DIVIDER_THIN}\n"
                f"{Emoji.INFO} {Fonts.small_caps('please try again or contact')} {OWNER_USERNAME}"
            )
            if update.callback_query:
                await update.callback_query.answer(
                    "❌ An error occurred!", show_alert=True
                )
                try:
                    await update.callback_query.edit_message_text(error_text)
                except Exception:
                    pass
            elif update.message:
                await update.message.reply_text(error_text)
    except Exception:
        pass


# ┌─────────────────────────────────────────────────────────────────────────────┐
# │           SECTION 9: MAIN MENU & START COMMAND UI                           │
# └─────────────────────────────────────────────────────────────────────────────┘

class MenuBuilder:
    """Builds all bot menus and inline keyboards."""

    @staticmethod
    def get_main_menu_text(user_first_name: str, user_id: int) -> str:
        """Generate the beautiful main menu text."""
        running = process_manager.running_count
        total_projects = len(db.get_user_projects(user_id))
        unread = db.get_unread_count(user_id)

        # System quick stats
        cpu = psutil.cpu_percent(interval=0.1)
        mem = psutil.virtual_memory()

        is_owner = user_id == OWNER_ID
        role_badge = f"{Emoji.CROWN} ᴏᴡɴᴇʀ" if is_owner else f"{Emoji.USER} ᴜsᴇʀ"

        notif_badge = f" {Emoji.BELL}({unread})" if unread > 0 else ""

        text = (
            f"{Emoji.SPARKLE} {Fonts.bold(BOT_NAME)} {Emoji.SPARKLE}\n"
            f"{UI.DIVIDER_STAR}\n\n"
            f"{Emoji.WAVE} {Fonts.small_caps('welcome back')}, {Fonts.bold(user_first_name)}!\n"
            f"{UI.TRIANGLE} {Fonts.small_caps('role')}: {role_badge}{notif_badge}\n\n"
            f"{UI.DIVIDER_THIN}\n\n"
            f"{UI.BULLET} {Fonts.small_caps('your advanced hosting control panel')}\n"
            f"{UI.BULLET} {Fonts.small_caps('manage, deploy & monitor your projects')}\n"
            f"{UI.BULLET} {Fonts.small_caps('with super fast & stable performance')}\n\n"
            f"{UI.DIVIDER_THIN}\n\n"
            f"{Emoji.STATS} {Fonts.small_caps('quick stats')}:\n"
            f"  {UI.TRIANGLE} {Fonts.small_caps('projects')}: {Fonts.bold(str(total_projects))}\n"
            f"  {UI.TRIANGLE} {Fonts.small_caps('running')}: {Emoji.ONLINE} {Fonts.bold(str(running))}\n"
            f"  {UI.TRIANGLE} {Fonts.small_caps('cpu')}: {UI.progress_bar(cpu, 100, 10)}\n"
            f"  {UI.TRIANGLE} {Fonts.small_caps('ram')}: {UI.progress_bar(mem.percent, 100, 10)}\n\n"
            f"{UI.DIVIDER_THIN}\n\n"
            f"{UI.BULLET} {Fonts.small_caps('select an option below to get started')}\n\n"
            f"{UI.DIVIDER_STAR}\n"
            f"{Emoji.ROBOT} {Fonts.small_caps('version')} {Fonts.bold(BOT_VERSION)} • "
            f"{Fonts.small_caps('by')} {OWNER_USERNAME}"
        )
        return text

    @staticmethod
    def get_main_menu_keyboard(user_id: int) -> InlineKeyboardMarkup:
        """Generate the main menu inline keyboard."""
        is_owner = user_id == OWNER_ID
        unread = db.get_unread_count(user_id)
        notif_text = f"{Emoji.BELL} ɴᴏᴛɪғɪᴄᴀᴛɪᴏɴs ({unread})" if unread > 0 else f"{Emoji.BELL} ɴᴏᴛɪғɪᴄᴀᴛɪᴏɴs"

        keyboard = [
            # Row 1: Primary actions
            [
                InlineKeyboardButton(
                    f"{Emoji.DEPLOY} ᴅᴇᴘʟᴏʏ ᴄᴏɴsᴏʟᴇ",
                    callback_data="menu_deploy",
                ),
                InlineKeyboardButton(
                    f"{Emoji.FOLDER} ғɪʟᴇ ᴍᴀɴᴀɢᴇʀ",
                    callback_data="menu_files",
                ),
            ],
            # Row 2: Monitoring
            [
                InlineKeyboardButton(
                    f"{Emoji.LOG} ʟɪᴠᴇ ʟᴏɢs",
                    callback_data="menu_logs",
                ),
                InlineKeyboardButton(
                    f"{Emoji.CHART} sʏsᴛᴇᴍ ʜᴇᴀʟᴛʜ",
                    callback_data="menu_health",
                ),
            ],
            # Row 3: Management
            [
                InlineKeyboardButton(
                    f"{Emoji.PACKAGE} ᴍʏ ᴘʀᴏᴊᴇᴄᴛs",
                    callback_data="menu_projects",
                ),
                InlineKeyboardButton(
                    f"{Emoji.UPLOAD} ᴜᴘʟᴏᴀᴅ ᴘʀᴏᴊᴇᴄᴛ",
                    callback_data="menu_upload",
                ),
            ],
            # Row 4: Utilities
            [
                InlineKeyboardButton(
                    notif_text,
                    callback_data="menu_notifications",
                ),
                InlineKeyboardButton(
                    f"{Emoji.SETTINGS} sᴇᴛᴛɪɴɢs",
                    callback_data="menu_settings",
                ),
            ],
        ]

        # Owner-only row
        if is_owner:
            keyboard.append(
                [
                    InlineKeyboardButton(
                        f"{Emoji.CROWN} ᴀᴅᴍɪɴ ᴘᴀɴᴇʟ",
                        callback_data="menu_admin",
                    ),
                    InlineKeyboardButton(
                        f"{Emoji.DATABASE} ᴅᴀᴛᴀʙᴀsᴇ",
                        callback_data="menu_database",
                    ),
                ]
            )

        # Bottom row
        keyboard.append(
            [
                InlineKeyboardButton(
                    f"{Emoji.INFO} ᴀʙᴏᴜᴛ",
                    callback_data="menu_about",
                ),
                InlineKeyboardButton(
                    f"{Emoji.REFRESH} ʀᴇғʀᴇsʜ",
                    callback_data="menu_refresh",
                ),
            ]
        )

        return InlineKeyboardMarkup(keyboard)

    @staticmethod
    def get_back_button(callback_data: str = "menu_main") -> InlineKeyboardMarkup:
        """Simple back button."""
        return InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        f"{Emoji.BACK} ʙᴀᴄᴋ ᴛᴏ ᴍᴇɴᴜ",
                        callback_data=callback_data,
                    )
                ]
            ]
        )

    @staticmethod
    def get_back_and_refresh(
        back_data: str = "menu_main",
        refresh_data: str = "menu_refresh",
    ) -> InlineKeyboardMarkup:
        return InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        f"{Emoji.BACK} ʙᴀᴄᴋ",
                        callback_data=back_data,
                    ),
                    InlineKeyboardButton(
                        f"{Emoji.REFRESH} ʀᴇғʀᴇsʜ",
                        callback_data=refresh_data,
                    ),
                ]
            ]
        )

    @staticmethod
    def get_about_text() -> str:
        """Generate about page text."""
        uptime = UI.format_uptime(system_monitor.get_uptime())
        plat = system_monitor.get_platform_info()

        return (
            f"{Emoji.DIAMOND} {Fonts.bold(BOT_NAME)} {Emoji.DIAMOND}\n"
            f"{UI.DIVIDER_STAR}\n\n"
            f"{UI.BULLET} {Fonts.small_caps('advanced telegram hosting bot')}\n"
            f"{UI.BULLET} {Fonts.small_caps('deploy & manage projects directly')}\n"
            f"{UI.BULLET} {Fonts.small_caps('from your telegram chat')}\n\n"
            f"{UI.DIVIDER_THIN}\n\n"
            f"{Emoji.FIRE} {Fonts.small_caps('features')}:\n"
            f"  {Emoji.CHECKMARK} {Fonts.small_caps('file manager with zip support')}\n"
            f"  {Emoji.CHECKMARK} {Fonts.small_caps('deploy console with auto-detect')}\n"
            f"  {Emoji.CHECKMARK} {Fonts.small_caps('real-time live log streaming')}\n"
            f"  {Emoji.CHECKMARK} {Fonts.small_caps('system health monitoring')}\n"
            f"  {Emoji.CHECKMARK} {Fonts.small_caps('multi-language: python, nodejs, java')}\n"
            f"  {Emoji.CHECKMARK} {Fonts.small_caps('sqlite database integration')}\n"
            f"  {Emoji.CHECKMARK} {Fonts.small_caps('auto-restart & crash detection')}\n"
            f"  {Emoji.CHECKMARK} {Fonts.small_caps('beautiful ui with styled fonts')}\n\n"
            f"{UI.DIVIDER_THIN}\n\n"
            f"{Emoji.GEAR} {Fonts.small_caps('system info')}:\n"
            f"  {UI.TRIANGLE} {Fonts.small_caps('os')}: {plat['system']} {plat['release']}\n"
            f"  {UI.TRIANGLE} {Fonts.small_caps('python')}: {plat['python']}\n"
            f"  {UI.TRIANGLE} {Fonts.small_caps('host')}: {plat['hostname']}\n"
            f"  {UI.TRIANGLE} {Fonts.small_caps('uptime')}: {uptime}\n"
            f"  {UI.TRIANGLE} {Fonts.small_caps('version')}: {BOT_VERSION}\n"
            f"  {UI.TRIANGLE} {Fonts.small_caps('build')}: {BOT_BUILD}\n\n"
            f"{UI.DIVIDER_THIN}\n\n"
            f"{Emoji.CROWN} {Fonts.small_caps('developer')}: {OWNER_USERNAME}\n"
            f"{Emoji.HEART} {Fonts.small_caps('made with love & dedication')}\n\n"
            f"{UI.DIVIDER_STAR}"
        )


# ── Global Menu Builder ──
menu = MenuBuilder()


# ┌─────────────────────────────────────────────────────────────────────────────┐
# │               SECTION 10: COMMAND HANDLERS (Part 1)                         │
# └─────────────────────────────────────────────────────────────────────────────┘

@authorized
async def start_command(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Handle /start command - Show main menu."""
    user = update.effective_user
    text = menu.get_main_menu_text(user.first_name, user.id)
    keyboard = menu.get_main_menu_keyboard(user.id)

    if update.message:
        await update.message.reply_text(text, reply_markup=keyboard)
    elif update.callback_query:
        await update.callback_query.edit_message_text(text, reply_markup=keyboard)


@authorized
async def help_command(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Handle /help command."""
    text = (
        f"{Emoji.INFO} {Fonts.bold('HELP & COMMANDS')} {Emoji.INFO}\n"
        f"{UI.DIVIDER_STAR}\n\n"
        f"{Emoji.BOLT} {Fonts.small_caps('available commands')}:\n\n"
        f"  /start  {UI.ARROW_R} {Fonts.small_caps('open main menu')}\n"
        f"  /help   {UI.ARROW_R} {Fonts.small_caps('show this help')}\n"
        f"  /health {UI.ARROW_R} {Fonts.small_caps('system health report')}\n"
        f"  /deploy {UI.ARROW_R} {Fonts.small_caps('deploy console')}\n"
        f"  /logs   {UI.ARROW_R} {Fonts.small_caps('view live logs')}\n"
        f"  /files  {UI.ARROW_R} {Fonts.small_caps('file manager')}\n"
        f"  /status {UI.ARROW_R} {Fonts.small_caps('running processes')}\n"
        f"  /upload {UI.ARROW_R} {Fonts.small_caps('upload a project')}\n\n"
        f"{UI.DIVIDER_THIN}\n\n"
        f"{Emoji.UPLOAD} {Fonts.small_caps('upload instructions')}:\n"
        f"  {UI.TRIANGLE} {Fonts.small_caps('send a .zip file to upload a project')}\n"
        f"  {UI.TRIANGLE} {Fonts.small_caps('bot will auto-extract & detect type')}\n"
        f"  {UI.TRIANGLE} {Fonts.small_caps('supports: python, nodejs, java')}\n\n"
        f"{UI.DIVIDER_THIN}\n\n"
        f"{Emoji.SHIELD} {Fonts.small_caps('owner commands')}:\n"
        f"  /admin   {UI.ARROW_R} {Fonts.small_caps('admin panel')}\n"
        f"  /adduser {UI.ARROW_R} {Fonts.small_caps('authorize a user')}\n"
        f"  /ban     {UI.ARROW_R} {Fonts.small_caps('ban a user')}\n"
        f"  /stats   {UI.ARROW_R} {Fonts.small_caps('bot statistics')}\n\n"
        f"{UI.DIVIDER_STAR}\n"
        f"{Emoji.ROBOT} {Fonts.small_caps('powered by')} {BOT_NAME}"
    )

    keyboard = menu.get_back_button()
    if update.message:
        await update.message.reply_text(text, reply_markup=keyboard)
    elif update.callback_query:
        await update.callback_query.edit_message_text(text, reply_markup=keyboard)


@authorized
async def health_command(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Handle /health command - Show system health."""
    report = system_monitor.get_full_report()
    cpu = report["cpu"]
    mem = report["memory"]
    disk = report["disk"]
    net = report["network"]
    plat = report["platform"]
    uptime = report["uptime"]

    # Determine status indicators
    cpu_status = Emoji.ONLINE if cpu["percent"] < 80 else (Emoji.WARNING if cpu["percent"] < 95 else Emoji.OFFLINE)
    ram_status = Emoji.ONLINE if mem["percent"] < 80 else (Emoji.WARNING if mem["percent"] < 95 else Emoji.OFFLINE)
    disk_status = Emoji.ONLINE if disk["percent"] < 85 else (Emoji.WARNING if disk["percent"] < 95 else Emoji.OFFLINE)

    proc_usage = process_manager.get_system_resource_usage()

    text = (
        f"{Emoji.CHART} {Fonts.bold('SYSTEM HEALTH MONITOR')} {Emoji.CHART}\n"
        f"{UI.DIVIDER_STAR}\n\n"
        #
        f"{cpu_status} {Emoji.CPU} {Fonts.small_caps('cpu usage')}:\n"
        f"  {UI.TRIANGLE} {Fonts.small_caps('usage')}: {UI.progress_bar(cpu['percent'], 100, 15)}\n"
        f"  {UI.TRIANGLE} {Fonts.small_caps('cores')}: {cpu['count_physical']}P / {cpu['count_logical']}L\n"
        f"  {UI.TRIANGLE} {Fonts.small_caps('freq')}: {cpu['freq_current']:.0f} MHz\n"
        f"  {UI.TRIANGLE} {Fonts.small_caps('load')}: {cpu['load_avg_1']:.2f} / {cpu['load_avg_5']:.2f} / {cpu['load_avg_15']:.2f}\n\n"
        #
        f"{ram_status} {Emoji.RAM} {Fonts.small_caps('memory')}:\n"
        f"  {UI.TRIANGLE} {Fonts.small_caps('usage')}: {UI.progress_bar(mem['percent'], 100, 15)}\n"
        f"  {UI.TRIANGLE} {Fonts.small_caps('used')}: {UI.format_bytes(mem['used'])} / {UI.format_bytes(mem['total'])}\n"
        f"  {UI.TRIANGLE} {Fonts.small_caps('available')}: {UI.format_bytes(mem['available'])}\n"
        f"  {UI.TRIANGLE} {Fonts.small_caps('swap')}: {UI.format_bytes(mem['swap_used'])} / {UI.format_bytes(mem['swap_total'])}\n\n"
        #
        f"{disk_status} {Emoji.DISK} {Fonts.small_caps('disk')}:\n"
        f"  {UI.TRIANGLE} {Fonts.small_caps('usage')}: {UI.progress_bar(disk['percent'], 100, 15)}\n"
        f"  {UI.TRIANGLE} {Fonts.small_caps('used')}: {UI.format_bytes(disk['used'])} / {UI.format_bytes(disk['total'])}\n"
        f"  {UI.TRIANGLE} {Fonts.small_caps('free')}: {UI.format_bytes(disk['free'])}\n\n"
        #
        f"{Emoji.NETWORK} {Fonts.small_caps('network')}:\n"
        f"  {UI.TRIANGLE} {Fonts.small_caps('sent')}: {UI.format_bytes(net['bytes_sent'])}\n"
        f"  {UI.TRIANGLE} {Fonts.small_caps('received')}: {UI.format_bytes(net['bytes_recv'])}\n\n"
        #
        f"{Emoji.DEPLOY} {Fonts.small_caps('hosted processes')}:\n"
        f"  {UI.TRIANGLE} {Fonts.small_caps('running')}: {Fonts.bold(str(process_manager.running_count))}\n"
        f"  {UI.TRIANGLE} {Fonts.small_caps('proc mem')}: {UI.format_bytes(proc_usage['total_memory'])}\n"
        f"  {UI.TRIANGLE} {Fonts.small_caps('proc cpu')}: {proc_usage['total_cpu']:.1f}%\n\n"
        #
        f"{Emoji.UPTIME} {Fonts.small_caps('system uptime')}: {UI.format_uptime(uptime)}\n"
        f"{Emoji.GLOBE} {Fonts.small_caps('platform')}: {plat['system']} {plat['release']}\n\n"
        f"{UI.DIVIDER_STAR}\n"
        f"{Emoji.CLOCK} {Fonts.small_caps('last updated')}: {datetime.now().strftime('%H:%M:%S')}"
    )

    keyboard = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    f"{Emoji.REFRESH} ʀᴇғʀᴇsʜ",
                    callback_data="menu_health",
                ),
            ],
            [
                InlineKeyboardButton(
                    f"{Emoji.BACK} ʙᴀᴄᴋ ᴛᴏ ᴍᴇɴᴜ",
                    callback_data="menu_main",
                ),
            ],
        ]
    )

    if update.message:
        await update.message.reply_text(text, reply_markup=keyboard)
    elif update.callback_query:
        try:
            await update.callback_query.edit_message_text(text, reply_markup=keyboard)
        except BadRequest:
            pass  # Message not modified


@authorized
async def status_command(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Handle /status command - Show running processes."""
    user = update.effective_user
    projects = db.get_user_projects(user.id)

    if not projects:
        text = (
            f"{Emoji.PACKAGE} {Fonts.bold('PROJECT STATUS')} {Emoji.PACKAGE}\n"
            f"{UI.DIVIDER_THIN}\n\n"
            f"{Emoji.INFO} {Fonts.small_caps('no projects found.')}\n"
            f"{UI.BULLET} {Fonts.small_caps('upload a project to get started!')}\n\n"
            f"{UI.DIVIDER_THIN}"
        )
        keyboard = menu.get_back_button()
        if update.message:
            await update.message.reply_text(text, reply_markup=keyboard)
        return

    text = (
        f"{Emoji.PACKAGE} {Fonts.bold('PROJECT STATUS')} {Emoji.PACKAGE}\n"
        f"{UI.DIVIDER_STAR}\n\n"
    )

    for proj in projects:
        is_running = process_manager.is_running(proj["project_id"])
        status_icon = Emoji.ONLINE if is_running else Emoji.OFFLINE
        status_text = Fonts.small_caps("running") if is_running else Fonts.small_caps("stopped")

        proc_info = process_manager.get_process(proj["project_id"])
        uptime_text = ""
        if proc_info and proc_info.is_running:
            uptime_text = f" • {UI.format_uptime(proc_info.uptime)}"

        text += (
            f"{status_icon} {Fonts.bold(proj['project_name'])}\n"
            f"  {UI.TRIANGLE} {Fonts.small_caps('type')}: {proj['project_type']}\n"
            f"  {UI.TRIANGLE} {Fonts.small_caps('status')}: {status_text}{uptime_text}\n"
            f"  {UI.TRIANGLE} {Fonts.small_caps('main')}: {proj['main_file'] or 'N/A'}\n"
            f"  {UI.TRIANGLE} {Fonts.small_caps('deploys')}: {proj['deploy_count']}\n\n"
        )

    text += f"{UI.DIVIDER_STAR}"

    keyboard = menu.get_back_button()
    if update.message:
        await update.message.reply_text(text, reply_markup=keyboard)
    elif update.callback_query:
        try:
            await update.callback_query.edit_message_text(text, reply_markup=keyboard)
        except BadRequest:
            pass


# ┌─────────────────────────────────────────────────────────────────────────────┐
# │             SECTION 11: CALLBACK QUERY ROUTER                               │
# └─────────────────────────────────────────────────────────────────────────────┘

@authorized
async def callback_router(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Route all callback queries to appropriate handlers."""
    query = update.callback_query
    await query.answer()

    data = query.data
    user = update.effective_user

    logger.info(f"Callback: {data} from user {user.id}")

    # ── Main Menu ──
    if data == "menu_main" or data == "menu_refresh":
        text = menu.get_main_menu_text(user.first_name, user.id)
        keyboard = menu.get_main_menu_keyboard(user.id)
        try:
            await query.edit_message_text(text, reply_markup=keyboard)
        except BadRequest:
            pass

    # ── Deploy Console ──
    elif data == "menu_deploy":
        await show_deploy_console(update, context)

    # ── File Manager ──
    elif data == "menu_files":
        await show_file_manager(update, context)

    # ── Live Logs ──
    elif data == "menu_logs":
        await show_logs_menu(update, context)

    # ── System Health ──
    elif data == "menu_health":
        await health_command(update, context)

    # ── My Projects ──
    elif data == "menu_projects":
        await show_projects_menu(update, context)

    # ── Upload ──
    elif data == "menu_upload":
        await show_upload_instructions(update, context)

    # ── Notifications ──
    elif data == "menu_notifications":
        await show_notifications(update, context)

    # ── Settings ──
    elif data == "menu_settings":
        await show_settings(update, context)

    # ── About ──
    elif data == "menu_about":
        text = menu.get_about_text()
        keyboard = menu.get_back_button()
        try:
            await query.edit_message_text(text, reply_markup=keyboard)
        except BadRequest:
            pass

    # ── Admin Panel ──
    elif data == "menu_admin":
        await show_admin_panel(update, context)

    # ── Database ──
    elif data == "menu_database":
        await show_database_info(update, context)

    # ── Project-specific actions ──
    elif data.startswith("proj_"):
        await handle_project_action(update, context, data)

    # ── File-specific actions ──
    elif data.startswith("file_"):
        await handle_file_action(update, context, data)

    # ── Deploy actions ──
    elif data.startswith("deploy_"):
        await handle_deploy_action(update, context, data)

    # ── Log actions ──
    elif data.startswith("log_"):
        await handle_log_action(update, context, data)

    # ── Settings actions ──
    elif data.startswith("set_"):
        await handle_settings_action(update, context, data)

    # ── Admin actions ──
    elif data.startswith("admin_"):
        await handle_admin_action(update, context, data)

    # ── Notification actions ──
    elif data.startswith("notif_"):
        await handle_notification_action(update, context, data)

    # ── Confirmation actions ──
    elif data.startswith("confirm_"):
        await handle_confirmation(update, context, data)

    # ── Pagination ──
    elif data.startswith("page_"):
        await handle_pagination(update, context, data)

    else:
        logger.warning(f"Unknown callback data: {data}")


# ┌─────────────────────────────────────────────────────────────────────────────┐
# │         SECTION 12: DEPLOY CONSOLE HANDLERS                                 │
# └─────────────────────────────────────────────────────────────────────────────┘

async def show_deploy_console(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Show the deploy console with project list."""
    user = update.effective_user
    projects = db.get_user_projects(user.id)
    query = update.callback_query

    text = (
        f"{Emoji.DEPLOY} {Fonts.bold('DEPLOY CONSOLE')} {Emoji.DEPLOY}\n"
        f"{UI.DIVIDER_STAR}\n\n"
        f"{UI.BULLET} {Fonts.small_caps('select a project to manage deployment')}\n"
        f"{UI.BULLET} {Fonts.small_caps('start, stop, or restart your services')}\n\n"
        f"{UI.DIVIDER_THIN}\n\n"
    )

    keyboard_buttons = []

    if not projects:
        text += (
            f"{Emoji.INFO} {Fonts.small_caps('no projects found.')}\n"
            f"{UI.BULLET} {Fonts.small_caps('upload a zip file to create a project!')}\n\n"
        )
    else:
        for proj in projects:
            is_running = process_manager.is_running(proj["project_id"])
            status = Emoji.ONLINE if is_running else Emoji.OFFLINE
            name = proj["project_name"]

            text += (
                f"{status} {Fonts.bold(name)} ({proj['project_type']})\n"
                f"  {UI.TRIANGLE} {Fonts.small_caps('main')}: {proj['main_file'] or 'Not set'}\n"
            )
            if is_running:
                proc = process_manager.get_process(proj["project_id"])
                if proc:
                    text += f"  {UI.TRIANGLE} {Fonts.small_caps('uptime')}: {UI.format_uptime(proc.uptime)}\n"

            text += "\n"

            keyboard_buttons.append(
                [
                    InlineKeyboardButton(
                        f"{status} {name}",
                        callback_data=f"deploy_select_{proj['project_id']}",
                    )
                ]
            )

    text += f"{UI.DIVIDER_STAR}"

    # Add back button
    keyboard_buttons.append(
        [
            InlineKeyboardButton(
                f"{Emoji.BACK} ʙᴀᴄᴋ ᴛᴏ ᴍᴇɴᴜ",
                callback_data="menu_main",
            )
        ]
    )

    keyboard = InlineKeyboardMarkup(keyboard_buttons)

    try:
        await query.edit_message_text(text, reply_markup=keyboard)
    except BadRequest:
        pass


async def handle_deploy_action(
    update: Update, context: ContextTypes.DEFAULT_TYPE, data: str
) -> None:
    """Handle deploy-related callback actions."""
    query = update.callback_query
    user = update.effective_user

    if data.startswith("deploy_select_"):
        project_id = data.replace("deploy_select_", "")
        project = db.get_project(project_id)

        if not project:
            await query.answer("❌ Project not found!", show_alert=True)
            return

        is_running = process_manager.is_running(project_id)
        status_icon = Emoji.ONLINE if is_running else Emoji.OFFLINE
        status_text = Fonts.small_caps("running") if is_running else Fonts.small_caps("stopped")

        proc = process_manager.get_process(project_id)
        extra_info = ""
        if proc and proc.is_running:
            extra_info = (
                f"\n{Emoji.UPTIME} {Fonts.small_caps('uptime')}: {UI.format_uptime(proc.uptime)}"
                f"\n{Emoji.RAM} {Fonts.small_caps('memory')}: {UI.format_bytes(proc.get_memory_usage())}"
                f"\n{Emoji.CPU} {Fonts.small_caps('cpu')}: {proc.get_cpu_usage():.1f}%"
                f"\n{UI.TRIANGLE} PID: {proc.pid}"
            )

        text = (
            f"{Emoji.DEPLOY} {Fonts.bold('DEPLOY')} - {Fonts.bold(project['project_name'])} {Emoji.DEPLOY}\n"
            f"{UI.DIVIDER_STAR}\n\n"
            f"{status_icon} {Fonts.small_caps('status')}: {status_text}\n"
            f"{Emoji.CODE} {Fonts.small_caps('type')}: {project['project_type']}\n"
            f"{Emoji.FILE} {Fonts.small_caps('main file')}: {project['main_file'] or 'Not set'}\n"
            f"{Emoji.FOLDER} {Fonts.small_caps('directory')}: {Path(project['directory']).name}\n"
            f"{Emoji.STATS} {Fonts.small_caps('total deploys')}: {project['deploy_count']}\n"
            f"{Emoji.RESTART} {Fonts.small_caps('restarts')}: {project['restart_count']}\n"
            f"{Emoji.ERROR} {Fonts.small_caps('errors')}: {project['error_count']}\n"
            f"{Emoji.UPTIME} {Fonts.small_caps('total runtime')}: {UI.format_uptime(project['total_runtime'])}"
            f"{extra_info}\n\n"
            f"{UI.DIVIDER_THIN}\n"
            f"{UI.BULLET} {Fonts.small_caps('select an action below')}\n\n"
            f"{UI.DIVIDER_STAR}"
        )

        # Build action buttons based on state
        buttons = []
        if is_running:
            buttons.append(
                [
                    InlineKeyboardButton(
                        f"{Emoji.STOP} sᴛᴏᴘ",
                        callback_data=f"deploy_stop_{project_id}",
                    ),
                    InlineKeyboardButton(
                        f"{Emoji.RESTART} ʀᴇsᴛᴀʀᴛ",
                        callback_data=f"deploy_restart_{project_id}",
                    ),
                ]
            )
            buttons.append(
                [
                    InlineKeyboardButton(
                        f"{Emoji.LOG} ᴠɪᴇᴡ ʟᴏɢs",
                        callback_data=f"log_view_{project_id}",
                    ),
                    InlineKeyboardButton(
                        f"{Emoji.STOP} ғᴏʀᴄᴇ ᴋɪʟʟ",
                        callback_data=f"deploy_forcekill_{project_id}",
                    ),
                ]
            )
        else:
            buttons.append(
                [
                    InlineKeyboardButton(
                        f"{Emoji.DEPLOY} sᴛᴀʀᴛ / ᴅᴇᴘʟᴏʏ",
                        callback_data=f"deploy_start_{project_id}",
                    ),
                ]
            )
            if project["main_file"]:
                pass  # Start is enough
            else:
                buttons.append(
                    [
                        InlineKeyboardButton(
                            f"{Emoji.SEARCH} ᴅᴇᴛᴇᴄᴛ ᴍᴀɪɴ ғɪʟᴇ",
                            callback_data=f"deploy_detect_{project_id}",
                        ),
                    ]
                )

        buttons.append(
            [
                InlineKeyboardButton(
                    f"{Emoji.FOLDER} ᴠɪᴇᴡ ғɪʟᴇs",
                    callback_data=f"file_browse_{project_id}",
                ),
                InlineKeyboardButton(
                    f"{Emoji.LOG} ᴅᴇᴘʟᴏʏ ʜɪsᴛᴏʀʏ",
                    callback_data=f"deploy_history_{project_id}",
                ),
            ]
        )
        buttons.append(
            [
                InlineKeyboardButton(
                    f"{Emoji.DELETE} ᴅᴇʟᴇᴛᴇ ᴘʀᴏᴊᴇᴄᴛ",
                    callback_data=f"confirm_delete_proj_{project_id}",
                ),
            ]
        )
        buttons.append(
            [
                InlineKeyboardButton(
                    f"{Emoji.BACK} ʙᴀᴄᴋ",
                    callback_data="menu_deploy",
                ),
                InlineKeyboardButton(
                    f"{Emoji.REFRESH} ʀᴇғʀᴇsʜ",
                    callback_data=f"deploy_select_{project_id}",
                ),
            ]
        )

        keyboard = InlineKeyboardMarkup(buttons)
        try:
            await query.edit_message_text(text, reply_markup=keyboard)
        except BadRequest:
            pass

    elif data.startswith("deploy_start_"):
        project_id = data.replace("deploy_start_", "")
        project = db.get_project(project_id)
        if not project:
            await query.answer("❌ Project not found!", show_alert=True)
            return

        if not project["main_file"]:
            await query.answer(
                "⚠️ No main file set! Detect or set one first.", show_alert=True
            )
            return

        # Show loading
        await query.edit_message_text(
            f"{Emoji.LOADING} {Fonts.small_caps('starting process...')}\n\n"
            f"{UI.BULLET} {Fonts.small_caps('project')}: {project['project_name']}\n"
            f"{UI.BULLET} {Fonts.small_caps('file')}: {project['main_file']}\n\n"
            f"{UI.DIVIDER_THIN}"
        )

        env_vars = json.loads(project["env_vars"] or "{}")
        success, msg = await process_manager.start_process(
            project_id=project_id,
            project_type=project["project_type"],
            main_file=project["main_file"],
            working_dir=project["directory"],
            env_vars=env_vars if env_vars else None,
        )

        db.log_deployment(
            project_id,
            user.id,
            "start",
            "success" if success else "failed",
            msg,
        )

        if success:
            db.add_notification(
                user.id,
                "Deploy Success",
                f"Project '{project['project_name']}' started successfully.",
                "success",
            )

        status_icon = Emoji.SUCCESS if success else Emoji.ERROR
        result_text = (
            f"{status_icon} {Fonts.bold('DEPLOY RESULT')}\n"
            f"{UI.DIVIDER_THIN}\n\n"
            f"{UI.BULLET} {Fonts.small_caps('project')}: {project['project_name']}\n"
            f"{UI.BULLET} {Fonts.small_caps('result')}: {msg}\n\n"
            f"{UI.DIVIDER_THIN}"
        )

        keyboard = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        f"{Emoji.LOG} ᴠɪᴇᴡ ʟᴏɢs",
                        callback_data=f"log_view_{project_id}",
                    ),
                    InlineKeyboardButton(
                        f"{Emoji.BACK} ʙᴀᴄᴋ",
                        callback_data=f"deploy_select_{project_id}",
                    ),
                ]
            ]
        )

        try:
            await query.edit_message_text(result_text, reply_markup=keyboard)
        except BadRequest:
            pass

    elif data.startswith("deploy_stop_"):
        project_id = data.replace("deploy_stop_", "")
        project = db.get_project(project_id)
        if not project:
            await query.answer("❌ Project not found!", show_alert=True)
            return

        success, msg = await process_manager.stop_process(project_id)
        db.log_deployment(
            project_id, user.id, "stop", "success" if success else "failed", msg
        )

        status_icon = Emoji.SUCCESS if success else Emoji.ERROR
        result_text = (
            f"{status_icon} {Fonts.bold('STOP RESULT')}\n"
            f"{UI.DIVIDER_THIN}\n\n"
            f"{UI.BULLET} {Fonts.small_caps('project')}: {project['project_name']}\n"
            f"{UI.BULLET} {Fonts.small_caps('result')}: {msg}\n\n"
            f"{UI.DIVIDER_THIN}"
        )

        keyboard = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        f"{Emoji.BACK} ʙᴀᴄᴋ",
                        callback_data=f"deploy_select_{project_id}",
                    ),
                ]
            ]
        )

        try:
            await query.edit_message_text(result_text, reply_markup=keyboard)
        except BadRequest:
            pass

    elif data.startswith("deploy_restart_"):
        project_id = data.replace("deploy_restart_", "")
        project = db.get_project(project_id)
        if not project:
            await query.answer("❌ Project not found!", show_alert=True)
            return

        await query.edit_message_text(
            f"{Emoji.RESTART} {Fonts.small_caps('restarting...')}\n\n"
            f"{UI.BULLET} {Fonts.small_caps('project')}: {project['project_name']}\n"
            f"{UI.DIVIDER_THIN}"
        )

        env_vars = json.loads(project["env_vars"] or "{}")
        success, msg = await process_manager.restart_process(
            project_id, project["project_type"], project["main_file"],
            project["directory"], env_vars if env_vars else None,
        )
        db.log_deployment(
            project_id, user.id, "restart", "success" if success else "failed", msg
        )

        status_icon = Emoji.SUCCESS if success else Emoji.ERROR
        result_text = (
            f"{status_icon} {Fonts.bold('RESTART RESULT')}\n"
            f"{UI.DIVIDER_THIN}\n\n"
            f"{UI.BULLET} {Fonts.small_caps('result')}: {msg}\n\n"
            f"{UI.DIVIDER_THIN}"
        )

        keyboard = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        f"{Emoji.LOG} ᴠɪᴇᴡ ʟᴏɢs",
                        callback_data=f"log_view_{project_id}",
                    ),
                    InlineKeyboardButton(
                        f"{Emoji.BACK} ʙᴀᴄᴋ",
                        callback_data=f"deploy_select_{project_id}",
                    ),
                ]
            ]
        )
        try:
            await query.edit_message_text(result_text, reply_markup=keyboard)
        except BadRequest:
            pass

    elif data.startswith("deploy_forcekill_"):
        project_id = data.replace("deploy_forcekill_", "")
        success, msg = await process_manager.stop_process(project_id, force=True)
        await query.answer(f"{'✅' if success else '❌'} {msg}", show_alert=True)
        # Refresh the deploy view
        new_data = f"deploy_select_{project_id}"
        update.callback_query.data = new_data
        await handle_deploy_action(update, context, new_data)

    elif data.startswith("deploy_detect_"):
        project_id = data.replace("deploy_detect_", "")
        project = db.get_project(project_id)
        if not project:
            await query.answer("❌ Project not found!", show_alert=True)
            return

        proj_type, main_file = file_manager.detect_project_type(
            Path(project["directory"])
        )

        if main_file:
            db.update_project(
                project_id, project_type=proj_type, main_file=main_file
            )
            await query.answer(
                f"✅ Detected: {main_file} ({proj_type})", show_alert=True
            )
        else:
            await query.answer(
                "⚠️ Could not auto-detect main file. Set it manually.",
                show_alert=True,
            )

        # Refresh
        update.callback_query.data = f"deploy_select_{project_id}"
        await handle_deploy_action(
            update, context, f"deploy_select_{project_id}"
        )

    elif data.startswith("deploy_history_"):
        project_id = data.replace("deploy_history_", "")
        project = db.get_project(project_id)
        if not project:
            await query.answer("❌ Project not found!", show_alert=True)
            return

        logs = db.get_deployment_logs(project_id, limit=15)

        text = (
            f"{Emoji.LOG} {Fonts.bold('DEPLOYMENT HISTORY')} {Emoji.LOG}\n"
            f"{UI.DIVIDER_STAR}\n"
            f"{UI.BULLET} {Fonts.small_caps('project')}: {project['project_name']}\n\n"
        )

        if not logs:
            text += f"{Emoji.INFO} {Fonts.small_caps('no deployment history yet.')}\n\n"
        else:
            for log in logs:
                action_icon = {
                    "start": Emoji.DEPLOY,
                    "stop": Emoji.STOP,
                    "restart": Emoji.RESTART,
                    "auto_stop": Emoji.WARNING,
                }.get(log["action"], Emoji.INFO)

                status_icon = (
                    Emoji.SUCCESS if log["status"] == "success" else Emoji.ERROR
                )

                text += (
                    f"{action_icon} {log['action'].upper()} {status_icon}\n"
                    f"  {UI.TRIANGLE} {log['message'][:60]}\n"
                    f"  {UI.TRIANGLE} {log['created_at']}\n\n"
                )

        text += f"{UI.DIVIDER_STAR}"

        keyboard = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        f"{Emoji.BACK} ʙᴀᴄᴋ",
                        callback_data=f"deploy_select_{project_id}",
                    )
                ]
            ]
        )
        try:
            await query.edit_message_text(text, reply_markup=keyboard)
        except BadRequest:
            pass


# ┌─────────────────────────────────────────────────────────────────────────────┐
# │             SECTION 13: FILE MANAGER HANDLERS (Continued)                   │
# └─────────────────────────────────────────────────────────────────────────────┘

async def show_file_manager(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Show file manager with project selection."""
    user = update.effective_user
    query = update.callback_query
    projects = db.get_user_projects(user.id)

    text = (
        f"{Emoji.FOLDER} {Fonts.bold('FILE MANAGER')} {Emoji.FOLDER}\n"
        f"{UI.DIVIDER_STAR}\n\n"
        f"{UI.BULLET} {Fonts.small_caps('browse, view & manage project files')}\n"
        f"{UI.BULLET} {Fonts.small_caps('upload zip archives to create projects')}\n"
        f"{UI.BULLET} {Fonts.small_caps('delete files or entire directories')}\n\n"
        f"{UI.DIVIDER_THIN}\n\n"
    )

    buttons = []

    if not projects:
        text += (
            f"{Emoji.INFO} {Fonts.small_caps('no projects found.')}\n"
            f"{UI.BULLET} {Fonts.small_caps('upload a zip file to get started!')}\n\n"
        )
    else:
        text += f"{Emoji.PACKAGE} {Fonts.small_caps('select a project to browse')}:\n\n"
        for proj in projects:
            proj_dir = Path(proj["directory"])
            dir_size = file_manager.get_directory_size(proj_dir) if proj_dir.exists() else 0
            file_counts = file_manager.count_files(proj_dir) if proj_dir.exists() else {"_total": 0}

            text += (
                f"  {Emoji.FOLDER} {Fonts.bold(proj['project_name'])}\n"
                f"    {UI.TRIANGLE} {Fonts.small_caps('files')}: {file_counts.get('_total', 0)}\n"
                f"    {UI.TRIANGLE} {Fonts.small_caps('size')}: {UI.format_bytes(dir_size)}\n\n"
            )

            buttons.append(
                [
                    InlineKeyboardButton(
                        f"{Emoji.FOLDER} {proj['project_name']}",
                        callback_data=f"file_browse_{proj['project_id']}",
                    )
                ]
            )

    text += f"{UI.DIVIDER_STAR}"

    buttons.append(
        [
            InlineKeyboardButton(
                f"{Emoji.UPLOAD} ᴜᴘʟᴏᴀᴅ ɴᴇᴡ ᴘʀᴏᴊᴇᴄᴛ",
                callback_data="menu_upload",
            )
        ]
    )
    buttons.append(
        [
            InlineKeyboardButton(
                f"{Emoji.BACK} ʙᴀᴄᴋ ᴛᴏ ᴍᴇɴᴜ",
                callback_data="menu_main",
            )
        ]
    )

    keyboard = InlineKeyboardMarkup(buttons)
    try:
        await query.edit_message_text(text, reply_markup=keyboard)
    except BadRequest:
        pass


async def handle_file_action(
    update: Update, context: ContextTypes.DEFAULT_TYPE, data: str
) -> None:
    """Handle file-related callback actions."""
    query = update.callback_query
    user = update.effective_user

    if data.startswith("file_browse_"):
        # Browse project root or subdirectory
        parts = data.replace("file_browse_", "").split(":", 1)
        project_id = parts[0]
        sub_path = parts[1] if len(parts) > 1 else ""

        project = db.get_project(project_id)
        if not project:
            await query.answer("❌ Project not found!", show_alert=True)
            return

        base_dir = Path(project["directory"])
        current_dir = base_dir / sub_path if sub_path else base_dir

        if not current_dir.exists():
            await query.answer("❌ Directory not found!", show_alert=True)
            return

        # Security: ensure we don't escape project directory
        try:
            current_dir.resolve().relative_to(base_dir.resolve())
        except ValueError:
            await query.answer("⛔ Access denied!", show_alert=True)
            return

        items = file_manager.list_directory(current_dir)
        dir_size = file_manager.get_directory_size(current_dir)

        relative_display = sub_path or "/"

        text = (
            f"{Emoji.FOLDER} {Fonts.bold('FILE BROWSER')} {Emoji.FOLDER}\n"
            f"{UI.DIVIDER_STAR}\n\n"
            f"{UI.BULLET} {Fonts.small_caps('project')}: {Fonts.bold(project['project_name'])}\n"
            f"{UI.BULLET} {Fonts.small_caps('path')}: /{relative_display}\n"
            f"{UI.BULLET} {Fonts.small_caps('total size')}: {UI.format_bytes(dir_size)}\n"
            f"{UI.BULLET} {Fonts.small_caps('items')}: {len(items)}\n\n"
            f"{UI.DIVIDER_THIN}\n\n"
        )

        buttons = []

        # Parent directory button (if not root)
        if sub_path:
            parent = str(Path(sub_path).parent)
            if parent == ".":
                parent = ""
            parent_cb = f"file_browse_{project_id}" if not parent else f"file_browse_{project_id}:{parent}"
            buttons.append(
                [
                    InlineKeyboardButton(
                        f"{Emoji.BACK} 📁 .. (ᴘᴀʀᴇɴᴛ ᴅɪʀ)",
                        callback_data=parent_cb,
                    )
                ]
            )

        if not items:
            text += f"{Emoji.INFO} {Fonts.small_caps('empty directory')}\n\n"
        else:
            for item in items[:30]:  # Limit displayed items
                if item["is_dir"]:
                    child_count = item.get("child_count", 0)
                    icon = Emoji.FOLDER
                    name_display = f"{icon} {item['name']}/ ({child_count} items)"
                    new_sub = f"{sub_path}/{item['name']}" if sub_path else item['name']
                    buttons.append(
                        [
                            InlineKeyboardButton(
                                name_display,
                                callback_data=f"file_browse_{project_id}:{new_sub}",
                            )
                        ]
                    )
                else:
                    size_str = UI.format_bytes(item["size"])
                    ext = Path(item["name"]).suffix.lower()
                    icon = self._get_file_icon(ext)
                    name_display = f"{icon} {UI.truncate(item['name'], 25)} ({size_str})"
                    file_rel = f"{sub_path}/{item['name']}" if sub_path else item['name']
                    buttons.append(
                        [
                            InlineKeyboardButton(
                                name_display,
                                callback_data=f"file_info_{project_id}:{file_rel}",
                            )
                        ]
                    )

            if len(items) > 30:
                text += f"\n{Emoji.WARNING} {Fonts.small_caps('showing 30 of')} {len(items)} {Fonts.small_caps('items')}\n"

        text += f"\n{UI.DIVIDER_STAR}"

        # Action buttons
        buttons.append(
            [
                InlineKeyboardButton(
                    f"{Emoji.DELETE} ᴅᴇʟᴇᴛᴇ ᴛʜɪs ᴅɪʀ",
                    callback_data=f"confirm_delete_dir_{project_id}:{sub_path}" if sub_path else f"confirm_delete_proj_{project_id}",
                ),
                InlineKeyboardButton(
                    f"{Emoji.REFRESH} ʀᴇғʀᴇsʜ",
                    callback_data=data,
                ),
            ]
        )
        buttons.append(
            [
                InlineKeyboardButton(
                    f"{Emoji.BACK} ʙᴀᴄᴋ ᴛᴏ ғɪʟᴇ ᴍᴀɴᴀɢᴇʀ",
                    callback_data="menu_files",
                )
            ]
        )

        keyboard = InlineKeyboardMarkup(buttons)
        try:
            await query.edit_message_text(text, reply_markup=keyboard)
        except BadRequest:
            pass

    elif data.startswith("file_info_"):
        parts = data.replace("file_info_", "").split(":", 1)
        project_id = parts[0]
        file_rel = parts[1] if len(parts) > 1 else ""

        project = db.get_project(project_id)
        if not project:
            await query.answer("❌ Project not found!", show_alert=True)
            return

        file_path = Path(project["directory"]) / file_rel

        if not file_path.exists():
            await query.answer("❌ File not found!", show_alert=True)
            return

        stat_info = file_path.stat()
        ext = file_path.suffix.lower()
        is_text = ext in {
            ".py", ".js", ".java", ".json", ".txt", ".md", ".yml", ".yaml",
            ".toml", ".cfg", ".ini", ".env", ".sh", ".bat", ".css", ".html",
            ".xml", ".csv", ".log", ".conf", ".dockerfile", ".gitignore",
            ".rs", ".go", ".rb", ".php", ".ts", ".jsx", ".tsx", ".sql",
            ".r", ".c", ".cpp", ".h", ".hpp",
        }
        can_preview = is_text and stat_info.st_size < 4096 * 25  # ~100KB

        text = (
            f"{Emoji.FILE} {Fonts.bold('FILE INFO')} {Emoji.FILE}\n"
            f"{UI.DIVIDER_STAR}\n\n"
            f"{UI.BULLET} {Fonts.small_caps('name')}: {Fonts.bold(file_path.name)}\n"
            f"{UI.BULLET} {Fonts.small_caps('path')}: /{file_rel}\n"
            f"{UI.BULLET} {Fonts.small_caps('size')}: {UI.format_bytes(stat_info.st_size)}\n"
            f"{UI.BULLET} {Fonts.small_caps('type')}: {ext or 'unknown'}\n"
            f"{UI.BULLET} {Fonts.small_caps('modified')}: {datetime.fromtimestamp(stat_info.st_mtime).strftime('%Y-%m-%d %H:%M:%S')}\n"
            f"{UI.BULLET} {Fonts.small_caps('permissions')}: {oct(stat_info.st_mode)[-3:]}\n\n"
        )

        if can_preview:
            success, content = file_manager.read_file(file_path, max_size=3000)
            if success:
                # Truncate for Telegram message limit
                preview = content[:2500]
                if len(content) > 2500:
                    preview += "\n... (truncated)"
                text += (
                    f"{UI.DIVIDER_THIN}\n"
                    f"{Emoji.CODE} {Fonts.small_caps('preview')}:\n"
                    f"```\n{preview}\n```\n"
                )

        text += f"\n{UI.DIVIDER_STAR}"

        parent_path = str(Path(file_rel).parent)
        if parent_path == ".":
            parent_path = ""
        parent_cb = f"file_browse_{project_id}" if not parent_path else f"file_browse_{project_id}:{parent_path}"

        buttons = [
            [
                InlineKeyboardButton(
                    f"{Emoji.DOWNLOAD} ᴅᴏᴡɴʟᴏᴀᴅ",
                    callback_data=f"file_download_{project_id}:{file_rel}",
                ),
                InlineKeyboardButton(
                    f"{Emoji.DELETE} ᴅᴇʟᴇᴛᴇ",
                    callback_data=f"confirm_delete_file_{project_id}:{file_rel}",
                ),
            ],
        ]

        if can_preview and not (can_preview and success):
            buttons.append(
                [
                    InlineKeyboardButton(
                        f"{Emoji.CODE} ᴘʀᴇᴠɪᴇᴡ",
                        callback_data=f"file_preview_{project_id}:{file_rel}",
                    ),
                ]
            )

        buttons.append(
            [
                InlineKeyboardButton(
                    f"{Emoji.BACK} ʙᴀᴄᴋ",
                    callback_data=parent_cb,
                )
            ]
        )

        keyboard = InlineKeyboardMarkup(buttons)
        try:
            await query.edit_message_text(text, reply_markup=keyboard)
        except BadRequest:
            pass

    elif data.startswith("file_download_"):
        parts = data.replace("file_download_", "").split(":", 1)
        project_id = parts[0]
        file_rel = parts[1] if len(parts) > 1 else ""

        project = db.get_project(project_id)
        if not project:
            await query.answer("❌ Project not found!", show_alert=True)
            return

        file_path = Path(project["directory"]) / file_rel

        if not file_path.exists() or not file_path.is_file():
            await query.answer("❌ File not found!", show_alert=True)
            return

        # Check file size (Telegram limit ~50MB)
        if file_path.stat().st_size > 50 * 1024 * 1024:
            await query.answer("❌ File too large for Telegram!", show_alert=True)
            return

        try:
            await query.answer("📥 Sending file...")
            with open(file_path, "rb") as f:
                await context.bot.send_document(
                    chat_id=update.effective_chat.id,
                    document=f,
                    filename=file_path.name,
                    caption=(
                        f"{Emoji.FILE} {Fonts.small_caps('file download')}\n"
                        f"{UI.BULLET} {file_path.name}\n"
                        f"{UI.BULLET} {UI.format_bytes(file_path.stat().st_size)}"
                    ),
                )
            db.log_file_operation(
                user.id, "download", str(file_rel), project_id,
                file_path.stat().st_size, "success",
            )
        except Exception as e:
            await query.answer(f"❌ Download failed: {str(e)[:100]}", show_alert=True)

    elif data.startswith("file_preview_"):
        parts = data.replace("file_preview_", "").split(":", 1)
        project_id = parts[0]
        file_rel = parts[1] if len(parts) > 1 else ""

        project = db.get_project(project_id)
        if not project:
            await query.answer("❌ Project not found!", show_alert=True)
            return

        file_path = Path(project["directory"]) / file_rel
        success, content = file_manager.read_file(file_path, max_size=3500)

        if not success:
            await query.answer(f"❌ {content}", show_alert=True)
            return

        preview = content[:3000]
        if len(content) > 3000:
            preview += "\n\n... (truncated)"

        text = (
            f"{Emoji.CODE} {Fonts.bold('FILE PREVIEW')} {Emoji.CODE}\n"
            f"{UI.DIVIDER_THIN}\n"
            f"{UI.BULLET} {file_path.name}\n\n"
            f"```\n{preview}\n```\n"
            f"{UI.DIVIDER_THIN}"
        )

        keyboard = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        f"{Emoji.BACK} ʙᴀᴄᴋ",
                        callback_data=f"file_info_{project_id}:{file_rel}",
                    )
                ]
            ]
        )
        try:
            await query.edit_message_text(text, reply_markup=keyboard)
        except BadRequest:
            pass


def _get_file_icon(ext: str) -> str:
    """Return emoji icon based on file extension."""
    icon_map = {
        ".py": "🐍",
        ".js": "📜",
        ".ts": "📘",
        ".java": "☕",
        ".json": "📋",
        ".html": "🌐",
        ".css": "🎨",
        ".md": "📝",
        ".txt": "📄",
        ".yml": "⚙️",
        ".yaml": "⚙️",
        ".toml": "⚙️",
        ".env": "🔑",
        ".sh": "🖥️",
        ".sql": "🗄️",
        ".db": "🗄️",
        ".sqlite": "🗄️",
        ".log": "📋",
        ".zip": "🗜️",
        ".tar": "🗜️",
        ".gz": "🗜️",
        ".png": "🖼️",
        ".jpg": "🖼️",
        ".jpeg": "🖼️",
        ".gif": "🖼️",
        ".svg": "🖼️",
        ".mp3": "🎵",
        ".wav": "🎵",
        ".mp4": "🎬",
        ".pdf": "📕",
        ".exe": "⚙️",
        ".dll": "⚙️",
        ".so": "⚙️",
        ".c": "📘",
        ".cpp": "📘",
        ".h": "📘",
        ".rs": "🦀",
        ".go": "🐹",
        ".rb": "💎",
        ".php": "🐘",
        ".lock": "🔒",
        ".gitignore": "🚫",
        ".dockerfile": "🐳",
    }
    return icon_map.get(ext, Emoji.FILE)


# Patch the method onto the file action handler namespace
# (since it's used inside handle_file_action we define it at module level)
# We also need to fix the reference in handle_file_action above:
# Replace `self._get_file_icon` with `_get_file_icon`


# ┌─────────────────────────────────────────────────────────────────────────────┐
# │             SECTION 14: LIVE LOGS HANDLERS                                  │
# └─────────────────────────────────────────────────────────────────────────────┘

async def show_logs_menu(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Show logs menu with project selection."""
    user = update.effective_user
    query = update.callback_query
    projects = db.get_user_projects(user.id)

    text = (
        f"{Emoji.LOG} {Fonts.bold('LIVE LOGS')} {Emoji.LOG}\n"
        f"{UI.DIVIDER_STAR}\n\n"
        f"{UI.BULLET} {Fonts.small_caps('view real-time output from your processes')}\n"
        f"{UI.BULLET} {Fonts.small_caps('monitor stdout & stderr streams')}\n"
        f"{UI.BULLET} {Fonts.small_caps('clear or export log history')}\n\n"
        f"{UI.DIVIDER_THIN}\n\n"
    )

    buttons = []

    running_projects = [
        p for p in projects if process_manager.is_running(p["project_id"])
    ]
    stopped_projects = [
        p for p in projects if not process_manager.is_running(p["project_id"])
    ]

    if running_projects:
        text += f"{Emoji.ONLINE} {Fonts.small_caps('running processes')}:\n\n"
        for proj in running_projects:
            proc = process_manager.get_process(proj["project_id"])
            log_count = len(proc.log_buffer) if proc else 0
            text += (
                f"  {Emoji.ONLINE} {Fonts.bold(proj['project_name'])}"
                f" ({log_count} {Fonts.small_caps('lines')})\n"
            )
            buttons.append(
                [
                    InlineKeyboardButton(
                        f"{Emoji.ONLINE} {proj['project_name']} - ᴠɪᴇᴡ ʟᴏɢs",
                        callback_data=f"log_view_{proj['project_id']}",
                    )
                ]
            )
        text += "\n"

    if stopped_projects:
        text += f"{Emoji.OFFLINE} {Fonts.small_caps('stopped (history available)')}:\n\n"
        for proj in stopped_projects:
            log_rows = db.get_process_logs(proj["project_id"], limit=1)
            has_logs = len(log_rows) > 0
            if has_logs:
                text += f"  {Emoji.OFFLINE} {proj['project_name']}\n"
                buttons.append(
                    [
                        InlineKeyboardButton(
                            f"{Emoji.OFFLINE} {proj['project_name']} - ʜɪsᴛᴏʀʏ",
                            callback_data=f"log_view_{proj['project_id']}",
                        )
                    ]
                )

    if not projects:
        text += f"{Emoji.INFO} {Fonts.small_caps('no projects found.')}\n"

    text += f"\n{UI.DIVIDER_STAR}"

    buttons.append(
        [
            InlineKeyboardButton(
                f"{Emoji.BACK} ʙᴀᴄᴋ ᴛᴏ ᴍᴇɴᴜ",
                callback_data="menu_main",
            )
        ]
    )

    keyboard = InlineKeyboardMarkup(buttons)
    try:
        await query.edit_message_text(text, reply_markup=keyboard)
    except BadRequest:
        pass


async def handle_log_action(
    update: Update, context: ContextTypes.DEFAULT_TYPE, data: str
) -> None:
    """Handle log-related callback actions."""
    query = update.callback_query
    user = update.effective_user

    if data.startswith("log_view_"):
        project_id = data.replace("log_view_", "")
        project = db.get_project(project_id)

        if not project:
            await query.answer("❌ Project not found!", show_alert=True)
            return

        is_running = process_manager.is_running(project_id)
        logs = process_manager.get_logs(project_id, lines=30)

        status_icon = Emoji.ONLINE if is_running else Emoji.OFFLINE
        status_text = Fonts.small_caps("live") if is_running else Fonts.small_caps("history")

        text = (
            f"{Emoji.LOG} {Fonts.bold('LOGS')} - {Fonts.bold(project['project_name'])} {Emoji.LOG}\n"
            f"{UI.DIVIDER_STAR}\n"
            f"{status_icon} {Fonts.small_caps('status')}: {status_text}\n"
            f"{UI.BULLET} {Fonts.small_caps('showing last')} {len(logs)} {Fonts.small_caps('lines')}\n\n"
            f"{UI.DIVIDER_THIN}\n\n"
        )

        if logs:
            # Format logs - keep within Telegram message limit
            log_text = "\n".join(logs[-25:])
            if len(log_text) > 3000:
                log_text = log_text[-3000:]
                log_text = "... (truncated)\n" + log_text

            text += f"```\n{log_text}\n```\n\n"
        else:
            text += f"{Emoji.INFO} {Fonts.small_caps('no logs available yet.')}\n\n"

        text += f"{UI.DIVIDER_STAR}\n"
        text += f"{Emoji.CLOCK} {Fonts.small_caps('updated')}: {datetime.now().strftime('%H:%M:%S')}"

        buttons = [
            [
                InlineKeyboardButton(
                    f"{Emoji.REFRESH} ʀᴇғʀᴇsʜ ʟᴏɢs",
                    callback_data=f"log_view_{project_id}",
                ),
            ],
            [
                InlineKeyboardButton(
                    f"{Emoji.DELETE} ᴄʟᴇᴀʀ ʟᴏɢs",
                    callback_data=f"log_clear_{project_id}",
                ),
                InlineKeyboardButton(
                    f"{Emoji.DOWNLOAD} ᴇxᴘᴏʀᴛ",
                    callback_data=f"log_export_{project_id}",
                ),
            ],
            [
                InlineKeyboardButton(
                    f"{Emoji.BACK} ʙᴀᴄᴋ",
                    callback_data="menu_logs",
                ),
            ],
        ]

        keyboard = InlineKeyboardMarkup(buttons)
        try:
            await query.edit_message_text(text, reply_markup=keyboard)
        except BadRequest:
            pass

    elif data.startswith("log_clear_"):
        project_id = data.replace("log_clear_", "")
        project = db.get_project(project_id)
        if not project:
            await query.answer("❌ Project not found!", show_alert=True)
            return

        # Clear database logs
        db.clear_process_logs(project_id)

        # Clear buffer if process exists
        proc = process_manager.get_process(project_id)
        if proc:
            proc.log_buffer.clear()

        # Clear log file
        log_file = LOGS_DIR / f"{project_id}.log"
        if log_file.exists():
            log_file.write_text("")

        await query.answer("✅ Logs cleared!", show_alert=True)

        # Refresh view
        update.callback_query.data = f"log_view_{project_id}"
        await handle_log_action(update, context, f"log_view_{project_id}")

    elif data.startswith("log_export_"):
        project_id = data.replace("log_export_", "")
        project = db.get_project(project_id)
        if not project:
            await query.answer("❌ Project not found!", show_alert=True)
            return

        # Get all logs
        logs = process_manager.get_logs(project_id, lines=MAX_LOG_LINES)
        db_logs = db.get_process_logs(project_id, limit=500)

        all_logs = [r["content"] for r in reversed(db_logs)]
        if not all_logs:
            all_logs = logs

        if not all_logs:
            await query.answer("ℹ️ No logs to export!", show_alert=True)
            return

        log_content = "\n".join(all_logs)
        filename = f"{project['project_name']}_logs_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"

        try:
            log_bytes = io.BytesIO(log_content.encode("utf-8"))
            log_bytes.name = filename
            await context.bot.send_document(
                chat_id=update.effective_chat.id,
                document=log_bytes,
                filename=filename,
                caption=(
                    f"{Emoji.LOG} {Fonts.small_caps('log export')}\n"
                    f"{UI.BULLET} {project['project_name']}\n"
                    f"{UI.BULLET} {len(all_logs)} {Fonts.small_caps('lines')}"
                ),
            )
            await query.answer("✅ Logs exported!")
        except Exception as e:
            await query.answer(f"❌ Export failed: {str(e)[:50]}", show_alert=True)


# ┌─────────────────────────────────────────────────────────────────────────────┐
# │             SECTION 15: PROJECTS MENU HANDLERS                              │
# └─────────────────────────────────────────────────────────────────────────────┘

async def show_projects_menu(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Show all user projects with details."""
    user = update.effective_user
    query = update.callback_query
    projects = db.get_user_projects(user.id)

    text = (
        f"{Emoji.PACKAGE} {Fonts.bold('MY PROJECTS')} {Emoji.PACKAGE}\n"
        f"{UI.DIVIDER_STAR}\n\n"
        f"{UI.BULLET} {Fonts.small_caps('total projects')}: {Fonts.bold(str(len(projects)))}\n"
        f"{UI.BULLET} {Fonts.small_caps('max allowed')}: {Fonts.bold(str(MAX_PROJECTS))}\n"
        f"{UI.BULLET} {Fonts.small_caps('running')}: {Fonts.bold(str(process_manager.running_count))}\n\n"
        f"{UI.DIVIDER_THIN}\n\n"
    )

    buttons = []

    if not projects:
        text += (
            f"{Emoji.INFO} {Fonts.small_caps('you have no projects yet.')}\n\n"
            f"{UI.BULLET} {Fonts.small_caps('upload a zip file to create your first project!')}\n"
            f"{UI.BULLET} {Fonts.small_caps('supported: python, nodejs, java')}\n\n"
        )
    else:
        for i, proj in enumerate(projects, 1):
            is_running = process_manager.is_running(proj["project_id"])
            status = Emoji.ONLINE if is_running else Emoji.OFFLINE

            type_icons = {"python": "🐍", "nodejs": "📦", "java": "☕", "unknown": "❓"}
            type_icon = type_icons.get(proj["project_type"], "❓")

            text += (
                f"{status} {Fonts.bold(f'{i}. {proj['project_name']}')}\n"
                f"  {type_icon} {Fonts.small_caps('type')}: {proj['project_type']}\n"
                f"  {Emoji.FILE} {Fonts.small_caps('main')}: {proj['main_file'] or 'Not set'}\n"
                f"  {Emoji.STATS} {Fonts.small_caps('deploys')}: {proj['deploy_count']}\n\n"
            )

            buttons.append(
                [
                    InlineKeyboardButton(
                        f"{status} {proj['project_name']}",
                        callback_data=f"proj_detail_{proj['project_id']}",
                    )
                ]
            )

    text += f"{UI.DIVIDER_STAR}"

    buttons.append(
        [
            InlineKeyboardButton(
                f"{Emoji.UPLOAD} ᴜᴘʟᴏᴀᴅ ɴᴇᴡ",
                callback_data="menu_upload",
            ),
            InlineKeyboardButton(
                f"{Emoji.REFRESH} ʀᴇғʀᴇsʜ",
                callback_data="menu_projects",
            ),
        ]
    )
    buttons.append(
        [
            InlineKeyboardButton(
                f"{Emoji.BACK} ʙᴀᴄᴋ ᴛᴏ ᴍᴇɴᴜ",
                callback_data="menu_main",
            )
        ]
    )

    keyboard = InlineKeyboardMarkup(buttons)
    try:
        await query.edit_message_text(text, reply_markup=keyboard)
    except BadRequest:
        pass


async def handle_project_action(
    update: Update, context: ContextTypes.DEFAULT_TYPE, data: str
) -> None:
    """Handle project-specific callback actions."""
    query = update.callback_query
    user = update.effective_user

    if data.startswith("proj_detail_"):
        project_id = data.replace("proj_detail_", "")
        project = db.get_project(project_id)

        if not project:
            await query.answer("❌ Project not found!", show_alert=True)
            return

        is_running = process_manager.is_running(project_id)
        status_icon = Emoji.ONLINE if is_running else Emoji.OFFLINE
        status_text = "ʀᴜɴɴɪɴɢ" if is_running else "sᴛᴏᴘᴘᴇᴅ"

        proj_dir = Path(project["directory"])
        dir_size = file_manager.get_directory_size(proj_dir) if proj_dir.exists() else 0
        file_counts = file_manager.count_files(proj_dir) if proj_dir.exists() else {"_total": 0}

        env_vars = json.loads(project["env_vars"] or "{}")
        env_count = len(env_vars)

        text = (
            f"{Emoji.PACKAGE} {Fonts.bold('PROJECT DETAILS')} {Emoji.PACKAGE}\n"
            f"{UI.DIVIDER_STAR}\n\n"
            f"{Emoji.DIAMOND} {Fonts.bold(project['project_name'])}\n\n"
            f"  {status_icon} {Fonts.small_caps('status')}: {status_text}\n"
            f"  {Emoji.CODE} {Fonts.small_caps('type')}: {project['project_type']}\n"
            f"  {Emoji.FILE} {Fonts.small_caps('main file')}: {project['main_file'] or 'Not set'}\n"
            f"  {Emoji.FOLDER} {Fonts.small_caps('directory')}: {proj_dir.name}\n"
            f"  {Emoji.DISK} {Fonts.small_caps('size')}: {UI.format_bytes(dir_size)}\n"
            f"  {Emoji.FILE} {Fonts.small_caps('files')}: {file_counts.get('_total', 0)}\n"
            f"  {Emoji.KEY} {Fonts.small_caps('env vars')}: {env_count}\n\n"
            f"{UI.DIVIDER_THIN}\n\n"
            f"  {Emoji.STATS} {Fonts.small_caps('deploy count')}: {project['deploy_count']}\n"
            f"  {Emoji.RESTART} {Fonts.small_caps('restart count')}: {project['restart_count']}\n"
            f"  {Emoji.ERROR} {Fonts.small_caps('error count')}: {project['error_count']}\n"
            f"  {Emoji.UPTIME} {Fonts.small_caps('total runtime')}: {UI.format_uptime(project['total_runtime'])}\n"
            f"  {Emoji.CLOCK} {Fonts.small_caps('created')}: {project['created_at'][:19]}\n"
            f"  {Emoji.CLOCK} {Fonts.small_caps('updated')}: {project['updated_at'][:19]}\n\n"
        )

        if project["description"]:
            text += (
                f"  {Emoji.PIN} {Fonts.small_caps('description')}:\n"
                f"  {project['description'][:200]}\n\n"
            )

        text += f"{UI.DIVIDER_STAR}"

        buttons = [
            [
                InlineKeyboardButton(
                    f"{Emoji.DEPLOY} ᴅᴇᴘʟᴏʏ ᴄᴏɴsᴏʟᴇ",
                    callback_data=f"deploy_select_{project_id}",
                ),
            ],
            [
                InlineKeyboardButton(
                    f"{Emoji.FOLDER} ʙʀᴏᴡsᴇ ғɪʟᴇs",
                    callback_data=f"file_browse_{project_id}",
                ),
                InlineKeyboardButton(
                    f"{Emoji.LOG} ᴠɪᴇᴡ ʟᴏɢs",
                    callback_data=f"log_view_{project_id}",
                ),
            ],
            [
                InlineKeyboardButton(
                    f"{Emoji.KEY} ᴇɴᴠ ᴠᴀʀs",
                    callback_data=f"proj_env_{project_id}",
                ),
                InlineKeyboardButton(
                    f"{Emoji.EDIT} ᴇᴅɪᴛ sᴇᴛᴛɪɴɢs",
                    callback_data=f"proj_edit_{project_id}",
                ),
            ],
            [
                InlineKeyboardButton(
                    f"{Emoji.DELETE} ᴅᴇʟᴇᴛᴇ ᴘʀᴏᴊᴇᴄᴛ",
                    callback_data=f"confirm_delete_proj_{project_id}",
                ),
            ],
            [
                InlineKeyboardButton(
                    f"{Emoji.BACK} ʙᴀᴄᴋ",
                    callback_data="menu_projects",
                ),
                InlineKeyboardButton(
                    f"{Emoji.REFRESH} ʀᴇғʀᴇsʜ",
                    callback_data=f"proj_detail_{project_id}",
                ),
            ],
        ]

        keyboard = InlineKeyboardMarkup(buttons)
        try:
            await query.edit_message_text(text, reply_markup=keyboard)
        except BadRequest:
            pass

    elif data.startswith("proj_env_"):
        project_id = data.replace("proj_env_", "")
        project = db.get_project(project_id)

        if not project:
            await query.answer("❌ Project not found!", show_alert=True)
            return

        env_vars = json.loads(project["env_vars"] or "{}")

        text = (
            f"{Emoji.KEY} {Fonts.bold('ENVIRONMENT VARIABLES')} {Emoji.KEY}\n"
            f"{UI.DIVIDER_STAR}\n"
            f"{UI.BULLET} {Fonts.small_caps('project')}: {project['project_name']}\n\n"
            f"{UI.DIVIDER_THIN}\n\n"
        )

        if env_vars:
            for key, value in env_vars.items():
                masked_value = value[:3] + "***" if len(value) > 3 else "***"
                text += f"  {Emoji.KEY} {Fonts.mono(key)} = {masked_value}\n"
            text += "\n"
        else:
            text += f"{Emoji.INFO} {Fonts.small_caps('no environment variables set.')}\n\n"

        text += (
            f"{UI.DIVIDER_THIN}\n\n"
            f"{UI.BULLET} {Fonts.small_caps('to add/edit env vars, send a message in format')}:\n"
            f"  {Fonts.mono('/setenv project_id KEY=VALUE')}\n\n"
            f"{UI.DIVIDER_STAR}"
        )

        keyboard = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        f"{Emoji.BACK} ʙᴀᴄᴋ",
                        callback_data=f"proj_detail_{project_id}",
                    )
                ]
            ]
        )
        try:
            await query.edit_message_text(text, reply_markup=keyboard)
        except BadRequest:
            pass

    elif data.startswith("proj_edit_"):
        project_id = data.replace("proj_edit_", "")
        project = db.get_project(project_id)

        if not project:
            await query.answer("❌ Project not found!", show_alert=True)
            return

        # List available main files for selection
        proj_dir = Path(project["directory"])
        available_mains = []
        for proj_type, main_files in SUPPORTED_MAIN_FILES.items():
            for mf in main_files:
                if (proj_dir / mf).exists():
                    available_mains.append((proj_type, mf))

        text = (
            f"{Emoji.EDIT} {Fonts.bold('EDIT PROJECT')} {Emoji.EDIT}\n"
            f"{UI.DIVIDER_STAR}\n"
            f"{UI.BULLET} {Fonts.small_caps('project')}: {project['project_name']}\n"
            f"{UI.BULLET} {Fonts.small_caps('current main')}: {project['main_file'] or 'Not set'}\n"
            f"{UI.BULLET} {Fonts.small_caps('current type')}: {project['project_type']}\n\n"
            f"{UI.DIVIDER_THIN}\n\n"
        )

        buttons = []

        if available_mains:
            text += f"{Emoji.SEARCH} {Fonts.small_caps('detected main files')}:\n\n"
            for proj_type, mf in available_mains:
                is_current = mf == project["main_file"]
                marker = f" {Emoji.CHECKMARK}" if is_current else ""
                text += f"  {UI.TRIANGLE} {mf} ({proj_type}){marker}\n"
                if not is_current:
                    buttons.append(
                        [
                            InlineKeyboardButton(
                                f"{'🐍' if proj_type == 'python' else '📦' if proj_type == 'nodejs' else '☕'} "
                                f"sᴇᴛ: {mf}",
                                callback_data=f"proj_setmain_{project_id}:{proj_type}:{mf}",
                            )
                        ]
                    )
            text += "\n"
        else:
            text += f"{Emoji.WARNING} {Fonts.small_caps('no recognized main files found.')}\n\n"

        text += (
            f"{UI.DIVIDER_THIN}\n"
            f"{UI.BULLET} {Fonts.small_caps('to set a custom main file')}:\n"
            f"  {Fonts.mono('/setmain project_id filename.py')}\n\n"
            f"{UI.DIVIDER_STAR}"
        )

        buttons.append(
            [
                InlineKeyboardButton(
                    f"{Emoji.SEARCH} ᴀᴜᴛᴏ ᴅᴇᴛᴇᴄᴛ",
                    callback_data=f"deploy_detect_{project_id}",
                ),
            ]
        )
        buttons.append(
            [
                InlineKeyboardButton(
                    f"{Emoji.BACK} ʙᴀᴄᴋ",
                    callback_data=f"proj_detail_{project_id}",
                ),
            ]
        )

        keyboard = InlineKeyboardMarkup(buttons)
        try:
            await query.edit_message_text(text, reply_markup=keyboard)
        except BadRequest:
            pass

    elif data.startswith("proj_setmain_"):
        parts = data.replace("proj_setmain_", "").split(":")
        if len(parts) != 3:
            await query.answer("❌ Invalid data!", show_alert=True)
            return

        project_id, proj_type, main_file = parts
        db.update_project(project_id, project_type=proj_type, main_file=main_file)
        await query.answer(f"✅ Main file set to: {main_file} ({proj_type})", show_alert=True)

        # Refresh
        update.callback_query.data = f"proj_detail_{project_id}"
        await handle_project_action(update, context, f"proj_detail_{project_id}")


# ┌─────────────────────────────────────────────────────────────────────────────┐
# │             SECTION 16: UPLOAD HANDLER                                      │
# └─────────────────────────────────────────────────────────────────────────────┘

async def show_upload_instructions(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Show upload instructions."""
    query = update.callback_query

    text = (
        f"{Emoji.UPLOAD} {Fonts.bold('UPLOAD PROJECT')} {Emoji.UPLOAD}\n"
        f"{UI.DIVIDER_STAR}\n\n"
        f"{UI.BULLET} {Fonts.small_caps('upload a zip archive to create a new project')}\n\n"
        f"{UI.DIVIDER_THIN}\n\n"
        f"{Emoji.FIRE} {Fonts.small_caps('instructions')}:\n\n"
        f"  {Emoji.CHECKMARK} {Fonts.small_caps('compress your project into a .zip file')}\n"
        f"  {Emoji.CHECKMARK} {Fonts.small_caps('send the zip file to this chat')}\n"
        f"  {Emoji.CHECKMARK} {Fonts.small_caps('bot will auto-extract & detect project type')}\n"
        f"  {Emoji.CHECKMARK} {Fonts.small_caps('then deploy from the deploy console')}\n\n"
        f"{UI.DIVIDER_THIN}\n\n"
        f"{Emoji.BOLT} {Fonts.small_caps('supported formats')}:\n"
        f"  {UI.TRIANGLE} .zip\n"
        f"  {UI.TRIANGLE} .tar / .tar.gz / .tgz\n"
        f"  {UI.TRIANGLE} .tar.bz2\n\n"
        f"{Emoji.CODE} {Fonts.small_caps('supported languages')}:\n"
        f"  {UI.TRIANGLE} 🐍 Python (main.py, app.py, bot.py, ...)\n"
        f"  {UI.TRIANGLE} 📦 Node.js (index.js, app.js, server.js, ...)\n"
        f"  {UI.TRIANGLE} ☕ Java (Main.java, App.java, ...)\n\n"
        f"{Emoji.WARNING} {Fonts.small_caps('limits')}:\n"
        f"  {UI.TRIANGLE} {Fonts.small_caps('max file size')}: {MAX_UPLOAD_SIZE_MB} MB\n"
        f"  {UI.TRIANGLE} {Fonts.small_caps('max projects')}: {MAX_PROJECTS}\n\n"
        f"{UI.DIVIDER_STAR}\n"
        f"{Emoji.INFO} {Fonts.small_caps('just send your zip file now!')}"
    )

    keyboard = menu.get_back_button()
    try:
        await query.edit_message_text(text, reply_markup=keyboard)
    except BadRequest:
        pass


@authorized
async def handle_document_upload(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Handle uploaded document files (ZIP/TAR archives)."""
    user = update.effective_user
    message = update.message
    document = message.document

    if not document:
        return

    filename = document.file_name or "unknown"
    file_size = document.file_size or 0

    # Check extension
    file_ext = "".join(Path(filename).suffixes).lower()
    if not any(filename.lower().endswith(ext) for ext in SUPPORTED_ARCHIVES):
        await message.reply_text(
            f"{Emoji.WARNING} {Fonts.small_caps('unsupported file format')}\n\n"
            f"{UI.BULLET} {Fonts.small_caps('file')}: {filename}\n"
            f"{UI.BULLET} {Fonts.small_caps('supported')}: .zip, .tar, .tar.gz, .tgz, .tar.bz2\n\n"
            f"{UI.DIVIDER_THIN}"
        )
        return

    # Check size
    if file_size > MAX_UPLOAD_SIZE_MB * 1024 * 1024:
        await message.reply_text(
            f"{Emoji.ERROR} {Fonts.small_caps('file too large')}\n\n"
            f"{UI.BULLET} {Fonts.small_caps('size')}: {UI.format_bytes(file_size)}\n"
            f"{UI.BULLET} {Fonts.small_caps('max')}: {MAX_UPLOAD_SIZE_MB} MB\n\n"
            f"{UI.DIVIDER_THIN}"
        )
        return

    # Check project limit
    project_count = db.get_project_count(user.id)
    if project_count >= MAX_PROJECTS:
        await message.reply_text(
            f"{Emoji.ERROR} {Fonts.small_caps('project limit reached')}\n\n"
            f"{UI.BULLET} {Fonts.small_caps('current')}: {project_count}\n"
            f"{UI.BULLET} {Fonts.small_caps('max')}: {MAX_PROJECTS}\n\n"
            f"{UI.DIVIDER_THIN}"
        )
        return

    # Show progress
    progress_msg = await message.reply_text(
        f"{Emoji.LOADING} {Fonts.small_caps('processing upload...')}\n\n"
        f"{UI.BULLET} {Fonts.small_caps('file')}: {filename}\n"
        f"{UI.BULLET} {Fonts.small_caps('size')}: {UI.format_bytes(file_size)}\n\n"
        f"{UI.progress_bar(0, 100, 20)}\n\n"
        f"{UI.DIVIDER_THIN}"
    )

    try:
        # Step 1: Download file
        await progress_msg.edit_text(
            f"{Emoji.LOADING} {Fonts.small_caps('downloading file...')}\n\n"
            f"{UI.BULLET} {Fonts.small_caps('file')}: {filename}\n"
            f"{UI.progress_bar(25, 100, 20)}\n\n"
            f"{UI.DIVIDER_THIN}"
        )

        temp_path = TEMP_DIR / f"{uuid.uuid4().hex}_{filename}"
        file_obj = await document.get_file()
        await file_obj.download_to_drive(str(temp_path))

        # Step 2: Generate project ID and directory
        project_name = Path(filename).stem.replace(" ", "_").replace("-", "_")
        project_id = f"proj_{uuid.uuid4().hex[:12]}"
        project_dir = PROJECTS_DIR / project_id

        await progress_msg.edit_text(
            f"{Emoji.LOADING} {Fonts.small_caps('extracting archive...')}\n\n"
            f"{UI.BULLET} {Fonts.small_caps('file')}: {filename}\n"
            f"{UI.progress_bar(50, 100, 20)}\n\n"
            f"{UI.DIVIDER_THIN}"
        )

        # Step 3: Extract
        success, extract_msg, file_count = file_manager.extract_archive(
            temp_path, project_dir
        )

        if not success:
            await progress_msg.edit_text(
                f"{Emoji.ERROR} {Fonts.small_caps('extraction failed')}\n\n"
                f"{UI.BULLET} {extract_msg}\n\n"
                f"{UI.DIVIDER_THIN}"
            )
            # Cleanup
            temp_path.unlink(missing_ok=True)
            if project_dir.exists():
                shutil.rmtree(str(project_dir), ignore_errors=True)
            return

        # Step 4: Detect project type
        await progress_msg.edit_text(
            f"{Emoji.LOADING} {Fonts.small_caps('detecting project type...')}\n\n"
            f"{UI.BULLET} {Fonts.small_caps('files extracted')}: {file_count}\n"
            f"{UI.progress_bar(75, 100, 20)}\n\n"
            f"{UI.DIVIDER_THIN}"
        )

        proj_type, main_file = file_manager.detect_project_type(project_dir)

        # Step 5: Save to database
        db.create_project(
            project_id=project_id,
            user_id=user.id,
            project_name=project_name,
            project_type=proj_type,
            directory=str(project_dir),
            main_file=main_file,
        )

        db.log_file_operation(
            user.id, "upload", filename, project_id, file_size, "success",
            f"Extracted {file_count} files",
        )

        db.add_notification(
            user.id,
            "Project Uploaded",
            f"Project '{project_name}' uploaded successfully with {file_count} files.",
            "success",
        )

        # Cleanup temp
        temp_path.unlink(missing_ok=True)

        type_icons = {"python": "🐍", "nodejs": "📦", "java": "☕", "unknown": "❓"}
        type_icon = type_icons.get(proj_type, "❓")

        dir_size = file_manager.get_directory_size(project_dir)

        # Step 6: Show success
        text = (
            f"{Emoji.SUCCESS} {Fonts.bold('UPLOAD SUCCESSFUL')} {Emoji.SUCCESS}\n"
            f"{UI.DIVIDER_STAR}\n\n"
            f"{Emoji.PACKAGE} {Fonts.small_caps('project created')}!\n\n"
            f"  {Emoji.DIAMOND} {Fonts.small_caps('name')}: {Fonts.bold(project_name)}\n"
            f"  {type_icon} {Fonts.small_caps('type')}: {proj_type}\n"
            f"  {Emoji.FILE} {Fonts.small_caps('main file')}: {main_file or 'Not detected'}\n"
            f"  {Emoji.FOLDER} {Fonts.small_caps('files')}: {file_count}\n"
            f"  {Emoji.DISK} {Fonts.small_caps('size')}: {UI.format_bytes(dir_size)}\n"
            f"  {Emoji.PIN} {Fonts.small_caps('id')}: {Fonts.mono(project_id)}\n\n"
            f"{UI.DIVIDER_THIN}\n\n"
        )

        if not main_file:
            text += (
                f"{Emoji.WARNING} {Fonts.small_caps('main file not auto-detected!')}\n"
                f"{UI.BULLET} {Fonts.small_caps('set it manually from deploy console')}\n\n"
            )

        text += (
            f"{UI.BULLET} {Fonts.small_caps('go to deploy console to start your project')}\n\n"
            f"{UI.DIVIDER_STAR}"
        )

        keyboard = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        f"{Emoji.DEPLOY} ᴅᴇᴘʟᴏʏ ɴᴏᴡ",
                        callback_data=f"deploy_select_{project_id}",
                    ),
                    InlineKeyboardButton(
                        f"{Emoji.FOLDER} ʙʀᴏᴡsᴇ ғɪʟᴇs",
                        callback_data=f"file_browse_{project_id}",
                    ),
                ],
                [
                    InlineKeyboardButton(
                        f"{Emoji.HOME} ᴍᴀɪɴ ᴍᴇɴᴜ",
                        callback_data="menu_main",
                    ),
                ],
            ]
        )

        await progress_msg.edit_text(text, reply_markup=keyboard)

    except Exception as e:
        logger.error(f"Upload error: {e}\n{traceback.format_exc()}")
        await progress_msg.edit_text(
            f"{Emoji.ERROR} {Fonts.small_caps('upload failed')}\n\n"
            f"{UI.BULLET} {str(e)[:200]}\n\n"
            f"{UI.DIVIDER_THIN}"
        )
        # Cleanup
        if 'temp_path' in locals() and temp_path.exists():
            temp_path.unlink(missing_ok=True)
        if 'project_dir' in locals() and project_dir.exists():
            shutil.rmtree(str(project_dir), ignore_errors=True)


# ┌─────────────────────────────────────────────────────────────────────────────┐
# │             SECTION 17: NOTIFICATIONS HANDLER                               │
# └─────────────────────────────────────────────────────────────────────────────┘

async def show_notifications(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Show user notifications."""
    user = update.effective_user
    query = update.callback_query
    notifications = db.get_notifications(user.id, limit=15)
    unread = db.get_unread_count(user.id)

    text = (
        f"{Emoji.BELL} {Fonts.bold('NOTIFICATIONS')} {Emoji.BELL}\n"
        f"{UI.DIVIDER_STAR}\n\n"
        f"{UI.BULLET} {Fonts.small_caps('unread')}: {Fonts.bold(str(unread))}\n"
        f"{UI.BULLET} {Fonts.small_caps('total shown')}: {len(notifications)}\n\n"
        f"{UI.DIVIDER_THIN}\n\n"
    )

    if not notifications:
        text += f"{Emoji.INFO} {Fonts.small_caps('no notifications yet.')}\n\n"
    else:
        type_icons = {
            "info": Emoji.INFO,
            "success": Emoji.SUCCESS,
            "warning": Emoji.WARNING,
            "error": Emoji.ERROR,
        }

        for notif in notifications:
            icon = type_icons.get(notif["notif_type"], Emoji.INFO)
            read_marker = "" if notif["is_read"] else f" {Emoji.FIRE}"
            text += (
                f"{icon} {Fonts.bold(notif['title'])}{read_marker}\n"
                f"  {UI.TRIANGLE} {notif['message'][:100]}\n"
                f"  {Emoji.CLOCK} {notif['created_at'][:16]}\n\n"
            )

    text += f"{UI.DIVIDER_STAR}"

    buttons = []
    if unread > 0:
        buttons.append(
            [
                InlineKeyboardButton(
                    f"{Emoji.CHECKMARK} ᴍᴀʀᴋ ᴀʟʟ ʀᴇᴀᴅ",
                    callback_data="notif_markall",
                ),
            ]
        )
    buttons.append(
        [
            InlineKeyboardButton(
                f"{Emoji.REFRESH} ʀᴇғʀᴇsʜ",
                callback_data="menu_notifications",
            ),
            InlineKeyboardButton(
                f"{Emoji.BACK} ʙᴀᴄᴋ",
                callback_data="menu_main",
            ),
        ]
    )

    keyboard = InlineKeyboardMarkup(buttons)
    try:
        await query.edit_message_text(text, reply_markup=keyboard)
    except BadRequest:
        pass


async def handle_notification_action(
    update: Update, context: ContextTypes.DEFAULT_TYPE, data: str
) -> None:
    """Handle notification actions."""
    query = update.callback_query
    user = update.effective_user

    if data == "notif_markall":
        db.mark_all_notifications_read(user.id)
        await query.answer("✅ All notifications marked as read!", show_alert=True)
        # Refresh
        update.callback_query.data = "menu_notifications"
        await show_notifications(update, context)


# ┌─────────────────────────────────────────────────────────────────────────────┐
# │             SECTION 18: SETTINGS HANDLER                                    │
# └─────────────────────────────────────────────────────────────────────────────┘

async def show_settings(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Show user settings."""
    user = update.effective_user
    query = update.callback_query
    user_data = db.get_user(user.id)

    notifications_enabled = user_data["notifications"] if user_data else 1
    theme = user_data["theme"] if user_data else "default"
    lang = user_data["language"] if user_data else "en"

    notif_status = Emoji.ONLINE if notifications_enabled else Emoji.OFFLINE

    text = (
        f"{Emoji.SETTINGS} {Fonts.bold('SETTINGS')} {Emoji.SETTINGS}\n"
        f"{UI.DIVIDER_STAR}\n\n"
        f"{UI.BULLET} {Fonts.small_caps('customize your bot experience')}\n\n"
        f"{UI.DIVIDER_THIN}\n\n"
        f"  {Emoji.BELL} {Fonts.small_caps('notifications')}: {notif_status} {'ᴏɴ' if notifications_enabled else 'ᴏғғ'}\n"
        f"  {Emoji.GLOBE} {Fonts.small_caps('language')}: {lang}\n"
        f"  {Emoji.SPARKLE} {Fonts.small_caps('theme')}: {theme}\n"
        f"  {Emoji.PACKAGE} {Fonts.small_caps('max projects')}: {user_data['max_projects'] if user_data else MAX_PROJECTS}\n\n"
        f"{UI.DIVIDER_THIN}\n\n"
        f"  {Emoji.USER} {Fonts.small_caps('user info')}:\n"
        f"    {UI.TRIANGLE} {Fonts.small_caps('id')}: {Fonts.mono(str(user.id))}\n"
        f"    {UI.TRIANGLE} {Fonts.small_caps('username')}: @{user.username or 'N/A'}\n"
        f"    {UI.TRIANGLE} {Fonts.small_caps('joined')}: {user_data['joined_at'][:10] if user_data else 'N/A'}\n"
        f"    {UI.TRIANGLE} {Fonts.small_caps('total deploys')}: {user_data['total_deploys'] if user_data else 0}\n\n"
        f"{UI.DIVIDER_STAR}"
    )

    buttons = [
        [
            InlineKeyboardButton(
                f"{Emoji.BELL} ᴛᴏɢɢʟᴇ ɴᴏᴛɪғɪᴄᴀᴛɪᴏɴs",
                callback_data="set_toggle_notif",
            ),
        ],
        [
            InlineKeyboardButton(
                f"{Emoji.DATABASE} ᴄʟᴇᴀɴᴜᴘ ᴏʟᴅ ʟᴏɢs",
                callback_data="set_cleanup_logs",
            ),
        ],
        [
            InlineKeyboardButton(
                f"{Emoji.BACK} ʙᴀᴄᴋ ᴛᴏ ᴍᴇɴᴜ",
                callback_data="menu_main",
            ),
        ],
    ]

    keyboard = InlineKeyboardMarkup(buttons)
    try:
        await query.edit_message_text(text, reply_markup=keyboard)
    except BadRequest:
        pass


async def handle_settings_action(
    update: Update, context: ContextTypes.DEFAULT_TYPE, data: str
) -> None:
    """Handle settings actions."""
    query = update.callback_query
    user = update.effective_user

    if data == "set_toggle_notif":
        user_data = db.get_user(user.id)
        current = user_data["notifications"] if user_data else 1
        new_val = 0 if current else 1
        db.execute(
            "UPDATE users SET notifications = ? WHERE user_id = ?",
            (new_val, user.id),
        )
        status = "enabled" if new_val else "disabled"
        await query.answer(f"✅ Notifications {status}!", show_alert=True)
        await show_settings(update, context)

    elif data == "set_cleanup_logs":
        db.cleanup_old_logs(days=7)
        await query.answer("✅ Old logs cleaned up (7+ days)!", show_alert=True)
        await show_settings(update, context)


# ┌─────────────────────────────────────────────────────────────────────────────┐
# │             SECTION 19: ADMIN PANEL                                         │
# └─────────────────────────────────────────────────────────────────────────────┘

@owner_only
async def show_admin_panel(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Show admin panel (owner only)."""
    query = update.callback_query

    all_users = db.get_all_users()
    all_projects = db.get_all_projects()
    running = process_manager.running_count
    db_size = db.get_db_size()

    text = (
        f"{Emoji.CROWN} {Fonts.bold('ADMIN PANEL')} {Emoji.CROWN}\n"
        f"{UI.DIVIDER_STAR}\n\n"
        f"{Emoji.SHIELD} {Fonts.small_caps('owner control center')}\n\n"
        f"{UI.DIVIDER_THIN}\n\n"
        f"  {Emoji.USERS} {Fonts.small_caps('total users')}: {Fonts.bold(str(len(all_users)))}\n"
        f"  {Emoji.PACKAGE} {Fonts.small_caps('total projects')}: {Fonts.bold(str(len(all_projects)))}\n"
        f"  {Emoji.ONLINE} {Fonts.small_caps('running')}: {Fonts.bold(str(running))}\n"
        f"  {Emoji.DATABASE} {Fonts.small_caps('db size')}: {UI.format_bytes(db_size)}\n\n"
        f"{UI.DIVIDER_THIN}\n\n"
        f"  {Emoji.STATS} {Fonts.small_caps('system overview')}:\n"
    )

    cpu = psutil.cpu_percent(interval=0.1)
    mem = psutil.virtual_memory()
    disk = psutil.disk_usage("/")

    text += (
        f"    {Emoji.CPU} CPU: {UI.progress_bar(cpu, 100, 12)}\n"
        f"    {Emoji.RAM} RAM: {UI.progress_bar(mem.percent, 100, 12)}\n"
        f"    {Emoji.DISK} Disk: {UI.progress_bar(disk.percent, 100, 12)}\n\n"
        f"{UI.DIVIDER_STAR}"
    )

    buttons = [
        [
            InlineKeyboardButton(
                f"{Emoji.USERS} ᴜsᴇʀ ᴍᴀɴᴀɢᴇᴍᴇɴᴛ",
                callback_data="admin_users",
            ),
        ],
        [
            InlineKeyboardButton(
                f"{Emoji.PACKAGE} ᴀʟʟ ᴘʀᴏᴊᴇᴄᴛs",
                callback_data="admin_all_projects",
            ),
        ],
        [
            InlineKeyboardButton(
                f"{Emoji.STOP} sᴛᴏᴘ ᴀʟʟ ᴘʀᴏᴄᴇssᴇs",
                callback_data="confirm_stop_all",
            ),
        ],
        [
            InlineKeyboardButton(
                f"{Emoji.DATABASE} ᴅᴀᴛᴀʙᴀsᴇ ᴏᴘᴛɪᴍɪᴢᴇ",
                callback_data="admin_db_optimize",
            ),
            InlineKeyboardButton(
                f"{Emoji.DELETE} ᴄʟᴇᴀɴᴜᴘ ᴏʟᴅ ᴅᴀᴛᴀ",
                callback_data="admin_cleanup",
            ),
        ],
        [
            InlineKeyboardButton(
                f"{Emoji.BACK} ʙᴀᴄᴋ ᴛᴏ ᴍᴇɴᴜ",
                callback_data="menu_main",
            ),
            InlineKeyboardButton(
                f"{Emoji.REFRESH} ʀᴇғʀᴇsʜ",
                callback_data="menu_admin",
            ),
        ],
    ]

    keyboard = InlineKeyboardMarkup(buttons)
    try:
        if query:
            await query.edit_message_text(text, reply_markup=keyboard)
        elif update.message:
            await update.message.reply_text(text, reply_markup=keyboard)
    except BadRequest:
        pass


async def handle_admin_action(
    update: Update, context: ContextTypes.DEFAULT_TYPE, data: str
) -> None:
    """Handle admin actions."""
    query = update.callback_query
    user = update.effective_user

    if user.id != OWNER_ID:
        await query.answer("👑 Owner only!", show_alert=True)
        return

    if data == "admin_users":
        users = db.get_all_users()

        text = (
            f"{Emoji.USERS} {Fonts.bold('USER MANAGEMENT')} {Emoji.USERS}\n"
            f"{UI.DIVIDER_STAR}\n\n"
        )

        for u in users[:20]:
            is_owner_badge = f" {Emoji.CROWN}" if u["is_owner"] else ""
            is_admin_badge = f" {Emoji.SHIELD}" if u["is_admin"] else ""
            is_banned_badge = f" {Emoji.ERROR}" if u["is_banned"] else ""

            text += (
                f"  {Emoji.USER} {u['first_name'] or 'Unknown'}"
                f"{is_owner_badge}{is_admin_badge}{is_banned_badge}\n"
                f"    {UI.TRIANGLE} ID: {Fonts.mono(str(u['user_id']))}\n"
                f"    {UI.TRIANGLE} @{u['username'] or 'N/A'}\n"
                f"    {UI.TRIANGLE} Last: {u['last_active'][:16]}\n\n"
            )

        text += f"{UI.DIVIDER_STAR}"

        keyboard = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        f"{Emoji.BACK} ʙᴀᴄᴋ",
                        callback_data="menu_admin",
                    ),
                    InlineKeyboardButton(
                        f"{Emoji.REFRESH} ʀᴇғʀᴇsʜ",
                        callback_data="admin_users",
                    ),
                ]
            ]
        )
        try:
            await query.edit_message_text(text, reply_markup=keyboard)
        except BadRequest:
            pass

    elif data == "admin_all_projects":
        projects = db.get_all_projects()

        text = (
            f"{Emoji.PACKAGE} {Fonts.bold('ALL PROJECTS')} {Emoji.PACKAGE}\n"
            f"{UI.DIVIDER_STAR}\n\n"
        )

        for proj in projects[:20]:
            is_running = process_manager.is_running(proj["project_id"])
            status = Emoji.ONLINE if is_running else Emoji.OFFLINE
            text += (
                f"  {status} {Fonts.bold(proj['project_name'])}\n"
                f"    {UI.TRIANGLE} Owner: {proj['user_id']}\n"
                f"    {UI.TRIANGLE} Type: {proj['project_type']}\n"
                f"    {UI.TRIANGLE} Deploys: {proj['deploy_count']}\n\n"
            )

        if not projects:
            text += f"{Emoji.INFO} {Fonts.small_caps('no projects found.')}\n\n"

        text += f"{UI.DIVIDER_STAR}"

        keyboard = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        f"{Emoji.BACK} ʙᴀᴄᴋ",
                        callback_data="menu_admin",
                    ),
                ]
            ]
        )
        try:
            await query.edit_message_text(text, reply_markup=keyboard)
        except BadRequest:
            pass

    elif data == "admin_db_optimize":
        try:
            db.vacuum()
            await query.answer("✅ Database optimized!", show_alert=True)
        except Exception as e:
            await query.answer(f"❌ Error: {str(e)[:50]}", show_alert=True)

    elif data == "admin_cleanup":
        db.cleanup_old_logs(days=3)
        await query.answer("✅ Old data cleaned up!", show_alert=True)
        await show_admin_panel(update, context)


# ┌─────────────────────────────────────────────────────────────────────────────┐
# │             SECTION 20: DATABASE INFO HANDLER                               │
# └─────────────────────────────────────────────────────────────────────────────┘

@owner_only
async def show_database_info(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Show database information."""
    query = update.callback_query

    db_size = db.get_db_size()
    user_count = len(db.get_all_users())
    project_count = len(db.get_all_projects())

    # Count records in each table
    tables = {
        "users": db.fetchone("SELECT COUNT(*) as cnt FROM users"),
        "projects": db.fetchone("SELECT COUNT(*) as cnt FROM projects"),
        "deployment_logs": db.fetchone("SELECT COUNT(*) as cnt FROM deployment_logs"),
        "process_logs": db.fetchone("SELECT COUNT(*) as cnt FROM process_logs"),
        "file_operations": db.fetchone("SELECT COUNT(*) as cnt FROM file_operations"),
        "system_stats": db.fetchone("SELECT COUNT(*) as cnt FROM system_stats"),
        "notifications": db.fetchone("SELECT COUNT(*) as cnt FROM notifications"),
        "scheduled_tasks": db.fetchone("SELECT COUNT(*) as cnt FROM scheduled_tasks"),
    }

    text = (
        f"{Emoji.DATABASE} {Fonts.bold('DATABASE INFO')} {Emoji.DATABASE}\n"
        f"{UI.DIVIDER_STAR}\n\n"
        f"  {Emoji.DISK} {Fonts.small_caps('size')}: {UI.format_bytes(db_size)}\n"
        f"  {Emoji.GEAR} {Fonts.small_caps('schema version')}: {DatabaseManager.SCHEMA_VERSION}\n"
        f"  {Emoji.FILE} {Fonts.small_caps('path')}: {DATABASE_PATH.name}\n\n"
        f"{UI.DIVIDER_THIN}\n\n"
        f"  {Fonts.small_caps('table records')}:\n\n"
    )

    for table_name, row in tables.items():
        count = row["cnt"] if row else 0
        text += f"    {UI.TRIANGLE} {Fonts.small_caps(table_name)}: {Fonts.bold(str(count))}\n"

    text += f"\n{UI.DIVIDER_STAR}"

    buttons = [
        [
            InlineKeyboardButton(
                f"{Emoji.WRENCH} ᴏᴘᴛɪᴍɪᴢᴇ (ᴠᴀᴄᴜᴜᴍ)",
                callback_data="admin_db_optimize",
            ),
        ],
        [
            InlineKeyboardButton(
                f"{Emoji.DELETE} ᴄʟᴇᴀɴᴜᴘ (7+ ᴅᴀʏs)",
                callback_data="admin_cleanup",
            ),
        ],
        [
            InlineKeyboardButton(
                f"{Emoji.BACK} ʙᴀᴄᴋ",
                callback_data="menu_admin",
            ),
            InlineKeyboardButton(
                f"{Emoji.REFRESH} ʀᴇғʀᴇsʜ",
                callback_data="menu_database",
            ),
        ],
    ]

    keyboard = InlineKeyboardMarkup(buttons)
    try:
        await query.edit_message_text(text, reply_markup=keyboard)
    except BadRequest:
        pass


# ┌─────────────────────────────────────────────────────────────────────────────┐
# │             SECTION 21: CONFIRMATION HANDLERS                               │
# └─────────────────────────────────────────────────────────────────────────────┘

async def handle_confirmation(
    update: Update, context: ContextTypes.DEFAULT_TYPE, data: str
) -> None:
    """Handle confirmation dialogs for destructive actions."""
    query = update.callback_query
    user = update.effective_user

    if data.startswith("confirm_delete_proj_"):
        project_id = data.replace("confirm_delete_proj_", "")
        project = db.get_project(project_id)

        if not project:
            await query.answer("❌ Project not found!", show_alert=True)
            return

        text = (
            f"{Emoji.WARNING} {Fonts.bold('CONFIRM DELETE')} {Emoji.WARNING}\n"
            f"{UI.DIVIDER_STAR}\n\n"
            f"{UI.BULLET} {Fonts.small_caps('are you sure you want to delete')}:\n\n"
            f"  {Emoji.PACKAGE} {Fonts.bold(project['project_name'])}\n"
            f"  {Emoji.CODE} {Fonts.small_caps('type')}: {project['project_type']}\n\n"
            f"{Emoji.ERROR} {Fonts.small_caps('this action cannot be undone!')}\n"
            f"{UI.BULLET} {Fonts.small_caps('all files and logs will be removed.')}\n\n"
            f"{UI.DIVIDER_STAR}"
        )

        keyboard = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        f"{Emoji.DELETE} ʏᴇs, ᴅᴇʟᴇᴛᴇ",
                        callback_data=f"confirm_yes_delproj_{project_id}",
                    ),
                    InlineKeyboardButton(
                        f"{Emoji.BACK} ᴄᴀɴᴄᴇʟ",
                        callback_data=f"deploy_select_{project_id}",
                    ),
                ]
            ]
        )
        try:
            await query.edit_message_text(text, reply_markup=keyboard)
        except BadRequest:
            pass

    elif data.startswith("confirm_yes_delproj_"):
        project_id = data.replace("confirm_yes_delproj_", "")
        project = db.get_project(project_id)

        if not project:
            await query.answer("❌ Project not found!", show_alert=True)
            return

        # Stop process if running
        if process_manager.is_running(project_id):
            await process_manager.stop_process(project_id, force=True)

        # Delete project directory
        proj_dir = Path(project["directory"])
        if proj_dir.exists():
            shutil.rmtree(str(proj_dir), ignore_errors=True)

        # Delete log file
        log_file = LOGS_DIR / f"{project_id}.log"
        log_file.unlink(missing_ok=True)

        # Delete from database
        project_name = project["project_name"]
        db.delete_project(project_id)

        db.log_file_operation(
            user.id, "delete_project", project_name, project_id, 0, "success",
        )

        text = (
            f"{Emoji.SUCCESS} {Fonts.bold('PROJECT DELETED')} {Emoji.SUCCESS}\n"
            f"{UI.DIVIDER_THIN}\n\n"
            f"{UI.BULLET} {Fonts.small_caps('project')} '{project_name}' "
            f"{Fonts.small_caps('has been deleted.')}\n\n"
            f"{UI.DIVIDER_THIN}"
        )

        keyboard = menu.get_back_button()
        try:
            await query.edit_message_text(text, reply_markup=keyboard)
        except BadRequest:
            pass

    elif data.startswith("confirm_delete_file_"):
        parts = data.replace("confirm_delete_file_", "").split(":", 1)
        project_id = parts[0]
        file_rel = parts[1] if len(parts) > 1 else ""

        project = db.get_project(project_id)
        if not project:
            await query.answer("❌ Project not found!", show_alert=True)
            return

        file_path = Path(project["directory"]) / file_rel

        text = (
            f"{Emoji.WARNING} {Fonts.bold('CONFIRM DELETE FILE')} {Emoji.WARNING}\n"
            f"{UI.DIVIDER_THIN}\n\n"
            f"{UI.BULLET} {Fonts.small_caps('file')}: {file_path.name}\n"
            f"{UI.BULLET} {Fonts.small_caps('path')}: /{file_rel}\n\n"
            f"{Emoji.ERROR} {Fonts.small_caps('this cannot be undone!')}\n\n"
            f"{UI.DIVIDER_THIN}"
        )

        keyboard = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        f"{Emoji.DELETE} ʏᴇs, ᴅᴇʟᴇᴛᴇ",
                        callback_data=f"confirm_yes_delfile_{project_id}:{file_rel}",
                    ),
                    InlineKeyboardButton(
                        f"{Emoji.BACK} ᴄᴀɴᴄᴇʟ",
                        callback_data=f"file_info_{project_id}:{file_rel}",
                    ),
                ]
            ]
        )
        try:
            await query.edit_message_text(text, reply_markup=keyboard)
        except BadRequest:
            pass

    elif data.startswith("confirm_yes_delfile_"):
        parts = data.replace("confirm_yes_delfile_", "").split(":", 1)
        project_id = parts[0]
        file_rel = parts[1] if len(parts) > 1 else ""

        project = db.get_project(project_id)
        if not project:
            await query.answer("❌ Project not found!", show_alert=True)
            return

        file_path = Path(project["directory"]) / file_rel
        success, msg = file_manager.delete_path(file_path)

        if success:
            db.log_file_operation(
                user.id, "delete", file_rel, project_id, 0, "success",
            )
            await query.answer(f"✅ {msg}", show_alert=True)
        else:
            await query.answer(f"❌ {msg}", show_alert=True)

        # Navigate to parent directory
        parent_path = str(Path(file_rel).parent)
        if parent_path == ".":
            parent_path = ""
        parent_cb = f"file_browse_{project_id}" if not parent_path else f"file_browse_{project_id}:{parent_path}"
        update.callback_query.data = parent_cb
        await handle_file_action(update, context, parent_cb)

    elif data.startswith("confirm_delete_dir_"):
        parts = data.replace("confirm_delete_dir_", "").split(":", 1)
        project_id = parts[0]
        dir_rel = parts[1] if len(parts) > 1 else ""

        project = db.get_project(project_id)
        if not project:
            await query.answer("❌ Project not found!", show_alert=True)
            return

        dir_path = Path(project["directory"]) / dir_rel

        text = (
            f"{Emoji.WARNING} {Fonts.bold('CONFIRM DELETE DIRECTORY')} {Emoji.WARNING}\n"
            f"{UI.DIVIDER_THIN}\n\n"
            f"{UI.BULLET} {Fonts.small_caps('directory')}: /{dir_rel}\n\n"
            f"{Emoji.ERROR} {Fonts.small_caps('all contents will be deleted!')}\n\n"
            f"{UI.DIVIDER_THIN}"
        )

        keyboard = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        f"{Emoji.DELETE} ʏᴇs, ᴅᴇʟᴇᴛᴇ",
                        callback_data=f"confirm_yes_deldir_{project_id}:{dir_rel}",
                    ),
                    InlineKeyboardButton(
                        f"{Emoji.BACK} ᴄᴀɴᴄᴇʟ",
                        callback_data=f"file_browse_{project_id}:{dir_rel}",
                    ),
                ]
            ]
        )
        try:
            await query.edit_message_text(text, reply_markup=keyboard)
        except BadRequest:
            pass

    elif data.startswith("confirm_yes_deldir_"):
        parts = data.replace("confirm_yes_deldir_", "").split(":", 1)
        project_id = parts[0]
        dir_rel = parts[1] if len(parts) > 1 else ""

        project = db.get_project(project_id)
        if not project:
            await query.answer("❌ Project not found!", show_alert=True)
            return

        dir_path = Path(project["directory"]) / dir_rel
        success, msg = file_manager.delete_path(dir_path)

        if success:
            db.log_file_operation(
                user.id, "delete_dir", dir_rel, project_id, 0, "success",
            )
            await query.answer(f"✅ {msg}", show_alert=True)
        else:
            await query.answer(f"❌ {msg}", show_alert=True)

        # Go back to project root
        update.callback_query.data = f"file_browse_{project_id}"
        await handle_file_action(update, context, f"file_browse_{project_id}")

    elif data == "confirm_stop_all":
        text = (
            f"{Emoji.WARNING} {Fonts.bold('STOP ALL PROCESSES?')} {Emoji.WARNING}\n"
            f"{UI.DIVIDER_THIN}\n\n"
            f"{UI.BULLET} {Fonts.small_caps('running')}: {process_manager.running_count}\n\n"
            f"{Emoji.ERROR} {Fonts.small_caps('all processes will be force killed!')}\n\n"
            f"{UI.DIVIDER_THIN}"
        )

        keyboard = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        f"{Emoji.STOP} ʏᴇs, sᴛᴏᴘ ᴀʟʟ",
                        callback_data="confirm_yes_stopall",
                    ),
                    InlineKeyboardButton(
                        f"{Emoji.BACK} ᴄᴀɴᴄᴇʟ",
                        callback_data="menu_admin",
                    ),
                ]
            ]
        )
        try:
            await query.edit_message_text(text, reply_markup=keyboard)
        except BadRequest:
            pass

    elif data == "confirm_yes_stopall":
        await process_manager.stop_all()
        await query.answer("✅ All processes stopped!", show_alert=True)
        await show_admin_panel(update, context)


# ┌─────────────────────────────────────────────────────────────────────────────┐
# │             SECTION 22: PAGINATION HANDLER                                  │
# └─────────────────────────────────────────────────────────────────────────────┘

async def handle_pagination(
    update: Update, context: ContextTypes.DEFAULT_TYPE, data: str
) -> None:
    """Handle pagination for long lists."""
    query = update.callback_query
    # Placeholder for future pagination implementation
    await query.answer("ℹ️ Pagination coming soon!", show_alert=True)


# ┌─────────────────────────────────────────────────────────────────────────────┐
# │             SECTION 23: ADDITIONAL COMMAND HANDLERS                         │
# └─────────────────────────────────────────────────────────────────────────────┘

@authorized
async def deploy_command(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Handle /deploy command."""
    user = update.effective_user
    projects = db.get_user_projects(user.id)

    text = (
        f"{Emoji.DEPLOY} {Fonts.bold('DEPLOY CONSOLE')} {Emoji.DEPLOY}\n"
        f"{UI.DIVIDER_STAR}\n\n"
        f"{UI.BULLET} {Fonts.small_caps('select a project to deploy')}\n\n"
        f"{UI.DIVIDER_THIN}\n\n"
    )

    buttons = []
    for proj in projects:
        is_running = process_manager.is_running(proj["project_id"])
        status = Emoji.ONLINE if is_running else Emoji.OFFLINE
        buttons.append(
            [
                InlineKeyboardButton(
                    f"{status} {proj['project_name']}",
                    callback_data=f"deploy_select_{proj['project_id']}",
                )
            ]
        )

    if not projects:
        text += f"{Emoji.INFO} {Fonts.small_caps('no projects. upload a zip file first!')}\n\n"

    text += f"{UI.DIVIDER_STAR}"

    buttons.append(
        [InlineKeyboardButton(f"{Emoji.HOME} ᴍᴀɪɴ ᴍᴇɴᴜ", callback_data="menu_main")]
    )

    await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(buttons))


@authorized
async def logs_command(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Handle /logs command."""
    user = update.effective_user
    projects = db.get_user_projects(user.id)

    buttons = []
    for proj in projects:
        is_running = process_manager.is_running(proj["project_id"])
        status = Emoji.ONLINE if is_running else Emoji.OFFLINE
        buttons.append(
            [
                InlineKeyboardButton(
                    f"{status} {proj['project_name']}",
                    callback_data=f"log_view_{proj['project_id']}",
                )
            ]
        )

    if not projects:
        buttons.append(
            [InlineKeyboardButton(f"{Emoji.HOME} ᴍᴀɪɴ ᴍᴇɴᴜ", callback_data="menu_main")]
        )
        await update.message.reply_text(
            f"{Emoji.LOG} {Fonts.small_caps('no projects found.')}\n{UI.DIVIDER_THIN}",
            reply_markup=InlineKeyboardMarkup(buttons),
        )
        return

    buttons.append(
        [InlineKeyboardButton(f"{Emoji.HOME} ᴍᴀɪɴ ᴍᴇɴᴜ", callback_data="menu_main")]
    )

    await update.message.reply_text(
        f"{Emoji.LOG} {Fonts.bold('SELECT PROJECT FOR LOGS')}\n{UI.DIVIDER_THIN}",
        reply_markup=InlineKeyboardMarkup(buttons),
    )


@authorized
async def files_command(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Handle /files command."""
    # Create a fake callback query context and route
    user = update.effective_user
    projects = db.get_user_projects(user.id)

    buttons = []
    for proj in projects:
        buttons.append(
            [
                InlineKeyboardButton(
                    f"{Emoji.FOLDER} {proj['project_name']}",
                    callback_data=f"file_browse_{proj['project_id']}",
                )
            ]
        )

    if not projects:
        buttons.append(
            [InlineKeyboardButton(f"{Emoji.HOME} ᴍᴀɪɴ ᴍᴇɴᴜ", callback_data="menu_main")]
        )
        await update.message.reply_text(
            f"{Emoji.FOLDER} {Fonts.small_caps('no projects found.')}\n{UI.DIVIDER_THIN}",
            reply_markup=InlineKeyboardMarkup(buttons),
        )
        return

    buttons.append(
        [InlineKeyboardButton(f"{Emoji.HOME} ᴍᴀɪɴ ᴍᴇɴᴜ", callback_data="menu_main")]
    )

    await update.message.reply_text(
        f"{Emoji.FOLDER} {Fonts.bold('FILE MANAGER - SELECT PROJECT')}\n{UI.DIVIDER_THIN}",
        reply_markup=InlineKeyboardMarkup(buttons),
    )


@authorized
async def upload_command(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Handle /upload command."""
    text = (
        f"{Emoji.UPLOAD} {Fonts.bold('UPLOAD PROJECT')} {Emoji.UPLOAD}\n"
        f"{UI.DIVIDER_THIN}\n\n"
        f"{UI.BULLET} {Fonts.small_caps('send a .zip file to upload a project')}\n"
        f"{UI.BULLET} {Fonts.small_caps('max size')}: {MAX_UPLOAD_SIZE_MB} MB\n"
        f"{UI.BULLET} {Fonts.small_caps('supported')}: .zip, .tar, .tar.gz\n\n"
        f"{UI.DIVIDER_THIN}"
    )
    await update.message.reply_text(text)


@owner_only
@authorized
async def admin_command(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Handle /admin command."""
    await show_admin_panel(update, context)


@owner_only
@authorized
async def adduser_command(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Handle /adduser <user_id> command."""
    args = context.args
    if not args:
        await update.message.reply_text(
            f"{Emoji.INFO} {Fonts.small_caps('usage')}: /adduser <user_id>"
        )
        return

    try:
        target_id = int(args[0])
        ALLOWED_USERS.add(target_id)
        db.set_admin(target_id, True)
        await update.message.reply_text(
            f"{Emoji.SUCCESS} {Fonts.small_caps('user')} {target_id} {Fonts.small_caps('authorized!')}"
        )
    except ValueError:
        await update.message.reply_text(
            f"{Emoji.ERROR} {Fonts.small_caps('invalid user id!')}"
        )


@owner_only
@authorized
async def ban_command(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Handle /ban <user_id> command."""
    args = context.args
    if not args:
        await update.message.reply_text(
            f"{Emoji.INFO} {Fonts.small_caps('usage')}: /ban <user_id>"
        )
        return

    try:
        target_id = int(args[0])
        if target_id == OWNER_ID:
            await update.message.reply_text(
                f"{Emoji.ERROR} {Fonts.small_caps('cannot ban the owner!')}"
            )
            return
        db.ban_user(target_id)
        ALLOWED_USERS.discard(target_id)
        await update.message.reply_text(
            f"{Emoji.SUCCESS} {Fonts.small_caps('user')} {target_id} {Fonts.small_caps('banned!')}"
        )
    except ValueError:
        await update.message.reply_text(
            f"{Emoji.ERROR} {Fonts.small_caps('invalid user id!')}"
        )


@owner_only
@authorized
async def stats_command(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Handle /stats command - Show bot statistics."""
    users = db.get_all_users()
    projects = db.get_all_projects()
    running = process_manager.running_count
    db_size = db.get_db_size()

    total_deploys = sum(p["deploy_count"] for p in projects)
    total_errors = sum(p["error_count"] for p in projects)
    total_runtime = sum(p["total_runtime"] for p in projects)

    text = (
        f"{Emoji.STATS} {Fonts.bold('BOT STATISTICS')} {Emoji.STATS}\n"
        f"{UI.DIVIDER_STAR}\n\n"
        f"  {Emoji.USERS} {Fonts.small_caps('users')}: {len(users)}\n"
        f"  {Emoji.PACKAGE} {Fonts.small_caps('projects')}: {len(projects)}\n"
        f"  {Emoji.ONLINE} {Fonts.small_caps('running')}: {running}\n"
        f"  {Emoji.DEPLOY} {Fonts.small_caps('total deploys')}: {total_deploys}\n"
        f"  {Emoji.ERROR} {Fonts.small_caps('total errors')}: {total_errors}\n"
        f"  {Emoji.UPTIME} {Fonts.small_caps('total runtime')}: {UI.format_uptime(total_runtime)}\n"
        f"  {Emoji.DATABASE} {Fonts.small_caps('db size')}: {UI.format_bytes(db_size)}\n\n"
        f"{UI.DIVIDER_STAR}"
    )

    keyboard = menu.get_back_button()
    await update.message.reply_text(text, reply_markup=keyboard)


@authorized
async def setenv_command(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Handle /setenv <project_id> <KEY=VALUE> command."""
    args = context.args
    if not args or len(args) < 2:
        await update.message.reply_text(
            f"{Emoji.INFO} {Fonts.small_caps('usage')}: /setenv <project_id> <KEY=VALUE>\n"
            f"{UI.BULLET} {Fonts.small_caps('example')}: /setenv proj_abc123 API_KEY=mykey123"
        )
        return

    project_id = args[0]
    kv = args[1]

    if "=" not in kv:
        await update.message.reply_text(
            f"{Emoji.ERROR} {Fonts.small_caps('invalid format. use KEY=VALUE')}"
        )
        return

    project = db.get_project(project_id)
    if not project:
        await update.message.reply_text(
            f"{Emoji.ERROR} {Fonts.small_caps('project not found!')}"
        )
        return

    key, value = kv.split("=", 1)
    env_vars = json.loads(project["env_vars"] or "{}")
    env_vars[key.strip()] = value.strip()
    db.update_project(project_id, env_vars=json.dumps(env_vars))

    await update.message.reply_text(
        f"{Emoji.SUCCESS} {Fonts.small_caps('env var set')}!\n"
        f"{UI.BULLET} {Fonts.mono(key.strip())} = {'*' * min(len(value.strip()), 5)}\n"
        f"{UI.BULLET} {Fonts.small_caps('restart the project to apply changes.')}"
    )


@authorized
async def setmain_command(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Handle /setmain <project_id> <filename> command."""
    args = context.args
    if not args or len(args) < 2:
        await update.message.reply_text(
            f"{Emoji.INFO} {Fonts.small_caps('usage')}: /setmain <project_id> <filename>\n"
            f"{UI.BULLET} {Fonts.small_caps('example')}: /setmain proj_abc123 main.py"
        )
        return

    project_id = args[0]
    main_file = args[1]

    project = db.get_project(project_id)
    if not project:
        await update.message.reply_text(
            f"{Emoji.ERROR} {Fonts.small_caps('project not found!')}"
        )
        return

    # Verify file exists
    file_path = Path(project["directory"]) / main_file
    if not file_path.exists():
        await update.message.reply_text(
            f"{Emoji.ERROR} {Fonts.small_caps('file not found')}: {main_file}"
        )
        return

    # Auto-detect type from extension
    ext = file_path.suffix.lower()
    type_map = {".py": "python", ".js": "nodejs", ".java": "java"}
    proj_type = type_map.get(ext, project["project_type"])

    db.update_project(project_id, main_file=main_file, project_type=proj_type)

    await update.message.reply_text(
        f"{Emoji.SUCCESS} {Fonts.small_caps('main file set')}!\n"
        f"{UI.BULLET} {Fonts.small_caps('file')}: {main_file}\n"
        f"{UI.BULLET} {Fonts.small_caps('type')}: {proj_type}"
    )


# ┌─────────────────────────────────────────────────────────────────────────────┐
# │             SECTION 24: SCHEDULED JOBS                                      │
# └─────────────────────────────────────────────────────────────────────────────┘

async def health_check_job(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Periodic health check job - monitors running processes."""
    try:
        # Save system stats
        system_monitor.save_snapshot()

        # Check for crashed processes
        running_projects = db.get_running_projects()
        for proj in running_projects:
            project_id = proj["project_id"]
            if not process_manager.is_running(project_id):
                # Process crashed but DB still shows running
                db.update_project(
                    project_id,
                    status="crashed",
                    pid=None,
                    last_stopped=datetime.now().isoformat(),
                )

                # Check auto-restart
                if proj["auto_restart"] and proj["restart_count"] < proj["max_restarts"]:
                    env_vars = json.loads(proj["env_vars"] or "{}")
                    success, msg = await process_manager.start_process(
                        project_id,
                        proj["project_type"],
                        proj["main_file"],
                        proj["directory"],
                        env_vars if env_vars else None,
                    )
                    db.log_deployment(
                        project_id, 0, "auto_restart",
                        "success" if success else "failed", msg,
                    )
                    logger.info(
                        f"Auto-restart for {proj['project_name']}: {'success' if success else 'failed'}"
                    )

                    # Notify owner
                    db.add_notification(
                        proj["user_id"],
                        "Auto-Restart",
                        f"Project '{proj['project_name']}' was auto-restarted. Status: {'success' if success else 'failed'}",
                        "warning",
                    )

    except Exception as e:
        logger.error(f"Health check error: {e}")


async def cleanup_job(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Periodic cleanup job."""
    try:
        db.cleanup_old_logs(days=7)

        # Clean temp directory
        for item in TEMP_DIR.iterdir():
            try:
                age = time.time() - item.stat().st_mtime
                if age > 3600:  # 1 hour
                    if item.is_file():
                        item.unlink()
                    elif item.is_dir():
                        shutil.rmtree(str(item))
            except Exception:
                pass

        logger.info("Cleanup job completed")
    except Exception as e:
        logger.error(f"Cleanup job error: {e}")


# ┌─────────────────────────────────────────────────────────────────────────────┐
# │             SECTION 25: BOT STARTUP & SHUTDOWN                              │
# └─────────────────────────────────────────────────────────────────────────────┘

async def post_init(application: Application) -> None:
    """Run after bot initialization."""
    logger.info(f"{'=' * 50}")
    logger.info(f"  {BOT_NAME} v{BOT_VERSION} Starting...")
    logger.info(f"  Owner: {OWNER_USERNAME} (ID: {OWNER_ID})")
    logger.info(f"  Build: {BOT_BUILD}")
    logger.info(f"  Database: {DATABASE_PATH}")
    logger.info(f"  Projects Dir: {PROJECTS_DIR}")
    logger.info(f"{'=' * 50}")

    # Set bot commands
    commands = [
        BotCommand("start", "🏠 Open Main Menu"),
        BotCommand("help", "ℹ️ Help & Commands"),
        BotCommand("deploy", "🚀 Deploy Console"),
        BotCommand("logs", "📋 View Live Logs"),
        BotCommand("files", "📁 File Manager"),
        BotCommand("health", "📊 System Health"),
        BotCommand("status", "📊 Project Status"),
        BotCommand("upload", "📤 Upload Instructions"),
        BotCommand("stats", "📈 Bot Statistics"),
    ]
    await application.bot.set_my_commands(commands)

    # Schedule periodic jobs
    job_queue = application.job_queue
    if job_queue:
        job_queue.run_repeating(
            health_check_job,
            interval=HEALTH_CHECK_INTERVAL,
            first=10,
            name="health_check",
        )
        job_queue.run_repeating(
            cleanup_job,
            interval=3600,  # Every hour
            first=300,
            name="cleanup",
        )

    # Restore running processes from DB (mark as crashed if we can't find them)
    running = db.get_running_projects()
    for proj in running:
        if proj["pid"]:
            try:
                os.kill(proj["pid"], 0)  # Check if process exists
            except (OSError, ProcessLookupError):
                db.update_project(
                    proj["project_id"],
                    status="crashed",
                    pid=None,
                    last_stopped=datetime.now().isoformat(),
                )
                logger.info(
                    f"Marked stale project as crashed: {proj['project_name']}"
                )


async def post_shutdown(application: Application) -> None:
    """Run before bot shutdown."""
    logger.info("Shutting down... Stopping all processes.")
    await process_manager.stop_all()
    db.close()
    logger.info(f"{BOT_NAME} shut down gracefully.")


# ┌─────────────────────────────────────────────────────────────────────────────┐
# │             SECTION 26: APPLICATION BUILDER & MAIN                          │
# └─────────────────────────────────────────────────────────────────────────────┘

def build_application() -> Application:
    """Build and configure the Telegram bot application."""

    application = (
        ApplicationBuilder()
        .token(BOT_TOKEN)
        .post_init(post_init)
        .post_shutdown(post_shutdown)
        .concurrent_updates(True)
        .read_timeout(30)
        .write_timeout(30)
        .connect_timeout(30)
        .build()
    )

    # ── Command Handlers ──
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("health", health_command))
    application.add_handler(CommandHandler("status", status_command))
    application.add_handler(CommandHandler("deploy", deploy_command))
    application.add_handler(CommandHandler("logs", logs_command))
    application.add_handler(CommandHandler("files", files_command))
    application.add_handler(CommandHandler("upload", upload_command))
    application.add_handler(CommandHandler("admin", admin_command))
    application.add_handler(CommandHandler("adduser", adduser_command))
    application.add_handler(CommandHandler("ban", ban_command))
    application.add_handler(CommandHandler("stats", stats_command))
    application.add_handler(CommandHandler("setenv", setenv_command))
    application.add_handler(CommandHandler("setmain", setmain_command))

    # ── Callback Query Handler ──
    application.add_handler(CallbackQueryHandler(callback_router))

    # ── Document Upload Handler ──
    application.add_handler(
        MessageHandler(filters.Document.ALL, handle_document_upload)
    )

    # ── Error Handler ──
    application.add_error_handler(error_handler)

    return application


def main():
    """Main entry point."""
    print(
        r"""
 ═══════════════════════════════════════════════════════════════════════════════
 ██████╗ ██╗   ██╗██╗  ██╗██╗    ██╗  ██╗    ██╗  ██╗ ██████╗ ███████╗████████╗
 ██╔══██╗██║   ██║██║  ██║██║    ╚██╗██╔╝    ██║  ██║██╔═══██╗██╔════╝╚══██╔══╝
 ██████╔╝██║   ██║███████║██║     ╚███╔╝     ███████║██║   ██║███████╗   ██║
 ██╔══██╗██║   ██║██╔══██║██║     ██╔██╗     ██╔══██║██║   ██║╚════██║   ██║
 ██║  ██║╚██████╔╝██║  ██║██║    ██╔╝ ██╗    ██║  ██║╚██████╔╝███████║   ██║
 ╚═╝  ╚═╝ ╚═════╝ ╚═╝  ╚═╝╚═╝    ╚═╝  ╚═╝    ╚═╝  ╚═╝ ╚═════╝ ╚══════╝   ╚═╝
 ═══════════════════════════════════════════════════════════════════════════════
        """
    )
    print(f"  {BOT_NAME} v{BOT_VERSION} ({BOT_BUILD})")
    print(f"  Owner: {OWNER_USERNAME}")
    print(f"  Starting bot...\n")

    if BOT_TOKEN == "YOUR_BOT_TOKEN_HERE":
        print("  ❌ ERROR: Please set your BOT_TOKEN in the script!")
        print("  Edit the BOT_TOKEN variable at the top of this file.")
        sys.exit(1)

    if OWNER_ID == 123456789:
        print("  ⚠️  WARNING: Please set your OWNER_ID in the script!")
        print("  Edit the OWNER_ID variable at the top of this file.")

    app = build_application()
    app.run_polling(
        allowed_updates=Update.ALL_TYPES,
        drop_pending_updates=True,
        close_loop=False,
    )


if __name__ == "__main__":
    main()
 
# ┌─────────────────────────────────────────────────────────────────────────────┐
# │         SECTION 27: ADVANCED PROCESS WATCHDOG & AUTO-RECOVERY               │
# └─────────────────────────────────────────────────────────────────────────────┘

class ProcessWatchdog:
    """
    Advanced process watchdog that monitors running processes,
    detects crashes, OOM kills, and handles auto-recovery with
    exponential backoff and configurable restart policies.
    """

    def __init__(self, process_mgr: ProcessManager, database: DatabaseManager):
        self._pm = process_mgr
        self._db = database
        self._restart_backoff: Dict[str, float] = {}
        self._crash_history: Dict[str, deque] = defaultdict(lambda: deque(maxlen=20))
        self._monitoring = False
        self._monitor_task: Optional[asyncio.Task] = None
        self._alert_callbacks: List[Callable] = []
        self._health_thresholds = {
            "cpu_warning": 80.0,
            "cpu_critical": 95.0,
            "ram_warning": 80.0,
            "ram_critical": 95.0,
            "disk_warning": 85.0,
            "disk_critical": 95.0,
            "process_mem_limit": 512 * 1024 * 1024,  # 512MB per process
            "max_crash_rate": 5,  # max crashes per 10 minutes
            "crash_window": 600,  # 10 minutes in seconds
        }

    def register_alert_callback(self, callback: Callable):
        """Register a callback for alert notifications."""
        self._alert_callbacks.append(callback)

    async def _send_alert(self, user_id: int, title: str, message: str, alert_type: str = "warning"):
        """Send alert to user via registered callbacks."""
        self._db.add_notification(user_id, title, message, alert_type)
        for callback in self._alert_callbacks:
            try:
                await callback(user_id, title, message, alert_type)
            except Exception as e:
                logger.error(f"Alert callback error: {e}")

    def _get_backoff_delay(self, project_id: str) -> float:
        """Calculate exponential backoff delay for restart."""
        current = self._restart_backoff.get(project_id, 1.0)
        # Exponential backoff: 1s, 2s, 4s, 8s, 16s, 32s, max 60s
        return min(current, 60.0)

    def _increase_backoff(self, project_id: str):
        """Increase backoff delay after a failed restart."""
        current = self._restart_backoff.get(project_id, 1.0)
        self._restart_backoff[project_id] = min(current * 2, 60.0)

    def _reset_backoff(self, project_id: str):
        """Reset backoff delay after successful restart."""
        self._restart_backoff[project_id] = 1.0

    def _is_crash_rate_exceeded(self, project_id: str) -> bool:
        """Check if crash rate exceeds threshold."""
        history = self._crash_history[project_id]
        now = time.time()
        window = self._health_thresholds["crash_window"]
        recent_crashes = sum(1 for t in history if now - t < window)
        return recent_crashes >= self._health_thresholds["max_crash_rate"]

    async def check_process_health(self, project_id: str) -> Dict[str, Any]:
        """Perform detailed health check on a specific process."""
        result = {
            "project_id": project_id,
            "is_running": False,
            "health": "unknown",
            "cpu_percent": 0.0,
            "memory_bytes": 0,
            "memory_percent": 0.0,
            "open_files": 0,
            "threads": 0,
            "uptime": 0.0,
            "warnings": [],
            "errors": [],
        }

        proc_info = self._pm.get_process(project_id)
        if not proc_info or not proc_info.is_running:
            result["health"] = "stopped"
            return result

        result["is_running"] = True
        result["uptime"] = proc_info.uptime

        try:
            ps_proc = psutil.Process(proc_info.pid)

            # CPU usage
            cpu = ps_proc.cpu_percent(interval=0.3)
            result["cpu_percent"] = cpu

            # Memory usage
            mem_info = ps_proc.memory_info()
            result["memory_bytes"] = mem_info.rss
            total_mem = psutil.virtual_memory().total
            result["memory_percent"] = (mem_info.rss / total_mem) * 100 if total_mem > 0 else 0

            # Open files & threads
            try:
                result["open_files"] = len(ps_proc.open_files())
            except (psutil.AccessDenied, psutil.NoSuchProcess):
                result["open_files"] = -1

            try:
                result["threads"] = ps_proc.num_threads()
            except (psutil.AccessDenied, psutil.NoSuchProcess):
                result["threads"] = -1

            # Health assessment
            if cpu > self._health_thresholds["cpu_critical"]:
                result["warnings"].append(f"CPU critical: {cpu:.1f}%")
                result["health"] = "critical"
            elif cpu > self._health_thresholds["cpu_warning"]:
                result["warnings"].append(f"CPU high: {cpu:.1f}%")
                if result["health"] != "critical":
                    result["health"] = "warning"

            if mem_info.rss > self._health_thresholds["process_mem_limit"]:
                result["warnings"].append(
                    f"Memory high: {UI.format_bytes(mem_info.rss)}"
                )
                if result["health"] != "critical":
                    result["health"] = "warning"

            if not result["warnings"]:
                result["health"] = "healthy"

        except psutil.NoSuchProcess:
            result["is_running"] = False
            result["health"] = "crashed"
            result["errors"].append("Process no longer exists")
        except psutil.AccessDenied:
            result["health"] = "unknown"
            result["errors"].append("Access denied to process info")
        except Exception as e:
            result["errors"].append(f"Health check error: {str(e)}")

        return result

    async def monitor_cycle(self):
        """Single monitoring cycle - check all running processes."""
        running = self._pm.get_all_running()
        all_projects = self._db.get_all_projects()

        for proj in all_projects:
            project_id = proj["project_id"]
            is_actually_running = project_id in running and running[project_id].is_running
            db_status = proj["status"]

            # Case 1: DB says running but process is dead
            if db_status == "running" and not is_actually_running:
                logger.warning(f"Watchdog: {proj['project_name']} crashed (DB=running, actual=dead)")

                self._crash_history[project_id].append(time.time())

                self._db.update_project(
                    project_id,
                    status="crashed",
                    pid=None,
                    last_stopped=datetime.now().isoformat(),
                )
                self._db.execute(
                    "UPDATE projects SET error_count = error_count + 1 WHERE project_id = ?",
                    (project_id,),
                )

                # Check auto-restart policy
                if proj["auto_restart"]:
                    if self._is_crash_rate_exceeded(project_id):
                        logger.error(
                            f"Watchdog: {proj['project_name']} crash rate exceeded, "
                            f"disabling auto-restart"
                        )
                        self._db.update_project(project_id, auto_restart=0)
                        await self._send_alert(
                            proj["user_id"],
                            "⚠️ Auto-Restart Disabled",
                            f"Project '{proj['project_name']}' has crashed too many times. "
                            f"Auto-restart has been disabled.",
                            "error",
                        )
                    elif proj["restart_count"] < proj["max_restarts"]:
                        delay = self._get_backoff_delay(project_id)
                        logger.info(
                            f"Watchdog: Auto-restarting {proj['project_name']} "
                            f"in {delay:.1f}s (attempt {proj['restart_count'] + 1}/{proj['max_restarts']})"
                        )

                        await asyncio.sleep(delay)

                        env_vars = json.loads(proj["env_vars"] or "{}")
                        success, msg = await self._pm.start_process(
                            project_id,
                            proj["project_type"],
                            proj["main_file"],
                            proj["directory"],
                            env_vars if env_vars else None,
                        )

                        if success:
                            self._reset_backoff(project_id)
                            await self._send_alert(
                                proj["user_id"],
                                "🔄 Auto-Restarted",
                                f"Project '{proj['project_name']}' was automatically restarted.",
                                "info",
                            )
                        else:
                            self._increase_backoff(project_id)
                            await self._send_alert(
                                proj["user_id"],
                                "❌ Auto-Restart Failed",
                                f"Failed to restart '{proj['project_name']}': {msg}",
                                "error",
                            )

                        self._db.log_deployment(
                            project_id,
                            proj["user_id"],
                            "watchdog_restart",
                            "success" if success else "failed",
                            msg,
                        )
                    else:
                        await self._send_alert(
                            proj["user_id"],
                            "⛔ Max Restarts Reached",
                            f"Project '{proj['project_name']}' has reached maximum restart attempts "
                            f"({proj['max_restarts']}). Manual intervention required.",
                            "error",
                        )
                else:
                    await self._send_alert(
                        proj["user_id"],
                        "💀 Process Crashed",
                        f"Project '{proj['project_name']}' has crashed. "
                        f"Auto-restart is disabled.",
                        "error",
                    )

            # Case 2: Running process exceeding resource limits
            elif is_actually_running:
                health = await self.check_process_health(project_id)
                if health["health"] == "critical":
                    for warning in health["warnings"]:
                        await self._send_alert(
                            proj["user_id"],
                            "🔴 Resource Critical",
                            f"Project '{proj['project_name']}': {warning}",
                            "warning",
                        )

    async def start_monitoring(self):
        """Start the watchdog monitoring loop."""
        if self._monitoring:
            return
        self._monitoring = True
        self._monitor_task = asyncio.create_task(self._monitor_loop())
        logger.info("Process Watchdog started")

    async def _monitor_loop(self):
        """Main monitoring loop."""
        while self._monitoring:
            try:
                await self.monitor_cycle()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Watchdog error: {e}\n{traceback.format_exc()}")
            await asyncio.sleep(HEALTH_CHECK_INTERVAL)

    async def stop_monitoring(self):
        """Stop the watchdog."""
        self._monitoring = False
        if self._monitor_task:
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass
        logger.info("Process Watchdog stopped")

    def get_crash_stats(self, project_id: str) -> Dict[str, Any]:
        """Get crash statistics for a project."""
        history = self._crash_history[project_id]
        now = time.time()
        window = self._health_thresholds["crash_window"]

        return {
            "total_crashes": len(history),
            "recent_crashes": sum(1 for t in history if now - t < window),
            "last_crash": max(history) if history else None,
            "crash_rate_exceeded": self._is_crash_rate_exceeded(project_id),
            "current_backoff": self._restart_backoff.get(project_id, 1.0),
        }


# ── Global Watchdog Instance ──
watchdog = ProcessWatchdog(process_manager, db)


# ┌─────────────────────────────────────────────────────────────────────────────┐
# │         SECTION 28: ADVANCED FILE OPERATIONS & BACKUP SYSTEM                │
# └─────────────────────────────────────────────────────────────────────────────┘

class BackupManager:
    """
    Handles project backups with compression, rotation, and restore.
    """

    def __init__(self, backup_dir: Path = BACKUPS_DIR, max_backups: int = 5):
        self._backup_dir = backup_dir
        self._max_backups = max_backups
        self._backup_dir.mkdir(parents=True, exist_ok=True)

    def create_backup(
        self, project_id: str, project_name: str, project_dir: str
    ) -> Tuple[bool, str, Optional[Path]]:
        """Create a ZIP backup of a project."""
        try:
            source = Path(project_dir)
            if not source.exists():
                return False, "Project directory not found", None

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            safe_name = re.sub(r'[^\w\-]', '_', project_name)
            backup_name = f"{safe_name}_{timestamp}.zip"
            backup_path = self._backup_dir / project_id
            backup_path.mkdir(parents=True, exist_ok=True)
            full_path = backup_path / backup_name

            with zipfile.ZipFile(str(full_path), 'w', zipfile.ZIP_DEFLATED) as zf:
                for file_path in source.rglob("*"):
                    if file_path.is_file():
                        arcname = file_path.relative_to(source)
                        # Skip certain files
                        skip_patterns = {
                            "__pycache__", ".git", "node_modules", ".env",
                            ".venv", "venv", ".pyc", ".pyo",
                        }
                        if any(part in skip_patterns for part in arcname.parts):
                            continue
                        zf.write(str(file_path), str(arcname))

            # Rotate old backups
            self._rotate_backups(backup_path)

            size = full_path.stat().st_size
            return True, f"Backup created: {backup_name} ({UI.format_bytes(size)})", full_path

        except Exception as e:
            logger.error(f"Backup creation failed: {e}")
            return False, f"Backup failed: {str(e)}", None

    def _rotate_backups(self, backup_dir: Path):
        """Remove old backups beyond the retention limit."""
        backups = sorted(
            [f for f in backup_dir.iterdir() if f.is_file() and f.suffix == ".zip"],
            key=lambda f: f.stat().st_mtime,
            reverse=True,
        )
        for old_backup in backups[self._max_backups:]:
            old_backup.unlink()
            logger.info(f"Rotated old backup: {old_backup.name}")

    def list_backups(self, project_id: str) -> List[Dict[str, Any]]:
        """List all backups for a project."""
        backup_dir = self._backup_dir / project_id
        if not backup_dir.exists():
            return []

        backups = []
        for f in sorted(backup_dir.iterdir(), key=lambda x: x.stat().st_mtime, reverse=True):
            if f.is_file() and f.suffix == ".zip":
                stat_info = f.stat()
                backups.append({
                    "name": f.name,
                    "path": str(f),
                    "size": stat_info.st_size,
                    "created": datetime.fromtimestamp(stat_info.st_mtime).strftime(
                        "%Y-%m-%d %H:%M:%S"
                    ),
                })
        return backups

    def restore_backup(
        self, backup_path: str, restore_to: str
    ) -> Tuple[bool, str]:
        """Restore a project from backup."""
        try:
            bp = Path(backup_path)
            rt = Path(restore_to)

            if not bp.exists():
                return False, "Backup file not found"

            # Clear target directory
            if rt.exists():
                shutil.rmtree(str(rt))
            rt.mkdir(parents=True, exist_ok=True)

            success, msg, count = FileManager.extract_archive(bp, rt)
            if success:
                return True, f"Restored {count} files from backup"
            return False, msg

        except Exception as e:
            return False, f"Restore failed: {str(e)}"

    def get_total_backup_size(self) -> int:
        """Get total size of all backups."""
        total = 0
        for f in self._backup_dir.rglob("*"):
            if f.is_file():
                total += f.stat().st_size
        return total

    def delete_backup(self, backup_path: str) -> Tuple[bool, str]:
        """Delete a specific backup."""
        try:
            bp = Path(backup_path)
            if bp.exists() and bp.is_file():
                bp.unlink()
                return True, "Backup deleted"
            return False, "Backup not found"
        except Exception as e:
            return False, f"Delete failed: {str(e)}"

    def delete_all_backups(self, project_id: str) -> Tuple[bool, str]:
        """Delete all backups for a project."""
        try:
            backup_dir = self._backup_dir / project_id
            if backup_dir.exists():
                shutil.rmtree(str(backup_dir))
                return True, "All backups deleted"
            return False, "No backups found"
        except Exception as e:
            return False, f"Delete failed: {str(e)}"


# ── Global Backup Manager ──
backup_manager = BackupManager()


class AdvancedFileEditor:
    """
    In-chat file editing capabilities for small text files.
    Supports viewing, editing (via message), and saving.
    """

    # Track active edit sessions: user_id -> session data
    _edit_sessions: Dict[int, Dict[str, Any]] = {}

    @classmethod
    def start_edit_session(
        cls, user_id: int, project_id: str, file_rel: str, file_path: str
    ) -> str:
        """Start an edit session and return session ID."""
        session_id = uuid.uuid4().hex[:8]
        cls._edit_sessions[user_id] = {
            "session_id": session_id,
            "project_id": project_id,
            "file_rel": file_rel,
            "file_path": file_path,
            "started_at": time.time(),
        }
        return session_id

    @classmethod
    def get_session(cls, user_id: int) -> Optional[Dict[str, Any]]:
        """Get active edit session for user."""
        session = cls._edit_sessions.get(user_id)
        if session:
            # Check timeout (30 minutes)
            if time.time() - session["started_at"] > 1800:
                del cls._edit_sessions[user_id]
                return None
        return session

    @classmethod
    def end_session(cls, user_id: int):
        """End an edit session."""
        cls._edit_sessions.pop(user_id, None)

    @classmethod
    def save_file(cls, user_id: int, content: str) -> Tuple[bool, str]:
        """Save edited content to file."""
        session = cls.get_session(user_id)
        if not session:
            return False, "No active edit session"

        try:
            file_path = Path(session["file_path"])
            # Create backup before editing
            backup_path = file_path.with_suffix(file_path.suffix + ".bak")
            if file_path.exists():
                shutil.copy2(str(file_path), str(backup_path))

            file_path.write_text(content, encoding="utf-8")
            cls.end_session(user_id)
            return True, f"File saved: {file_path.name}"

        except Exception as e:
            return False, f"Save failed: {str(e)}"


# ┌─────────────────────────────────────────────────────────────────────────────┐
# │         SECTION 29: DEPENDENCY MANAGER                                      │
# └─────────────────────────────────────────────────────────────────────────────┘

class DependencyManager:
    """
    Manages project dependencies: detect, install, and track
    requirements for Python (pip), Node.js (npm), and Java (maven).
    """

    @staticmethod
    def detect_dependencies(project_dir: str, project_type: str) -> Dict[str, Any]:
        """Detect dependency files in a project."""
        d = Path(project_dir)
        result = {
            "has_deps": False,
            "dep_file": None,
            "dep_type": None,
            "dependencies": [],
        }

        if project_type == "python":
            req_file = d / "requirements.txt"
            if req_file.exists():
                result["has_deps"] = True
                result["dep_file"] = "requirements.txt"
                result["dep_type"] = "pip"
                try:
                    deps = [
                        line.strip()
                        for line in req_file.read_text().splitlines()
                        if line.strip() and not line.strip().startswith("#")
                    ]
                    result["dependencies"] = deps
                except Exception:
                    pass

            # Also check Pipfile, pyproject.toml
            if (d / "Pipfile").exists():
                result["has_deps"] = True
                result["dep_file"] = result.get("dep_file") or "Pipfile"
                result["dep_type"] = result.get("dep_type") or "pipenv"

            if (d / "pyproject.toml").exists():
                result["has_deps"] = True
                if not result["dep_file"]:
                    result["dep_file"] = "pyproject.toml"
                    result["dep_type"] = "pip"

        elif project_type == "nodejs":
            pkg_file = d / "package.json"
            if pkg_file.exists():
                result["has_deps"] = True
                result["dep_file"] = "package.json"
                result["dep_type"] = "npm"
                try:
                    pkg = json.loads(pkg_file.read_text())
                    deps = list(pkg.get("dependencies", {}).keys())
                    dev_deps = list(pkg.get("devDependencies", {}).keys())
                    result["dependencies"] = deps
                    result["dev_dependencies"] = dev_deps
                except Exception:
                    pass

            # Check for yarn.lock
            if (d / "yarn.lock").exists():
                result["dep_type"] = "yarn"

        elif project_type == "java":
            if (d / "pom.xml").exists():
                result["has_deps"] = True
                result["dep_file"] = "pom.xml"
                result["dep_type"] = "maven"
            elif (d / "build.gradle").exists():
                result["has_deps"] = True
                result["dep_file"] = "build.gradle"
                result["dep_type"] = "gradle"

        return result

    @staticmethod
    async def install_dependencies(
        project_dir: str, project_type: str, dep_type: str = None
    ) -> Tuple[bool, str, str]:
        """
        Install project dependencies.
        Returns (success, output, error_output).
        """
        d = Path(project_dir)
        cmd = None

        if project_type == "python":
            req_file = d / "requirements.txt"
            if req_file.exists():
                cmd = [
                    sys.executable, "-m", "pip", "install",
                    "-r", "requirements.txt",
                    "--target", str(d / ".deps"),
                    "--quiet",
                ]
            else:
                return False, "", "No requirements.txt found"

        elif project_type == "nodejs":
            if dep_type == "yarn":
                cmd = ["yarn", "install", "--production"]
            else:
                cmd = ["npm", "install", "--production"]

        elif project_type == "java":
            if dep_type == "maven":
                cmd = ["mvn", "install", "-q"]
            elif dep_type == "gradle":
                cmd = ["gradle", "build", "-q"]
            else:
                return False, "", "Unknown Java build system"

        if not cmd:
            return False, "", "Could not determine install command"

        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                cwd=str(d),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            stdout, stderr = await asyncio.wait_for(
                process.communicate(), timeout=300
            )

            stdout_text = stdout.decode("utf-8", errors="replace")
            stderr_text = stderr.decode("utf-8", errors="replace")

            if process.returncode == 0:
                return True, stdout_text, stderr_text
            else:
                return False, stdout_text, stderr_text

        except asyncio.TimeoutError:
            return False, "", "Installation timed out (5 minutes)"
        except FileNotFoundError as e:
            return False, "", f"Command not found: {str(e)}"
        except Exception as e:
            return False, "", f"Installation error: {str(e)}"


# ── Global Dependency Manager ──
dep_manager = DependencyManager()


# ┌─────────────────────────────────────────────────────────────────────────────┐
# │         SECTION 30: PORT MANAGER                                            │
# └─────────────────────────────────────────────────────────────────────────────┘

class PortManager:
    """Manages port allocation for web-based projects."""

    _allocated_ports: Dict[str, int] = {}
    _port_range = (8000, 9000)
    _lock = threading.Lock()

    @classmethod
    def allocate_port(cls, project_id: str) -> int:
        """Allocate a free port for a project."""
        with cls._lock:
            if project_id in cls._allocated_ports:
                return cls._allocated_ports[project_id]

            for port in range(cls._port_range[0], cls._port_range[1]):
                if port not in cls._allocated_ports.values():
                    if cls._is_port_free(port):
                        cls._allocated_ports[project_id] = port
                        return port

            raise RuntimeError("No free ports available")

    @classmethod
    def release_port(cls, project_id: str):
        """Release a port allocation."""
        with cls._lock:
            cls._allocated_ports.pop(project_id, None)

    @classmethod
    def get_port(cls, project_id: str) -> Optional[int]:
        """Get allocated port for a project."""
        return cls._allocated_ports.get(project_id)

    @staticmethod
    def _is_port_free(port: int) -> bool:
        """Check if a port is free."""
        import socket
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(("127.0.0.1", port))
                return True
            except OSError:
                return False

    @classmethod
    def get_all_allocations(cls) -> Dict[str, int]:
        """Get all port allocations."""
        return dict(cls._allocated_ports)


# ┌─────────────────────────────────────────────────────────────────────────────┐
# │         SECTION 31: ADVANCED DEPLOY HANDLERS (Backup, Deps, Ports)          │
# └─────────────────────────────────────────────────────────────────────────────┘

async def handle_advanced_deploy_action(
    update: Update, context: ContextTypes.DEFAULT_TYPE, data: str
) -> None:
    """Handle advanced deploy-related callbacks."""
    query = update.callback_query
    user = update.effective_user

    if data.startswith("adv_backup_create_"):
        project_id = data.replace("adv_backup_create_", "")
        project = db.get_project(project_id)
        if not project:
            await query.answer("❌ Project not found!", show_alert=True)
            return

        await query.edit_message_text(
            f"{Emoji.LOADING} {Fonts.small_caps('creating backup...')}\n"
            f"{UI.BULLET} {project['project_name']}\n{UI.DIVIDER_THIN}"
        )

        success, msg, backup_path = backup_manager.create_backup(
            project_id, project["project_name"], project["directory"]
        )

        status_icon = Emoji.SUCCESS if success else Emoji.ERROR
        text = (
            f"{status_icon} {Fonts.bold('BACKUP RESULT')}\n"
            f"{UI.DIVIDER_THIN}\n\n"
            f"{UI.BULLET} {msg}\n\n"
            f"{UI.DIVIDER_THIN}"
        )

        if success:
            db.log_file_operation(
                user.id, "backup", str(backup_path), project_id,
                backup_path.stat().st_size if backup_path else 0, "success",
            )

        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton(
                    f"{Emoji.FOLDER} ᴠɪᴇᴡ ʙᴀᴄᴋᴜᴘs",
                    callback_data=f"adv_backup_list_{project_id}",
                ),
            ],
            [
                InlineKeyboardButton(
                    f"{Emoji.BACK} ʙᴀᴄᴋ",
                    callback_data=f"deploy_select_{project_id}",
                ),
            ],
        ])

        try:
            await query.edit_message_text(text, reply_markup=keyboard)
        except BadRequest:
            pass

    elif data.startswith("adv_backup_list_"):
        project_id = data.replace("adv_backup_list_", "")
        project = db.get_project(project_id)
        if not project:
            await query.answer("❌ Project not found!", show_alert=True)
            return

        backups = backup_manager.list_backups(project_id)

        text = (
            f"{Emoji.FOLDER} {Fonts.bold('BACKUPS')} {Emoji.FOLDER}\n"
            f"{UI.DIVIDER_STAR}\n"
            f"{UI.BULLET} {Fonts.small_caps('project')}: {project['project_name']}\n\n"
            f"{UI.DIVIDER_THIN}\n\n"
        )

        buttons = []

        if not backups:
            text += f"{Emoji.INFO} {Fonts.small_caps('no backups found.')}\n\n"
        else:
            for i, bk in enumerate(backups, 1):
                text += (
                    f"  {Emoji.ZIP} {Fonts.bold(f'{i}.')} {bk['name']}\n"
                    f"    {UI.TRIANGLE} {Fonts.small_caps('size')}: {UI.format_bytes(bk['size'])}\n"
                    f"    {UI.TRIANGLE} {Fonts.small_caps('created')}: {bk['created']}\n\n"
                )
                buttons.append([
                    InlineKeyboardButton(
                        f"{Emoji.DOWNLOAD} {bk['name'][:25]}",
                        callback_data=f"adv_backup_download_{project_id}:{i-1}",
                    ),
                    InlineKeyboardButton(
                        f"{Emoji.RESTART} ʀᴇsᴛᴏʀᴇ",
                        callback_data=f"adv_backup_restore_{project_id}:{i-1}",
                    ),
                ])

        text += f"{UI.DIVIDER_STAR}"

        buttons.append([
            InlineKeyboardButton(
                f"{Emoji.UPLOAD} ᴄʀᴇᴀᴛᴇ ɴᴇᴡ",
                callback_data=f"adv_backup_create_{project_id}",
            ),
        ])
        buttons.append([
            InlineKeyboardButton(
                f"{Emoji.BACK} ʙᴀᴄᴋ",
                callback_data=f"deploy_select_{project_id}",
            ),
        ])

        keyboard = InlineKeyboardMarkup(buttons)
        try:
            await query.edit_message_text(text, reply_markup=keyboard)
        except BadRequest:
            pass

    elif data.startswith("adv_backup_download_"):
        parts = data.replace("adv_backup_download_", "").split(":")
        project_id, idx = parts[0], int(parts[1])

        backups = backup_manager.list_backups(project_id)
        if idx >= len(backups):
            await query.answer("❌ Backup not found!", show_alert=True)
            return

        bk = backups[idx]
        bk_path = Path(bk["path"])

        if bk_path.stat().st_size > 50 * 1024 * 1024:
            await query.answer("❌ Backup too large for Telegram!", show_alert=True)
            return

        try:
            await query.answer("📥 Sending backup...")
            with open(bk_path, "rb") as f:
                await context.bot.send_document(
                    chat_id=update.effective_chat.id,
                    document=f,
                    filename=bk["name"],
                    caption=(
                        f"{Emoji.ZIP} {Fonts.small_caps('backup download')}\n"
                        f"{UI.BULLET} {bk['name']}\n"
                        f"{UI.BULLET} {UI.format_bytes(bk['size'])}"
                    ),
                )
        except Exception as e:
            await query.answer(f"❌ Download failed: {str(e)[:50]}", show_alert=True)

    elif data.startswith("adv_backup_restore_"):
        parts = data.replace("adv_backup_restore_", "").split(":")
        project_id, idx = parts[0], int(parts[1])

        project = db.get_project(project_id)
        backups = backup_manager.list_backups(project_id)

        if not project or idx >= len(backups):
            await query.answer("❌ Not found!", show_alert=True)
            return

        bk = backups[idx]

        text = (
            f"{Emoji.WARNING} {Fonts.bold('CONFIRM RESTORE')} {Emoji.WARNING}\n"
            f"{UI.DIVIDER_THIN}\n\n"
            f"{UI.BULLET} {Fonts.small_caps('backup')}: {bk['name']}\n"
            f"{UI.BULLET} {Fonts.small_caps('project')}: {project['project_name']}\n\n"
            f"{Emoji.ERROR} {Fonts.small_caps('current files will be replaced!')}\n\n"
            f"{UI.DIVIDER_THIN}"
        )

        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton(
                    f"{Emoji.RESTART} ʏᴇs, ʀᴇsᴛᴏʀᴇ",
                    callback_data=f"adv_backup_confirmrestore_{project_id}:{idx}",
                ),
                InlineKeyboardButton(
                    f"{Emoji.BACK} ᴄᴀɴᴄᴇʟ",
                    callback_data=f"adv_backup_list_{project_id}",
                ),
            ]
        ])
        try:
            await query.edit_message_text(text, reply_markup=keyboard)
        except BadRequest:
            pass

    elif data.startswith("adv_backup_confirmrestore_"):
        parts = data.replace("adv_backup_confirmrestore_", "").split(":")
        project_id, idx = parts[0], int(parts[1])

        project = db.get_project(project_id)
        backups = backup_manager.list_backups(project_id)

        if not project or idx >= len(backups):
            await query.answer("❌ Not found!", show_alert=True)
            return

        # Stop process if running
        if process_manager.is_running(project_id):
            await process_manager.stop_process(project_id, force=True)
            await asyncio.sleep(1)

        bk = backups[idx]
        success, msg = backup_manager.restore_backup(bk["path"], project["directory"])

        status_icon = Emoji.SUCCESS if success else Emoji.ERROR
        await query.answer(f"{'✅' if success else '❌'} {msg}", show_alert=True)

        # Re-detect project type
        if success:
            proj_type, main_file = file_manager.detect_project_type(Path(project["directory"]))
            if main_file:
                db.update_project(project_id, project_type=proj_type, main_file=main_file)

        update.callback_query.data = f"deploy_select_{project_id}"
        await handle_deploy_action(update, context, f"deploy_select_{project_id}")

    elif data.startswith("adv_deps_check_"):
        project_id = data.replace("adv_deps_check_", "")
        project = db.get_project(project_id)
        if not project:
            await query.answer("❌ Project not found!", show_alert=True)
            return

        deps = dep_manager.detect_dependencies(project["directory"], project["project_type"])

        text = (
            f"{Emoji.PACKAGE} {Fonts.bold('DEPENDENCIES')} {Emoji.PACKAGE}\n"
            f"{UI.DIVIDER_STAR}\n"
            f"{UI.BULLET} {Fonts.small_caps('project')}: {project['project_name']}\n"
            f"{UI.BULLET} {Fonts.small_caps('type')}: {project['project_type']}\n\n"
            f"{UI.DIVIDER_THIN}\n\n"
        )

        if deps["has_deps"]:
            text += (
                f"  {Emoji.FILE} {Fonts.small_caps('dep file')}: {deps['dep_file']}\n"
                f"  {Emoji.GEAR} {Fonts.small_caps('manager')}: {deps['dep_type']}\n\n"
            )

            if deps["dependencies"]:
                text += f"  {Fonts.small_caps('packages')} ({len(deps['dependencies'])}):\n"
                for dep in deps["dependencies"][:20]:
                    text += f"    {UI.TRIANGLE} {Fonts.mono(dep)}\n"
                if len(deps["dependencies"]) > 20:
                    text += f"    ... +{len(deps['dependencies']) - 20} {Fonts.small_caps('more')}\n"
                text += "\n"
        else:
            text += f"{Emoji.INFO} {Fonts.small_caps('no dependency file detected.')}\n\n"

        text += f"{UI.DIVIDER_STAR}"

        buttons = []
        if deps["has_deps"]:
            buttons.append([
                InlineKeyboardButton(
                    f"{Emoji.DOWNLOAD} ɪɴsᴛᴀʟʟ ᴅᴇᴘs",
                    callback_data=f"adv_deps_install_{project_id}",
                ),
            ])
        buttons.append([
            InlineKeyboardButton(
                f"{Emoji.BACK} ʙᴀᴄᴋ",
                callback_data=f"deploy_select_{project_id}",
            ),
        ])

        keyboard = InlineKeyboardMarkup(buttons)
        try:
            await query.edit_message_text(text, reply_markup=keyboard)
        except BadRequest:
            pass

    elif data.startswith("adv_deps_install_"):
        project_id = data.replace("adv_deps_install_", "")
        project = db.get_project(project_id)
        if not project:
            await query.answer("❌ Project not found!", show_alert=True)
            return

        deps = dep_manager.detect_dependencies(project["directory"], project["project_type"])

        await query.edit_message_text(
            f"{Emoji.LOADING} {Fonts.small_caps('installing dependencies...')}\n\n"
            f"{UI.BULLET} {Fonts.small_caps('this may take a few minutes')}\n"
            f"{UI.BULLET} {Fonts.small_caps('manager')}: {deps.get('dep_type', 'unknown')}\n\n"
            f"{UI.DIVIDER_THIN}"
        )

        success, stdout, stderr = await dep_manager.install_dependencies(
            project["directory"], project["project_type"], deps.get("dep_type"),
        )

        output = stdout[:1500] if stdout else ""
        errors = stderr[:500] if stderr else ""

        status_icon = Emoji.SUCCESS if success else Emoji.ERROR
        text = (
            f"{status_icon} {Fonts.bold('DEPENDENCY INSTALL RESULT')}\n"
            f"{UI.DIVIDER_THIN}\n\n"
            f"{UI.BULLET} {Fonts.small_caps('status')}: {'ᴄᴏᴍᴘʟᴇᴛᴇ' if success else 'ғᴀɪʟᴇᴅ'}\n\n"
        )

        if output:
            text += f"```\n{output[:1000]}\n```\n\n"
        if errors and not success:
            text += f"{Emoji.ERROR} {Fonts.small_caps('errors')}:\n```\n{errors[:500]}\n```\n\n"

        text += f"{UI.DIVIDER_THIN}"

        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton(
                    f"{Emoji.BACK} ʙᴀᴄᴋ",
                    callback_data=f"deploy_select_{project_id}",
                ),
            ]
        ])

        try:
            await query.edit_message_text(text, reply_markup=keyboard)
        except BadRequest:
            pass


# ┌─────────────────────────────────────────────────────────────────────────────┐
# │         SECTION 32: ENHANCED DEPLOY CONSOLE WITH ADVANCED OPTIONS           │
# └─────────────────────────────────────────────────────────────────────────────┘

# Patch the deploy_select handler to include advanced buttons
_original_handle_deploy_action = handle_deploy_action


async def enhanced_handle_deploy_action(
    update: Update, context: ContextTypes.DEFAULT_TYPE, data: str
) -> None:
    """Enhanced deploy action handler with backup, deps, watchdog options."""

    # Handle advanced actions
    if data.startswith("adv_"):
        await handle_advanced_deploy_action(update, context, data)
        return

    if data.startswith("deploy_select_"):
        project_id = data.replace("deploy_select_", "")
        project = db.get_project(project_id)

        if not project:
            query = update.callback_query
            await query.answer("❌ Project not found!", show_alert=True)
            return

        is_running = process_manager.is_running(project_id)
        status_icon = Emoji.ONLINE if is_running else Emoji.OFFLINE
        status_text = Fonts.small_caps("running") if is_running else Fonts.small_caps("stopped")

        proc = process_manager.get_process(project_id)
        extra_info = ""
        if proc and proc.is_running:
            health = await watchdog.check_process_health(project_id)
            health_icon = {
                "healthy": Emoji.ONLINE,
                "warning": Emoji.WARNING,
                "critical": Emoji.OFFLINE,
            }.get(health["health"], Emoji.INFO)

            extra_info = (
                f"\n\n{Emoji.CHART} {Fonts.small_caps('process health')}:\n"
                f"  {health_icon} {Fonts.small_caps('health')}: {health['health']}\n"
                f"  {Emoji.UPTIME} {Fonts.small_caps('uptime')}: {UI.format_uptime(proc.uptime)}\n"
                f"  {Emoji.RAM} {Fonts.small_caps('memory')}: {UI.format_bytes(health['memory_bytes'])}\n"
                f"  {Emoji.CPU} {Fonts.small_caps('cpu')}: {health['cpu_percent']:.1f}%\n"
                f"  {UI.TRIANGLE} {Fonts.small_caps('threads')}: {health['threads']}\n"
                f"  {UI.TRIANGLE} PID: {proc.pid}"
            )
            if health["warnings"]:
                extra_info += f"\n  {Emoji.WARNING} {', '.join(health['warnings'])}"

        # Crash stats
        crash_stats = watchdog.get_crash_stats(project_id)
        crash_info = ""
        if crash_stats["total_crashes"] > 0:
            crash_info = (
                f"\n\n{Emoji.BUG} {Fonts.small_caps('crash stats')}:\n"
                f"  {UI.TRIANGLE} {Fonts.small_caps('total crashes')}: {crash_stats['total_crashes']}\n"
                f"  {UI.TRIANGLE} {Fonts.small_caps('recent (10min)')}: {crash_stats['recent_crashes']}\n"
            )

        # Dependencies
        deps = dep_manager.detect_dependencies(project["directory"], project["project_type"])
        deps_info = ""
        if deps["has_deps"]:
            deps_info = (
                f"\n{Emoji.PACKAGE} {Fonts.small_caps('deps')}: "
                f"{deps['dep_file']} ({len(deps.get('dependencies', []))} packages)"
            )

        # Auto-restart status
        auto_restart_status = Emoji.ONLINE if project["auto_restart"] else Emoji.OFFLINE
        ar_text = "ᴏɴ" if project["auto_restart"] else "ᴏғғ"

        text = (
            f"{Emoji.DEPLOY} {Fonts.bold('DEPLOY CONSOLE')} {Emoji.DEPLOY}\n"
            f"{UI.DIVIDER_STAR}\n\n"
            f"{Emoji.DIAMOND} {Fonts.bold(project['project_name'])}\n\n"
            f"  {status_icon} {Fonts.small_caps('status')}: {status_text}\n"
            f"  {Emoji.CODE} {Fonts.small_caps('type')}: {project['project_type']}\n"
            f"  {Emoji.FILE} {Fonts.small_caps('main')}: {project['main_file'] or 'Not set'}\n"
            f"  {Emoji.STATS} {Fonts.small_caps('deploys')}: {project['deploy_count']}\n"
            f"  {Emoji.RESTART} {Fonts.small_caps('restarts')}: {project['restart_count']}\n"
            f"  {Emoji.ERROR} {Fonts.small_caps('errors')}: {project['error_count']}\n"
            f"  {Emoji.UPTIME} {Fonts.small_caps('runtime')}: {UI.format_uptime(project['total_runtime'])}\n"
            f"  {auto_restart_status} {Fonts.small_caps('auto-restart')}: {ar_text}"
            f"{deps_info}"
            f"{extra_info}"
            f"{crash_info}\n\n"
            f"{UI.DIVIDER_STAR}"
        )

        # Build comprehensive action buttons
        buttons = []

        # Row 1: Primary controls
        if is_running:
            buttons.append([
                InlineKeyboardButton(f"{Emoji.STOP} sᴛᴏᴘ", callback_data=f"deploy_stop_{project_id}"),
                InlineKeyboardButton(f"{Emoji.RESTART} ʀᴇsᴛᴀʀᴛ", callback_data=f"deploy_restart_{project_id}"),
                InlineKeyboardButton(f"💀 ᴋɪʟʟ", callback_data=f"deploy_forcekill_{project_id}"),
            ])
        else:
            buttons.append([
                InlineKeyboardButton(
                    f"{Emoji.DEPLOY} sᴛᴀʀᴛ / ᴅᴇᴘʟᴏʏ",
                    callback_data=f"deploy_start_{project_id}",
                ),
            ])

        # Row 2: Monitoring
        buttons.append([
            InlineKeyboardButton(f"{Emoji.LOG} ʟᴏɢs", callback_data=f"log_view_{project_id}"),
            InlineKeyboardButton(f"{Emoji.FOLDER} ғɪʟᴇs", callback_data=f"file_browse_{project_id}"),
        ])

        # Row 3: Advanced
        buttons.append([
            InlineKeyboardButton(f"{Emoji.ZIP} ʙᴀᴄᴋᴜᴘs", callback_data=f"adv_backup_list_{project_id}"),
            InlineKeyboardButton(f"{Emoji.PACKAGE} ᴅᴇᴘs", callback_data=f"adv_deps_check_{project_id}"),
        ])

        # Row 4: Settings
        ar_toggle_text = f"{Emoji.OFFLINE} ᴀᴜᴛᴏ-ʀᴇsᴛᴀʀᴛ" if project["auto_restart"] else f"{Emoji.ONLINE} ᴀᴜᴛᴏ-ʀᴇsᴛᴀʀᴛ"
        buttons.append([
            InlineKeyboardButton(ar_toggle_text, callback_data=f"deploy_toggle_ar_{project_id}"),
            InlineKeyboardButton(f"{Emoji.KEY} ᴇɴᴠ ᴠᴀʀs", callback_data=f"proj_env_{project_id}"),
        ])

        # Row 5: Edit & History
        buttons.append([
            InlineKeyboardButton(f"{Emoji.EDIT} ᴇᴅɪᴛ", callback_data=f"proj_edit_{project_id}"),
            InlineKeyboardButton(f"{Emoji.LOG} ʜɪsᴛᴏʀʏ", callback_data=f"deploy_history_{project_id}"),
        ])

        # Row 6: Danger zone
        buttons.append([
            InlineKeyboardButton(
                f"{Emoji.DELETE} ᴅᴇʟᴇᴛᴇ ᴘʀᴏᴊᴇᴄᴛ",
                callback_data=f"confirm_delete_proj_{project_id}",
            ),
        ])

        # Row 7: Navigation
        buttons.append([
            InlineKeyboardButton(f"{Emoji.BACK} ʙᴀᴄᴋ", callback_data="menu_deploy"),
            InlineKeyboardButton(f"{Emoji.REFRESH} ʀᴇғʀᴇsʜ", callback_data=f"deploy_select_{project_id}"),
        ])

        keyboard = InlineKeyboardMarkup(buttons)
        try:
            await update.callback_query.edit_message_text(text, reply_markup=keyboard)
        except BadRequest:
            pass

    elif data.startswith("deploy_toggle_ar_"):
        project_id = data.replace("deploy_toggle_ar_", "")
        project = db.get_project(project_id)
        if not project:
            await update.callback_query.answer("❌ Not found!", show_alert=True)
            return

        new_val = 0 if project["auto_restart"] else 1
        db.update_project(project_id, auto_restart=new_val)
        status = "enabled" if new_val else "disabled"
        await update.callback_query.answer(
            f"✅ Auto-restart {status}!", show_alert=True
        )
        # Refresh
        update.callback_query.data = f"deploy_select_{project_id}"
        await enhanced_handle_deploy_action(
            update, context, f"deploy_select_{project_id}"
        )

    else:
        # Delegate to original handler for start/stop/restart/etc.
        await _original_handle_deploy_action(update, context, data)


# Replace the deploy handler
handle_deploy_action = enhanced_handle_deploy_action


# ┌─────────────────────────────────────────────────────────────────────────────┐
# │         SECTION 33: LIVE LOG STREAMING VIA EDITS                            │
# └─────────────────────────────────────────────────────────────────────────────┘

class LiveLogStreamer:
    """
    Streams live logs to a Telegram message by periodically editing it.
    Supports multiple concurrent streams per user.
    """

    _active_streams: Dict[str, asyncio.Task] = {}
    _stream_messages: Dict[str, int] = {}  # stream_key -> message_id

    @classmethod
    def _stream_key(cls, chat_id: int, project_id: str) -> str:
        return f"{chat_id}:{project_id}"

    @classmethod
    async def start_stream(
        cls,
        bot,
        chat_id: int,
        message_id: int,
        project_id: str,
        project_name: str,
        interval: float = LOG_STREAM_INTERVAL,
    ):
        """Start streaming logs to a message."""
        key = cls._stream_key(chat_id, project_id)

        # Stop existing stream for this project/chat
        await cls.stop_stream(chat_id, project_id)

        cls._stream_messages[key] = message_id
        task = asyncio.create_task(
            cls._stream_loop(bot, chat_id, message_id, project_id, project_name, interval)
        )
        cls._active_streams[key] = task

    @classmethod
    async def stop_stream(cls, chat_id: int, project_id: str):
        """Stop a log stream."""
        key = cls._stream_key(chat_id, project_id)
        if key in cls._active_streams:
            cls._active_streams[key].cancel()
            try:
                await cls._active_streams[key]
            except asyncio.CancelledError:
                pass
            del cls._active_streams[key]
        cls._stream_messages.pop(key, None)

    @classmethod
    async def _stream_loop(
        cls, bot, chat_id: int, message_id: int,
        project_id: str, project_name: str, interval: float
    ):
        """Main streaming loop."""
        last_content = ""
        iteration = 0

        try:
            while True:
                iteration += 1
                is_running = process_manager.is_running(project_id)
                logs = process_manager.get_logs(project_id, lines=20)

                status_icon = Emoji.ONLINE if is_running else Emoji.OFFLINE
                status_text = "ʟɪᴠᴇ" if is_running else "sᴛᴏᴘᴘᴇᴅ"

                log_text = "\n".join(logs[-18:]) if logs else "No output yet..."
                if len(log_text) > 3200:
                    log_text = log_text[-3200:]

                spinner = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
                spin = spinner[iteration % len(spinner)] if is_running else "⏹"

                text = (
                    f"{spin} {Fonts.bold('LIVE LOGS')} - {Fonts.bold(project_name)}\n"
                    f"{UI.DIVIDER_THIN}\n"
                    f"{status_icon} {Fonts.small_caps(status_text)} | "
                    f"{Emoji.CLOCK} {datetime.now().strftime('%H:%M:%S')}\n\n"
                    f"```\n{log_text}\n```\n"
                    f"{UI.DIVIDER_THIN}\n"
                    f"{Fonts.small_caps('auto-refresh every')} {interval}s"
                )

                # Only edit if content changed
                if text != last_content:
                    try:
                        keyboard = InlineKeyboardMarkup([
                            [
                                InlineKeyboardButton(
                                    f"{Emoji.STOP} sᴛᴏᴘ sᴛʀᴇᴀᴍ",
                                    callback_data=f"log_stream_stop_{project_id}",
                                ),
                                InlineKeyboardButton(
                                    f"{Emoji.REFRESH} ʀᴇғʀᴇsʜ",
                                    callback_data=f"log_view_{project_id}",
                                ),
                            ],
                            [
                                InlineKeyboardButton(
                                    f"{Emoji.BACK} ʙᴀᴄᴋ",
                                    callback_data="menu_logs",
                                ),
                            ],
                        ])

                        await bot.edit_message_text(
                            chat_id=chat_id,
                            message_id=message_id,
                            text=text,
                            reply_markup=keyboard,
                        )
                        last_content = text
                    except BadRequest as e:
                        if "Message is not modified" in str(e):
                            pass
                        elif "Message to edit not found" in str(e):
                            logger.info(f"Stream message deleted, stopping stream for {project_id}")
                            break
                        else:
                            logger.warning(f"Stream edit error: {e}")
                    except (TimedOut, NetworkError):
                        pass
                    except RetryAfter as e:
                        await asyncio.sleep(e.retry_after + 1)
                    except Exception as e:
                        logger.error(f"Stream error: {e}")
                        break

                # Stop streaming if process is no longer running (after a few cycles)
                if not is_running and iteration > 5:
                    # Send final update
                    try:
                        final_text = text.replace(spin, "⏹").replace("ʟɪᴠᴇ", "ᴇɴᴅᴇᴅ")
                        await bot.edit_message_text(
                            chat_id=chat_id,
                            message_id=message_id,
                            text=final_text,
                            reply_markup=InlineKeyboardMarkup([
                                [
                                    InlineKeyboardButton(
                                        f"{Emoji.BACK} ʙᴀᴄᴋ ᴛᴏ ʟᴏɢs",
                                        callback_data="menu_logs",
                                    ),
                                ]
                            ]),
                        )
                    except Exception:
                        pass
                    break

                await asyncio.sleep(interval)

        except asyncio.CancelledError:
            pass
        finally:
            key = cls._stream_key(chat_id, project_id)
            cls._active_streams.pop(key, None)
            cls._stream_messages.pop(key, None)

    @classmethod
    def is_streaming(cls, chat_id: int, project_id: str) -> bool:
        key = cls._stream_key(chat_id, project_id)
        return key in cls._active_streams

    @classmethod
    async def stop_all_streams(cls):
        for key, task in list(cls._active_streams.items()):
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
        cls._active_streams.clear()
        cls._stream_messages.clear()


# ── Global Live Log Streamer ──
log_streamer = LiveLogStreamer()


# ┌─────────────────────────────────────────────────────────────────────────────┐
# │         SECTION 34: ENHANCED LOG HANDLERS WITH STREAMING                    │
# └─────────────────────────────────────────────────────────────────────────────┘

_original_handle_log_action = handle_log_action


async def enhanced_handle_log_action(
    update: Update, context: ContextTypes.DEFAULT_TYPE, data: str
) -> None:
    """Enhanced log handler with live streaming support."""
    query = update.callback_query

    if data.startswith("log_stream_start_"):
        project_id = data.replace("log_stream_start_", "")
        project = db.get_project(project_id)
        if not project:
            await query.answer("❌ Not found!", show_alert=True)
            return

        if not process_manager.is_running(project_id):
            await query.answer("⚠️ Process is not running!", show_alert=True)
            return

        # Start streaming on this message
        chat_id = update.effective_chat.id
        message_id = query.message.message_id

        await log_streamer.start_stream(
            context.bot, chat_id, message_id,
            project_id, project["project_name"],
        )
        await query.answer("📡 Live streaming started!")

    elif data.startswith("log_stream_stop_"):
        project_id = data.replace("log_stream_stop_", "")
        chat_id = update.effective_chat.id
        await log_streamer.stop_stream(chat_id, project_id)
        await query.answer("⏹ Stream stopped!")

        # Show static log view
        update.callback_query.data = f"log_view_{project_id}"
        await _original_handle_log_action(update, context, f"log_view_{project_id}")

    elif data.startswith("log_view_"):
        project_id = data.replace("log_view_", "")
        project = db.get_project(project_id)

        if not project:
            await query.answer("❌ Not found!", show_alert=True)
            return

        is_running = process_manager.is_running(project_id)
        logs = process_manager.get_logs(project_id, lines=30)

        status_icon = Emoji.ONLINE if is_running else Emoji.OFFLINE
        status_text = Fonts.small_caps("live") if is_running else Fonts.small_caps("history")

        text = (
            f"{Emoji.LOG} {Fonts.bold('LOGS')} - {Fonts.bold(project['project_name'])} {Emoji.LOG}\n"
            f"{UI.DIVIDER_STAR}\n"
            f"{status_icon} {Fonts.small_caps('status')}: {status_text}\n"
            f"{UI.BULLET} {Fonts.small_caps('showing last')} {len(logs)} {Fonts.small_caps('lines')}\n\n"
            f"{UI.DIVIDER_THIN}\n\n"
        )

        if logs:
            log_text = "\n".join(logs[-25:])
            if len(log_text) > 3000:
                log_text = log_text[-3000:]
                log_text = "... (truncated)\n" + log_text
            text += f"```\n{log_text}\n```\n\n"
        else:
            text += f"{Emoji.INFO} {Fonts.small_caps('no logs available yet.')}\n\n"

        text += (
            f"{UI.DIVIDER_STAR}\n"
            f"{Emoji.CLOCK} {Fonts.small_caps('updated')}: {datetime.now().strftime('%H:%M:%S')}"
        )

        buttons = [
            [
                InlineKeyboardButton(
                    f"{Emoji.REFRESH} ʀᴇғʀᴇsʜ",
                    callback_data=f"log_view_{project_id}",
                ),
            ],
        ]

        # Add streaming button if process is running
        if is_running:
            is_streaming = log_streamer.is_streaming(
                update.effective_chat.id, project_id
            )
            if is_streaming:
                buttons[0].insert(0, InlineKeyboardButton(
                    f"⏹ sᴛᴏᴘ sᴛʀᴇᴀᴍ",
                    callback_data=f"log_stream_stop_{project_id}",
                ))
            else:
                buttons[0].insert(0, InlineKeyboardButton(
                    f"📡 ʟɪᴠᴇ sᴛʀᴇᴀᴍ",
                    callback_data=f"log_stream_start_{project_id}",
                ))

        buttons.append([
            InlineKeyboardButton(
                f"{Emoji.DELETE} ᴄʟᴇᴀʀ",
                callback_data=f"log_clear_{project_id}",
            ),
            InlineKeyboardButton(
                f"{Emoji.DOWNLOAD} ᴇxᴘᴏʀᴛ",
                callback_data=f"log_export_{project_id}",
            ),
        ])
        buttons.append([
            InlineKeyboardButton(
                f"{Emoji.BACK} ʙᴀᴄᴋ",
                callback_data="menu_logs",
            ),
        ])

        keyboard = InlineKeyboardMarkup(buttons)
        try:
            await query.edit_message_text(text, reply_markup=keyboard)
        except BadRequest:
            pass

    else:
        # Delegate to original for clear/export
        await _original_handle_log_action(update, context, data)


# Replace the log handler
handle_log_action = enhanced_handle_log_action


# ┌─────────────────────────────────────────────────────────────────────────────┐
# │         SECTION 35: TERMINAL / SHELL COMMAND EXECUTOR                       │
# └─────────────────────────────────────────────────────────────────────────────┘

class TerminalSession:
    """
    Interactive terminal session for executing shell commands
    within a project directory context. Owner only.
    """

    _sessions: Dict[int, Dict[str, Any]] = {}

    @classmethod
    def start_session(cls, user_id: int, project_id: str, working_dir: str) -> str:
        """Start a terminal session."""
        session_id = uuid.uuid4().hex[:8]
        cls._sessions[user_id] = {
            "session_id": session_id,
            "project_id": project_id,
            "working_dir": working_dir,
            "history": deque(maxlen=50),
            "started_at": time.time(),
        }
        return session_id

    @classmethod
    def get_session(cls, user_id: int) -> Optional[Dict[str, Any]]:
        session = cls._sessions.get(user_id)
        if session and time.time() - session["started_at"] > SESSION_TIMEOUT:
            del cls._sessions[user_id]
            return None
        return session

    @classmethod
    def end_session(cls, user_id: int):
        cls._sessions.pop(user_id, None)

    @classmethod
    async def execute_command(
        cls, user_id: int, command: str, timeout: int = 30
    ) -> Tuple[bool, str, str]:
        """Execute a command in the session context."""
        session = cls.get_session(user_id)
        if not session:
            return False, "", "No active terminal session"

        # Security: block dangerous commands
        dangerous = {"rm -rf /", "mkfs", "dd if=", ":(){ :", "fork bomb", "> /dev/sd"}
        cmd_lower = command.lower().strip()
        for d in dangerous:
            if d in cmd_lower:
                return False, "", f"Blocked dangerous command: {command[:50]}"

        try:
            process = await asyncio.create_subprocess_shell(
                command,
                cwd=session["working_dir"],
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            stdout, stderr = await asyncio.wait_for(
                process.communicate(), timeout=timeout
            )

            stdout_text = stdout.decode("utf-8", errors="replace")
            stderr_text = stderr.decode("utf-8", errors="replace")

            # Store in history
            session["history"].append({
                "cmd": command,
                "stdout": stdout_text[:500],
                "stderr": stderr_text[:500],
                "exit_code": process.returncode,
                "time": datetime.now().strftime("%H:%M:%S"),
            })

            return process.returncode == 0, stdout_text, stderr_text

        except asyncio.TimeoutError:
            return False, "", f"Command timed out ({timeout}s)"
        except Exception as e:
            return False, "", str(e)


# ── Global Terminal ──
terminal = TerminalSession()


@owner_only
@authorized
async def terminal_command(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Handle /terminal <project_id> command."""
    args = context.args
    if not args:
        await update.message.reply_text(
            f"{Emoji.TERMINAL} {Fonts.small_caps('usage')}: /terminal <project_id>\n"
            f"{UI.BULLET} {Fonts.small_caps('starts an interactive terminal session')}"
        )
        return

    project_id = args[0]
    project = db.get_project(project_id)
    if not project:
        await update.message.reply_text(
            f"{Emoji.ERROR} {Fonts.small_caps('project not found!')}"
        )
        return

    session_id = terminal.start_session(
        update.effective_user.id, project_id, project["directory"]
    )

    text = (
        f"{Emoji.TERMINAL} {Fonts.bold('TERMINAL SESSION')} {Emoji.TERMINAL}\n"
        f"{UI.DIVIDER_STAR}\n\n"
        f"{UI.BULLET} {Fonts.small_caps('project')}: {project['project_name']}\n"
        f"{UI.BULLET} {Fonts.small_caps('dir')}: {Path(project['directory']).name}\n"
        f"{UI.BULLET} {Fonts.small_caps('session')}: {Fonts.mono(session_id)}\n\n"
        f"{UI.DIVIDER_THIN}\n\n"
        f"{Emoji.INFO} {Fonts.small_caps('send commands prefixed with')} $ \n"
        f"{UI.BULLET} {Fonts.small_caps('example')}: $ ls -la\n"
        f"{UI.BULLET} {Fonts.small_caps('example')}: $ python3 --version\n"
        f"{UI.BULLET} {Fonts.small_caps('type')} /endterm {Fonts.small_caps('to close')}\n\n"
        f"{UI.DIVIDER_STAR}"
    )

    await update.message.reply_text(text)


@owner_only
@authorized
async def endterm_command(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Handle /endterm - End terminal session."""
    terminal.end_session(update.effective_user.id)
    await update.message.reply_text(
        f"{Emoji.SUCCESS} {Fonts.small_caps('terminal session ended.')}"
    )


@authorized
async def handle_terminal_message(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Handle messages starting with $ as terminal commands."""
    message = update.message
    if not message or not message.text:
        return

    text = message.text.strip()
    if not text.startswith("$"):
        return

    user = update.effective_user
    if user.id != OWNER_ID:
        return

    session = terminal.get_session(user.id)
    if not session:
        await message.reply_text(
            f"{Emoji.WARNING} {Fonts.small_caps('no active terminal session.')}\n"
            f"{UI.BULLET} {Fonts.small_caps('use')} /terminal <project_id>"
        )
        return

    command = text[1:].strip()
    if not command:
        return

    # Show typing indicator
    await context.bot.send_chat_action(
        chat_id=update.effective_chat.id,
        action=ChatAction.TYPING,
    )

    success, stdout, stderr = await terminal.execute_command(user.id, command)

    output = ""
    if stdout:
        output += stdout[:3000]
    if stderr:
        output += f"\n--- stderr ---\n{stderr[:1000]}"

    if not output.strip():
        output = "(no output)"

    # Truncate for Telegram
    if len(output) > 3500:
        output = output[:3500] + "\n... (truncated)"

    status_icon = Emoji.SUCCESS if success else Emoji.ERROR

    result = (
        f"{status_icon} $ {Fonts.mono(command[:50])}\n"
        f"```\n{output}\n```"
    )

    await message.reply_text(result)


# ┌─────────────────────────────────────────────────────────────────────────────┐
# │         SECTION 36: SYSTEM METRICS GRAPH (TEXT-BASED)                       │
# └─────────────────────────────────────────────────────────────────────────────┘

class MetricsGraph:
    """Generate text-based graphs for system metrics history."""

    @staticmethod
    def generate_ascii_chart(
        data: List[float],
        width: int = 30,
        height: int = 8,
        label: str = "",
        unit: str = "%",
    ) -> str:
        """Generate an ASCII chart from data points."""
        if not data:
            return "No data available"

        max_val = max(data) if data else 100
        min_val = min(data) if data else 0

        if max_val == min_val:
            max_val = min_val + 1

        # Normalize data to fit height
        normalized = []
        step = max(1, len(data) // width)
        sampled = data[::step][:width]

        for val in sampled:
            norm = int((val - min_val) / (max_val - min_val) * (height - 1))
            normalized.append(norm)

        # Build chart
        lines = []
        for row in range(height - 1, -1, -1):
            line = ""
            for col in range(len(normalized)):
                if normalized[col] >= row:
                    # Color based on value
                    val_pct = sampled[col] / max_val * 100 if max_val > 0 else 0
                    if val_pct > 90:
                        line += "█"
                    elif val_pct > 70:
                        line += "▓"
                    elif val_pct > 50:
                        line += "▒"
                    else:
                        line += "░"
                else:
                    line += " "
            # Add y-axis label
            if row == height - 1:
                y_label = f"{max_val:.0f}{unit}"
            elif row == 0:
                y_label = f"{min_val:.0f}{unit}"
            else:
                y_label = ""
            lines.append(f"│{line}│ {y_label}")

        # Bottom border
        lines.append(f"└{'─' * len(normalized)}┘")

        # Title
        header = f"┌{'─' * len(normalized)}┐"
        title_line = f"│{label:^{len(normalized)}}│" if label else ""

        result = header + "\n"
        if title_line:
            result += title_line + "\n"
        result += "\n".join(lines)

        return result

    @classmethod
    def generate_system_report_graph(cls) -> str:
        """Generate graphs from stored system stats."""
        stats = db.fetchall(
            "SELECT * FROM system_stats ORDER BY created_at DESC LIMIT 60"
        )

        if not stats:
            return "No historical data available yet."

        stats = list(reversed(stats))

        cpu_data = [s["cpu_percent"] for s in stats]
        ram_data = [s["ram_percent"] for s in stats]
        disk_data = [s["disk_percent"] for s in stats]

        cpu_chart = cls.generate_ascii_chart(
            cpu_data, width=25, height=6, label="CPU Usage", unit="%"
        )
        ram_chart = cls.generate_ascii_chart(
            ram_data, width=25, height=6, label="RAM Usage", unit="%"
        )

        report = (
            f"{Emoji.CHART} {Fonts.bold('SYSTEM METRICS HISTORY')}\n"
            f"{UI.DIVIDER_THIN}\n\n"
            f"{Emoji.CPU} CPU ({len(cpu_data)} samples):\n"
            f"```\n{cpu_chart}\n```\n\n"
            f"{Emoji.RAM} RAM ({len(ram_data)} samples):\n"
            f"```\n{ram_chart}\n```\n\n"
            f"{UI.DIVIDER_THIN}\n"
            f"Avg CPU: {sum(cpu_data)/len(cpu_data):.1f}% | "
            f"Avg RAM: {sum(ram_data)/len(ram_data):.1f}%"
        )

        return report


# ┌─────────────────────────────────────────────────────────────────────────────┐
# │         SECTION 37: ENHANCED CALLBACK ROUTER (FINAL)                        │
# └─────────────────────────────────────────────────────────────────────────────┘

# Override the original callback router to include all new handlers
_original_callback_router = callback_router


@authorized
async def enhanced_callback_router(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Enhanced callback router with all advanced features."""
    query = update.callback_query
    await query.answer()
    data = query.data
    user = update.effective_user

    logger.info(f"Callback: {data} from user {user.id}")

    # ── Main Menu ──
    if data in ("menu_main", "menu_refresh"):
        text = menu.get_main_menu_text(user.first_name, user.id)
        keyboard = menu.get_main_menu_keyboard(user.id)
        try:
            await query.edit_message_text(text, reply_markup=keyboard)
        except BadRequest:
            pass

    # ── Deploy Console ──
    elif data == "menu_deploy":
        await show_deploy_console(update, context)

    # ── File Manager ──
    elif data == "menu_files":
        await show_file_manager(update, context)

    # ── Live Logs ──
    elif data == "menu_logs":
        await show_logs_menu(update, context)

    # ── System Health ──
    elif data == "menu_health":
        await health_command(update, context)

    # ── Metrics Graph ──
    elif data == "menu_metrics":
        report = MetricsGraph.generate_system_report_graph()
        keyboard = menu.get_back_and_refresh("menu_health", "menu_metrics")
        try:
            await query.edit_message_text(report, reply_markup=keyboard)
        except BadRequest:
            pass

    # ── My Projects ──
    elif data == "menu_projects":
        await show_projects_menu(update, context)

    # ── Upload ──
    elif data == "menu_upload":
        await show_upload_instructions(update, context)

    # ── Notifications ──
    elif data == "menu_notifications":
        await show_notifications(update, context)

    # ── Settings ──
    elif data == "menu_settings":
        await show_settings(update, context)

    # ── About ──
    elif data == "menu_about":
        text = menu.get_about_text()
        keyboard = menu.get_back_button()
        try:
            await query.edit_message_text(text, reply_markup=keyboard)
        except BadRequest:
            pass

    # ── Admin Panel ──
    elif data == "menu_admin":
        await show_admin_panel(update, context)

    # ── Database ──
    elif data == "menu_database":
        await show_database_info(update, context)

    # ── Project-specific ──
    elif data.startswith("proj_"):
        await handle_project_action(update, context, data)

    # ── File-specific ──
    elif data.startswith("file_"):
        await handle_file_action(update, context, data)

    # ── Deploy actions (including advanced) ──
    elif data.startswith("deploy_") or data.startswith("adv_"):
        await handle_deploy_action(update, context, data)

    # ── Log actions (including streaming) ──
    elif data.startswith("log_"):
        await handle_log_action(update, context, data)

    # ── Settings ──
    elif data.startswith("set_"):
        await handle_settings_action(update, context, data)

    # ── Admin ──
    elif data.startswith("admin_"):
        await handle_admin_action(update, context, data)

    # ── Notifications ──
    elif data.startswith("notif_"):
        await handle_notification_action(update, context, data)

    # ── Confirmations ──
    elif data.startswith("confirm_"):
        await handle_confirmation(update, context, data)

    # ── Pagination ──
    elif data.startswith("page_"):
        await handle_pagination(update, context, data)

    else:
        logger.warning(f"Unhandled callback: {data}")


# Replace global callback router
callback_router = enhanced_callback_router


# ┌─────────────────────────────────────────────────────────────────────────────┐
# │         SECTION 38: ENHANCED STARTUP & FINAL APPLICATION BUILDER            │
# └─────────────────────────────────────────────────────────────────────────────┘

async def enhanced_post_init(application: Application) -> None:
    """Enhanced initialization with watchdog startup."""
    # Call original post_init
    await post_init(application)

    # Start watchdog
    await watchdog.start_monitoring()

    # Register alert callback for sending Telegram messages
    async def telegram_alert(user_id: int, title: str, message: str, alert_type: str):
        try:
            icon = {
                "info": Emoji.INFO,
                "success": Emoji.SUCCESS,
                "warning": Emoji.WARNING,
                "error": Emoji.ERROR,
            }.get(alert_type, Emoji.INFO)

            text = (
                f"{icon} {Fonts.bold(title)}\n"
                f"{UI.DIVIDER_THIN}\n\n"
                f"{message}\n\n"
                f"{UI.DIVIDER_THIN}\n"
                f"{Emoji.CLOCK} {datetime.now().strftime('%H:%M:%S')}"
            )
            await application.bot.send_message(
                chat_id=user_id,
                text=text,
            )
        except Exception as e:
            logger.error(f"Failed to send alert to {user_id}: {e}")

    watchdog.register_alert_callback(telegram_alert)
    logger.info("Process Watchdog + Alert system initialized")


async def enhanced_post_shutdown(application: Application) -> None:
    """Enhanced shutdown with watchdog and stream cleanup."""
    # Stop all log streams
    await log_streamer.stop_all_streams()

    # Stop watchdog
    await watchdog.stop_monitoring()

    # Call original shutdown
    await post_shutdown(application)


def build_enhanced_application() -> Application:
    """Build the fully enhanced application with all features."""

    application = (
        ApplicationBuilder()
        .token(BOT_TOKEN)
        .post_init(enhanced_post_init)
        .post_shutdown(enhanced_post_shutdown)
        .concurrent_updates(True)
        .read_timeout(30)
        .write_timeout(30)
        .connect_timeout(30)
        .build()
    )

    # ── Command Handlers ──
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("health", health_command))
    application.add_handler(CommandHandler("status", status_command))
    application.add_handler(CommandHandler("deploy", deploy_command))
    application.add_handler(CommandHandler("logs", logs_command))
    application.add_handler(CommandHandler("files", files_command))
    application.add_handler(CommandHandler("upload", upload_command))
    application.add_handler(CommandHandler("admin", admin_command))
    application.add_handler(CommandHandler("adduser", adduser_command))
    application.add_handler(CommandHandler("ban", ban_command))
    application.add_handler(CommandHandler("stats", stats_command))
    application.add_handler(CommandHandler("setenv", setenv_command))
    application.add_handler(CommandHandler("setmain", setmain_command))
    application.add_handler(CommandHandler("terminal", terminal_command))
    application.add_handler(CommandHandler("endterm", endterm_command))

    # ── Callback Query Handler (enhanced) ──
    application.add_handler(CallbackQueryHandler(enhanced_callback_router))

    # ── Document Upload Handler ──
    application.add_handler(
        MessageHandler(filters.Document.ALL, handle_document_upload)
    )

    # ── Terminal message handler ($ prefix) ──
    application.add_handler(
        MessageHandler(
            filters.TEXT & filters.Regex(r"^\$\s*.+") & ~filters.COMMAND,
            handle_terminal_message,
        )
    )

    # ── Error Handler ──
    application.add_error_handler(error_handler)

    return application


# ┌─────────────────────────────────────────────────────────────────────────────┐
# │         SECTION 39: FINAL MAIN ENTRY POINT                                  │
# └─────────────────────────────────────────────────────────────────────────────┘

def main():
    """Main entry point - Production build."""
    print(
        r"""
 ═══════════════════════════════════════════════════════════════════════════════
 ██████╗ ██╗   ██╗██╗  ██╗██╗    ██╗  ██╗    ██╗  ██╗ ██████╗ ███████╗████████╗
 ██╔══██╗██║   ██║██║  ██║██║    ╚██╗██╔╝    ██║  ██║██╔═══██╗██╔════╝╚══██╔══╝
 ██████╔╝██║   ██║███████║██║     ╚███╔╝     ███████║██║   ██║███████╗   ██║
 ██╔══██╗██║   ██║██╔══██║██║     ██╔██╗     ██╔══██║██║   ██║╚════██║   ██║
 ██║  ██║╚██████╔╝██║  ██║██║    ██╔╝ ██╗    ██║  ██║╚██████╔╝███████║   ██║
 ╚═╝  ╚═╝ ╚═════╝ ╚═╝  ╚═╝╚═╝    ╚═╝  ╚═╝    ╚═╝  ╚═╝ ╚═════╝ ╚══════╝   ╚═╝
 ═══════════════════════════════════════════════════════════════════════════════

 ┌─────────────────────────────────────────────────────────────────────────────┐
 │                    RUHI X HOSTING - PRODUCTION BUILD                        │
 │                                                                             │
 │  Version : {ver:<10}  Build : {build:<15}                │
 │  Owner   : {owner:<55}│
 │  Python  : {pyver:<55}│
 │  System  : {sys_info:<55}│
 │                                                                             │
 │  Features:                                                                  │
 │    ★ File Manager with ZIP/TAR support                                      │
 │    ★ Deploy Console with auto-detection                                     │
 │    ★ Live Log Streaming with auto-refresh                                   │
 │    ★ System Health Monitor with ASCII graphs                                │
 │    ★ Process Watchdog with auto-recovery                                    │
 │    ★ Backup & Restore system                                                │
 │    ★ Dependency Manager (pip/npm/maven)                                     │
 │    ★ Interactive Terminal Sessions                                          │
 │    ★ Port Management for web projects                                       │
 │    ★ Multi-language: Python, Node.js, Java                                  │
 │    ★ SQLite Database with 8 tables                                          │
 │    ★ Beautiful UI with styled Unicode fonts                                 │
 └─────────────────────────────────────────────────────────────────────────────┘
        """.format(
            ver=BOT_VERSION,
            build=BOT_BUILD,
            owner=OWNER_USERNAME,
            pyver=platform.python_version(),
            sys_info=f"{platform.system()} {platform.release()}"
        )
    )

    # ── Validation ──
    if BOT_TOKEN == "YOUR_BOT_TOKEN_HERE":
        print("\n  ❌ FATAL: BOT_TOKEN not configured!")
        print("  → Edit the BOT_TOKEN variable at the top of hosting.py")
        print("  → Get your token from @BotFather on Telegram\n")
        sys.exit(1)

    if OWNER_ID == 123456789:
        print("\n  ⚠️  WARNING: OWNER_ID not configured!")
        print("  → Edit the OWNER_ID variable at the top of hosting.py")
        print("  → Get your ID from @userinfobot on Telegram\n")

    # ── Dependency Check ──
    print("  Checking dependencies...")
    required_modules = {
        "telegram": "python-telegram-bot",
        "psutil": "psutil",
    }
    missing = []
    for module, pip_name in required_modules.items():
        try:
            __import__(module)
            print(f"    ✅ {pip_name}")
        except ImportError:
            print(f"    ❌ {pip_name} (missing)")
            missing.append(pip_name)

    if missing:
        print(f"\n  Install missing packages:")
        print(f"    pip install {' '.join(missing)}\n")
        sys.exit(1)

    print(f"\n  ✅ All checks passed. Starting bot...\n")
    print(f"{'=' * 75}\n")

    # ── Build & Run ──
    app = build_enhanced_application()
    app.run_polling(
        allowed_updates=Update.ALL_TYPES,
        drop_pending_updates=True,
        close_loop=False,
    )


if __name__ == "__main__":
    main()
    
# ┌─────────────────────────────────────────────────────────────────────────────┐
# │         SECTION 40: RATE LIMITER & ANTI-FLOOD SYSTEM                        │
# └─────────────────────────────────────────────────────────────────────────────┘

class RateLimiter:
    """
    Advanced rate limiter with per-user and global rate limiting.
    Prevents API abuse, flood attacks, and excessive resource usage.
    Implements token bucket algorithm with sliding window.
    """

    def __init__(self):
        self._user_buckets: Dict[int, Dict[str, Any]] = {}
        self._global_counter: deque = deque(maxlen=1000)
        self._blocked_users: Dict[int, float] = {}
        self._warning_counts: Dict[int, int] = defaultdict(int)
        self._lock = threading.Lock()

        # Configuration
        self._limits = {
            "messages_per_minute": 30,
            "callbacks_per_minute": 60,
            "uploads_per_hour": 10,
            "commands_per_minute": 20,
            "global_per_second": 30,
            "block_duration": 300,  # 5 minutes
            "warning_threshold": 3,
        }

    def _get_bucket(self, user_id: int) -> Dict[str, Any]:
        """Get or create a rate limit bucket for user."""
        with self._lock:
            if user_id not in self._user_buckets:
                self._user_buckets[user_id] = {
                    "messages": deque(maxlen=100),
                    "callbacks": deque(maxlen=200),
                    "uploads": deque(maxlen=50),
                    "commands": deque(maxlen=100),
                }
            return self._user_buckets[user_id]

    def is_blocked(self, user_id: int) -> bool:
        """Check if user is currently blocked."""
        if user_id == OWNER_ID:
            return False
        block_time = self._blocked_users.get(user_id)
        if block_time:
            if time.time() - block_time < self._limits["block_duration"]:
                return True
            else:
                del self._blocked_users[user_id]
                self._warning_counts[user_id] = 0
                return False
        return False

    def _block_user(self, user_id: int):
        """Temporarily block a user."""
        if user_id != OWNER_ID:
            self._blocked_users[user_id] = time.time()
            logger.warning(f"Rate limiter: Blocked user {user_id}")

    def check_rate(
        self, user_id: int, action_type: str = "messages"
    ) -> Tuple[bool, str]:
        """
        Check if action is within rate limits.
        Returns (allowed, message).
        """
        if user_id == OWNER_ID:
            return True, ""

        if self.is_blocked(user_id):
            remaining = self._limits["block_duration"] - (
                time.time() - self._blocked_users.get(user_id, 0)
            )
            return False, (
                f"{Emoji.LOCK} {Fonts.small_caps('rate limited')}\n\n"
                f"{UI.BULLET} {Fonts.small_caps('you are temporarily blocked')}\n"
                f"{UI.BULLET} {Fonts.small_caps('try again in')} {int(remaining)}s\n"
                f"{UI.DIVIDER_THIN}"
            )

        bucket = self._get_bucket(user_id)
        now = time.time()

        # Add current action
        if action_type in bucket:
            bucket[action_type].append(now)

        # Check limits based on action type
        limit_map = {
            "messages": ("messages_per_minute", 60),
            "callbacks": ("callbacks_per_minute", 60),
            "uploads": ("uploads_per_hour", 3600),
            "commands": ("commands_per_minute", 60),
        }

        if action_type in limit_map:
            limit_key, window = limit_map[action_type]
            max_actions = self._limits[limit_key]

            # Count actions in window
            recent = sum(
                1 for t in bucket.get(action_type, []) if now - t < window
            )

            if recent > max_actions:
                self._warning_counts[user_id] += 1
                if self._warning_counts[user_id] >= self._limits["warning_threshold"]:
                    self._block_user(user_id)
                    return False, (
                        f"{Emoji.LOCK} {Fonts.small_caps('blocked for flooding')}\n"
                        f"{UI.BULLET} {Fonts.small_caps('duration')}: "
                        f"{self._limits['block_duration']}s\n"
                        f"{UI.DIVIDER_THIN}"
                    )
                return False, (
                    f"{Emoji.WARNING} {Fonts.small_caps('slow down!')}\n"
                    f"{UI.BULLET} {Fonts.small_caps('max')} {max_actions} "
                    f"{action_type}/{window}s\n"
                    f"{UI.BULLET} {Fonts.small_caps('warning')} "
                    f"{self._warning_counts[user_id]}/{self._limits['warning_threshold']}\n"
                    f"{UI.DIVIDER_THIN}"
                )

        # Global rate check
        self._global_counter.append(now)
        global_recent = sum(1 for t in self._global_counter if now - t < 1)
        if global_recent > self._limits["global_per_second"]:
            return False, f"{Emoji.WARNING} {Fonts.small_caps('server busy, please wait...')}"

        return True, ""

    def get_user_stats(self, user_id: int) -> Dict[str, Any]:
        """Get rate limit stats for a user."""
        bucket = self._get_bucket(user_id)
        now = time.time()
        return {
            "messages_last_min": sum(
                1 for t in bucket.get("messages", []) if now - t < 60
            ),
            "callbacks_last_min": sum(
                1 for t in bucket.get("callbacks", []) if now - t < 60
            ),
            "is_blocked": self.is_blocked(user_id),
            "warnings": self._warning_counts.get(user_id, 0),
        }

    def reset_user(self, user_id: int):
        """Reset rate limits for a user."""
        with self._lock:
            self._user_buckets.pop(user_id, None)
            self._blocked_users.pop(user_id, None)
            self._warning_counts.pop(user_id, None)

    def cleanup(self):
        """Clean up old data."""
        now = time.time()
        with self._lock:
            # Remove expired blocks
            expired = [
                uid
                for uid, bt in self._blocked_users.items()
                if now - bt >= self._limits["block_duration"]
            ]
            for uid in expired:
                del self._blocked_users[uid]
                self._warning_counts.pop(uid, None)


# ── Global Rate Limiter ──
rate_limiter = RateLimiter()


# ┌─────────────────────────────────────────────────────────────────────────────┐
# │         SECTION 41: RATE-LIMITED AUTHORIZATION DECORATOR                    │
# └─────────────────────────────────────────────────────────────────────────────┘

def rate_limited_authorized(action_type: str = "messages"):
    """Combined rate limiting + authorization decorator factory."""

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(
            update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs
        ):
            user = update.effective_user
            if not user:
                return

            # Rate check first (cheaper than DB lookup)
            allowed, rate_msg = rate_limiter.check_rate(user.id, action_type)
            if not allowed:
                if update.callback_query:
                    await update.callback_query.answer(
                        "⏳ Rate limited! Slow down.", show_alert=True
                    )
                elif update.message:
                    await update.message.reply_text(rate_msg)
                return

            # Then auth check
            db.upsert_user(
                user_id=user.id,
                username=user.username,
                first_name=user.first_name,
                last_name=user.last_name,
            )

            if not db.is_user_authorized(user.id):
                text = (
                    f"{Emoji.LOCK} {Fonts.small_caps('access denied')}\n\n"
                    f"{UI.DIVIDER_THIN}\n\n"
                    f"{UI.BULLET} {Fonts.small_caps('contact')} "
                    f"{OWNER_USERNAME} {Fonts.small_caps('for access.')}\n\n"
                    f"{UI.DIVIDER_THIN}"
                )
                if update.callback_query:
                    await update.callback_query.answer(
                        "⛔ Access Denied!", show_alert=True
                    )
                else:
                    await update.message.reply_text(text)
                return

            user_data = db.get_user(user.id)
            if user_data and user_data["is_banned"]:
                if update.callback_query:
                    await update.callback_query.answer(
                        "⛔ You are banned!", show_alert=True
                    )
                return

            return await func(update, context, *args, **kwargs)

        return wrapper

    return decorator


# ┌─────────────────────────────────────────────────────────────────────────────┐
# │         SECTION 42: PROJECT SEARCH ENGINE                                   │
# └─────────────────────────────────────────────────────────────────────────────┘

class SearchEngine:
    """
    Search functionality for projects, files, logs, and system resources.
    Supports fuzzy matching and multi-field search.
    """

    @staticmethod
    def _fuzzy_match(query: str, text: str, threshold: float = 0.4) -> float:
        """Simple fuzzy matching score (0.0 to 1.0)."""
        query = query.lower().strip()
        text = text.lower().strip()

        if not query or not text:
            return 0.0

        # Exact match
        if query == text:
            return 1.0

        # Contains
        if query in text:
            return 0.9

        # Starts with
        if text.startswith(query):
            return 0.85

        # Word match
        query_words = set(query.split())
        text_words = set(text.split())
        if query_words & text_words:
            intersection = len(query_words & text_words)
            return 0.6 + (intersection / max(len(query_words), 1)) * 0.3

        # Character overlap (Jaccard-like)
        query_chars = set(query)
        text_chars = set(text)
        if query_chars and text_chars:
            overlap = len(query_chars & text_chars) / len(query_chars | text_chars)
            if overlap >= threshold:
                return overlap * 0.5

        return 0.0

    @classmethod
    def search_projects(
        cls, user_id: int, query: str, limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Search projects by name, type, or ID."""
        projects = db.get_user_projects(user_id)
        results = []

        for proj in projects:
            scores = [
                cls._fuzzy_match(query, proj["project_name"]) * 1.5,
                cls._fuzzy_match(query, proj["project_type"]),
                cls._fuzzy_match(query, proj["project_id"]),
                cls._fuzzy_match(query, proj["main_file"] or ""),
                cls._fuzzy_match(query, proj["description"] or ""),
            ]
            max_score = max(scores)
            if max_score > 0.3:
                results.append({
                    "project": dict(proj),
                    "score": max_score,
                    "match_type": ["name", "type", "id", "main_file", "description"][
                        scores.index(max(scores))
                    ],
                })

        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:limit]

    @classmethod
    def search_files(
        cls, project_dir: str, query: str, limit: int = 20
    ) -> List[Dict[str, Any]]:
        """Search files within a project directory."""
        d = Path(project_dir)
        if not d.exists():
            return []

        results = []
        query_lower = query.lower()

        try:
            for f in d.rglob("*"):
                if f.is_file():
                    name = f.name.lower()
                    rel_path = str(f.relative_to(d))

                    score = cls._fuzzy_match(query, name)
                    path_score = cls._fuzzy_match(query, rel_path) * 0.7

                    # Extension match
                    ext_score = 0.0
                    if query_lower.startswith(".") and f.suffix.lower() == query_lower:
                        ext_score = 0.8

                    final_score = max(score, path_score, ext_score)
                    if final_score > 0.25:
                        results.append({
                            "name": f.name,
                            "path": rel_path,
                            "size": f.stat().st_size,
                            "score": final_score,
                            "is_dir": False,
                        })

                    if len(results) >= limit * 3:  # Pre-limit
                        break
        except (PermissionError, OSError):
            pass

        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:limit]

    @classmethod
    def search_logs(
        cls, project_id: str, query: str, limit: int = 30
    ) -> List[Dict[str, Any]]:
        """Search through process logs."""
        logs = db.get_process_logs(project_id, limit=500)
        results = []

        query_lower = query.lower()

        for log in logs:
            content = log["content"]
            if query_lower in content.lower():
                results.append({
                    "content": content,
                    "log_type": log["log_type"],
                    "created_at": log["created_at"],
                    "score": 1.0 if query_lower in content.lower() else 0.5,
                })

        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:limit]

    @classmethod
    def global_search(
        cls, user_id: int, query: str
    ) -> Dict[str, List[Dict[str, Any]]]:
        """Perform a global search across all categories."""
        return {
            "projects": cls.search_projects(user_id, query, limit=5),
            "files": [],  # Requires project context
            "logs": [],  # Requires project context
        }


# ── Global Search Engine ──
search_engine = SearchEngine()


# ┌─────────────────────────────────────────────────────────────────────────────┐
# │         SECTION 43: SEARCH COMMAND HANDLERS                                 │
# └─────────────────────────────────────────────────────────────────────────────┘

@authorized
async def search_command(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Handle /search <query> command."""
    args = context.args
    if not args:
        await update.message.reply_text(
            f"{Emoji.SEARCH} {Fonts.bold('SEARCH')}\n"
            f"{UI.DIVIDER_THIN}\n\n"
            f"{UI.BULLET} {Fonts.small_caps('usage')}:\n"
            f"  /search <query> - {Fonts.small_caps('search projects')}\n"
            f"  /searchfile <project_id> <query> - {Fonts.small_caps('search files')}\n"
            f"  /searchlog <project_id> <query> - {Fonts.small_caps('search logs')}\n\n"
            f"{UI.DIVIDER_THIN}"
        )
        return

    query = " ".join(args)
    user = update.effective_user

    results = search_engine.search_projects(user.id, query)

    text = (
        f"{Emoji.SEARCH} {Fonts.bold('SEARCH RESULTS')} {Emoji.SEARCH}\n"
        f"{UI.DIVIDER_STAR}\n"
        f"{UI.BULLET} {Fonts.small_caps('query')}: '{query}'\n"
        f"{UI.BULLET} {Fonts.small_caps('found')}: {len(results)} {Fonts.small_caps('results')}\n\n"
        f"{UI.DIVIDER_THIN}\n\n"
    )

    buttons = []

    if not results:
        text += f"{Emoji.INFO} {Fonts.small_caps('no results found.')}\n\n"
    else:
        for i, result in enumerate(results, 1):
            proj = result["project"]
            score = result["score"]
            match_type = result["match_type"]
            is_running = process_manager.is_running(proj["project_id"])
            status = Emoji.ONLINE if is_running else Emoji.OFFLINE

            # Score bar
            score_bar = "●" * int(score * 5) + "○" * (5 - int(score * 5))

            text += (
                f"  {status} {Fonts.bold(f'{i}. {proj['project_name']}')}\n"
                f"    {UI.TRIANGLE} {Fonts.small_caps('type')}: {proj['project_type']}\n"
                f"    {UI.TRIANGLE} {Fonts.small_caps('match')}: {match_type}\n"
                f"    {UI.TRIANGLE} {Fonts.small_caps('relevance')}: [{score_bar}]\n\n"
            )

            buttons.append([
                InlineKeyboardButton(
                    f"{status} {proj['project_name']}",
                    callback_data=f"proj_detail_{proj['project_id']}",
                )
            ])

    text += f"{UI.DIVIDER_STAR}"

    buttons.append([
        InlineKeyboardButton(
            f"{Emoji.HOME} ᴍᴀɪɴ ᴍᴇɴᴜ",
            callback_data="menu_main",
        )
    ])

    await update.message.reply_text(
        text, reply_markup=InlineKeyboardMarkup(buttons)
    )


@authorized
async def searchfile_command(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Handle /searchfile <project_id> <query> command."""
    args = context.args
    if not args or len(args) < 2:
        await update.message.reply_text(
            f"{Emoji.SEARCH} {Fonts.small_caps('usage')}: "
            f"/searchfile <project_id> <query>"
        )
        return

    project_id = args[0]
    query = " ".join(args[1:])

    project = db.get_project(project_id)
    if not project:
        await update.message.reply_text(
            f"{Emoji.ERROR} {Fonts.small_caps('project not found!')}"
        )
        return

    results = search_engine.search_files(project["directory"], query)

    text = (
        f"{Emoji.SEARCH} {Fonts.bold('FILE SEARCH')} {Emoji.SEARCH}\n"
        f"{UI.DIVIDER_STAR}\n"
        f"{UI.BULLET} {Fonts.small_caps('project')}: {project['project_name']}\n"
        f"{UI.BULLET} {Fonts.small_caps('query')}: '{query}'\n"
        f"{UI.BULLET} {Fonts.small_caps('found')}: {len(results)}\n\n"
        f"{UI.DIVIDER_THIN}\n\n"
    )

    buttons = []

    if not results:
        text += f"{Emoji.INFO} {Fonts.small_caps('no files found.')}\n\n"
    else:
        for r in results[:15]:
            icon = _get_file_icon(Path(r["name"]).suffix.lower())
            text += (
                f"  {icon} {r['name']} ({UI.format_bytes(r['size'])})\n"
                f"    {UI.TRIANGLE} {r['path']}\n\n"
            )
            buttons.append([
                InlineKeyboardButton(
                    f"{icon} {r['name'][:30]}",
                    callback_data=f"file_info_{project_id}:{r['path']}",
                )
            ])

    text += f"{UI.DIVIDER_STAR}"

    buttons.append([
        InlineKeyboardButton(
            f"{Emoji.BACK} ʙᴀᴄᴋ",
            callback_data=f"file_browse_{project_id}",
        )
    ])

    await update.message.reply_text(
        text, reply_markup=InlineKeyboardMarkup(buttons)
    )


@authorized
async def searchlog_command(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Handle /searchlog <project_id> <query> command."""
    args = context.args
    if not args or len(args) < 2:
        await update.message.reply_text(
            f"{Emoji.SEARCH} {Fonts.small_caps('usage')}: "
            f"/searchlog <project_id> <query>"
        )
        return

    project_id = args[0]
    query = " ".join(args[1:])

    project = db.get_project(project_id)
    if not project:
        await update.message.reply_text(
            f"{Emoji.ERROR} {Fonts.small_caps('project not found!')}"
        )
        return

    results = search_engine.search_logs(project_id, query)

    text = (
        f"{Emoji.SEARCH} {Fonts.bold('LOG SEARCH')} {Emoji.SEARCH}\n"
        f"{UI.DIVIDER_STAR}\n"
        f"{UI.BULLET} {Fonts.small_caps('project')}: {project['project_name']}\n"
        f"{UI.BULLET} {Fonts.small_caps('query')}: '{query}'\n"
        f"{UI.BULLET} {Fonts.small_caps('matches')}: {len(results)}\n\n"
        f"{UI.DIVIDER_THIN}\n\n"
    )

    if not results:
        text += f"{Emoji.INFO} {Fonts.small_caps('no matching logs found.')}\n\n"
    else:
        for r in results[:15]:
            # Highlight the match
            content = r["content"]
            if len(content) > 100:
                idx = content.lower().find(query.lower())
                start = max(0, idx - 30)
                end = min(len(content), idx + len(query) + 30)
                content = "..." + content[start:end] + "..."

            text += (
                f"  {Emoji.LOG} {r['created_at'][:19]}\n"
                f"    {content}\n\n"
            )

    text += f"{UI.DIVIDER_STAR}"

    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                f"{Emoji.LOG} ᴀʟʟ ʟᴏɢs",
                callback_data=f"log_view_{project_id}",
            ),
            InlineKeyboardButton(
                f"{Emoji.HOME} ᴍᴇɴᴜ",
                callback_data="menu_main",
            ),
        ]
    ])

    await update.message.reply_text(text, reply_markup=keyboard)


# ┌─────────────────────────────────────────────────────────────────────────────┐
# │         SECTION 44: ANALYTICS & STATISTICS ENGINE                           │
# └─────────────────────────────────────────────────────────────────────────────┘

class AnalyticsEngine:
    """
    Comprehensive analytics for bot usage, deployments, and system performance.
    """

    @staticmethod
    def get_deployment_analytics(
        user_id: int = None, days: int = 7
    ) -> Dict[str, Any]:
        """Get deployment analytics."""
        if user_id:
            logs = db.fetchall(
                """
                SELECT action, status, COUNT(*) as cnt,
                       AVG(duration) as avg_duration,
                       SUM(duration) as total_duration
                FROM deployment_logs
                WHERE user_id = ? AND created_at >= datetime('now', ?)
                GROUP BY action, status
                ORDER BY cnt DESC
                """,
                (user_id, f"-{days} days"),
            )
        else:
            logs = db.fetchall(
                """
                SELECT action, status, COUNT(*) as cnt,
                       AVG(duration) as avg_duration,
                       SUM(duration) as total_duration
                FROM deployment_logs
                WHERE created_at >= datetime('now', ?)
                GROUP BY action, status
                ORDER BY cnt DESC
                """,
                (f"-{days} days",),
            )

        total_deploys = sum(r["cnt"] for r in logs if r["action"] == "start")
        total_stops = sum(r["cnt"] for r in logs if r["action"] == "stop")
        total_restarts = sum(r["cnt"] for r in logs if r["action"] == "restart")
        total_crashes = sum(
            r["cnt"]
            for r in logs
            if r["action"] in ("auto_stop", "watchdog_restart")
        )

        success_count = sum(r["cnt"] for r in logs if r["status"] == "success")
        fail_count = sum(r["cnt"] for r in logs if r["status"] == "failed")
        total = success_count + fail_count
        success_rate = (success_count / total * 100) if total > 0 else 0

        return {
            "total_deploys": total_deploys,
            "total_stops": total_stops,
            "total_restarts": total_restarts,
            "total_crashes": total_crashes,
            "success_rate": success_rate,
            "success_count": success_count,
            "fail_count": fail_count,
            "period_days": days,
            "breakdown": [dict(r) for r in logs],
        }

    @staticmethod
    def get_project_rankings(user_id: int = None) -> List[Dict[str, Any]]:
        """Get project rankings by various metrics."""
        if user_id:
            projects = db.fetchall(
                """
                SELECT project_name, project_type, deploy_count,
                       total_runtime, error_count, restart_count, status
                FROM projects
                WHERE user_id = ?
                ORDER BY deploy_count DESC
                """,
                (user_id,),
            )
        else:
            projects = db.fetchall(
                """
                SELECT project_name, project_type, deploy_count,
                       total_runtime, error_count, restart_count, status, user_id
                FROM projects
                ORDER BY deploy_count DESC
                """
            )

        rankings = []
        for proj in projects:
            reliability = 0.0
            total_ops = proj["deploy_count"] + proj["restart_count"]
            if total_ops > 0:
                reliability = max(
                    0,
                    (1 - proj["error_count"] / total_ops) * 100
                )

            rankings.append({
                "name": proj["project_name"],
                "type": proj["project_type"],
                "deploys": proj["deploy_count"],
                "runtime": proj["total_runtime"],
                "errors": proj["error_count"],
                "restarts": proj["restart_count"],
                "reliability": reliability,
                "status": proj["status"],
            })

        return rankings

    @staticmethod
    def get_system_performance_summary(hours: int = 24) -> Dict[str, Any]:
        """Get system performance summary over time."""
        stats = db.fetchall(
            """
            SELECT
                AVG(cpu_percent) as avg_cpu,
                MAX(cpu_percent) as max_cpu,
                MIN(cpu_percent) as min_cpu,
                AVG(ram_percent) as avg_ram,
                MAX(ram_percent) as max_ram,
                MIN(ram_percent) as min_ram,
                AVG(disk_percent) as avg_disk,
                MAX(disk_percent) as max_disk,
                AVG(active_procs) as avg_procs,
                MAX(active_procs) as max_procs,
                COUNT(*) as sample_count
            FROM system_stats
            WHERE created_at >= datetime('now', ?)
            """,
            (f"-{hours} hours",),
        )

        row = stats[0] if stats else None
        if not row or row["sample_count"] == 0:
            return {
                "avg_cpu": 0, "max_cpu": 0, "min_cpu": 0,
                "avg_ram": 0, "max_ram": 0, "min_ram": 0,
                "avg_disk": 0, "max_disk": 0,
                "avg_procs": 0, "max_procs": 0,
                "sample_count": 0, "hours": hours,
            }

        return {
            "avg_cpu": row["avg_cpu"] or 0,
            "max_cpu": row["max_cpu"] or 0,
            "min_cpu": row["min_cpu"] or 0,
            "avg_ram": row["avg_ram"] or 0,
            "max_ram": row["max_ram"] or 0,
            "min_ram": row["min_ram"] or 0,
            "avg_disk": row["avg_disk"] or 0,
            "max_disk": row["max_disk"] or 0,
            "avg_procs": row["avg_procs"] or 0,
            "max_procs": row["max_procs"] or 0,
            "sample_count": row["sample_count"] or 0,
            "hours": hours,
        }

    @staticmethod
    def get_file_operation_summary(
        user_id: int = None, days: int = 7
    ) -> Dict[str, Any]:
        """Get file operation analytics."""
        if user_id:
            ops = db.fetchall(
                """
                SELECT operation, status, COUNT(*) as cnt,
                       SUM(file_size) as total_size
                FROM file_operations
                WHERE user_id = ? AND created_at >= datetime('now', ?)
                GROUP BY operation, status
                """,
                (user_id, f"-{days} days"),
            )
        else:
            ops = db.fetchall(
                """
                SELECT operation, status, COUNT(*) as cnt,
                       SUM(file_size) as total_size
                FROM file_operations
                WHERE created_at >= datetime('now', ?)
                GROUP BY operation, status
                """,
                (f"-{days} days",),
            )

        return {
            "operations": [dict(o) for o in ops],
            "total_ops": sum(o["cnt"] for o in ops),
            "total_size": sum(o["total_size"] or 0 for o in ops),
        }

    @staticmethod
    def get_uptime_report() -> Dict[str, Any]:
        """Get detailed uptime report for all projects."""
        projects = db.get_all_projects()
        total_runtime = sum(p["total_runtime"] for p in projects)
        total_deploys = sum(p["deploy_count"] for p in projects)
        total_errors = sum(p["error_count"] for p in projects)

        currently_running = []
        for proj in projects:
            if process_manager.is_running(proj["project_id"]):
                proc = process_manager.get_process(proj["project_id"])
                currently_running.append({
                    "name": proj["project_name"],
                    "uptime": proc.uptime if proc else 0,
                    "memory": proc.get_memory_usage() if proc else 0,
                    "cpu": proc.get_cpu_usage() if proc else 0,
                })

        return {
            "total_runtime_hours": total_runtime / 3600,
            "total_deploys": total_deploys,
            "total_errors": total_errors,
            "total_projects": len(projects),
            "running_now": len(currently_running),
            "running_details": currently_running,
        }


# ── Global Analytics ──
analytics = AnalyticsEngine()


# ┌─────────────────────────────────────────────────────────────────────────────┐
# │         SECTION 45: ANALYTICS COMMAND HANDLERS                              │
# └─────────────────────────────────────────────────────────────────────────────┘

@authorized
async def analytics_command(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Handle /analytics command - Show comprehensive analytics."""
    user = update.effective_user

    # Deployment analytics
    deploy_stats = analytics.get_deployment_analytics(user.id, days=7)

    # Project rankings
    rankings = analytics.get_project_rankings(user.id)

    # System performance
    sys_perf = analytics.get_system_performance_summary(hours=24)

    # File operations
    file_stats = analytics.get_file_operation_summary(user.id, days=7)

    # Uptime report
    uptime = analytics.get_uptime_report()

    text = (
        f"{Emoji.STATS} {Fonts.bold('ANALYTICS DASHBOARD')} {Emoji.STATS}\n"
        f"{UI.DIVIDER_STAR}\n\n"
        #
        f"{Emoji.DEPLOY} {Fonts.small_caps('deployment stats')} (7 {Fonts.small_caps('days')}):\n"
        f"  {UI.TRIANGLE} {Fonts.small_caps('deploys')}: {Fonts.bold(str(deploy_stats['total_deploys']))}\n"
        f"  {UI.TRIANGLE} {Fonts.small_caps('stops')}: {deploy_stats['total_stops']}\n"
        f"  {UI.TRIANGLE} {Fonts.small_caps('restarts')}: {deploy_stats['total_restarts']}\n"
        f"  {UI.TRIANGLE} {Fonts.small_caps('crashes')}: {deploy_stats['total_crashes']}\n"
        f"  {UI.TRIANGLE} {Fonts.small_caps('success rate')}: "
        f"{UI.progress_bar(deploy_stats['success_rate'], 100, 10)}\n\n"
        #
        f"{UI.DIVIDER_THIN}\n\n"
        #
        f"{Emoji.CHART} {Fonts.small_caps('system performance')} (24h):\n"
        f"  {Emoji.CPU} CPU: {Fonts.small_caps('avg')} {sys_perf['avg_cpu']:.1f}% | "
        f"{Fonts.small_caps('max')} {sys_perf['max_cpu']:.1f}%\n"
        f"  {Emoji.RAM} RAM: {Fonts.small_caps('avg')} {sys_perf['avg_ram']:.1f}% | "
        f"{Fonts.small_caps('max')} {sys_perf['max_ram']:.1f}%\n"
        f"  {Emoji.DISK} Disk: {Fonts.small_caps('avg')} {sys_perf['avg_disk']:.1f}% | "
        f"{Fonts.small_caps('max')} {sys_perf['max_disk']:.1f}%\n"
        f"  {UI.TRIANGLE} {Fonts.small_caps('samples')}: {sys_perf['sample_count']}\n\n"
        #
        f"{UI.DIVIDER_THIN}\n\n"
        #
        f"{Emoji.UPTIME} {Fonts.small_caps('uptime report')}:\n"
        f"  {UI.TRIANGLE} {Fonts.small_caps('total runtime')}: {uptime['total_runtime_hours']:.1f}h\n"
        f"  {UI.TRIANGLE} {Fonts.small_caps('running now')}: {Fonts.bold(str(uptime['running_now']))}\n"
        f"  {UI.TRIANGLE} {Fonts.small_caps('total deploys')}: {uptime['total_deploys']}\n"
        f"  {UI.TRIANGLE} {Fonts.small_caps('total errors')}: {uptime['total_errors']}\n\n"
    )

    # Running processes details
    if uptime["running_details"]:
        text += f"{Emoji.ONLINE} {Fonts.small_caps('active processes')}:\n"
        for proc in uptime["running_details"]:
            text += (
                f"  {Emoji.ONLINE} {proc['name']}\n"
                f"    ⏱ {UI.format_uptime(proc['uptime'])} | "
                f"🧠 {UI.format_bytes(proc['memory'])} | "
                f"🖥 {proc['cpu']:.1f}%\n"
            )
        text += "\n"

    # Project rankings
    if rankings:
        text += (
            f"{UI.DIVIDER_THIN}\n\n"
            f"{Emoji.STAR} {Fonts.small_caps('project rankings')}:\n"
        )
        medals = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣"]
        for i, rank in enumerate(rankings[:5]):
            medal = medals[i] if i < len(medals) else f"{i+1}."
            status_dot = UI.status_dot(rank["status"] == "running")
            reliability_bar = UI.progress_bar(rank["reliability"], 100, 8)
            text += (
                f"  {medal} {status_dot} {rank['name']}\n"
                f"    {Fonts.small_caps('deploys')}: {rank['deploys']} | "
                f"{Fonts.small_caps('reliability')}: {reliability_bar}\n"
            )
        text += "\n"

    # File operations
    if file_stats["total_ops"] > 0:
        text += (
            f"{UI.DIVIDER_THIN}\n\n"
            f"{Emoji.FILE} {Fonts.small_caps('file operations')} (7d):\n"
            f"  {UI.TRIANGLE} {Fonts.small_caps('total ops')}: {file_stats['total_ops']}\n"
            f"  {UI.TRIANGLE} {Fonts.small_caps('data transferred')}: "
            f"{UI.format_bytes(file_stats['total_size'])}\n\n"
        )

    text += f"{UI.DIVIDER_STAR}"

    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                f"{Emoji.CHART} ᴍᴇᴛʀɪᴄs ɢʀᴀᴘʜ",
                callback_data="menu_metrics",
            ),
            InlineKeyboardButton(
                f"{Emoji.REFRESH} ʀᴇғʀᴇsʜ",
                callback_data="cb_analytics",
            ),
        ],
        [
            InlineKeyboardButton(
                f"{Emoji.HOME} ᴍᴀɪɴ ᴍᴇɴᴜ",
                callback_data="menu_main",
            ),
        ],
    ])

    if update.message:
        await update.message.reply_text(text, reply_markup=keyboard)
    elif update.callback_query:
        try:
            await update.callback_query.edit_message_text(text, reply_markup=keyboard)
        except BadRequest:
            pass


# ┌─────────────────────────────────────────────────────────────────────────────┐
# │         SECTION 46: QUICK ACTIONS & INLINE SHORTCUTS                        │
# └─────────────────────────────────────────────────────────────────────────────┘

@authorized
async def quick_deploy_command(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Handle /qd <project_name> - Quick deploy by project name."""
    args = context.args
    if not args:
        await update.message.reply_text(
            f"{Emoji.BOLT} {Fonts.small_caps('usage')}: /qd <project_name>\n"
            f"{UI.BULLET} {Fonts.small_caps('quickly start a project by name')}"
        )
        return

    query = " ".join(args)
    user = update.effective_user

    results = search_engine.search_projects(user.id, query, limit=1)
    if not results:
        await update.message.reply_text(
            f"{Emoji.ERROR} {Fonts.small_caps('project not found')}: '{query}'"
        )
        return

    project = results[0]["project"]
    project_id = project["project_id"]

    if process_manager.is_running(project_id):
        await update.message.reply_text(
            f"{Emoji.ONLINE} {Fonts.bold(project['project_name'])} "
            f"{Fonts.small_caps('is already running!')}"
        )
        return

    if not project["main_file"]:
        await update.message.reply_text(
            f"{Emoji.WARNING} {Fonts.small_caps('no main file set for')} "
            f"{project['project_name']}"
        )
        return

    # Deploy
    progress_msg = await update.message.reply_text(
        f"{Emoji.LOADING} {Fonts.small_caps('quick deploying')} "
        f"{Fonts.bold(project['project_name'])}..."
    )

    env_vars = json.loads(project["env_vars"] or "{}")
    success, msg = await process_manager.start_process(
        project_id, project["project_type"], project["main_file"],
        project["directory"], env_vars if env_vars else None,
    )

    db.log_deployment(
        project_id, user.id, "quick_deploy",
        "success" if success else "failed", msg,
    )

    status_icon = Emoji.SUCCESS if success else Emoji.ERROR
    await progress_msg.edit_text(
        f"{status_icon} {Fonts.bold(project['project_name'])}\n"
        f"{UI.DIVIDER_THIN}\n"
        f"{UI.BULLET} {msg}\n"
        f"{UI.DIVIDER_THIN}",
        reply_markup=InlineKeyboardMarkup([
            [
                InlineKeyboardButton(
                    f"{Emoji.LOG} ʟᴏɢs",
                    callback_data=f"log_view_{project_id}",
                ),
                InlineKeyboardButton(
                    f"{Emoji.STOP} sᴛᴏᴘ",
                    callback_data=f"deploy_stop_{project_id}",
                ),
            ]
        ]) if success else InlineKeyboardMarkup([
            [
                InlineKeyboardButton(
                    f"{Emoji.HOME} ᴍᴇɴᴜ",
                    callback_data="menu_main",
                )
            ]
        ]),
    )


@authorized
async def quick_stop_command(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Handle /qs <project_name> - Quick stop by project name."""
    args = context.args
    if not args:
        await update.message.reply_text(
            f"{Emoji.BOLT} {Fonts.small_caps('usage')}: /qs <project_name>"
        )
        return

    query = " ".join(args)
    user = update.effective_user

    results = search_engine.search_projects(user.id, query, limit=1)
    if not results:
        await update.message.reply_text(
            f"{Emoji.ERROR} {Fonts.small_caps('project not found')}: '{query}'"
        )
        return

    project = results[0]["project"]
    project_id = project["project_id"]

    if not process_manager.is_running(project_id):
        await update.message.reply_text(
            f"{Emoji.OFFLINE} {Fonts.bold(project['project_name'])} "
            f"{Fonts.small_caps('is not running.')}"
        )
        return

    success, msg = await process_manager.stop_process(project_id)
    db.log_deployment(
        project_id, user.id, "quick_stop",
        "success" if success else "failed", msg,
    )

    status_icon = Emoji.SUCCESS if success else Emoji.ERROR
    await update.message.reply_text(
        f"{status_icon} {Fonts.bold(project['project_name'])}\n"
        f"{UI.DIVIDER_THIN}\n"
        f"{UI.BULLET} {msg}\n"
        f"{UI.DIVIDER_THIN}"
    )


@authorized
async def quick_restart_command(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Handle /qr <project_name> - Quick restart by project name."""
    args = context.args
    if not args:
        await update.message.reply_text(
            f"{Emoji.BOLT} {Fonts.small_caps('usage')}: /qr <project_name>"
        )
        return

    query = " ".join(args)
    user = update.effective_user

    results = search_engine.search_projects(user.id, query, limit=1)
    if not results:
        await update.message.reply_text(
            f"{Emoji.ERROR} {Fonts.small_caps('project not found')}: '{query}'"
        )
        return

    project = results[0]["project"]
    project_id = project["project_id"]

    progress_msg = await update.message.reply_text(
        f"{Emoji.RESTART} {Fonts.small_caps('restarting')} "
        f"{Fonts.bold(project['project_name'])}..."
    )

    env_vars = json.loads(project["env_vars"] or "{}")
    success, msg = await process_manager.restart_process(
        project_id, project["project_type"], project["main_file"],
        project["directory"], env_vars if env_vars else None,
    )

    db.log_deployment(
        project_id, user.id, "quick_restart",
        "success" if success else "failed", msg,
    )

    status_icon = Emoji.SUCCESS if success else Emoji.ERROR
    await progress_msg.edit_text(
        f"{status_icon} {Fonts.bold(project['project_name'])}\n"
        f"{UI.DIVIDER_THIN}\n"
        f"{UI.BULLET} {msg}\n"
        f"{UI.DIVIDER_THIN}"
    )


@authorized
async def quick_logs_command(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Handle /ql <project_name> - Quick logs by project name."""
    args = context.args
    if not args:
        await update.message.reply_text(
            f"{Emoji.BOLT} {Fonts.small_caps('usage')}: /ql <project_name>"
        )
        return

    query = " ".join(args)
    user = update.effective_user

    results = search_engine.search_projects(user.id, query, limit=1)
    if not results:
        await update.message.reply_text(
            f"{Emoji.ERROR} {Fonts.small_caps('project not found')}: '{query}'"
        )
        return

    project = results[0]["project"]
    project_id = project["project_id"]

    logs = process_manager.get_logs(project_id, lines=25)
    is_running = process_manager.is_running(project_id)

    log_text = "\n".join(logs[-20:]) if logs else "No logs available."
    if len(log_text) > 3500:
        log_text = log_text[-3500:]

    status = Emoji.ONLINE if is_running else Emoji.OFFLINE

    text = (
        f"{Emoji.LOG} {status} {Fonts.bold(project['project_name'])}\n"
        f"{UI.DIVIDER_THIN}\n\n"
        f"```\n{log_text}\n```\n\n"
        f"{UI.DIVIDER_THIN}\n"
        f"{Emoji.CLOCK} {datetime.now().strftime('%H:%M:%S')}"
    )

    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                f"{Emoji.REFRESH} ʀᴇғʀᴇsʜ",
                callback_data=f"log_view_{project_id}",
            ),
            InlineKeyboardButton(
                f"📡 sᴛʀᴇᴀᴍ",
                callback_data=f"log_stream_start_{project_id}",
            ),
        ]
    ])

    await update.message.reply_text(text, reply_markup=keyboard)


# ┌─────────────────────────────────────────────────────────────────────────────┐
# │         SECTION 47: ENVIRONMENT VARIABLE MANAGER (ENHANCED)                 │
# └─────────────────────────────────────────────────────────────────────────────┘

@authorized
async def delenv_command(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Handle /delenv <project_id> <KEY> command."""
    args = context.args
    if not args or len(args) < 2:
        await update.message.reply_text(
            f"{Emoji.KEY} {Fonts.small_caps('usage')}: /delenv <project_id> <KEY>"
        )
        return

    project_id = args[0]
    key = args[1].strip()

    project = db.get_project(project_id)
    if not project:
        await update.message.reply_text(
            f"{Emoji.ERROR} {Fonts.small_caps('project not found!')}"
        )
        return

    env_vars = json.loads(project["env_vars"] or "{}")
    if key in env_vars:
        del env_vars[key]
        db.update_project(project_id, env_vars=json.dumps(env_vars))
        await update.message.reply_text(
            f"{Emoji.SUCCESS} {Fonts.small_caps('env var removed')}: {Fonts.mono(key)}\n"
            f"{UI.BULLET} {Fonts.small_caps('restart to apply changes')}"
        )
    else:
        await update.message.reply_text(
            f"{Emoji.WARNING} {Fonts.small_caps('key not found')}: {Fonts.mono(key)}"
        )


@authorized
async def listenv_command(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Handle /listenv <project_id> command."""
    args = context.args
    if not args:
        await update.message.reply_text(
            f"{Emoji.KEY} {Fonts.small_caps('usage')}: /listenv <project_id>"
        )
        return

    project_id = args[0]
    project = db.get_project(project_id)
    if not project:
        await update.message.reply_text(
            f"{Emoji.ERROR} {Fonts.small_caps('project not found!')}"
        )
        return

    env_vars = json.loads(project["env_vars"] or "{}")

    text = (
        f"{Emoji.KEY} {Fonts.bold('ENV VARS')} - {project['project_name']}\n"
        f"{UI.DIVIDER_THIN}\n\n"
    )

    if env_vars:
        for key, value in env_vars.items():
            masked = value[:2] + "*" * min(len(value) - 2, 10) if len(value) > 2 else "***"
            text += f"  {Emoji.KEY} {Fonts.mono(key)} = {masked}\n"
    else:
        text += f"{Emoji.INFO} {Fonts.small_caps('no env vars set.')}\n"

    text += (
        f"\n{UI.DIVIDER_THIN}\n"
        f"{UI.BULLET} /setenv {project_id} KEY=VALUE\n"
        f"{UI.BULLET} /delenv {project_id} KEY"
    )

    await update.message.reply_text(text)


# ┌─────────────────────────────────────────────────────────────────────────────┐
# │         SECTION 48: PROJECT RENAME & DESCRIPTION                            │
# └─────────────────────────────────────────────────────────────────────────────┘

@authorized
async def rename_command(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Handle /rename <project_id> <new_name> command."""
    args = context.args
    if not args or len(args) < 2:
        await update.message.reply_text(
            f"{Emoji.EDIT} {Fonts.small_caps('usage')}: /rename <project_id> <new_name>"
        )
        return

    project_id = args[0]
    new_name = " ".join(args[1:])

    project = db.get_project(project_id)
    if not project:
        await update.message.reply_text(
            f"{Emoji.ERROR} {Fonts.small_caps('project not found!')}"
        )
        return

    # Sanitize name
    safe_name = re.sub(r'[^\w\s\-.]', '', new_name).strip()
    if not safe_name:
        await update.message.reply_text(
            f"{Emoji.ERROR} {Fonts.small_caps('invalid project name!')}"
        )
        return

    old_name = project["project_name"]
    db.update_project(project_id, project_name=safe_name)

    await update.message.reply_text(
        f"{Emoji.SUCCESS} {Fonts.small_caps('project renamed')}\n"
        f"{UI.BULLET} {Fonts.small_caps('from')}: {old_name}\n"
        f"{UI.BULLET} {Fonts.small_caps('to')}: {Fonts.bold(safe_name)}"
    )


@authorized
async def describe_command(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Handle /describe <project_id> <description> command."""
    args = context.args
    if not args or len(args) < 2:
        await update.message.reply_text(
            f"{Emoji.EDIT} {Fonts.small_caps('usage')}: "
            f"/describe <project_id> <description>"
        )
        return

    project_id = args[0]
    description = " ".join(args[1:])[:500]

    project = db.get_project(project_id)
    if not project:
        await update.message.reply_text(
            f"{Emoji.ERROR} {Fonts.small_caps('project not found!')}"
        )
        return

    db.update_project(project_id, description=description)

    await update.message.reply_text(
        f"{Emoji.SUCCESS} {Fonts.small_caps('description updated')}\n"
        f"{UI.BULLET} {description[:100]}{'...' if len(description) > 100 else ''}"
    )


# ┌─────────────────────────────────────────────────────────────────────────────┐
# │         SECTION 49: BROADCAST & USER MANAGEMENT COMMANDS                    │
# └─────────────────────────────────────────────────────────────────────────────┘

@owner_only
@authorized
async def broadcast_command(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Handle /broadcast <message> - Send message to all users."""
    args = context.args
    if not args:
        await update.message.reply_text(
            f"{Emoji.BELL} {Fonts.small_caps('usage')}: /broadcast <message>"
        )
        return

    message_text = " ".join(args)
    users = db.get_all_users()

    broadcast_text = (
        f"{Emoji.BELL} {Fonts.bold('BROADCAST')} {Emoji.BELL}\n"
        f"{UI.DIVIDER_THIN}\n\n"
        f"{message_text}\n\n"
        f"{UI.DIVIDER_THIN}\n"
        f"{Emoji.CROWN} {Fonts.small_caps('from')} {OWNER_USERNAME}"
    )

    sent = 0
    failed = 0

    progress_msg = await update.message.reply_text(
        f"{Emoji.LOADING} {Fonts.small_caps('broadcasting to')} {len(users)} {Fonts.small_caps('users...')}"
    )

    for user_row in users:
        try:
            await context.bot.send_message(
                chat_id=user_row["user_id"],
                text=broadcast_text,
            )
            sent += 1
        except Exception:
            failed += 1

        # Rate limiting
        if (sent + failed) % 20 == 0:
            await asyncio.sleep(1)

    await progress_msg.edit_text(
        f"{Emoji.SUCCESS} {Fonts.bold('BROADCAST COMPLETE')}\n"
        f"{UI.DIVIDER_THIN}\n"
        f"  {Emoji.SUCCESS} {Fonts.small_caps('sent')}: {sent}\n"
        f"  {Emoji.ERROR} {Fonts.small_caps('failed')}: {failed}\n"
        f"  {Emoji.USERS} {Fonts.small_caps('total')}: {len(users)}\n"
        f"{UI.DIVIDER_THIN}"
    )


@owner_only
@authorized
async def unban_command(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Handle /unban <user_id> command."""
    args = context.args
    if not args:
        await update.message.reply_text(
            f"{Emoji.INFO} {Fonts.small_caps('usage')}: /unban <user_id>"
        )
        return

    try:
        target_id = int(args[0])
        db.unban_user(target_id)
        ALLOWED_USERS.add(target_id)
        rate_limiter.reset_user(target_id)
        await update.message.reply_text(
            f"{Emoji.SUCCESS} {Fonts.small_caps('user')} {target_id} {Fonts.small_caps('unbanned!')}"
        )
    except ValueError:
        await update.message.reply_text(
            f"{Emoji.ERROR} {Fonts.small_caps('invalid user id!')}"
        )


@owner_only
@authorized
async def removeuser_command(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Handle /removeuser <user_id> command."""
    args = context.args
    if not args:
        await update.message.reply_text(
            f"{Emoji.INFO} {Fonts.small_caps('usage')}: /removeuser <user_id>"
        )
        return

    try:
        target_id = int(args[0])
        if target_id == OWNER_ID:
            await update.message.reply_text(
                f"{Emoji.ERROR} {Fonts.small_caps('cannot remove the owner!')}"
            )
            return

        db.set_admin(target_id, False)
        ALLOWED_USERS.discard(target_id)
        await update.message.reply_text(
            f"{Emoji.SUCCESS} {Fonts.small_caps('user')} {target_id} "
            f"{Fonts.small_caps('access revoked!')}"
        )
    except ValueError:
        await update.message.reply_text(
            f"{Emoji.ERROR} {Fonts.small_caps('invalid user id!')}"
        )


# ┌─────────────────────────────────────────────────────────────────────────────┐
# │         SECTION 50: EXPORT & IMPORT PROJECT CONFIG                          │
# └─────────────────────────────────────────────────────────────────────────────┘

@authorized
async def export_config_command(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Handle /exportconfig <project_id> - Export project configuration."""
    args = context.args
    if not args:
        await update.message.reply_text(
            f"{Emoji.DOWNLOAD} {Fonts.small_caps('usage')}: /exportconfig <project_id>"
        )
        return

    project_id = args[0]
    project = db.get_project(project_id)
    if not project:
        await update.message.reply_text(
            f"{Emoji.ERROR} {Fonts.small_caps('project not found!')}"
        )
        return

    config = {
        "project_name": project["project_name"],
        "project_type": project["project_type"],
        "main_file": project["main_file"],
        "description": project["description"],
        "auto_restart": bool(project["auto_restart"]),
        "max_restarts": project["max_restarts"],
        "env_vars": json.loads(project["env_vars"] or "{}"),
        "config": json.loads(project["config_json"] or "{}"),
        "exported_at": datetime.now().isoformat(),
        "bot_version": BOT_VERSION,
    }

    config_json = json.dumps(config, indent=2, ensure_ascii=False)
    filename = f"{project['project_name']}_config.json"

    config_bytes = io.BytesIO(config_json.encode("utf-8"))
    config_bytes.name = filename

    await context.bot.send_document(
        chat_id=update.effective_chat.id,
        document=config_bytes,
        filename=filename,
        caption=(
            f"{Emoji.DOWNLOAD} {Fonts.small_caps('project config exported')}\n"
            f"{UI.BULLET} {project['project_name']}"
        ),
    )


# ┌─────────────────────────────────────────────────────────────────────────────┐
# │         SECTION 51: SYSTEM COMMANDS                                         │
# └─────────────────────────────────────────────────────────────────────────────┘

@owner_only
@authorized
async def sysinfo_command(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Handle /sysinfo - Detailed system information."""
    plat = system_monitor.get_platform_info()
    cpu = system_monitor.get_cpu_info()
    mem = system_monitor.get_memory_info()
    disk = system_monitor.get_disk_info()
    net = system_monitor.get_network_info()
    uptime = system_monitor.get_uptime()

    # Process info
    proc_count = len(psutil.pids())
    boot_time = datetime.fromtimestamp(psutil.boot_time()).strftime(
        "%Y-%m-%d %H:%M:%S"
    )

    # Python environment
    py_path = sys.executable
    py_version = platform.python_version()

    # Bot runtime
    bot_uptime = time.time() - psutil.Process(os.getpid()).create_time()

    text = (
        f"{Emoji.TERMINAL} {Fonts.bold('SYSTEM INFORMATION')} {Emoji.TERMINAL}\n"
        f"{UI.DIVIDER_STAR}\n\n"
        #
        f"{Emoji.GLOBE} {Fonts.small_caps('platform')}:\n"
        f"  {UI.TRIANGLE} {Fonts.small_caps('os')}: {plat['system']} {plat['release']}\n"
        f"  {UI.TRIANGLE} {Fonts.small_caps('version')}: {plat['version'][:50]}\n"
        f"  {UI.TRIANGLE} {Fonts.small_caps('machine')}: {plat['machine']}\n"
        f"  {UI.TRIANGLE} {Fonts.small_caps('hostname')}: {plat['hostname']}\n"
        f"  {UI.TRIANGLE} {Fonts.small_caps('processor')}: {plat['processor'][:40]}\n\n"
        #
        f"{Emoji.CPU} {Fonts.small_caps('cpu details')}:\n"
        f"  {UI.TRIANGLE} {Fonts.small_caps('cores')}: {cpu['count_physical']}P / {cpu['count_logical']}L\n"
        f"  {UI.TRIANGLE} {Fonts.small_caps('freq')}: {cpu['freq_current']:.0f} / {cpu['freq_max']:.0f} MHz\n"
        f"  {UI.TRIANGLE} {Fonts.small_caps('usage')}: {cpu['percent']}%\n"
        f"  {UI.TRIANGLE} {Fonts.small_caps('per-core')}: {', '.join(f'{x:.0f}%' for x in cpu['per_cpu'][:8])}\n"
        f"  {UI.TRIANGLE} {Fonts.small_caps('load')}: {cpu['load_avg_1']:.2f} / {cpu['load_avg_5']:.2f} / {cpu['load_avg_15']:.2f}\n\n"
        #
        f"{Emoji.RAM} {Fonts.small_caps('memory')}:\n"
        f"  {UI.TRIANGLE} {Fonts.small_caps('total')}: {UI.format_bytes(mem['total'])}\n"
        f"  {UI.TRIANGLE} {Fonts.small_caps('used')}: {UI.format_bytes(mem['used'])} ({mem['percent']}%)\n"
        f"  {UI.TRIANGLE} {Fonts.small_caps('available')}: {UI.format_bytes(mem['available'])}\n"
        f"  {UI.TRIANGLE} {Fonts.small_caps('swap')}: {UI.format_bytes(mem['swap_used'])} / {UI.format_bytes(mem['swap_total'])}\n\n"
        #
        f"{Emoji.DISK} {Fonts.small_caps('disk')}:\n"
        f"  {UI.TRIANGLE} {Fonts.small_caps('total')}: {UI.format_bytes(disk['total'])}\n"
        f"  {UI.TRIANGLE} {Fonts.small_caps('used')}: {UI.format_bytes(disk['used'])} ({disk['percent']}%)\n"
        f"  {UI.TRIANGLE} {Fonts.small_caps('free')}: {UI.format_bytes(disk['free'])}\n"
        f"  {UI.TRIANGLE} {Fonts.small_caps('read')}: {UI.format_bytes(disk['read_bytes'])}\n"
        f"  {UI.TRIANGLE} {Fonts.small_caps('written')}: {UI.format_bytes(disk['write_bytes'])}\n\n"
        #
        f"{Emoji.NETWORK} {Fonts.small_caps('network')}:\n"
        f"  {UI.TRIANGLE} {Fonts.small_caps('sent')}: {UI.format_bytes(net['bytes_sent'])}\n"
        f"  {UI.TRIANGLE} {Fonts.small_caps('received')}: {UI.format_bytes(net['bytes_recv'])}\n"
        f"  {UI.TRIANGLE} {Fonts.small_caps('packets')}: ↑{net['packets_sent']} ↓{net['packets_recv']}\n"
        f"  {UI.TRIANGLE} {Fonts.small_caps('errors')}: ↑{net['errout']} ↓{net['errin']}\n\n"
        #
        f"{Emoji.GEAR} {Fonts.small_caps('runtime')}:\n"
        f"  {UI.TRIANGLE} {Fonts.small_caps('python')}: {py_version}\n"
        f"  {UI.TRIANGLE} {Fonts.small_caps('path')}: {py_path[:40]}\n"
        f"  {UI.TRIANGLE} {Fonts.small_caps('system processes')}: {proc_count}\n"
        f"  {UI.TRIANGLE} {Fonts.small_caps('boot time')}: {boot_time}\n"
        f"  {UI.TRIANGLE} {Fonts.small_caps('system uptime')}: {UI.format_uptime(uptime)}\n"
        f"  {UI.TRIANGLE} {Fonts.small_caps('bot uptime')}: {UI.format_uptime(bot_uptime)}\n"
        f"  {UI.TRIANGLE} {Fonts.small_caps('managed processes')}: {process_manager.running_count}\n\n"
        f"{UI.DIVIDER_STAR}"
    )

    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton(f"{Emoji.CHART} ᴍᴇᴛʀɪᴄs", callback_data="menu_metrics"),
            InlineKeyboardButton(f"{Emoji.REFRESH} ʀᴇғʀᴇsʜ", callback_data="cb_sysinfo"),
        ],
        [
            InlineKeyboardButton(f"{Emoji.HOME} ᴍᴇɴᴜ", callback_data="menu_main"),
        ],
    ])

    if update.message:
        await update.message.reply_text(text, reply_markup=keyboard)
    elif update.callback_query:
        try:
            await update.callback_query.edit_message_text(text, reply_markup=keyboard)
        except BadRequest:
            pass


# ┌─────────────────────────────────────────────────────────────────────────────┐
# │         SECTION 52: FINAL ENHANCED CALLBACK ROUTER (COMPLETE)               │
# └─────────────────────────────────────────────────────────────────────────────┘

_prev_callback_router = enhanced_callback_router


@authorized
async def final_callback_router(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Final comprehensive callback router with all features."""
    query = update.callback_query
    await query.answer()
    data = query.data

    # Analytics refresh
    if data == "cb_analytics":
        await analytics_command(update, context)
        return

    # Sysinfo refresh
    if data == "cb_sysinfo":
        await sysinfo_command(update, context)
        return

    # Delegate to previous router
    await _prev_callback_router(update, context)


# Replace callback router
callback_router = final_callback_router


# ┌─────────────────────────────────────────────────────────────────────────────┐
# │         SECTION 53: COMPLETE APPLICATION BUILDER (FINAL)                    │
# └─────────────────────────────────────────────────────────────────────────────┘

def build_final_application() -> Application:
    """Build the complete production application with ALL features."""

    application = (
        ApplicationBuilder()
        .token(BOT_TOKEN)
        .post_init(enhanced_post_init)
        .post_shutdown(enhanced_post_shutdown)
        .concurrent_updates(True)
        .read_timeout(30)
        .write_timeout(30)
        .connect_timeout(30)
        .build()
    )

    # ═══════════════════════════════════════
    # COMMAND HANDLERS (Alphabetical)
    # ═══════════════════════════════════════
    commands = {
        "start": start_command,
        "help": help_command,
        "health": health_command,
        "status": status_command,
        "deploy": deploy_command,
        "logs": logs_command,
        "files": files_command,
        "upload": upload_command,
        "admin": admin_command,
        "adduser": adduser_command,
        "removeuser": removeuser_command,
        "ban": ban_command,
        "unban": unban_command,
        "stats": stats_command,
        "setenv": setenv_command,
        "delenv": delenv_command,
        "listenv": listenv_command,
        "setmain": setmain_command,
        "terminal": terminal_command,
        "endterm": endterm_command,
        "search": search_command,
        "searchfile": searchfile_command,
        "searchlog": searchlog_command,
        "analytics": analytics_command,
        "sysinfo": sysinfo_command,
        "rename": rename_command,
        "describe": describe_command,
        "exportconfig": export_config_command,
        "broadcast": broadcast_command,
        # Quick commands
        "qd": quick_deploy_command,
        "qs": quick_stop_command,
        "qr": quick_restart_command,
        "ql": quick_logs_command,
    }

    for cmd_name, handler_func in commands.items():
        application.add_handler(CommandHandler(cmd_name, handler_func))

    # ═══════════════════════════════════════
    # CALLBACK QUERY HANDLER
    # ═══════════════════════════════════════
    application.add_handler(CallbackQueryHandler(final_callback_router))

    # ═══════════════════════════════════════
    # MESSAGE HANDLERS
    # ═══════════════════════════════════════

    # Document upload
    application.add_handler(
        MessageHandler(filters.Document.ALL, handle_document_upload)
    )

    # Terminal commands ($ prefix)
    application.add_handler(
        MessageHandler(
            filters.TEXT & filters.Regex(r"^\$\s*.+") & ~filters.COMMAND,
            handle_terminal_message,
        )
    )

    # ═══════════════════════════════════════
    # ERROR HANDLER
    # ═══════════════════════════════════════
    application.add_error_handler(error_handler)

    return application


# ┌─────────────────────────────────────────────────────────────────────────────┐
# │         SECTION 54: PRODUCTION MAIN ENTRY (FINAL)                           │
# └─────────────────────────────────────────────────────────────────────────────┘

def main():
    """
    ╔═══════════════════════════════════════════════════╗
    ║         RUHI X HOSTING - FINAL PRODUCTION         ║
    ║         Complete Telegram Hosting Bot              ║
    ╚═══════════════════════════════════════════════════╝
    """
    banner = r"""
 ═══════════════════════════════════════════════════════════════════════════════
 ██████╗ ██╗   ██╗██╗  ██╗██╗    ██╗  ██╗    ██╗  ██╗ ██████╗ ███████╗████████╗
 ██╔══██╗██║   ██║██║  ██║██║    ╚██╗██╔╝    ██║  ██║██╔═══██╗██╔════╝╚══██╔══╝
 ██████╔╝██║   ██║███████║██║     ╚███╔╝     ███████║██║   ██║███████╗   ██║
 ██╔══██╗██║   ██║██╔══██║██║     ██╔██╗     ██╔══██║██║   ██║╚════██║   ██║
 ██║  ██║╚██████╔╝██║  ██║██║    ██╔╝ ██╗    ██║  ██║╚██████╔╝███████║   ██║
 ╚═╝  ╚═╝ ╚═════╝ ╚═╝  ╚═╝╚═╝    ╚═╝  ╚═╝    ╚═╝  ╚═╝ ╚═════╝ ╚══════╝   ╚═╝
 ═══════════════════════════════════════════════════════════════════════════════
    """
    print(banner)

    info = f"""
 ┌─────────────────────────────────────────────────────────────────────────────┐
 │                    RUHI X HOSTING - PRODUCTION BUILD                        │
 │                                                                             │
 │  Version  : {BOT_VERSION:<12}  Build  : {BOT_BUILD:<15}              │
 │  Owner    : {OWNER_USERNAME:<55}│
 │  Python   : {platform.python_version():<55}│
 │  Platform : {platform.system() + ' ' + platform.release():<55}│
 │  Database : {str(DATABASE_PATH.name):<55}│
 │  Projects : {str(PROJECTS_DIR):<55}│
 │                                                                             │
 │  ┌───────────────────────────────────────────────────────────────────────┐  │
 │  │  FEATURES ({len(FEATURE_LIST)} total):                                              │  │"""

    FEATURE_LIST = [
        "File Manager (ZIP/TAR upload, browse, download, delete)",
        "Deploy Console (start/stop/restart with auto-detect)",
        "Live Log Streaming (auto-refresh message edits)",
        "System Health Monitor (CPU/RAM/Disk/Network)",
        "Process Watchdog (auto-recovery, exponential backoff)",
        "Backup & Restore (rotation, download, restore)",
        "Dependency Manager (pip/npm/maven auto-install)",
        "Interactive Terminal ($ commands in chat)",
        "Port Manager (auto-allocation for web projects)",
        "Search Engine (fuzzy project/file/log search)",
        "Analytics Dashboard (deployment stats, rankings)",
        "Rate Limiter (anti-flood, token bucket)",
        "Notification System (alerts, read/unread)",
        "Multi-Language (Python, Node.js, Java)",
        "SQLite Database (8 tables, WAL mode)",
        "Quick Commands (/qd, /qs, /qr, /ql)",
        "User Management (add/ban/unban/broadcast)",
        "ASCII Metrics Graphs (historical charts)",
        "Beautiful Unicode UI (small caps, styled fonts)",
        "Config Export/Import (JSON project configs)",
    ]

    for feat in FEATURE_LIST:
        print(f" │  │    ★ {feat:<65}│  │")

    print(f""" │  └───────────────────────────────────────────────────────────────────────┘  │
 │                                                                             │
 │  COMMANDS ({len(commands_list)} total):                                                     │""")

    commands_list = [
        "/start", "/help", "/health", "/deploy", "/logs", "/files",
        "/upload", "/status", "/admin", "/stats", "/analytics",
        "/search", "/searchfile", "/searchlog", "/terminal",
        "/setenv", "/delenv", "/listenv", "/setmain",
        "/rename", "/describe", "/exportconfig",
        "/adduser", "/removeuser", "/ban", "/unban", "/broadcast",
        "/qd", "/qs", "/qr", "/ql", "/sysinfo",
    ]

    # Print commands in rows of 4
    for i in range(0, len(commands_list), 4):
        row = commands_list[i:i+4]
        row_str = "  ".join(f"{c:<16}" for c in row)
        print(f" │    {row_str:<67}│")

    print(f""" │                                                                             │
 └─────────────────────────────────────────────────────────────────────────────┘
    """)

    # ── Validation ──
    errors = []
    warnings = []

    if BOT_TOKEN == "YOUR_BOT_TOKEN_HERE":
        errors.append("BOT_TOKEN not configured! Edit the variable at the top of hosting.py")

    if OWNER_ID == 123456789:
        warnings.append("OWNER_ID not configured! Set your Telegram user ID")

    # Dependency check
    print("  Checking dependencies...")
    required = {
        "telegram": "python-telegram-bot>=20.0",
        "psutil": "psutil>=5.0",
    }

    for module, pip_name in required.items():
        try:
            mod = __import__(module)
            version = getattr(mod, "__version__", "unknown")
            print(f"    ✅ {pip_name} (v{version})")
        except ImportError:
            errors.append(f"Missing: pip install {pip_name}")
            print(f"    ❌ {pip_name}")

    # Directory check
    print("\n  Checking directories...")
    for d in [PROJECTS_DIR, UPLOADS_DIR, LOGS_DIR, BACKUPS_DIR, TEMP_DIR]:
        status = "✅" if d.exists() else "❌"
        print(f"    {status} {d.name}/")

    # Database check
    print(f"\n  Database: {'✅' if DATABASE_PATH.exists() else '🆕'} {DATABASE_PATH.name}")
    print(f"  Schema version: {DatabaseManager.SCHEMA_VERSION}")

    if errors:
        print(f"\n  {'=' * 50}")
        print(f"  ❌ ERRORS ({len(errors)}):")
        for err in errors:
            print(f"    → {err}")
        print(f"  {'=' * 50}\n")
        sys.exit(1)

    if warnings:
        print(f"\n  ⚠️  WARNINGS ({len(warnings)}):")
        for warn in warnings:
            print(f"    → {warn}")

    print(f"\n  ✅ All checks passed!")
    print(f"  🚀 Starting {BOT_NAME}...\n")
    print(f"  {'═' * 60}\n")

    # ── Build & Run ──
    app = build_final_application()
    app.run_polling(
        allowed_updates=Update.ALL_TYPES,
        drop_pending_updates=True,
        close_loop=False,
    )


if __name__ == "__main__":
    main()    