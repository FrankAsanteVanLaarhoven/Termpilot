from __future__ import annotations

from httpx import AsyncClient


async def test_demo_metrics_are_labelled(client: AsyncClient) -> None:
    await client.post("/demo/reset")
    response = await client.get("/metrics/demo")
    body = response.json()
    assert body["kind"] == "demo"
    assert "Not a student pilot" in body["disclaimer"]


async def test_pilot_metrics_are_empty_until_collected(client: AsyncClient) -> None:
    await client.post("/demo/reset")
    response = await client.get("/metrics/impact")
    body = response.json()
    assert "No pilot results recorded" in body["pilot"]["disclaimer"]
    assert body["pilot"]["sessions"] == []
