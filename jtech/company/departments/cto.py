"""
CTO Department — Technical leadership for JTECH.

The CTO makes technology decisions, designs architecture, selects stacks,
and ensures everything JTECH builds is technically sound and scalable.
"""

from __future__ import annotations

import logging
from typing import Any, Optional

from jtech.llm import get_llm

logger = logging.getLogger(__name__)


class CTO:
    """Chief Technology Officer — technical direction and architecture."""

    def __init__(self):
        self.llm = get_llm()
        self.name = "CTO"

    def design_architecture(self, product_idea: dict) -> dict:
        """Design the architecture for a new product."""
        prompt = (
            f"You are the CTO of JTECH. Design the architecture for this product:\n\n"
            f"Product: {product_idea.get('product_name', 'Unknown')}\n"
            f"Description: {product_idea.get('description', 'N/A')}\n"
            f"Tech Stack: {product_idea.get('tech_stack', ['Python'])}\n\n"
            f"Provide:\n"
            f"1. SYSTEM ARCHITECTURE: Key components and how they interact\n"
            f"2. DATA MODEL: Core data structures\n"
            f"3. API DESIGN: Endpoints or interfaces needed\n"
            f"4. TECHNOLOGY CHOICES: Specific libraries and tools\n"
            f"5. SECURITY CONSIDERATIONS: What to protect\n"
            f"6. DEPLOYMENT STRATEGY: How to ship it\n\n"
            f"Output valid JSON only."
        )

        result = self.llm.chat_json(
            [{"role": "user", "content": prompt}],
            system_prompt="You are a hands-on CTO who designs practical, buildable architectures."
        )
        return result or {"architecture": "Simple client-server", "tech_stack": ["Python"]}

    def tech_stack_review(self, techs: list[str]) -> dict:
        """Review and validate technology choices."""
        prompt = (
            f"Review these technology choices for a JTECH product:\n"
            f"Stack: {', '.join(techs)}\n\n"
            f"Assess:\n"
            f"1. Is this the BEST choice for startup speed?\n"
            f"2. Any lower-cost or faster alternatives?\n"
            f"3. What's the learning curve?\n"
            f"4. Deployment complexity?\n\nOutput valid JSON with keys: verdict, alternatives, simplicity_score (1-10), notes"
        )

        result = self.llm.chat_json(
            [{"role": "user", "content": prompt}],
            system_prompt="You are a pragmatic CTO who values shipping speed above all."
        )
        return result or {"verdict": "acceptable", "simplicity_score": 7}

    def code_quality_guidelines(self, tech_stack: list[str]) -> list[str]:
        """Generate code quality guidelines for a given tech stack."""
        prompt = (
            f"Generate 5-7 code quality guidelines for building with:\n"
            f"{', '.join(tech_stack)}\n\n"
            f"Focus on: file structure, naming, error handling, configuration management, testing.\n"
            f"Output as a JSON array of strings."
        )

        result = self.llm.chat(
            [{"role": "user", "content": prompt}],
            system_prompt="You output valid JSON arrays only."
        )
        if result:
            try:
                import json
                return json.loads(result)
            except json.JSONDecodeError:
                pass
        return [
            "Keep files under 300 lines",
            "Use environment variables for config",
            "Handle errors gracefully with try/except",
            "Write one test per endpoint",
            "Use type hints everywhere",
        ]


class HeadOfProduct:
    """Head of Product — market research and product strategy."""

    def __init__(self):
        self.llm = get_llm()
        self.name = "HeadOfProduct"

    def market_research(self, product_name: str, description: str) -> dict:
        """Research market fit for a product idea."""
        prompt = (
            f"Conduct market research for this product:\n\n"
            f"Product: {product_name}\n"
            f"Description: {description}\n\n"
            f"Analyze:\n"
            f"1. TARGET MARKET: How big is it? Who are the buyers?\n"
            f"2. COMPETITION: Who else is doing this?\n"
            f"3. PRICING: What's the optimal price point?\n"
            f"4. DEMAND SIGNAL: How do we know people want this?\n"
            f"5. GO-TO-MARKET: How do we reach customers?\n"
            f"6. RISK: What could fail?\n\n"
            f"Output valid JSON with keys: market_size, competition_analysis, "
            f"recommended_price, demand_indicators, go_to_market, risk_assessment"
        )

        return self.llm.chat_json(
            [{"role": "user", "content": prompt}],
            system_prompt="You are a sharp product strategist who finds revenue opportunities."
        ) or {
            "market_size": "Unknown",
            "competition_analysis": "Needs research",
            "recommended_price": 9.99,
        }

    def validate_idea(self, idea: str) -> dict:
        """Validate whether an idea is worth building."""
        prompt = (
            f"Validate this product idea for JTECH:\n\n"
            f"\"{idea}\"\n\n"
            f"Score (1-10) on:\n"
            f"- BUILD SPEED: Can we build this fast?\n"
            f"- REVENUE POTENTIAL: Will people pay?\n"
            f"- UNIQUENESS: Is this differentiated?\n"
            f"- FIT: Does this match JTECH's capabilities?\n\n"
            f"Output valid JSON with scores and a build/no-build recommendation."
        )

        return self.llm.chat_json(
            [{"role": "user", "content": prompt}],
            system_prompt="You validate ideas ruthlessly. Only build what sells."
        ) or {"build_score": 7, "recommendation": "build"}
