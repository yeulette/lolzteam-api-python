"""
lolzteam.forum
~~~~~~~~~~~~~~
High-level client for the LOLZ forum API (https://prod-api.lolz.live).

Usage
-----
Sync::

    from lolzteam import Forum

    forum = Forum(token="YOUR_TOKEN")
    resp = forum.users.get(user_id=2410024)
    print(resp.json())

Async::

    import asyncio
    from lolzteam import Forum

    forum = Forum(token="YOUR_TOKEN", async_mode=True)

    async def main():
        resp = await forum.users.get(user_id=2410024)
        print(resp.json())

    asyncio.run(main())
"""
from __future__ import annotations

from ..base import BaseClient
from ._generated import ForumAPI

_BASE_URL = "https://prod-api.lolz.live"


class Forum(BaseClient):
    """
    LOLZ Forum API client.

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
        # Attach the auto-generated method namespace.
        # All ForumAPI methods are available directly on this object
        # via __getattr__ delegation below.
        self._api = ForumAPI()
        self._api._http = self._http

    # Delegate unknown attribute access to _api so callers can do
    # forum.get_users(…) for flat style.
    def __getattr__(self, name: str):
        # Use object.__getattribute__ to avoid triggering __getattr__ again
        try:
            api = object.__getattribute__(self, "_api")
            return getattr(api, name)
        except AttributeError:
            raise AttributeError(
                f"'{type(self).__name__}' object has no attribute '{name}'"
            ) from None

    def _inject_http(self) -> None:
        super()._inject_http()
        # Use object.__getattribute__ to safely check without recursion
        try:
            api = object.__getattribute__(self, "_api")
            api._http = object.__getattribute__(self, "_http")
        except AttributeError:
            pass
