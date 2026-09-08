"""Copy repo fixtures into the backend bundle for Vercel."""

from __future__ import annotations

import shutil
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
REPO = BACKEND.parent
SRC = REPO / "fixtures"
DST = BACKEND / "fixtures"


def main() -> None:
    # Vercel isolates the API service to backend/, so fixtures must already
    # live here or be copied from the repo root when that path is visible.
    if DST.exists() and any(DST.iterdir()):
        if not SRC.exists():
            return
    if not SRC.exists():
        return
    DST.mkdir(parents=True, exist_ok=True)
    shutil.copytree(SRC, DST, dirs_exist_ok=True)


if __name__ == "__main__":
    main()
