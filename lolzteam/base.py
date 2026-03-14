"""
lolzteam.base
~~~~~~~~~~~~~
``BaseClient`` provides the unified sync/async facade that
:class:`~lolzteam.forum.Forum` and :class:`~lolzteam.market.Market`
both inherit from.

Design goals
------------
* A single constructor works in both sync and async contexts.
* Switching between sync/async is transparent: ``await client.method()``
  works exactly like ``client.method()`` after you call
  ``client.use_async()``.
* Proxy and token can be changed at runtime without recreating the client.
"""
from __future__ import annotations

import inspect
import logging
from typing import Any

import httpx

from ._core.client import AsyncLolzteamClient, LolzteamClient

log = logging.getLogger("lolzteam")


class BaseClient:
    """
    Common base for Forum and Market clients.

    Parameters
    ----------
    base_url:
        API root URL.
    token:
        Bearer token.
    language:
        Response language (``"ru"`` or ``"en"``).
    proxy:
        Optional proxy string, e.g.
        ``"socks5://user:pass@host:port"`` or ``"http://host:port"``.
    timeout:
        HTTP request timeout in seconds.
    delay:
        Minimum seconds between consecutive requests.
        ``None`` disables artificial throttling.
    async_mode:
        Start in async mode.  If ``False`` (default) the sync client is
        used; ``True`` activates the async client.
    """

    def __init__(
        self,
        base_url: str,
        token: str,
        language: str = "en",
        proxy: str | None = None,
        timeout: float = 30.0,
        delay: float | None = None,
        async_mode: bool = False,
    ) -> None:
        self._base_url = base_url
        self._token = token
        self._language = language
        self._proxy = proxy
        self._timeout = timeout
        self._delay = delay
        self._async_mode = async_mode

        if async_mode:
            self._http: LolzteamClient | AsyncLolzteamClient = AsyncLolzteamClient(
                base_url, token, language, proxy, timeout, delay
            )
        else:
            self._http = LolzteamClient(
                base_url, token, language, proxy, timeout, delay
            )

        # Inject _http into every ApiMixin sub-attribute
        self._inject_http()

    # ------------------------------------------------------------------
    # Settings API  (mirrors the existing LOLZTEAM library's interface)
    # ------------------------------------------------------------------

    @property
    def token(self) -> str:
        return self._token

    @token.setter
    def token(self, value: str) -> None:
        self._token = value
        self._http.token = value

    @property
    def language(self) -> str:
        return self._language

    @language.setter
    def language(self, value: str) -> None:
        self._language = value
        self._http.language = value

    @property
    def proxy(self) -> str | None:
        return self._proxy

    @proxy.setter
    def proxy(self, value: str | None) -> None:
        self._proxy = value
        if isinstance(self._http, AsyncLolzteamClient):
            import asyncio
            asyncio.get_event_loop().run_until_complete(
                self._http.set_proxy(value)
            )
        else:
            self._http.proxy = value  # type: ignore[assignment]

    def use_async(self) -> "BaseClient":
        """Switch to async mode (returns self for chaining)."""
        if not self._async_mode:
            if isinstance(self._http, LolzteamClient):
                self._http.close()
            self._http = AsyncLolzteamClient(
                self._base_url, self._token, self._language,
                self._proxy, self._timeout, self._delay,
            )
            self._async_mode = True
            self._inject_http()
        return self

    def use_sync(self) -> "BaseClient":
        """Switch back to sync mode (returns self for chaining)."""
        if self._async_mode:
            self._http = LolzteamClient(
                self._base_url, self._token, self._language,
                self._proxy, self._timeout, self._delay,
            )
            self._async_mode = False
            self._inject_http()
        return self

    # ------------------------------------------------------------------
    # Raw request passthrough
    # ------------------------------------------------------------------

    def request(
        self,
        method: str,
        path: str,
        **kwargs: Any,
    ) -> Any:
        """
        Send a raw request.  Works both sync and async depending on the
        current mode.

        Example
        -------
        ::

            # sync
            resp = client.request("GET", "/users/me")
            print(resp.json())

            # async
            resp = await client.request("GET", "/users/me")
        """
        return self._http.request(method, path, **kwargs)

    # ------------------------------------------------------------------
    # Context managers
    # ------------------------------------------------------------------

    def __enter__(self) -> "BaseClient":
        return self

    def __exit__(self, *_: Any) -> None:
        if isinstance(self._http, LolzteamClient):
            self._http.close()

    async def __aenter__(self) -> "BaseClient":
        return self

    async def __aexit__(self, *_: Any) -> None:
        if isinstance(self._http, AsyncLolzteamClient):
            await self._http.aclose()

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _inject_http(self) -> None:
        """Push the current _http into every ApiMixin attribute."""
        from ._core.mixin import ApiMixin

        http = object.__getattribute__(self, "_http")
        for attr_name in list(self.__dict__.keys()):
            if attr_name.startswith("_"):
                continue
            try:
                attr = object.__getattribute__(self, attr_name)
            except AttributeError:
                continue
            if isinstance(attr, ApiMixin):
                attr._http = http
