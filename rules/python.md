# Python Rules

## Style

- Follow PEP 8
- Use type hints for all public functions
- Max line length: 100 characters
- Use f-strings over % or .format()
- Use pathlib over os.path

## Imports

```
# Standard library
import os
import sys

# Third party
import click
import requests

# Local
from jtech.llm import get_llm
```

## Concurrency

- Use threading for I/O-bound tasks
- Use multiprocessing for CPU-bound tasks
- Always use thread-safe data structures
- Prefer asyncio for new async code

## Project Structure

```
project/
├── __init__.py
├── cli.py          # CLI entry points
├── core.py         # Core business logic
├── models.py       # Data models
├── utils.py        # Utility functions
└── tests/
    ├── __init__.py
    └── test_core.py
```
