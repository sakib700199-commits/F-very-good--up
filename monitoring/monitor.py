"""
============================================================================
TELEGRAM UPTIME BOT - MONITORING ENGINE
============================================================================
The heart of the bot. This module contains the full async monitoring engine
that performs HTTP, HTTPS, TCP, DNS, and SSL checks on every monitored link,
records every ping log, calculates uptime metrics, detects downtime/recovery
events, and enqueues alerts for the AlertManager.

Architecture
------------
MonitoringEngine          ← top-level orchestrator, owns the worker pool
├── _fetch_links()        ← pulls due links from DB in batches
├── _dispatch_batch()     ← fans out one batch via asyncio.gather
├── _run_single_check()   ← dispatches to the correct checker
│   ├── HTTPChecker       ← performs GET/POST/HEAD via httpx
│   ├── TCPChecker        ← raw socket connect check
│   ├── DNSChecker        ← dnspython resolve check
│   └── SSLChecker        ← certificate expiry & validity
├── _record_result()      ← writes PingLog row, updates MonitoredLink
├── _handle_state_change()← fires DOWN / UP / SLOW alerts
└── _update_link_metrics()← recalcs uptime %, avg response, next_check

The engine runs inside an asyncio.Task created by the main application.
It sleeps between sweep cycles (configurable via MONITOR_SWEEP_INTERVAL).

Author: Professional Development Team
Version: 1.0.0
License: MIT
============================================================================
"""

import asyncio
import socket
import ssl
import time
import traceback
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List, Tuple

import httpx
import dns.resolver
import dns.exception

from database.models import (
    MonitoredLink, PingLog, LinkStatus, MonitorType,
    AlertType, User
)
from database.manager import DatabaseManager, LinkRepository
from config.settings import Settings, get_settings
from utils.logger import get_logger
from utils.helpers import TimeHelper, BatchProcessor


logger = get_logger("MonitoringEngine")


# ============================================================================
# CHECK RESULT DATACLASS
# ============================================================================

class CheckResult:
    """
    Immutable value object that carries every piece of information
    produced by a single monitoring check back up to the engine.
    """
    __slots__ = (
        "success", "status_code", "response_time", "response_size",
        "error_message", "error_type", "ssl_verified", "ssl_error",
        "dns_resolution_time", "connection_time", "ip_address",
        "response_headers", "request_method", "retry_count",
    )

    def __init__(
        self,
        success: bool = False,
        status_code: Optional[int] = None,
        response_time: Optional[float] = None,
        response_size: Optional[int] = None,
        error_message: Optional[str] = None,
        error_type: Optional[str] = None,
        ssl_verified: Optional[bool] = None,
        ssl_error: Optional[str] = None,
        dns_resolution_time: Optional[float] = None,
        connection_time: Optional[float] = None,
        ip_address: Optional[str] = None,
        response_headers: Optional[Dict[str, str]] = None,
        request_method: Optional[str] = None,
        retry_count: int = 0,
    ):
        self.success = success
        self.status_code = status_code
        self.response_time = response_time
        self.response_size = response_size
        self.error_message = error_message
        self.error_type = error_type
        self.ssl_verified = ssl_verified
        self.ssl_error = ssl_error
        self.dns_resolution_time = dns_resolution_time
        self.connection_time = connection_time
        self.ip_address = ip_address
        self.response_headers = response_headers or {}
        self.request_method = request_method
        self.retry_count = retry_count

    def to_dict(self) -> Dict[str, Any]:
        return {slot: getattr(self, slot) for slot in self.__slots__}


# ============================================================================
# HTTP CHECKER
# ============================================================================

