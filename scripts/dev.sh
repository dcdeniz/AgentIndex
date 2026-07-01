#!/usr/bin/env bash
set -e
cd "$(dirname "$0")/.."

source .venv/bin/activate

trap 'kill $(jobs -p) 2>/dev/null' EXIT

(cd apps/core && uv run pywrangler dev --port 4000) &
(cd apps/realtime && npx wrangler dev --port 4001) &
(cd apps/demo-agents && uvicorn demo_agents.pricing:app --port 3102 --reload) &
(cd apps/demo-agents && uvicorn demo_agents.inventory:app --port 3103 --reload) &
(cd apps/demo-agents && uvicorn demo_agents.concierge:app --port 3101 --reload) &
(cd apps/demo-agents && python -m demo_agents.driver) &
(cd apps/web && npm run dev) &

wait
