"""
CMO Department — Sales and marketing for JTECH products.

Inspired by Claude's approach to marketing:
- Structured XML prompting for brand consistency
- Pain language extraction from customer feedback
- Workflow-oriented copy (not just generation)
- Multi-channel strategy
- Storytelling and persuasion frameworks
"""

from __future__ import annotations

import json
import logging
from typing import Any, Optional

from jtech.llm import get_llm, ThinkingEffort, Personality

logger = logging.getLogger(__name__)


class CMO:
    """Chief Marketing Officer — structured marketing with Claude-style workflows."""

    def __init__(self):
        self.llm = get_llm()
        self.name = "CMO"

    def go_to_market(self, product: dict) -> dict:
        """Create a comprehensive go-to-market strategy with deep analysis."""
        prompt = (
            f"<product_brief>\n"
            f"  Name: {product.get('name')}\n"
            f"  Description: {product.get('description')}\n"
            f"  Price: ${product.get('price', 9.99)}\n"
            f"  Type: {product.get('product_type', 'SaaS')}\n"
            f"</product_brief>\n\n"
            f"<analysis_instructions>\n"
            f"Analyze the market position and create a go-to-market strategy:\n\n"
            f"1. LAUNCH STRATEGY: The specific steps for a successful launch\n"
            f"2. TARGET AUDIENCE: Who exactly will buy this?\n"
            f"3. CHANNEL MIX: Where to reach them (social, email, communities, ads)\n"
            f"4. MESSAGING FRAMEWORK: Core message, value prop, proof points\n"
            f"5. PRICING STRATEGY: Is the price right? What's the perceived value?\n"
            f"6. CONVERSION FUNNEL: How visitors become buyers\n"
            f"7. COMPETITIVE POSITIONING: How we win against alternatives\n"
            f"</analysis_instructions>\n\n"
            f"Output JSON with keys: launch_strategy, target_audience, channels, "
            f"messaging_framework, pricing_strategy, conversion_funnel, competitive_positioning"
        )

        result, reasoning = self.llm.chat_json_rich(
            [{"role": "user", "content": prompt}],
            system_prompt="You are a world-class CMO who launches products people love.",
            thinking_effort=ThinkingEffort.DEEP,
        )
        return result or {
            "launch_strategy": "Direct outreach + social media",
            "channels": ["Social media", "Direct"],
            "recommended_price": product.get("price", 9.99),
        }

    def create_listing(self, product: dict) -> str:
        """
        Create compelling product copy using Claude-style structured writing.

        Uses a storytelling framework: Problem → Solution → Proof → CTA
        """
        name = product.get("name", "Product")
        desc = product.get("description", "")
        price = product.get("price", 9.99)
        features = product.get("features", [])

        prompt = (
            f"<product_brief>\n"
            f"  Name: {name}\n"
            f"  Description: {desc}\n"
            f"  Price: ${price}\n"
            f"  Features: {json.dumps(features)}\n"
            f"</product_brief>\n\n"
            f"<writing_framework>\n"
            f"Write a compelling product listing using this structure:\n\n"
            f"1. PROBLEM AGITATION (2-3 sentences): Describe the pain your target customer feels.\n"
            f"   Use the language they use internally. Make them feel understood.\n\n"
            f"2. SOLUTION REVELATION (2-3 sentences): Introduce {name} as the obvious answer.\n"
            f"   Not features — benefits. How does their life change?\n\n"
            f"3. PROOF POINTS (3-4 bullet points): Specific capabilities that back up the promise.\n"
            f"   Each bullet: one clear benefit, not a feature list.\n\n"
            f"4. OBJECTION HANDLING (1 sentence): Address the #1 reason someone might not buy.\n\n"
            f"5. CALL TO ACTION (1 sentence): Clear, low-friction next step.\n"
            f"</writing_framework>\n\n"
            f"Output the complete listing copy. Use plain text, no markdown.\n"
            f"Tone: confident, empathetic, premium. No hype. Just value."
        )

        return self.llm.chat(
            [{"role": "user", "content": prompt}],
            system_prompt="You write product copy that converts. Clear. Compelling. Human.",
            thinking_effort=ThinkingEffort.HIGH,
            max_tokens=2048,
        ) or f"{name} — The solution you've been looking for."

    def price_product(self, product: dict, research: Optional[dict] = None) -> dict:
        """Determine optimal pricing with value-based analysis."""
        prompt = (
            f"<product_brief>\n"
            f"  Product: {product.get('name', 'Unknown')}\n"
            f"  Type: {product.get('product_type', 'SaaS')}\n"
            f"  Target: {research.get('target_audience', 'Developers/Founders') if research else 'Target market'}\n"
            f"</product_brief>\n\n"
            f"<pricing_analysis>\n"
            f"Determine the optimal price by considering:\n"
            f"1. VALUE-BASED: What is this worth to the customer? (Time saved, money saved)\n"
            f"2. COMPETITIVE: What do comparable solutions charge?\n"
            f"3. PSYCHOLOGICAL: What price point feels like a no-brainer?\n"
            f"4. REVENUE OPTIMAL: What maximizes total revenue?\n"
            f"</pricing_analysis>\n\n"
            f"Output JSON with: recommended_price, pricing_model (one-time/subscription/tiered), "
            f"justification, annual_discount_pct, price_anchor (the 'was' price for context)"
        )

        result, reasoning = self.llm.chat_json_rich(
            [{"role": "user", "content": prompt}],
            system_prompt="You maximize revenue through strategic pricing.",
            thinking_effort=ThinkingEffort.HIGH,
        )
        return result or {"recommended_price": product.get("price", 9.99), "pricing_model": "one-time"}

    def extract_pain_language(self, product: dict) -> list[str]:
        """
        Claude-style: Extract the language customers use to describe their problems.
        This helps JTECH write copy that resonates authentically.
        """
        prompt = (
            f"<product_brief>\n"
            f"  Product: {product.get('name')}\n"
            f"  Description: {product.get('description')}\n"
            f"</product_brief>\n\n"
            f"<task>\n"
            f"Imagine you've interviewed 20 potential customers about their problems.\n"
            f"Extract the RAW, AUTHENTIC phrases they would use to describe their pain.\n"
            f"Avoid marketing-speak. Use their words.\n\n"
            f"Output a JSON object with a 'phrases' array of 8-12 short phrases (under 15 words each).\n"
            f"Example: {{\"phrases\": [\"I waste hours on this every week\", \n"
            f"          \"There's no simple way to track this\",\n"
            f"          \"I keep losing data between tools\"]}}\n"
            f"</task>"
        )

        result = self.llm.chat_json(
            [{"role": "user", "content": prompt}],
            system_prompt="You extract authentic customer language. No jargon. Real talk.",
            thinking_effort=ThinkingEffort.HIGH,
        )
        if result and "phrases" in result:
            return result["phrases"]
        return ["I wish this was easier"]

    def generate_ad_copy(self, product: dict, platform: str = "twitter") -> list[str]:
        """
        Generate platform-specific ad copy.
        Like Claude's workflow-oriented copy generation.
        """
        pain = self.extract_pain_language(product)
        prompt = (
            f"<product_brief>\n"
            f"  Product: {product.get('name')}\n"
            f"  Description: {product.get('description')}\n"
            f"  Price: ${product.get('price', 9.99)}\n"
            f"</product_brief>\n\n"
            f"<customer_pain_points>\n"
            f"{json.dumps(pain[:5], indent=2)}\n"
            f"</customer_pain_points>\n\n"
            f"<task>\n"
            f"Write 5 ad variations for {platform}.\n"
            f"Each ad should:\n"
            f"- Hook with the pain point\n"
            f"- Present the solution\n"
            f"- End with a clear CTA\n"
            f"- Stay within {platform}'s character limits\n\n"
            f"Output a JSON array of strings."
            f"</task>"
        )

        result = self.llm.chat_json(
            [{"role": "user", "content": prompt}],
            system_prompt="You write ads that stop the scroll and drive clicks.",
            thinking_effort=ThinkingEffort.HIGH,
        )
        if isinstance(result, list):
            return result
        return [f"Stop wasting time. Try {product.get('name')} today."]
