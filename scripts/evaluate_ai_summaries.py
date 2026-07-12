import argparse
import json
import sys
import urllib.error
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CASES_PATH = PROJECT_ROOT / "tests" / "fixtures" / "ai_summary_eval_cases.json"
sys.path.insert(0, str(PROJECT_ROOT))

from backend.services import ai_summary_service, diff_service


def load_cases():
    with CASES_PATH.open(encoding="utf-8") as cases_file:
        return json.load(cases_file)


def score_summary(summary, case):
    lowered_summary = summary.lower()
    matched_groups = 0

    for alternatives in case["requiredTermGroups"]:
        if any(term.lower() in lowered_summary for term in alternatives):
            matched_groups += 1

    forbidden_matches = [
        term for term in case["forbiddenTerms"] if term.lower() in lowered_summary
    ]
    passed = matched_groups == len(case["requiredTermGroups"]) and not forbidden_matches
    return passed, matched_groups, forbidden_matches


def build_case_prompt(case):
    chunks = diff_service.build_diff(case["oldText"], case["newText"])
    return ai_summary_service.build_summary_prompt(
        chunks,
        document_title=case["title"],
        from_note=case["fromNote"],
        to_note=case["toNote"],
    )


def run_case(case, dry_run):
    prompt = build_case_prompt(case)
    if dry_run:
        print(f"[READY] {case['id']} ({len(prompt)} prompt characters)")
        return True

    summary = ai_summary_service.clean_summary(
        ai_summary_service.request_openai_summary(prompt)
    )
    passed, matched_groups, forbidden_matches = score_summary(summary, case)
    status = "PASS" if passed else "REVIEW"

    print(f"[{status}] {case['id']}")
    print(f"  Reference: {case['referenceSummary']}")
    print(f"  Actual:    {summary}")
    print(
        f"  Required concepts: {matched_groups}/{len(case['requiredTermGroups'])}; "
        f"forbidden matches: {forbidden_matches or 'none'}"
    )
    return passed


def main():
    parser = argparse.ArgumentParser(description="Evaluate AI diff summaries.")
    parser.add_argument("--dry-run", action="store_true", help="Validate cases without API calls.")
    parser.add_argument("--case", help="Run one case by id.")
    args = parser.parse_args()

    cases = load_cases()
    if args.case:
        cases = [case for case in cases if case["id"] == args.case]
        if not cases:
            parser.error(f"Unknown case: {args.case}")

    if not args.dry_run and not ai_summary_service.OPENAI_API_KEY:
        parser.error("OPENAI_API_KEY is not configured in backend/.env")

    try:
        results = [run_case(case, args.dry_run) for case in cases]
    except (OSError, TimeoutError, ValueError, urllib.error.URLError) as error:
        print(f"Evaluation stopped: {error}", file=sys.stderr)
        return 1

    if args.dry_run:
        print(f"\n{len(results)} evaluation cases are ready.")
        return 0

    passed = sum(results)
    print(f"\nAutomated checks passed for {passed}/{len(results)} cases.")
    print("Review every output against its reference before accepting a prompt change.")
    return 0 if passed == len(results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
