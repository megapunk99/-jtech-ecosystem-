"""
Designer Department — UI/UX design for JTECH products.

Inspired by Lovable.dev's visual editing and v0's component generation:
- Live preview generation
- Visual edit mode (natural language → UI changes)
- Component manipulation
- Brand-consistent design systems
- Stunning landing pages with animations
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any, Optional

from jtech.llm import get_llm, ThinkingEffort

logger = logging.getLogger(__name__)


class Designer:
    """UI/UX Designer — visual design with live previews and visual editing."""

    def __init__(self):
        self.llm = get_llm()
        self.name = "Designer"

    def design_ui(self, product: dict) -> dict:
        """Design the UI layout with deep reasoning about UX."""
        result, reasoning = self.llm.chat_json_rich(
            [{"role": "user", "content": (
                f"Design the complete UI for this product:\n\n"
                f"Product: {product.get('name', product.get('product_name', 'Unknown'))}\n"
                f"Description: {product.get('description')}\n"
                f"Type: {product.get('product_type', 'Web App')}\n\n"
                f"Think step-by-step about:\n"
                f"1. What pages does this app need?\n"
                f"2. What components go on each page?\n"
                f"3. How does the user flow work?\n"
                f"4. What makes this feel premium?\n\n"
                f"Output JSON:\n"
                f"{{\n"
                f'  "pages": [{{"name": "Dashboard", "path": "/", "layout": "sidebar+main"}}],\n'
                f'  "components": [{{"name": "Header", "type": "navigation", "location": "top"}}],\n'
                f'  "color_scheme": {{"primary": "#hex", "secondary": "#hex", "accent": "#hex"}},\n'
                f'  "typography": {{"heading": "Inter", "body": "Inter"}},\n'
                f'  "user_flow": ["Action 1", "Action 2"],\n'
                f'  "design_principles": ["Clean", "Fast", "Responsive"],\n'
                f'  "animation_style": "subtle transitions with micro-interactions"\n'
                f"}}"
            )}],
            system_prompt="Design world-class UIs. Think Linear, Notion, Stripe quality.",
            thinking_effort=ThinkingEffort.DEEP,
        )
        return result or {"pages": [{"name": "Dashboard"}], "components": ["Header"]}

    def generate_live_preview(self, product: dict) -> str:
        """
        Generate a stunning live preview HTML page for the product.
        Like Lovable's preview pane — interactive, beautiful, responsive.
        """
        name = product.get("name", product.get("product_name", "Product"))
        desc = product.get("description", "")
        price = product.get("price", product.get("price_point", 9.99))
        features = product.get("features", [])
        scheme = product.get("color_scheme", {})

        prompt = (
            f"Create a STUNNING, fully interactive HTML preview page for this product.\n"
            f"This is a LIVE PREVIEW of the actual app interface.\n\n"
            f"Product: {name}\n"
            f"Description: {desc}\n"
            f"Price: ${price}\n"
            f"Features: {json.dumps(features)}\n\n"
            f"REQUIREMENTS:\n"
            f"- Complete, working HTML document\n"
            f"- Tailwind CSS via CDN\n"
            f"- Inter font from Google Fonts\n"
            f"- ALL interactive elements should have hover/active states\n"
            f"- Include: hero, features grid, pricing card, CTA, footer\n"
            f"- Smooth scroll, fade-in animations on scroll\n"
            f"- Premium, modern aesthetic (think Stripe/Linear)\n"
            f"- Responsive (mobile + desktop)\n"
            f"- Dark/light mode toggle in top-right corner\n"
            f"- Logo placeholder with the product name initials\n\n"
            f"Output ONLY the complete HTML code. Make it jaw-dropping."
        )

        html = self.llm.chat(
            [{"role": "user", "content": prompt}],
            system_prompt="You build the most beautiful HTML pages on the internet. World-class design.",
            thinking_effort=ThinkingEffort.DEEP,
            max_tokens=16384,
            temperature=0.4,
        ) or ""

        # Extract from markdown if needed
        if "```" in html:
            match = re.search(r'```(?:html)?\s*(.*?)```', html, re.DOTALL)
            if match:
                html = match.group(1).strip()

        return html

    def visual_edit(self, html: str, instruction: str) -> str:
        """
        Visual editing mode — like Lovable's click-to-edit.
        Takes current HTML and a natural language instruction, returns modified HTML.
        """
        prompt = (
            f"Modify this HTML according to the user's request.\n\n"
            f"USER REQUEST: {instruction}\n\n"
            f"CURRENT HTML:\n```html\n{html[:5000]}\n```\n\n"
            f"Rules:\n"
            f"- Keep Tailwind CSS via CDN\n"
            f"- Preserve all existing functionality\n"
            f"- Only change what the user asked for\n"
            f"- Output ONLY the complete modified HTML\n"
        )

        result = self.llm.chat(
            [{"role": "user", "content": prompt}],
            system_prompt="You modify HTML precisely. Output ONLY the complete HTML.",
            thinking_effort=ThinkingEffort.HIGH,
            max_tokens=16384,
        ) or html

        if "```" in result:
            match = re.search(r'```(?:html)?\s*(.*?)```', result, re.DOTALL)
            if match:
                result = match.group(1).strip()

        return result

    def generate_component_html(self, component_type: str, props: dict) -> str:
        """Generate a single UI component as HTML."""
        prompt = (
            f"Generate a beautiful {component_type} component with these properties:\n"
            f"{json.dumps(props, indent=2)}\n\n"
            f"Use Tailwind CSS. Make it look premium. Include hover/active states.\n"
            f"Output ONLY the HTML for this single component."
        )

        return self.llm.chat(
            [{"role": "user", "content": prompt}],
            system_prompt="You build stunning UI components. One component, perfect output.",
            max_tokens=2048,
        ) or f"<div class='p-4 bg-white rounded-lg'>{component_type}</div>"

    def generate_html_template(self, product: dict) -> str:
        """Generate a complete landing page (legacy wrapper around live preview)."""
        return self.generate_live_preview(product)

    def design_api_ux(self, product: dict) -> dict:
        """Design the API interface (unchanged — already solid)."""
        result, reasoning = self.llm.chat_json_rich(
            [{"role": "user", "content": (
                f"Design the API interface for:\n"
                f"Product: {product.get('name', 'Unknown')}\n\n"
                f"Output JSON with: endpoints, auth, response_format, "
                f"error_handling, sdk_sketch"
            )}],
            system_prompt="Design APIs developers love. Think Stripe quality.",
        )
        return result or {"endpoints": ["GET /api/v1/resource"], "auth": "API key"}


class BrandManager:
    """Brand Manager — company and product branding with visual identity."""

    def __init__(self):
        self.llm = get_llm()
        self.name = "BrandManager"

    def create_brand_identity(self, company_name: str = "JTECH") -> dict:
        """Create a brand identity with deep thinking about positioning."""
        result, reasoning = self.llm.chat_json_rich(
            [{"role": "user", "content": (
                f"Create a premium brand identity for {company_name}:\n\n"
                f"Think about:\n"
                f"1. What emotions should this brand evoke?\n"
                f"2. Who is the target audience?\n"
                f"3. What makes this brand different?\n\n"
                f"Output JSON:\n"
                f"{{\n"
                f'  "colors": {{"primary": "#hex", "secondary": "#hex", '
                f'"accent": "#hex", "dark": "#hex", "light": "#hex"}},\n'
                f'  "brand_voice": ["adjective1", "adjective2", "adjective3"],\n'
                f'  "tagline": "Short memorable tagline",\n'
                f'  "design_principles": ["Principle 1", "Principle 2"],\n'
                f'  "logo_concept": "Describe a simple, iconic logo",\n'
                f'  "brand_personality": "Describe how the brand feels",\n'
                f'  "target_vibe": "Modern, premium, trustworthy"\n'
                f"}}"
            )}],
            system_prompt="Create brand identities for billion-dollar companies.",
            thinking_effort=ThinkingEffort.HIGH,
        )
        return result or {
            "colors": {"primary": "#3b82f6", "secondary": "#8b5cf6", "accent": "#06b6d4"},
            "tagline": "Build. Ship. Grow.",
        }

    def generate_svg_logo(self, brand: dict) -> str:
        """Generate a beautiful SVG logo."""
        prompt = (
            f"Create a beautiful, iconic SVG logo.\n\n"
            f"Brand colors: {brand.get('colors', {})}\n"
            f"Tagline: {brand.get('tagline', 'Build. Ship. Grow.')}\n"
            f"Logo concept: {brand.get('logo_concept', 'Abstract mark')}\n"
            f"Brand personality: {brand.get('brand_personality', 'Modern')}\n\n"
            f"Rules:\n"
            f"- ONLY output raw SVG code. No markdown, no explanations.\n"
            f"- Simple, memorable, scalable (viewBox)\n"
            f"- Works on light and dark backgrounds\n"
            f"- Professional, modern aesthetic\n"
            f"- Under 2KB if possible\n"
            f"- Use the brand colors\n"
            f"- The SVG should work standalone as a favicon\n"
        )

        result = self.llm.chat(
            [{"role": "user", "content": prompt}],
            system_prompt="You create iconic SVG logos. Raw SVG only. No markdown fences.",
            thinking_effort=ThinkingEffort.HIGH,
            temperature=0.3,
            max_tokens=2048,
        ) or '<svg viewBox="0 0 100 100"><rect x="20" y="20" width="60" height="60" rx="12" fill="#3b82f6"/><text x="50" y="65" text-anchor="middle" fill="white" font-size="36" font-weight="bold">J</text></svg>'

        # Strip markdown fences if present
        result = re.sub(r'```(?:svg)?\s*', '', result).strip()
        result = re.sub(r'\s*```', '', result).strip()

        return result
