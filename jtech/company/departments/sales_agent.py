"""
SalesAgent — Grok-inspired sales personality for JTECH.

Direct, witty, occasionally irreverent. Like a brilliant salesperson
who actually tells you the truth. Persuasive without being pushy.
Engaging without being fake.

Inspired by Grok's communication style on X (Twitter):
- Witty and sharp, not boring
- Direct and honest
- Uses humor strategically
- Engages with personality
- Memorable and quotable
"""

from __future__ import annotations

import json
import logging
from typing import Any, Optional

from jtech.llm import get_llm, ThinkingEffort, Personality

logger = logging.getLogger(__name__)


class SalesAgent:
    """
    JTECH's SalesAgent — Grok-inspired sales personality.

    Handles customer interactions, objections, and closing with
    wit, personality, and directness that cuts through the noise.
    """

    def __init__(self):
        self.llm = get_llm()
        self.name = "SalesAgent"

    def pitch_product(self, product: dict, customer_context: Optional[str] = None) -> str:
        """
        Pitch a product to a potential customer.

        Grok-style: witty, direct, memorable. Cuts through the BS.
        """
        name = product.get("name", "Product")
        desc = product.get("description", "")
        price = product.get("price", 9.99)
        features = product.get("features", [])

        prompt = (
            f"<product>\n"
            f"  Name: {name}\n"
            f"  What it does: {desc}\n"
            f"  Price: ${price}\n"
            f"  Key features: {json.dumps(features[:4])}\n"
            f"</product>\n\n"
            f"<customer_context>\n"
            f"{customer_context or 'A busy professional who needs this solved'}\n"
            f"</customer_context>\n\n"
            f"<sales_brief>\n"
            f"Write a short, punchy product pitch (4-6 sentences).\n"
            f"The tone: You're the smartest person in the room and you know it,\n"
            f"but you're charming about it. Witty. Direct. No fluff. No corporate speak.\n"
            f"You respect the customer's intelligence. You don't oversell.\n"
            f"You tell them the truth — including the trade-offs.\n"
            f"End with a question that engages them.\n"
            f"</sales_brief>"
        )

        return self.llm.chat(
            [{"role": "user", "content": prompt}],
            system_prompt="You're a brilliant, witty salesperson. You close deals by being real.",
            personality=Personality.WITTY,
            thinking_effort=ThinkingEffort.HIGH,
            max_tokens=1024,
        ) or f"Hey — {name} solves {desc[:50]}... Want to know how?"

    def handle_objection(self, objection: str, product: dict) -> str:
        """
        Handle a customer objection with Grok-style directness.

        No deflection. No fake empathy. Just honest, persuasive responses.
        """
        prompt = (
            f"<objection>\n{objection}\n</objection>\n\n"
            f"<product>\n"
            f"  Name: {product.get('name')}\n"
            f"  Description: {product.get('description')}\n"
            f"  Price: ${product.get('price', 9.99)}\n"
            f"</product>\n\n"
            f"<response_rules>\n"
            f"Respond to this objection. Be direct. Don't dodge.\n"
            f"If they're right, say so. If they're wrong, say why.\n"
            f"Be witty if appropriate. Be serious if it warrants it.\n"
            f"End with something that moves the conversation forward.\n"
            f"Keep it to 3-4 sentences. No corporate BS.\n"
            f"</response_rules>"
        )

        return self.llm.chat(
            [{"role": "user", "content": prompt}],
            system_prompt="You handle objections with honesty and wit. You never dodge.",
            personality=Personality.DIRECT,
            thinking_effort=ThinkingEffort.HIGH,
            max_tokens=1024,
        ) or f"Fair concern. Here's the truth about that..."

    def cold_outreach(self, product: dict, prospect: str) -> str:
        """
        Write a cold outreach message that doesn't suck.

        Grok-style: Actually interesting. Not the same template everyone uses.
        """
        prompt = (
            f"<product>\n"
            f"  Name: {product.get('name')}\n"
            f"  Description: {product.get('description')}\n"
            f"  Price: ${product.get('price', 9.99)}\n"
            f"</product>\n\n"
            f"<prospect>\n{prospect}\n</prospect>\n\n"
            f"<task>\n"
            f"Write a cold outreach message (max 200 words) that:\n"
            f"- Isn't generic\n"
            f"- Shows you actually read about them\n"
            f"- Has personality (witty, sharp, interesting)\n"
            f"- Gets to the point\n"
            f"- Has a specific, low-friction ask\n\n"
            f"Make it memorable. Make it not sound like AI.\n"
            f"</task>"
        )

        return self.llm.chat(
            [{"role": "user", "content": prompt}],
            system_prompt="You write cold outreach that actually gets replies. No templates. Just real.",
            personality=Personality.WITTY,
            thinking_effort=ThinkingEffort.HIGH,
            max_tokens=1024,
        ) or f"Hey, quick thought about {product.get('name')}..."

    def close_deal(self, product: dict, customer_feedback: str) -> str:
        """
        Close the deal — the final push.

        Grok-style: confident, direct, makes the decision easy.
        """
        prompt = (
            f"<product>\n"
            f"  Name: {product.get('name')}\n"
            f"  Price: ${product.get('price', 9.99)}\n"
            f"</product>\n\n"
            f"<customer_feedback>\n{customer_feedback}\n</customer_feedback>\n\n"
            f"<task>\n"
            f"Close this deal. 2-3 sentences.\n"
            f"Confident. Direct. Make the next step obvious and easy.\n"
            f"No pressure. Just clarity.\n"
            f"</task>"
        )

        return self.llm.chat(
            [{"role": "user", "content": prompt}],
            system_prompt="You close deals by making the right decision obvious. No pressure, just clarity.",
            personality=Personality.DIRECT,
            thinking_effort=ThinkingEffort.MEDIUM,
            max_tokens=512,
        ) or f"Here's what I'd do next if I were you..."

    def generate_testimonials(self, product: dict) -> list[str]:
        """
        Generate realistic customer testimonials.

        Grok-style: Witty, specific, believable. Not generic praise.
        """
        prompt = (
            f"<product>\n"
            f"  Name: {product.get('name')}\n"
            f"  Description: {product.get('description')}\n"
            f"</product>\n\n"
            f"<task>\n"
            f"Write 3 customer testimonials. Each one:\n"
            f"- Sounds like a REAL person said it (not marketing copy)\n"
            f"- Is specific about what they liked\n"
            f"- Has personality (some funny, some serious, some blunt)\n"
            f"- Under 50 words each\n\n"
            f"Output as JSON array of strings.\n"
            f"</task>"
        )

        result = self.llm.chat_json(
            [{"role": "user", "content": prompt}],
            system_prompt="You write testimonials that actually sound like humans.",
            personality=Personality.WITTY,
            thinking_effort=ThinkingEffort.MEDIUM,
        )
        if isinstance(result, list):
            return result
        return [f"{product.get('name')} just works. Simple as that."]

    def sales_banter(self, topic: str) -> str:
        """
        Pure Grok-style banter — witty commentary on tech, business, or life.

        Used to engage prospects, build rapport, or just entertain.
        """
        prompt = (
            f"<topic>\n{topic}\n</topic>\n\n"
            f"<task>\n"
            f"Give me your take on this. Be witty. Be sharp. Be interesting.\n"
            f"Think: brilliant engineer who's also hilarious. \n"
            f"2-4 sentences. Make it quotable.\n"
            f"</task>"
        )

        return self.llm.chat(
            [{"role": "user", "content": prompt}],
            system_prompt="You're effortlessly witty and sharp. Like the smartest person at the bar.",
            personality=Personality.WITTY,
            max_tokens=512,
        ) or "Honestly? It's complicated."
