"""Async unit tests for the FastAPI server.

Uses pytest + pytest-asyncio and httpx's AsyncClient over the ASGI transport,
so requests hit the app IN-PROCESS — no running server, no real port. Mirrors
the Node side where unit tests never need `uv run fastapi dev`.
"""

import pytest
from httpx import ASGITransport, AsyncClient

from src.rest.main import app

pytestmark = pytest.mark.asyncio


async def _client() -> AsyncClient:
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


class TestHealth:
    async def test_health_returns_ok(self):
        async with await _client() as client:
            res = await client.get("/health")
        assert res.status_code == 200
        body = res.json()
        assert body["status"] == "ok"
        assert body["service"] == "fastapi"
        assert body["timestamp"]


class TestEcho:
    async def test_echoes_valid_message(self):
        async with await _client() as client:
            res = await client.post("/echo", json={"message": "hello"})
        assert res.status_code == 200
        body = res.json()
        assert body["received"] == "hello"
        assert body["length"] == 5
        assert body["timestamp"]

    async def test_missing_message_is_422(self):
        # Pydantic rejects a missing required field -> FastAPI's 422.
        async with await _client() as client:
            res = await client.post("/echo", json={})
        assert res.status_code == 422

    async def test_empty_message_is_422(self):
        # The field_validator rejects empty/whitespace -> validation error (422).
        async with await _client() as client:
            res = await client.post("/echo", json={"message": "   "})
        assert res.status_code == 422

    async def test_non_string_message_is_422(self):
        async with await _client() as client:
            res = await client.post("/echo", json={"message": 123})
        assert res.status_code == 422
