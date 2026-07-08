# JTECH Rules — Language and Framework Coding Standards

Rules define how code should be written in each language and framework. They serve as system prompt context for AI agents.

## Available Rules

| Rule | Applies To |
|---|---|
| `common.md` | All languages — universal best practices |
| `python.md` | Python projects (JTECH core) |
| `typescript.md` | TypeScript/React frontend projects |
| `git.md` | Git workflow and commit conventions |

## Usage

Rules are loaded automatically by JTECH agents based on the project's tech stack. They're injected as part of the system prompt to guide code generation.

## Adding a New Rule

1. Create a markdown file in `rules/`
2. Use clear headings for each section
3. Provide specific, actionable guidelines
4. Include code examples where helpful
5. Keep it concise — under 100 lines
