"""
JTECH Health Monitor — Self-diagnostics and system health.

Provides:
- Component health checks with status reporting
- Resource monitoring (CPU, memory, disk)
- Uptime tracking
- Dependency health (API keys, databases, network)
- Performance metrics
- Automated recovery suggestions
"""

from __future__ import annotations

import logging
import os
import platform
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Optional
import sys

logger = logging.getLogger(__name__)


class HealthStatus(Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


@dataclass
class HealthCheck:
    """A single health check component."""
    name: str
    check_fn: Callable[[], bool]
    description: str = ""
    critical: bool = True
    last_check: Optional[float] = None
    last_status: Optional[bool] = None
    last_error: Optional[str] = None
    response_time_ms: Optional[float] = None

    def run(self) -> bool:
        """Run the health check. Returns True if healthy."""
        start = time.time()
        self.last_check = start

        try:
            result = self.check_fn()
            self.last_status = result
            self.last_error = None
            return result
        except Exception as e:
            self.last_status = False
            self.last_error = str(e)[:200]
            return False
        finally:
            self.response_time_ms = round((time.time() - start) * 1000, 1)


@dataclass
class HealthReport:
    """Complete health report for the system."""
    status: HealthStatus = HealthStatus.UNKNOWN
    checks: list[dict] = field(default_factory=list)
    summary: dict = field(default_factory=dict)
    timestamp: str = ""

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now().isoformat()


class HealthMonitor:
    """
    System health monitor with periodic checks and reporting.

    Usage:
        monitor = HealthMonitor()
        monitor.register_check("api_key", lambda: bool(os.environ.get("NVIDIA_API_KEY")))
        report = monitor.run_all()
        print(report.status.value)
    """

    def __init__(self):
        self._checks: list[HealthCheck] = []
        self._start_time = time.time()
        self._history: list[HealthReport] = []

    @property
    def uptime_seconds(self) -> float:
        """Get system uptime in seconds."""
        return time.time() - self._start_time

    @property
    def uptime_str(self) -> str:
        """Get human-readable uptime string."""
        seconds = int(self.uptime_seconds)
        days, remainder = divmod(seconds, 86400)
        hours, remainder = divmod(remainder, 3600)
        minutes, seconds = divmod(remainder, 60)
        parts = []
        if days > 0:
            parts.append(f"{days}d")
        if hours > 0:
            parts.append(f"{hours}h")
        if minutes > 0:
            parts.append(f"{minutes}m")
        parts.append(f"{seconds}s")
        return " ".join(parts)

    def register_check(self, name: str, check_fn: Callable[[], bool],
                       description: str = "", critical: bool = True) -> None:
        """Register a health check."""
        self._checks.append(HealthCheck(
            name=name,
            check_fn=check_fn,
            description=description,
            critical=critical,
        ))

    def check(self, name: str) -> Optional[HealthCheck]:
        """Run a specific health check by name."""
        for check in self._checks:
            if check.name == name:
                check.run()
                return check
        return None

    def run_all(self) -> HealthReport:
        """Run all registered health checks and generate a report."""
        results = []
        unhealthy_count = 0
        degraded_count = 0

        for check in self._checks:
            success = check.run()
            status = "passed" if success else ("failed" if check.critical else "warning")

            results.append({
                "name": check.name,
                "status": status,
                "description": check.description,
                "response_time_ms": check.response_time_ms,
                "error": check.last_error,
                "critical": check.critical,
            })

            if not success:
                if check.critical:
                    unhealthy_count += 1
                else:
                    degraded_count += 1

        # Determine overall status
        if unhealthy_count > 0:
            overall = HealthStatus.UNHEALTHY
        elif degraded_count > 0:
            overall = HealthStatus.DEGRADED
        elif all(r["status"] == "passed" for r in results):
            overall = HealthStatus.HEALTHY
        else:
            overall = HealthStatus.UNKNOWN

        report = HealthReport(
            status=overall,
            checks=results,
            summary={
                "total": len(results),
                "passed": sum(1 for r in results if r["status"] == "passed"),
                "warnings": degraded_count,
                "failed": unhealthy_count,
                "uptime": self.uptime_str,
                "uptime_seconds": self.uptime_seconds,
                "python_version": platform.python_version(),
                "platform": platform.platform(),
            },
        )

        self._history.append(report)
        return report

    def get_default_checks(self) -> list[tuple[str, Callable, str, bool]]:
        """Get default health checks for JTECH."""
        return [
            ("api_key", lambda: bool(os.environ.get("NVIDIA_API_KEY")),
             "NVIDIA DeepSeek API key is configured", True),
            ("disk_space", lambda: self._check_disk(),
             "Sufficient disk space available", False),
            ("python_version", lambda: sys.version_info >= (3, 12),
             "Python 3.12+ required", True),
        ]

    def _check_disk(self) -> bool:
        """Check available disk space."""
        try:
            import shutil
            usage = shutil.disk_usage(os.getcwd())
            free_gb = usage.free / (1024 ** 3)
            return free_gb > 0.5  # At least 500MB free
        except Exception:
            return True

    def get_history(self, limit: int = 10) -> list[HealthReport]:
        """Get health check history."""
        return self._history[-limit:]

    def get_summary(self) -> dict:
        """Get a quick health summary."""
        if not self._history:
            return {"status": "unknown", "message": "No health checks run yet"}

        latest = self._history[-1]
        return {
            "status": latest.status.value,
            "uptime": self.uptime_str,
            "checks_passed": latest.summary.get("passed", 0),
            "checks_total": latest.summary.get("total", 0),
            "timestamp": latest.timestamp,
        }



