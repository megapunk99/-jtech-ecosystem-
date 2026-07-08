# 🏢 JTECH Ecosystem

> **A self-building AI company that designs, builds, and sells software products.**  
> Powered by NVIDIA DeepSeek API. No GPU required.

<p align="center">
  <img src="https://img.shields.io/badge/version-2.0.0-2563eb?style=flat-square" alt="Version 2.0" />
  <img src="https://img.shields.io/badge/python-3.12%2B-2563eb?style=flat-square" alt="Python 3.12+" />
  <img src="https://img.shields.io/badge/license-MIT-2563eb?style=flat-square" alt="MIT License" />
  <img src="https://img.shields.io/badge/AI-DeepSeek%20v4-8b5cf6?style=flat-square" alt="DeepSeek v4" />
</p>

---

## 🚀 What is JTECH?

JTECH is a **fully autonomous software company** that runs on your laptop. It has specialized AI departments — CEO, CTO, CMO, Developer, Designer, and more — that work together to build, brand, and sell real software products.

Give it an idea, and JTECH will:

1. **Think deeply** about what to build (DeepSeek-style reasoning)
2. **Design** the architecture and data model
3. **Generate** a complete full-stack web application (React + TypeScript + Tailwind + Supabase)
4. **Design** the UI, brand identity, and logo
5. **Create** marketing copy, pricing, and a sales pitch
6. **Package** it for sale with a live preview page

All of this runs on your **NVIDIA DeepSeek API key** — no GPU, no cloud infrastructure, no Ollama needed.

---

## 🏛️ Architecture

```
┌──────────────────────────────────────────────────────────┐
│                    CLI (click commands)                    │
├──────────────────────────────────────────────────────────┤
│  ┌────────┐ ┌────────┐ ┌──────────┐ ┌────────┐ ┌─────┐  │
│  │  CEO   │ │  CTO   │ │Developer │ │Designer│ │ CMO │  │
│  │(Strat) │ │(Arch)  │ │ (Build)  │ │  (UI)  │ │(Mkt)│  │
│  └────────┘ └────────┘ └──────────┘ └────────┘ └─────┘  │
│  ┌────────┐ ┌────────┐ ┌──────────┐ ┌───────────────┐   │
│  │ Sales  │ │ Brand  │ │  Studio  │ │  Marketplace  │   │
│  │ Agent  │ │Manager │ │(Factory) │ │   (Sales)     │   │
│  └────────┘ └────────┘ └──────────┘ └───────────────┘   │
├──────────────────────────────────────────────────────────┤
│  ┌────────────┐ ┌──────────┐ ┌────────┐ ┌───────────┐   │
│  │  Project   │ │  System  │ │  SQLite│ │  Event    │   │
│  │  Manager   │ │  Access  │ │  State │ │  Bus      │   │
│  └────────────┘ └──────────┘ └────────┘ └───────────┘   │
│  ┌────────────┐ ┌──────────┐ ┌────────────────────┐     │
│  │  Health    │ │  Circuit │ │  Permission        │     │
│  │  Monitor   │ │  Breaker │ │  System            │     │
│  └────────────┘ └──────────┘ └────────────────────┘     │
└──────────────────────────────────────────────────────────┘
```

### Three Layers

| Layer | Purpose |
|---|---|
| **CLI** | Your interface — every command maps to a department or system function |
| **Company** | 9 specialized AI departments that work together to build products |
| **Infrastructure** | Bulletproof foundation — circuit breakers, SQLite persistence, audit trails, permissions |

---

## 🛠️ Quick Start

```bash
# 1. Clone and install
git clone https://github.com/megapunk99/-jtech-ecosystem-.git
cd jtech-ecosystem
pip install -e .

# 2. Add your NVIDIA API key to .env
echo "NVIDIA_API_KEY=nvapi-your-key-here" > .env

# 3. Verify everything works
jtech health

# 4. Run a company standup
jtech standup

# 5. Build your first product
jtech build "A SaaS dashboard for monitoring API health"
```

---

## 📋 Commands

### Product Development

| Command | What It Does |
|---|---|
| `jtech build "idea"` | Build a complete product from an idea (CEO → CTO → Developer → Designer → CMO) |
| `jtech build "idea" --stack python-api` | Build a Python FastAPI backend instead of a React app |
| `jtech list` | List all built products with sales and revenue |
| `jtech sell 1 --price 19.99` | Record a product sale |
| `jtech revenue` | Show revenue and sales analytics |
| `jtech preview 1` | Generate a stunning live preview HTML page |
| `jtech edit 1 "make it darker"` | Visual edit mode — modify UI with natural language |

### Company Operations

| Command | What It Does |
|---|---|
| `jtech standup` | All 9 departments report in (CEO, CTO, CMO, Developer, Designer, etc.) |
| `jtech status` | Company health report with AI analysis |
| `jtech think "question"` | See the CEO's deep reasoning process (with self-corrections) |
| `jtech history` | Recent company activity |
| `jtech launch` | Autonomous mode — standup + build first product |

### Project Management

