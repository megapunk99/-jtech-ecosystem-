"""
JTECH Product Studio — The factory that designs and builds software products.

Now powered by:
- Lovable-style AppBuilder (React/TypeScript/Tailwind + Supabase)
- DeepSeek thinking mode for all analysis
- Grok-style personality for output
- Claude-style structured marketing
- Live preview generation
- Visual editing capabilities

Pipeline: IDEATE → THINK → RESEARCH → DESIGN → BUILD → PREVIEW → PRICE → SHIP
"""

from __future__ import annotations

import json
import logging
import os
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from jtech.company.memory import CompanyMemory
from jtech.company.departments.ceo import CEO
from jtech.company.departments.cto import CTO, HeadOfProduct
from jtech.company.departments.developer import Developer
from jtech.company.departments.designer import Designer, BrandManager
from jtech.company.departments.cmo import CMO
from jtech.company.departments.sales_agent import SalesAgent
from jtech.llm import get_llm, ThinkingEffort

logger = logging.getLogger(__name__)


class ProductStudio:
    """
    The JTECH Product Studio — end-to-end product factory.

    Pipeline:
    1. IDEATE  → CEO decides what to build (with deep reasoning)
    2. THINK   → DeepSeek-style requirements analysis
    3. RESEARCH → HeadOfProduct validates market
    4. DESIGN  → CTO designs architecture
    5. BUILD   → AppBuilder generates full-stack app
    6. PREVIEW → Designer creates live preview
    7. PRICE   → CMO prices and creates listing
    8. SHIP    → Register product, generate sales pitch
    """

    def __init__(self, memory: Optional[CompanyMemory] = None):
        self.memory = memory or CompanyMemory()
        self.llm = get_llm()
        self.ceo = CEO()
        self.cto = CTO()
        self.head_of_product = HeadOfProduct()
        self.developer = Developer()
        self.designer = Designer()
        self.brand = BrandManager()
        self.cmo = CMO()
        self.sales = SalesAgent()

    def build_product(self, idea: Optional[str] = None, stack: str = "react-ts") -> dict:
        """
        Build a product from an idea (or have the CEO decide).

        Uses the full pipeline with thinking mode, Lovable-style builder,
        and Claude-style marketing.
        """
        # ── Phase 1: IDEATE ──
        logger.info("📋 Phase 1: Ideation")
        if idea:
            product_idea = {
                "product_name": idea.split(" - ")[0].strip()[:60],
                "description": idea,
                "tech_stack": ["React", "TypeScript", "Tailwind", "Supabase"],
                "price_point": 9.99,
            }
            logger.info(f"   Using your idea: {product_idea['product_name']}")
        else:
            logger.info("   CEO thinking deeply about what to build...")
            product_idea = self.ceo.decide_what_to_build()

        product_name = product_idea.get("product_name", "Unknown Product")
        description = product_idea.get("description", "")
        logger.info(f"   Product: {product_name}")

        # ── Phase 2: THINK (DeepSeek-style requirements analysis) ──
        logger.info("📋 Phase 2: Deep Requirements Analysis")
        analysis_result, analysis_reasoning = self.llm.chat_json_rich(
            [{"role": "user", "content": (
                f"Analyze the requirements for this product:\n\n"
                f"Name: {product_name}\n"
                f"Description: {description}\n"
                f"Stack: {product_idea.get('tech_stack', [])}\n\n"
                f"Think step-by-step about:\n"
                f"1. Core functionality needed\n"
                f"2. Key pages/screens\n"
                f"3. Data model requirements\n"
                f"4. API endpoints needed\n"
                f"5. User authentication model\n"
                f"6. External integrations\n\n"
                f"Output JSON:\n"
                f"{{\n"
                f'  "core_features": ["Feature 1", "Feature 2"],\n'
                f'  "pages": ["Dashboard", "Settings"],\n'
                f'  "data_entities": ["Entity1", "Entity2"],\n'
                f'  "api_endpoints": ["GET /api/items"],\n'
                f'  "auth_model": "supabase",\n'
                f'  "complexity": "low/medium/high",\n'
                f'  "estimated_pages": 3\n'
                f"}}"
            )}],
            system_prompt="You analyze product requirements with deep technical insight.",
            thinking_effort=ThinkingEffort.DEEP,
        )

        if analysis_reasoning.steps:
            logger.info(f"   🤔 Analysis: {len(analysis_reasoning.steps)} reasoning steps, "
                        f"{len(analysis_reasoning.self_corrections)} self-corrections")

        features = analysis_result.get("core_features", []) if analysis_result else []
        pages = analysis_result.get("pages", []) if analysis_result else []
        product_idea["features"] = features
        product_idea["pages"] = pages

        # ── Phase 3: RESEARCH ──
        logger.info("📋 Phase 3: Market Research")
        research = self.head_of_product.market_research(product_name, description)
        price = research.get("recommended_price", product_idea.get("price_point", 9.99))
        logger.info(f"   Recommended price: ${price}")

        # ── Phase 4: DESIGN ──
        logger.info("📋 Phase 4: Architecture Design")
        architecture = self.cto.design_architecture(product_idea)
        tech_stack = product_idea.get("tech_stack", architecture.get("tech_stack", ["React", "Supabase"]))
        product_idea["architecture"] = architecture
        logger.info(f"   Stack: {', '.join(tech_stack[:4])}")

        # ── Phase 5: BUILD (Lovable-style AppBuilder) ──
        logger.info("📋 Phase 5: Building Full-Stack Application")
        project_path = self.developer.scaffold_project(product_idea)

        try:
            build_result = self.developer.build_full_app(product_idea, stack=stack)
            files = build_result.get("files", {})
            preview_html = build_result.get("preview_html", "")
            components = build_result.get("components", [])

            if files:
                written = self.developer.write_files(files, project_path)
                logger.info(f"   Generated {len(written)} files")
            else:
                # Fallback: use old method
                data_model = self.developer.design_data_model(product_idea)
                product_idea["data_model"] = data_model
                implementation = self.developer.plan_implementation(product_idea)
                product_idea["features"] = [s.get("details", "") for s in implementation[:5]]
                code_files = self.developer.generate_code(product_idea)
                if code_files:
                    written = self.developer.write_files(code_files, project_path)
                    logger.info(f"   Generated {len(written)} files (legacy mode)")
                preview_html = ""
        except Exception as e:
            logger.warning(f"   AppBuilder error: {e}")
            logger.info("   Falling back to legacy code generation...")
            data_model = self.developer.design_data_model(product_idea)
            product_idea["data_model"] = data_model
            implementation = self.developer.plan_implementation(product_idea)
            product_idea["features"] = [s.get("details", "") for s in implementation[:5]]
            code_files = self.developer.generate_code(product_idea)
            written = self.developer.write_files(code_files, project_path) if code_files else []
            preview_html = ""

        logger.info(f"   Project path: {project_path}")

        # ── Phase 6: PREVIEW + BRANDING ──
        logger.info("📋 Phase 6: Design & Branding")

        # Brand identity
        brand_identity = self.brand.create_brand_identity(product_name)
        svg_logo = self.brand.generate_svg_logo(brand_identity)

        # Write logo
        logo_path = Path(project_path) / "logo.svg"
        with open(logo_path, "w") as f:
            f.write(svg_logo)

        # Write brand identity
        brand_path = Path(project_path) / "brand.json"
        with open(brand_path, "w") as f:
            json.dump(brand_identity, f, indent=2)

        # Generate stunning live preview
        logger.info("   Generating live preview...")
        try:
            live_preview = self.designer.generate_live_preview({
                "name": product_name,
                "description": description,
                "price": price,
                "features": features,
                "color_scheme": brand_identity.get("colors", {}),
            })
            preview_path = Path(project_path) / "preview.html"
            with open(preview_path, "w", encoding="utf-8") as f:
                f.write(live_preview)
            logger.info(f"   Live preview created: {preview_path}")
        except Exception as e:
            logger.warning(f"   Preview generation failed: {e}")
            live_preview = ""
            preview_path = None

        # Also generate legacy landing page
        landing_page = self.designer.generate_html_template({
            "name": product_name,
            "description": description,
            "price": price,
        })
        landing_path = Path(project_path) / "landing.html"
        with open(landing_path, "w") as f:
            f.write(landing_page)

        logger.info(f"   Brand identity, logo, landing page created")

        # ── Phase 7: PACKAGE ──
        logger.info("📋 Phase 7: Packaging")
        product_type = "Web App"
        if "api" in str(tech_stack).lower() or "fastapi" in str(tech_stack).lower():
            product_type = "API"
        elif stack == "python-api":
            product_type = "API"

        product_id = self.memory.register_product(
            name=product_name,
            description=description,
            product_type=product_type,
            tech_stack=tech_stack,
        )

        # Price the product (with reasoning)
        pricing = self.cmo.price_product({
            "name": product_name,
            "product_type": product_type,
        }, research)

        final_price = pricing.get("recommended_price", price)

        # Write product spec
        spec_path = Path(project_path) / "product_spec.json"
        with open(spec_path, "w") as f:
            json.dump({
                "product_id": product_id,
                "name": product_name,
                "description": description,
                "type": product_type,
                "tech_stack": tech_stack,
                "price": final_price,
                "pricing_model": pricing.get("pricing_model", "one-time"),
                "built_at": datetime.now().isoformat(),
                "features": features,
                "pages": pages,
                "brand": brand_identity,
                "stack": stack,
            }, f, indent=2)

        # ── Phase 8: LISTING + SALES ──
        logger.info("📋 Phase 8: Market Listing & Sales")

        # Claude-style structured listing
        listing_copy = self.cmo.create_listing({
            "name": product_name,
            "description": description,
            "price": final_price,
            "features": features,
        })

        # Go-to-market strategy
        market_strategy = self.cmo.go_to_market({
            "name": product_name,
            "description": description,
            "price": final_price,
            "product_type": product_type,
        })

        # Grok-style sales pitch
        sales_pitch = self.sales.pitch_product({
            "name": product_name,
            "description": description,
            "price": final_price,
            "features": features,
        })

        # Extract pain language
        pain_language = self.cmo.extract_pain_language({
            "name": product_name,
            "description": description,
        })

        # Store market strategy
        market_path = Path(project_path) / "market_strategy.json"
        with open(market_path, "w") as f:
            json.dump({
                "listing_copy": listing_copy,
                "market_strategy": market_strategy,
                "sales_pitch": sales_pitch,
                "pain_language": pain_language,
                "pricing": pricing,
            }, f, indent=2)

        # Count generated files
        file_count = 0
        if 'written' in locals():
            file_count = len(written)
        elif 'files' in locals() and files:
            file_count = len(files)

        result = {
            "product_id": product_id,
            "name": product_name,
            "description": description,
            "type": product_type,
            "tech_stack": tech_stack,
            "price": final_price,
            "pricing_model": pricing.get("pricing_model", "one-time"),
            "project_path": project_path,
            "files_generated": file_count,
            "preview_path": str(preview_path) if preview_path else None,
            "landing_page": str(landing_path),
            "has_logo": True,
            "brand_identity": brand_identity,
            "listing_copy": listing_copy,
            "market_strategy": market_strategy,
            "sales_pitch": sales_pitch,
            "pain_language": pain_language,
            "research": research,
            "features": features,
            "pages": pages,
        }

        self.memory.record_action("studio", "product_built_complete",
                                   f"Built {product_name} (ID: {product_id}) — ${final_price}",
                                   result)
        logger.info(f"✅  Product {product_name} (ID: {product_id}) built and ready for market!")
        logger.info(f"   Preview: {preview_path}")
        logger.info(f"   Sell:    jtech sell {product_id} --price {final_price}")

        return result

    def list_products(self) -> list[dict]:
        """List all built products."""
        return self.memory.list_products()

    def get_product(self, product_id: int) -> Optional[dict]:
        """Get a specific product."""
        return self.memory.get_product(product_id)
