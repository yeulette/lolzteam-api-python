# lolzteam Python SDK

[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Tests](https://github.com/your-org/lolzteam-python/actions/workflows/publish.yml/badge.svg)](https://github.com/your-org/lolzteam-python/actions)

Python SDK for the [LOLZ Forum](https://lolz.live) and [ZT.Market](https://lzt.market) APIs.

- ✅ Full **sync and async** support (`httpx`)
- ✅ **Proxy** support (HTTP, HTTPS, SOCKS5)
- ✅ Automatic **retry** on 429 / 502 / 503 with exponential back-off
- ✅ Methods **auto-generated** from official OpenAPI schemas
- ✅ Type annotations throughout
- ✅ MIT licence

---

## Quick start

### Synchronous

```python
from lolzteam import Forum, Market

forum  = Forum(token="YOUR_TOKEN")
market = Market(token="YOUR_TOKEN")

# Get your forum profile
me = forum.get_users_me().json()
print(me)

# Get a market item
item = market.get_item(item_id=12345678).json()
print(item)
```

### Asynchronous

```python
import asyncio
from lolzteam import Forum, Market

async def main():
    forum  = Forum(token="YOUR_TOKEN",  async_mode=True)
    market = Market(token="YOUR_TOKEN", async_mode=True)

    me   = (await forum.get_users_me()).json()
    item = (await market.get_item(item_id=12345678)).json()
    print(me, item)

    await forum._http.aclose()
    await market._http.aclose()

asyncio.run(main())
```

### Context managers

```python
# Sync
with Forum(token="YOUR_TOKEN") as forum:
    resp = forum.get_threads(forum_id=876, limit=10)

# Async
async with Forum(token="YOUR_TOKEN", async_mode=True) as forum:
    resp = await forum.get_threads(forum_id=876, limit=10)
```

---

## Client parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `token` | `str` | **required** | Bearer token |
| `language` | `str` | `"en"` | Response language (`"ru"` or `"en"`) |
| `proxy` | `str \| None` | `None` | Proxy URL (see below) |
| `timeout` | `float` | `30.0` | HTTP timeout (seconds) |
| `delay` | `float \| None` | `0.5` | Minimum delay between requests |
| `async_mode` | `bool` | `False` | Start in async mode |

### Proxy examples

```python
# HTTP proxy
forum = Forum(token="YOUR_TOKEN", proxy="http://user:pass@host:8080")

# SOCKS5 proxy
forum = Forum(token="YOUR_TOKEN", proxy="socks5://user:pass@host:1080")

# Change proxy at runtime
forum.proxy = "socks5://new-host:1080"

# Disable proxy
forum.proxy = None
```

---

## Runtime settings

```python
forum = Forum(token="YOUR_TOKEN")

forum.token    = "NEW_TOKEN"   # Change token
forum.language = "ru"          # Change language

forum.use_async()   # Switch to async mode
forum.use_sync()    # Switch back to sync mode
```

---

## Forum API examples

```python
forum = Forum(token="YOUR_TOKEN")

# Users
me         = forum.get_users_me().json()
user       = forum.get_users(user_id=2410024).json()
followers  = forum.get_users_followers(user_id=2410024, page=1, limit=10).json()

# Threads
threads = forum.get_threads(forum_id=876, limit=20).json()
thread  = forum.get_threads_by_thread_id(thread_id=1234567).json()

new_thread = forum.post_threads(
    forum_id=876,
    thread_title="Hello World",
    post_body="My first thread via SDK.",
).json()

# Posts
posts    = forum.get_posts(thread_id=1234567).json()
new_post = forum.post_posts(thread_id=1234567, post_body="Reply via SDK").json()

# Private messages
convs = forum.get_conversations().json()
new_conv = forum.post_conversations(
    recipient_id=2410024,
    message_body="Hi!",
    conversation_title="Hello",
).json()
```

---

## Market API examples

```python
market = Market(token="YOUR_TOKEN")

# Profile
me = market.get_me().json()

# Items
items = market.get_items(page=1, limit=50, order_by="price", order="asc").json()
item  = market.get_item(item_id=12345678).json()

# Buy
result = market.post_item_buy(
    item_id=12345678,
    price=500.0,
    currency="rub",
).json()

# Edit your listing
market.put_item_edit(
    item_id=12345678,
    title="Updated Title",
    price=450.0,
    currency="rub",
)

# Payments
payments = market.get_payments(page=1, limit=20).json()

# Transfer funds
market.post_transfer(
    receiver="username",
    currency="rub",
    amount=100.0,
    comment="Thanks!",
)
```

---

## Raw requests

Both clients expose a `request()` method for endpoints not yet in the generated layer:

```python
# Sync
resp = forum.request("GET", "/users/me")
resp = forum.request("POST", "/posts", json={"thread_id": 1, "post_body": "Hi"})

# Async
resp = await forum.request("GET", "/users/me")
```

---

## Code generation

All API methods are generated from the official OpenAPI schemas.  To regenerate:

```bash
# Download latest schemas
curl -o codegen/schemas/forum.json  https://raw.githubusercontent.com/AS7RIDENIED/LOLZTEAM/main/Official%20Documentation/forum.json
curl -o codegen/schemas/market.json https://raw.githubusercontent.com/AS7RIDENIED/LOLZTEAM/main/Official%20Documentation/market.json

# Run generator
python codegen/generate.py \
    --schema codegen/schemas/forum.json \
    --output lolzteam/forum/_generated.py \
    --class ForumAPI

python codegen/generate.py \
    --schema codegen/schemas/market.json \
    --output lolzteam/market/_generated.py \
    --class MarketAPI
```

The generator is also run automatically by GitHub Actions on every tagged release.

---

## Running tests

```bash
pip install -e ".[dev]"
pytest
```

---

## Release workflow

Tag a commit to trigger the CI/CD pipeline:

```bash
git tag v1.0.1
git push origin v1.0.1
```

GitHub Actions will:
1. Run the test matrix (Python 3.9–3.12)
2. Regenerate API methods from the latest OpenAPI schemas
3. Build the distribution
4. Publish to PyPI via Trusted Publishing (no API key needed)

---

## Project structure

```
lolzteam-python/
├── codegen/
│   ├── generate.py          ← OpenAPI → Python code generator
│   └── schemas/             ← Place forum.json & market.json here
├── lolzteam/
│   ├── __init__.py          ← Public API: Forum, Market
│   ├── base.py              ← Shared BaseClient
│   ├── _core/
│   │   ├── client.py        ← LolzteamClient / AsyncLolzteamClient
│   │   └── mixin.py         ← ApiMixin (bridges generated code → transport)
│   ├── forum/
│   │   ├── __init__.py      ← Forum class
│   │   └── _generated.py    ← AUTO-GENERATED Forum methods
│   └── market/
│       ├── __init__.py      ← Market class
│       └── _generated.py    ← AUTO-GENERATED Market methods
├── tests/
│   └── test_sdk.py
├── .github/
│   └── workflows/
│       └── publish.yml      ← CI/CD: test → codegen → PyPI
├── pyproject.toml
└── README.md
```

---

## License

MIT © lolzteam-sdk contributors
