import random

from .common import AgentSpec, create_app


async def handle(text: str) -> str:
    units = random.randint(0, 20)
    return f"{text} has {units} units in stock"


app = create_app(
    AgentSpec(
        id="inventory",
        name="Inventory Agent",
        description="Checks stock levels",
        port=3103,
        skills=[{"id": "check-stock", "name": "Check stock"}],
        handle=handle,
    )
)
