# JTECH Skills — Reusable Capabilities

Each skill defines a focused, reusable workflow invoked via the CLI or by AI agents.

## Format

```yaml
---
name: skill-name
description: What the skill does
agents: [agent-names-used]
calls: number of LLM calls needed
timeout: max expected seconds
---
```

## Available Skills

| Skill | Description | Agents | Calls |
|---|---|---|---|
| `build-product` | Build a complete software product from an idea | ceo, developer, designer, cmo | 3 |
| `think` | Deep reasoning with chain-of-thought | ceo | 1 |
| `code-review` | Review code for bugs, security, and best practices | developer | 1 |
| `security-scan` | Scan code for vulnerabilities and misconfigurations | developer | 1 |

## Creating a New Skill

1. Create a markdown file in `skills/`
2. Add YAML frontmatter with metadata
3. Define the workflow steps
4. Specify expected output format
5. List error handling strategies
