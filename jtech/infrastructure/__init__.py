"""
JTECH Infrastructure — Bulletproof foundation for the entire system.

Provides:
- Error handling with circuit breakers, retry, and fallback
- SQLite-backed persistent state management
- Event bus with full audit trail
- Health monitoring and self-diagnostics
- Permission system for computer access control
"""

from jtech.infrastructure.error_handler import ErrorHandler, CircuitBreaker, RetryConfig
from jtech.infrastructure.state_manager import StateManager
from jtech.infrastructure.event_bus import EventBus, AuditLog
from jtech.infrastructure.health_monitor import HealthMonitor, HealthStatus
from jtech.infrastructure.permissions import PermissionSystem, PermissionLevel

__all__ = [
    "ErrorHandler", "CircuitBreaker", "RetryConfig",
    "StateManager",
    "EventBus", "AuditLog",
    "HealthMonitor", "HealthStatus",
    "PermissionSystem", "PermissionLevel",
]
