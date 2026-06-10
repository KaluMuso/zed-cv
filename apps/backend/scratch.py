import asyncio
from unittest.mock import MagicMock
from app.services.tier_config import get_tier_prices, clear_tier_config_cache
from tests.conftest import FakeSupabase

async def test():
    clear_tier_config_cache()
    sb = FakeSupabase()
    # It seems tier_config is missing? Let's check:
    q = sb.table("tier_config").select("*")
    print("rows:", q.execute().data)
    prices = await get_tier_prices(sb)
    print("prices dict:", prices)

if __name__ == "__main__":
    asyncio.run(test())
