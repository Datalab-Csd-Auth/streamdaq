"""Data-driven EVB regression suite.

Each ``cases/*.json`` file is a self-contained regression case describing a raw EVB
message and its expected validation outcome. Every case is discovered automatically and
run on every test invocation, so collecting a new problematic message is just a matter of
dropping a new JSON file into ``cases/`` without further code changes.

Case file schema::

    {
        "description": "human-readable summary of what this message exercises",
        "message": { "measurements": [ ... ] },   // a raw EVB message
        "expected_errors": [ "substring", ... ]    // omit or leave empty for a valid message
    }

A message is expected to be valid when ``expected_errors`` is absent or empty; otherwise
each listed substring must appear in the raised validation error.
"""

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from streamdaq.schema.evb.definitions import ValidatableEVBSchema

_CASES_DIR = Path(__file__).parent / "cases"


def _load_cases() -> list[dict]:
    cases = []
    for path in sorted(_CASES_DIR.glob("*.json")):
        case = json.loads(path.read_text())
        case["_id"] = path.stem
        cases.append(case)
    return cases


_CASES = _load_cases()


def test_regression_cases_exist():
    """Guard against the suite silently passing because no cases were discovered."""
    assert _CASES, f"No EVB regression cases found in {_CASES_DIR}"


@pytest.mark.parametrize("case", _CASES, ids=[c["_id"] for c in _CASES])
def test_evb_message_validation(case: dict):
    message = case["message"]
    expected_errors = case.get("expected_errors", [])

    if not expected_errors:
        # Expected valid: validation must not raise.
        ValidatableEVBSchema(**message)
        return

    with pytest.raises(ValidationError) as exc_info:
        ValidatableEVBSchema(**message)

    reported = str(exc_info.value)
    missing = [substring for substring in expected_errors if substring not in reported]
    assert not missing, (
        f"Case '{case['_id']}' did not report expected error(s) {missing}.\n"
        f"Actual validation error:\n{reported}"
    )
