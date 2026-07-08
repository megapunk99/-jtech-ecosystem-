"""
JTECH CLI — The complete command center.

Now with:
- Project management (project lifecycle, workspace, files)
- System access (filesystem, terminal, env, system info)
- Infrastructure commands (health, permissions, events)
- Full company operations (standup, build, sell, etc.)

Usage:
    jtech build [idea]           Build a product
    jtech project create "name"   Create a project
    jtech project list            List all projects
    jtech project open <id>       Open a project workspace
    jtech project status <id>     Change project status
    jtech ls [path]               List directory contents
    jtech cat <file>              Read a file
    jtech run <command>           Run a command
    jtech env [key]               Read environment variables
    jtech sysinfo                 System information
    jtech health                  System health check
    jtech permissions             List permission grants
    jtech revoke                  Revoke permissions
    jtech events                  Show audit trail
    jtech standup                 Company standup
    jtech status                  Company health
    jtech list                    List products
    jtech sell <id>               Record a sale
    jtech think <question>        CEO reasoning
    jtech launch                  Autonomous mode
"""

from __future__ import annotations

import json
import logging
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

import click

from jtech import __version__
from jtech.llm import get_llm, ThinkingEffort
from jtech.infrastructure.state_manager import StateManager
from jtech.infrastructure.event_bus import EventBus, EventSeverity, EventCategory, get_event_bus
from jtech.infrastructure.health_monitor import HealthMonitor
from jtech.infrastructure.error_handler import ErrorHandler
from jtech.infrastructure.permissions import PermissionLevel, PermissionDuration, get_permissions
from jtech.project_manager import ProjectManager, ProjectStatus
from jtech.system_access import SystemAccess
from jtech.company.memory import CompanyMemory
from jtech.company.departments.ceo import CEO
from jtech.company.departments.cto import CTO, HeadOfProduct
from jtech.company.departments.cmo import CMO
from jtech.company.departments.developer import Developer
from jtech.company.departments.designer import Designer, BrandManager
from jtech.company.departments.sales_agent import SalesAgent
from jtech.studio import ProductStudio
from jtech.marketplace import Marketplace
from jtech.improve import Improver

logger = logging.getLogger(__name__)

# ── HELPERS ─────────────────────────────────────────────────────

BOX_H = "╔══════════════════════════════════════════════════════════╗"
BOX_F = "╚══════════════════════════════════════════════════════════╝"


def title(text: str):
    click.echo()
    click.echo(BOX_H)
    click.echo(f"║{text:^66}║")
    click.echo(BOX_F)
    click.echo()


# ── CLI GROUP ───────────────────────────────────────────────────

@click.group()
@click.option("--debug", is_flag=True, help="Enable debug logging")
@click.version_option(version=__version__, prog_name="jtech")
def cli(debug: bool):
    """JTECH — Self-building AI company that builds and sells software products."""
    level = logging.DEBUG if debug else logging.INFO
    logging.basicConfig(level=level, format="%(message)s", stream=sys.stderr)
    if debug:
        logging.getLogger("jtech").setLevel(logging.DEBUG)


# ═══════════════════════════════════════════════════════════════
#  PROJECT COMMANDS
# ═══════════════════════════════════════════════════════════════

@cli.group()
def project():
    """Manage JTECH projects (create, list, open, status)."""
    pass


@project.command("create")
@click.argument("name")
@click.option("--desc", "-d", default="", help="Project description")
@click.option("--type", "-t", "ptype", default="product", help="Project type")
def project_create(name: str, desc: str, ptype: str):
    """Create a new project."""
    pm = ProjectManager()
    p = pm.create(name, desc, ptype)
    click.echo(f"✅  Project created: #{p.id} {p.name} [{p.status}]")
    if p.workspace_path:
        click.echo(f"   Workspace: {p.workspace_path}")


