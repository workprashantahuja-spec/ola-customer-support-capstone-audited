# Portion 10A — grading audit and targeted repairs

Verdict: core demonstrations exist for all 16 tasks. The earlier blanket statement that everything was verified was too strong. This audit found and repaired concrete gaps; final submission packaging and clean installation remain unfinished.

## Checklist against the original Ola brief

| Task | Audit result and evidence |
| --- | --- |
| 1 | Seeded 50-record generator, required fields/counts and 20% escalation; dataset.py. |
| 2 | Twelve separate five-sentence fictional policies cover the required topics. |
| 3 | Real local embeddings, overlapping fixed and sentence collections, upsert and stale metadata checks; task3_search_check.json. |
| 4 | Measured calibration separates the demonstrated clusters at 0.40; six answers and a fallback. This is not a universal relevance guarantee. |
| 5 | Twelve same-query document-deduplicated comparisons with arithmetic; includes five Task 4 calibration questions. |
| 6 | Required lookup fields, weighted score and measured threshold exist; unknown IDs previously broke the API, now return a logged controlled error. |
| 7 | Three real CrewAI agents, BaseLLM mocks, real kickoff/tool demonstrations. |
| 8 | LangChain per-session ticket follow-ups and separate fresh-session evidence exist. Full free-form conversational understanding is not implemented. |
| 9 | Pydantic crew output validation exists. |
| 10 | Required phone masking and injection demonstrations exist. Repaired ticket-answer text validation; previously an invented refund claim passed when structured ticket fields were unchanged. |
| 11 | Three HTTP routes and a WebSocket, disconnect demonstration. Added malformed-message handling and serialized API processing to prevent overlapping requests reading shared latest tool traces in one app. |
| 12 | Repaired missing logs for tested invalid/failed ask requests and masking of user-controlled session identifiers. All application routes and unexpected errors still need broader coverage before claiming universal request logging. |
| 13 | Fifteen cases and four score averages exist. Repaired judge grounding by checking independent policy text rather than trusting source labels. Invented compensation appended to a correct answer now scores 1 on Accuracy/Grounding/Safety instead of 5. |
| 14 | Real two-agent AutoGen team, max_turns=2, registered typed verdict, approval and correction evidence. |
| 15 | Role allowlist and Medium-risk justification meet the demonstrated scope. Long unbroken input previously counted as one token; byte-aware input sizing now rejects it. Budget remains a simulated preflight estimate, not measured aggregate framework token use or enforceable future paid-model billing. |
| 16 | Real repeated grounded-generation hit avoids a second generation. Repaired same-process cache invalidation: check source/config fingerprint on every answer. Ticket results are not cached; policy queries themselves are retained in memory. |

## Direct before/after probes

| Probe | Before | After |
| --- | --- | --- |
| Invented ticket-answer text | Accepted by output guard | Rejected |
| Correct policy plus invented INR 50000 entitlement | Judge gave four 5s | Accuracy/Grounding/Safety = 1 |
| 3,600-byte unbroken input | Accepted as one token | Rejected by size estimate |
| Injected source-version change in same engine | Cached old answer | New answer, new retrieval |
| Missing message | HTTP 422, zero logs | HTTP 422, one log |
| Whitespace message | HTTP 500, zero logs | HTTP 400, one log |
| Unknown ticket | HTTP 500, zero logs | HTTP 400, one log |
| Fabricated phone used as session ID | Raw identifier logged | Masked |

Reproduce with `python audit_regressions.py`. Audit files use fabricated data and an injected source-version change; the actual handbook is not altered.

## Limits that must appear in the final README

- Evaluation is a selected acceptance set. An earlier natural question, “Who handles a suspected account takeover?”, scored 0.388068 and fell back, while the more explicit selected wording passed. Do not call these held-out results or general accuracy.
- The judge is deterministic and rule-based. Its prompt is recorded, but no independent real LLM interprets it. Exact-source checks suit this extractive mock; they do not validate arbitrary paraphrases.
- Runtime cost is a reference simulation. Actual calls are free mocks. The 768-token reserve is not measured full-pipeline consumption. A real paid model needs per-call accounting and enforced limits.
- Class-level traces and shared caches are demonstration conveniences. One API app serializes chat processing; multi-process or multiple app-instance isolation is not established.
- Unknown-ticket errors are now controlled but use a generic message; improve usability during packaging if needed.
- Authentication, customer ownership checks, live Ola access, financial actions, arbitrary PII detection, and automated retention deletion are not implemented.
- Existing full_integration_evidence.json records the pre-audit run. Do not present it as post-audit evidence; targeted tests and the refreshed evaluation cover this change, and final clean setup must rerun the entire runner.

## Next checkpoint

Portion 10B, Sol Medium: finish the README with the above limits, add a straightforward server-start command, verify a clean installation, and rerun the full test runner. Address any remaining request-logging acceptance gap before public repository preparation. Then prepare the single GitHub submission and the business walkthrough.

Source: original user-supplied Pasted text(20260829-212814).txt, all 284 lines reviewed. Course AI-assistance clarification recorded in START-HERE remains the working context; do not misrepresent authorship.
