# Tasks 11 and 12 — FastAPI, WebSocket, and masked request logs

## What this portion adds

`api_app.py` puts the completed support pipeline behind FastAPI. Every successful answer follows this order:

1. Input guardrails and session memory.
2. CrewAI retrieval or ticket lookup.
3. Output groundedness check.
4. AutoGen evidence review.
5. Pydantic response sent to the client.

## Endpoints

| Route | Purpose |
| --- | --- |
| `GET /health` | Confirms that the service is available. |
| `POST /ask` | Receives a Pydantic `AskRequest` and returns a typed answer, trace ID, timing, and AutoGen verdict. |
| `POST /sessions/{session_id}/reset` | Clears only that session's LangChain memory. |
| `WebSocket /ws/chat/{session_id}` | Supports multi-turn chat with the same session memory. |

The WebSocket catches `WebSocketDisconnect`. A customer closing their connection does not stop the server; another request can immediately use `/health` or open a new chat.

## Request logging

`request_logging.py` writes one JSON object per processed HTTP request or WebSocket chat message to a JSON-Lines file. Each record has a UUID trace ID, UTC timestamp, endpoint, timing in milliseconds, outcome, and only the sanitized request text.

The same input guardrail runs before CrewAI, memory, AutoGen, and logging. Supported phone, card-last-4, PAN, Aadhaar, and labelled bank-account formats are masked before the log writer sees them. Names, addresses, and arbitrary free text are not claimed as reliably detectable.

## Demonstration

Run:

```powershell
python verify_portion7.py
python -m unittest test_api_app.py
```

The verifier makes real HTTP and WebSocket calls through FastAPI's test client. It proves that the WebSocket retains ticket context, disconnects safely, and leaves the server available. It also checks the JSONL file has one record for each processed request and contains none of the fabricated raw phone, PAN, Aadhaar, or bank-account values.
