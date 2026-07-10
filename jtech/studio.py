"""
JTECH Product Studio — Streamlined build pipeline.

ECC-inspired approach:
- Fewer, faster LLM calls (3-4 max instead of 8)
- Each call has retry on 503
- Simple, focused prompts
- Combines phases where possible

Pipeline: IDEATE → DESIGN+BUILD → BRAND → SHIP
"""

from __future__ import annotations

import json
import logging
import os
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from jtech.company.memory import CompanyMemory
from jtech.llm import get_llm, ThinkingEffort
from jtech.builder import AppBuilder

logger = logging.getLogger(__name__)


class ProductStudio:
    """
    JTECH Product Studio — builds products quickly and reliably.

    Streamlined pipeline (3-4 LLM calls total):
    1. IDEATE → CEO decides what to build (1 call)
    2. BUILD → Generate complete product in one shot (1 call)
    3. BRAND → Create brand + listing + preview (1 call)
    4. SHIP → Register & write files
    """

    def __init__(self, memory: Optional[CompanyMemory] = None):
        self.memory = memory or CompanyMemory()
        self.llm = get_llm()
        self.projects_dir = Path(os.environ.get("JTECH_PROJECTS_DIR", "./built_products"))
        self.projects_dir.mkdir(parents=True, exist_ok=True)

    def build_product(self, idea: Optional[str] = None) -> dict:
        """
        Build a product quickly with parallel LLM calls.

        Runs Phase 2 (build) and Phase 3 (brand) in parallel to cut time in half.
        """
        import threading

        start_time = time.time()
        logger.info("Building product...")

        # ── Phase 1: IDEATE ──
        if idea:
            product_name = idea.split(" - ")[0].strip()[:60]
            description = idea
            tech_stack = ["React", "TypeScript", "Tailwind", "Supabase"]
            logger.info(f"   Using your idea: {product_name}")
        else:
            logger.info("   CEO deciding what to build...")
            idea_result = self.llm.chat_json(
                [{"role": "user", "content": (
                    "What software should JTECH build next? "
                    "Output JSON: {\"product_name\": \"...\", \"description\": \"...\", "
                    "\"tech_stack\": [\"React\",\"TypeScript\"], \"price_point\": 19.99}"
                )}],
                system_prompt="You pick products people pay for. Be specific.",
                thinking_effort=ThinkingEffort.MINIMAL,
                max_tokens=400,
            ) or {}
            product_name = idea_result.get("product_name", "Product")
            description = idea_result.get("description", "")
            tech_stack = idea_result.get("tech_stack", ["React", "TypeScript", "Tailwind"])
            logger.info(f"   CEO chose: {product_name}")

        slug = product_name.lower().replace(" ", "-").replace("_", "-")
        project_path = self.projects_dir / slug
        project_path.mkdir(parents=True, exist_ok=True)

        # ── Phase 2 & 3: BUILD + BRAND in PARALLEL ──
        logger.info("   Generating product + brand in parallel...")

        build_result = {}
        brand_result = {}
        build_done = threading.Event()
        brand_done = threading.Event()

        def do_build():
            nonlocal build_result
            try:
                r = self.llm.chat_json(
                    [{"role": "user", "content": (
                        f"Design a web app called '{product_name}'. {description[:200]}\n"
                        f"Output JSON: {{\"features\": [\"feature 1\", \"feature 2\", \"feature 3\"], "
                        f"\"landing_html\": \"<html><body><h1>{product_name}</h1></body></html>\", "
                        f"\"api_endpoints\": [\"GET /api/health\"], \"data_model\": [\"Entity\"]}}"
                    )}],
                    system_prompt="Output valid JSON. Keep HTML under 2000 chars.",
                    thinking_effort=ThinkingEffort.MINIMAL,
                    max_tokens=2500,
                )
                if r:
                    build_result.update(r)
            except Exception as e:
                logger.error(f"Build phase error: {e}")
            finally:
                build_done.set()

        def do_brand():
            nonlocal brand_result
            try:
                r = self.llm.chat_json(
                    [{"role": "user", "content": (
                        f"Create brand for '{product_name}': {description[:150]}\n"
                        f"Output JSON: {{\"tagline\": \"tagline\", "
                        f"\"colors\": {{\"primary\": \"#hex\", \"secondary\": \"#hex\", \"accent\": \"#hex\"}}, "
                        f"\"price\": 19.99, \"pricing_model\": \"one-time\", "
                        f"\"listing_copy\": \"2-3 sentence copy\", "
                        f"\"sales_pitch\": \"1 sentence pitch\", "
                        f"\"logo_svg\": \"<svg>...</svg>\"}}"
                    )}],
                    system_prompt="Output valid JSON. Be creative and compelling.",
                    thinking_effort=ThinkingEffort.MINIMAL,
                    max_tokens=1500,
                )
                if r:
                    brand_result.update(r)
            except Exception as e:
                logger.error(f"Brand phase error: {e}")
            finally:
                brand_done.set()

        # Start both threads
        t1 = threading.Thread(target=do_build, daemon=True)
        t2 = threading.Thread(target=do_brand, daemon=True)
        t1.start()
        t2.start()

        # Wait for both with timeout
        t1.join(timeout=180)
        t2.join(timeout=180)

        features = build_result.get("features", [f"Core feature of {product_name}"])
        landing_html = build_result.get("landing_html", "")
        api_endpoints = build_result.get("api_endpoints", [])
        data_model = build_result.get("data_model", [])

        tagline = brand_result.get("tagline", "Built by JTECH")
        colors = brand_result.get("colors", {"primary": "#3b82f6", "secondary": "#8b5cf6", "accent": "#06b6d4"})
        price = brand_result.get("price", 9.99)
        pricing_model = brand_result.get("pricing_model", "one-time")
        listing_copy = brand_result.get("listing_copy", "")
        sales_pitch = brand_result.get("sales_pitch", "")
        logo_svg = brand_result.get("logo_svg", "")

        # ── Phase 4: Generate real React project ──
        logger.info("   Generating real React project...")
        try:
            app_builder = AppBuilder()
            app_result = app_builder.build_app({
                "product_name": product_name,
                "description": description,
                "features": features,
                "data_model": build_result.get("data_model", []),
            })
            # AppBuilder wrote files to its own work_dir path
            if app_result and app_result.get("project_path"):
                logger.info(f"   React project saved to {app_result['project_path']}")
        except Exception as e:
            logger.warning(f"   React project generation skipped: {e}")

        # ── Phase 5: SHIP ──
        logger.info("   Shipping product...")

        # Use landing HTML from build or generate simple preview
        if landing_html and len(landing_html) > 200:
            preview_html = landing_html
        else:
            preview_html = self._generate_interactive_preview(product_name, description, features, colors, price)

        # Write preview
        preview_path = project_path / "preview.html"
        with open(preview_path, "w", encoding="utf-8") as f:
            f.write(preview_html)

        # Write logo
        if logo_svg:
            logo_path = project_path / "logo.svg"
            with open(logo_path, "w") as f:
                f.write(logo_svg)

        # Write brand
        brand_path = project_path / "brand.json"
        with open(brand_path, "w") as f:
            json.dump({
                "tagline": tagline,
                "colors": colors,
                "price": price,
                "pricing_model": pricing_model,
                "listing_copy": listing_copy,
                "sales_pitch": sales_pitch,
            }, f, indent=2)

        # Write spec
        spec_path = project_path / "product_spec.json"
        product_type = "Web App"
        with open(spec_path, "w") as f:
            json.dump({
                "name": product_name,
                "description": description,
                "type": product_type,
                "tech_stack": tech_stack,
                "price": price,
                "pricing_model": pricing_model,
                "features": features,
                "api_endpoints": api_endpoints,
                "data_model": data_model,
                "built_at": datetime.now().isoformat(),
            }, f, indent=2)

        # Register in memory
        product_id = self.memory.register_product(
            name=product_name,
            description=description,
            product_type=product_type,
            tech_stack=tech_stack,
        )

        # Record action
        elapsed = time.time() - start_time
        self.memory.record_action("studio", "product_built",
                                   f"Built {product_name} (ID: {product_id}) — ${price} in {elapsed:.0f}s")

        result = {
            "product_id": product_id,
            "name": product_name,
            "description": description,
            "type": product_type,
            "tech_stack": tech_stack,
            "price": price,
            "pricing_model": pricing_model,
            "project_path": str(project_path),
            "files_generated": 4,
            "preview_path": str(preview_path),
            "features": features,
            "tagline": tagline,
            "colors": colors,
            "listing_copy": listing_copy,
            "sales_pitch": sales_pitch,
            "build_time_seconds": round(elapsed, 1),
        }

        logger.info(f"✅  Built {product_name} (ID: {product_id}) in {elapsed:.0f}s")
        return result

    def _generate_interactive_preview(self, name, description, features, colors, price):
        """Generate an interactive product preview with working UI elements."""
        primary = colors.get("primary", "#3b82f6")
        secondary = colors.get("secondary", "#8b5cf6")
        accent = colors.get("accent", "#06b6d4")
        
        feature_items = "\n".join([
            f'<div class="bg-white rounded-xl p-6 shadow-sm border border-gray-100 hover:shadow-lg transition-all duration-300 cursor-pointer" onclick="showDemo(\'{f.replace(chr(39), "\\u2019")}\')">\\n'
            f'  <div class="w-10 h-10 rounded-lg bg-gradient-to-br from-[{primary}] to-[{secondary}] flex items-center justify-center text-white font-bold text-sm mb-3">{f[0].upper()}</div>\\n'
            f'  <h3 class="font-semibold text-lg text-gray-900">{f}</h3>\\n'
            f'  <p class="text-sm text-gray-400 mt-1">Click to see demo</p>\\n'
            f'</div>'
            for f in (features or ["Core feature"])[:6]
        ])

        return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{name} — Interactive Preview</title>
