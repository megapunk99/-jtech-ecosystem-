---
name: build-product
description: Build a complete software product from an idea
agents: [ceo, developer, designer, cmo]
calls: 3
timeout: 300
---

# Skill: build-product

Builds a complete, shippable software product from a description.

## Pipeline

1. **IDEATE** → CEO decides what to build (1 LLM call, minimal thinking)
2. **BUILD** → Developer + Designer generate features, API design, and landing page (1 LLM call, runs parallel with BRAND)
3. **BRAND** → CMO creates pricing, listing copy, and sales pitch (1 LLM call, runs parallel with BUILD)
4. **SHIP** → Write files to disk, register in marketplace, create project

## Input

```
idea: str (optional) — Product idea. If omitted, CEO decides.
```

## Output

```
{
  "product_id": int,
  "name": str,
  "description": str,
  "price": float,
  "features": [str],
  "preview_path": str,
  "listing_copy": str,
  "sales_pitch": str
}
```

## Error Handling

- If any LLM call fails: retry with next API key (rotation), up to 3 attempts
- If landing HTML is too short (< 200 chars): use template fallback
- If brand call fails: use default values (safe fallback)
- Partial results are better than failure

## Performance

- Phase 2 (BUILD) and Phase 3 (BRAND) run in parallel threads
- Expected total time: 60-120 seconds with functioning API keys
- Each LLM call uses ThinkingEffort.MINIMAL for speed
