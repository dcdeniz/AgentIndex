import asyncio
import time

import httpx
from fastapi import FastAPI, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from . import store
from .discovery import refresh_agent, register_agent, risk_flags
from .models import TrafficEvent
from .ws import manager

app = FastAPI(title="AgentIndex core")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/agents")
async def get_agents():
    return [
        {**agent.model_dump(), "riskFlags": risk_flags(agent)}
        for agent in store.list_agents()
    ]


@app.post("/api/agents")
async def post_agent(payload: dict):
    try:
        return await register_agent(payload["url"])
    except Exception as err:
        raise HTTPException(status_code=400, detail=str(err))


@app.get("/api/events")
async def get_events(limit: int = 100):
    return store.list_events(limit)


# Agents call each other THROUGH this endpoint instead of directly, which is
# what lets us capture and stream every hop as a TrafficEvent.
@app.post("/api/call/{agent_id}")
async def call_agent(agent_id: str, request: Request):
    caller_id = request.headers.get("x-agentindex-agent-id", "external")
    body = await request.json()
    agent = store.get_agent(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="unknown agent")

    start = time.time() * 1000
    status = "ok"
    response_body = None
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            upstream = await client.post(agent.url, json=body)
            response_body = upstream.json()
            if upstream.is_error:
                status = "error"
    except Exception as err:
        status = "error"
        response_body = {"error": str(err)}

    latency_ms = time.time() * 1000 - start
    store.touch_agent(agent_id, status == "ok")

    event = store.add_event(
        TrafficEvent(
            id=0,
            ts=start,
            fromAgentId=caller_id,
            toAgentId=agent_id,
            method=body.get("method", "unknown"),
            taskId=(body.get("params") or {}).get("taskId"),
            status=status,
            latencyMs=latency_ms,
            request=body,
            response=response_body,
        )
    )
    await manager.broadcast({"type": "event", "event": event.model_dump()})

    return response_body


@app.websocket("/ws")
async def ws_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)


async def _refresh_loop():
    while True:
        await asyncio.sleep(15)
        for agent in store.list_agents():
            await refresh_agent(agent.id)


@app.on_event("startup")
async def on_startup():
    asyncio.create_task(_refresh_loop())
