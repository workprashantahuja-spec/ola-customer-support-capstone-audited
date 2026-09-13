"""Generate real Task 14 CrewAI-to-AutoGen execution evidence."""

import json
import socket
from contextlib import ExitStack
from pathlib import Path
from unittest.mock import patch

from autogen_review import AutoGenAnswerReviewer, ReviewVerdict
from crew_workflow import PolicySearchTool, SupportCrewWorkflow


def blocked_network(*args, **kwargs):
    raise RuntimeError("Network access attempted during the offline Portion 6 check")


def run_verification():
    workflow = SupportCrewWorkflow()
    workflow.clear_tool_trace()
    reviewer = AutoGenAnswerReviewer()
    question = "How quickly must a P2 ticket be acknowledged?"

    with ExitStack() as stack:
        stack.enter_context(patch.object(socket.socket, "connect", blocked_network))
        stack.enter_context(patch.object(socket.socket, "connect_ex", blocked_network))
        stack.enter_context(patch.object(socket, "create_connection", blocked_network))
        stack.enter_context(patch.object(socket, "getaddrinfo", blocked_network))

        crew_draft = workflow.run_policy(question)
        original_evidence = PolicySearchTool.trace[-1]["result"]
        approval = reviewer.review(crew_draft, original_evidence)

        incorrect_draft = crew_draft.model_copy(update={
            "answer": "A P2 ticket can wait 24 business hours for acknowledgement."
        })
        revision = reviewer.review(incorrect_draft, original_evidence)

    if not approval.verdict.approved:
        raise AssertionError("Correct CrewAI draft should be approved")
    if approval.verdict.final_answer != crew_draft.answer:
        raise AssertionError("Approval path changed a supported answer")
    if revision.verdict.approved:
        raise AssertionError("Unsupported draft should not be approved")
    if revision.verdict.final_answer == incorrect_draft.answer:
        raise AssertionError("Revision path did not change the unsupported claim")
    if revision.verdict.final_answer != original_evidence["answer"]:
        raise AssertionError("Revision did not restore the evidence-backed answer")
    if not isinstance(approval.verdict, ReviewVerdict) or not isinstance(revision.verdict, ReviewVerdict):
        raise AssertionError("Every final editor output must validate as ReviewVerdict")

    return {
        "portion": 6,
        "rubric_task": 14,
        "status": "PASS",
        "pipeline_order": ["CrewAI Composer draft", "AutoGen Evidence Reviewer", "AutoGen Final Editor"],
        "autogen_configuration": {
            "team": "RoundRobinGroupChat",
            "agents": ["evidence_reviewer", "final_editor"],
            "max_turns": approval.max_turns,
            "final_editor_output_content_type": "ReviewVerdict",
            "registered_custom_message_type": "StructuredMessage[ReviewVerdict]",
            "api_keys_required": False,
            "runtime_network_required": False,
            "network_check": "Python socket connection and DNS calls blocked during CrewAI and both AutoGen runs",
        },
        "original_input": {
            "question": question,
            "crew_draft": crew_draft.model_dump(mode="json"),
            "retrieved_context": original_evidence,
        },
        "unchanged_approval": {
            "input_answer": crew_draft.answer,
            "run": approval.model_dump(mode="json"),
            "answer_unchanged": approval.verdict.final_answer == crew_draft.answer,
        },
        "genuine_revision": {
            "input_answer": incorrect_draft.answer,
            "run": revision.model_dump(mode="json"),
            "answer_changed": revision.verdict.final_answer != incorrect_draft.answer,
            "corrected_to_evidence": revision.verdict.final_answer == original_evidence["answer"],
        },
    }


if __name__ == "__main__":
    report = run_verification()
    destination = Path(__file__).resolve().parent / "transcripts" / "portion6_evidence.json"
    destination.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "portion": report["portion"],
        "status": report["status"],
        "team": report["autogen_configuration"]["team"],
        "max_turns": report["autogen_configuration"]["max_turns"],
        "approved_unchanged": report["unchanged_approval"]["answer_unchanged"],
        "incorrect_answer_revised": report["genuine_revision"]["answer_changed"],
        "revision_matches_evidence": report["genuine_revision"]["corrected_to_evidence"],
        "evidence": str(destination.relative_to(destination.parent.parent)),
    }, indent=2))

