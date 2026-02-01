"""
============================================================================
TELEGRAM UPTIME BOT - MONITORING PACKAGE
============================================================================
Part 3: Monitoring Engine & Utilities

This package contains all the runtime monitoring infrastructure:
    • MonitoringEngine   — the core async checker that pings every link
    • AlertManager       — cooldown / rate-limit / Telegram delivery
    • HealthServer       — aiohttp keep-alive server for Render
    • SelfPinger         — background task that pings itself on Render
    • Scheduler          — periodic background job runner

Place these files inside a  monitoring/  sub-directory in your project root
alongside the  config/ , database/ , utils/ , and  bot/  packages.

File layout (Part 3 additions)
-----------------------------
monitoring/
├── __init__.py          ← this file
├── monitor.py           ← MonitoringEngine + HTTP/TCP/DNS/SSL checkers
├── alerts.py            ← AlertManager
├── self_ping.py         ← HealthServer + SelfPinger
└── scheduler.py         ← Scheduler + built-in periodic jobs

============================================================================
"""

from monitoring.monitor import MonitoringEngine, HTTPChecker, TCPChecker, DNSChecker, SSLChecker, CheckResult
from monitoring.alerts import AlertManager, AlertPayload
from monitoring.self_ping import HealthServer, SelfPinger
from monitoring.scheduler import Scheduler, ScheduledJob

__all__ = [
    # Monitoring Engine
    "MonitoringEngine",
    "HTTPChecker",
    "TCPChecker",
    "DNSChecker",
    "SSLChecker",
    "CheckResult",

    # Alerts
    "AlertManager",
    "AlertPayload",

    # Render Keep-Alive
    "HealthServer",
    "SelfPinger",

    # Scheduler
    "Scheduler",
    "ScheduledJob",
]
