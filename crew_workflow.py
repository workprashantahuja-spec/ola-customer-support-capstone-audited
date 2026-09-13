"""Portion 4: real CrewAI orchestration with deterministic offline LLMs.

The CrewAI runtime and its ``Crew.kickoff()`` method are real. Only the language
model is replaced with a deterministic BaseLLM implementation, as required for
repeatable grading without API keys or runtime network access.
"""

from __future__ import annotations

import json
import os
from typing import ClassVar, Literal


def _configure_offline_runtime():
    """Disable telemetry and network proxy use before CrewAI is imported."""
    os.environ["CREWAI_DISABLE_TELEMETRY"] = "true"
    os.environ["OTEL_SDK_DISABLED"] = "true"
    for variable in (
        "HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY",
        "http_proxy", "https_proxy", "all_proxy",
    ):
        os.environ.pop(variable, None)


_configure_offline_runtime()

from crewai import Agent, Crew, Process, Task  # noqa: E402
from crewai.llms.base_llm import BaseLLM  # noqa: E402
from crewai.tools import BaseTool  # noqa: E402
from pydantic import BaseModel, ConfigDict, Field  # noqa: E402

from grounded_answers import GroundedAnswerEngine  # noqa: E402
from governance import LeastAutonomyPolicy  # noqa: E402
from ticket_lookup import TicketNotFoundError, check_support_ticket_status  # noqa: E402


class PolicySearchInput(BaseModel):
    question: str = Field(min_length=3, description="Customer policy question")


class TicketLookupInput(BaseModel):
    record_id: str = Field(pattern=r"^SUP-\d{4}$", description="Fabricated ticket ID")


class TicketDetails(BaseModel):
    model_config = ConfigDict(extra="forbid")

    record_id: str
    status: str
    resolution_time_hours: int = Field(ge=1, le=72)
    days_since_created: int = Field(ge=0, le=30)
    escalated: bool
    escalation_score: float = Field(ge=0.0, le=1.0)
    human_attention_recommended: bool


class SupportResponse(BaseModel):
    """Schema validated for every final CrewAI response."""

    model_config = ConfigDict(extra="forbid")

    request_type: Literal["policy", "ticket"]
    answer: str = Field(min_length=1)
    grounded: bool
    fallback_used: bool
    sources: list[str]
    ticket: TicketDetails | None = None


class PolicySearchTool(BaseTool):
    name: str = "search_support_policies"
    description: str = "Search the local fictional support-policy knowledge base."
    args_schema: type[BaseModel] = PolicySearchInput
    trace: ClassVar[list[dict]] = []
    _answer_engine: ClassVar[GroundedAnswerEngine | None] = None

    @classmethod
    def answer_engine(cls) -> GroundedAnswerEngine:
        if cls._answer_engine is None:
            cls._answer_engine = GroundedAnswerEngine()
        return cls._answer_engine

    @classmethod
    def reset_answer_engine(cls) -> None:
        cls._answer_engine = None

    def _run(self, question: str) -> str:
        result = self.answer_engine().answer(question)
        self.trace.append({
            "tool": self.name,
            "arguments": {"question": question},
            "result": result,
        })
        return json.dumps(result, sort_keys=True)


class TicketLookupTool(BaseTool):
    name: str = "check_support_ticket_status"
    description: str = "Look up one fabricated support ticket by its SUP-#### record ID."
    args_schema: type[BaseModel] = TicketLookupInput
    trace: ClassVar[list[dict]] = []

    def _run(self, record_id: str) -> str:
        try:
            result = check_support_ticket_status(record_id)
        except TicketNotFoundError as error:
            result = {"record_id": record_id, "error": str(error)}
        self.trace.append({
            "tool": self.name,
            "arguments": {"record_id": record_id},
            "result": result,
        })
        return json.dumps(result, sort_keys=True)


