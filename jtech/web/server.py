"""
JTECH Web Server — Browser dashboard for JTECH.

Zero external dependencies. Uses Python's built-in http.server.
Serves a modern dashboard UI and API endpoints for JTECH operations.

Usage:
    python -m jtech.web.server          # Start on port 8080
    python -m jtech.web.server --port 3000  # Custom port
    jtech web                           # Via CLI (once registered)
"""

from __future__ import annotations

import json
import logging
import os
import sys
import time
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from typing import Any, Optional
from urllib.parse import urlparse, parse_qs

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from jtech.company.memory import CompanyMemory
from jtech.studio import ProductStudio
from jtech.marketplace import Marketplace
from jtech.project_manager import ProjectManager
from jtech.llm import get_llm

logger = logging.getLogger(__name__)

PORT = int(os.environ.get("JTECH_WEB_PORT", "8080"))
HOST = os.environ.get("JTECH_WEB_HOST", "0.0.0.0")

STATIC_DIR = Path(__file__).resolve().parent / "static"
BUILT_PRODUCTS_DIR = Path(__file__).resolve().parent.parent.parent / "built_products"
JTECH_DIR = Path(__file__).resolve().parent.parent.parent

# ── MIME TYPES ──────────────────────────────────────────────────

MIME_TYPES = {
    ".html": "text/html; charset=utf-8",
    ".js": "application/javascript; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".json": "application/json; charset=utf-8",
    ".svg": "image/svg+xml",
    ".png": "image/png",
    ".ico": "image/x-icon",
}


# ── API HANDLERS ────────────────────────────────────────────────

def api_status() -> dict:
    """Company status and health."""
    memory = CompanyMemory()
    llm = get_llm()
    pm = ProjectManager()

    status = memory.get_status()
    revenue = memory.get_revenue()
    projects = pm.summary()

    return {
        "company": "JTECH",
        "status": "operational" if llm.available else "no_api_key",
        "model": llm.model,
        "api_keys": llm.num_keys,
        "api_available": llm.available,
        "products": {
            "built": status["products_built"],
            "total_sales": status["total_sales"],
            "total_revenue": status["total_revenue"],
            "actions_taken": status["actions_taken"],
        },
        "revenue": {
            "total": revenue["total_revenue"],
            "sales": revenue["total_sales"],
            "products_built": revenue["products_built"],
        },
        "projects": projects,
        "timestamp": datetime.now().isoformat(),
    }


def api_products() -> list[dict]:
    """List all products with details."""
    memory = CompanyMemory()
    products = memory.list_products()
    result = []
    for p in products:
        slug = p["name"].lower().replace(" ", "-").replace("_", "-")
        preview_path = BUILT_PRODUCTS_DIR / slug / "preview.html"
        spec_path = BUILT_PRODUCTS_DIR / slug / "product_spec.json"
        brand_path = BUILT_PRODUCTS_DIR / slug / "brand.json"

        product_info = {
            "id": p["id"],
            "name": p["name"],
            "description": p["description"],
            "type": p.get("product_type", "Web App"),
            "price": p.get("price"),
            "sales_count": p.get("sales_count", 0),
            "revenue": p.get("revenue", 0),
            "status": p.get("status", "built"),
            "version": p.get("version", "1.0.0"),
            "created_at": p.get("created_at", ""),
            "slug": slug,
            "has_preview": preview_path.exists(),
        }

        # Load spec if exists
        if spec_path.exists():
            try:
                with open(spec_path) as f:
                    spec = json.load(f)
                    product_info["features"] = spec.get("features", [])
                    product_info["tech_stack"] = spec.get("tech_stack", [])
            except Exception:
                pass

        # Load brand if exists
        if brand_path.exists():
            try:
                with open(brand_path) as f:
                    brand = json.load(f)
                    product_info["tagline"] = brand.get("tagline", "")
                    product_info["colors"] = brand.get("colors", {})
                    product_info["listing_copy"] = brand.get("listing_copy", "")
                    product_info["sales_pitch"] = brand.get("sales_pitch", "")
            except Exception:
                pass

        result.append(product_info)

    return result


