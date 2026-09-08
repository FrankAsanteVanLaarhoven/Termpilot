from __future__ import annotations

from httpx import AsyncClient


async def test_reset_is_repeatable(client: AsyncClient) -> None:
    first = await client.post("/demo/reset")
    second = await client.post("/demo/reset")
    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["user_id"] == second.json()["user_id"]
