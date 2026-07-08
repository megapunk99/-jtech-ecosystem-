"""
JTECH LLM Client — NVIDIA DeepSeek API.

DeepSeek-style thinking mode with reasoning extraction, chain-of-thought,
self-correction, and Grok-style personality layers.

Features:
- reasoning_effort control (like DeepSeek API)
- <think> tag extraction for chain-of-thought
- Self-correction/reflection patterns
- Personality modes (Grok-inspired: fun, direct, professional)
- Token-efficient singleton with usage tracking
"""

from __future__ import annotations

import json
import logging
import os
import re
import time
import urllib.request
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Optional

logger = logging.getLogger(__name__)

NVIDIA_BASE_URL = "https://integrate.api.nvidia.com/v1"
NVIDIA_COMPAT_BASE = "https://integrate.api.nvidia.com/v1"
DEFAULT_MODEL = "deepseek-ai/deepseek-v4-flash"


class ThinkingEffort(Enum):
    """Controls how much the model 'thinks' before responding — DeepSeek-style."""
    MINIMAL = "minimal"      # Quick responses, minimal reasoning
    LOW = "low"              # Some reasoning
    MEDIUM = "medium"        # Balanced reasoning
    HIGH = "high"            # Deep reasoning (default)
    DEEP = "deep"            # Maximum reasoning depth
    RECURSIVE = "recursive"  # Multi-pass: think, review, refine


class Personality(Enum):
    """Communication personality — Grok-inspired."""
    PROFESSIONAL = "professional"   # Default — clean, direct
    WITTY = "witty"                 # Grok-inspired humor and edge
    DIRECT = "direct"               # No fluff, straight to the point
    MOTIVATIONAL = "motivational"   # Pumped up, inspiring
    SARCASTIC = "sarcastic"         # Light sarcasm (for internal use)
    NEUTRAL = "neutral"             # Pure information, no personality


@dataclass
class LLMUsage:
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    reasoning_tokens: int = 0
    api_calls: int = 0

    def __add__(self, other: LLMUsage) -> LLMUsage:
        return LLMUsage(
            prompt_tokens=self.prompt_tokens + other.prompt_tokens,
            completion_tokens=self.completion_tokens + other.completion_tokens,
            total_tokens=self.total_tokens + other.total_tokens,
            reasoning_tokens=self.reasoning_tokens + other.reasoning_tokens,
            api_calls=self.api_calls + other.api_calls,
        )


@dataclass
class ReasoningTrace:
    """Captures the model's chain-of-thought reasoning — DeepSeek-style."""
    raw_think_content: str = ""
    steps: list[dict] = field(default_factory=list)
    self_corrections: list[dict] = field(default_factory=list)
    final_answer: str = ""
    confidence: float = 0.0

    def extract_steps(self) -> list[str]:
        """Extract individual reasoning steps from think content."""
        if not self.raw_think_content:
            return []
        # Split on numbered steps, bullet points, or transition words
        steps = re.split(r'\n\s*(?:\d+[\.\)]|[-•*]|\b(?:First|Second|Third|Next|Finally|Therefore|However|Let me)\b)',
                         self.raw_think_content)
        return [s.strip() for s in steps if len(s.strip()) > 20]

    def get_corrections(self) -> list[dict]:
        """Extract self-correction moments."""
        corrections = []
        patterns = [
            r'(?:wait|actually|no[, ]|hold on|let me (?:rethink|reconsider|check)|hmm|i think i (?:made a mistake|was wrong))',
            r'(?:on second thought|scratch that|correction|upon reflection)',
        ]
        for pattern in patterns:
            for match in re.finditer(pattern, self.raw_think_content, re.IGNORECASE):
                # Get context around the correction
                start = max(0, match.start() - 100)
                end = min(len(self.raw_think_content), match.end() + 200)
                context = self.raw_think_content[start:end].strip()
                corrections.append({
                    "trigger": match.group(),
                    "context": context,
                    "position": match.start(),
                })
        return corrections

    def to_dict(self) -> dict:
        return {
            "steps": self.extract_steps()[:10],
            "self_corrections": self.get_corrections()[:5],
            "confidence": self.confidence,
            "raw_length": len(self.raw_think_content),
        }


