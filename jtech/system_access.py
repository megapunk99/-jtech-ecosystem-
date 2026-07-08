"""
JTECH System Access — Permission-gated computer access layer.

Every operation that touches the user's computer goes through this layer:
- Filesystem: read/write/list files
- Terminal: execute commands
- Environment: read environment variables
- System: monitor CPU, memory, disk

All operations require EXPLICIT user permission via PermissionSystem.
Every access is logged with full audit trail.

No operation is performed without the user knowing and consenting.
"""

from __future__ import annotations

import json
import logging
import os
import platform
import re
import shutil
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from jtech.infrastructure.permissions import (
    PermissionSystem, PermissionLevel, PermissionDuration, PermissionRequest,
    get_permissions,
)
from jtech.infrastructure.event_bus import EventBus, EventSeverity, EventCategory, get_event_bus

logger = logging.getLogger(__name__)

# ── SAFE COMMANDS (auto-allowed for Info level) ─────────────────

SAFE_COMMANDS = [
    "ls", "dir", "echo", "pwd", "whoami", "hostname", "date",
    "python --version", "python3 --version", "node --version",
    "npm --version", "git --version", "which", "type",
    "cat", "head", "tail", "wc", "sort", "uniq",
    "find", "locate", "stat",
    "ps aux", "top -bn1", "uptime", "df -h", "free -h",
    "uname -a", "id",
]

BLOCKED_COMMANDS = [
    "rm -rf /", "rm -rf ~", "rm -rf .",
    "dd if=", "mkfs", "fdisk", "format",
    "chmod 777 /", "chown",
    "sudo", "su ",
    ":(){ :|:& };:",  # Fork bomb
    "wget ", "curl ",  # Downloads — need permission
    "shutdown", "reboot", "halt",
    "passwd", "useradd", "userdel",
    "kill -9", "pkill",
]


def _is_safe_command(command: str) -> bool:
    """Check if a command is safe to auto-execute."""
    cmd_lower = command.strip().lower()

    # Check blocked commands
    for blocked in BLOCKED_COMMANDS:
        if blocked in cmd_lower:
            return False

    # Check safe commands
    for safe in SAFE_COMMANDS:
        if cmd_lower.startswith(safe):
            return True

    return False


