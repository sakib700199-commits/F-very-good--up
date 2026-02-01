"""
============================================================================
TELEGRAM UPTIME BOT - SELF-PING & RENDER KEEP-ALIVE
============================================================================
Render's free tier spins down instances after 15 minutes of inactivity.
This module solves that problem with two cooperating components:

1.  HealthServer
    A lightweight aiohttp HTTP server that binds to the port Render expects
    (env var PORT, default 10000).  It exposes two endpoints:
        GET /          → 200 "OK"  (basic liveness)
        GET /health    → 200 JSON  { status, uptime, checks_performed, ... }
        GET /ping      → 200 "pong"  (the target our self-pinger hits)

    Render sees HTTP traffic on this port and keeps the instance alive.

2.  SelfPinger
    An asyncio background task that periodically sends an HTTP GET to
    the bot's own /ping endpoint.  The interval is configurable via
    SELF_PING_INTERVAL (default 4 minutes — well under the 15-minute
    spin-down threshold).

    If the bot is deployed on Render, SELF_PING_URL is set automatically
    from the RENDER_EXTERNAL_URL env var.  If not set, the pinger falls
    back to hitting localhost:{PORT}/ping.

Why both?
---------
The HealthServer alone would keep the instance alive *if* Render counts
its own health checks as traffic — but Render's docs say it doesn't.
The SelfPinger generates real outbound → inbound HTTP traffic through
Render's load balancer, which *does* count.  Having both gives belt-and-
suspenders reliability.

Author: Professional Development Team
Version: 1.0.0
License: MIT
============================================================================
"""

import asyncio
import time
import os
from datetime import datetime
from typing import Optional, Dict, Any

from aiohttp import web
import httpx

from config.settings import Settings, get_settings
from utils.logger import get_logger


logger = get_logger("SelfPing")


# ============================================================================
# HEALTH SERVER
# ============================================================================

class HealthServer:
    """
    Lightweight aiohttp server that keeps the Render instance awake.

    It also exposes a /health endpoint that the admin panel can call to
    verify the bot is still responsive — useful for monitoring the
    monitor itself.

    Attributes
    ----------
    _app : aiohttp.web.Application
    _runner : aiohttp.web.AppRunner
    _site : aiohttp.web.TCPSite
    _start_time : float          — epoch seconds when the server started
    _request_count : int         — total requests served
    """

    def __init__(self, settings: Settings):
        self.settings = settings
        self._port = settings.PORT
        self._app = web.Application()
        self._runner: Optional[web.AppRunner] = None
        self._site: Optional[web.TCPSite] = None
        self._start_time: float = 0.0
        self._request_count: int = 0

        # Register routes
        self._app.router.add_get("/", self._handle_root)
        self._app.router.add_get("/health", self._handle_health)
        self._app.router.add_get("/ping", self._handle_ping)
        self._app.router.add_get("/status", self._handle_status)

    async def start(self) -> None:
        """Bind and start serving."""
        self._start_time = time.time()
        self._runner = web.AppRunner(self._app)
        await self._runner.setup()
        self._site = web.TCPSite(self._runner, "0.0.0.0", self._port)
        await self._site.start()
        logger.info(f"✓ HealthServer listening on port {self._port}")

    async def stop(self) -> None:
        """Gracefully shut down the server."""
        if self._runner:
            await self._runner.cleanup()
            self._runner = None
            self._site = None
        logger.info("✓ HealthServer stopped")

    # ------------------------------------------------------------------
    # ROUTE HANDLERS
    # ------------------------------------------------------------------

    async def _handle_root(self, request: web.Request) -> web.Response:
        """GET / — simple liveness probe."""
        self._request_count += 1
        return web.Response(text="OK", status=200)

    async def _handle_ping(self, request: web.Request) -> web.Response:
        """GET /ping — the endpoint SelfPinger hits."""
        self._request_count += 1
        return web.Response(text="pong", status=200)

    async def _handle_health(self, request: web.Request) -> web.Response:
        """GET /health — detailed health JSON."""
        self._request_count += 1
        uptime_seconds = time.time() - self._start_time if self._start_time else 0

        health = {
            "status": "healthy",
            "uptime_seconds": round(uptime_seconds, 1),
            "uptime_human": _seconds_to_human(int(uptime_seconds)),
            "requests_served": self._request_count,
            "timestamp": datetime.utcnow().isoformat(),
            "port": self._port,
            "bot_name": self.settings.BOT_NAME,
            "bot_version": self.settings.BOT_VERSION,
        }

        return web.json_response(health, status=200)

    async def _handle_status(self, request: web.Request) -> web.Response:
        """GET /status — alias for /health (some monitors prefer this path)."""
        return await self._handle_health(request)


