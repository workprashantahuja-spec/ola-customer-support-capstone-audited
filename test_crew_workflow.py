import unittest

from crew_workflow import (
    DeterministicWorkerLLM,
    PolicySearchTool,
    SupportCrewWorkflow,
    SupportResponse,
    TicketLookupTool,
    _latest_observation,
)


class CrewWorkflowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.workflow = SupportCrewWorkflow()
        cls.workflow.clear_tool_trace()
        cls.policy = cls.workflow.run_policy("How quickly must a P2 ticket be acknowledged?")
        cls.ticket = cls.workflow.run_ticket("SUP-0001")

    def test_two_real_kickoffs_completed(self):
        self.assertEqual(self.workflow.kickoff_count, 2)

    def test_policy_tool_invoked_once(self):
        self.assertEqual(len(PolicySearchTool.trace), 1)
        self.assertEqual(
            PolicySearchTool.trace[0]["arguments"]["question"],
            "How quickly must a P2 ticket be acknowledged?",
        )

    def test_ticket_tool_invoked_once(self):
        self.assertEqual(len(TicketLookupTool.trace), 1)
        self.assertEqual(TicketLookupTool.trace[0]["arguments"]["record_id"], "SUP-0001")

    def test_policy_response_is_validated(self):
        self.assertIsInstance(self.policy, SupportResponse)
        self.assertEqual(self.policy.request_type, "policy")
        self.assertTrue(self.policy.grounded)
        self.assertIsNone(self.policy.ticket)

    def test_ticket_response_is_validated(self):
        self.assertIsInstance(self.ticket, SupportResponse)
        self.assertEqual(self.ticket.request_type, "ticket")
        self.assertEqual(self.ticket.ticket.record_id, "SUP-0001")

    def test_composer_has_no_tool_access(self):
        composer = next(agent for agent in self.workflow.last_crew.agents if agent.role == "Support Response Composer")
        self.assertEqual(composer.tools, [])

    def test_lookup_only_ticket_access(self):
        agents = {agent.role: {tool.name for tool in agent.tools} for agent in self.workflow.last_crew.agents}
        self.assertEqual(agents["Ticket Lookup Specialist"], {"check_support_ticket_status"})
        self.assertNotIn("check_support_ticket_status", agents["Policy Retrieval Specialist"])

    def test_prompt_example_is_not_mistaken_for_observation(self):
        messages = [{"role": "system", "content": "Example\nObservation: fake"}]
        self.assertIsNone(_latest_observation(messages))

    def test_worker_dispatches_declared_arguments(self):
        llm = DeterministicWorkerLLM("check_support_ticket_status", {"record_id": "SUP-0014"})
        reply = llm.call([{"role": "user", "content": "Current task"}])
        self.assertIn('Action: check_support_ticket_status', reply)
        self.assertIn('"record_id": "SUP-0014"', reply)


if __name__ == "__main__":
    unittest.main()

