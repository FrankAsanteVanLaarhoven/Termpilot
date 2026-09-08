from __future__ import annotations

from app.services.feeds import ROLE_NOTE, UNIVERSITY_LOCK, parse_feed_xml
from app.services.voicebridge import classify_intent
from httpx import AsyncClient

RSS_SAMPLE = """<?xml version="1.0"?>
<rss version="2.0"><channel>
<title>Sample</title>
<item>
  <title>Student visa deadline reminder</title>
  <link>https://www.gov.uk/student-visa</link>
  <description>Official guidance</description>
  <pubDate>Mon, 01 Sep 2026 10:00:00 GMT</pubDate>
</item>
</channel></rss>
"""

ATOM_SAMPLE = """<?xml version="1.0"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <title>DfE</title>
  <entry>
    <title>Education policy update</title>
    <link href="https://www.gov.uk/government/organisations/department-for-education"/>
    <published>2026-09-01T10:00:00Z</published>
    <summary>Official notice</summary>
  </entry>
</feed>
"""


def test_parse_rss_and_atom() -> None:
    rss = parse_feed_xml(
        RSS_SAMPLE, channel="government", source_label="GOV.UK", source_url="https://example.test/rss"
    )
    assert rss[0]["title"] == "Student visa deadline reminder"
    assert rss[0]["url"] == "https://www.gov.uk/student-visa"
    assert rss[0]["priority"] == "asap"
    atom = parse_feed_xml(
        ATOM_SAMPLE, channel="government", source_label="DfE", source_url="https://example.test/atom"
    )
    assert atom[0]["title"] == "Education policy update"
    assert "gov.uk" in atom[0]["url"]


def test_news_intent() -> None:
    assert classify_intent("show the newsfeed") == "open_news"
    assert classify_intent("student union") == "open_news"
    assert classify_intent("international students") == "open_news"
    assert classify_intent("I am overwhelmed") == "support"


async def test_feeds_include_public_and_university_when_email_linked(client: AsyncClient) -> None:
    await client.post("/demo/reset")
    response = await client.get("/feeds")
    assert response.status_code == 200
    body = response.json()
    assert ROLE_NOTE.split("dean")[0] in body["role_note"]
    assert "dean" in body["role_note"].lower()
    assert "not speak as the dean" in body["role_note"]
    assert "crisis" in body["crisis_note"].lower()
    assert body["university_authorised"] is True
    assert body["university_lock"] is None
    channels = {item["channel"] for item in body["items"]}
    assert "university" in channels
    groups = {link["group"] for link in body["directory"]}
    assert groups >= {"student_union", "career", "wellbeing", "student_support", "international", "community"}
    assert any(item["id"] == "uni-international" for item in body["items"])
    assert any(item.get("priority") == "asap" for item in body["items"])
    assert any("ukcisa.org.uk" in (link["url"] or "") for link in body["directory"])
    for item in body["items"]:
        if item["channel"] != "university":
            assert item.get("url")
            assert item.get("source_label")


async def test_university_news_requires_linked_university_email(client: AsyncClient) -> None:
    await client.post("/demo/reset")
    revoked = await client.post("/connectors/src_email/disconnect")
    assert revoked.status_code == 200
    body = (await client.get("/feeds")).json()
    assert body["university_authorised"] is False
    assert body["university_lock"] == UNIVERSITY_LOCK
    assert all(item["channel"] != "university" for item in body["items"])
    restored = await client.post("/connectors/src_email/connect")
    assert restored.status_code == 200
    again = (await client.get("/feeds")).json()
    assert again["university_authorised"] is True
    assert any(item["channel"] == "university" for item in again["items"])


async def test_voice_opens_news_view(client: AsyncClient) -> None:
    await client.post("/demo/reset")
    body = (
        await client.post(
            "/voicebridge/turn",
            json={"text": "show the newsfeed", "language": "en"},
        )
    ).json()
    assert body["facts"]["open_view"] == "news"
    assert "union" in body["display_text"].lower() or "dean" in body["display_text"].lower()