def _message_text(messages) -> str:
    if isinstance(messages, str):
        return messages
    return "\n".join(str(message.get("content", "")) for message in messages)


def _latest_observation(messages) -> str | None:
    """Read only an executed action's last observation, not prompt examples."""
    if not isinstance(messages, list) or not messages:
        return None
    latest = str(messages[-1].get("content", ""))
    marker = "\nObservation: "
    if not latest.startswith("Thought:") or marker not in latest:
        return None
    return latest.rsplit(marker, 1)[1].strip()


def _find_context_payload(text: str, required_key: str) -> dict:
    decoder = json.JSONDecoder()
    candidates = []
    for position, character in enumerate(text):
        if character != "{":
            continue
        try:
            value, _ = decoder.raw_decode(text[position:])
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict) and required_key in value:
            candidates.append(value)
    if not candidates:
        raise ValueError(f"Crew context did not contain {required_key!r}")
    return candidates[-1]


class DeterministicWorkerLLM(BaseLLM):
    """CrewAI-compatible mock that calls one declared tool, then returns its output."""

    def __init__(self, tool_name: str, tool_arguments: dict):
        super().__init__(model=f"deterministic-{tool_name}", temperature=0.0)
        self.tool_name = tool_name
        self.tool_arguments = tool_arguments
        self.call_count = 0

    def call(self, messages, tools=None, callbacks=None, available_functions=None):
        self.call_count += 1
        observation = _latest_observation(messages)
        if observation is not None:
            return f"Thought: I used the declared tool and have its result.\nFinal Answer: {observation}"
        return (
            "Thought: I must use my assigned tool for grounded data.\n"
            f"Action: {self.tool_name}\n"
            f"Action Input: {json.dumps(self.tool_arguments, sort_keys=True)}"
        )

    def supports_function_calling(self) -> bool:
        return False


class DeterministicComposerLLM(BaseLLM):
    """Convert a worker's actual JSON result into the final response schema."""

    def __init__(self, request_type: Literal["policy", "ticket"]):
        super().__init__(model=f"deterministic-composer-{request_type}", temperature=0.0)
        self.request_type = request_type
        self.call_count = 0

    def call(self, messages, tools=None, callbacks=None, available_functions=None):
        self.call_count += 1
        text = _message_text(messages)
        if self.request_type == "policy":
            source = _find_context_payload(text, "fallback")
            response = SupportResponse(
                request_type="policy",
                answer=source["answer"],
                grounded=bool(source["grounded"]),
                fallback_used=bool(source["fallback"]),
                sources=list(source["sources"]),
                ticket=None,
            )
        else:
            source = _find_context_payload(text, "record_id")
            if "error" in source:
                raise TicketNotFoundError(source["error"])
            ticket = TicketDetails.model_validate({
                key: source[key]
                for key in TicketDetails.model_fields
            })
            attention = (
                " Human attention is recommended."
                if ticket.human_attention_recommended
                else " Human attention is not currently recommended by the fabricated-data score."
            )
            response = SupportResponse(
                request_type="ticket",
                answer=(
                    f"Ticket {ticket.record_id} is {ticket.status}. Its recorded resolution-time "
                    f"value is {ticket.resolution_time_hours} hours and its attention score is "
                    f"{ticket.escalation_score:.4f}.{attention}"
                ),
                grounded=True,
                fallback_used=False,
                sources=["fabricated_support_tickets"],
                ticket=ticket,
            )
        return response.model_dump_json()

    def supports_function_calling(self) -> bool:
        return False


