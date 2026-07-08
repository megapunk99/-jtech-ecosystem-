"""
JTECH Marketplace — Lists, promotes, and sells products.

The Marketplace takes finished products from the Studio and makes them
available for sale. It manages listings, pricing, sales tracking, and revenue.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Optional

from jtech.company.memory import CompanyMemory
from jtech.llm import get_llm

logger = logging.getLogger(__name__)


class Marketplace:
    """
    JTECH Marketplace — product sales engine.

    Features:
    - Product listings with pricing
    - Sales tracking and revenue management
    - Customer acquisition tracking
    - Product performance analytics
    """

    def __init__(self, memory: Optional[CompanyMemory] = None):
        self.memory = memory or CompanyMemory()
        self.llm = get_llm()

    def list_available_products(self) -> list[dict]:
        """List all products available for sale."""
        products = self.memory.list_products()
        available = []
        for p in products:
            available.append({
                "id": p["id"],
                "name": p["name"],
                "description": p["description"],
                "type": p.get("product_type", "Software"),
                "price": p.get("price", "Unpriced"),
                "price_label": f"${p['price']:.2f}" if p.get("price") else "Contact for pricing",
                "sales": p.get("sales_count", 0),
                "revenue": p.get("revenue", 0),
                "status": p.get("status", "built"),
            })
        return available

    def record_sale(self, product_id: int, customer: str = "direct_sale",
                    price: Optional[float] = None) -> dict:
        """Record a product sale."""
        product = self.memory.get_product(product_id)
        if not product:
            return {"error": "Product not found", "success": False}

        sale_price = price if price is not None else product.get("price", 9.99)
        sale_id = self.memory.record_sale(product_id, customer, sale_price)

        return {
            "sale_id": sale_id,
            "product_id": product_id,
            "product_name": product["name"],
            "price": sale_price,
            "customer": customer,
            "timestamp": datetime.now().isoformat(),
            "success": True,
        }

    def get_analytics(self) -> dict:
        """Get marketplace analytics and performance."""
        revenue = self.memory.get_revenue()
        products = self.memory.list_products()

        return {
            "total_revenue": revenue["total_revenue"],
            "total_sales": revenue["total_sales"],
            "products_built": revenue["products_built"],
            "unique_products_sold": revenue["unique_products"],
            "average_revenue_per_product": (
                revenue["total_revenue"] / revenue["unique_products"]
                if revenue["unique_products"] > 0 else 0
            ),
            "products": [
                {
                    "name": p["name"],
                    "price": p.get("price"),
                    "sales": p.get("sales_count", 0),
                    "revenue": p.get("revenue", 0),
                }
                for p in products
            ],
        }

    def generate_catalog(self) -> str:
        """Generate a product catalog webpage."""
        products = self.list_available_products()

        prompt = (
            "Create a beautiful HTML product catalog page for JTECH.\n\n"
            f"Products:\n" + "\n".join(
                f"- {p['name']}: {p['description']} — {p['price_label']}"
                for p in products
            ) + "\n\n"
            "The page should look like a premium software marketplace.\n"
            "Include:\n"
            "- Header: JTECH Marketplace\n"
            "- Product cards with name, description, price, CTA\n"
            "- Modern CSS with smooth animations\n"
            "- Responsive grid layout\n"
            "- Professional typography\n\n"
            "Output ONLY the complete HTML code. No markdown fences."
        )

        return self.llm.chat(
            [{"role": "user", "content": prompt}],
            system_prompt="You build stunning marketplace pages that drive sales."
        ) or "<html><body><h1>JTECH Marketplace</h1><p>No products yet.</p></body></html>"
