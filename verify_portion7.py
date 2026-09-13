"""Run actual FastAPI HTTP/WebSocket and JSONL-log evidence for Tasks 11–12."""

import json
from pathlib import Path

from fastapi.testclient import TestClient

from api_app import create_app


def run_verification():
    destination = Path(__file__).resolve().parent / "transcripts" / "portion7_requests.jsonl"
    destination.unlink(missing_ok=True)
    client = TestClient(create_app(log_path=destination))

    health = client.get("/health")
    ask = client.post("/ask", json={
        "session_id": "http-demo",
        "message": (
            "Check ticket SUP-0014. Call +91 98765 43210. PAN ABCDE1234F, "
            "Aadhaar 1234 5678 9012, account number 123456789012, card ends in 4242."
        ),
    })
    reset = client.post("/sessions/http-demo/reset")
    with client.websocket_connect("/ws/chat/websocket-demo") as websocket:
        websocket.send_json({"message": "Please check ticket SUP-0001."})
        ws_first = websocket.receive_json()
        websocket.send_json({"message": "What is its status?"})
        ws_second = websocket.receive_json()
    health_after_disconnect = client.get("/health")
    entries = [json.loads(line) for line in destination.read_text(encoding="utf-8").splitlines()]

    if health.status_code != 200 or health_after_disconnect.status_code != 200:
        raise AssertionError("Server did not remain available after WebSocket disconnect")
    if ask.status_code != 200 or reset.status_code != 200:
        raise AssertionError("Required HTTP endpoint failed")
    ask_body = ask.json()
    if not ask_body["review"] or not ask_body["review"]["approved"]:
        raise AssertionError("HTTP route did not run the AutoGen review")
    if not ws_second["reply"]["memory_used"] or ws_second["reply"]["resolved_record_id"] != "SUP-0001":
        raise AssertionError("WebSocket multi-turn session did not retain context")
    if len(entries) != 6:
        raise AssertionError("Expected one JSONL record for two health checks, ask, reset, and two WebSocket messages")
    for entry in entries:
        if not entry["trace_id"] or entry["duration_ms"] < 0:
            raise AssertionError("Log record missing trace ID or timing")
    serialized = destination.read_text(encoding="utf-8")
    for forbidden in ("98765", "ABCDE1234F", "1234 5678 9012", "123456789012", "4242"):
        if forbidden in serialized:
            raise AssertionError("Raw PII reached the JSONL log")

    return {
        "portion": 7,
        "rubric_tasks": [11, 12],
        "status": "PASS",
        "http_endpoints": {
            "GET /health": health.json(),
            "POST /ask": ask_body,
            "POST /sessions/{session_id}/reset": reset.json(),
        },
        "websocket": {
            "endpoint": "/ws/chat/{session_id}",
            "first_response": ws_first,
            "followup_response": ws_second,
            "disconnect_handled_server_still_available": health_after_disconnect.status_code == 200,
        },
        "jsonl_log": {
            "path": str(destination.relative_to(destination.parent.parent)),
            "entries": entries,
            "one_entry_per_processed_request": len(entries) == 6,
            "raw_pii_absent": True,
        },
    }


if __name__ == "__main__":
    report = run_verification()
    evidence = Path(__file__).resolve().parent / "transcripts" / "portion7_evidence.json"
    evidence.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "portion": report["portion"],
        "status": report["status"],
        "http_endpoints": list(report["http_endpoints"]),
        "websocket_memory_used": report["websocket"]["followup_response"]["reply"]["memory_used"],
        "disconnect_handled": report["websocket"]["disconnect_handled_server_still_available"],
        "jsonl_entries": len(report["jsonl_log"]["entries"]),
        "raw_pii_absent": report["jsonl_log"]["raw_pii_absent"],
        "evidence": str(evidence.relative_to(evidence.parent.parent)),
    }, indent=2))