class SystemAccess:
    """
    Permission-gated access to the user's computer.

    Every method in this class:
    1. Checks permission via PermissionSystem
    2. Logs the access attempt
    3. Performs the operation (if permitted)
    4. Logs the result

    Usage:
        access = SystemAccess()
        
        # Read a file (asks for permission)
        content = access.read_file("/path/to/file")
        
        # Run a command (asks for permission)
        result = access.run_command("ls -la")
    """

    def __init__(self, permissions: Optional[PermissionSystem] = None,
                 event_bus: Optional[EventBus] = None):
        self.permissions = permissions or get_permissions()
        self.event_bus = event_bus or get_event_bus()

    # ── FILESYSTEM ──────────────────────────────────────────────

    def read_file(self, path: str, max_bytes: int = 1_000_000) -> Optional[str]:
        """Read a file with permission check. Returns content or None."""
        resolved = str(Path(path).resolve())

        if not self.permissions.request(
            operation="read_file",
            resource=resolved,
            level=PermissionLevel.READ,
            reason=f"Read file: {Path(path).name}",
        ):
            return None

        try:
            path_obj = Path(resolved)
            if not path_obj.exists():
                logger.error(f"File not found: {resolved}")
                return None
            if path_obj.stat().st_size > max_bytes:
                logger.warning(f"File too large ({path_obj.stat().st_size} bytes): {resolved}")
                return None

            with open(path_obj, "r", encoding="utf-8", errors="replace") as f:
                content = f.read()

            self.event_bus.emit_simple(
                event_type="access.file_read",
                message=f"Read file: {Path(path).name} ({len(content)} bytes)",
                source="system_access",
                severity=EventSeverity.INFO,
                category=EventCategory.ACCESS,
                details={"path": resolved, "size": len(content)},
            )
            return content

        except Exception as e:
            logger.error(f"Failed to read {resolved}: {e}")
            return None

    def write_file(self, path: str, content: str) -> bool:
        """Write a file with permission check."""
        resolved = str(Path(path).resolve())

        # Preview first few lines for user
        preview = "\n".join(content.split("\n")[:5])
        if len(content) > 500:
            preview += "\n..."

        if not self.permissions.request(
            operation="write_file",
            resource=resolved,
            level=PermissionLevel.WRITE,
            reason=f"Write {len(content)} bytes to {Path(path).name}",
            details={"size": len(content), "preview": preview},
        ):
            return False

        try:
            path_obj = Path(resolved)
            path_obj.parent.mkdir(parents=True, exist_ok=True)
            with open(path_obj, "w", encoding="utf-8") as f:
                f.write(content)

            self.event_bus.emit_simple(
                event_type="access.file_written",
                message=f"Wrote {len(content)} bytes to {Path(path).name}",
                source="system_access",
                severity=EventSeverity.SUCCESS,
                category=EventCategory.ACCESS,
                details={"path": resolved, "size": len(content)},
            )
            return True

        except Exception as e:
            logger.error(f"Failed to write {resolved}: {e}")
            return False

    def list_directory(self, path: str = ".") -> Optional[list[dict]]:
        """List directory contents with permission check."""
        resolved = str(Path(path).resolve())

        if not self.permissions.request(
            operation="list_directory",
            resource=resolved,
            level=PermissionLevel.READ,
            reason=f"List contents of {Path(path).name}",
        ):
            return None

        try:
            path_obj = Path(resolved)
            if not path_obj.is_dir():
                logger.error(f"Not a directory: {resolved}")
                return None

            items = []
            for entry in sorted(path_obj.iterdir(), key=lambda x: (not x.is_dir(), x.name)):
                try:
                    stat = entry.stat()
                    items.append({
                        "name": entry.name,
                        "path": str(entry),
                        "type": "directory" if entry.is_dir() else "file",
                        "size": stat.st_size,
                        "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                    })
                except OSError:
                    continue

            return items

        except Exception as e:
            logger.error(f"Failed to list {resolved}: {e}")
            return None

    def path_exists(self, path: str) -> bool:
        """Check if path exists with info-level permission."""
        if not self.permissions.request(
            operation="path_check",
            resource=path,
            level=PermissionLevel.INFO,
            reason=f"Check if path exists",
        ):
            return False
        return Path(path).exists()

    # ── TERMINAL ────────────────────────────────────────────────

    def run_command(self, command: str, timeout: int = 30,
                    capture_output: bool = True) -> dict:
        """
        Run a shell command with permission check.

        Args:
            command: Shell command to run
            timeout: Timeout in seconds
            capture_output: Whether to capture stdout/stderr

        Returns:
            dict with keys: success, stdout, stderr, exit_code, command
        """
        # Check for blocked commands
        if not _is_safe_command(command):
            # Higher risk — require explicit permission
            level = PermissionLevel.EXECUTE
        else:
            level = PermissionLevel.INFO

        if not self.permissions.request(
            operation="run_command",
            resource=command[:200],
            level=level,
            reason=f"Execute: {command[:100]}",
            details={"full_command": command, "timeout": timeout},
        ):
            return {"success": False, "stdout": "", "stderr": "Permission denied",
                    "exit_code": -1, "command": command}

        try:
            result = subprocess.run(
                command,
                shell=True,
                capture_output=capture_output,
                text=True,
                timeout=timeout,
            )

            output = {
                "success": result.returncode == 0,
                "stdout": result.stdout[-5000:] if result.stdout else "",
                "stderr": result.stderr[-2000:] if result.stderr else "",
                "exit_code": result.returncode,
                "command": command,
            }

            self.event_bus.emit_simple(
                event_type="access.command_run",
                message=f"Command executed (exit: {result.returncode}): {command[:80]}",
                source="system_access",
                severity=EventSeverity.SUCCESS if result.returncode == 0 else EventSeverity.WARNING,
                category=EventCategory.ACCESS,
                details={"command": command, "exit_code": result.returncode},
            )

            return output

        except subprocess.TimeoutExpired:
            logger.warning(f"Command timed out after {timeout}s: {command[:80]}")
            return {"success": False, "stdout": "", "stderr": "Timed out",
                    "exit_code": -1, "command": command}
        except Exception as e:
            logger.error(f"Command failed: {e}")
            return {"success": False, "stdout": "", "stderr": str(e),
                    "exit_code": -1, "command": command}

    # ── ENVIRONMENT ─────────────────────────────────────────────

    def get_env(self, key: str) -> Optional[str]:
        """Read an environment variable with permission."""
        if not self.permissions.request(
            operation="read_env",
            resource=key,
            level=PermissionLevel.INFO if not key.upper().startswith(("SECRET", "TOKEN", "KEY")) else PermissionLevel.READ,
            reason=f"Read env var: {key}",
        ):
            return None

        value = os.environ.get(key)
        if value:
            self.event_bus.emit_simple(
                event_type="access.env_read",
                message=f"Read env var: {key}",
                source="system_access",
                severity=EventSeverity.INFO,
                category=EventCategory.ACCESS,
            )
        return value

    def list_env(self) -> list[dict]:
        """List environment variables (hides sensitive keys)."""
        if not self.permissions.request(
            operation="list_env",
            resource="environment",
            level=PermissionLevel.READ,
            reason="List environment variables",
        ):
            return []

        sensitive_patterns = re.compile(
            r"(secret|token|key|password|passwd|credential|auth|api_key)", re.IGNORECASE
        )

        env_vars = []
        for key, value in sorted(os.environ.items()):
            is_sensitive = bool(sensitive_patterns.search(key))
            env_vars.append({
                "key": key,
                "value": "***" if is_sensitive else value[:100],
                "sensitive": is_sensitive,
            })

        self.event_bus.emit_simple(
            event_type="access.env_listed",
            message=f"Listed {len(env_vars)} environment variables",
            source="system_access",
            severity=EventSeverity.INFO,
            category=EventCategory.ACCESS,
        )
        return env_vars

    # ── SYSTEM MONITORING ───────────────────────────────────────

    def get_system_info(self) -> dict:
        """Get system information with permission."""
        if not self.permissions.request(
            operation="system_info",
            resource="system",
            level=PermissionLevel.INFO,
            reason="Get system information",
        ):
            return {"error": "Permission denied"}

        info = {
            "platform": platform.platform(),
            "python": platform.python_version(),
            "hostname": platform.node(),
            "processor": platform.processor(),
            "architecture": platform.machine(),
        }

        # Disk usage
        try:
            usage = shutil.disk_usage(os.getcwd())
            info["disk"] = {
                "total_gb": round(usage.total / (1024 ** 3), 1),
                "used_gb": round(usage.used / (1024 ** 3), 1),
                "free_gb": round(usage.free / (1024 ** 3), 1),
                "usage_pct": round(usage.used / usage.total * 100, 1),
            }
        except Exception:
            pass

        # Uptime
        try:
            if sys.platform == "win32":
                info["uptime"] = "N/A (Windows)"
            else:
                with open("/proc/uptime") as f:
                    uptime_sec = float(f.read().split()[0])
                    days = int(uptime_sec // 86400)
                    hours = int((uptime_sec % 86400) // 3600)
                    info["uptime"] = f"{days}d {hours}h"
        except Exception:
            pass

        # Memory (if available)
        try:
            import psutil
            vm = psutil.virtual_memory()
            info["memory"] = {
                "total_gb": round(vm.total / (1024 ** 3), 1),
                "available_gb": round(vm.available / (1024 ** 3), 1),
                "usage_pct": vm.percent,
            }
        except ImportError:
            # psutil not installed — skip memory info
            pass

        return info

    def get_cwd(self) -> str:
        """Get current working directory."""
        return os.getcwd()

    def resolve_path(self, path: str) -> str:
        """Resolve a relative path to absolute."""
        return str(Path(path).resolve())

    # ── PERMISSION MANAGEMENT ───────────────────────────────────

    def list_permissions(self) -> list[dict]:
        """List all active permission grants."""
        return self.permissions.list_grants()

    def revoke_permissions(self, operation: Optional[str] = None) -> int:
        """Revoke permissions."""
        if operation:
            return self.permissions.revoke(operation=operation)
        return self.permissions.revoke_all()