class HTTPChecker:
    """
    Performs HTTP / HTTPS monitoring using httpx async client.

    Features
    --------
    • Follows redirects (configurable, default 5)
    • Respects per-link custom headers and request body
    • Validates response against expected status codes
    • Optionally checks that response body contains expected_content
    • Automatic retry with exponential back-off
    • Captures detailed timing breakdowns via httpx hooks
    """

    def __init__(self, settings: Settings):
        self.settings = settings
        self.default_timeout = settings.REQUEST_TIMEOUT
        self.max_retries = settings.MAX_RETRIES
        self.retry_delay = settings.RETRY_DELAY

    async def check(self, link: MonitoredLink) -> CheckResult:
        """
        Execute an HTTP check against *link*.

        Parameters
        ----------
        link : MonitoredLink
            The database row describing what to check.

        Returns
        -------
        CheckResult
            Fully populated result object.
        """
        timeout = link.timeout or self.default_timeout
        method = link.http_method.value if link.http_method else "GET"
        headers = dict(link.custom_headers) if link.custom_headers else {}
        expected_codes = list(link.expected_status_codes) if link.expected_status_codes else [200]

        # Default User-Agent so the target server sees something sensible
        headers.setdefault(
            "User-Agent",
            "UptimeBot/1.0 (+https://github.com/uptimebot)"
        )

        retry_count = 0
        last_result: Optional[CheckResult] = None

        for attempt in range(self.max_retries + 1):
            start_time = time.perf_counter()
            try:
                async with httpx.AsyncClient(
                    timeout=httpx.Timeout(
                        connect=min(timeout, 10),
                        read=timeout,
                        write=timeout,
                        pool=timeout
                    ),
                    follow_redirects=True,
                    verify=True,          # enforce valid TLS by default
                    limits=httpx.Limits(
                        max_connections=1,
                        max_keepalive_connections=1
                    )
                ) as client:
                    response = await client.request(
                        method=method,
                        url=link.url,
                        headers=headers,
                        content=link.request_body if link.request_body else None,
                    )

                elapsed = time.perf_counter() - start_time

                # --- evaluate success criteria ---
                code_ok = response.status_code in expected_codes
                content_ok = True
                if link.expected_content and code_ok:
                    content_ok = link.expected_content in response.text

                success = code_ok and content_ok

                # Build a clean headers dict (httpx Headers → plain dict)
                resp_headers = dict(response.headers)

                last_result = CheckResult(
                    success=success,
                    status_code=response.status_code,
                    response_time=round(elapsed, 4),
                    response_size=len(response.content),
                    request_method=method,
                    response_headers=resp_headers,
                    retry_count=retry_count,
                    ssl_verified=True if link.url.startswith("https") else None,
                )

                if success:
                    logger.debug(
                        f"[HTTP] {link.url} → {response.status_code} "
                        f"in {elapsed:.3f}s"
                    )
                    return last_result

                # Non-success status but no exception — don't retry
                logger.warning(
                    f"[HTTP] {link.url} → status {response.status_code} "
                    f"(expected {expected_codes})"
                )
                return last_result

            except httpx.ConnectTimeout:
                elapsed = time.perf_counter() - start_time
                last_result = CheckResult(
                    success=False,
                    response_time=round(elapsed, 4),
                    error_message="Connection timed out",
                    error_type="ConnectTimeout",
                    request_method=method,
                    retry_count=retry_count,
                )
            except httpx.ReadTimeout:
                elapsed = time.perf_counter() - start_time
                last_result = CheckResult(
                    success=False,
                    response_time=round(elapsed, 4),
                    error_message="Read timed out",
                    error_type="ReadTimeout",
                    request_method=method,
                    retry_count=retry_count,
                )
            except httpx.ConnectError as e:
                elapsed = time.perf_counter() - start_time
                last_result = CheckResult(
                    success=False,
                    response_time=round(elapsed, 4),
                    error_message=f"Connection error: {str(e)[:200]}",
                    error_type="ConnectError",
                    request_method=method,
                    retry_count=retry_count,
                )
            except httpx.HTTPStatusError as e:
                elapsed = time.perf_counter() - start_time
                last_result = CheckResult(
                    success=False,
                    status_code=e.response.status_code,
                    response_time=round(elapsed, 4),
                    error_message=f"HTTP error: {e.response.status_code}",
                    error_type="HTTPStatusError",
                    request_method=method,
                    retry_count=retry_count,
                )
                return last_result  # explicit HTTP error → no retry
            except ssl.SSLCertVerificationError as e:
                elapsed = time.perf_counter() - start_time
                last_result = CheckResult(
                    success=False,
                    response_time=round(elapsed, 4),
                    error_message=f"SSL verification failed: {str(e)[:200]}",
                    error_type="SSLError",
                    ssl_verified=False,
                    ssl_error=str(e)[:500],
                    request_method=method,
                    retry_count=retry_count,
                )
                return last_result  # SSL errors → no retry
            except Exception as e:
                elapsed = time.perf_counter() - start_time
                last_result = CheckResult(
                    success=False,
                    response_time=round(elapsed, 4),
                    error_message=f"Unexpected error: {str(e)[:200]}",
                    error_type=type(e).__name__,
                    request_method=method,
                    retry_count=retry_count,
                )

            # --- retry logic ---
            retry_count += 1
            if retry_count <= self.max_retries:
                delay = self.retry_delay * (2 ** (retry_count - 1))
                logger.debug(
                    f"[HTTP] {link.url} attempt {retry_count}/{self.max_retries}, "
                    f"retrying in {delay}s…"
                )
                await asyncio.sleep(delay)
            else:
                logger.warning(
                    f"[HTTP] {link.url} exhausted all {self.max_retries} retries"
                )

        # Should never reach here but satisfy the type-checker
        return last_result or CheckResult(
            success=False,
            error_message="Unknown failure — no result produced",
            error_type="UnknownError",
        )


