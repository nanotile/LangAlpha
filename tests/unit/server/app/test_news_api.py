"""Tests for the News API router (src/server/app/news.py).

Focus: the ``provider`` query param routes to a single named source
(``get_news_source``) and bypasses the fallback chain
(``get_news_data_provider``), with a provider-scoped cache key.
"""

from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from tests.conftest import create_test_app

pytestmark = pytest.mark.asyncio

ARTICLE = {
    "id": "abc123",
    "title": "Top story",
    "author": None,
    "description": "d",
    "published_at": "2025-12-01T00:00:00+00:00",
    "article_url": "https://example.com/a",
    "image_url": None,
    "source": {"name": "investing.com", "logo_url": None, "homepage_url": None, "favicon_url": None},
    "tickers": ["TSLA"],
    "keywords": [],
    "sentiments": None,
}


@pytest_asyncio.fixture
async def client():
    from src.server.app.news import router

    app = create_test_app(router)
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as c:
        yield c


async def test_provider_routes_to_named_source(client):
    """provider=tickertick → get_news_source, NOT the fallback chain."""
    source = AsyncMock()
    source.get_news.return_value = {"results": [ARTICLE], "count": 1, "next_cursor": None}
    cache = AsyncMock()
    cache.get = AsyncMock(return_value=None)
    cache.set = AsyncMock()

    with (
        patch("src.server.app.news._cache", cache),
        patch("src.data_client.get_news_source", AsyncMock(return_value=source)) as get_source,
        patch("src.data_client.get_news_data_provider", AsyncMock()) as get_chain,
    ):
        resp = await client.get("/api/v1/news?provider=tickertick&limit=5")

    assert resp.status_code == 200
    body = resp.json()
    assert body["count"] == 1
    assert body["results"][0]["id"] == "abc123"
    get_source.assert_awaited_once_with("tickertick")
    get_chain.assert_not_called()
    # Cache key is provider-scoped.
    assert cache.get.await_args.kwargs.get("provider") == "tickertick"
    assert cache.set.await_args.kwargs.get("provider") == "tickertick"


async def test_compact_inlines_article_body(client):
    """The compact list response carries description/keywords/sentiments/author so
    the detail modal renders without a by-id round-trip."""
    rich = {
        **ARTICLE,
        "author": "Jane Doe",
        "description": "A full summary paragraph.",
        "keywords": ["ev", "earnings"],
        "sentiments": [{"ticker": "TSLA", "sentiment": "positive", "reasoning": "beat"}],
    }
    source = AsyncMock()
    source.get_news.return_value = {"results": [rich], "count": 1, "next_cursor": None}
    cache = AsyncMock()
    cache.get = AsyncMock(return_value=None)
    cache.set = AsyncMock()

    with (
        patch("src.server.app.news._cache", cache),
        patch("src.data_client.get_news_source", AsyncMock(return_value=source)),
        patch("src.data_client.get_news_data_provider", AsyncMock()),
    ):
        resp = await client.get("/api/v1/news?provider=tickertick&limit=5")

    assert resp.status_code == 200
    row = resp.json()["results"][0]
    assert row["author"] == "Jane Doe"
    assert row["description"] == "A full summary paragraph."
    assert row["keywords"] == ["ev", "earnings"]
    assert row["sentiments"][0]["ticker"] == "TSLA"
    assert row["has_sentiment"] is True


async def test_no_provider_uses_chain(client):
    """No provider → the fallback chain, provider passed as None to the cache."""
    chain = AsyncMock()
    chain.get_news.return_value = {"results": [ARTICLE], "count": 1, "next_cursor": None}
    cache = AsyncMock()
    cache.get = AsyncMock(return_value=None)
    cache.set = AsyncMock()

    with (
        patch("src.server.app.news._cache", cache),
        patch("src.data_client.get_news_source", AsyncMock()) as get_source,
        patch("src.data_client.get_news_data_provider", AsyncMock(return_value=chain)) as get_chain,
    ):
        resp = await client.get("/api/v1/news?limit=5")

    assert resp.status_code == 200
    get_chain.assert_awaited_once()
    get_source.assert_not_called()
    assert cache.get.await_args.kwargs.get("provider") is None