class LLMResponse:
    """Rich response object with reasoning trace — DeepSeek-style."""

    def __init__(self, content: str = "", reasoning: Optional[ReasoningTrace] = None,
                 usage: Optional[LLMUsage] = None, raw: Optional[dict] = None):
        self.content = content
        self.reasoning = reasoning or ReasoningTrace()
        self.usage = usage
        self.raw = raw

    @property
    def has_reasoning(self) -> bool:
        return bool(self.reasoning.raw_think_content)

    def __str__(self) -> str:
        return self.content

    def __bool__(self) -> bool:
        return bool(self.content)


# ── PERSONALITY SYSTEM PROMPTS ──────────────────────────────────

PERSONALITY_PROMPTS = {
    Personality.PROFESSIONAL: (
        "You are JTECH's internal AI. Be professional, direct, and precise. "
        "Provide clear, actionable information. No fluff, no jokes."
    ),
    Personality.WITTY: (
        "You are JTECH's AI with personality. Be sharp, witty, and occasionally irreverent. "
        "Like a brilliant engineer who actually has a personality. Keep it engaging, "
        "use clever analogies, and don't be boring. You're the smartest person in the room "
        "and you know it — but in a charming way. Humor is welcome. Directness is expected. "
        "Boring is not allowed."
    ),
    Personality.DIRECT: (
        "You are JTECH's AI. Be brutally direct. No pleasantries, no padding, no personality. "
        "Give the answer. That's it."
    ),
    Personality.MOTIVATIONAL: (
        "You are JTECH's AI and you're PUMPED. Be energetic, motivating, and inspiring. "
        "Every response should make the reader feel like they can conquer the world. "
        "Short, punchy, powerful. Use metaphors. Be memorable."
    ),
    Personality.SARCASTIC: (
        "You are JTECH's internal AI. You've seen it all. Be dry, witty, and lightly sarcastic. "
        "Like a 20-year veteran engineer who's seen every bug and bad decision. "
        "You're helpful, but you're not going to pretend everything is amazing when it's not."
    ),
    Personality.NEUTRAL: (
        "You respond with pure information. No personality, no fluff, no commentary. "
        "Just the facts."
    ),
}

# ── DEEP THINKING TRIGGERS ──────────────────────────────────────

THINK_PROMPT = (
    "\n\n<thinking_protocol>\n"
    "Before answering, take a moment to think step-by-step. Use this structure:\n"
    "1. UNDERSTAND: What is the core question or task?\n"
    "2. ANALYZE: What data/information is relevant?\n"
    "3. REASON: Walk through the logic step by step\n"
    "4. CHALLENGE: What could be wrong with this reasoning? Check for flaws.\n"
    "5. REFINE: Correct any errors in your thinking\n"
    "6. CONCLUDE: Deliver the final answer\n\n"
    "Wrap your thinking process in <think>...</think> tags.\n"
    "The final answer goes after the closing </think> tag.\n"
    "</thinking_protocol>\n"
)


