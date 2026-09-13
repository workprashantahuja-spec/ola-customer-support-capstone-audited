# Ola capstone execution map

Current checkpoint, 13 September: read FINAL-AUDIT.md. GitHub publication is complete. Historical schedule, next-step and test-count claims below are superseded by that audit; final LMS submission and Windows setup remain unverified.

Current handoff supersedes the older Next execution paragraph below: Portions 10A–10C are complete. Read README.md, BUSINESS-WALKTHROUGH.md, AUDIT10A.md, and GITHUB-PUBLISHING.md. The remaining work is public GitHub publication and LMS submission.

Prepared 9 September 2026. Submission: Sunday 13 September, 11:59 PM according to the course orientation; confirm the portal timezone at submission. Working-version target: Friday 11 September. This is a target, not a guarantee.

## Product and ownership

Build a demonstration customer-support assistant for the Ola domain. It answers questions from our fictional support handbook, checks fabricated tickets, recommends human attention where appropriate, remembers a conversation, and checks answers before returning them. It does not operate Ola's real systems or issue refunds.

The assistant owns implementation, integration, debugging, measurement, execution evidence and documentation. Prashant reviews the business meaning and learns to explain the workflow. Account sign-in and the final LMS submission require his account interaction unless supported access is available. Model selections below are recommendations for building the project in ChatGPT, not models that must run inside the submitted application.

## Execution portions

| # | Portion | Work and concrete completion evidence | Recommended build model | Rubric tasks / current status |
| --- | --- | --- | --- | --- |
| 1 | Business rules and sample information | Define what the assistant can do, its human boundaries, 50 fabricated tickets, and 12 short handbook documents. Preserve the existing validated dataset and consistent policies; review business assumptions. | Terra Medium for any amendments | 1–2: built and checked |
| 2 | Reliable handbook answers | Complete grounded answers on top of the two existing search indexes. Measure when to say information is unavailable; compare both search methods on identical questions and choose using precision/recall. Deliver measured results, cited answers and a fallback example. | Sol Medium | 3–5 built and verified; sentence strategy selected |
| 3 | Ticket checks and escalation | Look up a ticket, explain its status and resolution-hours field, and calculate a 0–1 attention score using its escalation flag and age. Justify the formula and threshold from our dataset. Demonstrate known and missing IDs. Do not infer actual SLA breaches from age alone. | Terra Medium | 6 built and verified |
| 4 | Connect the three workers | Use real CrewAI retrieval, lookup and answer-composer agents with a deterministic mock model. Validate every crew response with Pydantic. Record actual kickoff and tool calls for both question types. | Sol Medium; raise to High only for a specific integration blocker if available | 7 and 9 built and verified |
| 5 | Conversation memory and safety | Remember follow-up context within one session, show a new session starts fresh, mask phone numbers, reject instruction attacks and block unsupported answers. Deliver deliberate tests for every safeguard. | Sol Medium | 8 and 10 built and verified |
| 6 | Independent answer review | Pass the draft and original evidence to a real two-agent AutoGen review. Bound the conversation; return a typed verdict. Demonstrate an unchanged approval and a correction of an intentionally unsupported claim. | Sol Medium; High only for a specific unresolved integration problem | 14 built and verified |
| 7 | Access and request records | FastAPI health, ask, and session-reset HTTP routes plus a WebSocket chat route. Each request/message is logged after masking with a trace ID and timing; disconnects are handled safely. | Terra Medium | 11–12 built and verified |
| 8 | Permissions, limits and repeated questions | All four governance layers are applied. Only the Lookup agent can receive the ticket tool; Medium risk is justified; a 300-word request is rejected before CrewAI. A normalized repeat cache hit avoids a second retrieval and generation; ticket/session data is excluded and a knowledge/config namespace prevents stale reuse. | Sol Medium | 15–16 built and verified |
| 9 | Whole-project quality check | Fifteen API requests cover all 12 topics plus ticket, fallback, and injection cases. Every required metric is recorded per query and averaged. All 13 full-project commands pass offline, including 43 main tests, 11 dataset/retrieval tests, every verifier, and dependency checks. | Sol Medium for measured evaluation; Astra Medium reserved for the next bounded final audit | 13 and integration verification built and passed |
| 10 | Submission and your walkthrough | Finish README, setup instructions and actual execution transcripts; check a clean installation, prepare a public GitHub repository and explain sample journeys in plain language. Match the exact LMS domain label with the repo, verify public access and submit its single link. | Terra Medium | Delivery pending; user laptop setup remains unverified |

