---
name: security-scan
description: Scan code for vulnerabilities and security misconfigurations
agents: [developer]
calls: 1
timeout: 120
---

# Skill: security-scan

Scans source code for common security vulnerabilities.

## Scan Categories

1. **Injection** — SQL, command, NoSQL injection
2. **Authentication** — Weak auth, missing checks, hardcoded credentials
3. **Secrets** — API keys, tokens, passwords in code
4. **Configuration** — Insecure defaults, debug mode enabled
5. **Dependencies** — Known vulnerable packages
6. **Data Exposure** — Logging sensitive data, missing encryption

## Output

```
{
  "vulnerabilities": [
    {
      "severity": "critical" | "high" | "medium" | "low",
      "type": "injection" | "secrets" | "auth" | ...,
      "file": "path/to/file",
      "description": "What was found",
      "cve": "CVE-XXXX-XXXX" | null,
      "fix": "How to remediate"
    }
  ],
  "summary": "Overall security posture",
  "score": 1-10,
  "passed": bool
}
```
