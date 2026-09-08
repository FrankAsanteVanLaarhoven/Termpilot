from __future__ import annotations

from app.services.voicebridge import classify_intent, detect_language
from httpx import AsyncClient


def test_detect_dutch_and_spanish() -> None:
    assert detect_language("Wat moet ik deze week afmaken?", "auto")[0] == "nl"
    assert detect_language("Qué necesito terminar esta semana?", "auto")[0] == "es"
    assert detect_language("What do I need to finish this week?", "auto")[0] == "en"


def test_intent_classes() -> None:
    assert classify_intent("Move the Tuesday study session to Wednesday.") == "reschedule"
    assert classify_intent("yes") == "spoken_confirm"
    assert classify_intent("write my essay") == "blocked"
    assert classify_intent("open calendar") == "open_calendar"
    assert classify_intent("check email") == "email"
    assert classify_intent("show the newsfeed") == "open_news"
    assert classify_intent("student union") == "open_news"


async def test_week_answer_includes_five_w_and_smart(client: AsyncClient) -> None:
    await client.post("/demo/reset")
    await client.post(
        "/command",
        json={"text": "reconcile my next 14 days and ask before changing my calendar"},
    )
    body = (
        await client.post(
            "/voicebridge/turn",
            json={"text": "What do I need to finish this week?", "language": "en"},
        )
    ).json()
    assert set(body["facts"]["five_w"]) >= {"who", "what", "when", "where", "why", "how"}
    assert "specific" in body["facts"]["smart"]
    assert body["facts"]["empathy"]["note"]


async def test_week_question_preserves_module_codes(client: AsyncClient) -> None:
    await client.post("/demo/reset")
    await client.post(
        "/command",
        json={"text": "reconcile my next 14 days and ask before changing my calendar"},
    )
    response = await client.post(
        "/voicebridge/turn",
        json={"text": "What do I need to finish this week?", "language": "en", "source": "typed"},
    )
    assert response.status_code == 200
    body = response.json()
    blob = body["display_text"] + str(body["facts"])
    assert "CSC0000" in blob
    assert "ENG0001" in blob
    due = next(
        item["due_at"]
        for item in body["facts"]["obligations"]
        if item["title"] == "Robotics Lab Report"
    )
    assert due is not None
    assert due.startswith("2026-09-18T")


async def test_spanish_does_not_change_deadline(client: AsyncClient) -> None:
    await client.post("/demo/reset")
    await client.post(
        "/command",
        json={"text": "reconcile my next 14 days and ask before changing my calendar"},
    )
    en = await client.post(
        "/voicebridge/turn",
        json={"text": "What do I need to finish this week?", "language": "en"},
    )
    es = await client.post(
        "/voicebridge/turn",
        json={"text": "Qué necesito terminar esta semana?", "language": "es"},
    )
    en_due = {
        i["title"]: i["due_at"] for i in en.json()["facts"]["obligations"]
    }
    es_due = {
        i["title"]: i["due_at"] for i in es.json()["facts"]["obligations"]
    }
    assert en_due == es_due
    assert es.json()["language"] == "es"


async def test_low_confidence_cannot_act(client: AsyncClient) -> None:
    await client.post("/demo/reset")
    response = await client.post(
        "/voicebridge/turn",
        json={
            "text": "approve the calendar write",
            "source": "voice",
            "transcript_confidence": 0.4,
        },
    )
    body = response.json()
    assert body["intent"] == "clarify"
    assert body["requires_on_screen"] is True


async def test_spoken_yes_is_not_enough(client: AsyncClient) -> None:
    await client.post("/demo/reset")
    response = await client.post(
        "/voicebridge/turn",
        json={"text": "yes", "source": "voice", "transcript_confidence": 0.99},
    )
    body = response.json()
    assert body["intent"] == "spoken_confirm"
    assert body["facts"]["action"] == "none"
    assert body["requires_on_screen"] is True


async def test_reschedule_does_not_write_calendar(client: AsyncClient) -> None:
    await client.post("/demo/reset")
    await client.post(
        "/command",
        json={"text": "reconcile my next 14 days and ask before changing my calendar"},
    )
    before = await client.get("/calendar")
    response = await client.post(
        "/voicebridge/turn",
        json={"text": "Move the Tuesday study session to Wednesday.", "language": "en"},
    )
    after = await client.get("/calendar")
    assert response.json()["facts"]["calendar_changed"] is False
    assert len(before.json()["items"]) == len(after.json()["items"])
    assert "90" in response.json()["display_text"] or "minutes" in response.json()["display_text"]


async def test_delete_transcripts_and_no_audio_flag(client: AsyncClient) -> None:
    await client.post("/demo/reset")
    await client.post("/voicebridge/turn", json={"text": "hello"})
    listed = await client.get("/voicebridge/turns")
    assert listed.json()["items"]
    assert all(item["audio_retained"] is False for item in listed.json()["items"])
    deleted = await client.delete("/voicebridge/transcripts")
    assert deleted.json()["deleted"] >= 1


async def test_language_registry_is_honest(client: AsyncClient) -> None:
    body = (await client.get("/voicebridge/languages")).json()
    codes = {row["code"] for row in body["mvp"]}
    assert {"en", "es", "nl", "fr", "zh", "ar", "yo", "sw", "ha", "fil", "th", "vi", "ru", "id"} <= codes
    grok = {row["code"] for row in body["mvp"] if row["evaluation_status"] == "grok_voice_available"}
    assert {"en", "es", "nl", "fr", "de", "ja", "th", "vi", "ar", "hi"} <= grok
    assert all(row["conversation_translation"] == "complete" for row in body["mvp"])
    assert "Grok Voice" in body["claim"]
    assert body["audio_retention_default"] is False
