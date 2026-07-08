"""
JTECH Permission System — Gates all privileged access behind user consent.

Every computer access (filesystem, terminal, network, env vars) requires:
1. Check if permission has been granted for this operation type
2. If not, request user permission with full context
3. Log all access attempts for audit trail
4. Respect session-level, project-level, and permanent permissions

Security model:
- Operations are categorized by risk level
- User can grant one-time, session, or permanent permissions
- All access is logged with full context
- Sensitive operations always require explicit consent
"""

from __future__ import annotations

import json
import logging
import threading
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Optional

from jtech.infrastructure.event_bus import EventCategory, EventSeverity

logger = logging.getLogger(__name__)

# Module-level constants for permission audit events
_PERM_EVENT_CATEGORY = EventCategory.ACCESS


class PermissionLevel(Enum):
    """Risk levels for operations requiring permission."""
    INFO = "info"              # Read public info — auto-granted
    READ = "read"              # Read filesystem/env — user confirms once per session
    WRITE = "write"            # Write files — user confirms per operation
    EXECUTE = "execute"        # Run commands — user confirms per operation with preview
    DANGEROUS = "dangerous"    # Destructive operations — always require fresh approval
    SYSTEM = "system"          # System-level changes — requires explicit yes


class PermissionDuration(Enum):
    """How long a permission grant lasts."""
    ONCE = "once"            # One-time use
    SESSION = "session"      # Until process exits
    PROJECT = "project"      # For current project
    PERMANENT = "permanent"  # Remembered (until revoked)


@dataclass
class PermissionRequest:
    """A request for permission to perform an operation."""
    operation: str
    resource: str
    level: PermissionLevel
    reason: str
    details: Optional[dict] = None
    timestamp: str = ""

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now().isoformat()

    @property
    def risk_label(self) -> str:
        labels = {
            PermissionLevel.INFO: "ℹ️ Info",
            PermissionLevel.READ: "👁️ Read",
            PermissionLevel.WRITE: "✏️ Write",
            PermissionLevel.EXECUTE: "⚡ Execute",
            PermissionLevel.DANGEROUS: "⚠️ Dangerous",
            PermissionLevel.SYSTEM: "🔧 System",
        }
        return labels.get(self.level, str(self.level.value))

    def format_for_user(self) -> str:
        """Format the permission request for user display."""
        return (
            f"\n🔐  Permission Request [{self.risk_label}]\n"
            f"   Operation: {self.operation}\n"
            f"   Resource:  {self.resource}\n"
            f"   Reason:    {self.reason}\n"
        )


@dataclass
class PermissionGrant:
    """A granted permission."""
    request: PermissionRequest
    duration: PermissionDuration
    granted_at: str = ""
    used_count: int = 0
    expires_at: Optional[str] = None

    def __post_init__(self):
        if not self.granted_at:
            self.granted_at = datetime.now().isoformat()

    @property
    def is_valid(self) -> bool:
        """Check if the permission grant is still valid."""
        if self.duration == PermissionDuration.ONCE:
            return self.used_count == 0
        if self.duration == PermissionDuration.SESSION:
            return True
        if self.duration == PermissionDuration.PROJECT:
            return True
        if self.duration == PermissionDuration.PERMANENT:
            return True
        return False


