from typing import Any, List, Optional

from pydantic import BaseModel


class Skill(BaseModel):
    id: str
    name: str
    description: Optional[str] = None


class AgentCard(BaseModel):
    id: str
    name: str
    url: str
    description: Optional[str] = None
    version: Optional[str] = None
    skills: List[Skill] = []
    authSchemes: List[str] = []


class RegisteredAgent(AgentCard):
    registeredAt: float
    lastSeenAt: float
    reachable: bool


class TrafficEvent(BaseModel):
    id: int
    ts: float
    fromAgentId: str
    toAgentId: str
    method: str
    taskId: Optional[str] = None
    status: str
    latencyMs: float
    request: Any
    response: Any