# ============================================================================
# SELF PINGER
# ============================================================================

class SelfPinger:
    """
    Background task that pings the bot's own /ping endpoint on a regular
    interval to prevent Render from spinning down the instance.

    The target URL is resolved in this priority order:
    1.  settings.SELF_PING_URL  (explicitly configured)
    2.  RENDER_EXTERNAL_URL env var  (auto-set by Render)
    3.  http://localhost:{PORT}/ping  (fallback for local dev)

    Attributes
    ----------
    _target_url : str
    _interval : int       — seconds between pings
    _running : bool
    _task : asyncio.Task
    _success_count : int
    _fail_count : int
    _last_ping_time : float
    _last_ping_success : bool
    """

    def __init__(self, settings: Settings):
        self.settings = settings
        self._target_url = self._resolve_target_url()
        self._interval = settings.SELF_PING_INTERVAL  # default 300s (5 min)
        self._timeout = settings.SELF_PING_TIMEOUT    # default 15s
        self._retry_count = settings.SELF_PING_RETRY_COUNT  # default 3

        # State
        self._running = False
        self._task: Optional[asyncio.Task] = None
        self._success_count = 0
        self._fail_count = 0
        self._last_ping_time: Optional[float] = None
        self._last_ping_success: Optional[bool] = None

        logger.info(
            f"SelfPinger created — target={self._target_url}, "
            f"interval={self._interval}s"
        )

    # ------------------------------------------------------------------
    # URL RESOLUTION
    # ------------------------------------------------------------------

    def _resolve_target_url(self) -> str:
        """
        Determine the URL to ping, in priority order:
        1. Explicit SELF_PING_URL from settings
        2. RENDER_EXTERNAL_URL environment variable (Render sets this)
        3. Fallback to localhost
        """
        # 1. Explicit config
        if self.settings.SELF_PING_URL:
            url = self.settings.SELF_PING_URL.rstrip("/")
            if not url.endswith("/ping"):
                url += "/ping"
            return url

        # 2. Render env var
        render_url = os.environ.get("RENDER_EXTERNAL_URL")
        if render_url:
            url = render_url.rstrip("/")
            if not url.endswith("/ping"):
                url += "/ping"
            return url

        # 3. Localhost fallback
        return f"http://localhost:{self.settings.PORT}/ping"

    # ------------------------------------------------------------------
    # LIFECYCLE
    # ------------------------------------------------------------------

    async def start(self) -> None:
        """Start the self-ping loop."""
        if not self.settings.SELF_PING_ENABLED:
            logger.info("SelfPinger is disabled (SELF_PING_ENABLED=False)")
            return

        if self._running:
            logger.warning("SelfPinger is already running")
            return

        self._running = True
        self._task = asyncio.create_task(self._ping_loop())
        logger.info(f"✓ SelfPinger started — pinging {self._target_url}")

    async def stop(self) -> None:
        """Stop the self-ping loop."""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
        logger.info("✓ SelfPinger stopped")

    # ------------------------------------------------------------------
    # PING LOOP
    # ------------------------------------------------------------------

    async def _ping_loop(self) -> None:
        """
        Continuously ping the target URL every _interval seconds.
        """
        logger.info("[SelfPinger] Ping loop started")

        # Perform an immediate first ping so we know the system is working
        await self._do_ping()

        while self._running:
            try:
                await asyncio.sleep(self._interval)
                if not self._running:
                    break
                await self._do_ping()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"[SelfPinger] Unexpected error: {e}", exc_info=True)

        logger.info("[SelfPinger] Ping loop exited")

    # ------------------------------------------------------------------
    # SINGLE PING (with retry)
    # ------------------------------------------------------------------

    async def _do_ping(self) -> bool:
        """
        Send a single GET request to the target URL.
        Retries up to _retry_count times on failure.

        Returns
        -------
        bool
            True if at least one attempt succeeded.
        """
        self._last_ping_time = time.time()
        delay = 2.0  # initial retry delay

        for attempt in range(self._retry_count + 1):
            try:
                async with httpx.AsyncClient(
                    timeout=httpx.Timeout(self._timeout)
                ) as client:
                    response = await client.get(self._target_url)

                if response.status_code == 200:
                    self._success_count += 1
                    self._last_ping_success = True
                    logger.debug(
                        f"[SelfPinger] ✓ ping → {response.status_code} "
                        f"(total: {self._success_count} ok, {self._fail_count} fail)"
                    )
                    return True
                else:
                    logger.warning(
                        f"[SelfPinger] Unexpected status {response.status_code} "
                        f"from {self._target_url}"
                    )

            except httpx.ConnectError:
                # Server might not be ready yet (first ping right after start)
                if attempt == 0 and self._success_count == 0:
                    logger.debug("[SelfPinger] Server not ready yet, will retry…")
                else:
                    logger.warning(
                        f"[SelfPinger] Connection error on attempt {attempt + 1}"
                    )
            except httpx.TimeoutException:
                logger.warning(
                    f"[SelfPinger] Timeout on attempt {attempt + 1} "
                    f"(timeout={self._timeout}s)"
                )
            except Exception as e:
                logger.warning(
                    f"[SelfPinger] Error on attempt {attempt + 1}: {e}"
                )

            # Retry with back-off
            if attempt < self._retry_count:
                await asyncio.sleep(delay)
                delay *= 2
            else:
                # All retries exhausted
                self._fail_count += 1
                self._last_ping_success = False
                logger.error(
                    f"[SelfPinger] ✗ All {self._retry_count + 1} attempts failed "
                    f"for {self._target_url}"
                )

        return False

    # ------------------------------------------------------------------
    # DIAGNOSTICS
    # ------------------------------------------------------------------

    def get_stats(self) -> Dict[str, Any]:
        """Return current self-ping statistics."""
        return {
            "target_url": self._target_url,
            "interval_seconds": self._interval,
            "is_running": self._running,
            "success_count": self._success_count,
            "fail_count": self._fail_count,
            "last_ping_time": (
                datetime.fromtimestamp(self._last_ping_time).isoformat()
                if self._last_ping_time else None
            ),
            "last_ping_success": self._last_ping_success,
            "success_rate": (
                round(
                    self._success_count
                    / max(1, self._success_count + self._fail_count)
                    * 100, 1
                )
            ),
        }


# ============================================================================
# UTILITY
# ============================================================================

def _seconds_to_human(seconds: int) -> str:
    """Convert seconds to a human-readable string like '2h 30m 15s'."""
    if seconds < 0:
        return "0s"
    days, remainder = divmod(seconds, 86400)
    hours, remainder = divmod(remainder, 3600)
    minutes, secs = divmod(remainder, 60)
    parts = []
    if days:
        parts.append(f"{days}d")
    if hours:
        parts.append(f"{hours}h")
    if minutes:
        parts.append(f"{minutes}m")
    if secs or not parts:
        parts.append(f"{secs}s")
    return " ".join(parts)


# ============================================================================
# END OF SELF-PING MODULE
# ============================================================================
