# AgentIndex

Inventory + live traffic sniffer for A2A agents. Discovers agents via their
A2A Agent Cards, and captures every inter-agent call as it happens so you can
see who's talking to whom in real time.

## Architecture

```
apps/
  core/          FastAPI gateway (Python)
                 - fetches/refreshes Agent Cards (/.well-known/agent.json)
                 - agents route calls through /api/call/{agent_id}, which
                   forwards to the real agent and records a TrafficEvent
                 - pushes events to connected dashboards over a WebSocket
  demo-agents/   Three toy A2A agents (concierge, pricing, inventory), each
                 a small FastAPI app, that call each other through the
                 gateway, plus a driver loop that generates synthetic
                 traffic — gives the demo something to show without
                 needing real third-party agents.
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

## Run it

```
python3 -m venv .venv
source .venv/bin/activate
pip install -r apps/core/requirements.txt -r apps/demo-agents/requirements.txt
cd apps/web && npm install && cd ../..

./scripts/dev.sh
```

Starts the gateway on :4000, the dashboard on :3000, and the three demo
agents on :3101-3103. Open http://localhost:3000.