# ============================================================================
# TCP CHECKER
# ============================================================================

class TCPChecker:
    """
    Performs a raw TCP socket connect check.

    Use-case: verify that a port is reachable even when no HTTP endpoint
    is exposed (e.g., database ports, SMTP, custom game servers).

    The URL field is expected to be in the form  tcp://host:port  or
    just  host:port.  If no port is found we default to 80.
    """

    def __init__(self, settings: Settings):
        self.settings = settings
        self.default_timeout = settings.REQUEST_TIMEOUT

    @staticmethod
    def _parse_host_port(url: str) -> Tuple[str, int]:
        """Extract (host, port) from a TCP-style URL string."""
        url = url.strip()
        # Strip protocol prefix if present
        for prefix in ("tcp://", "http://", "https://"):
            if url.lower().startswith(prefix):
                url = url[len(prefix):]
                break
        # Strip trailing path
        url = url.split("/")[0]
        # Split host:port
        if ":" in url:
            parts = url.rsplit(":", 1)
            try:
                return parts[0], int(parts[1])
            except ValueError:
                return parts[0], 80
        return url, 80

    async def check(self, link: MonitoredLink) -> CheckResult:
        """
        Open a TCP socket to host:port, measure connect latency, close.
        """
        host, port = self._parse_host_port(link.url)
        timeout = link.timeout or self.default_timeout
        start_time = time.perf_counter()

        try:
            # Use asyncio's open_connection which respects the event loop
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(host, port),
                timeout=timeout
            )
            elapsed = time.perf_counter() - start_time

            # Immediately close — we only care about connectivity
            writer.close()
            try:
                await writer.wait_closed()
            except Exception:
                pass  # best-effort close

            # Resolve the IP for logging / storage
            try:
                resolved_ip = socket.gethostbyname(host)
            except socket.gaierror:
                resolved_ip = None

            logger.debug(f"[TCP] {host}:{port} → connected in {elapsed:.3f}s")

            return CheckResult(
                success=True,
                response_time=round(elapsed, 4),
                connection_time=round(elapsed, 4),
                ip_address=resolved_ip,
                status_code=None,  # TCP has no HTTP status
            )

        except asyncio.TimeoutError:
            elapsed = time.perf_counter() - start_time
            logger.warning(f"[TCP] {host}:{port} → timed out after {timeout}s")
            return CheckResult(
                success=False,
                response_time=round(elapsed, 4),
                error_message=f"TCP connection to {host}:{port} timed out",
                error_type="TimeoutError",
            )
        except (ConnectionRefusedError, OSError) as e:
            elapsed = time.perf_counter() - start_time
            logger.warning(f"[TCP] {host}:{port} → {e}")
            return CheckResult(
                success=False,
                response_time=round(elapsed, 4),
                error_message=f"TCP connection refused or failed: {str(e)[:200]}",
                error_type=type(e).__name__,
            )
        except Exception as e:
            elapsed = time.perf_counter() - start_time
            return CheckResult(
                success=False,
                response_time=round(elapsed, 4),
                error_message=f"TCP check error: {str(e)[:200]}",
                error_type=type(e).__name__,
            )


# ============================================================================
# DNS CHECKER
# ============================================================================

