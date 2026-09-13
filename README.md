# Ola — Business Operations / Customer Support

This capstone is a working demonstration of a customer-support assistant for the **Ola — Business Operations / Customer Support** track. It answers questions from a fictional support handbook, checks fabricated support tickets, remembers a ticket within one chat session, masks supported personal-data formats, and reviews every grounded answer before returning it.

It does not connect to Ola, identify real customers, approve refunds, change tickets, or take financial actions. A human support employee remains responsible for those decisions.

## What happens when a customer asks something

1. The system masks supported phone, card-last-4, PAN, Aadhaar, and labelled bank-account formats. It blocks obvious prompt-injection instructions.
2. Session memory understands a follow-up such as “What is its status?” when the earlier turn named a ticket.
3. CrewAI runs three workers: Retrieval finds handbook text, Lookup checks fabricated ticket records, and Composer creates a typed answer.
4. Pydantic checks the response format and the output guard rejects unsupported claims.
5. Two AutoGen reviewers compare the draft with the original evidence and approve or correct it.
6. FastAPI returns the answer and writes one masked JSON-Lines log record with a trace ID and timing.

CrewAI and AutoGen use deterministic `MOCK_LLM` implementations. This keeps the project free and repeatable while still exercising the real framework workflows. Policy search uses a real local SentenceTransformers model and two real ChromaDB collections.

## Project map

| Item | Purpose |
| --- | --- |
| `dataset.py` | Generates and validates 50 fabricated support tickets. |
| `knowledge_base/` | Twelve original fictional support-policy documents. |
| `rag_index.py` | Builds and searches fixed-size and sentence-based Chroma indexes. |
| `crew_workflow.py` | Runs the three CrewAI workers and their tools. |
| `session_service.py`, `guardrails.py` | Conversation memory, masking, injection checks, and grounded-output checks. |
| `autogen_review.py` | Bounded two-agent answer review. |
| `api_app.py`, `run_server.py` | HTTP and WebSocket access. |
| `evaluation.py`, `verify_*.py`, `test_*.py`, `tests/` | Evaluation and verification. |
| `transcripts/` | Real machine-readable execution evidence. |

## Dataset design

The generator uses random seed `3`, so the same 50 records are recreated every time. Category weights are Billing 30, Technical Issue 25, Account Access 15, Product Defect 10, and General Inquiry 20. Status weights are Open 20, In Progress 25, Escalated 15, Resolved 25, and Closed 15. These are generator weights, not guaranteed final percentages.

Ten of 50 records have an escalation flag: 20%. Resolution time is an integer from 1 to 72 hours, chosen to cover quick fixes through cases requiring several days; ticket age is an integer from 0 to 30 days. Active-ticket resolution hours are estimates. Escalated-status tickets always have the flag; resolved/closed tickets have a seeded 12% probability of a historical escalation. The required Ola ticket schema has no amount field, so amount range is not applicable. All tickets and policies are fictional and contain no real customer data or real Ola policy claims.

CrewAI telemetry is disabled before import with `CREWAI_DISABLE_TELEMETRY=true` and `OTEL_SDK_DISABLED=true`. The verification runner removes API keys; the graded workflow uses local models and deterministic mocks. Internet is needed only for initial package/model setup.

## Windows setup

Use 64-bit Python 3.12. One-time setup needs internet access to install packages and download the pinned embedding model. After that, graded verification removes API keys and runs locally.

Open PowerShell in this project folder and run:

```powershell
py -3.12 -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install torch==2.14.0 --index-url https://download.pytorch.org/whl/cpu
python -m pip install -r requirements.txt
python prepare_model.py
python rag_index.py build
python verify_full_project.py
```

If PowerShell blocks activation, run `Set-ExecutionPolicy -Scope Process Bypass` in that terminal and activate again. A successful final command prints `"status": "PASS"`.

## Start and try the API

With the virtual environment active, run:

```powershell
python run_server.py
```

