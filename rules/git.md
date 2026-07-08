# Git Workflow Rules

## Commits

- One commit = one logical change
- Write descriptive commit messages:

```
type(scope): Brief description

Detailed explanation of what changed and why.
- Bullet points for multiple changes
- Reference issues with #number
```

Types: `feat`, `fix`, `docs`, `style`, `refactor`, `test`, `chore`

## Branches

- `main` — Production-ready code
- `feature/*` — New features (merge to main)
- `fix/*` — Bug fixes (merge to main)
- `experiment/*` — Experimental changes (may be discarded)

## Before Committing

- Run tests: `python -m pytest`
- Check types: `mypy jtech/`
- Lint: `ruff check jtech/`
- Remove debug code, commented code, print statements
- Check for hardcoded secrets and credentials
