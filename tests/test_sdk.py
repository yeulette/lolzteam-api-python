"""
tests/test_sdk.py
-----------------
Unit tests for the lolzteam SDK.
Uses `respx` to mock httpx transports – no real network requests are made.
"""
from __future__ import annotations

import asyncio
import json

import httpx
import pytest
import respx

from lolzteam import Forum, Market
from lolzteam._core.client import LolzteamClient, AsyncLolzteamClient

FORUM_BASE = "https://prod-api.lolz.live"
MARKET_BASE = "https://api.lzt.market"

TOKEN = "test_token_abc123"


# ============================================================================
# helpers
# ============================================================================

def _ok(payload: dict) -> httpx.Response:
    return httpx.Response(200, json=payload)


def _rate_limited(retry_after: float = 0.01) -> httpx.Response:
    return httpx.Response(429, headers={"Retry-After": str(retry_after)}, json={"error": "rate limit"})


# ============================================================================
# Sync client – core
# ============================================================================

class TestSyncClient:
    def test_bearer_header(self):
        with respx.mock(base_url=FORUM_BASE) as mock:
            mock.get("/users/me").mock(return_value=_ok({"user": {"user_id": 1}}))
            client = LolzteamClient(FORUM_BASE, TOKEN)
            resp = client.request("GET", "/users/me")
            assert resp.status_code == 200
            # Verify auth header was sent
            assert mock.calls[0].request.headers["Authorization"] == f"Bearer {TOKEN}"
            client.close()

    def test_retry_on_429(self):
        responses = [_rate_limited(0.01), _rate_limited(0.01), _ok({"ok": True})]
        call_count = 0

        def handler(_request):
            nonlocal call_count
            call_count += 1
            return responses[min(call_count - 1, len(responses) - 1)]

        with respx.mock(base_url=FORUM_BASE) as mock:
            mock.get("/users/me").mock(side_effect=handler)
            client = LolzteamClient(FORUM_BASE, TOKEN)
            resp = client.request("GET", "/users/me")
            assert resp.status_code == 200
            assert call_count == 3
            client.close()

    def test_token_change(self):
        with respx.mock(base_url=FORUM_BASE) as mock:
            mock.get("/users/me").mock(return_value=_ok({}))
            client = LolzteamClient(FORUM_BASE, TOKEN)
            client.token = "new_token"
            client.request("GET", "/users/me")
            assert mock.calls[0].request.headers["Authorization"] == "Bearer new_token"
            client.close()

    def test_language_header(self):
        with respx.mock(base_url=FORUM_BASE) as mock:
            mock.get("/users/me").mock(return_value=_ok({}))
            client = LolzteamClient(FORUM_BASE, TOKEN, language="ru")
            client.request("GET", "/users/me")
            assert mock.calls[0].request.headers["Accept-Language"] == "ru"
            client.close()


# ============================================================================
# Async client – core
# ============================================================================

class TestAsyncClient:
    @pytest.mark.asyncio
    async def test_async_bearer(self):
        with respx.mock(base_url=FORUM_BASE) as mock:
            mock.get("/users/me").mock(return_value=_ok({"user": {}}))
            async with AsyncLolzteamClient(FORUM_BASE, TOKEN) as client:
                resp = await client.request("GET", "/users/me")
                assert resp.status_code == 200
                assert mock.calls[0].request.headers["Authorization"] == f"Bearer {TOKEN}"

    @pytest.mark.asyncio
    async def test_async_retry_on_429(self):
        responses = [_rate_limited(0.01), _ok({"ok": True})]
        call_count = 0

        def handler(_request):
            nonlocal call_count
            r = responses[min(call_count, len(responses) - 1)]
            call_count += 1
            return r

        with respx.mock(base_url=FORUM_BASE) as mock:
            mock.get("/ping").mock(side_effect=handler)
            async with AsyncLolzteamClient(FORUM_BASE, TOKEN) as client:
                resp = await client.request("GET", "/ping")
                assert resp.status_code == 200
                assert call_count == 2


# ============================================================================
# High-level Forum client
# ============================================================================

class TestForum:
    def test_users_get(self):
        with respx.mock(base_url=FORUM_BASE) as mock:
            mock.get("/users/42").mock(return_value=_ok({"user": {"user_id": 42}}))
            forum = Forum(token=TOKEN)
            resp = forum.users_get(user_id=42)
            assert resp.json()["user"]["user_id"] == 42

    def test_threads_get(self):
        with respx.mock(base_url=FORUM_BASE) as mock:
            mock.get("/threads/123").mock(return_value=_ok({"thread": {"thread_id": 123}}))
            forum = Forum(token=TOKEN)
            resp = forum.threads_get(thread_id=123)
            assert resp.status_code == 200

    def test_threads_list(self):
        with respx.mock(base_url=FORUM_BASE) as mock:
            mock.get("/threads").mock(return_value=_ok({"threads": []}))
            forum = Forum(token=TOKEN)
            resp = forum.threads_list()
            assert resp.status_code == 200

    def test_token_setter(self):
        with respx.mock(base_url=FORUM_BASE) as mock:
            mock.get("/users/42").mock(return_value=_ok({}))
            forum = Forum(token=TOKEN)
            forum.token = "changed"
            forum.users_get(user_id=42)
            assert mock.calls[0].request.headers["Authorization"] == "Bearer changed"

    def test_context_manager(self):
        with respx.mock(base_url=FORUM_BASE) as mock:
            mock.get("/threads/1").mock(return_value=_ok({}))
            with Forum(token=TOKEN) as forum:
                forum.threads_get(thread_id=1)

    @pytest.mark.asyncio
    async def test_async_mode(self):
        with respx.mock(base_url=FORUM_BASE) as mock:
            mock.get("/threads/1").mock(return_value=_ok({"thread": {}}))
            forum = Forum(token=TOKEN, async_mode=True)
            resp = await forum.threads_get(thread_id=1)
            assert resp.status_code == 200
            await forum._http.aclose()


# ============================================================================
# High-level Market client
# ============================================================================

class TestMarket:
    def test_get_me(self):
        with respx.mock(base_url=MARKET_BASE) as mock:
            mock.get("/me").mock(return_value=_ok({"user": {"user_id": 7}}))
            market = Market(token=TOKEN)
            resp = market.get_me()
            assert resp.json()["user"]["user_id"] == 7

    def test_get_item(self):
        with respx.mock(base_url=MARKET_BASE) as mock:
            mock.get("/12345678").mock(return_value=_ok({"item": {"item_id": 12345678}}))
            market = Market(token=TOKEN)
            resp = market.get_item(item_id=12345678)
            assert resp.status_code == 200

    def test_get_payments(self):
        with respx.mock(base_url=MARKET_BASE) as mock:
            mock.get("/payments").mock(return_value=_ok({"payments": []}))
            market = Market(token=TOKEN)
            resp = market.get_payments(page=1, limit=20)
            assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_async_get_me(self):
        with respx.mock(base_url=MARKET_BASE) as mock:
            mock.get("/me").mock(return_value=_ok({"user": {}}))
            market = Market(token=TOKEN, async_mode=True)
            resp = await market.get_me()
            assert resp.status_code == 200
            await market._http.aclose()


# ============================================================================
# use_async / use_sync switching
# ============================================================================

class TestModeSwitching:
    def test_switch_to_async_and_back(self):
        forum = Forum(token=TOKEN)
        assert isinstance(forum._http, LolzteamClient)
        forum.use_async()
        assert isinstance(forum._http, AsyncLolzteamClient)
        forum.use_sync()
        assert isinstance(forum._http, LolzteamClient)
        forum._http.close()
