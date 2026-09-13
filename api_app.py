"""FastAPI access layer for the reviewed, safe support pipeline."""

from __future__ import annotations

import asyncio
import time
import uuid
from contextvars import ContextVar
from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import ValidationError
from guardrails import mask_fixed_format_pii
from ticket_lookup import TicketNotFoundError
from pydantic import BaseModel, ConfigDict, Field

from autogen_review import AutoGenAnswerReviewer, ReviewVerdict
from crew_workflow import PolicySearchTool, TicketLookupTool
from guardrails import validate_grounded_output
from request_logging import RequestJsonlLogger
from session_service import SafeSessionSupportService, SessionReply


class AskRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    session_id: str = Field(min_length=1, max_length=100)
    message: str = Field(min_length=1, max_length=4000)


class AskResponse(BaseModel):
    trace_id: str
    duration_ms: float = Field(ge=0)
    reply: SessionReply
    review: ReviewVerdict | None = None
    final_answer: str | None = None


class ResetResponse(BaseModel):
    trace_id: str
    session_id: str
    reset: bool
    duration_ms: float = Field(ge=0)


class HealthResponse(BaseModel):
    status: str


class WebSocketAskRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    message: str = Field(min_length=1, max_length=4000)


def _mask_counts(reply: SessionReply) -> dict:
    return {
        "phone": reply.phone_numbers_masked,
        "card_last4": reply.card_last4_masked,
        "pan": reply.pan_masked,
        "aadhaar": reply.aadhaar_masked,
        "bank_account": reply.bank_accounts_masked,
    }


