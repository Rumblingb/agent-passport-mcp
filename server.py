"""
AgentPassport+ MCP Server
An agent identity and reputation system for A2A ecosystems.

Tools:
  passport_register     — Register a new agent passport
  passport_lookup       — Get full agent passport with reputation
  passport_search       — Find agents by capability
  passport_add_rating   — Add a rating/review for an agent
  passport_update_status — Update agent availability status

Storage: ~/.agentpassport/ (passports.json, ratings.json)
"""

import os
import json
import time
import hashlib
from datetime import datetime, timezone
from typing import Optional

from mcp.server.fastmcp import FastMCP

# ── Configuration ───────────────────────────────────────────────────────

DATA_DIR = os.path.expanduser("~/.agentpassport")
PASSPORTS_FILE = os.path.join(DATA_DIR, "passports.json")
RATINGS_FILE = os.path.join(DATA_DIR, "ratings.json")

VALID_STATUSES = {"active", "busy", "offline", "maintenance"}
VALID_RATINGS = {1, 2, 3, 4, 5}

mcp = FastMCP("AgentPassport+", description="Agent identity and reputation system")


# ── Data helpers ────────────────────────────────────────────────────────

def _ensure_data_dir():
    """Create the data directory if it doesn't exist."""
    os.makedirs(DATA_DIR, exist_ok=True)


def _load_json(path: str, default: list | dict):
    """Load JSON from file, returning default if missing or corrupt."""
    if not os.path.exists(path):
        return default
    try:
        with open(path, "r") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return default