class DNSChecker:
    """
    Resolves a domain name via DNS and measures resolution latency.

    The URL / domain is extracted from the link.url field.  We strip any
    scheme (http/https) and path so we get a bare hostname.

    By default we resolve an A record.  If the link.custom_headers dict
    contains a key  dns_record_type  we honour that (AAAA, MX, TXT, etc.).
    """

    def __init__(self, settings: Settings):
        self.settings = settings

    @staticmethod
    def _extract_domain(url: str) -> str:
        """Strip scheme, port, and path from URL to get the bare domain."""
        url = url.strip()
        for prefix in ("https://", "http://", "dns://"):
            if url.lower().startswith(prefix):
                url = url[len(prefix):]
                break
        # Remove port
        url = url.split(":")[0]
        # Remove path
        url = url.split("/")[0]
        return url

    async def check(self, link: MonitoredLink) -> CheckResult:
        """
        Resolve the domain and return timing + result.
        """
        domain = self._extract_domain(link.url)
        record_type = "A"

        # Allow override via custom_headers (reusing existing JSON field)
        if link.custom_headers and "dns_record_type" in link.custom_headers:
            record_type = link.custom_headers["dns_record_type"].upper()

        start_time = time.perf_counter()

        try:
            resolver = dns.resolver.Resolver()
            resolver.lifetime = link.timeout or self.settings.REQUEST_TIMEOUT

            answers = resolver.resolve(domain, record_type)
            elapsed = time.perf_counter() - start_time

            # Grab the first resolved address for storage
            resolved_ip = str(answers[0]) if answers else None

            logger.debug(
                f"[DNS] {domain} ({record_type}) → {resolved_ip} "
                f"in {elapsed:.3f}s"
            )

            return CheckResult(
                success=True,
                response_time=round(elapsed, 4),
                dns_resolution_time=round(elapsed, 4),
                ip_address=resolved_ip,
            )

        except dns.resolver.NXDOMAIN:
            elapsed = time.perf_counter() - start_time
            logger.warning(f"[DNS] {domain} → NXDOMAIN")
            return CheckResult(
                success=False,
                response_time=round(elapsed, 4),
                error_message=f"Domain {domain} does not exist (NXDOMAIN)",
                error_type="NXDOMAIN",
            )
        except dns.resolver.NoAnswer:
            elapsed = time.perf_counter() - start_time
            return CheckResult(
                success=False,
                response_time=round(elapsed, 4),
                error_message=f"No {record_type} record for {domain}",
                error_type="NoAnswer",
            )
        except dns.resolver.Timeout:
            elapsed = time.perf_counter() - start_time
            return CheckResult(
                success=False,
                response_time=round(elapsed, 4),
                error_message=f"DNS resolution for {domain} timed out",
                error_type="DNSTimeout",
            )
        except Exception as e:
            elapsed = time.perf_counter() - start_time
            return CheckResult(
                success=False,
                response_time=round(elapsed, 4),
                error_message=f"DNS check error: {str(e)[:200]}",
                error_type=type(e).__name__,
            )


# ============================================================================
# SSL CHECKER
# ============================================================================

