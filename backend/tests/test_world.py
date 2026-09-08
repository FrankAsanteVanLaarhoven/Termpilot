from __future__ import annotations

from app.services.world import fx_convert, world_clock
from httpx import AsyncClient


def test_world_clock_has_london_and_lagos() -> None:
    payload = world_clock()
    labels = {row["label"] for row in payload["items"]}
    assert "London" in labels
    assert "Lagos" in labels
    assert "UTC" in labels


async def test_fx_endpoint_returns_conversion_or_stale(client: AsyncClient) -> None:
    await client.post("/demo/reset")
    response = await client.get("/fx", params={"amount": 10, "base": "GBP", "quote": "EUR"})
    assert response.status_code == 200
    body = response.json()
    assert body["base"] == "GBP"
    assert body["quote"] == "EUR"
    assert body["converted"] is not None


async def test_fx_offline_fixture_never_invents_when_unknown() -> None:
    result = await fx_convert(5, "GBP", "EUR")
    assert result["converted"] is not None
    assert result["source"] in {"open.er-api.com", "offline_fixture"}
