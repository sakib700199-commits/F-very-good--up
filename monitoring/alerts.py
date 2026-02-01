"""
============================================================================
TELEGRAM UPTIME BOT - ALERT MANAGER
============================================================================
Manages the full lifecycle of monitoring alerts: enqueueing from the
MonitoringEngine, deduplication (cooldown), rate limiting, persistence to
the alerts table, and dispatching Telegram notifications via the bot.

Design
------
AlertManager uses an internal asyncio.Queue.  The MonitoringEngine calls
``enqueue_alert()`` which is non-blocking — it simply pushes a payload onto
the queue.  A separate ``_dispatch_loop()`` task pulls items off the queue
one at a time, applies cooldown / rate-limit logic, persists the Alert row,
and finally sends the Telegram message.

This decouples the hot monitoring path from the (potentially slow) Telegram
API call, preventing a slow send from blocking other checks.

Cooldown Logic
--------------
Each link has a cooldown timer.  Once a DOWN alert fires for a link, no
further DOWN alerts fire for that link until ALERT_COOLDOWN seconds have
passed.  UP (recovery) alerts are NOT subject to cooldown — they always
fire immediately.

Rate Limiting
-------------
Per-user rate limit: at most MAX_ALERTS_PER_HOUR alerts in any rolling
60-minute window.  If exceeded the alert is still persisted but the
Telegram message is suppressed.

Retry
-----
If the Telegram send fails (network blip, rate-limit from Telegram), the
alert is retried up to ``max_retries`` times with exponential back-off.

Author: Professional Development Team
Version: 1.0.0
License: MIT
============================================================================
"""

import asyncio
import time
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Any

from database.models import Alert, AlertType, NotificationChannel
from database.manager import DatabaseManager
from config.settings import Settings, get_settings
from utils.logger import get_logger


logger = get_logger("AlertManager")


# ============================================================================
# ALERT PAYLOAD (internal queue item)
# ============================================================================

@dataclass
class AlertPayload:
    """
    Lightweight payload that travels through the internal queue.
    Not persisted directly — used to carry data from enqueue to dispatch.
    """
    user_id: int                          # DB primary-key of the User row
    link_id: Optional[int]                # DB primary-key of the MonitoredLink row
    alert_type: AlertType
    title: str
    message: str
    priority: int = 1
    channels: List[str] = field(default_factory=lambda: ["telegram"])
    metadata: Dict[str, Any] = field(default_factory=dict)
    enqueued_at: float = field(default_factory=time.time)


# ============================================================================
# ALERT MANAGER
# ============================================================================

