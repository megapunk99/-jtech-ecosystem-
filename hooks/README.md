# JTECH Hooks — Session Lifecycle Management

Hooks are scripts that run automatically on session start and end. They manage state persistence, environment setup, and cleanup.

## Available Hooks

| Hook | When It Runs | Purpose |
|---|---|---|
| `session-start.sh` | On JTECH session start | Load state, set up environment |
| `session-end.sh` | On JTECH session end | Save state, clean up |

## Hook Contract

- Hooks receive the session ID as the first argument
- Hooks must exit with code 0 on success
- Hooks run synchronously — the session waits for completion
- Hook failures are logged but don't block the session

## Directory Structure

```
hooks/
├── README.md
├── session-start.sh
└── session-end.sh
```
