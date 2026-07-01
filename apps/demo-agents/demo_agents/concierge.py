import asyncio

from .common import AgentSpec, call_agent, create_app


async def handle(text: str) -> str:
    price, stock = await asyncio.gather(
        call_agent("concierge", "pricing", text),
        call_agent("concierge", "inventory", text),
    )
    return f"{price}. {stock}."


app = create_app(
    AgentSpec(
        id="concierge",
        name="Concierge Agent",
        description="Front-of-house agent that delegates to pricing and inventory",
        port=3101,
        skills=[{"id": "help", "name": "Handle customer request"}],
        handle=handle,
    )
)