class SupportCrewWorkflow:
    """Create all three required agents and execute route-specific CrewAI tasks."""

    def __init__(self):
        self.kickoff_count = 0
        self.last_crew: Crew | None = None

    @staticmethod
    def clear_tool_trace():
        PolicySearchTool.trace.clear()
        TicketLookupTool.trace.clear()

    def _agents(self, request_type, value):
        if request_type == "policy":
            retrieval_llm = DeterministicWorkerLLM(
                "search_support_policies", {"question": value}
            )
            lookup_llm = DeterministicWorkerLLM(
                "check_support_ticket_status", {"record_id": "SUP-0001"}
            )
        else:
            retrieval_llm = DeterministicWorkerLLM(
                "search_support_policies", {"question": "unused route"}
            )
            lookup_llm = DeterministicWorkerLLM(
                "check_support_ticket_status", {"record_id": value}
            )

        retrieval = Agent(
            role="Policy Retrieval Specialist",
            goal="Use local policy retrieval and report only its grounded result.",
            backstory="You retrieve fictional support policies without inventing facts.",
            llm=retrieval_llm,
            tools=[PolicySearchTool()],
            allow_delegation=False,
            max_iter=3,
            verbose=False,
        )
        lookup = Agent(
            role="Ticket Lookup Specialist",
            goal="Use the ticket tool and report the fabricated record accurately.",
            backstory="You alone may access the fabricated ticket lookup tool.",
            llm=lookup_llm,
            tools=[TicketLookupTool()],
            allow_delegation=False,
            max_iter=3,
            verbose=False,
        )
        composer = Agent(
            role="Support Response Composer",
            goal="Turn tool-grounded context into the required structured response.",
            backstory="You preserve the supplied facts and never call data tools.",
            llm=DeterministicComposerLLM(request_type),
            tools=[],
            allow_delegation=False,
            max_iter=2,
            verbose=False,
        )
        for agent in (retrieval, lookup, composer):
            LeastAutonomyPolicy.validate(agent.role, [tool.name for tool in agent.tools])
        return retrieval, lookup, composer

    def run_policy(self, question: str) -> SupportResponse:
        retrieval, lookup, composer = self._agents("policy", question)
        retrieve_task = Task(
            description=f"Use the policy-search tool to answer this question: {question}",
            expected_output="The exact JSON returned by the policy-search tool.",
            agent=retrieval,
            tools=[PolicySearchTool()],
        )
        compose_task = Task(
            description="Create the final structured support response from the retrieval result.",
            expected_output="One JSON object matching the SupportResponse schema.",
            agent=composer,
            context=[retrieve_task],
            output_pydantic=SupportResponse,
        )
        crew = Crew(
            agents=[retrieval, lookup, composer],
            tasks=[retrieve_task, compose_task],
            process=Process.sequential,
            memory=False,
            cache=False,
            verbose=False,
            share_crew=False,
        )
        self.last_crew = crew
        output = crew.kickoff()
        self.kickoff_count += 1
        if output.pydantic is None:
            raise TypeError("CrewAI did not produce the required Pydantic response")
        return SupportResponse.model_validate(output.pydantic)

    def run_ticket(self, record_id: str) -> SupportResponse:
        retrieval, lookup, composer = self._agents("ticket", record_id)
        lookup_task = Task(
            description=f"Use the ticket-status tool to look up this record: {record_id}",
            expected_output="The exact JSON returned by the ticket-status tool.",
            agent=lookup,
            tools=[TicketLookupTool()],
        )
        compose_task = Task(
            description="Create the final structured support response from the ticket result.",
            expected_output="One JSON object matching the SupportResponse schema.",
            agent=composer,
            context=[lookup_task],
            output_pydantic=SupportResponse,
        )
        crew = Crew(
            agents=[retrieval, lookup, composer],
            tasks=[lookup_task, compose_task],
            process=Process.sequential,
            memory=False,
            cache=False,
            verbose=False,
            share_crew=False,
        )
        self.last_crew = crew
        output = crew.kickoff()
        self.kickoff_count += 1
        if output.pydantic is None:
            raise TypeError("CrewAI did not produce the required Pydantic response")
        return SupportResponse.model_validate(output.pydantic)


def execution_trace() -> list[dict]:
    return [*PolicySearchTool.trace, *TicketLookupTool.trace]
