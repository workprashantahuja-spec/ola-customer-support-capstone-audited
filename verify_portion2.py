"""Create real Tasks 4-5 evidence with local embeddings and no network."""

from contextlib import ExitStack
import json
from pathlib import Path
import socket
from unittest.mock import patch

from grounded_answers import GroundedAnswerEngine
from rag_config import FALLBACK_THRESHOLD, PROJECT_ROOT
from rag_index import PolicyIndex


CALIBRATION_IN_SCOPE = [
    ("What is the maximum service credit for one incident?", "08_service_credits.md"),
    ("How long are closed tickets and request logs retained?", "12_ticket_data_retention.md"),
    ("Is routine support available on Sunday?", "06_business_hours_and_holidays.md"),
    ("What happens after a feedback rating of 1?", "09_feedback_collection.md"),
    ("Can a verified VIP P3 ticket take priority over a P1 case?", "10_vip_handling.md"),
]

CALIBRATION_OUT_OF_SCOPE = [
    "What is the weather in Mumbai tomorrow?",
    "How do I change a tyre on my car?",
    "Write a poem about the moon.",
]

COMPARISON_CASES = [
    ("Which issues are classified as P1 Critical?", {"01_ticket_priority.md"}),
    ("How quickly must a P2 High ticket be acknowledged and resolved?", {"02_sla_by_severity.md"}),
    ("Which human team handles a Technical Issue ticket?", {"03_escalation_matrix.md"}),
    ("Can a charge for a cancelled or unprovided ride receive a refund review?", {"04_refunds_and_compensation.md"}),
    ("Can ticket details be shared in a public social media reply?", {"05_communication_channels.md"}),
    ("Is routine support available on Sunday?", {"06_business_hours_and_holidays.md"}),
    ("What happens on the third report of the same unresolved complaint?", {"07_repeat_complaints.md"}),
    ("What is the maximum service credit for one incident?", {"08_service_credits.md"}),
    ("What happens after a feedback rating of 1?", {"09_feedback_collection.md"}),
    ("Can a verified VIP P3 ticket take priority over a P1 case?", {"10_vip_handling.md"}),
    ("How often are progress updates provided during a widespread outage?", {"11_outage_communication.md"}),
    ("How long are closed tickets and request logs retained?", {"12_ticket_data_retention.md"}),
]

ANSWER_CASES = CALIBRATION_IN_SCOPE + [
    ("What happens on the third report of the same unresolved complaint?", "07_repeat_complaints.md")
]


def blocked_network(*args, **kwargs):
    raise RuntimeError("Network access attempted during offline Portion 2 verification")


def unique_parent_docs(hits):
    return list(dict.fromkeys(hit["doc_id"] for hit in hits))


def metrics(retrieved, relevant):
    retrieved_set = set(retrieved)
    true_positives = len(retrieved_set & relevant)
    precision = true_positives / len(retrieved_set) if retrieved_set else 0.0
    recall = true_positives / len(relevant) if relevant else 0.0
    return true_positives, precision, recall


