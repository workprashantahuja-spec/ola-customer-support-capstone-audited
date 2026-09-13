"""Small in-memory cache for reusable, non-personal policy answers."""

from __future__ import annotations

import copy
import re
import unicodedata


def normalize_query(text: str) -> str:
    if not isinstance(text, str) or not text.strip():
        raise ValueError("Cache query must be a nonempty string")
    normalized = unicodedata.normalize("NFKC", text).casefold()
    return re.sub(r"\s+", " ", normalized).strip()


class GroundedResponseCache:
    """Cache normalized policy questions within a knowledge/config namespace."""

    def __init__(self):
        self._entries: dict[tuple[str, str], dict] = {}
        self.hits = 0
        self.misses = 0

    def get(self, query: str, namespace: str) -> dict | None:
        key = (namespace, normalize_query(query))
        value = self._entries.get(key)
        if value is None:
            self.misses += 1
            return None
        self.hits += 1
        return copy.deepcopy(value)

    def put(self, query: str, namespace: str, value: dict) -> None:
        self._entries[(namespace, normalize_query(query))] = copy.deepcopy(value)

    def clear(self) -> None:
        self._entries.clear()
        self.hits = 0
        self.misses = 0

    @property
    def size(self) -> int:
        return len(self._entries)

    def stats(self) -> dict:
        return {"entries": self.size, "hits": self.hits, "misses": self.misses}
