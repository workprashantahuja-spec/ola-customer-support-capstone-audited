# Tasks 4 and 5: grounded answers and retrieval comparison

Track: **Ola — Business Operations / Customer Support**.

Portion 2 is complete. The system now answers from retrieved handbook text, returns a fixed fallback below an empirically selected similarity threshold, and uses the measured comparison to choose sentence-based chunks. All results below come from `transcripts/portion2_evidence.json`; they are not estimated.

## What was built

- `grounded_answers.py` retrieves the top three chunks from the selected collection and gates the request on its top cosine similarity.
- The offline `DeterministicGroundedModel` returns only the body of the first retrieved chunk. It cannot add wording that is absent from that source.
- A below-threshold question returns the fixed fallback without calling the mock generator.
- `verify_portion2.py` reproduces calibration, six supported answers, one fallback and the same-query comparison of both indexes.

## Threshold calibration

The rule is: **answer when top similarity is at least 0.40; otherwise return the fallback**. The threshold is a retrieval gate, not a probability of correctness.

| Scope | Question | Fixed | Sentence |
| --- | --- | ---: | ---: |
| In | What is the maximum service credit for one incident? | 0.568735 | 0.531457 |
| In | How long are closed tickets and request logs retained? | 0.727765 | 0.764664 |
| In | Is routine support available on Sunday? | 0.624197 | 0.638851 |
| In | What happens after a feedback rating of 1? | 0.594146 | 0.623025 |
| In | Can a verified VIP P3 ticket take priority over a P1 case? | 0.673769 | 0.695657 |
| Out | What is the weather in Mumbai tomorrow? | 0.278553 | 0.273481 |
| Out | How do I change a tyre on my car? | 0.074373 | 0.095319 |
| Out | Write a poem about the moon. | 0.080016 | 0.097531 |

Minimum observed in-scope score across both collections: **0.531457**.
Maximum observed out-of-scope score across both collections: **0.278553**.
Observed gap: **0.252904**. The chosen **0.40** threshold lies inside that gap. This calibration satisfies five in-scope and three out-of-scope measurements; the final 15-query evaluation will provide a broader check.

Fallback text: `I do not have enough support-policy information to answer that question.`

## Same-query retrieval comparison

Both collections received the same 12 questions and returned three chunks per question. Before scoring, repeated chunks from the same source were collapsed to one parent document. For each query: `precision = relevant retrieved documents / unique retrieved documents`, and `recall = relevant retrieved documents / expected relevant documents`.

| Topic | Fixed P / R | Sentence P / R |
| --- | ---: | ---: |
| Ticket Priority | 1.0000 / 1.0000 | 0.5000 / 1.0000 |
| Sla By Severity | 0.5000 / 1.0000 | 0.5000 / 1.0000 |
| Escalation Matrix | 0.0000 / 0.0000 | 0.5000 / 1.0000 |
| Refunds And Compensation | 0.5000 / 1.0000 | 1.0000 / 1.0000 |
| Communication Channels | 0.5000 / 1.0000 | 0.5000 / 1.0000 |
| Business Hours And Holidays | 0.5000 / 1.0000 | 0.5000 / 1.0000 |
| Repeat Complaints | 0.5000 / 1.0000 | 0.5000 / 1.0000 |
| Service Credits | 0.5000 / 1.0000 | 0.5000 / 1.0000 |
| Feedback Collection | 0.5000 / 1.0000 | 1.0000 / 1.0000 |
| Vip Handling | 0.5000 / 1.0000 | 0.5000 / 1.0000 |
| Outage Communication | 1.0000 / 1.0000 | 1.0000 / 1.0000 |
| Ticket Data Retention | 1.0000 / 1.0000 | 0.5000 / 1.0000 |

| Result | Fixed | Sentence |
| --- | ---: | ---: |
| Macro precision | 0.5833 | **0.6250** |
| Macro recall | 0.9167 | **1.0000** |
| Correct first document | 11/12 | **12/12** |

**Recommendation: use sentence-based retrieval.** It achieved higher macro precision (0.6250 versus 0.5833), complete recall (1.0000 versus 0.9167), and the correct first document on all 12 questions. Complete sentence boundaries also make the extractive answers easier to read.

One concrete difference: for “Which human team handles a Technical Issue ticket?”, fixed-size retrieval returned only the ticket-priority document within its first three chunks and missed the escalation-matrix document. Sentence retrieval returned the escalation matrix first.

## Demonstrated behavior

- Six in-scope questions produced supported answers from the intended handbook source.
- The weather question scored 0.273481 on the selected sentence collection, returned the fallback, exposed no source and did not call the mock generator.
- The six supported requests made six generator calls; the fallback made zero additional calls.
- Seven focused unit tests passed: four chunking checks and three grounded-answer checks.
- During the integration run, Python socket connections and DNS resolution were blocked. Model preparation and dependency installation remain the only online setup steps.

## Reproduce

From the project folder after completing the Task 3 setup:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe verify_portion2.py
```

Linux/macOS uses `.venv/bin/python` in place of the Windows executable. Full per-query retrieved documents, arithmetic, answers, scores and sources are stored in `transcripts/portion2_evidence.json`.

## Limit retained for later testing

The cutoff is calibrated to the required sample rather than every possible sentence a user could write. Portion 9 will test the full system on 15 questions, including edge cases. A future handbook edit requires rebuilding the indexes and rerunning this calibration because similarity scores can change.
