"""Focused tests for the fallback gate and extractive grounding."""

import unittest

from grounded_answers import DeterministicGroundedModel, GroundedAnswerEngine
from rag_config import FALLBACK_MESSAGE


class StubIndex:
    def __init__(self, score, text="Policy title\nSupported policy sentence."):
        self.score = score
        self.text = text

    def query(self, question, strategy, top_k):
        return {"question": question, "strategy": strategy, "hits": [{
            "cosine_similarity": self.score,
            "source": "knowledge_base/example.md",
            "text": self.text,
        }]}


class GroundedAnswerTests(unittest.TestCase):
    def test_supported_answer_is_verbatim_retrieved_body(self):
        model = DeterministicGroundedModel()
        result = GroundedAnswerEngine(
            index=StubIndex(0.75), model=model, threshold=0.40
        ).answer("supported question")
        self.assertEqual(result["answer"], "Supported policy sentence.")
        self.assertTrue(result["grounded"])
        self.assertEqual(result["sources"], ["knowledge_base/example.md"])
        self.assertEqual(model.call_count, 1)

    def test_low_score_falls_back_without_calling_model(self):
        model = DeterministicGroundedModel()
        result = GroundedAnswerEngine(
            index=StubIndex(0.20), model=model, threshold=0.40
        ).answer("unrelated question")
        self.assertEqual(result["answer"], FALLBACK_MESSAGE)
        self.assertTrue(result["fallback"])
        self.assertEqual(result["sources"], [])
        self.assertEqual(model.call_count, 0)

    def test_threshold_range_is_validated(self):
        with self.assertRaises(ValueError):
            GroundedAnswerEngine(index=StubIndex(0.5), threshold=1.1)


if __name__ == "__main__":
    unittest.main()
