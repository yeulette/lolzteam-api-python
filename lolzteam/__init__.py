"""
lolzteam
~~~~~~~~
Python SDK for the LOLZ Forum and ZT.MARKET APIs.

Quick start::

    from lolzteam import Forum, Market

    # ── Sync ──────────────────────────────────────────────
    forum  = Forum(token="YOUR_TOKEN")
    market = Market(token="YOUR_TOKEN")

    me   = forum.get_users_me().json()
    item = market.get_item(item_id=12345678).json()

    # ── Async ─────────────────────────────────────────────
    import asyncio

    forum_async  = Forum(token="YOUR_TOKEN",  async_mode=True)
    market_async = Market(token="YOUR_TOKEN", async_mode=True)

    async def main():
        me   = (await forum_async.get_users_me()).json()
        item = (await market_async.get_item(item_id=12345678)).json()
        print(me, item)

    asyncio.run(main())
"""

from .forum import Forum
from .market import Market

__version__ = "1.0.0"
__all__ = ["Forum", "Market"]
