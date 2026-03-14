"""
lolzteam._core.mixin
~~~~~~~~~~~~~~~~~~~~
``ApiMixin`` is the base class for all auto-generated API classes.
It wires the ``_request`` helper to whichever underlying HTTP client
(sync or async) is provided by the parent :class:`~lolzteam.base.BaseClient`.
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Any

import httpx

if TYPE_CHECKING:
    from .client import AsyncLolzteamClient, LolzteamClient


class ApiMixin:
    """Shared request dispatch for generated API classes.

    The owner (Forum / Market) injects ``_http`` during construction.
    """

    _http: "LolzteamClient | AsyncLolzteamClient"

    def _request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        json: dict[str, Any] | None = None,
        data: dict[str, Any] | None = None,
        files: dict | None = None,
    ) -> Any:
        """
        Dispatch the request.

        Returns an :class:`httpx.Response` for sync clients and a
        coroutine for async clients (which also resolves to
        :class:`httpx.Response`).
        """
        return self._http.request(
            method,
            path,
            params=params,
            json=json,
            data=data,
            files=files,
        )
