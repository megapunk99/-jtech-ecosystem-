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
import random
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
    """DeepSeek-powered LLM client with thinking mode, personality control, and API key rotation."""

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        self.keys: list[str] = []
        self._current_key_index = 0
        self._load_keys(api_key)

        self.model = model or os.environ.get("NVIDIA_MODEL") or DEFAULT_MODEL
        self.usage = LLMUsage()
        self.base_url = NVIDIA_BASE_URL
        self.default_personality = Personality.PROFESSIONAL
        self.default_effort = ThinkingEffort.MEDIUM

        if not self.keys:
            logger.warning("No NVIDIA_API_KEY set — AI operations will fail")

    def _load_keys(self, provided_key: Optional[str] = None) -> None:
        """Load API keys from env vars NVIDIA_API_KEY_1 through _N, plus fallback."""
        keys = []

        # If a key was provided directly, use it
        if provided_key:
            keys.append(provided_key)

        # Load NVIDIA_API_KEY_1, NVIDIA_API_KEY_2, ... NVIDIA_API_KEY_N
        for i in range(1, 20):
            key = os.environ.get(f"NVIDIA_API_KEY_{i}")
            if key and key not in keys:
                keys.append(key)

        # Fallback to NVIDIA_API_KEY (backward compat)
        fallback = os.environ.get("NVIDIA_API_KEY")
        if fallback and fallback not in keys:
            keys.append(fallback)

        self.keys = keys
        self._current_key_index = 0

    @property
    def api_key(self) -> str:
        """Get the current active API key."""
        if not self.keys:
            return ""
        idx = self._current_key_index % len(self.keys)
        return self.keys[idx]

    def _rotate_key(self) -> None:
        """Rotate to the next API key."""
        if not self.keys:
            return
        self._current_key_index = (self._current_key_index + 1) % len(self.keys)
        logger.info(f"Rotated to API key {self._current_key_index + 1}/{len(self.keys)}")

    @property
    def num_keys(self) -> int:
        return len(self.keys)

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
                       max_tokens: int = 4096, temperature: float = 0.3,
                       thinking_effort: Optional[ThinkingEffort] = None,
                       personality: Optional[Personality] = None) -> LLMResponse:
        """Internal method that does the actual API call with retry on 503."""
        effort = thinking_effort or self.default_effort
        pers = personality or self.default_personality

        if not self.api_key:
            return LLMResponse(content="")

        # Build system prompt
        sp_parts = []
        sp_parts.append(PERSONALITY_PROMPTS.get(pers, PERSONALITY_PROMPTS[Personality.PROFESSIONAL]))
        if system_prompt:
            sp_parts.append(system_prompt)

        if effort == ThinkingEffort.DEEP or effort == ThinkingEffort.HIGH:
            sp_parts.append("Think step-by-step before answering.")
        elif effort == ThinkingEffort.MINIMAL:
            sp_parts.append("Be brief and direct.")

        combined_sp = "\n".join(sp_parts)

        msgs = list(messages)
        msgs.insert(0, {"role": "system", "content": combined_sp})

        actual_max = min(max_tokens, 4096)
        if effort in (ThinkingEffort.DEEP, ThinkingEffort.RECURSIVE):
            actual_max = 8192

        payload = json.dumps({
            "model": self.model,
            "messages": msgs,
            "max_tokens": actual_max,
            "temperature": min(temperature, 0.5),
        }).encode("utf-8")

        # Retry loop for 503 errors
        max_retries = 3
        base_delay = 3.0

        for attempt in range(max_retries + 1):
            try:
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

                with urllib.request.urlopen(req, timeout=180) as resp:
                    data = json.loads(resp.read())
                elapsed = time.time() - start_time

                # Extract content
                choice = data.get("choices", [{}])[0]
                msg = choice.get("message", {})
                content = msg.get("content", "")

                # Extract reasoning from <think> tags
                reasoning = ReasoningTrace()
                if "<think>" in content:
                    think_match = re.search(r'<think>(.*?)</think>', content, re.DOTALL)
                    if think_match:
                        reasoning.raw_think_content = think_match.group(1).strip()
                        reasoning.final_answer = content[think_match.end():].strip()

                if "usage" in data:
                    u = data["usage"]
                    self.usage += LLMUsage(
                        prompt_tokens=u.get("prompt_tokens", 0),
                        completion_tokens=u.get("completion_tokens", 0),
                        total_tokens=u.get("total_tokens", 0),
                        api_calls=1,
                    )

                logger.debug(f"LLM call in {elapsed:.1f}s | tokens={self.usage.total_tokens}")

                final = reasoning.final_answer if reasoning.final_answer else content
                return LLMResponse(content=final, reasoning=reasoning, usage=self.usage, raw=data)

            except urllib.error.HTTPError as e:
                status = e.code
                body = e.read().decode()[:200]
                if status == 503 and attempt < max_retries:
                    # Rotate to next API key and retry immediately
                    self._rotate_key()
                    delay = 0.5 + random.uniform(0, 0.5)  # Small delay to avoid stampede
                    logger.warning(f"API 503 — rotated to key {self._current_key_index + 1}/{len(self.keys)}")
                    time.sleep(delay)
                else:
                    logger.error(f"NVIDIA API HTTP {status}: {body}")
                    return LLMResponse(content="")
            except Exception as e:
                if "timeout" in str(e).lower() and attempt < max_retries:
                    # Rotate key on timeout too
                    self._rotate_key()
                    delay = 0.5 + random.uniform(0, 0.5)
                    logger.warning(f"Timeout on key {self._current_key_index + 1}, retrying with next key...")
                    time.sleep(delay)
                else:
                    logger.error(f"API error: {e}")
                    return LLMResponse(content="")

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
