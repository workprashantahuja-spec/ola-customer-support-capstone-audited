# Ola customer-support capstone

Current checkpoint, 13 September: read FINAL-AUDIT.md and README.md. The public repository exists. The audit supersedes historical completion, next-step and test-count claims below. Final LMS submission and Windows setup remain unverified.

Start with README.md and BUSINESS-WALKTHROUGH.md. The audit, documentation, clean setup, local Git preparation, and business walkthrough are complete. Read AUDIT10A.md before relying on earlier perfect-score language: results apply only to the selected acceptance set. The remaining work is to create and publish the public GitHub repository, then submit its URL in LMS.

Confirmed track: **Ola — Business Operations / Customer Support**, selected by Prashant on 6 September 2026. Use the matching Ola domain in LMS Question 1 and the submitted repository.

Submission date: **Sunday, 13 September 2026**, as stated by Prashant. Finish target: **Friday, 11 September**, preserving the weekend for fixes and submission.

## What we are building

A support agent that answers policy questions using our written knowledge base, checks a fabricated ticket's status, remembers a conversation, checks safety, and has its draft reviewed before returning the answer through an API.

The supplied brief requires one public GitHub repository containing code, data, knowledge-base text, a README, and real execution transcripts. It says images, PDFs, slide decks, video, and audio are not accepted deliverables. Graded runs must work with a deterministic `MOCK_LLM`, with no API keys or runtime network access. Local SentenceTransformers embeddings and ChromaDB are required. Download/install dependencies and the embedding model during setup, before offline graded runs.

Source: the user-supplied **Pasted text(20260829-212814).txt**, titled *Final Capstone — Ola Domain Support Agent (CrewAI)*, uploaded 29 August 2026. The user previously reported that later classes/Q&A allow AI assistance and require understanding the submitted system. The completed local build follows that clarification; public publication and final submission remain.

## First task delivered: the dataset

`dataset.py` generates a `SUPPORT_TICKETS` list containing 50 fabricated records. It validates the required fields, unique IDs, category/status coverage, value ranges, and the escalation percentage. It also checks that regeneration with the same seed produces the same records. It uses only Python's standard library.

| Design choice | Value and reason |
| --- | --- |
| Random seed | 3, selected by regeneration after seed 42 failed the minimum category count; no individual records were edited. |
| Record count | 50, exceeding the required minimum of 40. |
| Category weights | Billing 30; Technical Issue 25; Account Access 15; Product Defect 10; General Inquiry 20. These are generator weights, not promised final percentages. |
| Status weights | Open 20; In Progress 25; Escalated 15; Resolved 25; Closed 15. |
| Resolution time | Integer hours, 1–72: a synthetic range covering quick fixes through cases needing several days. For active tickets this is an estimate; for completed tickets it represents recorded resolution time. |
| Ticket age | Integer days, 0–30. |
| Escalation flag | True for currently Escalated tickets; resolved/closed tickets have a seeded 12% chance of retaining a prior escalation flag. The generated overall percentage must be 10–30%. |
| Personal data | No real customer information is used. |

Actual validated counts for seed 3:

| Category | Records |
| --- | ---: |
| Billing | 11 |
| Technical Issue | 11 |
| Account Access | 11 |
| Product Defect | 6 |
| General Inquiry | 11 |

| Status | Records |
| --- | ---: |
| Open | 7 |
| In Progress | 18 |
| Escalated | 9 |
| Resolved | 10 |
| Closed | 6 |

10 of 50 records are marked escalated: **20%**. There is one resolved/closed record with a prior escalation, so this count legitimately differs from the current Escalated status count.

## Run the first task on your Windows laptop

No register is needed for this setup.

1. Create a folder named `capstone-project` on your Desktop.
2. Extract `ola-capstone-starter.zip` into that folder; keep `dataset.py`, this file, and the `knowledge_base` folder together.
3. Open VS Code. Click **File → Open Folder**, choose `capstone-project`, and click **Select Folder**.
4. Click **Terminal → New Terminal**. In the PowerShell terminal, run:

```powershell
python dataset.py
```

Expected: `"validation": "PASS"`, `"deterministic_regeneration": "PASS"`, 50 records, and 20.0 escalated percentage. If `python` is not recognized but the Windows Python launcher is installed, use `py dataset.py`.

To inspect the full dataset later:

```powershell
python dataset.py --json
```

This first file needs no virtual environment or package installation. Create a dedicated virtual environment when we begin the RAG dependencies.

## Complete requirements checklist

Tasks 1–16 are delivered and verified. The final rubric audit, README, clean-install check, repository publication, and LMS submission remain. Sentence-based retrieval is the selected strategy after the formal comparison.

