"""Create real execution evidence for governance, budget, and response caching."""

import json
import socket
from contextlib import ExitStack
from pathlib import Path
from unittest.mock import patch

from crew_workflow import SupportCrewWorkflow
from grounded_answers import DeterministicGroundedModel, GroundedAnswerEngine
from governance import (
    GOVERNANCE_SUMMARY,
    RISK_CLASSIFICATION,
    LeastAutonomyPolicy,
    RuntimeBudget,
    ToolAccessDeniedError,
)
from rag_index import PolicyIndex
from response_cache import GroundedResponseCache, normalize_query
from session_service import SafeSessionSupportService


class CountingIndex:
    def __init__(self):
        self.index = PolicyIndex()
        self.call_count = 0

    def query(self, question, strategy, top_k):
        self.call_count += 1
        return self.index.query(question, strategy, top_k)


def blocked_network(*args, **kwargs):
    raise RuntimeError("Network access attempted during offline Portion 8 verification")


def run_verification():
    workflow = SupportCrewWorkflow()
    agents = workflow._agents("ticket", "SUP-0001")
    actual_access = {
        agent.role: sorted(tool.name for tool in agent.tools)
        for agent in agents
    }
    try:
        LeastAutonomyPolicy.validate(
            "Policy Retrieval Specialist", ["check_support_ticket_status"]
        )
    except ToolAccessDeniedError as error:
        denied_attempt = {"blocked": True, "reason": str(error)}
    else:
        raise AssertionError("Forbidden ticket-tool assignment was not blocked")

    service = SafeSessionSupportService(runtime_budget=RuntimeBudget())
    before_kickoffs = service.workflow.kickoff_count
    oversized = service.handle("oversized-test", "word " * 300)
    if oversized.status != "budget_rejected" or oversized.crew_invoked:
        raise AssertionError("Oversized request was not rejected before CrewAI")
    if service.workflow.kickoff_count != before_kickoffs:
        raise AssertionError("Rejected request still invoked CrewAI")

    index = CountingIndex()
    model = DeterministicGroundedModel()
    cache = GroundedResponseCache()
    engine = GroundedAnswerEngine(
        index=index,
        model=model,
        cache=cache,
        cache_namespace="portion8-real-kb-v1",
    )
    question1 = "Is routine support open Sunday?"
    question2 = "  IS routine   support open Sunday?  "
    with ExitStack() as stack:
        stack.enter_context(patch.object(socket.socket, "connect", blocked_network))
        stack.enter_context(patch.object(socket.socket, "connect_ex", blocked_network))
        stack.enter_context(patch.object(socket, "create_connection", blocked_network))
        stack.enter_context(patch.object(socket, "getaddrinfo", blocked_network))
        first = engine.answer(question1)
        after_first = {
            "retrieval_calls": index.call_count,
            "generation_calls": model.call_count,
            "cache": cache.stats(),
        }
        second = engine.answer(question2)
        after_second = {
            "retrieval_calls": index.call_count,
            "generation_calls": model.call_count,
            "cache": cache.stats(),
        }

    if first["cache_hit"] or not second["cache_hit"]:
        raise AssertionError("Expected miss followed by hit")
    if index.call_count != 1 or model.call_count != 1:
        raise AssertionError("Cache did not prevent redundant retrieval/generation")

    return {
        "portion": 8,
        "rubric_tasks": [15, 16],
        "status": "PASS",
        "governance": {
            "layers": GOVERNANCE_SUMMARY,
            "risk": RISK_CLASSIFICATION,
            "actual_agent_tool_access": actual_access,
            "forbidden_assignment_attempt": denied_attempt,
        },
        "runtime_budget": {
            "request_status": oversized.status,
            "crew_invoked": oversized.crew_invoked,
            "crew_kickoffs_before": before_kickoffs,
            "crew_kickoffs_after": service.workflow.kickoff_count,
            "decision": oversized.runtime_budget,
        },
        "cache": {
            "normalized_key_equal": normalize_query(question1) == normalize_query(question2),
            "first_result": first,
            "second_result": second,
            "after_first": after_first,
            "after_second": after_second,
            "redundant_retrieval_avoided": True,
            "redundant_generation_avoided": True,
            "ticket_or_session_data_cached": False,
            "invalidation": "Namespace includes knowledge/config version in normal application use.",
        },
        "network_check": "Python socket connection and DNS calls blocked during the cache demonstration",
    }


if __name__ == "__main__":
    report = run_verification()
    destination = Path(__file__).resolve().parent / "transcripts" / "portion8_evidence.json"
    destination.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "portion": report["portion"],
        "status": report["status"],
        "risk": report["governance"]["risk"]["level"],
        "forbidden_tool_assignment_blocked": report["governance"]["forbidden_assignment_attempt"]["blocked"],
        "oversized_request": report["runtime_budget"]["request_status"],
        "crew_invoked_for_oversized_request": report["runtime_budget"]["crew_invoked"],
        "cache_first_hit": report["cache"]["first_result"]["cache_hit"],
        "cache_second_hit": report["cache"]["second_result"]["cache_hit"],
        "generation_calls_after_repeat": report["cache"]["after_second"]["generation_calls"],
        "evidence": str(destination.relative_to(destination.parent.parent)),
    }, indent=2))
