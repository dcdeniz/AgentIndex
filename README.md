# AgentIndex

Inventory + live traffic sniffer for A2A agents. Discovers agents via their
A2A Agent Cards, and captures every inter-agent call as it happens so you can
see who's talking to whom in real time.

## Architecture

```
apps/
  core/          Python Worker gateway (FastAPI, deployed via pywrangler)
                 - fetches/refreshes Agent Cards (/.well-known/agent.json)
                 - agents route calls through /api/call/{agent_id}, which
                   forwards to the real agent and records a TrafficEvent in D1
                 - refreshes agent reachability on a Cron Trigger (Workers
                   isolates don't keep a background loop alive between requests)
                 - calls apps/realtime over a service binding to push new
                   events live
  realtime/      TS Worker + Durable Object (Hub)
                 - Python can't author Durable Object classes, so this thin
                   TS worker owns the live WebSocket fan-out only
                 - holds no durable state itself — reconnecting clients just
                   refetch from /api/events (D1)
  demo-agents/   Three toy A2A agents (concierge, pricing, inventory), each
                 a small FastAPI app, that call each other through the
                 gateway, plus a driver loop that generates synthetic
                 traffic — gives the demo something to show without
                 needing real third-party agents. Runs locally via uvicorn;
                 not deployed.
  web/           Next.js dashboard
                 - Inventory tab: discovered agents, skills, risk flags
                 - Live Traffic tab: streaming feed of inter-agent calls
```

Agents never call each other directly — they call the gateway
(`/api/call/{agent_id}`), which forwards, times, and logs the request. That's
the whole trick: no MITM/packet capture needed for the demo, just route
through us.

Risk flags computed today: `no-auth` (card declares no auth schemes),
`stale` (not seen in 30s), `unreachable` (last card fetch failed).

## Cloudflare resources

- D1 database: `agentindex-db`
- Workers: `agentindex-core` (Python/FastAPI gateway), `agentindex-realtime`
  (TS Durable Object WebSocket hub)

Both run on the Workers Free plan — Durable Objects, D1, Cron Triggers, and
WebSockets are all available free. The one thing to watch is Python Workers'
10ms/request CPU budget (I/O wait doesn't count against it, and the
`python_dedicated_snapshot` flag keeps interpreter warm-up cheap).

## Deploy

```
cd apps/realtime && npx wrangler deploy
cd apps/core && uv run pywrangler deploy
```

Node.js <= 24 is required for `pywrangler` (Pyodide's `--experimental-wasm-stack-switching`
flag isn't recognized by newer Node builds).

## Run it locally

```
python3 -m venv .venv
source .venv/bin/activate
pip install -r apps/demo-agents/requirements.txt
cd apps/web && npm install && cd ../..

./scripts/dev.sh
```

Starts the core gateway (`pywrangler dev`, :4000), the realtime hub
(`wrangler dev`, :4001), the dashboard (:3000), and the three demo agents on
:3101-3103. Open http://localhost:3000.
