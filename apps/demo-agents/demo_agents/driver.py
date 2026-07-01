import asyncio
import random

import httpx

from .common import GATEWAY, call_agent

AGENT_PORTS = [("pricing", 3102), ("inventory", 3103), ("concierge", 3101)]
PROMPTS = ["blue widget", "carbon fiber bracket", "steel bolt m6", "aluminum panel"]


async def register_all() -> None:
    async with httpx.AsyncClient(timeout=5) as client:
        for _, port in AGENT_PORTS:
            try:
                await client.post(f"{GATEWAY}/api/agents", json={"url": f"http://localhost:{port}"})
            except Exception:
                pass


async def drive_traffic() -> None:
    while True:
        await asyncio.sleep(4)
        text = random.choice(PROMPTS)
        try:
            await call_agent("external", "concierge", text)
        except Exception:
            pass


async def main() -> None:
    await asyncio.sleep(1.5)
    await register_all()
    await drive_traffic()


if __name__ == "__main__":
    asyncio.run(main())