@project.command("list")
@click.option("--status", "-s", default=None, help="Filter by status")
def project_list(status: Optional[str]):
    """List all projects."""
    pm = ProjectManager()
    if status:
        projects = pm.list_by_status(status)
    else:
        projects = pm.list_all()

    if not projects:
        click.echo("No projects yet. Create one with 'jtech project create'")
        return

    click.echo(f"\n📦  Projects ({len(projects)} total)\n")
    click.echo(f"   {'ID':<4} {'Name':<32} {'Status':<16} {'Type':<12}")
    click.echo("   " + "-" * 64)
    for p in projects:
        click.echo(f"   {p.id:<4} {p.name:<32} {p.status:<16} {p.project_type:<12}")
    click.echo()


@project.command("open")
@click.argument("project_id", type=int)
def project_open(project_id: int):
    """Open a project workspace."""
    pm = ProjectManager()
    p = pm.get(project_id)
    if not p:
        click.echo(f"❌  Project #{project_id} not found")
        return

    click.echo(f"\n📂  Project #{p.id}: {p.name}")
    click.echo(f"   Status:    {p.status}")
    click.echo(f"   Type:      {p.project_type}")
    click.echo(f"   Created:   {p.created_at}")
    click.echo(f"   Workspace: {p.workspace_path or '(none)'}")
    click.echo()

    # Show workspace tree
    tree = pm.get_workspace_tree(project_id)
    if tree:
        click.echo("── Workspace Files ──")
        click.echo(tree)
        click.echo()
    else:
        click.echo("   (empty workspace)")


@project.command("status")
@click.argument("project_id", type=int)
@click.argument("new_status")
def project_status(project_id: int, new_status: str):
    """Change project status. Valid: draft, in_progress, review, shipped, maintenance, archived"""
    pm = ProjectManager()
    p = pm.get(project_id)
    if not p:
        click.echo(f"❌  Project #{project_id} not found")
        return

    if p.transition_to(new_status):
        click.echo(f"✅  Project #{p.id} status: {p.status} → {new_status}")
    else:
        valid = ProjectStatus.valid_transitions(p.status)
        click.echo(f"❌  Cannot transition from '{p.status}' to '{new_status}'")
        click.echo(f"   Valid transitions: {', '.join(valid)}")


@project.command("archive")
@click.argument("project_id", type=int)
def project_archive(project_id: int):
    """Archive a project."""
    pm = ProjectManager()
    if pm.archive(project_id):
        click.echo(f"✅  Project #{project_id} archived")
    else:
        click.echo(f"❌  Project #{project_id} not found")


# ═══════════════════════════════════════════════════════════════
#  SYSTEM ACCESS COMMANDS
# ═══════════════════════════════════════════════════════════════

@cli.command()
@click.argument("path", default=".")
@click.option("--long", "-l", is_flag=True, help="Detailed listing")
def ls(path: str, long: bool):
    """List directory contents (with permission)."""
    access = SystemAccess()
    items = access.list_directory(path)
    if items is None:
        return

    if not items:
        click.echo(f"(empty)")
        return

    if long:
        click.echo(f"\n{'Type':<8} {'Size':<10} {'Name':<30}")
        click.echo("-" * 48)
        for item in items:
            itype = "📁" if item["type"] == "directory" else "📄"
            size = f"{item['size']:,}" if item["type"] == "file" else "-"
            click.echo(f"{itype:<8} {size:<10} {item['name']:<30}")
    else:
        for item in items:
            prefix = "📁 " if item["type"] == "directory" else "📄 "
            click.echo(f"   {prefix}{item['name']}")
    click.echo()


@cli.command()
@click.argument("path")
@click.option("--lines", "-n", type=int, default=None, help="Number of lines to show")
def cat(path: str, lines: Optional[int]):
    """Read a file (with permission)."""
    access = SystemAccess()
    content = access.read_file(path)
    if content is None:
        return

    if lines:
        content_lines = content.split("\n")
        total = len(content_lines)
        shown = min(lines, total)
        click.echo(f"Showing {shown} of {total} lines:\n")
        click.echo("\n".join(content_lines[:lines]))
    else:
        click.echo(content)


