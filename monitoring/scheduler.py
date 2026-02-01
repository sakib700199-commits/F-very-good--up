"""
============================================================================
TELEGRAM UPTIME BOT - BACKGROUND TASK SCHEDULER
============================================================================
A lightweight, asyncio-native task scheduler that runs periodic background
jobs alongside the monitoring engine.  It does NOT use APScheduler or Celery
— all jobs run as coroutines in the same event loop, keeping the deployment
simple (single process, no broker needed).

Registered Jobs
---------------
1.  stats_aggregation       (every 5 min)
    Recalculates global Statistics row: total users, links, checks, etc.

2.  log_cleanup             (every 24 h)
    Deletes PingLog and UserLog rows older than DB_LOG_RETENTION_DAYS.

3.  ssl_expiry_sweep        (every 6 h)
    Scans all active HTTPS links for certificates expiring within 30 days
    and fires SSL_EXPIRY alerts if not already sent recently.

4.  cooldown_map_gc         (every 1 h)
    Removes stale entries from the AlertManager's cooldown map to prevent
    unbounded memory growth.

5.  inactive_user_cleanup   (every 24 h)
    Marks users who have not been active for 90 days as INACTIVE.

6.  health_log              (every 10 min)
    Writes a heartbeat entry to the system log so operators can verify
    the bot is still alive even during quiet periods.

Author: Professional Development Team
Version: 1.0.0
License: MIT
============================================================================
"""

import asyncio
import time
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, Callable, List
from dataclasses import dataclass, field

from sqlalchemy import select, func, update, and_

from database.models import (
    Statistics, User, MonitoredLink, PingLog, UserLog,
    UserStatus, LinkStatus, MonitorType, AlertType
)
from database.manager import DatabaseManager
from config.settings import Settings, get_settings
from utils.logger import get_logger


logger = get_logger("Scheduler")


# ============================================================================
# JOB DEFINITION
# ============================================================================

@dataclass
class ScheduledJob:
    """
    Describes a single periodic background job.

    Attributes
    ----------
    name : str
        Human-readable identifier (used in logs).
    interval_seconds : int
        How often the job runs.
    coroutine_factory : Callable
        An async callable (no arguments) that performs the work.
    enabled : bool
        Can be toggled at runtime.
    last_run : Optional[float]
        Epoch timestamp of the last successful execution.
    next_run : float
        Epoch timestamp when the job should next execute.
    run_count : int
        Total number of successful executions since startup.
    error_count : int
        Total number of failed executions since startup.
    """
    name: str
    interval_seconds: int
    coroutine_factory: Callable
    enabled: bool = True
    last_run: Optional[float] = None
    next_run: float = field(default_factory=time.time)
    run_count: int = 0
    error_count: int = 0


# ============================================================================
# SCHEDULER
# ============================================================================

