import unittest

from autogen_agentchat.messages import StructuredMessage

from autogen_review import (
    AutoGenAnswerReviewer,
    MAX_REVIEW_TURNS,
    ReviewPayload,
    ReviewVerdict,
    draft_matches_evidence,
)
from crew_workflow import SupportResponse, TicketDetails
from ticket_lookup import check_support_ticket_status


EVIDENCE = {
    "answer": "For a P2 High ticket, acknowledge the report within 4 business hours.",
    "grounded": True,
    "fallback": False,
    "sources": ["knowledge_base/02_sla_by_severity.md"],
}


def supported_draft():
    return SupportResponse(
        request_type="policy",
        answer=EVIDENCE["answer"],
        grounded=True,
        fallback_used=False,
        sources=EVIDENCE["sources"],
        ticket=None,
    )


class AutoGenReviewTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        reviewer = AutoGenAnswerReviewer()
        cls.original = supported_draft()
        cls.approval = reviewer.review(cls.original, EVIDENCE)
        cls.incorrect = cls.original.model_copy(update={
            "answer": "A P2 ticket can wait 24 business hours for acknowledgement."
        })
        cls.revision = reviewer.review(cls.incorrect, EVIDENCE)

    def test_supported_draft_is_approved_unchanged(self):
        self.assertTrue(self.approval.verdict.approved)
        self.assertEqual(self.approval.verdict.final_answer, self.original.answer)

    def test_unsupported_draft_is_genuinely_revised(self):
        self.assertFalse(self.revision.verdict.approved)
        self.assertNotEqual(self.revision.verdict.final_answer, self.incorrect.answer)
        self.assertEqual(self.revision.verdict.final_answer, EVIDENCE["answer"])

    def test_round_robin_is_bounded_to_two_turns(self):
        self.assertEqual(self.approval.max_turns, MAX_REVIEW_TURNS)
        self.assertEqual(len(self.approval.agent_messages), 2)
        self.assertIn("Maximum number of turns 2 reached", self.approval.stop_reason)

    def test_final_message_is_structured_and_validated(self):
        final = self.approval.agent_messages[-1]
        self.assertIn("StructuredMessage", final["message_type"])
        self.assertIsInstance(self.approval.verdict, ReviewVerdict)

    def test_each_agent_model_runs_once(self):
        self.assertEqual(self.approval.reviewer_model_calls, 1)
        self.assertEqual(self.approval.editor_model_calls, 1)

    def test_draft_comparison_checks_more_than_answer_text(self):
        wrong_source = self.original.model_copy(update={"sources": ["knowledge_base/wrong.md"]})
        payload = ReviewPayload(draft=wrong_source, evidence=EVIDENCE)
        self.assertFalse(draft_matches_evidence(payload))

    def test_ticket_draft_can_also_be_approved(self):
        evidence = check_support_ticket_status("SUP-0001")
        ticket = TicketDetails.model_validate({
            key: evidence[key] for key in TicketDetails.model_fields
        })
        attention = " Human attention is recommended."
        draft = SupportResponse(
            request_type="ticket",
            answer=(
                f"Ticket {ticket.record_id} is {ticket.status}. Its recorded resolution-time "
                f"value is {ticket.resolution_time_hours} hours and its attention score is "
                f"{ticket.escalation_score:.4f}.{attention}"
            ),
            grounded=True,
            fallback_used=False,
            sources=["fabricated_support_tickets"],
            ticket=ticket,
        )
        result = AutoGenAnswerReviewer().review(draft, evidence)
        self.assertTrue(result.verdict.approved)
        self.assertEqual(result.verdict.final_answer, draft.answer)


if __name__ == "__main__":
    unittest.main()
