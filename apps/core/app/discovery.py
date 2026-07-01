import re
import time

import httpx

from . import store
from .models import RegisteredAgent, Skill


def _slugify(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower())
    return slug.strip("-")


async def register_agent(base_url: str) -> RegisteredAgent:
    card_url = base_url.rstrip("/") + "/.well-known/agent.json"
    async with httpx.AsyncClient(timeout=5) as client:
        res = await client.get(card_url)
        res.raise_for_status()
        card = res.json()

    now = time.time() * 1000
    agent = RegisteredAgent(
        id=card.get("id") or _slugify(card["name"]),
        name=card["name"],
        url=base_url,
        description=card.get("description"),
        version=card.get("version"),
        skills=[Skill(**s) for s in card.get("skills", [])],
        authSchemes=card.get("authSchemes", []),
        registeredAt=now,
        lastSeenAt=now,
        reachable=True,
    )
    store.upsert_agent(agent)
    return agent


async def refresh_agent(agent_id: str) -> None:
    agent = store.get_agent(agent_id)
    if not agent:
        return
    card_url = agent.url.rstrip("/") + "/.well-known/agent.json"
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            res = await client.get(card_url)
            store.touch_agent(agent_id, res.status_code < 400)
    except Exception:
        store.touch_agent(agent_id, False)


def risk_flags(agent: RegisteredAgent) -> list[str]:
    flags = []
    if not agent.authSchemes:
        flags.append("no-auth")
    if time.time() * 1000 - agent.lastSeenAt > 30_000:
        flags.append("stale")
    if not agent.reachable:
        flags.append("unreachable")
    return flags