def api_build(idea: str, stack: str = "react-ts") -> dict:
    """Build a product from an idea."""
    if not idea or not idea.strip():
        return {"error": "Idea cannot be empty", "success": False}

    try:
        studio = ProductStudio()
        result = studio.build_product(idea.strip())

        return {
            "success": True,
            "product": {
                "id": result.get("product_id"),
                "name": result.get("name"),
                "description": result.get("description"),
                "price": result.get("price"),
                "type": result.get("type"),
                "features": result.get("features", []),
                "tech_stack": result.get("tech_stack", []),
                "slug": result.get("name", "").lower().replace(" ", "-").replace("_", "-"),
                "project_path": result.get("project_path"),
                "preview_path": result.get("preview_path"),
                "tagline": result.get("tagline"),
                "colors": result.get("colors"),
                "listing_copy": result.get("listing_copy"),
                "sales_pitch": result.get("sales_pitch"),
            },
            "build_time_seconds": result.get("build_time_seconds", 0),
        }
    except Exception as e:
        logger.error(f"Build failed: {e}", exc_info=True)
        return {"error": str(e), "success": False}


def api_events(limit: int = 30) -> list[dict]:
    """Recent company activity."""
    memory = CompanyMemory()
    return memory.get_actions(limit=limit)


def api_revenue() -> dict:
    """Revenue analytics."""
    memory = CompanyMemory()
    return memory.get_revenue()


def api_sell(product_id: int, price: Optional[float] = None) -> dict:
    """Record a product sale."""
    marketplace = Marketplace()
    result = marketplace.record_sale(product_id, price=price)
    return result


# ── REQUEST HANDLER ─────────────────────────────────────────────