| Task | What must be delivered and demonstrated | Status |
| --- | --- | --- |
| 1 — Dataset | Seeded `dataset.py`, ≥40 tickets, all required fields, ≥3 of every required category, ≥1 of every required status, 10–30% escalated; counts and documented design choices. | Implemented and validated in the assistant workspace; run on the laptop next. |
| 2 — Knowledge base | ≥12 original documents, each 2–5 sentences, covering every required topic listed below. | Written: 12 separate documents, 5 sentences each; topic coverage, length, and cross-policy consistency checked. |
| 3 — Two indexes | Fixed-size chunks with overlap and sentence-based chunks; local SentenceTransformers embeddings; two separate ChromaDB collections populated with `upsert()`. | Implemented and tested: 31 fixed chunks and 36 sentence chunks; six sample searches passed; repeat builds and reopening verified. |
| 4 — Grounded answers | Measure top-1 cosine similarity on ≥3 in-scope and ≥2 out-of-scope queries; empirically select and document a threshold; show ≥5 in-scope answers and one out-of-scope fallback. | Implemented and verified: 0.40 measured threshold, 6 grounded answers, and 1 fallback. |
| 5 — Retrieval comparison | Document-level precision/recall, deduplicating parent documents, for both collections on the same ≥5 queries; show arithmetic and recommend a strategy using the measured results. | Implemented and verified on 12 identical queries; sentence chunks selected from measured results. |
| 6 — Ticket lookup | `check_support_ticket_status(record_id)` returns status, resolution time, and a designed 0–1 escalation score combining the escalation flag and normalized age; justify formula and threshold using the dataset. | Implemented and verified: 0.65 flag weight, 0.35 normalized-age weight, and 0.50 threshold selected from the observed dataset gap. |
| 7 — CrewAI | At least Retrieval, Lookup, and Composer agents; execute with `.kickoff()` and show both tools actually running on suitable queries. | Implemented and verified with two real `Crew.kickoff()` executions and one real invocation of each required tool. |
| 8 — Memory | LangChain session-based memory; one transcript retaining context across turns and a separate fresh-session transcript showing reset. | Implemented and verified with isolated LangChain histories: one same-session follow-up retained `SUP-0014`; a fresh session correctly requested an ID. |
| 9 — Structured output | A Pydantic response schema and actual validation of every crew response. | Implemented and verified: both crew results passed `SupportResponse`; an incomplete deliberate example was rejected. |
| 10 — Guardrails | Input phone-number masking and injection detection; output groundedness checks; demonstrate each firing on a deliberate case. Use fabricated examples for names, addresses, and payment details; those free-text fields are outside the brief's masking scope. | Implemented and verified: phone, card-last-4, PAN, Aadhaar, and labelled bank-account masking; injection blocking before CrewAI; and rejection of an unsupported output claim. |
| 11 — API | FastAPI with ≥2 HTTP endpoints and one WebSocket endpoint; Pydantic models; handle client disconnects while leaving the server running. | Implemented and verified: three HTTP routes, a multi-turn WebSocket chat route, typed request/response models, and clean disconnect handling. |
| 12 — Logs | One JSON-Lines entry per request with trace ID and timing; mask the same fixed-format PII before it reaches logs. | Implemented and verified: one safe JSONL entry for every HTTP request and WebSocket chat message, each with trace ID and timing. |
| 13 — Evaluation | 15 queries covering all 12 KB topics plus ≥2 out-of-scope/edge cases; mock judge scores Accuracy, Grounding, Completeness, and Safety; report every score and all four averages. | Implemented and verified: all 12 topics plus 3 edge/out-of-scope cases; every per-query score recorded; controlled-set averages are 5.00/5 for all four measures. |
| 14 — AutoGen review | Two-agent `RoundRobinGroupChat` after the CrewAI draft; bounded turns; Pydantic verdict with approved/final_answer/reason; show one unchanged approval and one genuine revision. | Implemented and verified with `max_turns=2`, a registered typed verdict, one unchanged approval, and one planted error corrected to the original evidence. |
| 15 — Governance | Apply Organization, Application, Model, and Runtime governance; explicitly enforce Lookup-only ticket-tool access, justify system risk, and reject an oversized request under a runtime token/cost budget. | Implemented and verified: tool allowlist enforcement, Medium-risk justification, and a 300-word request rejected before CrewAI under token/reference-cost limits. |
| 16 — Cache | In-memory grounded-generation cache keyed by normalized query; show a repeat hit avoiding a redundant call with counters or measured timing. | Implemented and verified: normalized repeat hit; retrieval and grounded-generation counters both remained at one. Ticket/session data is not cached. |

Marks: Tasks 1–5 = **30**; Tasks 6–10 = **30**; Tasks 11–13 = **20**; Tasks 14–16 = **20**.

## Second task delivered: 12 knowledge-base documents

The files in `knowledge_base/` are **fictional policies authored for this Ola capstone**, not statements of Ola's actual policies. Every file contains a heading and five policy sentences. Use the filename as the document ID and preserve it as metadata when chunking, so evaluation can map chunks back to their parent documents. Index only these 12 files as policy sources, keeping this setup guide out of the policy collections.

