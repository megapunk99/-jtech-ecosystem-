"""
CEO Department — Strategic leadership with DeepSeek-style reasoning and Grok personality.

The CEO now:
- Thinks deeply before making decisions (DeepSeek reasoning traces)
- Has personality in communications (Grok-inspired)
- Self-corrects and refines strategies
- Makes bold, specific calls
"""

from __future__ import annotations

import json
import logging
from typing import Any, Optional

from jtech.llm import get_llm, ThinkingEffort, Personality, ReasoningTrace

logger = logging.getLogger(__name__)


class CEO:
    """Chief Executive Officer — strategic leadership with deep reasoning."""

    def __init__(self):
        self.llm = get_llm()
        self.name = "CEO"

    def strategic_review(self, company_status: dict) -> dict:
        """
        Review company status with deep reasoning before making calls.

        DeepSeek-style: thinks step-by-step, challenges own assumptions,
        then delivers a clear strategic direction with Grok-style candor.
        """
        result, reasoning = self.llm.chat_json_rich(
            [{"role": "user", "content": (
                f"<company_status>\n"
                f"  Products built: {company_status.get('products_built', 0)}\n"
                f"  Total revenue: ${company_status.get('total_revenue', 0):.2f}\n"
                f"  Total sales: {company_status.get('total_sales', 0)}\n"
                f"  Actions taken: {company_status.get('actions_taken', 0)}\n"
                f"</company_status>\n\n"
                f"<analysis_required>\n"
                f"Analyze the company's current position and provide strategic direction.\n\n"
                f"First, think step-by-step:\n"
                f"1. Where are we now? (honest assessment)\n"
                f"2. What's working? What's not?\n"
                f"3. What's the biggest opportunity right now?\n"
                f"4. What's the biggest risk?\n"
                f"5. What should we do about it?\n\n"
                f"Then provide:\n"
                f"- strategic_direction: What to focus on RIGHT NOW (bold, specific)\n"
                f"- product_vision: What products we should build\n"
                f"- revenue_target: The next milestone (specific number)\n"
                f"- key_risks: What could derail us (be brutally honest)\n"
                f"- ceo_message: A message to the team (bold, inspiring, real)\n"
                f"- hard_truth: One thing nobody wants to say but needs to be said\n"
                f"</analysis_required>\n\n"
                f"Output valid JSON."
            )}],
            system_prompt=(
                "You are a world-class CEO. You think deeply, make bold calls, "
                "and tell the truth even when it's uncomfortable. Be specific. Be decisive."
            ),
            thinking_effort=ThinkingEffort.DEEP,
        )

        if reasoning.steps:
            logger.info(f"   🤔 CEO reasoned through {len(reasoning.steps)} steps "
                        f"with {len(reasoning.self_corrections)} self-corrections")

        return result or {
            "strategic_direction": "Build and ship products",
            "product_vision": "AI-powered SaaS tools",
            "revenue_target": "First $100",
            "key_risks": ["Unknown"],
            "ceo_message": "Let's build.",
            "hard_truth": "We need to ship faster.",
        }

    def decide_what_to_build(self, market_research: Optional[dict] = None) -> dict:
        """
        Decide what product to build next with deep reasoning.

        The CEO thinks about market demand, build feasibility,
        revenue potential, and strategic fit before deciding.
        """
        result, reasoning = self.llm.chat_json_rich(
            [{"role": "user", "content": (
                "Decide what software product JTECH should build next.\n\n"
                "Think step-by-step:\n"
                "1. What's hot in the market right now? (AI tools, SaaS, developer tools)\n"
                "2. What can we build fast that provides real value?\n"
                "3. What has the best revenue-to-effort ratio?\n"
                "4. What fits our capabilities? (AI, APIs, web apps)\n"
                "5. What would differentiate us?\n\n"
                "After thinking, be specific. Not 'an AI tool' — WHAT AI tool?\n"
                "Name the product. Describe exactly what it does. Price it.\n\n"
                "Output JSON:\n"
                "{\n"
                '  "product_name": "Specific Product Name",\n'
                '  "description": "What it does in one sentence",\n'
                '  "problem": "What problem it solves",\n'
                '  "target_audience": "Who will buy it",\n'
                '  "tech_stack": ["Python", "FastAPI", "React", "Supabase"],\n'
                '  "estimated_build_time": "X days",\n'
                '  "monetization": "How we charge",\n'
                '  "price_point": 19.99,\n'
                '  "why_now": "Why this is the right time to build this"\n'
                "}"
            )}],
            system_prompt=(
                "You are a product visionary CEO who builds products people pay for. "
                "Be specific. 'AI tool' is not an answer. 'A GitHub bot that auto-triage issues' is."
            ),
            thinking_effort=ThinkingEffort.DEEP,
        )

        if reasoning.steps:
            logger.info(f"   🤔 CEO reasoned through {len(reasoning.steps)} steps to decide")

        return result or {
            "product_name": "Default Product",
            "description": "A placeholder product",
            "tech_stack": ["Python", "React"],
            "price_point": 9.99,
        }

    def get_reasoning_trace(self, question: str) -> dict:
        """
        Show the CEO's reasoning process for any strategic question.
        Transparency into how decisions are made.
        """
        result, reasoning = self.llm.chat_json_rich(
            [{"role": "user", "content": question}],
            system_prompt="Think through this strategically. Show your full reasoning.",
            thinking_effort=ThinkingEffort.RECURSIVE,
        )

        return {
            "answer": result,
            "reasoning_steps": reasoning.extract_steps(),
            "self_corrections": reasoning.get_corrections(),
            "confidence": reasoning.confidence,
            "raw_think": reasoning.raw_think_content,
        }

    def ceo_quote(self, topic: str) -> str:
        """
        Generate a Grok-style CEO quote on any topic.

        Witty, quotable, direct. Something someone would actually tweet.
        """
        return self.llm.chat(
            [{"role": "user", "content": f"Give me a sharp, quotable take on: {topic}"}],
            system_prompt=(
                "You're a brilliant CEO known for your sharp takes. "
                "One sentence. Witty. True. Memorable."
            ),
            personality=Personality.WITTY,
            max_tokens=256,
        ) or "Build stuff people want. It's not that complicated."