class JTECHHTTPHandler(BaseHTTPRequestHandler):
    """HTTP request handler for JTECH web dashboard."""

    def log_message(self, format, *args):
        logger.info(f"{self.client_address[0]} - {format % args}")

    def _send_json(self, data: Any, status: int = 200):
        """Send a JSON response."""
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()
        self.wfile.write(json.dumps(data, indent=2, default=str).encode("utf-8"))

    def _send_html(self, html: str, status: int = 200):
        """Send an HTML response."""
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Cache-Control", "no-cache, must-revalidate")
        self.end_headers()
        self.wfile.write(html.encode("utf-8"))

    def _send_file(self, filepath: Path):
        """Send a static file."""
        ext = filepath.suffix.lower()
        mime = MIME_TYPES.get(ext, "application/octet-stream")

        try:
            with open(filepath, "rb") as f:
                content = f.read()

            self.send_response(200)
            self.send_header("Content-Type", mime)
            self.send_header("Content-Length", str(len(content)))
            self.send_header("Cache-Control", "public, max-age=3600")
            self.end_headers()
            self.wfile.write(content)
        except FileNotFoundError:
            self._send_json({"error": "File not found"}, 404)

    def _serve_preview(self, slug: str):
        """Serve a product preview HTML (sanitized against path traversal)."""
        # Sanitize slug: remove directory separators and traversal sequences
        slug = slug.replace("/", "").replace("\\", "").replace("..", "")
        if not slug:
            self._send_html("<h1>Invalid preview</h1>", 400)
            return
        preview_path = BUILT_PRODUCTS_DIR / slug / "preview.html"
        if preview_path.exists():
            self._send_file(preview_path)
        else:
            # Try alternative slug patterns
            for alt_dir in BUILT_PRODUCTS_DIR.iterdir():
                if alt_dir.is_dir() and slug in alt_dir.name:
                    alt_preview = alt_dir / "preview.html"
                    if alt_preview.exists():
                        self._send_file(alt_preview)
                        return
            self._send_html(f"""<!DOCTYPE html>
<html><head><title>Preview Not Found</title>
<script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-gray-50 min-h-screen flex items-center justify-center">
<div class="text-center">
  <div class="text-6xl mb-4">🔍</div>
  <h1 class="text-2xl font-bold text-gray-800 mb-2">Preview Not Found</h1>
  <p class="text-gray-500">No preview HTML for <code class="bg-gray-100 px-2 py-0.5 rounded">{slug}</code></p>
  <a href="/" class="mt-6 inline-block text-blue-600 hover:underline">← Back to dashboard</a>
</div>
</body></html>""", 404)

    def do_GET(self):
        """Handle GET requests."""
        parsed = urlparse(self.path)
        path = parsed.path
        params = parse_qs(parsed.query)

        # ── API Routes ──
        if path == "/api/status":
            return self._send_json(api_status())
        elif path == "/api/products":
            return self._send_json(api_products())
        elif path == "/api/events":
            limit = int(params.get("limit", [30])[0])
            return self._send_json(api_events(limit))
        elif path == "/api/revenue":
            return self._send_json(api_revenue())
        elif path.startswith("/preview/"):
            slug = path[len("/preview/"):].strip("/")
            return self._serve_preview(slug)

        # ── Serve static files (with path traversal protection) ──
        if path == "/" or path == "":
            path = "/index.html"

        safe_path = path.lstrip("/").replace("\\", "/")
        # Reject any path with parent directory traversal
        if ".." in safe_path.split("/"):
            self._send_json({"error": "Invalid path"}, 403)
            return
        filepath = (STATIC_DIR / safe_path).resolve()
        # Verify resolved path is within STATIC_DIR
        try:
            filepath.relative_to(STATIC_DIR.resolve())
        except ValueError:
            self._send_json({"error": "Access denied"}, 403)
            return
        if filepath.exists() and filepath.is_file():
            return self._send_file(filepath)

        # ── Fallback to dashboard ──
        fallback = STATIC_DIR / "index.html"
        if fallback.exists():
            return self._send_file(fallback)

        self._send_json({"error": "Not found"}, 404)

    def do_POST(self):
        """Handle POST requests."""
        parsed = urlparse(self.path)
        path = parsed.path

        # Read request body
        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length) if content_length > 0 else b"{}"
        try:
            data = json.loads(body) if body else {}
        except json.JSONDecodeError:
            data = {}

        if path == "/api/build":
            idea = data.get("idea", "")
            stack = data.get("stack", "react-ts")
            result = api_build(idea, stack)

            if result.get("success"):
                return self._send_json(result, 200)
            else:
                return self._send_json(result, 400)

        elif path == "/api/sell":
            product_id = data.get("product_id")
            price = data.get("price")

            if not product_id:
                return self._send_json({"error": "product_id required"}, 400)

            result = api_sell(int(product_id), price)
            if result.get("success"):
                return self._send_json(result, 200)
            else:
                return self._send_json(result, 400)

        elif path == "/api/think":
            question = data.get("question", "What should JTECH build next?")
            try:
                from jtech.company.departments.ceo import CEO
                ceo = CEO()
                result = ceo.get_reasoning_trace(question)
                return self._send_json({
                    "question": question,
                    "reasoning_steps": result.get("reasoning_steps", [])[:6],
                    "self_corrections": result.get("self_corrections", []),
                    "answer": result.get("answer", {}),
                })
            except Exception as e:
                return self._send_json({"error": str(e)}, 500)

        else:
            self._send_json({"error": f"Unknown endpoint: {path}"}, 404)

    def do_OPTIONS(self):
        """Handle CORS preflight."""
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()


# ── SERVER ──────────────────────────────────────────────────────

def create_server(host: str = HOST, port: int = PORT) -> HTTPServer:
    """Create and configure the JTECH web server."""
    server = HTTPServer((host, port), JTECHHTTPHandler)
    return server


def run_server(host: str = HOST, port: int = PORT):
    """Start the JTECH web server."""
    # Handle Windows encoding for unicode support in logs
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except (AttributeError, ValueError):
        pass

    server = create_server(host, port)
    print(f"""
{'='*62}
  JTECH Web Dashboard
{'='*62}

  Server:  http://{host}:{port}
  Dashboard  ->  http://localhost:{port}/
  Status API ->  http://localhost:{port}/api/status
  Products   ->  http://localhost:{port}/api/products

  Press Ctrl+C to stop
{'='*62}
""")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nServer stopped.")
        server.server_close()


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="JTECH Web Dashboard")
    parser.add_argument("--port", type=int, default=PORT, help=f"Port (default: {PORT})")
    parser.add_argument("--host", type=str, default=HOST, help=f"Host (default: {HOST})")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(message)s")
    run_server(args.host, args.port)