def create_app(service=None, reviewer=None, log_path=None) -> FastAPI:
    """Create a testable app; dependency arguments are for local verification."""
    support_service = service or SafeSessionSupportService()
    answer_reviewer = reviewer or AutoGenAnswerReviewer()
    logger = RequestJsonlLogger(log_path or Path("transcripts") / "request_log.jsonl")
    app = FastAPI(title="Ola Capstone Support API", version="1.0.0")
    pipeline_lock = asyncio.Lock()
    pending_http_log = ContextVar('pending_http_log', default=None)

    def record(entry):
        pending = pending_http_log.get()
        if pending is None:
            logger.append(entry)  # Each WebSocket message is its own request.
        else:
            pending.append(entry)

    @app.middleware('http')
    async def log_every_http_request(request, call_next):
        started = time.perf_counter()
        pending = []
        token = pending_http_log.set(pending)
        try:
            try:
                response = await call_next(request)
            except Exception:
                response = JSONResponse(status_code=500, content={
                    'message': 'Request could not be processed.'})
            entry = pending[-1] if pending else {
                'trace_id': str(uuid.uuid4()), 'transport': 'http',
                'masked_request_text': '', 'outcome': 'http_response',
            }
            # Never log arbitrary URL paths, query strings, bodies or exception text.
            # Matched route templates contain placeholders, not actual session IDs.
            route = request.scope.get('route')
            entry['endpoint'] = getattr(route, 'path', 'unmatched')
            entry['status_code'] = response.status_code
            entry['duration_ms'] = round((time.perf_counter() - started) * 1000, 3)
            logger.append(entry)
            response.headers['X-Trace-ID'] = entry['trace_id']
            return response
        finally:
            pending_http_log.reset(token)

    @app.exception_handler(RequestValidationError)
    async def invalid_request(request, error):
        # Do not echo or log invalid bodies: they may contain unmasked identifiers.
        trace_id = str(uuid.uuid4())
        record({'trace_id': trace_id, 'transport': 'http',
                       'endpoint': '/ask', 'outcome': 'invalid_request',
                       'masked_request_text': '', 'duration_ms': 0.0})
        return JSONResponse(status_code=422, content={'trace_id': trace_id,
                             'message': 'Invalid request fields.'})

    async def safe_process(session_id, message, transport, endpoint):
        started = time.perf_counter()
        async with pipeline_lock:
            try:
                if not message.strip() or not session_id.strip():
                    raise ValueError('Empty input')
                return await process(session_id, message, transport, endpoint)
            except Exception as error:
                trace_id = str(uuid.uuid4())
                status = 404 if isinstance(error, TicketNotFoundError) else 400 if isinstance(error, ValueError) else 500
                safe_text = mask_fixed_format_pii(message).sanitized_text if message.strip() else ''
                record({'trace_id': trace_id, 'transport': transport,
                    'endpoint': endpoint, 'masked_request_text': safe_text,
                    'outcome': 'request_error', 'duration_ms': round((time.perf_counter() - started) * 1000, 3)})
                body = {'trace_id': trace_id, 'message': 'Ticket not found.' if status == 404 else 'Request could not be processed.'}
                return JSONResponse(status_code=status, content=body)

    async def process(session_id: str, message: str, transport: str, endpoint: str) -> AskResponse:
        started = time.perf_counter()
        trace_id = str(uuid.uuid4())
        reply = await asyncio.to_thread(support_service.handle, session_id, message)
        verdict = None
        cache_hit = False
        if reply.status == "answered" and reply.response is not None:
            evidence = (
                PolicySearchTool.trace[-1]["result"]
                if reply.response.request_type == "policy"
                else TicketLookupTool.trace[-1]["result"]
            )
            cache_hit = bool(evidence.get("cache_hit", False))
            review_run = await answer_reviewer.review_async(reply.response, evidence)
            verdict = review_run.verdict
            if verdict.final_answer != reply.response.answer:
                reviewed_response = reply.response.model_copy(update={"answer": verdict.final_answer})
                validate_grounded_output(reviewed_response, evidence)
                reply = reply.model_copy(update={
                    "response": reviewed_response,
                    "message": verdict.final_answer,
                })
        duration_ms = round((time.perf_counter() - started) * 1000, 3)
        record({
            "trace_id": trace_id,
            "transport": transport,
            "endpoint": endpoint,
            "session_id": mask_fixed_format_pii(session_id).sanitized_text,
            "masked_request_text": reply.sanitized_input,
            "pii_mask_counts": _mask_counts(reply),
            "outcome": reply.status,
            "crew_invoked": reply.crew_invoked,
            "autogen_reviewed": verdict is not None,
            "cache_hit": cache_hit,
            "runtime_budget": reply.runtime_budget,
            "duration_ms": duration_ms,
        })
        return AskResponse(
            trace_id=trace_id,
            duration_ms=duration_ms,
            reply=reply,
            review=verdict,
            final_answer=reply.message if reply.status == "answered" else None,
        )

    @app.get("/health", response_model=HealthResponse)
    async def health():
        started = time.perf_counter()
        record({
            "trace_id": str(uuid.uuid4()),
            "transport": "http",
            "endpoint": "/health",
            "session_id": None,
            "masked_request_text": "",
            "pii_mask_counts": {"phone": 0, "card_last4": 0, "pan": 0, "aadhaar": 0, "bank_account": 0},
            "outcome": "ok",
            "crew_invoked": False,
            "autogen_reviewed": False,
            "duration_ms": round((time.perf_counter() - started) * 1000, 3),
        })
        return HealthResponse(status="ok")

    @app.post("/ask", response_model=AskResponse)
    async def ask(payload: AskRequest):
        return await safe_process(payload.session_id, payload.message, "http", "/ask")

    @app.post("/sessions/{session_id}/reset", response_model=ResetResponse)
    async def reset_session(session_id: str):
        started = time.perf_counter()
        trace_id = str(uuid.uuid4())
        support_service.memory.reset(session_id)
        duration_ms = round((time.perf_counter() - started) * 1000, 3)
        record({
            "trace_id": trace_id,
            "transport": "http",
            "endpoint": "/sessions/{session_id}/reset",
            "session_id": mask_fixed_format_pii(session_id).sanitized_text,
            "masked_request_text": "",
            "pii_mask_counts": {"phone": 0, "card_last4": 0, "pan": 0, "aadhaar": 0, "bank_account": 0},
            "outcome": "reset",
            "crew_invoked": False,
            "autogen_reviewed": False,
            "duration_ms": duration_ms,
        })
        return ResetResponse(trace_id=trace_id, session_id=session_id, reset=True, duration_ms=duration_ms)

    @app.websocket("/ws/chat/{session_id}")
    async def chat(websocket: WebSocket, session_id: str):
        await websocket.accept()
        try:
            while True:
                try:
                    incoming = WebSocketAskRequest.model_validate(await websocket.receive_json())
                except (ValidationError, ValueError):
                    trace_id = str(uuid.uuid4())
                    record({'trace_id': trace_id, 'transport': 'websocket',
                                   'outcome': 'invalid_request', 'masked_request_text': '', 'duration_ms': 0.0})
                    await websocket.send_json({'trace_id': trace_id, 'message': 'Invalid request fields.'})
                    continue
                response = await safe_process(session_id, incoming.message, "websocket", "/ws/chat/{session_id}")
                if isinstance(response, JSONResponse):
                    import json
                    await websocket.send_json(json.loads(response.body))
                else:
                    await websocket.send_json(response.model_dump(mode="json"))
        except WebSocketDisconnect:
            # A client leaving is normal; the FastAPI server remains available.
            return

    return app


app = create_app()