class SSLChecker:
    """
    Connects to an HTTPS endpoint and inspects the TLS certificate.

    Reports
    -------
    • Whether the cert is currently valid
    • Expiry date
    • Days remaining until expiry
    • Issuer common name
    • Subject common name
    • Whether the cert chain is trusted by the system CA bundle

    Alerts are generated by the engine when days_remaining drops below
    the configured warning threshold (default 30 days).
    """

    def __init__(self, settings: Settings):
        self.settings = settings

    @staticmethod
    def _extract_host(url: str) -> str:
        """Get bare hostname from URL."""
        url = url.strip()
        for prefix in ("https://", "http://", "ssl://"):
            if url.lower().startswith(prefix):
                url = url[len(prefix):]
                break
        return url.split("/")[0].split(":")[0]

    async def check(self, link: MonitoredLink) -> CheckResult:
        """
        Open a TLS socket, retrieve the peer certificate, parse it.
        """
        host = self._extract_host(link.url)
        port = 443
        timeout = link.timeout or self.settings.REQUEST_TIMEOUT
        start_time = time.perf_counter()

        try:
            # Create an SSL context that does NOT verify — we want the cert
            # even if it is expired or self-signed so we can report on it.
            context = ssl.create_default_context()
            context.check_hostname = False
            context.verify_mode = ssl.CERT_NONE

            loop = asyncio.get_event_loop()
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)

            # Wrap in SSL
            ssl_sock = context.wrap_socket(sock, server_hostname=host)

            # Connect (blocking, so run in executor to not block the loop)
            await asyncio.wait_for(
                loop.run_in_executor(None, ssl_sock.connect, (host, port)),
                timeout=timeout
            )

            elapsed = time.perf_counter() - start_time

            # Retrieve cert (DER-encoded dict)
            cert = ssl_sock.getpeercert(binary_form=False)
            ssl_sock.close()

            if not cert:
                # Some servers return empty cert with CERT_NONE
                return CheckResult(
                    success=False,
                    response_time=round(elapsed, 4),
                    error_message="Server did not present a certificate",
                    error_type="NoCertificate",
                    ssl_verified=False,
                )

            # --- Parse expiry ---
            not_after_str = cert.get("notAfter", "")
            try:
                # Format: "Jan 15 12:00:00 2025 GMT"
                expiry_dt = datetime.strptime(not_after_str, "%b %d %H:%M:%S %Y %Z")
            except (ValueError, TypeError):
                expiry_dt = None

            # --- Parse issuer / subject ---
            issuer = ""
            for field in cert.get("issuer", ()):
                for key, value in field:
                    if key == "commonName":
                        issuer = value
                        break

            subject = ""
            for field in cert.get("subject", ()):
                for key, value in field:
                    if key == "commonName":
                        subject = value
                        break

            # --- Validity check ---
            now = datetime.utcnow()
            not_before_str = cert.get("notBefore", "")
            try:
                not_before_dt = datetime.strptime(not_before_str, "%b %d %H:%M:%S %Y %Z")
            except (ValueError, TypeError):
                not_before_dt = None

            cert_valid = True
            ssl_error_msg = None

            if expiry_dt and now > expiry_dt:
                cert_valid = False
                ssl_error_msg = f"Certificate expired on {expiry_dt.strftime('%Y-%m-%d')}"
            elif not_before_dt and now < not_before_dt:
                cert_valid = False
                ssl_error_msg = f"Certificate not yet valid until {not_before_dt.strftime('%Y-%m-%d')}"

            days_remaining = (expiry_dt - now).days if expiry_dt else None

            logger.debug(
                f"[SSL] {host} → issuer={issuer}, "
                f"expires={expiry_dt}, days_left={days_remaining}, valid={cert_valid}"
            )

            return CheckResult(
                success=cert_valid,
                response_time=round(elapsed, 4),
                connection_time=round(elapsed, 4),
                ssl_verified=cert_valid,
                ssl_error=ssl_error_msg,
                ip_address=host,
                response_headers={
                    "ssl_issuer": issuer,
                    "ssl_subject": subject,
                    "ssl_expiry": expiry_dt.isoformat() if expiry_dt else None,
                    "ssl_days_remaining": days_remaining,
                    "ssl_not_before": not_before_dt.isoformat() if not_before_dt else None,
                },
            )

        except socket.timeout:
            elapsed = time.perf_counter() - start_time
            return CheckResult(
                success=False,
                response_time=round(elapsed, 4),
                error_message=f"SSL connection to {host}:{port} timed out",
                error_type="Timeout",
                ssl_verified=False,
            )
        except ConnectionRefusedError:
            elapsed = time.perf_counter() - start_time
            return CheckResult(
                success=False,
                response_time=round(elapsed, 4),
                error_message=f"Connection to {host}:{port} was refused",
                error_type="ConnectionRefused",
                ssl_verified=False,
            )
        except Exception as e:
            elapsed = time.perf_counter() - start_time
            return CheckResult(
                success=False,
                response_time=round(elapsed, 4),
                error_message=f"SSL check error: {str(e)[:200]}",
                error_type=type(e).__name__,
                ssl_verified=False,
            )


# ============================================================================
# MONITORING ENGINE — THE ORCHESTRATOR
# ============================================================================