def run_verification():
    with ExitStack() as stack:
        for target, attribute in [
            (socket.socket, "connect"), (socket.socket, "connect_ex"),
            (socket, "create_connection"), (socket, "getaddrinfo"),
        ]:
            stack.enter_context(patch.object(target, attribute, blocked_network))

        index = PolicyIndex()
        calibration = {"in_scope": [], "out_of_scope": []}
        for question, expected_doc in CALIBRATION_IN_SCOPE:
            item = {"question": question, "expected_doc": expected_doc, "scores": {}}
            for strategy in ("fixed", "sentence"):
                hit = index.query(question, strategy, top_k=1)["hits"][0]
                if hit["doc_id"] != expected_doc:
                    raise AssertionError(f"Calibration source mismatch: {question} / {strategy}")
                item["scores"][strategy] = hit["cosine_similarity"]
            calibration["in_scope"].append(item)

        for question in CALIBRATION_OUT_OF_SCOPE:
            item = {"question": question, "scores": {}, "top_sources": {}}
            for strategy in ("fixed", "sentence"):
                hit = index.query(question, strategy, top_k=1)["hits"][0]
                item["scores"][strategy] = hit["cosine_similarity"]
                item["top_sources"][strategy] = hit["doc_id"]
            calibration["out_of_scope"].append(item)

        all_in_scores = [score for item in calibration["in_scope"]
                         for score in item["scores"].values()]
        all_out_scores = [score for item in calibration["out_of_scope"]
                          for score in item["scores"].values()]
        min_in, max_out = min(all_in_scores), max(all_out_scores)
        if not max_out < FALLBACK_THRESHOLD <= min_in:
            raise AssertionError("Configured threshold is not between calibration clusters")
        calibration["summary"] = {
            "minimum_in_scope_score": min_in,
            "maximum_out_of_scope_score": max_out,
            "observed_separation": round(min_in - max_out, 6),
            "chosen_threshold": FALLBACK_THRESHOLD,
            "rule": "answer when top similarity >= threshold; otherwise return fallback",
        }

        comparison = {"top_k_chunks": 3, "deduplication": "parent document ID", "strategies": {}}
        for strategy in ("fixed", "sentence"):
            rows = []
            for question, relevant in COMPARISON_CASES:
                result = index.query(question, strategy, top_k=3)
                retrieved = unique_parent_docs(result["hits"])
                tp, precision, recall = metrics(retrieved, relevant)
                rows.append({
                    "question": question, "relevant_docs": sorted(relevant),
                    "retrieved_unique_docs": retrieved,
                    "arithmetic": {
                        "true_positives": tp,
                        "retrieved_unique_count": len(retrieved),
                        "relevant_count": len(relevant),
                        "precision": f"{tp}/{len(retrieved)} = {precision:.4f}",
                        "recall": f"{tp}/{len(relevant)} = {recall:.4f}",
                    },
                    "precision": round(precision, 4), "recall": round(recall, 4),
                })
            comparison["strategies"][strategy] = {
                "queries": rows,
                "macro_precision": round(sum(row["precision"] for row in rows) / len(rows), 4),
                "macro_recall": round(sum(row["recall"] for row in rows) / len(rows), 4),
                "top1_correct": sum(row["retrieved_unique_docs"][0] in row["relevant_docs"]
                                    for row in rows),
                "query_count": len(rows),
            }

        fixed = comparison["strategies"]["fixed"]
        sentence = comparison["strategies"]["sentence"]
        if sentence["macro_precision"] <= fixed["macro_precision"] or sentence["macro_recall"] < fixed["macro_recall"]:
            raise AssertionError("Measured evidence does not support the sentence recommendation")
        comparison["recommendation"] = {
            "strategy": "sentence",
            "reason": (
                "Sentence chunks achieved higher macro precision and recall on the same 12 questions, "
                "while preserving complete policy sentences for grounded answers."
            ),
        }

        engine = GroundedAnswerEngine(index=index)
        answer_demos = []
        for question, expected_doc in ANSWER_CASES:
            retrieval = index.query(question, "sentence", top_k=3)
            result = engine.answer(question)
            if result["fallback"] or result["sources"] != [f"knowledge_base/{expected_doc}"]:
                raise AssertionError(f"Grounded answer failed: {question}")
            first_body = retrieval["hits"][0]["text"].partition("\n")[2].strip()
            if result["answer"] != first_body:
                raise AssertionError("Answer contains text outside the retrieved source body")
            answer_demos.append(result)

        fallback_demo = engine.answer(CALIBRATION_OUT_OF_SCOPE[0])
        if not fallback_demo["fallback"] or engine.model.call_count != len(ANSWER_CASES):
            raise AssertionError("Fallback must avoid the generation model")

    return {
        "portion": 2, "rubric_tasks": [4, 5], "status": "PASS",
        "runtime": "local SentenceTransformers + ChromaDB + deterministic extractive MOCK_LLM",
        "network_check": "Python socket connection and DNS calls blocked",
        "calibration": calibration, "comparison": comparison,
        "grounded_answer_demonstrations": answer_demos,
        "out_of_scope_fallback_demonstration": fallback_demo,
        "model_calls": engine.model.call_count,
        "grounding_proof": "Each supported answer equals the body of its first retrieved policy chunk.",
    }


if __name__ == "__main__":
    report = run_verification()
    output = PROJECT_ROOT / "transcripts" / "portion2_evidence.json"
    output.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({
        "portion": report["portion"], "status": report["status"],
        "threshold": report["calibration"]["summary"],
        "comparison": {
            key: {name: value for name, value in data.items() if name != "queries"}
            for key, data in report["comparison"]["strategies"].items()
        },
        "recommended_strategy": report["comparison"]["recommendation"]["strategy"],
        "grounded_answers": len(report["grounded_answer_demonstrations"]),
        "fallback_passed": report["out_of_scope_fallback_demonstration"]["fallback"],
        "evidence": str(output.relative_to(PROJECT_ROOT)),
    }, indent=2))
