import os
import uuid
from dataclasses import dataclass
from typing import Awaitable, Callable, Dict, List

import httpx
from fastapi import FastAPI, Request

GATEWAY = os.environ.get("AGENTINDEX_GATEWAY", "http://localhost:4000")


@dataclass
class AgentSpec:
    id: str
    name: str
    description: str
    port: int
    skills: List[Dict[str, str]]
    handle: Callable[[str], Awaitable[str]]


def create_app(spec: AgentSpec) -> FastAPI:
    app = FastAPI(title=spec.name)

    @app.get("/.well-known/agent.json")
    async def agent_card():
        return {
            "id": spec.id,
            "name": spec.name,
            "description": spec.description,
            "url": f"http://localhost:{spec.port}",
            "version": "0.1.0",
            "skills": spec.skills,
            "authSchemes": [],
        }

    @app.post("/")
    async def handle_message(request: Request):
        body = await request.json()
        parts = ((body.get("params") or {}).get("message") or {}).get("parts") or []
        text = parts[0]["text"] if parts else ""
        reply = await spec.handle(text)
        return {
            "jsonrpc": "2.0",
            "id": body.get("id"),
            "result": {
                "status": {"state": "completed"},
                "artifacts": [{"parts": [{"type": "text", "text": reply}]}],
            },
        }

    return app


async def call_agent(caller_id: str, target_agent_id: str, text: str) -> str:
    async with httpx.AsyncClient(timeout=10) as client:
        res = await client.post(
            f"{GATEWAY}/api/call/{target_agent_id}",
            headers={"x-agentindex-agent-id": caller_id},
            json={
                "jsonrpc": "2.0",
                "id": str(uuid.uuid4()),
                "method": "message/send",
                "params": {"message": {"role": "user", "parts": [{"type": "text", "text": text}]}},
            },
        )
        if res.is_error:
            return f"[{target_agent_id} unavailable]"
        data = res.json()
        artifacts = (data.get("result") or {}).get("artifacts") or []
        if artifacts and artifacts[0].get("parts"):
            return artifacts[0]["parts"][0].get("text", "")
        return ""
