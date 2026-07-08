"""
JTECH Project Manager — Workspace and project lifecycle management.

Each product/application JTECH builds is a 'Project' with:
- Full lifecycle: Draft → InProgress → Review → Shipped → Maintenance → Archived
- File tracking and workspace management
- Version tracking
- Status reporting
- Integration with state manager, event bus, and infrastructure
"""

from __future__ import annotations

import json
import logging
import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from jtech.infrastructure.state_manager import StateManager
from jtech.infrastructure.event_bus import EventBus, Event, EventSeverity, EventCategory
from jtech.infrastructure.error_handler import ErrorHandler

logger = logging.getLogger(__name__)


class ProjectStatus:
    DRAFT = "draft"
    IN_PROGRESS = "in_progress"
    REVIEW = "review"
    SHIPPED = "shipped"
    MAINTENANCE = "maintenance"
    ARCHIVED = "archived"

    TRANSITIONS = {
        DRAFT: [IN_PROGRESS, ARCHIVED],
        IN_PROGRESS: [REVIEW, DRAFT, ARCHIVED],
        REVIEW: [SHIPPED, IN_PROGRESS, ARCHIVED],
        SHIPPED: [MAINTENANCE, ARCHIVED],
        MAINTENANCE: [SHIPPED, ARCHIVED],
        ARCHIVED: [DRAFT],
    }

    @classmethod
    def can_transition(cls, current: str, target: str) -> bool:
        """Check if a status transition is valid."""
        return target in cls.TRANSITIONS.get(current, [])

    @classmethod
    def valid_transitions(cls, current: str) -> list[str]:
        """Get valid transitions from a status."""
        return cls.TRANSITIONS.get(current, [])


class JTechProject:
    """
    A single JTECH project — represents a product or application.

    Wraps the state manager project record with business logic.
    """

    def __init__(self, state: StateManager, project_id: int):
        self._state = state
        self.id = project_id
        self._data = state.get_project(project_id)

        if not self._data:
            raise ValueError(f"Project {project_id} not found")

    @property
    def name(self) -> str:
        return self._data.get("name", "Unnamed")

    @property
    def status(self) -> str:
        return self._data.get("status", ProjectStatus.DRAFT)

    @property
    def description(self) -> str:
        return self._data.get("description", "")

    @property
    def project_type(self) -> str:
        return self._data.get("project_type", "product")

    @property
    def created_at(self) -> str:
        return self._data.get("created_at", "")

    @property
    def metadata(self) -> dict:
        try:
            return json.loads(self._data.get("metadata", "{}"))
        except (json.JSONDecodeError, TypeError):
            return {}

    @property
    def workspace_path(self) -> Optional[Path]:
        """Get the workspace directory for this project."""
        meta = self.metadata
        path_str = meta.get("workspace_path", "")
        if path_str:
            return Path(path_str)
        return None

    def transition_to(self, new_status: str) -> bool:
        """Change project status with validation."""
        if not ProjectStatus.can_transition(self.status, new_status):
            logger.warning(f"Cannot transition from {self.status} to {new_status}")
            return False

        success = self._state.update_project(self.id, status=new_status)
        if success:
            self._data["status"] = new_status
        return success

    def update(self, **kwargs: Any) -> bool:
        """Update project fields."""
        success = self._state.update_project(self.id, **kwargs)
        if success:
            self._data.update(kwargs)
        return success

    def to_dict(self) -> dict:
        """Get full project data as dict."""
        return dict(self._data)

    def __repr__(self) -> str:
        return f"<JTechProject #{self.id}: {self.name} [{self.status}]>"


