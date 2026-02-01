"""
============================================================================
TELEGRAM UPTIME BOT - MAIN APPLICATION (COMPLETE — Parts 1 + 2 + 3)
============================================================================
This is the FINAL main.py that integrates every layer of the bot:

    Layer 1 — Core & Database        (Part 1)
        • Settings (Pydantic)
        • SQLAlchemy async engine + models
        • DatabaseManager + Repositories
        • Logging, Validators, Helpers

    Layer 2 — Bot Logic & UI         (Part 2)
        • aiogram Bot + Dispatcher
        • User command handlers  (/start /add /remove /list /stats …)
        • Admin panel handlers   (/admin /users /broadcast …)
        • Inline keyboards & FSM workflows

    Layer 3 — Monitoring & Infra     (Part 3)  ← THIS FILE COMPLETES IT
        • MonitoringEngine   — async HTTP/TCP/DNS/SSL checkers
        • AlertManager       — cooldown, rate-limit, Telegram delivery
        • SelfPinger         — keeps Render instance alive
        • HealthServer       — aiohttp server on PORT for Render
        • Scheduler          — periodic background jobs

Startup Order
-------------
1.  Load settings & configure logging
2.  Initialize DatabaseManager (create tables if needed)
3.  Create aiogram Bot + Dispatcher, register all routers
4.  Wire up AlertManager (needs Bot for sending)
5.  Wire up MonitoringEngine (needs DB + AlertManager)
6.  Wire up Scheduler (needs DB + AlertManager)
7.  Start HealthServer (aiohttp, non-blocking)
8.  Start SelfPinger
9.  Start AlertManager dispatch loop
10. Start Scheduler
11. Start MonitoringEngine sweep loop
12. Start aiogram polling (this blocks until shutdown)

Shutdown Order (reverse)
-------------------------
On KeyboardInterrupt or SIGTERM:
    Stop monitoring engine → stop scheduler → stop alert manager →
    stop self-pinger → stop health server → close DB → exit

Author: Professional Development Team
Version: 1.0.0
License: MIT
============================================================================
"""

import asyncio
import signal
import sys
from pathlib import Path
from typing import Optional

# ---------------------------------------------------------------------------
# Path setup — ensure the project root is importable regardless of CWD
# ---------------------------------------------------------------------------
sys.path.insert(0, str(Path(__file__).parent))

# ---------------------------------------------------------------------------
# Project imports
# ---------------------------------------------------------------------------
from config.settings import get_settings
from database.manager import DatabaseManager
from utils.logger import get_logger, setup_logging

# Part 2 imports (bot)
from bot.core import BotManager
from bot.handlers.user import router as user_router
from bot.handlers.admin import router as admin_router
from bot.handlers.callbacks import router as callback_router

# Part 3 imports (monitoring infrastructure)
from monitoring.monitor import MonitoringEngine
from monitoring.alerts import AlertManager
from monitoring.self_ping import HealthServer, SelfPinger
from monitoring.scheduler import Scheduler


# ---------------------------------------------------------------------------
# Bootstrap logging before anything else runs
# ---------------------------------------------------------------------------
setup_logging()
logger = get_logger("Main")


# ============================================================================
# APPLICATION CLASS
# ============================================================================

