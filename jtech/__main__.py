"""
JTECH — Self-building AI company that builds and sells software products.

A fully autonomous AI company with specialized departments:
  - C-Suite: CEO, CTO, Head of Product
  - Engineering: Developer (builds products)
  - Design: UI/UX Designer, Brand Manager
  - Sales & Marketing: CMO
  - Studio: Full product factory
  - Marketplace: Product sales engine

Powered by NVIDIA DeepSeek API. No GPU required.

Usage:
    jtech build [idea]     Build a product from an idea
    jtech list             List all built products
    jtech status           Company health report
    jtech sell <id>        Record a product sale
    jtech revenue          Revenue and sales analytics
    jtech catalog          Generate product catalog
    jtech standup          Full company standup
    jtech history          Recent company activity
    jtech launch           Start autonomous mode
"""

from jtech.cli import cli, main

__all__ = ["cli", "main"]
