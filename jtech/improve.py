"""
JTECH Improvement Engine — Real code improvement pipeline.

Unlike `jtech build` which generates product preview pages,
the improvement engine actually:
- Copies projects between locations
- Analyzes codebases for issues
- Fixes bugs, adds type hints, improves error handling
- Reports what was changed
"""

from __future__ import annotations

import logging
import re
import shutil
import time
from pathlib import Path
from typing import Any, Optional

from jtech.llm import get_llm, ThinkingEffort

logger = logging.getLogger(__name__)


class Improver:
    """
    JTECH Improvement Engine — copies, analyzes, and improves real codebases.

    Pipeline:
    1. COPY — Copy source project to destination
    2. ANALYZE — Scan for issues (bare excepts, missing docstrings, long lines)
    3. IMPROVE — Fix common issues (bare excepts, add docstring stubs)
    4. AI IMPROVE — LLM-powered improvements on medium files
    5. REPORT — Summary of all changes made
    """

    def __init__(self):
        self.llm = get_llm()

    def improve(self, source: str, destination: str) -> dict:
        """Copy a project from source to destination and improve it."""
        start = time.time()
        source_path = Path(source)
        dest_path = Path(destination)

        if not source_path.exists():
            return {"success": False, "error": f"Source not found: {source}"}

        logger.info(f"Improving project: {source} -> {destination}")

        # Phase 1: Copy
        logger.info("  Phase 1: Copying project...")
        files_copied = self._copy_project(source_path, dest_path)
        logger.info(f"  Copied {files_copied} items")

        # Phase 2: Analyze
        logger.info("  Phase 2: Analyzing code...")
        issues = self._analyze_project(dest_path)

        # Phase 3: Fix
        logger.info(f"  Phase 3: Fixing {len(issues)} issues...")
        fixes = self._fix_issues(dest_path, issues)

        # Phase 4: AI improve medium files (2K-30K chars)
        ai_fixes = 0
        if self.llm.available:
            py_files = sorted(dest_path.rglob("*.py"))
            candidates = [
                f for f in py_files
                if "__pycache__" not in str(f) and ".egg-info" not in str(f)
            ]
            medium = [f for f in candidates if 2000 < f.stat().st_size < 30000]
            medium.sort(key=lambda f: f.stat().st_size, reverse=True)
            for cf in medium[:3]:
                rel = str(cf.relative_to(dest_path))
                logger.info(f"  AI improving: {rel}")
                result = self.ai_improve_file(rel, dest_path)
                if result:
                    ai_fixes += 1

        # Phase 5: Report
        elapsed = time.time() - start
        report = self._generate_report(dest_path, files_copied, issues, fixes, ai_fixes, elapsed)

        total_fixes = sum(f.get("count", 1) for f in fixes) + ai_fixes
        logger.info(f"Complete in {elapsed:.0f}s ({total_fixes} fixes applied)")
        return {
            "success": True,
            "source": str(source_path),
            "destination": str(dest_path),
            "files_copied": files_copied,
            "issues_found": len(issues),
            "issues_fixed": total_fixes,
            "fixes": fixes,
            "ai_improved_files": ai_fixes,
            "report": report,
            "elapsed_seconds": round(elapsed, 1),
        }

    # ── COPY ──────────────────────────────────────────────────

    def _copy_project(self, source: Path, dest: Path) -> int:
        """Copy project files, skipping common non-essential dirs."""
        if dest.exists():
            shutil.rmtree(dest)
        dest.mkdir(parents=True, exist_ok=True)

        skip = {".git", "__pycache__", ".pytest_cache", ".venv", "venv",
                "node_modules", ".egg-info", ".ollama"}
        count = 0

        for item in source.iterdir():
            if item.name in skip:
                continue
            try:
                if item.is_dir():
                    shutil.copytree(
                        item, dest / item.name,
                        ignore=shutil.ignore_patterns("__pycache__", "*.pyc", ".git"),
                        dirs_exist_ok=True,
                    )
                else:
                    shutil.copy2(item, dest / item.name)
                count += 1
            except Exception as e:
                logger.debug(f"Skip {item.name}: {e}")
        return count

    # ── ANALYZE ────────────────────────────────────────────────

    def _analyze_project(self, project_path: Path) -> list[dict]:
        """Scan Python files for common issues."""
        issues = []

        for py_file in project_path.rglob("*.py"):
            if "__pycache__" in str(py_file) or ".egg-info" in str(py_file):
                continue
            try:
                content = py_file.read_text(encoding="utf-8", errors="replace")
                rel = str(py_file.relative_to(project_path))
                lines = content.split("\n")

                # bare except
                for i, line in enumerate(lines, 1):
                    s = line.strip()
                    if s == "except:" or s == "except :":
                        issues.append({
                            "file": rel, "line": i, "type": "bare_except",
                            "severity": "medium",
                            "description": "Bare except clause",
                            "code": s,
                        })

                # missing docstrings
                for i, line in enumerate(lines, 1):
                    s = line.strip()
                    if s.startswith("def ") or s.startswith("class "):
                        has_doc = False
                        for j in range(i + 1, min(i + 6, len(lines))):
                            c = lines[j].strip()
                            if c.startswith('"""') or c.startswith("'''"):
                                has_doc = True
                                break
                            if c and not c.startswith("@") and not c.startswith("#"):
                                break
                        if not has_doc:
                            issues.append({
                                "file": rel, "line": i, "type": "missing_docstring",
                                "severity": "low",
                                "description": f"Missing docstring for {s}",
                                "code": s[:60],
                            })

                # long lines
                for i, line in enumerate(lines, 1):
                    if len(line.rstrip("\n")) > 120:
                        issues.append({
                            "file": rel, "line": i, "type": "long_line",
                            "severity": "low",
                            "description": f"Line too long ({len(line.rstrip())} chars)",
                            "code": line.rstrip()[:80],
                        })
                        break  # one per file

            except Exception as e:
                logger.debug(f"Could not analyze {py_file}: {e}")

        return issues

    # ── FIX ────────────────────────────────────────────────────

    def _fix_issues(self, project_path: Path, issues: list[dict]) -> list[dict]:
        """Fix identified issues — bare excepts AND missing docstrings."""
        by_file: dict[str, list[dict]] = {}
        for issue in issues:
            by_file.setdefault(issue["file"], []).append(issue)

        fixes = []
        for file_path, file_issues in by_file.items():
            full_path = project_path / file_path
            if not full_path.exists():
                continue
            try:
                content = full_path.read_text(encoding="utf-8")
                lines = content.split("\n")
                modified = False
                bare_fixes = 0
                docstring_fixes = 0

                for issue in file_issues:
                    if issue["type"] == "bare_except":
                        idx = issue["line"] - 1
                        if idx < len(lines):
                            old = lines[idx]
                            indent = old[: len(old) - len(old.lstrip())]
                            lines[idx] = f"{indent}except Exception:  # Fixed: was bare except\n"
                            modified = True
                            bare_fixes += 1

                    elif issue["type"] == "missing_docstring":
                        idx = issue["line"] - 1
                        if idx < len(lines):
                            # Find the colon that ends the def/class signature
                            for k in range(idx, min(idx + 6, len(lines))):
                                stripped = lines[k].strip()
                                if stripped.rstrip().endswith(":"):
                                    # Detect indentation from the next non-empty line
                                    indent = "    "
                                    for m in range(k + 1, min(k + 4, len(lines))):
                                        if lines[m].strip() and not lines[m].strip().startswith("#"):
                                            actual = lines[m]
                                            indent = actual[: len(actual) - len(actual.lstrip())]
                                            break
                                    lines.insert(k + 1, f'{indent}"""TODO: Add docstring."""')
                                    modified = True
                                    docstring_fixes += 1
                                    break

                if modified:
                    full_path.write_text("\n".join(lines))
                    if bare_fixes > 0:
                        fixes.append({
                            "file": file_path,
                            "type": "fixed_bare_excepts",
                            "count": bare_fixes,
                        })
                    if docstring_fixes > 0:
                        fixes.append({
                            "file": file_path,
                            "type": "added_docstring_stubs",
                            "count": docstring_fixes,
                        })
            except Exception as e:
                logger.debug(f"Could not fix {file_path}: {e}")
        return fixes

    def ai_improve_file(self, file_path: str, project_path: Path) -> Optional[str]:
        """Use AI to improve a single file (add docstrings, error handling, type hints)."""
        if not self.llm.available:
            return None
        full_path = project_path / file_path
        if not full_path.exists():
            return None
        try:
            content = full_path.read_text(encoding="utf-8", errors="replace")
            if len(content) > 50000:
                return None

            if len(content) > 8000:
                prompt = (
                    f"Add docstrings to any public functions/classes missing them. "
                    f"Do not change any functionality.\n\n"
                    f"File: {file_path}\n\n"
                    f"```python\n{content[:40000]}\n```\n\n"
                    f"Output the COMPLETE file with docstrings added."
                )
            else:
                prompt = (
                    f"Improve this Python code. Add error handling, improve documentation, "
                    f"fix bugs, and add type hints where appropriate.\n\n"
                    f"File: {file_path}\n\n"
                    f"```python\n{content}\n```\n\n"
                    f"Output the COMPLETE improved file. Keep the same functionality."
                )

            improved = self.llm.chat(
                [{"role": "user", "content": prompt}],
                system_prompt="Senior Python engineer. Improve code quality without breaking functionality.",
                thinking_effort=ThinkingEffort.MINIMAL,
                max_tokens=8192,
            )
            if improved and len(improved) > len(content) * 0.3:
                # Strip markdown code fences if present
                fence_match = re.search(
                    r'```(?:python|py)?\n(.*?)```',
                    improved, re.DOTALL
                )
                if fence_match:
                    improved = fence_match.group(1).strip()
                full_path.write_text(improved, encoding="utf-8")
                return improved
        except Exception as e:
            logger.debug(f"AI improve failed for {file_path}: {e}")
        return None

    # ── REPORT ─────────────────────────────────────────────────

    def _generate_report(self, project_path: Path, files_copied: int,
                         issues: list[dict], fixes: list[dict],
                         ai_fixes: int, elapsed: float) -> str:
        """Generate a human-readable report."""
        total_fixed = sum(f.get("count", 1) for f in fixes) + ai_fixes
        lines = [
            "=" * 60,
            "JTECH Improvement Report",
            "=" * 60,
            f"Project:        {project_path}",
            f"Items copied:   {files_copied}",
            f"Issues found:   {len(issues)}",
            f"Issues fixed:   {total_fixed}",
            f"Time:           {elapsed:.0f}s",
            "",
        ]
        if fixes:
            lines.append("Fixes Applied:")
            for f in fixes:
                lines.append(f"  + {f['file']}: {f['type']} ({f['count']} fix{'es' if f['count'] > 1 else ''})")
            lines.append("")
        if ai_fixes:
            lines.append(f"AI Improvements: {ai_fixes} file(s)")
            lines.append("")

        sev = {}
        for issue in issues:
            s = issue["severity"]
            sev[s] = sev.get(s, 0) + 1
        if sev:
            lines.append("Issues by Severity:")
            for s in ("critical", "high", "medium", "low"):
                if s in sev:
                    lines.append(f"  {s.title()}: {sev[s]}")
            lines.append("")
        lines.append("=" * 60)
        return "\n".join(lines)