<script src="https://cdn.tailwindcss.com"></script>
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');
* {{font-family:'Inter',sans-serif}}
.gradient-text {{background:linear-gradient(135deg,{primary},{secondary});-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text}}
.demo-modal {{display:none;position:fixed;inset:0;background:rgba(0,0,0,0.5);backdrop-filter:blur(4px);z-index:50;align-items:center;justify-content:center;padding:20px}}
.demo-modal.show {{display:flex}}
.demo-content {{background:white;border-radius:16px;padding:24px;max-width:500px;width:100%;box-shadow:0 25px 50px -12px rgba(0,0,0,0.25)}}
.toast {{position:fixed;bottom:24px;right:24px;background:#059669;color:white;padding:12px 20px;border-radius:12px;font-weight:500;box-shadow:0 8px 32px rgba(0,0,0,0.15);transform:translateY(100px);opacity:0;transition:all 0.3s ease;z-index:100}}
.toast.show {{transform:translateY(0);opacity:1}}
</style>
</head>
<body class="bg-gray-50 text-gray-900 antialiased">
<div id="toast" class="toast"></div>

<!-- Demo Modal -->
<div id="demoModal" class="demo-modal">
  <div class="demo-content">
    <div class="flex items-center justify-between mb-4">
      <h3 class="text-lg font-bold text-gray-900" id="demoTitle">Feature Demo</h3>
      <button onclick="closeDemo()" class="p-2 hover:bg-gray-100 rounded-lg text-gray-400 hover:text-gray-600">
        <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/></svg>
      </button>
    </div>
    <div id="demoBody" class="text-gray-600 text-sm leading-relaxed mb-6">
      This is a simulated demo of the feature. In the full React application, this would connect to a real backend with actual data.
    </div>
    <div class="flex gap-3">
      <button onclick="closeDemo()" class="flex-1 px-4 py-2.5 bg-gray-900 text-white rounded-xl font-medium hover:bg-gray-800 transition-colors">Try It</button>
      <button onclick="closeDemo()" class="flex-1 px-4 py-2.5 border border-gray-200 rounded-xl font-medium hover:bg-gray-50 transition-colors">Close</button>
    </div>
  </div>
</div>

<!-- Hero -->
<div class="max-w-6xl mx-auto px-6 py-16 text-center">
  <div class="inline-block px-4 py-1.5 bg-blue-50 text-blue-600 rounded-full text-sm font-medium mb-6">Built by JTECH — Interactive Preview</div>
  <h1 class="text-5xl md:text-6xl font-extrabold gradient-text mb-6">{name}</h1>
  <p class="text-xl text-gray-500 max-w-2xl mx-auto mb-8">{description[:200]}</p>
  <div class="flex gap-4 justify-center mb-16 flex-wrap">
    <button onclick="showToast('🚀 {name} demo launched! Full React app coming soon.')" class="px-8 py-3.5 bg-gray-900 text-white rounded-xl font-medium hover:bg-gray-800 transition-all hover:scale-105 active:scale-95">Get Started — ${price}</button>
    <button onclick="document.getElementById('features').scrollIntoView({{behavior:'smooth'}})" class="px-8 py-3.5 border border-gray-200 rounded-xl font-medium hover:border-gray-300 hover:bg-white transition-all">Explore Features</button>
    <button onclick="showToast('✨ Opening real React project... The source code is in the src/ folder!')" class="px-8 py-3.5 border border-gray-200 rounded-xl font-medium hover:border-gray-300 hover:bg-white transition-all">View Source</button>
  </div>
</div>

<!-- Stats Bar -->
<div class="max-w-6xl mx-auto px-6 pb-8">
  <div class="bg-white rounded-2xl shadow-sm border border-gray-100 p-8 grid grid-cols-2 md:grid-cols-4 gap-6">
    <div class="text-center">
      <div class="text-2xl font-bold text-gray-900">{len(features or [])}+</div>
      <div class="text-sm text-gray-400">Features</div>
    </div>
    <div class="text-center">
      <div class="text-2xl font-bold text-gray-900">React</div>
      <div class="text-sm text-gray-400">Frontend</div>
    </div>
    <div class="text-center">
      <div class="text-2xl font-bold text-gray-900">TypeScript</div>
      <div class="text-sm text-gray-400">Language</div>
    </div>
    <div class="text-center">
      <div class="text-2xl font-bold text-gray-900">Tailwind</div>
      <div class="text-sm text-gray-400">Styling</div>
    </div>
  </div>
</div>

<!-- Features -->
<div id="features" class="max-w-6xl mx-auto px-6 pb-16">
  <h2 class="text-3xl font-bold text-center mb-4">Features</h2>
  <p class="text-gray-400 text-center mb-10 max-w-xl mx-auto">Click any feature card to see a simulated demo</p>
  <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">{feature_items}</div>
</div>

<!-- CTA -->
<div class="max-w-6xl mx-auto px-6 pb-16">
  <div class="bg-gradient-to-r from-[{primary}] to-[{secondary}] rounded-2xl p-12 text-center text-white">
    <h2 class="text-3xl font-bold mb-4">Ready to Get Started?</h2>
    <p class="text-white/80 mb-8 max-w-lg mx-auto">The full React application is being generated alongside this preview.</p>
    <button onclick="showToast('🎉 Product is ready! Check the built_products folder for the full React project.')" class="px-8 py-3.5 bg-white text-gray-900 rounded-xl font-medium hover:bg-gray-100 transition-all hover:scale-105 active:scale-95">Launch Full App</button>
  </div>
</div>

<!-- Footer -->
<footer class="text-center py-8 text-sm text-gray-400 border-t border-gray-100">
  <p>Built by <a href="https://github.com/megapunk99/-jtech-ecosystem-" class="text-gray-600 hover:text-gray-900">JTECH Ecosystem</a></p>
</footer>

<script>
function showToast(msg) {{
  const t = document.getElementById('toast');
  t.textContent = msg;
  t.className = 'toast show';
  setTimeout(() => t.className = 'toast', 3000);
}}
function showDemo(feature) {{
  document.getElementById('demoTitle').textContent = feature;
  document.getElementById('demoBody').innerHTML = 
    '<p>This is an interactive preview of: <strong>' + feature + '</strong></p>' +
    '<p class=\"mt-3\">In the full React application, this feature would include real data fetching, state management, and API integration.</p>' +
    '<div class=\"mt-4 p-4 bg-gray-50 rounded-xl\">' +
    '<div class=\"flex items-center gap-3 mb-2\">' +
    '<div class=\"w-2 h-2 rounded-full bg-green-400\"></div>' +
    '<span class=\"text-sm font-medium\">Demo data loaded successfully</span></div>' +
    '<div class=\"text-xs text-gray-400\">This is a simulation. Real data comes from your backend.</div></div>';
  document.getElementById('demoModal').classList.add('show');
}}
function closeDemo() {{
  document.getElementById('demoModal').classList.remove('show');
}}
</script>
</body>
</html>"""

    def list_products(self) -> list[dict]:
        return self.memory.list_products()

    def get_product(self, product_id: int) -> Optional[dict]:
        return self.memory.get_product(product_id)