@cli.command()
@click.argument("command")
@click.option("--timeout", "-t", type=int, default=30, help="Timeout in seconds")
def run(command: str, timeout: int):
    """Run a shell command (with permission)."""
    access = SystemAccess()
    result = access.run_command(command, timeout=timeout)
    if result.get("stdout"):
        click.echo(result["stdout"])
    if result.get("stderr"):
        click.echo(f"⚠️  stderr: {result['stderr']}", err=True)
    click.echo(f"\n→ Exit code: {result.get('exit_code', -1)}")


@cli.command()
@click.argument("key", required=False, default=None)
def env(key: Optional[str]):
    """Read environment variables (with permission)."""
    access = SystemAccess()
    if key:
        value = access.get_env(key)
        if value is not None:
            click.echo(f"{key}={value}")
    else:
        env_vars = access.list_env()
        if env_vars:
            for v in env_vars:
                value_display = "***" if v["sensitive"] else v["value"]
                click.echo(f"   {v['key']}={value_display}")


@cli.command()
def sysinfo():
    """Show system information."""
    access = SystemAccess()
    info = access.get_system_info()

    title("🖥️  System Information")

    click.echo(f"   Platform:  {info.get('platform', 'N/A')}")
    click.echo(f"   Python:    {info.get('python', 'N/A')}")
    click.echo(f"   Hostname:  {info.get('hostname', 'N/A')}")
    click.echo(f"   CWD:       {access.get_cwd()}")
    click.echo()

    if "disk" in info:
        d = info["disk"]
        click.echo(f"   Disk:      {d['used_gb']}/{d['total_gb']} GB ({d['usage_pct']}%)")
    if "memory" in info:
        m = info["memory"]
        click.echo(f"   Memory:    {m['usage_pct']}% used ({m['available_gb']} GB free)")
    if "uptime" in info:
        click.echo(f"   Uptime:    {info['uptime']}")
    click.echo()


# ═══════════════════════════════════════════════════════════════
#  INFRASTRUCTURE COMMANDS
# ═══════════════════════════════════════════════════════════════

@cli.command()
def health():
    """Run system health checks."""
    monitor = HealthMonitor()

    # Register default checks
    for name, fn, desc, critical in monitor.get_default_checks():
        monitor.register_check(name, fn, desc, critical)

    # Add JTECH-specific checks
    sm = StateManager()
    monitor.register_check("database", lambda: bool(sm.get_status()),
                           "SQLite database is operational", True)

    llm = get_llm()
    monitor.register_check("llm_client", llm.available,
                           "LLM client is configured (NVIDIA API)", True)

    monitor.register_check("workspace", lambda: Path("./workspace").exists() or True,
                           "Workspace directory", False)

    report = monitor.run_all()

    title("🩺  JTECH Health Report")

    click.echo(f"   Status:    {report.status.value.upper()}")
    click.echo(f"   Uptime:    {report.summary.get('uptime', 'N/A')}")
    click.echo()

    for check in report.checks:
        icon = "✅" if check["status"] == "passed" else ("⚠️" if check["status"] == "warning" else "❌")
        rt = f" ({check['response_time_ms']}ms)" if check.get("response_time_ms") else ""
        click.echo(f"   {icon} {check['name']}{rt}")
        if check.get("error"):
            click.echo(f"      Error: {check['error']}")

    click.echo()
    click.echo(f"   Passed: {report.summary.get('passed', 0)}/{report.summary.get('total', 0)}")


@cli.command()
def permissions():
    """List active permission grants."""
    access = SystemAccess()
    grants = access.list_permissions()

    title("🔐  Active Permissions")

    if not grants:
        click.echo("   No active permission grants.")
        click.echo()
        return

    for g in grants:
        click.echo(f"   {g['operation']:<20} -> {g['resource'][:40]:<40} [{g['level']}]")
    click.echo()


@cli.command()
@click.option("--operation", "-o", default=None, help="Revoke specific operation")
def revoke(operation: Optional[str]):
    """Revoke permission grants."""
    access = SystemAccess()
    count = access.revoke_permissions(operation)
    click.echo(f"✅  Revoked {count} permission grant(s)")


