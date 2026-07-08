"""
JTECH State Manager — SQLite-backed persistent state with transactions.

Replaces the JSON file-based CompanyMemory with proper ACID-compliant storage.
Supports:
- Multiple state collections (kv store, projects, events)
- Atomic transactions
- Schema versioning and migration
- Concurrent access safety
- Query and filter capabilities

Uses Python stdlib sqlite3 — no external dependencies.
"""

from __future__ import annotations

import json
import logging
import os
import sqlite3
import threading
import time
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Iterator, Optional

logger = logging.getLogger(__name__)


class StateError(Exception):
    """Base exception for state management errors."""


class MigrationError(StateError):
    """Exception for migration failures."""


# ── SCHEMA ──────────────────────────────────────────────────────

SCHEMA_VERSION = 1

CREATE_SCHEMA = """
-- Schema version tracking
CREATE TABLE IF NOT EXISTS schema_version (
    version INTEGER PRIMARY KEY,
    applied_at TEXT NOT NULL
);

-- Key-value store for simple state
CREATE TABLE IF NOT EXISTS kv_store (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

-- Projects/Products storage
CREATE TABLE IF NOT EXISTS projects (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    project_type TEXT NOT NULL DEFAULT 'product',
    status TEXT NOT NULL DEFAULT 'draft',
    description TEXT DEFAULT '',
    metadata TEXT DEFAULT '{}',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

-- Project files tracking
CREATE TABLE IF NOT EXISTS project_files (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER NOT NULL,
    file_path TEXT NOT NULL,
    file_type TEXT DEFAULT '',
    size_bytes INTEGER DEFAULT 0,
    checksum TEXT DEFAULT '',
    created_at TEXT NOT NULL,
    FOREIGN KEY (project_id) REFERENCES projects(id)
);

-- Actions/Activity log
CREATE TABLE IF NOT EXISTS actions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    source TEXT NOT NULL DEFAULT 'system',
    action TEXT NOT NULL,
    category TEXT DEFAULT '',
    summary TEXT DEFAULT '',
    metadata TEXT DEFAULT '{}',
    project_id INTEGER,
    FOREIGN KEY (project_id) REFERENCES projects(id)
);

-- Sales tracking
CREATE TABLE IF NOT EXISTS sales (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    project_id INTEGER NOT NULL,
    customer TEXT NOT NULL DEFAULT 'anonymous',
    price REAL NOT NULL DEFAULT 0.0,
    currency TEXT NOT NULL DEFAULT 'USD',
    status TEXT NOT NULL DEFAULT 'completed',
    metadata TEXT DEFAULT '{}',
    FOREIGN KEY (project_id) REFERENCES projects(id)
);

-- Metrics
CREATE TABLE IF NOT EXISTS metrics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    name TEXT NOT NULL,
    value REAL NOT NULL,
    tags TEXT DEFAULT '{}',
    project_id INTEGER
);

-- Events (audit trail)
CREATE TABLE IF NOT EXISTS events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    event_type TEXT NOT NULL,
    source TEXT NOT NULL,
    severity TEXT NOT NULL DEFAULT 'info',
    message TEXT NOT NULL,
    details TEXT DEFAULT '{}'
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_actions_timestamp ON actions(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_actions_source ON actions(source);
CREATE INDEX IF NOT EXISTS idx_actions_project ON actions(project_id);
CREATE INDEX IF NOT EXISTS idx_projects_status ON projects(status);
CREATE INDEX IF NOT EXISTS idx_sales_project ON sales(project_id);
CREATE INDEX IF NOT EXISTS idx_metrics_name ON metrics(name);
CREATE INDEX IF NOT EXISTS idx_metrics_timestamp ON metrics(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_events_timestamp ON events(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_events_type ON events(event_type);
"""


