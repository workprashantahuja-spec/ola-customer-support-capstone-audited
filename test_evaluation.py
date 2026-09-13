import unittest

from evaluation import (
    EVALUATION_CASES,
    DeterministicMockJudge,
    EvaluationCase,
)
from rag_config import FALLBACK_MESSAGE


class EvaluationTests(unittest.TestCase):
    def test_set_has_15_cases_and_all_12_kb_topics(self):
        self.assertEqual(len(EVALUATION_CASES), 15)
        sources = {case.expected_source for case in EVALUATION_CASES}
        for number in range(1, 13):
            prefix = f"knowledge_base/{number:02d}_"
            self.assertTrue(any(source and source.startswith(prefix) for source in sources))

    def test_set_has_two_out_of_scope_or_edge_cases(self):
        edge_kinds = {"ticket", "out_of_scope", "prompt_injection"}
        self.assertGreaterEqual(sum(case.kind in edge_kinds for case in EVALUATION_CASES), 2)

    def test_mock_judge_scores_correct_fallback(self):
        case = EvaluationCase(
            case_id="T", topic="test", query="weather", kind="out_of_scope",
            required_facts=[FALLBACK_MESSAGE],
        )
        observed = {"reply": {
            "status": "answered", "message": FALLBACK_MESSAGE, "crew_invoked": True,
            "response": {"fallback_used": True, "grounded": False, "sources": []},
        }}
        scores, prompt = DeterministicMockJudge().judge(case, observed)
        self.assertEqual(scores.accuracy, 5)
        self.assertIn("Accuracy", prompt)

    def test_mock_judge_penalizes_missing_required_fact(self):
        case = EvaluationCase(
            case_id="T", topic="test", query="question", kind="policy",
            expected_source="knowledge_base/test.md", required_facts=["required fact"],
        )
        observed = {"reply": {
            "status": "answered", "message": "Different answer", "crew_invoked": True,
            "response": {
                "request_type": "policy", "fallback_used": False, "grounded": True,
                "sources": ["knowledge_base/test.md"],
            },
        }}
        scores, _ = DeterministicMockJudge().judge(case, observed)
        self.assertEqual(scores.accuracy, 1)
        self.assertEqual(scores.completeness, 1)


if __name__ == "__main__":
    unittest.main()