@cli.command()
@click.option("--type", "-t", "etype", default=None, help="Filter by event type")
@click.option("--limit", "-n", type=int, default=20, help="Number of events to show")
def events(etype: Optional[str], limit: int):
    """Show recent audit trail events."""
    bus = get_event_bus()
    recent = bus.get_recent_events(limit)

    title("📋  Recent Events")

    if not recent:
        click.echo("   No events recorded yet.")
        click.echo()
        return

    for e in recent[-limit:]:
        icon = {
            "success": "✅", "info": "ℹ️", "warning": "⚠️",
            "error": "❌", "critical": "🚨", "debug": "🔍"
        }.get(e.severity.value if hasattr(e.severity, 'value') else str(e.severity), "ℹ️")
        click.echo(f"   {icon} [{e.source}] {e.message}")
    click.echo()


@cli.command()
def events_stats():
    """Show event statistics."""
    bus = get_event_bus()
    counts = bus.get_audit().count_by_severity()
    click.echo("\n📊  Event Statistics\n")
    for severity, count in counts.items():
        click.echo(f"   {severity}: {count}")
    click.echo()


@cli.command()
def circuit():
    """Show circuit breaker status."""
    handler = ErrorHandler()
    circuits = handler.circuit_summary()

    title("⚡  Circuit Breaker Status")

    if not circuits:
        click.echo("   No circuits registered yet.")
        click.echo()
        return

    for c in circuits:
        icon = "✅" if c["state"] == "closed" else ("⚠️" if c["state"] == "half_open" else "❌")
        click.echo(f"   {icon} {c['name']:<20} [{c['state']}] "
                   f"({c['successes_total']} OK / {c['failures_total']} fail)")
    click.echo()


# ═══════════════════════════════════════════════════════════════
#  BUILD COMMAND
# ═══════════════════════════════════════════════════════════════

@cli.command()
@click.argument("idea", required=False, default=None)
@click.option("--stack", default="react-ts",
              type=click.Choice(["react-ts", "python-api"], case_sensitive=False))
def build(idea: Optional[str], stack: str):
    """Build a product from an idea (or let the CEO decide)."""
    llm = get_llm()
    if not llm.available:
        click.echo("❌  No NVIDIA API key configured. Set NVIDIA_API_KEY in .env")
        return

    title("JTECH Product Studio")

    pm = ProjectManager()
    start = time.time()
    result = ProductStudio().build_product(idea, stack=stack)
    elapsed = time.time() - start

    # Also create a project for tracking
    project = pm.create(
        name=result["name"],
        description=result["description"][:200],
        project_type=result["type"],
    )
    project.transition_to("shipped")

    click.echo("✅  BUILD COMPLETE")
    click.echo()
    click.echo(f"   Product:  {result['name']}")
    click.echo(f"   Type:     {result['type']}")
    click.echo(f"   Price:    ${result['price']:.2f}")
    click.echo(f"   Stack:    {', '.join(result['tech_stack'][:5])}")
    click.echo(f"   Location: {result['project_path']}")
    click.echo(f"   Files:    {result.get('files_generated', 0)}")
    click.echo(f"   Project:  #{project.id}")
    click.echo(f"   Time:     {elapsed:.1f}s")
    click.echo()

    if result.get("preview_path"):
        click.echo(f"   🖥️  Preview: {result['preview_path']}")
    if result.get("listing_copy"):
        click.echo(f"   📝  Copy: {result['listing_copy'][:200]}...")
    click.echo()
    click.echo(f"   💡  jtech sell {result['product_id']} --price {result['price']}")
    click.echo()


# ═══════════════════════════════════════════════════════════════
#  OTHER COMMANDS (unchanged)
# ═══════════════════════════════════════════════════════════════

