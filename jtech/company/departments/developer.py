"""
Developer Department — Builds products for JTECH using the AppBuilder.

Inspired by Lovable.dev, Bolt.new, and v0:
- Uses the AppBuilder for full-stack React/TypeScript/Tailwind apps
- DeepSeek thinking mode for requirements analysis
- Generates live previews and production-ready code
- Supports multiple stack templates
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any, Optional

from jtech.builder import AppBuilder
from jtech.llm import get_llm, ThinkingEffort

logger = logging.getLogger(__name__)


class Developer:
    """Software Engineer — builds full-stack applications using JTECH's AppBuilder."""

    def __init__(self):
        self.llm = get_llm()
        self.builder = AppBuilder()
        self.name = "Developer"
        self.projects_dir = Path(os.environ.get("JTECH_PROJECTS_DIR", "./built_products"))
        self.projects_dir.mkdir(parents=True, exist_ok=True)

    def scaffold_project(self, product_idea: dict) -> str:
        """Create the project directory structure."""
        name = product_idea.get("product_name", "product").lower().replace(" ", "_").replace("-", "_")
        project_path = self.projects_dir / name
        project_path.mkdir(parents=True, exist_ok=True)
        return str(project_path)

    def design_data_model(self, product_idea: dict) -> list[dict]:
        """Design the data model using DeepSeek thinking."""
        result, reasoning = self.llm.chat_json_rich(
            [{"role": "user", "content": (
                f"Design the data model for:\n"
                f"Product: {product_idea.get('product_name')}\n"
                f"Description: {product_idea.get('description')}\n"
                f"Tech: {product_idea.get('tech_stack', ['React', 'Supabase'])}\n\n"
                f"Output {{\"models\": [{{\"name\": \"Model\", \"fields\": [{{\"name\": \"field\", "
                f"\"type\": \"str\", \"required\": true}}]}}]}}"
            )}],
            system_prompt="Design minimal, practical data models.",
            thinking_effort=ThinkingEffort.LOW,
        )
        return result.get("models", []) if result else []

    def plan_implementation(self, product_idea: dict) -> list[dict]:
        """Generate implementation steps using thinking mode."""
        result, reasoning = self.llm.chat_json_rich(
            [{"role": "user", "content": (
                f"Plan the implementation for:\n"
                f"Product: {product_idea.get('product_name')}\n"
                f"Stack: {product_idea.get('tech_stack', ['React'])}\n\n"
                f"Output {{\"steps\": [{{\"step\": 1, \"action\": \"...\", \"file\": \"...\", "
                f"\"details\": \"...\"}}]}}"
            )}],
            system_prompt="Plan implementations that ship fast.",
            thinking_effort=ThinkingEffort.HIGH,
        )
        if result and "steps" in result:
            return result["steps"]
        return [
            {"step": 1, "action": "Create project structure", "file": "project/", "details": "Set up basic files"},
            {"step": 2, "action": "Build core logic", "file": "main.py", "details": "Implement the main feature"},
        ]

    def build_full_app(self, product_idea: dict, stack: str = "react-ts") -> dict:
        """
        Build a complete web application using the AppBuilder.

        This is the main entry point for product generation.
        Returns the complete build result with files, preview, and metadata.
        """
        return self.builder.build_app(product_idea, stack=stack)

    def generate_landing_preview(self, product_data: dict) -> str:
        """Generate a live preview landing page."""
        return self.builder.generate_preview(product_data)

    def generate_code(self, specification: dict) -> dict[str, str]:
        """Generate code files using the AppBuilder."""
        result = self.builder.build_app(specification)
        return result.get("files", {})

    def write_files(self, files: dict[str, str], project_path: str) -> list[str]:
        """Write generated files to disk."""
        written = []
        for file_path, content in files.items():
            full_path = Path(project_path) / file_path
            full_path.parent.mkdir(parents=True, exist_ok=True)
            try:
                with open(full_path, "w", encoding="utf-8") as f:
                    f.write(content)
                written.append(str(full_path))
            except Exception as e:
                logger.error(f"Failed to write {full_path}: {e}")
        return written

    def suggest_edit(self, current_html: str, instruction: str) -> str:
        """Visual editing — suggest UI changes based on natural language instructions."""
        return self.builder.suggest_visual_edits(current_html, instruction)
