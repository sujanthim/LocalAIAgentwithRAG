"""
Evaluation script for LocalAIAgentWithRAG.

Runs all cases in eval_dataset.json and reports per-test pass/fail
plus an overall score. No JWT required — eval calls internal functions directly.

Usage:
    python eval.py
    python eval.py --dataset path/to/custom_eval.json
"""

import argparse
import json
import os
import sys

from vector import initialize_vector_store, get_retriever_for_role
from guardrails import check_input
from main import build_chain, format_docs

EVAL_DATASET_DEFAULT = "eval_dataset.json"

# Cache retrievers and chains per role to avoid rebuilding for every case
_retrievers: dict = {}
_chains: dict = {}


def _get_chain(role: str):
    if role not in _chains:
        retriever = get_retriever_for_role(role)
        _retrievers[role] = retriever
        _chains[role] = build_chain(retriever)
    return _retrievers[role], _chains[role]


def _run_guardrail(case: dict) -> tuple[bool, str]:
    question = case["question"]
    expected_blocked = case["expected_blocked"]
    valid, _ = check_input(question)
    actually_blocked = not valid
    passed = actually_blocked == expected_blocked
    detail = (
        f"guardrail {'blocked' if actually_blocked else 'allowed'} "
        f"(expected: {'blocked' if expected_blocked else 'allowed'})"
    )
    return passed, detail


def _run_retrieval_and_answer(case: dict) -> tuple[bool, str]:
    role = case["role"]
    question = case["question"]
    expected_source = case["expected_source"]
    expected_keywords = case["expected_answer_contains"]

    retriever, chain = _get_chain(role)

    docs = retriever.invoke(question)
    sources = [os.path.basename(d.metadata.get("source", "")) for d in docs]
    retrieval_ok = expected_source in sources

    answer = chain.invoke(question)
    answer_lower = answer.lower()
    missing_keywords = [kw for kw in expected_keywords if kw.lower() not in answer_lower]
    answer_ok = not missing_keywords

    passed = retrieval_ok and answer_ok

    retrieval_detail = "OK" if retrieval_ok else f"MISS — expected '{expected_source}', got {sources}"
    answer_detail = "OK" if answer_ok else f"MISS — keywords not found: {missing_keywords}"
    detail = f"retrieval={retrieval_detail} | answer={answer_detail}"
    return passed, detail


def run_eval(dataset_path: str) -> bool:
    print(f"Loading eval dataset: {dataset_path}")
    with open(dataset_path) as f:
        cases = json.load(f)

    print("Initializing vector store...")
    initialize_vector_store()
    print()

    results = []
    col_width = max(len(c["id"]) for c in cases)

    for case in cases:
        case_id = case["id"]
        case_type = case["type"]

        if case_type == "guardrail":
            passed, detail = _run_guardrail(case)
        elif case_type == "retrieval_and_answer":
            passed, detail = _run_retrieval_and_answer(case)
        else:
            passed, detail = False, f"unknown type '{case_type}'"

        status = "PASS" if passed else "FAIL"
        print(f"[{status}] {case_id:<{col_width}}  {detail}")
        results.append({"id": case_id, "passed": passed})

    total = len(results)
    num_passed = sum(1 for r in results if r["passed"])
    pct = int(100 * num_passed / total) if total else 0

    print()
    print("=" * 60)
    print(f"Score: {num_passed}/{total} passed ({pct}%)")

    failed_ids = [r["id"] for r in results if not r["passed"]]
    if failed_ids:
        print(f"Failed cases ({len(failed_ids)}):")
        for fid in failed_ids:
            print(f"  - {fid}")

    return num_passed == total


def main():
    parser = argparse.ArgumentParser(description="Run RAG eval suite")
    parser.add_argument(
        "--dataset",
        default=EVAL_DATASET_DEFAULT,
        help=f"Path to eval dataset JSON (default: {EVAL_DATASET_DEFAULT})",
    )
    args = parser.parse_args()

    if not os.path.exists(args.dataset):
        print(f"ERROR: dataset not found: {args.dataset}")
        sys.exit(1)

    all_passed = run_eval(args.dataset)
    sys.exit(0 if all_passed else 1)


if __name__ == "__main__":
    main()