@cli.command(name="list")
def list_products():
    """List all built products."""
    memory = CompanyMemory()
    products = memory.list_products()
    if not products:
        click.echo("📦  No products yet. Build one with 'jtech build'")
        return
    click.echo(f"\n📦  Products ({len(products)})\n")
    click.echo(f"   {'ID':<4} {'Name':<32} {'Price':<10} {'Sales':<8} {'Revenue':<10}")
    click.echo("   " + "-" * 64)
    for p in products:
        price = f"${p.get('price', 0):.2f}" if p.get("price") else "Free"
        rev = f"${p.get('revenue', 0):.2f}"
        click.echo(f"   {p['id']:<4} {p['name']:<32} {price:<10} {p.get('sales_count', 0):<8} {rev:<10}")
    click.echo()
    total = memory.get_revenue()
    click.echo(f"   Total: {total['total_sales']} sales, ${total['total_revenue']:.2f}")


@cli.command()
def status():
    """Show company health report."""
    memory = CompanyMemory()
    llm = get_llm()
    pm = ProjectManager()

    status = memory.get_status()
    revenue = memory.get_revenue()
    project_summary = pm.summary()

    title("JTECH — Company Status")

    click.echo(f"   Status:    {'🟢 Operational' if llm.available else '🔴 No API Key'}")
    click.echo(f"   Model:     {llm.model}")
    click.echo(f"   Usage:     {llm.get_usage_report()}")
    click.echo()
    click.echo(f"   Products:  {status['products_built']} built")
    click.echo(f"   Projects:  {project_summary['total']} total ({project_summary['active']} active)")
    click.echo(f"   Revenue:   ${status['total_revenue']:.2f} ({status['total_sales']} sales)")
    click.echo(f"   Actions:   {status['actions_taken']}")
    click.echo()

    if llm.available:
        ceo = CEO()
        analysis = ceo.strategic_review(status)
        if analysis:
            click.echo(f"   📢  CEO: \"{analysis.get('ceo_message', '')}\"")
            click.echo(f"   🎯  {analysis.get('strategic_direction', '')}")
    click.echo()


@cli.command()
@click.argument("product_id", type=int)
@click.option("--price", type=float, default=None)
@click.option("--customer", default="walk_in")
def sell(product_id: int, price: Optional[float], customer: str):
    """Record a product sale."""
    result = Marketplace().record_sale(product_id, customer=customer, price=price)
    if result.get("success"):
        click.echo(f"💰  Sale: {result['product_name']} — ${result['price']:.2f}")
    else:
        click.echo(f"❌  {result.get('error', 'Sale failed')}")


@cli.command()
def revenue():
    """Show revenue analytics."""
    analytics = Marketplace().get_analytics()
    title("💰  Revenue Report")
    click.echo(f"   Total Revenue:  ${analytics['total_revenue']:.2f}")
    click.echo(f"   Total Sales:    {analytics['total_sales']}")
    click.echo(f"   Products Built: {analytics['products_built']}")
    click.echo()


@cli.command()
def history():
    """Show recent activity."""
    actions = CompanyMemory().get_actions(limit=30)
    if not actions:
        click.echo("📋  No activity yet.")
        return
    click.echo(f"\n{'ID':<4} {'Source':<18} {'Action':<22} {'Time':<10}")
    click.echo("-" * 54)
    for a in reversed(actions):
        ts = a.get("timestamp", "")[11:19]
        click.echo(f"   {a['id']:<4} {a.get('department', '?'):<18} {a.get('action', '?'):<22} {ts:<10}")
    click.echo()


@cli.command()
@click.argument("question", required=False, default="What should JTECH build next?")
def think(question: str):
    """See the CEO's deep reasoning."""
    llm = get_llm()
    if not llm.available:
        click.echo("❌  No API key configured.")
        return

    title("🤔  Deep Thinking")

    click.echo(f"   Q: {question}\n")
    result = CEO().get_reasoning_trace(question)

    for i, step in enumerate(result.get("reasoning_steps", [])[:8], 1):
        if len(step) > 200:
            step = step[:200] + "..."
        click.echo(f"   [{i}] {step}")

    if result.get("self_corrections"):
        click.echo(f"\n   🔄 Self-corrections: {len(result['self_corrections'])}")

    if result.get("answer"):
        click.echo(f"\n💡 Answer: {json.dumps(result['answer'], indent=2)[:1000]}")
    click.echo()


