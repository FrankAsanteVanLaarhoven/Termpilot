"""TermPilot offline/read-only SDK. Does not send mail or write calendars."""

from __future__ import annotations

import json
import urllib.request


class TermPilot:
    def __init__(self, base: str = "http://127.0.0.1:8000") -> None:
        self.base = base.rstrip("/")

    def _get(self, path: str) -> object:
        with urllib.request.urlopen(self.base + path) as response:
            return json.load(response)

    def health(self) -> object:
        return self._get("/health")

    def tower(self) -> object:
        return self._get("/tower")

    def catalog(self) -> object:
        return self._get("/llm/catalog")
