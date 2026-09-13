"""Grounded policy answers for Tasks 4 and 5.

The default model is deliberately deterministic and extractive: it can return
only text present in a retrieved policy chunk. This keeps the required offline
MOCK_LLM path reproducible and makes unsupported additions impossible here.
"""

import hashlib
from dataclasses import dataclass
from pathlib import Path

from rag_config import (
    DEFAULT_RETRIEVAL_STRATEGY,
    FALLBACK_MESSAGE,
    FALLBACK_THRESHOLD,
)
from rag_index import PolicyIndex
from response_cache import GroundedResponseCache, normalize_query


@dataclass
class DeterministicGroundedModel:
    """Small offline MOCK_LLM used until the CrewAI adapter is added."""

    call_count: int = 0

    def generate(self, retrieved_contexts):
        if not retrieved_contexts:
            raise ValueError("Grounded generation requires retrieved context")
        self.call_count += 1
        # Each indexed chunk is stored as "title\npolicy body". Returning the
        # body verbatim proves that this mock cannot add an unsupported claim.
        _, separator, body = retrieved_contexts[0]["text"].partition("\n")
        return body.strip() if separator else retrieved_contexts[0]["text"].strip()


class GroundedAnswerEngine:
    def __init__(self, index=None, model=None, strategy=DEFAULT_RETRIEVAL_STRATEGY,
                 threshold=FALLBACK_THRESHOLD, top_k=3, cache=None, cache_namespace=None):
        if not 0.0 <= threshold <= 1.0:
            raise ValueError("Threshold must be between 0 and 1")
        self.index = index or PolicyIndex()
        self.model = model or DeterministicGroundedModel()
        self.strategy = strategy
        self.threshold = threshold
        self.top_k = top_k
        self.cache = cache or GroundedResponseCache()
        self.cache_namespace = cache_namespace or self._cache_namespace()
        self._explicit_namespace = cache_namespace

    def _cache_namespace(self):
        """Invalidate old answers when policy files or retrieval settings change."""
        digest = hashlib.sha256()
        knowledge_dir = Path(__file__).resolve().parent / "knowledge_base"
        for path in sorted(knowledge_dir.glob("*.md")):
            digest.update(path.name.encode("utf-8"))
            digest.update(path.read_bytes())
        settings = f"{self.strategy}|{self.threshold}|{self.top_k}|extractive-v1"
        digest.update(settings.encode("utf-8"))
        return digest.hexdigest()[:16]

    def answer(self, question):
        if self._explicit_namespace is None:
            current = self._cache_namespace()
            if current != self.cache_namespace:
                self.cache.clear()
                self.cache_namespace = current
        cached = self.cache.get(question, self.cache_namespace)
        if cached is not None:
            cached["question"] = question
            cached["cache_hit"] = True
            return cached

        retrieval = self.index.query(question, self.strategy, self.top_k)
        hits = retrieval["hits"]
        top_score = hits[0]["cosine_similarity"] if hits else 0.0
        if not hits or top_score < self.threshold:
            return {
                "question": question,
                "answer": FALLBACK_MESSAGE,
                "grounded": False,
                "fallback": True,
                "strategy": self.strategy,
                "threshold": self.threshold,
                "top_similarity": top_score,
                "sources": [],
                "model": "deterministic_extractive_mock_v1",
                "cache_hit": False,
                "cache_key": normalize_query(question),
            }

        answer = self.model.generate(hits)
        result = {
            "question": question,
            "answer": answer,
            "grounded": True,
            "fallback": False,
            "strategy": self.strategy,
            "threshold": self.threshold,
            "top_similarity": top_score,
            "sources": [hits[0]["source"]],
            "retrieved_context": hits[0]["text"],
            "model": "deterministic_extractive_mock_v1",
            "cache_hit": False,
            "cache_key": normalize_query(question),
        }
        # Only grounded policy answers are reusable. Session/ticket data is never cached.
        self.cache.put(question, self.cache_namespace, result)
        return result