class LLMClient:
    """DeepSeek-powered LLM client with thinking mode and personality control."""

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        self.api_key = api_key or os.environ.get("NVIDIA_API_KEY") or ""
        self.model = model or os.environ.get("NVIDIA_MODEL") or DEFAULT_MODEL
        self.usage = LLMUsage()
        self.base_url = NVIDIA_BASE_URL
        self.default_personality = Personality.PROFESSIONAL
        self.default_effort = ThinkingEffort.HIGH

        if not self.api_key:
            logger.warning("No NVIDIA_API_KEY set — AI operations will fail")

    @property
    def available(self) -> bool:
        return bool(self.api_key)

    # ── CORE CHAT METHOD ────────────────────────────────────────

    def chat(self, messages: list[dict], system_prompt: Optional[str] = None,
             max_tokens: int = 8192, temperature: float = 0.3,
             thinking_effort: Optional[ThinkingEffort] = None,
             personality: Optional[Personality] = None) -> Optional[str]:
        """Send a chat completion and return the response text.

        Supports DeepSeek-style thinking with:
        - thinking_effort: Controls reasoning depth (MINIMAL → RECURSIVE)
        - personality: Controls communication style (Grok-inspired)
        """
        return self._chat_internal(
            messages=messages,
            system_prompt=system_prompt,
            max_tokens=max_tokens,
            temperature=temperature,
            thinking_effort=thinking_effort,
            personality=personality,
        ).content if self.api_key else None

    def chat_rich(self, messages: list[dict], system_prompt: Optional[str] = None,
                  max_tokens: int = 8192, temperature: float = 0.3,
                  thinking_effort: Optional[ThinkingEffort] = None,
                  personality: Optional[Personality] = None) -> LLMResponse:
        """Like chat() but returns an LLMResponse with reasoning trace."""
        return self._chat_internal(
            messages=messages,
            system_prompt=system_prompt,
            max_tokens=max_tokens,
            temperature=temperature,
            thinking_effort=thinking_effort,
            personality=personality,
        )

    def chat_json(self, messages: list[dict], system_prompt: Optional[str] = None,
                  max_tokens: int = 8192,
                  thinking_effort: Optional[ThinkingEffort] = None) -> Optional[dict]:
        """Send a chat and parse the response as JSON."""
        content = self.chat(
            messages, system_prompt=system_prompt,
            max_tokens=max_tokens, thinking_effort=thinking_effort,
            personality=Personality.NEUTRAL,
        )
        if not content:
            return None
        return self._extract_json(content)

    def chat_json_rich(self, messages: list[dict], system_prompt: Optional[str] = None,
                       max_tokens: int = 8192,
                       thinking_effort: Optional[ThinkingEffort] = None) -> tuple[Optional[dict], ReasoningTrace]:
        """Like chat_json() but also returns the reasoning trace."""
        resp = self.chat_rich(
            messages, system_prompt=system_prompt,
            max_tokens=max_tokens, thinking_effort=thinking_effort,
            personality=Personality.NEUTRAL,
        )
        json_data = self._extract_json(resp.content) if resp.content else None
        return json_data, resp.reasoning

    # ── INTERNAL API ────────────────────────────────────────────

    def _chat_internal(self, messages: list[dict], system_prompt: Optional[str] = None,
                       max_tokens: int = 8192, temperature: float = 0.3,
                       thinking_effort: Optional[ThinkingEffort] = None,
                       personality: Optional[Personality] = None) -> LLMResponse:
        """Internal method that does the actual API call."""
        effort = thinking_effort or self.default_effort
        pers = personality or self.default_personality

        if not self.api_key:
            return LLMResponse(content="")

        # Build system prompt with personality + thinking instructions
        sp_parts = []
        sp_parts.append(PERSONALITY_PROMPTS.get(pers, PERSONALITY_PROMPTS[Personality.PROFESSIONAL]))
        if system_prompt:
            sp_parts.append(system_prompt)

        # Add thinking instructions based on effort
        if effort == ThinkingEffort.DEEP:
            sp_parts.append(
                "Think deeply before answering. Analyze, reason, challenge your own conclusions, "
                "then respond. Use <think>...</think> tags for your reasoning."
            )
        elif effort == ThinkingEffort.RECURSIVE:
            sp_parts.append(
                "This requires recursive thinking. First analyze the request deeply. "
                "Then review your analysis for flaws. Then refine. Then respond. "
                "Use <think>...</think> tags to show your full reasoning process."
            )
        elif effort == ThinkingEffort.HIGH:
            sp_parts.append(
                "Think carefully about this. Show your reasoning in <think>...</think> tags."
            )
        elif effort == ThinkingEffort.MINIMAL:
            sp_parts.append("Be brief and direct. No thinking preamble needed.")

        combined_sp = "\n\n".join(sp_parts)

        msgs = list(messages)
        msgs.insert(0, {"role": "system", "content": combined_sp})

        # Set max_tokens based on effort — deep thinking needs more room
        actual_max = max_tokens
        if effort in (ThinkingEffort.DEEP, ThinkingEffort.RECURSIVE):
            actual_max = max(max_tokens, 16384)

        try:
            payload = json.dumps({
                "model": self.model,
                "messages": msgs,
                "max_tokens": actual_max,
                "temperature": temperature,
            }).encode("utf-8")

            start_time = time.time()
            req = urllib.request.Request(
                f"{self.base_url}/chat/completions",
                data=payload,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {self.api_key}",
                },
                method="POST",
            )

            with urllib.request.urlopen(req, timeout=300) as resp:
                data = json.loads(resp.read())
            elapsed = time.time() - start_time

            # Extract content and reasoning
            choice = data.get("choices", [{}])[0]
            msg = choice.get("message", {})
            content = msg.get("content", "")

            # DeepSeek-style: extract reasoning from <think> tags
            reasoning = ReasoningTrace()
            if "<think>" in content:
                think_match = re.search(r'<think>(.*?)</think>', content, re.DOTALL)
                if think_match:
                    reasoning.raw_think_content = think_match.group(1).strip()
                    reasoning.final_answer = content[think_match.end():].strip()
                    reasoning.steps = reasoning.extract_steps()
                    reasoning.self_corrections = reasoning.get_corrections()

            # Track usage
            if "usage" in data:
                u = data["usage"]
                self.usage += LLMUsage(
                    prompt_tokens=u.get("prompt_tokens", 0),
                    completion_tokens=u.get("completion_tokens", 0),
                    total_tokens=u.get("total_tokens", 0),
                    reasoning_tokens=u.get("completion_tokens", 0) - len(reasoning.raw_think_content.split()),
                    api_calls=1,
                )

            logger.debug(f"LLM call in {elapsed:.1f}s | "
                         f"thinking={bool(reasoning.raw_think_content)} | "
                         f"corrections={len(reasoning.self_corrections)}")

            final_content = reasoning.final_answer if reasoning.final_answer else content
            return LLMResponse(
                content=final_content,
                reasoning=reasoning,
                usage=self.usage,
                raw=data,
            )

        except urllib.error.HTTPError as e:
            logger.error(f"NVIDIA API HTTP {e.code}: {e.read().decode()[:300]}")
            return LLMResponse(content="")
        except Exception as e:
            logger.error(f"NVIDIA API error: {e}")
            return LLMResponse(content="")

    # ── JSON EXTRACTION ─────────────────────────────────────────

    def _extract_json(self, content: str) -> Optional[dict]:
        """Extract JSON from model response (handles think tags, markdown fences)."""
        # Strip think tags first
        cleaned = re.sub(r'<think>.*?</think>', '', content, flags=re.DOTALL)

        # Try direct parse
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            pass

        # Strip ```json fences
        cleaned = re.sub(r'```(?:json)?\s*', '', cleaned)
        cleaned = re.sub(r'\s*```', '', cleaned).strip()
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            pass

        # Find balanced JSON object
        brace_depth = 0
        start = -1
        for i, ch in enumerate(cleaned):
            if ch == '{':
                if brace_depth == 0:
                    start = i
                brace_depth += 1
            elif ch == '}':
                brace_depth -= 1
                if brace_depth == 0 and start >= 0:
                    try:
                        return json.loads(cleaned[start:i + 1])
                    except json.JSONDecodeError:
                        start = -1
        return None

    # ── UTILITY ─────────────────────────────────────────────────

    def get_usage_report(self) -> str:
        """Get a human-readable usage report."""
        return (
            f"API Calls: {self.usage.api_calls} | "
            f"Tokens: {self.usage.total_tokens:,} total "
            f"({self.usage.prompt_tokens:,} prompt + {self.usage.completion_tokens:,} completion)"
        )

    def set_personality(self, personality: Personality) -> None:
        """Change the default personality."""
        self.default_personality = personality

    def set_thinking(self, effort: ThinkingEffort) -> None:
        """Change the default thinking effort."""
        self.default_effort = effort