class Scheduler:
    """
    Asyncio-based periodic job scheduler.

    Usage
    -----
        scheduler = Scheduler(db_manager, alert_manager)
        scheduler.register_job("my_job", 300, my_async_func)
        await scheduler.start()
        # ... later ...
        await scheduler.stop()
    """

    def __init__(
        self,
        db_manager: DatabaseManager,
        alert_manager: Any = None,
    ):
        self.settings = get_settings()
        self.db_manager = db_manager
        self.alert_manager = alert_manager

        self._jobs: Dict[str, ScheduledJob] = {}
        self._running = False
        self._loop_task: Optional[asyncio.Task] = None
        self._tick_interval = 2.0  # how often the main loop wakes up to check jobs

        # Register built-in jobs
        self._register_builtin_jobs()

        logger.info(
            f"Scheduler created with {len(self._jobs)} built-in jobs"
        )

    # ------------------------------------------------------------------
    # JOB REGISTRATION
    # ------------------------------------------------------------------

    def register_job(
        self,
        name: str,
        interval_seconds: int,
        coroutine_factory: Callable,
        enabled: bool = True,
    ) -> None:
        """
        Register a new periodic job.

        Parameters
        ----------
        name : str
            Unique job name.
        interval_seconds : int
            Period in seconds.
        coroutine_factory : Callable
            An async callable that takes no arguments.
        enabled : bool
            Whether the job starts enabled.
        """
        if name in self._jobs:
            logger.warning(f"[Scheduler] Job '{name}' already registered, overwriting")

        self._jobs[name] = ScheduledJob(
            name=name,
            interval_seconds=interval_seconds,
            coroutine_factory=coroutine_factory,
            enabled=enabled,
            next_run=time.time(),  # run immediately on first tick
        )
        logger.debug(f"[Scheduler] Registered job '{name}' (interval={interval_seconds}s)")

    def enable_job(self, name: str) -> bool:
        """Enable a job by name. Returns True if found."""
        if name in self._jobs:
            self._jobs[name].enabled = True
            return True
        return False

    def disable_job(self, name: str) -> bool:
        """Disable a job by name. Returns True if found."""
        if name in self._jobs:
            self._jobs[name].enabled = False
            return True
        return False

    # ------------------------------------------------------------------
    # LIFECYCLE
    # ------------------------------------------------------------------

    async def start(self) -> None:
        """Start the scheduler loop."""
        if self._running:
            logger.warning("Scheduler is already running")
            return
        self._running = True
        self._loop_task = asyncio.create_task(self._main_loop())
        logger.info("✓ Scheduler started")

    async def stop(self) -> None:
        """Stop the scheduler loop."""
        self._running = False
        if self._loop_task:
            self._loop_task.cancel()
            try:
                await self._loop_task
            except asyncio.CancelledError:
                pass
            self._loop_task = None
        logger.info("✓ Scheduler stopped")

    # ------------------------------------------------------------------
    # MAIN LOOP
    # ------------------------------------------------------------------

    async def _main_loop(self) -> None:
        """
        Wake up every _tick_interval seconds.  For each enabled job whose
        next_run time has arrived, launch it as a background task.
        """
        logger.info("[Scheduler] Main loop started")
        while self._running:
            now = time.time()
            for job in self._jobs.values():
                if job.enabled and now >= job.next_run:
                    # Launch the job as a fire-and-forget task
                    asyncio.create_task(self._execute_job(job))
                    # Advance next_run immediately so we don't re-trigger
                    job.next_run = now + job.interval_seconds

            try:
                await asyncio.sleep(self._tick_interval)
            except asyncio.CancelledError:
                break

        logger.info("[Scheduler] Main loop exited")

    # ------------------------------------------------------------------
    # JOB EXECUTION
    # ------------------------------------------------------------------

    async def _execute_job(self, job: ScheduledJob) -> None:
        """
        Run a single job, capture timing and errors.
        """
        start_time = time.time()
        try:
            logger.debug(f"[Scheduler] Running job '{job.name}'…")
            await job.coroutine_factory()
            elapsed = time.time() - start_time

            job.run_count += 1
            job.last_run = time.time()
            logger.debug(
                f"[Scheduler] Job '{job.name}' completed in {elapsed:.2f}s "
                f"(run #{job.run_count})"
            )

        except Exception as e:
            job.error_count += 1
            elapsed = time.time() - start_time
            logger.error(
                f"[Scheduler] Job '{job.name}' FAILED after {elapsed:.2f}s: {e}",
                exc_info=True
            )

    # ------------------------------------------------------------------
    # DIAGNOSTICS
    # ------------------------------------------------------------------

    def get_job_stats(self) -> List[Dict[str, Any]]:
        """Return status of all registered jobs."""
        stats = []
        for job in self._jobs.values():
            stats.append({
                "name": job.name,
                "interval_seconds": job.interval_seconds,
                "enabled": job.enabled,
                "run_count": job.run_count,
                "error_count": job.error_count,
                "last_run": (
                    datetime.fromtimestamp(job.last_run).isoformat()
                    if job.last_run else None
                ),
                "next_run": (
                    datetime.fromtimestamp(job.next_run).isoformat()
                    if job.next_run else None
                ),
            })
        return stats

    # ==================================================================
    # BUILT-IN JOBS
    # ==================================================================

    def _register_builtin_jobs(self) -> None:
        """Register all built-in periodic jobs."""

        # 1. Stats aggregation (every 5 minutes)
        self.register_job(
            "stats_aggregation",
            interval_seconds=300,
            coroutine_factory=self._job_stats_aggregation,
        )

        # 2. Log cleanup (every 24 hours)
        self.register_job(
            "log_cleanup",
            interval_seconds=86400,
            coroutine_factory=self._job_log_cleanup,
        )

        # 3. SSL expiry sweep (every 6 hours)
        self.register_job(
            "ssl_expiry_sweep",
            interval_seconds=21600,
            coroutine_factory=self._job_ssl_expiry_sweep,
            enabled=self.settings.ENABLE_SSL_MONITORING,
        )

        # 4. Cooldown map GC (every 1 hour)
        self.register_job(
            "cooldown_gc",
            interval_seconds=3600,
            coroutine_factory=self._job_cooldown_gc,
        )

        # 5. Inactive user cleanup (every 24 hours)
        self.register_job(
            "inactive_user_cleanup",
            interval_seconds=86400,
            coroutine_factory=self._job_inactive_user_cleanup,
        )

        # 6. Health heartbeat (every 10 minutes)
        self.register_job(
            "health_heartbeat",
            interval_seconds=600,
            coroutine_factory=self._job_health_heartbeat,
        )

    # ------------------------------------------------------------------
    # JOB: Stats Aggregation
    # ------------------------------------------------------------------

    async def _job_stats_aggregation(self) -> None:
        """
        Recalculate and upsert the daily Statistics row.
        """
        try:
            async with self.db_manager.session() as session:
                # --- user counts ---
                total_users = await session.scalar(
                    select(func.count(User.id))
                ) or 0
                active_users = await session.scalar(
                    select(func.count(User.id)).where(
                        User.status == UserStatus.ACTIVE
                    )
                ) or 0
                premium_users = await session.scalar(
                    select(func.count(User.id)).where(
                        User.is_premium == True
                    )
                ) or 0

                # --- link counts ---
                total_links = await session.scalar(
                    select(func.count(MonitoredLink.id))
                ) or 0
                active_links = await session.scalar(
                    select(func.count(MonitoredLink.id)).where(
                        MonitoredLink.is_active == True
                    )
                ) or 0
                up_links = await session.scalar(
                    select(func.count(MonitoredLink.id)).where(
                        and_(
                            MonitoredLink.is_active == True,
                            MonitoredLink.is_up == True
                        )
                    )
                ) or 0
                down_links = active_links - up_links

                # --- check counts (from links, not from ping_logs for perf) ---
                total_checks = await session.scalar(
                    select(func.coalesce(func.sum(MonitoredLink.total_checks), 0))
                ) or 0
                successful_checks = await session.scalar(
                    select(func.coalesce(func.sum(MonitoredLink.successful_checks), 0))
                ) or 0
                failed_checks = await session.scalar(
                    select(func.coalesce(func.sum(MonitoredLink.failed_checks), 0))
                ) or 0

                # --- avg response time ---
                avg_resp = await session.scalar(
                    select(func.avg(MonitoredLink.avg_response_time)).where(
                        MonitoredLink.avg_response_time.isnot(None)
                    )
                )

                # --- total downtime ---
                total_downtime = await session.scalar(
                    select(func.coalesce(func.sum(MonitoredLink.total_downtime_seconds), 0))
                ) or 0

                # --- Upsert today's Statistics row ---
                today = datetime.utcnow().replace(
                    hour=0, minute=0, second=0, microsecond=0
                )
                existing = await session.scalar(
                    select(Statistics).where(Statistics.date == today)
                )

                if existing:
                    existing.total_users = total_users
                    existing.active_users = active_users
                    existing.premium_users = premium_users
                    existing.total_links = total_links
                    existing.active_links = active_links
                    existing.up_links = up_links
                    existing.down_links = down_links
                    existing.total_checks = total_checks
                    existing.successful_checks = successful_checks
                    existing.failed_checks = failed_checks
                    existing.avg_response_time = float(avg_resp) if avg_resp else None
                    existing.total_downtime_seconds = total_downtime
                else:
                    stats_row = Statistics(
                        date=today,
                        total_users=total_users,
                        active_users=active_users,
                        premium_users=premium_users,
                        total_links=total_links,
                        active_links=active_links,
                        up_links=up_links,
                        down_links=down_links,
                        total_checks=total_checks,
                        successful_checks=successful_checks,
                        failed_checks=failed_checks,
                        avg_response_time=float(avg_resp) if avg_resp else None,
                        total_downtime_seconds=total_downtime,
                    )
                    session.add(stats_row)

                await session.commit()

            logger.debug(
                f"[StatsAgg] users={total_users}, links={total_links}, "
                f"up={up_links}, down={down_links}"
            )

        except Exception as e:
            logger.error(f"[StatsAgg] Failed: {e}", exc_info=True)
            raise

    # ------------------------------------------------------------------
    # JOB: Log Cleanup
    # ------------------------------------------------------------------

    async def _job_log_cleanup(self) -> None:
        """
        Delete old PingLog and UserLog entries beyond the retention window.
        """
        retention_days = self.settings.DB_LOG_RETENTION_DAYS
        deleted = await self.db_manager.cleanup_old_logs(days=retention_days)
        logger.info(
            f"[LogCleanup] Deleted {deleted} log entries older than "
            f"{retention_days} days"
        )

    # ------------------------------------------------------------------
    # JOB: SSL Expiry Sweep
    # ------------------------------------------------------------------

    async def _job_ssl_expiry_sweep(self) -> None:
        """
        Find all active HTTPS/SSL links with certificates expiring within
        30 days and fire alerts.  The MonitoringEngine also does this on
        each check, but this sweep catches links that haven't been checked
        recently (e.g., high-interval links).
        """
        try:
            async with self.db_manager.session() as session:
                result = await session.execute(
                    select(MonitoredLink).where(
                        and_(
                            MonitoredLink.is_active == True,
                            MonitoredLink.is_deleted == False,
                            MonitoredLink.ssl_days_remaining.isnot(None),
                            MonitoredLink.ssl_days_remaining <= 30,
                        )
                    )
                )
                expiring_links = result.scalars().all()

            if not expiring_links:
                logger.debug("[SSLSweep] No certificates expiring soon")
                return

            logger.warning(
                f"[SSLSweep] Found {len(expiring_links)} link(s) with "
                f"SSL certificates expiring within 30 days"
            )

            for link in expiring_links:
                if self.alert_manager:
                    await self.alert_manager.enqueue_alert(
                        user_id=link.user_id,
                        link_id=link.id,
                        alert_type=AlertType.SSL_EXPIRY,
                        title=f"🔐 SSL Expiring: {link.display_name}",
                        message=(
                            f"<b>URL:</b> {link.url}\n"
                            f"<b>Days Remaining:</b> {link.ssl_days_remaining}\n"
                            f"<b>Issuer:</b> {link.ssl_issuer or 'Unknown'}\n"
                            f"<b>⚡ Action Required:</b> Renew your SSL certificate!"
                        ),
                        priority=2,
                    )
                else:
                    logger.warning(
                        f"[SSLSweep] SSL expiring for link {link.id} "
                        f"({link.url}) — {link.ssl_days_remaining} days left "
                        f"(no AlertManager to send notification)"
                    )

        except Exception as e:
            logger.error(f"[SSLSweep] Failed: {e}", exc_info=True)
            raise

    # ------------------------------------------------------------------
    # JOB: Cooldown Map GC
    # ------------------------------------------------------------------

    async def _job_cooldown_gc(self) -> None:
        """
        Remove stale entries from the AlertManager's cooldown map.
        Entries older than 2× the cooldown window can be safely removed.
        """
        if not self.alert_manager:
            return

        import time as _time
        now = _time.time()
        cooldown = self.alert_manager._cooldown_seconds
        cutoff = now - (cooldown * 2)

        stale_keys = [
            link_id
            for link_id, ts in self.alert_manager._cooldown_map.items()
            if ts < cutoff
        ]
        for key in stale_keys:
            del self.alert_manager._cooldown_map[key]

        if stale_keys:
            logger.debug(f"[CooldownGC] Removed {len(stale_keys)} stale cooldown entries")

    # ------------------------------------------------------------------
    # JOB: Inactive User Cleanup
    # ------------------------------------------------------------------

    async def _job_inactive_user_cleanup(self) -> None:
        """
        Mark users as INACTIVE if they haven't used the bot in 90 days.
        Does NOT delete them or their links — just changes status for
        reporting purposes.
        """
        cutoff_date = datetime.utcnow() - timedelta(days=90)

        try:
            async with self.db_manager.session() as session:
                result = await session.execute(
                    update(User)
                    .where(
                        and_(
                            User.status == UserStatus.ACTIVE,
                            User.last_activity.isnot(None),
                            User.last_activity < cutoff_date,
                        )
                    )
                    .values(status=UserStatus.INACTIVE)
                )
                await session.commit()
                updated = result.rowcount

            if updated:
                logger.info(
                    f"[InactiveCleanup] Marked {updated} user(s) as INACTIVE "
                    f"(no activity in 90 days)"
                )
            else:
                logger.debug("[InactiveCleanup] No inactive users found")

        except Exception as e:
            logger.error(f"[InactiveCleanup] Failed: {e}", exc_info=True)
            raise

    # ------------------------------------------------------------------
    # JOB: Health Heartbeat
    # ------------------------------------------------------------------

    async def _job_health_heartbeat(self) -> None:
        """
        Write a simple heartbeat log entry.  This is purely for operator
        confidence — if you see heartbeats in the log, the bot is alive.
        """
        # Quick DB health check
        is_alive = await self.db_manager.check_connection()
        logger.info(
            f"[Heartbeat] ✓ Bot alive — db={'OK' if is_alive else 'FAIL'}, "
            f"time={datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC"
        )


# ============================================================================
# END OF SCHEDULER MODULE
# ============================================================================
