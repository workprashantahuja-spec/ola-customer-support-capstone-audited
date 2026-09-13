"""Focused Task 6 checks independent of the later agent framework."""

import unittest

from ticket_lookup import (
    HUMAN_ATTENTION_THRESHOLD,
    TicketNotFoundError,
    check_support_ticket_status,
    escalation_score,
)


class TicketLookupTests(unittest.TestCase):
    def test_score_uses_both_flag_and_normalized_age(self):
        self.assertEqual(escalation_score(False, 0), 0.0)
        self.assertEqual(escalation_score(False, 30), 0.35)
        self.assertEqual(escalation_score(True, 0), 0.65)
        self.assertEqual(escalation_score(True, 30), 1.0)

    def test_known_ticket_returns_required_fields_and_threshold_result(self):
        result = check_support_ticket_status("sup-0001")
        self.assertEqual(result["record_id"], "SUP-0001")
        self.assertEqual(result["status"], "Escalated")
        self.assertEqual(result["resolution_time_hours"], 48)
        self.assertEqual(result["escalation_score"], 0.9883)
        self.assertGreaterEqual(result["escalation_score"], HUMAN_ATTENTION_THRESHOLD)
        self.assertTrue(result["human_attention_recommended"])

    def test_unflagged_ticket_does_not_cross_dataset_threshold(self):
        result = check_support_ticket_status("SUP-0014")
        self.assertFalse(result["escalated"])
        self.assertEqual(result["escalation_score"], 0.315)
        self.assertFalse(result["human_attention_recommended"])

    def test_missing_and_invalid_ids_fail_explicitly(self):
        with self.assertRaises(TicketNotFoundError):
            check_support_ticket_status("SUP-9999")
        with self.assertRaises(ValueError):
            check_support_ticket_status("   ")


if __name__ == "__main__":
    unittest.main()
