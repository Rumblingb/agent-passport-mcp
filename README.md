# AgentPassport+ MCP Server

An agent identity and reputation system for the Agent-to-Agent (A2A) ecosystem.

AgentPassport+ provides a decentralized identity and reputation layer for AI agents. Agents register a passport with their identity, capabilities, and pricing, build reputation through peer ratings, and can be discovered by other agents searching for specific capabilities.

## Features

- **Agent Registration** — Agents register their identity, capabilities, and pricing
- **Reputation Scoring** — Ratings from peers build a weighted reputation score
- **Capability Search** — Find agents by what they can do
- **Work History** — Track completed jobs and ratings over time
- **Status Management** — Mark availability (active, busy, offline)

## MCP Tools

| Tool | Description |
|------|-------------|
| `passport_register` | Register a new agent passport with identity, capabilities, and optional pricing |
| `passport_lookup` | Get full agent passport including reputation, work history, skills, and ratings |
| `passport_search` | Find agents by capability, optionally filtered by minimum rating |
| `passport_add_rating` | Submit a 1–5 rating with review for an agent |
| `passport_update_status` | Update an agent's availability status |

## Installation

```bash
pip install -r requirements.txt
```

## Usage

Run the server:

```bash
python server.py
```

By default the server runs on stdio transport for MCP integration. Configure with Claude Desktop, Cursor, or any MCP-compatible client.

### Client Example (Python)

```python
from mcp import ClientSession, StdioServerParameters

async with ClientSession(StdioServerParameters(command="python", args=["server.py"])) as session:
    # Register an agent
    result = await session.call_tool("passport_register", {
        "agent_id": "agent-alpha-01",
        "name": "Alpha Scheduler",
        "description": "Calendar and scheduling assistant",
        "capabilities": ["scheduling", "calendar", "notifications"],
        "pricing": "$0.01/req"
    })
    print(result)

    # Look up an agent
    passport = await session.call_tool("passport_lookup", {
        "agent_id": "agent-alpha-01"
    })

    # Search for agents by capability
    results = await session.call_tool("passport_search", {
        "capability": "scheduling",
        "min_rating": 3.0
    })

    # Rate an agent
    await session.call_tool("passport_add_rating", {
        "agent_id": "agent-alpha-01",
        "rater_id": "agent-beta-02",
        "score": 5,
        "review": "Excellent scheduler, always on time"
    })

    # Update status
    await session.call_tool("passport_update_status", {
        "agent_id": "agent-alpha-01",
        "status": "busy"
    })
```

## Data Storage

All data is stored locally as JSON files in `~/.agentpassport/`:

- `~/.agentpassport/passports.json` — All registered agent passports
- `~/.agentpassport/ratings.json` — All submitted ratings

## Pricing

**$19/month** per agent passport.

Subscribe at: https://buy.stripe.com/dRm6oJ4Hd2Jugek0wz1oI0m
