# Final submission audit — 13 September 2026

Scope: the public Ola capstone repository, checked against all 284 lines of the original supplied `Pasted text(20260829-212814).txt` and the later Final Capstone LMS submission instructions inspected in this conversation. This is a requirements and execution audit, not a guarantee of marks, plagiarism-detector results, production readiness, or correctness for arbitrary unseen questions.

## Execution results

The starting GitHub revision was `92bc5abef7224b8868a103f13deb3b7094dce1b9`. All 82 published file hashes matched the local source before this audit. That version passed its existing 13-command runner (43 main tests and 11 retrieval tests), but additional independent checks exposed gaps that its existing suite did not catch.

The repaired version is checked by two full reruns, with separate records in `transcripts/final_audit_run1.json` and `transcripts/final_audit_run2.json`. The summary and source hashes are in `transcripts/final_audit_summary.json`. Each successful full run executes 14 commands, including 48 main tests, 11 retrieval tests, the earlier adversarial regression probes and `pip check`.

Separately, `verify_live_server.py` starts the actual `run_server.py` entry point, checks policy/ticket/fallback responses over HTTP, runs a two-turn WebSocket ticket conversation, disconnects and verifies the server remains healthy. Its result is saved in `transcripts/live_server_evidence.json`. This supplemental check uses localhost networking; the graded verifiers exercise the offline mock path.

## Confirmed defects repaired

| Finding before repair | Repair and verification |
| --- | --- |
| `/docs`, `/openapi.json`, unmatched URLs, method errors and unexpected route exceptions could miss the JSONL request log. | Central HTTP logging writes exactly one masked record per completed request; independent tests include 404, 405, 422 and 500 responses. Trace IDs and actual elapsed timings are checked. |
| Default Uvicorn access logs could print raw identifiers in URL paths. | `run_server.py` disables access logging; application logs use route templates and masked session identifiers. |
| An unknown ticket caused a Composer parsing error and a generic 400 result. | Composer recognizes the actual tool's error payload; the API returns a controlled 404 “Ticket not found.” with one request log. |
| The full runner omitted `audit_regressions.py`. | It now runs that regression check; 14 commands are actually executed. |
| Logging evidence reported `len(entries) == 4` despite a six-request exercise. | The evidence condition now checks six and the verifier reruns. |
| README omitted required measured calibration values and explicit telemetry settings. | Added the empirical score table, threshold justification, telemetry flags, dataset range reasoning and escalation-generation details. |
| Server dependencies were not explicitly declared. | Pinned Uvicorn and WebSockets to the installed, exercised versions. |
| AutoGen received the generated tool answer but no separate original policy passage. | Grounded generation carries its original retrieved passage into review. A new adversarial test corrupts the generated answer and confirms the review corrects it from the passage. |
| Historical documentation claimed 14 commands/44 tests, while the published package had 13/43. | Corrected the packaging/progress notes and identified historical text as superseded by this audit. |

## All 16 tasks

“Pass” below means demonstrated against the brief's deterministic mock acceptance scope, subject to the explicit qualifications at the end.