class UptimeBotApplication:
    """
    Top-level application orchestrator.

    Owns every subsystem and is the single place that knows the startup /
    shutdown order.  All subsystems communicate through the instances stored
    here — no global singletons (except Settings, which is intentionally
    cached via lru_cache).
    """

    def __init__(self):
        self.settings = get_settings()

        # --- subsystems (populated during startup) ---
        self.db_manager: Optional[DatabaseManager] = None
        self.bot_manager: Optional[BotManager] = None
        self.alert_manager: Optional[AlertManager] = None
        self.monitoring_engine: Optional[MonitoringEngine] = None
        self.scheduler: Optional[Scheduler] = None
        self.health_server: Optional[HealthServer] = None
        self.self_pinger: Optional[SelfPinger] = None

        # --- lifecycle flag ---
        self._is_running = False

        self._print_banner()

    # ------------------------------------------------------------------
    # BANNER
    # ------------------------------------------------------------------

    def _print_banner(self) -> None:
        banner = f"""
╔══════════════════════════════════════════════════════════════════════════╗
║                                                                          ║
║          🚀  TELEGRAM UPTIME MONITORING BOT  v{self.settings.BOT_VERSION:<20}       ║
║                                                                          ║
║   Monitoring Engine  •  Alert System  •  Self-Ping  •  Admin Panel       ║
║                                                                          ║
║   Database : {self.settings.DB_TYPE:<10}   Port : {self.settings.PORT:<8}                          ║
║   Owner ID : {self.settings.OWNER_ID:<50}     ║
║                                                                          ║
╚══════════════════════════════════════════════════════════════════════════╝
"""
        logger.info(banner)

    # ==================================================================
    # PHASE 1 — DATABASE
    # ==================================================================

    async def _init_database(self) -> bool:
        """Initialize the database manager and verify connectivity."""
        logger.info("── Phase 1: Database ─────────────────────────────")
        try:
            self.db_manager = DatabaseManager(self.settings)
            await self.db_manager.initialize()

            if not await self.db_manager.check_connection():
                logger.error("✗ Database connection check failed")
                return False

            db_info = await self.db_manager.get_database_info()
            logger.info(
                f"  ✓ Connected to {self.settings.DB_TYPE} — "
                f"users={db_info.get('users', 0)}, "
                f"links={db_info.get('links', 0)}, "
                f"logs={db_info.get('logs', 0)}"
            )
            return True

        except Exception as e:
            logger.error(f"  ✗ Database init failed: {e}", exc_info=True)
            return False

    # ==================================================================
    # PHASE 2 — BOT (aiogram)
    # ==================================================================

    async def _init_bot(self) -> bool:
        """Create the aiogram Bot, register routers, inject dependencies."""
        logger.info("── Phase 2: Telegram Bot ─────────────────────────")
        try:
            self.bot_manager = BotManager(self.db_manager)

            if not await self.bot_manager.initialize():
                logger.error("  ✗ BotManager.initialize() returned False")
                return False

            # Register routers (Part 2 handlers)
            self.bot_manager.dp.include_router(user_router)
            self.bot_manager.dp.include_router(admin_router)
            self.bot_manager.dp.include_router(callback_router)

            # Inject shared dependencies into the dispatcher's workflow_data
            # so that handler functions can receive them as keyword arguments
            self.bot_manager.dp.workflow_data.update({
                "db_manager": self.db_manager,
                "bot": self.bot_manager.bot,
            })

            logger.info("  ✓ Bot initialized, all routers registered")
            return True

        except Exception as e:
            logger.error(f"  ✗ Bot init failed: {e}", exc_info=True)
            return False

    # ==================================================================
    # PHASE 3 — MONITORING INFRASTRUCTURE
    # ==================================================================

    async def _init_monitoring(self) -> bool:
        """Wire up AlertManager, MonitoringEngine, Scheduler."""
        logger.info("── Phase 3: Monitoring Infrastructure ────────────")
        try:
            # AlertManager needs the Bot instance to send Telegram messages
            bot_instance = (
                self.bot_manager.bot if self.bot_manager else None
            )
            self.alert_manager = AlertManager(
                db_manager=self.db_manager,
                bot=bot_instance,
            )

            # MonitoringEngine needs DB + AlertManager
            self.monitoring_engine = MonitoringEngine(
                db_manager=self.db_manager,
                alert_manager=self.alert_manager,
            )

            # Scheduler needs DB + AlertManager (for SSL sweep alerts)
            self.scheduler = Scheduler(
                db_manager=self.db_manager,
                alert_manager=self.alert_manager,
            )

            logger.info(
                "  ✓ AlertManager, MonitoringEngine, Scheduler created"
            )
            return True

        except Exception as e:
            logger.error(f"  ✗ Monitoring init failed: {e}", exc_info=True)
            return False

    # ==================================================================
    # PHASE 4 — RENDER KEEP-ALIVE
    # ==================================================================

    async def _init_render(self) -> bool:
        """Set up HealthServer and SelfPinger for Render deployment."""
        logger.info("── Phase 4: Render Keep-Alive ────────────────────")
        try:
            self.health_server = HealthServer(self.settings)
            self.self_pinger = SelfPinger(self.settings)
            logger.info("  ✓ HealthServer and SelfPinger created")
            return True

        except Exception as e:
            logger.error(f"  ✗ Render init failed: {e}", exc_info=True)
            return False

    # ==================================================================
    # FULL STARTUP SEQUENCE
    # ==================================================================

    async def startup(self) -> bool:
        """
        Execute the complete startup sequence.
        Returns False (and logs errors) if any critical phase fails.
        """
        logger.info("=" * 74)
        logger.info("  STARTING UP …")
        logger.info("=" * 74)

        # Phase 1 — DB (critical)
        if not await self._init_database():
            return False

        # Phase 2 — Bot (critical)
        if not await self._init_bot():
            return False

        # Phase 3 — Monitoring (critical)
        if not await self._init_monitoring():
            return False

        # Phase 4 — Render keep-alive (non-critical on non-Render hosts)
        if not await self._init_render():
            logger.warning("  ⚠ Render keep-alive init failed — continuing without it")

        # --- START background services ---
        logger.info("── Starting background services ───────────────────")

        # Start HealthServer (aiohttp)
        if self.health_server:
            await self.health_server.start()

        # Start SelfPinger
        if self.self_pinger:
            await self.self_pinger.start()

        # Start AlertManager dispatch loop
        if self.alert_manager:
            await self.alert_manager.start()

        # Start Scheduler
        if self.scheduler:
            await self.scheduler.start()

        # Start MonitoringEngine sweep loop
        if self.monitoring_engine:
            await self.monitoring_engine.start()

        self._is_running = True

        logger.info("=" * 74)
        logger.info("  ✓ ALL SYSTEMS OPERATIONAL")
        logger.info("=" * 74)
        logger.info(
            f"  Bot: {self.settings.BOT_NAME} v{self.settings.BOT_VERSION}"
        )
        logger.info(
            f"  Health endpoint: http://0.0.0.0:{self.settings.PORT}/health"
        )
        logger.info(
            f"  Monitoring: {self.settings.MAX_CONCURRENT_PINGS} concurrent, "
            f"{self.settings.DEFAULT_PING_INTERVAL}s default interval"
        )
        logger.info("=" * 74)

        return True

    # ==================================================================
    # SHUTDOWN SEQUENCE
    # ==================================================================

    async def shutdown(self) -> None:
        """
        Graceful shutdown in reverse order.
        Each step is wrapped in try/except so a failure in one subsystem
        doesn't prevent the others from cleaning up.
        """
        logger.info("=" * 74)
        logger.info("  SHUTTING DOWN …")
        logger.info("=" * 74)

        self._is_running = False

        # 1. Stop monitoring engine (finish in-flight checks)
        if self.monitoring_engine:
            try:
                await self.monitoring_engine.stop()
                logger.info("  ✓ MonitoringEngine stopped")
            except Exception as e:
                logger.error(f"  ✗ MonitoringEngine stop error: {e}")

        # 2. Stop scheduler
        if self.scheduler:
            try:
                await self.scheduler.stop()
                logger.info("  ✓ Scheduler stopped")
            except Exception as e:
                logger.error(f"  ✗ Scheduler stop error: {e}")

        # 3. Stop alert manager (drains queue)
        if self.alert_manager:
            try:
                await self.alert_manager.stop()
                logger.info("  ✓ AlertManager stopped")
            except Exception as e:
                logger.error(f"  ✗ AlertManager stop error: {e}")

        # 4. Stop self-pinger
        if self.self_pinger:
            try:
                await self.self_pinger.stop()
                logger.info("  ✓ SelfPinger stopped")
            except Exception as e:
                logger.error(f"  ✗ SelfPinger stop error: {e}")

        # 5. Stop health server
        if self.health_server:
            try:
                await self.health_server.stop()
                logger.info("  ✓ HealthServer stopped")
            except Exception as e:
                logger.error(f"  ✗ HealthServer stop error: {e}")

        # 6. Stop bot polling
        if self.bot_manager:
            try:
                await self.bot_manager.stop_polling()
                logger.info("  ✓ Bot polling stopped")
            except Exception as e:
                logger.error(f"  ✗ Bot stop error: {e}")

        # 7. Close database connections
        if self.db_manager:
            try:
                await self.db_manager.close()
                logger.info("  ✓ Database connections closed")
            except Exception as e:
                logger.error(f"  ✗ Database close error: {e}")

        logger.info("=" * 74)
        logger.info("  ✓ SHUTDOWN COMPLETE")
        logger.info("=" * 74)

    # ==================================================================
    # RUN
    # ==================================================================

    async def run(self) -> None:
        """
        Main run method.  After startup, this starts aiogram polling which
        blocks until the bot is stopped (e.g., via Ctrl+C or SIGTERM).
        """
        if self.bot_manager:
            logger.info("  Starting aiogram polling…")
            await self.bot_manager.start_polling()
        else:
            # Fallback: just keep the loop alive if bot isn't available
            logger.warning("  No bot manager — running in headless mode")
            while self._is_running:
                await asyncio.sleep(1)