class AlertManager:
    """
    Central hub for all alert processing.

    Parameters
    ----------
    db_manager : DatabaseManager
        Shared database manager.
    bot : aiogram.Bot | None
        The aiogram Bot instance used to send Telegram messages.
        If None, alerts are persisted but Telegram messages are skipped
        (useful during testing or when the bot hasn't connected yet).
    """

    def __init__(self, db_manager: DatabaseManager, bot: Any = None):
        self.settings = get_settings()
        self.db_manager = db_manager
        self.bot = bot

        # --- internal queue ---
        self._queue: asyncio.Queue[AlertPayload] = asyncio.Queue(maxsize=10_000)

        # --- cooldown tracking: link_id → timestamp of last DOWN alert ---
        self._cooldown_map: Dict[int, float] = {}
        self._cooldown_seconds = self.settings.ALERT_COOLDOWN  # default 900s

        # --- per-user rate limit: user_id → deque of send timestamps ---
        self._rate_limit_map: Dict[int, deque] = {}
        self._max_alerts_per_hour = self.settings.MAX_ALERTS_PER_HOUR
        self._rate_window = 3600  # 1 hour in seconds

        # --- retry config ---
        self._max_retries = self.settings.ALERT_RETRY_COUNT

        # --- lifecycle ---
        self._running = False
        self._dispatch_task: Optional[asyncio.Task] = None

        logger.info(
            f"AlertManager created — cooldown={self._cooldown_seconds}s, "
            f"rate_limit={self._max_alerts_per_hour}/hr, "
            f"max_retries={self._max_retries}"
        )

    # ------------------------------------------------------------------
    # PUBLIC API
    # ------------------------------------------------------------------

    async def start(self) -> None:
        """Start the background dispatch loop."""
        if self._running:
            logger.warning("AlertManager is already running")
            return
        self._running = True
        self._dispatch_task = asyncio.create_task(self._dispatch_loop())
        logger.info("✓ AlertManager started — dispatch loop active")

    async def stop(self) -> None:
        """Stop the dispatch loop and drain remaining items."""
        self._running = False
        if self._dispatch_task:
            self._dispatch_task.cancel()
            try:
                await self._dispatch_task
            except asyncio.CancelledError:
                pass
            self._dispatch_task = None

        # Drain any remaining alerts (persist but don't send)
        drained = 0
        while not self._queue.empty():
            try:
                payload = self._queue.get_nowait()
                await self._persist_alert(payload, sent=False)
                drained += 1
            except asyncio.QueueEmpty:
                break
        if drained:
            logger.info(f"[AlertManager] Drained {drained} remaining alerts on shutdown")
        logger.info("✓ AlertManager stopped")

    async def enqueue_alert(
        self,
        user_id: int,
        link_id: Optional[int],
        alert_type: AlertType,
        title: str,
        message: str,
        priority: int = 1,
        channels: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        Non-blocking enqueue of an alert.

        Returns
        -------
        bool
            True if the alert was enqueued, False if the queue is full.
        """
        payload = AlertPayload(
            user_id=user_id,
            link_id=link_id,
            alert_type=alert_type,
            title=title,
            message=message,
            priority=priority,
            channels=channels or ["telegram"],
            metadata=metadata or {},
        )

        try:
            self._queue.put_nowait(payload)
            logger.debug(
                f"[AlertManager] Enqueued {alert_type.value} alert for "
                f"link={link_id}, queue_size={self._queue.qsize()}"
            )
            return True
        except asyncio.QueueFull:
            logger.warning(
                f"[AlertManager] Alert queue is full ({self._queue.maxsize}). "
                f"Dropping alert: {title}"
            )
            return False

    # ------------------------------------------------------------------
    # DISPATCH LOOP
    # ------------------------------------------------------------------

    async def _dispatch_loop(self) -> None:
        """
        Pull alerts off the queue one at a time and process them.
        Runs until self._running is False.
        """
        logger.info("[AlertManager] Dispatch loop started")
        while self._running:
            try:
                # Wait for an item with a short timeout so we can check
                # self._running periodically
                payload = await asyncio.wait_for(
                    self._queue.get(), timeout=1.0
                )
                await self._process_alert(payload)
                self._queue.task_done()
            except asyncio.TimeoutError:
                continue  # loop back and check self._running
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(
                    f"[AlertManager] Unhandled error in dispatch loop: {e}",
                    exc_info=True
                )
        logger.info("[AlertManager] Dispatch loop exited")

    # ------------------------------------------------------------------
    # ALERT PROCESSING PIPELINE
    # ------------------------------------------------------------------

    async def _process_alert(self, payload: AlertPayload) -> None:
        """
        Full pipeline for a single alert:
        1. Cooldown check (skip duplicate DOWN alerts within window)
        2. Rate-limit check (suppress Telegram send if over limit)
        3. Persist to DB
        4. Send Telegram message (with retry)
        """
        # --- 1. Cooldown ---
        if not self._check_cooldown(payload):
            logger.debug(
                f"[AlertManager] Alert suppressed by cooldown — "
                f"link={payload.link_id}, type={payload.alert_type.value}"
            )
            return

        # --- 2. Rate limit check (we still persist, but may skip send) ---
        send_allowed = self._check_rate_limit(payload.user_id)

        # --- 3. Persist ---
        alert_row = await self._persist_alert(payload, sent=send_allowed)

        # --- 4. Send ---
        if send_allowed and self.bot:
            success = await self._send_telegram(payload)
            if success and alert_row:
                # Mark as sent in DB
                try:
                    async with self.db_manager.session() as session:
                        merged = await session.merge(alert_row)
                        merged.mark_as_sent()
                        await session.commit()
                except Exception as e:
                    logger.error(f"[AlertManager] Failed to mark alert as sent: {e}")
        elif not send_allowed:
            logger.info(
                f"[AlertManager] Rate limit reached for user {payload.user_id} — "
                f"alert persisted but not sent via Telegram"
            )

    # ------------------------------------------------------------------
    # COOLDOWN LOGIC
    # ------------------------------------------------------------------

    def _check_cooldown(self, payload: AlertPayload) -> bool:
        """
        Returns True if the alert should proceed, False if suppressed.

        Rules:
        • DOWN alerts: suppressed if another DOWN alert for the same link
          fired within the last ALERT_COOLDOWN seconds.
        • UP alerts: never suppressed (recovery is always important).
        • SLOW alerts: subject to cooldown per link (same as DOWN).
        • SSL_EXPIRY alerts: subject to cooldown per link.
        """
        # UP / recovery alerts always go through
        if payload.alert_type == AlertType.UP:
            return True

        # For DOWN, SLOW, SSL_EXPIRY — check cooldown map
        link_id = payload.link_id
        if link_id is None:
            return True  # no link_id → can't cooldown

        now = time.time()
        last_alert_time = self._cooldown_map.get(link_id, 0)

        if now - last_alert_time < self._cooldown_seconds:
            return False  # still within cooldown window

        # Update cooldown timestamp
        self._cooldown_map[link_id] = now
        return True

    # ------------------------------------------------------------------
    # RATE LIMIT LOGIC
    # ------------------------------------------------------------------

    def _check_rate_limit(self, user_id: int) -> bool:
        """
        Returns True if the user is under their hourly alert limit.
        Maintains a sliding window of send timestamps per user.
        """
        now = time.time()
        window_start = now - self._rate_window

        if user_id not in self._rate_limit_map:
            self._rate_limit_map[user_id] = deque()

        # Remove timestamps outside the window
        while (
            self._rate_limit_map[user_id]
            and self._rate_limit_map[user_id][0] < window_start
        ):
            self._rate_limit_map[user_id].popleft()

        # Check count
        if len(self._rate_limit_map[user_id]) >= self._max_alerts_per_hour:
            return False

        # Record this send
        self._rate_limit_map[user_id].append(now)
        return True

    # ------------------------------------------------------------------
    # PERSISTENCE
    # ------------------------------------------------------------------

    async def _persist_alert(
        self, payload: AlertPayload, sent: bool = False
    ) -> Optional[Alert]:
        """
        Write an Alert row to the database.

        Returns the Alert instance (detached) or None on failure.
        """
        try:
            alert = Alert(
                user_id=payload.user_id,
                link_id=payload.link_id,
                alert_type=payload.alert_type,
                title=payload.title,
                message=payload.message,
                priority=payload.priority,
                channels=payload.channels,
                sent=sent,
                sent_at=datetime.utcnow() if sent else None,
                max_retries=self._max_retries,
                metadata=payload.metadata,
            )

            async with self.db_manager.session() as session:
                session.add(alert)
                await session.commit()
                await session.refresh(alert)

            logger.debug(
                f"[AlertManager] Alert persisted — id={alert.id}, "
                f"type={payload.alert_type.value}, user={payload.user_id}"
            )
            return alert

        except Exception as e:
            logger.error(f"[AlertManager] Failed to persist alert: {e}")
            return None

    # ------------------------------------------------------------------
    # TELEGRAM SEND (with retry)
    # ------------------------------------------------------------------

    async def _send_telegram(self, payload: AlertPayload) -> bool:
        """
        Send the alert message to the user via the aiogram Bot.
        Retries up to max_retries with exponential back-off.

        Returns True if at least one attempt succeeded.
        """
        # The user_id in the payload is the DB PK — we need the Telegram
        # user_id (the user.user_id column).  We fetch it here.
        telegram_user_id = await self._get_telegram_user_id(payload.user_id)
        if telegram_user_id is None:
            logger.warning(
                f"[AlertManager] Cannot find Telegram ID for DB user {payload.user_id}"
            )
            return False

        # Build the full message
        full_message = f"{payload.title}\n\n{payload.message}"

        delay = 1.0  # initial retry delay in seconds
        for attempt in range(self._max_retries + 1):
            try:
                await self.bot.send_message(
                    chat_id=telegram_user_id,
                    text=full_message,
                    parse_mode="HTML",
                )
                logger.info(
                    f"[AlertManager] ✓ Alert sent to user {telegram_user_id} — "
                    f"{payload.alert_type.value}: {payload.title[:60]}"
                )
                return True

            except Exception as e:
                logger.warning(
                    f"[AlertManager] Send attempt {attempt + 1}/{self._max_retries + 1} "
                    f"failed for user {telegram_user_id}: {e}"
                )
                if attempt < self._max_retries:
                    await asyncio.sleep(delay)
                    delay *= 2  # exponential back-off
                else:
                    logger.error(
                        f"[AlertManager] All {self._max_retries + 1} send attempts "
                        f"exhausted for alert: {payload.title[:60]}"
                    )

        return False

    # ------------------------------------------------------------------
    # UTILITY: resolve DB user_id → Telegram user_id
    # ------------------------------------------------------------------

    async def _get_telegram_user_id(self, db_user_id: int) -> Optional[int]:
        """
        Look up the Telegram user_id from the users table.
        Uses the DB user PK (users.id) which is also the Telegram user_id
        in this schema (user_id column stores the Telegram ID).
        """
        try:
            from database.models import User
            from sqlalchemy import select

            async with self.db_manager.session() as session:
                result = await session.execute(
                    select(User.user_id).where(User.id == db_user_id)
                )
                row = result.scalar_one_or_none()
                return row
        except Exception as e:
            logger.error(f"[AlertManager] Error resolving Telegram user_id: {e}")
            return None

    # ------------------------------------------------------------------
    # DIAGNOSTIC
    # ------------------------------------------------------------------

    def get_stats(self) -> Dict[str, Any]:
        """Return current state of the alert manager for diagnostics."""
        return {
            "queue_size": self._queue.qsize(),
            "cooldown_entries": len(self._cooldown_map),
            "rate_limit_entries": len(self._rate_limit_map),
            "is_running": self._running,
        }


# ============================================================================
# END OF ALERT MANAGER MODULE
# ============================================================================
