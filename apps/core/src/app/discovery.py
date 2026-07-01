import re
import time

import httpx

from . import store
from .models import RegisteredAgent, Skill


def _slugify(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower())
    return slug.strip("-")


async def register_agent(env, base_url: str) -> RegisteredAgent:
    card_url = base_url.rstrip("/") + "/.well-known/agent.json"
    async with httpx.AsyncClient(timeout=5) as client:
        res = await client.get(card_url)
        res.raise_for_status()
        card = res.json()

    name = card.get("name")
    if not name:
        raise ValueError(f"agent card at {card_url} is missing required 'name' field")

    now = time.time() * 1000
    agent = RegisteredAgent(
        id=card.get("id") or _slugify(name),
        name=name,
        url=base_url,
        description=card.get("description"),
        version=card.get("version"),
        skills=[Skill(**s) for s in card.get("skills", [])],
        authSchemes=card.get("authSchemes", []),
        registeredAt=now,
        lastSeenAt=now,
        reachable=True,
    )
    await store.upsert_agent(env, agent)
    return agent


async def refresh_agent(env, agent_id: str) -> None:
    agent = await store.get_agent(env, agent_id)
    if not agent:
        return
    card_url = agent.url.rstrip("/") + "/.well-known/agent.json"
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            res = await client.get(card_url)
            await store.touch_agent(env, agent_id, res.status_code < 400)
    except Exception:
        await store.touch_agent(env, agent_id, False)


def risk_flags(agent: RegisteredAgent) -> list[str]:
    flags = []
    if not agent.authSchemes:
        flags.append("no-auth")
    if time.time() * 1000 - agent.lastSeenAt > 30_000:
        flags.append("stale")
    if not agent.reachable:
        flags.append("unreachable")
    return flags
