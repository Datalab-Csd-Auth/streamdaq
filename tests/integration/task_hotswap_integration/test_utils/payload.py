"""Builds the initial and updated ``bulk_create`` payloads for the task hot-swap test.
A task is hot-swapped in the middle of the stream, changing the output path
and the check thresholds. Then, the output files is compared against the expected ones
to verify that the task hot-swapping took effect mid-stream and also the watermarking
mechanism worked as expected, prunning as much as possible double processing."""

from typing import Any

from task_hotswap_integration.test_utils.stream import INT, TIME

TASK_NAME = "task_hotswapping"

INPUT_FILENAME = "input.jsonl"

INITIAL_INSTANT_OUTPUT = "output_initial.jsonl"
INITIAL_WINDOW_OUTPUT = "output_initial_window.jsonl"
FINAL_INSTANT_OUTPUT = "output_final.jsonl"
FINAL_WINDOW_OUTPUT = "output_final_window.jsonl"


def _input_config() -> dict[str, Any]:
    return {
        "type": "jsonlines",
        "params": {
            "path": INPUT_FILENAME,
            "mode": "streaming",
            "schema": {TIME: "int", INT: "int"},
        },
    }


def _task_payload(
    *, instant_high: int, window_must_be: str, output_filename: str
) -> dict[str, Any]:
    return {
        "name": TASK_NAME,
        "windowby_column": TIME,
        "input": _input_config(),
        "output": {"type": "jsonlines", "params": {"filename": output_filename}},
        "instant_checks": [
            {
                "name": "value_in_range",
                "check_class": "InRange",
                "params": {"column": INT, "low": 0, "high": instant_high},
            }
        ],
        "window_checks_config": {
            "window": {"type": "tumbling", "params": {"duration": 1000}},
            "checks": [
                {
                    "name": "count_ok",
                    "measure": {"type": "Count", "params": {"column": INT}},
                    "must_be": window_must_be,
                }
            ],
        },
    }


def build_initial_payload() -> list[dict[str, Any]]:
    """Initial config: wide instant range and a loose window-count threshold."""
    return [
        _task_payload(
            instant_high=100, window_must_be="== 2", output_filename=INITIAL_INSTANT_OUTPUT
        )
    ]


def build_updated_payload() -> list[dict[str, Any]]:
    """Updated config (same task name): narrower instant range and a stricter window threshold."""
    return [
        _task_payload(instant_high=25, window_must_be=">= 3", output_filename=FINAL_INSTANT_OUTPUT)
    ]
