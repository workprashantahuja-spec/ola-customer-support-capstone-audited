"""Task 6: deterministic support-ticket lookup and escalation scoring.

This module reads only the fabricated dataset. It does not change a ticket,
create a handoff, or claim that an SLA has been breached.
"""

from dataset import SUPPORT_TICKETS


ESCALATION_FLAG_WEIGHT = 0.65
TICKET_AGE_WEIGHT = 0.35
MAX_TICKET_AGE_DAYS = 30
HUMAN_ATTENTION_THRESHOLD = 0.50


class TicketNotFoundError(LookupError):
    """Raised when a fabricated ticket ID is absent from the local dataset."""


def normalized_age(days_since_created):
    if not isinstance(days_since_created, int) or not 0 <= days_since_created <= MAX_TICKET_AGE_DAYS:
        raise ValueError("days_since_created must be an integer from 0 to 30")
    return days_since_created / MAX_TICKET_AGE_DAYS


def escalation_score(escalated, days_since_created):
    """Return a 0–1 attention score from explicit escalation history and age.

    The existing escalation flag receives greater weight because it is a direct
    signal in this fabricated dataset. Age is a ranking signal only: it must not
    be presented as proof of a real-world SLA breach.
    """
    if not isinstance(escalated, bool):
        raise ValueError("escalated must be boolean")
    score = (
        ESCALATION_FLAG_WEIGHT * int(escalated)
        + TICKET_AGE_WEIGHT * normalized_age(days_since_created)
    )
    return round(score, 4)


def check_support_ticket_status(record_id, tickets=SUPPORT_TICKETS):
    """Return the required Task 6 ticket fields and a human-attention signal."""
    if not isinstance(record_id, str) or not record_id.strip():
        raise ValueError("record_id must be a nonempty string")
    requested_id = record_id.strip().upper()
    ticket = next((item for item in tickets if item["record_id"] == requested_id), None)
    if ticket is None:
        raise TicketNotFoundError(f"Support ticket not found: {requested_id}")

    score = escalation_score(ticket["escalated"], ticket["days_since_created"])
    return {
        "record_id": ticket["record_id"],
        "status": ticket["status"],
        "resolution_time_hours": ticket["resolution_time_hours"],
        "days_since_created": ticket["days_since_created"],
        "escalated": ticket["escalated"],
        "escalation_score": score,
        "human_attention_recommended": score >= HUMAN_ATTENTION_THRESHOLD,
        "score_formula": (
            "0.65 × escalation flag + 0.35 × (days since created / 30)"
        ),
        "score_interpretation": (
            "This is a fabricated-data attention score, not evidence of an SLA breach, "
            "refund eligibility, or a completed human escalation."
        ),
    }
