"""Create actual execution evidence for Task 6 without external services."""

import json
from pathlib import Path

from dataset import SUPPORT_TICKETS, validate_tickets
from ticket_lookup import (
    ESCALATION_FLAG_WEIGHT,
    HUMAN_ATTENTION_THRESHOLD,
    TICKET_AGE_WEIGHT,
    TicketNotFoundError,
    check_support_ticket_status,
    escalation_score,
)


def score_summary(tickets):
    scored = [{**ticket, "score": escalation_score(ticket["escalated"], ticket["days_since_created"])}
              for ticket in tickets]
    flagged = [row["score"] for row in scored if row["escalated"]]
    unflagged = [row["score"] for row in scored if not row["escalated"]]
    attention = [row for row in scored if row["score"] >= HUMAN_ATTENTION_THRESHOLD]
    return {
        "records": len(scored),
        "flagged_records": len(flagged),
        "unflagged_records": len(unflagged),
        "flagged_score_range": {"min": min(flagged), "max": max(flagged)},
        "unflagged_score_range": {"min": min(unflagged), "max": max(unflagged)},
        "gap_between_groups": round(min(flagged) - max(unflagged), 4),
        "threshold": HUMAN_ATTENTION_THRESHOLD,
        "human_attention_recommendations": len(attention),
        "human_attention_percentage": round(100 * len(attention) / len(scored), 1),
        "recommended_ticket_ids": [row["record_id"] for row in attention],
    }


def run_verification():
    dataset_report = validate_tickets(SUPPORT_TICKETS)
    summary = score_summary(SUPPORT_TICKETS)
    if not summary["unflagged_score_range"]["max"] < HUMAN_ATTENTION_THRESHOLD < summary["flagged_score_range"]["min"]:
        raise AssertionError("Threshold must lie between observed score groups")

    known_ids = ["SUP-0001", "SUP-0014", "SUP-0002"]
    known = [check_support_ticket_status(record_id) for record_id in known_ids]
    for result in known:
        required = {"record_id", "status", "resolution_time_hours", "escalation_score"}
        if not required <= result.keys():
            raise AssertionError("Task 6 required fields missing")
        if not 0.0 <= result["escalation_score"] <= 1.0:
            raise AssertionError("Escalation score outside 0–1")

    try:
        check_support_ticket_status("SUP-9999")
    except TicketNotFoundError as error:
        missing = {"record_id": "SUP-9999", "error": str(error)}
    else:
        raise AssertionError("Missing ticket should fail explicitly")

    return {
        "portion": 3,
        "rubric_task": 6,
        "status": "PASS",
        "dataset_validation": dataset_report,
        "formula": {
            "expression": "0.65 × escalation flag + 0.35 × (days since created / 30)",
            "flag_weight": ESCALATION_FLAG_WEIGHT,
            "age_weight": TICKET_AGE_WEIGHT,
            "age_normalization_max_days": 30,
            "human_attention_threshold": HUMAN_ATTENTION_THRESHOLD,
        },
        "distribution_and_threshold_justification": summary,
        "known_ticket_demonstrations": known,
        "missing_ticket_demonstration": missing,
        "limitation": (
            "The score ranks fabricated ticket data only. Days since created is not a real SLA clock, "
            "and the lookup does not establish a real SLA breach, refund eligibility, or a completed escalation."
        ),
    }


if __name__ == "__main__":
    report = run_verification()
    destination = Path(__file__).resolve().parent / "transcripts" / "portion3_evidence.json"
    destination.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "portion": report["portion"], "status": report["status"],
        "formula": report["formula"],
        "distribution": report["distribution_and_threshold_justification"],
        "known_ticket_count": len(report["known_ticket_demonstrations"]),
        "missing_ticket": report["missing_ticket_demonstration"],
        "evidence": str(destination.relative_to(destination.parent.parent)),
    }, indent=2))