# ============================================================================
# SIGNAL HANDLER SETUP
# ============================================================================

_app_instance: Optional[UptimeBotApplication] = None


def _install_signal_handlers(loop: asyncio.AbstractEventLoop) -> None:
    """
    Install SIGTERM / SIGINT handlers so that the bot shuts down gracefully
    even when killed by the OS (e.g., Render restart).
    """
    async def _handle_signal():
        logger.info("  ⚡ Signal received — initiating graceful shutdown…")
        if _app_instance:
            await _app_instance.shutdown()
        loop.stop()

    for sig in (signal.SIGTERM, signal.SIGINT):
        try:
            loop.add_signal_handler(
                sig,
                lambda: asyncio.ensure_future(_handle_signal())
            )
        except (NotImplementedError, OSError):
            # Signal handlers aren't supported on Windows or in some
            # restricted environments — fall back to KeyboardInterrupt
            pass


# ============================================================================
# MAIN ENTRY POINT
# ============================================================================

async def main() -> None:
    """
    Async main — creates the app, starts it, and runs until shutdown.
    """
    global _app_instance

    app = UptimeBotApplication()
    _app_instance = app

    # Install OS signal handlers for graceful shutdown
    loop = asyncio.get_event_loop()
    _install_signal_handlers(loop)

    # Startup
    if not await app.startup():
        logger.error("  ✗ Startup failed — exiting")
        sys.exit(1)

    # Run (blocks on aiogram polling)
    try:
        await app.run()
    except KeyboardInterrupt:
        logger.info("  ⚡ KeyboardInterrupt received")
    except Exception as e:
        logger.error(f"  ✗ Unhandled error in run: {e}", exc_info=True)
    finally:
        await app.shutdown()


# ============================================================================
# SCRIPT ENTRY POINT
# ============================================================================

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        # asyncio.run() already handles this, but just in case
        pass
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)
