# Task 14 — Independent AutoGen answer review

## What this portion adds

The system now has a second checking stage after CrewAI. CrewAI still retrieves or looks up the facts and composes the draft. AutoGen then receives both that draft and the original tool evidence.

| AutoGen agent | Job |
| --- | --- |
| Evidence Reviewer | Compares every material part of the CrewAI draft with the original evidence. |
| Final Editor | Keeps a supported answer unchanged or replaces an unsupported answer with the evidence-backed answer. |

The two agents run through the real AutoGen `RoundRobinGroupChat` with `max_turns=2`. This is deliberately bounded so the review cannot continue indefinitely.

## Typed final verdict

The Final Editor uses `output_content_type=ReviewVerdict`. The team registers `custom_message_types=[StructuredMessage[ReviewVerdict]]`. Every final message must therefore validate these three fields:

- `approved`: whether the original draft passed.
- `final_answer`: the unchanged or corrected answer returned to the customer.
- `reason`: why the answer was approved or revised.

## Recorded demonstrations

`verify_portion6.py` first executes a real CrewAI policy draft and preserves its retrieved context. It then runs two real AutoGen reviews:

1. The supported CrewAI draft is approved and its answer remains exactly unchanged.
2. The same draft is deliberately changed to claim a 24-business-hour P2 acknowledgement. AutoGen rejects it and restores the evidence-backed answer.

The language-model clients are deterministic local mocks. AutoGen, its two agents, typed message, team, and bounded execution are real. No API key or runtime network is used.

Run:

```powershell
python verify_portion6.py
python -m unittest test_autogen_review.py
```

The full execution record is written to `transcripts/portion6_evidence.json`.

