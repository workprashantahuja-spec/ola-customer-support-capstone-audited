"""Task 14: bounded two-agent AutoGen review after the CrewAI draft."""

from __future__ import annotations

import asyncio
import json
import os
from collections.abc import AsyncGenerator, Mapping, Sequence
from typing import Any

os.environ["OTEL_SDK_DISABLED"] = "true"

from autogen_agentchat.agents import AssistantAgent  # noqa: E402
from autogen_agentchat.messages import StructuredMessage  # noqa: E402
from autogen_agentchat.teams import RoundRobinGroupChat  # noqa: E402
from autogen_core import CancellationToken  # noqa: E402
from autogen_core.models import (  # noqa: E402
    ChatCompletionClient,
    CreateResult,
    LLMMessage,
    RequestUsage,
)
from autogen_core.tools import Tool, ToolSchema  # noqa: E402
from pydantic import BaseModel, ConfigDict, Field  # noqa: E402

from crew_workflow import SupportResponse  # noqa: E402
from rag_config import FALLBACK_MESSAGE  # noqa: E402


MAX_REVIEW_TURNS = 2


class ReviewVerdict(BaseModel):
    model_config = ConfigDict(extra="forbid")

    approved: bool
    final_answer: str = Field(min_length=1)
    reason: str = Field(min_length=1)


class ReviewPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    draft: SupportResponse
    evidence: dict[str, Any]


class AutoGenReviewRun(BaseModel):
    model_config = ConfigDict(extra="forbid")

    verdict: ReviewVerdict
    stop_reason: str
    max_turns: int
    agent_messages: list[dict[str, Any]]
    reviewer_model_calls: int
    editor_model_calls: int


def _canonical_ticket_answer(evidence: dict[str, Any]) -> str:
    attention = (
        " Human attention is recommended."
        if evidence["human_attention_recommended"]
        else " Human attention is not currently recommended by the fabricated-data score."
    )
    return (
        f"Ticket {evidence['record_id']} is {evidence['status']}. Its recorded resolution-time "
        f"value is {evidence['resolution_time_hours']} hours and its attention score is "
        f"{evidence['escalation_score']:.4f}.{attention}"
    )


def expected_answer(payload: ReviewPayload) -> str:
    if payload.draft.request_type == "policy":
        if payload.evidence.get("fallback"):
            return FALLBACK_MESSAGE
        if "retrieved_context" in payload.evidence:
            context = payload.evidence["retrieved_context"]
            _, separator, body = context.partition("\n")
            return body.strip() if separator else context.strip()
        return str(payload.evidence["answer"])
    return _canonical_ticket_answer(payload.evidence)


def draft_matches_evidence(payload: ReviewPayload) -> bool:
    draft = payload.draft
    evidence = payload.evidence
    if draft.answer != expected_answer(payload):
        return False
    if draft.request_type == "policy":
        fallback = bool(evidence.get("fallback"))
        return (
            draft.fallback_used == fallback
            and draft.grounded == (not fallback)
            and draft.sources == list(evidence.get("sources", []))
            and draft.ticket is None
        )
    ticket_fields = {
        key: evidence.get(key)
        for key in (
            "record_id", "status", "resolution_time_hours", "days_since_created",
            "escalated", "escalation_score", "human_attention_recommended",
        )
    }
    return (
        draft.ticket is not None
        and draft.ticket.model_dump() == ticket_fields
        and draft.grounded
        and not draft.fallback_used
        and draft.sources == ["fabricated_support_tickets"]
    )


def _payload_from_messages(messages: Sequence[LLMMessage]) -> ReviewPayload:
    for message in messages:
        content = getattr(message, "content", None)
        if not isinstance(content, str):
            continue
        try:
            candidate = json.loads(content)
        except json.JSONDecodeError:
            continue
        if isinstance(candidate, dict) and {"draft", "evidence"} <= candidate.keys():
            return ReviewPayload.model_validate(candidate)
    raise ValueError("AutoGen messages did not contain the review payload")


