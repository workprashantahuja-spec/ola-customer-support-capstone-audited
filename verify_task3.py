"""Reproduce Task 3 integration evidence using real embeddings and Chroma.

Python socket connections and DNS resolution are blocked during this check.
That is a Python-level check, not an operating-system network isolation test.
"""

from contextlib import ExitStack
import importlib.metadata
import json
from pathlib import Path
import socket
import subprocess
import sys
from unittest.mock import patch

from rag_config import COLLECTION_NAMES, PROJECT_ROOT
from rag_index import PolicyIndex


CASES = [
    ("What is the maximum service credit for one incident?", "08_service_credits.md"),
    ("How long are request logs retained?", "12_ticket_data_retention.md"),
    ("Is routine support available on Sunday?", "06_business_hours_and_holidays.md"),
]


def blocked_network(*args, **kwargs):
    raise RuntimeError("Network access attempted during the offline Task 3 check")


def run_check():
    with ExitStack() as stack:
        stack.enter_context(patch.object(socket.socket, "connect", blocked_network))
        stack.enter_context(patch.object(socket.socket, "connect_ex", blocked_network))
        stack.enter_context(patch.object(socket, "create_connection", blocked_network))
        stack.enter_context(patch.object(socket, "getaddrinfo", blocked_network))
        index = PolicyIndex()
        if "--reopen-check" in sys.argv:
            return {
                strategy: {
                    "count": index.client.get_collection(name, embedding_function=None).count(),
                    "result": index.query(CASES[0][0], strategy),
                }
                for strategy, name in COLLECTION_NAMES.items()
            }
        first = index.build()
        repeated = index.build()
        if first["collections"] != repeated["collections"]:
            raise AssertionError("Repeated upsert changed the index counts or configuration")
        samples = []
        for question, expected in CASES:
            for strategy in COLLECTION_NAMES:
                result = index.query(question, strategy)
                matched = expected in {hit["doc_id"] for hit in result["hits"]}
                if not matched:
                    raise AssertionError(f"Expected source missing: {question} / {strategy}")
                samples.append({"expected_doc": expected, "expected_doc_in_top3": matched,
                                **result})
        versions = {name: importlib.metadata.version(name) for name in [
            "torch", "sentence-transformers", "chromadb", "transformers",
            "huggingface-hub", "numpy",
        ]}
    # A separate interpreter reopens the files and retrieves without a build call.
    reopened_process = subprocess.run(
        [sys.executable, str(Path(__file__).resolve()), "--reopen-check"],
        cwd=PROJECT_ROOT, check=True, capture_output=True, text=True,
    )
    reopened = json.loads(reopened_process.stdout)
    for strategy in COLLECTION_NAMES:
        if reopened[strategy]["count"] != first["collections"][strategy]["chunks"]:
            raise AssertionError("Collection count changed after reopening")
        if CASES[0][1] not in {hit["doc_id"] for hit in reopened[strategy]["result"]["hits"]}:
            raise AssertionError("Persistent index failed retrieval after reopening")
    return {
        "task": 3, "status": "PASS", "python": sys.version.split()[0],
        "platform": sys.platform, "versions": versions,
        "network_check": "Python socket connection and DNS calls blocked during build/query",
        "build": first, "repeated_upsert_same_counts": True,
        "separate_process_reopen": {key: {"chunks": val["count"], "retrieval_passed": True}
                                    for key, val in reopened.items()},
        "retrieval_cases_passed": len(samples), "retrieval_cases": samples,
        "scope": "Task 3 retrieval check only; generation and scored evaluation are pending",
    }


if __name__ == "__main__":
    report = run_check()
    if "--reopen-check" in sys.argv:
        print(json.dumps(report))
    else:
        destination = PROJECT_ROOT / "transcripts" / "task3_search_check.json"
        destination.parent.mkdir(exist_ok=True)
        destination.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n",
                               encoding="utf-8")
        print(json.dumps({key: value for key, value in report.items()
                          if key != "retrieval_cases"}, indent=2))
        print("Full evidence: transcripts/task3_search_check.json")