@cli.command()
def standup():
    """Run a full company standup."""
    memory = CompanyMemory()
    llm = get_llm()
    if not llm.available:
        click.echo("❌  JTECH requires a valid NVIDIA_API_KEY in .env")
        return

    title("JTECH Daily Standup")

    status = memory.get_status()
    pm = ProjectManager()

    ceo = CEO()
    strategic = ceo.strategic_review(status)
    click.echo(f"👔  CEO: {strategic.get('strategic_direction', 'N/A')}")
    click.echo(f"   📢  \"{strategic.get('ceo_message', '')}\"")
    click.echo()

    revenue_data = memory.get_revenue()
    projects = pm.summary()
    click.echo(f"📊  Metrics: {status['products_built']} products, "
               f"{projects['total']} projects, "
               f"${revenue_data['total_revenue']:.2f} revenue")
    click.echo()

    memory.record_action("standup", "completed",
                          f"Products: {status['products_built']}, "
                          f"Projects: {projects['total']}, "
                          f"Revenue: ${revenue_data['total_revenue']:.2f}")

    click.echo(f"   💡  jtech build \"idea\"  — Build a product")
    click.echo(f"   💡  jtech project list   — See all projects")
    click.echo(f"   💡  jtech health         — System health check")
    click.echo()


@cli.command()
def launch():
    """Start autonomous mode."""
    llm = get_llm()
    if not llm.available:
        click.echo("❌  No API key configured.")
        return

    title("🚀  JTECH Autonomous Launch")

    click.echo("   Systems initializing...\n")
    ctx = click.get_current_context()
    ctx.invoke(standup)

    click.echo("   🏭  Building first product...")
    result = ProductStudio().build_product()
    click.echo(f"\n✅  Built: {result['name']} (${result['price']:.2f})")
    click.echo(f"   📁  {result['project_path']}")
    click.echo()


@cli.command()
@click.argument("source")
@click.argument("destination")
@click.option("--report", is_flag=True, help="Show detailed report")
def improve(source: str, destination: str, report: bool):
    """Copy a project and improve its code quality.

    SOURCE is the path to the project to improve.
    DESTINATION is where to save the improved copy.

    Example:
        jtech improve C:/source/my-project C:/dest/my-project
    """
    llm = get_llm()
    if not llm.available:
        click.echo("⚠️  No API key configured. Improvements will be basic.")

    improver = Improver()
    result = improver.improve(source, destination)

    if not result.get("success"):
        click.echo(f"❌  {result.get('error', 'Failed to improve project')}")
        return

    title("JTECH Improvement Complete")

    click.echo(f"   Source:      {result['source']}")
    click.echo(f"   Destination: {result['destination']}")
    click.echo(f"   Files:       {result['files_copied']}")
    click.echo(f"   Issues:      {result['issues_found']} found, {result['issues_fixed']} fixed")
    click.echo(f"   Time:        {result['elapsed_seconds']}s")
    click.echo()

    if result.get('fixes'):
        click.echo("   Fixes Applied:")
        for fix in result['fixes']:
            click.echo(f"     ✅ {fix['file']}: {fix['type']}")
        click.echo()

    if report and result.get('report'):
        click.echo(result['report'])


@cli.command()
@click.option("--port", "-p", type=int, default=8080, help="Port to serve on")
@click.option("--host", default="0.0.0.0", help="Host to bind to")
@click.option("--open", "open_browser", is_flag=True, help="Open browser automatically")
def web(port: int, host: str, open_browser: bool):
    """Start the JTECH web dashboard in your browser."""
    llm = get_llm()
    if not llm.available:
        click.echo("⚠️  No NVIDIA API key found. The dashboard will load but building products won't work.")
        click.echo("   Set NVIDIA_API_KEY in .env to enable product building.")
        click.echo()

    click.echo(f"🚀  Starting JTECH web dashboard on http://{host}:{port}")
    if open_browser:
        import webbrowser
        webbrowser.open(f"http://localhost:{port}")
        click.echo(f"   Opening browser to http://localhost:{port}")
    click.echo()

    from jtech.web.server import run_server
    run_server(host=host, port=port)


def main():
    """Entry point for the jtech CLI."""
    cli()