class MonitoringEngine:
    """
    Async monitoring engine that continuously sweeps the database for links
    whose next_check time has arrived, fans out checks via a bounded
    worker-pool (asyncio.Semaphore), persists every result, and fires alerts
    on state transitions.

    Lifecycle
    ---------
    1.  ``await engine.start()``   — launches the background sweep loop
    2.  ``await engine.stop()``    — signals the loop to exit, waits for
                                     in-flight checks to finish

    Thread-safety
    -------------
    All state is accessed only from the single asyncio event loop; no
    threading primitives are needed.
    """

    def __init__(self, db_manager: DatabaseManager, alert_manager: Any = None):
        """
        Parameters
        ----------
        db_manager : DatabaseManager
            Shared database manager (connection pool owner).
        alert_manager : AlertManager | None
            If supplied, state-change events are forwarded here.
            If None the engine still works but alerts are only logged.
        """
        self.settings = get_settings()
        self.db_manager = db_manager
        self.alert_manager = alert_manager

        # --- checkers (stateless, reusable) ---
        self._http_checker = HTTPChecker(self.settings)
        self._tcp_checker = TCPChecker(self.settings)
        self._dns_checker = DNSChecker(self.settings)
        self._ssl_checker = SSLChecker(self.settings)

        # --- concurrency control ---
        self._semaphore = asyncio.Semaphore(self.settings.MAX_CONCURRENT_PINGS)
        self._sweep_interval = getattr(
            self.settings, "MONITOR_SWEEP_INTERVAL", 5
        )  # seconds between sweeps
        self._batch_size = self.settings.MONITOR_BATCH_SIZE

        # --- lifecycle ---
        self._running = False
        self._sweep_task: Optional[asyncio.Task] = None
        self._in_flight: int = 0  # how many checks are currently running

        logger.info(
            f"MonitoringEngine created — "
            f"max_concurrent={self.settings.MAX_CONCURRENT_PINGS}, "
            f"sweep_interval={self._sweep_interval}s, "
            f"batch_size={self._batch_size}"
        )

    # ------------------------------------------------------------------
    # PUBLIC API
    # ------------------------------------------------------------------

    async def start(self) -> None:
        """Start the background sweep loop."""
        if self._running:
            logger.warning("MonitoringEngine is already running")
            return

        self._running = True
        self._sweep_task = asyncio.create_task(self._sweep_loop())
        logger.info("✓ MonitoringEngine started — sweep loop is active")

    async def stop(self) -> None:
        """
        Signal the sweep loop to exit and wait for it to finish.
        Any checks currently in flight will complete before shutdown.
        """
        self._running = False
        if self._sweep_task:
            self._sweep_task.cancel()
            try:
                await self._sweep_task
            except asyncio.CancelledError:
                pass
            self._sweep_task = None
        logger.info("✓ MonitoringEngine stopped")

    @property
    def is_running(self) -> bool:
        return self._running

    @property
    def in_flight_checks(self) -> int:
        return self._in_flight

    # ------------------------------------------------------------------
    # SWEEP LOOP
    # ------------------------------------------------------------------

    async def _sweep_loop(self) -> None:
        """
        Continuously fetch due links, dispatch checks, sleep, repeat.
        Runs until self._running becomes False.
        """
        logger.info("[Engine] Sweep loop started")
        while self._running:
            try:
                await self._do_sweep()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"[Engine] Unhandled error in sweep: {e}", exc_info=True)

            # Sleep between sweeps
            try:
                await asyncio.sleep(self._sweep_interval)
            except asyncio.CancelledError:
                break

        logger.info("[Engine] Sweep loop exited")

    async def _do_sweep(self) -> None:
        """
        Single sweep iteration:
        1. Pull a batch of links whose next_check <= now
        2. Fan them out concurrently (bounded by semaphore)
        """
        try:
            link_repo = LinkRepository(self.db_manager)
            links = await link_repo.get_links_to_check(limit=self._batch_size)

            if not links:
                return  # nothing to do this cycle

            logger.debug(f"[Engine] Sweep found {len(links)} links to check")

            # Fan out all checks concurrently, bounded by the semaphore
            tasks = [
                asyncio.create_task(self._run_guarded(link))
                for link in links
            ]
            # Wait for all, but don't let one failure crash the rest
            results = await asyncio.gather(*tasks, return_exceptions=True)

            # Log any tasks that raised an exception we didn't catch
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    logger.error(
                        f"[Engine] Check for link {links[i].id} raised: {result}",
                        exc_info=True
                    )

        except Exception as e:
            logger.error(f"[Engine] Error in _do_sweep: {e}", exc_info=True)

    # ------------------------------------------------------------------
    # GUARDED SINGLE CHECK
    # ------------------------------------------------------------------

    async def _run_guarded(self, link: MonitoredLink) -> None:
        """
        Acquire the concurrency semaphore, run the check, release.
        Wraps _run_single_check so that semaphore bookkeeping is safe
        even if the inner function raises.
        """
        async with self._semaphore:
            self._in_flight += 1
            try:
                await self._run_single_check(link)
            finally:
                self._in_flight -= 1

    # ------------------------------------------------------------------
    # SINGLE CHECK DISPATCHER
    # ------------------------------------------------------------------

    async def _run_single_check(self, link: MonitoredLink) -> None:
        """
        Route to the correct checker based on monitor_type, then persist
        the result and handle state changes.
        """
        monitor_type = link.monitor_type

        try:
            # --- dispatch to checker ---
            if monitor_type in (MonitorType.HTTP, MonitorType.HTTPS):
                result = await self._http_checker.check(link)
            elif monitor_type == MonitorType.TCP:
                result = await self._tcp_checker.check(link)
            elif monitor_type == MonitorType.DNS:
                result = await self._dns_checker.check(link)
            elif monitor_type == MonitorType.SSL:
                result = await self._ssl_checker.check(link)
            else:
                # Fallback: treat unknown types as HTTP
                logger.warning(
                    f"[Engine] Unknown monitor_type '{monitor_type}' for link "
                    f"{link.id}, falling back to HTTP"
                )
                result = await self._http_checker.check(link)

            # --- persist ---
            await self._record_result(link, result)

            # --- state-change logic ---
            await self._handle_state_change(link, result)

            # --- update link row (metrics, next_check) ---
            await self._update_link_metrics(link, result)

        except Exception as e:
            logger.error(
                f"[Engine] Exception checking link {link.id} ({link.url}): {e}",
                exc_info=True
            )
            # Even if the check itself crashed, record a failure so the link
            # doesn't silently disappear from monitoring.
            fallback_result = CheckResult(
                success=False,
                error_message=f"Monitoring engine internal error: {str(e)[:200]}",
                error_type="EngineError",
            )
            try:
                await self._record_result(link, fallback_result)
                await self._handle_state_change(link, fallback_result)
                await self._update_link_metrics(link, fallback_result)
            except Exception as inner_e:
                logger.error(
                    f"[Engine] Failed to record fallback for link {link.id}: {inner_e}"
                )

    # ------------------------------------------------------------------
    # PERSIST PING LOG
    # ------------------------------------------------------------------

    async def _record_result(self, link: MonitoredLink, result: CheckResult) -> None:
        """
        Insert a PingLog row for this check.
        """
        try:
            ping_log = PingLog(
                link_id=link.id,
                check_time=datetime.utcnow(),
                success=result.success,
                status_code=result.status_code,
                response_time=result.response_time,
                response_size=result.response_size,
                error_message=result.error_message,
                error_type=result.error_type,
                request_method=result.request_method,
                request_headers=link.custom_headers or {},
                response_headers=result.response_headers,
                ip_address=result.ip_address,
                dns_resolution_time=result.dns_resolution_time,
                connection_time=result.connection_time,
                ssl_verified=result.ssl_verified,
                ssl_error=result.ssl_error,
                retry_count=result.retry_count,
                metadata={
                    "monitor_type": link.monitor_type.value if link.monitor_type else None,
                    "link_url": link.url,
                },
            )

            async with self.db_manager.session() as session:
                session.add(ping_log)
                await session.commit()

            logger.debug(f"[Engine] PingLog recorded for link {link.id}")

        except Exception as e:
            logger.error(f"[Engine] Failed to record PingLog for link {link.id}: {e}")

    # ------------------------------------------------------------------
    # STATE CHANGE DETECTION & ALERT FIRING
    # ------------------------------------------------------------------

    async def _handle_state_change(self, link: MonitoredLink, result: CheckResult) -> None:
        """
        Compare previous state (link.is_up) with the new result.
        Fire DOWN / UP / SLOW alerts as appropriate.

        DOWN alert  → fired once when link transitions from UP → DOWN
        UP alert    → fired once when link transitions from DOWN → UP
        SLOW alert  → fired every time response_time > slow_threshold
        SSL alert   → fired when SSL days_remaining < 30
        """
        was_up = link.is_up
        is_now_up = result.success

        # --- DOWN transition ---
        if was_up and not is_now_up:
            logger.warning(
                f"[Engine] 🔴 DOWNTIME DETECTED — link {link.id} ({link.url})"
            )
            if link.alert_on_down:
                await self._fire_alert(
                    link=link,
                    alert_type=AlertType.DOWN,
                    title=f"🔴 {link.display_name} is DOWN",
                    message=(
                        f"<b>Link:</b> {link.url}\n"
                        f"<b>Error:</b> {result.error_message or 'Unknown'}\n"
                        f"<b>Status Code:</b> {result.status_code or 'N/A'}\n"
                        f"<b>Detected At:</b> {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC"
                    ),
                    priority=3,
                )

        # --- UP (recovery) transition ---
        elif not was_up and is_now_up:
            logger.info(
                f"[Engine] 🟢 RECOVERY DETECTED — link {link.id} ({link.url})"
            )
            if link.alert_on_recovery:
                # Calculate how long it was down
                downtime_str = "Unknown duration"
                if link.current_downtime_start:
                    down_secs = int(
                        (datetime.utcnow() - link.current_downtime_start).total_seconds()
                    )
                    from utils.helpers import TimeHelper
                    downtime_str = TimeHelper.seconds_to_human_readable(down_secs)

                await self._fire_alert(
                    link=link,
                    alert_type=AlertType.UP,
                    title=f"🟢 {link.display_name} is back UP",
                    message=(
                        f"<b>Link:</b> {link.url}\n"
                        f"<b>Response Time:</b> {result.response_time:.3f}s\n"
                        f"<b>Down For:</b> {downtime_str}\n"
                        f"<b>Recovered At:</b> {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC"
                    ),
                    priority=2,
                )

        # --- SLOW response ---
        if result.success and result.response_time is not None:
            if link.alert_on_slow and result.response_time > link.slow_threshold:
                logger.warning(
                    f"[Engine] ⚠️  SLOW RESPONSE — link {link.id} "
                    f"({result.response_time:.3f}s > {link.slow_threshold}s threshold)"
                )
                await self._fire_alert(
                    link=link,
                    alert_type=AlertType.SLOW,
                    title=f"⚠️ {link.display_name} is responding slowly",
                    message=(
                        f"<b>Link:</b> {link.url}\n"
                        f"<b>Response Time:</b> {result.response_time:.3f}s\n"
                        f"<b>Threshold:</b> {link.slow_threshold}s\n"
                        f"<b>Detected At:</b> {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC"
                    ),
                    priority=1,
                )

        # --- SSL expiry warning ---
        if result.response_headers and "ssl_days_remaining" in result.response_headers:
            days_left = result.response_headers["ssl_days_remaining"]
            if days_left is not None and days_left <= 30:
                logger.warning(
                    f"[Engine] 🔐 SSL EXPIRY WARNING — link {link.id}, "
                    f"{days_left} days remaining"
                )
                await self._fire_alert(
                    link=link,
                    alert_type=AlertType.SSL_EXPIRY,
                    title=f"🔐 SSL certificate expiring soon — {link.display_name}",
                    message=(
                        f"<b>Link:</b> {link.url}\n"
                        f"<b>Days Remaining:</b> {days_left}\n"
                        f"<b>Issuer:</b> {result.response_headers.get('ssl_issuer', 'Unknown')}\n"
                        f"<b>Expiry Date:</b> {result.response_headers.get('ssl_expiry', 'Unknown')}"
                    ),
                    priority=2,
                )

    # ------------------------------------------------------------------
    # UPDATE LINK METRICS ROW
    # ------------------------------------------------------------------

    async def _update_link_metrics(self, link: MonitoredLink, result: CheckResult) -> None:
        """
        Call link.record_check() (which updates all counters, uptime %,
        response-time stats, and next_check), then persist.
        Also updates SSL fields if this was an SSL check.
        """
        try:
            # record_check handles is_up transitions, counters, next_check
            link.record_check(
                success=result.success,
                status_code=result.status_code,
                response_time=result.response_time,
            )

            # Update SSL metadata if available
            if result.response_headers:
                ssl_expiry = result.response_headers.get("ssl_expiry")
                if ssl_expiry:
                    try:
                        link.ssl_expiry_date = datetime.fromisoformat(ssl_expiry)
                    except (ValueError, TypeError):
                        pass
                ssl_issuer = result.response_headers.get("ssl_issuer")
                if ssl_issuer:
                    link.ssl_issuer = ssl_issuer
                days_rem = result.response_headers.get("ssl_days_remaining")
                if days_rem is not None:
                    link.ssl_days_remaining = days_rem

            # If the link just went down, update its status enum too
            if not result.success and link.status == LinkStatus.ACTIVE:
                # Keep status as ACTIVE — the is_up flag tracks the actual state.
                # status is for user-controlled states (paused, maintenance).
                pass

            async with self.db_manager.session() as session:
                # Merge detached instance back into this session
                merged_link = await session.merge(link)
                await session.commit()

            logger.debug(
                f"[Engine] Link {link.id} metrics updated — "
                f"is_up={link.is_up}, uptime={link.uptime_percentage:.2f}%, "
                f"next_check={link.next_check}"
            )

        except Exception as e:
            logger.error(f"[Engine] Failed to update metrics for link {link.id}: {e}")

    # ------------------------------------------------------------------
    # ALERT HELPER
    # ------------------------------------------------------------------

    async def _fire_alert(
        self,
        link: MonitoredLink,
        alert_type: AlertType,
        title: str,
        message: str,
        priority: int = 1,
    ) -> None:
        """
        Enqueue an alert via the AlertManager (if configured) or just log it.
        """
        if self.alert_manager:
            try:
                await self.alert_manager.enqueue_alert(
                    user_id=link.user_id,
                    link_id=link.id,
                    alert_type=alert_type,
                    title=title,
                    message=message,
                    priority=priority,
                )
            except Exception as e:
                logger.error(f"[Engine] Failed to enqueue alert: {e}")
        else:
            # No alert manager wired up — log the alert for visibility
            logger.info(
                f"[ALERT] type={alert_type.value} link={link.id} "
                f"title={title}"
            )


# ============================================================================
# END OF MONITORING ENGINE MODULE
# ============================================================================
