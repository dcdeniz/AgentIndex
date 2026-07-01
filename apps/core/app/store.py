import time
from typing import Dict, List, Optional

from .models import RegisteredAgent, TrafficEvent

_agents: Dict[str, RegisteredAgent] = {}
_events: List[TrafficEvent] = []
_next_event_id = 1


def upsert_agent(agent: RegisteredAgent) -> None:
    _agents[agent.id] = agent


def get_agent(agent_id: str) -> Optional[RegisteredAgent]:
    return _agents.get(agent_id)


def list_agents() -> List[RegisteredAgent]:
    return list(_agents.values())


def touch_agent(agent_id: str, reachable: bool) -> None:
    agent = _agents.get(agent_id)
    if agent:
        agent.lastSeenAt = time.time() * 1000
        agent.reachable = reachable


def add_event(event: TrafficEvent) -> TrafficEvent:
    global _next_event_id
    event.id = _next_event_id
    _next_event_id += 1
    _events.append(event)
    if len(_events) > 500:
        _events.pop(0)
    return event


def list_events(limit: int = 100) -> List[TrafficEvent]:
    return _events[-limit:]
