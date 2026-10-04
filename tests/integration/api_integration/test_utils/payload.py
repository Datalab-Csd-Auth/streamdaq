"""
Builds the ``bulk_create`` payload that exercises every specified measure and instant check.

Two tasks run over the same finite input: one sliding window, one tumbling window, each
carrying all specified instant checks and all specified measures as window checks.
"""

from typing import Any

from api_integration.test_utils.registry import (
    CATEGORICAL,
    FLOAT,
    INSTANT_CHECK_SPECS,
    INT,
    MEASURE_SPECS,
    TEXT,
    TIME,
)

_MODULE = "api_integration.test_utils.stream"
_CLASS = "FiniteIntegrationStream"


def input_config_payload() -> dict[str, Any]:
    return {
        "type": "python_connector",
        "params": {
            "module": _MODULE,
            "class_name": _CLASS,
            "data_type": "native",
            "schema": {
                TIME: "int",
                INT: "int",
                FLOAT: "float",
                TEXT: "str",
                CATEGORICAL: "str",
            },
        },
    }


def window_checks_payload() -> list[dict[str, Any]]:
    checks: list[dict[str, Any]] = []
    for measure_name, spec in sorted(MEASURE_SPECS.items()):
        thresholds = (spec.must_be, *spec.extra_must_be)
        measure_contains_suffixes = len(spec.suffixes) > 0
        for index, must_be in enumerate(thresholds):
            name = (
                f"wc_{measure_name}_{spec.suffixes[index]}"
                if measure_contains_suffixes
                else f"wc_{measure_name}"
            )
            checks.append(
                {
                    "name": name,
                    "measure": {"type": measure_name, "params": spec.params},
                    "must_be": must_be,
                }
            )
    return checks


def instant_checks_payload() -> list[dict[str, Any]]:
    return [
        {"name": f"ic_{name}", "check_class": spec.check_class, "params": spec.params}
        for name, spec in sorted(INSTANT_CHECK_SPECS.items())
    ]


def task_payload(
    name: str, window_type: str, window_params: dict[str, Any], output_filename: str
) -> dict:
    return {
        "name": name,
        "windowby_column": TIME,
        "input": input_config_payload(),
        "output": {"type": "jsonlines", "params": {"filename": output_filename}},
        "instant_checks": instant_checks_payload(),
        "window_checks_config": {
            "window": {"type": window_type, "params": window_params},
            "checks": window_checks_payload(),
        },
    }


def build_request_payload(sliding_output: str, tumbling_output: str) -> list[dict[str, Any]]:
    """Two tasks over the same stream: one sliding window, one tumbling window."""
    return [
        task_payload(
            "integration_sliding", "sliding", {"duration": 1000, "hop": 500}, sliding_output
        ),
        task_payload("integration_tumbling", "tumbling", {"duration": 1000}, tumbling_output),
    ]


def instant_check_names() -> list[str]:
    """Instant-check output column names, the single source of truth for the test."""
    return [check["name"] for check in instant_checks_payload()]


def window_check_names() -> list[str]:
    """Window-check output column names, the single source of truth for the test."""
    return [check["name"] for check in window_checks_payload()]
