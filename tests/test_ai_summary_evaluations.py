import json
from pathlib import Path

import pytest

from backend.services import diff_service


CASES_PATH = Path(__file__).parent / "fixtures" / "ai_summary_eval_cases.json"


with CASES_PATH.open(encoding="utf-8") as cases_file:
    EVALUATION_CASES = json.load(cases_file)


@pytest.mark.parametrize("case", EVALUATION_CASES, ids=lambda case: case["id"])
def test_ai_summary_evaluation_case_is_complete(case):
    assert case["oldText"] != case["newText"]
    assert case["referenceSummary"].endswith(".")
    assert case["requiredTermGroups"]
    assert all(group for group in case["requiredTermGroups"])
    assert any(
        chunk["type"] != "equal"
        for chunk in diff_service.build_diff(case["oldText"], case["newText"])
    )
