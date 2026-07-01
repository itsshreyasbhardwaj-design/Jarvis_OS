"""
Logging Configuration
=====================
Configures Loguru for structured, multi-destination logging.

Outputs:
- Console: Rich-formatted human-readable output (development)
- File: JSON-formatted structured log (production, supports log aggregators)
- Audit: Separate stream for security-critical events

Log Levels used by JARVIS:
- TRACE:   Detailed debug info (verbose, disable in production)
- DEBUG:   Developer debugging
- INFO:    Normal operational events
- SUCCESS: Module started, task completed
- WARNING: Degraded state, non-critical errors
- ERROR:   Operation failed, needs attention
- CRITICAL: System-level failure
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import TYPE_CHECKING

from loguru import logger

if TYPE_CHECKING:
    from jarvis.config.settings import Settings


def configure_logging(settings: Settings) -> None:
    """
    Configure Loguru based on application settings.
    Called once during application initialization.
    """
    # Remove default handler
    logger.remove()

    log_level = settings.log_level.upper()
    log_format_console = (
        "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
        "<level>{message}</level>"
    )
    log_format_json = (
        '{{"time": "{time:YYYY-MM-DDTHH:mm:ss.SSSZ}", '
        '"level": "{level}", '
        '"logger": "{name}", '
        '"function": "{function}", '
        '"line": {line}, '
        '"message": "{message}"}}'
    )

    # --- Console Handler ---
    logger.add(
        sys.stderr,
        level=log_level,
        format=log_format_console,
        colorize=True,
        backtrace=True,
        diagnose=settings.environment == "development",
    )

    # --- File Handler ---
    log_file = Path(settings.log_file)
    log_file.parent.mkdir(parents=True, exist_ok=True)

    logger.add(
        str(log_file),
        level=log_level,
        format=log_format_json if settings.log_format == "json" else log_format_console,
        rotation=settings.log_rotation,
        retention=settings.log_retention,
        compression="gz",
        backtrace=True,
        diagnose=False,  # Never include local vars in file logs (security)
        enqueue=True,    # Thread-safe async logging
    )

    # --- Performance Logger (separate file for latency metrics) ---
    perf_log = log_file.parent / "performance.log"
    logger.add(
        str(perf_log),
        level="DEBUG",
        filter=lambda record: "performance" in record["extra"],
        format="{time:YYYY-MM-DDTHH:mm:ss.SSS} | {message}",
        rotation="1 day",
        retention="7 days",
        enqueue=True,
    )

    logger.debug(
        f"Logging configured: level={log_level}, "
        f"file={log_file}, format={settings.log_format}"
    )