## Working order and timing

These are outcome groups, not promises of equal duration. Write demonstration cases with each portion and record results after it runs; portion 9 consolidates evaluation rather than postponing all testing until the end.

| Date | Target |
| --- | --- |
| Wednesday 9 Sep | Finish portions 2–3 and start portion 4. |
| Thursday 10 Sep | Finish portion 4 and implement portions 5–6. |
| Friday 11 Sep | Complete portions 7–8 and run the first whole-system evaluation. |
| Saturday 12 Sep | Finish portion 9, repair blockers, prepare portion 10 and verify clean setup. |
| Sunday 13 Sep | Final access and submission checks; submit before the portal deadline. |

If work slips, remove optional polish, not rubric requirements. No custom dashboard, slide deck, WhatsApp integration, live Ola integration or paid runtime LLM is planned. The brief accepts code and text in one public repository; do not add prohibited media.

## Model budget practice

Use the recommendation for the active portion, rather than running every task on Astra. A model change should inherit this file, START-HERE.md and the latest real results. Close each portion with what changed, what ran, what remains and the next portion. Do not re-read six lectures or rebuild completed work every time the model changes.

Astra is reserved for one bounded review of cross-component correctness and missing grading requirements. A concrete difficult bug can justify higher reasoning; no blanket Astra High allocation is needed. Recommendations are engineering judgment, not measured benchmarks or guaranteed subscription-limit savings. Available picker choices and account limits vary; the assistant cannot promise or automatically change the main conversation's model.

The submitted application defaults to deterministic MOCK_LLM. It must execute real framework and retrieval code with zero API keys and no runtime network after dependency/model setup. Mock judge scores are test-harness results, not independent proof of real-world LLM quality. Any business improvement is a proposed benefit unless actually measured.

## Lecture findings applied

- Design the business scope, agent roles, data handoffs, tools, human boundaries and success measures before connecting components.
- Nimbus Pay Desk is the practice example. Its invoice/GST/purchase-order rules, payment thresholds and optional n8n webhooks do not become Ola requirements.
- Lectures contain conflicting earlier guidance about substituting LangChain. The later support Q&A explicitly requires CrewAI and calls out automated kickoff checks; retain the named stack in the original Ola brief.
- AI assistance is permitted, with a strong expectation that the student understands the implementation and data flow. Include a practical walkthrough throughout the build.
- Use separate short knowledge documents, deterministic synthetic data, real execution traces and explicit negative tests. A plausible answer without the required tool execution does not prove the workflow works.
- Final delivery is one public GitHub repository plus the matching exact domain name in LMS, not separate submissions for each portion.
- Governance: the brief and supplied transcripts explicitly describe Application and Runtime controls but do not clearly enumerate all four governance layer names. Do not confuse the Nimbus architecture floors (interface, orchestration, tools, data) with that governance model. Look for the course governance notes during portion 8; document any remaining terminology uncertainty rather than inventing course labels.

## Sources consulted

Original user-supplied Ola brief: Pasted text(20260829-212814).txt; existing START-HERE.md and Task 3 execution evidence.

All six lecture attachments supplied on 9 September:
1. Pasted markdown(20260909-152145).md — business design and Nimbus orientation.
2. Pasted markdown (2)(5).md — interfaces, ingestion, HTTP, observability and trace IDs.
3. Pasted markdown (3)(4).md — course submission orientation and project scaffolding.
4. Pasted markdown (4)(2).md — practical tool, database, retrieval and pipeline wiring.
5. Pasted markdown (5)(2).md — final domain briefs, rubric and Ola requirements.
6. Pasted markdown (6)(1).md — support clarification on CrewAI, separate documents and AutoGen review.

Official current model-selection reference: https://learn.chatgpt.com/docs/models (consulted 9 September 2026). The per-portion recommendations above are our application of that guidance.

## Next execution

Create the public GitHub repository from this prepared local Git project, verify that its README and transcripts are visible without signing in, then submit its single URL in LMS under the exact Ola track name.