| Command | What It Does |
|---|---|
| `jtech project create "name"` | Create a new project with workspace directory |
| `jtech project list` | List all projects with their lifecycle status |
| `jtech project open 1` | Open a project and see its workspace tree |
| `jtech project status 1 shipped` | Transition project through its lifecycle |
| `jtech project archive 1` | Archive a completed project |

### System Access (permission-gated)

| Command | What It Does |
|---|---|
| `jtech ls /path` | List directory contents (asks permission first) |
| `jtech cat file.txt` | Read a file (asks permission first) |
| `jtech run "command"` | Run a shell command (asks permission, auto-blocks dangerous commands) |
| `jtech env PATH` | Read environment variables (asks permission, masks secrets) |
| `jtech sysinfo` | System information (auto-granted) |

### Infrastructure

| Command | What It Does |
|---|---|
| `jtech health` | Run full system health diagnostics |
| `jtech permissions` | List active permission grants |
| `jtech revoke` | Revoke all permissions |
| `jtech events` | View the audit trail |
| `jtech circuit` | Show circuit breaker states |

---

## 🧠 How It Works

### The Product Pipeline

When you run `jtech build "a dashboard for X"`:

```
1. IDEATE    → CEO decides what to build (with deep reasoning)
2. THINK     → Requirements analysis (DeepSeek-style chain-of-thought)
3. RESEARCH  → Head of Product validates market fit
4. DESIGN    → CTO designs architecture and data model
5. BUILD     → AppBuilder generates full-stack app (React/TS/Tailwind + Supabase)
6. PREVIEW   → Designer creates stunning live preview HTML
7. BRAND     → Brand Manager creates logo, colors, and identity
8. PRICE     → CMO determines optimal pricing and go-to-market
9. PITCH     → Sales Agent writes Grok-style sales pitch
10. SHIP     → Registered in marketplace, project created, ready to sell
```

Every step uses the **NVIDIA DeepSeek API** for AI operations, with:
- Circuit breaker protection (auto-fail if API degrades)
- Exponential backoff retry (survive transient failures)
- Full audit trail (every decision is logged)
- Graceful fallbacks (if one step fails, the system degrades, doesn't crash)

### The Departments

| Department | Role | Inspired By |
|---|---|---|
| **CEO** | Strategic direction, product decisions | DeepSeek reasoning + Grok personality |
| **CTO** | Architecture, tech stack, code guidelines | — |
| **Head of Product** | Market research, product validation | — |
| **CMO** | Go-to-market, pricing, structured copy | Claude's structured marketing |
| **Developer** | Full-stack app generation | Lovable.dev, Bolt.new |
| **Designer** | UI/UX design, live previews | v0, Lovable |
| **Brand Manager** | Brand identity, logos, colors | — |
| **Sales Agent** | Sales pitches, objection handling | Grok's witty personality |
| **Product Studio** | End-to-end product factory | — |
| **Marketplace** | Product listings, sales, revenue | — |

---

## 🏗️ Infrastructure

JTECH is built on a production-grade infrastructure layer:

| Component | What It Does |
|---|---|
| **Circuit Breaker** | Prevents cascading failures — auto-blocks calls to failing services |
| **Retry with Backoff** | Exponential backoff with jitter — survives transient API failures |
| **SQLite State Manager** | ACID-compliant persistent storage — no data loss on crash |
| **Event Bus** | Pub/sub system — every action is logged and auditable |
| **Health Monitor** | Self-diagnostics — knows when it's sick |
| **Permission System** | Gates ALL computer access behind user consent — 6 risk levels |

Security model: **Default deny**. Every filesystem read, command execution, and environment variable access requires explicit user permission, logged with full audit trail.

---

## 📦 Requirements

- **Python 3.12+**
- **NVIDIA API key** (free tier available at [build.nvidia.com](https://build.nvidia.com/deepseek-ai/deepseek-v4-flash))
- **No GPU required** — all AI runs on NVIDIA's cloud API
- **No Ollama, no Docker, no cloud subscription**

---

## 🎯 What You Can Build

JTECH specializes in AI-powered SaaS products. Example products it can build:

- **API monitoring dashboards** — Track uptime, latency, and error rates
- **GitHub analytics tools** — Repository health, contributor metrics, issue triage
- **Customer feedback platforms** — Collect, analyze, and act on user feedback
- **Internal tooling** — Admin panels, reporting dashboards, workflow automation
- **Data visualization** — Interactive charts, real-time monitoring, exportable reports

Each product comes with:
- Complete React + TypeScript + Tailwind frontend
- Supabase backend integration (auth, database, storage)
- Brand identity (logo, colors, typography)
- Marketing copy and sales pitch
- Live preview page ready to open in a browser

---

## 🤝 Contributing

JTECH is designed to be extended:

- **Add a new department**: Create a class in `jtech/company/departments/` and register it in the Studio
- **Add a new stack template**: Add to `STACKS` in `jtech/builder.py`
- **Add a new infrastructure component**: Create a file in `jtech/infrastructure/`

---

## 📄 License

MIT — see [LICENSE](LICENSE)

---

<p align="center">
  <sub>Built by <a href="https://github.com/megapunk99">megapunk99</a> · Powered by NVIDIA DeepSeek · Think. Build. Ship.</sub>
</p>
