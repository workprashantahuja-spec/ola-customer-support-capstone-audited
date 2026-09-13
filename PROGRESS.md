# Ola capstone progress checkpoint

Latest audit: 13 September 2026. Read FINAL-AUDIT.md and README.md; they supersede historical test-count and publication claims below.

## Completed

- Portion 1 / rubric Tasks 1–2: deterministic 50-ticket dataset and 12 fictional support-policy documents.
- Retrieval foundation / Task 3: two real local SentenceTransformers + ChromaDB indexes, repeatable upsert and offline retrieval evidence.
- Portion 2 / Tasks 4–5: calibrated 0.40 fallback, six grounded answer demonstrations, one out-of-scope fallback and a 12-query document-level comparison. Sentence chunks selected: macro precision 0.6250, macro recall 1.0000, first source correct 12/12.
- Portion 3 / Task 6: `check_support_ticket_status(record_id)` with a 0–1 escalation score. Formula: 0.65 × stored escalation flag + 0.35 × normalized age. The measured 0.50 threshold cleanly separates 10 flagged tickets (0.6617–0.9883) from 40 unflagged tickets (0.0000–0.3500).
- Portion 4 / Tasks 7 and 9: real CrewAI Retrieval, Lookup, and Composer agents with two actual `Crew.kickoff()` runs. The policy and ticket tools each ran once on suitable requests, both final responses passed `SupportResponse` validation, and an incomplete response was rejected.
- Portion 5 / Tasks 8 and 10: LangChain session histories retain a ticket across a same-session follow-up while a fresh session starts clean. Input guardrails mask supported phone, card-last-4, PAN, Aadhaar, and labelled bank-account formats and block prompt injection before CrewAI. The output guardrail checks responses against tool evidence and rejects a deliberate unsupported claim.
- Portion 6 / Task 14: a real two-agent AutoGen `RoundRobinGroupChat(max_turns=2)` reviews the CrewAI draft against original tool evidence. Its Final Editor emits a registered, Pydantic-validated `StructuredMessage[ReviewVerdict]`. A supported answer remained unchanged and a planted 24-hour error was corrected to the retrieved 4-business-hour policy.
- Portion 7 / Tasks 11–12: FastAPI supplies health, ask, and session-reset HTTP routes plus a multi-turn WebSocket chat route. Disconnects are handled cleanly. Each HTTP request and chat message receives a trace ID, timing, and one masked JSON-Lines record; a six-record route exercise proves the pipeline, review, session memory, safe logs, and disconnect behavior.
- Portion 8 / Tasks 15–16: all four course governance layers are documented and connected to implementation. A code allowlist blocks non-Lookup agents from receiving the ticket tool; the system is justified as Medium risk. A 300-word request is rejected before CrewAI under token/reference-cost limits. A normalized repeated policy question produces a real cache hit, leaving both retrieval and generation counters at one.
- Portion 9 / Task 13 and integration: 15 requests ran through the complete API pipeline, covering all 12 handbook topics, a fabricated ticket, an out-of-scope query, and a prompt-injection attack. The deterministic MOCK_LLM judge reported 5.00/5 averages for Accuracy, Grounding, Completeness, and Safety on this controlled set.
- Portions 10B–10C: documentation and walkthrough are available and GitHub publication is complete. The 13 September audit repaired missing logging coverage, dependency declarations, review context, and inaccurate evidence counts. See FINAL-AUDIT.md for measured results; a fresh Windows install is not claimed.

## Next task

Portion 10A audit and Portions 10B–10C packaging are complete. Earlier perfect evaluation claims are limited to a selected acceptance set. Budget is a simulated preflight estimate, not actual aggregate token accounting.

Next: confirm final LMS submission of the public URL and practice explaining the project.

## Connections that must be preserved

- Final answers use sentence retrieval and the threshold in `rag_config.py`.
- `grounded_answers.py` is the reusable retrieval-answer layer for the later CrewAI retrieval tool and response cache.
- Dataset age is not proof that a real SLA was breached; resolution hours is an estimate for active tickets.
- The submitted system defaults to deterministic MOCK_LLM, real CrewAI `.kickoff()`, real local embeddings and zero runtime network/API keys after setup.
- Do not mark work complete without real output in `transcripts/`.

## Remaining portions

10. Public GitHub publication is complete. Final LMS submission and Windows setup remain unverified; see FINAL-AUDIT.md.
