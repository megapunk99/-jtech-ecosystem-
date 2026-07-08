---
name: think
description: Deep reasoning on any question with chain-of-thought
agents: [ceo]
calls: 1
timeout: 120
---

# Skill: think

Applies chain-of-thought reasoning to any question.

## Process

1. **Understand** — What is the core question?
2. **Analyze** — What data is relevant?
3. **Reason** — Walk through the logic step by step
4. **Challenge** — What could be wrong with this reasoning?
5. **Refine** — Correct any errors found
6. **Conclude** — Deliver the final answer

## Input

```
question: str — Any question to reason about
```

## Output

```
{
  "reasoning_steps": [str],      # Individual reasoning steps
  "self_corrections": [dict],    # Where the model caught mistakes
  "answer": dict,                # Final structured answer
  "confidence": float             # 0.0 to 1.0
}
```

## Usage

```bash
jtech think "What is the best product to build right now?"
```
