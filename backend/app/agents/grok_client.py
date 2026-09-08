"""xAI/Grok adapter with a deterministic fake for offline tests and demos."""

from __future__ import annotations

import json
from typing import Any

from app.domain.enums import SourceType
from app.domain.schemas import ExtractionResult
from app.observability.logging import get_logger
from app.services.extraction import extract_observation
from app.settings import get_settings

log = get_logger("termpilot.grok")


class GrokUnavailableError(RuntimeError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


class FakeGrokAdapter:
    """Returns schema-valid structured results using the deterministic extractors.

    This is not a silent stand-in for a live model in production metrics. Demo and
    system-test traces label the adapter as `fake`.
    """

    mode = "fake"

    async def extract_obligations(
        self,
        source_type: SourceType,
        payload: dict[str, Any],
        observed_at: Any,
        reference: str,
        timezone_name: str,
    ) -> ExtractionResult:
        del timezone_name
        return extract_observation(source_type, payload, observed_at, reference)

    async def complete_json(self, system: str, user: str, schema_name: str) -> dict[str, Any]:
        del system, user, schema_name
        raise GrokUnavailableError(
            "fake_model", "FakeGrokAdapter does not invent free-form completions."
        )


class LiveGrokAdapter:
    mode = "live"

    def __init__(self) -> None:
        settings = get_settings()
        if not settings.xai_api_key:
            raise GrokUnavailableError("missing_api_key", "XAI_API_KEY is not configured.")
        from openai import AsyncOpenAI

        self._client = AsyncOpenAI(api_key=settings.xai_api_key, base_url=settings.xai_base_url)
        self._model = settings.xai_model

    async def complete_json(self, system: str, user: str, schema_name: str) -> dict[str, Any]:
        settings = get_settings()
        if settings.simulate_grok_timeout or settings.simulate_offline:
            raise GrokUnavailableError("grok_timeout", "Grok API timeout (simulated).")
        response = await self._client.chat.completions.create(
            model=self._model,
            temperature=0,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        )
        content = response.choices[0].message.content or "{}"
        try:
            parsed = json.loads(content)
        except json.JSONDecodeError as exc:
            raise GrokUnavailableError("invalid_structured_output", str(exc)) from exc
        if not isinstance(parsed, dict):
            raise GrokUnavailableError(
                "invalid_structured_output", f"Expected object for {schema_name}."
            )
        return parsed

    async def extract_obligations(
        self,
        source_type: SourceType,
        payload: dict[str, Any],
        observed_at: Any,
        reference: str,
        timezone_name: str,
    ) -> ExtractionResult:
        # Live model is allowed to interpret messy text, but output is schema-validated
        # and the deterministic extractor is the fallback if the model fails.
        try:
            from app.agents.prompts import EXTRACT_OBLIGATIONS_PROMPT

            raw = await self.complete_json(
                EXTRACT_OBLIGATIONS_PROMPT,
                json.dumps(
                    {
                        "source_type": source_type.value,
                        "source_reference": reference,
                        "timezone": timezone_name,
                        "observed_at": str(observed_at),
                        "payload": payload,
                    },
                    default=str,
                )[:12000],
                "extract-obligations",
            )
            return ExtractionResult.model_validate(raw)
        except Exception as exc:  # noqa: BLE001 — fail closed to deterministic parser
            log.warning("live_extract_fallback", error=str(exc), reference=reference)
            result = extract_observation(source_type, payload, observed_at, reference)
            return result


def get_grok_adapter() -> FakeGrokAdapter | LiveGrokAdapter:
    settings = get_settings()
    if settings.use_live_grok:
        try:
            return LiveGrokAdapter()
        except GrokUnavailableError:
            return FakeGrokAdapter()
    return FakeGrokAdapter()
