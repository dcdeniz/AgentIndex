import time

import httpx
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from workers import WorkerEntrypoint

from app import store
from app.discovery import refresh_agent, register_agent, risk_flags
from app.models import TrafficEvent

app = FastAPI(title="AgentIndex core")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/agents")
async def get_agents(request: Request):
    env = request.scope["env"]
    agents = await store.list_agents(env)
    return [{**agent.model_dump(), "riskFlags": risk_flags(agent)} for agent in agents]


@app.post("/api/agents")
async def post_agent(request: Request):
    env = request.scope["env"]
    payload = await request.json()
    try:
        return await register_agent(env, payload["url"])
    except Exception as err:
        raise HTTPException(status_code=400, detail=str(err))


@app.get("/api/events")
async def get_events(request: Request, limit: int = 100):
    env = request.scope["env"]
    return await store.list_events(env, limit)


# Agents call each other THROUGH this endpoint instead of directly, which is
# what lets us capture and stream every hop as a TrafficEvent.
@app.post("/api/call/{agent_id}")
async def call_agent(agent_id: str, request: Request):
    env = request.scope["env"]
    caller_id = request.headers.get("x-agentindex-agent-id", "external")
    body = await request.json()
    agent = await store.get_agent(env, agent_id)
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
    await store.touch_agent(env, agent_id, status == "ok")

    event = await store.add_event(
        env,
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
        ),
    )
    # apps/realtime owns the live WebSocket fan-out; this is the only place
    # the gateway talks to it, over a plain RPC service binding.
    await env.REALTIME.broadcast({"type": "event", "event": event.model_dump()})

    return response_body


class Default(WorkerEntrypoint):
    async def fetch(self, request):
        import asgi

        return await asgi.fetch(app, request.js_object, self.env)

    # Replaces the old setInterval/asyncio-background-task refresh loop —
    # Workers isolates don't keep a process alive between requests, so agent
    # reachability is refreshed on a Cron Trigger instead (see wrangler.jsonc).
    async def scheduled(self, *args):
        for agent in await store.list_agents(self.env):
            await refresh_agent(self.env, agent.id)