| Document | Topic | Example question it should answer |
| --- | --- | --- |
| [01_ticket_priority.md](knowledge_base/01_ticket_priority.md) | Priority classification | Which issues are P1 Critical? |
| [02_sla_by_severity.md](knowledge_base/02_sla_by_severity.md) | SLA by severity | How quickly must a P2 ticket be acknowledged? |
| [03_escalation_matrix.md](knowledge_base/03_escalation_matrix.md) | Escalation matrix | Who reviews an account-takeover report? |
| [04_refunds_and_compensation.md](knowledge_base/04_refunds_and_compensation.md) | Refunds and compensation | What evidence is needed for a duplicate-charge refund? |
| [05_communication_channels.md](knowledge_base/05_communication_channels.md) | Communication channels | Can customer ticket details be shared on social media? |
| [06_business_hours_and_holidays.md](knowledge_base/06_business_hours_and_holidays.md) | Hours and holidays | Is routine support available on Sunday? |
| [07_repeat_complaints.md](knowledge_base/07_repeat_complaints.md) | Repeat complaints | What happens on the third report of an unresolved issue? |
| [08_service_credits.md](knowledge_base/08_service_credits.md) | Service credits | What is the maximum service credit for one incident? |
| [09_feedback_collection.md](knowledge_base/09_feedback_collection.md) | Feedback | What happens after a feedback rating of 1? |
| [10_vip_handling.md](knowledge_base/10_vip_handling.md) | VIP customers | Can a VIP P3 ticket jump ahead of a standard P1 ticket? |
| [11_outage_communication.md](knowledge_base/11_outage_communication.md) | Outage updates | How often should outage progress updates be sent? |
| [12_ticket_data_retention.md](knowledge_base/12_ticket_data_retention.md) | Retention | How long are closed tickets and request logs retained? |

These are example questions for understanding the documents, not a completed retrieval evaluation or the required 15-query scored evaluation.

### Shared rules checked across the documents

- Routine hours are Monday–Saturday, 09:00–18:00 Indian Standard Time; routine support closes on Sundays and the three listed project holidays.
- P1 receives continuous coverage; P2 and P3 timers count business hours only.
- The service-credit limit is INR 200 per incident, including for VIP customers; it cannot reimburse an already refunded charge.
- All approvals, payments, case-status changes, handoffs, and data deletion are human actions; the agent explains, retrieves, and recommends.
- The third report of the same unresolved issue within 30 calendar days requires lead review; P1 specialist handling is preserved.
- Closed tickets and feedback have a 90-calendar-day retention window; masked request logs have a separate 30-calendar-day window.

The generated ticket dataset does not contain severity, creation timestamps, ride/payment evidence, VIP designation, identity ownership, or repeat-complaint history. The agent must not invent these facts or claim a real SLA breach or financial eligibility from the available fields. The generated resolution-time field is an estimate for active tickets, not proof of an SLA timer or promise of completion.

## Third task delivered: working search indexes

See [TASK3-SEARCH.md](TASK3-SEARCH.md) for exact Windows setup commands, the splitting rules, tested dependency versions, and measured search results. `rag_index.py` builds the two persistent Chroma collections and retrieves source passages from either one. The starter includes actual execution evidence in `transcripts/task3_search_check.json`.

The same local MiniLM model creates real 384-dimensional embeddings for both indexes. The fixed strategy produced 31 overlapping chunks; the sentence strategy produced 36 chunks. Both returned the correct policy first for sample questions on credits, log retention, and Sunday support. Generated answers and the out-of-scope fallback are the next task.

## Work schedule

Updated 10 September: Portion 9 is complete. Use [EXECUTION-MAP.md](EXECUTION-MAP.md) for the execution portions and [PROGRESS.md](PROGRESS.md) for the exact handoff between turns and models. All 16 rubric tasks are implemented; the next checkpoint is a bounded final-rubric audit before the final README, clean setup, repository publication, and submission work.

## Technical details to preserve when we reach integration

- Use CrewAI's documented `BaseLLM` extension for the mock; do not fake `.kickoff()` or bypass real tool invocations.
- Avoid confusing example `Observation:` text in a system prompt with a real tool result. Dispatch arguments using the declared tool schema.
- Disable CrewAI telemetry before graded runs (`CREWAI_DISABLE_TELEMETRY=true` or `OTEL_SDK_DISABLED=true`).
- Use AutoGen's real bounded-team settings and register the structured verdict message type with the team.
- Record actual execution transcripts. Do not invent test scores, performance evidence, or approval/revision outputs.
- The Ola brief's generic README instruction mentions an amount range, but its actual record schema requires resolution hours and no amount field. Document the resolution-hour range and avoid adding an unrelated banking field.

## Next session

The next task is Portion 10A: use Astra Medium for one bounded final-rubric audit of the completed system, then repair any confirmed gaps before final packaging. Use `PROGRESS.md` as the handoff checkpoint between turns and models.
