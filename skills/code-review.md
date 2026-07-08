---
name: code-review
description: Review code for bugs, security issues, and best practices
agents: [developer]
calls: 1
timeout: 120
---

# Skill: code-review

Reviews source code and provides actionable feedback.

## Checklist

1. **Correctness** — Does the code do what it should?
2. **Security** — Injection vectors, exposed secrets, auth flaws?
3. **Performance** — N+1 queries, memory leaks, unnecessary work?
4. **Style** — Consistent with project conventions?
5. **Error Handling** — Are failures handled gracefully?
6. **Testing** — Is the code testable? Are edge cases covered?

## Output

```
{
  "issues": [
    {
      "severity": "critical" | "warning" | "suggestion",
      "file": "path/to/file.py",
      "line": 42,
      "description": "What's wrong",
      "fix": "How to fix it"
    }
  ],
  "summary": "Overall assessment",
  "score": 1-10
}
```
