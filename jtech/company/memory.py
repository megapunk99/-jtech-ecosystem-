"""
JTECH Company Memory — Tracks all company operations, products, decisions.

Every action, every product built, every sale is recorded here.
This is the company's institutional memory.
"""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)


class CompanyMemory:
    """
    Persistent memory for JTECH operations.

    Stores actions, products, sales, and metrics in a JSON-based store.
    No external database required — works out of the box.
    """

    def __init__(self, data_dir: Optional[str] = None):
        self.data_dir = Path(data_dir or os.environ.get("JTECH_DATA_DIR", "./data"))
        self.data_dir.mkdir(parents=True, exist_ok=True)

        self._actions_file = self.data_dir / "actions.json"
        self._products_file = self.data_dir / "products.json"
        self._sales_file = self.data_dir / "sales.json"
        self._metrics_file = self.data_dir / "metrics.json"
        self._knowledge_file = self.data_dir / "knowledge.json"

        self._actions: list[dict] = self._load(self._actions_file)
        self._products: list[dict] = self._load(self._products_file)
        self._sales: list[dict] = self._load(self._sales_file)
        self._metrics: list[dict] = self._load(self._metrics_file)
        self._knowledge: list[dict] = self._load(self._knowledge_file)

    def _load(self, path: Path) -> list:
        try:
            if path.exists():
                with open(path) as f:
                    return json.load(f)
        except Exception as e:
            logger.debug(f"Could not load {path}: {e}")
        return []

    def _save(self, path: Path, data: list) -> None:
        try:
            with open(path, "w") as f:
                json.dump(data, f, indent=2, default=str)
        except Exception as e:
            logger.error(f"Could not save {path}: {e}")

    # ── Actions ────────────────────────────────────────────────

    def record_action(self, department: str, action: str, summary: str,
                      metadata: Optional[dict] = None) -> int:
        """Record a company action."""
        entry = {
            "id": len(self._actions) + 1,
            "timestamp": datetime.now().isoformat(),
            "department": department,
            "action": action,
            "summary": summary,
            "metadata": metadata or {},
        }
        self._actions.append(entry)
        self._save(self._actions_file, self._actions)
        return entry["id"]

    def get_actions(self, limit: int = 20, department: Optional[str] = None) -> list[dict]:
        """Get recent actions."""
        actions = self._actions
        if department:
            actions = [a for a in actions if a["department"] == department]
        return actions[-limit:]

    # ── Products ───────────────────────────────────────────────

    def register_product(self, name: str, description: str,
                         product_type: str, tech_stack: list[str]) -> int:
        """Register a new product built by JTECH."""
        entry = {
            "id": len(self._products) + 1,
            "created_at": datetime.now().isoformat(),
            "name": name,
            "description": description,
            "product_type": product_type,
            "tech_stack": tech_stack,
            "status": "built",
            "version": "1.0.0",
            "price": None,
            "sales_count": 0,
            "revenue": 0,
        }
        self._products.append(entry)
        self._save(self._products_file, self._products)
        self.record_action("studio", "product_built",
                           f"Built product: {name} ({product_type})")
        return entry["id"]

    def list_products(self, status: Optional[str] = None) -> list[dict]:
        """List all products, optionally filtered by status."""
        products = self._products
        if status:
            products = [p for p in products if p.get("status") == status]
        return products

    def get_product(self, product_id: int) -> Optional[dict]:
        """Get a specific product by ID."""
        for p in self._products:
            if p["id"] == product_id:
                return p
        return None

    # ── Sales ──────────────────────────────────────────────────

    def record_sale(self, product_id: int, customer: str, price: float) -> int:
        """Record a product sale."""
        entry = {
            "id": len(self._sales) + 1,
            "timestamp": datetime.now().isoformat(),
            "product_id": product_id,
            "customer": customer,
            "price": price,
        }
        self._sales.append(entry)
        self._save(self._sales_file, self._sales)

        # Update product stats
        for p in self._products:
            if p["id"] == product_id:
                p["sales_count"] = p.get("sales_count", 0) + 1
                p["revenue"] = p.get("revenue", 0) + price
                break
        self._save(self._products_file, self._products)

        self.record_action("marketplace", "product_sold",
                           f"Sold product #{product_id} for ${price:.2f}")
        return entry["id"]

    def get_revenue(self) -> dict:
        """Get total revenue and sales stats."""
        total = sum(s["price"] for s in self._sales)
        return {
            "total_revenue": total,
            "total_sales": len(self._sales),
            "unique_products": len(set(s["product_id"] for s in self._sales)),
            "products_built": len(self._products),
        }

    # ── Metrics ────────────────────────────────────────────────

    def record_metric(self, name: str, value: float, tags: Optional[dict] = None) -> None:
        """Record a business metric."""
        self._metrics.append({
            "timestamp": datetime.now().isoformat(),
            "name": name,
            "value": value,
            "tags": tags or {},
        })
        self._save(self._metrics_file, self._metrics)

    def get_metrics(self, name: Optional[str] = None, limit: int = 50) -> list[dict]:
        """Get metrics history."""
        metrics = self._metrics
        if name:
            metrics = [m for m in metrics if m["name"] == name]
        return metrics[-limit:]

    # ── Knowledge ──────────────────────────────────────────────

    def store_knowledge(self, topic: str, content: str, source: str = "internal") -> int:
        """Store a piece of knowledge/lesson learned."""
        entry = {
            "id": len(self._knowledge) + 1,
            "timestamp": datetime.now().isoformat(),
            "topic": topic,
            "content": content,
            "source": source,
        }
        self._knowledge.append(entry)
        self._save(self._knowledge_file, self._knowledge)
        return entry["id"]

    def get_knowledge(self, topic: Optional[str] = None, limit: int = 20) -> list[dict]:
        """Get stored knowledge."""
        knowledge = self._knowledge
        if topic:
            knowledge = [k for k in knowledge if topic.lower() in k["topic"].lower()]
        return knowledge[-limit:]

    # ── Company status ─────────────────────────────────────────

    def get_status(self) -> dict:
        """Get a comprehensive company status report."""
        revenue = self.get_revenue()
        return {
            "company": "JTECH",
            "status": "operational",
            "actions_taken": len(self._actions),
            "products_built": len(self._products),
            "total_sales": revenue["total_sales"],
            "total_revenue": revenue["total_revenue"],
            "knowledge_base": len(self._knowledge),
            "metrics_tracked": len(self._metrics),
        }
