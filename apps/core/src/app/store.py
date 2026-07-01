import json
import time
from typing import List, Optional

from .models import RegisteredAgent, Skill, TrafficEvent

# All state lives in D1 (env.DB) — there is no in-memory fallback, since
# Workers isolates don't persist state across requests. The realtime Hub
# Durable Object (apps/realtime) holds no state of its own either; it's
# purely a live fan-out for events already durably written here.

MAX_EVENTS = 500


def _row_to_agent(row: dict) -> RegisteredAgent:
    return RegisteredAgent(
        id=row["id"],
        name=row["name"],
        url=row["url"],
        description=row.get("description"),
        version=row.get("version"),
        skills=[Skill(**s) for s in json.loads(row["skills"])],
        authSchemes=json.loads(row["auth_schemes"]),
        registeredAt=row["registered_at"],
        lastSeenAt=row["last_seen_at"],
        reachable=bool(row["reachable"]),
    )


def _row_to_event(row: dict) -> TrafficEvent:
    return TrafficEvent(
        id=row["id"],
        ts=row["ts"],
        fromAgentId=row["from_agent_id"],
        toAgentId=row["to_agent_id"],
        method=row["method"],
        taskId=row.get("task_id"),
        status=row["status"],
        latencyMs=row["latency_ms"],
        request=json.loads(row["request"]),
        response=json.loads(row["response"]) if row["response"] is not None else None,
    )


async def upsert_agent(env, agent: RegisteredAgent) -> None:
    await env.DB.prepare(
        """
        INSERT INTO agents
          (id, name, url, description, version, skills, auth_schemes, registered_at, last_seen_at, reachable)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(id) DO UPDATE SET
          name = excluded.name,
          url = excluded.url,
          description = excluded.description,
          version = excluded.version,
          skills = excluded.skills,
          auth_schemes = excluded.auth_schemes,
          registered_at = excluded.registered_at,
          last_seen_at = excluded.last_seen_at,
          reachable = excluded.reachable
        """
    ).bind(
        agent.id,
        agent.name,
        agent.url,
        agent.description,
        agent.version,
        json.dumps([s.model_dump() for s in agent.skills]),
        json.dumps(agent.authSchemes),
        agent.registeredAt,
        agent.lastSeenAt,
        int(agent.reachable),
    ).run()


async def get_agent(env, agent_id: str) -> Optional[RegisteredAgent]:
    result = await env.DB.prepare("SELECT * FROM agents WHERE id = ?").bind(agent_id).all()
    rows = result.results
    return _row_to_agent(rows[0]) if rows else None


async def list_agents(env) -> List[RegisteredAgent]:
    result = await env.DB.prepare("SELECT * FROM agents").all()
    return [_row_to_agent(r) for r in result.results]


async def touch_agent(env, agent_id: str, reachable: bool) -> None:
    await env.DB.prepare(
        "UPDATE agents SET last_seen_at = ?, reachable = ? WHERE id = ?"
    ).bind(time.time() * 1000, int(reachable), agent_id).run()


async def add_event(env, event: TrafficEvent) -> TrafficEvent:
    result = (
        await env.DB.prepare(
            """
            INSERT INTO traffic_events
              (ts, from_agent_id, to_agent_id, method, task_id, status, latency_ms, request, response)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            RETURNING id
            """
        )
        .bind(
            event.ts,
            event.fromAgentId,
            event.toAgentId,
            event.method,
            event.taskId,
            event.status,
            event.latencyMs,
            json.dumps(event.request, default=str),
            json.dumps(event.response, default=str) if event.response is not None else None,
        )
        .all()
    )
    event.id = result.results[0]["id"]

    await env.DB.prepare(
        """
        DELETE FROM traffic_events
        WHERE id NOT IN (SELECT id FROM traffic_events ORDER BY id DESC LIMIT ?)
        """
    ).bind(MAX_EVENTS).run()

    return event


async def list_events(env, limit: int = 100) -> List[TrafficEvent]:
    result = await env.DB.prepare(
        "SELECT * FROM traffic_events ORDER BY id DESC LIMIT ?"
    ).bind(limit).all()
    events = [_row_to_event(r) for r in result.results]
    events.reverse()  # oldest-first, matching the original in-memory ordering
    return events