class StateManager:
    """
    Bulletproof SQLite-backed state manager.

    Thread-safe, transaction-safe, with automatic schema management.
    Replaces the JSON-file-based CompanyMemory with proper database storage.

    Usage:
        sm = StateManager("jtech.db")
        sm.set("api_key_status", "connected")
        value = sm.get("api_key_status")
    """

    def __init__(self, db_path: Optional[str] = None):
        self.db_path = Path(db_path or os.environ.get("JTECH_DB_PATH", "./data/jtech.db"))
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        self._local = threading.local()
        self._lock = threading.Lock()

        # Initialize schema
        self._init_schema()

    @property
    def _conn(self) -> sqlite3.Connection:
        """Get thread-local connection."""
        if not hasattr(self._local, 'conn') or self._local.conn is None:
            self._local.conn = sqlite3.connect(str(self.db_path))
            self._local.conn.row_factory = sqlite3.Row
            self._local.conn.execute("PRAGMA journal_mode=WAL")
            self._local.conn.execute("PRAGMA foreign_keys=ON")
        return self._local.conn

    @contextmanager
    def _transaction(self) -> Iterator[sqlite3.Connection]:
        """Context manager for atomic transactions."""
        conn = self._conn
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise

    def _init_schema(self) -> None:
        """Initialize the database schema."""
        with self._lock:
            conn = self._conn
            try:
                conn.executescript(CREATE_SCHEMA)
                conn.commit()

                # Check and migrate schema version
                cursor = conn.execute("SELECT MAX(version) FROM schema_version")
                row = cursor.fetchone()
                current_version = row[0] if row and row[0] else 0

                if current_version < SCHEMA_VERSION:
                    self._migrate(current_version)
                    conn.execute(
                        "INSERT INTO schema_version (version, applied_at) VALUES (?, ?)",
                        (SCHEMA_VERSION, datetime.now().isoformat())
                    )
                    conn.commit()
                    logger.info(f"Schema migrated to v{SCHEMA_VERSION}")

            except Exception as e:
                logger.error(f"Schema initialization failed: {e}")
                raise StateError(f"Database init failed: {e}")

    def _migrate(self, from_version: int) -> None:
        """Run schema migrations."""
        if from_version < 1:
            # v1 is the initial schema — nothing to migrate yet
            pass

    # ── KV STORE ────────────────────────────────────────────────

    def set(self, key: str, value: Any) -> None:
        """Set a key-value pair (JSON-serialized)."""
        with self._lock:
            with self._transaction() as conn:
                conn.execute(
                    """INSERT INTO kv_store (key, value, updated_at)
                       VALUES (?, ?, ?)
                       ON CONFLICT(key) DO UPDATE SET value=excluded.value, updated_at=excluded.updated_at""",
                    (key, json.dumps(value), datetime.now().isoformat())
                )

    def get(self, key: str, default: Any = None) -> Any:
        """Get a value by key (JSON-deserialized)."""
        cursor = self._conn.execute("SELECT value FROM kv_store WHERE key = ?", (key,))
        row = cursor.fetchone()
        if row:
            try:
                return json.loads(row["value"])
            except (json.JSONDecodeError, TypeError):
                return row["value"]
        return default

    def delete(self, key: str) -> bool:
        """Delete a key-value pair. Returns True if deleted."""
        with self._lock:
            cursor = self._conn.execute("DELETE FROM kv_store WHERE key = ?", (key,))
            return cursor.rowcount > 0

    def list_keys(self, prefix: str = "") -> list[str]:
        """List all keys, optionally filtered by prefix."""
        if prefix:
            cursor = self._conn.execute(
                "SELECT key FROM kv_store WHERE key LIKE ? ORDER BY key",
                (f"{prefix}%",)
            )
        else:
            cursor = self._conn.execute("SELECT key FROM kv_store ORDER BY key")
        return [row["key"] for row in cursor.fetchall()]

    # ── PROJECTS ────────────────────────────────────────────────

    def create_project(self, name: str, description: str = "",
                       project_type: str = "product") -> int:
        """Create a new project. Returns the project ID."""
        now = datetime.now().isoformat()
        with self._lock:
            with self._transaction() as conn:
                cursor = conn.execute(
                    """INSERT INTO projects (name, project_type, status, description, created_at, updated_at)
                       VALUES (?, ?, 'draft', ?, ?, ?)""",
                    (name, project_type, description, now, now)
                )
                return cursor.lastrowid

    def update_project(self, project_id: int, **kwargs: Any) -> bool:
        """Update project fields."""
        allowed = {"name", "status", "description", "metadata"}
        updates = {k: v for k, v in kwargs.items() if k in allowed}
        if not updates:
            return False

        updates["updated_at"] = datetime.now().isoformat()
        set_clause = ", ".join(f"{k} = ?" for k in updates)
        values = list(updates.values()) + [project_id]

        with self._lock:
            cursor = self._conn.execute(
                f"UPDATE projects SET {set_clause} WHERE id = ?",
                values
            )
            return cursor.rowcount > 0

    def get_project(self, project_id: int) -> Optional[dict]:
        """Get a project by ID."""
        cursor = self._conn.execute("SELECT * FROM projects WHERE id = ?", (project_id,))
        row = cursor.fetchone()
        if row:
            return dict(row)
        return None

    def list_projects(self, status: Optional[str] = None,
                      project_type: Optional[str] = None) -> list[dict]:
        """List projects, optionally filtered."""
        query = "SELECT * FROM projects WHERE 1=1"
        params = []
        if status:
            query += " AND status = ?"
            params.append(status)
        if project_type:
            query += " AND project_type = ?"
            params.append(project_type)
        query += " ORDER BY created_at DESC"

        cursor = self._conn.execute(query, params)
        return [dict(row) for row in cursor.fetchall()]

    def delete_project(self, project_id: int) -> bool:
        """Delete a project and its related data."""
        with self._lock:
            with self._transaction() as conn:
                conn.execute("DELETE FROM project_files WHERE project_id = ?", (project_id,))
                conn.execute("DELETE FROM actions WHERE project_id = ?", (project_id,))
                conn.execute("DELETE FROM sales WHERE project_id = ?", (project_id,))
                cursor = conn.execute("DELETE FROM projects WHERE id = ?", (project_id,))
                return cursor.rowcount > 0

    # ── PROJECT FILES ───────────────────────────────────────────

    def register_file(self, project_id: int, file_path: str,
                      file_type: str = "", size_bytes: int = 0) -> int:
        """Register a file as part of a project."""
        now = datetime.now().isoformat()
        with self._lock:
            cursor = self._conn.execute(
                """INSERT INTO project_files (project_id, file_path, file_type, size_bytes, created_at)
                   VALUES (?, ?, ?, ?, ?)""",
                (project_id, file_path, file_type, size_bytes, now)
            )
            return cursor.lastrowid

    def list_project_files(self, project_id: int) -> list[dict]:
        """List files for a project."""
        cursor = self._conn.execute(
            "SELECT * FROM project_files WHERE project_id = ? ORDER BY file_path",
            (project_id,)
        )
        return [dict(row) for row in cursor.fetchall()]

    # ── ACTIONS ─────────────────────────────────────────────────

    def record_action(self, source: str, action: str, summary: str = "",
                      category: str = "", metadata: Optional[dict] = None,
                      project_id: Optional[int] = None) -> int:
        """Record an action/event."""
        now = datetime.now().isoformat()
        with self._lock:
            cursor = self._conn.execute(
                """INSERT INTO actions (timestamp, source, action, category, summary, metadata, project_id)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (now, source, action, category, summary,
                 json.dumps(metadata or {}), project_id)
            )
            return cursor.lastrowid

    def get_actions(self, limit: int = 50, source: Optional[str] = None,
                    project_id: Optional[int] = None) -> list[dict]:
        """Get recent actions."""
        query = "SELECT * FROM actions WHERE 1=1"
        params = []
        if source:
            query += " AND source = ?"
            params.append(source)
        if project_id:
            query += " AND project_id = ?"
            params.append(project_id)
        query += " ORDER BY timestamp DESC LIMIT ?"
        params.append(limit)

        cursor = self._conn.execute(query, params)
        return [dict(row) for row in cursor.fetchall()]

    # ── SALES ───────────────────────────────────────────────────

    def record_sale(self, project_id: int, price: float,
                    customer: str = "anonymous", metadata: Optional[dict] = None) -> int:
        """Record a sale."""
        now = datetime.now().isoformat()
        with self._lock:
            cursor = self._conn.execute(
                """INSERT INTO sales (timestamp, project_id, customer, price, metadata)
                   VALUES (?, ?, ?, ?, ?)""",
                (now, project_id, customer, price, json.dumps(metadata or {}))
            )
            return cursor.lastrowid

    def get_sales(self, project_id: Optional[int] = None,
                  limit: int = 100) -> list[dict]:
        """Get sales records."""
        query = "SELECT * FROM sales"
        params = []
        if project_id is not None:
            query += " WHERE project_id = ?"
            params.append(project_id)
        query += " ORDER BY timestamp DESC LIMIT ?"
        params.append(limit)

        cursor = self._conn.execute(query, params)
        return [dict(row) for row in cursor.fetchall()]

    def get_revenue_summary(self) -> dict:
        """Get revenue aggregation."""
        cursor = self._conn.execute(
            """SELECT COUNT(*) as total_sales,
                      COALESCE(SUM(price), 0) as total_revenue,
                      COUNT(DISTINCT project_id) as unique_products
               FROM sales WHERE status = 'completed'"""
        )
        row = cursor.fetchone()
        return dict(row) if row else {"total_sales": 0, "total_revenue": 0, "unique_products": 0}

    # ── METRICS ─────────────────────────────────────────────────

    def record_metric(self, name: str, value: float,
                      tags: Optional[dict] = None,
                      project_id: Optional[int] = None) -> int:
        """Record a metric datapoint."""
        now = datetime.now().isoformat()
        with self._lock:
            cursor = self._conn.execute(
                """INSERT INTO metrics (timestamp, name, value, tags, project_id)
                   VALUES (?, ?, ?, ?, ?)""",
                (now, name, value, json.dumps(tags or {}), project_id)
            )
            return cursor.lastrowid

    def get_metrics(self, name: str, limit: int = 100) -> list[dict]:
        """Get metrics by name."""
        cursor = self._conn.execute(
            "SELECT * FROM metrics WHERE name = ? ORDER BY timestamp DESC LIMIT ?",
            (name, limit)
        )
        return [dict(row) for row in cursor.fetchall()]

    # ── EVENTS (AUDIT TRAIL) ────────────────────────────────────

    def record_event(self, event_type: str, message: str,
                     source: str = "system", severity: str = "info",
                     details: Optional[dict] = None) -> int:
        """Record an audit event."""
        now = datetime.now().isoformat()
        with self._lock:
            cursor = self._conn.execute(
                """INSERT INTO events (timestamp, event_type, source, severity, message, details)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (now, event_type, source, severity, message, json.dumps(details or {}))
            )
            return cursor.lastrowid

    def get_events(self, event_type: Optional[str] = None,
                   severity: Optional[str] = None,
                   limit: int = 100) -> list[dict]:
        """Get audit events."""
        query = "SELECT * FROM events WHERE 1=1"
        params = []
        if event_type:
            query += " AND event_type = ?"
            params.append(event_type)
        if severity:
            query += " AND severity = ?"
            params.append(severity)
        query += " ORDER BY timestamp DESC LIMIT ?"
        params.append(limit)

        cursor = self._conn.execute(query, params)
        return [dict(row) for row in cursor.fetchall()]

    # ── STATUS ──────────────────────────────────────────────────

    def get_status(self) -> dict:
        """Get comprehensive system status."""
        status = {}

        # Project counts
        cursor = self._conn.execute(
            "SELECT status, COUNT(*) as count FROM projects GROUP BY status"
        )
        status["projects_by_status"] = {row["status"]: row["count"] for row in cursor.fetchall()}

        # Total counts
        cursor = self._conn.execute("SELECT COUNT(*) as c FROM projects")
        status["total_projects"] = cursor.fetchone()["c"]

        cursor = self._conn.execute("SELECT COUNT(*) as c FROM actions")
        status["total_actions"] = cursor.fetchone()["c"]

        cursor = self._conn.execute("SELECT COUNT(*) as c FROM sales")
        status["total_sales"] = cursor.fetchone()["c"]

        cursor = self._conn.execute("SELECT COUNT(*) as c FROM events")
        status["total_events"] = cursor.fetchone()["c"]

        # Revenue
        rev = self.get_revenue_summary()
        status["total_revenue"] = rev["total_revenue"]
        status["total_sales_count"] = rev["total_sales"]

        # Database info
        db_size = self.db_path.stat().st_size if self.db_path.exists() else 0
        status["database_size_mb"] = round(db_size / (1024 * 1024), 2)

        # Schema version
        cursor = self._conn.execute("SELECT MAX(version) as v FROM schema_version")
        status["schema_version"] = cursor.fetchone()["v"]

        return status

    def close(self) -> None:
        """Close the database connection."""
        if hasattr(self._local, 'conn') and self._local.conn:
            self._local.conn.close()
            self._local.conn = None

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()
