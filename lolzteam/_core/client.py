"""
lolzteam._core.client
~~~~~~~~~~~~~~~~~~~~~
Low-level HTTP transport layer.

Features
--------
* Unified sync / async execution via httpx
* Automatic retry on 429 (rate-limit) and 502/503 (transient errors)
* Exponential back-off with jitter
* Proxy support (http, https, socks5)
* Token-based auth via Bearer header
* Configurable request timeout and per-client delay
"""
from __future__ import annotations

import asyncio
import logging
import random
import time
from typing import Any

import httpx

log = logging.getLogger("lolzteam")

_DEFAULT_TIMEOUT = 30.0
_RETRY_STATUSES = {429, 502, 503}
_MAX_RETRIES = 5
_BASE_BACKOFF = 1.0  # seconds


def _backoff(attempt: int) -> float:
    """Exponential back-off with full jitter: [0, base * 2^attempt]."""
    return random.uniform(0, _BASE_BACKOFF * (2 ** attempt))


def _build_headers(token: str, language: str) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {token}",
        "Accept-Language": language,
        "Accept": "application/json",
        "User-Agent": "lolzteam-python-sdk/1.0.0",
    }


class LolzteamClient:
    """
    Synchronous HTTP client for LOLZTEAM APIs.

    Parameters
    ----------
    base_url:
        Root URL, e.g. ``https://prod-api.lolz.live`` or ``https://api.lzt.market``.
    token:
        Bearer token for authentication.
    language:
        Response language, ``"ru"`` or ``"en"``.
    proxy:
        Proxy URL string, e.g. ``"socks5://user:pass@host:port"``
        or ``"http://host:port"``.
    timeout:
        Request timeout in seconds.
    delay:
        Minimum delay (seconds) between consecutive requests.  When ``None``
        no artificial delay is added.
    """

    def __init__(
        self,
        base_url: str,
        token: str,
        language: str = "en",
        proxy: str | None = None,
        timeout: float = _DEFAULT_TIMEOUT,
        delay: float | None = None,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._token = token
        self._language = language
        self._timeout = timeout
        self._delay = delay
        self._last_request_at: float = 0.0

        self._client = httpx.Client(
            base_url=self._base_url,
            headers=_build_headers(token, language),
            timeout=timeout,
            proxy=proxy,
        )

    # ------------------------------------------------------------------
    # public
    # ------------------------------------------------------------------

    @property
    def token(self) -> str:
        return self._token

    @token.setter
    def token(self, value: str) -> None:
        self._token = value
        self._client.headers["Authorization"] = f"Bearer {value}"

    @property
    def language(self) -> str:
        return self._language

    @language.setter
    def language(self, value: str) -> None:
        self._language = value
        self._client.headers["Accept-Language"] = value

    @property
    def proxy(self) -> str | None:
        return self._proxy_url

    @proxy.setter
    def proxy(self, value: str | None) -> None:
        # httpx does not support changing proxies on a live client;
        # we recreate it transparently.
        self._proxy_url = value
        self._client = httpx.Client(
            base_url=self._base_url,
            headers=_build_headers(self._token, self._language),
            timeout=self._timeout,
            proxy=value,
        )

    def request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        json: dict[str, Any] | None = None,
        data: dict[str, Any] | None = None,
        files: dict | None = None,
    ) -> httpx.Response:
        """Execute a synchronous request with automatic retry."""
        self._throttle_sync()
        url = path if path.startswith("http") else path
        for attempt in range(_MAX_RETRIES):
            log.debug("→ %s %s (attempt %d)", method, url, attempt + 1)
            resp = self._client.request(
                method, url, params=params, json=json, data=data, files=files
            )
            log.debug("← %s %s", resp.status_code, url)
            if resp.status_code not in _RETRY_STATUSES:
                return resp
            wait = self._retry_after(resp) or _backoff(attempt)
            log.warning("Rate limited (%s). Retrying in %.1fs…", resp.status_code, wait)
            time.sleep(wait)
        return resp  # return last response even if still failing

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> "LolzteamClient":
        return self

    def __exit__(self, *_: Any) -> None:
        self.close()

    # ------------------------------------------------------------------
    # private
    # ------------------------------------------------------------------

    def _throttle_sync(self) -> None:
        if self._delay is None:
            return
        elapsed = time.monotonic() - self._last_request_at
        if elapsed < self._delay:
            time.sleep(self._delay - elapsed)
        self._last_request_at = time.monotonic()

    @staticmethod
    def _retry_after(resp: httpx.Response) -> float | None:
        val = resp.headers.get("Retry-After")
        if val is None:
            return None
        try:
            return float(val)
        except ValueError:
            return None


