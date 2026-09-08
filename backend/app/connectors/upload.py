"""Local file-upload connector. Rejects path traversal and oversized files."""

from __future__ import annotations

from datetime import datetime
from hashlib import sha256
from pathlib import Path

from app.connectors.base import healthy
from app.domain.enums import SourceAuthority, SourceType
from app.domain.schemas import ConnectorHealth, SourceObservationIn
from app.services import clock
from app.settings import get_settings

_MAX_BYTES = 256_000
_ALLOWED_SUFFIXES = {".txt", ".md", ".pdf", ".html"}


class UploadError(ValueError):
    pass


class UploadConnector:
    source_type = SourceType.UPLOAD
    label = "Local uploads"

    def __init__(self, root: Path | None = None) -> None:
        self._root = (root or get_settings().fixtures_root / "uploads").resolve()
        self._last_success: datetime | None = None

    async def health_check(self) -> ConnectorHealth:
        return healthy(self.source_type, self.label, self._last_success or clock.now())

    def _safe_path(self, relative: str) -> Path:
        if ".." in Path(relative).parts or relative.startswith("/"):
            raise UploadError("path_traversal")
        path = (self._root / relative).resolve()
        if not str(path).startswith(str(self._root)):
            raise UploadError("path_traversal")
        if path.suffix.lower() not in _ALLOWED_SUFFIXES:
            raise UploadError("unsupported_type")
        if not path.is_file():
            raise UploadError("missing_file")
        if path.stat().st_size > _MAX_BYTES:
            raise UploadError("oversized_file")
        return path

    async def fetch_observations(
        self, user_id: str, since: datetime | None = None
    ) -> list[SourceObservationIn]:
        del user_id, since
        items: list[SourceObservationIn] = []
        for path in sorted(self._root.glob("*")):
            if not path.is_file() or path.suffix.lower() not in _ALLOWED_SUFFIXES:
                continue
            if path.stat().st_size > _MAX_BYTES:
                continue
            text = path.read_text(encoding="utf-8", errors="replace")[:4000]
            items.append(
                SourceObservationIn(
                    source_type=SourceType.UPLOAD,
                    source_reference=f"fixtures/uploads/{path.name}",
                    source_authority=SourceAuthority.TERTIARY,
                    observed_at=clock.now(),
                    excerpt=text[:180],
                    payload={"text": text, "filename": path.name},
                    content_digest=sha256(path.read_bytes()).hexdigest(),
                )
            )
        self._last_success = clock.now()
        return items
