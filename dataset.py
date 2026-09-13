"""Ola capstone starter: reproducible, fabricated support-ticket data.

Confirmed project domain: Ola, selected by Prashant on 6 September 2026.
Run `python dataset.py` to validate and report, or `python dataset.py --json`.
No external packages, API keys, or network access are needed.
"""

import argparse
from collections import Counter
import json
import random

SEED = 3
RECORD_COUNT = 50
CATEGORIES = (
    "Billing", "Technical Issue", "Account Access", "Product Defect",
    "General Inquiry",
)
CATEGORY_WEIGHTS = (30, 25, 15, 10, 20)
STATUSES = ("Open", "In Progress", "Escalated", "Resolved", "Closed")
STATUS_WEIGHTS = (20, 25, 15, 25, 15)
RESOLUTION_HOURS = (1, 72)
PRIOR_ESCALATION_PROBABILITY = 0.12


def generate_tickets(seed=SEED, count=RECORD_COUNT):
    """Generate all fields from one local seeded random source; never patch rows."""
    rng = random.Random(seed)
    records = []
    for number in range(1, count + 1):
        category = rng.choices(CATEGORIES, weights=CATEGORY_WEIGHTS, k=1)[0]
        status = rng.choices(STATUSES, weights=STATUS_WEIGHTS, k=1)[0]
        hours = rng.randint(*RESOLUTION_HOURS)
        days = rng.randint(0, 30)
        # Resolved/closed tickets can retain a history of earlier escalation.
        escalated = status == "Escalated" or (
            status in ("Resolved", "Closed")
            and rng.random() < PRIOR_ESCALATION_PROBABILITY
        )
        records.append({
            "record_id": f"SUP-{number:04d}",
            "category": category,
            "status": status,
            "resolution_time_hours": hours,
            "days_since_created": days,
            "escalated": escalated,
        })
    return records


def validate_tickets(records):
    """Enforce Task 1's thresholds and fail explicitly when a design misses one."""
    errors = []
    required = {
        "record_id", "category", "status", "resolution_time_hours",
        "days_since_created", "escalated",
    }
    if len(records) < 40:
        errors.append("At least 40 records are required.")
    seen = set()
    for number, record in enumerate(records, start=1):
        if set(record) != required:
            errors.append(f"Record {number}: incorrect fields.")
            continue
        record_id = record["record_id"]
        if not isinstance(record_id, str) or not record_id:
            errors.append(f"Record {number}: ID must be a nonempty string.")
        elif record_id in seen:
            errors.append(f"Duplicate ID: {record_id}")
        else:
            seen.add(record_id)
        if record["category"] not in CATEGORIES:
            errors.append(f"Record {number}: unknown category.")
        if record["status"] not in STATUSES:
            errors.append(f"Record {number}: unknown status.")
        hours = record["resolution_time_hours"]
        if type(hours) is not int or not RESOLUTION_HOURS[0] <= hours <= RESOLUTION_HOURS[1]:
            errors.append(f"Record {number}: resolution hours must be 1–72.")
        days = record["days_since_created"]
        if type(days) is not int or not 0 <= days <= 30:
            errors.append(f"Record {number}: age must be an integer from 0 to 30.")
        if type(record["escalated"]) is not bool:
            errors.append(f"Record {number}: escalated must be boolean.")
    category_counts = Counter(record.get("category") for record in records)
    status_counts = Counter(record.get("status") for record in records)
    for category in CATEGORIES:
        if category_counts[category] < 3:
            errors.append(f"Category {category}: at least 3 records required.")
    for status in STATUSES:
        if status_counts[status] < 1:
            errors.append(f"Status {status}: at least 1 record required.")
    escalated_count = sum(record.get("escalated") is True for record in records)
    percentage = 100 * escalated_count / len(records) if records else 0
    if not 10 <= percentage <= 30:
        errors.append("Escalated records must be between 10% and 30%.")
    if errors:
        raise ValueError("Dataset validation failed:\n" + "\n".join(errors))
    return {
        "records": len(records),
        "category_counts": {key: category_counts[key] for key in CATEGORIES},
        "status_counts": {key: status_counts[key] for key in STATUSES},
        "escalated_count": escalated_count,
        "escalated_percentage": percentage,
    }


SUPPORT_TICKETS = generate_tickets()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="Print all ticket records.")
    arguments = parser.parse_args()
    report = validate_tickets(SUPPORT_TICKETS)
    if SUPPORT_TICKETS != generate_tickets():
        raise RuntimeError("Seeded regeneration produced different records.")
    print(json.dumps(SUPPORT_TICKETS if arguments.json else {
        "validation": "PASS",
        "deterministic_regeneration": "PASS",
        "seed": SEED,
        **report,
    }, indent=2))