Open `http://127.0.0.1:8000/docs` in a browser. In `POST /ask`, use:

```json
{
  "session_id": "demo-1",
  "message": "How often should outage progress updates be sent?"
}
```

For a ticket example, use `Please check ticket SUP-0014.` The response includes the answer, review verdict, trace ID, and processing time. Use `POST /sessions/demo-1/reset` to clear that session. The WebSocket route is `/ws/chat/{session_id}`. The server only binds to your computer; stop it with **Ctrl+C**.

## Measured results

- Both Chroma indexes use pinned local `all-MiniLM-L6-v2` embeddings: 384 dimensions with cosine distance.
- Fixed-size splitting created 31 chunks; sentence splitting created 36. Sentence splitting was selected after a 12-query comparison: macro precision `0.6250`, macro recall `1.0000`, and the expected first source on 12 of 12 selected questions.
- The demonstrated fallback threshold is `0.40`.
- Ticket attention uses `0.65 × escalation flag + 0.35 × normalized age`, with a demonstrated threshold of `0.50`.
- The 15-case acceptance evaluation covers all 12 handbook topics plus a fabricated ticket, an out-of-scope question, and an injection attempt. Its deterministic judge gives `5.00/5` averages for Accuracy, Grounding, Completeness, and Safety on that selected set.

See `transcripts/portion9_evaluation.json`, `transcripts/full_integration_evidence.json`, and the task documents for the detailed records.

### Measured threshold calibration

These are top-1 cosine similarities from our actual calibration queries, not a general accuracy claim. The chosen `0.40` lies above the largest out-of-scope score (`0.278553`) and below the smallest in-scope score (`0.531457`) across both collections.

| Calibration question | Fixed | Sentence |
| --- | ---: | ---: |
| Maximum service credit for one incident? | 0.568735 | 0.531457 |
| How long are closed tickets and request logs retained? | 0.727765 | 0.764664 |
| Is routine support available on Sunday? | 0.624197 | 0.638851 |
| What happens after a feedback rating of 1? | 0.594146 | 0.623025 |
| Can a verified VIP P3 ticket take priority over P1? | 0.673769 | 0.695657 |
| Weather in Mumbai tomorrow? (out of scope) | 0.278553 | 0.273481 |
| How do I change a tyre? (out of scope) | 0.074373 | 0.095319 |
| Write a poem about the moon. (out of scope) | 0.080016 | 0.097531 |

Full query wording, separate document-level precision/recall arithmetic for both strategies, and the recommendation are in `transcripts/portion2_evidence.json` and `TASK4-5-GROUNDED-ANSWERS.md`.

### Submission

The student should understand and be able to explain the implementation and data flow. Submit this public repository URL as Question 2 and select the matching Ola domain in Question 1. Publishing to GitHub does not complete the LMS submission. No images, PDFs, slides, audio, or video are part of this repository deliverable.

## Limits of this demonstration

- The evaluation is a selected acceptance set, not held-out testing or proof of general accuracy.
- The judge is deterministic and rule-based. It suits this extractive mock but does not independently validate arbitrary paraphrases.
- Runtime token and cost figures are a preflight reference simulation because all LLM calls are free mocks. A paid deployment needs per-call accounting and enforced billing limits.
- The in-memory traces and cache support one demonstration process. Multi-process isolation is not established.
- There is no authentication, customer-ownership check, live Ola access, financial-action permission, arbitrary PII detection, or automated retention deletion.

The student should run the setup and examples and be able to explain the six steps above in their own words.

## Final verification

Read [FINAL-AUDIT.md](FINAL-AUDIT.md) for the 13 September requirement-by-requirement audit, repaired defects, two rerun records, and remaining limits. Run `python verify_full_project.py` for the offline graded checks. For an additional real-server check, with port 8000 free, run `python verify_live_server.py`; this uses localhost HTTP and WebSocket traffic and stops its server afterward.
