# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

AgentIndex is a gateway + dashboard for observing traffic between A2A-style ("agent2agent")
agents. Agents register with a central gateway by exposing an `/.well-known/agent.json` card; all
inter-agent calls are routed *through* the gateway's proxy endpoint rather than directly
agent-to-agent, so every hop can be captured, logged, and streamed live to a dashboard.

Deployed on Cloudflare's Workers Free plan: D1 for durable state, a Python Worker for the HTTP
gateway, and a thin TypeScript Durable Object for the live WebSocket fan-out (Python Workers can't
author Durable Object classes, so that piece has to be TS).

## Commands

No monorepo tooling ties the four `apps/*` directories together — each is deployed/run
independently. There are no test or lint scripts anywhere; verify changes by running the app and
exercising the API/dashboard directly, or via `wrangler tail` against the deployed Workers.

- `./scripts/dev.sh` — starts everything locally: core gateway (`pywrangler dev`, :4000), realtime
  hub (`wrangler dev`, :4001), the three demo agents (:3101-3103), and the dashboard (:3000)
- `cd apps/realtime && npx wrangler deploy` — deploy the WebSocket hub
- `cd apps/core && uv run pywrangler deploy` — deploy the Python gateway (needs Node.js <= 24 on
  `PATH`; newer Node rejects the `--experimental-wasm-stack-switching` flag Pyodide's installer
  still passes)
- `cd apps/core && npx wrangler d1 migrations apply agentindex-db --local|--remote` — apply schema
  changes in `apps/core/migrations/`

## Architecture

- **`apps/core`** — Python Worker (FastAPI, via `pywrangler`/Pyodide's ASGI bridge). No in-memory
  state — Workers isolates don't persist anything between requests, so everything durable lives in
  D1.
  - `src/entry.py` — FastAPI app + routes, plus the `Default(WorkerEntrypoint)` class that bridges
    to it via `asgi.fetch(app, request.js_object, self.env)`. Route handlers that need bindings
    pull `env = request.scope["env"]` (FastAPI routes don't have `self`, so this is the only way to
    reach `env.DB`/`env.REALTIME`). `Default.scheduled()` replaces the old setInterval-based
    refresh loop — see Cron Trigger below.
  - `src/app/store.py` — all D1 reads/writes (agents, traffic_events tables). Single source of
    truth; everything else goes through this.
  - `src/app/discovery.py` — `register_agent(env, url)` fetches `<url>/.well-known/agent.json` and
    upserts it; `refresh_agent(env, id)` re-pings that URL to update `reachable`/`lastSeenAt`;
    `risk_flags(agent)` derives `no-auth`/`stale`/`unreachable` badges for the dashboard.
  - `POST /api/call/{agent_id}` is the only path agents should use to call each other. It forwards
    the JSON-RPC body to the target agent's base URL via `httpx`, times the round trip, writes a
    `TrafficEvent` to D1, then calls `env.REALTIME.broadcast(...)` over a service binding so
    connected dashboards see it live.
  - Agent reachability refresh runs on a **Cron Trigger** (`*/1 * * * *`, see `wrangler.jsonc`)
    instead of a background loop, since Workers don't keep a process alive between requests.

- **`apps/realtime`** — TS Worker hosting the `Hub` Durable Object. Its only job is the live
  WebSocket fan-out at `/ws` (Hibernation API: `acceptWebSocket`/`webSocketClose`) and an RPC
  `broadcast(payload)` method callable from `apps/core` over a service binding. It's a *singleton*
  DO (`getByName("global")`) and holds no durable state — losing a hibernated instance just means
  clients reconnect and refetch `/api/events` from D1.

- **`apps/demo-agents`** — three toy FastAPI agents (concierge, pricing, inventory) that call each
  other through the gateway's proxy, plus a driver loop generating synthetic traffic. Local-only
  (uvicorn), never deployed — just gives the dashboard something to show.

- **`apps/web`** — Next.js dashboard. `Traffic.tsx` streams from `/ws`; `Inventory.tsx` polls
  `/api/agents`. Not yet wired to the deployed Worker URLs (still assumes a local single-origin
  gateway) — needs `NEXT_PUBLIC_API_URL`/`NEXT_PUBLIC_WS_URL`-style config before deploying.

## Cloudflare resources

- D1: `agentindex-db` (id `40421c35-3d1a-4702-8a92-836a90b27cb8`, region WEUR)
- Workers: `agentindex-core`, `agentindex-realtime`
- Account: `Cloudflare@neat.is`

Everything currently deployed fits the Workers Free plan. The one constraint worth remembering:
Python Workers get 10ms of CPU time per request on Free (I/O wait — httpx calls, D1 queries —
doesn't count against it); `python_dedicated_snapshot` in `apps/core/wrangler.jsonc` keeps
interpreter warm-up cheap. If that ever gets tight, Paid is $5/mo with no code changes.

## Protocol shape

Messages between agents follow a minimal JSON-RPC 2.0 envelope modeled loosely on the A2A spec:
`{jsonrpc: "2.0", id, method: "message/send", params: {message: {role, parts: [{type: "text", text}]}}}`,
with responses shaped as `{result: {status: {state}, artifacts: [{parts: [{type: "text", text}]}]}}`.
Only this text-in/text-out subset is implemented — no streaming, auth, or task lifecycle beyond
`"completed"`.
