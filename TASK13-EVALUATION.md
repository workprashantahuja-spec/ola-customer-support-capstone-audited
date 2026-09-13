# Task 13 — Fifteen-query evaluation and integration check

## What was tested

The test sends 15 requests through the real FastAPI route and the connected safety, memory, CrewAI, grounded-retrieval, AutoGen-review, and logging pipeline.

| Cases | Coverage |
| --- | --- |
| E01–E12 | One question for each of the 12 fictional handbook topics. |
| E13 | Fabricated ticket lookup for `SUP-0014`. |
| E14 | Out-of-scope weather question that must return the exact fallback. |
| E15 | Prompt-injection attempt that must be blocked before CrewAI. |

## How scoring works

`evaluation.py` supplies a written judge prompt to a deterministic `MOCK_LLM` judge. It returns a Pydantic-validated score from 1 to 5 for every measure:

| Measure | Meaning |
| --- | --- |
| Accuracy | Does the response agree with the expected facts? |
| Grounding | Is the answer tied to the approved handbook/ticket source, or correctly evidence-free when blocked/fallback? |
| Completeness | Does it contain every fact required for the question? |
| Safety | Does it avoid unsupported actions or data exposure and handle unsafe/out-of-scope input correctly? |

## Measured result

| Metric | Average across 15 |
| --- | ---: |
| Accuracy | 5.00 / 5 |
| Grounding | 5.00 / 5 |
| Completeness | 5.00 / 5 |
| Safety | 5.00 / 5 |

Every individual score is recorded in `transcripts/portion9_evaluation.json`, together with the query, observed API response, judge prompt, reason, source, and score. Exactly 15 corresponding JSONL request records were produced.

These perfect scores mean the deterministic implementation passed this controlled acceptance set. They must not be presented as proof of perfect accuracy on untested real-world language or live Ola data.

## Whole-project verification

`verify_full_project.py` runs the dataset validation, every portion verifier, both unit-test groups, and dependency checks with API keys and proxy variables removed and CrewAI telemetry disabled. Its evidence is written to `transcripts/full_integration_evidence.json`.

Run:

```powershell
python verify_portion9.py
python -m unittest test_evaluation.py
python verify_full_project.py
```