class ProjectManager:
    """
    Central project manager for JTECH.

    Manages the full lifecycle of all projects/products.
    Integrates with the event bus, state manager, and workspace filesystem.

    Usage:
        pm = ProjectManager()
        
        # Create a new project
        project = pm.create("My SaaS App", "A dashboard for...")
        
        # List all active projects
        for p in pm.list_active():
            print(p.name, p.status)
        
        # Get a specific project
        p = pm.get(1)
        p.transition_to("in_progress")
    """

    def __init__(self, state: Optional[StateManager] = None,
                 event_bus: Optional[EventBus] = None):
        self.state = state or StateManager()
        self.event_bus = event_bus or EventBus()
        self.error_handler = ErrorHandler()
        self.workspace_root = Path(os.environ.get("JTECH_WORKSPACE_ROOT", "./workspace"))
        self.workspace_root.mkdir(parents=True, exist_ok=True)

    # ── CREATE ──────────────────────────────────────────────────

    def create(self, name: str, description: str = "",
               project_type: str = "product") -> JTechProject:
        """Create a new project and its workspace."""
        # Create state record
        project_id = self.state.create_project(name, description, project_type)

        # Create workspace directory
        slug = name.lower().replace(" ", "-").replace("_", "-")
        workspace = self.workspace_root / slug
        workspace.mkdir(parents=True, exist_ok=True)

        # Store workspace path in metadata
        self.state.update_project(project_id, metadata=json.dumps({
            "workspace_path": str(workspace),
            "created_by": "jtech",
            "slug": slug,
        }))

        # Emit event
        self.event_bus.emit_simple(
            event_type="project.created",
            message=f"Project created: {name} (ID: {project_id})",
            source="project_manager",
            severity=EventSeverity.SUCCESS,
            category=EventCategory.PROJECT,
            details={"project_id": project_id, "name": name, "workspace": str(workspace)},
        )

        logger.info(f"Created project #{project_id}: {name} at {workspace}")
        return JTechProject(self.state, project_id)

    # ── GET / LIST ──────────────────────────────────────────────

    def get(self, project_id: int) -> Optional[JTechProject]:
        """Get a project by ID."""
        try:
            return JTechProject(self.state, project_id)
        except ValueError:
            return None

    def list_all(self) -> list[JTechProject]:
        """List all projects."""
        return [JTechProject(self.state, p["id"]) for p in self.state.list_projects()]

    def list_by_status(self, status: str) -> list[JTechProject]:
        """List projects by status."""
        return [
            JTechProject(self.state, p["id"])
            for p in self.state.list_projects(status=status)
        ]

    def list_active(self) -> list[JTechProject]:
        """List active (non-archived) projects."""
        all_projects = self.list_all()
        return [p for p in all_projects if p.status not in (ProjectStatus.ARCHIVED,)]

    def count_by_status(self) -> dict[str, int]:
        """Count projects by status."""
        counts = {}
        for p in self.list_all():
            counts[p.status] = counts.get(p.status, 0) + 1
        return counts

    # ── WORKSPACE ───────────────────────────────────────────────

    def get_workspace(self, project_id: int) -> Optional[Path]:
        """Get the workspace path for a project."""
        project = self.get(project_id)
        if project and project.workspace_path:
            path = project.workspace_path
            path.mkdir(parents=True, exist_ok=True)
            return path
        return None

    def list_workspace_files(self, project_id: int) -> list[dict]:
        """List files in a project workspace."""
        workspace = self.get_workspace(project_id)
        if not workspace or not workspace.exists():
            return []

        files = []
        for f in workspace.rglob("*"):
            if f.is_file():
                rel_path = f.relative_to(workspace)
                files.append({
                    "path": str(rel_path),
                    "size": f.stat().st_size,
                    "modified": datetime.fromtimestamp(f.stat().st_mtime).isoformat(),
                })
        return sorted(files, key=lambda x: x["path"])

    def get_workspace_tree(self, project_id: int) -> str:
        """Get a tree representation of the workspace."""
        workspace = self.get_workspace(project_id)
        if not workspace or not workspace.exists():
            return "(empty)"

        lines = []
        for f in sorted(workspace.rglob("*")):
            if f.is_file():
                rel = f.relative_to(workspace)
                depth = len(rel.parents)
                prefix = "  " * depth + "├── "
                lines.append(f"{prefix}{rel.name}")

        return "\n".join(lines) if lines else "(empty)"

    # ── DELETE / ARCHIVE ────────────────────────────────────────

    def archive(self, project_id: int) -> bool:
        """Archive a project (soft delete)."""
        project = self.get(project_id)
        if not project:
            return False
        return project.transition_to(ProjectStatus.ARCHIVED)

    def delete(self, project_id: int, remove_files: bool = False) -> bool:
        """
        Permanently delete a project.

        Args:
            project_id: The project to delete
            remove_files: Also delete workspace files (default: False)
        """
        project = self.get(project_id)
        if not project:
            return False

        # Optionally remove workspace files
        if remove_files and project.workspace_path:
            try:
                shutil.rmtree(project.workspace_path)
                logger.info(f"Removed workspace: {project.workspace_path}")
            except Exception as e:
                logger.error(f"Failed to remove workspace: {e}")

        # Delete from state
        self.state.delete_project(project_id)

        self.event_bus.emit_simple(
            event_type="project.deleted",
            message=f"Project deleted: {project.name} (ID: {project_id})",
            source="project_manager",
            severity=EventSeverity.INFO,
            category=EventCategory.PROJECT,
        )

        return True

    # ── SUMMARY ─────────────────────────────────────────────────

    def summary(self) -> dict:
        """Get a summary of all projects."""
        all_projects = self.list_all()
        return {
            "total": len(all_projects),
            "by_status": self.count_by_status(),
            "active": len(self.list_active()),
            "recent": [
                {"id": p.id, "name": p.name, "status": p.status}
                for p in all_projects[:5]
            ],
        }
