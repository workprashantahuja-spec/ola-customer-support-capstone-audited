# Tasks 15 and 16 — Governance, runtime budget, and cache

## What this portion adds

`governance.py` organizes controls into four layers. The original brief explicitly names Application and Runtime; Organization and Model are this project's interpretation of the remaining layers, not a verified quotation of course terminology:

| Layer | Ola support rule |
| --- | --- |
| Organization | Use fabricated records, minimize retained data, and keep real actions with humans. |
| Application | Allow only the Ticket Lookup Specialist to use `check_support_ticket_status`; mask supported PII before processing and logs. |
| Model | Use deterministic local mock models with no API keys or runtime network during graded runs. |
| Runtime | Estimate each request before execution and reject it if it exceeds the token or reference-cost cap. |

This support assistant is **Medium risk** under the course classification because it handles customer-support tickets and influences customer communication. It is not High risk because it uses fabricated records and cannot make payments, change tickets, issue refunds, or access a real Ola system. Medium risk still requires privacy masking, least-autonomy permissions, grounded answers, bounded review, request budgets, and human ownership of real actions.

## Least autonomy proof

The allowlist gives the policy agent only `search_support_policies`, the ticket agent only `check_support_ticket_status`, and the composer no tools. Crew creation validates these assignments. The verifier deliberately tries to give the ticket tool to the Policy Retrieval Specialist and records the resulting `ToolAccessDeniedError`.

## Runtime budget proof

Before CrewAI runs, `RuntimeBudget` estimates input tokens plus a fixed 768-token simulation reserve. The default limits are 256 input tokens, 1,024 estimated total tokens, and USD 0.001 reference cost. The submitted mock path actually bills USD 0. This meets the brief's oversized simulated-request demonstration; it does not measure aggregate framework tokens or enforce future paid-model billing. A paid model would require per-call accounting and enforced limits.

The verifier submits a fabricated 300-word request. It is returned as `budget_rejected`, with zero CrewAI kickoffs. The rejected text is not added to conversation memory.

## Cache proof

`response_cache.py` normalizes Unicode, letter case, and repeated whitespace. Only grounded policy answers enter the in-memory cache; ticket results and session data never do. In normal application use, the cache namespace includes a fingerprint of the knowledge-base files and retrieval settings, preventing an old answer from surviving a handbook/configuration change.

The verifier asks the same Sunday-support question twice with different case and spacing. The first request performs one retrieval and one grounded generation. The second is a real cache hit: both counters remain at one.

Run:

```powershell
python verify_portion8.py
python -m unittest test_governance_cache.py
```

The complete execution record is written to `transcripts/portion8_evidence.json`.
