"""Run and save real CrewAI execution evidence for Tasks 7 and 9."""

import json
from pathlib import Path
import socket
from contextlib import ExitStack
from unittest.mock import patch

from pydantic import ValidationError

from crew_workflow import SupportCrewWorkflow, SupportResponse, execution_trace
from crewai import Crew


def blocked_network(*args, **kwargs):
    raise RuntimeError("Network access attempted during the offline Portion 4 check")


def run_verification():
    workflow = SupportCrewWorkflow()
    workflow.clear_tool_trace()

    policy_question = "How quickly must a P2 ticket be acknowledged?"
    ticket_request = "SUP-0001"
    with ExitStack() as stack:
        stack.enter_context(patch.object(socket.socket, "connect", blocked_network))
        stack.enter_context(patch.object(socket.socket, "connect_ex", blocked_network))
        stack.enter_context(patch.object(socket, "create_connection", blocked_network))
        stack.enter_context(patch.object(socket, "getaddrinfo", blocked_network))
        policy_response = workflow.run_policy(policy_question)
        ticket_response = workflow.run_ticket(ticket_request)
    trace = execution_trace()

    if workflow.kickoff_count != 2:
        raise AssertionError("Expected two real Crew.kickoff() executions")
    expected_tools = {"search_support_policies", "check_support_ticket_status"}
    used_tools = {event["tool"] for event in trace}
    if used_tools != expected_tools or len(trace) != 2:
        raise AssertionError("Each required tool must run exactly once")
    if trace[0]["arguments"] == trace[1]["arguments"]:
        raise AssertionError("The two tools need suitable, different requests")
    if not isinstance(policy_response, SupportResponse) or not isinstance(ticket_response, SupportResponse):
        raise AssertionError("Every crew response must be Pydantic-validated")
    if policy_response.request_type != "policy" or policy_response.ticket is not None:
        raise AssertionError("Policy response shape is incorrect")
    if ticket_response.request_type != "ticket" or ticket_response.ticket is None:
        raise AssertionError("Ticket response shape is incorrect")

    invalid_schema_rejected = False
    try:
        SupportResponse.model_validate({"request_type": "policy", "answer": "missing fields"})
    except ValidationError:
        invalid_schema_rejected = True
    if not invalid_schema_rejected:
        raise AssertionError("Invalid response should fail Pydantic validation")

    return {
        "portion": 4,
        "rubric_tasks": [7, 9],
        "status": "PASS",
        "runtime": {
            "framework": "CrewAI",
            "crew_class": f"{Crew.__module__}.{Crew.__name__}",
            "kickoff_method_called": "Crew.kickoff()",
            "kickoff_count": workflow.kickoff_count,
            "llm_mode": "deterministic BaseLLM mock",
            "api_keys_required": False,
            "runtime_network_required": False,
            "network_check": "Python socket connection and DNS calls blocked during both kickoffs",
        },
        "agents": [
            {"role": "Policy Retrieval Specialist", "tool_access": ["search_support_policies"]},
            {"role": "Ticket Lookup Specialist", "tool_access": ["check_support_ticket_status"]},
            {"role": "Support Response Composer", "tool_access": []},
        ],
        "tool_invocations": trace,
        "validated_responses": [
            {
                "request": policy_question,
                "validation": "SupportResponse PASS",
                "response": policy_response.model_dump(),
            },
            {
                "request": ticket_request,
                "validation": "SupportResponse PASS",
                "response": ticket_response.model_dump(),
            },
        ],
        "invalid_schema_rejected": invalid_schema_rejected,
    }


if __name__ == "__main__":
    report = run_verification()
    destination = Path(__file__).resolve().parent / "transcripts" / "portion4_evidence.json"
    destination.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "portion": report["portion"],
        "status": report["status"],
        "kickoff_count": report["runtime"]["kickoff_count"],
        "tools_used": [event["tool"] for event in report["tool_invocations"]],
        "validated_responses": len(report["validated_responses"]),
        "invalid_schema_rejected": report["invalid_schema_rejected"],
        "evidence": str(destination.relative_to(destination.parent.parent)),
    }, indent=2))