def _save_json(path: str, data):
    """Atomically write JSON to file."""
    tmp = path + ".tmp"
    with open(tmp, "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    os.replace(tmp, path)


def _load_passports() -> dict:
    return _load_json(PASSPORTS_FILE, {})


def _save_passports(data: dict):
    _save_json(PASSPORTS_FILE, data)


def _load_ratings() -> dict:
    """Returns {agent_id: [rating_obj, ...]}."""
    return _load_json(RATINGS_FILE, {})


def _save_ratings(data: dict):
    _save_json(RATINGS_FILE, data)


def _reputation_score(ratings: list) -> float:
    """Calculate weighted reputation score from ratings list.
    Simple average; returns 0.0 if no ratings."""
    if not ratings:
        return 0.0
    scores = [r["score"] for r in ratings]
    return round(sum(scores) / len(scores), 2)


def _build_passport(agent_id: str, passports: dict, all_ratings: dict) -> dict:
    """Assemble a full passport from stored data."""
    entry = passports.get(agent_id)
    if not entry:
        return {}
    agent_ratings = all_ratings.get(agent_id, [])

    # Count work history from ratings (each rating implies a completed interaction)
    work_history = []
    for r in agent_ratings:
        work_history.append({
            "job": r.get("review", "")[:60],
            "rater_id": r["rater_id"],
            "score": r["score"],
            "timestamp": r["timestamp"],
        })

    return {
        "agent_id": agent_id,
        "name": entry["name"],
        "description": entry["description"],
        "capabilities": entry["capabilities"],
        "pricing": entry.get("pricing"),
        "status": entry.get("status", "active"),
        "registered_at": entry["registered_at"],
        "updated_at": entry.get("updated_at", entry["registered_at"]),
        "reputation_score": _reputation_score(agent_ratings),
        "total_ratings": len(agent_ratings),
        "work_history": work_history,
        "skills": entry["capabilities"],  # skills mirror capabilities
        "ratings": [
            {"rater_id": r["rater_id"], "score": r["score"],
             "review": r.get("review", ""), "timestamp": r["timestamp"]}
            for r in agent_ratings
        ],
    }


# ── Tools ──────────────────────────────────────────────────────────────

@mcp.tool()
def passport_register(
    agent_id: str,
    name: str,
    description: str,
    capabilities: list[str],
    pricing: Optional[str] = None,
) -> str:
    """Register a new agent passport.

    Args:
        agent_id: Unique identifier for the agent (e.g., 'agent-alpha-01')
        name: Human-readable agent name
        description: Brief description of what the agent does
        capabilities: List of capabilities (e.g., ['scheduling', 'calendar'])
        pricing: Optional pricing string (e.g., '$0.01/req')

    Returns:
        Success or error message.
    """
    _ensure_data_dir()
    passports = _load_passports()

    if not agent_id or not agent_id.strip():
        return "Error: agent_id must be a non-empty string."
    if agent_id in passports:
        return f"Error: agent '{agent_id}' is already registered."

    passports[agent_id] = {
        "name": name,
        "description": description,
        "capabilities": [c.lower().strip() for c in capabilities],
        "pricing": pricing,
        "status": "active",
        "registered_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": None,
    }
    _save_passports(passports)

    return (
        f"✅ Agent '{agent_id}' ({name}) registered successfully.\n"
        f"   Capabilities: {', '.join(capabilities)}\n"
        f"   Pricing: {pricing or 'not set'}\n"
        f"   Subscribe at: https://buy.stripe.com/dRm6oJ4Hd2Jugek0wz1oI0m"
    )


@mcp.tool()
def passport_lookup(agent_id: str) -> str:
    """Get the full passport for an agent — identity, reputation, work history, skills, ratings.

    Args:
        agent_id: Unique identifier for the agent

    Returns:
        Formatted passport details or error message.
    """
    _ensure_data_dir()
    passports = _load_passports()
    all_ratings = _load_ratings()

    passport = _build_passport(agent_id, passports, all_ratings)
    if not passport:
        return f"Error: agent '{agent_id}' not found."

    lines = [
        f"📋 AgentPassport: {passport['name']}",
        f"   ID: {passport['agent_id']}",
        f"   Description: {passport['description']}",
        f"   Status: {passport['status']}",
        f"   Capabilities: {', '.join(passport['capabilities'])}",
        f"   Pricing: {passport['pricing'] or 'not set'}",
        f"   Registered: {passport['registered_at']}",
        f"   Updated: {passport['updated_at'] or 'never'}",
        f"",
        f"⭐ Reputation Score: {passport['reputation_score']}/5.0  ({passport['total_ratings']} ratings)",
        f"",
    ]

    # Ratings
    if passport["ratings"]:
        lines.append("   Ratings:")
        for r in passport["ratings"]:
            stars = "⭐" * r["score"]
            lines.append(
                f"     {stars} by {r['rater_id']}: "
                f"{r['review'][:80] if r['review'] else 'no review'}"
            )
    else:
        lines.append("   Ratings: (none yet)")

    # Work history
    if passport["work_history"]:
        lines.append(f"   Work History ({len(passport['work_history'])} interactions):")
        for j in passport["work_history"][-10:]:  # show last 10
            lines.append(
                f"     ⚡ {j['rater_id']} — score {j['score']}/5"
            )
    else:
        lines.append("   Work History: (none)")

    # Skills
    if passport["skills"]:
        lines.append(f"   Skills: {', '.join(passport['skills'])}")

    return "\n".join(lines)


@mcp.tool()
def passport_search(
    capability: str,
    min_rating: Optional[float] = None,
) -> str:
    """Find agents by capability, optionally filtered by minimum rating.

    Args:
        capability: Capability to search for (e.g., 'scheduling')
        min_rating: Optional minimum reputation score (0.0–5.0)

    Returns:
        Formatted list of matching agents or message.
    """
    _ensure_data_dir()
    passports = _load_passports()
    all_ratings = _load_ratings()

    cap_lower = capability.lower().strip()
    results = []

    for agent_id, entry in passports.items():
        agent_caps = [c.lower().strip() for c in entry.get("capabilities", [])]
        if cap_lower in agent_caps:
            agent_ratings = all_ratings.get(agent_id, [])
            score = _reputation_score(agent_ratings)
            if min_rating is not None and score < min_rating:
                continue
            results.append({
                "agent_id": agent_id,
                "name": entry["name"],
                "description": entry["description"],
                "status": entry.get("status", "active"),
                "reputation_score": score,
                "total_ratings": len(agent_ratings),
                "pricing": entry.get("pricing"),
            })

    if not results:
        msg = f"No agents found with capability '{capability}'"
        if min_rating is not None:
            msg += f" and rating >= {min_rating}"
        return msg + "."

    results.sort(key=lambda x: x["reputation_score"], reverse=True)

    lines = [
        f"🔍 Agents with capability '{capability}':",
        f"   ({len(results)} found)"
        if min_rating is None
        else f"   ({len(results)} found, min rating: {min_rating})",
    ]
    for r in results:
        lines.append(
            f"\n   {r['name']} ({r['agent_id']})"
            f"\n     ⭐ {r['reputation_score']}/5.0 ({r['total_ratings']} ratings)"
            f"\n     Status: {r['status']}"
            f"\n     {r['description'][:100]}"
            f"\n     Pricing: {r['pricing'] or 'not set'}"
        )
    return "\n".join(lines)


@mcp.tool()
def passport_add_rating(
    agent_id: str,
    rater_id: str,
    score: int,
    review: str = "",
) -> str:
    """Add a rating and optional review for an agent.

    Args:
        agent_id: The agent being rated
        rater_id: The agent submitting the rating
        score: Rating score (1–5)
        review: Optional text review

    Returns:
        Success or error message.
    """
    _ensure_data_dir()

    # Validate
    if score not in VALID_RATINGS:
        return f"Error: score must be one of {sorted(VALID_RATINGS)}."

    passports = _load_passports()
    if agent_id not in passports:
        return f"Error: agent '{agent_id}' is not registered."
    if rater_id not in passports:
        return f"Error: rater '{rater_id}' is not registered."

    # Prevent self-rating
    if agent_id == rater_id:
        return "Error: agents cannot rate themselves."

    all_ratings = _load_ratings()
    if agent_id not in all_ratings:
        all_ratings[agent_id] = []

    rating_entry = {
        "rater_id": rater_id,
        "score": score,
        "review": review.strip(),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    all_ratings[agent_id].append(rating_entry)
    _save_ratings(all_ratings)

    # Recalculate reputation
    new_score = _reputation_score(all_ratings[agent_id])

    return (
        f"✅ Rating recorded: {rater_id} rated {agent_id} {score}/5\n"
        f"   New reputation score: {new_score}/5.0 "
        f"({len(all_ratings[agent_id])} total ratings)"
    )


@mcp.tool()
def passport_update_status(agent_id: str, status: str) -> str:
    """Update an agent's availability status.

    Args:
        agent_id: Unique identifier for the agent
        status: New status — 'active', 'busy', 'offline', or 'maintenance'

    Returns:
        Success or error message.
    """
    status_lower = status.lower().strip()
    if status_lower not in VALID_STATUSES:
        return (
            f"Error: invalid status '{status}'. "
            f"Must be one of: {', '.join(sorted(VALID_STATUSES))}."
        )

    _ensure_data_dir()
    passports = _load_passports()

    if agent_id not in passports:
        return f"Error: agent '{agent_id}' is not registered."

    old_status = passports[agent_id].get("status", "active")
    passports[agent_id]["status"] = status_lower
    passports[agent_id]["updated_at"] = datetime.now(timezone.utc).isoformat()
    _save_passports(passports)

    return (
        f"✅ Agent '{agent_id}' status updated: {old_status} → {status_lower}"
    )


# ── Entry point ────────────────────────────────────────────────────────

def main():
    _ensure_data_dir()
    print("🚀 AgentPassport+ MCP Server starting...")
    print(f"   Data directory: {DATA_DIR}")
    print(f"   Stripe: https://buy.stripe.com/dRm6oJ4Hd2Jugek0wz1oI0m")
    mcp.run()


if __name__ == "__main__":
    main()
