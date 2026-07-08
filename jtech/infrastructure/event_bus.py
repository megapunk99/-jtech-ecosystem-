"""
JTECH Event Bus — Central event system with full audit trail.

Every action in JTECH is logged as an event. Events are:
- Persisted to SQLite via StateManager
- Emitted in real-time to subscribers
- Classified by type, severity, and source
- Searchable and filterable for audit

This is the nervous system of JTECH — everything flows through here.
"""

from __future__ import annotations

import json
import logging
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Optional

logger = logging.getLogger(__name__)


class EventSeverity(Enum):
    DEBUG = "debug"
    INFO = "info"
    SUCCESS = "success"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class EventCategory(Enum):
    SYSTEM = "system"               # System operations
    PROJECT = "project"             # Project lifecycle
    BUILD = "build"                 # Product building
    SALE = "sale"                   # Sales
    ACCESS = "access"               # Computer/permission access
    ERROR = "error"                 # Errors
    COMMAND = "command"             # CLI commands
    EXTERNAL = "external"           # External API calls
    USER = "user"                   # User actions
    SECURITY = "security"           # Security-related
    INFRASTRUCTURE = "infrastructure"  # Infrastructure operations


@dataclass
class Event:
    """A single event in the JTECH event system."""
    type: str
    source: str
    message: str
    severity: EventSeverity = EventSeverity.INFO
    category: EventCategory = EventCategory.SYSTEM
    details: Optional[dict] = None
    timestamp: Optional[str] = None
    id: Optional[int] = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now().isoformat()


class AuditLog:
    """
    Structured audit log for compliance and debugging.

    Every event is stored with:
    - Who (source)
    - What (action/event type)
    - When (timestamp)
    - Why (context/details)
    - Severity
    """

    def __init__(self, state_manager=None):
        self._state = state_manager
        self._events: list[Event] = []
        self._lock = threading.Lock()

    def record(self, event: Event) -> int:
        """Record an event to the audit log and persistent storage."""
        with self._lock:
            self._events.append(event)

            # Persist via state manager if available
            event_id = 0
            if self._state:
                try:
                    event_id = self._state.record_event(
                        event_type=event.type,
                        message=event.message,
                        source=event.source,
                        severity=event.severity.value,
                        details={
                            "category": event.category.value,
                            **(event.details or {}),
                        }
                    )
                except Exception as e:
                    logger.error(f"Failed to persist event: {e}")

            # Log to Python logger
            log_level = {
                EventSeverity.DEBUG: logging.DEBUG,
                EventSeverity.INFO: logging.INFO,
                EventSeverity.SUCCESS: logging.INFO,
                EventSeverity.WARNING: logging.WARNING,
                EventSeverity.ERROR: logging.ERROR,
                EventSeverity.CRITICAL: logging.CRITICAL,
            }.get(event.severity, logging.INFO)

            logger.log(log_level,
                       f"[{event.category.value}] {event.source} — {event.message}")

            return event_id or len(self._events)

    def query(self, event_type: Optional[str] = None,
              source: Optional[str] = None,
              severity: Optional[EventSeverity] = None,
              category: Optional[EventCategory] = None,
              limit: int = 100) -> list[Event]:
        """Query events with filters."""
        results = list(self._events)

        if event_type:
            results = [e for e in results if e.type == event_type]
        if source:
            results = [e for e in results if e.source == source]
        if severity:
            results = [e for e in results if e.severity == severity]
        if category:
            results = [e for e in results if e.category == category]

        return results[-limit:]

    def get_recent(self, limit: int = 20) -> list[Event]:
        """Get most recent events."""
        return self._events[-limit:]

    def count_by_severity(self) -> dict[str, int]:
        """Count events by severity."""
        counts = {}
        for event in self._events:
            sev = event.severity.value
            counts[sev] = counts.get(sev, 0) + 1
        return counts


class EventBus:
    """
    Central event bus for JTECH.

    Features:
    - Publish/subscribe pattern
    - Event filtering per subscriber
    - Asynchronous delivery
    - Audit log integration
    - Error isolation (one subscriber can't crash others)
    """

    def __init__(self, audit_log: Optional[AuditLog] = None):
        self._subscribers: dict[str, list[Callable]] = {}
        self._audit_log = audit_log or AuditLog()
        self._lock = threading.Lock()

    def subscribe(self, event_type: str, callback: Callable[[Event], None]) -> None:
        """Subscribe to events of a specific type."""
        with self._lock:
            if event_type not in self._subscribers:
                self._subscribers[event_type] = []
            self._subscribers[event_type].append(callback)

    def subscribe_all(self, callback: Callable[[Event], None]) -> None:
        """Subscribe to ALL events."""
        self.subscribe("*", callback)

    def unsubscribe(self, event_type: str, callback: Callable) -> bool:
        """Unsubscribe from events."""
        with self._lock:
            if event_type in self._subscribers:
                try:
                    self._subscribers[event_type].remove(callback)
                    return True
                except ValueError:
                    pass
            return False

    def emit(self, event: Event) -> int:
        """Emit an event to all subscribers and the audit log."""
        # Record in audit log
        event_id = self._audit_log.record(event)

        # Notify subscribers
        with self._lock:
            # Direct type subscribers
            for cb in self._subscribers.get(event.type, []):
                try:
                    cb(event)
                except Exception as e:
                    logger.error(f"Event subscriber failed for {event.type}: {e}")

            # Wildcard subscribers
            for cb in self._subscribers.get("*", []):
                try:
                    cb(event)
                except Exception as e:
                    logger.error(f"Wildcard subscriber failed: {e}")

        return event_id

    def emit_simple(self, event_type: str, message: str,
                    source: str = "system",
                    severity: EventSeverity = EventSeverity.INFO,
                    category: EventCategory = EventCategory.SYSTEM,
                    details: Optional[dict] = None) -> int:
        """Create and emit an event in one call."""
        event = Event(
            type=event_type,
            source=source,
            message=message,
            severity=severity,
            category=category,
            details=details,
        )
        return self.emit(event)

    def get_audit(self) -> AuditLog:
        """Get the audit log."""
        return self._audit_log

    def get_recent_events(self, limit: int = 50) -> list[Event]:
        """Get recent events from the audit log."""
        return self._audit_log.get_recent(limit)


# Global singleton
_bus: Optional[EventBus] = None


def get_event_bus() -> EventBus:
    """Get or create the global event bus singleton."""
    global _bus
    if _bus is None:
        _bus = EventBus()
    return _bus
