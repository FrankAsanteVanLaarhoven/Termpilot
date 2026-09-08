from __future__ import annotations

from app.services.exporting import next_page_url
from app.services.formatter import format_record, hash_identifier, strip_html
from app.services.llm import catalog, resolve
from httpx import AsyncClient


def test_formatter_strips_html_and_hashes_mail() -> None:
    assert "<" not in strip_html("<p>Hello <b>lab</b></p>")
    hashed = hash_identifier("info@frankvanlaarhoven.co.uk")
    assert hashed.startswith("h_")
    assert "frank" not in hashed
    row = format_record({"from": "a@b.c", "body": "<div>secret@x.com hi</div>"})
    assert row["from"].startswith("h_")
    assert "@" not in row["body"]


def test_next_page_is_public_feed_only() -> None:
    xml = '<feed><link rel="next" href="https://example.test/page2"/></feed>'
    assert next_page_url(xml) == "https://example.test/page2"
    assert next_page_url("<html>no portal scrape</html>") is None


def test_grok_is_native_and_max_is_locked() -> None:
    pack = catalog(student_openrouter=False)
    assert pack["native"] == "grok"
    grok = next(row for row in pack["models"] if row["id"] == "grok-4.6")
    assert grok["provider"] == "grok"
    locked = next(row for row in pack["models"] if row["id"] == "claude-opus-5")
    assert locked["locked"] is True
    council = next(row for row in pack["tools"] if row["id"] == "model_council")
    assert council["locked"] is True
    best = resolve("best")
    assert best["ok"] is True
    assert best["provider"] == "grok"


async def test_export_json_hashes_and_omits_raw_bodies(client: AsyncClient) -> None:
    await client.post("/demo/reset")
    body = (await client.post("/export", json={"destination": "json"})).json()
    assert body["raw_bodies_stored"] is False
    assert body["payload_hash"]
    assert "smtp" not in str(body).lower() or body["destination"] == "json"


async def test_llm_catalog_endpoint(client: AsyncClient) -> None:
    body = (await client.get("/llm/catalog")).json()
    labels = {row["label"] for row in body["models"]}
    assert "Grok 4.6" in labels
    assert "Chat" in {row["label"] for row in body["modes"]}
    assert "Work" in {row["label"] for row in body["modes"]}
    assert "Computer" in {row["label"] for row in body["modes"]}
    assert body["keys_persisted"] is False
