"""Builds the ``bulk_create`` payload for the Pathway-delegated window options test.
A single window-only task keys its tumbling windows per group (``groupby_column``)
and waits for late rows (``wait_for_late``). The window output is then compared
against the expected one to verify that rows arriving late within the wait frame
are counted, rows arriving beyond it are dropped, and counts are kept per group."""

from typing import Any

from window_options_integration.test_utils.stream import INSTANCE, INT, TIME

TASK_NAME = "window_options"

INPUT_FILENAME = "input.jsonl"

OUTPUT_FILENAME = "output.jsonl"
WINDOW_OUTPUT = "output_window.jsonl"
WINDOW_OUTPUT_LABEL = "output_window"

WAIT_FOR_LATE = 2500


def _input_config() -> dict[str, Any]:
    return {
        "type": "jsonlines",
        "params": {
            "path": INPUT_FILENAME,
            "mode": "streaming",
            "schema": {TIME: "int", INT: "int", INSTANCE: "str"},
        },
    }


def build_payload() -> list[dict[str, Any]]:
    """Window-only config: per-group tumbling windows that wait ``WAIT_FOR_LATE`` for late rows."""
    return [
        {
            "name": TASK_NAME,
            "input": _input_config(),
            "output": {"type": "jsonlines", "params": {"filename": OUTPUT_FILENAME}},
            "wait_for_late": WAIT_FOR_LATE,
            "window_checks_config": {
                "windowby_column": TIME,
                "groupby_column": INSTANCE,
                "window": {"type": "tumbling", "params": {"duration": 1000}},
                "checks": [
                    {
                        "name": "value_count",
                        "measure": {"type": "Count", "params": {"column": INT}},
                    },
                    {
                        "name": "enough_readings",
                        "measure": {"type": "Count", "params": {"column": INT}},
                        "must_be": ">= 3",
                    },
                ],
            },
        }
    ]
