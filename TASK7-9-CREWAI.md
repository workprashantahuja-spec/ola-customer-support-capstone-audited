# Tasks 7 and 9 — CrewAI agents and structured responses

## What this portion adds

`crew_workflow.py` connects the earlier policy-answer engine and ticket lookup to a real CrewAI workflow. It creates three agents:

| Agent | Responsibility | Tool access |
| --- | --- | --- |
| Policy Retrieval Specialist | Retrieves an answer from the 12 fictional support-policy files. | `search_support_policies` only |
| Ticket Lookup Specialist | Looks up one fabricated support ticket. | `check_support_ticket_status` only |
| Support Response Composer | Converts the worker result into the final response schema. | No tools |

The workflow uses CrewAI's actual `Crew` and `Task` classes and directly executes `Crew.kickoff()`. The local deterministic model subclasses `crewai.llms.base_llm.BaseLLM`; it replaces only the paid language model, not CrewAI or its agent/tool execution.

## Why there are two demonstrations

A policy question and a ticket-ID request need different evidence. The verifier therefore runs two crews:

1. `How quickly must a P2 ticket be acknowledged?` invokes the policy-search tool.
2. `SUP-0001` invokes the ticket-status tool.

This proves that both tools ran on suitable requests. The Composer cannot access either tool, and the Retrieval agent cannot access ticket records.

## Structured output

Every final crew result must validate as `SupportResponse`. The schema requires the request type, answer, grounding and fallback flags, sources, and optional validated ticket details. CrewAI receives it through `Task(output_pydantic=SupportResponse)`, and the workflow validates the returned object again before returning it. The verifier also deliberately submits an incomplete object and confirms that Pydantic rejects it.

## Offline deterministic execution

The deterministic mock makes the run reproducible and needs no API key. Telemetry and runtime proxy use are disabled before CrewAI imports, so the graded workflow makes no network call. Setup still needs internet once to install packages and download the local embedding model.

Run after completing the setup from `TASK3-SEARCH.md`:

```powershell
python verify_portion4.py
python -m unittest test_crew_workflow.py
```

Expected summary: Portion 4 `PASS`, two `.kickoff()` calls, both tool names, two validated responses, and rejection of the invalid response. The complete real run is saved in `transcripts/portion4_evidence.json`.