| Task | Requirement | Implementation and evidence | Result |
| --- | --- | --- | --- |
| 1 | Seeded dataset, at least 40 records, required schema/vocabularies/counts, 10–30% escalated | `dataset.py` regenerates 50 tickets; validates category counts ≥3, status coverage, integer ranges, booleans, IDs and 20% escalated. Generator output is in the full-run record; design choices are in README. | Pass |
| 2 | At least 12 original policy documents, 2–5 sentences each, every required topic | All 12 `knowledge_base/*.md` files contain five policy sentences; priority, SLA, escalation, refunds, channels, hours, repeats, credits, feedback, VIP, outage and retention are covered. | Pass |
| 3 | Two chunking strategies, local embeddings and separate Chroma upserts | `rag_index.py`; fixed 400-character chunks with 80-character overlap and sentence chunks; local 384-dimensional embeddings; 31 fixed and 36 sentence chunks. `task3_search_check.json` checks retrieval, repeated upsert and reopening. | Pass |
| 4 | Empirically calibrated fallback and ≥5 supported answers plus an out-of-scope fallback | Five in-scope and three out-of-scope calibration queries; six answer demos and a fallback; threshold 0.40 between measured clusters. `portion2_evidence.json`, README. | Pass |
| 5 | Document-deduplicated precision/recall for both strategies on the same ≥5 queries; numeric recommendation | Twelve common queries, including five calibration queries, with per-query arithmetic. Fixed macro P/R 0.5833/0.9167; sentence 0.6250/1.0000. `portion2_evidence.json`, `TASK4-5-GROUNDED-ANSWERS.md`. | Pass |
| 6 | Ticket lookup and designed, justified 0–1 escalation score | `ticket_lookup.py`; 0.65 × flag + 0.35 × age/30, threshold 0.50 in measured gap between flagged/unflagged groups. `portion3_evidence.json`. | Pass |
| 7 | ≥3 real CrewAI agents, `.kickoff()`, both tools actually called | Retrieval, Lookup and Composer use `BaseLLM` mocks with route-specific tasks. Both real tool invocations and structured results are in `portion4_evidence.json`. No fake kickoff. | Pass |
| 8 | LangChain session memory, multi-turn example and separate fresh-conversation transcript | `InMemoryChatMessageHistory`; `portion5_evidence.json`, `same_session_transcript.json` and `fresh_session_transcript.json`. Fresh session asks for the missing ticket ID. | Pass |
| 9 | Pydantic schema validates every final crew response | `SupportResponse`, task `output_pydantic`, explicit `model_validate`; malformed-response tests. `portion4_evidence.json`. | Pass |
| 10 | Input phone masking and injection detection; output groundedness guard; deliberate triggers | `guardrails.py`, `portion5_evidence.json`, `audit10a_evidence.json`; planted unsupported ticket text is rejected. Other documented fixed-format masks are also exercised. | Pass |
| 11 | ≥2 HTTP endpoints plus a disconnect-safe WebSocket, Pydantic models | `/health`, `/ask`, session reset and `/ws/chat/{session_id}`; `portion7_evidence.json` and actual-server smoke test. | Pass |
| 12 | Every request has one JSONL record with trace, timing and masked fixed-format PII | HTTP logging middleware plus per-message WebSocket logging; nine HTTP boundary cases, injected 500, unknown ticket, invalid WebSocket JSON and disconnect tests. `test_submission_audit.py`, `portion7_evidence.json`. | Pass |
| 13 | 15-query mock-judge evaluation covering 12 topics plus ≥2 edge cases, all four scores and means | `evaluation.py`, `portion9_evaluation.json`: 12 policy queries plus ticket, fallback and injection cases; Accuracy, Grounding, Completeness and Safety reported individually and averaged. | Pass for selected set |
| 14 | Real two-agent AutoGen review with two turns, registered Pydantic verdict, approval and correction | `RoundRobinGroupChat(max_turns=2)`, `StructuredMessage[ReviewVerdict]`, real approval/correction examples in `portion6_evidence.json`; original-passage corruption regression. | Pass |
| 15 | Least autonomy, risk explanation, four-layer governance and oversized simulated-budget rejection | Lookup-only tool allowlist and denied wrong-role assignment; Medium-risk explanation; 300-word and long-unbroken requests rejected before crew. `portion8_evidence.json`, `audit10a_evidence.json`. | Explicit controls pass; layer-name qualification below |
| 16 | Normalized query cache avoids a redundant generation/tool call with evidence | Policy-only cache, source/config invalidation, before/after retrieval and generation counters. `portion8_evidence.json`. | Pass |

## Submission rules

- One public GitHub repository: `https://github.com/workprashantahuja-spec/ola-customer-support-capstone-audited`. Public visibility was verified during this audit.
- README begins with the Ola Business Operations / Customer Support track, seeded design choices, mock operation, setup and limitations.
- Repository deliverables are code/text; no uploaded images, PDFs, slides, audio, video, virtual environment or model weights are included. Model weights and the Chroma database are prepared locally by the setup commands.
- Graded mock execution requires no API keys or paid account. Initial dependency/model preparation needs internet. Telemetry is disabled before CrewAI imports; offline verifiers block Python socket/DNS calls around demonstrations. This is not claimed as an OS-level network isolation proof.
- AI-rule conflict: the original brief and the later authenticated Final Capstone LMS instructions differ on AI-tool use. The later LMS instructions explicitly allow AI tools and require the student to understand the code, implementation and data flow. A plagiarism/similarity score is not predictable or guaranteed by this audit.
- Amount-range ambiguity: the generic README instruction mentions amount, but the Ola record schema contains no amount field. README explicitly states “not applicable” and documents resolution hours instead.
- Governance-name ambiguity: the supplied brief explicitly names Application and Runtime, but does not specify the other two layer names. Organization and Model are documented project interpretations. This audit cannot certify agreement with an unseen course-specific taxonomy.
- Final LMS action: Question 1 must select the exact `Support` domain; Question 2 must contain `https://github.com/workprashantahuja-spec/ola-customer-support-capstone-audited`. The LMS page is `https://students.masaischool.com/assignments/82616?tab=assignmentDetails`. Its displayed deadline was 13 September, 20:29 Italy time / 23:59 IST. **This audit does not verify that the final LMS submission was completed or accepted.**

## Practical limits

Tests ran on Linux with the retained Python 3.12 environment and pinned local model; both indexes were rebuilt and installed dependency consistency was checked. This is not a new clean dependency download or a Windows-laptop installation test. The Windows commands remain unexecuted on the student's laptop in this audit.

The judge is deterministic, results come from a selected acceptance set, and the empirical threshold can reject valid unseen paraphrases. Budgets are simulated preflight estimates, not paid-model usage accounting. The system uses fabricated tickets/policies and has no real Ola connection, customer authentication, automatic financial actions or production-grade multi-process isolation. Student understanding must be demonstrated by the student; software tests cannot establish it.