class AsyncLolzteamClient:
    """
    Asynchronous HTTP client for LOLZTEAM APIs.

    Parameters
    ----------
    Same as :class:`LolzteamClient`.
    """

    def __init__(
        self,
        base_url: str,
        token: str,
        language: str = "en",
        proxy: str | None = None,
        timeout: float = _DEFAULT_TIMEOUT,
        delay: float | None = None,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._token = token
        self._language = language
        self._timeout = timeout
        self._delay = delay
        self._last_request_at: float = 0.0
        self._lock = asyncio.Lock()
        self._proxy_url = proxy

        self._client = httpx.AsyncClient(
            base_url=self._base_url,
            headers=_build_headers(token, language),
            timeout=timeout,
            proxy=proxy,
        )

    # ------------------------------------------------------------------
    # public
    # ------------------------------------------------------------------

    @property
    def token(self) -> str:
        return self._token

    @token.setter
    def token(self, value: str) -> None:
        self._token = value
        self._client.headers["Authorization"] = f"Bearer {value}"

    @property
    def language(self) -> str:
        return self._language

    @language.setter
    def language(self, value: str) -> None:
        self._language = value
        self._client.headers["Accept-Language"] = value

    async def set_proxy(self, value: str | None) -> None:
        """Replace the proxy.  Recreates the underlying httpx client."""
        await self._client.aclose()
        self._proxy_url = value
        self._client = httpx.AsyncClient(
            base_url=self._base_url,
            headers=_build_headers(self._token, self._language),
            timeout=self._timeout,
            proxy=value,
        )

    async def request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        json: dict[str, Any] | None = None,
        data: dict[str, Any] | None = None,
        files: dict | None = None,
    ) -> httpx.Response:
        """Execute an asynchronous request with automatic retry."""
        await self._throttle_async()
        url = path if path.startswith("http") else path
        for attempt in range(_MAX_RETRIES):
            log.debug("→ %s %s (attempt %d)", method, url, attempt + 1)
            resp = await self._client.request(
                method, url, params=params, json=json, data=data, files=files
            )
            log.debug("← %s %s", resp.status_code, url)
            if resp.status_code not in _RETRY_STATUSES:
                return resp
            wait = self._retry_after(resp) or _backoff(attempt)
            log.warning("Rate limited (%s). Retrying in %.1fs…", resp.status_code, wait)
            await asyncio.sleep(wait)
        return resp

    async def aclose(self) -> None:
        await self._client.aclose()

    async def __aenter__(self) -> "AsyncLolzteamClient":
        return self

    async def __aexit__(self, *_: Any) -> None:
        await self.aclose()

    # ------------------------------------------------------------------
    # private
    # ------------------------------------------------------------------

    async def _throttle_async(self) -> None:
        if self._delay is None:
            return
        async with self._lock:
            elapsed = time.monotonic() - self._last_request_at
            if elapsed < self._delay:
                await asyncio.sleep(self._delay - elapsed)
            self._last_request_at = time.monotonic()

    @staticmethod
    def _retry_after(resp: httpx.Response) -> float | None:
        val = resp.headers.get("Retry-After")
        if val is None:
            return None
        try:
            return float(val)
        except ValueError:
            return None
