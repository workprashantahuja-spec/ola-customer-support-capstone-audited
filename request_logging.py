"""Append-only masked JSON-Lines request logging for the FastAPI layer."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path


class RequestJsonlLogger:
    def __init__(self, path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def append(self, entry: dict):
        record = {
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
            **entry,
        }
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, sort_keys=True) + "\n")

    def read_entries(self) -> list[dict]:
        if not self.path.exists():
            return []
        return [json.loads(line) for line in self.path.read_text(encoding="utf-8").splitlines() if line]