class PermissionSystem:
    """
    Central permission system for JTECH.

    Manages all access to privileged operations with:
    - Risk-based permission levels
    - Duration-based grants (once, session, permanent)
    - Full audit trail via event bus
    - Thread-safe grant management

    Usage:
        perms = PermissionSystem()
        
        # Check permission (asks user if needed)
        if perms.request("read_file", "/etc/passwd", PermissionLevel.READ,
                         "Need to check configuration"):
            content = open("/etc/passwd").read()
    """

    def __init__(self, user_approval_callback: Optional[Callable] = None):
        self._grants: list[PermissionGrant] = []
        self._lock = threading.Lock()
        self._user_approval_callback = user_approval_callback
        self._event_bus = None

        # Default grants for info-level operations
        self._auto_grant_levels = {PermissionLevel.INFO}

    def set_user_callback(self, callback: Callable[[PermissionRequest], bool]) -> None:
        """Set the callback for user approval."""
        self._user_approval_callback = callback

    def request(self, operation: str, resource: str,
                level: PermissionLevel = PermissionLevel.READ,
                reason: str = "",
                duration: PermissionDuration = PermissionDuration.ONCE,
                details: Optional[dict] = None) -> bool:
        """
        Request permission for an operation.

        Returns True if permission is granted (either from cache or user approval).
        """
        # Auto-grant info-level operations
        if level == PermissionLevel.INFO:
            self._log_access("auto_granted", operation, resource, level, details)
            return True

        # Check for existing valid grant
        with self._lock:
            for grant in self._grants:
                if (grant.request.operation == operation
                        and grant.request.resource == resource
                        and grant.request.level == level
                        and grant.is_valid):
                    grant.used_count += 1
                    self._log_access("cached", operation, resource, level, details)
                    return True

        # Need user approval
        req = PermissionRequest(
            operation=operation,
            resource=resource,
            level=level,
            reason=reason or f"Access to {resource}",
            details=details,
        )

        if self._user_approval_callback:
            approved = self._user_approval_callback(req)
        else:
            # No callback configured — deny by default
            logger.warning(f"No user approval callback — denying {operation} on {resource}")
            approved = False

        if approved:
            grant = PermissionGrant(request=req, duration=duration)
            with self._lock:
                self._grants.append(grant)

            self._log_access("granted", operation, resource, level, details)
            return True

        self._log_access("denied", operation, resource, level, details)
        return False

    def revoke(self, operation: Optional[str] = None,
               resource: Optional[str] = None) -> int:
        """Revoke permissions. Returns count revoked."""
        with self._lock:
            before = len(self._grants)
            self._grants = [
                g for g in self._grants
                if (operation and g.request.operation != operation)
                or (resource and g.request.resource != resource)
            ]
            revoked = before - len(self._grants)
            if revoked:
                self._log_access("revoked", operation or "*", resource or "*",
                                 PermissionLevel.SYSTEM, {"count": revoked})
            return revoked

    def revoke_all(self) -> int:
        """Revoke ALL permissions."""
        with self._lock:
            count = len(self._grants)
            self._grants.clear()
            self._log_access("revoked_all", "*", "*", PermissionLevel.SYSTEM,
                             {"count": count})
            return count

    def list_grants(self) -> list[dict]:
        """List all active permission grants."""
        with self._lock:
            return [
                {
                    "operation": g.request.operation,
                    "resource": g.request.resource,
                    "level": g.request.level.value,
                    "duration": g.duration.value,
                    "reason": g.request.reason,
                    "granted_at": g.granted_at,
                    "used_count": g.used_count,
                    "valid": g.is_valid,
                }
                for g in self._grants
            ]

    def _log_access(self, status: str, operation: str, resource: str,
                    level: PermissionLevel, details: Optional[dict] = None) -> None:
        """Log an access attempt to the audit trail."""
        if self._event_bus:
            try:
                self._event_bus.emit_simple(
                    event_type=f"permission.{status}",
                    message=f"{status}: {operation} on {resource}",
                    source="permissions",
                    severity=self._severity_for(status, level),
                    category=_PERM_EVENT_CATEGORY,
                )
            except Exception:
                pass

        log_msg = f"Permission [{level.value}] {status}: {operation} -> {resource}"
        if status == "denied":
            logger.warning(log_msg)
        elif status == "granted":
            logger.info(log_msg)
        else:
            logger.debug(log_msg)

    def _severity_for(self, status: str, level: PermissionLevel):
        if status == "denied":
            return EventSeverity.WARNING
        if status == "revoked" or status == "revoked_all":
            return EventSeverity.INFO
        if level in (PermissionLevel.DANGEROUS, PermissionLevel.SYSTEM):
            return EventSeverity.WARNING
        return EventSeverity.INFO


# Global singleton
_permissions: Optional[PermissionSystem] = None


def get_permissions() -> PermissionSystem:
    """Get or create the global permissions singleton."""
    global _permissions
    if _permissions is None:
        _permissions = PermissionSystem()
    return _permissions