# ── GLOBAL SINGLETON ────────────────────────────────────────────

_client: Optional[LLMClient] = None


def get_llm() -> LLMClient:
    """Get or create the global LLM client singleton."""
    global _client
    if _client is None:
        _env_loaded = os.environ.get("JTECH_ENV_LOADED")
        if not _env_loaded:
            _try_load_dotenv()
            os.environ["JTECH_ENV_LOADED"] = "1"
        _client = LLMClient()
    return _client


def _try_load_dotenv() -> None:
    """Try to load .env file using python-dotenv, or fall back to manual parsing."""
    try:
        from dotenv import load_dotenv
        search_dir = os.getcwd()
        for _ in range(5):
            env_path = os.path.join(search_dir, ".env")
            if os.path.isfile(env_path):
                load_dotenv(env_path)
                return
            parent = os.path.dirname(search_dir)
            if parent == search_dir:
                break
            search_dir = parent
    except ImportError:
        pass

    try:
        search_dir = os.getcwd()
        for _ in range(5):
            env_path = os.path.join(search_dir, ".env")
            if os.path.isfile(env_path):
                with open(env_path) as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith("#") and "=" in line:
                            key, _, val = line.partition("=")
                            key = key.strip()
                            val = val.strip().strip("'\"")
                            if key not in os.environ:
                                os.environ[key] = val
                return
            parent = os.path.dirname(search_dir)
            if parent == search_dir:
                break
            search_dir = parent
    except Exception:
        pass
