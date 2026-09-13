# Task 6: ticket lookup and escalation score

Track: **Ola — Business Operations / Customer Support**.

Portion 3 is complete. `ticket_lookup.py` reads a fabricated ticket by its record ID and returns its status, resolution time in hours, age, escalation flag and a 0–1 escalation score. It has no network access and does not modify any record.

## Score design

```
escalation score = 0.65 × escalation flag + 0.35 × (days since created / 30)
```

- The escalation flag is 1 when the seeded ticket records escalation and 0 otherwise.
- `days since created / 30` normalizes the dataset's allowed age range to 0–1.
- The score therefore stays between 0 and 1.
- The flag receives the larger weight because it is the dataset's direct escalation signal. Age ranks tickets within each group, but does not establish a real SLA breach.
- Recommend human attention when score is at least **0.50**.

## Threshold justification from the actual dataset

The seeded dataset contains 50 tickets: 10 flagged and 40 unflagged.

| Group | Observed score range |
| --- | ---: |
| Flagged tickets | 0.6617–0.9883 |
| Unflagged tickets | 0.0000–0.3500 |

The 0.50 threshold lies in the measured gap between 0.3500 and 0.6617. It recommends attention for exactly 10 of 50 tickets, or **20.0%**, which matches the dataset's designed escalation proportion. This is a deliberate interpretation for our fabricated data, not a claim about Ola's live operational policy.

## Demonstrations

| Ticket | Status | Resolution hours | Age | Score | Attention recommendation |
| --- | --- | ---: | ---: | ---: | --- |
| `SUP-0001` | Escalated | 48 | 29 | 0.9883 | Yes |
| `SUP-0014` | In Progress | 4 | 27 | 0.3150 | No |
| `SUP-0002` | Resolved | 9 | 19 | 0.8717 | Yes, because the dataset retains a prior escalation flag |
| `SUP-9999` | — | — | — | — | Explicit `TicketNotFoundError` |

A high score on a Resolved or Closed ticket records historical attention in this synthetic dataset. It does not reopen the ticket, trigger a real handoff, prove an SLA breach, or approve a refund.

## Reproduce

```powershell
python -m unittest discover -s tests -v
python verify_portion3.py
```

The verification writes the full executed report to `transcripts/portion3_evidence.json`. It validates the dataset, checks the score range and observed threshold gap, demonstrates three known tickets, and captures the missing-ticket error.
