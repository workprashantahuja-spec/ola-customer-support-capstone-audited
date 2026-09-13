import unittest

from crew_workflow import SupportCrewWorkflow
from grounded_answers import DeterministicGroundedModel, GroundedAnswerEngine
from governance import (
    GOVERNANCE_SUMMARY,
    RISK_CLASSIFICATION,
    LeastAutonomyPolicy,
    RuntimeBudget,
    ToolAccessDeniedError,
)
from response_cache import GroundedResponseCache, normalize_query
from session_service import SafeSessionSupportService


class CountingIndex:
    def __init__(self):
        self.call_count = 0

    def query(self, question, strategy, top_k):
        self.call_count += 1
        return {"hits": [{
            "cosine_similarity": 0.91,
            "source": "knowledge_base/example.md",
            "text": "Policy title\nSupported policy sentence.",
        }]}


class GovernanceAndCacheTests(unittest.TestCase):
    def test_all_four_governance_layers_are_declared(self):
        self.assertEqual(
            set(GOVERNANCE_SUMMARY),
            {"organization", "application", "model", "runtime"},
        )

    def test_lookup_tool_is_blocked_for_retrieval_agent(self):
        with self.assertRaises(ToolAccessDeniedError):
            LeastAutonomyPolicy.validate(
                "Policy Retrieval Specialist", ["check_support_ticket_status"]
            )

    def test_actual_crew_assignments_pass_allowlist(self):
        agents = SupportCrewWorkflow()._agents("ticket", "SUP-0001")
        access = {agent.role: {tool.name for tool in agent.tools} for agent in agents}
        self.assertEqual(
            access["Ticket Lookup Specialist"], {"check_support_ticket_status"}
        )
        self.assertNotIn(
            "check_support_ticket_status", access["Policy Retrieval Specialist"]
        )

    def test_risk_is_medium(self):
        self.assertEqual(RISK_CLASSIFICATION["level"], "Medium")

    def test_oversized_request_is_rejected_before_crew(self):
        service = SafeSessionSupportService(runtime_budget=RuntimeBudget())
        before = service.workflow.kickoff_count
        reply = service.handle("budget-test", "word " * 300)
        self.assertEqual(reply.status, "budget_rejected")
        self.assertFalse(reply.crew_invoked)
        self.assertEqual(service.workflow.kickoff_count, before)
        self.assertFalse(reply.runtime_budget["accepted"])

    def test_normalized_repeat_skips_retrieval_and_generation(self):
        index = CountingIndex()
        model = DeterministicGroundedModel()
        engine = GroundedAnswerEngine(
            index=index,
            model=model,
            cache=GroundedResponseCache(),
            cache_namespace="unit-test-v1",
        )
        first = engine.answer("Is routine support open Sunday?")
        second = engine.answer("  IS routine   support open Sunday?  ")
        self.assertFalse(first["cache_hit"])
        self.assertTrue(second["cache_hit"])
        self.assertEqual(index.call_count, 1)
        self.assertEqual(model.call_count, 1)
        self.assertEqual(
            normalize_query(first["question"]), normalize_query(second["question"])
        )


if __name__ == "__main__":
    unittest.main()
