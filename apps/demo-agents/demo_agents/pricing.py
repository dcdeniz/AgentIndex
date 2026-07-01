import random

from .common import AgentSpec, create_app


async def handle(text: str) -> str:
    price = round(random.uniform(0, 100), 2)
    return f'Price for "{text}" is ${price}'


app = create_app(
    AgentSpec(
        id="pricing",
        name="Pricing Agent",
        description="Quotes prices for items",
        port=3102,
        skills=[{"id": "quote", "name": "Quote price"}],
        handle=handle,
    )
)
