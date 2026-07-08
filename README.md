# JTECH
[![Version](https://img.shields.io/badge/version-1.0.0-blue)]()

**JTECH** — A self-building AI company that designs, builds, and sells software products.

Powered by the NVIDIA DeepSeek API (via your API key), JTECH operates as a full company with specialized AI departments that work together to create revenue-generating products.

## Quick Start

```bash
# Install
pip install -e .

# Configure your API key
# Edit .env and add your NVIDIA_API_KEY

# Run a company standup
jtech standup

# Build a product
jtech build "A SaaS dashboard for tracking GitHub stars"

# Check company health
jtech status
```

## The Company Structure

| Role | Department | Responsibilities |
|---|---|---|
| **CEO** | C-Suite | Strategic direction, product decisions |
| **CTO** | C-Suite | Architecture, tech stack, code quality |
| **Head of Product** | C-Suite | Market research, product validation |
| **CMO** | Sales & Marketing | Go-to-market, pricing, listings, sales |
| **Developer** | Engineering | Writes production code, builds products |
| **Designer** | Design | UI/UX design, landing pages |
| **Brand Manager** | Design | Brand identity, logos, visual assets |
| **Product Studio** | Operations | End-to-end product factory (ideate → ship) |
| **Marketplace** | Sales | Product listings, sales tracking, revenue |

## Commands

```bash
jtech build "idea"     # Build a product from an idea
jtech list             # List all built products
jtech status           # Company health report
jtech sell 1           # Record a product sale
jtech revenue          # Revenue analytics
jtech catalog          # Generate product catalog HTML
jtech standup          # Full company standup
jtech history          # Recent activity
jtech launch           # Start autonomous mode
```

## How It Works

1. **CEO** decides what to build (or you give an idea)
2. **Head of Product** researches market fit
3. **CTO** designs the architecture
4. **Developer** writes the code
5. **Designer + Brand** creates the UI, logo, and landing page
6. **CMO** prices it and creates the listing
7. **Marketplace** lists it for sale
8. **You** record sales and track revenue

All AI operations use the **NVIDIA DeepSeek API** via your API key.

## Requirements

- Python 3.12+
- NVIDIA API key (free tier available at build.nvidia.com)
- No GPU required

## License

MIT
