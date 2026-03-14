"""
lolzteam.market
~~~~~~~~~~~~~~~
High-level client for the ZT.MARKET API (https://api.lzt.market).

Usage
-----
Sync::

    from lolzteam import Market

    market = Market(token="YOUR_TOKEN")
    resp = market.profile.get()
    print(resp.json())

Async::

    import asyncio
    from lolzteam import Market

    market = Market(token="YOUR_TOKEN", async_mode=True)

    async def main():
        resp = await market.profile.get()
        print(resp.json())

    asyncio.run(main())
"""
from __future__ import annotations

from ..base import BaseClient
from ._generated import MarketAPI

_BASE_URL = "https://api.lzt.market"


class Market(BaseClient):
    """
    ZT.MARKET API client.

    Parameters
    ----------
    token:
        Your API bearer token.
    language:
        Response language: ``"ru"`` or ``"en"``.
    proxy:
        Optional proxy, e.g. ``"socks5://user:pass@host:port"``.
    timeout:
        HTTP timeout in seconds.
    delay:
        Minimum seconds between requests (``None`` = no throttle).
    async_mode:
        Pass ``True`` to operate in async mode.
    """

    def __init__(
        self,
        token: str,
        language: str = "en",
        proxy: str | None = None,
        timeout: float = 30.0,
        delay: float | None = 0.5,
        async_mode: bool = False,
    ) -> None:
        super().__init__(
            base_url=_BASE_URL,
            token=token,
            language=language,
            proxy=proxy,
            timeout=timeout,
            delay=delay,
            async_mode=async_mode,
        )
        self._api = MarketAPI()
        self._api._http = self._http

    def __getattr__(self, name: str):
        try:
            api = object.__getattribute__(self, "_api")
            return getattr(api, name)
        except AttributeError:
            raise AttributeError(
                f"'{type(self).__name__}' object has no attribute '{name}'"
            ) from None

    def _inject_http(self) -> None:
        super()._inject_http()
        try:
            api = object.__getattribute__(self, "_api")
            api._http = object.__getattribute__(self, "_http")
        except AttributeError:
            pass
