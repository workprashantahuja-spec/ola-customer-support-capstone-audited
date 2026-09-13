"""Run every saved verifier and test suite as one offline integration check."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent

COMMANDS = [
    [sys.executable, "dataset.py"],
    [sys.executable, "verify_task3.py"],
    [sys.executable, "verify_portion2.py"],
    [sys.executable, "verify_portion3.py"],
    [sys.executable, "verify_portion4.py"],
    [sys.executable, "verify_portion5.py"],
    [sys.executable, "verify_portion6.py"],
    [sys.executable, "verify_portion7.py"],
    [sys.executable, "verify_portion8.py"],
    [sys.executable, "verify_portion9.py"],
    [sys.executable, "audit_regressions.py"],
    [
        sys.executable, "-m", "unittest", "-q",
        "test_api_app.py", "test_autogen_review.py", "test_memory_guardrails.py",
        "test_crew_workflow.py", "test_governance_cache.py", "test_evaluation.py",
        "test_submission_audit.py",
    ],
    [sys.executable, "-m", "unittest", "discover", "-s", "tests", "-q"],
    [sys.executable, "-m", "pip", "check"],
]


def safe_environment():
    environment = os.environ.copy()
    for key in list(environment):
        if key.upper().endswith("_API_KEY") or key.lower() in {
            "http_proxy", "https_proxy", "all_proxy"
        }:
            environment.pop(key, None)
    environment["CREWAI_DISABLE_TELEMETRY"] = "true"
    environment["OTEL_SDK_DISABLED"] = "true"
    environment["TOKENIZERS_PARALLELISM"] = "false"
    return environment


def run_all():
    results = []
    for command in COMMANDS:
        completed = subprocess.run(
            command,
            cwd=ROOT,
            env=safe_environment(),
            text=True,
            capture_output=True,
            timeout=240,
            check=False,
        )
        combined = (completed.stdout + "\n" + completed.stderr).strip()
        results.append({
            "command": [Path(command[0]).name, *command[1:]],
            "return_code": completed.returncode,
            "passed": completed.returncode == 0,
            "output_tail": combined[-2500:],
        })
        if completed.returncode != 0:
            raise RuntimeError(
                f"Integration command failed: {' '.join(command)}\n{combined[-2500:]}"
            )
    return {
        "status": "PASS",
        "commands_passed": len(results),
        "commands_total": len(COMMANDS),
        "runtime": {
            "mock_llm": True,
            "api_keys_removed": True,
            "proxy_variables_removed": True,
            "crewai_telemetry_disabled": True,
        },
        "results": results,
    }


if __name__ == "__main__":
    report = run_all()
    destination = ROOT / "transcripts" / "full_integration_evidence.json"
    destination.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "status": report["status"],
        "commands_passed": report["commands_passed"],
        "commands_total": report["commands_total"],
        "mock_llm": report["runtime"]["mock_llm"],
        "api_keys_removed": report["runtime"]["api_keys_removed"],
        "evidence": str(destination.relative_to(ROOT)),
    }, indent=2))
