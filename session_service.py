"""Session-aware support service backed by LangChain chat history."""

from __future__ import annotations

import re
from typing import Literal

from langchain_core.chat_history import InMemoryChatMessageHistory
from pydantic import BaseModel, ConfigDict, Field

from crew_workflow import (
    PolicySearchTool,
    SupportCrewWorkflow,
    SupportResponse,
    TicketLookupTool,
)
from guardrails import PromptInjectionError, inspect_input, validate_grounded_output
from governance import RuntimeBudget, RuntimeBudgetExceededError


TICKET_ID_PATTERN = re.compile(r"\bSUP-\d{4}\b", re.IGNORECASE)
TICKET_FOLLOWUP_PATTERN = re.compile(
    r"(?i)\b(?:it|its|that\s+ticket|the\s+ticket)\b.*\b(?:status|resolution|score|attention)\b|"
    r"\b(?:status|resolution|score|attention)\b.*\b(?:it|its|that\s+ticket|the\s+ticket)\b"
)


class SessionReply(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: Literal["answered", "needs_context", "blocked", "budget_rejected"]
    session_id: str = Field(min_length=1)
    sanitized_input: str
    phone_numbers_masked: int = Field(ge=0)
    card_last4_masked: int = Field(ge=0)
    pan_masked: int = Field(ge=0)
    aadhaar_masked: int = Field(ge=0)
    bank_accounts_masked: int = Field(ge=0)
    memory_used: bool
    resolved_record_id: str | None
    crew_invoked: bool
    response: SupportResponse | None
    message: str
    guardrail_events: list[str]
    runtime_budget: dict | None = None


class SessionMemoryStore:
    """Keep an independent LangChain history for each session ID."""

    def __init__(self):
        self._sessions: dict[str, InMemoryChatMessageHistory] = {}

    def get(self, session_id: str) -> InMemoryChatMessageHistory:
        if not isinstance(session_id, str) or not session_id.strip():
            raise ValueError("session_id must be a nonempty string")
        key = session_id.strip()
        return self._sessions.setdefault(key, InMemoryChatMessageHistory())

    def reset(self, session_id: str):
        self._sessions.pop(session_id.strip(), None)

    def snapshot(self, session_id: str) -> list[dict]:
        return [
            {"role": message.type, "content": str(message.content)}
            for message in self.get(session_id).messages
        ]


class SafeSessionSupportService:
    def __init__(self, workflow=None, memory=None, runtime_budget=None):
        self.workflow = workflow or SupportCrewWorkflow()
        self.memory = memory or SessionMemoryStore()
        self.runtime_budget = runtime_budget or RuntimeBudget()

    @staticmethod
    def _ticket_from_history(history: InMemoryChatMessageHistory) -> str | None:
        for message in reversed(history.messages):
            match = TICKET_ID_PATTERN.search(str(message.content))
            if match:
                return match.group(0).upper()
        return None

    def handle(self, session_id: str, text: str) -> SessionReply:
        history = self.memory.get(session_id)
        try:
            safe = inspect_input(text)
        except PromptInjectionError as error:
            return SessionReply(
                status="blocked",
                session_id=session_id,
                sanitized_input=error.sanitized_text,
                phone_numbers_masked=error.phone_numbers_masked,
                card_last4_masked=error.card_last4_masked,
                pan_masked=error.pan_masked,
                aadhaar_masked=error.aadhaar_masked,
                bank_accounts_masked=error.bank_accounts_masked,
                memory_used=False,
                resolved_record_id=None,
                crew_invoked=False,
                response=None,
                message="Request blocked because it tried to override the assistant's instructions.",
                guardrail_events=[f"prompt_injection:{error.rule}"],
                runtime_budget=None,
            )

        sanitized = safe.sanitized_text
        try:
            budget = self.runtime_budget.enforce(sanitized)
        except RuntimeBudgetExceededError as error:
            return SessionReply(
                status="budget_rejected",
                session_id=session_id,
                sanitized_input=sanitized,
                phone_numbers_masked=safe.phone_numbers_masked,
                card_last4_masked=safe.card_last4_masked,
                pan_masked=safe.pan_masked,
                aadhaar_masked=safe.aadhaar_masked,
                bank_accounts_masked=safe.bank_accounts_masked,
                memory_used=False,
                resolved_record_id=None,
                crew_invoked=False,
                response=None,
                message="Request rejected because it exceeds the per-request runtime budget.",
                guardrail_events=["runtime_budget:rejected"],
                runtime_budget=error.decision.to_dict(),
            )
        direct_match = TICKET_ID_PATTERN.search(sanitized)
        record_id = direct_match.group(0).upper() if direct_match else None
        memory_used = False
        if record_id is None and TICKET_FOLLOWUP_PATTERN.search(sanitized):
            record_id = self._ticket_from_history(history)
            memory_used = record_id is not None
            if record_id is None:
                message = "Please provide the ticket ID in the format SUP-0000."
                history.add_user_message(sanitized)
                history.add_ai_message(message)
                return SessionReply(
                    status="needs_context",
                    session_id=session_id,
                    sanitized_input=sanitized,
                    phone_numbers_masked=safe.phone_numbers_masked,
                    card_last4_masked=safe.card_last4_masked,
                    pan_masked=safe.pan_masked,
                    aadhaar_masked=safe.aadhaar_masked,
                    bank_accounts_masked=safe.bank_accounts_masked,
                    memory_used=False,
                    resolved_record_id=None,
                    crew_invoked=False,
                    response=None,
                    message=message,
                    guardrail_events=["fresh_session:no_ticket_context"],
                    runtime_budget=budget.to_dict(),
                )

        if record_id:
            response = self.workflow.run_ticket(record_id)
            evidence = TicketLookupTool.trace[-1]["result"]
        else:
            response = self.workflow.run_policy(sanitized)
            evidence = PolicySearchTool.trace[-1]["result"]
        response = validate_grounded_output(response, evidence)

        history.add_user_message(sanitized)
        history.add_ai_message(response.model_dump_json())
        events = []
        if safe.phone_numbers_masked:
            events.append("pii_masked:phone")
        if safe.card_last4_masked:
            events.append("pii_masked:card_last4")
        if safe.pan_masked:
            events.append("pii_masked:pan")
        if safe.aadhaar_masked:
            events.append("pii_masked:aadhaar")
        if safe.bank_accounts_masked:
            events.append("pii_masked:bank_account")
        events.append("runtime_budget:accepted")
        events.append("output_groundedness:pass")
        return SessionReply(
            status="answered",
            session_id=session_id,
            sanitized_input=sanitized,
            phone_numbers_masked=safe.phone_numbers_masked,
            card_last4_masked=safe.card_last4_masked,
            pan_masked=safe.pan_masked,
            aadhaar_masked=safe.aadhaar_masked,
            bank_accounts_masked=safe.bank_accounts_masked,
            memory_used=memory_used,
            resolved_record_id=record_id,
            crew_invoked=True,
            response=response,
            message=response.answer,
            guardrail_events=events,
            runtime_budget=budget.to_dict(),
        )