class DeterministicAutoGenClient(ChatCompletionClient):
    """Offline model client used by one named review role."""

    def __init__(self, role: str):
        self.role = role
        self.call_count = 0
        self._usage = RequestUsage(prompt_tokens=0, completion_tokens=0)

    async def create(
        self,
        messages: Sequence[LLMMessage],
        *,
        tools: Sequence[Tool | ToolSchema] = [],
        tool_choice="auto",
        json_output: bool | type[BaseModel] | None = None,
        extra_create_args: Mapping[str, Any] = {},
        cancellation_token: CancellationToken | None = None,
    ) -> CreateResult:
        self.call_count += 1
        payload = _payload_from_messages(messages)
        matches = draft_matches_evidence(payload)
        if self.role == "evidence_reviewer":
            content = (
                "APPROVE: The CrewAI draft matches the original tool evidence."
                if matches
                else "REVISE: The CrewAI draft differs from the original tool evidence; use the evidence-backed answer."
            )
        else:
            verdict = ReviewVerdict(
                approved=matches,
                final_answer=payload.draft.answer if matches else expected_answer(payload),
                reason=(
                    "Draft matches the original tool evidence; no revision was needed."
                    if matches
                    else "Draft differed from the original tool evidence and was replaced with the evidence-backed answer."
                ),
            )
            content = verdict.model_dump_json()

        prompt_tokens = sum(len(str(getattr(message, "content", "")).split()) for message in messages)
        completion_tokens = len(content.split())
        usage = RequestUsage(prompt_tokens=prompt_tokens, completion_tokens=completion_tokens)
        self._usage = RequestUsage(
            prompt_tokens=self._usage.prompt_tokens + prompt_tokens,
            completion_tokens=self._usage.completion_tokens + completion_tokens,
        )
        return CreateResult(finish_reason="stop", content=content, usage=usage, cached=False)

    async def create_stream(self, messages, **kwargs) -> AsyncGenerator[str | CreateResult, None]:
        yield await self.create(messages, **kwargs)

    async def close(self) -> None:
        return None

    def actual_usage(self) -> RequestUsage:
        return self._usage

    def total_usage(self) -> RequestUsage:
        return self._usage

    def count_tokens(self, messages, *, tools=[]) -> int:
        return sum(len(str(getattr(message, "content", "")).split()) for message in messages)

    def remaining_tokens(self, messages, *, tools=[]) -> int:
        return max(0, 4096 - self.count_tokens(messages, tools=tools))

    @property
    def capabilities(self):
        return {"vision": False, "function_calling": False, "json_output": True}

    @property
    def model_info(self):
        return {
            "vision": False,
            "function_calling": False,
            "json_output": True,
            "family": "unknown",
            "structured_output": True,
        }


def _message_record(message) -> dict[str, Any]:
    content = message.content
    if isinstance(content, BaseModel):
        content = content.model_dump(mode="json")
    return {
        "source": message.source,
        "message_type": type(message).__name__,
        "content": content,
    }


class AutoGenAnswerReviewer:
    async def review_async(self, draft: SupportResponse, evidence: dict[str, Any]) -> AutoGenReviewRun:
        payload = ReviewPayload(draft=draft, evidence=evidence)
        reviewer_client = DeterministicAutoGenClient("evidence_reviewer")
        editor_client = DeterministicAutoGenClient("final_editor")

        evidence_reviewer = AssistantAgent(
            "evidence_reviewer",
            reviewer_client,
            description="Checks the CrewAI draft against the original tool evidence.",
            system_message=(
                "Compare the CrewAI Composer draft with the original retrieved or lookup evidence. "
                "State APPROVE only when every material claim matches; otherwise state REVISE."
            ),
        )
        final_editor = AssistantAgent(
            "final_editor",
            editor_client,
            description="Returns the final typed approval or revision verdict.",
            system_message=(
                "Use the original evidence and the review. Preserve an approved answer unchanged; "
                "replace an unsupported answer with the evidence-backed answer."
            ),
            output_content_type=ReviewVerdict,
        )
        team = RoundRobinGroupChat(
            [evidence_reviewer, final_editor],
            max_turns=MAX_REVIEW_TURNS,
            custom_message_types=[StructuredMessage[ReviewVerdict]],
        )
        result = await team.run(task=payload.model_dump_json())
        final_message = result.messages[-1]
        verdict = ReviewVerdict.model_validate(final_message.content)
        records = [_message_record(message) for message in result.messages if message.source != "user"]
        await reviewer_client.close()
        await editor_client.close()
        return AutoGenReviewRun(
            verdict=verdict,
            stop_reason=str(result.stop_reason),
            max_turns=MAX_REVIEW_TURNS,
            agent_messages=records,
            reviewer_model_calls=reviewer_client.call_count,
            editor_model_calls=editor_client.call_count,
        )

    def review(self, draft: SupportResponse, evidence: dict[str, Any]) -> AutoGenReviewRun:
        return asyncio.run(self.review_async(draft, evidence))
