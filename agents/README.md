# JTECH Agents — ECC-Style Agent Personas

Each agent definition is a markdown file with:
- **YAML frontmatter**: name, model, temperature, output format
- **System prompt**: Core directives and behavior rules
- **Capabilities**: What the agent can do
- **Output format**: Expected response structure
- **Constraints**: Rules the agent must follow

## Available Agents

| Agent | Role | Output | Temperature |
|---|---|---|---|
| `ceo` | Strategic decisions, product direction | JSON | 0.3 |
| `developer` | Full-stack software development | Code | 0.2 |
| `designer` | UI/UX design, brand identity | HTML | 0.4 |
| `cmo` | Marketing, pricing, sales copy | Text | 0.5 |
| `sales-agent` | Sales pitches, objection handling | Text | 0.7 |

## Usage

Each agent can be invoked by the JTECH CLI or directly via the LLM client:

```python
from jtech.llm import get_llm
llm = get_llm()

# Load agent definition
with open("agents/default/ceo.md") as f:
    agent_def = f.read()

# Use the system prompt from the agent definition
response = llm.chat_json(
    [{"role": "user", "content": "What should we build?"}],
    system_prompt=agent_def,
)
```
