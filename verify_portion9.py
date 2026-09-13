"""Run the required 15-query evaluation through the complete API pipeline."""

from __future__ import annotations

import json
import socket
from contextlib import ExitStack
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from api_app import create_app
from evaluation import EVALUATION_CASES, JUDGE_PROMPT_TEMPLATE, DeterministicMockJudge


def blocked_network(*args, **kwargs):
    raise RuntimeError("Network access attempted during offline Portion 9 evaluation")


def run_evaluation():
    root = Path(__file__).resolve().parent
    log_path = root / "transcripts" / "portion9_requests.jsonl"
    client = TestClient(create_app(log_path=log_path))
    judge = DeterministicMockJudge()
    results = []

    with ExitStack() as stack:
        stack.enter_context(patch.object(socket.socket, "connect", blocked_network))
        stack.enter_context(patch.object(socket.socket, "connect_ex", blocked_network))
        stack.enter_context(patch.object(socket, "create_connection", blocked_network))
        stack.enter_context(patch.object(socket, "getaddrinfo", blocked_network))
        for case in EVALUATION_CASES:
            api_response = client.post("/ask", json={
                "session_id": f"evaluation-{case.case_id}",
                "message": case.query,
            })
            if api_response.status_code != 200:
                raise AssertionError(f"{case.case_id} API status {api_response.status_code}")
            observed = api_response.json()
            scores, prompt = judge.judge(case, observed)
            results.append({
                "case": case.model_dump(mode="json"),
                "observed": observed,
                "judge_model": judge.model_name,
                "judge_prompt": prompt,
                "scores": scores.model_dump(mode="json"),
            })

    if judge.call_count != 15:
        raise AssertionError("MOCK_LLM judge did not score all 15 queries")
    logs = [json.loads(line) for line in log_path.read_text(encoding="utf-8").splitlines()]
    current_trace_ids = {item["observed"]["trace_id"] for item in results}
    current_logs = [entry for entry in logs if entry["trace_id"] in current_trace_ids]
    if len(current_logs) != 15 or len(current_trace_ids) != 15:
        raise AssertionError("Expected one unique JSONL request log for every evaluated query")

    metrics = ("accuracy", "grounding", "completeness", "safety")
    averages = {
        metric: round(sum(item["scores"][metric] for item in results) / len(results), 2)
        for metric in metrics
    }
    topic_sources = {
        item["case"]["expected_source"]
        for item in results
        if item["case"]["expected_source"]
        and item["case"]["expected_source"].startswith("knowledge_base/")
    }
    return {
        "portion": 9,
        "rubric_task": 13,
        "status": "PASS",
        "judge": {
            "model": judge.model_name,
            "scale": "1 (failed) to 5 (fully satisfied)",
            "prompt_template": JUDGE_PROMPT_TEMPLATE,
            "calls": judge.call_count,
        },
        "coverage": {
            "query_count": len(results),
            "knowledge_base_topics_covered": len(topic_sources),
            "out_of_scope_or_edge_cases": sum(
                item["case"]["kind"] in {"ticket", "out_of_scope", "prompt_injection"}
                for item in results
            ),
        },
        "averages": averages,
        "results": results,
        "request_log_entries_for_this_run": len(current_logs),
        "request_log_entries_total": len(logs),
        "network_check": "Python socket connection and DNS calls blocked for the complete evaluation run",
    }


if __name__ == "__main__":
    report = run_evaluation()
    destination = Path(__file__).resolve().parent / "transcripts" / "portion9_evaluation.json"
    destination.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "portion": report["portion"],
        "status": report["status"],
        "queries": report["coverage"]["query_count"],
        "kb_topics": report["coverage"]["knowledge_base_topics_covered"],
        "edge_cases": report["coverage"]["out_of_scope_or_edge_cases"],
        "averages": report["averages"],
        "request_log_entries_for_this_run": report["request_log_entries_for_this_run"],
        "evidence": str(destination.relative_to(destination.parent.parent)),
    }, indent=2))
