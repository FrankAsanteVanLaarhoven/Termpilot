from __future__ import annotations

from httpx import AsyncClient


async def test_me_and_task_invite(client: AsyncClient) -> None:
    await client.post("/demo/reset")
    me = (await client.get("/me")).json()
    assert me["display_name"] == "Frank Van Laarhoven"
    assert me["username"] == "FAVL"
    assert me["synthetic"] is True
    await client.post(
        "/command",
        json={"text": "reconcile my next 14 days and ask before changing my calendar"},
    )
    items = (await client.get("/obligations")).json()["items"]
    obl = items[0]["obligation_id"]
    invited = await client.post(
        "/collaborate/invite",
        json={"to_code": "usr_okonkwo", "obligation_id": obl, "note": "Lab pairing"},
    )
    assert invited.status_code == 200
    listed = (await client.get("/collaborate")).json()
    assert listed["items"]
    assert listed["items"][0]["to_name"] == "S. Okonkwo"
